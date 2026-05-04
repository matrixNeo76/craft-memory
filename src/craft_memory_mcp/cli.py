"""
Craft Memory MCP — Command-line interface.

Usage:
    craft-memory serve [--stdio|--http] [--host HOST] [--port PORT]
    craft-memory check
    craft-memory status
    craft-memory stop
    craft-memory ensure
    craft-memory install [--workspace PATH] [--merge] [--overwrite] [--dry-run]
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error


def _env(key: str, default: str) -> str:
    """Read config from env var with default."""
    return os.environ.get(key, default)


def _port() -> int:
    return int(_env("CRAFT_MEMORY_PORT", "8392"))


def _host() -> str:
    return _env("CRAFT_MEMORY_HOST", "127.0.0.1")


def _health_url() -> str:
    return f"http://{_host()}:{_port()}/health"


# ─── Health check ────────────────────────────────────────────────────

def is_alive() -> bool:
    """Check if the server responds to /health."""
    try:
        req = urllib.request.Request(_health_url(), method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return data.get("status") in ("healthy", "degraded")
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, OSError):
        return False


# ─── Start server ────────────────────────────────────────────────────

def _server_log_path() -> str:
    """Return path to the server log file."""
    import tempfile
    return os.path.join(tempfile.gettempdir(), "craft-memory-server.log")


def start_server(host: str | None = None, port: int | None = None,
                 transport: str = "http") -> int | None:
    """Start the server as a detached background process.

    Server stdout/stderr are redirected to a log file at:
      {tempdir}/craft-memory-server.log

    If the server crashes, check this file for the error traceback.
    """
    h = host or _host()
    p = port or _port()

    env = os.environ.copy()
    env["CRAFT_MEMORY_TRANSPORT"] = transport
    env["CRAFT_MEMORY_HOST"] = h
    env["CRAFT_MEMORY_PORT"] = str(p)
    # Propagate CRAFT_WORKSPACE_ID from parent env so the server
    # starts with the correct workspace database. Fallback: "default".
    # Belt-and-suspenders: the automation command prefix already sets this,
    # but this ensures it works regardless of shell syntax (bash vs cmd).
    if "CRAFT_WORKSPACE_ID" not in env:
        env["CRAFT_WORKSPACE_ID"] = os.environ.get("CRAFT_WORKSPACE", "default")

    cmd = [sys.executable, "-m", "craft_memory_mcp.server"]

    # Log file for server stdout/stderr (instead of DEVNULL — so we can
    # debug crashes):
    log_path = _server_log_path()
    log_file = open(log_path, "a", buffering=1)  # line-buffered
    # Prepend a separator so each server start is distinguishable
    log_file.write(f"\n--- Server start at {__import__('datetime').datetime.now()} PID=? ---\n")
    log_file.flush()

    # Platform-specific detachment
    kwargs = dict(
        env=env,
        stdout=log_file,
        stderr=log_file,  # stderr goes to SAME log file (so tracebacks are captured)
        close_fds=True,
    )
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen(cmd, **kwargs)
        # Don't close log_file — the subprocess owns it now
        # (closing would break when the subprocess writes to it)
        return proc.pid
    except Exception as e:
        log_file.write(f"ERROR starting server: {e}\n")
        log_file.close()
        print(f"ERROR: Failed to start server: {e}", file=sys.stderr)
        return None


# ─── Wait for alive ──────────────────────────────────────────────────

def wait_for_alive(timeout: int = 10) -> bool:
    """Poll /health until the server is ready or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_alive():
            return True
        time.sleep(0.5)
    return False


# ─── Stop server ─────────────────────────────────────────────────────

def stop_server() -> bool:
    """Stop a running server by finding the process on the port."""
    port = _port()
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["netstat", "-aon"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    subprocess.run(["taskkill", "/F", "/PID", pid],
                                   capture_output=True, timeout=5)
                    print(f"Stopped process PID {pid}")
                    return True
        except Exception as e:
            print(f"ERROR: Could not stop server: {e}", file=sys.stderr)
    else:
        # Unix/macOS: use lsof
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True, timeout=5,
            )
            if result.stdout.strip():
                pid = result.stdout.strip().split("\n")[0]
                os.kill(int(pid), signal.SIGTERM)
                print(f"Stopped process PID {pid}")
                return True
        except Exception as e:
            print(f"ERROR: Could not stop server: {e}", file=sys.stderr)
    return False


# ─── Subcommands ─────────────────────────────────────────────────────

def cmd_serve(args):
    """Start the MCP server in the foreground."""
    transport = "http" if not args.stdio else "stdio"
    host = args.host or _host()
    port = args.port or _port()

    # Set env vars so server.py picks them up
    os.environ["CRAFT_MEMORY_TRANSPORT"] = transport
    os.environ["CRAFT_MEMORY_HOST"] = host
    os.environ["CRAFT_MEMORY_PORT"] = str(port)

    # Import and run the server module directly
    from craft_memory_mcp import server as srv
    srv.run_server()


def cmd_check(args):
    """Check if the server is alive. Exit 0=up, 2=down."""
    if is_alive():
        print(f"OK: Craft Memory server is running on port {_port()}")
        sys.exit(0)
    else:
        print(f"DOWN: Craft Memory server is not responding on port {_port()}")
        sys.exit(2)


def cmd_status(args):
    """Detailed status of the server."""
    try:
        req = urllib.request.Request(_health_url(), method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"DOWN: Server not responding ({e})")
        sys.exit(2)


def cmd_stop(args):
    """Stop a running server."""
    if stop_server():
        print("Craft Memory server stopped.")
    else:
        print(f"No running server found on port {_port()}")
        sys.exit(1)


def cmd_ensure(args):
    """Ensure the server is running; start it if down."""
    if is_alive():
        print(f"OK: Craft Memory server already running on port {_port()}")
        return

    print(f"Starting Craft Memory server on port {_port()}...")
    pid = start_server(port=args.port, host=args.host)
    if pid is None:
        print("ERROR: Could not start server", file=sys.stderr)
        sys.exit(1)

    print(f"Server process started (PID {pid}), waiting for readiness...")
    if wait_for_alive():
        print(f"OK: Craft Memory server is ready at http://{_host()}:{_port()}/mcp")
        print(f"     Server log: {_server_log_path()}")
    else:
        log_path = _server_log_path()
        print(f"ERROR: Server started but not responding after 10s", file=sys.stderr)
        if os.path.exists(log_path):
            print(f"       Last 20 lines from {log_path}:", file=sys.stderr)
            with open(log_path) as f:
                lines = f.readlines()
            for line in lines[-20:]:
                print(f"       | {line.rstrip()}", file=sys.stderr)
        sys.exit(1)


def _diff_text(label: str, old: str, new: str) -> str:
    """Return a unified diff string between old and new text."""
    import difflib
    lines = list(difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"{label} (existing)",
        tofile=f"{label} (new)",
        n=2,
    ))
    return "".join(lines)


def _merge_automations(existing: dict, template: dict) -> tuple[dict, list[str], list[str]]:
    """Merge template automations into existing, keyed by (event, name).

    Returns (merged_dict, added_list, skipped_list).
    Existing entries are never overwritten.
    """
    merged = {k: list(v) for k, v in existing.items()}
    added: list[str] = []
    skipped: list[str] = []

    for event, entries in template.get("automations", {}).items():
        existing_names = {e.get("name") for e in merged.get(event, [])}
        for entry in entries:
            name = entry.get("name", "<unnamed>")
            if name in existing_names:
                skipped.append(f"{event}/{name}")
            else:
                merged.setdefault(event, []).append(entry)
                added.append(f"{event}/{name}")

    return merged, added, skipped


def _merge_bash_patterns(perms: dict, patterns: list[dict]) -> tuple[dict, list[str]]:
    """Add missing allowedBashPatterns entries. Returns (updated_perms, added_list)."""
    existing = perms.get("allowedBashPatterns", [])
    existing_patterns = {e["pattern"] for e in existing}
    added: list[str] = []
    result = list(existing)
    for p in patterns:
        if p["pattern"] not in existing_patterns:
            result.append(p)
            added.append(p["pattern"])
    perms_out = dict(perms)
    perms_out["allowedBashPatterns"] = result
    return perms_out, added


def _merge_mcp_patterns(perms: dict, patterns: list[dict]) -> tuple[dict, list[str]]:
    """Add missing allowedMcpPatterns entries. Returns (updated_perms, added_list)."""
    existing = perms.get("allowedMcpPatterns", [])
    existing_patterns = {e["pattern"] for e in existing}
    added: list[str] = []
    result = list(existing)
    for p in patterns:
        if p["pattern"] not in existing_patterns:
            result.append(p)
            added.append(p["pattern"])
    perms_out = dict(perms)
    perms_out["allowedMcpPatterns"] = result
    return perms_out, added


def _write_or_dry(path, content: str, dry_run: bool, label: str) -> None:
    """Write a text file, or print path in dry-run mode."""
    if dry_run:
        print(f"  [dry-run] would write: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  + {label}: {path}")


def cmd_install(args):
    """Install Craft Memory source into a Craft Agents workspace.

    Default (no flags): merge-safe — create missing files, never overwrite existing.
    --merge: auto-merge JSON files (automations by name, perms by pattern);
             update skills if source is newer.
    --overwrite: force-overwrite all files (destructive).
    --dry-run: show what would happen without writing.
    """
    import difflib
    import secrets
    from pathlib import Path

    dry = args.dry_run
    overwrite = args.overwrite
    merge = args.merge or overwrite  # --overwrite implies merge logic too

    def _write_json(path: Path, data: dict, label: str) -> None:
        content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        _write_or_dry(path, content, dry, label)

    # ── Locate workspace ───────────────────────────────────────────────
    if args.workspace:
        ws_dir = Path(args.workspace)
    else:
        base = Path.home() / ".craft-agent" / "workspaces"
        if not base.exists():
            print("ERROR: No Craft Agents workspaces found", file=sys.stderr)
            sys.exit(1)
        workspaces = [d for d in base.iterdir() if d.is_dir() and (d / "config.json").exists()]
        if not workspaces:
            print("ERROR: No valid workspaces found", file=sys.stderr)
            sys.exit(1)
        if len(workspaces) == 1:
            ws_dir = workspaces[0]
        else:
            print("Multiple workspaces found:")
            for i, w in enumerate(workspaces):
                print(f"  [{i}] {w.name}")
            choice = input("Select workspace (number): ").strip()
            try:
                ws_dir = workspaces[int(choice)]
            except (ValueError, IndexError):
                print("Invalid choice", file=sys.stderr)
                sys.exit(1)

    if not ws_dir.exists():
        print(f"ERROR: Workspace not found: {ws_dir}", file=sys.stderr)
        sys.exit(1)

    # Repo root: cli.py is at src/craft_memory_mcp/cli.py → 3 levels up
    repo_root = Path(__file__).parent.parent.parent
    craft_agents_dir = repo_root / "craft-agents"

    print(f"\nInstalling Craft Memory to workspace: {ws_dir}")
    if dry:
        print("  (dry-run mode — no files will be written)\n")

    # ── Source: config.json ────────────────────────────────────────────
    source_dir = ws_dir / "sources" / "memory"
    if not dry:
        source_dir.mkdir(parents=True, exist_ok=True)

    config_path = source_dir / "config.json"
    if config_path.exists() and not overwrite:
        print(f"  = source config exists (skip): {config_path}")
    else:
        # Load template from craft-agents/source/config.json if available
        tpl_config_path = craft_agents_dir / "source" / "config.json"
        if tpl_config_path.exists():
            config = json.loads(tpl_config_path.read_text(encoding="utf-8"))
        else:
            config = {
                "name": "Craft Memory",
                "slug": "memory",
                "enabled": True,
                "provider": "craft-memory",
                "type": "mcp",
                "icon": "🧠",
                "tagline": "Persistent cross-session memory with SQLite + FTS5",
                "mcp": {"transport": "http", "url": f"http://localhost:{_port()}/mcp", "authType": "none"},
            }
        # Inject a stable ID and correct port
        if "id" not in config or overwrite:
            config["id"] = f"memory_{secrets.token_hex(4)}"
        config.setdefault("mcp", {})["url"] = f"http://localhost:{_port()}/mcp"
        _write_json(config_path, config, "source config")

    # ── Source: permissions.json ───────────────────────────────────────
    mcp_patterns = [
        {"pattern": "remember", "comment": "Store episodic memories"},
        {"pattern": "search_memory", "comment": "Search memories via FTS5"},
        {"pattern": "get_recent_memory", "comment": "Get recent memories"},
        {"pattern": "upsert_fact", "comment": "Store/update stable facts"},
        {"pattern": "find_similar", "comment": "Semantic similarity search"},
        {"pattern": "list_open_loops", "comment": "List open loops"},
        {"pattern": "close_open_loop", "comment": "Close open loops"},
        {"pattern": "summarize_scope", "comment": "Generate scope summary"},
    ]
    perms_path = source_dir / "permissions.json"
    if perms_path.exists() and not overwrite:
        if merge:
            existing_perms = json.loads(perms_path.read_text(encoding="utf-8"))
            merged_perms, added_patterns = _merge_mcp_patterns(existing_perms, mcp_patterns)
            if added_patterns:
                _write_json(perms_path, merged_perms, f"source perms (merged +{len(added_patterns)})")
            else:
                print(f"  = source perms up-to-date: {perms_path}")
        else:
            print(f"  = source perms exist (skip): {perms_path}")
    else:
        _write_json(perms_path, {"allowedMcpPatterns": mcp_patterns}, "source perms")

    # ── Source: guide.md ──────────────────────────────────────────────
    guide_path = source_dir / "guide.md"
    tpl_guide_path = craft_agents_dir / "source" / "guide.md"
    if guide_path.exists() and not overwrite:
        if merge and tpl_guide_path.exists():
            old_guide = guide_path.read_text(encoding="utf-8")
            new_guide = tpl_guide_path.read_text(encoding="utf-8")
            if old_guide.strip() == new_guide.strip():
                print(f"  = guide.md up-to-date")
            else:
                diff = _diff_text("guide.md", old_guide, new_guide)
                print(f"  ~ guide.md differs (--merge: overwriting)")
                if diff:
                    print(diff[:1000] + ("  ...(truncated)" if len(diff) > 1000 else ""))
                _write_or_dry(guide_path, new_guide, dry, "guide.md")
        else:
            print(f"  = guide.md exists (skip)")
    else:
        if tpl_guide_path.exists():
            _write_or_dry(guide_path, tpl_guide_path.read_text(encoding="utf-8"), dry, "guide.md")
        else:
            print(f"  WARN: guide template not found at {tpl_guide_path}")

    # ── Workspace config: enabledSourceSlugs ──────────────────────────
    ws_config_path = ws_dir / "config.json"
    if ws_config_path.exists():
        ws_config = json.loads(ws_config_path.read_text(encoding="utf-8"))
        slugs = ws_config.get("defaults", {}).get("enabledSourceSlugs", [])
        if "memory" not in slugs:
            slugs.append("memory")
            ws_config.setdefault("defaults", {})["enabledSourceSlugs"] = slugs
            _write_json(ws_config_path, ws_config, "workspace config (enabledSourceSlugs)")
        else:
            print(f"  = 'memory' already in enabledSourceSlugs")

    # ── Workspace automations.json ─────────────────────────────────────
    tpl_automations_path = craft_agents_dir / "automations.json"
    ws_automations_path = ws_dir / "automations.json"
    if tpl_automations_path.exists():
        tpl_auto = json.loads(tpl_automations_path.read_text(encoding="utf-8"))
        if ws_automations_path.exists():
            existing_auto = json.loads(ws_automations_path.read_text(encoding="utf-8"))
            merged_events, added, skipped = _merge_automations(
                existing_auto.get("automations", {}), tpl_auto,
            )
            if added:
                out = {"version": existing_auto.get("version", 2), "automations": merged_events}
                _write_json(ws_automations_path, out, f"automations (merged +{len(added)})")
                for a in added:
                    print(f"    + {a}")
            else:
                print(f"  = automations up-to-date ({len(skipped)} already present)")
            if skipped and not added:
                for s in skipped[:5]:
                    print(f"    = {s} (exists, skip)")
        else:
            # Create fresh automations.json from template
            out = {"version": tpl_auto.get("version", 2), "automations": tpl_auto.get("automations", {})}
            _write_json(ws_automations_path, out, "automations (new)")
    else:
        print(f"  WARN: automations template not found at {tpl_automations_path}")

    # ── Workspace permissions.json: bash patterns ─────────────────────
    bash_patterns = [
        {"pattern": "^craft-memory\\s", "comment": "Allow craft-memory CLI commands"},
    ]
    ws_perms_path = ws_dir / "permissions.json"
    if ws_perms_path.exists():
        ws_perms = json.loads(ws_perms_path.read_text(encoding="utf-8"))
    else:
        ws_perms = {}
    ws_perms_updated, bash_added = _merge_bash_patterns(ws_perms, bash_patterns)
    if bash_added:
        _write_json(ws_perms_path, ws_perms_updated, f"workspace perms (bash +{len(bash_added)})")
    else:
        print(f"  = workspace bash permissions up-to-date")

    # ── Skills ────────────────────────────────────────────────────────
    skills_dir = ws_dir / "skills"
    if not dry:
        skills_dir.mkdir(parents=True, exist_ok=True)
    package_skills = repo_root / "skills"
    skill_names = ["memory-start", "memory-protocol", "memory-maintenance", "session-handoff"]
    if package_skills.exists():
        copied = updated = skipped_skills = 0
        for skill_name in skill_names:
            src_skill = package_skills / skill_name
            dst_skill = skills_dir / skill_name
            if not src_skill.exists():
                print(f"  WARN: skill not found: {src_skill}")
                continue
            if dst_skill.exists():
                if merge:
                    # Update if any source file is newer than destination
                    src_mtime = max(f.stat().st_mtime for f in src_skill.rglob("*") if f.is_file())
                    dst_mtime = max(
                        (f.stat().st_mtime for f in dst_skill.rglob("*") if f.is_file()),
                        default=0,
                    )
                    if src_mtime > dst_mtime:
                        if not dry:
                            shutil.rmtree(dst_skill)
                            shutil.copytree(src_skill, dst_skill)
                        print(f"  ~ skill updated: {skill_name}")
                        updated += 1
                    else:
                        print(f"  = skill up-to-date: {skill_name}")
                        skipped_skills += 1
                else:
                    print(f"  = skill exists (skip): {skill_name}")
                    skipped_skills += 1
            else:
                if not dry:
                    shutil.copytree(src_skill, dst_skill)
                print(f"  + skill installed: {skill_name}")
                copied += 1
        summary_parts = []
        if copied:
            summary_parts.append(f"{copied} installed")
        if updated:
            summary_parts.append(f"{updated} updated")
        if skipped_skills:
            summary_parts.append(f"{skipped_skills} unchanged")
        if summary_parts:
            print(f"  skills: {', '.join(summary_parts)}")
    else:
        print(f"  WARN: Skills source not found at {package_skills}")
        print(f"        Copy manually: {', '.join(skill_names)}")

    # ── Ensure server is running ───────────────────────────────────────
    if not dry:
        print(f"\n  Checking server...")
        if not is_alive():
            pid = start_server()
            if pid and wait_for_alive():
                print(f"  + Server started (PID {pid})")
            else:
                print(f"  WARN: Could not start server. Run: craft-memory ensure")
        else:
            print(f"  = Server already running on port {_port()}")

    print(f"\n{'[dry-run] ' if dry else ''}Done: Craft Memory installed to workspace: {ws_dir.name}")
    if not dry:
        print(f"  Next: Start a new session and run 'craft-memory check'")


# ─── Scan sessions ───────────────────────────────────────────────────

def cmd_scan(args):
    """Scan unprocessed Craft Agents sessions and save discoveries to memory."""
    # Locate the scanner script relative to this file
    scanner_script = os.path.join(
        os.path.dirname(__file__), "..", "..", "scripts", "session-scanner.py",
    )
    scanner_script = os.path.abspath(scanner_script)

    if not os.path.exists(scanner_script):
        print(f"ERROR: Scanner script not found at {scanner_script}", file=sys.stderr)
        sys.exit(1)

    cmd = [sys.executable, scanner_script, args.workspace]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.force:
        cmd.append("--force")
    if args.verbose:
        cmd.append("--verbose")
    if args.json:
        cmd.append("--json")

    # Run in same process group
    result = subprocess.run(cmd, timeout=args.timeout or 120)
    sys.exit(result.returncode)


# ─── Analyze command (code analysis orchestration) ────────────────

def cmd_analyze_code(args):
    """Analyze a code directory via craft-code-mapper and save to memory."""
    if not is_alive():
        print("ERROR: craft-memory server is not running. Start with: craft-memory ensure")
        sys.exit(1)

    # Call craft-code-mapper as subprocess
    cmd = ["craft-code-mapper", "scan", args.directory]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.force:
        cmd.append("--force")
    cmd.extend(["--memory-url", args.memory_url])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, timeout=300)
    sys.exit(result.returncode)


# ─── Graph command (generate HTML) ───────────────────────────────────

def cmd_graph(args):
    """Generate interactive HTML knowledge graph."""
    if not is_alive():
        print("ERROR: craft-memory server is not running. Start with: craft-memory ensure")
        sys.exit(1)

    import httpx

    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {
            "name": "export_graph_html",
            "arguments": {
                "output_path": os.path.abspath(args.output),
                "resolution": args.resolution,
                "limit": args.limit,
            }
        }
    }

    try:
        resp = httpx.post(args.memory_url, json=payload, headers=headers, timeout=30)
        result = resp.json()
        text = result.get("result", {}).get("content", [{}])[0].get("text", "")
        print(text)

        if args.open:
            import webbrowser
            webbrowser.open(os.path.abspath(args.output))
            print(f"Opened in browser: {os.path.abspath(args.output)}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


# ─── Watch command (periodic re-analysis) ────────────────────────────

def cmd_watch(args):
    """Watch directory and re-analyze on changes."""
    import time as _time

    if not is_alive():
        print("ERROR: craft-memory server is not running. Start with: craft-memory ensure")
        sys.exit(1)

    print(f"Watching: {os.path.abspath(args.directory)}")
    print(f"Interval: {args.interval}s")
    print("Press Ctrl+C to stop.\n")

    cmd = ["craft-code-mapper", "scan", args.directory, "--no-check"]
    cmd.extend(["--memory-url", args.memory_url])

    iteration = 0
    while True:
        iteration += 1
        print(f"[{_time.strftime('%H:%M:%S')}] Scan #{iteration}...")
        try:
            result = subprocess.run(cmd, timeout=args.interval * 2, capture_output=True, text=True)
            # Print last line of output (summary)
            if result.stdout:
                for line in result.stdout.strip().split("\n")[-8:]:
                    print(f"  {line}")
            if result.returncode != 0:
                print(f"  WARN: exit code {result.returncode}")
        except subprocess.TimeoutExpired:
            print(f"  WARN: scan timed out")
        except FileNotFoundError:
            print(f"  ERROR: craft-code-mapper not found. Install with: pip install -e /path/to/craft-code-mapper")
            sys.exit(1)

        print(f"  Next scan in {args.interval}s...\n")
        _time.sleep(args.interval)


# ─── Argument parser ─────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="craft-memory",
        description="Craft Memory MCP — Persistent cross-session memory for Craft Agents",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # serve
    p_serve = sub.add_parser("serve", help="Start the MCP server")
    p_serve.add_argument("--stdio", action="store_true", help="Use stdio transport (default: HTTP)")
    p_serve.add_argument("--host", default=None, help=f"HTTP host (default: {_host()})")
    p_serve.add_argument("--port", type=int, default=None, help=f"HTTP port (default: {_port()})")

    # check
    sub.add_parser("check", help="Check if server is alive (exit 0=up, 2=down)")

    # status
    sub.add_parser("status", help="Detailed server status")

    # stop
    sub.add_parser("stop", help="Stop a running server")

    # ensure
    p_ensure = sub.add_parser("ensure", help="Ensure server is running; start if down")
    p_ensure.add_argument("--host", default=None, help="HTTP host override")
    p_ensure.add_argument("--port", type=int, default=None, help="HTTP port override")

    # scan
    p_scan = sub.add_parser("scan", help="Scan unprocessed sessions and save discoveries to memory")
    p_scan.add_argument("workspace", nargs="?",
                        default=os.path.expanduser("~/.craft-agent/workspaces/auresys-backend"),
                        help="Path to Craft Agents workspace")
    p_scan.add_argument("--dry-run", action="store_true", help="Simulate without saving")
    p_scan.add_argument("--force", action="store_true", help="Re-scan already processed sessions")
    p_scan.add_argument("--verbose", "-v", action="store_true", help="Show per-session details")
    p_scan.add_argument("--json", action="store_true", help="Output raw JSON")
    p_scan.add_argument("--timeout", type=int, default=120,
                        help="Max execution time in seconds (default: 120)")

    # analyze (code analysis via craft-code-mapper)
    p_analyze = sub.add_parser("analyze", help="Analyze code directory via craft-code-mapper")
    p_analyze.add_argument("directory", help="Directory to analyze")
    p_analyze.add_argument("--dry-run", action="store_true", help="Don\'t save to memory")
    p_analyze.add_argument("--force", action="store_true", help="Re-analyze unchanged files")
    p_analyze.add_argument("--memory-url", default="http://127.0.0.1:8392/mcp",
                          help="craft-memory MCP URL")

    # graph (generate HTML graph)
    p_graph = sub.add_parser("graph", help="Generate interactive HTML knowledge graph")
    p_graph.add_argument("output", nargs="?", default="memory-graph.html",
                         help="Output HTML file path")
    p_graph.add_argument("--resolution", type=float, default=1.0,
                         help="Leiden clustering resolution (default: 1.0)")
    p_graph.add_argument("--limit", type=int, default=500,
                         help="Max nodes (default: 500)")
    p_graph.add_argument("--open", action="store_true",
                         help="Open graph in browser after generation")
    p_graph.add_argument("--memory-url", default="http://127.0.0.1:8392/mcp",
                         help="craft-memory MCP URL")

    # watch (periodic code analysis)
    p_watch = sub.add_parser("watch", help="Watch directory and re-analyze on changes")
    p_watch.add_argument("directory", help="Directory to watch")
    p_watch.add_argument("--interval", type=int, default=60,
                         help="Poll interval in seconds (default: 60)")
    p_watch.add_argument("--memory-url", default="http://127.0.0.1:8392/mcp",
                         help="craft-memory MCP URL")

    # install
    p_install = sub.add_parser("install", help="Install into a Craft Agents workspace")
    p_install.add_argument("--workspace", default=None, help="Path to workspace directory")
    p_install.add_argument(
        "--merge", action="store_true",
        help="Auto-merge JSON files (automations by name, perms by pattern); update skills if newer",
    )
    p_install.add_argument(
        "--overwrite", action="store_true",
        help="Force-overwrite all files (implies --merge for JSON; destructive)",
    )
    p_install.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="Show what would be written without making changes",
    )

    return parser


# ─── Main ────────────────────────────────────────────────────────────

def main():
    # Ensure UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError for ✓ ⚠ etc.)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "serve": cmd_serve,
        "check": cmd_check,
        "status": cmd_status,
        "stop": cmd_stop,
        "ensure": cmd_ensure,
        "install": cmd_install,
        "scan": cmd_scan,
        "analyze": cmd_analyze_code,
        "graph": cmd_graph,
        "watch": cmd_watch,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
