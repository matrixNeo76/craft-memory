-- Sprint 5: scope hierarchy for coarse-to-fine retrieval fallback
-- Levels: session(0) < project(1) < workspace(2) < user(3) < global(4)

CREATE TABLE IF NOT EXISTS scope_hierarchy (
  scope        TEXT PRIMARY KEY,
  parent_scope TEXT REFERENCES scope_hierarchy(scope),
  level        INTEGER NOT NULL
);

INSERT OR IGNORE INTO scope_hierarchy (scope, parent_scope, level) VALUES
  ('session',   'project',   0),
  ('project',   'workspace', 1),
  ('workspace', 'user',      2),
  ('user',      'global',    3),
  ('global',    NULL,        4);
