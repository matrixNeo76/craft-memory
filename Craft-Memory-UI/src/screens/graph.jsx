// Knowledge Graph viewer — force-directed layout, interactive
const GraphScreen = ({ onNavigate, focusId }) => {
  const { MEMORIES, RELATIONS, CATEGORIES } = window.CRAFT;
  const [selected, setSelected] = React.useState(focusId || 1247);
  const [hovered, setHovered] = React.useState(null);
  const [activeRoles, setActiveRoles] = React.useState(new Set(["core", "context", "detail", "temporal", "causal"]));

  const catColor = (id) => CATEGORIES.find(c => c.id === id)?.color || "var(--ink-2)";

  // Simple deterministic layout — circular by category
  const W = 800, H = 540;
  const cx = W/2, cy = H/2;
  const positions = React.useMemo(() => {
    const pos = {};
    const sortedMems = [...MEMORIES].sort((a, b) => a.id - b.id);
    sortedMems.forEach((m, i) => {
      const ring = m.isCore ? 0 : (m.importance > 0.75 ? 1 : 2);
      const ringR = [0, 130, 230][ring];
      const inRing = sortedMems.filter(x => {
        const r = x.isCore ? 0 : (x.importance > 0.75 ? 1 : 2);
        return r === ring;
      });
      const idx = inRing.indexOf(m);
      const a = (idx / inRing.length) * Math.PI * 2 + ring * 0.3;
      pos[m.id] = { x: cx + Math.cos(a) * ringR, y: cy + Math.sin(a) * ringR, ring };
    });
    return pos;
  }, []);

  const visibleEdges = RELATIONS.filter(r => activeRoles.has(r.role));
  const neighborIds = new Set();
  visibleEdges.forEach(r => {
    if (r.source === selected) neighborIds.add(r.target);
    if (r.target === selected) neighborIds.add(r.source);
  });

  const selectedMem = MEMORIES.find(m => m.id === selected);
  const incident = visibleEdges.filter(r => r.source === selected || r.target === selected);

  const toggleRole = (r) => {
    const next = new Set(activeRoles);
    next.has(r) ? next.delete(r) : next.add(r);
    setActiveRoles(next);
  };

  const ROLES = [
    { id: "core",     color: "oklch(0.78 0.18 var(--accent-h))" },
    { id: "context",  color: "oklch(0.82 0.14 175)" },
    { id: "detail",   color: "oklch(0.7 0.04 var(--accent-h))" },
    { id: "temporal", color: "oklch(0.78 0.16 55)" },
    { id: "causal",   color: "oklch(0.72 0.20 22)" },
  ];

  return (
    <div className="grph">
      <style>{`
        .grph { display: grid; grid-template-columns: 1fr 320px; gap: 16px; }
        .grph-h { grid-column: 1 / -1; display: flex; align-items: end; justify-content: space-between; }
        .grph-h h1 { margin: 0; font-size: 24px; font-weight: 500; }
        .grph-h .sub { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); margin-top: 2px; }
        .grph-canvas { position: relative; background:
          radial-gradient(circle at 50% 50%, oklch(0.78 0.18 var(--accent-h) / 0.06), transparent 60%),
          var(--bg-1);
          border: 1px solid var(--line);
          border-radius: var(--radius);
          overflow: hidden;
          min-height: 580px;
        }
        .grph-svg { width: 100%; height: 100%; display: block; }
        .grph-side { display: flex; flex-direction: column; gap: 12px; }
        .role-toggles { display: flex; gap: 6px; flex-wrap: wrap; padding: 12px; }
        .role-toggle { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--line); cursor: pointer; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-2); }
        .role-toggle.on { color: var(--ink-0); border-color: var(--line-2); background: var(--bg-2); }
        .role-toggle .swatch { width: 8px; height: 2px; }
        .grph-legend { position: absolute; bottom: 12px; left: 12px; background: var(--bg-2); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 8px 10px; font-family: var(--font-mono); font-size: 10px; color: var(--ink-2); display: flex; flex-direction: column; gap: 4px; }
        .grph-legend .lr { display: flex; align-items: center; gap: 6px; }
        .grph-zoom { position: absolute; top: 12px; right: 12px; display: flex; gap: 4px; }
        .node-info-line { padding: 8px 14px; font-family: var(--font-mono); font-size: 11px; display: flex; justify-content: space-between; border-bottom: 1px solid var(--line); }
        .node-info-line .k { color: var(--ink-3); }
        .node-info-line .v { color: var(--ink-0); }
        .edge-row { padding: 8px 14px; border-bottom: 1px solid var(--line); cursor: pointer; }
        .edge-row:hover { background: var(--bg-2); }
        .edge-row .top { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10px; }
        .edge-row .arrow { color: var(--accent); }
        .edge-row .desc { font-size: 12px; color: var(--ink-1); margin-top: 4px; }
        .grph-content-card { padding: 14px; font-size: 13px; color: var(--ink-0); line-height: 1.5; border-bottom: 1px solid var(--line); }
        @keyframes pulse-r { 0%, 100% { r: 11; opacity: 1; } 50% { r: 14; opacity: 0.6; } }
      `}</style>

      <div className="grph-h">
        <div>
          <h1>Knowledge Graph</h1>
          <div className="sub">{MEMORIES.length} nodes · {RELATIONS.length} edges · roles: core, context, detail, temporal, causal</div>
        </div>
        <div className="row gap-12">
          <button className="btn ghost"><Icon name="link" /> link_memories()</button>
          <button className="btn ghost"><Icon name="spark" /> find_similar()</button>
        </div>
      </div>

      <div className="grph-canvas">
        <svg className="grph-svg" viewBox={`0 0 ${W} ${H}`}>
          <defs>
            <radialGradient id="ring-glow" cx="50%" cy="50%">
              <stop offset="0" stopColor="var(--accent)" stopOpacity="0" />
              <stop offset="0.7" stopColor="var(--accent)" stopOpacity="0" />
              <stop offset="1" stopColor="var(--accent)" stopOpacity="0.18" />
            </radialGradient>
            {ROLES.map(r => (
              <marker key={r.id} id={`arrow-${r.id}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill={r.color} />
              </marker>
            ))}
          </defs>

          {/* concentric ring guides */}
          {[130, 230].map(r => (
            <circle key={r} cx={cx} cy={cy} r={r} fill="none" stroke="var(--line)" strokeWidth="1" strokeDasharray="2 6" />
          ))}
          <circle cx={cx} cy={cy} r="40" fill="none" stroke="var(--accent-soft)" strokeWidth="1" />

          {/* edges */}
          {visibleEdges.map((r, i) => {
            const s = positions[r.source], t = positions[r.target];
            if (!s || !t) return null;
            const role = ROLES.find(x => x.id === r.role);
            const isIncident = r.source === selected || r.target === selected;
            const dim = !isIncident && (selected !== null);
            return (
              <line key={i}
                x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                stroke={role.color}
                strokeWidth={1 + r.weight * 1.5}
                opacity={dim ? 0.12 : (0.3 + r.weight * 0.5)}
                strokeDasharray={r.confidence === "ambiguous" ? "3 3" : (r.confidence === "inferred" ? "5 2" : "0")}
                markerEnd={`url(#arrow-${r.id})`}
              />
            );
          })}

          {/* nodes */}
          {MEMORIES.map(m => {
            const p = positions[m.id];
            if (!p) return null;
            const isSelected = m.id === selected;
            const isNeighbor = neighborIds.has(m.id);
            const dim = selected !== null && !isSelected && !isNeighbor;
            const r = m.isCore ? 9 : 6 + m.importance * 3;
            return (
              <g key={m.id}
                style={{ cursor: "pointer", opacity: dim ? 0.25 : 1, transition: "opacity 0.15s" }}
                onClick={() => setSelected(m.id)}
                onMouseEnter={() => setHovered(m.id)}
                onMouseLeave={() => setHovered(null)}>
                {isSelected && <circle cx={p.x} cy={p.y} r={r + 6} fill="none" stroke={catColor(m.category)} strokeWidth="1" opacity="0.5" style={{ animation: "pulse-r 2s ease-in-out infinite" }} />}
                {m.isCore && <circle cx={p.x} cy={p.y} r={r + 3} fill="none" stroke="var(--accent)" strokeWidth="1" strokeDasharray="2 2" opacity="0.6" />}
                <circle cx={p.x} cy={p.y} r={r}
                  fill={catColor(m.category)}
                  stroke={isSelected ? "var(--ink-0)" : (hovered === m.id ? "var(--accent)" : "transparent")}
                  strokeWidth="1.4" />
                {(isSelected || hovered === m.id || isNeighbor) && (
                  <text x={p.x} y={p.y - r - 6} textAnchor="middle"
                    fontFamily="var(--font-mono)" fontSize="9" fill="var(--ink-1)">
                    #{m.id}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        <div className="grph-legend">
          <div className="lr"><span style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--accent)" }} /> core (immune to decay)</div>
          <div className="lr"><span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--ink-2)" }} /> ring 1 · importance &gt; 0.75</div>
          <div className="lr"><span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ink-3)" }} /> ring 2 · others</div>
          <div className="lr"><span style={{ width: 14, height: 1.5, background: "var(--ink-2)" }} /> solid: extracted</div>
          <div className="lr"><span style={{ width: 14, height: 1.5, background: "var(--ink-2)", borderTop: "1px dashed var(--ink-2)" }} /> dashed: inferred / ambiguous</div>
        </div>
      </div>

      <div className="grph-side">
        <div className="panel">
          <div className="panel-head"><div className="panel-title">Edge roles</div></div>
          <div className="role-toggles">
            {ROLES.map(r => {
              const on = activeRoles.has(r.id);
              return (
                <span key={r.id} className={"role-toggle" + (on ? " on" : "")} onClick={() => toggleRole(r.id)}>
                  <span className="swatch" style={{ background: r.color, height: 2, width: 12, display: "inline-block" }} />
                  {r.id}
                </span>
              );
            })}
          </div>
        </div>

        {selectedMem && (
          <div className="panel">
            <div className="panel-head">
              <div className="panel-title">Selected · #{selectedMem.id}</div>
              <button className="btn ghost" style={{ marginLeft: "auto" }} onClick={() => onNavigate("explorer")}><Icon name="external" size={11} /></button>
            </div>
            <div className="grph-content-card">{selectedMem.content}</div>
            <div className="node-info-line"><span className="k">category</span><span className="v" style={{ color: catColor(selectedMem.category) }}>{selectedMem.category}</span></div>
            <div className="node-info-line"><span className="k">scope</span><span className="v">{selectedMem.scope}</span></div>
            <div className="node-info-line"><span className="k">importance</span><span className="v">{selectedMem.importance.toFixed(2)}</span></div>
            <div className="node-info-line"><span className="k">is_core</span><span className="v">{selectedMem.isCore ? "true" : "false"}</span></div>
            <div className="node-info-line"><span className="k">confidence</span><span className="v">{selectedMem.confidence}</span></div>
          </div>
        )}

        <div className="panel">
          <div className="panel-head"><div className="panel-title">Edges · {incident.length}</div></div>
          <div>
            {incident.map((r, i) => {
              const role = ROLES.find(x => x.id === r.role);
              const otherId = r.source === selected ? r.target : r.source;
              const dir = r.source === selected ? "→" : "←";
              return (
                <div key={i} className="edge-row" onClick={() => setSelected(otherId)}>
                  <div className="top">
                    <span style={{ color: role.color }}>{r.role}</span>
                    <span className="dim">·</span>
                    <span>#{selected}</span>
                    <span className="arrow" style={{ color: role.color }}>─{r.relation}{dir}</span>
                    <span>#{otherId}</span>
                  </div>
                  <div className="desc">w={r.weight.toFixed(2)} · {r.confidence}</div>
                </div>
              );
            })}
            {incident.length === 0 && <div style={{ padding: 16, fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-3)" }}>no edges visible · adjust role filters</div>}
          </div>
        </div>
      </div>
    </div>
  );
};

window.GraphScreen = GraphScreen;
