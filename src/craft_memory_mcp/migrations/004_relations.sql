-- Migration 004: confidence_type on facts + memory_relations table
-- Pattern from graphify: EXTRACTED | INFERRED | AMBIGUOUS confidence labels
-- + directed edges between memories (knowledge graph layer)

-- Add confidence_type to facts
-- extracted: fact observed directly in source/conversation
-- inferred: fact deduced by the agent (may need verification)
-- ambiguous: uncertain, flagged for review
ALTER TABLE facts ADD COLUMN confidence_type TEXT DEFAULT 'extracted'
    CHECK(confidence_type IN ('extracted', 'inferred', 'ambiguous'));

-- memory_relations: directed edges between memories
-- Enables BFS/DFS retrieval, god_facts, memory_diff, surprising connections
CREATE TABLE IF NOT EXISTS memory_relations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id        INTEGER NOT NULL,
    target_id        INTEGER NOT NULL,
    relation         TEXT    NOT NULL
                             CHECK(relation IN (
                               'caused_by', 'contradicts', 'extends',
                               'implements', 'supersedes', 'semantically_similar_to'
                             )),
    confidence_type  TEXT    NOT NULL DEFAULT 'inferred'
                             CHECK(confidence_type IN ('extracted', 'inferred', 'ambiguous')),
    confidence_score REAL    DEFAULT 1.0 CHECK(confidence_score BETWEEN 0 AND 1),
    workspace_id     TEXT    NOT NULL,
    created_at_epoch INTEGER NOT NULL,
    UNIQUE(source_id, target_id, relation),
    FOREIGN KEY(source_id) REFERENCES memories(id) ON DELETE CASCADE,
    FOREIGN KEY(target_id) REFERENCES memories(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_relations_source    ON memory_relations(source_id);
CREATE INDEX IF NOT EXISTS idx_relations_target    ON memory_relations(target_id);
CREATE INDEX IF NOT EXISTS idx_relations_workspace ON memory_relations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_relations_type      ON memory_relations(confidence_type);
CREATE INDEX IF NOT EXISTS idx_relations_relation  ON memory_relations(relation);
