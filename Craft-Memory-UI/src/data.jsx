// Static helpers — dynamic data is loaded from the server by app.jsx via CRAFT_API
const NOW = Date.now();

const CATEGORIES = [
  { id: "decision",  label: "decision",  color: "oklch(0.78 0.18 var(--accent-h))" },
  { id: "discovery", label: "discovery", color: "oklch(0.82 0.14 175)" },
  { id: "bugfix",    label: "bugfix",    color: "oklch(0.72 0.20 22)" },
  { id: "feature",   label: "feature",   color: "oklch(0.78 0.16 280)" },
  { id: "refactor",  label: "refactor",  color: "oklch(0.78 0.16 55)" },
  { id: "change",    label: "change",    color: "oklch(0.78 0.12 95)" },
  { id: "note",      label: "note",      color: "oklch(0.7 0.04 var(--accent-h))" },
];

const SCOPES = ["session", "project", "workspace", "user", "global"];

const formatRelTime = (ts) => {
  const diff = Date.now() - ts;
  if (diff < 60000)   return "just now";
  if (diff < 3600000) return Math.floor(diff / 60000) + "m ago";
  if (diff < 86400000) return Math.floor(diff / 3600000) + "h ago";
  return Math.floor(diff / 86400000) + "d ago";
};

const formatTime = (ts) => new Date(ts).toTimeString().slice(0, 5);

const EMPTY_STATS = {
  memoriesTotal: 0,
  memoriesCore: 0,
  factsTotal: 0,
  loopsOpen: 0,
  loopsCritical: 0,
  proceduresTotal: 0,
  edgesTotal: 0,
  workspaceSize: "—",
  oldestMemory: "—",
  uptime: "—",
};

// Initialise window.CRAFT with empty arrays — app.jsx populates these from the API
window.CRAFT = {
  CATEGORIES,
  SCOPES,
  MEMORIES: [],
  FACTS: [],
  LOOPS: [],
  RELATIONS: [],
  DIFF_EVENTS: [],
  SESSIONS: [],
  STATS: { ...EMPTY_STATS },
  HEATMAP: {},
  TIMELINE: [],
  formatRelTime,
  formatTime,
};
