#!/usr/bin/env python3
"""
Session Scanner — Estrae conoscenza dalle sessioni Craft Agents OSS
e la salva in Craft Memory.

REST API (craft-memory server :8392):
  GET  /api/stats
  GET  /api/memories/search?q=...
  POST /api/memories
  POST /api/loops

Usage:
    python scripts/session-scanner.py [workspace_path]
    python scripts/session-scanner.py [workspace_path] --dry-run
    python scripts/session-scanner.py [workspace_path] --force
    python scripts/session-scanner.py [workspace_path] --verbose
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────

CRAFT_MEMORY_URL = "http://127.0.0.1:8392"
STATE_FILENAME = ".session-scanner-state.json"


# ══════════════════════════════════════════════════════════════════════
# REST API helpers
# ══════════════════════════════════════════════════════════════════════

def _rest_get(path: str) -> dict | list:
    """GET request to craft-memory REST API."""
    url = f"{CRAFT_MEMORY_URL}{path}"
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"}
    except (urllib.error.URLError, ConnectionRefusedError, OSError) as e:
        return {"error": f"Connection failed: {e}"}


def _rest_post(path: str, data: dict) -> dict:
    """POST request to craft-memory REST API."""
    url = f"{CRAFT_MEMORY_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"}
    except (urllib.error.URLError, ConnectionRefusedError, OSError) as e:
        return {"error": f"Connection failed: {e}"}


# ══════════════════════════════════════════════════════════════════════
# Classification (deterministic — no LLM)
# ══════════════════════════════════════════════════════════════════════

_TRIVIAL_PATTERN = re.compile(
    r"^(ok|okay|s[iì]|si|no|non lo so|procedi|vai|perfetto|grazie|thanks|"
    r"ty||done|fatto|continua|esatto|corretto|giusto|"
    r"prosegui|avanti|ottimo|perfetto|bene|"
    r"certamente|assolutamente|d'accordo|va bene|okay)$",
    re.IGNORECASE,
)

_DISCARD_PATTERNS = [
    re.compile(r"^(ok|okay|si|s[iì]|no|va bene|procedi)", re.IGNORECASE),
]

_BUG_KEYWORDS = ["bug", "fix", "errore", "problema", "issue", "non funziona",
                 "crash", "fallisce", "rotto", "malfunzionamento"]

_DECISION_KEYWORDS = ["ho deciso", "scelgo", "optiamo", "useremo", "migriamo",
                      "refactoring", "architettura", "pattern architetturale",
                      "soluzione adottata", "abbiamo deciso", "decidiamo di",
                      "implementeremo", "strategia", "approccio"]

_FACT_KEYWORDS = ["usa ", "utilizza ", "e configurato", "e impostato",
                  "e installato", "si trova in", "endpoint", "versione",
                  "host:", "porta:", "db:", "database:", "api key",
                  "configurato con", "dipende da", "richiede"]

_DISCOVERY_KEYWORDS = ["scoperto", "trovato", "identificato", "analisi mostra",
                       "emerso", "riscontrato", "ho notato", "abbiamo scoperto",
                       "rilevato", "evidenziato", "risulta che"]

_LOOP_KEYWORDS = ["da fare", "todo", "bloccato", "pending", "da seguire",
                  "rimasto in sospeso", "da completare", "da verificare",
                  "next step", "prossimo passo", "da implementare",
                  "manca ancora", "serve ancora"]


def classify_content(content: str) -> tuple[str, str, int]:
    """Classify content into (memory_class, reason, suggested_importance).

    memory_class: DISCARD | EPISODIC | FACT_CANDIDATE | OPEN_LOOP | PROCEDURE_CANDIDATE
    """
    c = content.strip()
    if len(c) < 20:
        return ("DISCARD", "content too short (<20 chars)", 0)
    if _TRIVIAL_PATTERN.match(c):
        return ("DISCARD", "trivial response", 0)

    cl = c.lower()

    # Bug/fix → EPISODIC with category=bugfix
    if any(kw in cl for kw in _BUG_KEYWORDS):
        return ("EPISODIC", "bug/fix detected (use category=bugfix)", 8)

    # Decision/arch → EPISODIC with category=decision
    if any(kw in cl for kw in _DECISION_KEYWORDS):
        return ("EPISODIC", "decision/arch detected (use category=decision)", 8)

    # Multi-step procedure → PROCEDURE_CANDIDATE
    step_hits = sum(1 for i in range(1, 6) if f"step {i}" in cl)
    if step_hits >= 2:
        return ("PROCEDURE_CANDIDATE", "multi-step procedure pattern", 7)

    # Task/loop → OPEN_LOOP
    if any(kw in cl for kw in _LOOP_KEYWORDS):
        return ("OPEN_LOOP", "task/loop keyword detected", 6)

    # Factual statement → FACT_CANDIDATE
    if any(kw in cl for kw in _FACT_KEYWORDS):
        return ("FACT_CANDIDATE", "factual statement detected", 6)

    # Discovery → EPISODIC with category=discovery
    if any(kw in cl for kw in _DISCOVERY_KEYWORDS):
        return ("EPISODIC", "discovery detected (use category=discovery)", 7)

    # Default → EPISODIC with category=note, low importance
    return ("EPISODIC", "general message", 4)


# ══════════════════════════════════════════════════════════════════════
# Session file readers
# ══════════════════════════════════════════════════════════════════════

def get_session_meta(session_dir: str) -> dict | None:
    """Read first line of session.jsonl → metadata dict."""
    path = os.path.join(session_dir, "session.jsonl")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.loads(f.readline())
    except (json.JSONDecodeError, OSError):
        return None


def extract_user_messages(session_dir: str) -> list[dict]:
    """Extract user messages from session.jsonl.

    Returns list of {"content": str, "timestamp": int, "type": str}
    """
    path = os.path.join(session_dir, "session.jsonl")
    if not os.path.exists(path):
        return []

    messages = []
    with open(path, encoding="utf-8") as f:
        f.readline()  # skip meta header
        for line in f:
            try:
                msg = json.loads(line)
                if msg.get("type") == "user":
                    content = msg.get("content", "").strip()
                    if content and len(content) >= 20:
                        # Strip source markers like [source:memory]
                        clean = content
                        if "[" in clean[:30] and "]" in clean[:40]:
                            clean = clean.split("]", 1)[-1].strip()
                        messages.append({
                            "content": clean,
                            "timestamp": msg.get("timestamp", 0),
                            "type": "user",
                        })
            except (json.JSONDecodeError, KeyError):
                continue
    return messages


# ══════════════════════════════════════════════════════════════════════
# State management (which sessions have been processed)
# ══════════════════════════════════════════════════════════════════════

def _state_path(workspace_path: str) -> str:
    return os.path.join(workspace_path, STATE_FILENAME)


def load_state(workspace_path: str) -> dict:
    """Load processed sessions state."""
    path = _state_path(workspace_path)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"version": 1, "scanned_at": None, "processed": {}}


def save_state(workspace_path: str, state: dict):
    """Save processed sessions state."""
    state["scanned_at"] = datetime.now(timezone.utc).isoformat()
    path = _state_path(workspace_path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════
# Session filter logic
# ══════════════════════════════════════════════════════════════════════

def should_skip_session(
    session_id: str,
    meta: dict,
    processed: dict,
    force: bool = False,
    verbose: bool = False,
) -> str | None:
    """Return reason string if session should be skipped, None if it should be processed."""
    if meta is None:
        return "no session.jsonl"

    # Already processed?
    if session_id in processed and not force:
        return f"already processed ({processed[session_id].get('memories_saved', 0)} memories)"

    # Status filter
    status = meta.get("sessionStatus", "")
    if status in ("todo", "in_progress"):
        # Active sessions — skip (might still be in use)
        return f"session still active (status={status})"

    # Too few messages
    msg_count = meta.get("messageCount", 0)
    if msg_count < 10:
        return f"too few messages ({msg_count})"

    # Skip automation/agentic-only sessions (SessionEnd, LabelAdd, etc.)
    # These have no real user content — just single "ok" replies
    name = meta.get("name", "") or ""
    if any(name.startswith(p) for p in ["Memory:", "Session:", "Agentic:"]):
        return f"automation session: {name[:50]}"

    return None  # Process this session


# ══════════════════════════════════════════════════════════════════════
# Save to craft-memory
# ══════════════════════════════════════════════════════════════════════

def save_classified_messages(
    session_id: str,
    messages: list[dict],
    dry_run: bool,
    verbose: bool,
    project_name: str = "default",
) -> dict:
    """Classify and save messages to craft-memory.

    Returns summary of what was saved.
    """
    results = {
        "memories_saved": 0,
        "facts_saved": 0,
        "loops_created": 0,
        "discarded": 0,
        "details": [],
    }

    for msg in messages:
        cls, reason, importance = classify_content(msg["content"])

        if cls == "DISCARD":
            results["discarded"] += 1
            if verbose:
                results["details"].append({
                    "action": "discard", "reason": reason,
                    "preview": msg["content"][:60],
                })
            continue

        # Determine category based on classification
        category_map = {
            "EPISODIC": "note",  # will be refined below
            "FACT_CANDIDATE": "discovery",
            "OPEN_LOOP": "note",
            "PROCEDURE_CANDIDATE": "note",
        }
        category = category_map.get(cls, "note")

        # Refine EPISODIC subcategories
        if cls == "EPISODIC":
            if "bug" in reason:
                category = "bugfix"
            elif "decision" in reason:
                category = "decision"
            elif "discovery" in reason:
                category = "discovery"

        # Build tags
        tags = ["session:scanned", f"session:{session_id}", f"project:{project_name}"]
        if category:
            tags.append(f"category:{category}")

        # Content preview for report
        preview = msg["content"][:80]

        if dry_run:
            results["details"].append({
                "action": f"would_save_as_{cls.lower()}",
                "category": category,
                "importance": importance,
                "reason": reason,
                "preview": preview,
            })
            if cls in ("EPISODIC", "FACT_CANDIDATE"):
                results["memories_saved"] += 1
            elif cls == "OPEN_LOOP":
                results["loops_created"] += 1
            continue

        # --- REAL SAVE ---
        try:
            if cls == "OPEN_LOOP":
                # API expects 'title', not 'content'
                resp = _rest_post("/api/loops", {
                    "title": msg["content"][:200],
                    "description": f"Auto-scanned from session {session_id}",
                    "priority": "medium",
                    "scope": "workspace",
                })
                if "error" not in resp:
                    results["loops_created"] += 1

            elif cls == "FACT_CANDIDATE":
                # Save as memory (REST API doesn't have upsert_fact)
                resp = _rest_post("/api/memories", {
                    "content": f"[FACT] {msg['content']}",
                    "category": "discovery",
                    "importance": importance,
                    "scope": "workspace",
                    "tags": tags + ["fact-candidate"],
                })
                if "error" not in resp and not resp.get("duplicate"):
                    results["facts_saved"] += 1
                elif verbose and resp.get("duplicate"):
                    results["details"].append({
                        "action": "duplicate_skipped", "preview": preview,
                    })

            else:  # EPISODIC
                resp = _rest_post("/api/memories", {
                    "content": msg["content"],
                    "category": category,
                    "importance": importance,
                    "scope": "workspace",
                    "tags": tags,
                })
                if "error" not in resp and not resp.get("duplicate"):
                    results["memories_saved"] += 1
                elif verbose and resp.get("duplicate"):
                    results["details"].append({
                        "action": "duplicate_skipped", "preview": preview,
                    })

        except Exception as e:
            if verbose:
                results["details"].append({
                    "action": "error", "error": str(e), "preview": preview,
                })

    return results


# ══════════════════════════════════════════════════════════════════════
# Main scan logic
# ══════════════════════════════════════════════════════════════════════

def scan_sessions(workspace_path: str, dry_run: bool = False,
                  force: bool = False, verbose: bool = False) -> dict:
    """Main scan: iterate sessions, extract knowledge, save to memory."""
    sessions_dir = os.path.join(workspace_path, "sessions")
    if not os.path.isdir(sessions_dir):
        return {"error": f"sessions directory not found: {sessions_dir}"}

    # Health check
    health = _rest_get("/health")
    if isinstance(health, dict) and health.get("status") != "healthy":
        return {"error": f"Craft Memory server not healthy: {health}"}

    state = load_state(workspace_path)
    processed = state.get("processed", {})

    report = {
        "workspace": workspace_path,
        "dry_run": dry_run,
        "force": force,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_sessions": 0,
        "skipped": [],
        "scanned": [],
        "total_memories_saved": 0,
        "total_facts_saved": 0,
        "total_loops_created": 0,
        "total_discarded": 0,
        "errors": [],
    }

    # Scan sessions (sorted by name = chronological)
    all_sessions = sorted(
        s for s in os.listdir(sessions_dir)
        if os.path.isdir(os.path.join(sessions_dir, s))
    )
    report["total_sessions"] = len(all_sessions)

    for session_id in all_sessions:
        session_dir = os.path.join(sessions_dir, session_id)
        meta = get_session_meta(session_dir)

        # Should we skip?
        skip_reason = should_skip_session(session_id, meta, processed, force, verbose)
        if skip_reason:
            report["skipped"].append({"id": session_id, "reason": skip_reason})
            if verbose:
                name = meta.get("name", "?") if meta else "?"
                print(f"  SKIP {session_id}: {name} -> {skip_reason}")
            continue

        # Extract user messages
        messages = extract_user_messages(session_dir)
        if not messages:
            report["skipped"].append({"id": session_id, "reason": "no user messages"})
            if verbose:
                print(f"  SKIP {session_id}: no user messages")
            continue

        name = meta.get("name", "?")
        msg_count = meta.get("messageCount", 0)
        token_usage = meta.get("tokenUsage", {})
        cost = token_usage.get("costUsd", 0)

        if verbose:
            cost_f = f"${cost:.2f}" if cost else "$0.00"
            print(f"  SCAN {session_id}: {name} ({len(messages)} user msgs, {msg_count} total, {cost_f})")

        # Classify and save
        # Derive project name from workspace path
        project_name = os.path.basename(os.path.normpath(workspace_path))
        session_results = save_classified_messages(
            session_id, messages, dry_run, verbose, project_name=project_name,
        )

        report["scanned"].append({
            "id": session_id,
            "name": name,
            "user_messages": len(messages),
            "total_messages": msg_count,
            "cost_usd": cost,
            "results": session_results,
        })
        report["total_memories_saved"] += session_results.get("memories_saved", 0)
        report["total_facts_saved"] += session_results.get("facts_saved", 0)
        report["total_loops_created"] += session_results.get("loops_created", 0)
        report["total_discarded"] += session_results.get("discarded", 0)

        # Mark as processed (unless dry_run)
        if not dry_run:
            processed[session_id] = {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "name": name,
                "memories_saved": session_results.get("memories_saved", 0),
                "facts_saved": session_results.get("facts_saved", 0),
                "loops_created": session_results.get("loops_created", 0),
            }

    # Save state
    state["processed"] = processed
    save_state(workspace_path, state)

    return report


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def print_report(report: dict):
    """Pretty-print scan report."""
    if "error" in report:
        print(f"ERROR: {report['error']}")
        return

    print()
    print("=" * 60)
    print(f"  Session Scanner Report")
    print(f"  Workspace: {report['workspace']}")
    print(f"  Dry run:   {report['dry_run']}")
    print(f"  Timestamp: {report['timestamp']}")
    print("=" * 60)

    total = report["total_sessions"]
    scanned = len(report["scanned"])
    skipped = len(report["skipped"])
    print(f"\n  Total sessions: {total}")
    print(f"  Scanned:        {scanned}")
    print(f"  Skipped:        {skipped}")

    if report["scanned"]:
        print(f"\n  Results:")
        print(f"    Memories saved:  {report['total_memories_saved']}")
        print(f"    Facts saved:     {report['total_facts_saved']}")
        print(f"    Loops created:   {report['total_loops_created']}")
        print(f"    Discarded:       {report['total_discarded']}")

        print(f"\n  Scanned sessions:")
        for s in report["scanned"]:
            r = s["results"]
            details = []
            if r.get("memories_saved"):
                details.append(f"{r['memories_saved']} mem")
            if r.get("facts_saved"):
                details.append(f"{r['facts_saved']} facts")
            if r.get("loops_created"):
                details.append(f"{r['loops_created']} loops")
            if r.get("discarded"):
                details.append(f"{r['discarded']} discarded")
            cost_str = f"${s.get('cost_usd', 0):.2f}" if s.get('cost_usd') else ""
            cost_fmt = f"${s.get('cost_usd', 0):.2f}" if s.get('cost_usd') else ""
            print(f"    {s['id'][:20]:20s} | {s.get('name','?')[:40]:40s} | {', '.join(details):40s} | {cost_fmt}")

    if skipped > 0 and report.get("skipped"):
        print(f"\n  Skipped ({skipped}):")
        for s in report["skipped"][:10]:
            print(f"    {s['id'][:20]:20s} -> {s['reason']}")
        if skipped > 10:
            print(f"    ... and {skipped - 10} more")

    if report.get("errors"):
        print(f"\n  Errors ({len(report['errors'])}):")
        for e in report["errors"]:
            print(f"    {e}")


def main():
    # Fix Windows cp1252 encoding for Unicode output
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Session Scanner - Extract knowledge from Craft Agents sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/session-scanner.py ~/.craft-agent/workspaces/my-workspace
  python scripts/session-scanner.py ~/.craft-agent/workspaces/my-workspace --dry-run
  python scripts/session-scanner.py ~/.craft-agent/workspaces/my-workspace --force
  python scripts/session-scanner.py ~/.craft-agent/workspaces/my-workspace --verbose
  python scripts/session-scanner.py ~/.craft-agent/workspaces/my-workspace --json
        """,
    )
    parser.add_argument(
        "workspace",
        nargs="?",
        default=os.path.expanduser("~/.craft-agent/workspaces/auresys-backend"),
        help="Path to Craft Agents workspace directory",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without saving anything")
    parser.add_argument("--force", action="store_true",
                        help="Re-scan already processed sessions")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-session details")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted report")

    args = parser.parse_args()

    report = scan_sessions(
        workspace_path=os.path.expanduser(args.workspace),
        dry_run=args.dry_run,
        force=args.force,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)

    # Exit code
    if "error" in report:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
