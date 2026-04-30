-- Migration 007: is_manual flag on memory_relations
-- Distinguishes manual edges (is_manual=1, never pruned) from auto-link edges (is_manual=0, prunable).
-- Default 1 = safe: existing edges without the flag are treated as manual, never pruned accidentally.
ALTER TABLE memory_relations ADD COLUMN is_manual INTEGER DEFAULT 1 CHECK(is_manual IN (0, 1));
CREATE INDEX IF NOT EXISTS idx_memory_relations_is_manual ON memory_relations(workspace_id, is_manual);
