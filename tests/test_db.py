"""Unit tests for the craft_memory_mcp database layer (craft_memory_mcp/db.py)."""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID

from craft_memory_mcp.db import (
    close_open_loop,
    create_open_loop,
    get_facts,
    get_recent_memory,
    list_open_loops,
    register_session,
    remember,
    search_memory,
    upsert_fact,
)


# ─── Session ─────────────────────────────────────────────────────────


def test_register_session_idempotent(db_conn):
    """Calling register_session twice with the same ID must not duplicate rows."""
    id1 = register_session(db_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID)
    id2 = register_session(db_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID)

    assert id1 == id2  # Same row ID returned both times

    rows = db_conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE craft_session_id = ?",
        (TEST_SESSION_ID,),
    ).fetchone()[0]
    assert rows == 1


def test_register_session_creates_row(db_conn):
    """register_session stores the session in the sessions table."""
    register_session(db_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID)
    row = db_conn.execute(
        "SELECT craft_session_id, workspace_id, status FROM sessions WHERE craft_session_id = ?",
        (TEST_SESSION_ID,),
    ).fetchone()
    assert row is not None
    assert row["craft_session_id"] == TEST_SESSION_ID
    assert row["workspace_id"] == TEST_WORKSPACE_ID
    assert row["status"] == "active"


# ─── Memory ──────────────────────────────────────────────────────────


def test_remember_saves_correctly(registered_conn):
    """remember() must store the memory and return a non-None row ID."""
    mem_id = remember(
        registered_conn,
        session_id=TEST_SESSION_ID,
        workspace_id=TEST_WORKSPACE_ID,
        content="Found that SQLite FTS5 is available in Python stdlib",
        category="discovery",
        importance=8,
    )
    assert mem_id is not None
    assert isinstance(mem_id, int)

    row = registered_conn.execute(
        "SELECT content, category, importance FROM memories WHERE id = ?",
        (mem_id,),
    ).fetchone()
    assert row is not None
    assert row["content"] == "Found that SQLite FTS5 is available in Python stdlib"
    assert row["category"] == "discovery"
    assert row["importance"] == 8


def test_remember_dedup_same_session(registered_conn):
    """Saving the same content twice in the same session returns None on second call.

    This tests the UNIQUE(session_id, content_hash) constraint.
    This is the test that would have caught the FK bug (Fix #8):
    if session was not registered, the first call would also return None.
    """
    content = "Architecture decision: use HTTP not stdio"

    first_id = remember(
        registered_conn,
        session_id=TEST_SESSION_ID,
        workspace_id=TEST_WORKSPACE_ID,
        content=content,
        category="decision",
    )
    second_id = remember(
        registered_conn,
        session_id=TEST_SESSION_ID,
        workspace_id=TEST_WORKSPACE_ID,
        content=content,
        category="decision",
    )

    assert first_id is not None, "First call must succeed — if None, FK constraint is failing"
    assert second_id is None, "Second call with same content must be deduped"

    count = registered_conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    assert count == 1


def test_remember_different_sessions_same_content(db_conn):
    """Two different sessions can store the same content — dedup is per session."""
    session_a = "session-a"
    session_b = "session-b"
    register_session(db_conn, session_a, TEST_WORKSPACE_ID)
    register_session(db_conn, session_b, TEST_WORKSPACE_ID)

    content = "Same discovery made in both sessions"

    id_a = remember(db_conn, session_a, TEST_WORKSPACE_ID, content, category="discovery")
    id_b = remember(db_conn, session_b, TEST_WORKSPACE_ID, content, category="discovery")

    assert id_a is not None
    assert id_b is not None
    assert id_a != id_b

    count = db_conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    assert count == 2


def test_search_memory_fts5(registered_conn):
    """FTS5 search must find memories containing the search term."""
    remember(
        registered_conn,
        session_id=TEST_SESSION_ID,
        workspace_id=TEST_WORKSPACE_ID,
        content="The database uses WAL mode for concurrent reads",
        category="discovery",
        importance=6,
    )
    remember(
        registered_conn,
        session_id=TEST_SESSION_ID,
        workspace_id=TEST_WORKSPACE_ID,
        content="Fixed authentication bug in login flow",
        category="bugfix",
        importance=7,
    )

    results = search_memory(registered_conn, "WAL mode", TEST_WORKSPACE_ID)
    assert len(results) >= 1
    assert any("WAL" in r["content"] for r in results)

    results_auth = search_memory(registered_conn, "authentication", TEST_WORKSPACE_ID)
    assert len(results_auth) >= 1
    assert any("authentication" in r["content"] for r in results_auth)


def test_get_recent_memory_returns_all(registered_conn):
    """get_recent_memory returns all stored memories up to limit."""
    remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Alpha memory", "note")
    remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Beta memory", "note")
    remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Gamma memory", "note")

    results = get_recent_memory(registered_conn, TEST_WORKSPACE_ID, limit=3)
    assert len(results) == 3

    # All three must be present (ordering by epoch may not be deterministic
    # when all inserts happen within the same second)
    contents = {r["content"] for r in results}
    assert contents == {"Alpha memory", "Beta memory", "Gamma memory"}


def test_get_recent_memory_respects_limit(registered_conn):
    """get_recent_memory returns at most limit memories."""
    for i in range(5):
        remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, f"Memory {i}", "note")

    results = get_recent_memory(registered_conn, TEST_WORKSPACE_ID, limit=3)
    assert len(results) == 3


# ─── Facts ───────────────────────────────────────────────────────────


def test_upsert_fact_idempotent(db_conn):
    """Upserting the same key twice updates the value — no duplicate rows."""
    id1 = upsert_fact(db_conn, "tech_stack", "Python + FastMCP", TEST_WORKSPACE_ID)
    id2 = upsert_fact(db_conn, "tech_stack", "Python + FastMCP + SQLite", TEST_WORKSPACE_ID)

    assert id1 == id2  # Same row ID (upsert, not insert)

    facts = get_facts(db_conn, TEST_WORKSPACE_ID)
    assert len(facts) == 1
    assert facts[0]["value"] == "Python + FastMCP + SQLite"  # Updated value


def test_upsert_fact_different_keys(db_conn):
    """Different keys in the same workspace create separate fact rows."""
    upsert_fact(db_conn, "tech_stack", "Python", TEST_WORKSPACE_ID)
    upsert_fact(db_conn, "db_url", "sqlite:///memory.db", TEST_WORKSPACE_ID)

    facts = get_facts(db_conn, TEST_WORKSPACE_ID)
    assert len(facts) == 2
    keys = {f["key"] for f in facts}
    assert keys == {"tech_stack", "db_url"}


# ─── Open Loops ──────────────────────────────────────────────────────


def test_list_open_loops_priority_order(registered_conn):
    """list_open_loops must return loops sorted critical > high > medium > low."""
    create_open_loop(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Low task", priority="low")
    create_open_loop(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Critical task", priority="critical")
    create_open_loop(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Medium task", priority="medium")
    create_open_loop(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "High task", priority="high")

    loops = list_open_loops(registered_conn, TEST_WORKSPACE_ID)
    priorities = [l["priority"] for l in loops]

    assert priorities[0] == "critical"
    assert priorities[1] == "high"
    assert priorities[2] == "medium"
    assert priorities[3] == "low"


def test_close_open_loop(registered_conn):
    """close_open_loop changes status to closed and stores resolution."""
    loop_id = create_open_loop(
        registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Implement tests", priority="high"
    )
    success = close_open_loop(registered_conn, loop_id, resolution="Tests implemented in Phase 5")

    assert success is True

    open_loops = list_open_loops(registered_conn, TEST_WORKSPACE_ID, status="open")
    assert all(l["id"] != loop_id for l in open_loops)

    row = registered_conn.execute(
        "SELECT status, resolution FROM open_loops WHERE id = ?", (loop_id,)
    ).fetchone()
    assert row["status"] == "closed"
    assert "Phase 5" in row["resolution"]


def test_close_open_loop_idempotent(registered_conn):
    """Closing an already-closed loop returns False without error."""
    loop_id = create_open_loop(
        registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Task", priority="medium"
    )
    close_open_loop(registered_conn, loop_id)
    second = close_open_loop(registered_conn, loop_id)

    assert second is False
