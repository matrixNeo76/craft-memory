"""
Craft Memory — ensure-running.py
Checks if the HTTP server is alive; starts it if not.

Usage:
    python ensure-running.py          # check & start if needed
    python ensure-running.py --check  # only check, don't start
    python ensure-running.py --stop   # stop a running server

Exit codes:
    0 = server is running (was already up or just started)
    1 = server could not be started
    2 = server is not running (--check mode only)
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

# ─── Configuration ───────────────────────────────────────────────────

PYTHON = os.environ.get("CRAFT_MEMORY_PYTHON", sys.executable)

_default_home = os.path.join(os.path.expanduser("~"), "craft-memory")
CRAFT_MEMORY_HOME = os.environ.get("CRAFT_MEMORY_HOME", _default_home)
SERVER_DIR = os.path.join(CRAFT_MEMORY_HOME, "src")
SERVER_SCRIPT = os.path.join(SERVER_DIR, "server.py")

HOST = os.environ.get("CRAFT_MEMORY_HOST", "127.0.0.1")
PORT = int(os.environ.get("CRAFT_MEMORY_PORT", "8392"))
HEALTH_URL = f"http://{HOST}:{PORT}/health"
STARTUP_TIMEOUT = 10  # seconds to wait for server to become ready


# ─── Helpers ─────────────────────────────────────────────────────────

def is_alive():
    """Check if the server responds to /health."""
    try:
        req = urllib.request.Request(HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "healthy"
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, OSError):
        return False


def start_server():
    """Start the server as a detached background process."""
    env = os.environ.copy()
    env["CRAFT_WORKSPACE_ID"] = env.get("CRAFT_WORKSPACE_ID", "ws_ecad0f3d")
    env["CRAFT_MEMORY_TRANSPORT"] = "http"
    env["CRAFT_MEMORY_HOST"] = HOST
    env["CRAFT_MEMORY_PORT"] = str(PORT)
    env["PYTHONPATH"] = SERVER_DIR

    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP = 0x00000008 | 0x00000200
    creationflags = 0x00000208
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        proc = subprocess.Popen(
            [PYTHON, "-u", SERVER_SCRIPT],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )
        return proc.pid
    except Exception as e:
        print(f"ERROR: Failed to start server: {e}", file=sys.stderr)
        return None


def wait_for_alive(timeout=STARTUP_TIMEOUT):
    """Poll /health until the server is ready or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_alive():
            return True
        time.sleep(0.5)
    return False


def stop_server():
    """Stop a running server by finding the process on the port."""
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["netstat", "-aon"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if f":{PORT}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    subprocess.run(["taskkill", "/F", "/PID", pid],
                                   capture_output=True, timeout=5)
                    print(f"Stopped process PID {pid}")
                    return True
        except Exception as e:
            print(f"ERROR: Could not stop server: {e}", file=sys.stderr)
    return False


# ─── Main ────────────────────────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    if mode == "--stop":
        if stop_server():
            print("Memory server stopped.")
            sys.exit(0)
        else:
            print("No running server found on port", PORT)
            sys.exit(1)

    if mode == "--check":
        if is_alive():
            print(f"OK: Memory server is running on port {PORT}")
            sys.exit(0)
        else:
            print(f"DOWN: Memory server is not responding on port {PORT}")
            sys.exit(2)

    # Default: ensure running
    if is_alive():
        print(f"OK: Memory server already running on port {PORT}")
        sys.exit(0)

    print(f"Starting memory server on port {PORT}...")
    pid = start_server()
    if pid is None:
        print("ERROR: Could not start server", file=sys.stderr)
        sys.exit(1)

    print(f"Server process started (PID {pid}), waiting for readiness...")
    if wait_for_alive():
        print(f"OK: Memory server is ready at http://{HOST}:{PORT}/mcp")
        sys.exit(0)
    else:
        print(f"ERROR: Server started but not responding after {STARTUP_TIMEOUT}s", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
