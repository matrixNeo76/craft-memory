-- Migration 012: session quality scoring for SessionDB
-- Adds quality_score and quality_notes to session_summaries.
-- Enables get_high_quality_sessions and export_session_traces (Sprint 9).

ALTER TABLE session_summaries ADD COLUMN quality_score REAL CHECK(quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0));
ALTER TABLE session_summaries ADD COLUMN quality_notes TEXT DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_summaries_quality ON session_summaries(workspace_id, quality_score DESC)
    WHERE quality_score IS NOT NULL;
