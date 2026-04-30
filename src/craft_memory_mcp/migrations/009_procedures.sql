-- Migration 009: Procedural Memory
-- Creates procedures table (reusable step-by-step patterns) and FTS5 index.
-- UNIQUE(workspace_id, name) enables safe upsert semantics in save_procedure().
CREATE TABLE IF NOT EXISTS procedures (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id        TEXT    NOT NULL,
  name                TEXT    NOT NULL,
  trigger_context     TEXT    NOT NULL,
  steps_md            TEXT    NOT NULL,
  confidence          REAL    DEFAULT 0.5 CHECK(confidence BETWEEN 0 AND 1),
  source_memory_ids   TEXT    DEFAULT NULL,
  last_validated_at   INTEGER DEFAULT NULL,
  created_at_epoch    INTEGER NOT NULL,
  updated_at_epoch    INTEGER NOT NULL,
  status              TEXT    DEFAULT 'active'
                              CHECK(status IN ('active', 'draft', 'deprecated')),
  UNIQUE(workspace_id, name)
);
CREATE INDEX IF NOT EXISTS idx_procedures_workspace
    ON procedures(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_procedures_confidence
    ON procedures(workspace_id, confidence DESC);
CREATE VIRTUAL TABLE IF NOT EXISTS procedures_fts USING fts5(
  name, trigger_context, steps_md,
  tokenize='porter ascii'
);
