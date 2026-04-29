"""
Craft Memory MCP — Command-line interface.

Usage:
    craft-memory serve [--stdio|--http] [--host HOST] [--port PORT]
    craft-memory check
    craft-memory status
    craft-memory stop
    craft-memory ensure
    craft-memory install [--workspace PATH]
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

def start_server(host: str | None = None, port: int | None = None,
                 transport: str = "http") -> int | None:
    """Start the server as a detached background process."""
    h = host or _host()
    p = port or _port()

    env = os.environ.copy()
    env["CRAFT_MEMORY_TRANSPORT"] = transport
    env["CRAFT_MEMORY_HOST"] = h
    env["CRAFT_MEMORY_PORT"] = str(p)

    cmd = [sys.executable, "-m", "craft_memory_mcp.server"]

    # Platform-specific detachment
    kwargs = dict(
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        # Unix: start new session, detach from terminal
        kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen(cmd, **kwargs)
        return proc.pid
    except Exception as e:
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
    else:
        print("ERROR: Server started but not responding after 10s", file=sys.stderr)
        sys.exit(1)


def cmd_install(args):
    """Install Craft Memory source into a Craft Agents workspace."""
    from pathlib import Path

    # Determine workspace directory
    if args.workspace:
        ws_dir = Path(args.workspace)
    else:
        # Auto-detect: find first workspace with config.json
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

    # Create source directory
    source_dir = ws_dir / "sources" / "memory"
    source_dir.mkdir(parents=True, exist_ok=True)

    # Write config.json
    import secrets
    config_id = f"memory_{secrets.token_hex(4)}"
    config = {
        "id": config_id,
        "name": "Craft Memory",
        "slug": "memory",
        "enabled": True,
        "provider": "craft-memory",
        "type": "mcp",
        "icon": "🧠",
        "tagline": "Persistent cross-session memory with SQLite + FTS5",
        "mcp": {
            "transport": "http",
            "url": f"http://localhost:{_port()}/mcp",
            "authType": "none",
        },
    }
    config_path = source_dir / "config.json"
    if config_path.exists():
        print(f"  Source config already exists: {config_path} (skipping)")
    else:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print(f"  ✓ Created source config: {config_path}")

    # Write permissions.json
    perms = {
        "allowedMcpPatterns": [
            {"pattern": "remember", "comment": "Store episodic memories"},
            {"pattern": "search_memory", "comment": "Search memories via FTS5"},
            {"pattern": "get_recent_memory", "comment": "Get recent memories"},
            {"pattern": "upsert_fact", "comment": "Store/update stable facts"},
            {"pattern": "list_open_loops", "comment": "List open loops"},
            {"pattern": "close_open_loop", "comment": "Close open loops"},
            {"pattern": "summarize_scope", "comment": "Generate scope summary"},
        ]
    }
    perms_path = source_dir / "permissions.json"
    if perms_path.exists():
        print(f"  Permissions already exist: {perms_path} (skipping)")
    else:
        with open(perms_path, "w", encoding="utf-8") as f:
            json.dump(perms, f, indent=2)
        print(f"  ✓ Created permissions: {perms_path}")

    # Write guide.md
    guide = """# Craft Memory

Persistent cross-session memory for your Craft Agents workspace.

## What it does
- **Remember**: Store decisions, discoveries, and key takeaways across sessions
- **Facts**: Stable knowledge that persists (tech stack, conventions, patterns)
- **Open loops**: Track incomplete tasks and follow-ups
- **Search**: Full-text search across all memories

## Available tools
| Tool | Purpose |
|------|---------|
| `remember` | Store an episodic memory |
| `search_memory` | Full-text search |
| `get_recent_memory` | Get recent memories |
| `upsert_fact` | Store/update a stable fact |
| `list_open_loops` | List open loops |
| `close_open_loop` | Close an open loop |
| `summarize_scope` | Generate comprehensive summary |

## When to use each tool
- **Session start**: `get_recent_memory` + `list_open_loops` to recover context
- **During work**: `remember` for decisions/discoveries, `upsert_fact` for confirmed knowledge
- **Session end**: `remember` key takeaways + `summarize_scope` for handoff

## Troubleshooting
| Issue | Solution |
|-------|----------|
| Tool not found | Server may be down. Ask: "start memory server" |
| "Session not found" | Server was restarted. Just retry |
| "Not connected" | Check HTTP transport is configured, not stdio |
"""
    guide_path = source_dir / "guide.md"
    if guide_path.exists():
        print(f"  Guide already exists: {guide_path} (skipping)")
    else:
        with open(guide_path, "w", encoding="utf-8") as f:
            f.write(guide)
        print(f"  ✓ Created guide: {guide_path}")

    # Update enabledSourceSlugs in workspace config.json
    ws_config_path = ws_dir / "config.json"
    if ws_config_path.exists():
        with open(ws_config_path, "r", encoding="utf-8") as f:
            ws_config = json.load(f)
        slugs = ws_config.get("defaults", {}).get("enabledSourceSlugs", [])
        if "memory" not in slugs:
            slugs.append("memory")
            ws_config.setdefault("defaults", {})["enabledSourceSlugs"] = slugs
            with open(ws_config_path, "w", encoding="utf-8") as f:
                json.dump(ws_config, f, indent=2)
            print(f"  ✓ Added 'memory' to enabledSourceSlugs")
        else:
            print(f"  'memory' already in enabledSourceSlugs")

    # Copy skills
    skills_dir = ws_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    # Skills live at the repo root: <craft-memory>/skills/
    # Path(__file__) = src/craft_memory_mcp/cli.py → go up 3 levels to repo root
    package_skills = Path(__file__).parent.parent.parent / "skills"
    skill_names = ["memory-start", "memory-protocol", "memory-maintenance", "session-handoff"]
    if package_skills.exists():
        copied = 0
        for skill_name in skill_names:
            src_skill = package_skills / skill_name
            dst_skill = skills_dir / skill_name
            if not src_skill.exists():
                print(f"  WARN: skill not found: {src_skill}")
                continue
            if dst_skill.exists():
                print(f"  Skill already exists: {skill_name} (skipping)")
            else:
                shutil.copytree(src_skill, dst_skill)
                print(f"  Copied skill: {skill_name}")
                copied += 1
        if copied:
            print(f"  {copied} skill(s) installed to {skills_dir}")
    else:
        print(f"  WARN: Skills source not found at {package_skills}")
        print(f"        Copy manually: {', '.join(skill_names)}")

    # Ensure server is running
    print(f"\n  Ensuring server is running...")
    if not is_alive():
        pid = start_server()
        if pid and wait_for_alive():
            print(f"  ✓ Server started (PID {pid})")
        else:
            print(f"  ⚠ Could not start server. Run: craft-memory ensure")

    print(f"\n✓ Craft Memory installed to workspace: {ws_dir}")
    print(f"  Next: Start a new Craft Agents session and say 'check my memory'")


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

    # install
    p_install = sub.add_parser("install", help="Install into a Craft Agents workspace")
    p_install.add_argument("--workspace", default=None, help="Path to workspace directory")

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
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
