"""Sprint 8.2: consolidate_memories — combine candidates into a procedure and invalidate originals."""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID


def _add_memory(conn, content: str, importance: int = 3) -> int:
    from craft_memory_mcp.db import remember
    mid = remember(conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, content, "note", importance, "workspace")
    assert mid is not None, f"Failed to save memory: {content}"
    return mid


class TestConsolidateMemoriesDryRun:
    def test_dry_run_returns_preview(self, registered_conn):
        """consolidate_memories with confirm=False returns preview dict."""
        from craft_memory_mcp.db import consolidate_memories
        m1 = _add_memory(registered_conn, "old note about auth", importance=2)
        m2 = _add_memory(registered_conn, "old note about tokens", importance=2)
        result = consolidate_memories(
            registered_conn, [m1, m2], TEST_WORKSPACE_ID,
            procedure_name="auth_procedure",
            trigger_context="when dealing with auth",
            steps_md="## Steps\n1. check auth\n2. validate tokens",
            confirm=False,
        )
        assert result["dry_run"] is True
        assert result["candidate_count"] == 2
        assert "auth_procedure" in result["procedure_name"]

    def test_dry_run_does_not_modify_db(self, registered_conn):
        """dry_run leaves memories active and does not create procedure."""
        from craft_memory_mcp.db import consolidate_memories
        m1 = _add_memory(registered_conn, "note for dry run")
        consolidate_memories(
            registered_conn, [m1], TEST_WORKSPACE_ID,
            procedure_name="dry_proc",
            trigger_context="ctx",
            steps_md="## Steps\n1. x",
            confirm=False,
        )
        row = registered_conn.execute(
            "SELECT lifecycle_status FROM memories WHERE id = ?", (m1,)
        ).fetchone()
        assert row["lifecycle_status"] == "active"
        proc = registered_conn.execute(
            "SELECT id FROM procedures WHERE name = ? AND workspace_id = ?",
            ("dry_proc", TEST_WORKSPACE_ID),
        ).fetchone()
        assert proc is None


class TestConsolidateMemoriesExecute:
    def test_creates_procedure(self, registered_conn):
        """consolidate_memories with confirm=True creates a procedure."""
        from craft_memory_mcp.db import consolidate_memories
        m1 = _add_memory(registered_conn, "step A for new proc")
        result = consolidate_memories(
            registered_conn, [m1], TEST_WORKSPACE_ID,
            procedure_name="new_proc",
            trigger_context="when X happens",
            steps_md="## Steps\n1. do A",
            confirm=True,
        )
        assert result["dry_run"] is False
        assert result["procedure_id"] is not None
        assert result["procedure_id"] > 0

    def test_invalidates_all_candidates(self, registered_conn):
        """All candidate memories are marked invalidated after confirm=True."""
        from craft_memory_mcp.db import consolidate_memories
        m1 = _add_memory(registered_conn, "candidate memory alpha")
        m2 = _add_memory(registered_conn, "candidate memory beta")
        consolidate_memories(
            registered_conn, [m1, m2], TEST_WORKSPACE_ID,
            procedure_name="alpha_beta_proc",
            trigger_context="ctx",
            steps_md="## Steps\n1. alpha\n2. beta",
            confirm=True,
        )
        for mid in (m1, m2):
            row = registered_conn.execute(
                "SELECT lifecycle_status FROM memories WHERE id = ?", (mid,)
            ).fetchone()
            assert row["lifecycle_status"] == "invalidated", f"Memory {mid} should be invalidated"

    def test_returns_invalidated_count(self, registered_conn):
        """Result dict contains correct invalidated_count."""
        from craft_memory_mcp.db import consolidate_memories
        m1 = _add_memory(registered_conn, "count test a")
        m2 = _add_memory(registered_conn, "count test b")
        m3 = _add_memory(registered_conn, "count test c")
        result = consolidate_memories(
            registered_conn, [m1, m2, m3], TEST_WORKSPACE_ID,
            procedure_name="count_proc",
            trigger_context="ctx",
            steps_md="## Steps\n1. x",
            confirm=True,
        )
        assert result["invalidated_count"] == 3

    def test_empty_candidate_ids_dry_run(self, registered_conn):
        """Empty candidate_ids with dry_run returns candidate_count=0."""
        from craft_memory_mcp.db import consolidate_memories
        result = consolidate_memories(
            registered_conn, [], TEST_WORKSPACE_ID,
            procedure_name="empty_proc",
            trigger_context="ctx",
            steps_md="## Steps\n1. x",
            confirm=False,
        )
        assert result["candidate_count"] == 0

    def test_nonexistent_ids_skipped(self, registered_conn):
        """Non-existent memory IDs in candidate_ids are silently skipped."""
        from craft_memory_mcp.db import consolidate_memories
        m1 = _add_memory(registered_conn, "real memory for consolidation")
        result = consolidate_memories(
            registered_conn, [m1, 99999], TEST_WORKSPACE_ID,
            procedure_name="partial_proc",
            trigger_context="ctx",
            steps_md="## Steps\n1. x",
            confirm=True,
        )
        assert result["invalidated_count"] == 1


class TestConsolidateMemoriesTool:
    def test_tool_dry_run_json(self, server_module, registered_conn):
        """consolidate_memories tool returns JSON with dry_run=true."""
        import json
        from craft_memory_mcp.db import remember
        mid = remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "tool dry run content", "note", 3, "workspace")
        server_module._conn = registered_conn
        result = server_module.consolidate_memories(
            candidate_ids_json=f"[{mid}]",
            procedure_name="tool_dry_proc",
            trigger_context="ctx",
            steps_md="## Steps\n1. x",
            confirm=False,
        )
        parsed = json.loads(result)
        assert parsed["dry_run"] is True

    def test_tool_confirms_execution(self, server_module, registered_conn):
        """consolidate_memories tool with confirm=True returns procedure_id."""
        import json
        from craft_memory_mcp.db import remember
        mid = remember(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, "tool confirm content", "note", 3, "workspace")
        server_module._conn = registered_conn
        result = server_module.consolidate_memories(
            candidate_ids_json=f"[{mid}]",
            procedure_name="tool_confirm_proc",
            trigger_context="ctx",
            steps_md="## Steps\n1. x",
            confirm=True,
        )
        parsed = json.loads(result)
        assert parsed["procedure_id"] is not None
        assert parsed["invalidated_count"] == 1
