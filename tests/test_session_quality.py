"""Sprint 8.3 + 9: session quality scoring, SessionDB — rate_session, get_high_quality_sessions, export_session_traces."""
import json
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID


def _add_summary(conn, summary: str = "test summary") -> int:
    from craft_memory_mcp.db import save_summary, register_session
    register_session(conn, TEST_SESSION_ID, TEST_WORKSPACE_ID)
    return save_summary(conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, summary=summary)


# ─── Migration 012 ────────────────────────────────────────────────────────────

class TestMigration012:
    def test_quality_score_column_exists(self, db_conn):
        """Migration 012 adds quality_score column to session_summaries."""
        cols = {r[1] for r in db_conn.execute("PRAGMA table_info(session_summaries)")}
        assert "quality_score" in cols

    def test_quality_notes_column_exists(self, db_conn):
        """Migration 012 adds quality_notes column to session_summaries."""
        cols = {r[1] for r in db_conn.execute("PRAGMA table_info(session_summaries)")}
        assert "quality_notes" in cols

    def test_quality_score_defaults_null(self, db_conn):
        """New summaries have quality_score=NULL by default."""
        summary_id = _add_summary(db_conn, "fresh summary")
        row = db_conn.execute(
            "SELECT quality_score FROM session_summaries WHERE id = ?", (summary_id,)
        ).fetchone()
        assert row["quality_score"] is None


# ─── rate_session ─────────────────────────────────────────────────────────────

class TestRateSession:
    def test_rate_session_sets_score(self, db_conn):
        """rate_session updates quality_score for the given summary."""
        from craft_memory_mcp.db import rate_session
        sid = _add_summary(db_conn)
        result = rate_session(db_conn, sid, TEST_WORKSPACE_ID, 0.85)
        assert result is True
        row = db_conn.execute(
            "SELECT quality_score FROM session_summaries WHERE id = ?", (sid,)
        ).fetchone()
        assert abs(row["quality_score"] - 0.85) < 0.001

    def test_rate_session_with_notes(self, db_conn):
        """rate_session stores quality_notes."""
        from craft_memory_mcp.db import rate_session
        sid = _add_summary(db_conn)
        rate_session(db_conn, sid, TEST_WORKSPACE_ID, 0.9, notes="excellent session")
        row = db_conn.execute(
            "SELECT quality_notes FROM session_summaries WHERE id = ?", (sid,)
        ).fetchone()
        assert row["quality_notes"] == "excellent session"

    def test_rate_session_wrong_workspace_returns_false(self, db_conn):
        """rate_session returns False when summary belongs to different workspace."""
        from craft_memory_mcp.db import rate_session
        sid = _add_summary(db_conn)
        result = rate_session(db_conn, sid, "wrong_workspace", 0.5)
        assert result is False

    def test_rate_session_nonexistent_returns_false(self, db_conn):
        """rate_session returns False for non-existent summary ID."""
        from craft_memory_mcp.db import rate_session
        result = rate_session(db_conn, 99999, TEST_WORKSPACE_ID, 0.5)
        assert result is False

    def test_rate_session_score_upper_bound(self, db_conn):
        """rate_session accepts 1.0 as maximum valid score."""
        from craft_memory_mcp.db import rate_session
        sid = _add_summary(db_conn)
        result = rate_session(db_conn, sid, TEST_WORKSPACE_ID, 1.0)
        assert result is True

    def test_rate_session_score_lower_bound(self, db_conn):
        """rate_session accepts 0.0 as minimum valid score."""
        from craft_memory_mcp.db import rate_session
        sid = _add_summary(db_conn)
        result = rate_session(db_conn, sid, TEST_WORKSPACE_ID, 0.0)
        assert result is True


# ─── get_high_quality_sessions ────────────────────────────────────────────────

class TestGetHighQualitySessions:
    def test_returns_sessions_above_threshold(self, db_conn):
        """get_high_quality_sessions returns only sessions with score >= min_score."""
        from craft_memory_mcp.db import rate_session, get_high_quality_sessions
        sid_high = _add_summary(db_conn, "high quality session")
        sid_low = _add_summary(db_conn, "low quality session")
        rate_session(db_conn, sid_high, TEST_WORKSPACE_ID, 0.9)
        rate_session(db_conn, sid_low, TEST_WORKSPACE_ID, 0.3)
        results = get_high_quality_sessions(db_conn, TEST_WORKSPACE_ID, min_score=0.7)
        ids = [r["id"] for r in results]
        assert sid_high in ids
        assert sid_low not in ids

    def test_empty_when_none_qualify(self, db_conn):
        """Returns [] when no session meets min_score threshold."""
        from craft_memory_mcp.db import rate_session, get_high_quality_sessions
        sid = _add_summary(db_conn)
        rate_session(db_conn, sid, TEST_WORKSPACE_ID, 0.4)
        results = get_high_quality_sessions(db_conn, TEST_WORKSPACE_ID, min_score=0.8)
        assert results == []

    def test_unrated_sessions_excluded(self, db_conn):
        """Sessions without quality_score (NULL) are excluded."""
        from craft_memory_mcp.db import get_high_quality_sessions
        _add_summary(db_conn, "unrated")
        results = get_high_quality_sessions(db_conn, TEST_WORKSPACE_ID, min_score=0.0)
        assert results == []

    def test_ordered_by_score_desc(self, db_conn):
        """Results are ordered by quality_score descending."""
        from craft_memory_mcp.db import rate_session, get_high_quality_sessions
        sid_a = _add_summary(db_conn, "session A")
        sid_b = _add_summary(db_conn, "session B")
        rate_session(db_conn, sid_a, TEST_WORKSPACE_ID, 0.7)
        rate_session(db_conn, sid_b, TEST_WORKSPACE_ID, 0.95)
        results = get_high_quality_sessions(db_conn, TEST_WORKSPACE_ID, min_score=0.5)
        scores = [r["quality_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_workspace_isolation(self, db_conn):
        """Sessions from other workspaces are not returned."""
        from craft_memory_mcp.db import save_summary, register_session, rate_session, get_high_quality_sessions
        register_session(db_conn, "other_session", "other_ws")
        other_sid = save_summary(db_conn, "other_session", "other_ws", summary="other ws session")
        rate_session(db_conn, other_sid, "other_ws", 0.99)
        results = get_high_quality_sessions(db_conn, TEST_WORKSPACE_ID, min_score=0.5)
        assert all(r["id"] != other_sid for r in results)


# ─── export_session_traces ────────────────────────────────────────────────────

class TestExportSessionTraces:
    def test_returns_jsonl_string(self, db_conn):
        """export_session_traces returns a JSONL string (one JSON object per line)."""
        from craft_memory_mcp.db import rate_session, export_session_traces
        sid = _add_summary(db_conn, "trace session")
        rate_session(db_conn, sid, TEST_WORKSPACE_ID, 0.8)
        output = export_session_traces(db_conn, TEST_WORKSPACE_ID)
        assert isinstance(output, str)
        lines = [l for l in output.strip().split("\n") if l]
        assert len(lines) >= 1
        for line in lines:
            parsed = json.loads(line)
            assert "id" in parsed

    def test_includes_quality_score(self, db_conn):
        """Each JSONL line includes quality_score."""
        from craft_memory_mcp.db import rate_session, export_session_traces
        sid = _add_summary(db_conn)
        rate_session(db_conn, sid, TEST_WORKSPACE_ID, 0.75)
        output = export_session_traces(db_conn, TEST_WORKSPACE_ID)
        line = json.loads(output.strip().split("\n")[0])
        assert "quality_score" in line
        assert abs(line["quality_score"] - 0.75) < 0.001

    def test_min_score_filter(self, db_conn):
        """min_score filters out sessions below threshold."""
        from craft_memory_mcp.db import rate_session, export_session_traces
        sid_high = _add_summary(db_conn, "high quality")
        sid_low = _add_summary(db_conn, "low quality")
        rate_session(db_conn, sid_high, TEST_WORKSPACE_ID, 0.9)
        rate_session(db_conn, sid_low, TEST_WORKSPACE_ID, 0.2)
        output = export_session_traces(db_conn, TEST_WORKSPACE_ID, min_score=0.7)
        ids_in_output = [json.loads(l)["id"] for l in output.strip().split("\n") if l]
        assert sid_high in ids_in_output
        assert sid_low not in ids_in_output

    def test_empty_output_when_no_sessions(self, db_conn):
        """export_session_traces returns empty string when no sessions exist."""
        from craft_memory_mcp.db import export_session_traces
        output = export_session_traces(db_conn, TEST_WORKSPACE_ID)
        assert output.strip() == ""

    def test_limit_respected(self, db_conn):
        """limit parameter caps the number of lines in output."""
        from craft_memory_mcp.db import rate_session, export_session_traces, save_summary, register_session
        register_session(db_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID)
        for i in range(5):
            sid = save_summary(db_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, summary=f"session {i}")
            rate_session(db_conn, sid, TEST_WORKSPACE_ID, 0.8)
        output = export_session_traces(db_conn, TEST_WORKSPACE_ID, limit=3)
        lines = [l for l in output.strip().split("\n") if l]
        assert len(lines) <= 3


# ─── Tools (rate_session, get_high_quality_sessions, export_session_traces) ───

class TestRateSessionTool:
    def test_rate_session_tool_success(self, server_module, registered_conn):
        """rate_session tool returns success message."""
        from craft_memory_mcp.db import save_summary
        sid = save_summary(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, summary="tool test session")
        server_module._conn = registered_conn
        result = server_module.rate_session(summary_id=sid, score=0.8)
        assert "rated" in result.lower() or "0.8" in result

    def test_rate_session_tool_not_found(self, server_module):
        """rate_session tool returns error for non-existent ID."""
        result = server_module.rate_session(summary_id=99999, score=0.5)
        assert "not found" in result.lower() or "error" in result.lower()


class TestGetHighQualitySessionsTool:
    def test_returns_json(self, server_module, registered_conn):
        """get_high_quality_sessions tool returns valid JSON list."""
        from craft_memory_mcp.db import save_summary, rate_session
        sid = save_summary(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, summary="quality session")
        rate_session(registered_conn, sid, TEST_WORKSPACE_ID, 0.9)
        server_module._conn = registered_conn
        result = server_module.get_high_quality_sessions(min_score=0.7)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1


class TestExportSessionTracesTool:
    def test_returns_jsonl(self, server_module, registered_conn):
        """export_session_traces tool returns JSONL string."""
        from craft_memory_mcp.db import save_summary, rate_session
        sid = save_summary(registered_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, summary="trace test")
        rate_session(registered_conn, sid, TEST_WORKSPACE_ID, 0.8)
        server_module._conn = registered_conn
        result = server_module.export_session_traces()
        lines = [l for l in result.strip().split("\n") if l]
        assert len(lines) >= 1
        json.loads(lines[0])
