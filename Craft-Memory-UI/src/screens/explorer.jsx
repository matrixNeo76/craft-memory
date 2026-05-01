// Memory Explorer — search FTS5-style + filters + result list
const ExplorerScreen = ({ onNavigate }) => {
  const { MEMORIES, CATEGORIES, SCOPES, formatRelTime } = window.CRAFT;
  const [query, setQuery] = React.useState("");
  const [activeCats, setActiveCats] = React.useState(new Set());
  const [activeScope, setActiveScope] = React.useState("all");
  const [coreOnly, setCoreOnly] = React.useState(false);
  const [sortBy, setSortBy] = React.useState("rrf");

  const catColor = (id) => CATEGORIES.find(c => c.id === id)?.color || "var(--ink-2)";

  const filtered = React.useMemo(() => {
    let out = MEMORIES.filter(m => {
      if (activeCats.size > 0 && !activeCats.has(m.category)) return false;
      if (activeScope !== "all" && m.scope !== activeScope) return false;
      if (coreOnly && !m.isCore) return false;
      if (query.trim()) {
        const q = query.toLowerCase();
        const hay = (m.content + " " + m.tags.join(" ")).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    if (sortBy === "importance") out = [...out].sort((a, b) => b.importance - a.importance);
    else if (sortBy === "recent") out = [...out].sort((a, b) => b.ts - a.ts);
    return out;
  }, [query, activeCats, activeScope, coreOnly, sortBy]);

  const highlight = (text, q) => {
    if (!q.trim()) return text;
    const re = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
    const parts = text.split(re);
    return parts.map((p, i) => re.test(p) ? <mark key={i}>{p}</mark> : <span key={i}>{p}</span>);
  };

  const toggleCat = (id) => {
    const next = new Set(activeCats);
    next.has(id) ? next.delete(id) : next.add(id);
    setActiveCats(next);
  };

  return (
    <div className="exp">
      <style>{`
        .exp { display: grid; grid-template-columns: 240px 1fr; gap: 16px; }
        .exp-h { grid-column: 1 / -1; display: flex; align-items: end; justify-content: space-between; }
        .exp-h h1 { margin: 0; font-size: 24px; font-weight: 500; }
        .exp-h .sub { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); margin-top: 2px; }
        .exp-search { grid-column: 1 / -1; display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: var(--bg-1); border: 1px solid var(--line-2); border-radius: var(--radius); font-family: var(--font-mono); font-size: 13px; box-shadow: 0 0 0 3px transparent; transition: box-shadow 0.15s, border-color 0.15s; }
        .exp-search:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
        .exp-search input { flex: 1; background: transparent; border: 0; outline: 0; font: inherit; color: var(--ink-0); }
        .exp-search .syntax { color: var(--accent); margin-right: 4px; }
        .exp-search .clear { color: var(--ink-3); cursor: pointer; padding: 2px; }
        .exp-search .clear:hover { color: var(--ink-1); }
        .exp-side { display: flex; flex-direction: column; gap: 16px; }
        .filter-block { background: var(--bg-1); border: 1px solid var(--line); border-radius: var(--radius); }
        .filter-h { padding: 10px 14px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-3); border-bottom: 1px solid var(--line); }
        .filter-body { padding: 8px; display: flex; flex-direction: column; gap: 2px; }
        .filter-item { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: var(--radius-sm); cursor: pointer; font-size: 12px; color: var(--ink-1); }
        .filter-item:hover { background: var(--bg-2); }
        .filter-item.on { background: var(--accent-soft); color: var(--ink-0); }
        .filter-item .swatch { width: 8px; height: 8px; border-radius: 2px; flex: none; }
        .filter-item .count { margin-left: auto; font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); }
        .filter-item.on .count { color: var(--accent); }
        .toggle-line { display: flex; align-items: center; justify-content: space-between; padding: 8px 14px; font-size: 12px; color: var(--ink-1); cursor: pointer; }
        .toggle-line:hover { background: var(--bg-2); }
        .switch { width: 28px; height: 16px; border-radius: 8px; background: var(--bg-3); position: relative; flex: none; transition: background 0.15s; }
        .switch.on { background: var(--accent); }
        .switch::after { content: ""; position: absolute; top: 2px; left: 2px; width: 12px; height: 12px; border-radius: 50%; background: var(--ink-0); transition: transform 0.15s; }
        .switch.on::after { transform: translateX(12px); }
        .results-h { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-bottom: 1px solid var(--line); font-family: var(--font-mono); font-size: 11px; color: var(--ink-2); }
        .results-h .count-big { color: var(--ink-0); font-size: 13px; }
        .sort-pills { display: flex; gap: 4px; margin-left: auto; }
        .sort-pill { padding: 3px 8px; font-family: var(--font-mono); font-size: 10px; border-radius: 999px; cursor: pointer; color: var(--ink-2); border: 1px solid transparent; }
        .sort-pill:hover { color: var(--ink-0); }
        .sort-pill.on { color: var(--accent); border-color: var(--accent-soft); background: var(--accent-soft); }
        .res-card { padding: 14px 16px; border-bottom: 1px solid var(--line); cursor: pointer; }
        .res-card:hover { background: var(--bg-2); }
        .res-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
        .res-id { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); }
        .res-cat { font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; padding: 2px 7px; border-radius: 3px; }
        .res-meta { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); margin-left: auto; display: flex; gap: 10px; align-items: center; }
        .res-content { font-size: 13.5px; color: var(--ink-0); line-height: 1.55; }
        .res-content mark { background: oklch(0.78 0.18 var(--accent-h) / 0.25); color: var(--ink-0); padding: 1px 2px; border-radius: 2px; }
        .res-tags { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
        .res-rank { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); }
        .res-rank .bar { width: 60px; height: 3px; background: var(--bg-3); border-radius: 2px; overflow: hidden; }
        .res-rank .bar > div { height: 100%; background: var(--accent); }
        .empty-state { padding: 60px 20px; text-align: center; color: var(--ink-3); font-family: var(--font-mono); font-size: 12px; }
      `}</style>

      <div className="exp-h">
        <div>
          <h1>Memory Explorer</h1>
          <div className="sub">RRF hybrid search · FTS5 BM25 + Jaccard fused via 1/(k+rank), k=60</div>
        </div>
      </div>

      <div className="exp-search" style={{ gridColumn: "1 / -1" }}>
        <Icon name="search" />
        <span className="syntax mono">search_memory(</span>
        <input
          placeholder='"transport" OR scope:project tag:fts5'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <span className="syntax mono">)</span>
        {query && <span className="clear" onClick={() => setQuery("")}><Icon name="x" size={12} /></span>}
        <kbd style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)", background: "var(--bg-3)", padding: "2px 5px", borderRadius: 3, border: "1px solid var(--line)" }}>↵</kbd>
      </div>

      <div className="exp-side">
        <div className="filter-block">
          <div className="filter-h">Category</div>
          <div className="filter-body">
            {CATEGORIES.map(c => {
              const count = MEMORIES.filter(m => m.category === c.id).length;
              const on = activeCats.has(c.id);
              return (
                <div key={c.id} className={"filter-item" + (on ? " on" : "")} onClick={() => toggleCat(c.id)}>
                  <span className="swatch" style={{ background: c.color }} />
                  <span>{c.label}</span>
                  <span className="count">{count}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="filter-block">
          <div className="filter-h">Scope</div>
          <div className="filter-body">
            {["all", ...SCOPES].map(s => {
              const on = activeScope === s;
              const count = s === "all" ? MEMORIES.length : MEMORIES.filter(m => m.scope === s).length;
              return (
                <div key={s} className={"filter-item" + (on ? " on" : "")} onClick={() => setActiveScope(s)}>
                  <span>{s}</span>
                  <span className="count">{count}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="filter-block">
          <div className="filter-h">Options</div>
          <div className="toggle-line" onClick={() => setCoreOnly(!coreOnly)}>
            <span>Core only <Icon name="core" size={11} /></span>
            <span className={"switch" + (coreOnly ? " on" : "")} />
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="results-h">
          <span className="count-big">{filtered.length}</span>
          <span>results</span>
          {query && <span>· matched <span className="mono" style={{ color: "var(--accent)" }}>"{query}"</span></span>}
          <div className="sort-pills">
            <span className={"sort-pill" + (sortBy === "rrf" ? " on" : "")} onClick={() => setSortBy("rrf")}>rrf rank</span>
            <span className={"sort-pill" + (sortBy === "importance" ? " on" : "")} onClick={() => setSortBy("importance")}>importance</span>
            <span className={"sort-pill" + (sortBy === "recent" ? " on" : "")} onClick={() => setSortBy("recent")}>recent</span>
          </div>
        </div>

        <div>
          {filtered.length === 0 && (
            <div className="empty-state">No results · try clearing filters or relaxing the query</div>
          )}
          {filtered.map((m, i) => (
            <div key={m.id} className="res-card" onClick={() => onNavigate("graph", { focusId: m.id })}>
              <div className="res-top">
                <span className="res-id">#{m.id}</span>
                <span className="res-cat" style={{ color: catColor(m.category), background: catColor(m.category) + "1f" }}>{m.category}</span>
                <span className="chip muted">{m.scope}</span>
                {m.isCore && <span className="chip accent"><Icon name="core" size={10} /> core</span>}
                <span className="chip muted">{m.confidence}</span>
                <div className="res-meta">
                  <span>rrf #{i+1}</span>
                  <span>·</span>
                  <span>{formatRelTime(m.ts)}</span>
                  <div className="res-rank">
                    <span>imp</span>
                    <div className="bar"><div style={{ width: (m.importance * 100) + "%" }} /></div>
                    <span>{m.importance.toFixed(2)}</span>
                  </div>
                </div>
              </div>
              <div className="res-content">{highlight(m.content, query)}</div>
              <div className="res-tags">
                {m.tags.map(t => <span key={t} className="chip muted"><Icon name="tag" size={9} /> {t}</span>)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

window.ExplorerScreen = ExplorerScreen;
