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
| **Episodic memory** | Save decisions, discoveries, bugfixes with category and importance |
| **Stable facts** | Key-value store for confirmed project knowledge (tech stack, URLs, conventions) |
| **Open loops** | Track incomplete tasks across sessions with priority levels |
| **Full-text search** | FTS5 with BM25 ranking and Porter stemmer |
| **Auto-deduplication** | Content hash prevents duplicate memories |
| **Session summaries** | Structured handoff documents between sessions |
| **4 automations** | SessionStart, SessionEnd, SchedulerTick, LabelAdd — all pre-configured |
| **4 skills** | memory-protocol, memory-start, memory-maintenance, session-handoff |
| **Local-first** | All data stays on your machine, no cloud sync |

---

## MCP Tools

| Tool | Purpose |
|------|---------|
| `remember(content, category, scope, importance)` | Save an episodic memory. Categories: `decision`, `discovery`, `bugfix`, `feature`, `refactor`, `change`, `note` |
| `search_memory(query, scope, limit)` | Full-text search over all memories (FTS5 + BM25) |
| `get_recent_memory(scope, limit)` | Get the N most recent memories |
| `upsert_fact(key, value, scope, confidence)` | Save or update a stable fact. Idempotent. |
| `list_open_loops(scope)` | List open tasks ordered by priority (critical → high → medium → low) |
| `close_open_loop(id, resolution)` | Close a loop with an optional resolution note |
| `summarize_scope(scope)` | Generate a full snapshot: memories + facts + loops + latest summary |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CRAFT_MEMORY_TRANSPORT` | `stdio` | Transport mode: `http` or `stdio` |
| `CRAFT_MEMORY_HOST` | `127.0.0.1` | HTTP server bind address |
| `CRAFT_MEMORY_PORT` | `8392` | HTTP server port |
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
craft-memory serve  # default transport
```

Use stdio for local testing or on macOS/Linux where stdio works reliably.

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
│   │   ├── server.py        # FastMCP server, 7 tools, health check
│   │   ├── db.py            # SQLite layer (WAL, FTS5, dedup)
│   │   ├── schema.sql       # 5 tables + FTS virtual table
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
│   └── adr/                 # Architecture Decision Records
├── tests/                   # pytest suite (Phase 5)
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
