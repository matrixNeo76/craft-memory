// Memory Explorer — FTS5-backed hybrid search + filters + result list + graph preview
const ExplorerScreen = ({ onNavigate, action }) => {
  const { MEMORIES, CATEGORIES, SCOPES, formatRelTime } = window.CRAFT;

  const [query, setQuery]           = React.useState("");
  const [activeCats, setActiveCats] = React.useState(new Set());
  const [activeScope, setActiveScope] = React.useState("all");
  const [coreOnly, setCoreOnly]     = React.useState(false);
  const [sortBy, setSortBy]         = React.useState("rrf");

  // ─── Server-side search state ──────────────────────────────────────
  const [searchResults, setSearchResults] = React.useState(null);
  const [searching, setSearching]         = React.useState(false);
  const [searchError, setSearchError]     = React.useState(null);

  // ─── Graph relations (for edge counts and inline neighbors) ─────────
  const [relations, setRelations] = React.useState(window.CRAFT.RELATIONS || []);
  const [loadingRel, setLoadingRel] = React.useState(!window.CRAFT.RELATIONS_LOADED);

  // ─── Pagination + expandable neighbors + content truncation ─────────
  const [showCount, setShowCount]     = React.useState(50);
  const [expandedCards, setExpandedCards] = React.useState(new Set());
  const [showFullContent, setShowFullContent] = React.useState(new Set());

  // ─── "Remember" modal state ─────────────────────────────────────────
  const [showRemember, setShowRemember] = React.useState(false);

  const inputRef = React.useRef(null);

  // ─── ⌘K keyboard shortcut to focus search ──────────────────────────
  React.useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // ─── Load relations if not already cached by Graph screen ───────────
  React.useEffect(() => {
    if (window.CRAFT.RELATIONS_LOADED) { setRelations(window.CRAFT.RELATIONS); setLoadingRel(false); return; }
    CRAFT_API.relations(null, null)
      .then((r) => {
        const edges = Array.isArray(r) ? r : (r?.edges ?? []);
        setRelations(edges);
        window.CRAFT.RELATIONS = edges;
        window.CRAFT.RELATIONS_LOADED = true;
      })
      .catch(() => { window.CRAFT.RELATIONS_LOADED = true; })
      .finally(() => setLoadingRel(false));
  }, []);

  // ─── Precomputed edge data: O(1) lookups instead of O(N) filters ────
  const edgeCounts = React.useMemo(() => {
    const counts = {};
    for (const r of relations) {
      counts[r.source] = (counts[r.source] || 0) + 1;
      counts[r.target] = (counts[r.target] || 0) + 1;
    }
    return counts;
  }, [relations]);

  const neighborsMap = React.useMemo(() => {
    const map = {};
    for (const r of relations) {
      if (!map[r.source]) map[r.source] = [];
      if (!map[r.target]) map[r.target] = [];
      map[r.source].push(r);
      map[r.target].push(r);
    }
    return map;
  }, [relations]);

  function edgeCount(memId) { return edgeCounts[memId] || 0; }
  function neighborEdges(memId) { return neighborsMap[memId] || []; }

  function toggleExpanded(memId) {
    const next = new Set(expandedCards);
    next.has(memId) ? next.delete(memId) : next.add(memId);
    setExpandedCards(next);
  }

  function toggleFullContent(memId) {
    const next = new Set(showFullContent);
    next.has(memId) ? next.delete(memId) : next.add(memId);
    setShowFullContent(next);
  }

  // React to routeArgs.action from sidebar MCP tool clicks
  React.useEffect(() => {
    if (action === "search") {
      inputRef.current?.focus();
    } else if (action === "remember") {
      setShowRemember(true);
    }
  }, [action]);

  const filterActive = activeCats.size > 0 || activeScope !== "all" || coreOnly;

  function clearAllFilters() {
    setActiveCats(new Set());
    setActiveScope("all");
    setCoreOnly(false);
  }

  const catColor = (id) => CATEGORIES.find(c => c.id === id)?.color || "var(--ink-2)";

  // ─── Debounced FTS5 server search ──────────────────────────────────
  React.useEffect(() => {
    if (!query.trim()) {
      setSearchResults(null);
      setSearchError(null);
      return;
    }
    const timer = setTimeout(() => {
      setSearching(true);
      setSearchError(null);
      CRAFT_API.searchMemories(query.trim(), activeScope !== "all" ? activeScope : null, 100)
        .then((rows) => setSearchResults(rows))
        .catch((e) => {
          console.warn("[explorer] search failed:", e.message);
          setSearchError(e.message);
          setSearchResults(null);
        })
        .finally(() => setSearching(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [query, activeScope]);

  // ─── Computed lists (all memoized) ─────────────────────────────────
  const baseList = React.useMemo(
    () => query.trim() && searchResults !== null ? searchResults : MEMORIES,
    [query, searchResults, MEMORIES]
  );

  const catCounts = React.useMemo(() => {
    const counts = {};
    for (const m of baseList) counts[m.category] = (counts[m.category] || 0) + 1;
    return counts;
  }, [baseList]);

  const scopeCounts = React.useMemo(() => {
    const counts = { all: baseList.length };
    for (const m of baseList) counts[m.scope] = (counts[m.scope] || 0) + 1;
    return counts;
  }, [baseList]);

  const filtered = React.useMemo(() => {
    let out = baseList.filter(m => {
      if (activeCats.size > 0 && !activeCats.has(m.category)) return false;
      if (activeScope !== "all" && m.scope !== activeScope) return false;
      if (coreOnly && !m.isCore) return false;
      if (query.trim() && searchResults === null) {
        const q = query.toLowerCase();
        const hay = (m.content + " " + m.tags.join(" ")).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    if (sortBy === "importance") out = [...out].sort((a, b) => b.importance - a.importance);
    else if (sortBy === "recent") out = [...out].sort((a, b) => b.ts - a.ts);
    return out;
  }, [baseList, activeCats, activeScope, coreOnly, sortBy, query, searchResults]);

  const displayed = React.useMemo(() => filtered.slice(0, showCount), [filtered, showCount]);
  const hasMore = filtered.length > showCount;

  // Memoized highlight — single RegExp, reused across cards
  const highlight = React.useMemo(() => {
    if (!query.trim()) return (text) => text;
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp("(" + escaped + ")", "gi");
    return (text) => {
      const parts = text.split(re);
      return parts.map((p, i) => re.test(p) ? React.createElement("mark", { key: i }, p) : React.createElement("span", { key: i }, p));
    };
  }, [query]);

  const toggleCat = (id) => {
    const next = new Set(activeCats);
    next.has(id) ? next.delete(id) : next.add(id);
    setActiveCats(next);
  };

  const usingServerSearch = query.trim() && searchResults !== null;
  const totalDb = window.CRAFT.STATS?.memoriesTotal || MEMORIES.length;
  const MAX_CONTENT_PREVIEW = 280;

  // Early return: loading state before MEMORIES arrive
  if (MEMORIES.length === 0) {
    return (
      <div className="exp">
        <style>{`.exp { min-height: 400px; }`}</style>
        <div className="exp-h"><div><h1>Memory Explorer</h1></div></div>
        <div style={{ gridColumn: "1 / -1", padding: "80px 20px", textAlign: "center", color: "var(--ink-3)", fontFamily: "var(--font-mono)", fontSize: 12 }}>
          <div className="search-spinner" style={{ margin: "0 auto 12px" }} />
          Loading memories…
        </div>
      </div>
    );
  }

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
        .exp-search .search-spinner { width: 12px; height: 12px; border: 1.5px solid var(--accent-soft); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.7s linear infinite; flex-none; }
        @keyframes spin { to { transform: rotate(360deg); } }
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
        .res-card { padding: 14px 16px; border-bottom: 1px solid var(--line); cursor: default; }
        .res-card:hover { background: var(--bg-2); }
        .res-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
        .res-id { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); cursor: pointer; }
        .res-id:hover { color: var(--accent); }
        .res-cat { font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; padding: 2px 7px; border-radius: 3px; }
        .res-meta { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); margin-left: auto; display: flex; gap: 10px; align-items: center; }
        .res-content { font-size: 13.5px; color: var(--ink-0); line-height: 1.55; cursor: pointer; }
        .res-content:hover { color: var(--accent); }
        .res-content mark { background: oklch(0.78 0.18 var(--accent-h) / 0.25); color: var(--ink-0); padding: 1px 2px; border-radius: 2px; }
        .res-tags { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
        .res-rank { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); }
        .res-rank .bar { width: 60px; height: 3px; background: var(--bg-3); border-radius: 2px; overflow: hidden; }
        .res-rank .bar > div { height: 100%; background: var(--accent); }
        .empty-state { padding: 60px 20px; text-align: center; color: var(--ink-3); font-family: var(--font-mono); font-size: 12px; }
        .search-badge { padding: 2px 8px; border-radius: 999px; font-family: var(--font-mono); font-size: 10px; background: var(--accent-soft); color: var(--accent); border: 1px solid oklch(0.78 0.18 var(--accent-h) / 0.3); }
        .search-err { padding: 8px 14px; font-family: var(--font-mono); font-size: 11px; color: var(--critical); border-bottom: 1px solid var(--line); }
        .expand-link { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); cursor: pointer; display: inline-block; margin-top: 4px; }
        .expand-link:hover { color: var(--accent); }
        /* ── Graph edge badge / inline neighbors ── */
        .edge-badge { display: inline-flex; align-items: center; gap: 4px; font-family: var(--font-mono); font-size: 10px; color: var(--ink-2); cursor: pointer; padding: 2px 7px; border-radius: 3px; background: var(--bg-3); }
        .edge-badge:hover { background: var(--bg-2); color: var(--accent); }
        .edge-badge.on { background: var(--accent-soft); color: var(--accent); }
        .neighbor-list { margin-top: 6px; padding-left: 8px; border-left: 2px solid var(--line); font-size: 12px; display: flex; flex-direction: column; gap: 3px; }
        .neighbor-item { display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--ink-2); padding: 2px 4px; border-radius: 2px; }
        .neighbor-item:hover { background: var(--bg-3); color: var(--ink-0); }
        .neighbor-item .arrow { color: var(--accent); font-size: 10px; }
        /* ── Pagination load-more ── */
        .load-more { padding: 16px; text-align: center; }
        /* ── InsertMemoryModal ── */
        .imm-overlay { position: fixed; inset: 0; background: rgba(5,7,13,0.82); display: flex; align-items: center; justify-content: center; z-index: 2000; backdrop-filter: blur(4px); }
        .imm-box { background: var(--bg-2); border: 1px solid var(--line-2); border-radius: var(--radius); padding: 28px; width: 520px; display: flex; flex-direction: column; gap: 18px; box-shadow: var(--glow); }
        .imm-title { font-size: 14px; font-weight: 500; color: var(--ink-0); display: flex; align-items: center; justify-content: space-between; }
        .imm-title button { background: none; border: none; color: var(--ink-3); cursor: pointer; font-size: 22px; line-height: 1; padding: 2px; }
        .imm-field { display: flex; flex-direction: column; gap: 6px; }
        .imm-label { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.1em; }
        .imm-textarea { background: var(--bg-1); border: 1px solid var(--line-2); border-radius: var(--radius-sm); padding: 10px 12px; color: var(--ink-0); font: 13px/1.55 var(--font-ui); outline: none; resize: vertical; min-height: 100px; }
        .imm-textarea:focus { border-color: var(--accent); }
        .imm-select { background: var(--bg-1); border: 1px solid var(--line-2); border-radius: var(--radius-sm); padding: 7px 10px; color: var(--ink-0); font: 12px var(--font-mono); outline: none; }
        .imm-select:focus { border-color: var(--accent); }
        .imm-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
        .imm-actions { display: flex; gap: 8px; justify-content: flex-end; }
        .imm-saving { opacity: 0.5; pointer-events: none; }
      `}</style>

      {/* ── Insert Memory Modal ────────────────────────────────────────── */}
      {showRemember && (
        <InsertMemoryModal
          onClose={() => setShowRemember(false)}
          onSaved={(mem) => {
            window.CRAFT.MEMORIES = [mem, ...window.CRAFT.MEMORIES];
            setShowRemember(false);
          }}
        />
      )}

      <div className="exp-h">
        <div>
          <h1>Memory Explorer</h1>
          <div className="sub">
            RRF hybrid search · FTS5 BM25 + Jaccard · {totalDb.toLocaleString()} total in DB
            {" · "}{loadingRel ? "loading edges…" : relations.length.toLocaleString() + " graph edges"} · <kbd style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)", background: "var(--bg-3)", padding: "1px 4px", borderRadius: 2, border: "1px solid var(--line)" }}>⌘K</kbd> to search
          </div>
        </div>
        <button className="btn primary" onClick={() => setShowRemember(true)}>
          <Icon name="plus" /> remember()
        </button>
      </div>

      <div className="exp-search" style={{ gridColumn: "1 / -1" }}>
        <Icon name="search" />
        <span className="syntax mono">search_memory(</span>
        <input
          ref={inputRef}
          placeholder='"transport" OR scope:project tag:fts5'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") { setQuery(""); e.target.blur(); }
          }}
          autoFocus
        />
        <span className="syntax mono">)</span>
        {searching && <span className="search-spinner" />}
        {usingServerSearch && !searching && <span className="search-badge">FTS5</span>}
        {query && <span className="clear" onClick={() => { setQuery(""); inputRef.current?.focus(); }}><Icon name="x" size={12} /></span>}
        <kbd style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)", background: "var(--bg-3)", padding: "2px 5px", borderRadius: 3, border: "1px solid var(--line)" }}>Esc ↵</kbd>
      </div>

      <div className="exp-side">
        {filterActive && (
          <div className="filter-block">
            <div className="toggle-line" onClick={clearAllFilters} style={{ justifyContent: "center", color: "var(--accent)", fontFamily: "var(--font-mono)", fontSize: 10 }}>
              ✕ clear all filters
            </div>
          </div>
        )}
        <div className="filter-block">
          <div className="filter-h">Category</div>
          <div className="filter-body">
            {CATEGORIES.map(c => {
              const count = catCounts[c.id] || 0;
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
            {["all", ...SCOPES].map(s => (
              <div key={s} className={"filter-item" + (activeScope === s ? " on" : "")} onClick={() => setActiveScope(s)}>
                <span>{s}</span>
                <span className="count">{scopeCounts[s] || 0}</span>
              </div>
            ))}
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
          {showCount < filtered.length && <span>· showing {Math.min(showCount, filtered.length)}</span>}
          {usingServerSearch && <span>· <span className="mono" style={{ color: "var(--accent)" }}>FTS5 "{query}"</span></span>}
          {!usingServerSearch && query && <span>· local filter <span className="mono" style={{ color: "var(--ink-3)" }}>"{query}"</span></span>}
          <div className="sort-pills">
            <span className={"sort-pill" + (sortBy === "rrf" ? " on" : "")} onClick={() => setSortBy("rrf")}>rrf rank</span>
            <span className={"sort-pill" + (sortBy === "importance" ? " on" : "")} onClick={() => setSortBy("importance")}>importance</span>
            <span className={"sort-pill" + (sortBy === "recent" ? " on" : "")} onClick={() => setSortBy("recent")}>recent</span>
          </div>
        </div>

        {searchError && (
          <div className="search-err">⚠ Server search failed: {searchError} — showing local results</div>
        )}

        <div>
          {filtered.length === 0 && (
            <div className="empty-state">
              {searching ? "Searching…" : "No results · try clearing filters or relaxing the query"}
            </div>
          )}
          {displayed.map((m, i) => {
            const eCount = edgeCount(m.id);
            const expanded = expandedCards.has(m.id);
            const contentLong = m.content.length > MAX_CONTENT_PREVIEW;
            const showingFull = showFullContent.has(m.id);
            return (
              <div key={m.id} className="res-card">
                <div className="res-top">
                  <span className="res-id" onClick={() => onNavigate("graph", { focusId: m.id })}>#{m.id}</span>
                  <span className="res-cat" style={{ color: catColor(m.category), background: catColor(m.category) + "1f" }}>{m.category}</span>
                  <span className="chip muted">{m.scope}</span>
                  {m.isCore && <span className="chip accent"><Icon name="core" size={10} /> core</span>}
                  <span className="chip muted">{m.confidence}</span>
                  {eCount > 0 && (
                    <span className={"edge-badge" + (expanded ? " on" : "")} onClick={() => toggleExpanded(m.id)}
                      title={(() => { try { const n = neighborEdges(m.id).slice(0, 5).map(e => { const o = e.source === m.id ? e.target : e.source; return "#"+o+" ("+e.relation+")"; }).join(", "); return n + (eCount > 5 ? " ... +"+(eCount-5)+" more" : ""); } catch(e) { return ""; } })()}>
                      ◆ {eCount}
                    </span>
                  )}
                  <div className="res-meta">
                    <span>#{i + 1}</span>
                    <span>·</span>
                    <span>{formatRelTime ? formatRelTime(m.ts) : new Date(m.ts).toLocaleDateString()}</span>
                    <div className="res-rank">
                      <span>imp</span>
                      <div className="bar"><div style={{ width: Math.round(m.importance * 100) + "%" }} /></div>
                      <span>{m.importance.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
                <div className="res-content" onClick={() => onNavigate("graph", { focusId: m.id })}
                  title={contentLong && !showingFull ? m.content.slice(0, 500) + (m.content.length > 500 ? "..." : "") : ""}>
                  {highlight(showingFull ? m.content : m.content.slice(0, MAX_CONTENT_PREVIEW))}
                </div>
                {contentLong && (
                  <span className="expand-link" onClick={(e) => { e.stopPropagation(); toggleFullContent(m.id); }}>
                    {showingFull ? "▲ show less" : "▼ show all (" + m.content.length + " chars)"}
                  </span>
                )}
                <div className="res-tags">
                  {m.tags.map(t => <span key={t} className="chip muted"><Icon name="tag" size={9} /> {t}</span>)}
                </div>
                {expanded && eCount > 0 && (
                  <div className="neighbor-list">
                    {neighborEdges(m.id).slice(0, 10).map((e, j) => {
                      const otherId = e.source === m.id ? e.target : e.source;
                      return (
                        <div key={j} className="neighbor-item" onClick={() => onNavigate("graph", { focusId: otherId })}>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)" }}>#{otherId}</span>
                          <span className="arrow">─{e.relation}→</span>
                          <span style={{ fontSize: 10, color: "var(--ink-3)" }}>w={e.weight.toFixed(2)}</span>
                        </div>
                      );
                    })}
                    {eCount > 10 && (
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)", padding: "2px 4px" }}>
                        … and {eCount - 10} more — <span style={{ cursor: "pointer", color: "var(--accent)", textDecoration: "underline" }} onClick={() => onNavigate("graph", { focusId: m.id })}>view in graph</span>
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {hasMore && (
          <div className="load-more">
            <button className="btn ghost" onClick={() => setShowCount(s => s + 50)}>
              Show 50 more ({filtered.length - showCount} remaining)
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Insert Memory Modal ─────────────────────────────────────────────────────
const InsertMemoryModal = ({ onClose, onSaved }) => {
  const [content, setContent]   = React.useState("");
  const [category, setCategory] = React.useState("note");
  const [scope, setScope]       = React.useState("workspace");
  const [importance, setImportance] = React.useState(5);
  const [tags, setTags]         = React.useState("");
  const [saving, setSaving]     = React.useState(false);
  const [error, setError]       = React.useState(null);

  const { CATEGORIES, SCOPES } = window.CRAFT;

  const save = () => {
    if (!content.trim() || saving) return;
    setSaving(true);
    setError(null);
    const tagList = tags.split(",").map(t => t.trim()).filter(Boolean);
    CRAFT_API.remember({
      content: content.trim(),
      category,
      scope,
      importance,
      tags: tagList,
    })
      .then((res) => onSaved(res))
      .catch((e) => { setError(e.message); setSaving(false); });
  };

  return (
    <div className="imm-overlay" onClick={(e) => e.target === e.currentTarget && onClose()} onKeyDown={(e) => { if (e.key === "Escape") onClose(); }} tabIndex={-1} style={{ outline: 0 }}>
      <div className={`imm-box${saving ? " imm-saving" : ""}`}>
        <div className="imm-title">
          <span><span style={{ color: "var(--accent)", fontFamily: "var(--font-mono)" }}>remember()</span> — New memory</span>
          <button onClick={onClose}>×</button>
        </div>

        <div className="imm-field">
          <div className="imm-label">Content</div>
          <textarea
            className="imm-textarea"
            placeholder="What should the agent remember?"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            autoFocus
            onKeyDown={(e) => { if (e.key === "Enter" && e.metaKey) save(); }}
          />
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)", textAlign: "right" }}>
          {content.length} chars
        </div>

        <div className="imm-row">
          <div className="imm-field">
            <div className="imm-label">Category</div>
            <select className="imm-select" value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </div>
          <div className="imm-field">
            <div className="imm-label">Scope</div>
            <select className="imm-select" value={scope} onChange={(e) => setScope(e.target.value)}>
              {SCOPES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="imm-field">
            <div className="imm-label">Importance (1–10)</div>
            <select className="imm-select" value={importance} onChange={(e) => setImportance(Number(e.target.value))}>
              {[1,2,3,4,5,6,7,8,9,10].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>

        <div className="imm-field">
          <div className="imm-label">Tags (comma-separated)</div>
          <input
            className="imm-select"
            style={{ width: "100%" }}
            placeholder="fts5, architecture, decision"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
        </div>

        {error && <div style={{ color: "var(--critical)", fontFamily: "var(--font-mono)", fontSize: 12 }}>Error: {error}</div>}

        <div className="imm-actions">
          <button className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={save} disabled={!content.trim() || saving}>
            {saving ? "Saving…" : <><Icon name="plus" /> Save memory</>}
          </button>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)", alignSelf: "center", marginLeft: 4 }}>
            ⌘↵
          </div>
        </div>
      </div>
    </div>
  );
};

window.ExplorerScreen = ExplorerScreen;
