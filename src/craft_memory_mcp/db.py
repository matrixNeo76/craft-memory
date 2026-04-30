"""
Craft Memory System - Database Layer
SQLite + FTS5 initialization, CRUD operations, and query helpers.

Environment variables:
  CRAFT_MEMORY_DB_DIR - Directory for database files (default: ~/.craft-agent/memory)
"""

import hashlib
import json
import math
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _now_epoch() -> int:
    """Return current UTC time as Unix epoch seconds."""
    return int(datetime.now(timezone.utc).timestamp())


def _content_hash(content: str, kind: str = "memory") -> str:
    """Full SHA-256 hash of content + kind namespace for dedup.

    kind namespace prevents hash collisions across different entity types.
    NOTE: legacy entries used [:16] truncated hashes — mixed state is acceptable
    since UNIQUE(session_id, content_hash) deduplicates per-session only.
    """
    h = hashlib.sha256()
    h.update(content.encode("utf-8"))
    h.update(b"\x00")
    h.update(kind.encode("utf-8"))
    return h.hexdigest()


def _db_path(workspace_id: str) -> Path:
    """Return the database path for a given workspace."""
    base = Path(os.environ.get("CRAFT_MEMORY_DB_DIR", str(Path.home() / ".craft-agent" / "memory")))
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{workspace_id}.db"


_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_DECAY_LAMBDA = float(os.environ.get("CRAFT_MEMORY_DECAY_LAMBDA", "0.005"))

# Graph hygiene: auto-link threshold (BM25 score, negative — more negative = stronger match)
# Default -2.5: strict, precision over recall. Relax to -2.0 after data collection.
_AUTOLINK_THRESHOLD = float(os.environ.get("CRAFT_MEMORY_AUTOLINK_THRESHOLD", "-2.5"))
# Pruning: inferred edges with weight below this AND older than _PRUNE_AGE_DAYS are removed
_PRUNE_WEIGHT_THRESHOLD = float(os.environ.get("CRAFT_MEMORY_PRUNE_WEIGHT_THRESHOLD", "0.3"))
_PRUNE_AGE_DAYS = int(os.environ.get("CRAFT_MEMORY_PRUNE_AGE_DAYS", "60"))


def _effective_importance(importance: int, created_at_epoch: int, is_core: bool = False) -> float:
    """Time-decayed importance score. Core memories are immune to decay."""
    if is_core:
        return float(importance)
    age_days = (_now_epoch() - created_at_epoch) / 86400
    return importance * math.exp(-_DECAY_LAMBDA * age_days)


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply pending schema migrations in version order."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    """)
    conn.commit()

    current = conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_version"
    ).fetchone()[0]

    if current < 1:
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found at {schema_path}")
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        conn.execute("INSERT OR IGNORE INTO schema_version VALUES (1, datetime('now'))")
        conn.commit()
        current = 1

    if _MIGRATIONS_DIR.exists():
        for mf in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            try:
                version = int(mf.stem.split("_")[0])
            except (ValueError, IndexError):
                continue
            if version > current:
                conn.executescript(mf.read_text(encoding="utf-8"))
                conn.execute(
                    "INSERT OR IGNORE INTO schema_version VALUES (?, datetime('now'))",
                    (version,),
                )
                conn.commit()
                current = version


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize database and run pending migrations. Returns connection."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")
    run_migrations(conn)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_connection(workspace_id: str) -> sqlite3.Connection:
    """Get or create a database connection for the workspace."""
    path = _db_path(workspace_id)
    return init_db(path)


# ─── Session CRUD ────────────────────────────────────────────────────

def register_session(
    conn: sqlite3.Connection,
    craft_session_id: str,
    workspace_id: str,
    model_provider: str | None = None,
    model_name: str | None = None,
    user_prompt: str | None = None,
) -> int:
    """Register a new session. Returns the row id."""
    now_iso = _now_iso()
    now_epoch = _now_epoch()
    conn.execute(
        """INSERT OR IGNORE INTO sessions
           (craft_session_id, workspace_id, model_provider, model_name,
            user_prompt, started_at, started_at_epoch, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
        (craft_session_id, workspace_id, model_provider, model_name,
         user_prompt, now_iso, now_epoch),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM sessions WHERE craft_session_id = ?",
        (craft_session_id,),
    ).fetchone()
    return row["id"]


def complete_session(conn: sqlite3.Connection, craft_session_id: str) -> None:
    """Mark a session as completed."""
    now_iso = _now_iso()
    now_epoch = _now_epoch()
    conn.execute(
        """UPDATE sessions
           SET status = 'completed', completed_at = ?, completed_at_epoch = ?
           WHERE craft_session_id = ?""",
        (now_iso, now_epoch, craft_session_id),
    )
    conn.commit()


# ─── Memory CRUD ─────────────────────────────────────────────────────

def remember(
    conn: sqlite3.Connection,
    session_id: str,
    workspace_id: str,
    content: str,
    category: str = "note",
    importance: int = 5,
    scope: str = "workspace",
    source_session: str | None = None,
    tags: list[str] | None = None,
) -> int | None:
    """Store a new episodic memory. Returns row id or None if duplicate."""
    c_hash = _content_hash(content)
    now_iso = _now_iso()
    now_epoch = _now_epoch()
    tags_json = json.dumps(tags) if tags else None
    try:
        cursor = conn.execute(
            """INSERT INTO memories
               (session_id, workspace_id, content, category, importance,
                scope, source_session, content_hash, created_at, created_at_epoch, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, workspace_id, content, category, importance,
             scope, source_session, c_hash, now_iso, now_epoch, tags_json),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Duplicate (workspace_id, content_hash) - silently skip
        return None


def search_memory(
    conn: sqlite3.Connection,
    query: str,
    workspace_id: str,
    scope: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Full-text search on memories. Returns list of matching memories."""
    scope_filter = "AND scope = ?" if scope else ""
    params: list[Any] = [workspace_id]
    if scope:
        params.append(scope)

    # Try FTS5 first with bm25 + importance hybrid ranking
    try:
        fts_query = query.replace('"', '""')  # Escape double quotes
        rows = conn.execute(
            f"""SELECT m.* FROM memories m
                JOIN memories_fts fts ON m.id = fts.rowid
                WHERE memories_fts MATCH ?
                AND m.workspace_id = ?
                {scope_filter}
                ORDER BY (bm25(memories_fts) * -1.0 * 0.7) + (m.importance * 0.3) DESC
                LIMIT ?""",
            [fts_query] + params + [limit],
        ).fetchall()
        if rows:
            return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        pass  # FTS5 query syntax error, fall back to LIKE

    # Fallback: LIKE search — build params independently to avoid scope binding bug
    like_pattern = f"%{query}%"
    like_params: list[Any] = [workspace_id, like_pattern, like_pattern]
    if scope:
        like_params.append(scope)
    rows = conn.execute(
        f"""SELECT * FROM memories
            WHERE workspace_id = ?
            AND (content LIKE ? OR category LIKE ?)
            {scope_filter}
            ORDER BY importance DESC, created_at_epoch DESC
            LIMIT ?""",
        like_params + [limit],
    ).fetchall()
    return [dict(r) for r in rows]


def _rrf_score(
    bm25_ranks: dict[int, int],
    overlap_ranks: dict[int, int],
    k: int = 60,
) -> dict[int, float]:
    """Reciprocal Rank Fusion across two ranking lists.

    bm25_ranks / overlap_ranks: {memory_id: rank_position (0-based)}
    Returns {memory_id: rrf_score}
    """
    scores: dict[int, float] = {}
    for mem_id, rank in bm25_ranks.items():
        scores[mem_id] = scores.get(mem_id, 0.0) + 1.0 / (k + rank + 1)
    for mem_id, rank in overlap_ranks.items():
        scores[mem_id] = scores.get(mem_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    workspace_id: str,
    scope: str | None = None,
    limit: int = 20,
    k: int = 60,
) -> list[dict[str, Any]]:
    """RRF Hybrid Search: fuses BM25 (FTS5) + word-overlap ranking.

    No embeddings required. Both sources use only FTS5 + Python math.
    Falls back to LIKE search if FTS5 pool is empty.
    """
    scope_filter = "AND m.scope = ?" if scope else ""
    base_params: list[Any] = [workspace_id]
    if scope:
        base_params.append(scope)

    pool_limit = limit * 3

    # Source 1: BM25 via FTS5
    bm25_rows: list[dict] = []
    try:
        fts_query = query.replace('"', '""')
        rows = conn.execute(
            f"""SELECT m.*, bm25(memories_fts) AS bm25_score
                FROM memories m
                JOIN memories_fts fts ON m.id = fts.rowid
                WHERE memories_fts MATCH ?
                AND m.workspace_id = ?
                {scope_filter}
                ORDER BY bm25(memories_fts) ASC
                LIMIT ?""",
            [fts_query] + base_params + [pool_limit],
        ).fetchall()
        bm25_rows = [dict(r) for r in rows]
    except sqlite3.OperationalError:
        pass

    # Source 2: Word-overlap (Jaccard-like on query terms)
    query_words = set(re.sub(r"[^a-zA-Z0-9\s]", "", query).lower().split())
    overlap_rows: list[dict] = []
    if bm25_rows and query_words:
        all_ids = [r["id"] for r in bm25_rows]
        id_placeholders = ",".join("?" * len(all_ids))
        candidate_rows = conn.execute(
            f"SELECT id, content FROM memories WHERE id IN ({id_placeholders})",
            all_ids,
        ).fetchall()
        scored: list[tuple[int, float]] = []
        for row in candidate_rows:
            mem_words = set(re.sub(r"[^a-zA-Z0-9\s]", "", row["content"]).lower().split())
            union = len(query_words | mem_words)
            overlap = len(query_words & mem_words) / union if union else 0.0
            scored.append((row["id"], overlap))
        scored.sort(key=lambda x: x[1], reverse=True)
        overlap_rows = [{"id": mid, "overlap": ov} for mid, ov in scored]

    # RRF Fusion
    bm25_ranks = {r["id"]: i for i, r in enumerate(bm25_rows)}
    overlap_ranks = {r["id"]: i for i, r in enumerate(overlap_rows)}
    rrf_scores = _rrf_score(bm25_ranks, overlap_ranks, k=k)

    bm25_by_id = {r["id"]: r for r in bm25_rows}
    sorted_ids = sorted(rrf_scores.keys(), key=lambda mid: rrf_scores[mid], reverse=True)
    results = [bm25_by_id[mid] for mid in sorted_ids if mid in bm25_by_id][:limit]

    # Fallback LIKE if pool is empty
    if not results:
        like_pattern = f"%{query}%"
        like_params: list[Any] = [workspace_id, like_pattern, like_pattern]
        if scope:
            like_params.append(scope)
        scope_like_filter = "AND scope = ?" if scope else ""
        fallback_rows = conn.execute(
            f"""SELECT * FROM memories
                WHERE workspace_id = ? AND (content LIKE ? OR category LIKE ?)
                {scope_like_filter}
                ORDER BY importance DESC, created_at_epoch DESC
                LIMIT ?""",
            like_params + [limit],
        ).fetchall()
        results = [dict(r) for r in fallback_rows]

    return results


def get_recent_memory(
    conn: sqlite3.Connection,
    workspace_id: str,
    scope: str | None = None,
    limit: int = 10,
    max_tokens: int | None = None,
) -> list[dict[str, Any]]:
    """Get most relevant memories, ranked by importance with time decay."""
    scope_filter = "AND scope = ?" if scope else ""
    params: list[Any] = [workspace_id]
    if scope:
        params.append(scope)

    # Fetch a larger pool and re-rank by effective (decayed) importance
    fetch_limit = max(limit * 5, 50)
    rows = conn.execute(
        f"""SELECT * FROM memories
            WHERE workspace_id = ?
            {scope_filter}
            ORDER BY created_at_epoch DESC
            LIMIT ?""",
        params + [fetch_limit],
    ).fetchall()

    scored = sorted(
        [dict(r) for r in rows],
        key=lambda m: _effective_importance(m["importance"], m["created_at_epoch"], bool(m.get("is_core", 0))),
        reverse=True,
    )

    if max_tokens is not None:
        budget = 0
        result = []
        for m in scored[:limit]:
            token_est = len(m.get("content", "")) // 4
            if budget + token_est > max_tokens:
                break
            budget += token_est
            result.append(m)
        return result

    return scored[:limit]


# ─── Facts CRUD ──────────────────────────────────────────────────────

def upsert_fact(
    conn: sqlite3.Connection,
    key: str,
    value: str,
    workspace_id: str,
    scope: str = "workspace",
    confidence: float = 1.0,
    source_session: str | None = None,
    confidence_type: str = "extracted",
) -> int:
    """Insert or update a fact. Returns row id."""
    now_iso = _now_iso()
    conn.execute(
        """INSERT INTO facts (key, value, workspace_id, scope, confidence,
                              confidence_type, source_session, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(key, workspace_id, scope)
           DO UPDATE SET value=excluded.value, confidence=excluded.confidence,
                         confidence_type=excluded.confidence_type,
                         source_session=excluded.source_session,
                         updated_at=excluded.updated_at""",
        (key, value, workspace_id, scope, confidence,
         confidence_type, source_session, now_iso, now_iso),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM facts WHERE key = ? AND workspace_id = ? AND scope = ?",
        (key, workspace_id, scope),
    ).fetchone()
    return row["id"]


def get_facts(
    conn: sqlite3.Connection,
    workspace_id: str,
    scope: str | None = None,
) -> list[dict[str, Any]]:
    """Get all facts for a workspace, optionally filtered by scope."""
    scope_filter = "AND scope = ?" if scope else ""
    params: list[Any] = [workspace_id]
    if scope:
        params.append(scope)

    rows = conn.execute(
        f"""SELECT * FROM facts
            WHERE workspace_id = ?
            {scope_filter}
            ORDER BY key""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def search_facts(
    conn: sqlite3.Connection,
    query: str,
    workspace_id: str,
    scope: str | None = None,
) -> list[dict[str, Any]]:
    """Search facts by key or value."""
    like_pattern = f"%{query}%"
    scope_filter = "AND scope = ?" if scope else ""
    params: list[Any] = [workspace_id, like_pattern, like_pattern]
    if scope:
        params.append(scope)

    rows = conn.execute(
        f"""SELECT * FROM facts
            WHERE workspace_id = ?
            AND (key LIKE ? OR value LIKE ?)
            {scope_filter}
            ORDER BY confidence DESC, key""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


# ─── Open Loops CRUD ─────────────────────────────────────────────────

def create_open_loop(
    conn: sqlite3.Connection,
    session_id: str,
    workspace_id: str,
    title: str,
    description: str | None = None,
    priority: str = "medium",
    scope: str = "workspace",
    source_session: str | None = None,
) -> int:
    """Create a new open loop. Returns row id."""
    now_iso = _now_iso()
    now_epoch = _now_epoch()
    cursor = conn.execute(
        """INSERT INTO open_loops
           (session_id, workspace_id, title, description, priority,
            scope, status, source_session, created_at, created_at_epoch)
           VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)""",
        (session_id, workspace_id, title, description, priority,
         scope, source_session, now_iso, now_epoch),
    )
    conn.commit()
    return cursor.lastrowid


def list_open_loops(
    conn: sqlite3.Connection,
    workspace_id: str,
    scope: str | None = None,
    status: str = "open",
) -> list[dict[str, Any]]:
    """List open loops, optionally filtered by scope and status."""
    scope_filter = "AND scope = ?" if scope else ""
    status_filter = "AND status = ?" if status else ""
    params: list[Any] = [workspace_id]
    if status:
        params.append(status)
    if scope:
        params.append(scope)

    rows = conn.execute(
        f"""SELECT * FROM open_loops
            WHERE workspace_id = ?
            {status_filter}
            {scope_filter}
            ORDER BY
              CASE priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
              END,
              created_at_epoch DESC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def close_open_loop(
    conn: sqlite3.Connection,
    loop_id: int,
    resolution: str | None = None,
) -> bool:
    """Close an open loop with an optional resolution. Returns True if updated."""
    now_iso = _now_iso()
    now_epoch = _now_epoch()
    cursor = conn.execute(
        """UPDATE open_loops
           SET status = 'closed', resolution = ?, closed_at = ?, closed_at_epoch = ?
           WHERE id = ? AND status != 'closed'""",
        (resolution, now_iso, now_epoch, loop_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def update_open_loop(
    conn: sqlite3.Connection,
    loop_id: int,
    workspace_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> bool:
    """Update mutable fields of an open loop. Returns True if updated."""
    valid_priorities = {"low", "medium", "high", "critical"}
    valid_statuses = {"open", "in_progress", "closed", "stale"}

    if priority and priority not in valid_priorities:
        return False
    if status and status not in valid_statuses:
        return False

    sets: list[str] = []
    params: list[Any] = []
    if title is not None:
        sets.append("title = ?")
        params.append(title)
    if description is not None:
        sets.append("description = ?")
        params.append(description)
    if priority is not None:
        sets.append("priority = ?")
        params.append(priority)
    if status is not None:
        sets.append("status = ?")
        params.append(status)

    if not sets:
        return False

    params.extend([loop_id, workspace_id])
    cursor = conn.execute(
        f"UPDATE open_loops SET {', '.join(sets)} WHERE id = ? AND workspace_id = ?",
        params,
    )
    conn.commit()
    return cursor.rowcount > 0


# ─── Session Summaries CRUD ──────────────────────────────────────────

def save_summary(
    conn: sqlite3.Connection,
    session_id: str,
    workspace_id: str,
    summary: str | None = None,
    decisions: list[str] | None = None,
    facts_learned: list[str] | None = None,
    open_loops: list[str] | None = None,
    refs: list[str] | None = None,
    next_steps: str | None = None,
) -> int:
    """Save a session summary (handoff document). Returns row id."""
    now_iso = _now_iso()
    now_epoch = _now_epoch()
    cursor = conn.execute(
        """INSERT INTO session_summaries
           (session_id, workspace_id, summary, decisions, facts_learned,
            open_loops, refs, next_steps, created_at, created_at_epoch)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, workspace_id, summary,
         json.dumps(decisions or []),
         json.dumps(facts_learned or []),
         json.dumps(open_loops or []),
         json.dumps(refs or []),
         next_steps, now_iso, now_epoch),
    )
    conn.commit()
    return cursor.lastrowid


def get_latest_summary(
    conn: sqlite3.Connection,
    workspace_id: str,
) -> dict[str, Any] | None:
    """Get the most recent session summary for a workspace."""
    row = conn.execute(
        """SELECT * FROM session_summaries
           WHERE workspace_id = ?
           ORDER BY created_at_epoch DESC
           LIMIT 1""",
        (workspace_id,),
    ).fetchone()
    if row:
        result = dict(row)
        # Parse JSON fields
        for field in ("decisions", "facts_learned", "open_loops", "refs"):
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return result
    return None


def summarize_scope(
    conn: sqlite3.Connection,
    workspace_id: str,
    scope: str = "workspace",
) -> dict[str, Any]:
    """Generate a summary of a scope: recent memories, key facts, open loops."""
    # Recent memories
    scope_filter = "AND scope = ?" if scope != "all" else ""
    params_mem: list[Any] = [workspace_id]
    if scope != "all":
        params_mem.append(scope)

    recent_rows = conn.execute(
        f"""SELECT * FROM memories
            WHERE workspace_id = ?
            {scope_filter}
            ORDER BY created_at_epoch DESC
            LIMIT 60""",
        params_mem,
    ).fetchall()
    recent = sorted(
        [dict(r) for r in recent_rows],
        key=lambda m: _effective_importance(m["importance"], m["created_at_epoch"]),
        reverse=True,
    )[:20]

    # Key facts
    params_facts: list[Any] = [workspace_id]
    if scope != "all":
        params_facts.append(scope)
    facts = conn.execute(
        f"""SELECT * FROM facts
            WHERE workspace_id = ?
            {scope_filter}
            ORDER BY confidence DESC""",
        params_facts,
    ).fetchall()

    # Open loops
    params_loops: list[Any] = [workspace_id]
    if scope != "all":
        params_loops.append(scope)
    loops = conn.execute(
        f"""SELECT * FROM open_loops
            WHERE workspace_id = ? AND status = 'open'
            {scope_filter}
            ORDER BY created_at_epoch DESC""",
        params_loops,
    ).fetchall()

    # Latest summary
    latest = get_latest_summary(conn, workspace_id)

    return {
        "workspace_id": workspace_id,
        "scope": scope,
        "recent_memories": recent,
        "facts": [dict(r) for r in facts],
        "open_loops": [dict(r) for r in loops],
        "latest_summary": latest,
        "memory_count": len(recent),
        "fact_count": len(facts),
        "open_loop_count": len(loops),
    }


# ─── Maintenance Operations ──────────────────────────────────────────

def mark_stale_loops(
    conn: sqlite3.Connection,
    workspace_id: str,
    days: int = 30,
) -> int:
    """Mark open loops older than N days as stale. Returns count updated."""
    cutoff_epoch = _now_epoch() - (days * 86400)
    cursor = conn.execute(
        """UPDATE open_loops
           SET status = 'stale'
           WHERE workspace_id = ? AND status = 'open'
           AND created_at_epoch < ?""",
        (workspace_id, cutoff_epoch),
    )
    conn.commit()
    return cursor.rowcount


def delete_old_memories(
    conn: sqlite3.Connection,
    workspace_id: str,
    days: int = 180,
    min_importance: int = 3,
) -> int:
    """Delete memories older than N days with importance below threshold."""
    cutoff_epoch = _now_epoch() - (days * 86400)
    cursor = conn.execute(
        """DELETE FROM memories
           WHERE workspace_id = ? AND importance < ?
           AND created_at_epoch < ?""",
        (workspace_id, min_importance, cutoff_epoch),
    )
    conn.commit()
    return cursor.rowcount


def dedup_memories(
    conn: sqlite3.Connection,
    workspace_id: str,
) -> int:
    """Remove duplicate memories (same content hash, keep earliest)."""
    cursor = conn.execute(
        """DELETE FROM memories
           WHERE workspace_id = ? AND id NOT IN (
             SELECT MIN(id) FROM memories
             WHERE workspace_id = ?
             GROUP BY content_hash
           )""",
        (workspace_id, workspace_id),
    )
    conn.commit()
    return cursor.rowcount


def trim_session_summaries(
    conn: sqlite3.Connection,
    workspace_id: str,
    keep_last: int = 20,
) -> int:
    """Delete old session summaries keeping only the most recent N. Returns count deleted."""
    cursor = conn.execute(
        """DELETE FROM session_summaries
           WHERE workspace_id = ? AND id NOT IN (
             SELECT id FROM session_summaries
             WHERE workspace_id = ?
             ORDER BY created_at_epoch DESC
             LIMIT ?
           )""",
        (workspace_id, workspace_id, keep_last),
    )
    conn.commit()
    return cursor.rowcount


def daily_maintenance(
    conn: sqlite3.Connection,
    workspace_id: str,
) -> dict[str, Any]:
    """Run all maintenance: cleanup, dedup, trim summaries, prune inferred edges, VACUUM.

    All operations are conservative (automatic-safe):
    - Only deletes old low-importance memories
    - Only marks stale loops, never closes them
    - Only prunes is_manual=0 edges with weight < _PRUNE_WEIGHT_THRESHOLD and age > _PRUNE_AGE_DAYS
    Returns stats including inferred_edges_pruned for threshold tuning.
    """
    deleted_mem = delete_old_memories(conn, workspace_id, days=180, min_importance=3)
    stale_loops = mark_stale_loops(conn, workspace_id, days=30)
    trimmed = trim_session_summaries(conn, workspace_id, keep_last=20)
    deduped = dedup_memories(conn, workspace_id)
    pruned_edges = prune_inferred_edges(conn, workspace_id)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.executescript("VACUUM;")
    return {
        "deleted_memories": deleted_mem,
        "stale_loops": stale_loops,
        "trimmed_summaries": trimmed,
        "deduped_memories": deduped,
        "inferred_edges_pruned": pruned_edges,
    }


def promote_memory_to_core(
    conn: sqlite3.Connection,
    memory_id: int,
    workspace_id: str,
) -> bool:
    """Mark a memory as core (immune to importance decay). Returns True if updated."""
    cursor = conn.execute(
        "UPDATE memories SET is_core = 1 WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def demote_memory_from_core(
    conn: sqlite3.Connection,
    memory_id: int,
    workspace_id: str,
) -> bool:
    """Remove core flag from a memory. Returns True if updated."""
    cursor = conn.execute(
        "UPDATE memories SET is_core = 0 WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def find_consolidation_candidates(
    conn: sqlite3.Connection,
    workspace_id: str,
    importance_threshold: float = 2.0,
    age_days: int = 30,
) -> list[dict[str, Any]]:
    """Find old memories with low effective importance — candidates for consolidation."""
    cutoff_epoch = _now_epoch() - (age_days * 86400)
    now_epoch = _now_epoch()
    rows = conn.execute(
        """SELECT * FROM (
               SELECT *,
                   importance * EXP(:lam * (:now - created_at_epoch) / -86400.0) AS effective_importance
               FROM memories
               WHERE workspace_id = :ws
               AND is_core = 0
               AND created_at_epoch < :cutoff
           )
           WHERE effective_importance < :threshold
           ORDER BY effective_importance ASC
           LIMIT 50""",
        {"ws": workspace_id, "now": now_epoch, "cutoff": cutoff_epoch,
         "threshold": importance_threshold, "lam": _DECAY_LAMBDA},
    ).fetchall()
    return [dict(r) for r in rows]


def prune_inferred_edges(
    conn: sqlite3.Connection,
    workspace_id: str,
    weight_threshold: float | None = None,
    age_days: int | None = None,
) -> int:
    """Remove weak, old auto-link edges (is_manual=0).

    Only affects edges where is_manual=0 (auto-created by find_similar).
    Manual edges (is_manual=1, default) are never touched.
    Returns count of pruned edges.
    """
    wt = weight_threshold if weight_threshold is not None else _PRUNE_WEIGHT_THRESHOLD
    ad = age_days if age_days is not None else _PRUNE_AGE_DAYS
    cutoff_epoch = _now_epoch() - (ad * 86400)
    cursor = conn.execute(
        """DELETE FROM memory_relations
           WHERE workspace_id = ? AND is_manual = 0
           AND weight < ? AND created_at_epoch <= ?""",
        (workspace_id, wt, cutoff_epoch),
    )
    conn.commit()
    return cursor.rowcount


def search_by_tag(
    conn: sqlite3.Connection,
    tag: str,
    workspace_id: str,
    scope: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search memories by tag. Returns memories that have the given tag."""
    scope_filter = "AND scope = ?" if scope else ""
    params: list[Any] = [workspace_id, f'%"{tag}"%']
    if scope:
        params.append(scope)

    rows = conn.execute(
        f"""SELECT * FROM memories
            WHERE workspace_id = ?
            AND tags LIKE ?
            {scope_filter}
            ORDER BY importance DESC, created_at_epoch DESC
            LIMIT ?""",
        params + [limit],
    ).fetchall()
    return [dict(r) for r in rows]


# ─── Knowledge Graph Layer ───────────────────────────────────────────

def link_memories(
    conn: sqlite3.Connection,
    source_id: int,
    target_id: int,
    relation: str,
    workspace_id: str,
    confidence_type: str = "extracted",
    confidence_score: float = 1.0,
    role: str = "context",
    weight: float = 1.0,
    is_manual: bool = True,
) -> int | None:
    """Create a directed relation between two memories. Returns row id or None if duplicate/invalid.

    is_manual=True (default): manually created edge — never pruned by maintenance.
    is_manual=False: auto-created edge (e.g. from find_similar) — prunable if weight < threshold and old.
    """
    valid_relations = {
        "caused_by", "contradicts", "extends",
        "implements", "supersedes", "semantically_similar_to",
    }
    valid_roles = {"core", "context", "detail", "temporal", "causal"}
    if relation not in valid_relations or role not in valid_roles:
        return None
    now_epoch = _now_epoch()
    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO memory_relations
               (source_id, target_id, relation, confidence_type, confidence_score,
                workspace_id, created_at_epoch, role, weight, is_manual)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (source_id, target_id, relation, confidence_type,
             confidence_score, workspace_id, now_epoch, role, weight, 1 if is_manual else 0),
        )
        conn.commit()
        return cursor.lastrowid if cursor.rowcount > 0 else None
    except sqlite3.Error:
        return None


def get_relations(
    conn: sqlite3.Connection,
    memory_id: int,
    workspace_id: str,
    direction: str = "both",
) -> list[dict[str, Any]]:
    """Get all relations for a memory. direction: 'out' | 'in' | 'both'."""
    rows: list[Any] = []
    if direction in ("out", "both"):
        rows += conn.execute(
            """SELECT mr.id, mr.source_id, mr.target_id, mr.relation,
                      mr.confidence_type, mr.confidence_score, mr.is_manual,
                      m.content AS other_content, m.category AS other_category,
                      'out' AS direction
               FROM memory_relations mr JOIN memories m ON mr.target_id = m.id
               WHERE mr.source_id = ? AND mr.workspace_id = ?""",
            (memory_id, workspace_id),
        ).fetchall()
    if direction in ("in", "both"):
        rows += conn.execute(
            """SELECT mr.id, mr.source_id, mr.target_id, mr.relation,
                      mr.confidence_type, mr.confidence_score, mr.is_manual,
                      m.content AS other_content, m.category AS other_category,
                      'in' AS direction
               FROM memory_relations mr JOIN memories m ON mr.source_id = m.id
               WHERE mr.target_id = ? AND mr.workspace_id = ?""",
            (memory_id, workspace_id),
        ).fetchall()
    return [dict(r) for r in rows]


def get_relations_by_role(
    conn: sqlite3.Connection,
    memory_id: int,
    workspace_id: str,
    role: str,
    direction: str = "both",
) -> list[dict[str, Any]]:
    """Get graph neighbors filtered by semantic role. Ordered by weight DESC."""
    rows: list[Any] = []
    if direction in ("out", "both"):
        rows += conn.execute(
            """SELECT mr.*, m.content AS other_content, 'out' AS direction
               FROM memory_relations mr JOIN memories m ON mr.target_id = m.id
               WHERE mr.source_id = ? AND mr.workspace_id = ? AND mr.role = ?
               ORDER BY mr.weight DESC""",
            (memory_id, workspace_id, role),
        ).fetchall()
    if direction in ("in", "both"):
        rows += conn.execute(
            """SELECT mr.*, m.content AS other_content, 'in' AS direction
               FROM memory_relations mr JOIN memories m ON mr.source_id = m.id
               WHERE mr.target_id = ? AND mr.workspace_id = ? AND mr.role = ?
               ORDER BY mr.weight DESC""",
            (memory_id, workspace_id, role),
        ).fetchall()
    return [dict(r) for r in rows]


def find_similar_memories(
    conn: sqlite3.Connection,
    memory_id: int,
    workspace_id: str,
    top_n: int = 5,
    auto_link: bool = False,
) -> list[dict[str, Any]]:
    """Find memories similar to a given one using FTS5 BM25.

    If auto_link=True, creates INFERRED 'semantically_similar_to' edges only for very
    strong matches (BM25 score < _AUTOLINK_THRESHOLD, default -2.5). Auto-links are
    marked is_manual=False and are prunable by daily_maintenance.
    Returns list of similar memories with scores; each entry includes 'auto_linked' bool.
    """
    source = conn.execute(
        "SELECT content FROM memories WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    ).fetchone()
    if not source:
        return []

    import re as _re_local
    raw = source["content"][:80].split()
    words = [_re_local.sub(r"[^a-zA-Z0-9]", "", w) for w in raw]
    words = [w for w in words if len(w) > 3][:8]
    if not words:
        return []

    fts_query = " OR ".join(words)
    try:
        rows = conn.execute(
            """SELECT m.id, m.content, m.category, m.importance,
                      bm25(memories_fts) AS score
               FROM memories m
               JOIN memories_fts fts ON m.id = fts.rowid
               WHERE memories_fts MATCH ?
               AND m.workspace_id = ?
               AND m.id != ?
               ORDER BY score ASC
               LIMIT ?""",
            [fts_query, workspace_id, memory_id, top_n],
        ).fetchall()
    except sqlite3.OperationalError:
        return []

    results = []
    for row in rows:
        r = dict(row)
        r["similarity_score"] = round(abs(r["score"]), 3)
        linked = False
        if auto_link and r["score"] < _AUTOLINK_THRESHOLD:
            rel_id = link_memories(
                conn, memory_id, row["id"], "semantically_similar_to",
                workspace_id, "inferred",
                min(1.0, abs(r["score"]) / 10.0),
                is_manual=False,
            )
            linked = rel_id is not None
        r["auto_linked"] = linked
        results.append(r)
    return results


def god_facts(
    conn: sqlite3.Connection,
    workspace_id: str,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    """Return the most impactful facts — those most referenced in memories.

    Score = confidence * (1 + mention_count * 0.2)
    EXTRACTED facts outrank INFERRED at same mention count.
    """
    facts = get_facts(conn, workspace_id)
    result = []
    for fact in facts:
        key = fact["key"]
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE workspace_id = ? AND content LIKE ?",
                (workspace_id, f"%{key}%"),
            ).fetchone()[0]
        except sqlite3.Error:
            count = 0
        # EXTRACTED facts get a small bonus over INFERRED
        type_bonus = {"extracted": 1.0, "inferred": 0.8, "ambiguous": 0.5}.get(
            fact.get("confidence_type", "extracted"), 1.0
        )
        score = fact["confidence"] * type_bonus * (1.0 + count * 0.2)
        result.append({**fact, "mention_count": count, "god_score": round(score, 3)})
    result.sort(key=lambda x: x["god_score"], reverse=True)
    return result[:top_n]


def memory_diff(
    conn: sqlite3.Connection,
    workspace_id: str,
    since_epoch: int,
) -> dict[str, Any]:
    """Return what changed in memory since a given Unix epoch timestamp.

    Useful for session-start context injection and handoff summaries.
    """
    since_iso = datetime.fromtimestamp(since_epoch, tz=timezone.utc).isoformat()

    new_memories = conn.execute(
        """SELECT id, category, importance, content, created_at, created_at_epoch, tags
           FROM memories WHERE workspace_id = ? AND created_at_epoch > ?
           ORDER BY created_at_epoch ASC""",
        (workspace_id, since_epoch),
    ).fetchall()

    updated_facts = conn.execute(
        """SELECT key, value, confidence, confidence_type, updated_at
           FROM facts WHERE workspace_id = ? AND updated_at > ?
           ORDER BY updated_at ASC""",
        (workspace_id, since_iso),
    ).fetchall()

    new_loops = conn.execute(
        """SELECT id, title, priority, status, created_at, created_at_epoch
           FROM open_loops WHERE workspace_id = ? AND created_at_epoch > ?
           ORDER BY created_at_epoch ASC""",
        (workspace_id, since_epoch),
    ).fetchall()

    closed_loops = conn.execute(
        """SELECT id, title, resolution, closed_at, closed_at_epoch
           FROM open_loops WHERE workspace_id = ? AND closed_at_epoch > ?
           AND status = 'closed' ORDER BY closed_at_epoch ASC""",
        (workspace_id, since_epoch),
    ).fetchall()

    nm = [dict(r) for r in new_memories]
    uf = [dict(r) for r in updated_facts]
    nl = [dict(r) for r in new_loops]
    cl = [dict(r) for r in closed_loops]

    return {
        "since_epoch": since_epoch,
        "since_iso": since_iso,
        "new_memories": nm,
        "updated_facts": uf,
        "new_loops": nl,
        "closed_loops": cl,
        "summary": (
            f"{len(nm)} new memories, {len(uf)} updated facts, "
            f"{len(nl)} new loops, {len(cl)} closed loops"
        ),
    }


# ─────────────────────────────────────────────────────────────────────

def update_memory(
    conn: sqlite3.Connection,
    memory_id: int,
    workspace_id: str,
    content: str | None = None,
    category: str | None = None,
    importance: int | None = None,
) -> bool:
    """Update fields of an existing memory. Returns True if updated."""
    updates = []
    params: list[Any] = []
    if content is not None:
        updates.append("content = ?")
        params.append(content)
        updates.append("content_hash = ?")
        params.append(_content_hash(content))
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    if importance is not None:
        updates.append("importance = ?")
        params.append(importance)
    if not updates:
        return False
    params += [memory_id, workspace_id]
    cursor = conn.execute(
        f"UPDATE memories SET {', '.join(updates)} WHERE id = ? AND workspace_id = ?",
        params,
    )
    conn.commit()
    return cursor.rowcount > 0


# --- Sprint 1: Observability ---


def get_memory_stats(
    conn,
    workspace_id: str,
    scope=None,
):
    """Aggregate stats for a workspace: counts, averages, edge breakdown."""
    scope_filter = "AND scope = ?" if scope else ""
    base_params = [workspace_id]
    if scope:
        base_params.append(scope)

    rows = conn.execute(
        "SELECT category, COUNT(*) AS cnt FROM memories"
        " WHERE workspace_id = ? " + scope_filter +
        " GROUP BY category",
        base_params,
    ).fetchall()
    by_category = {r["category"]: r["cnt"] for r in rows}
    total_memories = sum(by_category.values())

    core_row = conn.execute(
        "SELECT COUNT(*) FROM memories"
        " WHERE workspace_id = ? AND is_core = 1 " + scope_filter,
        base_params,
    ).fetchone()
    core_memories = core_row[0] if core_row else 0

    avg_row = conn.execute(
        "SELECT AVG(importance) FROM memories WHERE workspace_id = ? " + scope_filter,
        base_params,
    ).fetchone()
    avg_importance = round(avg_row[0] or 0.0, 2)

    loop_scope = "AND scope = ?" if scope else ""
    loop_params = [workspace_id, "open"]
    if scope:
        loop_params.append(scope)
    loop_row = conn.execute(
        "SELECT COUNT(*) FROM open_loops WHERE workspace_id = ? AND status = ? " + loop_scope,
        loop_params,
    ).fetchone()
    open_loops = loop_row[0] if loop_row else 0

    total_edges = conn.execute(
        "SELECT COUNT(*) FROM memory_relations WHERE workspace_id = ?",
        (workspace_id,),
    ).fetchone()[0]

    manual_edges = conn.execute(
        "SELECT COUNT(*) FROM memory_relations WHERE workspace_id = ? AND is_manual = 1",
        (workspace_id,),
    ).fetchone()[0]

    return {
        "total_memories": total_memories,
        "by_category": by_category,
        "core_memories": core_memories,
        "open_loops": open_loops,
        "total_edges": total_edges,
        "manual_edges": manual_edges,
        "inferred_edges": total_edges - manual_edges,
        "avg_importance": avg_importance,
    }


def explain_retrieval(
    conn,
    memory_id: int,
    workspace_id: str,
):
    """Return diagnostic info for a memory: full row + edge graph.

    Returns None if memory not found.
    """
    row = conn.execute(
        "SELECT * FROM memories WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    ).fetchone()
    if row is None:
        return None

    mem = dict(row)
    relations = get_relations(conn, memory_id, workspace_id, direction="both")

    return {
        "id": mem["id"],
        "content": mem["content"],
        "category": mem["category"],
        "importance": mem["importance"],
        "is_core": bool(mem.get("is_core", 0)),
        "scope": mem["scope"],
        "created_at": mem.get("created_at"),
        "tags": mem.get("tags"),
        "relations": relations,
        "relation_count": len(relations),
    }


def generate_handoff(
    conn,
    workspace_id: str,
    scope=None,
    decisions_limit: int = 10,
    facts_limit: int = 15,
    loops_limit: int = 20,
):
    """Generate a structured session-handoff pack.

    Returns recent_decisions, active_open_loops, recent_facts,
    and memory_stats_snapshot.
    """
    scope_filter = "AND scope = ?" if scope else ""
    base_params = [workspace_id]
    if scope:
        base_params.append(scope)

    decision_rows = conn.execute(
        "SELECT id, content, category, importance, created_at, tags FROM memories"
        " WHERE workspace_id = ? AND category = 'decision' " + scope_filter +
        " ORDER BY importance DESC, created_at_epoch DESC LIMIT ?",
        base_params + [decisions_limit],
    ).fetchall()

    loop_scope = "AND scope = ?" if scope else ""
    loop_params = [workspace_id, "open"]
    if scope:
        loop_params.append(scope)
    loop_rows = conn.execute(
        "SELECT id, title, description, priority, created_at FROM open_loops"
        " WHERE workspace_id = ? AND status = ? " + loop_scope +
        " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1"
        " WHEN 'medium' THEN 2 ELSE 3 END, created_at_epoch DESC LIMIT ?",
        loop_params + [loops_limit],
    ).fetchall()

    fact_scope = "AND scope = ?" if scope else ""
    fact_params = [workspace_id]
    if scope:
        fact_params.append(scope)
    fact_rows = conn.execute(
        "SELECT key, value, scope, confidence, confidence_type, updated_at FROM facts"
        " WHERE workspace_id = ? " + fact_scope +
        " ORDER BY confidence DESC, key LIMIT ?",
        fact_params + [facts_limit],
    ).fetchall()

    return {
        "generated_at": _now_iso(),
        "scope": scope or "workspace",
        "recent_decisions": [dict(r) for r in decision_rows],
        "active_open_loops": [dict(r) for r in loop_rows],
        "recent_facts": [dict(r) for r in fact_rows],
        "memory_stats_snapshot": get_memory_stats(conn, workspace_id, scope=scope),
    }
