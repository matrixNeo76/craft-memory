# Craft Memory UI — Debug Plan
**Data Audit:** 2026-05-01

Questo documento delinea i risultati dell'audit del codice sorgente della UI (Phase 1) e propone fix strutturati per stabilizzare e completare il frontend dell'applicazione.

## 🔴 Criticità Bloccanti (Cosa impedisce il funzionamento)

### 1. Grafo della Conoscenza vuoto (Edge mancanti)
- **Problema:** In `src/app.jsx` (funzione `loadData`), le relazioni non vengono mai caricate. Di conseguenza, `window.CRAFT.RELATIONS` rimane un array vuoto (come impostato in `data.jsx`). Il `GraphScreen` renderizza solo nodi isolati senza alcuna connessione.
- [ ] **Fix:** Aggiungere il fetching delle relazioni. In `app.jsx`, aggiungere la chiamata API nel `Promise.all` iniziale (se si vuole avere un set globale) o far caricare a `GraphScreen` le proprie `RELATIONS` asincronamente utilizzando `CRAFT_API.relations()`.

### 2. Widget "Memory diff" nella Dashboard rotto/vuoto
- **Problema:** Il componente `DashboardScreen` mappa l'array `window.CRAFT.DIFF_EVENTS` per mostrare gli ultimi eventi. Tuttavia, `app.jsx` non effettua mai il fetch degli eventi diff, mantenendo l'array sempre vuoto. Il widget risulterà costantemente vuoto, non riflettendo i cambiamenti live.
- [ ] **Fix:** In `app.jsx`, includere una chiamata a `CRAFT_API.diff()` e popolare `window.CRAFT.DIFF_EVENTS` oppure delegare il caricamento del diff al mount del componente `DashboardScreen` stesso.

## 🟡 Criticità Minori (UX, Warning, Edge case)

### 1. Dati mancanti nella schermata di Session Handoff
- **Problema:** In `app.jsx` (linea 105), viene mockato un oggetto sessione in `window.CRAFT.SESSIONS` contenente solo `id` e `date`. Il componente `HandoffScreen` cerca di renderizzare valori chiave come `duration`, `model`, `memoriesAdded`, `factsLearned`, ecc. Questi campi non esistono e producono aree vuote nella UI, degradando l'esperienza utente.
- [ ] **Fix:** Popolare l'oggetto mock in `app.jsx` con valori di default o null safety, oppure implementare un endpoint backend reale per recuperare lo storico dettagliato delle sessioni.

### 2. Modifica della priorità dei Loop non persistita (Solo locale)
- **Problema:** In `loops.jsx`, la funzione `cycle(id)` scorre ciclicamente la priorità dei task/loop. Questo aggiornamento modifica solo lo stato React locale senza effettuare nessuna chiamata API per persistere il cambio nel backend. Ricaricando la pagina, il cambiamento viene perso.
- [ ] **Fix:** Aggiungere l'endpoint `updateLoop` in `api.jsx` (e sul server FastAPI) e invocarlo alla fine della funzione `cycle()`.

### 3. Tool MCP nella Sidebar non funzionali (Solo mock visivo)
- **Problema:** Le voci della barra laterale come "remember()", "search_memory()" o "run_maintenance()" eseguono solo una semplice navigazione (`navigate`) verso `explorer` o `graph`. Non attivano la funzionalità MCP attesa e non pre-compilano alcuno stato per guidare l'utente.
- [ ] **Fix:** Intercettare le route arguments nel `navigate` (es. `setRouteArgs({ action: "remember" })`) e far reagire la UI (es. aprire una modale di insert) nel componente destinatario.

## 🔵 Punti da verificare (Dipendenze dal backend/runtime)

1. **Endpoint e Schema:** Assicurarsi che gli endpoint come `/api/relations` e `/api/diff` siano non solo implementati nel backend ma che la struttura dei dati sia esattamente quella attesa da `api.jsx` e dai componenti (es. `new_memories`, `updated_facts`, ecc.).
2. **God Score / Confidence:** Il normalizzatore `normFact` (in `api.jsx`) richiede dal backend la proprietà `god_score` ed eventuali parametri di `confidence`. Verificare che il calcolo di questi campi sia live e funzionante lato API, altrimenti i widget di ranking avranno tutti valore 0.
3. **Mock Uptime:** `STATS.uptime` è bypassato in `DashboardScreen` con un espediente logico `STATS.uptime ? Date.now() - 60000 : Date.now()`, forzando la visualizzazione di "1m ago". Questo dato deve essere calcolato correttamente dal frontend partendo dal timestamp di boot inviato dal backend.

## 📝 Next Steps (Piano di Azione)
- [ ] Implementare le chiamate API in `app.jsx` per inizializzare `RELATIONS` e `DIFF_EVENTS`.
- [ ] Aggiungere fallback/valori completi alla `SESSIONS` mockata o chiamare endpoint.
- [ ] Abilitare endpoint di PATCH/Update per completare l'esperienza dei "Loops".

## 🏛️ Decisioni prese (Log delle Architetture e Fix)
*(Nessuna decisione registrata finora. Aggiornare questa sezione man mano che i fix vengono implementati per tracciare le motivazioni dietro a scelte architetturali, cambi di librerie o workaround).*
