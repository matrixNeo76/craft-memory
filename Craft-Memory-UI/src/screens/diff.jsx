// Memory Diff — real-time changelog stream via /api/diff
const DiffScreen = ({ onNavigate }) => {
  const { formatRelTime } = window.CRAFT;
  const [since, setSince] = React.useState("4h");
  const [events, setEvents] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [lastFetch, setLastFetch] = React.useState(null);

  const sinceMap = {
    "1h":  3600,
    "4h":  14400,
    "24h": 86400,
    "7d":  604800,
  };

  const fetchDiff = React.useCallback(() => {
    setLoading(true);
    setError(null);
    const epoch = Math.floor(Date.now() / 1000) - sinceMap[since];
    CRAFT_API.diff(epoch)
      .then((diff) => {
        // Convert server diff format → event stream
        const raw = [
          ...(diff.new_memories || []).map((m) => ({
            kind: "memory.new",
            ts: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
            id: m.id,
            summary: (m.content || "").slice(0, 100),
            category: m.category,
          })),
          ...(diff.updated_facts || []).map((f) => ({
            kind: "fact.updated",
            ts: f.updated_at ? new Date(f.updated_at).getTime() : Date.now(),
            key: f.key,
            newValue: String(f.value || ""),
            oldValue: "",
          })),
          ...(diff.new_loops || []).map((l) => ({
            kind: "loop.opened",
            ts: l.created_at ? new Date(l.created_at).getTime() : Date.now(),
            id: l.id,
            summary: l.title || "",
            priority: l.priority || "medium",
          })),
          ...(diff.closed_loops || []).map((l) => ({
            kind: "loop.closed",
            ts: l.closed_at ? new Date(l.closed_at).getTime() : Date.now(),
            id: l.id,
            resolution: l.resolution || "—",
          })),
        ].sort((a, b) => b.ts - a.ts);
        setEvents(raw);
        setLastFetch(new Date());
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [since]);

  // Fetch on mount + when "since" changes
  React.useEffect(() => { fetchDiff(); }, [fetchDiff]);

  const counts = events.reduce((acc, e) => {
    acc[e.kind] = (acc[e.kind] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="diff-scr">
      <style>{`
        .diff-scr { display: flex; flex-direction: column; gap: 16px; }
        .diff-h { display: flex; align-items: end; justify-content: space-between; }
        .diff-h h1 { margin: 0; font-size: 24px; font-weight: 500; }
        .diff-h .sub { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); margin-top: 2px; }
        .since-pick { display: flex; gap: 4px; padding: 4px; background: var(--bg-1); border: 1px solid var(--line); border-radius: var(--radius-sm); }
        .since-pick span { padding: 4px 10px; font-family: var(--font-mono); font-size: 11px; color: var(--ink-2); cursor: pointer; border-radius: 4px; }
        .since-pick span.on { background: var(--bg-3); color: var(--ink-0); }
        .summ-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
        .summ-card { padding: 14px; background: var(--bg-1); border: 1px solid var(--line); border-radius: var(--radius); display: flex; flex-direction: column; gap: 4px; }
        .summ-card .l { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.1em; }
        .summ-card .v { font-family: var(--font-mono); font-size: 22px; color: var(--ink-0); font-weight: 500; }
        .stream { background: var(--bg-1); border: 1px solid var(--line); border-radius: var(--radius); }
        .stream-h { padding: 12px 16px; border-bottom: 1px solid var(--line); display: flex; align-items: center; gap: 10px; font-family: var(--font-mono); font-size: 11px; color: var(--ink-2); }
        .stream-h .live { display: flex; align-items: center; gap: 6px; color: oklch(0.78 0.18 150); }
        .stream-h .pulse { width: 6px; height: 6px; border-radius: 50%; background: oklch(0.78 0.18 150); animation: pulse 1.5s ease-in-out infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        .stream-row { display: grid; grid-template-columns: 90px 110px 1fr 30px; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--line); align-items: start; }
        .stream-row:last-child { border-bottom: 0; }
        .stream-row:hover { background: var(--bg-2); }
        .stream-ts { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); padding-top: 2px; }
        .stream-kind { font-family: var(--font-mono); font-size: 10px; padding: 3px 8px; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.05em; width: max-content; height: max-content; }
        .stream-kind.new  { color: oklch(0.78 0.18 150); background: oklch(0.78 0.18 150 / 0.12); }
        .stream-kind.upd  { color: var(--accent); background: var(--accent-soft); }
        .stream-kind.cls  { color: var(--ink-2); background: var(--bg-3); }
        .stream-kind.crit { color: var(--critical); background: oklch(0.72 0.20 22 / 0.12); }
        .stream-kind.prn  { color: var(--ink-3); background: var(--bg-3); text-decoration: line-through; }
        .stream-kind.prm  { color: var(--accent-2); background: oklch(0.85 0.14 calc(var(--accent-h) + 30) / 0.12); }
        .stream-msg { font-size: 13px; color: var(--ink-1); }
        .stream-msg .id { font-family: var(--font-mono); color: var(--ink-3); }
        .stream-msg .new-val { color: var(--ink-0); font-family: var(--font-mono); }
        .stream-msg .arrow { color: var(--ink-3); margin: 0 4px; font-family: var(--font-mono); }
        .stream-go { color: var(--ink-3); cursor: pointer; padding: 2px; }
        .stream-go:hover { color: var(--accent); }
        .diff-empty { padding: 40px 24px; text-align: center; font-family: var(--font-mono); font-size: 12px; color: var(--ink-3); }
        .diff-loading { padding: 40px 24px; display: flex; align-items: center; justify-content: center; gap: 10px; font-family: var(--font-mono); font-size: 12px; color: var(--ink-3); }
        .diff-error { padding: 20px 24px; color: var(--critical); font-family: var(--font-mono); font-size: 12px; }
      `}</style>

      <div className="diff-h">
        <div>
          <h1>Memory Diff</h1>
          <div className="sub">
            memory_diff(since_epoch) · changes in the last {since}
            {lastFetch && <span style={{ marginLeft: 8, opacity: 0.5 }}>· fetched {formatRelTime(lastFetch.getTime())}</span>}
          </div>
        </div>
        <div className="row gap-12">
          <div className="since-pick">
            {["1h", "4h", "24h", "7d"].map((s) => (
              <span key={s} className={since === s ? "on" : ""} onClick={() => setSince(s)}>{s}</span>
            ))}
          </div>
          <button className="btn" onClick={fetchDiff} disabled={loading}>
            <Icon name="settings" size={12} /> {loading ? "loading…" : "refresh"}
          </button>
        </div>
      </div>

      <div className="summ-grid">
        <div className="summ-card">
          <div className="l">memories.new</div>
          <div className="v" style={{ color: "oklch(0.78 0.18 150)" }}>+{counts["memory.new"] || 0}</div>
        </div>
        <div className="summ-card">
          <div className="l">facts.changed</div>
          <div className="v" style={{ color: "var(--accent)" }}>{counts["fact.updated"] || 0}</div>
        </div>
        <div className="summ-card">
          <div className="l">loops Δ</div>
          <div className="v" style={{ color: "var(--medium)" }}>
            +{counts["loop.opened"] || 0} / -{counts["loop.closed"] || 0}
          </div>
        </div>
        <div className="summ-card">
          <div className="l">total events</div>
          <div className="v">{events.length}</div>
        </div>
      </div>

      <div className="stream">
        <div className="stream-h">
          {loading ? (
            <span style={{ color: "var(--ink-3)" }}>fetching…</span>
          ) : error ? (
            <span style={{ color: "var(--critical)" }}>error: {error}</span>
          ) : (
            <>
              <span className="live"><span className="pulse" /> live</span>
              <span>·</span>
              <span>{events.length} events in last {since}</span>
            </>
          )}
        </div>

        {loading && (
          <div className="diff-loading">
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)", animation: "pulse 1.5s infinite" }} />
            loading diff…
          </div>
        )}
        {!loading && error && (
          <div className="diff-error">Failed to load diff: {error}</div>
        )}
        {!loading && !error && events.length === 0 && (
          <div className="diff-empty">No changes in the last {since}.</div>
        )}
        {!loading && !error && events.map((e, i) => (
          <StreamRow key={i} e={e} onNavigate={onNavigate} />
        ))}
      </div>
    </div>
  );
};

const StreamRow = ({ e, onNavigate }) => {
  const { formatRelTime } = window.CRAFT;
  const kindMap = {
    "memory.new":    { cls: "new",  label: "MEM.NEW" },
    "memory.promoted": { cls: "prm", label: "PROMOTED" },
    "loop.opened":   { cls: "crit", label: "LOOP.OPEN" },
    "loop.closed":   { cls: "cls",  label: "LOOP.CLOSE" },
    "fact.new":      { cls: "new",  label: "FACT.NEW" },
    "fact.updated":  { cls: "upd",  label: "FACT.UPD" },
    "edge.created":  { cls: "new",  label: "EDGE.NEW" },
    "edge.pruned":   { cls: "prn",  label: "EDGE.PRN" },
  };
  const k = kindMap[e.kind] || { cls: "new", label: e.kind.toUpperCase() };

  return (
    <div className="stream-row">
      <div className="stream-ts">{formatRelTime(e.ts)}</div>
      <div className={"stream-kind " + k.cls}>{k.label}</div>
      <div className="stream-msg">
        {e.kind === "memory.new" && (
          <><span className="id">#{e.id}</span> · {e.summary}
          {e.category && <span className="chip muted" style={{ marginLeft: 6 }}>{e.category}</span>}</>
        )}
        {e.kind === "memory.promoted" && <><span className="id">#{e.id}</span> · {e.note}</>}
        {e.kind === "loop.opened" && (
          <><span className="id">#{e.id}</span> · {e.summary}
          <span className="chip" style={{ marginLeft: 6, color: "var(--critical)", borderColor: "oklch(0.72 0.20 22 / 0.4)", background: "oklch(0.72 0.20 22 / 0.1)" }}>{e.priority}</span></>
        )}
        {e.kind === "loop.closed" && <><span className="id">#{e.id}</span> · resolved: {e.resolution}</>}
        {(e.kind === "fact.new" || e.kind === "fact.updated") && (
          <><span className="id">{e.key}</span>
          {e.oldValue && <><span className="arrow">→</span></>}
          <span className="new-val"> {e.newValue}</span></>
        )}
        {e.kind === "edge.created" && (
          <><span className="id">#{e.source}</span><span className="arrow"> ─{e.relation}→ </span><span className="id">#{e.target}</span></>
        )}
        {e.kind === "edge.pruned" && (
          <><span className="id">#{e.source}─#{e.target}</span> · {e.reason}</>
        )}
      </div>
      <span
        className="stream-go"
        onClick={() => onNavigate(
          e.kind.startsWith("loop") ? "loops" :
          e.kind.startsWith("edge") ? "graph" : "explorer"
        )}
      >
        <Icon name="chevron" size={14} />
      </span>
    </div>
  );
};

window.DiffScreen = DiffScreen;
