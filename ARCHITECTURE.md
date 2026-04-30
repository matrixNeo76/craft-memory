# Craft Memory System — Complete Architectural Documentation

> **Date**: 2026-04-30
> **Version**: 4.0 (Phase 14 — 19 tools, EverOS patterns: RRF hybrid search, core memory promotion, hyperedge roles)
> **Environment**: Windows 11, Craft Agents (pi), Python 3.12

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [MCP Server Components](#3-mcp-server-components)
4. [Craft Agents Configuration](#4-craft-agents-configuration)
5. [Automations](#5-automations)
6. [Skills](#6-skills)
7. [Resolved Issues and Applied Fixes](#7-resolved-issues-and-applied-fixes)
8. [Deployment Guide for New Installations](#8-deployment-guide-for-new-installations)
9. [Reusability Analysis for Craft Agents](#9-reusability-analysis-for-craft-agents)
10. [Stability-First Design Principles](#10-stability-first-design-principles)

---

## 1. System Overview

Craft Memory is a persistent cross-session memory system for Craft Agents (pi). It allows the AI agent to save and retrieve context across different sessions, even when switching models or providers.

**What it solves**: Without memory, every pi session starts from scratch — no recollection of decisions made, bugs fixed, or knowledge acquired. Craft Memory gives pi a long-term, local memory.

**Technology stack**:

| Component | Technology |
|-----------|------------|
| MCP Server | FastMCP 1.26.0 (Python) |
| Storage | SQLite 3 + FTS5 (full-text search) |
| Transport | HTTP (Streamable HTTP on localhost) |
| Runtime | Python 3.12, uvicorn |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Craft Agents (pi)                     │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────┐  │
│  │ Session  │  │ Session  │  │ Scheduler │  │ Label  │  │
│  │  Start   │  │   End    │  │   Tick    │  │  Add   │  │
│  │  Auto    │  │  Auto    │  │   Auto    │  │  Auto  │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └───┬────┘  │
│       │              │              │              │       │
│       ▼              ▼              ▼              ▼       │
│  ┌──────────────────────────────────────────────────┐    │
│  │            Memory Source (MCP/HTTP)              │    │
│  │         localhost:8392/mcp (Streamable HTTP)      │    │
│  └──────────────────────┬───────────────────────────┘    │
│                         │ HTTP                           │
└─────────────────────────┼────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────┐
│              Craft Memory Server (Python)                 │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │   server.py  │  │    db.py      │  │  schema.sql   │  │
│  │  (FastMCP)   │  │  (SQLite)     │  │   (Schema)    │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────────┘  │
│         │                  │                              │
│         ▼                  ▼                              │
│  ┌──────────────────────────────────────────────────┐    │
│  │     ~/.craft-agent/memory/{workspaceId}.db       │    │
│  │     (SQLite + WAL + FTS5)                        │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

**Data flow**:

1. **Session starts** → SessionStart automation runs `ensure-running.py` (starts server if down) → calls `get_recent_memory` + `list_open_loops`
2. **During work** → agent calls `remember` / `upsert_fact` / `search_memory` as needed
3. **Session ends** → SessionEnd automation calls `remember` for decisions + `summarize_scope` for handoff
4. **Every night at 03:00** → SchedulerTick automation calls `ensure-running.py` + maintenance (consolidation, fact promotion, stale loop detection)

---

## 3. MCP Server Components

### 3.1 File: `src/server.py`

MCP server built with FastMCP. Key points:

**Pydantic patch (lines 20-28)**:
```python
from mcp.server.fastmcp.utilities.func_metadata import ArgModelBase
ArgModelBase.model_config["extra"] = "ignore"
```
Craft Agents injects internal parameters (`_displayName`, `_intent`) into MCP calls. Without this patch, Pydantic rejects them with a validation error. The `extra="ignore"` patch silently discards extra fields — one line, works for all tools.

**FastMCP with stateless HTTP (lines 75-77)**:
```python
mcp = FastMCP(
    "craft-memory",
    stateless_http=True,   # ← CRITICAL FIX: avoids "Session not found" after restart
    json_response=True,    # ← FIX: JSON responses instead of SSE stream
    instructions="..."
)
```
Without `stateless_http=True`, the server creates stateful sessions. After a process restart, clients with expired session IDs receive "Session not found". With `stateless_http=True` every request is independent.

**Dual transport (entry point)**:
```python
if MCP_TRANSPORT == "http":
    import uvicorn
    app = mcp.streamable_http_app()  # ← Not http_app() (doesn't exist in 1.26.0)
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
else:
    mcp.run(transport="stdio")
```
**IMPORTANT**: `http_app(stateless_http=True)` existed in earlier versions of FastMCP but **no longer exists in 1.26.0**. The correct API is `streamable_http_app()`, combined with `stateless_http=True` in the FastMCP constructor.

**Health check endpoint** (`/health`):
- Verifies DB connection with `SELECT 1`
- Returns `db_size_mb` and `db_size_warning` (>100 MB)
- `version` read from `importlib.metadata` (not hardcoded — updates automatically with release-please)

**Automatic WAL checkpoint**:
```python
_write_count += 1
if _write_count >= 100:
    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
```
Every 100 writes to keep the WAL file bounded without blocking readers.

**Auto-reconnect** on stale connection:
```python
def _get_conn():
    if _conn is not None:
        try: _conn.execute("SELECT 1")
        except: _conn = None
    if _conn is None:
        _conn = _db_get_connection(...)
        _db_register_session(...)
```

**Privacy stripping** before every `remember` and `update_memory`:
```python
_PRIVATE_PATTERNS = _re.compile(
    r"<(private|system-reminder|system-instruction|system)>.*?</\1>",
    _re.DOTALL | _re.IGNORECASE,
)
```

**19 tools exposed**:

| Tool | Purpose | R/W |
|------|---------|-----|
| `remember` | Save episodic memory (with privacy stripping and tags) | Write |
| `update_memory` | Update content/category/importance of an existing memory | Write |
| `search_memory` | RRF hybrid search: BM25 FTS5 + Jaccard word-overlap fused via `1/(k+rank)`; LIKE fallback; `use_rrf=True` param | Read |
| `search_by_tag` | Filter memories by tag | Read |
| `get_recent_memory` | Memories ranked by importance decay; supports token budget | Read |
| `upsert_fact` | Save/update stable fact with confidence score and `confidence_type` | Write |
| `list_open_loops` | List open loops ordered by priority | Read |
| `add_open_loop` | Create new cross-session loop | Write |
| `close_open_loop` | Close a loop with optional resolution | Write |
| `update_open_loop` | Update fields on an existing loop (title, description, priority, status) with enum validation | Write |
| `summarize_scope` | Full snapshot: memories (decay-ranked) + facts + loops | Read |
| `save_summary` | Save structured handoff document (decisions, facts, next_steps) | Write |
| `run_maintenance` | Cleanup old memories, trim summaries, dedup, VACUUM | Write |
| `promote_to_core` | Set `is_core=1` on a memory — immune to exponential decay | Write |
| `link_memories` | Create directed graph edge; `role` (core/context/detail/temporal/causal) and `weight` (0–1) params | Write |
| `get_relations` | Return all neighbors (in/out/both) of a memory in the graph | Read |
| `find_similar` | FTS5 BM25 similarity search; `auto_link=True` creates INFERRED edges | Read |
| `god_facts` | Top N facts by impact: `confidence × type_bonus × (1 + mention_count × 0.2)` | Read |
| `memory_diff` | Delta since epoch timestamp: new memories, updated facts, opened/closed loops | Read |

### 3.2 File: `src/db.py`

SQLite data layer. Main functions:

**Infrastructure**:
- `run_migrations(conn)` → applies `schema.sql` as v1 then `migrations/NNN_*.sql` in order; uses `schema_version` table as tracker
- `init_db(db_path)` → WAL connection + runs migrations; FK off during migrations, on after
- `_effective_importance(importance, created_at_epoch, is_core=False)` → if `is_core=True` returns `float(importance)` without decay; otherwise `importance × e^(-λ × age_days)` with λ from `CRAFT_MEMORY_DECAY_LAMBDA` (default 0.005)

**Memories**:
- `remember(...)` → INSERT with global dedup `UNIQUE(workspace_id, content_hash)` — one content per workspace, independent of session; supports `tags` (JSON array)
- `search_memory(query, ...)` → FTS5 + BM25×0.7 + importance×0.3; LIKE fallback with correct params (scope binding bug fixed)
- `get_recent_memory(...)` → pool × 5, re-rank by decay; `max_tokens` truncates to budget
- `update_memory(id, workspace_id, ...)` → updates content/category/importance; recalculates content_hash if content changes
- `search_by_tag(tag, ...)` → LIKE `%"tag"%` on the JSON tags field

**RRF Hybrid Search** (Phase 11 — μ1):
- `_rrf_score(bm25_ranks, overlap_ranks, k=60) → dict[int, float]` → Reciprocal Rank Fusion: `score = Σ 1/(k+rank)` over two ordinal rankings; no embeddings required
- `hybrid_search(conn, query, workspace_id, scope, limit, k=60)` → FTS5 BM25 pool (×2 limit) + parallel Jaccard word-overlap ranking; fuses both with RRF; LIKE fallback if FTS5 fails; words sanitized via `re.sub(r"[^a-zA-Z0-9]", "", w)` to avoid FTS5 errors from hyphens/punctuation

**Core Memory Promotion** (Phase 12 — μ2):
- `promote_memory_to_core(conn, memory_id, workspace_id) → bool` → sets `is_core=1`; core memories do not decay (`_effective_importance` returns importance directly)
- `demote_memory_from_core(conn, memory_id, workspace_id) → bool` → sets `is_core=0`; restores normal decay
- `find_consolidation_candidates(conn, workspace_id, importance_threshold=2.0, age_days=30)` → uses a subquery wrapper to compute `effective_importance` inline (avoids `HAVING` without `GROUP BY`, SQLite bug); returns non-core memories with effective_importance below threshold, at least 30 days old, ordered ASC, limit 50

**Facts / Open Loops**:
- `upsert_fact(...)` → `ON CONFLICT DO UPDATE` on `UNIQUE(key, workspace_id, scope)`; accepts `confidence_type: str = "extracted"` (`extracted | inferred | ambiguous`)
- `create_open_loop(...)` / `list_open_loops(...)` / `close_open_loop(...)`
- `update_open_loop(conn, loop_id, workspace_id, title, description, priority, status)` → updates optional fields; validates `priority` ∈ `{low, medium, high, critical}` and `status` ∈ `{open, in_progress, closed, stale}`; builds SET clause dynamically; returns `bool`

**Knowledge Graph Layer** (Phase 10):
- `_content_hash(content, kind)` → full SHA256 (not truncated) + kind namespace (`"\x00{kind}"`) to avoid cross-entity collisions
- `link_memories(conn, source_id, target_id, relation, workspace_id, confidence_type, confidence_score, role="context", weight=1.0)` → inserts directed edge in `memory_relations`; `UNIQUE(source_id, target_id, relation)` for idempotency; validates `role` ∈ `{core, context, detail, temporal, causal}` and `relation`; returns row id or None if duplicate/invalid. Allowed relations: `caused_by | contradicts | extends | implements | supersedes | semantically_similar_to`
- `get_relations(conn, memory_id, workspace_id, direction="both")` → returns neighbors with direction label (`"in"` / `"out"`); JOINs `memories` for content preview
- `get_relations_by_role(conn, memory_id, workspace_id, role, direction="both")` → filters edges by semantic role; ordered by `weight DESC`; usable for selective traversal (e.g. only `causal` or `core` relations)
- `find_similar_memories(conn, memory_id, workspace_id, top_n=5, auto_link=False)` → extracts memory content, sanitizes words, builds `"word1 OR word2 OR ..."`, runs FTS5 BM25 search excluding the source memory; if `auto_link=True` and BM25 score < -1.5, creates `semantically_similar_to` edge with `confidence_type="inferred"`
- `god_facts(conn, workspace_id, top_n=10)` → score = `confidence × type_bonus × (1 + mention_count × 0.2)`; `type_bonus`: extracted=1.0, inferred=0.8, ambiguous=0.5; ordered DESC, returns with `god_score` field
- `memory_diff(conn, workspace_id, since_epoch)` → returns `{new_memories: [...], updated_facts: [...], opened_loops: [...], closed_loops: [...]}` comparing `created_at_epoch` / `updated_at` against the provided epoch

**Summaries**:
- `save_summary(...)` → structured handoff document (decisions, facts_learned, open_loops, refs, next_steps)
- `summarize_scope(...)` → uses decay ranking for recent memories (aligned with `get_recent_memory`)

**Maintenance**:
- `daily_maintenance(...)` → `delete_old_memories` + `mark_stale_loops` + `trim_session_summaries` + `dedup_memories` + `VACUUM`
- `trim_session_summaries(conn, workspace_id, keep_last=20)`

### 3.3 File: `src/schema.sql` + `src/migrations/`

Base schema (v1) + versioned migrations:

| Table | Purpose |
|-------|---------|
| `sessions` | Session tracking (craft_session_id, model, status) |
| `memories` | Episodic memories with category, importance, scope, tags, dedup hash |
| `memories_fts` | FTS5 index with porter stemmer + unicode61; category/scope UNINDEXED |
| `facts` | Stable knowledge (UNIQUE key+workspace+scope) with confidence score |
| `open_loops` | Incomplete tasks with priority and status |
| `session_summaries` | Structured handoff documents between sessions |
| `schema_version` | Version tracker for migration runner |

**Applied migrations**:
- `002_global_dedup.sql`: changes UNIQUE from `(session_id, content_hash)` to `(workspace_id, content_hash)`; recreates FTS5 with category/scope UNINDEXED
- `003_tags.sql`: adds `tags TEXT` column to `memories` + index
- `004_relations.sql`: adds `confidence_type TEXT DEFAULT 'extracted' CHECK(...)` to `facts`; creates `memory_relations` table with 5 indexes; FK CASCADE on `memories(id)`
- `005_core_promotion.sql`: adds `is_core INTEGER DEFAULT 0 CHECK(is_core IN (0, 1))` and `consolidated_from TEXT` to `memories`; creates partial index `WHERE is_core = 1`
- `006_relation_roles.sql`: adds `role TEXT DEFAULT 'context' CHECK(role IN ('core','context','detail','temporal','causal'))` and `weight REAL DEFAULT 1.0 CHECK(weight BETWEEN 0 AND 1)` to `memory_relations`; creates index on `(workspace_id, role)`

**`memory_relations` table** (introduced in v3.0, extended in v4.0):

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Autoincrement |
| `source_id` | INTEGER FK | → `memories(id)` CASCADE DELETE |
| `target_id` | INTEGER FK | → `memories(id)` CASCADE DELETE |
| `relation` | TEXT | `caused_by | contradicts | extends | implements | supersedes | semantically_similar_to` |
| `confidence_type` | TEXT | `extracted | inferred | ambiguous` |
| `confidence_score` | REAL | 0.0–1.0 |
| `workspace_id` | TEXT | Workspace isolation |
| `created_at_epoch` | INTEGER | Unix timestamp |
| `role` | TEXT | Semantic role of the edge: `core | context | detail | temporal | causal` (default: `context`) |
| `weight` | REAL | Edge weight 0.0–1.0 (default: 1.0); used for ordered graph traversal |

The migration runner in `db.py:run_migrations()` checks `MAX(version)` from the `schema_version` table and applies only pending migrations.

### 3.4 File: `scripts/ensure-running.py`

Server lifecycle management script — check, start, stop.

```
python ensure-running.py          # Check + auto-start if down
python ensure-running.py --check  # Check only (exit code 0=up, 2=down)
python ensure-running.py --stop   # Stop process on port
```

**Start mechanism**: Uses `subprocess.DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` on Windows to detach the process from the terminal. The server keeps running after the shell is closed.

**Health check**: Issues `GET /health` with urllib (no external dependencies). Waits up to 10 seconds for readiness.

**Stop**: On Windows uses `netstat -aon` to find the PID on the port, then `taskkill /F /PID`.

---

## 4. Craft Agents Configuration

### 4.1 Source: `sources/memory/config.json`

```json
{
  "id": "memory_e4c7a2b9",
  "name": "Craft Memory",
  "slug": "memory",
  "enabled": true,
  "provider": "craft-memory",
  "type": "mcp",
  "icon": "🧠",
  "tagline": "Persistent cross-session memory with SQLite + FTS5",
  "mcp": {
    "transport": "http",
    "url": "http://localhost:8392/mcp",
    "authType": "none"
  }
}
```

**Critical note**: `transport: "http"` is required on Windows where stdio has the "Not connected" bug. On Linux/macOS, `transport: "stdio"` would work, but HTTP is more robust because the server stays always alive.

### 4.2 Source: `sources/memory/permissions.json`

```json
{
  "allowedMcpPatterns": [
    { "pattern": "remember", "comment": "Store episodic memories" },
    { "pattern": "update_memory", "comment": "Update existing memory" },
    { "pattern": "search_memory", "comment": "Search memories via FTS5" },
    { "pattern": "search_by_tag", "comment": "Search memories by tag" },
    { "pattern": "get_recent_memory", "comment": "Get recent memories (decay-ranked)" },
    { "pattern": "upsert_fact", "comment": "Store/update stable facts" },
    { "pattern": "list_open_loops", "comment": "List open loops" },
    { "pattern": "add_open_loop", "comment": "Create new open loop" },
    { "pattern": "close_open_loop", "comment": "Close open loops" },
    { "pattern": "update_open_loop", "comment": "Update open loop fields" },
    { "pattern": "summarize_scope", "comment": "Generate scope summary" },
    { "pattern": "save_summary", "comment": "Save structured session handoff" },
    { "pattern": "run_maintenance", "comment": "Database maintenance" },
    { "pattern": "promote_to_core", "comment": "Promote memory to core (no decay)" },
    { "pattern": "link_memories", "comment": "Create knowledge graph edge" },
    { "pattern": "get_relations", "comment": "Get graph neighbors of a memory" },
    { "pattern": "find_similar", "comment": "FTS5 BM25 similarity search" },
    { "pattern": "god_facts", "comment": "Top facts by impact score" },
    { "pattern": "memory_diff", "comment": "Delta since epoch timestamp" }
  ]
}
```

These patterns allow all 19 tools to work even in Explore (safe) mode. Patterns are automatically scoped to the `memory` source slug.

### 4.3 Workspace: `config.json`

```json
{
  "defaults": {
    "enabledSourceSlugs": ["memory", "claude-mem"],
    "permissionMode": "safe"
  }
}
```

**Important**: `"memory"` MUST be in `enabledSourceSlugs`, otherwise tools are not available in new sessions.

### 4.4 Bash permissions: `permissions/default.json`

Added pattern to allow `ensure-running.py` even in safe mode:

```json
{
  "pattern": "^python\\b.*ensure-running\\.py\\b",
  "comment": "Craft Memory server lifecycle: check, start, stop"
}
```

---

## 5. Automations

4 automations configured in `automations.json`:

### 5.1 SessionStart — "Memory: Recover Session Context"

**Event**: Session starts
**Permission**: `allow-all` (required to execute MCP tools without manual user approval)

**Steps**:
1. Runs `python ensure-running.py` → starts server if down
2. Calls `get_recent_memory(scope='workspace', limit=10)`
3. Calls `list_open_loops()`
4. Summarizes context for the user

**Why allow-all**: In safe mode, every MCP tool call would require manual user approval. For a session start automation this is unsustainable.

### 5.2 SessionEnd — "Memory: Save Session Handoff"

**Event**: Session ends
**Permission**: `allow-all`

**Steps**:
1. Calls `remember(category='decision', importance=8)` for key decisions
2. Calls `remember(category='discovery', importance=7)` for discoveries
3. Calls `upsert_fact()` for confirmed stable knowledge
4. Calls `close_open_loop()` for resolved loops
5. Calls `summarize_scope()` for final snapshot
6. Presents compact handoff to the user

### 5.3 SchedulerTick — "Memory: Daily Maintenance"

**Event**: Cron `0 3 * * *` (every night at 03:00, timezone Europe/Rome)
**Permission**: `allow-all`
**Labels**: `scheduled`, `memory-maintenance`

**Steps**:
1. Runs `ensure-running.py` (auto-start if server is down)
2. Calls `summarize_scope()` for state review
3. Searches for consolidation candidates
4. Identifies facts to promote from memories
5. Checks stale loops (>30 days)
6. Presents maintenance report

### 5.4 LabelAdd — "Memory: Promote Important/Fact-Candidate Labels"

**Event**: Label `important` or `fact-candidate` added
**Matcher**: `^(important|fact-candidate)$`
**Permission**: `allow-all`

**Variable**: `$CRAFT_LABEL` contains the name of the added label (documented in Craft Agents automations)

**Behavior**:
- Label `important` → `remember(importance=9)` for key takeaways
- Label `fact-candidate` → `upsert_fact()` for stable knowledge

---

## 6. Skills

4 skills in the `skills/` folder:

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `memory-start` | Start/verify the HTTP server | "start memory", "check memory", "memory status", or when tools fail |
| `memory-protocol` | Mandatory protocol for reading/writing memory | Session start, when memory is needed |
| `memory-maintenance` | Deduplication, consolidation, cleanup | Periodic maintenance, on demand |
| `session-handoff` | Create handoff document for next session | Session end, model switch |

All declare `requiredSources: [memory]` in their YAML frontmatter.

---

## 7. Resolved Issues and Applied Fixes

### 7.1 Windows stdio bug → HTTP transport

| | Detail |
|---|---|
| **Problem** | On Windows, the MCP stdio transport disconnects after ~4 seconds. Subsequent tool calls fail with "Not connected". |
| **Root cause** | Known MCP SDK bug on Windows: the stdin pipe closes prematurely. |
| **Fix** | Migrated to HTTP transport (localhost:8392/mcp). The server stays alive as a persistent HTTP process. |

### 7.2 Wrong FastMCP API: http_app() → streamable_http_app()

| | Detail |
|---|---|
| **Problem** | `AttributeError: 'FastMCP' object has no attribute 'http_app'` |
| **Root cause** | FastMCP 1.26.0 removed `http_app()`. The correct API is `streamable_http_app()`. |
| **Fix** | Replaced `mcp.http_app(stateless_http=True)` with `mcp.streamable_http_app()` + `stateless_http=True` in the constructor. |

### 7.3 "Session not found" after server restart

| | Detail |
|---|---|
| **Problem** | After restarting the server process, tools fail with `{"error":{"code":-32600,"message":"Session not found"}}` |
| **Root cause** | `streamable_http_app()` creates stateful sessions by default. Clients with expired session IDs are rejected. |
| **Fix** | Added `stateless_http=True` and `json_response=True` to the `FastMCP()` constructor. Every request is independent, no session state. |

### 7.4 Pydantic validation error on framework parameters

| | Detail |
|---|---|
| **Problem** | Craft Agents injects `_displayName`, `_intent` into MCP tool calls. Pydantic rejects them as unknown fields. |
| **Fix** | `ArgModelBase.model_config["extra"] = "ignore"` — one line, silently discards all extra fields. |

### 7.5 Missing enabledSourceSlugs

| | Detail |
|---|---|
| **Problem** | `"memory"` was not in `enabledSourceSlugs` in the workspace config. Tools were not available in new sessions. |
| **Fix** | Added `"memory"` to `enabledSourceSlugs`. |

### 7.6 Automations without permissionMode

| | Detail |
|---|---|
| **Problem** | All 4 automations inherited `permissionMode: "safe"` from the workspace default. In safe mode, every tool call requires manual approval — useless for automations. |
| **Fix** | Added `"permissionMode": "allow-all"` to all 4 automations. |

### 7.7 SessionStart automation without server auto-start

| | Detail |
|---|---|
| **Problem** | If the HTTP server is not running, the SessionStart automation fails silently. |
| **Fix** | Added Step 1 to SessionStart and SchedulerTick: run `ensure-running.py` before any tool call. |

### 7.8 remember() saves nothing — silent FK violation

| | Detail |
|---|---|
| **Problem** | `remember()` returned "Duplicate memory skipped" on every call. `memories COUNT` stayed 0 despite the server being healthy. |
| **Root cause** | `register_session()` was never called → `sessions` table empty → `memories` has `FOREIGN KEY(session_id) REFERENCES sessions(craft_session_id)` → `INSERT OR IGNORE` silently discards FK violations, reporting them as duplicates. |
| **Evidence** | `facts = 13` (working, no FK), `sessions = 0`, `memories = 0`. |
| **Fix** | Added auto-call `_db_register_session(conn, CRAFT_SESSION_ID, WORKSPACE_ID)` in `_get_conn()`, immediately after connection creation. `register_session` uses `INSERT OR IGNORE` → idempotent. |
| **Files** | `src/server.py` line 122, `src/craft_memory_mcp/server.py` line 131. |

### 7.9 search_memory() incorrect scope binding in LIKE fallback

| | Detail |
|---|---|
| **Problem** | When `scope` was set and the FTS5 query failed (LIKE fallback), results were completely wrong with no errors. |
| **Root cause** | `params = [workspace_id, scope]` for the FTS5 path. In the LIKE fallback the query expects `[workspace_id, like_pattern, like_pattern, scope]`, but `params + [like_pattern, like_pattern]` was passed = `[workspace_id, scope, like_pattern, like_pattern]` → `scope` ended up in the `content LIKE ?` placeholder. |
| **Fix** | Build a separate `like_params`: `[workspace_id, like_pattern, like_pattern]` + optional `scope` appended at end. |
| **File** | `src/craft_memory_mcp/db.py` function `search_memory()`. |

### 7.10 SQLite HAVING without GROUP BY

| | Detail |
|---|---|
| **Problem** | `find_consolidation_candidates` used `HAVING effective_importance < :threshold` on a non-aggregate query → `sqlite3.OperationalError: HAVING clause on a non-aggregate query`. |
| **Fix** | Wrapped in a subquery: `SELECT * FROM (SELECT *, EXP(...) AS effective_importance FROM memories WHERE ...) WHERE effective_importance < :threshold` |
| **File** | `src/craft_memory_mcp/db.py` function `find_consolidation_candidates()`. |

---

## 8. Deployment Guide for New Installations

### Prerequisites

- Python 3.11+ with pip
- Craft Agents (pi) installed
- SQLite 3 with FTS5 support (included in Python stdlib)

### Step 1: Install the server

```bash
# Clone or copy the craft-memory folder
git clone https://github.com/matrixNeo76/craft-memory.git ~/craft-memory

# Install dependencies
pip install -e ~/craft-memory
```

### Step 2: Test startup

```bash
# Test stdio (to verify the server works)
cd ~/craft-memory/src
python server.py

# Test HTTP (default from v2.0)
CRAFT_MEMORY_TRANSPORT=http CRAFT_MEMORY_PORT=8392 python server.py
# Verify: curl http://localhost:8392/health
```

### Step 3: Configure Craft Agents source

Create the source folder in your workspace:

```bash
mkdir -p ~/.craft-agent/workspaces/{WS_ID}/sources/memory/
```

Create `config.json`:

```json
{
  "id": "memory_{random8hex}",
  "name": "Craft Memory",
  "slug": "memory",
  "enabled": true,
  "provider": "craft-memory",
  "type": "mcp",
  "icon": "🧠",
  "tagline": "Persistent cross-session memory with SQLite + FTS5",
  "mcp": {
    "transport": "http",
    "url": "http://localhost:8392/mcp",
    "authType": "none"
  },
  "createdAt": TIMESTAMP_MS,
  "updatedAt": TIMESTAMP_MS
}
```

Create `permissions.json` (see Section 4.2 above for the full pattern list).

Create `guide.md` (adapt to your context).

### Step 4: Enable the source in your workspace

In `~/.craft-agent/workspaces/{WS_ID}/config.json`, add `"memory"` to `enabledSourceSlugs`:

```json
"enabledSourceSlugs": ["memory"]
```

### Step 5: Configure automations

Copy `automations.json` to the workspace, adapting:
- The paths of `ensure-running.py` to your system
- The timezone in SchedulerTick
- Python paths in `start-http.bat` (Windows) or `start-memory.sh` (macOS/Linux)

### Step 6: Copy the skills

```bash
cp -r skills/memory-* skills/session-handoff ~/.craft-agent/workspaces/{WS_ID}/skills/
```

### Step 7: Add bash permission for ensure-running.py

In `permissions/default.json`:

```json
{ "pattern": "^python\\b.*ensure-running\\.py\\b", "comment": "Craft Memory server lifecycle" }
```

### Step 8: Validate and test

```bash
craft-agent source test memory
craft-agent automation validate
```

### Step 9: Start the server

```bash
python ~/craft-memory/scripts/ensure-running.py
```

From here on, the SessionStart automation will do this automatically.

---

## 9. Reusability Analysis for Craft Agents

### 9.1 Is the methodology reusable?

**Yes**, with some qualifications. The system decomposes into three layers reusable at different levels:

| Layer | Reusable? | How |
|-------|-----------|-----|
| **MCP Server** (`server.py` + `db.py` + `schema.sql`) | ✅ Fully | It's a generic MCP server. Works with any MCP client, not just Craft Agents. Can be published as a PyPI package. |
| **Craft Agents Configuration** (source + automations + skills) | ✅ Fully | `config.json`, `automations.json`, `permissions.json` and `SKILL.md` files are portable templates. Just adapt paths and slug. |
| **Lifecycle scripts** (`ensure-running.py` + `start-http.bat`) | ⚠️ Partially | `ensure-running.py` is generic (uses only Python stdlib). `start-http.bat` is Windows-specific. On macOS/Linux an equivalent `.sh` script is needed. |

### 9.2 Is it proposable on the official Craft Agents GitHub?

**Yes, but not as a single PR — better as a structured proposal.** Here's why and how:

#### What makes this implementation interesting for Craft Agents

1. **Solves a real bug**: The stdio transport on Windows is broken. Our HTTP solution is the documented workaround.

2. **Architectural pattern**: This is the first complete example of:
   - HTTP MCP source with health check
   - Automations that manage source lifecycle (auto-start)
   - Cross-session memory system with skills and structured protocols
   - MCP permissions scoped to work in Explore mode

3. **The `ensure-running.py` pattern** is generalizable: any HTTP MCP source can use it for auto-start. It is not memory-specific.

#### How to propose it

The best format is a **Craft Agents Source Template** — an installable package via `craft-agent source add memory` that:

1. Automatically creates `config.json`, `permissions.json`, `guide.md`
2. Installs skills in the workspace
3. Configures automations
4. Starts the server

This is exactly the model used by official sources (GitHub, Linear, Slack).

#### What requires adjustments to be generic

| Aspect | Current state | What is needed to be generic |
|--------|--------------|------------------------------|
| Hardcoded paths | `C:\Users\auresystem\craft-memory\...` | Use `~/.craft-agent/memory/` as base, or configurable path |
| Workspace ID | `ws_ecad0f3d` | Auto-detected from `$CRAFT_WORKSPACE_ID` |
| Python path | Hardcoded in `.bat` | Use `sys.executable` or `which python3` |
| Guide language | Mixture | English (or multilingual with i18n) |
| Windows-only `.bat` | Only `.bat` | Add `.sh` for macOS/Linux |
| `pyproject.toml` | Minimal dependencies | Add `[project.scripts]` entry point |

#### Feasibility assessment

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Community utility** | ⭐⭐⭐⭐⭐ | Cross-session memory requested by many; three-tier model unique in the MCP ecosystem |
| **Integration complexity** | ⭐⭐⭐ | Requires external MCP server — not "zero config", but `craft-memory install` automates everything |
| **Stability** | ⭐⭐⭐⭐⭐ | HTTP + stateless + health check + auto-reconnect + WAL checkpoint = production-ready |
| **Differentiation vs claude-mem** | ⭐⭐⭐⭐⭐ | Opposite and complementary design: explicit vs passive; decay + open loops + facts unique |
| **Generalizability** | ⭐⭐⭐⭐ | Generic MCP server; automations/skills portable with minor adaptations |
| **Maintainability** | ⭐⭐⭐⭐ | Migration runner + release-please + CI tests; automatic semver versioning |
| **Privacy/security** | ⭐⭐⭐⭐⭐ | Privacy stripping, no external dependencies, zero cloud, local data |

### 9.3 Recommendation

**Propose as a community source** on Craft Agents GitHub, following this format:

1. **Separate repository**: `craft-agents/craft-memory-source` (not in the main monorepo)
2. **CLI install**: `craft-agent source add memory` → downloads and configures everything
3. **Cross-platform**: Add startup scripts for macOS/Linux
4. **English documentation**: Guide, README, and skills in English
5. **CI tests**: Automated tests for the MCP server on Windows, macOS, Linux
6. **Semver versioning**: To manage breaking changes in the FastMCP API

The main value **is not just the MCP server** — it is the **complete pattern** of:
- HTTP MCP source with lifecycle management
- Automations that guarantee source availability
- Skills that teach the agent how to use memory
- Structured protocol (session start → work → session end)

This pattern is applicable to **any persistent MCP source** (database, knowledge base, project tracker) and could become a reference template for the Craft Agents community.

---

## 10. Stability-First Design Principles

### 10.1 Recommended Tool Groups

Tools are organized into three groups to reduce cognitive load. The **core group** covers 90% of daily use; the other groups are opt-in.

| Group | Tools | When to use |
|-------|-------|-------------|
| **core** | `remember`, `search_memory`, `get_recent_memory`, `upsert_fact`, `list_open_loops` | Every session — the default session flow |
| **graph** | `link_memories`, `get_relations`, `find_similar`, `god_facts`, `memory_diff`, `search_by_tag` | When building or exploring relationships between memories |
| **admin** | `run_maintenance`, `promote_to_core`, `summarize_scope`, `save_summary`, `update_memory`, `add_open_loop`, `close_open_loop`, `update_open_loop` | Lifecycle management and housekeeping |

Tool docstrings in `server.py` are prefixed with `[graph]` or `[admin]` for non-core tools. Core tools have no prefix — they are the default path.

The `FastMCP.instructions` field also documents the three groups so the agent can apply the right tool at the right time without reading all docstrings.

### 10.2 Maintenance vs Intelligence Boundaries

A key design principle: **conservative operations run automatically; semantic promotions require human or assisted decision**.

| Operation | Automation Level | Trigger |
|-----------|-----------------|---------|
| Delete old low-importance memories | **Automatic** | SchedulerTick / `run_maintenance` |
| Mark stale open loops (>30d) | **Automatic** | SchedulerTick / `run_maintenance` |
| Trim session summaries (keep 20) | **Automatic** | SchedulerTick / `run_maintenance` |
| Deduplicate memories | **Automatic** | SchedulerTick / `run_maintenance` |
| Prune weak inferred graph edges | **Automatic** | SchedulerTick / `run_maintenance` |
| WAL checkpoint | **Automatic** | Every 100 writes |
| Find consolidation candidates | **Assisted** | Agent surfaces candidates → human approves |
| Promote memory to core | **Assisted** | Agent suggests → human or agent with explicit instruction |
| Promote memory content to stable fact | **Assisted** | Agent suggests → human or agent with explicit instruction |
| Close open loop | **Never automatic** | Human or explicit agent instruction only |
| Create manual graph edge (`link_memories`) | **Never automatic** | Human or explicit agent instruction only |
| Delete specific memories | **Never automatic** | Human explicit instruction only |

**Rationale**:
- `automatic` operations are **conservative and reversible**: they remove old low-signal data, never high-importance or core content.
- `assisted` operations **change the semantic meaning** of a memory (immune to decay, elevated to stable fact) — they require a conscious choice.
- `never-auto` operations are **destructive or high-stakes**: closing a loop or linking memories creates permanent state changes that should be intentional.

### 10.3 Stability-First Mode

In the current phase, the system prioritizes **precision, explainability, and safety** over aggressive automation. This translates to concrete parameter choices:

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `CRAFT_MEMORY_AUTOLINK_THRESHOLD` | `-2.5` | Strict BM25 threshold for auto-links. Only very strong matches get auto-linked. Prevents graph pollution. |
| `CRAFT_MEMORY_PRUNE_WEIGHT_THRESHOLD` | `0.3` | Inferred edges with weight < 0.3 are pruned. Low-confidence auto-links are cleaned up. |
| `CRAFT_MEMORY_PRUNE_AGE_DAYS` | `60` | Only prune inferred edges older than 60 days. Gives time for edges to accumulate context before pruning. |
| `CRAFT_MEMORY_DECAY_LAMBDA` | `0.005` | Slow decay rate. Memories remain retrievable for months. |

All thresholds are tunable via environment variables. The initial defaults favor **fewer, higher-quality automatic edges** over graph density. After collecting real data via maintenance logs (`auto_links_created`, `inferred_edges_pruned`), thresholds can be relaxed (e.g. auto-link to `-2.0`) if the precision/recall tradeoff warrants it.

**How to interpret maintenance logs** (available after Fase C implementation):
- `inferred_edges_pruned` / `auto_links_created` ratio > 0.5 → threshold may be too loose, tighten to `-3.0`
- `inferred_edges_pruned` = 0 consistently → threshold may be too strict, relax to `-2.0`
- Graph density grows unbounded → lower `CRAFT_MEMORY_PRUNE_AGE_DAYS` to `30`

---

*End of documentation*
