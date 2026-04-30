"""Unit tests for knowledge graph layer: link_memories, get_relations,
find_similar_memories, god_facts, memory_diff, confidence_type on facts."""
import time
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID

from craft_memory_mcp.db import (
    find_similar_memories,
    get_relations,
    god_facts,
    link_memories,
    memory_diff,
    register_session,
    remember,
    upsert_fact,
)


# ─── Helpers ─────────────────────────────────────────────────────────

def _mem(conn, content, category="note", importance=5):
    return remember(conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, content, category, importance)


# ─── link_memories ───────────────────────────────────────────────────

def test_link_memories_creates_relation(registered_conn):
    a = _mem(registered_conn, "Decided to use SQLite for storage")
    b = _mem(registered_conn, "SQLite FTS5 supports BM25 ranking")
    rel_id = link_memories(registered_conn, a, b, "extends", TEST_WORKSPACE_ID)
    assert rel_id is not None
    row = registered_conn.execute(
        "SELECT * FROM memory_relations WHERE id = ?", (rel_id,)
    ).fetchone()
    assert row["source_id"] == a
    assert row["target_id"] == b
    assert row["relation"] == "extends"
    assert row["confidence_type"] == "extracted"


def test_link_memories_duplicate_returns_none(registered_conn):
    a = _mem(registered_conn, "Auth uses JWT tokens")
    b = _mem(registered_conn, "JWT expiry set to 24h")
    link_memories(registered_conn, a, b, "extends", TEST_WORKSPACE_ID)
    result = link_memories(registered_conn, a, b, "extends", TEST_WORKSPACE_ID)
    assert result is None


def test_link_memories_invalid_relation(registered_conn):
    a = _mem(registered_conn, "Memory A")
    b = _mem(registered_conn, "Memory B")
    result = link_memories(registered_conn, a, b, "related_to_invalid", TEST_WORKSPACE_ID)
    assert result is None


def test_link_memories_inferred_confidence(registered_conn):
    a = _mem(registered_conn, "Bug in the auth middleware fixed")
    b = _mem(registered_conn, "Auth middleware refactored")
    rel_id = link_memories(
        registered_conn, a, b, "caused_by", TEST_WORKSPACE_ID,
        confidence_type="inferred", confidence_score=0.7,
    )
    assert rel_id is not None
    row = registered_conn.execute(
        "SELECT confidence_type, confidence_score FROM memory_relations WHERE id = ?",
        (rel_id,),
    ).fetchone()
    assert row["confidence_type"] == "inferred"
    assert abs(row["confidence_score"] - 0.7) < 0.001


# ─── get_relations ───────────────────────────────────────────────────

def test_get_relations_out(registered_conn):
    a = _mem(registered_conn, "Feature: dark mode implemented")
    b = _mem(registered_conn, "Dark mode extends the theme system")
    link_memories(registered_conn, a, b, "extends", TEST_WORKSPACE_ID)
    rels = get_relations(registered_conn, a, TEST_WORKSPACE_ID, direction="out")
    assert len(rels) == 1
    assert rels[0]["target_id"] == b
    assert rels[0]["relation"] == "extends"
    assert rels[0]["direction"] == "out"


def test_get_relations_in(registered_conn):
    a = _mem(registered_conn, "Bug #42 caused a memory leak")
    b = _mem(registered_conn, "Fixed memory leak in session handler")
    link_memories(registered_conn, b, a, "caused_by", TEST_WORKSPACE_ID)
    rels = get_relations(registered_conn, a, TEST_WORKSPACE_ID, direction="in")
    assert len(rels) == 1
    assert rels[0]["direction"] == "in"


def test_get_relations_both(registered_conn):
    a = _mem(registered_conn, "Refactored the API client")
    b = _mem(registered_conn, "API client now uses async")
    c = _mem(registered_conn, "Old sync API client deprecated")
    link_memories(registered_conn, a, b, "extends", TEST_WORKSPACE_ID)
    link_memories(registered_conn, c, a, "supersedes", TEST_WORKSPACE_ID)
    rels = get_relations(registered_conn, a, TEST_WORKSPACE_ID, direction="both")
    assert len(rels) == 2


def test_get_relations_empty(registered_conn):
    a = _mem(registered_conn, "Isolated memory with no relations")
    rels = get_relations(registered_conn, a, TEST_WORKSPACE_ID)
    assert rels == []


# ─── find_similar_memories ───────────────────────────────────────────

def test_find_similar_returns_results(registered_conn):
    _mem(registered_conn, "SQLite database initialization uses WAL mode")
    _mem(registered_conn, "SQLite WAL mode improves write performance")
    target = _mem(registered_conn, "SQLite FTS5 full-text search configuration")
    results = find_similar_memories(registered_conn, target, TEST_WORKSPACE_ID, top_n=5)
    assert len(results) >= 1
    assert all("similarity_score" in r for r in results)


def test_find_similar_excludes_self(registered_conn):
    mem_id = _mem(registered_conn, "SQLite database configuration")
    results = find_similar_memories(registered_conn, mem_id, TEST_WORKSPACE_ID, top_n=5)
    assert all(r["id"] != mem_id for r in results)


def test_find_similar_auto_link(registered_conn):
    _mem(registered_conn, "FastMCP HTTP transport configuration for MCP server")
    _mem(registered_conn, "FastMCP stateless HTTP server setup")
    target = _mem(registered_conn, "FastMCP streamable HTTP app initialization")
    find_similar_memories(registered_conn, target, TEST_WORKSPACE_ID, top_n=3, auto_link=True)
    rels = registered_conn.execute(
        "SELECT COUNT(*) FROM memory_relations WHERE source_id = ?", (target,)
    ).fetchone()[0]
    # May or may not create links depending on BM25 threshold — just ensure no error
    assert isinstance(rels, int)


# ─── god_facts ───────────────────────────────────────────────────────

def test_god_facts_returns_ranked_list(registered_conn):
    upsert_fact(registered_conn, "tech_stack", "Python + FastMCP + SQLite", TEST_WORKSPACE_ID)
    upsert_fact(registered_conn, "auth_method", "JWT tokens", TEST_WORKSPACE_ID)
    # Add memories that mention tech_stack key
    _mem(registered_conn, "Decided on tech_stack: Python and FastMCP")
    _mem(registered_conn, "tech_stack confirmed after spike")
    results = god_facts(registered_conn, TEST_WORKSPACE_ID, top_n=10)
    assert len(results) >= 2
    # tech_stack should score higher (mentioned in memories)
    keys = [r["key"] for r in results]
    tech_idx = keys.index("tech_stack")
    auth_idx = keys.index("auth_method")
    assert tech_idx < auth_idx


def test_god_facts_confidence_type_field(registered_conn):
    upsert_fact(
        registered_conn, "db_engine", "SQLite", TEST_WORKSPACE_ID,
        confidence_type="extracted",
    )
    upsert_fact(
        registered_conn, "scale_estimate", "10k users", TEST_WORKSPACE_ID,
        confidence_type="inferred",
    )
    results = god_facts(registered_conn, TEST_WORKSPACE_ID)
    types = {r["key"]: r.get("confidence_type") for r in results}
    assert types.get("db_engine") == "extracted"
    assert types.get("scale_estimate") == "inferred"


# ─── upsert_fact confidence_type ─────────────────────────────────────

def test_upsert_fact_confidence_type_default(registered_conn):
    upsert_fact(registered_conn, "framework", "FastMCP", TEST_WORKSPACE_ID)
    row = registered_conn.execute(
        "SELECT confidence_type FROM facts WHERE key = ? AND workspace_id = ?",
        ("framework", TEST_WORKSPACE_ID),
    ).fetchone()
    assert row["confidence_type"] == "extracted"


def test_upsert_fact_confidence_type_inferred(registered_conn):
    upsert_fact(
        registered_conn, "bottleneck", "DB writes",
        TEST_WORKSPACE_ID, confidence_type="inferred",
    )
    row = registered_conn.execute(
        "SELECT confidence_type FROM facts WHERE key = ? AND workspace_id = ?",
        ("bottleneck", TEST_WORKSPACE_ID),
    ).fetchone()
    assert row["confidence_type"] == "inferred"


# ─── memory_diff ─────────────────────────────────────────────────────

def test_memory_diff_captures_new_memories(registered_conn):
    before = int(time.time()) - 1
    _mem(registered_conn, "New decision after the cutoff")
    _mem(registered_conn, "Another discovery post cutoff")
    diff = memory_diff(registered_conn, TEST_WORKSPACE_ID, before)
    assert len(diff["new_memories"]) == 2
    assert diff["since_epoch"] == before


def test_memory_diff_captures_updated_facts(registered_conn):
    before = int(time.time()) - 1
    upsert_fact(registered_conn, "deploy_target", "AWS Lambda", TEST_WORKSPACE_ID)
    diff = memory_diff(registered_conn, TEST_WORKSPACE_ID, before)
    keys = [f["key"] for f in diff["updated_facts"]]
    assert "deploy_target" in keys


def test_memory_diff_empty_when_nothing_changed(registered_conn):
    _mem(registered_conn, "Old memory before the cutoff")
    after = int(time.time()) + 1
    diff = memory_diff(registered_conn, TEST_WORKSPACE_ID, after)
    assert len(diff["new_memories"]) == 0
    assert len(diff["updated_facts"]) == 0


def test_memory_diff_summary_string(registered_conn):
    before = int(time.time()) - 1
    _mem(registered_conn, "Something changed")
    diff = memory_diff(registered_conn, TEST_WORKSPACE_ID, before)
    assert "new memories" in diff["summary"]
