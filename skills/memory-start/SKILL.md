---
name: "Memory Start"
description: "Start or verify the Craft Memory HTTP server. Use when memory tools fail with connection errors, when starting a new session, or when asked to 'start memory', 'check memory', or 'memory status'."
requiredSources:
  - memory
---

# Memory Start

This skill manages the Craft Memory HTTP server lifecycle. Use it whenever memory tools are unavailable or you need to verify the server status.

## Quick Commands

| What | Command |
|------|---------|
| **Ensure running** (start if down) | `craft-memory ensure` |
| **Check status only** | `craft-memory check` |
| **Detailed status** | `craft-memory status` |
| **Stop server** | `craft-memory stop` |

## When to Use

- **Session start**: Run `craft-memory check`. If down, run `craft-memory ensure`.
- **Tool call fails** with connection error: Run `craft-memory ensure`, then retry.
- **User asks "start memory"**: Run `craft-memory ensure`.
- **User asks "memory status"**: Run `craft-memory status`.

## Procedure

### Step 1: Check if server is running

```bash
craft-memory check
```

If output is `OK: ...already running`, skip to Step 3.

### Step 2: Start if needed

```bash
craft-memory ensure
```

Wait for `OK: Craft Memory server is ready`. If it fails, report the error to the user.

### Step 3: Verify with a tool call

Call `get_recent_memory(limit=1)` to confirm the MCP connection works end-to-end.

## Server Details

- **Endpoint**: `http://127.0.0.1:8392/mcp`
- **Health check**: `http://127.0.0.1:8392/health`
- **Transport**: HTTP Streamable (FastMCP 1.26.0)
- **Process**: Runs detached in background, survives shell closure
- **Data**: `~/.craft-agent/memory/{workspaceId}.db`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `craft-memory ensure` exits with error | Package not installed. Run: `pip install craft-memory-mcp` |
| Server starts but health check fails | Port 8392 may be in use. Check with `craft-memory status`. |
| Tool calls still fail after start | The source may need re-activation in workspace settings. |
