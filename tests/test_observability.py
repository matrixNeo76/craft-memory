"""Sprint 1 - Observability and Handoff tests.

Tests for:
- memory_stats: aggregate counts across categories, edges, loops
- explain_retrieval: per-memory diagnostic info
- generate_handoff: structured session-end pack
"""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID
from craft_memory_mcp.db import (
    create_open_loop,
    generate_handoff,
    get_memory_stats,
    link_memories,
    remember,
    upsert_fact,
    explain_retrieval,
)


def _mem(conn, content, category="note", importance=5):
    return remember(
        conn, TEST_SESSION_ID, TEST_WORKSPACE_ID,
        content, category, importance, "workspace", TEST_SESSION_ID,
    )


def test_memory_stats_empty_workspace(db_conn):
    """Stats on empty workspace return zero counts without errors."""
    stats = get_memory_stats(db_conn, TEST_WORKSPACE_ID)
    assert stats["total_memories"] == 0
    assert stats["core_memories"] == 0
    assert stats["open_loops"] == 0
    assert stats["total_edges"] == 0
    assert stats["by_category"] == {}


def test_memory_stats_counts_by_category(registered_conn):
    """Stats correctly counts memories per category."""
    _mem(registered_conn, "Decision A", "decision", importance=8)
    _mem(registered_conn, "Discovery B", "discovery", importance=6)
    _mem(registered_conn, "Note C", "note", importance=3)
    _mem(registered_conn, "Decision D", "decision", importance=7)

    stats = get_memory_stats(registered_conn, TEST_WORKSPACE_ID)
    assert stats["total_memories"] == 4
    assert stats["by_category"]["decision"] == 2
    assert stats["by_category"]["discovery"] == 1
    assert stats["by_category"]["note"] == 1


def test_memory_stats_open_loops_count(registered_conn):
    """Stats includes count of active open loops."""
    create_open_loop(
        registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID,
        "Loop 1", priority="high",
    )
    create_open_loop(
        registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID,
        "Loop 2", priority="medium",
    )
    stats = get_memory_stats(registered_conn, TEST_WORKSPACE_ID)
    assert stats["open_loops"] == 2


def test_memory_stats_edge_counts(registered_conn):
    """Stats counts total, manual and inferred edges separately."""
    a = _mem(registered_conn, "Node A", "note")
    b = _mem(registered_conn, "Node B", "note")
    c = _mem(registered_conn, "Node C", "note")
    link_memories(registered_conn, a, b, "extends", TEST_WORKSPACE_ID, is_manual=True)
    link_memories(registered_conn, a, c, "semantically_similar_to", TEST_WORKSPACE_ID, is_manual=False)

    stats = get_memory_stats(registered_conn, TEST_WORKSPACE_ID)
    assert stats["total_edges"] == 2
    assert stats["manual_edges"] == 1
    assert stats["inferred_edges"] == 1


def test_memory_stats_avg_importance(registered_conn):
    """Stats returns average importance across memories."""
    _mem(registered_conn, "Low importance memory", importance=2)
    _mem(registered_conn, "Mid importance memory", importance=6)
    _mem(registered_conn, "High importance memory", importance=10)
    stats = get_memory_stats(registered_conn, TEST_WORKSPACE_ID)
    assert abs(stats["avg_importance"] - 6.0) < 0.01


def test_memory_stats_required_keys(registered_conn):
    """Stats dict always contains all required keys."""
    _mem(registered_conn, "Some memory", "note")
    stats = get_memory_stats(registered_conn, TEST_WORKSPACE_ID)
    required = {
        "total_memories", "by_category", "core_memories",
        "open_loops", "total_edges", "manual_edges", "inferred_edges", "avg_importance",
    }
    assert required.issubset(stats.keys())


def test_explain_retrieval_returns_memory_info(registered_conn):
    """explain_retrieval returns id, content, category and importance."""
    mid = _mem(registered_conn, "Explainable memory content", "decision", importance=8)
    info = explain_retrieval(registered_conn, mid, TEST_WORKSPACE_ID)
    assert info["id"] == mid
    assert "Explainable memory content" in info["content"]
    assert info["category"] == "decision"
    assert info["importance"] == 8


def test_explain_retrieval_includes_relations(registered_conn):
    """explain_retrieval includes the local edge graph."""
    a = _mem(registered_conn, "Explain source node", "note")
    b = _mem(registered_conn, "Explain target node", "note")
    link_memories(registered_conn, a, b, "extends", TEST_WORKSPACE_ID)
    info = explain_retrieval(registered_conn, a, TEST_WORKSPACE_ID)
    assert "relations" in info
    assert len(info["relations"]) == 1
    assert info["relations"][0]["relation"] == "extends"


def test_explain_retrieval_unknown_id_returns_none(db_conn):
    """explain_retrieval returns None for non-existent memory ID."""
    result = explain_retrieval(db_conn, 99999, TEST_WORKSPACE_ID)
    assert result is None


def test_generate_handoff_structure(registered_conn):
    """generate_handoff returns all required top-level keys."""
    pack = generate_handoff(registered_conn, TEST_WORKSPACE_ID)
    for key in (
        "generated_at", "scope", "recent_decisions",
        "active_open_loops", "recent_facts", "memory_stats_snapshot",
    ):
        assert key in pack, f"Missing key: {key}"


def test_generate_handoff_includes_decisions(registered_conn):
    """generate_handoff recent_decisions contains decision-category memories."""
    _mem(registered_conn, "Decided to use SQLite as primary store", "decision", importance=9)
    pack = generate_handoff(registered_conn, TEST_WORKSPACE_ID)
    contents = [d["content"] for d in pack["recent_decisions"]]
    assert any("SQLite" in c for c in contents)


def test_generate_handoff_includes_open_loops(registered_conn):
    """generate_handoff active_open_loops contains open loops."""
    create_open_loop(
        registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID,
        "Finish Sprint 1 implementation", priority="high",
    )
    pack = generate_handoff(registered_conn, TEST_WORKSPACE_ID)
    titles = [lp["title"] for lp in pack["active_open_loops"]]
    assert "Finish Sprint 1 implementation" in titles


def test_generate_handoff_includes_facts(registered_conn):
    """generate_handoff recent_facts contains workspace facts."""
    upsert_fact(
        registered_conn, "tech_stack", "FastMCP+SQLite",
        TEST_WORKSPACE_ID, scope="workspace",
    )
    pack = generate_handoff(registered_conn, TEST_WORKSPACE_ID)
    fact_keys = [f["key"] for f in pack["recent_facts"]]
    assert "tech_stack" in fact_keys


def test_generate_handoff_scope_field(registered_conn):
    """generate_handoff includes the scope passed as argument."""
    pack = generate_handoff(registered_conn, TEST_WORKSPACE_ID, scope="project")
    assert pack["scope"] == "project"
