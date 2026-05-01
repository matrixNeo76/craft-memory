# Architecture — Craft Memory UI

This document outlines the technical architecture of the Craft Memory UI. 

## 1. Core Paradigm: Zero-Build React

The UI is built using **React 18** and **Babel Standalone**, directly in the browser. 
There is no Node.js build step, no Webpack, and no Vite. 

- `index.html` loads React and Babel via CDN.
- All components are written in `.jsx` files and included via `<script type="text/babel" src="...">`.
- A cache-busting mechanism (`cache-bust.js`) intercepts `XMLHttpRequest` and `fetch` calls made by Babel to ensure JSX files bypass Chromium's memory cache during development.

## 2. Global State & Data Flow

Instead of Redux or Context APIs, the UI relies heavily on a globally scoped object: `window.CRAFT`.

### Bootstrapping (`app.jsx`)
When the application loads, it runs an initialization sequence:
1. Fetches foundational data via `CRAFT_API.init()`.
2. Populates `window.CRAFT` with:
   - `MEMORIES`: Most recent memory nodes.
   - `STATS`: System statistics (uptime, counts).
   - `FACTS`: High-scoring knowledge.
   - `CATEGORIES` & `SCOPES`: Enums for styling and filtering.
3. Renders the main shell and router.

### Component State
Components handle their own localized states (e.g., search queries, active filters, form drafts) using standard React hooks (`useState`, `useEffect`).

When a component needs to mutate global data (e.g., adding a new memory in `explorer.jsx`), it posts to the backend via `CRAFT_API`, and upon success, optimistically updates the `window.CRAFT` object (e.g., prepending the new memory) and forces a local state update to reflect changes immediately without a full page reload.

## 3. Directory Structure

```text
Craft-Memory-UI/
├── index.html            # Entry point, CSS variables, global styles, CDN links
├── index.css             # Vanilla CSS (if externalized)
├── cache-bust.js         # Interceptor to prevent JSX caching during dev
├── DEBUG_PLAN.md         # Living document for UI bug tracking and feature planning
├── README.md             # High-level overview
├── ARCHITECTURE.md       # This file
├── tweaks-panel.jsx      # Hidden panel for adjusting UI parameters dynamically
└── src/
    ├── api.jsx           # CRAFT_API object encapsulating all fetch calls to the Python backend
    ├── app.jsx           # Main App component, Shell layout, routing logic, boot sequence
    ├── config.jsx        # Configuration constants (e.g., backend URL)
    ├── data.jsx          # Placeholder/mock data (used if backend is unreachable)
    ├── icons.jsx         # SVG icon library as React components
    ├── logo.jsx          # Animated SVG logo component
    └── screens/          # View components for the router
        ├── dashboard.jsx # Stats, recent activities, diff stream
        ├── diff.jsx      # Historical diffs of memory changes
        ├── explorer.jsx  # FTS5 search interface + Memory creation modal
        ├── graph.jsx     # Force-directed knowledge graph visualization
        ├── handoff.jsx   # Session handoff markdown generator
        └── loops.jsx     # Kanban board for open cognitive loops
```

## 4. UI/UX Design System

- **Vanilla CSS:** Styling is handled primarily via `<style>` blocks injected locally within the components themselves, combined with global CSS variables defined in `index.html`.
- **Theme Variables:** Colors, fonts, and radii are managed via CSS Custom Properties (e.g., `var(--bg-1)`, `var(--accent)`, `var(--font-mono)`).
- **Responsive & Dense modes:** The Shell layout adapts to available width, and a "dense" mode can be toggled to compress paddings for data-heavy views.
- **Icons:** A custom `icons.jsx` file contains all SVG paths, standardizing the visual language without external icon font dependencies.

## 5. Integration with Backend (Python / MCP / REST)

The UI is natively served by the `craft-memory` Python backend process and acts as its visual dashboard.

- **Static Serving:** In `craft_memory_mcp/server.py`, a `StaticFiles` route is mounted at `/ui` to serve the `Craft-Memory-UI` directory directly.
- **REST API:** The Python FastMCP server exposes custom HTTP endpoints (`/api/memories/search`, `/api/loops`, `/api/stats`, etc.) using `@mcp.custom_route(...)`. 
- **FTS5 Search:** `explorer.jsx` delegates real search queries to the backend's `/api/memories/search` endpoint (powered by SQLite FTS5) instead of filtering locally.
- **Routing from MCP:** The UI supports deep-linking or action triggering via URL fragments (`#explorer?action=search`), allowing the Agent/MCP server to dynamically push the human user to specific views and actions.
- **Tool Fallbacks:** Where complex actions are required (e.g., generating a full handoff, linking memories semantically), the UI prompts the user to utilize the MCP client/Agent, acting as an observer to the Agent's actions rather than replicating heavy backend logic in the frontend.
