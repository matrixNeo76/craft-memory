"""Sprint 2 — Temporal Invalidation + Review Flag tests.

12 tests covering:
- 2A: invalidate_memory, get_memory_history, search/recent lifecycle filtering
- 2B: flag_for_review, list_needs_review, approve_memory, maintenance count
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID
from craft_memory_mcp.db import (
    approve_memory,
    daily_maintenance,
    flag_for_review,
    get_memory_history,
    get_recent_memory,
    invalidate_memory,
    list_needs_review,
    remember,
    search_memory,
)


def _mem(conn, content, category="note", importance=5):
    return remember(conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, content, category, importance)


# ── Microfase 2A: Temporal Invalidation ──────────────────────────────


def test_invalidate_memory_sets_status(registered_conn):
    """invalidate_memory marks lifecycle_status='invalidated'."""
    mid = _mem(registered_conn, "Deprecated approach")
    result = invalidate_memory(registered_conn, mid, "No longer valid", TEST_WORKSPACE_ID)
    assert result is True
    row = registered_conn.execute(
        "SELECT lifecycle_status FROM memories WHERE id = ?", (mid,)
    ).fetchone()
    assert row["lifecycle_status"] == "invalidated"


def test_invalidate_memory_sets_valid_to(registered_conn):
    """invalidate_memory writes a non-null valid_to epoch."""
    mid = _mem(registered_conn, "Old design decision")
    invalidate_memory(registered_conn, mid, "Replaced by ADR-006", TEST_WORKSPACE_ID)
    row = registered_conn.execute(
        "SELECT valid_to FROM memories WHERE id = ?", (mid,)
    ).fetchone()
    assert row["valid_to"] is not None
    assert isinstance(row["valid_to"], int)


def test_invalidate_memory_unknown_id_returns_false(registered_conn):
    """invalidate_memory returns False when memory_id doesn't exist."""
    result = invalidate_memory(registered_conn, 99999, "ghost", TEST_WORKSPACE_ID)
    assert result is False


def test_search_excludes_invalidated_by_default(registered_conn):
    """search_memory hides invalidated memories unless include_inactive=True."""
    _mem(registered_conn, "active memory about authentication")
    mid = _mem(registered_conn, "invalidated memory about authentication")
    invalidate_memory(registered_conn, mid, "old", TEST_WORKSPACE_ID)

    results = search_memory(registered_conn, "authentication", TEST_WORKSPACE_ID)
    ids = [r["id"] for r in results]
    assert mid not in ids


def test_get_recent_excludes_invalidated(registered_conn):
    """get_recent_memory excludes invalidated memories by default."""
    _mem(registered_conn, "active note")
    mid = _mem(registered_conn, "invalidated note")
    invalidate_memory(registered_conn, mid, "stale", TEST_WORKSPACE_ID)

    results = get_recent_memory(registered_conn, TEST_WORKSPACE_ID)
    ids = [r["id"] for r in results]
    assert mid not in ids


def test_get_memory_history_single(registered_conn):
    """get_memory_history on a standalone memory returns a list with one entry."""
    mid = _mem(registered_conn, "Standalone memory")
    history = get_memory_history(registered_conn, mid, TEST_WORKSPACE_ID)
    assert len(history) == 1
    assert history[0]["id"] == mid


def test_get_memory_history_chain(registered_conn):
    """get_memory_history follows the superseded_by chain."""
    a = _mem(registered_conn, "Decision v1")
    b = _mem(registered_conn, "Decision v2")
    # Mark A as superseded by B
    invalidate_memory(registered_conn, a, "Updated", TEST_WORKSPACE_ID, replaced_by_id=b)
    history = get_memory_history(registered_conn, a, TEST_WORKSPACE_ID)
    ids = [h["id"] for h in history]
    assert a in ids
    assert b in ids


# ── Microfase 2B: Review Flag ─────────────────────────────────────────


def test_flag_for_review_sets_status(registered_conn):
    """flag_for_review marks lifecycle_status='needs_review'."""
    mid = _mem(registered_conn, "Possibly wrong assumption")
    result = flag_for_review(registered_conn, mid, "Needs verification", TEST_WORKSPACE_ID)
    assert result is True
    row = registered_conn.execute(
        "SELECT lifecycle_status FROM memories WHERE id = ?", (mid,)
    ).fetchone()
    assert row["lifecycle_status"] == "needs_review"


def test_list_needs_review_returns_flagged(registered_conn):
    """list_needs_review returns memories with lifecycle_status='needs_review'."""
    mid1 = _mem(registered_conn, "First suspect memory")
    mid2 = _mem(registered_conn, "Second suspect memory")
    _mem(registered_conn, "Healthy memory")
    flag_for_review(registered_conn, mid1, "reason A", TEST_WORKSPACE_ID)
    flag_for_review(registered_conn, mid2, "reason B", TEST_WORKSPACE_ID)

    results = list_needs_review(registered_conn, TEST_WORKSPACE_ID)
    ids = [r["id"] for r in results]
    assert mid1 in ids
    assert mid2 in ids


def test_approve_memory_restores_active(registered_conn):
    """approve_memory sets lifecycle_status back to 'active'."""
    mid = _mem(registered_conn, "Under review")
    flag_for_review(registered_conn, mid, "check this", TEST_WORKSPACE_ID)
    result = approve_memory(registered_conn, mid, TEST_WORKSPACE_ID)
    assert result is True
    row = registered_conn.execute(
        "SELECT lifecycle_status FROM memories WHERE id = ?", (mid,)
    ).fetchone()
    assert row["lifecycle_status"] == "active"


def test_list_needs_review_limit(registered_conn):
    """list_needs_review respects the limit parameter."""
    for i in range(5):
        mid = _mem(registered_conn, f"Suspect memory {i}")
        flag_for_review(registered_conn, mid, "test", TEST_WORKSPACE_ID)

    results = list_needs_review(registered_conn, TEST_WORKSPACE_ID, limit=3)
    assert len(results) <= 3


def test_maintenance_includes_needs_review_count(registered_conn):
    """daily_maintenance returns needs_review count in its report."""
    mid = _mem(registered_conn, "Memory to review")
    flag_for_review(registered_conn, mid, "verify", TEST_WORKSPACE_ID)

    report = daily_maintenance(registered_conn, TEST_WORKSPACE_ID)
    assert "needs_review" in report
    assert report["needs_review"] >= 1
