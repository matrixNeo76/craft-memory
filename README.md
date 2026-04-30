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
| **Local-first** | All data stays on your machine, no cloud sync, zero external dependencies |

---

## MCP Tools

| Tool | Purpose |
|------|---------|
| `remember(content, category, scope, importance, tags)` | Save an episodic memory. Categories: `decision`, `discovery`, `bugfix`, `feature`, `refactor`, `change`, `note` |
| `update_memory(id, content, category, importance)` | Update an existing memory's content, category, or importance |
| `search_memory(query, scope, limit)` | Full-text search over all memories (FTS5 + BM25 hybrid ranking) |
| `search_by_tag(tag, scope, limit)` | Find memories by tag |
| `get_recent_memory(scope, limit, max_tokens)` | Get memories ranked by importance decay; `max_tokens` caps the context budget |
| `upsert_fact(key, value, scope, confidence)` | Save or update a stable fact. Idempotent. |
| `list_open_loops(scope)` | List open tasks ordered by priority (critical → high → medium → low) |
| `add_open_loop(title, description, priority, scope)` | Create a new open loop to track across sessions |
| `close_open_loop(id, resolution)` | Close a loop with an optional resolution note |
| `summarize_scope(scope)` | Generate a full snapshot: memories + facts + loops + latest summary |
| `save_summary(summary, decisions, facts_learned, open_loops, refs, next_steps)` | Save a structured session handoff document |
| `run_maintenance()` | Cleanup old memories, trim summaries, dedup, VACUUM |
| `link_memories(source_id, target_id, relation, confidence_type, confidence_score)` | Create a directed edge between two memories in the knowledge graph |
| `get_relations(memory_id, direction)` | Get graph neighbors of a memory (`in`, `out`, or `both`) |
| `find_similar(memory_id, top_n, auto_link)` | Find semantically similar memories via FTS5 BM25; optionally auto-links results as INFERRED edges |
| `god_facts(top_n)` | Return the N most impactful facts with `god_score`, `mention_count`, `confidence_type` |
| `memory_diff(since_epoch)` | Return changes since a Unix timestamp: new memories, updated facts, new/closed loops |

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
│   │   ├── server.py        # FastMCP server, 12 tools, health check
│   │   ├── db.py            # SQLite layer (WAL, FTS5, dedup, decay)
│   │   ├── schema.sql       # 6 tables + FTS virtual table + triggers
│   │   ├── migrations/      # Versioned SQL migrations (applied on startup)
│   │   │   ├── 001_global_dedup.sql
│   │   │   ├── 002_global_dedup.sql
│   │   │   ├── 003_tags.sql
│   │   │   └── 004_relations.sql  # knowledge graph: memory_relations + confidence_type
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
├── tests/                   # pytest suite (42 tests: core + graph layer)
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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
