// Open Loops Kanban — real data via /api/loops, close/add via API
const LoopsScreen = ({ onNavigate }) => {
  const [loops, setLoops] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [filter, setFilter] = React.useState("all");
  const [adding, setAdding] = React.useState(false);
  const [draft, setDraft] = React.useState({ title: "", priority: "medium" });
  const [saving, setSaving] = React.useState(false);

  const PRIORITIES = [
    { id: "critical", label: "critical", color: "var(--critical)" },
    { id: "high",     label: "high",     color: "var(--high)" },
    { id: "medium",   label: "medium",   color: "var(--medium)" },
    { id: "low",      label: "low",      color: "var(--low)" },
  ];

  // ─── Load from server ─────────────────────────────────────────────
  const reload = React.useCallback(() => {
    setLoading(true);
    setError(null);
    CRAFT_API.loops(null, "open")
      .then((rows) => setLoops(rows))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  React.useEffect(() => { reload(); }, [reload]);

  // ─── Close a loop via API (optimistic update) ─────────────────────
  const close = (id) => {
    setLoops((prev) => prev.filter((l) => l.id !== id));
    CRAFT_API.closeLoop(id, null).catch((e) => {
      console.warn("close loop failed:", e.message);
      reload();
    });
  };

  // ─── Cycle priority — persist to backend via PATCH ────────────────
  const cycle = (id) => {
    const order = ["critical", "high", "medium", "low"];
    setLoops((prev) => prev.map((l) => {
      if (l.id !== id) return l;
      const i = order.indexOf(l.priority);
      const nextPriority = order[(i + 1) % order.length];
      // Persist to backend (fire-and-forget with rollback on error)
      CRAFT_API.updateLoop(id, { priority: nextPriority }).catch((e) => {
        console.warn("update loop priority failed:", e.message);
        reload(); // rollback to server state
      });
      return { ...l, priority: nextPriority };
    }));
  };

  // ─── Add a loop via API ───────────────────────────────────────────
  const add = () => {
    if (!draft.title.trim() || saving) return;
    setSaving(true);
    CRAFT_API.addLoop({ title: draft.title.trim(), priority: draft.priority, scope: "workspace" })
      .then((newLoop) => {
        setLoops((prev) => [newLoop, ...prev]);
        setDraft({ title: "", priority: "medium" });
        setAdding(false);
      })
      .catch((e) => { setError("Failed to add loop: " + e.message); setTimeout(() => setError(null), 4000); })
      .finally(() => setSaving(false));

  };

  const visible = loops.filter((l) => filter === "all" || l.scope === filter);

  return (
    <div className="loops">
      <style>{`
        .loops { display: flex; flex-direction: column; gap: 16px; }
        .loops-h { display: flex; align-items: end; justify-content: space-between; }
        .loops-h h1 { margin: 0; font-size: 24px; font-weight: 500; }
        .loops-h .sub { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); margin-top: 2px; }
        .kanban { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; align-items: start; }
        .kcol { background: var(--bg-1); border: 1px solid var(--line); border-radius: var(--radius); display: flex; flex-direction: column; min-height: 400px; }
        .kcol-h { padding: 12px 14px; border-bottom: 1px solid var(--line); display: flex; align-items: center; gap: 8px; }
        .kcol-pri { font-family: var(--font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
        .kcol-count { margin-left: auto; font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); padding: 2px 6px; border-radius: 999px; background: var(--bg-2); }
        .kcol-bar { height: 2px; }
        .kcol-body { padding: 10px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
        .lcard { background: var(--bg-2); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 12px; cursor: pointer; transition: border-color 0.15s, transform 0.15s; }
        .lcard:hover { border-color: var(--line-2); transform: translateY(-1px); }
        .lcard-top { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); margin-bottom: 6px; }
        .lcard-id { color: var(--ink-2); }
        .lcard-title { font-size: 13px; color: var(--ink-0); line-height: 1.45; font-weight: 500; }
        .lcard-desc { font-size: 12px; color: var(--ink-2); line-height: 1.5; margin-top: 6px; }
        .lcard-meta { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); }
        .lcard-actions { display: flex; gap: 4px; margin-top: 10px; opacity: 0; transition: opacity 0.15s; }
        .lcard:hover .lcard-actions { opacity: 1; }
        .lcard-action { padding: 3px 8px; font-family: var(--font-mono); font-size: 10px; border-radius: 3px; background: var(--bg-3); color: var(--ink-2); cursor: pointer; border: 1px solid var(--line); }
        .lcard-action:hover { color: var(--ink-0); border-color: var(--line-2); }
        .lcard-action.danger:hover { color: var(--critical); border-color: oklch(0.72 0.20 22 / 0.5); }
        .add-card { background: var(--bg-2); border: 1px dashed var(--line-2); border-radius: var(--radius-sm); padding: 12px; cursor: pointer; color: var(--ink-3); font-family: var(--font-mono); font-size: 11px; text-align: center; }
        .add-card:hover { color: var(--accent); border-color: var(--accent); }
        .add-form { background: var(--bg-2); border: 1px solid var(--accent-soft); border-radius: var(--radius-sm); padding: 10px; }
        .add-form input { width: 100%; background: var(--bg-1); border: 1px solid var(--line); border-radius: 4px; padding: 6px 8px; color: var(--ink-0); font: inherit; font-size: 12px; outline: none; }
        .add-form input:focus { border-color: var(--accent); }
        .add-form-row { display: flex; gap: 4px; margin-top: 8px; }
        .pri-pick { display: flex; gap: 4px; }
        .pri-btn { padding: 3px 8px; border-radius: 999px; font-family: var(--font-mono); font-size: 10px; cursor: pointer; border: 1px solid var(--line); }
        .pri-btn.on { color: var(--bg-0); }
        .filter-bar { display: flex; gap: 6px; padding: 4px; background: var(--bg-1); border: 1px solid var(--line); border-radius: var(--radius-sm); width: max-content; }
        .filter-bar span { padding: 4px 10px; font-family: var(--font-mono); font-size: 11px; color: var(--ink-2); cursor: pointer; border-radius: 4px; }
        .filter-bar span.on { background: var(--bg-3); color: var(--ink-0); }
        .loops-loading { padding: 60px 24px; display: flex; align-items: center; justify-content: center; gap: 10px; font-family: var(--font-mono); font-size: 12px; color: var(--ink-3); }
        .loops-error { padding: 20px 24px; color: var(--critical); font-family: var(--font-mono); font-size: 12px; }
      `}</style>

      <div className="loops-h">
        <div>
          <h1>Open Loops</h1>
          <div className="sub">tracked across sessions until resolved · ordered by priority</div>
        </div>
        <div className="row gap-12">
          <div className="filter-bar">
            {["all", "project", "workspace", "global"].map((f) => (
              <span key={f} className={filter === f ? "on" : ""} onClick={() => setFilter(f)}>{f}</span>
            ))}
          </div>
          <button className="btn" onClick={reload} disabled={loading} style={{ opacity: loading ? 0.5 : 1 }}>
            ↻
          </button>
          <button className="btn primary" onClick={() => setAdding(true)}>
            <Icon name="plus" /> Add loop
          </button>
        </div>
      </div>

      {loading && (
        <div className="loops-loading">
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)", animation: "pulse 1.5s infinite" }} />
          loading loops…
        </div>
      )}
      {!loading && error && (
        <div className="loops-error">Failed to load loops: {error}</div>
      )}

      {!loading && !error && (
        <div className="kanban">
          {PRIORITIES.map((p) => {
            const items = visible.filter((l) => l.priority === p.id);
            return (
              <div className="kcol" key={p.id}>
                <div className="kcol-h">
                  <span className="kcol-pri" style={{ color: p.color }}>● {p.label}</span>
                  <span className="kcol-count">{items.length}</span>
                </div>
                <div className="kcol-bar" style={{ background: p.color, opacity: 0.6 }} />
                <div className="kcol-body">

                  {adding && draft.priority === p.id && (
                    <div className="add-form">
                      <input
                        placeholder="loop title…"
                        value={draft.title}
                        autoFocus
                        onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") add();
                          if (e.key === "Escape") setAdding(false);
                        }}
                      />
                      <div className="add-form-row">
                        <div className="pri-pick">
                          {PRIORITIES.map((pp) => (
                            <span
                              key={pp.id}
                              className={"pri-btn" + (draft.priority === pp.id ? " on" : "")}
                              style={{
                                background: draft.priority === pp.id ? pp.color : "transparent",
                                borderColor: pp.color,
                                color: draft.priority === pp.id ? "var(--bg-0)" : pp.color,
                              }}
                              onClick={() => setDraft({ ...draft, priority: pp.id })}
                            >{pp.id}</span>
                          ))}
                        </div>
                        <button className="btn primary" style={{ marginLeft: "auto" }} onClick={add} disabled={saving}>
                          {saving ? "saving…" : "Save"}
                        </button>
                        <button className="btn ghost" onClick={() => setAdding(false)}>Cancel</button>
                      </div>
                    </div>
                  )}

                  {items.map((l) => (
                    <div className="lcard" key={l.id}>
                      <div className="lcard-top">
                        <span className="lcard-id">#{l.id}</span>
                        <span className="dim">· {l.scope}</span>
                        <span style={{ marginLeft: "auto" }}>{l.age}d old</span>
                      </div>
                      <div className="lcard-title">{l.title}</div>
                      {l.description && (
                        <div className="lcard-desc">{l.description}</div>
                      )}
                      <div className="lcard-actions">
                        <span className="lcard-action" onClick={() => cycle(l.id)}>↑ priority</span>
                        <span className="lcard-action danger" onClick={() => close(l.id)}>✓ close</span>
                      </div>
                    </div>
                  ))}

                  {!adding && (
                    <div
                      className="add-card"
                      onClick={() => { setDraft({ ...draft, priority: p.id }); setAdding(true); }}
                    >+ add to {p.label}</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

window.LoopsScreen = LoopsScreen;
