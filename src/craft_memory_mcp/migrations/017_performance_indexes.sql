-- Sprint 10: Performance Indexes
-- Aggiunge indici per query comuni su memorie e compressed flag.

CREATE INDEX IF NOT EXISTS idx_memories_compressed ON memories(compressed);
CREATE INDEX IF NOT EXISTS idx_memories_lifecycle ON memories(lifecycle_status);
