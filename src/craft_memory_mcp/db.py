"""
Craft Memory System - Database Layer
SQLite + FTS5 initialization, CRUD operations, and query helpers.

Environment variables:
  CRAFT_MEMORY_DB_DIR - Directory for database files (default: ~/.craft-agent/memory)
"""

import hashlib
import html
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

# Parole corte ma semanticamente ricche da preservare nell'estrazione FTS
_SHORT_WORD_WHITELIST: set[str] = {
    "fix", "git", "api", "db", "ui", "ux", "url", "cli", "mcp", "ssh",
    "tls", "ssl", "dns", "sql", "pdf", "xml", "csv", "json", "yaml",
    "toml", "aws", "gcp", "vpc", "iot", "sdk", "rpc", "gpu", "cpu",
    "ram", "vpn", "lan", "wan", "www", "cdn", "img", "svg", "png",
    "jpg", "gif", "ico", "css", "html", "jsx", "tsx", "npm", "yarn",
    "dot", "env", "cfg", "yml", "log", "pid", "os", "ip", "io",
    "pr", "feat", "docs", "refactor", "bug", "hotfix", "wip",
    "cicd", "auth", "oauth", "jwt", "oidc", "http", "https",
    "smtp", "pop3", "imap", "tcp", "udp", "dhcp", "dns",
}


def _extract_fts_keywords(text: str, max_words: int = 8) -> str | None:
    """Extract FTS5-safe keywords from text for similarity search.

    Returns an OR-joined query string or None if no suitable keywords found.
    Text window increased to 200 chars (was 80) to capture more content
    past structured headers like "DECISION:" or "FIX:".
    Short words (2-3 chars) are preserved if in _SHORT_WORD_WHITELIST.
    """
    raw = text[:200].split()
    words = [re.sub(r"[^a-zA-Z0-9]", "", w) for w in raw]
    words = [w for w in words if len(w) > 2 or w.lower() in _SHORT_WORD_WHITELIST][:max_words]
    if not words:
        return None
    return " OR ".join(words)


def _auto_link_similar(
    conn: sqlite3.Connection,
    memory_id: int,
    workspace_id: str,
    limit: int = 3,
) -> int:
    """Find similar memories and create INFERRED semantically_similar_to edges.

    Called after a new memory is inserted. Uses FTS5 BM25 to find the top-N
    most similar memories (by shared keywords) and links them. No absolute
    threshold — the FTS5 MATCH already guarantees keyword overlap, and BM25
    ordering ensures only the most relevant ones are linked.

    Edges are is_manual=False (prunable by maintenance).
    Returns the number of edges created.
    """
    source = conn.execute(
        "SELECT content FROM memories WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    ).fetchone()
    if not source:
        return 0

    fts_query = _extract_fts_keywords(source["content"])
    if not fts_query:
        return 0

    try:
        rows = conn.execute(
            """SELECT m.id, bm25(memories_fts) AS score
               FROM memories m
               JOIN memories_fts fts ON m.id = fts.rowid
               WHERE memories_fts MATCH ?
               AND m.workspace_id = ?
               AND m.id != ?
               AND (m.lifecycle_status = 'active' OR m.lifecycle_status IS NULL)
               ORDER BY score ASC
               LIMIT ?""",
            [fts_query, workspace_id, memory_id, limit],
        ).fetchall()
    except sqlite3.OperationalError:
        return 0

    # Skip linking if BM25 score is not at least mildly negative,
    # meaning the top match shares at least some meaningful overlap.
    # This prevents linking to noise from very short or generic keywords.
    if not rows:
        return 0
    best_score = rows[0]["score"]
    if best_score >= -1.0:
        return 0

    linked = 0
    for row in rows:
        score = abs(row["score"])
        # Forward edge: new memory → similar memory
        rel_id = link_memories(
            conn, memory_id, row["id"], "semantically_similar_to",
            workspace_id, "inferred",
            round(min(1.0, score / 8.0), 3),
            role="context", weight=round(min(1.0, score / 8.0), 3),
            is_manual=False,
        )
        if rel_id is not None:
            linked += 1

        # Reverse edge: similar memory → new memory (if it doesn't exist yet)
        # This ensures the knowledge graph is bidirectional even when
        # _auto_link_similar is called only for new memories.
        existing_reverse = conn.execute(
            """SELECT id FROM memory_relations
               WHERE source_id = ? AND target_id = ? AND workspace_id = ?
               AND relation = 'semantically_similar_to'""",
            (row["id"], memory_id, workspace_id),
        ).fetchone()
        if not existing_reverse:
            rev_id = link_memories(
                conn, row["id"], memory_id, "semantically_similar_to",
                workspace_id, "inferred",
                round(min(1.0, score / 8.0), 3),
                role="context", weight=round(min(1.0, score / 8.0), 3),
                is_manual=False,
            )
            if rev_id is not None:
                linked += 1

    if linked:
        conn.commit()
    return linked


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
    force: bool = False,
    compress_level: int = 0,
) -> int | None:
    """Store a new episodic memory. Returns row id or None if duplicate.

    After inserting, automatically links to similar memories via FTS5 BM25
    similarity search. Edges are is_manual=False (prunable by daily maintenance).

    Args:
        force: If True, bypasses dedup by appending timestamp to hash.
        compress_level: 0=no compression, 1=dictionary compression (~40%).
    """
    if compress_level > 0:
        from craft_memory_mcp.compress import compress as _compress
        content = _compress(content, level=compress_level)
    c_hash = _content_hash(content + str(_now_epoch()) if force else content)
    now_iso = _now_iso()
    now_epoch = _now_epoch()
    tags_json = json.dumps(tags) if tags else None
    try:
        cursor = conn.execute(
            """INSERT INTO memories
               (session_id, workspace_id, content, category, importance,
                scope, source_session, content_hash, created_at, created_at_epoch,
                tags, compressed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, workspace_id, content, category, importance,
             scope, source_session, c_hash, now_iso, now_epoch, tags_json,
             compress_level),
        )
        conn.commit()
        new_id = cursor.lastrowid
        # Auto-link similar memories (fire-and-forget, best-effort)
        if new_id:
            _auto_link_similar(conn, new_id, workspace_id)
        return new_id
    except sqlite3.IntegrityError as exc:
        err_str = str(exc)
        if "UNIQUE" in err_str and "content_hash" in err_str:
            # Duplicate (workspace_id, content_hash) — silently skip
            return None
        # FK or CHECK constraint violation — re-raise with context
        raise ValueError(f"Cannot save memory: {err_str} (category='{category}', importance={importance}, session='{session_id}')") from exc


def _decompress_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Decompress content of memories that were stored compressed."""
    try:
        from craft_memory_mcp.compress import decompress as _decompress
        for r in results:
            if r.get("compressed", 0) > 0:
                r["content"] = _decompress(r["content"])
    except ImportError:
        pass  # compress module not available
    return results


def search_memory(
    conn: sqlite3.Connection,
    query: str,
    workspace_id: str,
    scope: str | None = None,
    limit: int = 20,
    include_inactive: bool = False,
    decompress: bool = True,
) -> list[dict[str, Any]]:
    """Full-text search on memories. Returns list of matching memories.

    By default excludes invalidated/superseded/needs_review memories.
    Pass include_inactive=True to include all lifecycle statuses.
    """
    scope_filter = "AND scope = ?" if scope else ""
    lifecycle_filter = "" if include_inactive else "AND (lifecycle_status = 'active' OR lifecycle_status IS NULL)"
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
                {lifecycle_filter}
                ORDER BY (bm25(memories_fts) * -1.0 * 0.7) + (m.importance * 0.3) DESC
                LIMIT ?""",
            [fts_query] + params + [limit],
        ).fetchall()
        if rows:
            results = [dict(r) for r in rows]
            if decompress:
                results = _decompress_results(results)
            return results
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
            {lifecycle_filter}
            ORDER BY importance DESC, created_at_epoch DESC
            LIMIT ?""",
        like_params + [limit],
    ).fetchall()
    results = [dict(r) for r in rows]
    if decompress:
        results = _decompress_results(results)
    return results


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
    decompress: bool = True,
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

    if decompress:
        results = _decompress_results(results)
    return results


def get_recent_memory(
    conn: sqlite3.Connection,
    workspace_id: str,
    scope: str | None = None,
    limit: int = 10,
    max_tokens: int | None = None,
    include_inactive: bool = False,
    decompress: bool = True,
) -> list[dict[str, Any]]:
    """Get most relevant memories, ranked by importance with time decay.

    By default excludes invalidated/superseded/needs_review memories.
    Pass include_inactive=True to include all lifecycle statuses.
    """
    scope_filter = "AND scope = ?" if scope else ""
    lifecycle_filter = "" if include_inactive else "AND (lifecycle_status = 'active' OR lifecycle_status IS NULL)"
    params: list[Any] = [workspace_id]
    if scope:
        params.append(scope)

    # Fetch a larger pool and re-rank by effective (decayed) importance
    fetch_limit = max(limit * 5, 50)
    rows = conn.execute(
        f"""SELECT * FROM memories
            WHERE workspace_id = ?
            {scope_filter}
            {lifecycle_filter}
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

    results = scored[:limit]
    if decompress:
        results = _decompress_results(results)
    return results


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

    # Get total count first
    count_row = conn.execute(
        f"""SELECT count(*) AS cnt FROM memories
            WHERE workspace_id = ?
            {scope_filter}""",
        params_mem,
    ).fetchone()
    total_count = count_row["cnt"] if count_row else 0

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
        "total_memory_count": len(recent_rows),
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
    needs_review_row = conn.execute(
        "SELECT COUNT(*) FROM memories WHERE workspace_id = ? AND lifecycle_status = 'needs_review'",
        (workspace_id,),
    ).fetchone()
    # Sprint 6: evolve procedure confidence from recorded outcomes
    try:
        procedures_updated = _update_all_procedure_confidences(conn, workspace_id)
    except Exception:
        procedures_updated = 0
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.executescript("VACUUM;")
    return {
        "deleted_memories": deleted_mem,
        "stale_loops": stale_loops,
        "trimmed_summaries": trimmed,
        "deduped_memories": deduped,
        "inferred_edges_pruned": pruned_edges,
        "needs_review": needs_review_row[0] if needs_review_row else 0,
        "procedures_confidence_updated": procedures_updated,
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


def get_all_relations(
    conn: sqlite3.Connection,
    workspace_id: str,
) -> list[dict[str, Any]]:
    """Return ALL relations for a workspace, normalized for graph UI.

    Returns objects with source_id -> source, target_id -> target,
    plus role, weight, confidence, and relation_type for visualization.
    Used by the Knowledge Graph UI to render the full graph.
    """
    rows = conn.execute(
        """SELECT mr.id, mr.source_id, mr.target_id, mr.relation AS relation_type,
                  mr.confidence_type AS confidence, mr.confidence_score,
                  mr.role, mr.weight, mr.is_manual,
                  m1.content AS source_content, m2.content AS target_content
           FROM memory_relations mr
           JOIN memories m1 ON mr.source_id = m1.id
           JOIN memories m2 ON mr.target_id = m2.id
           WHERE mr.workspace_id = ?""",
        (workspace_id,),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        # Normalize for UI: source_id -> source, target_id -> target
        d["source"] = d.pop("source_id")
        d["target"] = d.pop("target_id")
        # UI expects r.relation (not r.relation_type) for edge label
        d["relation"] = d.get("relation_type", "semantically_similar_to")
        result.append(d)
    return result


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


# --- Sprint 2: Temporal Invalidation + Review Flag ---


def invalidate_memory(
    conn: sqlite3.Connection,
    memory_id: int,
    reason: str,
    workspace_id: str,
    replaced_by_id: int | None = None,
) -> bool:
    """Mark a memory as invalidated.

    Sets lifecycle_status='invalidated', valid_to=now, and optionally
    links superseded_by to the replacement memory.
    Returns True if the memory was found and updated, False otherwise.
    """
    row = conn.execute(
        "SELECT id FROM memories WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    ).fetchone()
    if row is None:
        return False
    conn.execute(
        """UPDATE memories
           SET lifecycle_status = 'invalidated',
               valid_to = ?,
               superseded_by = COALESCE(?, superseded_by)
           WHERE id = ? AND workspace_id = ?""",
        (_now_epoch(), replaced_by_id, memory_id, workspace_id),
    )
    conn.commit()
    return True


def get_memory_history(
    conn: sqlite3.Connection,
    memory_id: int,
    workspace_id: str,
) -> list[dict[str, Any]]:
    """Return the supersession chain starting from memory_id.

    Follows superseded_by links forward. Returns a list of memory dicts
    from oldest (given memory_id) to newest (final version with no superseded_by).
    """
    chain: list[dict[str, Any]] = []
    current_id: int | None = memory_id
    visited: set[int] = set()
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        row = conn.execute(
            "SELECT * FROM memories WHERE id = ? AND workspace_id = ?",
            (current_id, workspace_id),
        ).fetchone()
        if row is None:
            break
        m = dict(row)
        chain.append(m)
        current_id = m.get("superseded_by")
    return chain


def flag_for_review(
    conn: sqlite3.Connection,
    memory_id: int,
    reason: str,
    workspace_id: str,
) -> bool:
    """Mark a memory as needing human review (lifecycle_status='needs_review').

    Returns True if the memory was found and updated, False otherwise.
    """
    row = conn.execute(
        "SELECT id FROM memories WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    ).fetchone()
    if row is None:
        return False
    conn.execute(
        "UPDATE memories SET lifecycle_status = 'needs_review' WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    )
    conn.commit()
    return True


def list_needs_review(
    conn: sqlite3.Connection,
    workspace_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return memories with lifecycle_status='needs_review', ordered by importance desc."""
    rows = conn.execute(
        """SELECT * FROM memories
           WHERE workspace_id = ? AND lifecycle_status = 'needs_review'
           ORDER BY importance DESC, created_at_epoch DESC
           LIMIT ?""",
        (workspace_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def approve_memory(
    conn: sqlite3.Connection,
    memory_id: int,
    workspace_id: str,
) -> bool:
    """Restore lifecycle_status to 'active' for a memory under review.

    Returns True if the memory was found and updated, False otherwise.
    """
    row = conn.execute(
        "SELECT id FROM memories WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    ).fetchone()
    if row is None:
        return False
    conn.execute(
        "UPDATE memories SET lifecycle_status = 'active' WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    )
    conn.commit()
    return True


# --- Sprint 3: Boundary Detection Policy ---

import re as _re
from enum import Enum


class MemoryClass(str, Enum):
    """Classification of a memory event into the most appropriate storage strategy."""
    DISCARD = "discard"
    EPISODIC = "episodic"
    FACT_CANDIDATE = "fact_candidate"
    OPEN_LOOP = "open_loop"
    PROCEDURE_CANDIDATE = "procedure_candidate"
    CORE_CANDIDATE = "core_candidate"


_TRIVIAL_PATTERN = _re.compile(
    r"^(ok|yes|no|done|got it|understood|sure|thanks|ok thanks|noted|agreed|correct|right)[\.\!\?]*$",
    _re.IGNORECASE,
)

_LOOP_KEYWORDS = frozenset({
    "todo", "fixme", "need to", "must fix", "pending",
    "blocked", "waiting for", "follow up", "follow-up",
})

_CORE_KEYWORDS = frozenset({
    "always", "never", "critical", "invariant",
    "rule:", "policy:", "must always", "must never",
})

_FACT_KEYWORDS = frozenset({
    "the db", "the api", "the url", "the port", "the key", "the version",
    "is set to", "is configured", "equals", "means", "defined as", "is always",
})


def classify_memory_event(
    content: str,
    context_signals: dict | None = None,
    conn: sqlite3.Connection | None = None,
    workspace_id: str | None = None,
) -> tuple["MemoryClass", str]:
    """Classify a memory event into the most appropriate storage strategy.

    Returns a (MemoryClass, reason) tuple. Rules are applied in priority order:
    DISCARD > OPEN_LOOP > PROCEDURE_CANDIDATE > CORE_CANDIDATE > FACT_CANDIDATE > EPISODIC.

    context_signals: optional dict with 'importance' (int 1-10) and 'category' (str).
    conn/workspace_id: optional — reserved for future FTS5 frequency checks.
    """
    signals = context_signals or {}
    importance: int = int(signals.get("importance", 5))
    content_stripped = content.strip()
    content_lower = content_stripped.lower()

    # Rule 1: Too short → discard
    if len(content_stripped) < 15:
        return MemoryClass.DISCARD, "content too short (<15 chars)"

    # Rule 2: Trivial conversational filler → discard
    if _TRIVIAL_PATTERN.match(content_lower):
        return MemoryClass.DISCARD, "trivial conversational response"

    # Rule 3: Task/todo/blocked keywords → open_loop
    if any(kw in content_lower for kw in _LOOP_KEYWORDS):
        return MemoryClass.OPEN_LOOP, "loop/task keyword detected"

    # Rule 4: Multi-step procedure pattern → procedure_candidate
    step_hits = sum(
        1 for i in range(1, 6) if f"step {i}" in content_lower
    )
    keyword_hits = sum(1 for kw in ("first:", "then:", "finally:", "workflow:", "process:") if kw in content_lower)
    if step_hits >= 2 or keyword_hits >= 2:
        return MemoryClass.PROCEDURE_CANDIDATE, "multi-step procedure pattern detected"

    # Rule 5: High importance or invariant keywords → core_candidate
    if importance >= 8 or any(kw in content_lower for kw in _CORE_KEYWORDS):
        return MemoryClass.CORE_CANDIDATE, "high importance or invariant keyword"

    # Rule 6: Factual statement patterns → fact_candidate
    if any(kw in content_lower for kw in _FACT_KEYWORDS):
        return MemoryClass.FACT_CANDIDATE, "factual statement pattern detected"

    # Default → episodic memory
    return MemoryClass.EPISODIC, "general episodic memory"


# --- Sprint 4: Procedural Memory ---


def save_procedure(
    conn: sqlite3.Connection,
    workspace_id: str,
    name: str,
    trigger_context: str,
    steps_md: str,
    confidence: float = 0.5,
    source_memory_ids: list[int] | None = None,
    status: str = "active",
    verify_command: str | None = None,
    acceptance_criteria: str | None = None,
    spec_text: str | None = None,
    mode: str = "manual",
) -> int:
    """Upsert a procedure (keyed by workspace_id + name). Returns procedure id.

    If a procedure with the same name already exists in the workspace it is
    updated in place; the FTS5 index is kept in sync via explicit delete/insert.

    Args:
        mode: "manual" (default) | "cavekit" (spec-driven with verify_command)
        verify_command: Shell command to verify the procedure succeeded
        acceptance_criteria: Criteria that define success
        spec_text: Original spec that generated this procedure (cavekit mode)
    """
    now_epoch = _now_epoch()
    src_ids_json = json.dumps(source_memory_ids) if source_memory_ids else None

    existing = conn.execute(
        "SELECT id FROM procedures WHERE workspace_id = ? AND name = ?",
        (workspace_id, name),
    ).fetchone()

    if existing:
        proc_id: int = existing["id"]
        # Read OLD FTS values before updating — FTS5 delete requires exact old content
        old_row = conn.execute(
            "SELECT name, trigger_context, steps_md FROM procedures WHERE id = ?",
            (proc_id,),
        ).fetchone()
        conn.execute(
            """UPDATE procedures
               SET trigger_context = ?, steps_md = ?, confidence = ?,
                   source_memory_ids = ?, updated_at_epoch = ?, status = ?,
                   verify_command = ?, acceptance_criteria = ?, spec_text = ?,
                   mode = ?
               WHERE id = ?""",
            (trigger_context, steps_md, confidence, src_ids_json, now_epoch, status,
             verify_command, acceptance_criteria, spec_text, mode, proc_id),
        )
        # Sync FTS5: DELETE old row by rowid, then insert updated content
        conn.execute("DELETE FROM procedures_fts WHERE rowid = ?", (proc_id,))
        conn.execute(
            "INSERT INTO procedures_fts(rowid, name, trigger_context, steps_md) VALUES (?, ?, ?, ?)",
            (proc_id, name, trigger_context, steps_md),
        )
    else:
        cursor = conn.execute(
            """INSERT INTO procedures
               (workspace_id, name, trigger_context, steps_md, confidence,
                source_memory_ids, created_at_epoch, updated_at_epoch, status,
                verify_command, acceptance_criteria, spec_text, mode)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (workspace_id, name, trigger_context, steps_md, confidence,
             src_ids_json, now_epoch, now_epoch, status,
             verify_command, acceptance_criteria, spec_text, mode),
        )
        proc_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO procedures_fts(rowid, name, trigger_context, steps_md) VALUES (?, ?, ?, ?)",
            (proc_id, name, trigger_context, steps_md),
        )

    conn.commit()
    return proc_id


def search_procedures(
    conn: sqlite3.Connection,
    query: str,
    workspace_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """FTS5 search across procedure name, trigger_context, and steps_md.

    Deprecated procedures are always excluded.
    Falls back to LIKE search if the FTS5 query is malformed.
    """
    try:
        fts_query = query.replace('"', '""')
        rows = conn.execute(
            """SELECT p.* FROM procedures p
               JOIN procedures_fts fts ON p.id = fts.rowid
               WHERE procedures_fts MATCH ?
               AND p.workspace_id = ?
               AND p.status != 'deprecated'
               ORDER BY rank, p.confidence DESC
               LIMIT ?""",
            (fts_query, workspace_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        like = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM procedures
               WHERE workspace_id = ?
               AND status != 'deprecated'
               AND (name LIKE ? OR trigger_context LIKE ? OR steps_md LIKE ?)
               ORDER BY confidence DESC
               LIMIT ?""",
            (workspace_id, like, like, like, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_applicable_procedures(
    conn: sqlite3.Connection,
    current_context: str,
    workspace_id: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return the most applicable active procedures for the given context.

    Uses FTS5 search then re-ranks by confidence (descending). Only active
    procedures are returned (draft and deprecated are excluded).
    """
    candidates = search_procedures(conn, current_context, workspace_id, limit=limit * 3)
    active = [r for r in candidates if r.get("status") == "active"]
    active.sort(key=lambda r: r.get("confidence", 0.5), reverse=True)
    return active[:limit]


# ---------------------------------------------------------------------------
# Sprint 10: Cavekit Workflow
# ---------------------------------------------------------------------------


def spec_to_plan(spec_text: str, name: str | None = None) -> dict[str, Any]:
    """Converts a natural language spec into a structured plan with tasks.

    This is a template-based parser that extracts tasks from common spec
    patterns. For full spec-to-plan conversion, use an LLM with this
    function as the structured output schema.

    Args:
        spec_text: The specification text
        name: Optional plan name (default: first line of spec)

    Returns:
        dict with: name, spec, tasks[], verify_command
    """
    lines = spec_text.strip().split("\n")
    title = name or (lines[0][:60] if lines else "Untitled Plan")

    tasks = []
    verify_commands = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # Task: numbered items like "1. Do X" or "- [ ] Do X"
        task_match = None
        for prefix_pattern in [
            r"^\d+[\.\)]\s+(.+)",
            r"^-\s+\[.\]\s+(.+)",
            r"^\*\s+(.+)",
            r"^Task\s+\d+[\:\.]\s+(.+)",
        ]:
            import re as _re
            m = _re.match(prefix_pattern, line)
            if m:
                task_match = m.group(1)
                break

        if task_match:
            # Extract verify command if present in brackets
            verify = ""
            criteria = ""
            vmatch = _re.search(r"\[verify:\s*(.+?)\]", task_match)
            if vmatch:
                verify = vmatch.group(1).strip()
                task_match = _re.sub(r"\[verify:\s*.+?\]", "", task_match).strip()
            cmatch = _re.search(r"\[criteria:\s*(.+?)\]", task_match)
            if cmatch:
                criteria = cmatch.group(1).strip()
                task_match = _re.sub(r"\[criteria:\s*.+?\]", "", task_match).strip()

            tasks.append({
                "id": len(tasks) + 1,
                "title": task_match[:100],
                "verify_command": verify,
                "acceptance_criteria": criteria or f"{task_match[:60]} completed successfully",
                "status": "pending",
            })
            if verify:
                verify_commands.append(verify)

    if not tasks:
        # Fallback: whole spec as single task
        tasks.append({
            "id": 1,
            "title": spec_text[:100],
            "verify_command": "",
            "acceptance_criteria": "Spec implemented successfully",
            "status": "pending",
        })

    return {
        "name": title,
        "spec": spec_text,
        "tasks": tasks,
        "total_tasks": len(tasks),
        "verify_command": " && ".join(verify_commands) if verify_commands else "",
    }


def plan_to_tasks_text(plan: dict[str, Any]) -> str:
    """Format a plan as readable text with task checklist."""
    lines = [
        f"# Plan: {plan.get('name', 'Untitled')}",
        f"Total tasks: {plan['total_tasks']}",
        "",
    ]

    if plan.get("spec"):
        lines.append("## Spec")
        lines.append(plan["spec"][:300])
        lines.append("")

    lines.append("## Tasks")
    for t in plan.get("tasks", []):
        status_mark = "[ ]" if t.get("status") == "pending" else "[x]"
        lines.append(f"  {status_mark} Task #{t['id']}: {t['title']}")
        if t.get("acceptance_criteria"):
            lines.append(f"     AC: {t['acceptance_criteria']}")
        if t.get("verify_command"):
            lines.append(f"     Verify: {t['verify_command']}")
        lines.append("")

    if plan.get("verify_command"):
        lines.append(f"Global verify: {plan['verify_command']}")

    return "\n".join(lines)


def list_procedures(
    conn: sqlite3.Connection,
    workspace_id: str,
    status: str = "active",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List procedures for a workspace filtered by status, ordered by confidence desc."""
    rows = conn.execute(
        """SELECT * FROM procedures
           WHERE workspace_id = ? AND status = ?
           ORDER BY confidence DESC, updated_at_epoch DESC
           LIMIT ?""",
        (workspace_id, status, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Sprint 5 — Hierarchical Scopes + Coarse-to-Fine Retrieval
# ---------------------------------------------------------------------------

_SCOPE_ORDER = ["session", "project", "workspace", "user", "global"]


def get_scope_ancestors(conn: sqlite3.Connection, scope: str) -> list[str]:
    """Return scope + all ancestor scopes in order from specific to broad.

    Uses scope_hierarchy table when available; falls back to the hardcoded
    canonical order so the function works even before migration 010 runs.
    """
    try:
        rows = conn.execute(
            "SELECT scope, level FROM scope_hierarchy ORDER BY level"
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []

    if rows:
        order = [r[0] for r in rows]  # already sorted by level
    else:
        order = _SCOPE_ORDER

    try:
        idx = order.index(scope)
        return order[idx:]
    except ValueError:
        return [scope]


def get_memory_bundle(
    conn: sqlite3.Connection,
    memory_ids: list[int],
    workspace_id: str,
) -> list[dict[str, Any]]:
    """Batch-fetch complete memory objects by ID list.

    Returns only memories that belong to workspace_id.
    Missing or cross-workspace IDs are silently skipped.
    """
    if not memory_ids:
        return []
    placeholders = ",".join("?" * len(memory_ids))
    rows = conn.execute(
        f"SELECT * FROM memories WHERE id IN ({placeholders}) AND workspace_id = ?",
        (*memory_ids, workspace_id),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Sprint 6 — Procedure Outcome Tracking + Confidence Evolution
# ---------------------------------------------------------------------------

_VALID_OUTCOMES = {"success", "partial", "failure"}
_OUTCOME_SCORES = {"success": 1.0, "partial": 0.5, "failure": 0.0}


def record_procedure_outcome(
    conn: sqlite3.Connection,
    procedure_id: int,
    workspace_id: str,
    outcome: str,
    notes: str | None = None,
) -> int:
    """Record an execution outcome for a procedure. Returns outcome row id.

    outcome must be 'success', 'partial', or 'failure'.
    """
    if outcome not in _VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {sorted(_VALID_OUTCOMES)!r}, got {outcome!r}")
    cursor = conn.execute(
        """INSERT INTO procedure_outcomes
           (procedure_id, workspace_id, outcome, notes, created_at_epoch)
           VALUES (?, ?, ?, ?, ?)""",
        (procedure_id, workspace_id, outcome, notes, _now_epoch()),
    )
    conn.commit()
    return cursor.lastrowid


def get_procedure_outcomes(
    conn: sqlite3.Connection,
    procedure_id: int,
    workspace_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return the most recent outcomes for a procedure, newest first."""
    rows = conn.execute(
        """SELECT * FROM procedure_outcomes
           WHERE procedure_id = ? AND workspace_id = ?
           ORDER BY created_at_epoch DESC
           LIMIT ?""",
        (procedure_id, workspace_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def update_procedure_confidence(
    conn: sqlite3.Connection,
    procedure_id: int,
    workspace_id: str,
    recent_n: int = 10,
) -> float | None:
    """Recalculate and persist confidence for a procedure based on recent outcomes.

    Uses a Bayesian-style blend: new_confidence = old * 0.3 + outcome_avg * 0.7.
    Outcome scores: success=1.0, partial=0.5, failure=0.0.
    Result is clamped to [0.05, 0.95].
    Returns the new confidence value, or None if no outcomes exist.
    """
    rows = conn.execute(
        """SELECT outcome FROM procedure_outcomes
           WHERE procedure_id = ? AND workspace_id = ?
           ORDER BY created_at_epoch DESC
           LIMIT ?""",
        (procedure_id, workspace_id, recent_n),
    ).fetchall()
    if not rows:
        return None

    avg_score = sum(_OUTCOME_SCORES[r["outcome"]] for r in rows) / len(rows)

    proc = conn.execute(
        "SELECT confidence FROM procedures WHERE id = ? AND workspace_id = ?",
        (procedure_id, workspace_id),
    ).fetchone()
    if not proc:
        return None

    old_conf = proc["confidence"]
    new_conf = max(0.05, min(0.95, old_conf * 0.3 + avg_score * 0.7))
    conn.execute(
        "UPDATE procedures SET confidence = ?, updated_at_epoch = ? WHERE id = ? AND workspace_id = ?",
        (new_conf, _now_epoch(), procedure_id, workspace_id),
    )
    conn.commit()
    return new_conf


def _update_all_procedure_confidences(conn: sqlite3.Connection, workspace_id: str) -> int:
    """Update confidence for all procedures that have at least one outcome. Returns count updated."""
    proc_ids = conn.execute(
        """SELECT DISTINCT procedure_id FROM procedure_outcomes WHERE workspace_id = ?""",
        (workspace_id,),
    ).fetchall()
    updated = 0
    for row in proc_ids:
        result = update_procedure_confidence(conn, row["procedure_id"], workspace_id)
        if result is not None:
            updated += 1
    return updated


# ---------------------------------------------------------------------------
# Sprint 7 — Multi-hop Graph Context + Batch Remember
# ---------------------------------------------------------------------------

def get_graph_context(
    conn: sqlite3.Connection,
    memory_id: int,
    workspace_id: str,
    depth: int = 2,
) -> dict[str, Any] | None:
    """BFS from memory_id up to `depth` hops in the knowledge graph.

    Returns a context dict with:
      center      — the root memory dict
      nodes       — all unique memories encountered (including center)
      edges       — all traversed edge dicts (with relation, role, weight)
      depth_map   — {memory_id: hop_distance_from_center}
      total_nodes / total_edges — summary counts

    Returns None if memory_id does not exist in workspace_id.
    Handles cycles safely (visited set prevents re-traversal).
    Traverses both inbound and outbound edges at each hop.
    """
    center_row = conn.execute(
        "SELECT * FROM memories WHERE id = ? AND workspace_id = ?",
        (memory_id, workspace_id),
    ).fetchone()
    if not center_row:
        return None

    center_dict = dict(center_row)
    visited: set[int] = {memory_id}
    depth_map: dict[int, int] = {memory_id: 0}
    nodes: dict[int, dict[str, Any]] = {memory_id: center_dict}
    edges: list[dict[str, Any]] = []
    seen_edges: set[int] = set()

    frontier = [memory_id]
    for current_depth in range(1, depth + 1):
        if not frontier:
            break
        next_frontier: list[int] = []
        for mid in frontier:
            edge_rows = conn.execute(
                """SELECT mr.*
                   FROM memory_relations mr
                   WHERE (mr.source_id = ? OR mr.target_id = ?)
                   AND mr.workspace_id = ?""",
                (mid, mid, workspace_id),
            ).fetchall()

            for edge_row in edge_rows:
                edge_dict = dict(edge_row)
                edge_id: int = edge_dict["id"]
                if edge_id in seen_edges:
                    continue
                seen_edges.add(edge_id)
                edges.append(edge_dict)

                neighbor_id = (
                    edge_dict["target_id"]
                    if edge_dict["source_id"] == mid
                    else edge_dict["source_id"]
                )
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    depth_map[neighbor_id] = current_depth
                    next_frontier.append(neighbor_id)
                    neighbor_row = conn.execute(
                        "SELECT * FROM memories WHERE id = ? AND workspace_id = ?",
                        (neighbor_id, workspace_id),
                    ).fetchone()
                    if neighbor_row:
                        nodes[neighbor_id] = dict(neighbor_row)
        frontier = next_frontier

    return {
        "center": center_dict,
        "nodes": list(nodes.values()),
        "edges": edges,
        "depth_map": depth_map,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


# ---------------------------------------------------------------------------
# Sprint 10 — Shortest Path + Graph Query
# ---------------------------------------------------------------------------


def shortest_path(
    conn: sqlite3.Connection,
    source_id: int,
    target_id: int,
    workspace_id: str,
    max_depth: int = 10,
) -> list[dict[str, Any]] | None:
    """BFS shortest path discovery in the knowledge graph.

    Returns a list of edge dicts forming the shortest path,
    or None if no path exists within max_depth.
    """
    if source_id == target_id:
        return []

    # BFS: node_id → (prev_node_id, edge_dict)
    visited: dict[int, tuple[int | None, dict[str, Any]]] = {source_id: (None, {})}
    queue: list[int] = [source_id]
    found = False

    while queue and len(visited) <= max_depth + 1:
        current = queue.pop(0)
        if current == target_id:
            found = True
            break

        edges = conn.execute(
            """SELECT id, source_id, target_id, relation, confidence_type, weight
               FROM memory_relations
               WHERE workspace_id = ? AND (source_id = ? OR target_id = ?)""",
            (workspace_id, current, current),
        ).fetchall()

        for e in edges:
            neighbor = e["target_id"] if e["source_id"] == current else e["source_id"]
            if neighbor not in visited:
                visited[neighbor] = (current, dict(e))
                queue.append(neighbor)

    if not found:
        return None

    # Reconstruct path from target to source, then reverse
    path: list[dict[str, Any]] = []
    node = target_id
    while node != source_id:
        prev_info = visited.get(node)
        if prev_info is None:
            break
        prev_node, edge = prev_info
        if not edge:
            break
        path.append(edge)
        node = prev_node  # type: ignore[assignment]

    path.reverse()
    return path


def query_graph(
    conn: sqlite3.Connection,
    workspace_id: str,
    tag: str | None = None,
    category: str | None = None,
    min_importance: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """Query the graph: filter nodes by tag/category/importance + return their edges.

    Returns {"nodes": [...], "edges": [...], "count": N}.
    """
    where_clauses: list[str] = ["workspace_id = ?"]
    params: list[Any] = [workspace_id]

    if tag:
        where_clauses.append("tags LIKE ?")
        params.append(f'%"{tag}"%')
    if category:
        where_clauses.append("category = ?")
        params.append(category)

    params.append(min_importance)
    params.append(limit)

    memories = conn.execute(
        """SELECT * FROM memories
            WHERE %s
            AND importance >= ?
            AND (lifecycle_status IS NULL OR lifecycle_status = 'active')
            ORDER BY importance DESC
            LIMIT ?""" % " AND ".join(where_clauses),
        params,
    ).fetchall()

    ids = [m["id"] for m in memories]

    if ids:
        placeholders = ",".join("?" * len(ids))
        edges = conn.execute(
            """SELECT * FROM memory_relations
                WHERE workspace_id = ?
                AND (source_id IN (%s) OR target_id IN (%s))"""
            % (placeholders, placeholders),
            [workspace_id] + ids + ids,
        ).fetchall()
    else:
        edges = []

    return {
        "nodes": [dict(m) for m in memories],
        "edges": [dict(e) for e in edges],
        "count": len(memories),
    }


def batch_remember(
    conn: sqlite3.Connection,
    entries: list[dict[str, Any]],
    session_id: str,
    workspace_id: str,
) -> list[int | None]:
    """Save multiple memories in one operation. Returns list of IDs (None for duplicates).

    Each entry dict supports keys: content (required), category, importance, scope, tags.
    Duplicate content (same workspace content_hash) returns None for that slot — no error.
    """
    results: list[int | None] = []
    for entry in entries:
        mid = remember(
            conn,
            session_id,
            workspace_id,
            content=entry.get("content", ""),
            category=entry.get("category", "note"),
            importance=int(entry.get("importance", 5)),
            scope=entry.get("scope", "workspace"),
            tags=entry.get("tags"),
        )
        results.append(mid)
    return results


# ---------------------------------------------------------------------------
# Sprint 8 — Procedure Intelligence + Session Quality
# ---------------------------------------------------------------------------

def get_top_procedures(
    conn: sqlite3.Connection,
    workspace_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return top procedures ranked by confidence × success_rate × use_count.

    Simmetrico di god_facts per le procedure. Procedure senza outcome hanno
    use_count=0 e top_score=0.0. Solo procedure con status='active'.
    """
    rows = conn.execute(
        """SELECT
               p.*,
               COUNT(po.id)                                           AS use_count,
               COALESCE(
                   COUNT(CASE WHEN po.outcome='success' THEN 1 END) * 1.0
                   / NULLIF(COUNT(po.id), 0),
                   0.0
               )                                                      AS success_rate,
               p.confidence
               * COALESCE(
                   COUNT(CASE WHEN po.outcome='success' THEN 1 END) * 1.0
                   / NULLIF(COUNT(po.id), 0),
                   0.0
               )
               * COUNT(po.id)                                         AS top_score
           FROM procedures p
           LEFT JOIN procedure_outcomes po
               ON po.procedure_id = p.id AND po.workspace_id = ?
           WHERE p.workspace_id = ? AND p.status = 'active'
           GROUP BY p.id
           ORDER BY top_score DESC, p.confidence DESC
           LIMIT ?""",
        (workspace_id, workspace_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def consolidate_memories(
    conn: sqlite3.Connection,
    candidate_ids: list[int],
    workspace_id: str,
    procedure_name: str,
    trigger_context: str,
    steps_md: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """Combine consolidation candidates into a procedure and invalidate originals.

    With confirm=False (default) performs a dry-run: returns what would happen
    without modifying the database.
    With confirm=True: creates the procedure via save_procedure and marks each
    candidate memory as 'invalidated' via invalidate_memory.

    Returns:
      dry_run          — whether this was a dry-run
      procedure_name   — name that was/would be used
      candidate_count  — number of valid candidate IDs found
      procedure_id     — id of created procedure (None on dry-run)
      invalidated_count — number of memories actually invalidated (0 on dry-run)
    """
    valid_ids = []
    for mid in candidate_ids:
        row = conn.execute(
            "SELECT id FROM memories WHERE id = ? AND workspace_id = ?",
            (mid, workspace_id),
        ).fetchone()
        if row:
            valid_ids.append(mid)

    if not confirm:
        return {
            "dry_run": True,
            "procedure_name": procedure_name,
            "candidate_count": len(valid_ids),
            "procedure_id": None,
            "invalidated_count": 0,
        }

    proc_id = save_procedure(
        conn, workspace_id, procedure_name, trigger_context, steps_md,
        source_memory_ids=valid_ids or None,
    )
    invalidated = 0
    for mid in valid_ids:
        ok = invalidate_memory(conn, mid, f"consolidated into procedure '{procedure_name}'", workspace_id)
        if ok:
            invalidated += 1

    return {
        "dry_run": False,
        "procedure_name": procedure_name,
        "candidate_count": len(valid_ids),
        "procedure_id": proc_id,
        "invalidated_count": invalidated,
    }


def rate_session(
    conn: sqlite3.Connection,
    summary_id: int,
    workspace_id: str,
    score: float,
    notes: str | None = None,
) -> bool:
    """Set quality_score (and optionally quality_notes) on a session summary.

    Returns True if the summary was found and updated, False otherwise.
    score must be in [0.0, 1.0].
    """
    row = conn.execute(
        "SELECT id FROM session_summaries WHERE id = ? AND workspace_id = ?",
        (summary_id, workspace_id),
    ).fetchone()
    if row is None:
        return False
    conn.execute(
        "UPDATE session_summaries SET quality_score = ?, quality_notes = ? WHERE id = ?",
        (score, notes, summary_id),
    )
    conn.commit()
    return True


# ---------------------------------------------------------------------------
# Sprint 9 — SessionDB Foundation
# ---------------------------------------------------------------------------

def get_high_quality_sessions(
    conn: sqlite3.Connection,
    workspace_id: str,
    min_score: float = 0.7,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return session summaries with quality_score >= min_score, ordered by score desc.

    Sessions with NULL quality_score are excluded. Workspace-isolated.
    """
    rows = conn.execute(
        """SELECT id, session_id, summary, decisions, quality_score, quality_notes, created_at
           FROM session_summaries
           WHERE workspace_id = ? AND quality_score >= ?
           ORDER BY quality_score DESC, created_at_epoch DESC
           LIMIT ?""",
        (workspace_id, min_score, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def export_session_traces(
    conn: sqlite3.Connection,
    workspace_id: str,
    min_score: float | None = None,
    limit: int = 50,
) -> str:
    """Export session summaries as JSONL (one JSON object per line).

    Each line includes: id, session_id, summary, decisions, quality_score,
    quality_notes, created_at.
    min_score=None includes all scored sessions; unscored (NULL) are excluded.
    Returns empty string when no sessions match.
    """
    params: list[Any]
    if min_score is not None:
        rows = conn.execute(
            """SELECT id, session_id, summary, decisions, quality_score, quality_notes, created_at
               FROM session_summaries
               WHERE workspace_id = ? AND quality_score >= ?
               ORDER BY quality_score DESC, created_at_epoch DESC
               LIMIT ?""",
            (workspace_id, min_score, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT id, session_id, summary, decisions, quality_score, quality_notes, created_at
               FROM session_summaries
               WHERE workspace_id = ? AND quality_score IS NOT NULL
               ORDER BY quality_score DESC, created_at_epoch DESC
               LIMIT ?""",
            (workspace_id, limit),
        ).fetchall()

    if not rows:
        return ""
    lines = [json.dumps(dict(r), default=str, ensure_ascii=False) for r in rows]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sprint 10: Graph Visualization Helpers
# ---------------------------------------------------------------------------


def get_memories_for_graph(
    conn: sqlite3.Connection,
    workspace_id: str,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Get all active memories for graph visualization."""
    rows = conn.execute(
        """SELECT id, content, category, importance, tags, created_at, scope
           FROM memories
           WHERE workspace_id = ?
           AND (lifecycle_status IS NULL OR lifecycle_status = 'active')
           ORDER BY importance DESC, created_at_epoch DESC
           LIMIT ?""",
        (workspace_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def export_graphml(
    conn: sqlite3.Connection,
    workspace_id: str,
) -> str:
    """Export the graph as GraphML XML string (compatible with Gephi, yEd)."""
    memories = get_memories_for_graph(conn, workspace_id)
    edges = get_all_relations(conn, workspace_id)

    mem_ids = {m["id"] for m in memories}
    def _src(e): return e.get("source_id") or e.get("source")
    def _tgt(e): return e.get("target_id") or e.get("target")
    valid_edges = [e for e in edges if _src(e) in mem_ids and _tgt(e) in mem_ids]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
        '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '  <key id="d0" for="node" attr.name="category" attr.type="string"/>',
        '  <key id="d1" for="node" attr.name="importance" attr.type="int"/>',
        '  <key id="d2" for="edge" attr.name="relation" attr.type="string"/>',
        '  <key id="d3" for="edge" attr.name="confidence" attr.type="string"/>',
        '  <key id="d4" for="node" attr.name="preview" attr.type="string"/>',
        '  <graph id="G" edgedefault="directed">',
    ]

    for m in memories:
        preview = html.escape(m.get("content", "")[:100])
        lines.append(
            f'    <node id="n{m["id"]}">'
            f'<data key="d0">{m["category"]}</data>'
            f'<data key="d1">{m["importance"]}</data>'
            f'<data key="d4">{preview}</data>'
            f'</node>'
        )

    for e in valid_edges:
        src = _src(e)
        tgt = _tgt(e)
        lines.append(
            f'    <edge source="n{src}" target="n{tgt}">'
            f'<data key="d2">{e["relation"]}</data>'
            f'<data key="d3">{e.get("confidence_type", "unknown")}</data>'
            f'</edge>'
        )

    lines.append('  </graph>')
    lines.append('</graphml>')
    return "\n".join(lines)


def export_cypher(
    conn: sqlite3.Connection,
    workspace_id: str,
) -> str:
    """Export the graph as Cypher queries (compatible with Neo4j)."""
    memories = get_memories_for_graph(conn, workspace_id)
    edges = get_all_relations(conn, workspace_id)

    mem_ids = {m["id"] for m in memories}
    def _src(e): return e.get("source_id") or e.get("source")
    def _tgt(e): return e.get("target_id") or e.get("target")
    valid_edges = [e for e in edges if _src(e) in mem_ids and _tgt(e) in mem_ids]

    lines = ["// Craft Memory Graph Export — Cypher for Neo4j", f"// Generated: {__import__('datetime').datetime.now()}", ""]

    for m in memories:
        preview = m.get("content", "")[:80].replace("\\", "\\\\").replace('"', '\\"')
        cat = m.get("category", "note")
        imp = m.get("importance", 5)
        lines.append(
            f'CREATE (n{m["id"]}:Memory {{id: {m["id"]}, '
            f'category: "{cat}", importance: {imp}, '
            f'preview: "{preview}"}});'
        )

    lines.append("")
    for e in valid_edges:
        rel = e.get("relation", "RELATED").upper().replace(" ", "_")
        conf = e.get("confidence_type", "extracted")
        src = _src(e)
        tgt = _tgt(e)
        lines.append(
            f'MATCH (a:Memory {{id: {src}}}), '
            f'(b:Memory {{id: {tgt}}}) '
            f'CREATE (a)-[:{rel} {{confidence: "{conf}"}}]->(b);'
        )

    return "\n".join(lines)


def lint_wiki(
    conn: sqlite3.Connection,
    workspace_id: str,
) -> dict[str, Any]:
    """Health-check the knowledge base. Returns a diagnostic report.

    Checks performed:
    1. Contradictory facts — same key prefix, diverging values, high confidence
    2. Orphan memories — no graph edges (source_id = id OR target_id = id)
    3. Pending reviews — lifecycle_status = 'needs_review' not yet approved
    4. Low-confidence facts — confidence < 0.5, candidates for verification
    5. Unlinked high-importance memories — importance >= 8 but no edges
    6. Memories with stale lifecycle or inconsistent states

    Returns a dict with findings and suggestions.
    """
    report: dict[str, Any] = {
        "contradictions": [],
        "orphans": [],
        "pending_reviews": [],
        "low_confidence_facts": [],
        "unlinked_high_importance": [],
        "inconsistencies": [],
        "summary": "",
    }

    # 1. Contradictory facts — find facts with same key prefix but different values
    facts = conn.execute(
        "SELECT key, value, confidence, confidence_type, created_at FROM facts WHERE workspace_id = ? ORDER BY key",
        (workspace_id,),
    ).fetchall()
    key_groups: dict[str, list[dict]] = {}
    for f in facts:
        prefix = f["key"].rsplit("_", 1)[0] if "_" in f["key"] else f["key"]
        if prefix not in key_groups:
            key_groups[prefix] = []
        key_groups[prefix].append(dict(f))
    for prefix, group in key_groups.items():
        if len(group) < 2:
            continue
        values = set(g["value"] for g in group)
        if len(values) > 1:
            report["contradictions"].append({
                "prefix": prefix,
                "keys": [g["key"] for g in group],
                "values": [g["value"][:80] for g in group],
                "notes": f"{len(group)} facts with same prefix '{prefix}' but different values",
            })

    # 2. Orphan memories — no incoming or outgoing edges
    all_mem_ids = conn.execute(
        "SELECT id FROM memories WHERE workspace_id = ? AND (lifecycle_status IS NULL OR lifecycle_status = 'active')",
        (workspace_id,),
    ).fetchall()
    for row in all_mem_ids:
        mid = row["id"]
        edge = conn.execute(
            "SELECT id FROM memory_relations WHERE workspace_id = ? AND (source_id = ? OR target_id = ?) LIMIT 1",
            (workspace_id, mid, mid),
        ).fetchone()
        if not edge:
            mem = conn.execute(
                "SELECT id, category, importance, content FROM memories WHERE id = ?",
                (mid,),
            ).fetchone()
            if mem:
                report["orphans"].append({
                    "id": mem["id"],
                    "category": mem["category"],
                    "importance": mem["importance"],
                    "preview": mem["content"][:80],
                })

    # 3. Pending reviews
    reviews = conn.execute(
        "SELECT id, content, importance FROM memories WHERE workspace_id = ? AND lifecycle_status = 'needs_review' ORDER BY importance DESC",
        (workspace_id,),
    ).fetchall()
    for r in reviews:
        report["pending_reviews"].append({
            "id": r["id"],
            "importance": r["importance"],
            "preview": r["content"][:80],
        })

    # 4. Low-confidence facts
    low_conf = conn.execute(
        "SELECT key, value, confidence FROM facts WHERE workspace_id = ? AND confidence < 0.5 ORDER BY confidence ASC",
        (workspace_id,),
    ).fetchall()
    for f in low_conf:
        report["low_confidence_facts"].append({
            "key": f["key"],
            "value": f["value"][:80],
            "confidence": f["confidence"],
        })

    # 5. High-importance memories without edges
    high_no_edges = conn.execute(
        """SELECT m.id, m.content, m.importance FROM memories m
           WHERE m.workspace_id = ? AND m.importance >= 8
           AND (m.lifecycle_status IS NULL OR m.lifecycle_status = 'active')
           AND NOT EXISTS (
               SELECT 1 FROM memory_relations mr
               WHERE mr.workspace_id = ? AND (mr.source_id = m.id OR mr.target_id = m.id)
           )
           ORDER BY m.importance DESC
           LIMIT 20""",
        (workspace_id, workspace_id),
    ).fetchall()
    for m in high_no_edges:
        report["unlinked_high_importance"].append({
            "id": m["id"],
            "importance": m["importance"],
            "preview": m["content"][:80],
        })

    # 6. Inconsistencies
    invalid_lifecycle = conn.execute(
        "SELECT id, lifecycle_status FROM memories WHERE workspace_id = ? AND lifecycle_status NOT IN ('active', 'superseded', 'invalidated', 'needs_review', NULL)",
        (workspace_id,),
    ).fetchall()
    for m in invalid_lifecycle:
        report["inconsistencies"].append({
            "id": m["id"],
            "issue": f"invalid lifecycle_status: {m['lifecycle_status']}",
        })

    # Summary
    total = len(all_mem_ids)
    total_facts = len(facts)
    report["summary"] = (
        f"Wiki health check complete: "
        f"{len(report['contradictions'])} contradictions, "
        f"{len(report['orphans'])} orphan memories (/{total}), "
        f"{len(report['pending_reviews'])} pending reviews, "
        f"{len(report['low_confidence_facts'])} low-confidence facts (/{total_facts}), "
        f"{len(report['unlinked_high_importance'])} high-importance unlinked, "
        f"{len(report['inconsistencies'])} inconsistencies"
    )

    return report


def export_wiki(
    conn: sqlite3.Connection,
    workspace_id: str,
    output_dir: str,
    min_importance: int = 3,
    max_pages: int = 500,
) -> dict[str, Any]:
    """Export memories as an interlinked markdown wiki (Obsidian-compatible).

    Generates:
      wiki/index.md       — catalog of all pages with metadata
      wiki/pages/         — one markdown file per memory, with wikilinks to neighbors
      wiki/edges.md       — summary of all graph connections
      wiki/log.md         — chronological record of exports

    Each page includes YAML frontmatter (tags, category, importance, source)
    and [[wikilink]] references to connected memories.
    """
    import os
    from datetime import datetime, timezone

    base = os.path.abspath(output_dir)
    pages_dir = os.path.join(base, "pages")
    os.makedirs(pages_dir, exist_ok=True)

    # Load all active memories
    memories = conn.execute(
        """SELECT m.id, m.content, m.category, m.importance, m.tags, m.created_at,
                  m.scope, m.lifecycle_status, m.is_core
           FROM memories m
           WHERE m.workspace_id = ?
           AND m.importance >= ?
           AND (m.lifecycle_status IS NULL OR m.lifecycle_status = 'active')
           ORDER BY m.importance DESC, m.created_at_epoch DESC
           LIMIT ?""",
        (workspace_id, min_importance, max_pages),
    ).fetchall()

    # Load all edges for this workspace
    edges = conn.execute(
        "SELECT source_id, target_id, relation, weight, role FROM memory_relations WHERE workspace_id = ?",
        (workspace_id,),
    ).fetchall()

    # Build neighbor index
    neighbors: dict[int, list[dict]] = {}
    for e in edges:
        s, t = e["source_id"], e["target_id"]
        neighbors.setdefault(s, []).append({"other": t, "rel": e["relation"], "weight": e["weight"], "role": e["role"]})
        neighbors.setdefault(t, []).append({"other": s, "rel": e["relation"], "weight": e["weight"], "role": e["role"]})

    mem_map = {m["id"]: m for m in memories}
    page_count = 0
    error_count = 0

    # Generate one page per memory
    for m in memories:
        mid = m["id"]
        # Slug from first line of content
        title_line = m["content"].split("\n")[0][:60].strip()
        safe_name = re.sub(r"[^a-zA-Z0-9\-\s]", "", title_line)[:40].strip().replace(" ", "-").lower()
        slug = f"mem-{mid}-{safe_name}" if safe_name else f"mem-{mid}"

        # Parse tags
        tags_list = []
        if m["tags"]:
            try:
                tags_list = json.loads(m["tags"]) if isinstance(m["tags"], str) else m["tags"]
            except (json.JSONDecodeError, TypeError):
                tags_list = []

        # Build wikilinks to neighbors
        neighbor_links = []
        nbrs = neighbors.get(mid, [])[:15]
        for nb in nbrs:
            other = mem_map.get(nb["other"])
            if not other:
                continue
            other_title = other["content"].split("\n")[0][:60].strip()
            other_slug = re.sub(r"[^a-zA-Z0-9\-\s]", "", other_title)[:40].strip().replace(" ", "-").lower()
            other_name = f"mem-{nb['other']}-{other_slug}" if other_slug else f"mem-{nb['other']}"
            neighbor_links.append(f"  [[{other_name}]] — {nb['rel']} (w={nb['weight']:.2f})")

        # YAML frontmatter
        frontmatter = (
            "---\n"
            f"id: {mid}\n"
            f"title: \"{title_line}\"\n"
            f"category: {m['category']}\n"
            f"importance: {m['importance']}\n"
            f"scope: {m['scope']}\n"
            f"created: {m['created_at']}\n"
            f"is_core: {'true' if m['is_core'] else 'false'}\n"
            f"tags: {json.dumps(tags_list)}\n"
            f"edges: {len(neighbors.get(mid, []))}\n"
            "---\n\n"
        )

        # Page body
        body_lines = [f"# {title_line}\n"]
        body_lines.append(m["content"] + "\n\n")

        if neighbor_links:
            body_lines.append("## Connections\n\n")
            body_lines.extend(neighbor_links)
            body_lines.append("\n")

        if tags_list:
            body_lines.append("## Tags\n\n")
            body_lines.append(" ".join(f"#{t}" for t in tags_list) + "\n")

        try:
            with open(os.path.join(pages_dir, f"{slug}.md"), "w", encoding="utf-8") as f:
                f.write(frontmatter + "\n".join(body_lines))
            page_count += 1
        except OSError:
            error_count += 1

    # Generate index.md
    index_lines = ["# Wiki Index\n", f"Generated: {datetime.now(timezone.utc).isoformat()[:19]}\n"]
    index_lines.append(f"Total pages: {page_count} | Total edges: {len(edges)}\n\n")
    index_lines.append("## By Category\n")
    by_cat: dict[str, list[tuple[int, str, str]]] = {}
    for m in memories:
        title = m["content"].split("\n")[0][:60].strip()
        by_cat.setdefault(m["category"], []).append((m["id"], title, m["tags"]))
    for cat, items in sorted(by_cat.items()):
        index_lines.append(f"\n### {cat} ({len(items)})\n")
        for mid, title, tags in items:
            index_lines.append(f"- [[mem-{mid}-]] — {title[:80]}")
    try:
        with open(os.path.join(base, "index.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(index_lines))
    except OSError:
        error_count += 1

    # Generate edges.md
    edge_lines = ["# Graph Edges\n", f"Total: {len(edges)} edges\n"]
    for e in edges[:200]:
        edge_lines.append(f"- [[mem-{e['source_id']}-]] --{e['relation']}--> [[mem-{e['target_id']}-]] (w={e['weight']:.2f})")
    if len(edges) > 200:
        edge_lines.append(f"\n… and {len(edges) - 200} more edges\n")
    try:
        with open(os.path.join(base, "edges.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(edge_lines))
    except OSError:
        error_count += 1

    # Generate log.md (append)
    log_line = f"## [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] export | {page_count} pages, {len(edges)} edges"
    try:
        with open(os.path.join(base, "log.md"), "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except OSError:
        error_count += 1

    return {
        "page_count": page_count,
        "edge_count": len(edges),
        "output_dir": base,
        "error_count": error_count,
        "files": ["index.md", "edges.md", "log.md", f"pages/ ({page_count} files)"],
    }
