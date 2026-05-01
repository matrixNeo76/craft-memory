// Session Handoff — generated structured handoff for the current session
const HandoffScreen = ({ onNavigate }) => {
  const { SESSIONS, MEMORIES, FACTS, LOOPS, formatRelTime } = window.CRAFT;
  const [handoffData, setHandoffData] = React.useState(null);
  const [loadingHandoff, setLoadingHandoff] = React.useState(true);

  // Attempt to load structured handoff from backend
  React.useEffect(() => {
    setLoadingHandoff(true);
    CRAFT_API.handoff(null)
      .then((data) => setHandoffData(data))
      .catch(() => setHandoffData(null))
      .finally(() => setLoadingHandoff(false));
  }, []);

  // Safe session: use backend data or fallback to window.CRAFT.SESSIONS[0] with complete defaults
  const fallbackSession = SESSIONS[0] || {};
  const [selectedSession, setSelectedSession] = React.useState(fallbackSession.id || "current");
  const sess = {
    id:             fallbackSession.id || "current",
    date:           fallbackSession.date || new Date().toISOString().split("T")[0],
    duration:       fallbackSession.duration || "—",
    model:          fallbackSession.model || "—",
    memoriesAdded:  fallbackSession.memoriesAdded ?? "—",
    factsLearned:   fallbackSession.factsLearned  ?? "—",
    loopsOpened:    fallbackSession.loopsOpened   ?? "—",
    loopsClosed:    fallbackSession.loopsClosed   ?? "—",
  };

  const decisions    = MEMORIES.filter(m => m.category === "decision").slice(0, 3);
  const discoveries  = MEMORIES.filter(m => m.category === "discovery").slice(0, 2);
  const openLoops    = LOOPS.slice(0, 4);

  // Derive next steps from handoff API if available
  const nextSteps = handoffData?.next_steps || [
    { text: "Check open loops and resolve any critical ones." },
    { text: "Run run_maintenance() to compact the DB and prune stale edges." },
  ];

  // Summary from API or static placeholder
  const summary = handoffData?.summary ||
    "No handoff summary available. Call generate_handoff() from the MCP client to produce one.";

  return (
    <div className="hand">
      <style>{`
        .hand { display: grid; grid-template-columns: 280px 1fr; gap: 16px; }
        .hand-h { grid-column: 1 / -1; display: flex; align-items: end; justify-content: space-between; }
        .hand-h h1 { margin: 0; font-size: 24px; font-weight: 500; }
        .hand-h .sub { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); margin-top: 2px; }
        .sess-row { padding: 12px 14px; border-bottom: 1px solid var(--line); cursor: pointer; }
        .sess-row:hover { background: var(--bg-2); }
        .sess-row.on { background: var(--accent-soft); border-left: 2px solid var(--accent); }
        .sess-row .id { font-family: var(--font-mono); font-size: 11px; color: var(--accent); }
        .sess-row .date { font-size: 12px; color: var(--ink-1); margin-top: 2px; }
        .sess-row .meta { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); margin-top: 6px; display: flex; gap: 8px; flex-wrap: wrap; }
        .doc { padding: 24px 28px; background: var(--bg-1); border: 1px solid var(--line); border-radius: var(--radius); font-size: 14px; line-height: 1.6; }
        .doc h2 { font-size: 13px; font-family: var(--font-mono); text-transform: uppercase; letter-spacing: 0.1em; color: var(--accent); margin: 24px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }
        .doc h2:first-child { margin-top: 0; }
        .doc .head { display: flex; align-items: center; gap: 12px; padding-bottom: 16px; border-bottom: 1px solid var(--line); margin-bottom: 8px; }
        .doc .head .id { font-family: var(--font-mono); font-size: 12px; color: var(--accent); }
        .doc .head .title { font-size: 18px; font-weight: 500; }
        .doc .head .meta { font-family: var(--font-mono); font-size: 11px; color: var(--ink-3); margin-left: auto; }
        .doc-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 16px 0; border-bottom: 1px solid var(--line); margin-bottom: 8px; }
        .doc-stat { padding: 10px; background: var(--bg-2); border-radius: var(--radius-sm); }
        .doc-stat .v { font-family: var(--font-mono); font-size: 18px; color: var(--ink-0); font-weight: 500; }
        .doc-stat .l { font-family: var(--font-mono); font-size: 9px; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px; }
        .doc-list { padding: 0; margin: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; }
        .doc-list li { padding: 10px 14px; background: var(--bg-2); border-left: 2px solid var(--accent); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
        .doc-list li .ref { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); display: block; margin-top: 4px; }
        .next-box { padding: 14px; background: linear-gradient(135deg, var(--accent-soft), transparent); border: 1px solid var(--accent-soft); border-radius: var(--radius-sm); }
        .next-box ol { margin: 0; padding-left: 20px; color: var(--ink-1); }
        .next-box ol li { margin-bottom: 6px; }
        .copy-row { display: flex; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line); }
      `}</style>

      <div className="hand-h">
        <div>
          <h1>Session Handoff</h1>
          <div className="sub">structured continuation document · save_summary() output</div>
        </div>
        <div className="row gap-12">
          <button className="btn ghost"><Icon name="external" /> Copy markdown</button>
          <button className="btn primary"><Icon name="play" /> Start next session with this</button>
        </div>
      </div>

      <div className="panel" style={{ height: "max-content" }}>
        <div className="panel-head"><div className="panel-title">Sessions <span className="dim">/ {SESSIONS.length}</span></div></div>
        <div>
          {SESSIONS.map(s => (
            <div key={s.id} className={"sess-row" + (s.id === selectedSession ? " on" : "")} onClick={() => setSelectedSession(s.id)}>
              <div className="id">{s.id}</div>
              <div className="date">{s.date}</div>
              <div className="meta">
                <span>{s.duration}</span>
                <span>·</span>
                <span>{s.model}</span>
              </div>
              <div className="meta">
                <span>+{s.memoriesAdded} mem</span>
                <span>+{s.factsLearned} fact</span>
                <span>↻{s.loopsOpened} ✓{s.loopsClosed}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="doc">
        <div className="head">
          <span className="id">{sess.id}</span>
          <div>
            <div className="title">Session Handoff</div>
            <div className="dimmer mono" style={{ fontSize: 11, marginTop: 2 }}>{sess.date} · {sess.duration} · {sess.model}</div>
          </div>
          <div className="meta">generated by <span style={{ color: "var(--accent)" }}>generate_handoff()</span></div>
        </div>

        <div className="doc-stats">
          <div className="doc-stat"><div className="v">{sess.memoriesAdded}</div><div className="l">memories saved</div></div>
          <div className="doc-stat"><div className="v">{sess.factsLearned}</div><div className="l">facts learned</div></div>
          <div className="doc-stat"><div className="v">{sess.loopsOpened}</div><div className="l">loops opened</div></div>
          <div className="doc-stat"><div className="v">{sess.loopsClosed}</div><div className="l">loops closed</div></div>
        </div>

        <h2>Summary</h2>
        <p style={{ color: "var(--ink-1)", margin: 0 }}>
          {loadingHandoff ? (
            <span style={{ color: "var(--ink-3)", fontFamily: "var(--font-mono)", fontSize: 12 }}>Loading handoff…</span>
          ) : summary}
        </p>

        <h2>Decisions</h2>
        <ul className="doc-list">
          {decisions.map(m => (
            <li key={m.id}>
              {m.content}
              <span className="ref">ref: #{m.id} · scope: {m.scope} · importance: {m.importance.toFixed(2)} {m.isCore && "· core"}</span>
            </li>
          ))}
        </ul>

        <h2>Discoveries</h2>
        <ul className="doc-list">
          {discoveries.map(m => (
            <li key={m.id} style={{ borderLeftColor: "oklch(0.82 0.14 175)" }}>
              {m.content}
              <span className="ref">ref: #{m.id} · scope: {m.scope}</span>
            </li>
          ))}
        </ul>

        <h2>Facts learned</h2>
        <ul className="doc-list">
          {FACTS.slice(0, 3).map(f => (
            <li key={f.key} style={{ borderLeftColor: "oklch(0.78 0.16 280)" }}>
              <span className="mono" style={{ color: "var(--accent)" }}>{f.key}</span> = {f.value}
              <span className="ref">scope: {f.scope} · confidence: {f.confidence.toFixed(2)} · {f.type}</span>
            </li>
          ))}
        </ul>

        <h2>Open loops</h2>
        <ul className="doc-list">
          {openLoops.map(l => (
            <li key={l.id} style={{ borderLeftColor: l.priority === "critical" ? "var(--critical)" : l.priority === "high" ? "var(--high)" : "var(--medium)" }}>
              <strong>#{l.id}</strong> · {l.title}
              <span className="ref">priority: {l.priority} · age: {l.age}d · scope: {l.scope}</span>
            </li>
          ))}
        </ul>

        <h2>Next steps</h2>
        <div className="next-box">
          <ol>
            {nextSteps.map((s, i) => (
              <li key={i} dangerouslySetInnerHTML={{ __html: s.text || s }} />
            ))}
          </ol>
        </div>

        <div className="copy-row">
          <button className="btn"><Icon name="external" /> Copy as markdown</button>
          <button className="btn ghost" onClick={() => onNavigate("loops")}><Icon name="loops" /> Open loops</button>
          <button className="btn ghost" onClick={() => onNavigate("explorer")}><Icon name="search" /> Search referenced</button>
        </div>
      </div>
    </div>
  );
};

window.HandoffScreen = HandoffScreen;
