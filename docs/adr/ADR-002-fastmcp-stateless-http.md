# ADR-002: FastMCP with stateless_http=True and json_response=True

**Status:** Accepted  
**Date:** 2026-04-28  

---

## Context

FastMCP 1.26.0 is the MCP server framework used by Craft Memory. It supports HTTP transport via `streamable_http_app()`.

By default, `streamable_http_app()` creates **stateful sessions**: the server assigns each client a session ID and expects subsequent requests to include that ID. This works for long-running client connections but fails after server restarts — any client with a stale session ID receives `{"error": {"code": -32600, "message": "Session not found"}}`.

Since the Craft Memory server can restart (manually, after a crash, after system reboot), stateful sessions would cause frequent "Session not found" errors until the client reconnects.

Additionally, FastMCP's default HTTP response format is SSE (Server-Sent Events), which is designed for streaming. Craft Agents expects standard JSON responses from MCP tool calls.

**Important API note:** In FastMCP versions prior to 1.26.0, `http_app(stateless_http=True)` was the correct API. In 1.26.0, this method was removed. The correct API is now `streamable_http_app()` with `stateless_http=True` set in the `FastMCP()` constructor.

---

## Decision

Configure FastMCP with:

```python
mcp = FastMCP(
    "craft-memory",
    stateless_http=True,   # Each request is independent — no session state
    json_response=True,    # Return JSON instead of SSE stream
)
app = mcp.streamable_http_app()
```

Every HTTP request is self-contained. The server holds no client state between requests.

---

## Consequences

**Positive:**
- Server restarts are transparent — clients reconnect without error
- No session ID management required
- Simpler debugging (every request is identical in structure)
- JSON responses are easier to inspect and test

**Negative:**
- Cannot use server-side streaming for long-running tool calls (acceptable — all 7 tools complete quickly)
- Stateless design means no request-level context sharing between tool calls in a single "logical session" (not needed for our use case — state lives in SQLite, not in memory)

**Alternatives considered:**
- **Stateful HTTP**: Would require session cleanup logic and fail on server restart — rejected
- **SSE responses**: Craft Agents works correctly with JSON — no need for SSE complexity
