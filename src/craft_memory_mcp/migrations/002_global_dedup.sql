-- Migration 002: Global dedup for memories
-- Changes UNIQUE constraint from (session_id, content_hash) to (workspace_id, content_hash)
-- so that the same memory content is stored at most once per workspace, regardless of session.
-- Also marks category and scope as UNINDEXED in the FTS5 table for better bm25 accuracy.

PRAGMA foreign_keys=OFF;

-- Step 1: Dedup — keep earliest memory per (workspace_id, content_hash)
DELETE FROM memories WHERE id NOT IN (
  SELECT MIN(id) FROM memories GROUP BY workspace_id, content_hash
);

-- Step 2: Recreate memories with new UNIQUE(workspace_id, content_hash)
CREATE TABLE memories_v2 (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id          TEXT    NOT NULL,
  workspace_id        TEXT    NOT NULL,
  content             TEXT    NOT NULL,
  category            TEXT    NOT NULL
                              CHECK(category IN (
                                'decision', 'discovery', 'bugfix',
                                'feature', 'refactor', 'change', 'note'
                              )),
  importance          INTEGER DEFAULT 5 CHECK(importance BETWEEN 1 AND 10),
  scope               TEXT    DEFAULT 'workspace',
  source_session      TEXT,
  content_hash        TEXT,
  created_at          TEXT    NOT NULL,
  created_at_epoch    INTEGER NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(craft_session_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  UNIQUE(workspace_id, content_hash)
);

INSERT INTO memories_v2 SELECT * FROM memories;
DROP TABLE memories;
ALTER TABLE memories_v2 RENAME TO memories;

-- Step 3: Recreate indexes
CREATE INDEX IF NOT EXISTS idx_memories_session    ON memories(session_id);
CREATE INDEX IF NOT EXISTS idx_memories_workspace  ON memories(workspace_id);
CREATE INDEX IF NOT EXISTS idx_memories_category   ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_created    ON memories(created_at_epoch DESC);
CREATE INDEX IF NOT EXISTS idx_memories_scope      ON memories(scope);

-- Step 4: Drop and recreate FTS5 virtual table with UNINDEXED columns
-- category and scope are filterable but should not affect bm25 relevance scores
DROP TABLE IF EXISTS memories_fts;

CREATE VIRTUAL TABLE memories_fts USING fts5(
  content,
  category UNINDEXED,
  scope UNINDEXED,
  content='memories',
  content_rowid='id',
  tokenize='porter unicode61'
);

-- Rebuild FTS index from current memories data
INSERT INTO memories_fts(rowid, content, category, scope)
  SELECT id, content, category, scope FROM memories;

-- Step 5: Recreate FTS triggers (auto-dropped when memories table was dropped)
CREATE TRIGGER IF NOT EXISTS memories_fts_insert AFTER INSERT ON memories BEGIN
  INSERT INTO memories_fts(rowid, content, category, scope)
    VALUES (new.id, new.content, new.category, new.scope);
END;

CREATE TRIGGER IF NOT EXISTS memories_fts_delete AFTER DELETE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, content, category, scope)
    VALUES ('delete', old.id, old.content, old.category, old.scope);
END;

CREATE TRIGGER IF NOT EXISTS memories_fts_update AFTER UPDATE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, content, category, scope)
    VALUES ('delete', old.id, old.content, old.category, old.scope);
  INSERT INTO memories_fts(rowid, content, category, scope)
    VALUES (new.id, new.content, new.category, new.scope);
END;

PRAGMA foreign_keys=ON;
