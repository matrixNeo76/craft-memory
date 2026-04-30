"""Sprint 5-Close: newly exposed MCP tools — search_facts, list_procedures,
get_scope_ancestors (tool wrapper), find_consolidation_candidates."""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_fact(conn, key: str, value: str, scope: str = "workspace") -> None:
    from craft_memory_mcp.db import upsert_fact
    upsert_fact(conn, key, value, TEST_WORKSPACE_ID, scope=scope)


def _add_memory(conn, content: str, importance: int = 5) -> int:
    from craft_memory_mcp.db import remember
    return remember(conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, content, importance=importance)


def _add_procedure(conn, name: str, trigger: str = "any context", steps: str = "do it") -> None:
    from craft_memory_mcp.db import save_procedure
    save_procedure(conn, TEST_WORKSPACE_ID, name, trigger, steps, confidence=0.8)


# ---------------------------------------------------------------------------
# search_facts
# ---------------------------------------------------------------------------

class TestSearchFacts:
    def test_finds_by_key(self, db_conn):
        """search_facts finds a fact matching the key keyword."""
        _add_fact(db_conn, "python_version", "3.12")
        from craft_memory_mcp.db import search_facts
        results = search_facts(db_conn, "python", TEST_WORKSPACE_ID)
        assert len(results) == 1
        assert results[0]["key"] == "python_version"

    def test_finds_by_value(self, db_conn):
        """search_facts finds a fact matching the value keyword."""
        _add_fact(db_conn, "db_engine", "SQLite + FTS5")
        from craft_memory_mcp.db import search_facts
        results = search_facts(db_conn, "SQLite", TEST_WORKSPACE_ID)
        assert len(results) == 1
        assert results[0]["value"] == "SQLite + FTS5"

    def test_no_match_returns_empty(self, db_conn):
        """search_facts returns [] when nothing matches."""
        _add_fact(db_conn, "framework", "FastMCP")
        from craft_memory_mcp.db import search_facts
        results = search_facts(db_conn, "nonexistent_xyz", TEST_WORKSPACE_ID)
        assert results == []

    def test_scope_filter(self, db_conn):
        """search_facts respects scope filter."""
        _add_fact(db_conn, "api_key", "abc123", scope="session")
        _add_fact(db_conn, "api_key_global", "xyz", scope="workspace")
        from craft_memory_mcp.db import search_facts
        results = search_facts(db_conn, "api", TEST_WORKSPACE_ID, scope="session")
        assert len(results) == 1
        assert results[0]["scope"] == "session"

    def test_workspace_isolation(self, db_conn):
        """search_facts does not return facts from other workspaces."""
        _add_fact(db_conn, "my_key", "my_value")
        from craft_memory_mcp.db import search_facts
        results = search_facts(db_conn, "my_key", "other-workspace")
        assert results == []


# ---------------------------------------------------------------------------
# list_procedures
# ---------------------------------------------------------------------------

class TestListProcedures:
    def test_returns_active_by_default(self, db_conn):
        """list_procedures returns active procedures by default."""
        _add_procedure(db_conn, "deploy_backend")
        _add_procedure(db_conn, "run_tests")
        from craft_memory_mcp.db import list_procedures
        results = list_procedures(db_conn, TEST_WORKSPACE_ID)
        names = {r["name"] for r in results}
        assert "deploy_backend" in names
        assert "run_tests" in names

    def test_status_filter(self, db_conn):
        """list_procedures filters by status correctly."""
        from craft_memory_mcp.db import save_procedure, list_procedures
        save_procedure(db_conn, TEST_WORKSPACE_ID, "draft_proc", "ctx", "steps", status="draft")
        active = list_procedures(db_conn, TEST_WORKSPACE_ID, status="active")
        draft = list_procedures(db_conn, TEST_WORKSPACE_ID, status="draft")
        assert all(r["status"] == "active" for r in active)
        assert len(draft) == 1
        assert draft[0]["name"] == "draft_proc"

    def test_workspace_isolation(self, db_conn):
        """list_procedures does not return other workspaces' procedures."""
        _add_procedure(db_conn, "my_proc")
        from craft_memory_mcp.db import list_procedures
        results = list_procedures(db_conn, "other-workspace")
        assert results == []


# ---------------------------------------------------------------------------
# find_consolidation_candidates
# ---------------------------------------------------------------------------

class TestConsolidationCandidates:
    def test_returns_old_low_importance(self, registered_conn):
        """find_consolidation_candidates returns old memories below threshold."""
        import time
        from craft_memory_mcp.db import find_consolidation_candidates
        # Add a low-importance memory and fake its creation time to be old
        mid = _add_memory(registered_conn, "old low importance note", importance=1)
        # Backdate the memory by 40 days
        cutoff = int(time.time()) - (40 * 86400)
        registered_conn.execute(
            "UPDATE memories SET created_at_epoch = ? WHERE id = ?", (cutoff, mid)
        )
        registered_conn.commit()
        results = find_consolidation_candidates(registered_conn, TEST_WORKSPACE_ID, importance_threshold=3.0, age_days=30)
        assert len(results) >= 1

    def test_skips_core_memories(self, registered_conn):
        """find_consolidation_candidates never returns is_core=1 memories."""
        import time
        from craft_memory_mcp.db import find_consolidation_candidates, promote_memory_to_core
        mid = _add_memory(registered_conn, "important core note", importance=1)
        cutoff = int(time.time()) - (40 * 86400)
        registered_conn.execute(
            "UPDATE memories SET created_at_epoch = ? WHERE id = ?", (cutoff, mid)
        )
        promote_memory_to_core(registered_conn, mid, TEST_WORKSPACE_ID)
        registered_conn.commit()
        results = find_consolidation_candidates(registered_conn, TEST_WORKSPACE_ID, importance_threshold=10.0)
        ids = [r["id"] for r in results]
        assert mid not in ids

    def test_recent_memories_excluded(self, registered_conn):
        """find_consolidation_candidates excludes recently created memories."""
        from craft_memory_mcp.db import find_consolidation_candidates
        _add_memory(registered_conn, "recent low importance", importance=1)
        # Default age_days=30 — recent memory should not appear
        results = find_consolidation_candidates(registered_conn, TEST_WORKSPACE_ID, age_days=30)
        assert results == []
