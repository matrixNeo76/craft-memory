# Craft Memory

[![Tests](https://github.com/matrixNeo76/craft-memory/actions/workflows/test.yml/badge.svg)](https://github.com/matrixNeo76/craft-memory/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/craft-memory-mcp.svg)](https://pypi.org/project/craft-memory-mcp/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://pypi.org/project/craft-memory-mcp/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

> Persistent cross-session memory for [Craft Agents](https://craft.do/agents). Built on FastMCP + SQLite + FTS5.

Without memory, every AI session starts from zero. Craft Memory gives your agent a long-term, local memory that survives session restarts, model switches, and provider changes.

---

## Why

Craft Agents are powerful but stateless by default. Each new session loses context from the previous one — decisions made, bugs fixed, code patterns discovered. Craft Memory solves this with a persistent SQLite database exposed as an MCP server, fully integrated with the Craft Agents automation system.

**What you get:**
- Episodic memories saved during work, recalled on the next session
- Stable facts (tech stack, API keys, conventions) that never expire
- Open loops — tasks tracked across sessions until resolved
- Session summaries for clean handoffs between models/providers
- Full-text search over all stored knowledge

---

## Quick Start

**Step 1 — Install**

```bash
git clone https://github.com/your-org/craft-memory.git ~/craft-memory
cd ~/craft-memory
pip install -e .
```

**Step 2 — Install into your Craft Agents workspace**

```bash
craft-memory install --workspace ~/.craft-agent/workspaces/YOUR_WS_ID
```

This copies `config.json`, `permissions.json`, `guide.md`, and all 4 skills into your workspace.

**Step 3 — Start the server**

```bash
craft-memory ensure
# → OK: Craft Memory server running on port 8392
```

The SessionStart automation will run `craft-memory ensure` automatically at the start of every session.

---

## Quick Path

Five tools cover 90% of daily use:

```
Session start  → get_recent_memory + list_open_loops
During work    → remember (decisions) + upsert_fact (stable knowledge)
Search         → search_memory
```

Everything else — graph relationships, procedure tracking, multi-hop context, batch ops — is available but optional. Tools are grouped into **core**, **graph**, **procedures**, **facts**, **batch**, and **admin** in the [guide](sources/memory/guide.md) and docstrings.

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    Craft Agents                          │
│                                                          │
│  SessionStart    SessionEnd    SchedulerTick   LabelAdd  │
│  (auto-start +  (save handoff)  (daily 3:00)  (promote) │
│   recall ctx)                                            │
│       │              │              │              │      │
│       └──────────────┴──────────────┴──────────────┘     │
│                             │                            │
│                    Memory Source (HTTP MCP)               │
│                    localhost:8392/mcp                    │
└─────────────────────────────┼────────────────────────────┘
                              │ HTTP
┌─────────────────────────────▼────────────────────────────┐
│              Craft Memory Server (Python)                 │
│         FastMCP 1.26.0 · stateless HTTP · uvicorn         │
│                             │                            │
│       ~/.craft-agent/memory/{workspaceId}.db             │
│       SQLite 3 · WAL mode · FTS5 full-text search        │
└──────────────────────────────────────────────────────────┘
```

**Session lifecycle:**

1. **Session starts** → automation runs `craft-memory ensure` (starts server if down), then calls `get_recent_memory` + `list_open_loops` to recover context
2. **During work** → agent calls `remember`, `upsert_fact`, `search_memory` as needed
3. **Session ends** → automation saves decisions, discoveries, updates facts, generates handoff summary
4. **Daily at 03:00** → SchedulerTick automation consolidates memories, promotes stable knowledge to facts, closes stale loops

---

## Features

| Feature | Description |
|---------|-------------|
| **Episodic memory** | Save decisions, discoveries, bugfixes with category, importance, and optional tags |
| **Stable facts** | Key-value store for confirmed project knowledge with confidence scores |
| **Open loops** | Track incomplete tasks across sessions with priority levels (critical → low) |
| **Hybrid FTS search** | FTS5 + BM25 × 0.7 + importance × 0.3 ranking; LIKE fallback for edge cases |
| **Global deduplication** | Content hash unique per workspace — no duplicate across any session |
| **Importance decay** | `effective_importance = importance × e^(-λ × age_days)` — older memories rank lower |
| **Tags on memories** | Attach tags for topic-based retrieval via `search_by_tag` |
| **Privacy stripping** | `<private>`, `<system-reminder>`, `<system>` blocks stripped before storage |
| **Session summaries** | Structured handoff: decisions, facts learned, open loops, refs, next steps |
| **Migration runner** | Versioned SQL migrations applied automatically on startup |
| **4 automations** | SessionStart, SessionEnd, SchedulerTick, LabelAdd — all pre-configured |
| **4 skills** | memory-protocol, memory-start, memory-maintenance, session-handoff |
| **Knowledge graph** | Directed edges between memories (`link_memories`) with typed relations: caused_by, contradicts, extends, implements, supersedes, semantically_similar_to |
| **Confidence labels** | Facts and graph edges carry `confidence_type`: `extracted` (observed directly), `inferred` (derived), `ambiguous` (uncertain) |
| **god_facts** | Top N most impactful facts ranked by `confidence × type_bonus × (1 + mention_count × 0.2)` — the most load-bearing knowledge at a glance |
| **memory_diff** | Delta since a Unix timestamp: new memories, updated facts, opened/closed loops — ideal for session catch-up |
| **Semantic similarity** | `find_similar` uses FTS5 BM25 to find related memories; `auto_link=True` auto-creates INFERRED graph edges |
| **RRF hybrid search** | `search_memory` fuses FTS5 BM25 + Jaccard word-overlap via Reciprocal Rank Fusion `1/(k+rank)` — no embeddings needed; +6-8% accuracy over linear weighting |
| **Core memory promotion** | `promote_to_core` marks a memory `is_core=1` — immune to exponential decay; `find_consolidation_candidates` surfaces non-core memories ready for pruning |
| **Hyperedge roles** | Graph edges carry semantic `role` (core/context/detail/temporal/causal) and `weight` (0–1); `get_relations_by_role` for selective graph traversal |
| **Local-first** | All data stays on your machine, no cloud sync, zero external dependencies |
| **Observability** | `memory_stats` (aggregate counts), `generate_handoff` (auto structured handoff), `save_decision_record` (decision log with rationale) |
| **Temporal lifecycle** | Memories carry `lifecycle_status` (`active / superseded / invalidated / needs_review`); `valid_from / valid_to` fields; full supersession chain via `superseded_by` FK |
| **Boundary detection** | `classify_event` classifies any content into `DISCARD / EPISODIC / FACT_CANDIDATE / OPEN_LOOP / PROCEDURE_CANDIDATE / CORE_CANDIDATE` before storage |
| **Procedural memory** | `procedures` table with `UNIQUE(workspace_id, name)` upsert; FTS5 porter index; trigger context + markdown steps + confidence; `save_procedure`, `search_procedures`, `get_applicable_procedures` |
| **Scope hierarchy** | `scope_hierarchy` table: `session < project < workspace < user < global`; `get_scope_ancestors()` traverses the chain for coarse-to-fine fallback |
| **Coarse-to-fine retrieval** | 3-layer pattern: Layer 1 = `search_memory` (FTS5 snippets), Layer 2 = `get_recent_memory` + `get_relations` (context), Layer 3 = `get_memory_bundle` (full batch fetch by IDs) |
| **Exposed utility tools** | `search_facts` (keyword search on key/value), `list_procedures` (by status), `get_scope_ancestors` (chain from specific to broad), `consolidation_candidates` (pruning candidates) — previously internal, now full MCP tools |
| **Procedure outcome tracking** | `record_procedure_outcome` saves success/partial/failure results per procedure; `get_procedure_outcomes` returns history newest-first |
| **Bayesian confidence evolution** | `daily_maintenance` updates procedure confidence via `new = clamp(old×0.3 + avg_score×0.7, 0.05, 0.95)` using the last N outcomes; outcome scores: success=1.0, partial=0.5, failure=0.0 |
| **Multi-hop graph context** | `get_graph_context` BFS traversal up to N hops: returns center memory + all reachable nodes/edges + `depth_map`; inbound + outbound traversal, cycle-safe via visited set |
| **Batch memory save** | `batch_remember` saves N memories in one MCP call (JSON array input); duplicates return `None` in that slot without error; reduces round-trips in session-end automations |
| **Procedure ranking** | `top_procedures` ranks active procedures by `confidence × success_rate × use_count` — shows which workflows are actually delivering value |
| **Memory consolidation** | `consolidate_memories` combines low-value memories into a procedure in one call; `confirm=False` dry-run, `confirm=True` executes; all invalidations are soft (reversible) |
| **Session quality scoring** | `rate_session` assigns a `quality_score` (0.0–1.0) to any session summary; feeds `get_high_quality_sessions` and `export_session_traces` |
| **SessionDB** | `get_high_quality_sessions` and `export_session_traces` (JSONL) provide the data bridge for self-improvement loops, fine-tuning, and evaluation datasets (Hermes/GEPA pattern) |
| **Prometheus metrics** | `GET /metrics` exposes memories, facts, open loops, procedures, avg confidence, db_size in Prometheus text format — Grafana-ready without MCP overhead |

---

## MCP Tools

| Tool | Purpose |
|------|---------|
| `remember(content, category, scope, importance, tags)` | Save an episodic memory. Categories: `decision`, `discovery`, `bugfix`, `feature`, `refactor`, `change`, `note` |
| `update_memory(id, content, category, importance)` | Update an existing memory's content, category, or importance |
| `search_memory(query, scope, limit, use_rrf)` | RRF hybrid search: FTS5 BM25 + Jaccard word-overlap fused via Reciprocal Rank Fusion; `use_rrf=False` falls back to linear BM25 |
| `search_by_tag(tag, scope, limit)` | Find memories by tag |
| `get_recent_memory(scope, limit, max_tokens)` | Get memories ranked by importance decay; `max_tokens` caps the context budget |
| `upsert_fact(key, value, scope, confidence)` | Save or update a stable fact. Idempotent. |
| `list_open_loops(scope)` | List open tasks ordered by priority (critical → high → medium → low) |
| `add_open_loop(title, description, priority, scope)` | Create a new open loop to track across sessions |
| `close_open_loop(id, resolution)` | Close a loop with an optional resolution note |
| `update_open_loop(id, title, description, priority, status)` | Update fields on an existing open loop; validates priority/status enums |
| `summarize_scope(scope)` | Generate a full snapshot: memories + facts + loops + latest summary |
| `save_summary(summary, decisions, facts_learned, open_loops, refs, next_steps)` | Save a structured session handoff document |
| `run_maintenance()` | Cleanup old memories, trim summaries, dedup, VACUUM |
| `promote_to_core(id)` | Mark a memory as core (`is_core=1`) — immune to importance decay |
| `link_memories(source_id, target_id, relation, confidence_type, confidence_score, role, weight)` | Create a directed edge; `role` classifies semantic type (core/context/detail/temporal/causal), `weight` sets traversal priority |
| `get_relations(memory_id, direction)` | Get graph neighbors of a memory (`in`, `out`, or `both`) |
| `find_similar(memory_id, top_n, auto_link)` | Find semantically similar memories via FTS5 BM25; optionally auto-links results as INFERRED edges |
| `god_facts(top_n)` | Return the N most impactful facts with `god_score`, `mention_count`, `confidence_type` |
| `memory_diff(since_epoch)` | Return changes since a Unix timestamp: new memories, updated facts, new/closed loops |
| **— Sprint 1: Observability —** | |
| `memory_stats()` | Aggregate counts: memories by category/scope, is_core, lifecycle_status, open loops, facts, procedures |
| `generate_handoff(limit)` | Auto-generate a structured markdown handoff from recent memories, open loops, and facts |
| `save_decision_record(title, decision, options, rationale, outcome)` | Store a decision log entry as a tagged memory with structured metadata |
| **— Sprint 2: Temporal Lifecycle —** | |
| `invalidate_memory(memory_id, reason)` | Mark a memory as `invalidated` with a reason |
| `get_memory_history(memory_id)` | Return the full supersession chain for a memory (follows `superseded_by` links) |
| `flag_for_review(memory_id, reason)` | Mark a memory as `needs_review` |
| `list_needs_review(limit)` | List memories awaiting review |
| `approve_memory(memory_id)` | Restore a `needs_review` memory to `active` status |
| **— Sprint 3: Boundary Detection —** | |
| `classify_event(content, importance, category)` | Classify content into a MemoryClass before deciding how to store it |
| **— Sprint 4: Procedural Memory —** | |
| `save_procedure(name, trigger_context, steps_md, confidence)` | Upsert a named procedure. Idempotent by name within workspace. |
| `search_procedures(query, limit)` | FTS5 porter search over procedures (name + trigger + steps) |
| `get_applicable_procedures(current_context, limit)` | Find the most relevant procedures for the current task |
| **— Sprint 5: Scope Hierarchy + Retrieval —** | |
| `get_memory_bundle(memory_ids)` | Batch-fetch N complete memories by ID list. Layer 3 of coarse-to-fine retrieval. |
| **— Sprint 5-Close: Expose Utility Tools —** | |
| `search_facts(query, scope, limit)` | Keyword search on facts key or value; scope-filterable; ordered by confidence desc |
| `list_procedures(status, limit)` | List all procedures in workspace filtered by status (`active`/`draft`/`deprecated`) |
| `get_scope_ancestors(scope)` | Return scope + full ancestor chain from specific to broad (session → global) |
| `consolidation_candidates(importance_threshold, age_days, limit)` | Find old non-core memories with low effective importance ready for pruning |
| **— Sprint 6: Procedure Outcome Tracking —** | |
| `record_procedure_outcome(procedure_id, outcome, notes)` | Record execution result (`success`/`partial`/`failure`) for a procedure; triggers confidence evolution |
| `get_procedure_outcomes(procedure_id, limit)` | Return recent execution outcomes for a procedure, newest first |
| **— Sprint 7: Graph Context + Batch Ops —** | |
| `get_graph_context(memory_id, depth)` | BFS multi-hop traversal: return center memory + neighbors up to N hops with edges and `depth_map` |
| `batch_remember(entries_json)` | Save N memories in one call (JSON array); duplicates return `None` without error; reduces round-trips |
| **— Sprint 8: Procedure Intelligence + Session Quality —** | |
| `top_procedures(limit)` | Rank procedures by `confidence × success_rate × use_count`; simmetrico di `god_facts` for procedures |
| `consolidate_memories(candidate_ids_json, procedure_name, trigger_context, steps_md, confirm)` | Combine low-value memories into a procedure; `confirm=False` is dry-run (safe), `confirm=True` executes |
| `rate_session(summary_id, score, notes)` | Assign quality score 0.0–1.0 to a session summary for SessionDB |
| **— Sprint 9: SessionDB Foundation —** | |
| `get_high_quality_sessions(min_score, limit)` | Return session summaries scored >= min_score; positive examples for self-improvement |
| `export_session_traces(min_score, limit)` | Export rated sessions as JSONL for training, eval, or DSPy optimization |

**HTTP Endpoints** (not MCP tools — direct HTTP):
| Endpoint | Purpose |
|----------|---------|
| `GET /health` | JSON health check: status, db, version, workspace, db_size_mb |
| `GET /metrics` | Prometheus text format: memories, facts, loops, procedures, avg confidence, db_size |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CRAFT_MEMORY_TRANSPORT` | `http` | Transport mode: `http` or `stdio` |
| `CRAFT_MEMORY_HOST` | `127.0.0.1` | HTTP server bind address |
| `CRAFT_MEMORY_PORT` | `8392` | HTTP server port |
| `CRAFT_MEMORY_DB_DIR` | `~/.craft-agent/memory` | Directory for database files |
| `CRAFT_MEMORY_DECAY_LAMBDA` | `0.005` | Importance decay rate λ (higher = faster decay) |
| `CRAFT_WORKSPACE_ID` | `default` | Workspace ID (determines which `.db` file to use) |
| `CRAFT_SESSION_ID` | `session_{timestamp}` | Session ID injected by Craft Agents |
| `CRAFT_MEMORY_HOME` | `~/craft-memory` | Path to the craft-memory installation |
| `CRAFT_MEMORY_PYTHON` | `sys.executable` | Python interpreter for subprocess launch |

### Database Location

```
~/.craft-agent/memory/{workspaceId}.db
```

Each workspace gets its own isolated database.

---

## Transport Modes

### HTTP (recommended)

```bash
CRAFT_MEMORY_TRANSPORT=http craft-memory serve
# or
craft-memory ensure  # auto-starts if not running
```

The MCP source connects to `http://localhost:8392/mcp`.

**Why HTTP instead of stdio?** On Windows, the MCP stdio transport disconnects after ~4 seconds due to a known bug in the MCP SDK. HTTP is more robust and keeps the server alive independently of any session.

### stdio

```bash
CRAFT_MEMORY_TRANSPORT=stdio craft-memory serve
```

Use stdio for local testing or when HTTP is not needed. Note: on Windows, the MCP stdio transport may disconnect after a few seconds due to a known SDK issue — HTTP is preferred.

---

## CLI Reference

```bash
craft-memory ensure      # Start server if not running (used in automations)
craft-memory serve       # Start server in foreground
craft-memory check       # Check if server is running (exit 0=up, 2=down)
craft-memory stop        # Stop the running server
craft-memory status      # Print server status as JSON
craft-memory install --workspace PATH   # Install source into a workspace
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "Not connected" / connection refused | HTTP server not running | Run `craft-memory ensure` |
| Tools not available in session | Source not enabled | Add `"memory"` to `enabledSourceSlugs` in workspace config |
| Automations fail silently | `permissionMode` not set | Set `"permissionMode": "allow-all"` on all 4 automations |
| `remember()` returns "Duplicate" on first call | FK violation (sessions table empty) | Fixed in v0.1.0 — update if on older version |
| `Session not found` after server restart | Stateful HTTP sessions | Fixed in v0.1.0 — uses `stateless_http=True` |

---

## Project Structure

```
craft-memory/
├── src/
│   ├── craft_memory_mcp/    # Canonical package (installed by pip)
│   │   ├── server.py        # FastMCP server, 46 tools, /health + /metrics endpoints
│   │   ├── db.py            # SQLite layer (WAL, FTS5, dedup, decay)
│   │   ├── schema.sql       # 6 tables + FTS virtual table + triggers
│   │   ├── migrations/      # Versioned SQL migrations (applied on startup)
│   │   │   ├── 002_global_dedup.sql
│   │   │   ├── 003_tags.sql
│   │   │   ├── 004_relations.sql       # knowledge graph: memory_relations + confidence_type
│   │   │   ├── 005_core_promotion.sql  # is_core flag + consolidated_from column
│   │   │   ├── 006_relation_roles.sql  # hyperedge role + weight on memory_relations
│   │   │   ├── 007_edge_manual_flag.sql
│   │   │   ├── 008_fact_temporal.sql   # lifecycle status + temporal fields
│   │   │   ├── 009_procedures.sql      # procedural memory + FTS5 index
│   │   │   ├── 010_scope_hierarchy.sql # scope hierarchy (session→global)
│   │   │   ├── 011_procedure_outcomes.sql # procedure execution outcomes + confidence evolution
│   │   │   └── 012_session_quality.sql    # quality_score + quality_notes on session_summaries (SessionDB)
│   │   └── cli.py           # craft-memory CLI
│   ├── server.py            # Shim → craft_memory_mcp.server
│   └── db.py                # Shim → craft_memory_mcp.db
├── scripts/
│   └── ensure-running.py    # Server lifecycle manager
├── skills/                  # Craft Agents skills (copied on install)
│   ├── memory-protocol/
│   ├── memory-start/
│   ├── memory-maintenance/
│   └── session-handoff/
├── docs/
│   └── adr/                 # Architecture Decision Records (ADR-001 → ADR-008)
├── tests/                   # pytest suite (209 tests: core, graph, observability, temporal, policy, procedures, scopes, exposed-tools, procedure-outcomes, graph-context, batch, top-procedures, consolidate, session-quality)
├── pyproject.toml
└── ARCHITECTURE.md
```

---

## Requirements

- Python 3.11+
- SQLite 3 with FTS5 (included in Python stdlib)
- [Craft Agents](https://craft.do/agents) (pi)
- FastMCP >= 1.26.0
- uvicorn >= 0.30.0

---

## Stability-First Mode

This system prioritizes **precision, explainability, and safety** over aggressive automation:

| Concern | Default behavior |
|---------|-----------------|
| Graph auto-links | Only created when BM25 score < -2.5 (strict). Configurable via `CRAFT_MEMORY_AUTOLINK_THRESHOLD`. |
| Inferred edge pruning | Edges with weight < 0.3 AND age > 60d are removed by `run_maintenance`. |
| Core promotion | Always requires explicit decision. Never runs automatically. |
| Loop close / fact promotion | Never automatic. Always human or explicit agent instruction. |

After collecting real usage data (via `inferred_edges_pruned` / `auto_links_created` in maintenance logs), thresholds can be relaxed. See [ARCHITECTURE.md §10.3](ARCHITECTURE.md#103-stability-first-mode) for tuning guidance.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
