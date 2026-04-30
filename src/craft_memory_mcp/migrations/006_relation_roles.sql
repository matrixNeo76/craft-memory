-- Migration 006: Hyperedge Roles + Weights
-- Adds semantic role and importance weight to memory_relations edges.
-- Inspired by HyperMem (EverOS) hyperedge role classification.
ALTER TABLE memory_relations ADD COLUMN role TEXT DEFAULT 'context'
    CHECK(role IN ('core', 'context', 'detail', 'temporal', 'causal'));
ALTER TABLE memory_relations ADD COLUMN weight REAL DEFAULT 1.0
    CHECK(weight BETWEEN 0 AND 1);
CREATE INDEX IF NOT EXISTS idx_memory_relations_role
    ON memory_relations(workspace_id, role);
