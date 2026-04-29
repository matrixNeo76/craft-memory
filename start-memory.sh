#!/usr/bin/env bash
# Craft Memory HTTP Server — Unix/macOS launcher
# Usage:  ./start-memory.sh [start|stop|status]
# Default action: start

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${SCRIPT_DIR}/.craft-memory.pid"
LOG_FILE="${SCRIPT_DIR}/.craft-memory.log"

export CRAFT_WORKSPACE_ID="${CRAFT_WORKSPACE_ID:-default}"
export CRAFT_MEMORY_TRANSPORT=http
export CRAFT_MEMORY_HOST="${CRAFT_MEMORY_HOST:-127.0.0.1}"
export CRAFT_MEMORY_PORT="${CRAFT_MEMORY_PORT:-8392}"
export PYTHONPATH="${SCRIPT_DIR}/src"

cmd_start() {
    if [[ -f "$PID_FILE" ]]; then
        existing_pid=$(cat "$PID_FILE")
        if kill -0 "$existing_pid" 2>/dev/null; then
            echo "Server already running (PID $existing_pid)"
            echo "  Endpoint: http://${CRAFT_MEMORY_HOST}:${CRAFT_MEMORY_PORT}/mcp"
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi

    echo "============================================"
    echo "  Craft Memory HTTP Server"
    echo "  Endpoint: http://${CRAFT_MEMORY_HOST}:${CRAFT_MEMORY_PORT}/mcp"
    echo "  Health:   http://${CRAFT_MEMORY_HOST}:${CRAFT_MEMORY_PORT}/health"
    echo "  Log:      ${LOG_FILE}"
    echo "============================================"

    nohup python "${SCRIPT_DIR}/src/server.py" \
        > "$LOG_FILE" 2>&1 &
    server_pid=$!
    echo "$server_pid" > "$PID_FILE"

    # Wait up to 5 s for the server to become healthy
    for i in {1..10}; do
        sleep 0.5
        if curl -sf "http://${CRAFT_MEMORY_HOST}:${CRAFT_MEMORY_PORT}/health" >/dev/null 2>&1; then
            echo "Server started (PID $server_pid)"
            return 0
        fi
    done

    echo "WARNING: Server did not respond after 5s — check ${LOG_FILE}"
}

cmd_stop() {
    if [[ ! -f "$PID_FILE" ]]; then
        echo "No PID file found — server not running via this script"
        return 0
    fi
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        rm -f "$PID_FILE"
        echo "Server stopped (PID $pid)"
    else
        echo "Process $pid not found — removing stale PID file"
        rm -f "$PID_FILE"
    fi
}

cmd_status() {
    if [[ -f "$PID_FILE" ]]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Running (PID $pid)"
            curl -sf "http://${CRAFT_MEMORY_HOST}:${CRAFT_MEMORY_PORT}/health" 2>/dev/null \
                | python3 -m json.tool 2>/dev/null || true
            return 0
        fi
    fi
    echo "Not running"
}

case "${1:-start}" in
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    restart) cmd_stop; cmd_start ;;
    *)
        echo "Usage: $0 [start|stop|status|restart]"
        exit 1
        ;;
esac
