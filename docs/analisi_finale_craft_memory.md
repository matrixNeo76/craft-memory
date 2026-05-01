# Analisi Finale — Sistema Craft Memory

**Data**: 2026-05-01
**Repo**: [matrixNeo76/craft-memory](https://github.com/matrixNeo76/craft-memory)
**Stack**: FastMCP 1.26.0 · SQLite + FTS5 · Python 3.12 · Craft Agents (pi)

---

## 1. Panoramica

Craft Memory è un **MCP server Python** che fornisce memoria persistente cross-session per Craft Agents. Ogni sessione di pi parte da zero — Craft Memory colma questo gap con un database SQLite locale esposto via HTTP MCP.

### Componenti

| Componente | Descrizione | Righe |
|---|---|---|
| `src/craft_memory_mcp/server.py` | FastMCP server, 46 tool, Pydantic patch, health/metrics endpoint | ~800 |
| `src/craft_memory_mcp/db.py` | SQLite + WAL + FTS5, CRUD, grafo, migrazioni, manutenzione | ~900 |
| `src/craft_memory_mcp/cli.py` | CLI craft-memory (ensure/serve/check/stop/install) | ~200 |
| `src/craft_memory_mcp/schema.sql` | Schema v1 (6 tabelle + FTS5) | ~100 |
| `migrations/` | 12 migrazioni versionate (002→012) | ~500 |
| `scripts/ensure-running.py` | Lifecycle manager: check, start, stop | ~150 |
| `skills/` | 4 skill: memory-protocol, memory-start, memory-maintenance, session-handoff | 4 SKILL.md |
| `craft-agents/automations.json` | 4 automazioni (SessionStart, SessionEnd, SchedulerTick, LabelAdd) | 1 file |
| `tests/` | 209 pytest (core, graph, observability, temporal, policy, procedures, etc.) | ~2000 |
| `docs/adr/` | 8 Architecture Decision Records | 8 file |

---

## 2. Architettura

```
┌─────────────────────────────────────────────────────────┐
│                    Craft Agents (pi)                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────┐  │
│  │ Session  │  │ Session  │  │ Scheduler │  │ Label  │  │
│  │  Start   │  │   End    │  │   Tick    │  │  Add   │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └───┬────┘  │
│       ▼              ▼              ▼              ▼       │
│            Memory Source (HTTP MCP, :8392/mcp)            │
└─────────────────────────┬────────────────────────────────┘
                          │ HTTP / Streamable HTTP
┌─────────────────────────▼────────────────────────────────┐
│              Craft Memory Server (Python)                 │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │   server.py  │  │    db.py      │  │  schema.sql   │  │
│  │  (FastMCP)   │  │  (SQLite)     │  │   (Schema)    │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────────┘  │
│         ▼                  ▼                              │
│        ~/.craft-agent/memory/{workspaceId}.db             │
│        (SQLite + WAL + FTS5)                              │
└──────────────────────────────────────────────────────────┘
```

### Trasporto

- **HTTP** (default, raccomandato): `localhost:8392/mcp`, server persistente, bypassa bug stdio Windows
- **stdio**: alternativa per test locali su Linux/macOS

### Bug risolti (documentati in ARCHITECTURE.md §7)

| # | Problema | Fix |
|---|----------|-----|
| 7.1 | Windows stdio disconnette dopo ~4s | Migrazione a HTTP transport |
| 7.2 | `http_app()` rimosso in FastMCP 1.26.0 | `streamable_http_app()` |
| 7.3 | "Session not found" dopo restart | `stateless_http=True` |
| 7.4 | Pydantic rifiuta `_displayName`, `_intent` | `ArgModelBase.model_config["extra"] = "ignore"` |
| 7.5 | `memory` non in `enabledSourceSlugs` | Aggiunto manualmente |
| 7.6 | Automations senza `permissionMode` | `"allow-all"` su tutte 4 |
| 7.7 | Server non partiva automaticamente | `ensure-running.py` in SessionStart |
| 7.8 | `remember()` ritorna "Duplicate" sempre | FK violation: `register_session` auto-call in `_get_conn()` |
| 7.9 | `search_memory()` scope binding errato LIKE fallback | Parametri separati per LIKE scope |
| 7.10 | `HAVING` senza `GROUP BY` | Subquery wrapper |

---

## 3. Criticità Identificate

### 🔴 Critiche

| ID | Criticità | Dettaglio |
|----|-----------|-----------|
| **C1** | **server.py God Object** | 46 tool nello stesso file, ognuno con `_get_conn()` duplicato. Ogni modifica tocca il file centrale. Test isolati impossibili. |
| **C2** | **Global State** | `_conn = None` e `_write_count = 0` come variabili module-level. In ambiente multi-worker (uvicorn), le connessioni collidono. |
| **C3** | **Automations sono Prompt, non Workflow** | Le 4 automations usano `"type": "prompt"` con testo libero all'agente. Nessuna garanzia che l'agente esegua i passi correttamente. |

### 🟠 Importanti

| ID | Criticità | Dettaglio |
|----|-----------|-----------|
| **C4** | **Nessun test regressione bug fix** | I 10 bug fix in §7 non hanno test. Un refactoring futuro può reintrodurli. |
| **C5** | **Error handling asimmetrico** | Alcuni tool hanno try/except (es. search_memory con FTS5 fallback), altri no (update_memory, link_memories). |
| **C6** | **FastMCP API fragile** | `streamable_http_app()` e `ArgModelBase` non sono API stabili. Una minor release di FastMCP può rompere tutto. |
| **C7** | **Output solo testo** | Tutti i 46 tool ritornano `str`. Impossibile per client MCP fare parsing strutturato senza regex. |

### 🟡 Minori

| ID | Criticità | Dettaglio |
|----|-----------|-----------|
| **C8** | **Secret scanner assente in db.py** | `_strip_private()` solo in server.py. Chiamate dirette a db.py bypassano la protezione. |
| **C9** | **Nessuna CI Windows/macOS** | badge test.yml presente, ma non è chiaro se testa su piattaforme non-Linux. |
| **C10** | **Dimensione WAL** | `_CHECKPOINT_EVERY = 100` è probabilmente troppo basso per sessioni lunghe con molte scritture. |

---

## 4. Piano 11 Microfasi

### MF-0 — Fondamenta (30 min)
- Test di regressione per bug fix §7.8, 7.9, 7.10
- `make test-regression` in pyproject.toml

### MF-1 — Refactoring Tools Modulari (2 sessioni)
- Creare `tools/` con moduli: `core.py`, `graph.py`, `admin.py`, `lifecycle.py`, `procedures.py`, `batch.py`, `observability.py`
- `server.py` ridotto a ~50 righe (bootstrap + health + metrics)

### MF-2 — Error Handling Uniforme (45 min)
- Eccezioni custom in `errors.py`
- Decoratore `@handle_errors` per tutti i tool

### MF-3 — Output Strutturato (1 sessione)
- Parametro `format: str = "text"` su tutti i tool
- Modalità `"json"` e `"table"` oltre al default `"text"`

### MF-4 — Secret Scanner Doppio Layer (45 min)
- Spostare `_strip_private()` in `db.py`
- Applicare in `remember()` e `update_memory()` lato DB
- Mantenere anche in server.py per defense-in-depth

### MF-5 — Automation Robustness (1 sessione)
- Documentare in ARCHITECTURE.md il limite delle automations prompt-based
- Fallback espliciti nei prompt per errori MCP

### MF-6 — FastMCP Compat (45 min)
- Pinning `fastmcp>=1.26.0,<1.30.0`
- Test che verifica API `streamable_http_app()` e `ArgModelBase`

### MF-7 — Thread Safety SQLite (1 sessione)
- `ThreadLocal()` al posto di `_conn` globale
- `PRAGMA busy_timeout=5000`
- Test concorrenza con 10 chiamate parallele

### MF-8 — CI Multi-Platform (30 min)
- Matrix: `[ubuntu-latest, windows-latest, macos-latest]`
- Test avvio server HTTP + `/health`

### MF-9 — Self-Healing Server (1 sessione)
- Flag `--recover` per backup e ricreazione DB corrotto
- `GET /health?probe=1` con HTTP 503 su errore DB

### MF-10 — Skill Session-Manager (1 sessione)
- Skill che centralizza il protocollo sessionale
- `requiredSources: [memory]`

### Grafo Dipendenze

```
MF-0 ──→ MF-1 ──→ MF-2 ──→ MF-3 ──→ MF-10
  │        │
  │        ├──→ MF-4
  │        ├──→ MF-5
  │        ├──→ MF-6
  │        ├──→ MF-7 ──→ MF-9
  │        └──→ MF-8
```

**Indipendenti**: MF-4, MF-5, MF-6, MF-8 (paralleli)
**Sequenziali**: MF-1 → MF-2 → MF-3 → MF-10
**Stima totale**: 8-10 sessioni

---

## 5. Punti di Forza

- **Architettura pulita**: server/db/schema ben separati, migration runner, 12 migrazioni versionate
- **Stabilità**: stateless_http, auto-reconnect, WAL checkpoint, double-layer privacy stripping
- **Ricchezza funzionale**: 46 tool con RRF hybrid search, knowledge graph, procedural memory, SessionDB
- **Testing**: 209 pytest coprono tutti gli sprint
- **Documentazione**: ARCHITECTURE.md di ~500 righe, 8 ADR, guide.md per il source
- **Cross-platform**: `start-http.bat` + `start-memory.sh` + `ensure-running.py` con DETACHED_PROCESS
- **CI/CD**: release-please per versionamento automatico semver
- **PyPI**: `craft-memory-mcp` installabile via pip

---

## 6. Metriche

| Metrica | Valore |
|---------|--------|
| MCP Tools | 46 (baseline 19 + 27 sprint 1-10) |
| Migrazioni SQL | 12 (v1 + 002→012) |
| Test | 209 pytest |
| Skills | 4 |
| Automations | 4 |
| ADR | 8 |
| Bug fix documentati | 10 |
| Directory struttura | ~20 cartelle |

---

## 7. Riconciliazione Reviewer

| Osservazione | Risposta |
|---|---|
| `$CLAUDE_SESSION_ID` non documentata | Il repo usa `CRAFT_SESSION_ID`/`CRAFT_WORKSPACE_ID`, già in ARCHITECTURE.md |
| Formato hook `matcher` mancante | `LabelAdd` ha `matcher`, SessionStart/End sono event-driven (Craft Agents) |
| `Notification` come trigger periodico | Non usato. SchedulerTick con `cron` è il meccanismo corretto. |
| Controllo processo fragile | Il server MCP è processo Python separato, non claude. OK. |
| Compatibilità Windows | Già gestita: `.bat` + `.sh` + `ensure-running.py` cross-platform |
| Integrazione con craft-memory | Già implementata: ogni tool accetta `source_session` |
