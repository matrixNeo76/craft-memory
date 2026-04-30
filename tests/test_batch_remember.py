"""Sprint 7: batch_remember — save N memories in one call."""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID


# ---------------------------------------------------------------------------
# batch_remember db function
# ---------------------------------------------------------------------------

class TestBatchRemember:
    def test_basic_saves_three(self, registered_conn):
        """batch_remember saves 3 entries and returns 3 non-None IDs."""
        from craft_memory_mcp.db import batch_remember
        entries = [
            {"content": "batch entry one"},
            {"content": "batch entry two"},
            {"content": "batch entry three"},
        ]
        ids = batch_remember(registered_conn, entries, TEST_SESSION_ID, TEST_WORKSPACE_ID)
        assert len(ids) == 3
        assert all(i is not None and i > 0 for i in ids)

    def test_empty_list_returns_empty(self, registered_conn):
        """batch_remember with empty list returns []."""
        from craft_memory_mcp.db import batch_remember
        ids = batch_remember(registered_conn, [], TEST_SESSION_ID, TEST_WORKSPACE_ID)
        assert ids == []

    def test_preserves_category_and_importance(self, registered_conn):
        """Each entry's category and importance are stored correctly."""
        from craft_memory_mcp.db import batch_remember
        entries = [
            {"content": "a decision", "category": "decision", "importance": 9},
            {"content": "a bugfix", "category": "bugfix", "importance": 7},
        ]
        ids = batch_remember(registered_conn, entries, TEST_SESSION_ID, TEST_WORKSPACE_ID)
        row0 = dict(registered_conn.execute(
            "SELECT category, importance FROM memories WHERE id = ?", (ids[0],)
        ).fetchone())
        row1 = dict(registered_conn.execute(
            "SELECT category, importance FROM memories WHERE id = ?", (ids[1],)
        ).fetchone())
        assert row0["category"] == "decision" and row0["importance"] == 9
        assert row1["category"] == "bugfix" and row1["importance"] == 7

    def test_duplicate_returns_none_for_that_entry(self, registered_conn):
        """Duplicate content returns None for that entry, others still saved."""
        from craft_memory_mcp.db import batch_remember, remember
        # Pre-save first entry
        remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "dupe content")
        entries = [
            {"content": "dupe content"},       # duplicate → None
            {"content": "unique content xyz"},  # new → ID
        ]
        ids = batch_remember(registered_conn, entries, TEST_SESSION_ID, TEST_WORKSPACE_ID)
        assert len(ids) == 2
        assert ids[0] is None
        assert ids[1] is not None

    def test_large_batch(self, registered_conn):
        """Batch of 15 memories all saved correctly."""
        from craft_memory_mcp.db import batch_remember
        entries = [{"content": f"large batch entry {i}"} for i in range(15)]
        ids = batch_remember(registered_conn, entries, TEST_SESSION_ID, TEST_WORKSPACE_ID)
        non_none = [i for i in ids if i is not None]
        assert len(non_none) == 15

    def test_scope_and_tags_stored(self, registered_conn):
        """scope and tags from entry dict are persisted."""
        from craft_memory_mcp.db import batch_remember
        entries = [{"content": "tagged memory", "scope": "session", "tags": ["sprint7", "test"]}]
        ids = batch_remember(registered_conn, entries, TEST_SESSION_ID, TEST_WORKSPACE_ID)
        row = dict(registered_conn.execute(
            "SELECT scope, tags FROM memories WHERE id = ?", (ids[0],)
        ).fetchone())
        assert row["scope"] == "session"
        import json
        assert "sprint7" in json.loads(row["tags"])


# ---------------------------------------------------------------------------
# batch_remember MCP tool (server)
# ---------------------------------------------------------------------------

class TestBatchRememberTool:
    def test_tool_accepts_json_list(self, server_module):
        """batch_remember MCP tool parses JSON input and returns summary."""
        import json
        entries_json = json.dumps([
            {"content": "tool batch one"},
            {"content": "tool batch two"},
        ])
        result = server_module.batch_remember(entries_json)
        assert "2" in result or "saved" in result.lower()

    def test_tool_invalid_json_returns_error(self, server_module):
        """batch_remember tool returns an error string for invalid JSON."""
        result = server_module.batch_remember("this is not json at all")
        assert "error" in result.lower() or "invalid" in result.lower()
