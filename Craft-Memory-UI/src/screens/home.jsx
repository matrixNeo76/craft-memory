// Home / landing screen — big A logo + product framing
const HomeScreen = ({ onNavigate }) => {
  const { STATS } = window.CRAFT;
  return (
    <div className="home-wrap">
      <style>{`
        .home-wrap { display: grid; grid-template-columns: 1.1fr 1fr; gap: 48px; align-items: center; min-height: calc(100vh - 140px); padding: 32px 16px; }
        .home-left { display: flex; flex-direction: column; gap: 24px; }
        .home-eyebrow { display: inline-flex; align-items: center; gap: 10px; padding: 4px 10px; border: 1px solid var(--line-2); border-radius: 999px; font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-1); width: max-content; background: var(--bg-1); }
        .home-eyebrow .pulse { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 8px var(--accent); animation: pulse 2s ease-in-out infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .home-h1 { font-size: 56px; line-height: 1.05; font-weight: 600; letter-spacing: -0.02em; margin: 0; }
        .home-h1 .accent { color: var(--accent); }
        .home-h1 .stencil { font-family: var(--font-mono); color: var(--ink-2); font-weight: 400; }
        .home-sub { font-size: 17px; line-height: 1.55; color: var(--ink-1); max-width: 560px; }
        .home-sub strong { color: var(--ink-0); font-weight: 500; }
        .home-cta-row { display: flex; gap: 12px; align-items: center; margin-top: 4px; }
        .home-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; background: var(--bg-1); margin-top: 12px; max-width: 620px; }
        .home-stat { padding: 14px 16px; border-right: 1px solid var(--line); }
        .home-stat:last-child { border-right: 0; }
        .home-stat .v { font-family: var(--font-mono); font-size: 22px; color: var(--ink-0); font-weight: 500; }
        .home-stat .l { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px; }
        .home-right { display: flex; align-items: center; justify-content: center; position: relative; }
        .home-right::before { content: ""; position: absolute; inset: -40px; border-radius: 50%; background: radial-gradient(circle, var(--accent-soft), transparent 60%); filter: blur(40px); }
        .home-right svg { position: relative; z-index: 1; }
        .home-features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px; }
        .home-feature { padding: 14px; background: var(--bg-1); border: 1px solid var(--line); border-radius: var(--radius); }
        .home-feature .label { font-family: var(--font-mono); font-size: 10px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.1em; }
        .home-feature .title { font-size: 13px; color: var(--ink-0); margin-top: 4px; font-weight: 500; }
        .home-feature .desc { font-size: 12px; color: var(--ink-2); margin-top: 4px; line-height: 1.5; }
        .home-codeline { font-family: var(--font-mono); font-size: 12px; color: var(--ink-2); padding: 10px 14px; background: var(--bg-1); border: 1px solid var(--line); border-radius: var(--radius-sm); display: flex; align-items: center; gap: 10px; max-width: 480px; }
        .home-codeline .prompt { color: var(--accent); }
        .home-codeline .arg { color: var(--ink-0); }
        .home-codeline .copy-btn { margin-left: auto; color: var(--ink-3); cursor: pointer; }
        .home-codeline .copy-btn:hover { color: var(--ink-1); }
      `}</style>

      <div className="home-left">
        <div className="home-eyebrow">
          <span className="pulse" />
          <span>v0.5.0 · Server up · {(window.__CRAFT_CONFIG?.serverUrl || "localhost:8392").replace("http://", "")}</span>
        </div>
        <h1 className="home-h1">
          Persistent neural memory<br />
          for <span className="accent">Craft Agents</span>.
        </h1>
        <p className="home-sub">
          Without memory, every AI session starts from zero. Craft Memory gives your agent a <strong>long-term, local memory</strong> that survives session restarts, model switches, and provider changes — built on FastMCP, SQLite, and FTS5.
        </p>

        <div className="home-codeline">
          <span className="prompt">$</span>
          <span><span className="arg">craft-memory</span> ensure</span>
          <span className="dim">→ OK: server running on 8392</span>
        </div>

        <div className="home-cta-row">
          <button className="btn primary" onClick={() => onNavigate("dashboard")}>
            Open dashboard <Icon name="arrow" />
          </button>
          <button className="btn" onClick={() => onNavigate("explorer")}>
            <Icon name="search" /> Explore memory
          </button>
          <a className="btn ghost" href="https://github.com/matrixNeo76/craft-memory" target="_blank" rel="noreferrer">
            <Icon name="github" /> GitHub
          </a>
        </div>

        <div className="home-stats">
          <div className="home-stat"><div className="v">{STATS.memoriesTotal.toLocaleString()}</div><div className="l">Memories</div></div>
          <div className="home-stat"><div className="v">{STATS.factsTotal}</div><div className="l">Stable facts</div></div>
          <div className="home-stat"><div className="v">{STATS.edgesTotal}</div><div className="l">Graph edges</div></div>
          <div className="home-stat"><div className="v">{STATS.uptime}</div><div className="l">Uptime</div></div>
        </div>

        <div className="home-features">
          <div className="home-feature">
            <div className="label">Episodic</div>
            <div className="title">Decisions, discoveries, bugfixes</div>
            <div className="desc">Saved during work, recalled next session.</div>
          </div>
          <div className="home-feature">
            <div className="label">RRF Search</div>
            <div className="title">FTS5 BM25 + Jaccard</div>
            <div className="desc">No embeddings. +6–8% over linear.</div>
          </div>
          <div className="home-feature">
            <div className="label">Graph</div>
            <div className="title">Typed relations + roles</div>
            <div className="desc">causal · temporal · context · core · detail</div>
          </div>
        </div>
      </div>

      <div className="home-right">
        <LogoHero size={420} />
      </div>
    </div>
  );
};

window.HomeScreen = HomeScreen;
