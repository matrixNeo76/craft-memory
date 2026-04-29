"""
Craft Memory System - MCP Server
Persistent cross-session memory for Craft Agents.
Powered by FastMCP + SQLite + FTS5.

Transport modes:
  - stdio (default): for CLI and local subprocess usage
  - http:           for Craft Agents / pi (bypasses Windows stdio bug)
                    Set CRAFT_MEMORY_TRANSPORT=http to enable
                    Uses FastMCP.streamable_http_app() + uvicorn

Environment variables:
  CRAFT_MEMORY_TRANSPORT  - "http" or "stdio" (default: "http")
  CRAFT_MEMORY_HOST       - HTTP bind host (default: "127.0.0.1")
  CRAFT_MEMORY_PORT       - HTTP bind port (default: 8392)
  CRAFT_MEMORY_DB_DIR     - Database directory (default: ~/.craft-agent/memory)
  CRAFT_MEMORY_LOG_LEVEL  - Logging level (default: "info")
  CRAFT_WORKSPACE_ID      - Workspace identifier (default: "default")
"""

import os
import sys
from typing import Any

# ─── Robustness patch: make Pydantic ignore extra framework params ──
# Agent frameworks like Craft Agent / pi inject internal metadata
# (_displayName, _intent, etc.) into MCP tool call arguments. By default
# Pydantic's ArgModelBase raises a validation error on unknown fields.
# Setting extra="ignore" makes ALL tool argument models silently
# discard any field not in the function signature. This is the single
# most robust fix: one line, works for every tool, present and future.

from mcp.server.fastmcp.utilities.func_metadata import ArgModelBase
ArgModelBase.model_config["extra"] = "ignore"

# ─── Now import FastMCP (it will use the patched ArgModelBase) ───────

from mcp.server.fastmcp import FastMCP

from craft_memory_mcp.db import (
    close_open_loop as _db_close_open_loop,
    complete_session as _db_complete_session,
    create_open_loop as _db_create_open_loop,
    dedup_memories as _db_dedup_memories,
    delete_old_memories as _db_delete_old_memories,
    get_connection as _db_get_connection,
    get_facts as _db_get_facts,
    get_latest_summary as _db_get_latest_summary,
    get_recent_memory as _db_get_recent_memory,
    list_open_loops as _db_list_open_loops,
    mark_stale_loops as _db_mark_stale_loops,
    remember as _db_remember,
    register_session as _db_register_session,
    save_summary as _db_save_summary,
    search_facts as _db_search_facts,
    search_memory as _db_search_memory,
    summarize_scope as _db_summarize_scope,
    upsert_fact as _db_upsert_fact,
)

# ─── Configuration (all from env vars with sensible defaults) ────────

WORKSPACE_ID = os.environ.get(
    "CRAFT_WORKSPACE_ID",
    os.environ.get("CRAFT_WORKSPACE", "default"),
)

CRAFT_SESSION_ID = os.environ.get(
    "CRAFT_SESSION_ID",
    "unknown-session",
)

MCP_TRANSPORT = os.environ.get("CRAFT_MEMORY_TRANSPORT", "http")
MCP_HOST = os.environ.get("CRAFT_MEMORY_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("CRAFT_MEMORY_PORT", "8392"))

# ─── MCP Server ──────────────────────────────────────────────────────

mcp = FastMCP(
    "craft-memory",
    stateless_http=True,
    json_response=True,
    instructions="""Craft Memory System - Persistent cross-session memory.

USAGE PROTOCOL:
1. At session start: call get_recent_memory + list_open_loops to recover context
2. During work: call remember for important decisions/discoveries, upsert_fact for stable knowledge
3. At session end: call summarize_scope to create a handoff document
4. For search: use search_memory for keyword search across all memories

MEMORY TYPES:
- memories (episodic): decisions, discoveries, bugfixes, features, refactors, changes, notes
- facts (stable): persistent project knowledge with confidence scores
- open_loops: incomplete tasks and follow-ups that carry across sessions

IMPORTANT: Only store what has real value. Avoid noise and trivial entries.""",
)

# ─── Health check endpoint (HTTP transport only) ─────────────────────

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for monitoring and keep-alive probes."""
    from starlette.responses import JSONResponse
    try:
        conn = _get_conn()
        # Quick DB liveness check
        conn.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {e}"

    return JSONResponse({
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "craft-memory",
        "version": "0.1.0",
        "workspace": WORKSPACE_ID,
        "transport": MCP_TRANSPORT,
        "db": db_status,
    })


# Global connection (one per server instance)
_conn = None


def _get_conn():
    global _conn
    if _conn is None:
        _conn = _db_get_connection(WORKSPACE_ID)
        # Fix #8: sessions table must have a row before any memory INSERT (FK constraint)
        _db_register_session(_conn, CRAFT_SESSION_ID, WORKSPACE_ID)
    return _conn


# ─── Tool: remember ──────────────────────────────────────────────────

@mcp.tool()
def remember(
    content: str,
    category: str = "note",
    scope: str = "workspace",
    importance: int = 5,
    source_session: str | None = None,
) -> str:
    """Store a new episodic memory (decision, discovery, bugfix, feature, refactor, change, note).

    Args:
        content: The memory content to store
        category: Type of memory - decision, discovery, bugfix, feature, refactor, change, note
        scope: Memory scope (default: workspace)
        importance: Priority 1-10 (default: 5)
        source_session: Session ID that created this memory

    Returns:
        Confirmation with memory ID or duplicate notice
    """
    conn = _get_conn()
    session_id = source_session or CRAFT_SESSION_ID
    mem_id = _db_remember(
        conn, session_id, WORKSPACE_ID, content,
        category, importance, scope, session_id,
    )
    if mem_id is None:
        return f"Duplicate memory skipped (same content already stored in this session)"
    return f"Memory #{mem_id} stored: [{category}] (importance={importance})"


# ─── Tool: search_memory ─────────────────────────────────────────────

@mcp.tool()
def search_memory(
    query: str,
    scope: str | None = None,
    limit: int = 20,
) -> str:
    """Search memories using full-text search. Returns matching memories with IDs.

    Args:
        query: Search query (keywords, phrases)
        scope: Filter by scope (default: all)
        limit: Max results (default: 20)

    Returns:
        List of matching memories
    """
    conn = _get_conn()
    results = _db_search_memory(conn, query, WORKSPACE_ID, scope, limit)
    if not results:
        return "No memories found matching your query."

    lines = [f"Found {len(results)} memories:\n"]
    for r in results:
        lines.append(
            f"#{r['id']} [{r['category']}] importance={r['importance']} "
            f"({r['created_at'][:10]})\n"
            f"  {r['content'][:200]}"
        )
    return "\n\n".join(lines)


# ─── Tool: get_recent_memory ─────────────────────────────────────────

@mcp.tool()
def get_recent_memory(
    scope: str | None = None,
    limit: int = 10,
) -> str:
    """Get most recent memories, ordered by creation time. Use at session start.

    Args:
        scope: Filter by scope (default: all)
        limit: Max results (default: 10)

    Returns:
        List of recent memories
    """
    conn = _get_conn()
    results = _db_get_recent_memory(conn, WORKSPACE_ID, scope, limit)
    if not results:
        return "No memories found for this workspace."

    lines = [f"Recent {len(results)} memories:\n"]
    for r in results:
        lines.append(
            f"#{r['id']} [{r['category']}] importance={r['importance']} "
            f"({r['created_at'][:10]})\n"
            f"  {r['content'][:200]}"
        )
    return "\n\n".join(lines)


# ─── Tool: upsert_fact ───────────────────────────────────────────────

@mcp.tool()
def upsert_fact(
    key: str,
    value: str,
    scope: str = "workspace",
    confidence: float = 1.0,
) -> str:
    """Store or update a stable fact about the project. Use for confirmed knowledge.

    Args:
        key: Fact identifier (e.g., 'tech_stack', 'db_url', 'auth_provider')
        value: Fact value
        scope: Fact scope (default: workspace)
        confidence: Confidence level 0.0-1.0 (default: 1.0)

    Returns:
        Confirmation with fact ID
    """
    conn = _get_conn()
    fact_id = _db_upsert_fact(
        conn, key, value, WORKSPACE_ID, scope, confidence, CRAFT_SESSION_ID,
    )

    # Also show current facts for context
    all_facts = _db_get_facts(conn, WORKSPACE_ID, scope if scope != "workspace" else None)
    fact_lines = [f"  {f['key']}: {f['value']} (confidence={f['confidence']})" for f in all_facts]

    return f"Fact #{fact_id} upserted: {key} = {value}\n\nCurrent facts:\n" + "\n".join(fact_lines)


# ─── Tool: list_open_loops ───────────────────────────────────────────

@mcp.tool()
def list_open_loops(
    scope: str | None = None,
) -> str:
    """List open loops (incomplete tasks, follow-ups). Use at session start.

    Args:
        scope: Filter by scope (default: all)

    Returns:
        List of open loops sorted by priority
    """
    conn = _get_conn()
    results = _db_list_open_loops(conn, WORKSPACE_ID, scope, status="open")
    if not results:
        return "No open loops found."

    lines = [f"Open loops ({len(results)}):\n"]
    for r in results:
        lines.append(
            f"#{r['id']} [{r['priority']}] {r['title']}\n"
            f"  {r.get('description', '')[:200] or '(no description)'}\n"
            f"  Created: {r['created_at'][:10]}"
        )
    return "\n\n".join(lines)


# ─── Tool: close_open_loop ───────────────────────────────────────────

@mcp.tool()
def close_open_loop(
    id: int,
    resolution: str | None = None,
) -> str:
    """Close an open loop with an optional resolution.

    Args:
        id: Loop ID to close
        resolution: How the loop was resolved

    Returns:
        Confirmation or not-found notice
    """
    conn = _get_conn()
    success = _db_close_open_loop(conn, id, resolution)
    if success:
        return f"Loop #{id} closed." + (f" Resolution: {resolution}" if resolution else "")
    return f"Loop #{id} not found or already closed."


# ─── Tool: summarize_scope ───────────────────────────────────────────

@mcp.tool()
def summarize_scope(
    scope: str = "workspace",
) -> str:
    """Generate a comprehensive summary of a scope. Use at session end for handoff.

    Args:
        scope: Scope to summarize (default: workspace)

    Returns:
        Structured summary with recent memories, facts, and open loops
    """
    conn = _get_conn()
    result = _db_summarize_scope(conn, WORKSPACE_ID, scope)

    lines = [
        f"=== Memory Summary: {result['workspace_id']} / {result['scope']} ===\n",
        f"Stats: {result['memory_count']} memories, {result['fact_count']} facts, "
        f"{result['open_loop_count']} open loops\n",
    ]

    if result["latest_summary"]:
        s = result["latest_summary"]
        lines.append("--- Latest Session Summary ---")
        if s.get("summary"):
            lines.append(f"Summary: {s['summary']}")
        if s.get("next_steps"):
            lines.append(f"Next steps: {s['next_steps']}")
        lines.append("")

    if result["facts"]:
        lines.append("--- Facts ---")
        for f in result["facts"]:
            lines.append(f"  {f['key']}: {f['value']} (confidence={f['confidence']})")
        lines.append("")

    if result["open_loops"]:
        lines.append("--- Open Loops ---")
        for l in result["open_loops"]:
            lines.append(f"  #{l['id']} [{l['priority']}] {l['title']}")
        lines.append("")

    if result["recent_memories"]:
        lines.append("--- Recent Memories ---")
        for m in result["recent_memories"][:10]:
            lines.append(
                f"  #{m['id']} [{m['category']}] importance={m['importance']} "
                f"({m['created_at'][:10]}): {m['content'][:150]}"
            )

    return "\n".join(lines)


# ─── Entry Point (called by CLI or directly) ─────────────────────────

def run_server():
    """Start the MCP server with the configured transport."""
    if MCP_TRANSPORT == "http":
        import uvicorn
        print(f"[craft-memory] v0.1.0 HTTP server on http://{MCP_HOST}:{MCP_PORT}/mcp", flush=True)
        print(f"[craft-memory] Health: http://{MCP_HOST}:{MCP_PORT}/health", flush=True)
        print(f"[craft-memory] Workspace: {WORKSPACE_ID}", flush=True)
        app = mcp.streamable_http_app()
        uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
    else:
        print(f"[craft-memory] v0.1.0 stdio server (workspace: {WORKSPACE_ID})", flush=True)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
