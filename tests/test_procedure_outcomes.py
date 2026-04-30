"""Sprint 6: procedure outcome tracking + confidence evolution."""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_procedure(conn, name: str = "test_proc", confidence: float = 0.5) -> int:
    from craft_memory_mcp.db import save_procedure
    proc_id = save_procedure(conn, TEST_WORKSPACE_ID, name, "trigger ctx", "## Steps\n1. do it", confidence=confidence)
    return proc_id


# ---------------------------------------------------------------------------
# Migration 011 — procedure_outcomes table
# ---------------------------------------------------------------------------

class TestProcedureOutcomesMigration:
    def test_table_exists(self, db_conn):
        """Migration 011 creates procedure_outcomes table."""
        row = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='procedure_outcomes'"
        ).fetchone()
        assert row is not None, "procedure_outcomes table should exist after migration 011"

    def test_table_columns(self, db_conn):
        """procedure_outcomes has required columns."""
        cols = {r[1] for r in db_conn.execute("PRAGMA table_info(procedure_outcomes)")}
        for col in ("id", "procedure_id", "workspace_id", "outcome", "notes", "created_at_epoch"):
            assert col in cols, f"Column '{col}' missing from procedure_outcomes"


# ---------------------------------------------------------------------------
# record_procedure_outcome
# ---------------------------------------------------------------------------

class TestRecordProcedureOutcome:
    def test_success_outcome(self, db_conn):
        """record_procedure_outcome stores a success outcome."""
        from craft_memory_mcp.db import record_procedure_outcome
        proc_id = _add_procedure(db_conn, "proc_success")
        outcome_id = record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "success")
        assert outcome_id is not None and outcome_id > 0

    def test_failure_outcome(self, db_conn):
        """record_procedure_outcome stores a failure outcome."""
        from craft_memory_mcp.db import record_procedure_outcome
        proc_id = _add_procedure(db_conn, "proc_fail")
        outcome_id = record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "failure", notes="step 2 broke")
        assert outcome_id is not None

    def test_partial_outcome(self, db_conn):
        """record_procedure_outcome accepts 'partial' outcome."""
        from craft_memory_mcp.db import record_procedure_outcome
        proc_id = _add_procedure(db_conn, "proc_partial")
        outcome_id = record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "partial")
        assert outcome_id is not None

    def test_invalid_outcome_raises(self, db_conn):
        """record_procedure_outcome raises ValueError for unknown outcome."""
        from craft_memory_mcp.db import record_procedure_outcome
        proc_id = _add_procedure(db_conn, "proc_invalid")
        with pytest.raises((ValueError, Exception)):
            record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "unknown_outcome")

    def test_notes_stored(self, db_conn):
        """Notes are stored and retrievable."""
        from craft_memory_mcp.db import record_procedure_outcome, get_procedure_outcomes
        proc_id = _add_procedure(db_conn, "proc_notes")
        record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "success", notes="worked great")
        outcomes = get_procedure_outcomes(db_conn, proc_id, TEST_WORKSPACE_ID)
        assert outcomes[0]["notes"] == "worked great"


# ---------------------------------------------------------------------------
# get_procedure_outcomes
# ---------------------------------------------------------------------------

class TestGetProcedureOutcomes:
    def test_returns_outcomes_for_procedure(self, db_conn):
        """get_procedure_outcomes returns all outcomes for a procedure."""
        from craft_memory_mcp.db import record_procedure_outcome, get_procedure_outcomes
        proc_id = _add_procedure(db_conn, "proc_multi")
        record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "success")
        record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "failure")
        outcomes = get_procedure_outcomes(db_conn, proc_id, TEST_WORKSPACE_ID)
        assert len(outcomes) == 2
        outcome_types = {o["outcome"] for o in outcomes}
        assert outcome_types == {"success", "failure"}

    def test_empty_when_no_outcomes(self, db_conn):
        """get_procedure_outcomes returns [] when no outcomes recorded."""
        from craft_memory_mcp.db import get_procedure_outcomes
        proc_id = _add_procedure(db_conn, "proc_empty")
        outcomes = get_procedure_outcomes(db_conn, proc_id, TEST_WORKSPACE_ID)
        assert outcomes == []


# ---------------------------------------------------------------------------
# update_procedure_confidence
# ---------------------------------------------------------------------------

class TestUpdateProcedureConfidence:
    def test_confidence_increases_with_successes(self, db_conn):
        """After recording successes, update_procedure_confidence raises confidence."""
        from craft_memory_mcp.db import record_procedure_outcome, update_procedure_confidence
        proc_id = _add_procedure(db_conn, "proc_rising", confidence=0.5)
        record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "success")
        record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "success")
        record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "success")
        update_procedure_confidence(db_conn, proc_id, TEST_WORKSPACE_ID)
        row = db_conn.execute("SELECT confidence FROM procedures WHERE id = ?", (proc_id,)).fetchone()
        assert row["confidence"] > 0.5

    def test_confidence_decreases_with_failures(self, db_conn):
        """After recording failures, update_procedure_confidence lowers confidence."""
        from craft_memory_mcp.db import record_procedure_outcome, update_procedure_confidence
        proc_id = _add_procedure(db_conn, "proc_falling", confidence=0.8)
        record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "failure")
        record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "failure")
        update_procedure_confidence(db_conn, proc_id, TEST_WORKSPACE_ID)
        row = db_conn.execute("SELECT confidence FROM procedures WHERE id = ?", (proc_id,)).fetchone()
        assert row["confidence"] < 0.8

    def test_confidence_stays_bounded(self, db_conn):
        """Confidence stays in [0, 1] regardless of outcome extremes."""
        from craft_memory_mcp.db import record_procedure_outcome, update_procedure_confidence
        proc_id = _add_procedure(db_conn, "proc_bounded", confidence=0.95)
        for _ in range(10):
            record_procedure_outcome(db_conn, proc_id, TEST_WORKSPACE_ID, "success")
        update_procedure_confidence(db_conn, proc_id, TEST_WORKSPACE_ID)
        row = db_conn.execute("SELECT confidence FROM procedures WHERE id = ?", (proc_id,)).fetchone()
        assert 0.0 <= row["confidence"] <= 1.0
