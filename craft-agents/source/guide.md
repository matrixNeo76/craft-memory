# Craft Memory

Persistent cross-session memory for Craft Agents. Uses SQLite + FTS5 for local storage and full-text search.

## Transport

The MCP server runs in **HTTP** mode on `http://localhost:8392/mcp`.

- **Health check**: `GET http://localhost:8392/health`
- **Start**: `craft-memory ensure`
- **If the server is down**: tools will fail with connection errors. Run `craft-memory ensure` before using the source.

> **Windows Job Object**: When Craft Agents (Electron) restarts, Windows Job Objects terminate child processes — even `DETACHED_PROCESS` ones. The automations handle this with `"type": "command"` actions that run `craft-memory ensure` deterministically before each `"type": "prompt"` action. This guarantees the server is up without relying on LLM interpretation.

## Scope

MCP source exposing 7 tools for managing episodic memory, stable facts, and open loops. Data persists in `~/.craft-agent/memory/{workspaceId}.db` and survives model/provider changes.

## Available Tools

### remember(content, category, scope, importance, source_session)

Save an episodic memory. Categories: `decision`, `discovery`, `bugfix`, `feature`, `refactor`, `change`, `note`. Importance 1–10. Automatic deduplication via content hash.

### search_memory(query, scope, limit)

Full-text search over all memories. Uses FTS5 with Porter stemmer. Returns IDs + content for filtering.

### get_recent_memory(scope, limit)

Retrieve the most recent memories. Call at session start to recover context.

### upsert_fact(key, value, scope, confidence)

Save or update a stable fact. Unique key per workspace+scope. Confidence 0–1. Upsert: updates if exists.

### list_open_loops(scope)

List open loops ordered by priority (critical > high > medium > low).

### close_open_loop(id, resolution)

Close a loop with an optional resolution note.

### summarize_scope(scope)

Generate a full summary: recent memories, facts, open loops, and the latest session summary.

## Usage Protocol

1. **Session start**: call `get_recent_memory` + `list_open_loops` to recover context
2. **During work**: call `remember` for decisions/discoveries, `upsert_fact` for stable knowledge
3. **Session end**: call `summarize_scope` for handoff + `remember` for final decisions
4. **Search**: use `search_memory` for keyword search

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "Not connected" / connection refused | HTTP server not running | Run `craft-memory ensure` |
| Tools not available in session | Source not enabled | Check `enabledSourceSlugs` in workspace config |
| Automations fail silently | `permissionMode` not set | Verify `"permissionMode": "allow-all"` on all automations |

## Guidelines

- Store only information with real, lasting value — not every minor action
- Use high importance (7–10) for architectural decisions, low (1–3) for minor notes
- Update facts when knowledge changes
- Close open loops when resolved
- Local-first: no data leaves your machine
