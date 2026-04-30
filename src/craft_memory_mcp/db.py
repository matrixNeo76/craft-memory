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


def _content_hash(content: str) -> str:
    """SHA-256 hash of content for dedup."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _db_path(workspace_id: str) -> Path:
    """Return the database path for a given workspace."""
    base = Path(os.environ.get("CRAFT_MEMORY_DB_DIR", str(Path.home() / ".craft-agent" / "memory")))
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{workspace_id}.db"


_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_DECAY_LAMBDA = float(os.environ.get("CRAFT_MEMORY_DECAY_LAMBDA", "0.005"))


def _effective_importance(importance: int, created_at_epoch: int) -> float:
    """Time-decayed importance score. Older memories score progressively lower."""
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
        key=lambda m: _effective_importance(m["importance"], m["created_at_epoch"]),
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
) -> int:
    """Insert or update a fact. Returns row id."""
    now_iso = _now_iso()
    conn.execute(
        """INSERT INTO facts (key, value, workspace_id, scope, confidence,
                              source_session, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(key, workspace_id, scope)
           DO UPDATE SET value=excluded.value, confidence=excluded.confidence,
                         source_session=excluded.source_session,
                         updated_at=excluded.updated_at""",
        (key, value, workspace_id, scope, confidence,
         source_session, now_iso, now_iso),
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
    """Run all maintenance: cleanup, dedup, trim summaries, VACUUM. Returns stats."""
    deleted_mem = delete_old_memories(conn, workspace_id, days=180, min_importance=3)
    stale_loops = mark_stale_loops(conn, workspace_id, days=30)
    trimmed = trim_session_summaries(conn, workspace_id, keep_last=20)
    deduped = dedup_memories(conn, workspace_id)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.executescript("VACUUM;")
    return {
        "deleted_memories": deleted_mem,
        "stale_loops": stale_loops,
        "trimmed_summaries": trimmed,
        "deduped_memories": deduped,
    }


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
