// Main app shell — sidebar nav, topbar, screen routing, tweaks integration
const { useState, useEffect, useCallback } = React;

const NAV = [
  { id: "home",      label: "Home",            icon: "home" },
  { id: "dashboard", label: "Dashboard",       icon: "dashboard" },
  { id: "explorer",  label: "Memory Explorer", icon: "search" },
  { id: "graph",     label: "Knowledge Graph", icon: "graph" },
  { id: "loops",     label: "Open Loops",      icon: "loops",   badgeCrit: true },
  { id: "handoff",   label: "Session Handoff", icon: "handoff" },
  { id: "diff",      label: "Memory Diff",     icon: "diff" },
];

const TOOLS = [
  { id: "remember",     label: "remember()",      icon: "plus" },
  { id: "search",       label: "search_memory()", icon: "search" },
  { id: "find_similar", label: "find_similar()",  icon: "spark" },
  { id: "maintenance",  label: "run_maintenance()", icon: "settings" },
];

// ─── Skeleton loading screen shown while initial data loads ──────────
const LoadingScreen = ({ error }) => (
  <div style={{
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
    height: "100vh", gap: 16, background: "var(--bg-0)", color: "var(--ink-2)",
    fontFamily: "var(--font-mono)", fontSize: 13,
  }}>
    {error ? (
      <>
        <div style={{ color: "var(--critical)", fontSize: 14, fontWeight: 500 }}>Server offline</div>
        <div style={{ color: "var(--ink-3)", maxWidth: 360, textAlign: "center", lineHeight: 1.7 }}>
          Cannot reach <span style={{ color: "var(--accent)" }}>{window.__CRAFT_CONFIG?.serverUrl}</span>.
          Start the server or check the URL in settings.
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <button
            onClick={() => window.location.reload()}
            style={{ padding: "7px 16px", background: "var(--bg-2)", border: "1px solid var(--line-2)", borderRadius: "var(--radius-sm)", color: "var(--ink-0)", cursor: "pointer" }}
          >Retry</button>
          <button
            onClick={() => {
              const url = prompt("Server URL:", window.__CRAFT_CONFIG?.serverUrl || "http://127.0.0.1:8392");
              if (url) { window.__CRAFT_CONFIG_SAVE({ ...window.__CRAFT_CONFIG, serverUrl: url }); window.location.reload(); }
            }}
            style={{ padding: "7px 16px", background: "var(--accent)", border: "none", borderRadius: "var(--radius-sm)", color: "var(--bg-0)", cursor: "pointer", fontWeight: 600 }}
          >Change URL</button>
        </div>
      </>
    ) : (
      <>
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--accent)", animation: "pulse 1.5s ease-in-out infinite" }} />
        <span style={{ color: "var(--ink-3)" }}>Connecting to {window.__CRAFT_CONFIG?.serverUrl}…</span>
      </>
    )}
  </div>
);

// ─── Main App ─────────────────────────────────────────────────────────
const App = () => {
  const [route, setRoute] = useState("home");
  const [routeArgs, setRouteArgs] = useState({});
  const [tweaks, setTweaks] = useTweaks(window.__CRAFT_TWEAKS__);

  const [appReady, setAppReady]   = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [connected, setConnected] = useState(null);
  const [liveStats, setLiveStats] = useState(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [wsId, setWsId] = useState(window.__CRAFT_CONFIG?.workspaceId || "");

  // ─── Initial data load ─────────────────────────────────────────────
  const loadData = useCallback(async () => {
    try {
      // Auto-detect workspace from server health
      const health = await CRAFT_API.health();
      if (health.workspace) {
        window.__CRAFT_CONFIG = { ...window.__CRAFT_CONFIG, workspaceId: health.workspace };
        setWsId(health.workspace);
      }

      const [stats, memories, facts, loops, relations, diff] = await Promise.all([
        CRAFT_API.stats(),
        CRAFT_API.recentMemories(null, 50),
        CRAFT_API.facts(20),
        CRAFT_API.loops(null, "open"),
        CRAFT_API.relations(null, null).catch(() => []),
        CRAFT_API.diff(null).catch(() => []),
      ]);

      // Calculate uptime from server boot_time if available
      const bootTs = health.boot_time ? new Date(health.boot_time).getTime() : null;

      window.CRAFT = {
        ...window.CRAFT,
        STATS: {
          memoriesTotal:   stats.total_memories    ?? 0,
          memoriesCore:    stats.core_memories     ?? 0,
          factsTotal:      stats.total_facts       ?? 0,
          loopsOpen:       stats.open_loops        ?? 0,
          loopsCritical:   0,
          proceduresTotal: stats.total_procedures  ?? 0,
          edgesTotal:      stats.total_edges       ?? 0,
          workspaceSize:   stats.db_size_mb != null ? `${stats.db_size_mb} MB` : "—",
          oldestMemory:    "—",
          uptime:          bootTs,
        },
        MEMORIES:    memories,
        FACTS:       facts,
        LOOPS:       loops,
        RELATIONS:   Array.isArray(relations) ? relations : (relations?.edges ?? []),
        DIFF_EVENTS: Array.isArray(diff) ? diff : (diff?.events ?? []),
        SESSIONS:    [{
          id:             health.workspace || window.__CRAFT_CONFIG.workspaceId,
          date:           new Date().toISOString().split("T")[0],
          duration:       bootTs ? Math.round((Date.now() - bootTs) / 60000) + "m" : "—",
          model:          health.model || "—",
          memoriesAdded:  stats.total_memories    ?? 0,
          factsLearned:   stats.total_facts       ?? 0,
          loopsOpened:    stats.open_loops        ?? 0,
          loopsClosed:    0,
        }],
      };

      setLiveStats(stats);
      setConnected(true);
      setLoadError(false);
    } catch (err) {
      console.warn("[craft-memory] offline:", err.message);
      window.CRAFT = {
        ...window.CRAFT,
        MEMORIES: [], FACTS: [], LOOPS: [], SESSIONS: [], RELATIONS: [], DIFF_EVENTS: [],
        STATS: { memoriesTotal: 0, memoriesCore: 0, factsTotal: 0, loopsOpen: 0, loopsCritical: 0, proceduresTotal: 0, edgesTotal: 0, workspaceSize: "—", oldestMemory: "—", uptime: null },
      };
      setConnected(false);
      setLoadError(true);
    }
    setAppReady(true);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Health check every 30s
  useEffect(() => {
    const id = setInterval(() => {
      CRAFT_API.health().then(() => setConnected(true)).catch(() => setConnected(false));
    }, 30000);
    return () => clearInterval(id);
  }, []);

  // ─── Apply tweaks → CSS / body classes ────────────────────────────
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--accent-h", String(tweaks.accentHue));
    root.style.setProperty("--font-ui", `"${tweaks.uiFont}", -apple-system, system-ui, sans-serif`);
    root.style.setProperty("--font-mono", `"${tweaks.monoFont}", ui-monospace, Menlo, monospace`);
    const bgMap = {
      void:     ["#000000", "#070b13", "#0c121d"],
      midnight: ["#05070d", "#0a0f1a", "#0f1623"],
      navy:     ["#070d1a", "#0d1424", "#131c30"],
      slate:    ["#0a0e16", "#11151f", "#181d2a"],
    };
    const bg = bgMap[tweaks.background] || bgMap.midnight;
    root.style.setProperty("--bg-0", bg[0]);
    root.style.setProperty("--bg-1", bg[1]);
    root.style.setProperty("--bg-2", bg[2]);
    document.body.classList.toggle("glow-off",  tweaks.glow === "off");
    document.body.classList.toggle("motion-off", tweaks.motion === "off");
    document.body.classList.toggle("grid-off",   !tweaks.showGrid);
    document.body.classList.toggle("scanlines",   tweaks.scanlines);
    const binary = document.getElementById("bg-binary");
    if (binary) binary.style.display = tweaks.showBinary ? "" : "none";
  }, [tweaks]);

  useEffect(() => {
    if (!tweaks.scanlines) return;
    const id = "scanlines-style";
    if (document.getElementById(id)) return;
    const s = document.createElement("style");
    s.id = id;
    s.textContent = `body.scanlines::after { content:""; position:fixed; inset:0; pointer-events:none; z-index:50; background:repeating-linear-gradient(to bottom, transparent, transparent 2px, rgba(120,170,255,0.025) 2px, rgba(120,170,255,0.025) 3px); }`;
    document.head.appendChild(s);
  }, [tweaks.scanlines]);

  const navigate = (id, args = {}) => {
    setRoute(id);
    setRouteArgs(args);
    document.querySelector(".main")?.scrollTo({ top: 0, behavior: tweaks.motion === "off" ? "instant" : "smooth" });
  };

  const isDense = tweaks.density === "compact";
  const cfg = window.__CRAFT_CONFIG || {};

  // Dynamic nav badges from live data
  const navWithBadges = NAV.map(n => {
    if (!liveStats) return n;
    if (n.id === "explorer") return { ...n, badge: String(liveStats.total_memories ?? 0) };
    if (n.id === "graph")    return { ...n, badge: String(liveStats.total_edges ?? 0) };
    if (n.id === "loops") {
      const cnt = liveStats.open_loops ?? 0;
      return { ...n, badge: cnt > 0 ? String(cnt) : null };
    }
    return n;
  });

  if (!appReady) return <LoadingScreen error={loadError} />;

  return (
    <div className={"shell" + (isDense ? " dense" : "")}>
      {configOpen && <ConfigModal onClose={() => setConfigOpen(false)} />}

      <header className="topbar">
        <div className="brand">
          <LogoMark size={28} glow={tweaks.glow !== "off"} />
          <span className="brand-name">Craft Memory</span>
          <span className="brand-sub">v0.5.0</span>
        </div>
        <div className="topbar-search">
          <Icon name="search" />
          <input placeholder="Search memories, facts, procedures…" onFocus={() => navigate("explorer")} />
          <kbd>⌘K</kbd>
        </div>
        <div className="topbar-meta">
          <span className="topbar-status">
            <span className="dot" style={{ background: connected === false ? "var(--critical)" : connected === true ? "oklch(0.78 0.18 150)" : "var(--ink-3)" }} />
            <span style={{ color: connected === false ? "var(--critical)" : "inherit" }}>
              {connected === false ? "offline" : cfg.serverUrl?.replace("http://", "") || "127.0.0.1:8392"}
            </span>
          </span>
          <span>·</span>
          <span title="Workspace ID" style={{ cursor: "default" }}>{wsId || cfg.workspaceId || "—"}</span>
          <span>·</span>
          <button
            onClick={() => setConfigOpen(true)}
            title="Server configuration"
            style={{ background: "none", border: "none", color: "var(--ink-3)", cursor: "pointer", padding: "2px 4px", borderRadius: 4, fontSize: 12, fontFamily: "var(--font-mono)" }}
          >settings</button>
        </div>
      </header>

      <aside className="sidebar">
        <div>
          <div className="nav-group-label">Workspace</div>
          {navWithBadges.map(n => (
            <div key={n.id} className={"nav-item" + (route === n.id ? " active" : "")} onClick={() => navigate(n.id)}>
              <Icon name={n.icon} className="icon" />
              <span>{n.label}</span>
              {n.badge && (
                <span className="badge" style={n.badgeCrit ? { background: "var(--critical)", color: "var(--bg-0)" } : undefined}>
                  {n.badge}
                </span>
              )}
            </div>
          ))}
        </div>

        <div>
          <div className="nav-group-label">MCP Tools</div>
          {TOOLS.map(t => (
            <div key={t.id} className="nav-item" onClick={() => {
              if (t.id === "search")       { navigate("explorer", { action: "search" }); }
              else if (t.id === "find_similar") { navigate("graph",    { action: "find_similar" }); }
              else if (t.id === "remember")    { navigate("explorer", { action: "remember" }); }
              else if (t.id === "maintenance") { navigate("dashboard", { action: "maintenance" }); }
              else { navigate("explorer", { action: t.id }); }
            }}>
              <Icon name={t.icon} className="icon" />
              <span className="mono" style={{ fontSize: 12 }}>{t.label}</span>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="row"><span>db</span><span>{window.CRAFT.STATS.workspaceSize}</span></div>
          <div className="row"><span>memories</span><span>{window.CRAFT.STATS.memoriesTotal.toLocaleString()}</span></div>
          <div className="row"><span>facts</span><span>{window.CRAFT.STATS.factsTotal}</span></div>
          <div className="row"><span>λ decay</span><span>0.005</span></div>
        </div>
      </aside>

      <main className="main">
        <div className="main-inner">
          {route === "home"      && <HomeScreen      onNavigate={navigate} />}
          {route === "dashboard" && <DashboardScreen onNavigate={navigate} />}
          {route === "explorer"  && <ExplorerScreen  onNavigate={navigate} action={routeArgs.action} />}
          {route === "graph"     && <GraphScreen     onNavigate={navigate} focusId={routeArgs.focusId} action={routeArgs.action} />}
          {route === "loops"     && <LoopsScreen     onNavigate={navigate} />}
          {route === "handoff"   && <HandoffScreen   onNavigate={navigate} />}
          {route === "diff"      && <DiffScreen      onNavigate={navigate} />}
        </div>
      </main>

      <footer className="statusbar">
        <span className={connected === false ? "err" : "ok"}>
          {connected === false ? "● server offline" : connected === true ? "● connected" : "● connecting…"}
        </span>
        <span className="sep" />
        <span>FastMCP 1.26.0 · stateless_http=True</span>
        <span className="sep" />
        <span>SQLite WAL · FTS5 unicode61</span>
        <span className="sep" />
        <span className="accent">RRF k=60</span>
        <span className="sep" />
        <span>BM25 autolink &lt; -2.5</span>
        <span style={{ marginLeft: "auto", color: "var(--ink-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
          ws: {wsId || cfg.workspaceId || "—"}
        </span>
      </footer>

      <CraftTweaks tweaks={tweaks} setTweak={setTweaks} />
    </div>
  );
};

// ─── Tweaks panel ─────────────────────────────────────────────────────
const CraftTweaks = ({ tweaks, setTweak }) => {
  const TP = TweaksPanel;
  const TS = TweakSection;
  return (
    <TP title="Tweaks">
      <TS label="Color">
        <TweakSlider label="Accent hue" value={tweaks.accentHue} min={0} max={360} step={1} unit="°" onChange={(v) => setTweak("accentHue", v)} />
        <TweakRadio label="Background" value={tweaks.background} options={["void", "midnight", "navy", "slate"]} onChange={(v) => setTweak("background", v)} />
        <TweakRadio label="Glow" value={tweaks.glow} options={["off", "subtle", "strong"]} onChange={(v) => setTweak("glow", v)} />
      </TS>
      <TS label="Layout">
        <TweakRadio label="Density" value={tweaks.density} options={["compact", "comfortable"]} onChange={(v) => setTweak("density", v)} />
        <TweakToggle label="Grid background" value={tweaks.showGrid} onChange={(v) => setTweak("showGrid", v)} />
        <TweakToggle label="Binary rain" value={tweaks.showBinary} onChange={(v) => setTweak("showBinary", v)} />
        <TweakToggle label="Scanlines (CRT)" value={tweaks.scanlines} onChange={(v) => setTweak("scanlines", v)} />
      </TS>
      <TS label="Type">
        <TweakSelect label="UI font" value={tweaks.uiFont} options={["Geist", "Inter", "system-ui"]} onChange={(v) => setTweak("uiFont", v)} />
        <TweakSelect label="Mono font" value={tweaks.monoFont} options={["JetBrains Mono", "IBM Plex Mono", "Geist Mono"]} onChange={(v) => setTweak("monoFont", v)} />
      </TS>
      <TS label="Motion">
        <TweakRadio label="Animations" value={tweaks.motion} options={["off", "calm", "lively"]} onChange={(v) => setTweak("motion", v)} />
      </TS>
    </TP>
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
