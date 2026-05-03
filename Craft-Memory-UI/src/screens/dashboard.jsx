// Dashboard — stats hero + recent memories + god_facts + diff stream
const DashboardScreen = ({ onNavigate, action }) => {
  const { STATS, MEMORIES, FACTS, formatRelTime, CATEGORIES } = window.CRAFT;
  const [diffEvents, setDiffEvents] = React.useState(window.CRAFT.DIFF_EVENTS || []);
  const [maintenanceMsg, setMaintenanceMsg] = React.useState(null);

  // ─── Wiki health check (lint) state ──────────────────────────────────
  const [lintResult, setLintResult] = React.useState(null);
  const [linting, setLinting] = React.useState(false);
  const [lintError, setLintError] = React.useState(null);
  const runLint = () => {
    setLinting(true); setLintError(null);
    CRAFT_API.lint()
      .then((r) => setLintResult(r))
      .catch((e) => { setLintError(e.message); setLintResult(null); })
      .finally(() => setLinting(false));
  };

  // ─── Wiki export state ──────────────────────────────────────────────
  const exportPathRef = React.useRef(null);
  const [exportPath, setExportPath] = React.useState("./wiki");
  const [exportMinImp, setExportMinImp] = React.useState(5);
  const [exportResult, setExportResult] = React.useState(null);
  const [exporting, setExporting] = React.useState(false);
  const [exportError, setExportError] = React.useState(null);
  const runExport = () => {
    const path = exportPathRef.current?.value || exportPath;
    setExportPath(path); setExporting(true); setExportError(null); setExportResult(null);
    CRAFT_API.exportWiki({ output_dir: path, min_importance: exportMinImp })
      .then((r) => setExportResult(r))
      .catch((e) => setExportError(e.message))
      .finally(() => setExporting(false));
  };

  const recent = MEMORIES.slice(0, 5);
  const godFacts = [...FACTS].sort((a, b) => b.godScore - a.godScore).slice(0, 6);

  // React to routeArgs.action from sidebar MCP tool clicks
  React.useEffect(() => {
    if (action === "maintenance") {
      setMaintenanceMsg("run_maintenance() — use the MCP client to run the maintenance routine");
      setTimeout(() => setMaintenanceMsg(null), 3000);
    }
  }, [action]);

  // Load diff events from backend if not already loaded globally
  React.useEffect(() => {
    if (diffEvents.length > 0) return; // already populated by loadData
    const since = new Date(Date.now() - 4 * 3600000).toISOString(); // 4h ago
    CRAFT_API.diff(since)
      .then((r) => {
        const evts = Array.isArray(r) ? r : (r?.events ?? []);
        setDiffEvents(evts);
        window.CRAFT.DIFF_EVENTS = evts; // cache globally
      })
      .catch((e) => console.warn("[dashboard] diff load failed:", e.message));
  }, []);

  const catColor = (id) => CATEGORIES.find(c => c.id === id)?.color || "var(--ink-2)";


  return (
    <div className="dash">
      <style>{`
        .dash { display: flex; flex-direction: column; gap: 16px; }
        .dash-h { display: flex; align-items: end; justify-content: space-between; gap: 16px; }
        .dash-h h1 { margin: 0; font-size: 24px; font-weight: 500; letter-spacing: -0.01em; }
        .dash-h .dash-sub { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); margin-top: 2px; }
        .stat-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }
        .stat-card { padding: 14px; background: var(--bg-1); border: 1px solid var(--line); border-radius: var(--radius); position: relative; overflow: hidden; }
        .stat-card .v { font-family: var(--font-mono); font-size: 22px; font-weight: 500; color: var(--ink-0); letter-spacing: -0.01em; }
        .stat-card .l { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px; }
        .stat-card .delta { position: absolute; top: 10px; right: 12px; font-family: var(--font-mono); font-size: 10px; color: oklch(0.78 0.18 150); }
        .stat-card.accent { border-color: var(--accent-soft); }
        .stat-card.accent::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: var(--accent); box-shadow: 0 0 12px var(--accent); }
        .stat-card.crit { border-color: oklch(0.72 0.20 22 / 0.4); }
        .stat-card.crit .v { color: var(--critical); }
        .dash-row { display: grid; grid-template-columns: 1.6fr 1fr; gap: 16px; }
        .dash-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .mem-row { display: grid; grid-template-columns: 60px 90px 1fr 110px 80px; gap: 12px; align-items: start; padding: 10px 16px; border-bottom: 1px solid var(--line); transition: background 0.15s; cursor: pointer; }
        .mem-row:last-child { border-bottom: 0; }
        .mem-row:hover { background: var(--bg-2); }
        .mem-id { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); padding-top: 1px; }
        .mem-cat { display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; padding-top: 2px; }
        .mem-cat .swatch { width: 6px; height: 6px; border-radius: 50%; flex: none; }
        .mem-content { font-size: 13px; color: var(--ink-0); line-height: 1.5; }
        .mem-meta { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); display: flex; flex-direction: column; gap: 3px; }
        .mem-imp { display: flex; align-items: center; gap: 4px; font-family: var(--font-mono); font-size: 11px; color: var(--ink-2); }
        .mem-bar { width: 50px; height: 4px; background: var(--bg-3); border-radius: 2px; overflow: hidden; }
        .mem-bar-fill { height: 100%; background: var(--accent); }
        .mem-core-flag { color: var(--accent); font-size: 10px; }
        .gf-card { padding: 12px 14px; border-bottom: 1px solid var(--line); display: flex; flex-direction: column; gap: 6px; }
        .gf-card:last-child { border-bottom: 0; }
        .gf-card:hover { background: var(--bg-2); }
        .gf-key { font-family: var(--font-mono); font-size: 11px; color: var(--accent); }
        .gf-val { font-size: 13px; color: var(--ink-0); }
        .gf-meta { display: flex; align-items: center; gap: 10px; font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); }
        .gf-score { display: flex; align-items: center; gap: 6px; }
        .gf-score-bar { width: 60px; height: 3px; background: var(--bg-3); border-radius: 2px; overflow: hidden; }
        .gf-score-bar-fill { height: 100%; background: linear-gradient(to right, var(--accent), var(--accent-2)); }
        .diff-row { display: grid; grid-template-columns: 70px 90px 1fr; gap: 12px; padding: 8px 16px; border-bottom: 1px solid var(--line); align-items: start; font-size: 12px; }
        .diff-row:last-child { border-bottom: 0; }
        .diff-ts { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); padding-top: 2px; }
        .diff-kind { font-family: var(--font-mono); font-size: 10px; padding: 2px 6px; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.05em; width: max-content; height: max-content; }
        .diff-kind.new { color: oklch(0.78 0.18 150); background: oklch(0.78 0.18 150 / 0.12); }
        .diff-kind.upd { color: var(--accent); background: var(--accent-soft); }
        .diff-kind.cls { color: var(--ink-2); background: var(--bg-3); }
        .diff-kind.crit { color: var(--critical); background: oklch(0.72 0.20 22 / 0.12); }
        .diff-kind.prn { color: var(--ink-3); background: var(--bg-3); text-decoration: line-through; }
        .diff-kind.prm { color: var(--accent-2); background: oklch(0.85 0.14 calc(var(--accent-h) + 30) / 0.12); }
        .diff-msg { font-size: 12px; color: var(--ink-1); }
        .diff-msg .id { font-family: var(--font-mono); color: var(--ink-3); }
        .diff-msg .arrow { color: var(--ink-3); margin: 0 4px; }
        .diff-msg .new-val { color: var(--ink-0); }
        .timeline-svg { width: 100%; height: 120px; display: block; }
        .heat-grid { display: grid; grid-template-columns: 80px repeat(5, 1fr); gap: 2px; padding: 8px; }
        .heat-h { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); text-transform: uppercase; padding: 4px; }
        .heat-cell { aspect-ratio: 2.4; display: flex; align-items: center; justify-content: center; font-family: var(--font-mono); font-size: 10px; border-radius: 3px; cursor: pointer; transition: transform 0.1s; }
        .heat-cell:hover { transform: scale(1.05); outline: 1px solid var(--accent); }
        .heat-row-label { font-family: var(--font-mono); font-size: 10px; color: var(--ink-1); display: flex; align-items: center; gap: 6px; padding: 4px; }
      `}</style>

      <div className="dash-h">
        <div>
          <h1>Dashboard</h1>
          <div className="dash-sub">workspace {window.__CRAFT_CONFIG?.workspaceId || "ws_???"} · server up {STATS.uptime ? formatRelTime(STATS.uptime) : "just now"}</div>
        </div>
        <div className="row gap-12">
          <button className="btn ghost" onClick={() => onNavigate("diff")}><Icon name="diff" /> Memory diff</button>
          <button className="btn primary" onClick={() => onNavigate("handoff")}><Icon name="handoff" /> Generate handoff</button>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card accent">
          <div className="delta">+7</div>
          <div className="v">{STATS.memoriesTotal.toLocaleString()}</div>
          <div className="l">Memories</div>
        </div>
        <div className="stat-card">
          <div className="v">{STATS.memoriesCore}</div>
          <div className="l">Core (immune)</div>
        </div>
        <div className="stat-card">
          <div className="delta">+3</div>
          <div className="v">{STATS.factsTotal}</div>
          <div className="l">Stable facts</div>
        </div>
        <div className="stat-card crit">
          <div className="v">{STATS.loopsOpen}</div>
          <div className="l">Open loops · {STATS.loopsCritical} crit</div>
        </div>
        <div className="stat-card">
          <div className="v">{STATS.proceduresTotal}</div>
          <div className="l">Procedures</div>
        </div>
        <div className="stat-card">
          <div className="v">{STATS.edgesTotal}</div>
          <div className="l">Graph edges</div>
        </div>
      </div>

      <div className="dash-row">
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">Recent memory <span className="dim">/ ranked by importance × decay</span></div>
            <div className="row gap-12 grow" style={{ justifyContent: "flex-end" }}>
              <button className="btn ghost" onClick={() => onNavigate("explorer")}>View all <Icon name="chevron" /></button>
            </div>
          </div>
          <div className="panel-body flush">
            {recent.map(m => (
              <div className="mem-row" key={m.id} onClick={() => onNavigate("explorer")}>
                <div className="mem-id">#{m.id}</div>
                <div className="mem-cat" style={{ color: catColor(m.category) }}>
                  <span className="swatch" style={{ background: catColor(m.category) }} />
                  {m.category}
                </div>
                <div>
                  <div className="mem-content">{m.content}</div>
                  <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                    {m.tags.map(t => <span key={t} className="chip muted">#{t}</span>)}
                    {m.isCore && <span className="chip accent"><Icon name="core" size={10} /> core</span>}
                  </div>
                </div>
                <div className="mem-meta">
                  <span>{m.scope}</span>
                  <span>{formatRelTime(m.ts)}</span>
                </div>
                <div className="mem-imp">
                  <div className="mem-bar"><div className="mem-bar-fill" style={{ width: (m.importance * 100) + "%" }} /></div>
                  <span>{m.importance.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">God facts <span className="dim">/ top by score</span></div>
          </div>
          <div className="panel-body flush">
            {godFacts.map(f => (
              <div className="gf-card" key={f.key}>
                <div className="gf-key">{f.key}</div>
                <div className="gf-val">{f.value}</div>
                <div className="gf-meta">
                  <span>{f.scope}</span>
                  <span>·</span>
                  <span>{f.mentions} mentions</span>
                  <span>·</span>
                  <span>{f.type}</span>
                  <div className="gf-score" style={{ marginLeft: "auto" }}>
                    <div className="gf-score-bar"><div className="gf-score-bar-fill" style={{ width: (f.godScore * 100) + "%" }} /></div>
                    <span>{f.godScore.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="dash-row-2">
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">Importance × age timeline <span className="dim">/ 30d, λ=0.005</span></div>
          </div>
          <div className="panel-body">
            <TimelineChart />
          </div>
        </div>
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">Heatmap <span className="dim">/ category × scope</span></div>
          </div>
          <div className="panel-body" style={{ padding: 0 }}>
            <HeatmapView />
          </div>
        </div>
      </div>

      <div className="dash-row-2">
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title"><Icon name="search" /> Wiki health check <span className="dim">/* lint_wiki() */</span></div>
            <button className="btn ghost" onClick={runLint} disabled={linting}>
              {linting ? "Scanning…" : "Run check"}
            </button>
          </div>
          <div className="panel-body" style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-1)", maxHeight: 300, overflowY: "auto" }}>
            {lintResult === null && !linting && <div style={{ padding: 8, color: "var(--ink-3)" }}>Press "Run check" to scan the knowledge base for contradictions, orphans, pending reviews, low-confidence facts, and inconsistencies.</div>}
            {linting && <div style={{ padding: 8, color: "var(--ink-3)" }}>Scanning {STATS.memoriesTotal} memories and {STATS.factsTotal} facts…</div>}
            {lintResult && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div className="stat-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
                  <FindingsCard label="Contradictions" count={lintResult.contradictions.length} color={lintResult.contradictions.length > 0 ? "var(--critical)" : "oklch(0.78 0.18 150)"} />
                  <FindingsCard label="Orphans" count={lintResult.orphans.length} color={lintResult.orphans.length > 0 ? "var(--accent)" : "oklch(0.78 0.18 150)"} />
                  <FindingsCard label="Pending review" count={lintResult.pending_reviews.length} color={lintResult.pending_reviews.length > 0 ? "var(--critical)" : "oklch(0.78 0.18 150)"} />
                </div>
                <div className="stat-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
                  <FindingsCard label="Low conf facts" count={lintResult.low_confidence_facts.length} />
                  <FindingsCard label="High imp unlinked" count={lintResult.unlinked_high_importance.length} color={lintResult.unlinked_high_importance.length > 0 ? "var(--accent)" : "oklch(0.78 0.18 150)"} />
                  <FindingsCard label="Inconsistencies" count={lintResult.inconsistencies.length} color={lintResult.inconsistencies.length > 0 ? "var(--critical)" : "oklch(0.78 0.18 150)"} />
                </div>
                {lintResult.contradictions.length > 0 && (
                  <div>
                    <div style={{ color: "var(--critical)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Contradictions</div>
                    {lintResult.contradictions.slice(0, 5).map((c, i) => (
                      <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid var(--line)", fontSize: 10, lineHeight: 1.4 }}>
                        <span style={{ color: "var(--ink-2)" }}>{c.prefix}:</span> {c.values.join(" vs ")}
                      </div>
                    ))}
                  </div>
                )}
                {lintResult.orphans.length > 0 && (
                  <div style={{ fontFamily: "var(--font-ui)", fontSize: 12, color: "var(--ink-2)" }}>
                    {lintResult.orphans.length} memories have no graph edges — use <span style={{ fontFamily: "var(--font-mono)", color: "var(--accent)" }}>find_similar(auto_link=True)</span> to connect them.
                  </div>
                )}
                <div style={{ color: "var(--ink-3)", fontSize: 10, borderTop: "1px solid var(--line)", paddingTop: 6 }}>
                  {lintResult.summary}
                </div>
              </div>
            )}
            {lintError && <div style={{ color: "var(--critical)", padding: 8, fontFamily: "var(--font-mono)", fontSize: 10 }}>Error: {lintError}</div>}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div className="panel-title"><Icon name="export" /> Export wiki <span className="dim">/* export_wiki() */</span></div>
          </div>
          <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)" }}>
              Generate an Obsidian-compatible markdown wiki from all memories. Each memory becomes a .md file with YAML frontmatter and [[wikilink]] neighbors.
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input ref={exportPathRef}
                defaultValue={exportPath}
                style={{ flex: 1, background: "var(--bg-1)", border: "1px solid var(--line-2)", borderRadius: "var(--radius-sm)", padding: "7px 10px", color: "var(--ink-0)", fontFamily: "var(--font-mono)", fontSize: 11, outline: "none" }}
                placeholder="/path/to/wiki"
              />
              <button className="btn primary" onClick={runExport} disabled={exporting}>
                {exporting ? "Exporting…" : "Export"}
              </button>
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)" }}>
              Min importance: {exportMinImp}
              <input type="range" min="1" max="10" value={exportMinImp}
                onChange={(e) => setExportMinImp(Number(e.target.value))}
                style={{ marginLeft: 6, verticalAlign: "middle", width: 60 }} />
            </div>
            {exportResult && (
              <div style={{ background: "var(--bg-1)", borderRadius: "var(--radius-sm)", padding: 10, fontFamily: "var(--font-mono)", fontSize: 10, lineHeight: 1.5 }}>
                <div style={{ color: "oklch(0.78 0.18 150)" }}>✓ {exportResult.page_count} pages · {exportResult.edge_count} edges</div>
                <div style={{ color: "var(--ink-2)" }}>Output: {exportResult.output_dir}</div>
                <div style={{ color: "var(--ink-3)", marginTop: 4 }}>Files: {exportResult.files.join(", ")}</div>
              </div>
            )}
            {exportError && <div style={{ color: "var(--critical)", fontFamily: "var(--font-mono)", fontSize: 10 }}>Error: {exportError}</div>}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div className="panel-title">Memory diff <span className="dim">/ since 4h ago · live stream</span></div>
          <div className="row gap-12 grow" style={{ justifyContent: "flex-end" }}>
            <span className="chip"><span className="chip-dot" style={{ background: "oklch(0.78 0.18 150)" }} /> live</span>
            <button className="btn ghost" onClick={() => onNavigate("diff")}>Open diff <Icon name="chevron" /></button>
          </div>
        </div>
        <div className="panel-body flush" style={{ maxHeight: 280, overflowY: "auto" }}>
          {diffEvents.length > 0
            ? diffEvents.map((e, i) => <DiffRow key={i} e={e} />)
            : <div style={{ padding: "24px 16px", textAlign: "center", fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-3)" }}>No diff events in the last 4h</div>
          }
        </div>
      </div>
    </div>
  );
};

const DiffRow = ({ e }) => {
  const { formatRelTime } = window.CRAFT;
  const kindMap = {
    "memory.new": { cls: "new", label: "MEM.NEW" },
    "memory.promoted": { cls: "prm", label: "PROMOTED" },
    "loop.opened": { cls: "crit", label: "LOOP.OPEN" },
    "loop.closed": { cls: "cls", label: "LOOP.CLOSE" },
    "fact.new": { cls: "new", label: "FACT.NEW" },
    "fact.updated": { cls: "upd", label: "FACT.UPD" },
    "edge.created": { cls: "new", label: "EDGE.NEW" },
    "edge.pruned": { cls: "prn", label: "EDGE.PRN" },
  };
  const k = kindMap[e.kind] || { cls: "new", label: e.kind };
  return (
    <div className="diff-row">
      <div className="diff-ts">{formatRelTime(e.ts)}</div>
      <div className={"diff-kind " + k.cls}>{k.label}</div>
      <div className="diff-msg">
        {e.kind === "memory.new" && <><span className="id">#{e.id}</span> · {e.summary}</>}
        {e.kind === "memory.promoted" && <><span className="id">#{e.id}</span> · {e.note}</>}
        {e.kind === "loop.opened" && <><span className="id">#{e.id}</span> · {e.summary} <span className="chip crit" style={{ marginLeft: 8, color: "var(--critical)", borderColor: "oklch(0.72 0.20 22 / 0.4)" }}>{e.priority}</span></>}
        {e.kind === "loop.closed" && <><span className="id">#{e.id}</span> · resolved: {e.resolution}</>}
        {e.kind === "fact.new" && <><span className="id">{e.key}</span> = <span className="new-val">{e.value}</span></>}
        {e.kind === "fact.updated" && <><span className="id">{e.key}</span> · <span className="dim">{e.oldValue}</span> <span className="arrow">→</span> <span className="new-val">{e.newValue}</span></>}
        {e.kind === "edge.created" && <><span className="id">#{e.source}</span> <span className="arrow">─{e.relation}→</span> <span className="id">#{e.target}</span></>}
        {e.kind === "edge.pruned" && <><span className="id">#{e.source}─#{e.target}</span> · {e.reason}</>}
      </div>
    </div>
  );
};

const TimelineChart = () => {
  const memories = window.CRAFT.MEMORIES || [];
  const DAYS = 30;
  const now = Date.now();
  const day = 86400000;
  const buckets = Array.from({ length: DAYS }, (_, i) => {
    const start = now - (DAYS - 1 - i) * day;
    const end = start + day;
    const count = memories.filter(m => m.ts >= start && m.ts < end).length;
    const decay = 0.3 + (i / (DAYS - 1)) * 0.7;
    return { count, decay };
  });
  const max = Math.max(...buckets.map(t => t.count), 1);
  const W = 700, H = 120, P = 8;
  const bw = (W - P * 2) / DAYS;

  if (memories.length === 0) {
    return (
      <div style={{ height: H, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--font-mono)" }}>
        No memories yet
      </div>
    );
  }

  return (
    <svg className="timeline-svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="tl-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--accent)" stopOpacity="0.7" />
          <stop offset="1" stopColor="var(--accent)" stopOpacity="0.05" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map(p => (
        <line key={p} x1={P} x2={W - P} y1={H * p} y2={H * p} stroke="var(--line)" strokeWidth="1" strokeDasharray="2 4" />
      ))}
      {buckets.map((t, i) => {
        const h = (t.count / max) * (H - P * 2 - 16);
        const x = P + i * bw;
        return (
          <g key={i}>
            <rect x={x + 1} y={H - P - h} width={bw - 2} height={h} fill="url(#tl-grad)" opacity={0.4 + t.decay * 0.6} />
            {h > 0 && <rect x={x + 1} y={H - P - h} width={bw - 2} height={1.2} fill="var(--accent)" opacity={t.decay} />}
          </g>
        );
      })}
      <text x={P + 4} y={14} fontSize="9" fill="var(--ink-3)" fontFamily="var(--font-mono)">29d ago</text>
      <text x={W - P - 30} y={14} fontSize="9" fill="var(--ink-3)" fontFamily="var(--font-mono)">today</text>
    </svg>
  );
};

const HeatmapView = () => {
  const { CATEGORIES, SCOPES } = window.CRAFT;
  const memories = window.CRAFT.MEMORIES || [];
  // Compute heatmap from real memories
  const HEATMAP = {};
  CATEGORIES.forEach(c => {
    HEATMAP[c.id] = {};
    SCOPES.forEach(s => {
      HEATMAP[c.id][s] = memories.filter(m => m.category === c.id && m.scope === s).length;
    });
  });
  const allVals = CATEGORIES.flatMap(c => SCOPES.map(s => HEATMAP[c.id][s]));
  const max = Math.max(...allVals, 1);
  return (
    <div className="heat-grid">
      <div className="heat-h" />
      {SCOPES.map(s => <div className="heat-h" key={s}>{s}</div>)}
      {CATEGORIES.map(c => (
        <React.Fragment key={c.id}>
          <div className="heat-row-label"><span style={{ width: 6, height: 6, borderRadius: "50%", background: c.color }} /> {c.label}</div>
          {SCOPES.map(s => {
            const v = HEATMAP[c.id][s];
            const t = v / max;
            return (
              <div className="heat-cell" key={s}
                style={{ background: `oklch(0.78 ${0.02 + t*0.18} var(--accent-h) / ${0.06 + t*0.6})`, color: t > 0.5 ? "var(--bg-0)" : "var(--ink-1)" }}
                title={`${c.label} × ${s}: ${v}`}>
                {v}
              </div>
            );
          })}
        </React.Fragment>
      ))}
    </div>
  );
};

// ─── Mini findings card for lint report ────────────────────────────────
const FindingsCard = ({ label, count, color }) => (
  <div style={{ padding: "8px 10px", background: "var(--bg-2)", borderRadius: "var(--radius-sm)", display: "flex", flexDirection: "column", gap: 2 }}>
    <span style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 500, color: color || "var(--ink-0)" }}>{count}</span>
    <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</span>
  </div>
);

window.DashboardScreen = DashboardScreen;
