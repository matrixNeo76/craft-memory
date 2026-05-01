// Craft Memory — Config management (server URL + workspace ID via localStorage)
(function () {
  const STORAGE_KEY = "craft-memory-config";

  const DEFAULTS = {
    serverUrl: "http://127.0.0.1:8392",
    workspaceId: "",
  };

  function load() {
    try {
      return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") };
    } catch {
      return { ...DEFAULTS };
    }
  }

  function save(cfg) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
    window.__CRAFT_CONFIG = { ...cfg };
  }

  window.__CRAFT_CONFIG = load();
  window.__CRAFT_CONFIG_SAVE = save;
  window.__CRAFT_CONFIG_LOAD = load;
  window.__CRAFT_CONFIG_VER = 3;

  // ─── Config Modal component ──────────────────────────────────────────
  window.ConfigModal = function ({ onClose }) {
    const [cfg, setCfg] = React.useState(load());

    const saveAndReload = () => {
      save(cfg);
      window.location.reload();
    };

    const inputStyle = {
      width: "100%",
      background: "var(--bg-1)",
      border: "1px solid var(--line-2)",
      borderRadius: "var(--radius-sm)",
      padding: "8px 12px",
      color: "var(--ink-0)",
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      outline: "none",
    };

    const labelStyle = {
      fontFamily: "var(--font-mono)",
      fontSize: 10,
      color: "var(--ink-3)",
      textTransform: "uppercase",
      letterSpacing: "0.1em",
      marginBottom: 6,
    };

    return (
      <div
        style={{
          position: "fixed", inset: 0,
          background: "rgba(5,7,13,0.82)",
          display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 2000,
          backdropFilter: "blur(4px)",
        }}
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <div style={{
          background: "var(--bg-2)",
          border: "1px solid var(--line-2)",
          borderRadius: "var(--radius)",
          padding: 28,
          width: 440,
          display: "flex", flexDirection: "column", gap: 20,
          boxShadow: "var(--glow)",
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--ink-0)", fontWeight: 500 }}>
              Server Configuration
            </span>
            <button
              onClick={onClose}
              style={{ background: "none", border: "none", color: "var(--ink-3)", cursor: "pointer", fontSize: 22, lineHeight: 1, padding: 2 }}
            >×</button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <div style={labelStyle}>Server URL</div>
              <input
                style={inputStyle}
                value={cfg.serverUrl}
                onChange={(e) => setCfg((c) => ({ ...c, serverUrl: e.target.value }))}
                placeholder="http://127.0.0.1:8392"
                spellCheck={false}
              />
            </div>
            <div>
              <div style={labelStyle}>Workspace ID</div>
              <input
                style={inputStyle}
                value={cfg.workspaceId}
                onChange={(e) => setCfg((c) => ({ ...c, workspaceId: e.target.value }))}
                placeholder="default"
                spellCheck={false}
              />
              <div style={{ marginTop: 6, fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)" }}>
                Must match CRAFT_WORKSPACE_ID env var on the server.
              </div>
            </div>
          </div>

          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-3)",
            background: "var(--bg-1)", padding: "10px 12px", borderRadius: "var(--radius-sm)",
            borderLeft: "2px solid var(--accent-soft)",
          }}>
            Saving reloads the page to apply new settings.
          </div>

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              onClick={onClose}
              style={{ padding: "7px 16px", background: "var(--bg-1)", border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", color: "var(--ink-1)", cursor: "pointer", fontFamily: "var(--font-ui)" }}
            >Cancel</button>
            <button
              onClick={saveAndReload}
              style={{ padding: "7px 16px", background: "var(--accent)", border: "none", borderRadius: "var(--radius-sm)", color: "var(--bg-0)", cursor: "pointer", fontWeight: 600, fontFamily: "var(--font-ui)" }}
            >Save &amp; Reload</button>
          </div>
        </div>
      </div>
    );
  };
})();
