-- Migration 003: Add tags column to memories
-- Tags stored as JSON array, e.g. '["auth","deploy","fastmcp"]'
-- Enables search_by_tag tool and tag-based grouping of memories.

ALTER TABLE memories ADD COLUMN tags TEXT DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(tags);
