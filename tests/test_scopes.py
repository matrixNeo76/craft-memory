"""Sprint 5: scope hierarchy + get_memory_bundle batch retrieval."""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_memory(conn, content: str, scope: str = "workspace") -> int:
    from craft_memory_mcp.db import remember
    return remember(conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, content, scope=scope)


# ---------------------------------------------------------------------------
# 5A — scope_hierarchy table
# ---------------------------------------------------------------------------

class TestScopeHierarchyMigration:
    def test_scope_hierarchy_table_exists(self, db_conn):
        """Migration 010 creates scope_hierarchy table."""
        row = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='scope_hierarchy'"
        ).fetchone()
        assert row is not None, "scope_hierarchy table should exist after migration"

    def test_scope_hierarchy_contains_all_levels(self, db_conn):
        """Table contains all 5 canonical scopes."""
        scopes = {
            r[0] for r in db_conn.execute("SELECT scope FROM scope_hierarchy")
        }
        assert scopes == {"session", "project", "workspace", "user", "global"}

    def test_scope_hierarchy_ordering(self, db_conn):
        """session has lowest level (0), global has highest (4)."""
        rows = {
            r[0]: r[1]
            for r in db_conn.execute("SELECT scope, level FROM scope_hierarchy")
        }
        assert rows["session"] < rows["project"] < rows["workspace"] < rows["user"] < rows["global"]

    def test_scope_hierarchy_parent_chain(self, db_conn):
        """Parent pointers form a valid chain: session→project→workspace→user→global(NULL)."""
        rows = {
            r[0]: r[1]
            for r in db_conn.execute("SELECT scope, parent_scope FROM scope_hierarchy")
        }
        assert rows["session"] == "project"
        assert rows["project"] == "workspace"
        assert rows["workspace"] == "user"
        assert rows["user"] == "global"
        assert rows["global"] is None


# ---------------------------------------------------------------------------
# 5A — get_scope_ancestors helper
# ---------------------------------------------------------------------------

class TestGetScopeAncestors:
    def test_ancestors_from_session(self, db_conn):
        """session → all scopes from session to global."""
        from craft_memory_mcp.db import get_scope_ancestors
        result = get_scope_ancestors(db_conn, "session")
        assert result == ["session", "project", "workspace", "user", "global"]

    def test_ancestors_from_workspace(self, db_conn):
        """workspace → workspace, user, global only."""
        from craft_memory_mcp.db import get_scope_ancestors
        result = get_scope_ancestors(db_conn, "workspace")
        assert result == ["workspace", "user", "global"]

    def test_ancestors_from_global(self, db_conn):
        """global → just global (top of hierarchy)."""
        from craft_memory_mcp.db import get_scope_ancestors
        result = get_scope_ancestors(db_conn, "global")
        assert result == ["global"]

    def test_ancestors_unknown_scope(self, db_conn):
        """Unknown scope returns singleton list — no crash."""
        from craft_memory_mcp.db import get_scope_ancestors
        result = get_scope_ancestors(db_conn, "custom_scope")
        assert result == ["custom_scope"]


# ---------------------------------------------------------------------------
# 5B — get_memory_bundle batch retrieval
# ---------------------------------------------------------------------------

class TestGetMemoryBundle:
    def test_bundle_basic(self, registered_conn):
        """Fetch 2 IDs returns 2 complete memory dicts."""
        from craft_memory_mcp.db import get_memory_bundle
        id1 = _add_memory(registered_conn, "bundle memory one")
        id2 = _add_memory(registered_conn, "bundle memory two")
        results = get_memory_bundle(registered_conn, [id1, id2], TEST_WORKSPACE_ID)
        assert len(results) == 2
        contents = {r["content"] for r in results}
        assert "bundle memory one" in contents
        assert "bundle memory two" in contents

    def test_bundle_empty_list(self, registered_conn):
        """Empty ID list returns empty list without error."""
        from craft_memory_mcp.db import get_memory_bundle
        result = get_memory_bundle(registered_conn, [], TEST_WORKSPACE_ID)
        assert result == []

    def test_bundle_partial_invalid(self, registered_conn):
        """Invalid/missing IDs are silently skipped — no crash."""
        from craft_memory_mcp.db import get_memory_bundle
        id1 = _add_memory(registered_conn, "valid memory")
        results = get_memory_bundle(registered_conn, [id1, 99999], TEST_WORKSPACE_ID)
        assert len(results) == 1
        assert results[0]["content"] == "valid memory"

    def test_bundle_workspace_isolation(self, tmp_db_dir):
        """Cross-workspace IDs are excluded — strict workspace isolation."""
        from craft_memory_mcp.db import init_db, register_session, remember, get_memory_bundle
        # Workspace A
        db_a = init_db(tmp_db_dir / "ws_a.db")
        register_session(db_a, "sess-a", "workspace-a")
        id_a = remember(db_a, "sess-a", "workspace-a", "ws-a memory")

        # Workspace B
        db_b = init_db(tmp_db_dir / "ws_b.db")
        register_session(db_b, "sess-b", "workspace-b")
        id_b = remember(db_b, "sess-b", "workspace-b", "ws-b memory")

        # Querying workspace-a conn with ids from workspace-b's DB
        # Since each DB has its own autoincrement, id values may collide.
        # The important check is: returned content should be from workspace-a, not workspace-b.
        results_self = get_memory_bundle(db_a, [id_a], "workspace-a")
        assert len(results_self) == 1
        assert results_self[0]["content"] == "ws-a memory"

        results_cross = get_memory_bundle(db_a, [id_b], "workspace-b")
        # Cross-workspace query on the wrong DB should return empty
        assert results_cross == []

    def test_bundle_returns_full_fields(self, registered_conn):
        """Returned dicts contain id, content, scope, is_core, lifecycle_status."""
        from craft_memory_mcp.db import get_memory_bundle
        mid = _add_memory(registered_conn, "fields check memory")
        bundle = get_memory_bundle(registered_conn, [mid], TEST_WORKSPACE_ID)
        assert len(bundle) == 1
        mem = bundle[0]
        assert "id" in mem
        assert "content" in mem
        assert "scope" in mem
        assert "is_core" in mem
        assert "lifecycle_status" in mem

    def test_bundle_large_batch(self, registered_conn):
        """Batch of 10 IDs all returned correctly."""
        from craft_memory_mcp.db import get_memory_bundle
        ids = [_add_memory(registered_conn, f"batch mem {i}") for i in range(10)]
        results = get_memory_bundle(registered_conn, ids, TEST_WORKSPACE_ID)
        assert len(results) == 10
