-- Migration 008: Temporal Invalidation + Review Flag
-- Adds lifecycle tracking columns to memories table.
-- All columns have safe DEFAULT values — zero breaking changes for existing rows.
ALTER TABLE memories ADD COLUMN valid_from INTEGER DEFAULT NULL;
ALTER TABLE memories ADD COLUMN valid_to INTEGER DEFAULT NULL;
ALTER TABLE memories ADD COLUMN superseded_by INTEGER DEFAULT NULL
    REFERENCES memories(id);
ALTER TABLE memories ADD COLUMN lifecycle_status TEXT DEFAULT 'active'
    CHECK(lifecycle_status IN ('active', 'superseded', 'invalidated', 'needs_review'));
CREATE INDEX IF NOT EXISTS idx_memories_lifecycle
    ON memories(workspace_id, lifecycle_status);
