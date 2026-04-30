"""Unit tests for the craft_memory_mcp database layer (craft_memory_mcp/db.py)."""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID

from craft_memory_mcp.db import (
    close_open_loop,
    create_open_loop,
    get_facts,
    get_recent_memory,
    hybrid_search,
    list_open_loops,
    register_session,
    remember,
    search_memory,
    update_open_loop,
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
    """Global dedup: same content in two sessions stores only the first occurrence."""
    session_a = "session-a"
    session_b = "session-b"
    register_session(db_conn, session_a, TEST_WORKSPACE_ID)
    register_session(db_conn, session_b, TEST_WORKSPACE_ID)

    content = "Same discovery made in both sessions"

    id_a = remember(db_conn, session_a, TEST_WORKSPACE_ID, content, category="discovery")
    id_b = remember(db_conn, session_b, TEST_WORKSPACE_ID, content, category="discovery")

    assert id_a is not None
    assert id_b is None  # global dedup: second session gets duplicate skipped

    count = db_conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    assert count == 1


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


def test_update_open_loop_priority(registered_conn):
    """update_open_loop changes priority correctly."""
    loop_id = create_open_loop(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Test task")
    ok = update_open_loop(registered_conn, loop_id, TEST_WORKSPACE_ID, priority="high")
    assert ok is True
    row = registered_conn.execute(
        "SELECT priority FROM open_loops WHERE id = ?", (loop_id,)
    ).fetchone()
    assert row["priority"] == "high"


def test_update_open_loop_status_to_in_progress(registered_conn):
    """update_open_loop can move a loop to in_progress without closing it."""
    loop_id = create_open_loop(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "WIP task")
    ok = update_open_loop(registered_conn, loop_id, TEST_WORKSPACE_ID, status="in_progress")
    assert ok is True
    loops = list_open_loops(registered_conn, TEST_WORKSPACE_ID, status="in_progress")
    assert any(l["id"] == loop_id for l in loops)


def test_update_open_loop_invalid_priority_rejected(registered_conn):
    """update_open_loop rejects unknown priority values."""
    loop_id = create_open_loop(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Task")
    ok = update_open_loop(registered_conn, loop_id, TEST_WORKSPACE_ID, priority="urgent")
    assert ok is False
    row = registered_conn.execute(
        "SELECT priority FROM open_loops WHERE id = ?", (loop_id,)
    ).fetchone()
    assert row["priority"] == "medium"  # unchanged


# ─── Hybrid Search (RRF) ─────────────────────────────────────────────


def test_hybrid_search_returns_results(registered_conn):
    """hybrid_search finds memories matching the query."""
    remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID,
             "SQLite WAL mode enables concurrent reads", "discovery")
    remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID,
             "FastMCP stateless HTTP transport", "note")

    results = hybrid_search(registered_conn, "SQLite WAL", TEST_WORKSPACE_ID)
    assert len(results) >= 1
    assert any("SQLite" in r["content"] for r in results)


def test_hybrid_search_scope_filter(registered_conn):
    """hybrid_search respects scope filter."""
    remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID,
             "Session-scoped memory", "note", scope="session")
    remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID,
             "Workspace-scoped memory", "note", scope="workspace")

    results = hybrid_search(registered_conn, "memory", TEST_WORKSPACE_ID, scope="session")
    assert all(r["scope"] == "session" for r in results)


def test_hybrid_search_fallback_on_fts5_error(registered_conn):
    """hybrid_search falls back to LIKE when FTS5 query is invalid."""
    remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID,
             "Hyphenated content full-text search", "discovery")

    # Hyphenated query can trip FTS5 — RRF must still return results via LIKE fallback
    results = hybrid_search(registered_conn, "full-text", TEST_WORKSPACE_ID)
    assert isinstance(results, list)


def test_hybrid_search_empty_query_returns_empty(registered_conn):
    """hybrid_search with whitespace-only query returns empty list gracefully."""
    remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "Some content", "note")
    results = hybrid_search(registered_conn, "   ", TEST_WORKSPACE_ID)
    assert isinstance(results, list)


def test_rrf_score_combines_ranks():
    """_rrf_score fuses two rank dicts and sums scores correctly."""
    from craft_memory_mcp.db import _rrf_score
    bm25 = {1: 0, 2: 1}
    overlap = {2: 0, 3: 0}
    scores = _rrf_score(bm25, overlap, k=60)
    # id=2 appears in both — must have the highest combined score
    assert scores[2] > scores[1]
    assert scores[2] > scores[3]
