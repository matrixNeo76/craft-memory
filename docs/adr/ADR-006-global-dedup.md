# ADR-006: Global Dedup via UNIQUE(workspace_id, content_hash)

**Date:** 2026-04-30  
**Status:** Accepted  
**Deciders:** Matrix (AureSystem)

---

## Context

The original schema used `UNIQUE(session_id, content_hash)` to prevent duplicate memories
within a single session. This meant the same piece of knowledge could be stored N times
across N sessions — one row per session that encountered it.

Over time this causes:
- Unnecessary DB growth (identical content repeated many times)
- Noisy recall results (same memory appears multiple times with different session IDs)
- Misleading `importance` aggregation (importance of a memory diluted across copies)

## Decision

Change the UNIQUE constraint to `UNIQUE(workspace_id, content_hash)`.

This means: a given piece of content can be stored **at most once per workspace**, regardless
of which session stores it. Subsequent sessions that encounter the same content will get
"Duplicate memory skipped" and no row is created.

The dedup is SHA-256 based (first 16 hex chars of the hash), computed from the raw content string.

## Consequences

**Positive:**
- DB size stays bounded: same knowledge = 1 row, not N rows
- Recall results are clean: no duplicate hits for the same content
- Simpler mental model: "one memory per fact per workspace"

**Negative:**
- Lost provenance: we no longer track which sessions saw the same content
  (the original `session_id` on the row reflects the *first* session that stored it)
- Cross-workspace sharing is still not supported (memories are workspace-scoped)

## Migration

Migration 002 (`002_global_dedup.sql`) handles existing DBs:
1. Deletes duplicates (keeps MIN(id) per workspace+content_hash)
2. Recreates the memories table with the new UNIQUE constraint
3. Rebuilds all indexes and FTS5 triggers
