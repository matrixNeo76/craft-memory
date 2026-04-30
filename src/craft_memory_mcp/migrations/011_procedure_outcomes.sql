-- Sprint 6: procedure outcome tracking for confidence evolution
-- Outcome types: success | partial | failure

CREATE TABLE IF NOT EXISTS procedure_outcomes (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  procedure_id     INTEGER NOT NULL REFERENCES procedures(id) ON DELETE CASCADE,
  workspace_id     TEXT NOT NULL,
  outcome          TEXT NOT NULL CHECK(outcome IN ('success', 'partial', 'failure')),
  notes            TEXT DEFAULT NULL,
  created_at_epoch INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_outcomes_procedure ON procedure_outcomes(procedure_id, workspace_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_workspace  ON procedure_outcomes(workspace_id, created_at_epoch DESC);
