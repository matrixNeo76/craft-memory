// Craft Memory — API client (all server communication goes through here)
(function () {
  const base = () => (window.__CRAFT_CONFIG?.serverUrl || "http://127.0.0.1:8392").replace(/\/$/, "");
  const ws   = () =>  window.__CRAFT_CONFIG?.workspaceId || "";

  function buildQs(params) {
    const p = { workspace_id: ws(), ...params };
    return Object.entries(p)
      .filter(([, v]) => v !== null && v !== undefined && v !== "")
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join("&");
  }

  async function get(path, params = {}) {
    const url = `${base()}${path}?${buildQs(params)}`;
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
    return res.json();
  }

  async function post(path, body = {}) {
    const url = `${base()}${path}`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: ws(), ...body }),
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
    return res.json();
  }

  async function patch(path, body = {}) {
    const url = `${base()}${path}`;
    const res = await fetch(url, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: ws(), ...body }),
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
    return res.json();
  }

  // ─── Normalizers: server row → UI shape ──────────────────────────────

  function normMemory(m) {
    let tags = [];
    if (m.tags) {
      try { tags = typeof m.tags === "string" ? JSON.parse(m.tags) : m.tags; }
      catch { tags = []; }
    }
    // importance stored as 1-10 integer in DB → normalize to 0.0-1.0
    const imp = typeof m.importance === "number" ? m.importance : 5;
    return {
      id: m.id,
      content: m.content || "",
      category: m.category || "note",
      scope: m.scope || "workspace",
      importance: imp > 1 ? imp / 10 : imp,
      isCore: !!m.is_core,
      ts: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
      tags,
      confidence: m.confidence_type || "extracted",
    };
  }

  function normFact(f) {
    return {
      key: f.key,
      value: f.value,
      scope: f.scope || "workspace",
      confidence: f.confidence ?? 1.0,
      type: f.confidence_type || "extracted",
      mentions: f.mention_count ?? 0,
      godScore: f.god_score ?? 0,
    };
  }

  function normLoop(l) {
    return {
      id: l.id,
      title: l.title || "",
      priority: l.priority || "medium",
      description: l.description || "",
      scope: l.scope || "workspace",
      age: l.created_at
        ? Math.max(0, Math.floor((Date.now() - new Date(l.created_at).getTime()) / 86400000))
        : 0,
      refs: [],
      status: l.status || "open",
    };
  }

  // ─── Public API ───────────────────────────────────────────────────────

  window.CRAFT_API = {
    health:          ()              => fetch(`${base()}/health`, { signal: AbortSignal.timeout(8000) }).then(r => { if (!r.ok) throw new Error(`health ${r.status}`); return r.json(); }),
    stats:           ()              => get("/api/stats"),
    recentMemories:  (scope, limit)  => get("/api/memories/recent", { scope, limit }).then((r) => r.map(normMemory)),
    searchMemories:  (q, scope, lim) => get("/api/memories/search", { q, scope, limit: lim }).then((r) => r.map(normMemory)),
    facts:           (top_n)         => get("/api/facts", { top_n }).then((r) => r.map(normFact)),
    loops:           (scope, status) => get("/api/loops", { scope, status }).then((r) => r.map(normLoop)),
    diff:            (since)         => get("/api/diff", { since }),
    relations:       (id, dir)       => get("/api/relations", { memory_id: id, direction: dir }),
    handoff:         (scope)         => get("/api/handoff", { scope }),
    remember:        (body)          => post("/api/memories", body),
    addLoop:         (body)          => post("/api/loops", body).then(normLoop),
    closeLoop:       (id, resolution) => post(`/api/loops/${id}/close`, { resolution: resolution || "" }),
    updateLoop:      (id, fields)    => patch(`/api/loops/${id}`, fields),
  };
})();
