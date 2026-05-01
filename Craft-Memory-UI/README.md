# Craft Memory UI

Welcome to the frontend interface for **Craft Memory**, a persistent neural memory system for AI agents.

This UI provides a visualization and management layer over the SQLite/FTS5 backend, allowing human operators and agents to inspect memories, manage open loops, view knowledge graphs, and handle session handoffs.

## Philosophy

The Craft Memory UI is designed with a **zero-build-step** philosophy:
- No Webpack, Vite, or Node.js required.
- React and Babel are loaded via CDN.
- JSX is transpiled directly in the browser on-the-fly.
- You can simply serve the directory with any static HTTP server.

This approach ensures maximum portability and simplicity, fitting perfectly into lightweight agentic workflows without requiring complex tooling chains.

## Features

- **Dashboard:** Operational overview, uptime stats, recent memories, and "god facts".
- **Explorer:** Hybrid RRF search (FTS5 + semantic) with debounce and real-time filtering (category, scope, core).
- **Knowledge Graph:** Interactive force-directed layout showing relationships (core, context, detail, temporal, causal) between memories.
- **Open Loops Kanban:** Board for tracking and prioritizing unresolved agent tasks or cognitive loops.
- **Session Handoff:** Generates structured markdown summaries of a session (decisions, discoveries, next steps) for seamless context transfer.
- **Diff Stream:** Live stream of state changes.

## Usage

Since there's no build step, simply serve the `Craft-Memory-UI` directory using any local web server. For example:

```bash
# Using Python
python -m http.server 8000

# Using Node.js
npx serve .
```

Then open `http://localhost:8000` in your browser.

*Note: The UI expects the Craft Memory Python backend API to be running on `http://localhost:8080` (or as configured in `src/config.jsx`).*

## Documentation

For technical details on how the UI is structured and its data flow, see [ARCHITECTURE.md](./ARCHITECTURE.md).
