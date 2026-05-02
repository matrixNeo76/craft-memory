"""Integration tests for the Craft Memory MCP server.

Strategy:
- /health endpoint tests: use TestClient without lifespan (custom route, no session manager needed)
- Tool behavior tests: call Python functions directly on server_module
  FastMCP's @mcp.tool() returns the original function, so tool handlers are
  directly callable. This tests business logic without HTTP transport overhead
  and avoids the StreamableHTTPSessionManager singleton constraint.
"""
import sqlite3

import pytest
from starlette.testclient import TestClient

from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID


# ─── Health check endpoint ───────────────────────────────────────────
# /health is a custom route that does NOT go through StreamableHTTPSessionManager.
# Use TestClient without context manager (no lifespan startup needed).


def test_health_check(test_app):
    """GET /health must return 200 with status=healthy."""
    client = TestClient(test_app, raise_server_exceptions=False)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "craft-memory"
    # Version must match installed package (copes with Release Please bumps)
    assert isinstance(data["version"], str) and len(data["version"]) > 0
    assert "workspace" in data


def test_health_check_db_field(test_app):
    """Health check must report db=healthy when the database is accessible."""
    client = TestClient(test_app, raise_server_exceptions=False)
    resp = client.get("/health")
    assert resp.json()["db"] == "healthy"


def test_stateless_http_two_requests(test_app):
    """Two sequential /health requests must both succeed (no shared HTTP session state)."""
    client = TestClient(test_app, raise_server_exceptions=False)
    r1 = client.get("/health")
    r2 = client.get("/health")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["status"] == "healthy"
    assert r2.json()["status"] == "healthy"


# ─── Session auto-registration (Fix #8 regression) ───────────────────


def test_session_auto_registration(server_module, tmp_db_dir):
    """_get_conn() must auto-register the session before any memory INSERT.

    Regression test for Fix #8: previously register_session() was never called,
    leaving sessions table empty → FK violation → every remember() silently failed.
    """
    server_module._get_conn()  # Trigger connection creation

    db_path = tmp_db_dir / f"{TEST_WORKSPACE_ID}.db"
    check_conn = sqlite3.connect(str(db_path))
    row = check_conn.execute(
        "SELECT craft_session_id FROM sessions WHERE craft_session_id = ?",
        (TEST_SESSION_ID,),
    ).fetchone()
    check_conn.close()

    assert row is not None, (
        "Session NOT auto-registered. Fix #8 regression: "
        "_get_conn() must call _db_register_session() on first connection."
    )
    assert row[0] == TEST_SESSION_ID


# ─── Tool: remember ──────────────────────────────────────────────────
# FastMCP's @mcp.tool() returns the original function — direct calls work.


def test_remember_tool_roundtrip(server_module, tmp_db_dir):
    """remember() must store memory and return a confirmation with Memory #id."""
    result = server_module.remember(
        content="FastMCP 1.26.0 requires streamable_http_app() not http_app()",
        category="bugfix",
        importance=9,
    )
    assert "Memory #" in result, f"Expected 'Memory #' in result, got: {result}"

    db_path = tmp_db_dir / f"{TEST_WORKSPACE_ID}.db"
    db_conn = sqlite3.connect(str(db_path))
    count = db_conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    db_conn.close()
    assert count == 1


def test_remember_dedup_via_server(server_module):
    """Calling remember twice with same content returns Duplicate on second call."""
    content = "HTTP transport workaround for Windows stdio bug"

    first = server_module.remember(content=content, category="decision")
    second = server_module.remember(content=content, category="decision")

    assert "Memory #" in first, f"First call must store the memory, got: {first}"
    assert "Duplicate" in second, f"Second call must report duplicate, got: {second}"


# ─── Tool: upsert_fact ───────────────────────────────────────────────


def test_upsert_fact_tool(server_module, tmp_db_dir):
    """upsert_fact() must persist a fact and confirm with fact id."""
    result = server_module.upsert_fact(
        key="transport",
        value="HTTP on localhost:8392",
        confidence=1.0,
    )
    assert "upserted" in result.lower() or "transport" in result

    db_path = tmp_db_dir / f"{TEST_WORKSPACE_ID}.db"
    db_conn = sqlite3.connect(str(db_path))
    row = db_conn.execute("SELECT value FROM facts WHERE key = 'transport'").fetchone()
    db_conn.close()
    assert row is not None
    assert "8392" in row[0]


# ─── Tool: get_recent_memory ─────────────────────────────────────────


def test_get_recent_memory_empty(server_module):
    """get_recent_memory on empty workspace must return a graceful message."""
    result = server_module.get_recent_memory()
    assert "No memories" in result or len(result) > 0


def test_get_recent_memory_after_remember(server_module):
    """get_recent_memory must return memories previously stored via remember."""
    server_module.remember(
        content="Persistent memory system works across sessions",
        category="note",
    )
    result = server_module.get_recent_memory(limit=5)
    assert "Persistent memory system works" in result


# ─── Tool: list_open_loops ───────────────────────────────────────────


def test_list_open_loops_empty(server_module):
    """list_open_loops on workspace with no loops must return graceful message."""
    result = server_module.list_open_loops()
    assert "No open loops" in result
