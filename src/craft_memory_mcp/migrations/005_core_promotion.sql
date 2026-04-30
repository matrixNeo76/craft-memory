-- Migration 005: Core Memory Promotion
-- Adds is_core flag (immune to importance decay) and consolidated_from
-- for tracking memory merges during SchedulerTick consolidation.
ALTER TABLE memories ADD COLUMN is_core INTEGER DEFAULT 0
    CHECK(is_core IN (0, 1));
ALTER TABLE memories ADD COLUMN consolidated_from TEXT DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_is_core
    ON memories(workspace_id, is_core) WHERE is_core = 1;
