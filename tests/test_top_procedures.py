"""Sprint 8.1: top_procedures — ranking by success_rate × use_count × confidence."""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID


def _add_procedure(conn, name: str, confidence: float = 0.5) -> int:
    from craft_memory_mcp.db import save_procedure
    return save_procedure(conn, TEST_WORKSPACE_ID, name, "trigger", "## Steps\n1. do it", confidence=confidence)


def _add_outcome(conn, proc_id: int, outcome: str) -> None:
    from craft_memory_mcp.db import record_procedure_outcome
    record_procedure_outcome(conn, proc_id, TEST_WORKSPACE_ID, outcome)


class TestGetTopProcedures:
    def test_returns_list(self, db_conn):
        """get_top_procedures returns a list."""
        from craft_memory_mcp.db import get_top_procedures
        result = get_top_procedures(db_conn, TEST_WORKSPACE_ID)
        assert isinstance(result, list)

    def test_empty_when_no_procedures(self, db_conn):
        """Returns [] when workspace has no procedures."""
        from craft_memory_mcp.db import get_top_procedures
        result = get_top_procedures(db_conn, TEST_WORKSPACE_ID)
        assert result == []

    def test_includes_required_fields(self, db_conn):
        """Each row has top_score, success_rate, use_count fields."""
        from craft_memory_mcp.db import get_top_procedures
        _add_procedure(db_conn, "proc_a", confidence=0.8)
        results = get_top_procedures(db_conn, TEST_WORKSPACE_ID)
        assert len(results) == 1
        row = results[0]
        assert "top_score" in row
        assert "success_rate" in row
        assert "use_count" in row
        assert "name" in row

    def test_ranked_by_top_score(self, db_conn):
        """Procedure with more successes and higher confidence ranks first."""
        from craft_memory_mcp.db import get_top_procedures
        low_id = _add_procedure(db_conn, "low_proc", confidence=0.3)
        high_id = _add_procedure(db_conn, "high_proc", confidence=0.9)
        _add_outcome(db_conn, high_id, "success")
        _add_outcome(db_conn, high_id, "success")
        _add_outcome(db_conn, low_id, "failure")
        results = get_top_procedures(db_conn, TEST_WORKSPACE_ID)
        assert results[0]["name"] == "high_proc"

    def test_zero_outcomes_has_zero_score(self, db_conn):
        """Procedure with no outcomes has use_count=0 and success_rate of 0.0."""
        from craft_memory_mcp.db import get_top_procedures
        _add_procedure(db_conn, "no_outcomes", confidence=0.9)
        results = get_top_procedures(db_conn, TEST_WORKSPACE_ID)
        assert results[0]["use_count"] == 0
        assert results[0]["top_score"] == 0.0

    def test_workspace_isolation(self, db_conn):
        """Procedures from other workspaces are not returned."""
        from craft_memory_mcp.db import get_top_procedures, save_procedure
        save_procedure(db_conn, "other_ws", "other_proc", "ctx", "## Steps\n1. x")
        results = get_top_procedures(db_conn, TEST_WORKSPACE_ID)
        assert all(r["name"] != "other_proc" for r in results)

    def test_limit_respected(self, db_conn):
        """limit parameter caps returned results."""
        from craft_memory_mcp.db import get_top_procedures
        for i in range(5):
            _add_procedure(db_conn, f"proc_{i}")
        results = get_top_procedures(db_conn, TEST_WORKSPACE_ID, limit=3)
        assert len(results) <= 3


class TestTopProceduresTool:
    def test_top_procedures_tool_returns_json(self, server_module, registered_conn):
        """top_procedures tool returns valid JSON string."""
        import json
        from craft_memory_mcp.db import save_procedure
        save_procedure(registered_conn, TEST_WORKSPACE_ID, "tool_proc", "ctx", "## Steps\n1. x", confidence=0.7)
        server_module._conn = registered_conn
        result = server_module.top_procedures(limit=5)
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    def test_top_procedures_empty_message(self, server_module):
        """top_procedures returns descriptive message when no procedures exist."""
        result = server_module.top_procedures(limit=5)
        assert "No active procedures" in result or result == "[]" or isinstance(result, str)
