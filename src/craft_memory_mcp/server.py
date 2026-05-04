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
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import Any

from craft_memory_mcp import __version__ as _VERSION

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
    _AUTOLINK_THRESHOLD,
    close_open_loop as _db_close_open_loop,
    complete_session as _db_complete_session,
    create_open_loop as _db_create_open_loop,
    daily_maintenance as _db_daily_maintenance,
    dedup_memories as _db_dedup_memories,
    delete_old_memories as _db_delete_old_memories,
    find_consolidation_candidates as _db_find_consolidation_candidates,
    find_similar_memories as _db_find_similar_memories,
    get_connection as _db_get_connection,
    hybrid_search as _db_hybrid_search,
    promote_memory_to_core as _db_promote_memory_to_core,
    get_facts as _db_get_facts,
    get_latest_summary as _db_get_latest_summary,
    get_recent_memory as _db_get_recent_memory,
    get_all_relations as _db_get_all_relations,
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
    explain_retrieval as _db_explain_retrieval,
    generate_handoff as _db_generate_handoff,
    get_memory_stats as _db_get_memory_stats,
    approve_memory as _db_approve_memory,
    flag_for_review as _db_flag_for_review,
    get_memory_history as _db_get_memory_history,
    invalidate_memory as _db_invalidate_memory,
    list_needs_review as _db_list_needs_review,
    MemoryClass as _MemoryClass,
    classify_memory_event as _db_classify_memory_event,
    get_applicable_procedures as _db_get_applicable_procedures,
    list_procedures as _db_list_procedures,
    save_procedure as _db_save_procedure,
    search_procedures as _db_search_procedures,
    get_memory_bundle as _db_get_memory_bundle,
    get_scope_ancestors as _db_get_scope_ancestors,
    search_facts as _db_search_facts,
    lint_wiki as _db_lint_wiki,
    list_procedures as _db_list_procedures_all,
    find_consolidation_candidates as _db_find_consolidation_candidates,
    record_procedure_outcome as _db_record_procedure_outcome,
    get_procedure_outcomes as _db_get_procedure_outcomes,
    get_graph_context as _db_get_graph_context,
    batch_remember as _db_batch_remember,
    get_top_procedures as _db_get_top_procedures,
    consolidate_memories as _db_consolidate_memories,
    rate_session as _db_rate_session,
    spec_to_plan as _db_spec_to_plan,
    plan_to_tasks_text as _db_plan_to_tasks_text,
    get_high_quality_sessions as _db_get_high_quality_sessions,
    export_session_traces as _db_export_session_traces,
    export_wiki as _db_export_wiki,
    shortest_path as _db_shortest_path,
    query_graph as _db_query_graph,
    get_memories_for_graph as _db_get_memories_for_graph,
    get_all_relations as _db_get_all_relations,
    export_graphml as _db_export_graphml,
    export_cypher as _db_export_cypher,
    record_procedure_outcome as _db_record_outcome,
    update_procedure_confidence as _db_update_conf,
)

from craft_memory_mcp.clustering import detect_communities as _cluster, get_community_stats as _cluster_stats
from craft_memory_mcp.graph_viz import generate_graph_html as _graph_viz


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
    instructions="""Craft Memory — Persistent cross-session memory.

TOOL GROUPS:
  CORE (use every session):
    remember, search_memory, get_recent_memory, upsert_fact, list_open_loops

  GRAPH (knowledge relationships — use when needed):
    link_memories, get_relations, find_similar, god_facts, memory_diff, search_by_tag

  ADMIN (lifecycle & housekeeping — use sparingly):
    run_maintenance, promote_to_core, summarize_scope, save_summary,
    update_memory, add_open_loop, close_open_loop, update_open_loop

RECOMMENDED WORKFLOW:
  1. Session start  → get_recent_memory + list_open_loops
  2. During work    → remember for decisions; upsert_fact for confirmed knowledge
  3. Session end    → summarize_scope for handoff

KNOWLEDGE GRAPH: remember() now includes automatic linking — when a new memory is
  saved, it searches for similar memories (FTS5 BM25) and creates INFERRED
  'semantically_similar_to' edges for strong matches. Edges are is_manual=False
  (prunable by daily maintenance). Use link_memories for manual curation.

STABILITY-FIRST: Core promotion and fact promotion are always assisted or manual.
Close-loop is never automatic. Only store what has lasting value.""",
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


# ─── Prometheus-compatible metrics endpoint (HTTP transport only) ─────

@mcp.custom_route("/metrics", methods=["GET"])
async def metrics(request):
    """Prometheus-compatible metrics endpoint.

    Exposes memory, procedure, open loop, and DB size counters.
    Useful for Grafana dashboards and external monitoring without MCP calls.
    """
    from starlette.responses import PlainTextResponse
    ws = WORKSPACE_ID
    lines = [f'# HELP craft_memory_info Craft Memory server info\n# TYPE craft_memory_info gauge\nccraft_memory_info{{version="{_VERSION}",workspace="{ws}"}} 1']
    try:
        conn = _get_conn()
        stats = _db_get_memory_stats(conn, ws)

        mem_total = stats.get("total_memories", 0)
        core_total = stats.get("core_memories", 0)
        facts_total = stats.get("total_facts", 0)
        loops_total = stats.get("open_loops", 0)
        proc_total = stats.get("total_procedures", 0)

        avg_conf_row = conn.execute(
            "SELECT AVG(confidence) AS avg_conf FROM procedures WHERE workspace_id = ? AND status = 'active'",
            (ws,),
        ).fetchone()
        avg_conf = round(avg_conf_row["avg_conf"] or 0.0, 4)

        db_dir = Path(os.environ.get("CRAFT_MEMORY_DB_DIR", str(Path.home() / ".craft-agent/memory")))
        db_path = db_dir / f"{ws}.db"
        db_size_mb = round(db_path.stat().st_size / 1024 / 1024, 4) if db_path.exists() else 0.0

        def _gauge(name: str, help_text: str, value) -> str:
            return f"# HELP {name} {help_text}\n# TYPE {name} gauge\n{name}{{workspace=\"{ws}\"}} {value}"

        lines += [
            _gauge("craft_memory_memories_total", "Total memories stored", mem_total),
            _gauge("craft_memory_core_memories_total", "Core memories (decay-immune)", core_total),
            _gauge("craft_memory_facts_total", "Total stable facts", facts_total),
            _gauge("craft_memory_open_loops_total", "Open loops count", loops_total),
            _gauge("craft_memory_procedures_total", "Active procedures count", proc_total),
            _gauge("craft_memory_procedure_confidence_avg", "Average active procedure confidence", avg_conf),
            _gauge("craft_memory_db_size_mb", "Database size in megabytes", db_size_mb),
        ]
    except Exception as exc:
        lines.append(f"# ERROR collecting metrics: {exc}")

    return PlainTextResponse("\n\n".join(lines) + "\n", media_type="text/plain; version=0.0.4; charset=utf-8")


# ─── Rate limiter ────────────────────────────────────────────────────
# Prevents rapid-fire tool calls (max RATE_LIMIT calls per second)
from collections import deque
import time as _time

_RATE_LIMIT = 30  # max calls per second
_call_timestamps: deque = deque(maxlen=_RATE_LIMIT)


def _check_rate_limit() -> str | None:
    """Check rate limit. Returns error message if exceeded, None if OK."""
    now = _time.time()
    _call_timestamps.append(now)
    if len(_call_timestamps) >= _RATE_LIMIT:
        oldest = _call_timestamps[0]
        if now - oldest < 1.0:
            return f"Rate limit exceeded: max {_RATE_LIMIT} calls per second. Wait and retry."
    return None


# ─── Thread safety ────────────────────────────────────────────────
import threading as _threading

_conn_lock = _threading.Lock()
_conn = None

_write_count = 0
_CHECKPOINT_EVERY = 50


def _maybe_checkpoint(conn) -> None:
    global _write_count
    with _conn_lock:
        _write_count += 1
        if _write_count >= _CHECKPOINT_EVERY:
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            _write_count = 0


def _get_conn():
    global _conn
    with _conn_lock:
        if _conn is not None:
            try:
                _conn.execute("SELECT 1")
            except Exception:
                _conn = None
        if _conn is None:
            _conn = _db_get_connection(WORKSPACE_ID)
            _db_register_session(_conn, CRAFT_SESSION_ID, WORKSPACE_ID)
        return _conn


# WAL checkpoint counter — flush WAL every N writes to keep file size bounded
_write_count = 0
_CHECKPOINT_EVERY = 50  # Checkpoint every 50 writes (was 100)

def _maybe_checkpoint(conn) -> None:
    """Checkpoint WAL every N writes. Uses TRUNCATE to keep WAL file size bounded.

    PRAGMA wal_checkpoint(TRUNCATE) moves WAL pages back to the main DB file
    and truncates the WAL to 0 bytes. This prevents unbounded WAL growth which
    can reach 3+ MB during heavy graph edge creation (backfill, auto-linking).
    """
    global _write_count
    _write_count += 1
    if _write_count >= _CHECKPOINT_EVERY:
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            # Fallback to PASSIVE if TRUNCATE fails (shared WAL, etc.)
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
    force: bool = False,
    compress_level: int = 0,
) -> str:
    """Store a new episodic memory (decision, discovery, bugfix, feature, refactor, change, note).

    Args:
        content: The memory content to store
        category: Type of memory - decision, discovery, bugfix, feature, refactor, change, note
        scope: Memory scope (default: workspace)
        importance: Priority 1-10 (default: 5)
        source_session: Session ID that created this memory
        tags: Optional list of tags e.g. ["auth", "deploy"]
        force: If True, bypasses dedup and stores even if duplicate content_hash
        compress_level: 0=no compression, 1=dictionary compression (~40% saving)

    Returns:
        Confirmation with memory ID or duplicate notice
    """
    rate_msg = _check_rate_limit()
    if rate_msg:
        return rate_msg
    conn = _get_conn()
    session_id = source_session or CRAFT_SESSION_ID
    content = _strip_private(content)
    if not content:
        return "Memory skipped: content was empty after stripping private tags."

    # Input validation
    valid_categories = {'decision', 'discovery', 'bugfix', 'feature', 'refactor', 'change', 'note'}
    if category not in valid_categories:
        return f"Invalid category '{category}'. Must be one of: {', '.join(sorted(valid_categories))}"
    if not isinstance(importance, int) or importance < 1 or importance > 10:
        return f"Importance must be 1-10, got {importance}"
    if not isinstance(compress_level, int) or compress_level < 0 or compress_level > 1:
        return f"compress_level must be 0 or 1, got {compress_level}"
    if tags is not None:
        if not isinstance(tags, list):
            return "Tags must be a list of strings"
        for t in tags:
            if not isinstance(t, str):
                return f"Each tag must be a string, got {type(t).__name__}"

    mem_id = _db_remember(
        conn, session_id, WORKSPACE_ID, content,
        category, importance, scope, session_id, tags,
        force=force, compress_level=compress_level,
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
    use_rrf: bool = True,
    decompress: bool = True,
) -> str:
    """Search memories using full-text search with RRF hybrid ranking.

    Args:
        query: Search query (keywords, phrases)
        scope: Filter by scope (default: all)
        limit: Max results (default: 20)
        use_rrf: Use RRF hybrid ranking (BM25 + word-overlap fusion). Default True.
        decompress: Decompress content stored with compress_level>0 (default: True)

    Returns:
        List of matching memories
    """
    rate_msg = _check_rate_limit()
    if rate_msg:
        return rate_msg
    conn = _get_conn()
    if use_rrf:
        results = _db_hybrid_search(conn, query, WORKSPACE_ID, scope=scope, limit=limit, decompress=decompress)
    else:
        results = _db_search_memory(conn, query, WORKSPACE_ID, scope, limit, decompress=decompress)
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
    decompress: bool = True,
) -> str:
    """Get most recent memories, ranked by importance with time decay. Use at session start.

    Args:
        scope: Filter by scope (default: all)
        limit: Max results (default: 10)
        max_tokens: Token budget limit — stops adding memories when exceeded (optional)
        decompress: Decompress content stored with compress_level>0 (default: True)

    Returns:
        List of recent memories
    """
    rate_msg = _check_rate_limit()
    if rate_msg:
        return rate_msg
    conn = _get_conn()
    results = _db_get_recent_memory(conn, WORKSPACE_ID, scope, limit, max_tokens, decompress=decompress)
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
    """[admin] Close an open loop with an optional resolution. Never runs automatically.

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
    """[admin] Create a new open loop (incomplete task or follow-up to track across sessions).

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
    """[admin] Update title, description, priority or status of an open loop.

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
    """[admin] Generate a comprehensive summary of a scope. Use at session end for handoff.

    Args:
        scope: Scope to summarize (default: workspace)

    Returns:
        Structured summary with recent memories, facts, and open loops
    """
    conn = _get_conn()
    result = _db_summarize_scope(conn, WORKSPACE_ID, scope)

    total_mem = result.get('total_memory_count', result['memory_count'])
    shown_mem = result['memory_count']
    if total_mem == shown_mem:
        mem_label = str(total_mem)
    else:
        mem_label = f"{shown_mem} shown / {total_mem} total"

    lines = [
        f"=== Memory Summary: {result['workspace_id']} / {result['scope']} ===\n",
        f"Stats: {mem_label} memories, {result['fact_count']} facts, "
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
    """[admin] Save a structured session summary (handoff document). Call at session end.

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
    """[admin] Update an existing memory's content, category, or importance.

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
    """[admin] Run database maintenance: cleanup old memories, trim session summaries, VACUUM.

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
        f"deduped_memories={result['deduped_memories']}, "
        f"inferred_edges_pruned={result['inferred_edges_pruned']}"
    )


# ─── Tool: promote_to_core ──────────────────────────────────────────

@mcp.tool()
def promote_to_core(
    id: int,
) -> str:
    """[admin] Mark a memory as core — immune to importance decay. Assisted action: requires explicit decision.

    Core memories always rank at full importance regardless of age.
    Use for architectural decisions, confirmed patterns, or key facts
    that must always be retrieved.

    Args:
        id: Memory ID to promote

    Returns:
        Confirmation or not-found notice
    """
    conn = _get_conn()
    ok = _db_promote_memory_to_core(conn, id, WORKSPACE_ID)
    return f"Memory #{id} promoted to core." if ok else f"Memory #{id} not found."


# ─── Tool: search_by_tag ────────────────────────────────────────────

@mcp.tool()
def search_by_tag(
    tag: str,
    scope: str | None = None,
    limit: int = 20,
) -> str:
    """[graph] Search memories by tag.

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
    role: str = "context",
    weight: float = 1.0,
) -> str:
    """[graph] Create a directed relation between two memories (knowledge graph edge). Use for manual curation — remember() auto-links similar content.

    Args:
        source_id: Source memory ID
        target_id: Target memory ID
        relation: caused_by | contradicts | extends | implements | supersedes | semantically_similar_to
        confidence_type: extracted (you observed it) | inferred (reasoned) | ambiguous (uncertain)
        confidence_score: Strength of the relation 0.0-1.0 (default: 1.0)
        role: core | context | detail | temporal | causal (semantic role, default: context)
        weight: Importance of this edge in the graph 0.0-1.0 (default: 1.0)

    Returns:
        Confirmation or duplicate notice
    """
    conn = _get_conn()
    rel_id = _db_link_memories(
        conn, source_id, target_id, relation,
        WORKSPACE_ID, confidence_type, confidence_score,
        role=role, weight=weight,
    )
    if rel_id is None:
        return f"Relation already exists or invalid: #{source_id} --{relation}--> #{target_id}"
    _maybe_checkpoint(conn)
    return f"Relation #{rel_id} created: #{source_id} --[{role}:{relation} w={weight}]--> #{target_id}"


# ─── Tool: get_relations ────────────────────────────────────────────

@mcp.tool()
def get_relations(
    memory_id: int,
    direction: str = "both",
) -> str:
    """[graph] Get all graph relations for a memory (neighbors in the knowledge graph).

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
    """[graph] Find memories similar to a given one using FTS5 BM25 scoring.

    Args:
        memory_id: Memory ID to find similarities for
        top_n: Max results (default: 5)
        auto_link: If True, automatically create INFERRED 'semantically_similar_to' edges
                   for very strong matches only (threshold configurable via CRAFT_MEMORY_AUTOLINK_THRESHOLD,
                   default -2.5 — strict by design, precision over recall)

    Returns:
        List of similar memories with similarity scores
    """
    conn = _get_conn()
    results = _db_find_similar_memories(conn, memory_id, WORKSPACE_ID, top_n, auto_link)
    if not results:
        return f"No similar memories found for #{memory_id}."

    linked_count = sum(1 for r in results if r.get("auto_linked"))
    action = f" ({linked_count} INFERRED links created, threshold={_AUTOLINK_THRESHOLD})" if auto_link else ""
    lines = [f"Similar to #{memory_id}{action} ({len(results)} found):\n"]
    for r in results:
        link_marker = " [auto-linked]" if r.get("auto_linked") else ""
        lines.append(
            f"#{r['id']} [{r['category']}] importance={r['importance']} "
            f"similarity={r['similarity_score']}{link_marker}\n"
            f"  {r['content'][:200]}"
        )
    return "\n\n".join(lines)


# ─── Tool: god_facts ────────────────────────────────────────────────

@mcp.tool()
def god_facts(
    top_n: int = 10,
) -> str:
    """[graph] Return the most impactful facts — core knowledge nodes referenced most in memories.

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
    """[graph] Return what changed in memory since a given Unix epoch timestamp.

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


# --- Sprint 1: Observability & Handoff tools ---


@mcp.tool()
def memory_stats(
    scope: str | None = None,
) -> str:
    """[admin] Aggregate stats for this workspace.

    Args:
        scope: Filter by scope (default: all scopes)

    Returns:
        Summary of workspace memory state
    """
    conn = _get_conn()
    stats = _db_get_memory_stats(conn, WORKSPACE_ID, scope=scope)
    lines = [
        f"Workspace stats (scope={scope or 'all'}):",
        f"  Memories: {stats['total_memories']} total ({stats['core_memories']} core, avg importance {stats['avg_importance']})",
        f"  Categories: {stats['by_category']}",
        f"  Open loops: {stats['open_loops']}",
        f"  Edges: {stats['total_edges']} total ({stats['manual_edges']} manual, {stats['inferred_edges']} inferred)",
    ]
    return chr(10).join(lines)


@mcp.tool()
def explain_retrieval(
    memory_id: int,
) -> str:
    """[admin] Diagnostic info for a specific memory: content, category, edge graph.

    Args:
        memory_id: ID of the memory to inspect

    Returns:
        Full memory details with relation graph
    """
    conn = _get_conn()
    info = _db_explain_retrieval(conn, memory_id, WORKSPACE_ID)
    if info is None:
        return f"Memory #{memory_id} not found in this workspace."
    out = [
        f"Memory #{info['id']} [{info['category']}] importance={info['importance']} confidence={info['confidence_type']}",
        f"  scope: {info['scope']}",
        f"  created: {info.get('created_at', 'unknown')}",
        f"  content: {info['content'][:300]}",
    ]
    if info['relations']:
        out.append(f"  relations ({info['relation_count']}):")
        for rel in info['relations'][:10]:
            flag = ' [manual]' if rel.get('is_manual') else ' [inferred]'
            other = rel['source_id'] if rel['direction'] == 'in' else rel['target_id']
            out.append(f"    {rel['direction']} --{rel['relation']}--> #{other}{flag}")
    else:
        out.append('  relations: none')
    return chr(10).join(out)


@mcp.tool()
def generate_handoff(
    scope: str | None = None,
) -> str:
    """[core] Generate a structured session-handoff pack for context continuity.

    Collects recent decisions, active open loops, recent facts and stats snapshot.

    Args:
        scope: Memory scope to filter (default: all)

    Returns:
        Formatted handoff document
    """
    conn = _get_conn()
    pack = _db_generate_handoff(conn, WORKSPACE_ID, scope=scope)
    out = [f"SESSION HANDOFF - {pack['generated_at']} (scope={pack['scope']})", '']

    out.append(f"DECISIONS ({len(pack['recent_decisions'])}) :")
    for d in pack['recent_decisions']:
        out.append(f"  #{d['id']} importance={d['importance']}: {d['content'][:150]}")
    if not pack['recent_decisions']:
        out.append('  (none)')

    out.append('')
    out.append(f"OPEN LOOPS ({len(pack['active_open_loops'])}) :")
    for lp in pack['active_open_loops']:
        out.append(f"  [{lp['priority']}] {lp['title']}")
    if not pack['active_open_loops']:
        out.append('  (none)')

    out.append('')
    out.append(f"FACTS ({len(pack['recent_facts'])}) :")
    for fc in pack['recent_facts']:
        out.append(f"  {fc['key']}: {str(fc['value'])[:100]}")
    if not pack['recent_facts']:
        out.append('  (none)')

    s = pack['memory_stats_snapshot']
    out.append('')
    out.append(f"STATS: {s['total_memories']} memories, {s['open_loops']} open loops, {s['total_edges']} edges")
    return chr(10).join(out)


@mcp.tool()
def save_decision_record(
    title: str,
    context: str,
    decision: str,
    rationale: str,
    scope: str = 'workspace',
) -> str:
    """[core] Save an architectural or product decision as a high-importance ADR memory.

    Args:
        title: Short title for the decision
        context: Problem or situation that prompted this decision
        decision: What was decided
        rationale: Why this decision was made
        scope: Memory scope (default: workspace)

    Returns:
        Confirmation with memory ID
    """
    conn = _get_conn()
    nl = chr(10)
    content = f"DECISION: {title}{nl}Context: {context}{nl}Decision: {decision}{nl}Rationale: {rationale}"
    content = _strip_private(content)
    mem_id = _db_remember(
        conn, CRAFT_SESSION_ID, WORKSPACE_ID, content,
        category='decision',
        importance=9,
        scope=scope,
        source_session=CRAFT_SESSION_ID,
        tags=['decision-record', 'architecture'],
    )
    _maybe_checkpoint(conn)
    if mem_id is None:
        return 'Duplicate decision record skipped.'
    return f'Decision record #{mem_id} saved: {title}'

# --- Sprint 2: Temporal Invalidation + Review Flag ---

@mcp.tool()
def invalidate_memory(memory_id: int, reason: str) -> str:
    """Mark a memory as invalidated (lifecycle_status='invalidated').

    Use when a memory is no longer valid — e.g. a decision was reversed,
    an assumption proved wrong, or information is stale.
    The memory is preserved for history but excluded from search and retrieval.
    """
    conn = _get_conn()
    ok = _db_invalidate_memory(conn, memory_id, reason, WORKSPACE_ID)
    _maybe_checkpoint(conn)
    if not ok:
        return f'Memory #{memory_id} not found in this workspace.'
    return f'Memory #{memory_id} marked as invalidated: {reason}'


@mcp.tool()
def get_memory_history(memory_id: int) -> str:
    """Return the full supersession chain for a memory.

    Follows superseded_by links to show how a memory evolved over time.
    Useful for understanding the history of a decision or fact.
    """
    conn = _get_conn()
    chain = _db_get_memory_history(conn, memory_id, WORKSPACE_ID)
    if not chain:
        return f'Memory #{memory_id} not found.'
    nl = chr(10)
    lines = [f'History chain for memory #{memory_id} ({len(chain)} entries):']
    for i, m in enumerate(chain):
        status = m.get('lifecycle_status') or 'active'
        lines.append(f'  [{i+1}] #{m["id"]} [{status}] {m["content"][:120]}')
    return nl.join(lines)


@mcp.tool()
def flag_for_review(memory_id: int, reason: str) -> str:
    """Flag a memory for human review (lifecycle_status='needs_review').

    Use when a memory might be incorrect, outdated, or needs verification.
    Flagged memories are excluded from default search and retrieval until approved.
    """
    conn = _get_conn()
    ok = _db_flag_for_review(conn, memory_id, reason, WORKSPACE_ID)
    _maybe_checkpoint(conn)
    if not ok:
        return f'Memory #{memory_id} not found in this workspace.'
    return f'Memory #{memory_id} flagged for review: {reason}'


@mcp.tool()
def list_needs_review(limit: int = 20) -> str:
    """List memories currently flagged for human review.

    Returns memories with lifecycle_status='needs_review', ordered by importance.
    Use approve_memory or invalidate_memory to process each entry.
    """
    conn = _get_conn()
    items = _db_list_needs_review(conn, WORKSPACE_ID, limit=limit)
    if not items:
        return 'No memories pending review.'
    nl = chr(10)
    lines = [f'Memories pending review ({len(items)}):']
    for m in items:
        lines.append(f'  #{m["id"]} [importance={m["importance"]}] {m["content"][:120]}')
    return nl.join(lines)


@mcp.tool()
def approve_memory(memory_id: int) -> str:
    """Approve a memory under review, restoring it to active status.

    Sets lifecycle_status back to 'active' so the memory reappears in
    search and retrieval results.
    """
    conn = _get_conn()
    ok = _db_approve_memory(conn, memory_id, WORKSPACE_ID)
    _maybe_checkpoint(conn)
    if not ok:
        return f'Memory #{memory_id} not found in this workspace.'
    return f'Memory #{memory_id} approved and restored to active status.'


# --- Sprint 3: Boundary Detection Policy ---

@mcp.tool()
def classify_event(
    content: str,
    importance: int = 5,
    category: str = "",
) -> str:
    """Classify a memory event and recommend the best storage strategy.

    Use this BEFORE calling remember/upsert_fact/add_open_loop to determine
    which tool is most appropriate for a given piece of information.

    Returns: classification (DISCARD/EPISODIC/FACT_CANDIDATE/OPEN_LOOP/
    PROCEDURE_CANDIDATE/CORE_CANDIDATE) + reason + recommended action.
    """
    signals = {"importance": importance}
    if category:
        signals["category"] = category
    cls, reason = _db_classify_memory_event(content, context_signals=signals)
    nl = chr(10)
    action_map = {
        _MemoryClass.DISCARD: "Do not save — content is too short or trivial.",
        _MemoryClass.EPISODIC: "Use remember() with appropriate category.",
        _MemoryClass.FACT_CANDIDATE: "Use upsert_fact() with a clear key and value.",
        _MemoryClass.OPEN_LOOP: "Use add_open_loop() to track as a pending task.",
        _MemoryClass.PROCEDURE_CANDIDATE: "Use remember(category='note') now; save_procedure() in Sprint 4.",
        _MemoryClass.CORE_CANDIDATE: "Use remember() then promote_to_core() for persistence.",
    }
    lines = [
        f"Classification: {cls.value.upper()}",
        f"Reason: {reason}",
        f"Recommended action: {action_map[cls]}",
    ]
    return nl.join(lines)


# --- Sprint 4: Procedural Memory ---

@mcp.tool()
def save_procedure(
    name: str,
    trigger_context: str,
    steps_md: str,
    confidence: float = 0.5,
    source_memory_ids: str = "",
    status: str = "active",
    mode: str = "manual",
    verify_command: str | None = None,
    acceptance_criteria: str | None = None,
    spec_text: str | None = None,
) -> str:
    """Save or update a reusable procedure (step-by-step pattern).

    Procedures capture recurring workflows so they can be retrieved and applied
    in future sessions. Upserts by name — calling again with the same name updates it.

    Args:
        name: Short unique identifier (e.g. 'deploy-backend', 'code-review-process')
        trigger_context: When to apply this procedure (natural language description)
        steps_md: Markdown-formatted steps (e.g. '1. Pull main\\n2. Run tests\\n3. Deploy')
        confidence: How reliable is this procedure (0.0–1.0, default 0.5)
        source_memory_ids: Comma-separated memory IDs that inspired this procedure (optional)
        status: 'active' | 'draft' | 'deprecated'
        mode: 'manual' (default) | 'cavekit' (spec-driven with verify)
        verify_command: Shell command to verify the procedure succeeded (cavekit mode)
        acceptance_criteria: Criteria that define success (cavekit mode)
        spec_text: Original spec that generated this procedure (cavekit mode)
    """
    conn = _get_conn()
    src_ids = None
    if source_memory_ids.strip():
        try:
            src_ids = [int(x.strip()) for x in source_memory_ids.split(",") if x.strip()]
        except ValueError:
            pass
    pid = _db_save_procedure(
        conn, WORKSPACE_ID, name, trigger_context, steps_md,
        confidence=confidence, source_memory_ids=src_ids, status=status,
        mode=mode, verify_command=verify_command,
        acceptance_criteria=acceptance_criteria, spec_text=spec_text,
    )
    _maybe_checkpoint(conn)
    parts = [f'Procedure #{pid} "{name}" saved']
    if mode == "cavekit":
        parts.append("(cavekit mode)")
    parts.append(f'(confidence={confidence}, status={status})')
    return " ".join(parts)


@mcp.tool()
def spec_to_plan(
    spec_text: str,
    name: str | None = None,
) -> str:
    """[cavekit] Converte una specifica testuale in un piano strutturato con task.

    Analizza la specifica riga per riga, estraendo task numerati
    e comandi di verifica [verify: ...] per ogni task.

    Args:
        spec_text: Il testo della specifica
            Formato consigliato:
              1. Task description [verify: command]
              2. Another task [criteria: acceptance criteria]
              * Bullet task
        name: Nome opzionale del piano (default: prima riga della spec)

    Returns:
        Piano strutturato con task, criteri di accettazione, comandi verify
    """
    plan = _db_spec_to_plan(spec_text, name=name)
    return _db_plan_to_tasks_text(plan)


@mcp.tool()
def record_procedure_outcome_and_advance(
    procedure_id: int,
    outcome: str,
    notes: str | None = None,
    next_task_id: int | None = None,
) -> str:
    """[cavekit] Registra l'esito di un task e passa al successivo.

    Da usare durante l'esecuzione di un piano Cavekit:
    1. Esegui un task
    2. Chiama questa funzione con l'esito
    3. Prendi il task successivo dal piano

    Args:
        procedure_id: ID della procedura (piano)
        outcome: 'success' | 'partial' | 'failure'
        notes: Note sull'esecuzione
        next_task_id: ID del prossimo task da eseguire (opzionale)

    Returns:
        Messaggio con l'esito e il task successivo
    """
    conn = _get_conn()

    # Recupera la procedura
    proc = conn.execute(
        "SELECT * FROM procedures WHERE id = ? AND workspace_id = ?",
        (procedure_id, WORKSPACE_ID),
    ).fetchone()

    if not proc:
        return f"Procedure #{procedure_id} not found."

    # Registra outcome
    outcome_id = _db_record_outcome(conn, procedure_id, WORKSPACE_ID, outcome, notes)
    _maybe_checkpoint(conn)

    # Aggiorna confidence
    new_conf = _db_update_conf(conn, procedure_id, WORKSPACE_ID)

    lines = [
        f"Outcome #{outcome_id} recorded: {outcome}",
    ]
    if new_conf is not None:
        lines.append(f"Updated confidence: {new_conf:.3f}")
    if next_task_id:
        lines.append(f"Next task to execute: #{next_task_id}")
    if notes:
        lines.append(f"Notes: {notes}")

    return "\n".join(lines)


@mcp.tool()
def search_procedures(query: str, limit: int = 10) -> str:
    """Search procedures by name, trigger context, or steps content (FTS5).

    Use to find relevant procedures before starting a task or when looking for
    established workflows in this workspace.
    """
    conn = _get_conn()
    results = _db_search_procedures(conn, query, WORKSPACE_ID, limit=limit)
    if not results:
        return f'No procedures found matching "{query}".'
    nl = chr(10)
    lines = [f'Procedures matching "{query}" ({len(results)}):']
    for p in results:
        lines.append(
            f'  #{p["id"]} [{p["status"]}] "{p["name"]}" (confidence={p["confidence"]:.2f})'
            f'{nl}    Trigger: {p["trigger_context"][:100]}'
        )
    return nl.join(lines)


@mcp.tool()
def get_applicable_procedures(current_context: str, limit: int = 5) -> str:
    """Find the most applicable procedures for the current task context.

    Call at the start of a task to retrieve relevant workflows. Returns active
    procedures ranked by relevance and confidence.
    """
    conn = _get_conn()
    results = _db_get_applicable_procedures(conn, current_context, WORKSPACE_ID, limit=limit)
    if not results:
        return 'No applicable procedures found for this context.'
    nl = chr(10)
    lines = [f'Applicable procedures ({len(results)}):']
    for p in results:
        lines.append(
            f'  #{p["id"]} "{p["name"]}" (confidence={p["confidence"]:.2f})'
            f'{nl}    Trigger: {p["trigger_context"][:100]}'
            f'{nl}    Steps:{nl}    {p["steps_md"][:300]}'
        )
    return nl.join(lines)


@mcp.tool()
def get_memory_bundle(memory_ids: list[int]) -> str:
    """Batch-fetch complete memory objects by a list of IDs.

    Layer 3 of the coarse-to-fine retrieval pattern: call this after
    search_memory (Layer 1) and get_recent_memory/get_relations (Layer 2)
    identified the IDs worth inspecting in full detail.

    Returns full memory records as JSON. Missing or cross-workspace IDs
    are silently skipped.
    """
    conn = _get_conn()
    results = _db_get_memory_bundle(conn, memory_ids, WORKSPACE_ID)
    if not results:
        return "No memories found for the given IDs."
    return json.dumps(results, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
def search_facts(query: str, scope: str | None = None, limit: int = 20) -> str:
    """Search stable facts by keyword (matches key or value).

    Complements god_facts (top-ranked) with keyword-driven lookup.
    Use when you remember part of a fact key or value but not the exact name.
    """
    conn = _get_conn()
    results = _db_search_facts(conn, query, WORKSPACE_ID, scope=scope)
    if not results:
        return f"No facts found matching '{query}'."
    results = results[:limit]
    nl = chr(10)
    lines = [f"Facts matching '{query}' ({len(results)}):"]
    for f in results:
        lines.append(
            f"  [{f['scope']}] {f['key']} = {f['value']}"
            f"  (confidence={f['confidence']:.2f}, type={f['confidence_type']})"
        )
    return nl.join(lines)


@mcp.tool()
def list_procedures(status: str = "active", limit: int = 20) -> str:
    """[admin] List all procedures for the current workspace filtered by status.

    status options: active | draft | deprecated
    Use this to review what reusable workflows are available before starting a task.
    """
    conn = _get_conn()
    results = _db_list_procedures_all(conn, WORKSPACE_ID, status=status, limit=limit)
    if not results:
        return f"No {status} procedures found."
    nl = chr(10)
    lines = [f"{status.capitalize()} procedures ({len(results)}):"]
    for p in results:
        lines.append(
            f"  #{p['id']} \"{p['name']}\" (confidence={p['confidence']:.2f})"
            f"{nl}    Trigger: {p['trigger_context'][:120]}"
        )
    return nl.join(lines)


@mcp.tool()
def get_scope_ancestors(scope: str) -> str:
    """Return the ancestor chain for a scope level, from most specific to broadest.

    Hierarchy: session < project < workspace < user < global
    Example: get_scope_ancestors('project') → ['project', 'workspace', 'user', 'global']
    Use to understand which broader scopes will be searched on a scope-fallback query.
    """
    conn = _get_conn()
    ancestors = _db_get_scope_ancestors(conn, scope)
    return json.dumps(ancestors, ensure_ascii=False)


@mcp.tool()
def consolidation_candidates(importance_threshold: float = 2.0, age_days: int = 30) -> str:
    """[admin] Find old memories with low effective importance — candidates for consolidation.

    Returns non-core memories older than age_days with effective_importance < threshold.
    Use in SchedulerTick to surface memories ready for promotion to fact or deletion.
    """
    conn = _get_conn()
    results = _db_find_consolidation_candidates(
        conn, WORKSPACE_ID,
        importance_threshold=importance_threshold,
        age_days=age_days,
    )
    if not results:
        return "No consolidation candidates found."
    nl = chr(10)
    lines = [f"Consolidation candidates ({len(results)}):"]
    for m in results:
        eff = m.get("effective_importance", 0)
        lines.append(
            f"  #{m['id']} [{m['category']}] eff={eff:.3f} — {m['content'][:120]}"
        )
    return nl.join(lines)


@mcp.tool()
def record_procedure_outcome(procedure_id: int, outcome: str, notes: str | None = None) -> str:
    """Record the execution result of a procedure (success / partial / failure).

    Call this after executing a procedure to track its real-world effectiveness.
    The confidence score evolves automatically during nightly maintenance.

    outcome: 'success' | 'partial' | 'failure'
    notes: optional free-text context about what worked or failed
    """
    conn = _get_conn()
    try:
        outcome_id = _db_record_procedure_outcome(conn, procedure_id, WORKSPACE_ID, outcome, notes)
        return f"Outcome recorded (id={outcome_id}). Procedure #{procedure_id} confidence will be updated in next maintenance run."
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool()
def get_procedure_outcomes(procedure_id: int, limit: int = 20) -> str:
    """Return recent execution outcomes for a procedure, newest first.

    Use to audit whether a procedure is performing reliably before deciding
    to promote, demote, or deprecate it.
    """
    conn = _get_conn()
    outcomes = _db_get_procedure_outcomes(conn, procedure_id, WORKSPACE_ID, limit=limit)
    if not outcomes:
        return f"No outcomes recorded for procedure #{procedure_id}."
    return json.dumps(outcomes, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
def get_graph_context(memory_id: int, depth: int = 2) -> str:
    """BFS graph traversal: return a memory and all its neighbors up to `depth` hops.

    This is the neighborhood context tool for deep reasoning on memory chains.
    Use after search_memory or get_memory_bundle identifies a relevant memory —
    explore its knowledge graph neighborhood without N separate get_relations calls.

    Returns JSON with: center, nodes[], edges[], depth_map, total_nodes, total_edges.
    depth=1 → direct neighbors only; depth=2 → neighbors of neighbors (default).
    Handles cycles safely. Traverses both inbound and outbound edges.
    """
    conn = _get_conn()
    result = _db_get_graph_context(conn, memory_id, WORKSPACE_ID, depth=depth)
    if result is None:
        return f"Memory #{memory_id} not found in workspace."
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
def batch_remember(entries_json: str) -> str:
    """Save multiple memories in one call to reduce MCP round-trips.

    Pass a JSON array of entry objects. Each entry supports:
      content (required), category, importance (1-10), scope, tags (array)

    Example:
      [
        {"content": "fixed auth bug", "category": "bugfix", "importance": 8},
        {"content": "API uses JWT", "category": "discovery", "importance": 7}
      ]

    Returns a summary of how many memories were saved vs. skipped as duplicates.
    """
    conn = _get_conn()
    try:
        entries = json.loads(entries_json)
        if not isinstance(entries, list):
            return "Error: input must be a JSON array of entry objects."
    except (json.JSONDecodeError, ValueError) as exc:
        return f"Error: invalid JSON — {exc}"

    ids = _db_batch_remember(conn, entries, CRAFT_SESSION_ID, WORKSPACE_ID)
    saved = sum(1 for i in ids if i is not None)
    dupes = len(ids) - saved
    parts = [f"Batch complete: {saved} saved, {dupes} duplicate(s) skipped."]
    for entry, mid in zip(entries, ids):
        status = f"id={mid}" if mid else "duplicate"
        parts.append(f"  [{status}] {entry.get('content', '')[:80]}")
    return chr(10).join(parts)


# ─── Sprint 8: Procedure Intelligence + Session Quality ──────────────

@mcp.tool()
def top_procedures(limit: int = 10) -> str:
    """Return top procedures ranked by confidence × success_rate × use_count.

    Simmetrico di god_facts per le procedure. Mostra quali procedure sono più
    efficaci in base agli outcome registrati. Solo procedure active.
    Returns JSON array with name, confidence, success_rate, use_count, top_score.
    """
    conn = _get_conn()
    results = _db_get_top_procedures(conn, WORKSPACE_ID, limit=limit)
    if not results:
        return "No active procedures found in workspace."
    return json.dumps(results, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
def consolidate_memories(
    candidate_ids_json: str,
    procedure_name: str,
    trigger_context: str,
    steps_md: str,
    confirm: bool = False,
) -> str:
    """Combine old memories into a procedure and optionally invalidate the originals.

    candidate_ids_json: JSON array of memory IDs to consolidate, e.g. "[3, 7, 12]"
    procedure_name: name for the new (or updated) procedure
    trigger_context: when this procedure should be triggered
    steps_md: markdown steps for the procedure
    confirm: if False (default) → dry-run, no changes made
             if True → creates procedure and marks memories as invalidated

    Safe by default: memories are marked lifecycle_status='invalidated', not deleted.
    Use approve_memory() to reverse if needed.
    """
    conn = _get_conn()
    try:
        candidate_ids = json.loads(candidate_ids_json)
        if not isinstance(candidate_ids, list):
            return "Error: candidate_ids_json must be a JSON array of integers."
    except (json.JSONDecodeError, ValueError) as exc:
        return f"Error: invalid JSON — {exc}"

    result = _db_consolidate_memories(
        conn, candidate_ids, WORKSPACE_ID,
        procedure_name=procedure_name,
        trigger_context=trigger_context,
        steps_md=steps_md,
        confirm=confirm,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def rate_session(summary_id: int, score: float, notes: str = "") -> str:
    """Assign a quality score (0.0–1.0) to a session summary.

    Use at the end of a session to mark how useful, correct, and productive
    the session was. High-quality sessions (score >= 0.7) are retrievable
    via get_high_quality_sessions and exportable as training traces.

    score: float between 0.0 (poor) and 1.0 (excellent)
    notes: optional free-text explanation of the rating
    """
    conn = _get_conn()
    ok = _db_rate_session(conn, summary_id, WORKSPACE_ID, score, notes=notes or None)
    if not ok:
        return f"Error: session summary #{summary_id} not found in workspace."
    return f"Session #{summary_id} rated {score:.2f}." + (f" Notes: {notes}" if notes else "")


# ─── Sprint 9: SessionDB Foundation ──────────────────────────────────

@mcp.tool()
def get_high_quality_sessions(min_score: float = 0.7, limit: int = 10) -> str:
    """Return session summaries with quality_score >= min_score.

    Use to retrieve your best sessions as positive examples for self-improvement,
    fine-tuning, or eval dataset construction (Hermes-style GEPA).
    Sessions without a quality score are excluded.

    Returns JSON array ordered by quality_score descending.
    """
    conn = _get_conn()
    results = _db_get_high_quality_sessions(conn, WORKSPACE_ID, min_score=min_score, limit=limit)
    if not results:
        return f"No sessions found with quality_score >= {min_score}."
    return json.dumps(results, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
def export_session_traces(min_score: float = 0.0, limit: int = 50) -> str:
    """Export session summaries as JSONL for training, eval, or analysis.

    Each line is a JSON object with: id, session_id, summary, decisions,
    quality_score, quality_notes, created_at.
    min_score=0.0 includes all rated sessions; raise it to filter top sessions only.
    Unrated sessions (NULL quality_score) are always excluded.
    limit caps output at N sessions (default 50) to avoid oversized responses.
    """
    conn = _get_conn()
    output = _db_export_session_traces(
        conn, WORKSPACE_ID,
        min_score=min_score if min_score > 0.0 else None,
        limit=limit,
    )
    if not output:
        return "No rated sessions found. Use rate_session() to score sessions first."
    return output


# ─── Tool: lint_wiki — health check for the knowledge base ────────────

@mcp.tool()
def lint_wiki() -> str:
    """[admin] Health-check the knowledge base. Finds contradictions, orphans,
    pending reviews, low-confidence facts, high-importance unlinked memories,
    and lifecycle inconsistencies.

    Returns a structured diagnostic report that can be filed back into
    memory or reviewed manually. Run periodically to keep the knowledge
    base healthy as it grows.
    """
    conn = _get_conn()
    report = _db_lint_wiki(conn, WORKSPACE_ID)

    lines = [f"=== Wiki Health Check — {WORKSPACE_ID} ===\n"]

    # Contradictions
    c = report["contradictions"]
    lines.append(f"Contradictions ({len(c)}):")
    for item in c[:10]:
        lines.append(f"  • prefix '{item['prefix']}': {item['notes']}")
        for k, v in zip(item["keys"][:3], item["values"][:3]):
            lines.append(f"    - {k} = {v}")
    if len(c) > 10:
        lines.append(f"  … and {len(c) - 10} more")
    lines.append("")

    # Orphans (show top 10)
    o = report["orphans"]
    lines.append(f"Orphan memories (no edges) ({len(o)}):")
    for item in o[:10]:
        lines.append(f"  • #{item['id']} [{item['category']}] imp={item['importance']}: {item['preview']}")
    if len(o) > 10:
        lines.append(f"  … and {len(o) - 10} more")
    lines.append("")

    # Pending reviews
    p = report["pending_reviews"]
    lines.append(f"Pending reviews ({len(p)}):")
    if p:
        for item in p[:10]:
            lines.append(f"  • #{item['id']} imp={item['importance']}: {item['preview']}")
    else:
        lines.append("  (none)")
    lines.append("")

    # Low-confidence facts
    lc = report["low_confidence_facts"]
    lines.append(f"Low-confidence facts ({len(lc)}):")
    if lc:
        for item in lc[:10]:
            lines.append(f"  • {item['key']} (conf={item['confidence']}): {item['value']}")
    else:
        lines.append("  (none)")
    lines.append("")

    # High-importance unlinked
    hu = report["unlinked_high_importance"]
    lines.append(f"High-importance memories without edges ({len(hu)}):")
    if hu:
        for item in hu[:10]:
            lines.append(f"  • #{item['id']} imp={item['importance']}: {item['preview']}")
    else:
        lines.append("  (none)")
    lines.append("")

    # Inconsistencies
    ic = report["inconsistencies"]
    lines.append(f"Inconsistencies ({len(ic)}):")
    if ic:
        for item in ic[:10]:
            lines.append(f"  • #{item['id']}: {item['issue']}")
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append(report["summary"])

    return "\n".join(lines)


# ─── Tool: export_wiki — generate markdown wiki from memories ────────

@mcp.tool()
def export_wiki(
    output_dir: str,
    min_importance: int = 3,
    max_pages: int = 500,
) -> str:
    """Export all memories as an interlinked markdown wiki (Obsidian-compatible).

    Generates:
      {output_dir}/index.md    — catalog by category with [[wikilinks]]
      {output_dir}/pages/      — one .md file per memory with YAML frontmatter
      {output_dir}/edges.md    — all graph connections as wikilinks
      {output_dir}/log.md      — append-only export log

    Each page includes YAML frontmatter (id, title, category, importance,
    scope, created, tags, edges count) and [[wikilink]] references to
    connected memories. Open the output directory in Obsidian for graph view.

    Args:
        output_dir: Directory to write the wiki into (will be created)
        min_importance: Minimum importance (1-10) to include (default: 3)
        max_pages: Maximum number of pages to export (default: 500)
    """
    conn = _get_conn()
    result = _db_export_wiki(conn, WORKSPACE_ID, output_dir, min_importance, max_pages)

    lines = [
        f"=== Wiki Exported ===\n",
        f"Output: {result['output_dir']}\n",
        f"Pages: {result['page_count']} ({result['edge_count']} edges, {result['error_count']} errors)\n",
        f"Files created:",
    ]
    for f in result["files"]:
        lines.append(f"  • {f}")
    lines.append(f"\nOpen {result['output_dir']}/index.md in Obsidian to start browsing.")

    return "\n".join(lines)


# ─── Sprint 10: Query Tools ────────────────────────────────────────────


@mcp.tool()
def shortest_path(
    source_id: int,
    target_id: int,
    max_depth: int = 10,
) -> str:
    """[graph] Trova il percorso più breve tra due memorie nel grafo.

    Args:
        source_id: Memory ID di partenza
        target_id: Memory ID di destinazione
        max_depth: Profondità massima BFS (default: 10)

    Returns:
        Percorso come lista di edge, o messaggio "non raggiungibile"
    """
    conn = _get_conn()
    path = _db_shortest_path(conn, source_id, target_id, WORKSPACE_ID, max_depth)
    if path is None:
        return f"Nessun percorso trovato da #{source_id} a #{target_id} (max_depth={max_depth})"
    if path == []:
        return f"Source #{source_id} e target #{target_id} sono lo stesso nodo."

    lines = [f"Percorso da #{source_id} a #{target_id} ({len(path)} hop):\n"]
    for i, e in enumerate(path):
        arrow = f"  {i+1}. #{e['source_id']} --[{e['relation']}]--> #{e['target_id']}"
        lines.append(arrow)
    return "\n".join(lines)


@mcp.tool()
def subgraph(
    memory_id: int,
    depth: int = 2,
) -> str:
    """[graph] Estrae il contesto locale di una memoria (subgraph BFS).

    Args:
        memory_id: Memory ID centrale
        depth: Profondità BFS (default: 2, massimo: 4)

    Returns:
        Nodi e archi del subgrafo
    """
    conn = _get_conn()
    depth = min(depth, 4)
    ctx = _db_get_graph_context(conn, memory_id, WORKSPACE_ID, depth=depth)
    if ctx is None:
        return f"Memory #{memory_id} not found."

    lines = [
        f"Subgraph centered on #{memory_id} (depth={depth}):",
        f"  Nodes: {ctx['total_nodes']}",
        f"  Edges: {ctx['total_edges']}\n",
    ]
    for n in ctx['nodes'][:15]:
        lines.append(f"  #{n['id']} [{n['category']}] {n['content'][:80]}")
    if ctx['total_nodes'] > 15:
        lines.append(f"  ... and {ctx['total_nodes'] - 15} more nodes")

    return "\n".join(lines)


@mcp.tool()
def query_graph(
    tag: str | None = None,
    category: str | None = None,
    min_importance: int = 1,
    limit: int = 20,
) -> str:
    """[graph] Query strutturata: filtra nodi per tag/categoria/importanza + mostra loro edge.

    Args:
        tag: Filtra per tag (es. 'code:python')
        category: Filtra per categoria (decision, discovery, bugfix, feature, refactor, change, note)
        min_importance: Importanza minima (1-10, default: 1)
        limit: Max risultati (default: 20)

    Returns:
        Nodi filtrati con le loro relazioni
    """
    conn = _get_conn()
    result = _db_query_graph(conn, WORKSPACE_ID, tag=tag, category=category,
                             min_importance=min_importance, limit=limit)

    lines = [
        f"Graph query result: {result['count']} nodes, {len(result['edges'])} edges\n",
    ]
    for n in result['nodes']:
        lines.append(f"  #{n['id']} [{n['category']}] importance={n['importance']}")
        lines.append(f"    {n['content'][:120]}")

    if result['edges']:
        lines.append(f"\nEdges ({len(result['edges'])}):")
        for e in result['edges'][:20]:
            lines.append(f"  #{e['source_id']} --[{e['relation']}]--> #{e['target_id']}")

    return "\n".join(lines)


# ─── Sprint 10: Graph Visualization + Export Tools ────────────────────


@mcp.tool()
def get_communities(
    resolution: float = 1.0,
    limit: int = 500,
) -> str:
    """[graph] Rileva comunità semantiche nel grafo usando Leiden clustering.

    Args:
        resolution: Risoluzione clustering (>1=più comunità, <1=meno, default: 1.0)
        limit: Max nodi da considerare (default: 500)

    Returns:
        Comunità rivelate con dimensione e membri principali.
    """
    conn = _get_conn()
    memories = _db_get_memories_for_graph(conn, WORKSPACE_ID, limit=limit)
    edges = _db_get_all_relations(conn, WORKSPACE_ID)

    partition = _cluster(memories, edges, resolution=resolution)
    if not partition:
        return "Nessuna comunità rilevata. Il grafo potrebbe essere vuoto."

    stats = _cluster_stats(partition)
    lines = [f"Community detection (resolution={resolution}):\n"]
    lines.append(f"  Total communities: {len(stats)}")
    lines.append(f"  Clustered nodes: {len(partition)}\n")

    for s in stats[:15]:
        members = s["member_ids"][:5]
        member_str = ", ".join(f"#{m}" for m in members)
        if len(s["member_ids"]) > 5:
            member_str += f"... (+{len(s['member_ids']) - 5} more)"
        lines.append(f"  Community #{s['community_id']}: {s['size']} nodes [{member_str}]")

    if len(stats) > 15:
        lines.append(f"  ... and {len(stats) - 15} more communities")

    return "\n".join(lines)


@mcp.tool()
def export_graph_html(
    output_path: str,
    resolution: float = 1.0,
    limit: int = 500,
) -> str:
    """[graph] Genera grafo HTML interattivo con D3.js.

    I nodi sono colorati per community (Leiden) e dimensionati per importance.
    Include ricerca, filtri per confidence/categoria, legenda.

    Args:
        output_path: Percorso del file HTML da generare
        resolution: Risoluzione clustering (default: 1.0)
        limit: Max nodi (default: 500)

    Returns:
        Conferma con percorso del file generato
    """
    import os
    from pathlib import Path

    conn = _get_conn()
    memories = _db_get_memories_for_graph(conn, WORKSPACE_ID, limit=limit)
    edges = _db_get_all_relations(conn, WORKSPACE_ID)
    partition = _cluster(memories, edges, resolution=resolution)

    html = _graph_viz(memories, edges, partition=partition, title=f"Memory Graph - {WORKSPACE_ID}")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    size_kb = os.path.getsize(out) // 1024
    return f"Graph HTML saved: {out.resolve()} ({size_kb} KB, {len(memories)} nodes, {len(edges)} edges)"


@mcp.tool()
def export_graphml(
    output_path: str,
) -> str:
    """[graph] Esporta il grafo in formato GraphML (compatibile con Gephi, yEd).

    Args:
        output_path: Percorso del file .graphml da generare

    Returns:
        Conferma con percorso del file
    """
    from pathlib import Path

    conn = _get_conn()
    xml = _db_export_graphml(conn, WORKSPACE_ID)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml, encoding="utf-8")

    return f"GraphML saved: {out.resolve()}"


@mcp.tool()
def export_cypher(
    output_path: str,
) -> str:
    """[graph] Esporta il grafo come query Cypher (compatibile con Neo4j).

    Args:
        output_path: Percorso del file .cypher da generare

    Returns:
        Conferma con percorso del file
    """
    from pathlib import Path

    conn = _get_conn()
    cypher = _db_export_cypher(conn, WORKSPACE_ID)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(cypher, encoding="utf-8")

    return f"Cypher saved: {out.resolve()}"


# ─── REST API layer for Craft Memory UI (browser-friendly endpoints) ──

def _resolve_ws(raw: str | None) -> str:
    """Map empty/default workspace_id to the server's configured WORKSPACE_ID."""
    if not raw or raw.strip() in ("", "default"):
        return WORKSPACE_ID
    return raw.strip()

@mcp.custom_route("/api/stats", methods=["GET"])
async def api_stats(request):
    """Workspace stats summary for UI dashboard."""
    from starlette.responses import JSONResponse
    ws = _resolve_ws(request.query_params.get("workspace_id"))
    conn = _get_conn()
    stats = _db_get_memory_stats(conn, ws)
    return JSONResponse(stats)


@mcp.custom_route("/api/memories/recent", methods=["GET"])
async def api_recent_memories(request):
    """Recent memories ranked by importance × time-decay."""
    from starlette.responses import JSONResponse
    ws = _resolve_ws(request.query_params.get("workspace_id"))
    scope = request.query_params.get("scope") or None
    limit = min(int(request.query_params.get("limit", "20")), 100)
    conn = _get_conn()
    results = _db_get_recent_memory(conn, ws, scope, limit)
    return JSONResponse(results or [])


@mcp.custom_route("/api/memories/search", methods=["GET"])
async def api_search_memories(request):
    """Hybrid BM25+Jaccard RRF search. Falls back to recent when no query."""
    from starlette.responses import JSONResponse
    ws = _resolve_ws(request.query_params.get("workspace_id"))
    query = request.query_params.get("q", "").strip()
    scope = request.query_params.get("scope") or None
    limit = min(int(request.query_params.get("limit", "20")), 100)
    conn = _get_conn()
    if query:
        results = _db_hybrid_search(conn, query, ws, scope=scope, limit=limit)
    else:
        results = _db_get_recent_memory(conn, ws, scope, limit)
    return JSONResponse(results or [])


@mcp.custom_route("/api/facts", methods=["GET"])
async def api_facts(request):
    """God facts ranked by confidence × type_bonus × mentions."""
    from starlette.responses import JSONResponse
    ws = _resolve_ws(request.query_params.get("workspace_id"))
    top_n = min(int(request.query_params.get("top_n", "15")), 50)
    conn = _get_conn()
    results = _db_god_facts(conn, ws, top_n)
    return JSONResponse(results or [])


@mcp.custom_route("/api/loops", methods=["GET"])
async def api_loops_get(request):
    """List open loops filtered by scope and status."""
    from starlette.responses import JSONResponse
    ws = _resolve_ws(request.query_params.get("workspace_id"))
    scope = request.query_params.get("scope") or None
    status = request.query_params.get("status", "open")
    conn = _get_conn()
    results = _db_list_open_loops(conn, ws, scope, status=status)
    return JSONResponse(results or [])


@mcp.custom_route("/api/loops", methods=["POST"])
async def api_loops_post(request):
    """Create a new open loop from the UI."""
    from starlette.responses import JSONResponse
    body = await request.json()
    ws = _resolve_ws(body.get("workspace_id"))
    title = (body.get("title") or "").strip()
    if not title:
        return JSONResponse({"error": "title required"}, status_code=400)
    description = body.get("description") or None
    priority = body.get("priority", "medium")
    scope = body.get("scope", "workspace")
    conn = _get_conn()
    loop_id = _db_create_open_loop(conn, CRAFT_SESSION_ID, ws, title, description, priority, scope, CRAFT_SESSION_ID)
    _maybe_checkpoint(conn)
    return JSONResponse({"id": loop_id, "title": title, "priority": priority, "scope": scope, "description": description or ""})


@mcp.custom_route("/api/diff", methods=["GET"])
async def api_diff(request):
    """Memory diff since a given epoch. Defaults to last 24h."""
    import time
    from starlette.responses import JSONResponse
    ws = _resolve_ws(request.query_params.get("workspace_id"))
    since_default = int(time.time()) - 86400
    since = int(request.query_params.get("since", str(since_default)))
    conn = _get_conn()
    result = _db_memory_diff(conn, ws, since)
    return JSONResponse(result)


@mcp.custom_route("/api/relations", methods=["GET"])
async def api_relations(request):
    """Get graph relations — ALL edges for the graph UI, or per-memory details.

    Query params:
      workspace_id (required): target workspace
      memory_id    (optional): if set, returns edges only for that memory + direction;
                               if omitted, returns ALL edges for the workspace
                               (used by Knowledge Graph UI to render the full graph).
      direction    (optional): "in" | "out" | "both" (default "both", used only with memory_id)

    Returns objects normalized for the UI: source, target, role, weight, confidence, relation_type.
    """
    from starlette.responses import JSONResponse
    ws = _resolve_ws(request.query_params.get("workspace_id"))
    memory_id_str = request.query_params.get("memory_id")
    direction = request.query_params.get("direction", "both")

    conn = _get_conn()

    # If memory_id is specified and valid → return per-memory edges
    if memory_id_str and memory_id_str.isdigit():
        results = _db_get_relations(conn, int(memory_id_str), ws, direction)
        return JSONResponse(results or [])

    # No memory_id → return ALL edges for the workspace (graph UI)
    all_edges = _db_get_all_relations(conn, ws)
    return JSONResponse(all_edges or [])


@mcp.custom_route("/api/memories", methods=["POST"])
async def api_remember(request):
    """Store a new memory from the UI."""
    from starlette.responses import JSONResponse
    body = await request.json()
    ws = _resolve_ws(body.get("workspace_id"))
    content = _strip_private(body.get("content", ""))
    if not content:
        return JSONResponse({"error": "empty content"}, status_code=400)
    category = body.get("category", "note")
    importance = int(body.get("importance", 5))
    scope = body.get("scope", "workspace")
    tags = body.get("tags") or None
    conn = _get_conn()
    mem_id = _db_remember(conn, CRAFT_SESSION_ID, ws, content, category, importance, scope, CRAFT_SESSION_ID, tags)
    _maybe_checkpoint(conn)
    if mem_id is None:
        return JSONResponse({"duplicate": True, "id": None})
    return JSONResponse({"id": mem_id, "category": category, "importance": importance, "duplicate": False})


@mcp.custom_route("/api/loops/{loop_id}/close", methods=["POST"])
async def api_close_loop(request):
    """Close an open loop with optional resolution note."""
    from starlette.responses import JSONResponse
    loop_id = int(request.path_params["loop_id"])
    body = await request.json()
    resolution = body.get("resolution") or None
    conn = _get_conn()
    ok = _db_close_open_loop(conn, loop_id, resolution)
    _maybe_checkpoint(conn)
    return JSONResponse({"closed": ok, "id": loop_id})


@mcp.custom_route("/api/handoff", methods=["GET"])
async def api_handoff(request):
    """Generate a structured session handoff pack."""
    from starlette.responses import JSONResponse
    ws = _resolve_ws(request.query_params.get("workspace_id"))
    scope = request.query_params.get("scope") or None
    conn = _get_conn()
    pack = _db_generate_handoff(conn, ws, scope=scope)
    return JSONResponse(pack)


@mcp.custom_route("/api/lint", methods=["GET"])
async def api_lint(request):
    """Run knowledge base health check. Returns structured report."""
    from starlette.responses import JSONResponse
    ws = _resolve_ws(request.query_params.get("workspace_id"))
    conn = _get_conn()
    report = _db_lint_wiki(conn, ws)
    return JSONResponse(report)


@mcp.custom_route("/api/export-wiki", methods=["POST"])
async def api_export_wiki(request):
    """Export memories as Obsidian-compatible markdown wiki."""
    from starlette.responses import JSONResponse
    body = await request.json()
    ws = _resolve_ws(body.get("workspace_id"))
    output_dir = body.get("output_dir", "/tmp/craft-memory-wiki")
    min_importance = int(body.get("min_importance", 3))
    max_pages = int(body.get("max_pages", 500))
    conn = _get_conn()
    result = _db_export_wiki(conn, ws, output_dir, min_importance, max_pages)
    return JSONResponse(result)


def run_server():
    """Start the MCP server with the configured transport."""
    if MCP_TRANSPORT == "http":
        import uvicorn
        from starlette.middleware.cors import CORSMiddleware
        print(f"[craft-memory] v{_VERSION} HTTP server on http://{MCP_HOST}:{MCP_PORT}/mcp", flush=True)
        print(f"[craft-memory] Health:   http://{MCP_HOST}:{MCP_PORT}/health", flush=True)
        print(f"[craft-memory] Metrics:  http://{MCP_HOST}:{MCP_PORT}/metrics", flush=True)
        print(f"[craft-memory] UI API:   http://{MCP_HOST}:{MCP_PORT}/api/*", flush=True)
        print(f"[craft-memory] Workspace: {WORKSPACE_ID}", flush=True)
        app = mcp.streamable_http_app()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
        from pathlib import Path
        from starlette.staticfiles import StaticFiles

        class NoCacheStaticFiles(StaticFiles):
            """StaticFiles that adds no-cache headers at ASGI level (no buffering)."""
            async def __call__(self, scope, receive, send):
                async def send_no_cache(message):
                    if message["type"] == "http.response.start":
                        headers = list(message.get("headers", []))
                        headers.append((b"cache-control", b"no-cache, no-store, must-revalidate"))
                        headers.append((b"pragma", b"no-cache"))
                        message = {**message, "headers": headers}
                    await send(message)
                await super().__call__(scope, receive, send_no_cache)

        _ui_dir = Path(__file__).parent.parent.parent / "Craft-Memory-UI"
        if _ui_dir.exists():
            app.mount("/ui", NoCacheStaticFiles(directory=str(_ui_dir), html=True), name="ui")
            print(f"[craft-memory] UI:       http://{MCP_HOST}:{MCP_PORT}/ui/", flush=True)
        uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
    else:
        print(f"[craft-memory] v{_VERSION} stdio server (workspace: {WORKSPACE_ID})", flush=True)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
