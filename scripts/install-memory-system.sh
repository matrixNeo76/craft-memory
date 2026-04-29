#!/usr/bin/env bash
# Craft Memory System - Bootstrap/Installation Script
# Sets up the persistent memory MCP server for Craft Agents
#
# Usage: bash install-memory-system.sh [workspace_path]
#
# Example: bash install-memory-system.sh ~/.craft-agent/workspaces/my-workspace

set -euo pipefail

echo "🧠 Craft Memory System - Installation"
echo "======================================"

# ─── Configuration ────────────────────────────────────────────────────
WORKSPACE_PATH="${1:-}"
MEMORY_SERVER_DIR="$HOME/craft-memory"
MEMORY_DB_DIR="$HOME/.craft-agent/memory"

# ─── Step 1: Install Python dependencies ──────────────────────────────
echo ""
echo "📦 Step 1: Installing Python dependencies..."
cd "$MEMORY_SERVER_DIR"
pip install fastmcp 2>/dev/null || pip3 install fastmcp 2>/dev/null
echo "   ✅ Dependencies installed"

# ─── Step 2: Verify server can start ──────────────────────────────────
echo ""
echo "🔍 Step 2: Verifying server..."
PYTHONPATH=src python -c "from server import mcp; print(f'   ✅ Server OK: {mcp.name}')" 2>/dev/null || {
    echo "   ❌ Server verification failed. Check Python and FastMCP installation."
    exit 1
}

# ─── Step 3: Create memory database directory ──────────────────────────
echo ""
echo "📂 Step 3: Creating database directory..."
mkdir -p "$MEMORY_DB_DIR"
echo "   ✅ Directory: $MEMORY_DB_DIR"

# ─── Step 4: Auto-detect workspace ───────────────────────────────────
echo ""
echo "🔎 Step 4: Detecting workspace..."

if [ -z "$WORKSPACE_PATH" ]; then
    # Try to find workspace automatically
    WORKSPACE_PATH=$(find "$HOME/.craft-agent/workspaces" -maxdepth 1 -mindepth 1 -type d | head -1)
fi

if [ -z "$WORKSPACE_PATH" ] || [ ! -d "$WORKSPACE_PATH" ]; then
    echo "   ⚠️  Could not auto-detect workspace."
    echo "   Run: bash install-memory-system.sh /path/to/your/workspace"
    echo ""
    echo "   To find your workspace ID:"
    echo "   ls ~/.craft-agent/workspaces/"
    exit 1
fi

WORKSPACE_ID=$(basename "$WORKSPACE_PATH")
echo "   ✅ Workspace: $WORKSPACE_ID ($WORKSPACE_PATH)"

# ─── Step 5: Verify source configuration ─────────────────────────────
echo ""
echo "📋 Step 5: Verifying source configuration..."
SOURCE_DIR="$WORKSPACE_PATH/sources/memory"

if [ -d "$SOURCE_DIR" ] && [ -f "$SOURCE_DIR/config.json" ]; then
    echo "   ✅ Memory source already configured"
else
    echo "   ⚠️  Memory source not found. Create it in Craft Agent by adding a source with:"
    echo "   - Type: MCP (stdio)"
    echo "   - Command: python"
    echo "   - Args: -u $MEMORY_SERVER_DIR/src/server.py"
    echo "   - Env: CRAFT_WORKSPACE_ID=$WORKSPACE_ID, PYTHONPATH=$MEMORY_SERVER_DIR/src"
fi

# ─── Step 6: Verify skills ────────────────────────────────────────────
echo ""
echo "🎯 Step 6: Verifying skills..."
SKILLS_DIR="$WORKSPACE_PATH/skills"
for skill in memory-protocol session-handoff memory-maintenance; do
    if [ -f "$SKILLS_DIR/$skill/SKILL.md" ]; then
        echo "   ✅ Skill: $skill"
    else
        echo "   ⚠️  Skill missing: $skill"
    fi
done

# ─── Step 7: Verify automations ───────────────────────────────────────
echo ""
echo "⚡ Step 7: Verifying automations..."
if [ -f "$WORKSPACE_PATH/automations.json" ]; then
    echo "   ✅ automations.json exists"
    # Check for key automations
    if grep -q "SessionStart" "$WORKSPACE_PATH/automations.json"; then
        echo "   ✅ SessionStart automation configured"
    fi
    if grep -q "SessionEnd" "$WORKSPACE_PATH/automations.json"; then
        echo "   ✅ SessionEnd automation configured"
    fi
    if grep -q "SchedulerTick" "$WORKSPACE_PATH/automations.json"; then
        echo "   ✅ SchedulerTick (maintenance) automation configured"
    fi
else
    echo "   ⚠️  automations.json not found"
fi

# ─── Summary ──────────────────────────────────────────────────────────
echo ""
echo "======================================"
echo "🧠 Craft Memory System - Installation Complete!"
echo ""
echo "   Server:  $MEMORY_SERVER_DIR"
echo "   DB:      $MEMORY_DB_DIR/${WORKSPACE_ID}.db"
echo ""
echo "   Next steps:"
echo "   1. Restart Craft Agent to load the memory source"
echo "   2. Start a new session - the SessionStart automation will recover context"
echo "   3. End the session - the SessionEnd automation will save handoff"
echo "   4. Open a new session with a different model/provider - context persists!"
echo ""
