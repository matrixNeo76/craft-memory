# Craft Memory System — Documentazione Architetturale Completa

> **Data**: 2026-04-30  
> **Versione**: 3.0 (Phase 10 — 17 tools, knowledge graph layer, confidence labels, god_facts, memory_diff)  
> **Ambiente**: Windows 11, Craft Agents (pi), Python 3.12

---

## Indice

1. [Panoramica del Sistema](#1-panoramica-del-sistema)
2. [Architettura](#2-architettura)
3. [Componenti Server MCP](#3-componenti-server-mcp)
4. [Configurazione Craft Agents](#4-configurazione-craft-agents)
5. [Automazioni](#5-automazioni)
6. [Skills](#6-skills)
7. [Problemi Risolti e Fix Applicati](#7-problemi-risolti-e-fix-applicati)
8. [Guida al Deployment su Nuova Installazione](#8-guida-al-deployment-su-nuova-installazione)
9. [Analisi di Riutilizzabilità per Craft Agents](#9-analisi-di-riutilizzabilità-per-craft-agents)

---

## 1. Panoramica del Sistema

Craft Memory è un sistema di memoria persistente cross-sessione per Craft Agents (pi). Permette all'agente AI di salvare e recuperare contesto tra sessioni diverse, anche cambiando modello o provider.

**Cosa risolve**: Senza memoria, ogni sessione di pi inizia da zero — nessuna memoria di decisioni prese, bug fixati, o conoscenza acquisita. Craft Memory dà a pi una memoria a lungo termine locale.

**Stack tecnologico**:

| Componente | Tecnologia |
|------------|------------|
| MCP Server | FastMCP 1.26.0 (Python) |
| Storage | SQLite 3 + FTS5 (full-text search) |
| Transport | HTTP (Streamable HTTP su localhost) |
| Runtime | Python 3.12, uvicorn |

---

## 2. Architettura

```
┌─────────────────────────────────────────────────────────┐
│                    Craft Agents (pi)                     │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────┐  │
│  │ Session  │  │ Session  │  │ Scheduler │  │ Label  │  │
│  │  Start   │  │   End    │  │   Tick    │  │  Add   │  │
│  │ Auto     │  │ Auto     │  │  Auto     │  │ Auto   │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └───┬────┘  │
│       │              │              │              │       │
│       ▼              ▼              ▼              ▼       │
│  ┌──────────────────────────────────────────────────┐    │
│  │            Memory Source (MCP/HTTP)              │    │
│  │         localhost:8392/mcp (Streamable HTTP)      │    │
│  └──────────────────────┬───────────────────────────┘    │
│                         │ HTTP                           │
└─────────────────────────┼────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────┐
│              Craft Memory Server (Python)                 │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │   server.py  │  │    db.py      │  │  schema.sql   │  │
│  │  (FastMCP)   │  │  (SQLite)    │  │   (Schema)    │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────────┘  │
│         │                  │                              │
│         ▼                  ▼                              │
│  ┌──────────────────────────────────────────────────┐    │
│  │     ~/.craft-agent/memory/{workspaceId}.db       │    │
│  │     (SQLite + WAL + FTS5)                        │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

**Flusso dati**:

1. **Sessione inizia** → automazione SessionStart chiama `ensure-running.py` (avvia server se down) → chiama `get_recent_memory` + `list_open_loops`
2. **Durante lavoro** → l'agente chiama `remember` / `upsert_fact` / `search_memory` secondo necessità
3. **Sessione finisce** → automazione SessionEnd chiama `remember` per decisioni + `summarize_scope` per handoff
4. **Ogni notte 3:00** → automazione SchedulerTick chiama `ensure-running.py` + manutenzione (consolidamento, promozione facts, loop stale)

---

## 3. Componenti Server MCP

### 3.1 File: `src/server.py`

Server MCP con FastMCP. Punti chiave:

**Patch Pydantic (righe 20-28)**:
```python
from mcp.server.fastmcp.utilities.func_metadata import ArgModelBase
ArgModelBase.model_config["extra"] = "ignore"
```
Craft Agents inietta parametri interni (`_displayName`, `_intent`) nelle chiamate MCP. Senza questo patch, Pydantic li rifiuta con errore di validazione. Il patch `extra="ignore"` scarta i campi extra silenziosamente — una riga, funziona per tutti i tool.

**FastMCP con stateless HTTP (righe 75-77)**:
```python
mcp = FastMCP(
    "craft-memory",
    stateless_http=True,   # ← FIX CRITICO: evita "Session not found" dopo restart
    json_response=True,    # ← FIX: risposte JSON invece di SSE stream
    instructions="..."
)
```
Senza `stateless_http=True`, il server crea sessioni stateful. Dopo un restart del processo, i client con session ID scaduti ricevono "Session not found". Con `stateless_http=True` ogni richiesta è indipendente.

**Dual transport (entry point)**:
```python
if MCP_TRANSPORT == "http":
    import uvicorn
    app = mcp.streamable_http_app()  # ← Non http_app() (non esiste in 1.26.0)
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
else:
    mcp.run(transport="stdio")
```
**ATTENZIONE**: `http_app(stateless_http=True)` esisteva in versioni precedenti di FastMCP ma **non esiste più in 1.26.0**. L'API corretta è `streamable_http_app()`, combinata con `stateless_http=True` nel costruttore FastMCP.

**Health check endpoint** (`/health`):
- Verifica connessione DB con `SELECT 1`
- Ritorna `db_size_mb` e `db_size_warning` (>100 MB)
- `version` letta da `importlib.metadata` (non hardcoded — si aggiorna con release-please)

**WAL checkpoint automatico**:
```python
_write_count += 1
if _write_count >= 100:
    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
```
Ogni 100 write per tenere il file WAL bounded senza bloccare i reader.

**Auto-reconnect** su connessione stale:
```python
def _get_conn():
    if _conn is not None:
        try: _conn.execute("SELECT 1")
        except: _conn = None
    if _conn is None:
        _conn = _db_get_connection(...)
        _db_register_session(...)
```

**Privacy stripping** prima di ogni `remember` e `update_memory`:
```python
_PRIVATE_PATTERNS = _re.compile(
    r"<(private|system-reminder|system-instruction|system)>.*?</\1>",
    _re.DOTALL | _re.IGNORECASE,
)
```

**17 tool esposti**:

| Tool | Scopo | Lettura/Scrittura |
|------|-------|-------------------|
| `remember` | Salva memoria episodica (con privacy stripping e tags) | Scrittura |
| `update_memory` | Aggiorna content/category/importance di una memoria esistente | Scrittura |
| `search_memory` | Ricerca FTS5 + BM25 hybrid ranking; LIKE fallback sicuro | Lettura |
| `search_by_tag` | Filtra memorie per tag | Lettura |
| `get_recent_memory` | Memorie ranked per importance decay; supporta token budget | Lettura |
| `upsert_fact` | Salva/aggiorna fact stabile con confidence score e `confidence_type` | Scrittura |
| `list_open_loops` | Lista loop aperti per priorità | Lettura |
| `add_open_loop` | Crea nuovo loop cross-session | Scrittura |
| `close_open_loop` | Chiude un loop con risoluzione opzionale | Scrittura |
| `summarize_scope` | Snapshot completo: memorie (decay-ranked) + facts + loops | Lettura |
| `save_summary` | Salva documento di handoff strutturato (decisions, facts, next_steps) | Scrittura |
| `run_maintenance` | Cleanup old memories, trim summaries, dedup, VACUUM | Scrittura |
| `link_memories` | Crea arco diretto nel knowledge graph tra due memorie | Scrittura |
| `get_relations` | Restituisce tutti i vicini (in/out/both) di una memoria nel grafo | Lettura |
| `find_similar` | FTS5 BM25 similarity search; opzione `auto_link` per creare archi INFERRED | Lettura |
| `god_facts` | Top N fact per impatto: `confidence × type_bonus × (1 + mention_count × 0.2)` | Lettura |
| `memory_diff` | Delta dal timestamp epoch: nuove memorie, fact aggiornati, loop aperti/chiusi | Lettura |

### 3.2 File: `src/db.py`

Layer dati SQLite. Funzioni principali:

**Infrastruttura**:
- `run_migrations(conn)` → applica `schema.sql` come v1 poi `migrations/NNN_*.sql` in ordine; usa tabella `schema_version` come tracker
- `init_db(db_path)` → connessione WAL + esegue migrazioni; FK off durante migrazioni, on dopo
- `_effective_importance(importance, created_at_epoch)` → `importance × e^(-λ × age_days)` con λ da `CRAFT_MEMORY_DECAY_LAMBDA` (default 0.005)

**Memories**:
- `remember(...)` → INSERT con dedup globale `UNIQUE(workspace_id, content_hash)` — un contenuto per workspace, indipendente dalla sessione; supporta `tags` (JSON array)
- `search_memory(query, ...)` → FTS5 + BM25×0.7 + importance×0.3; fallback LIKE con parametri corretti (bug scope binding fixato)
- `get_recent_memory(...)` → pool × 5, re-rank per decay; `max_tokens` tronca al budget
- `update_memory(id, workspace_id, ...)` → aggiorna content/category/importance; ricalcola content_hash se content cambia
- `search_by_tag(tag, ...)` → LIKE `%"tag"%` sul campo JSON tags

**Facts / Open Loops**:
- `upsert_fact(...)` → `ON CONFLICT DO UPDATE` su `UNIQUE(key, workspace_id, scope)`; accetta `confidence_type: str = "extracted"` (`extracted | inferred | ambiguous`)
- `create_open_loop(...)` / `list_open_loops(...)` / `close_open_loop(...)`

**Knowledge Graph Layer** (Phase 10):
- `_content_hash(content, kind)` → SHA256 full (non troncato) + kind namespace (`"\x00{kind}"`) per evitare collisioni cross-entità
- `link_memories(conn, source_id, target_id, relation, workspace_id, confidence_type, confidence_score)` → inserisce arco diretto in `memory_relations`; `UNIQUE(source_id, target_id, relation)` per idempotenza; ritorna row id o None se duplicato/relazione invalida. Relazioni ammesse: `caused_by | contradicts | extends | implements | supersedes | semantically_similar_to`
- `get_relations(conn, memory_id, workspace_id, direction="both")` → restituisce vicini con label direzione (`"in"` / `"out"`); JOIN con `memories` per content preview
- `find_similar_memories(conn, memory_id, workspace_id, top_n=5, auto_link=False)` → estrae content della memoria, sanifica le parole (`re.sub(r"[^a-zA-Z0-9]", "", w)` per evitare errori FTS5 da trattini/punteggiatura), costruisce `"word1 OR word2 OR ..."`, esegue FTS5 BM25 search escludendo la memoria sorgente; se `auto_link=True` e BM25 score < -1.5, crea arco `semantically_similar_to` con `confidence_type="inferred"`
- `god_facts(conn, workspace_id, top_n=10)` → score = `confidence × type_bonus × (1 + mention_count × 0.2)`; `type_bonus`: extracted=1.0, inferred=0.8, ambiguous=0.5; ordina DESC, ritorna con campo `god_score`
- `memory_diff(conn, workspace_id, since_epoch)` → ritorna `{new_memories: [...], updated_facts: [...], opened_loops: [...], closed_loops: [...]}` comparando `created_at_epoch` / `updated_at` (come ISO string) rispetto all'epoch fornito

**Summaries**:
- `save_summary(...)` → documento di handoff strutturato (decisions, facts_learned, open_loops, refs, next_steps)
- `summarize_scope(...)` → usa decay ranking per recent memories (allineato a `get_recent_memory`)

**Manutenzione**:
- `daily_maintenance(...)` → `delete_old_memories` + `mark_stale_loops` + `trim_session_summaries` + `dedup_memories` + `VACUUM`
- `trim_session_summaries(conn, workspace_id, keep_last=20)`

### 3.3 File: `src/schema.sql` + `src/migrations/`

Schema base (v1) + migrazioni versionate:

| Tabella | Scopo |
|---------|-------|
| `sessions` | Tracking sessioni (craft_session_id, model, status) |
| `memories` | Memorie episodiche con category, importance, scope, tags, dedup hash |
| `memories_fts` | Indice FTS5 con porter stemmer + unicode61; category/scope UNINDEXED |
| `facts` | Knowledge stabile (UNIQUE key+workspace+scope) con confidence score |
| `open_loops` | Task incompleti con priorità e status |
| `session_summaries` | Documenti di handoff strutturati tra sessioni |
| `schema_version` | Tracker versioni per migration runner |

**Migrazioni applicate**:
- `001_global_dedup.sql`: cambia UNIQUE da `(session_id, content_hash)` a `(workspace_id, content_hash)`; ricrea FTS5 con category/scope UNINDEXED
- `002_global_dedup.sql`: stessa logica (numerazione dipende da ordine applicazione)
- `003_tags.sql`: aggiunge colonna `tags TEXT` a `memories` + index
- `004_relations.sql`: aggiunge `confidence_type TEXT DEFAULT 'extracted' CHECK(...)` a `facts`; crea tabella `memory_relations` con 5 indici (source_id, target_id, workspace_id, confidence_type, relation); FK CASCADE su `memories(id)`

**Tabella `memory_relations`** (introdotta in v3.0):

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | INTEGER PK | Autoincrement |
| `source_id` | INTEGER FK | → `memories(id)` CASCADE DELETE |
| `target_id` | INTEGER FK | → `memories(id)` CASCADE DELETE |
| `relation` | TEXT | `caused_by | contradicts | extends | implements | supersedes | semantically_similar_to` |
| `confidence_type` | TEXT | `extracted | inferred | ambiguous` |
| `confidence_score` | REAL | 0.0–1.0 |
| `workspace_id` | TEXT | Isolamento per workspace |
| `created_at_epoch` | INTEGER | Unix timestamp creazione |

Il migration runner in `db.py:run_migrations()` controlla `MAX(version)` dalla tabella `schema_version` e applica solo le migrazioni pending.

### 3.4 File: `scripts/ensure-running.py`

Script di lifecycle management — check, start, stop del server HTTP.

```
python ensure-running.py          # Check + auto-start se down
python ensure-running.py --check  # Solo check (exit code 0=up, 2=down)
python ensure-running.py --stop   # Stop processo sulla porta
```

**Meccanismo di avvio**: Usa `subprocess.DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` su Windows per staccare il processo dal terminale. Il server continua a girare dopo la chiusura della shell.

**Health check**: Fa `GET /health` con urllib (nessuna dipendenza esterna). Attende fino a 10 secondi per il readiness.

**Stop**: Su Windows usa `netstat -aon` per trovare il PID sulla porta, poi `taskkill /F /PID`.

---

## 4. Configurazione Craft Agents

### 4.1 Source: `sources/memory/config.json`

```json
{
  "id": "memory_e4c7a2b9",
  "name": "Craft Memory",
  "slug": "memory",
  "enabled": true,
  "provider": "craft-memory",
  "type": "mcp",
  "icon": "🧠",
  "tagline": "Persistent cross-session memory with SQLite + FTS5",
  "mcp": {
    "transport": "http",
    "url": "http://localhost:8392/mcp",
    "authType": "none"
  }
}
```

**Nota critica**: `transport: "http"` è necessario su Windows dove stdio ha il bug "Not connected". Su Linux/macOS, `transport: "stdio"` funzionerebbe, ma HTTP è più robusto perché il server resta sempre vivo.

### 4.2 Source: `sources/memory/permissions.json`

```json
{
  "allowedMcpPatterns": [
    { "pattern": "remember", "comment": "Store episodic memories" },
    { "pattern": "update_memory", "comment": "Update existing memory" },
    { "pattern": "search_memory", "comment": "Search memories via FTS5" },
    { "pattern": "search_by_tag", "comment": "Search memories by tag" },
    { "pattern": "get_recent_memory", "comment": "Get recent memories (decay-ranked)" },
    { "pattern": "upsert_fact", "comment": "Store/update stable facts" },
    { "pattern": "list_open_loops", "comment": "List open loops" },
    { "pattern": "add_open_loop", "comment": "Create new open loop" },
    { "pattern": "close_open_loop", "comment": "Close open loops" },
    { "pattern": "summarize_scope", "comment": "Generate scope summary" },
    { "pattern": "save_summary", "comment": "Save structured session handoff" },
    { "pattern": "run_maintenance", "comment": "Database maintenance" },
    { "pattern": "link_memories", "comment": "Create knowledge graph edge" },
    { "pattern": "get_relations", "comment": "Get graph neighbors of a memory" },
    { "pattern": "find_similar", "comment": "FTS5 BM25 similarity search" },
    { "pattern": "god_facts", "comment": "Top facts by impact score" },
    { "pattern": "memory_diff", "comment": "Delta since epoch timestamp" }
  ]
}
```

Questi pattern permettono a tutti i 17 tool di funzionare anche in modalità Explore (safe). I pattern sono scope-ati automaticamente al source slug `memory`.

### 4.3 Workspace: `config.json`

```json
{
  "defaults": {
    "enabledSourceSlugs": ["memory", "claude-mem"],
    "permissionMode": "safe"
  }
}
```

**Importante**: `"memory"` DEVE essere in `enabledSourceSlugs`, altrimenti i tool non sono disponibili nelle nuove sessioni.

### 4.4 Permessi bash: `permissions/default.json`

Aggiunto pattern per permettere `ensure-running.py` anche in modalità safe:

```json
{
  "pattern": "^python\\b.*ensure-running\\.py\\b",
  "comment": "Craft Memory server lifecycle: check, start, stop"
}
```

---

## 5. Automazioni

4 automazioni configurate in `automations.json`:

### 5.1 SessionStart — "Memory: Recover Session Context"

**Evento**: Sessione inizia  
**Permission**: `allow-all` (necessario per eseguire tool MCP senza approvazione manuale)

**Step**:
1. Esegue `python ensure-running.py` → avvia il server se down
2. Chiama `get_recent_memory(scope='workspace', limit=10)`
3. Chiama `list_open_loops()`
4. Riassume contesto per l'utente

**Perché allow-all**: In modalità safe, ogni tool call MCP richiederebbe approvazione manuale dell'utente. Per un'automazione di session start questo è insostenibile.

### 5.2 SessionEnd — "Memory: Save Session Handoff"

**Evento**: Sessione finisce  
**Permission**: `allow-all`

**Step**:
1. Chiama `remember(category='decision', importance=8)` per decisioni chiave
2. Chiama `remember(category='discovery', importance=7)` per scoperte
3. Chiama `upsert_fact()` per conoscenza stabile confermata
4. Chiama `close_open_loop()` per loop risolti
5. Chiama `summarize_scope()` per snapshot finale
6. Presenta handoff compatto all'utente

### 5.3 SchedulerTick — "Memory: Daily Maintenance"

**Evento**: Cron `0 3 * * *` (ogni notte alle 3:00, timezone Europe/Rome)  
**Permission**: `allow-all`  
**Labels**: `scheduled`, `memory-maintenance`

**Step**:
1. Esegue `ensure-running.py` (auto-start se server down)
2. Chiama `summarize_scope()` per review stato
3. Cerca memorie consolidabili
4. Identifica facts da promuovere da memorie
5. Controlla loop stale (>30 giorni)
6. Presenta report manutenzione

### 5.4 LabelAdd — "Memory: Promote Important/Fact-Candidate Labels"

**Evento**: Label `important` o `fact-candidate` aggiunta  
**Matcher**: `^(important|fact-candidate)$`  
**Permission**: `allow-all`

**Variabile**: `$CRAFT_LABEL` contiene il nome della label aggiunta (documentata nelle automazioni Craft Agents)

**Comportamento**:
- Label `important` → `remember(importance=9)` per i key takeaways
- Label `fact-candidate` → `upsert_fact()` per conoscenza stabile

---

## 6. Skills

4 skill nella cartella `skills/`:

| Skill | Scopo | Trigger |
|-------|-------|---------|
| `memory-start` | Avviare/verificare il server HTTP | "start memory", "check memory", "memory status", o quando i tool falliscono |
| `memory-protocol` | Protocollo obbligatorio per leggere/scrivere memoria | Inizio sessione, quando serve memoria |
| `memory-maintenance` | Deduplicazione, consolidamento, cleanup | Manutenzione periodica, on demand |
| `session-handoff` | Creare documento di handoff per prossima sessione | Fine sessione, cambio modello |

Tutti dichiarano `requiredSources: [memory]` nel frontmatter YAML.

---

## 7. Problemi Risolti e Fix Applicati

### 7.1 Bug Windows stdio → HTTP transport

| | Dettaglio |
|---|---|
| **Problema** | Su Windows, il transport stdio di MCP si disconnette dopo ~4 secondi. Tool calls successivi falliscono con "Not connected". |
| **Root cause** | Bug noto in MCP SDK su Windows: il pipe stdin si chiude prematuramente. |
| **Fix** | Migrato a HTTP transport (localhost:8392/mcp). Il server resta sempre vivo come processo HTTP. |
| **Riferimenti** | [openclaw#65520](https://github.com/openclaw/openclaw/issues/65520), [copilot-cli#2892](https://github.com/github/copilot-cli/issues/2892) |

### 7.2 FastMCP API errata: http_app() → streamable_http_app()

| | Dettaglio |
|---|---|
| **Problema** | `AttributeError: 'FastMCP' object has no attribute 'http_app'` |
| **Root cause** | FastMCP 1.26.0 ha rimosso `http_app()`. L'API corretta è `streamable_http_app()`. |
| **Fix** | Sostituito `mcp.http_app(stateless_http=True)` con `mcp.streamable_http_app()` + `stateless_http=True` nel costruttore. |

### 7.3 "Session not found" dopo restart server

| | Dettaglio |
|---|---|
| **Problema** | Dopo restart del processo server, i tool falliscono con `{"error":{"code":-32600,"message":"Session not found"}}` |
| **Root cause** | `streamable_http_app()` crea sessioni stateful di default. I client con session ID scaduti vengono rifiutati. |
| **Fix** | Aggiunto `stateless_http=True` e `json_response=True` nel costruttore `FastMCP()`. Ogni richiesta è indipendente, nessun session state. |

### 7.4 Pydantic validation error su parametri framework

| | Dettaglio |
|---|---|
| **Problema** | Craft Agents inietta `_displayName`, `_intent` nei tool call MCP. Pydantic li rifiuta come campi sconosciuti. |
| **Fix** | `ArgModelBase.model_config["extra"] = "ignore"` — una riga, scarta tutti i campi extra silenziosamente. |

### 7.5 enabledSourceSlugs mancante

| | Dettaglio |
|---|---|
| **Problema** | `"memory"` non era in `enabledSourceSlugs` del workspace config. I tool non erano disponibili nelle nuove sessioni. |
| **Fix** | Aggiunto `"memory"` a `enabledSourceSlugs`. |

### 7.6 Automazioni senza permissionMode

| | Dettaglio |
|---|---|
| **Problema** | Tutte e 4 le automazioni ereditavano `permissionMode: "safe"` dal workspace default. In safe mode, ogni tool call richiede approvazione manuale — inutile per automazioni. |
| **Fix** | Aggiunto `"permissionMode": "allow-all"` a tutte e 4 le automazioni. |

### 7.7 Automazione SessionStart senza auto-start server

| | Dettaglio |
|---|---|
| **Problema** | Se il server HTTP non è avviato, l'automazione SessionStart fallisce silenziosamente. |
| **Fix** | Aggiunto Step 1 in SessionStart e SchedulerTick: esegui `ensure-running.py` prima di qualsiasi tool call. |

### 7.9 search_memory() scope binding errato nel LIKE fallback

| | Dettaglio |
|---|---|
| **Problema** | Quando `scope` era impostato e la query FTS5 falliva (fallback LIKE), i risultati erano completamente sbagliati senza errori. |
| **Root cause** | `params = [workspace_id, scope]` per il path FTS5. Nel fallback LIKE la query si aspetta `[workspace_id, like_pattern, like_pattern, scope]`, ma veniva passato `params + [like_pattern, like_pattern]` = `[workspace_id, scope, like_pattern, like_pattern]` → `scope` finiva nel placeholder di `content LIKE ?`. |
| **Fix** | Costruire `like_params` separato: `[workspace_id, like_pattern, like_pattern]` + `scope` opzionale in coda. |
| **File** | `src/craft_memory_mcp/db.py` funzione `search_memory()`. |
| **Rilevato** | Phase 9 (2026-04-30) durante analisi critica pre-community proposal. |

### 7.8 remember() non salva nulla — violazione FK silenziosa

| | Dettaglio |
|---|---|
| **Problema** | `remember()` restituiva "Duplicate memory skipped" su ogni chiamata. `memories COUNT` rimaneva 0 nonostante il server fosse healthy. |
| **Root cause** | `register_session()` non veniva mai chiamata → tabella `sessions` vuota → `memories` ha `FOREIGN KEY(session_id) REFERENCES sessions(craft_session_id)` → `INSERT OR IGNORE` scarta silenziosamente la violazione FK riportandola come duplicato. |
| **Prova** | `facts = 13` (funzionano, nessun FK), `sessions = 0`, `memories = 0`. |
| **Fix** | Aggiunto auto-call `_db_register_session(conn, CRAFT_SESSION_ID, WORKSPACE_ID)` in `_get_conn()`, subito dopo la creazione della connessione. `register_session` usa `INSERT OR IGNORE` → idempotente. |
| **File modificati** | `src/server.py` riga 122, `src/craft_memory_mcp/server.py` riga 131. |
| **Verificato** | 2026-04-29: `memories COUNT` passa da 0 a 1 dopo la prima chiamata `remember()`. |

---

## 8. Guida al Deployment su Nuova Installazione

### Prerequisiti

- Python 3.11+ con pip
- Craft Agents (pi) installato
- SQLite 3 con supporto FTS5 (incluso in Python stdlib)

### Step 1: Installa il server

```bash
# Clona o copia la cartella craft-memory
cp -r craft-memory/ ~/craft-memory/

# Installa dipendenze
pip install fastmcp uvicorn
```

### Step 2: Test avvio

```bash
# Test stdio (per verificare che il server funziona)
cd ~/craft-memory/src
python server.py

# Test HTTP (default dal v2.0)
CRAFT_MEMORY_TRANSPORT=http CRAFT_MEMORY_PORT=8392 python server.py
# Verifica: curl http://localhost:8392/health
```

### Step 3: Configura Craft Agents source

Crea la cartella source nel workspace:

```bash
mkdir -p ~/.craft-agent/workspaces/{WS_ID}/sources/memory/
```

Crea `config.json`:

```json
{
  "id": "memory_{random8hex}",
  "name": "Craft Memory",
  "slug": "memory",
  "enabled": true,
  "provider": "craft-memory",
  "type": "mcp",
  "icon": "🧠",
  "tagline": "Persistent cross-session memory with SQLite + FTS5",
  "mcp": {
    "transport": "http",
    "url": "http://localhost:8392/mcp",
    "authType": "none"
  },
  "createdAt": TIMESTAMP_MS,
  "updatedAt": TIMESTAMP_MS
}
```

Crea `permissions.json`:

```json
{
  "allowedMcpPatterns": [
    { "pattern": "remember", "comment": "Store episodic memories" },
    { "pattern": "update_memory", "comment": "Update existing memory" },
    { "pattern": "search_memory", "comment": "Search memories via FTS5" },
    { "pattern": "search_by_tag", "comment": "Search memories by tag" },
    { "pattern": "get_recent_memory", "comment": "Get recent memories" },
    { "pattern": "upsert_fact", "comment": "Store/update stable facts" },
    { "pattern": "list_open_loops", "comment": "List open loops" },
    { "pattern": "add_open_loop", "comment": "Create new open loop" },
    { "pattern": "close_open_loop", "comment": "Close open loops" },
    { "pattern": "summarize_scope", "comment": "Generate scope summary" },
    { "pattern": "save_summary", "comment": "Save structured session handoff" },
    { "pattern": "run_maintenance", "comment": "Database maintenance" }
  ]
}
```

Crea `guide.md` (adatta al tuo contesto linguistico).

### Step 4: Abilita il source nel workspace

In `~/.craft-agent/workspaces/{WS_ID}/config.json`, aggiungi `"memory"` a `enabledSourceSlugs`:

```json
"enabledSourceSlugs": ["memory"]
```

### Step 5: Configura automazioni

Copia `automations.json` nel workspace, adattando:
- I path di `ensure-running.py` al tuo sistema
- Il timezone in SchedulerTick
- I path di Python in `start-http.bat` (se usi Windows)

### Step 6: Copia le skills

```bash
cp -r skills/memory-* skills/session-handoff ~/.craft-agent/workspaces/{WS_ID}/skills/
```

### Step 7: Aggiungi permesso bash per ensure-running.py

In `permissions/default.json`:

```json
{ "pattern": "^python\\b.*ensure-running\\.py\\b", "comment": "Craft Memory server lifecycle" }
```

### Step 8: Valida e testa

```bash
craft-agent source test memory
craft-agent automation validate
```

### Step 9: Avvia il server

```bash
python ~/craft-memory/scripts/ensure-running.py
```

D'ora in poi, l'automazione SessionStart lo farà automaticamente.

---

## 9. Analisi di Riutilizzabilità per Craft Agents

### 9.1 La metodologia è riutilizzabile?

**Sì**, con alcune precisazioni. Il sistema si decompone in tre layer riutilizzabili a livelli diversi:

| Layer | Riutilizzabile? | Come |
|-------|----------------|------|
| **MCP Server** (`server.py` + `db.py` + `schema.sql`) | ✅ Completamente | È un MCP server generico. Funziona con qualsiasi client MCP, non solo Craft Agents. Può essere pubblicato come pacchetto PyPI. |
| **Configurazione Craft Agents** (source + automazioni + skills) | ✅ Completamente | I file config.json, automations.json, permissions.json e SKILL.md sono template portabili. Basta adattare path e slug. |
| **Script lifecycle** (`ensure-running.py` + `start-http.bat`) | ⚠️ Parzialmente | `ensure-running.py` è generico (usa solo Python stdlib). `start-http.bat` è Windows-specific. Su macOS/Linux servirebbe uno script `.sh` equivalente. |

### 9.2 È proponibile sul GitHub ufficiale di Craft Agents?

**Sì, ma non come singola PR — meglio come proposta strutturata.** Ecco perché e come:

#### Cosa rende questa implementazione interessante per Craft Agents

1. **Risolve un bug reale**: Lo stdio transport su Windows è broken. La nostra soluzione HTTP è il workaround ufficiale documentato.

2. **Pattern architetturale**: È il primo esempio completo di:
   - MCP source HTTP con health check
   - Automazioni che gestiscono il lifecycle di un source (auto-start)
   - Sistema memoria cross-sessione con skills e protocolli strutturati
   - Permessi MCP scope-ati per funzionare in Explore mode

3. **Il pattern `ensure-running.py`** è generalizzabile: qualsiasi MCP source HTTP può usarlo per auto-start. Non è specifico della memoria.

#### Come proporlo

Il formato migliore è un **Craft Agents Source Template** — un pacchetto installabile con `craft-agent source add memory` che:

1. Crea automaticamente `config.json`, `permissions.json`, `guide.md`
2. Installa le skills nel workspace
3. Configura le automazioni
4. Avvia il server

Questo è esattamente il modello usato dai source ufficiali (GitHub, Linear, Slack).

#### Cosa richiede adjustments per essere generico

| Aspetto | Stato attuale | Cosa serve per essere generico |
|---------|--------------|-------------------------------|
| Path hardcoded | `C:\Users\auresystem\craft-memory\...` | Usare `~/.craft-agent/memory/` come base, o path configurabile |
| Workspace ID | `ws_ecad0f3d` | Rilevato automaticamente da `$CRAFT_WORKSPACE_ID` |
| Python path | Hardcoded in `.bat` | Usare `sys.executable` o `which python3` |
| Lingua guide | Italiano | Inglese (o multilingua con i18n) |
| Windows-only `.bat` | Solo `.bat` | Aggiungere `.sh` per macOS/Linux |
| `pyproject.toml` | Dipendenze minime | Aggiungere `[project.scripts]` entry point |

#### Valutazione di fattibilità (aggiornata post-Phase 9)

| Criterio | Voto | Note |
|----------|------|------|
| **Utilità per la community** | ⭐⭐⭐⭐⭐ | Memoria cross-sessione richiesta da molti; tre-tier model unico nel panorama MCP |
| **Complessità di integrazione** | ⭐⭐⭐ | Richiede MCP server esterno — non "zero config", ma `craft-memory install` automatizza tutto |
| **Stabilità** | ⭐⭐⭐⭐⭐ | HTTP + stateless + health check + auto-reconnect + WAL checkpoint = produzione-ready |
| **Differenziazione vs claude-mem** | ⭐⭐⭐⭐⭐ | Design opposto e complementare: esplicito vs passivo; decay + open loops + facts unici |
| **Generalizzabilità** | ⭐⭐⭐⭐ | Server MCP generico; automazioni/skills portabili con piccoli adattamenti |
| **Manutenibilità** | ⭐⭐⭐⭐ | Migration runner + release-please + CI tests; versioning semver automatico |
| **Privacy/sicurezza** | ⭐⭐⭐⭐⭐ | Privacy stripping, nessuna dipendenza esterna, zero cloud, dati locali |

### 9.3 Raccomandazione

**Proponi come source community** su Craft Agents GitHub, seguendo questo formato:

1. **Repository separato**: `craft-agents/craft-memory-source` (non nel monorepo principale)
2. **Installazione via CLI**: `craft-agent source add memory` → scarica e configura tutto
3. **Cross-platform**: Aggiungere script di avvio per macOS/Linux
4. **Documentazione inglese**: Guide, README, e skills in inglese
5. **Test CI**: Test automatici per il server MCP su Windows, macOS, Linux
6. **Versioning semver**: Per gestire breaking changes nell'API FastMCP

Il valore principale **non è solo il server MCP** — è il **pattern completo** di:
- MCP source HTTP con lifecycle management
- Automazioni che garantiscono la disponibilità del source
- Skills che insegnano all'agente come usare la memoria
- Protocollo strutturato (session start → work → session end)

Questo pattern è applicabile a **qualsiasi MCP source persistente** (database, knowledge base, project tracker) e potrebbe diventare un template di riferimento per la community Craft Agents.

---

*Fine documentazione*
