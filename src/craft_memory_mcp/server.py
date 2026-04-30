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

import json
import os
import re as _re
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path
from typing import Any

try:
    _VERSION = _pkg_version("craft-memory-mcp")
except PackageNotFoundError:
    _VERSION = "dev"

_PRIVATE_PATTERNS = _re.compile(
    r"<(private|system-reminder|system-instruction|system)>.*?</\1>",
    _re.DOTALL | _re.IGNORECASE,
)


def _strip_private(text: str) -> str:
    return _PRIVATE_PATTERNS.sub("", text).strip()

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
    daily_maintenance as _db_daily_maintenance,
    dedup_memories as _db_dedup_memories,
    delete_old_memories as _db_delete_old_memories,
    find_similar_memories as _db_find_similar_memories,
    get_connection as _db_get_connection,
    get_facts as _db_get_facts,
    get_latest_summary as _db_get_latest_summary,
    get_recent_memory as _db_get_recent_memory,
    get_relations as _db_get_relations,
    god_facts as _db_god_facts,
    link_memories as _db_link_memories,
    list_open_loops as _db_list_open_loops,
    mark_stale_loops as _db_mark_stale_loops,
    memory_diff as _db_memory_diff,
    remember as _db_remember,
    register_session as _db_register_session,
    save_summary as _db_save_summary,
    search_by_tag as _db_search_by_tag,
    search_facts as _db_search_facts,
    search_memory as _db_search_memory,
    summarize_scope as _db_summarize_scope,
    update_memory as _db_update_memory,
    update_open_loop as _db_update_open_loop,
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
        conn.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {e}"

    db_dir = Path(os.environ.get("CRAFT_MEMORY_DB_DIR", str(Path.home() / ".craft-agent/memory")))
    db_path = db_dir / f"{WORKSPACE_ID}.db"
    db_size_mb = round(db_path.stat().st_size / 1024 / 1024, 2) if db_path.exists() else 0

    return JSONResponse({
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "craft-memory",
        "version": _VERSION,
        "workspace": WORKSPACE_ID,
        "transport": MCP_TRANSPORT,
        "db": db_status,
        "db_size_mb": db_size_mb,
        "db_size_warning": db_size_mb > 100,
    })


# Global connection (one per server instance)
_conn = None

# WAL checkpoint counter — flush WAL every N writes to keep file size bounded
_write_count = 0
_CHECKPOINT_EVERY = 100


def _maybe_checkpoint(conn) -> None:
    global _write_count
    _write_count += 1
    if _write_count >= _CHECKPOINT_EVERY:
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        _write_count = 0


def _get_conn():
    global _conn
    # Ping to detect stale/corrupted connection and reset if needed
    if _conn is not None:
        try:
            _conn.execute("SELECT 1")
        except Exception:
            _conn = None
    if _conn is None:
        _conn = _db_get_connection(WORKSPACE_ID)
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
    tags: list[str] | None = None,
) -> str:
    """Store a new episodic memory (decision, discovery, bugfix, feature, refactor, change, note).

    Args:
        content: The memory content to store
        category: Type of memory - decision, discovery, bugfix, feature, refactor, change, note
        scope: Memory scope (default: workspace)
        importance: Priority 1-10 (default: 5)
        source_session: Session ID that created this memory
        tags: Optional list of tags e.g. ["auth", "deploy"]

    Returns:
        Confirmation with memory ID or duplicate notice
    """
    conn = _get_conn()
    session_id = source_session or CRAFT_SESSION_ID
    content = _strip_private(content)
    if not content:
        return "Memory skipped: content was empty after stripping private tags."
    mem_id = _db_remember(
        conn, session_id, WORKSPACE_ID, content,
        category, importance, scope, session_id, tags,
    )
    if mem_id is None:
        return "Duplicate memory skipped (same content already stored in this workspace)"
    tag_str = f" tags={tags}" if tags else ""
    _maybe_checkpoint(conn)
    return f"Memory #{mem_id} stored: [{category}] (importance={importance}){tag_str}"


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
    max_tokens: int | None = None,
) -> str:
    """Get most recent memories, ranked by importance with time decay. Use at session start.

    Args:
        scope: Filter by scope (default: all)
        limit: Max results (default: 10)
        max_tokens: Token budget limit — stops adding memories when exceeded (optional)

    Returns:
        List of recent memories
    """
    conn = _get_conn()
    results = _db_get_recent_memory(conn, WORKSPACE_ID, scope, limit, max_tokens)
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
    confidence_type: str = "extracted",
) -> str:
    """Store or update a stable fact about the project. Use for confirmed knowledge.

    Args:
        key: Fact identifier (e.g., 'tech_stack', 'db_url', 'auth_provider')
        value: Fact value
        scope: Fact scope (default: workspace)
        confidence: Confidence level 0.0-1.0 (default: 1.0)
        confidence_type: extracted (observed directly) | inferred (reasoned) | ambiguous (uncertain)

    Returns:
        Confirmation with fact ID
    """
    conn = _get_conn()
    fact_id = _db_upsert_fact(
        conn, key, value, WORKSPACE_ID, scope, confidence, CRAFT_SESSION_ID, confidence_type,
    )
    _maybe_checkpoint(conn)
    return f"Fact #{fact_id} upserted: [{confidence_type}] {key} = {value[:100]}"


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


# ─── Tool: add_open_loop ────────────────────────────────────────────

@mcp.tool()
def add_open_loop(
    title: str,
    description: str | None = None,
    priority: str = "medium",
    scope: str = "workspace",
) -> str:
    """Create a new open loop (incomplete task or follow-up to track across sessions).

    Args:
        title: Short title for the loop
        description: Detailed description (optional)
        priority: low | medium | high | critical (default: medium)
        scope: Memory scope (default: workspace)

    Returns:
        Confirmation with loop ID
    """
    conn = _get_conn()
    loop_id = _db_create_open_loop(
        conn, CRAFT_SESSION_ID, WORKSPACE_ID,
        title, description, priority, scope, CRAFT_SESSION_ID,
    )
    return f"Open loop #{loop_id} created: [{priority}] {title}"


# ─── Tool: update_open_loop ──────────────────────────────────────────

@mcp.tool()
def update_open_loop(
    id: int,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> str:
    """Update title, description, priority or status of an open loop.

    Args:
        id: Loop ID to update
        title: New title (optional)
        description: New description (optional)
        priority: low | medium | high | critical (optional)
        status: open | in_progress | closed | stale (optional)

    Returns:
        Confirmation or not-found notice
    """
    conn = _get_conn()
    ok = _db_update_open_loop(conn, id, WORKSPACE_ID, title=title, description=description, priority=priority, status=status)
    if ok:
        parts = [f"Loop #{id} updated."]
        if title:
            parts.append(f"Title: {title}")
        if priority:
            parts.append(f"Priority: {priority}")
        if status:
            parts.append(f"Status: {status}")
        return " ".join(parts)
    return f"Loop #{id} not found or no valid fields to update."


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


# ─── Tool: save_summary ─────────────────────────────────────────────

@mcp.tool()
def save_summary(
    summary: str | None = None,
    decisions: list[str] | None = None,
    facts_learned: list[str] | None = None,
    open_loops: list[str] | None = None,
    refs: list[str] | None = None,
    next_steps: str | None = None,
) -> str:
    """Save a structured session summary (handoff document). Call at session end.

    Args:
        summary: Free-form narrative of what happened this session
        decisions: List of key decisions made
        facts_learned: List of new facts discovered
        open_loops: List of open loop titles/descriptions to carry forward
        refs: List of relevant references (file paths, URLs, IDs)
        next_steps: What to prioritize in the next session

    Returns:
        Confirmation with summary ID
    """
    conn = _get_conn()
    summary_id = _db_save_summary(
        conn, CRAFT_SESSION_ID, WORKSPACE_ID,
        summary, decisions, facts_learned, open_loops, refs, next_steps,
    )
    _maybe_checkpoint(conn)
    parts = []
    if summary:
        parts.append("summary")
    if decisions:
        parts.append(f"{len(decisions)} decisions")
    if facts_learned:
        parts.append(f"{len(facts_learned)} facts")
    if open_loops:
        parts.append(f"{len(open_loops)} open loops")
    if next_steps:
        parts.append("next_steps")
    detail = ", ".join(parts) if parts else "empty"
    return f"Session summary #{summary_id} saved ({detail})"


# ─── Tool: update_memory ────────────────────────────────────────────

@mcp.tool()
def update_memory(
    id: int,
    content: str | None = None,
    category: str | None = None,
    importance: int | None = None,
) -> str:
    """Update an existing memory's content, category, or importance.

    Args:
        id: Memory ID to update
        content: New content (optional)
        category: New category: decision, discovery, bugfix, feature, refactor, change, note (optional)
        importance: New importance 1-10 (optional)

    Returns:
        Confirmation or not-found notice
    """
    conn = _get_conn()
    if content is not None:
        content = _strip_private(content)
    success = _db_update_memory(conn, id, WORKSPACE_ID, content, category, importance)
    if success:
        parts = []
        if content is not None:
            parts.append("content")
        if category is not None:
            parts.append("category")
        if importance is not None:
            parts.append("importance")
        _maybe_checkpoint(conn)
        return f"Memory #{id} updated: {', '.join(parts)}"
    return f"Memory #{id} not found in workspace '{WORKSPACE_ID}'."


# ─── Tool: run_maintenance ──────────────────────────────────────────

@mcp.tool()
def run_maintenance() -> str:
    """Run database maintenance: cleanup old memories, trim session summaries, VACUUM.

    Deletes memories older than 180 days with importance < 3, marks stale loops,
    keeps only the 20 most recent session summaries, deduplicates, and runs VACUUM.

    Returns:
        Maintenance stats (deleted memories, stale loops, trimmed summaries, deduped)
    """
    conn = _get_conn()
    result = _db_daily_maintenance(conn, WORKSPACE_ID)
    return (
        f"Maintenance complete: "
        f"deleted_memories={result['deleted_memories']}, "
        f"stale_loops={result['stale_loops']}, "
        f"trimmed_summaries={result['trimmed_summaries']}, "
        f"deduped_memories={result['deduped_memories']}"
    )


# ─── Tool: search_by_tag ────────────────────────────────────────────

@mcp.tool()
def search_by_tag(
    tag: str,
    scope: str | None = None,
    limit: int = 20,
) -> str:
    """Search memories by tag.

    Args:
        tag: Tag to search for (e.g. "auth", "deploy")
        scope: Filter by scope (default: all)
        limit: Max results (default: 20)

    Returns:
        List of memories with the given tag
    """
    conn = _get_conn()
    results = _db_search_by_tag(conn, tag, WORKSPACE_ID, scope, limit)
    if not results:
        return f"No memories found with tag '{tag}'."

    lines = [f"Memories tagged '{tag}' ({len(results)}):\n"]
    for r in results:
        tags_str = ""
        if r.get("tags"):
            try:
                tags_str = f" tags={json.loads(r['tags'])}"
            except Exception:
                pass
        lines.append(
            f"#{r['id']} [{r['category']}] importance={r['importance']}"
            f"{tags_str} ({r['created_at'][:10]})\n"
            f"  {r['content'][:200]}"
        )
    return "\n\n".join(lines)


# ─── Tool: link_memories ────────────────────────────────────────────

@mcp.tool()
def link_memories(
    source_id: int,
    target_id: int,
    relation: str,
    confidence_type: str = "extracted",
    confidence_score: float = 1.0,
) -> str:
    """Create a directed relation between two memories (knowledge graph edge).

    Args:
        source_id: Source memory ID
        target_id: Target memory ID
        relation: caused_by | contradicts | extends | implements | supersedes | semantically_similar_to
        confidence_type: extracted (you observed it) | inferred (reasoned) | ambiguous (uncertain)
        confidence_score: Strength of the relation 0.0-1.0 (default: 1.0)

    Returns:
        Confirmation or duplicate notice
    """
    conn = _get_conn()
    rel_id = _db_link_memories(
        conn, source_id, target_id, relation,
        WORKSPACE_ID, confidence_type, confidence_score,
    )
    if rel_id is None:
        return f"Relation already exists or invalid: #{source_id} --{relation}--> #{target_id}"
    _maybe_checkpoint(conn)
    return f"Relation #{rel_id} created: #{source_id} --{relation} [{confidence_type}]--> #{target_id}"


# ─── Tool: get_relations ────────────────────────────────────────────

@mcp.tool()
def get_relations(
    memory_id: int,
    direction: str = "both",
) -> str:
    """Get all graph relations for a memory (neighbors in the knowledge graph).

    Args:
        memory_id: Memory ID to inspect
        direction: out (edges FROM this memory) | in (edges TO this memory) | both

    Returns:
        List of related memories with relation type and confidence
    """
    conn = _get_conn()
    results = _db_get_relations(conn, memory_id, WORKSPACE_ID, direction)
    if not results:
        return f"No relations found for memory #{memory_id}."

    lines = [f"Relations for #{memory_id} ({len(results)} edges):\n"]
    for r in results:
        arrow = f"#{memory_id} --{r['relation']} [{r['confidence_type']}]--> #{r['target_id']}"
        if r["direction"] == "in":
            arrow = f"#{r['source_id']} --{r['relation']} [{r['confidence_type']}]--> #{memory_id}"
        lines.append(f"{arrow}\n  {r['other_content'][:120]}")
    return "\n\n".join(lines)


# ─── Tool: find_similar ─────────────────────────────────────────────

@mcp.tool()
def find_similar(
    memory_id: int,
    top_n: int = 5,
    auto_link: bool = False,
) -> str:
    """Find memories similar to a given one using FTS5 BM25 scoring.

    Args:
        memory_id: Memory ID to find similarities for
        top_n: Max results (default: 5)
        auto_link: If True, automatically create INFERRED 'semantically_similar_to' edges
                   for strong matches (BM25 score < -1.5)

    Returns:
        List of similar memories with similarity scores
    """
    conn = _get_conn()
    results = _db_find_similar_memories(conn, memory_id, WORKSPACE_ID, top_n, auto_link)
    if not results:
        return f"No similar memories found for #{memory_id}."

    action = " (INFERRED links created for strong matches)" if auto_link else ""
    lines = [f"Similar to #{memory_id}{action} ({len(results)} found):\n"]
    for r in results:
        lines.append(
            f"#{r['id']} [{r['category']}] importance={r['importance']} "
            f"similarity={r['similarity_score']}\n"
            f"  {r['content'][:200]}"
        )
    return "\n\n".join(lines)


# ─── Tool: god_facts ────────────────────────────────────────────────

@mcp.tool()
def god_facts(
    top_n: int = 10,
) -> str:
    """Return the most impactful facts — core knowledge nodes referenced most in memories.

    Score = confidence × type_bonus × (1 + mention_count × 0.2)
    EXTRACTED > INFERRED > AMBIGUOUS at equal confidence.
    Use to identify the core concepts and architectural decisions of the workspace.

    Args:
        top_n: Max results (default: 10)

    Returns:
        Ranked list of facts with god_score, confidence_type, and mention_count
    """
    conn = _get_conn()
    results = _db_god_facts(conn, WORKSPACE_ID, top_n)
    if not results:
        return "No facts found for this workspace."

    lines = ["God Facts (most impactful):\n"]
    for i, f in enumerate(results, 1):
        ctype = f.get("confidence_type", "extracted")
        lines.append(
            f"{i}. [{ctype}] {f['key']} (score={f['god_score']}, "
            f"confidence={f['confidence']}, mentions={f['mention_count']})\n"
            f"   {f['value'][:150]}"
        )
    return "\n\n".join(lines)


# ─── Tool: memory_diff ──────────────────────────────────────────────

@mcp.tool()
def memory_diff(
    since_epoch: int,
) -> str:
    """Return what changed in memory since a given Unix epoch timestamp.

    Useful at session start to understand what happened in previous sessions.
    Tip: use int(time.time()) - 86400 for last 24h, or a session's started_at_epoch.

    Args:
        since_epoch: Unix timestamp to diff from

    Returns:
        Summary of new memories, updated facts, new/closed loops since that time
    """
    conn = _get_conn()
    diff = _db_memory_diff(conn, WORKSPACE_ID, since_epoch)

    lines = [
        f"Memory diff since {diff['since_iso'][:19]} UTC\n",
        f"Summary: {diff['summary']}\n",
    ]

    if diff["updated_facts"]:
        lines.append("--- Updated Facts ---")
        for f in diff["updated_facts"]:
            ctype = f.get("confidence_type", "extracted")
            lines.append(f"  [{ctype}] {f['key']}: {f['value'][:100]} (updated {f['updated_at'][:10]})")
        lines.append("")

    if diff["new_loops"]:
        lines.append("--- New Open Loops ---")
        for l in diff["new_loops"]:
            lines.append(f"  #{l['id']} [{l['priority']}] {l['title']}")
        lines.append("")

    if diff["closed_loops"]:
        lines.append("--- Closed Loops ---")
        for l in diff["closed_loops"]:
            res = f" → {l['resolution'][:80]}" if l.get("resolution") else ""
            lines.append(f"  #{l['id']} {l['title']}{res}")
        lines.append("")

    if diff["new_memories"]:
        lines.append(f"--- New Memories ({len(diff['new_memories'])}) ---")
        for m in diff["new_memories"][:10]:
            lines.append(
                f"  #{m['id']} [{m['category']}] importance={m['importance']} "
                f"({m['created_at'][:10]}): {m['content'][:120]}"
            )
        if len(diff["new_memories"]) > 10:
            lines.append(f"  ... and {len(diff['new_memories']) - 10} more")

    return "\n".join(lines)


# ─── Entry Point (called by CLI or directly) ─────────────────────────

def run_server():
    """Start the MCP server with the configured transport."""
    if MCP_TRANSPORT == "http":
        import uvicorn
        print(f"[craft-memory] v{_VERSION} HTTP server on http://{MCP_HOST}:{MCP_PORT}/mcp", flush=True)
        print(f"[craft-memory] Health: http://{MCP_HOST}:{MCP_PORT}/health", flush=True)
        print(f"[craft-memory] Workspace: {WORKSPACE_ID}", flush=True)
        app = mcp.streamable_http_app()
        uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
    else:
        print(f"[craft-memory] v{_VERSION} stdio server (workspace: {WORKSPACE_ID})", flush=True)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
