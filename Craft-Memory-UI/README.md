# Craft Memory UI

Welcome to the frontend interface for **Craft Memory**, a persistent neural memory system for AI agents.

This UI is natively integrated into the Craft Memory FastMCP server. It provides a visualization and management layer over the SQLite/FTS5 backend, allowing human operators and agents to inspect memories, manage open loops, view knowledge graphs, and handle session handoffs.

## Philosophy

The Craft Memory UI is designed with a **zero-build-step** philosophy:
- No Webpack, Vite, or Node.js required.
- React and Babel are loaded via CDN.
- JSX is transpiled directly in the browser on-the-fly.
- The UI is served directly by the Python `craft-memory` HTTP backend (via `StaticFiles`).

This approach ensures maximum portability and simplicity, fitting perfectly into lightweight agentic workflows without requiring complex tooling chains.

## Features

- **Dashboard:** Operational overview, uptime stats, recent memories, and "god facts".
- **Explorer:** Hybrid RRF search (FTS5 + semantic) with debounce and real-time filtering (category, scope, core).
- **Knowledge Graph:** Interactive force-directed layout showing relationships (core, context, detail, temporal, causal) between memories.
- **Open Loops Kanban:** Board for tracking and prioritizing unresolved agent tasks or cognitive loops.
- **Session Handoff:** Generates structured markdown summaries of a session (decisions, discoveries, next steps) for seamless context transfer.
- **Diff Stream:** Live stream of state changes.

## Usage

You do **not** need to run a separate web server. 
When you start the Craft Memory HTTP server:

```bash
craft-memory ensure
# or
CRAFT_MEMORY_TRANSPORT=http craft-memory serve
```

The UI is automatically available at:
👉 **http://127.0.0.1:8392/ui/**

The UI communicates directly with the same Python backend process using custom REST endpoints (`/api/...`) that are mounted alongside the primary `/mcp` endpoints.

## Documentation

For technical details on how the UI is structured and its data flow, see [ARCHITECTURE.md](./ARCHITECTURE.md).
