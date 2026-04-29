# ADR-003: SQLite + FTS5 as the Storage Backend

**Status:** Accepted  
**Date:** 2026-04-28  

---

## Context

Craft Memory needs a storage backend for:
- Episodic memories (text content, category, importance, timestamps)
- Stable facts (key-value pairs)
- Open loops (tasks with priority and status)
- Session summaries (structured documents)
- Full-text search over all memories

Alternatives evaluated:

| Option | Pros | Cons |
|--------|------|------|
| **SQLite + FTS5** | Zero install, in Python stdlib, FTS5 built-in, WAL mode for concurrency | Not distributed, single-machine |
| **ChromaDB** | Vector search, semantic similarity | External process, embeddings cost, overkill for text recall |
| **PostgreSQL** | Production-grade, full SQL | Requires server setup, external dependency |
| **JSON files** | Simplest possible | No search, no transactions, corruption risk |
| **Redis** | Fast, simple K/V | No full-text search, external process, volatile |

---

## Decision

Use SQLite 3 with FTS5 extension.

- **Storage**: `~/.craft-agent/memory/{workspaceId}.db` — one file per workspace
- **WAL mode**: `PRAGMA journal_mode=WAL` for concurrent reads during writes
- **Foreign keys**: `PRAGMA foreign_keys=ON` for referential integrity
- **FTS5**: Virtual table with `porter` tokenizer + `unicode61` for English stemming and accent normalization
- **BM25 ranking**: `bm25(memories_fts)` for relevance-ordered search results
- **Content hash dedup**: `content_hash` column on `memories` with `ON CONFLICT DO NOTHING` prevents duplicate memories

---

## Consequences

**Positive:**
- Zero external dependencies — SQLite is in Python's stdlib
- Single file per workspace — trivial to backup, inspect, migrate
- FTS5 with BM25 gives quality full-text search without an embedding model
- WAL mode allows reads during writes (multiple tools can query while a memory is being saved)
- Local-first — no data leaves the machine

**Negative:**
- No semantic/vector search — keyword search only (acceptable for the use case)
- Not distributed — single machine only (acceptable: Craft Agents is a local desktop app)
- FTS5 availability: must be compiled into SQLite. Python's bundled SQLite always includes FTS5 on all platforms since Python 3.9

**Schema versioning:**
The `schema_version` table tracks the current schema version for future migrations.
