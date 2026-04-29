-- Craft Memory System - SQLite Schema
-- Persistent cross-session memory for Craft Agents
-- Inspired by claude-mem, adapted for Craft Agents architecture

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ─────────────────────────────────────────────────────────────────────
-- sessions: one row per Craft Agents session tracked by the memory system
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  craft_session_id    TEXT    UNIQUE NOT NULL,
  workspace_id        TEXT    NOT NULL,
  model_provider      TEXT,
  model_name          TEXT,
  user_prompt         TEXT,
  started_at          TEXT    NOT NULL,
  started_at_epoch    INTEGER NOT NULL,
  completed_at        TEXT,
  completed_at_epoch  INTEGER,
  status              TEXT    NOT NULL DEFAULT 'active'
                              CHECK(status IN ('active', 'completed', 'failed'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_craft_id    ON sessions(craft_session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_workspace   ON sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status      ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_started     ON sessions(started_at_epoch DESC);

-- ─────────────────────────────────────────────────────────────────────
-- memories: episodic memory - observations, decisions, discoveries
-- UNIQUE(session_id, content_hash) for dedup via ON CONFLICT DO NOTHING
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memories (
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
  UNIQUE(session_id, content_hash)
);
CREATE INDEX IF NOT EXISTS idx_memories_session    ON memories(session_id);
CREATE INDEX IF NOT EXISTS idx_memories_workspace  ON memories(workspace_id);
CREATE INDEX IF NOT EXISTS idx_memories_category   ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_created    ON memories(created_at_epoch DESC);
CREATE INDEX IF NOT EXISTS idx_memories_scope      ON memories(scope);

-- ─────────────────────────────────────────────────────────────────────
-- memories_fts: full-text search index on memories
-- Uses FTS5 with porter stemmer for English + unicode61 for diacritics
-- ─────────────────────────────────────────────────────────────────────
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
  content,
  category,
  scope,
  content='memories',
  content_rowid='id',
  tokenize='porter unicode61'
);

-- Triggers to keep FTS in sync with memories table
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

-- ─────────────────────────────────────────────────────────────────────
-- facts: stable, persistent knowledge about the project/workspace
-- UNIQUE(key, workspace_id, scope) - one fact per key per scope per workspace
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS facts (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  key                 TEXT    NOT NULL,
  value               TEXT    NOT NULL,
  workspace_id        TEXT    NOT NULL,
  scope               TEXT    DEFAULT 'workspace',
  confidence          REAL    DEFAULT 1.0 CHECK(confidence BETWEEN 0 AND 1),
  source_session      TEXT,
  created_at          TEXT    NOT NULL,
  updated_at          TEXT    NOT NULL,
  UNIQUE(key, workspace_id, scope)
);
CREATE INDEX IF NOT EXISTS idx_facts_workspace  ON facts(workspace_id);
CREATE INDEX IF NOT EXISTS idx_facts_scope      ON facts(scope);
CREATE INDEX IF NOT EXISTS idx_facts_key        ON facts(key);

-- ─────────────────────────────────────────────────────────────────────
-- open_loops: incomplete tasks, follow-ups, things to revisit
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS open_loops (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id          TEXT    NOT NULL,
  workspace_id        TEXT    NOT NULL,
  title               TEXT    NOT NULL,
  description         TEXT,
  priority            TEXT    DEFAULT 'medium'
                              CHECK(priority IN ('low', 'medium', 'high', 'critical')),
  scope               TEXT    DEFAULT 'workspace',
  status              TEXT    DEFAULT 'open'
                              CHECK(status IN ('open', 'in_progress', 'closed', 'stale')),
  resolution          TEXT,
  source_session      TEXT,
  created_at          TEXT    NOT NULL,
  created_at_epoch    INTEGER NOT NULL,
  closed_at           TEXT,
  closed_at_epoch     INTEGER,
  FOREIGN KEY(session_id) REFERENCES sessions(craft_session_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_loops_session     ON open_loops(session_id);
CREATE INDEX IF NOT EXISTS idx_loops_workspace   ON open_loops(workspace_id);
CREATE INDEX IF NOT EXISTS idx_loops_status      ON open_loops(status);
CREATE INDEX IF NOT EXISTS idx_loops_priority    ON open_loops(priority);
CREATE INDEX IF NOT EXISTS idx_loops_created     ON open_loops(created_at_epoch DESC);

-- ─────────────────────────────────────────────────────────────────────
-- session_summaries: handoff documents between sessions
-- Contains structured JSON fields for decisions, facts, loops, references
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS session_summaries (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id          TEXT    NOT NULL,
  workspace_id        TEXT    NOT NULL,
  summary             TEXT,
  decisions           TEXT,   -- JSON array of strings
  facts_learned       TEXT,   -- JSON array of strings
  open_loops          TEXT,   -- JSON array of strings
  refs                TEXT,   -- JSON array of strings (renamed from 'references' to avoid SQL keyword)
  next_steps          TEXT,
  created_at          TEXT    NOT NULL,
  created_at_epoch    INTEGER NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(craft_session_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);
-- No index on refs column needed, JSON is not indexed directly
CREATE INDEX IF NOT EXISTS idx_summaries_session   ON session_summaries(session_id);
CREATE INDEX IF NOT EXISTS idx_summaries_workspace ON session_summaries(workspace_id);
CREATE INDEX IF NOT EXISTS idx_summaries_created   ON session_summaries(created_at_epoch DESC);

-- ─────────────────────────────────────────────────────────────────────
-- schema_version: track schema migrations
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
);
INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (1, datetime('now'));
