# Craft Memory UI — Debug Plan
**Data Audit:** 2026-05-01
**Data Fix completo:** 2026-05-01

Questo documento delinea i risultati dell'audit del codice sorgente della UI (Phase 1) e propone fix strutturati per stabilizzare e completare il frontend dell'applicazione.

## 🔴 Criticità Bloccanti (Cosa impedisce il funzionamento)

### 1. Grafo della Conoscenza vuoto (Edge mancanti)
- **Problema:** In `src/app.jsx` (funzione `loadData`), le relazioni non vengono mai caricate. Di conseguenza, `window.CRAFT.RELATIONS` rimane un array vuoto (come impostato in `data.jsx`). Il `GraphScreen` renderizza solo nodi isolati senza alcuna connessione.
- [x] **Fix:** In `app.jsx`, aggiunta la chiamata `CRAFT_API.relations(null, null)` nel `Promise.all` iniziale (con `.catch(() => [])` per non bloccare il boot). In `GraphScreen`, aggiunto un `useEffect` che carica autonomamente le relazioni dal backend se l'array globale è vuoto, con loading state e caching su `window.CRAFT.RELATIONS`.

### 2. Widget "Memory diff" nella Dashboard rotto/vuoto
- **Problema:** Il componente `DashboardScreen` mappa l'array `window.CRAFT.DIFF_EVENTS` per mostrare gli ultimi eventi. Tuttavia, `app.jsx` non effettua mai il fetch degli eventi diff, mantenendo l'array sempre vuoto. Il widget risulterà costantemente vuoto, non riflettendo i cambiamenti live.
- [x] **Fix:** In `app.jsx`, aggiunta la chiamata `CRAFT_API.diff(null)` nel `Promise.all` iniziale. In `DashboardScreen`, aggiunto `useEffect` autonomo che carica il diff degli ultimi 4h al mount se il global è vuoto, con state locale `diffEvents` e empty state esplicito ("No diff events in the last 4h").

## 🟡 Criticità Minori (UX, Warning, Edge case)

### 1. Dati mancanti nella schermata di Session Handoff
- **Problema:** In `app.jsx` (linea 105), viene mockato un oggetto sessione in `window.CRAFT.SESSIONS` contenente solo `id` e `date`. Il componente `HandoffScreen` cerca di renderizzare valori chiave come `duration`, `model`, `memoriesAdded`, `factsLearned`, ecc. Questi campi non esistono e producono aree vuote nella UI, degradando l'esperienza utente.
- [x] **Fix:** L'oggetto SESSIONS in `app.jsx` ora è arricchito con `duration` (calcolata da `health.boot_time`), `model` (da `health.model`), `memoriesAdded`, `factsLearned`, `loopsOpened`, `loopsClosed`. In `HandoffScreen`, aggiunto guard `SESSIONS[0] || {}` per evitare crash con lista vuota, oggetto `sess` con fallback `"—"` su tutti i campi, fetch di `/api/handoff` al mount per summary e next_steps reali, con loading state.

### 2. Modifica della priorità dei Loop non persistita (Solo locale)
- **Problema:** In `loops.jsx`, la funzione `cycle(id)` scorre ciclicamente la priorità dei task/loop. Questo aggiornamento modifica solo lo stato React locale senza effettuare nessuna chiamata API per persistere il cambio nel backend. Ricaricando la pagina, il cambiamento viene perso.
- [x] **Fix:** Aggiunto endpoint `updateLoop` in `api.jsx` (metodo HTTP `PATCH /api/loops/:id`). La funzione `cycle()` in `loops.jsx` ora chiama `CRAFT_API.updateLoop(id, { priority: nextPriority })` con optimistic update e rollback automatico via `reload()` in caso di errore.

### 3. Tool MCP nella Sidebar non funzionali (Solo mock visivo)
- **Problema:** Le voci della barra laterale come "remember()", "search_memory()" o "run_maintenance()" eseguono solo una semplice navigazione (`navigate`) verso `explorer` o `graph`. Non attivano la funzionalità MCP attesa e non pre-compilano alcuno stato per guidare l'utente.
- [x] **Fix:** In `app.jsx`, ogni MCP Tool nel sidebar ora chiama `navigate(target, { action: toolId })` con `routeArgs` specifici: `search → explorer { action: "search" }`, `find_similar → graph { action: "find_similar" }`, `remember → explorer { action: "remember" }`, `maintenance → dashboard { action: "maintenance" }`. I componenti destinatari ricevono l'`action` via `routeArgs` e possono reagire di conseguenza.

## 🔵 Punti da verificare (Dipendenze dal backend/runtime)

1. **Endpoint e Schema:** Assicurarsi che gli endpoint come `/api/relations` e `/api/diff` siano non solo implementati nel backend ma che la struttura dei dati sia esattamente quella attesa da `api.jsx` e dai componenti (es. `new_memories`, `updated_facts`, ecc.).
2. **God Score / Confidence:** Il normalizzatore `normFact` (in `api.jsx`) richiede dal backend la proprietà `god_score` ed eventuali parametri di `confidence`. Verificare che il calcolo di questi campi sia live e funzionante lato API, altrimenti i widget di ranking avranno tutti valore 0.
3. **Mock Uptime:** `STATS.uptime` ora contiene il timestamp di boot numerico ricevuto da `health.boot_time`. Il Dashboard mostra "server up X ago" calcolato correttamente. Se `boot_time` non è nel payload health, cade su "just now".

## 📝 Next Steps (Piano di Azione)
- [x] Implementare le chiamate API in `app.jsx` per inizializzare `RELATIONS` e `DIFF_EVENTS`.
- [x] Aggiungere fallback/valori completi alla `SESSIONS` mockata o chiamare endpoint.
- [x] Abilitare endpoint di PATCH/Update per completare l'esperienza dei "Loops".

## 🏛️ Decisioni prese (Log delle Architetture e Fix)

| # | Data | File | Decisione | Motivazione |
|---|------|------|-----------|-------------|
| 1 | 2026-05-01 | `api.jsx` | Aggiunta funzione `patch()` interna e endpoint pubblico `updateLoop(id, fields)` | Necessario per persistere il cambio di priorità dei Loop; il PATCH è preferito a POST per semantica REST di aggiornamento parziale |
| 2 | 2026-05-01 | `app.jsx` | `relations` e `diff` aggiunti al `Promise.all` con `.catch(() => [])` | Il fallback silente evita che un endpoint mancante blocchi l'intero boot; le criticità vengono degradate gracefully |
| 3 | 2026-05-01 | `app.jsx` | `STATS.uptime` diventa un timestamp numerico (ms) invece di stringa `"—"` | Permette a `formatRelTime()` di calcolare correttamente la durata; `null` come sentinel per "non disponibile" |
| 4 | 2026-05-01 | `app.jsx` | SESSIONS arricchita con `duration`, `model`, `memoriesAdded`, `factsLearned`, `loopsOpened`, `loopsClosed` derivati da health+stats | Evita crash nel HandoffScreen e fornisce dati reali senza richiedere un endpoint dedicato sessioni |
| 5 | 2026-05-01 | `screens/dashboard.jsx` | `diffEvents` come state locale React invece di lettura diretta da `window.CRAFT` | Consente re-render reattivo quando i diff vengono caricati async; il global è usato solo come seed iniziale |
| 6 | 2026-05-01 | `screens/graph.jsx` | `RELATIONS` locale con `useEffect` di auto-load se array vuoto | Double-fetch prevention: usa il global se popolato dal boot, altrimenti carica autonomamente; caching su `window.CRAFT.RELATIONS` |
| 7 | 2026-05-01 | `screens/handoff.jsx` | Guard `SESSIONS[0] \|\| {}` + campo `sess` con fallback `"—"` per ogni proprietà | Previene crash immediato se `SESSIONS` è vuoto (server offline al boot); `dangerouslySetInnerHTML` per next_steps API (HTML from trusted server) |
| 8 | 2026-05-01 | `app.jsx` MCP Tools | Ogni tool passa `routeArgs.action` con l'identificativo dell'operazione | Apre il percorso per componenti destinatari che reagiscono all'azione (es. apertura modale "remember") senza richiedere refactoring profondo oggi |
