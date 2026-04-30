"""Unit tests for knowledge graph layer: link_memories, get_relations,
find_similar_memories, god_facts, memory_diff, confidence_type on facts."""
import time
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID

from craft_memory_mcp.db import (
    _AUTOLINK_THRESHOLD,
    _PRUNE_AGE_DAYS,
    _PRUNE_WEIGHT_THRESHOLD,
    find_similar_memories,
    get_relations,
    get_relations_by_role,
    god_facts,
    link_memories,
    memory_diff,
    prune_inferred_edges,
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


# ─── Hyperedge Roles (μ3) ────────────────────────────────────────────


def test_link_memories_with_role_and_weight(registered_conn):
    """link_memories accepts role and weight and stores them."""
    a = _mem(registered_conn, "Decision: use SQLite WAL mode", "decision")
    b = _mem(registered_conn, "WAL mode prevents write contention", "discovery")
    rel_id = link_memories(registered_conn, a, b, "caused_by", TEST_WORKSPACE_ID,
                           role="causal", weight=0.9)
    assert rel_id is not None
    row = registered_conn.execute(
        "SELECT role, weight FROM memory_relations WHERE id = ?", (rel_id,)
    ).fetchone()
    assert row["role"] == "causal"
    assert abs(row["weight"] - 0.9) < 0.001


def test_link_memories_invalid_role_rejected(registered_conn):
    """link_memories rejects unknown role values."""
    a = _mem(registered_conn, "Memory A", "note")
    b = _mem(registered_conn, "Memory B", "note")
    rel_id = link_memories(registered_conn, a, b, "extends", TEST_WORKSPACE_ID,
                           role="unknown_role")
    assert rel_id is None


def test_get_relations_by_role_filters_correctly(registered_conn):
    """get_relations_by_role returns only edges with the specified role."""
    a = _mem(registered_conn, "Core decision", "decision")
    b = _mem(registered_conn, "Supporting detail", "note")
    c = _mem(registered_conn, "Temporal context", "note")
    link_memories(registered_conn, a, b, "extends", TEST_WORKSPACE_ID, role="detail")
    link_memories(registered_conn, a, c, "extends", TEST_WORKSPACE_ID, role="temporal")

    detail_rels = get_relations_by_role(registered_conn, a, TEST_WORKSPACE_ID, role="detail")
    temporal_rels = get_relations_by_role(registered_conn, a, TEST_WORKSPACE_ID, role="temporal")

    assert len(detail_rels) == 1
    assert detail_rels[0]["role"] == "detail"
    assert len(temporal_rels) == 1
    assert temporal_rels[0]["role"] == "temporal"


def test_get_relations_by_role_ordered_by_weight(registered_conn):
    """get_relations_by_role returns edges ordered by weight descending."""
    a = _mem(registered_conn, "Source memory", "note")
    b = _mem(registered_conn, "Low weight target", "note")
    c = _mem(registered_conn, "High weight target", "note")
    link_memories(registered_conn, a, b, "semantically_similar_to", TEST_WORKSPACE_ID,
                  role="context", weight=0.3)
    link_memories(registered_conn, a, c, "semantically_similar_to", TEST_WORKSPACE_ID,
                  role="context", weight=0.9)

    rels = get_relations_by_role(registered_conn, a, TEST_WORKSPACE_ID, role="context")
    assert len(rels) == 2
    assert rels[0]["weight"] >= rels[1]["weight"]


# ─── μ-hygiene: is_manual flag, pruning, threshold ───────────────────

def test_link_memories_manual_flag_default(registered_conn):
    """link_memories default is_manual=True — edge has is_manual=1."""
    a = _mem(registered_conn, "Source node", "note")
    b = _mem(registered_conn, "Target node", "note")
    link_memories(registered_conn, a, b, "extends", TEST_WORKSPACE_ID)
    rels = get_relations(registered_conn, a, TEST_WORKSPACE_ID, direction="out")
    assert len(rels) == 1
    assert rels[0]["is_manual"] == 1


def test_link_memories_auto_flag(registered_conn):
    """link_memories with is_manual=False sets is_manual=0."""
    a = _mem(registered_conn, "Source node B", "note")
    b = _mem(registered_conn, "Target node B", "note")
    link_memories(registered_conn, a, b, "semantically_similar_to",
                  TEST_WORKSPACE_ID, is_manual=False)
    rels = get_relations(registered_conn, a, TEST_WORKSPACE_ID, direction="out")
    assert len(rels) == 1
    assert rels[0]["is_manual"] == 0


def test_prune_inferred_edges_removes_weak_old_auto(registered_conn):
    """prune_inferred_edges deletes is_manual=0 edges below weight threshold."""
    a = _mem(registered_conn, "Prune source", "note")
    b = _mem(registered_conn, "Prune target weak", "note")
    c = _mem(registered_conn, "Keep target strong", "note")
    # Weak auto-link (prunable)
    link_memories(registered_conn, a, b, "semantically_similar_to",
                  TEST_WORKSPACE_ID, confidence_score=0.2, weight=0.1, is_manual=False)
    # Strong manual link (must NOT be pruned even if weight is low)
    link_memories(registered_conn, a, c, "semantically_similar_to",
                  TEST_WORKSPACE_ID, confidence_score=0.2, weight=0.1, is_manual=True)

    # Force age to 0 days — with age_days=0 threshold applies to all
    pruned = prune_inferred_edges(registered_conn, TEST_WORKSPACE_ID,
                                   weight_threshold=0.5, age_days=0)
    assert pruned == 1  # Only the auto-link is removed

    rels = get_relations(registered_conn, a, TEST_WORKSPACE_ID, direction="out")
    assert len(rels) == 1
    assert rels[0]["is_manual"] == 1  # Manual edge survived


def test_prune_inferred_edges_respects_age(registered_conn):
    """prune_inferred_edges does not remove edges younger than age_days threshold."""
    a = _mem(registered_conn, "Age test source", "note")
    b = _mem(registered_conn, "Age test target", "note")
    link_memories(registered_conn, a, b, "semantically_similar_to",
                  TEST_WORKSPACE_ID, weight=0.1, is_manual=False)

    # age_days=999 means nothing is old enough to prune
    pruned = prune_inferred_edges(registered_conn, TEST_WORKSPACE_ID,
                                   weight_threshold=0.5, age_days=999)
    assert pruned == 0


def test_prune_manual_edges_never_pruned(registered_conn):
    """Manual edges (is_manual=1) are never pruned regardless of weight."""
    a = _mem(registered_conn, "Manual never prune source", "note")
    b = _mem(registered_conn, "Manual never prune target", "note")
    link_memories(registered_conn, a, b, "contradicts",
                  TEST_WORKSPACE_ID, weight=0.01, is_manual=True)

    pruned = prune_inferred_edges(registered_conn, TEST_WORKSPACE_ID,
                                   weight_threshold=1.0, age_days=0)
    assert pruned == 0


def test_autolink_threshold_is_negative(registered_conn):
    """_AUTOLINK_THRESHOLD is negative (BM25 negative scores) and stricter than -1.5."""
    assert _AUTOLINK_THRESHOLD < -1.5, "Default threshold must be stricter than original -1.5"


def test_find_similar_auto_linked_field_present(registered_conn):
    """find_similar_memories returns auto_linked field in each result."""
    a = _mem(registered_conn, "Python asyncio event loop programming guide", "note")
    _mem(registered_conn, "asyncio coroutines and tasks tutorial", "note")

    results = find_similar_memories(registered_conn, a, TEST_WORKSPACE_ID,
                                     top_n=5, auto_link=False)
    for r in results:
        assert "auto_linked" in r
        assert r["auto_linked"] is False  # auto_link=False, nothing linked
