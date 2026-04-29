# ADR-001: HTTP Transport Instead of stdio

**Status:** Accepted  
**Date:** 2026-04-28  

---

## Context

MCP servers can run with two transport mechanisms: stdio (subprocess with stdin/stdout pipes) or HTTP (Streamable HTTP on a local port).

The default for local MCP servers is stdio, which is simpler — no port management, no HTTP overhead, the server process lives and dies with the client session.

However, on Windows, the MCP SDK has a known bug: the stdio transport disconnects after approximately 4 seconds. Subsequent tool calls from the same session fail with "Not connected". This makes stdio unreliable for Craft Agents on Windows.

Additionally, a persistent memory server has different lifecycle requirements than a typical MCP tool: it should stay alive between sessions, not restart on every session open.

---

## Decision

Use HTTP transport (Streamable HTTP on `localhost:8392`) instead of stdio.

The server runs as a background process, independent of any Craft Agents session. The MCP source connects via `http://localhost:8392/mcp`.

A lifecycle manager script (`scripts/ensure-running.py`, exposed as `craft-memory ensure`) handles process management: check if the server is up, start it if not.

---

## Consequences

**Positive:**
- Works reliably on Windows (stdio bug avoided)
- Server stays alive between sessions — no cold-start latency
- Health check endpoint (`GET /health`) enables reliable status checking
- Multiple sessions can share the same server instance

**Negative:**
- Port 8392 must be free (conflict risk if something else uses it)
- Server must be started before tool calls — the SessionStart automation handles this
- Process management complexity (ensure-running, stop, status commands)
- On macOS/Linux, stdio would work fine — HTTP adds unnecessary complexity for those users

**Mitigations:**
- `craft-memory ensure` is idempotent — safe to call even if server is already running
- The SessionStart automation guarantees the server is up before any tool call
- Port is configurable via `CRAFT_MEMORY_PORT` environment variable
