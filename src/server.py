"""
Craft Memory — standalone entry point shim.

Delegates to the canonical package: src/craft_memory_mcp/server.py
PYTHONPATH must include src/ (already set by ensure-running.py and start-http.bat).
"""
from craft_memory_mcp.server import run_server

if __name__ == "__main__":
    run_server()
