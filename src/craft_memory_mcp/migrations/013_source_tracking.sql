-- Migration 013: Add source tracking columns (source_url, source_title)
-- Allows memories to track their provenance from external sources.

ALTER TABLE memories ADD COLUMN source_url TEXT DEFAULT NULL;

ALTER TABLE memories ADD COLUMN source_title TEXT DEFAULT NULL;

-- Index for source-based queries (find all memories from a source)
CREATE INDEX idx_memories_source_url ON memories(workspace_id, source_url);
