# Craft Memory System — Complete Architectural Documentation

> **Date**: 2026-04-30
> **Version**: 7.0 (Sprint 1–10 — 46 tools: observability, temporal lifecycle, boundary detection, procedural memory, scope hierarchy, graph context, batch ops, procedure intelligence, session quality, SessionDB)
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
11. [Session Scanner](#11-session-scanner)

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

**46 tools exposed** (19 baseline + 27 added in Sprints 1–10) + 2 HTTP endpoints (`/health`, `/metrics`):

| Tool | Purpose | R/W | Sprint |
|------|---------|-----|--------|
| `remember` | Save episodic memory (with privacy stripping and tags) | Write | baseline |
| `update_memory` | Update content/category/importance of an existing memory | Write | baseline |
| `search_memory` | RRF hybrid search: BM25 FTS5 + Jaccard word-overlap; LIKE fallback; lifecycle filter | Read | baseline |
| `search_by_tag` | Filter memories by tag | Read | baseline |
| `get_recent_memory` | Memories ranked by importance decay; supports token budget; lifecycle filter | Read | baseline |
| `upsert_fact` | Save/update stable fact with confidence score and `confidence_type` | Write | baseline |
| `list_open_loops` | List open loops ordered by priority | Read | baseline |
| `add_open_loop` | Create new cross-session loop | Write | baseline |
| `close_open_loop` | Close a loop with optional resolution | Write | baseline |
| `update_open_loop` | Update fields on an existing loop with enum validation | Write | baseline |
| `summarize_scope` | Full snapshot: memories (decay-ranked) + facts + loops | Read | baseline |
| `save_summary` | Save structured handoff document (decisions, facts, next_steps) | Write | baseline |
| `run_maintenance` | Cleanup old memories, trim summaries, dedup, VACUUM | Write | baseline |
| `promote_to_core` | Set `is_core=1` on a memory — immune to exponential decay | Write | baseline |
| `link_memories` | Create directed graph edge; `role` and `weight` (0–1) params | Write | baseline |
| `get_relations` | Return all neighbors (in/out/both) of a memory in the graph | Read | baseline |
| `find_similar` | FTS5 BM25 similarity search; `auto_link=True` creates INFERRED edges | Read | baseline |
| `god_facts` | Top N facts by impact: `confidence × type_bonus × (1 + mention_count × 0.2)` | Read | baseline |
| `memory_diff` | Delta since epoch timestamp: new memories, updated facts, opened/closed loops | Read | baseline |
| `memory_stats` | Aggregate stats: memory count by scope/category, is_core count, open loops, facts, procedures | Read | Sprint 1 |
| `explain_retrieval` | Explain why a memory would be retrieved: score, decay, is_core, tags | Read | Sprint 1 |
| `generate_handoff` | Auto-generate structured handoff from recent memories, open loops, and facts | Read | Sprint 1 |
| `save_decision_record` | Save a tagged memory with decision metadata (options, rationale, outcome) | Write | Sprint 1 |
| `invalidate_memory` | Set lifecycle_status to `invalidated` with a reason | Write | Sprint 2 |
| `get_memory_history` | Return the supersession chain for a memory (follows `superseded_by` links) | Read | Sprint 2 |
| `flag_for_review` | Set lifecycle_status to `needs_review` with a reason | Write | Sprint 2 |
| `list_needs_review` | List memories in `needs_review` state, ordered by created_at | Read | Sprint 2 |
| `approve_memory` | Restore a `needs_review` memory to `active` lifecycle status | Write | Sprint 2 |
| `classify_event` | Classify content into MemoryClass (DISCARD/EPISODIC/FACT_CANDIDATE/OPEN_LOOP/PROCEDURE_CANDIDATE/CORE_CANDIDATE) | Read | Sprint 3 |
| `save_procedure` | Upsert a named procedure with trigger context, steps (markdown), and confidence | Write | Sprint 4 |
| `search_procedures` | FTS5 search over procedures (name + trigger + steps) | Read | Sprint 4 |
| `get_applicable_procedures` | Find the most applicable procedures for the current task context | Read | Sprint 4 |
| `get_memory_bundle` | Batch-fetch N complete memories by ID list (Layer 3 coarse-to-fine retrieval) | Read | Sprint 5 |
| `search_facts` | Keyword search on facts key or value; scope-filterable; ordered by confidence desc | Read | Sprint 5-Close |
| `list_procedures` | List all procedures in workspace filtered by status (active/draft/deprecated) | Read | Sprint 5-Close |
| `get_scope_ancestors` | Return scope + ancestor chain from specific to broad (session→global) | Read | Sprint 5-Close |
| `consolidation_candidates` | Find old non-core memories with low effective importance ready for pruning | Read | Sprint 5-Close |
| `record_procedure_outcome` | Record execution result (success/partial/failure) for a procedure; triggers confidence evolution | Write | Sprint 6 |
| `get_procedure_outcomes` | Return recent execution outcomes for a procedure, newest first | Read | Sprint 6 |
| `get_graph_context` | BFS multi-hop traversal: return center memory + neighbors up to N hops with edges and depth_map | Read | Sprint 7 |
| `batch_remember` | Save N memories in one call (JSON array input); reduces MCP round-trips for session-end automation | Write | Sprint 7 |
| `top_procedures` | Rank procedures by `confidence × success_rate × use_count`; simmetrico di `god_facts` | Read | Sprint 8 |
| `consolidate_memories` | Dry-run or execute: create procedure from candidates + invalidate originals; `confirm=False` is safe | Write | Sprint 8 |
| `rate_session` | Assign quality_score (0.0–1.0) + notes to a session summary; feeds SessionDB | Write | Sprint 8 |
| `get_high_quality_sessions` | Return session summaries with quality_score >= min_score; positive examples for self-improvement | Read | Sprint 9 |
| `export_session_traces` | Export rated sessions as JSONL; training/eval bridge for DSPy, fine-tuning, eval harness | Read | Sprint 9 |

**HTTP endpoints** (non-MCP, direct HTTP):
- `GET /health` — JSON status: db state, version, workspace, db_size_mb (Sprint baseline)
- `GET /metrics` — Prometheus text format: memories, facts, loops, procedures, avg confidence, db_size (Sprint 10)

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
- `daily_maintenance(...)` → `delete_old_memories` + `mark_stale_loops` + `trim_session_summaries` + `dedup_memories` + `VACUUM`; returns dict including `needs_review` count (Sprint 2)
- `trim_session_summaries(conn, workspace_id, keep_last=20)`

**Observability — Sprint 1**:
- `get_memory_stats(conn, workspace_id)` → aggregate stats: memory count by category/scope, is_core, lifecycle_status, open loops, facts, procedures
- `generate_handoff(conn, workspace_id, session_id, limit)` → builds structured handoff from recent memories + open loops + facts; output is a markdown document
- `save_decision_record(conn, session_id, workspace_id, title, decision, ...)` → stores a tagged memory with category `decision` and structured metadata

**Temporal Lifecycle — Sprint 2** (migration 008_fact_temporal):
- Adds `valid_from`, `valid_to`, `superseded_by`, `lifecycle_status` columns to `memories`
- `lifecycle_status` values: `active | superseded | invalidated | needs_review`
- `invalidate_memory(conn, memory_id, workspace_id, reason)` → sets `lifecycle_status='invalidated'`
- `get_memory_history(conn, memory_id, workspace_id)` → follows `superseded_by` FK chain; returns chronological list
- `flag_for_review(conn, memory_id, workspace_id, reason)` → sets `lifecycle_status='needs_review'`
- `list_needs_review(conn, workspace_id, limit)` → lists memories awaiting review
- `approve_memory(conn, memory_id, workspace_id)` → resets `lifecycle_status='active'`
- `search_memory` and `get_recent_memory` extended: `include_inactive=False`, `lifecycle_filter` param

**Boundary Detection — Sprint 3**:
- `MemoryClass(str, Enum)` → `DISCARD | EPISODIC | FACT_CANDIDATE | OPEN_LOOP | PROCEDURE_CANDIDATE | CORE_CANDIDATE`
- `classify_memory_event(content, context_signals, conn, workspace_id) → tuple[MemoryClass, str]` → heuristic classifier; returns class + reasoning string

**Procedural Memory — Sprint 4** (migration 009_procedures):
- `save_procedure(conn, workspace_id, name, trigger_context, steps_md, ...)` → UPSERT with `UNIQUE(workspace_id, name)`; syncs `procedures_fts` standalone FTS5 index (delete + re-insert)
- `search_procedures(conn, query, workspace_id, limit)` → porter FTS5 search over name + trigger_context + steps_md
- `get_applicable_procedures(conn, context, workspace_id, limit)` → active procedures ordered by confidence desc
- `list_procedures(conn, workspace_id, status, limit)` → list by status

**Scope Hierarchy — Sprint 5** (migration 010_scope_hierarchy):
- `get_scope_ancestors(conn, scope) → list[str]` → reads `scope_hierarchy` table; returns scope + all ancestors from specific to broad; graceful fallback to hardcoded order if table missing
- `get_memory_bundle(conn, memory_ids, workspace_id) → list[dict]` → batch-fetch by ID list with workspace isolation; missing IDs silently skipped; returns full row dicts

**Sprint 5-Close — expose previously import-only functions**:
- `search_facts(conn, query, workspace_id, scope) → list[dict]` → LIKE search on `(key, value)` ordered by confidence desc; complements `god_facts` with keyword-driven lookup
- `list_procedures(conn, workspace_id, status, limit)` — already in Sprint 4; now also exposed as MCP tool `list_procedures`
- `get_scope_ancestors` — already in Sprint 5; now also exposed as MCP tool `get_scope_ancestors`
- `find_consolidation_candidates` — already implemented; now exposed as MCP tool `consolidation_candidates`

**Procedure Outcome Tracking — Sprint 6** (migration 011_procedure_outcomes):
- `record_procedure_outcome(conn, procedure_id, workspace_id, outcome, notes) → int` → INSERT into `procedure_outcomes`; validates outcome ∈ `{'success','partial','failure'}` (raises `ValueError` otherwise); returns row id
- `get_procedure_outcomes(conn, procedure_id, workspace_id, limit) → list[dict]` → returns outcomes newest-first
- `update_procedure_confidence(conn, procedure_id, workspace_id, recent_n=10) → float|None` → Bayesian blend: `new = clamp(old×0.3 + avg_score×0.7, 0.05, 0.95)`; scores: success=1.0, partial=0.5, failure=0.0; returns None if no outcomes
- `_update_all_procedure_confidences(conn, workspace_id) → int` → iterates all procedures with outcomes, calls `update_procedure_confidence`; used by `daily_maintenance`
- `daily_maintenance` extended: calls `_update_all_procedure_confidences`; returns dict now includes `procedures_confidence_updated` count

**Multi-hop Graph Context + Batch Ops — Sprint 7**:
- `get_graph_context(conn, memory_id, workspace_id, depth=2) → dict|None` → BFS from `memory_id` up to `depth` hops; traverses both inbound and outbound edges; uses `visited` set to handle cycles safely; returns `{center, nodes[], edges[], depth_map, total_nodes, total_edges}`; returns `None` if memory not found or wrong workspace
- `batch_remember(conn, entries, session_id, workspace_id) → list[int|None]` → saves N memories in one call; each entry dict accepts `content`, `category`, `importance`, `scope`, `tags`; duplicates return `None` in that slot without error; preserves order

**Procedure Intelligence — Sprint 8**:
- `get_top_procedures(conn, workspace_id, limit=10) → list[dict]` → ranks active procedures by `confidence × success_rate × use_count`; LEFT JOIN `procedure_outcomes`; zero-outcome procedures get `top_score=0.0`, `use_count=0`; simmetrico di `god_facts`
- `consolidate_memories(conn, candidate_ids, workspace_id, procedure_name, trigger_context, steps_md, confirm=False) → dict` → dry-run (`confirm=False`): returns preview with `candidate_count`; confirm (`confirm=True`): calls `save_procedure` + `invalidate_memory` per each valid ID; returns `{dry_run, procedure_id, invalidated_count}`
- `rate_session(conn, summary_id, workspace_id, score, notes=None) → bool` → UPDATE `session_summaries` with `quality_score` and `quality_notes`; returns `False` if summary not found or wrong workspace

**SessionDB Foundation — Sprint 9**:
- `get_high_quality_sessions(conn, workspace_id, min_score=0.7, limit=10) → list[dict]` → returns session summaries with `quality_score >= min_score`; NULL scores excluded; ordered by score desc
- `export_session_traces(conn, workspace_id, min_score=None, limit=50) → str` → JSONL export (one JSON per line); `min_score=None` includes all scored sessions; unscored always excluded; returns `""` if no results

**Observability — Sprint 10**:
- `GET /metrics` HTTP endpoint → Prometheus text format; aggregates via `get_memory_stats()` + AVG confidence query + db_size; workspace-scoped labels

### 3.3 File: `src/schema.sql` + `src/migrations/`

Base schema (v1) + versioned migrations:

| Table | Purpose | Added |
|-------|---------|-------|
| `sessions` | Session tracking (craft_session_id, model, status) | v1 |
| `memories` | Episodic memories with category, importance, scope, tags, dedup hash, lifecycle_status | v1 + Sprint 2 |
| `memories_fts` | FTS5 index with porter stemmer + unicode61; category/scope UNINDEXED | v1 |
| `facts` | Stable knowledge (UNIQUE key+workspace+scope) with confidence score | v1 |
| `open_loops` | Incomplete tasks with priority and status | v1 |
| `session_summaries` | Structured handoff documents between sessions | v1 |
| `memory_relations` | Directed knowledge graph edges (relation, role, weight, confidence) | migration 004 |
| `schema_version` | Version tracker for migration runner | v1 |
| `procedures` | Named reusable workflows with trigger context and markdown steps | migration 009 (Sprint 4) |
| `procedures_fts` | Standalone FTS5 index for procedures (porter tokenizer) | migration 009 (Sprint 4) |
| `scope_hierarchy` | Scope inheritance chain (session→project→workspace→user→global) | migration 010 (Sprint 5) |
| `procedure_outcomes` | Execution outcome records (success/partial/failure) per procedure for confidence evolution | migration 011 (Sprint 6) |
| `session_summaries` | Extended with `quality_score REAL` and `quality_notes TEXT` for SessionDB | migration 012 (Sprint 8) |

**Applied migrations**:
- `002_global_dedup.sql`: changes UNIQUE from `(session_id, content_hash)` to `(workspace_id, content_hash)`; recreates FTS5 with category/scope UNINDEXED
- `003_tags.sql`: adds `tags TEXT` column to `memories` + index
- `004_relations.sql`: adds `confidence_type TEXT DEFAULT 'extracted' CHECK(...)` to `facts`; creates `memory_relations` table with 5 indexes; FK CASCADE on `memories(id)`
- `005_core_promotion.sql`: adds `is_core INTEGER DEFAULT 0` and `consolidated_from TEXT` to `memories`; creates partial index `WHERE is_core = 1`
- `006_relation_roles.sql`: adds `role TEXT DEFAULT 'context'` and `weight REAL DEFAULT 1.0` to `memory_relations`; creates index on `(workspace_id, role)`
- `007_edge_manual_flag.sql`: adds `is_manual INTEGER DEFAULT 0` to `memory_relations` to distinguish human-created edges from auto-linked ones
- `008_fact_temporal.sql` (Sprint 2): adds `valid_from`, `valid_to`, `superseded_by`, `lifecycle_status` to `memories`; `lifecycle_status CHECK IN ('active','superseded','invalidated','needs_review')`; partial index on `(workspace_id, lifecycle_status)`
- `009_procedures.sql` (Sprint 4): creates `procedures` table with `UNIQUE(workspace_id, name)`; status `CHECK IN ('active','draft','deprecated')`; confidence `BETWEEN 0 AND 1`; standalone `procedures_fts USING fts5(name, trigger_context, steps_md, tokenize='porter ascii')`
- `010_scope_hierarchy.sql` (Sprint 5): creates `scope_hierarchy` table with `scope` PK, `parent_scope` FK (self-referential), `level INTEGER`; seeds 5 canonical scopes: `session(0) → project(1) → workspace(2) → user(3) → global(4)`
- `011_procedure_outcomes.sql` (Sprint 6): creates `procedure_outcomes` table with FK→`procedures(id)` CASCADE DELETE; `outcome CHECK IN ('success','partial','failure')`; two indexes: `(procedure_id, workspace_id)` and `(workspace_id, created_at_epoch DESC)`
- `012_session_quality.sql` (Sprint 8): `ALTER TABLE session_summaries ADD COLUMN quality_score REAL CHECK(0.0–1.0)` and `quality_notes TEXT`; partial index `(workspace_id, quality_score DESC) WHERE quality_score IS NOT NULL`

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

14 automations configured in `automations.json` (updated 2026-05-02):

> **Action types**: Craft Agents automations support `prompt` (sends text to LLM — fragile, model-dependent) and `command` (executes shell command directly — deterministic, always runs). The memory automations use **`command` actions for server startup** (`craft-memory ensure`) and **`prompt` actions for agent memory operations**. This ensures the MCP server is running before the agent sees any instructions.

### 5.1 SessionStart — "Memory: Start Server & Recover Context (Enhanced)"

**Event**: Session starts
**Permission**: `allow-all`

**Action type**: `command` + `prompt`

**Steps**:
1. **`command`**: Runs `craft-memory ensure` → starts server if down (deterministic, no agent interpretation)
2. **`prompt`**: Calls `get_recent_memory(scope='workspace', limit=10)`
3. Calls `list_open_loops()`
4. Calls `get_applicable_procedures(current_context='session start', limit=3)`
5. Summarizes context for the user
6. Suggests applicable procedures if found
7. Sets proactive label behavior: `important`, `fact-candidate`, `procedure-candidate`

**Why command action first**: When Craft Agents restarts on Windows, the child process (craft-memory server) is killed by Windows Job Objects. The `command` action runs `craft-memory ensure` directly via shell, without waiting for the LLM to interpret a prompt. If the server was killed, it restarts immediately. See [§7.9](#79-windows-job-object-kills-server-on-craft-agents-restart).

**Why allow-all**: In safe mode, every MCP tool call would require manual user approval.

### 5.2 SessionEnd — "Memory: Save Session Handoff"

**Event**: Session ends
**Permission**: `allow-all`

**Action type**: `command` + `prompt`

**Steps**:
1. **`command`**: Runs `craft-memory ensure` → ensures server is up before saving
2. **`prompt`**: Calls `remember(category='decision', importance=8)` for key decisions
3. Calls `remember(category='discovery', importance=7)` for discoveries
4. Calls `upsert_fact()` for confirmed stable knowledge
5. Calls `close_open_loop()` for resolved loops
6. Calls `summarize_scope()` for final snapshot
7. Presents compact handoff to the user

### 5.3 PreCompact — "Memory: PreCompact Emergency Save"

**Event**: Context about to be compacted
**Permission**: `allow-all`
**Why**: Prevents loss of unrecoverable context. Saves decisions, facts, and a snapshot before compaction.

**Steps**:
1. Calls `get_recent_memory(limit=5)` to check what is already saved
2. Saves decisions → `remember(category='decision', importance=9)`
3. Saves facts → `upsert_fact()`
4. Saves open loops → `add_open_loop()`
5. Creates snapshot → `remember(category='note', importance=7)`

### 5.4 SessionStatusChange — "Memory: Session Done - Quality & Archive"

**Event**: Session status changed to `done`
**Matcher**: `^done$`
**Permission**: `allow-all`

**Steps**:
1. Quality assessment → `rate_session()` if score >= 0.7
2. Knowledge consolidation → `upsert_fact()`, `save_procedure()`
3. Loop cleanup → `close_open_loop()` for resolved loops
4. Handoff → `generate_handoff()`

### 5.5 PermissionModeChange — "Memory: Permission Escalation Audit"

**Event**: Permission mode changes from `safe` to `allow-all`
**Condition**: `state.permissionMode from=safe to=allow-all`

**Steps**:
1. `remember(category='change', importance=8, tags=['security', 'audit'])`
2. Warns user about auto-approval risks

### 5.6 FlagChange — "Memory: Flagged Session → Open Loop"

**Event**: Session flagged
**Matcher**: `true`

**Steps**:
1. `add_open_loop(title='Flagged Session: ...', priority='high')`
2. `remember(category='note', importance=8, tags=['flagged'])`

### 5.7 SubagentStart — "Memory: Track Subagent Start"

**Event**: Subagent spawned
**Steps**: `remember(category='note', importance=5, tags=['subagent', 'spawn'])`

### 5.8 SubagentStop — "Memory: Capture Subagent Outcome"

**Event**: Subagent completed
**Steps**: If successful → `remember(category='feature', importance=7)`. If failed → `add_open_loop(priority='medium')`

### 5.9 SchedulerTick — "Memory: Daily Maintenance"

**Event**: Cron `0 3 * * *` (every night at 03:00, timezone Europe/Rome)
**Permission**: `allow-all`
**Labels**: `scheduled`, `memory-maintenance`

**Action type**: `command` + `prompt`

**Steps**:
1. **`command`**: Runs `craft-memory ensure` → ensures server is up
2. **`prompt`**: Calls `summarize_scope()` for state review
3. Searches for consolidation candidates
4. Identifies facts to promote from memories
5. Checks stale loops (>30 days)
6. Presents maintenance report

### 5.10 SchedulerTick — "Memory: Weekly Review Report"

**Event**: Cron `0 10 * * 1` (Monday 10:00, timezone Europe/Rome)
**Labels**: `scheduled`, `weekly-review`

**Action type**: `command` + `prompt`

**Steps**:
1. **`command`**: Runs `craft-memory ensure`
2. **`prompt`**: `memory_stats()` overview
3. `memory_diff()` analyze week changes
4. `list_procedures()` + `get_procedure_outcomes()` health check
5. `get_high_quality_sessions()` quality report
6. Recommendations: deprecate, promote, close

### 5.11 SchedulerTick — "Memory: Monthly Archive"

**Event**: Cron `0 3 1 * *` (1st of month 03:00, timezone Europe/Rome)
**Labels**: `scheduled`, `monthly-archive`

**Action type**: `command` + `prompt`

**Steps**:
1. **`command`**: Runs `craft-memory ensure`
2. **`prompt`**: `summarize_scope()` → save as milestone
3. `export_session_traces()` training data
4. `run_maintenance()` aggressive cleanup + VACUUM
5. Archive report with stats

### 5.12 LabelAdd — "Memory: Promote Important/Fact-Candidate/Procedure-Candidate Labels"

**Event**: Label `important`, `fact-candidate`, or `procedure-candidate` added
**Matcher**: `^(important|fact-candidate|procedure-candidate)$`
**Permission**: `allow-all`

**Variable**: `$CRAFT_LABEL` contains the name of the added label

**Behavior**:
- Label `important` → `remember(importance=9)` for key takeaways
- Label `fact-candidate` → `upsert_fact()` for stable knowledge
- Label `procedure-candidate` → `save_procedure()` for repeatable workflows ← **NEW**

### 5.13 LabelAdd — "Memory: Suggest Graph Links"

**Event**: Label `link-suggestions` added
**Matcher**: `^link-suggestions$`

**Steps**: `find_similar()` for recent memories, suggest `link_memories()` pairs

### 5.14 LabelAdd — "Memory: Consolidate Related Memories"

**Event**: Label `consolidate` added
**Matcher**: `^consolidate$`

**Steps**: `consolidation_candidates()` → propose clusters → `consolidate_memories(confirm=True)` after user approval

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

### 7.9 Windows Job Object kills server on Craft Agents restart

| | Detail |
|---|---|
| **Problem** | Craft Memory server (port 8392) is killed when Craft Agents (Electron) restarts. On Windows, `DETACHED_PROCESS` only detaches the console — the process remains in the parent's Job Object and is terminated when Craft Agents exits. |
| **Root cause** | Windows Job Object: all child processes are terminated when the parent process exits, regardless of `DETACHED_PROCESS` or `CREATE_NEW_PROCESS_GROUP` flags. |
| **Trigger** | Craft Agents restart, app update, system reboot. |
| **Fix** | Changed 5 automations (SessionStart, SessionEnd, SchedulerTick Daily/Weekly/Monthly) from `"type": "prompt"` (LLM-interpreted text — fragile) to `"type": "command"` + `"type": "prompt"`. The `command` action executes `craft-memory ensure` as a shell command **deterministically**, before the LLM receives any instructions. This guarantees the server is running when the agent tries to use memory tools. |
| **Why prompt failed** | The old SessionStart prompt said "Run: craft-memory ensure" — text that the agent had to interpret and execute. If the agent skipped it or couldn't run shell commands (permissions, missing PATH), the server stayed down. |
| **Why command works** | `"type": "command"` in Craft Agents executes the shell command directly via OS, without any LLM interpretation. It runs first, then the `prompt` action sends instructions to the agent. |
| **Automations changed** | `SessionStart`, `SessionEnd`, `SchedulerTick` (Daily Maintenance, Weekly Review Report, Monthly Archive) — 5 total |
| **Relevant files** | `~/.craft-agent/workspaces/{workspace}/automations.json` |
| **Date** | 2026-05-02 |
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
- The timezone in SchedulerTick
- Python paths in `start-http.bat` (Windows) or `start-memory.sh` (macOS/Linux)

**Important**: The automations use `"type": "command"` actions to run `craft-memory ensure` before each `"type": "prompt"` action. This is intentional — `command` actions execute shell commands deterministically without LLM interpretation, guaranteeing the MCP server is running before the agent attempts memory operations. Do not change these to `prompt` actions.

See [§7.9](#79-windows-job-object-kills-server-on-craft-agents-restart) for details on why `command` actions are needed (Windows Job Object kills child processes on parent exit).

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
| **graph** | `link_memories`, `get_relations`, `find_similar`, `god_facts`, `memory_diff`, `search_by_tag` | Building or exploring relationships between memories |
| **admin** | `run_maintenance`, `promote_to_core`, `summarize_scope`, `save_summary`, `update_memory`, `add_open_loop`, `close_open_loop`, `update_open_loop` | Lifecycle management and housekeeping |
| **observability** | `memory_stats`, `explain_retrieval`, `generate_handoff`, `save_decision_record` | Diagnostics and session handoff (Sprint 1) |
| **lifecycle** | `invalidate_memory`, `get_memory_history`, `flag_for_review`, `list_needs_review`, `approve_memory` | Memory lifecycle management — review, invalidation, supersession (Sprint 2) |
| **policy** | `classify_event` | Boundary detection before storing a memory event (Sprint 3) |
| **procedures** | `save_procedure`, `search_procedures`, `get_applicable_procedures`, `list_procedures`, `record_procedure_outcome`, `get_procedure_outcomes` | Capturing, retrieving, and evolving reusable workflows (Sprints 4, 5-Close, 6) |
| **retrieval** | `get_memory_bundle`, `get_graph_context`, `get_scope_ancestors`, `consolidation_candidates` | Layer 3 coarse-to-fine: full detail, neighborhood context, scope hierarchy (Sprints 5, 7) |
| **facts** | `search_facts` | Keyword-driven fact lookup when `god_facts` is not specific enough (Sprint 5-Close) |
| **batch** | `batch_remember` | Bulk memory storage — reduces MCP round-trips for session-end automation (Sprint 7) |

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

---

## 11. Session Scanner

### 11.1 Overview

The Session Scanner (`scripts/session-scanner.py`) is a standalone CLI tool that extracts knowledge from Craft Agents session files and saves it to Craft Memory. It bridges the gap between raw session data (JSONL files) and structured memory (episodic memories, facts, open loops).

**Problem**: Not all sessions trigger the SessionEnd automation. Sessions may be abandoned, interrupted, or the automation may fail. Valuable decisions, discoveries, and facts are lost.

**Solution**: A lightweight scanner that reads session metadata, filters out automation sessions, extracts user messages, classifies content using deterministic rules (no LLM tokens), and saves via REST API.

### 11.2 Architecture

```
Session Scanner (CLI)
       |
       |--- read session.jsonl (filesystem)
       |--- filter: skip active, automation, too-short sessions
       |--- extract user messages only (skip tool calls)
       |--- classify_content() -> DISCARD/EPISODIC/FACT_CANDIDATE/OPEN_LOOP
       |--- POST /api/memories (REST)
       |--- POST /api/loops (REST)
       |--- track state in .session-scanner-state.json
```

### 11.3 Key design decisions

| Decision | Rationale |
|----------|-----------|
| **Standalone CLI, not MCP tool** | Filesystem I/O doesn't belong in an MCP server. The CLI runs on-demand or via automation. |
| **Deterministic classification** | `classify_content()` uses pattern matching (no LLM). Zero cost per scan. |
| **REST API, not MCP** | The craft-memory server already exposes `/api/*` endpoints. No additional dependencies. |
| **State file tracking** | `.session-scanner-state.json` tracks processed sessions to avoid re-scans. |
| **Automation filter** | Sessions named "Memory: ..." or "Session: ..." are skipped — they contain no real user content. |

### 11.4 Classification rules

| Class | Trigger | Action | Importance |
|-------|---------|--------|------------|
| DISCARD | Content <20 chars, trivial responses ("ok", "procedi") | Skipped | 0 |
| EPISODIC (bugfix) | Keywords: bug, fix, errore, non funziona | `remember(category=bugfix)` | 8 |
| EPISODIC (decision) | Keywords: ho deciso, useremo, refactoring, migriamo | `remember(category=decision)` | 8 |
| EPISODIC (discovery) | Keywords: scoperto, trovato, identificato, emerso | `remember(category=discovery)` | 7 |
| EPISODIC (general) | Default for meaningful messages | `remember(category=note)` | 4 |
| FACT_CANDIDATE | Keywords: usa, utilizza, configurato, versione | `remember(tags=[fact-candidate])` | 6 |
| OPEN_LOOP | Keywords: da fare, todo, bloccato, pending | `POST /api/loops` | 6 |
| PROCEDURE_CANDIDATE | >=2 of "step 1/2/3/4/5" | — | 7 |

### 11.5 CLI usage

```bash
# Scan workspace (default: auresys-backend)
craft-memory scan

# Dry run (preview only)
craft-memory scan --dry-run

# Re-scan already processed sessions
craft-memory scan --force

# Verbose output
craft-memory scan --verbose

# JSON output (for scripting)
craft-memory scan --json

# Custom workspace path
craft-memory scan ~/.craft-agent/workspaces/my-workspace
```

### 11.6 Automation

The scanner runs weekly via SchedulerTick automation:

```json
{
  "name": "Memory: Weekly Session Scan",
  "cron": "0 9 * * 1",
  "timezone": "Europe/Rome",
  "actions": [
    {
      "type": "command",
      "command": "python -m craft_memory_mcp.cli scan",
      "timeout": 120000
    }
  ]
}
```

### 11.7 Real-world results (2026-05-02)

| Metric | Value |
|--------|-------|
| Total sessions scanned | **17** |
| Sessions skipped | **39** (22 automation, 13 active/short) |
| New memories saved | **199** |
| New facts saved | **8** |
| New open loops created | **7** |
| Total messages processed | **~5,000** |
| Cost (API tokens) | **$0.00** (deterministic rules only) |
| Execution time | **~5 seconds** |

### 11.8 Duplication prevention

- **State file**: `.session-scanner-state.json` tracks `session_id → memories_saved` per workspace
- **API dedup**: `POST /api/memories` uses content hash dedup — duplicates return `{"duplicate": true}` without saving
- **`--force` flag**: Re-scans everything; duplicates are silently skipped by the API
