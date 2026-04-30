"""Sprint 4 — Procedural Memory tests.

12 tests covering:
- 4A: save_procedure (upsert by name), search_procedures, get_applicable_procedures
- 4B: list_procedures, FTS exclusion of deprecated
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID
from craft_memory_mcp.db import (
    get_applicable_procedures,
    list_procedures,
    save_procedure,
    search_procedures,
)


# ── CRUD ──────────────────────────────────────────────────────────────


def test_save_procedure_returns_id(db_conn):
    """save_procedure returns a positive integer id."""
    pid = save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="deploy-backend",
        trigger_context="When deploying the backend service to production",
        steps_md="1. Pull latest main.\n2. Run migrations.\n3. Restart gunicorn.",
    )
    assert isinstance(pid, int)
    assert pid > 0


def test_save_procedure_upserts_by_name(db_conn):
    """Calling save_procedure with the same name updates in place (same id)."""
    pid1 = save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="run-tests",
        trigger_context="Before merging any PR",
        steps_md="1. pytest -q",
    )
    pid2 = save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="run-tests",
        trigger_context="Before merging any PR — updated",
        steps_md="1. pytest -q\n2. mypy .",
        confidence=0.9,
    )
    assert pid1 == pid2


def test_save_procedure_stores_steps_md(db_conn):
    """save_procedure persists steps_md accurately."""
    steps = "Step 1: git pull\nStep 2: docker-compose up -d\nStep 3: check logs"
    pid = save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="start-local-env",
        trigger_context="When setting up local dev environment",
        steps_md=steps,
    )
    row = db_conn.execute("SELECT steps_md FROM procedures WHERE id=?", (pid,)).fetchone()
    assert row["steps_md"] == steps


def test_save_procedure_stores_confidence(db_conn):
    """save_procedure persists the confidence score."""
    pid = save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="hotfix-process",
        trigger_context="When a critical bug hits production",
        steps_md="1. Create hotfix branch.\n2. Fix.\n3. Deploy.\n4. Merge back.",
        confidence=0.85,
    )
    row = db_conn.execute("SELECT confidence FROM procedures WHERE id=?", (pid,)).fetchone()
    assert abs(row["confidence"] - 0.85) < 0.001


# ── Search ────────────────────────────────────────────────────────────


def test_search_procedures_finds_by_name(db_conn):
    """search_procedures returns procedures matching the name."""
    save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="database-migration",
        trigger_context="When applying schema changes",
        steps_md="1. Backup DB.\n2. Run alembic upgrade head.\n3. Verify.",
    )
    results = search_procedures(db_conn, "database-migration", TEST_WORKSPACE_ID)
    names = [r["name"] for r in results]
    assert "database-migration" in names


def test_search_procedures_finds_by_trigger_context(db_conn):
    """search_procedures matches content in trigger_context field."""
    save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="incident-response",
        trigger_context="When a production outage alert fires",
        steps_md="1. Check Grafana.\n2. Page on-call.\n3. Open incident channel.",
    )
    results = search_procedures(db_conn, "outage alert", TEST_WORKSPACE_ID)
    assert len(results) >= 1
    assert any(r["name"] == "incident-response" for r in results)


def test_search_procedures_finds_by_steps(db_conn):
    """search_procedures matches content inside steps_md."""
    save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="release-checklist",
        trigger_context="Before cutting a release",
        steps_md="1. Tag the commit.\n2. Build Docker image.\n3. Push to registry.",
    )
    results = search_procedures(db_conn, "Docker image", TEST_WORKSPACE_ID)
    assert any(r["name"] == "release-checklist" for r in results)


def test_search_procedures_excludes_deprecated(db_conn):
    """search_procedures does not return deprecated procedures."""
    save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="old-deploy-flow",
        trigger_context="Deprecated deploy process for legacy system",
        steps_md="1. FTP upload.\n2. Restart Apache.",
        status="deprecated",
    )
    results = search_procedures(db_conn, "deploy", TEST_WORKSPACE_ID)
    statuses = [r.get("status") for r in results]
    assert "deprecated" not in statuses


# ── Applicable ────────────────────────────────────────────────────────


def test_get_applicable_procedures_returns_matching(db_conn):
    """get_applicable_procedures finds the most relevant procedure for a context."""
    save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="code-review-process",
        trigger_context="When reviewing a pull request",
        steps_md="1. Check tests.\n2. Check lint.\n3. Approve or request changes.",
        confidence=0.8,
    )
    results = get_applicable_procedures(db_conn, "reviewing pull request", TEST_WORKSPACE_ID)
    assert len(results) >= 1
    assert any(r["name"] == "code-review-process" for r in results)


def test_get_applicable_procedures_excludes_deprecated(db_conn):
    """get_applicable_procedures skips deprecated procedures."""
    save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="old-review-process",
        trigger_context="Reviewing pull requests — old way",
        steps_md="1. Email the team.\n2. Wait.",
        status="deprecated",
    )
    results = get_applicable_procedures(db_conn, "reviewing pull request", TEST_WORKSPACE_ID)
    statuses = [r.get("status") for r in results]
    assert "deprecated" not in statuses


def test_get_applicable_procedures_respects_limit(db_conn):
    """get_applicable_procedures returns at most limit results."""
    for i in range(6):
        save_procedure(
            db_conn, TEST_WORKSPACE_ID,
            name=f"procedure-{i}",
            trigger_context=f"Context for deploy procedure {i}",
            steps_md=f"Step 1: action {i}",
            confidence=0.5 + i * 0.05,
        )
    results = get_applicable_procedures(db_conn, "deploy procedure", TEST_WORKSPACE_ID, limit=3)
    assert len(results) <= 3


def test_list_procedures_returns_active_only(db_conn):
    """list_procedures with default status='active' excludes draft and deprecated."""
    save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="active-proc",
        trigger_context="Active procedure context",
        steps_md="1. Do it.",
        status="active",
    )
    save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="draft-proc",
        trigger_context="Draft procedure context",
        steps_md="1. Draft step.",
        status="draft",
    )
    save_procedure(
        db_conn, TEST_WORKSPACE_ID,
        name="deprecated-proc",
        trigger_context="Deprecated procedure context",
        steps_md="1. Old step.",
        status="deprecated",
    )
    results = list_procedures(db_conn, TEST_WORKSPACE_ID, status="active")
    statuses = {r["status"] for r in results}
    assert statuses == {"active"}
    names = [r["name"] for r in results]
    assert "active-proc" in names
    assert "draft-proc" not in names
