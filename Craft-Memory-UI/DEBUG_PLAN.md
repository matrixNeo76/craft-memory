# Craft Memory UI — Debug Plan
**Data Audit:** 2026-05-01 (Post-Phase 1 Fixes)
**Data Fix Phase 2:** 2026-05-01

Questo documento delinea i risultati del **secondo audit** del codice sorgente della UI, dopo la risoluzione delle criticità iniziali. Nonostante la UI ora si avvii e carichi correttamente le relazioni, il diff e le sessioni, permangono severi colli di bottiglia logici che degradano l'esperienza o bypassano le capacità del backend.

## 🔴 Criticità Bloccanti (Cosa impedisce il funzionamento)

### 1. Ricerca "Fake" (FTS5 bypassato) in `explorer.jsx`
- **Problema:** L'`ExplorerScreen` vantava "RRF hybrid search FTS5 BM25 + Jaccard", ma in realtà la logica di filtro era un semplice `.includes()` Javascript in memoria. Dato che l'array globale `MEMORIES` viene popolato al boot con i soli 50 elementi più recenti, la ricerca non scavava mai nel database FTS5 reale. L'endpoint `CRAFT_API.searchMemories()` era definito in `api.jsx` ma mai utilizzato.
- [x] **Fix:** `ExplorerScreen` riscritto con logica di ricerca ibrida: debounce 300ms sull'input → chiamata `CRAFT_API.searchMemories()` → badge visivo "FTS5" quando si usano i risultati del server, spinner di caricamento, fallback locale con messaggio di errore in caso di server down. I filtri di categoria/scope/coreOnly si applicano sui risultati server in modo cumulativo.

### 2. Routing dei Tools MCP incompleto (`routeArgs` orfani)
- **Problema:** Sebbene in `app.jsx` i click sulla sidebar dei Tools MCP istruissero il router a passare argomenti (es. `navigate("explorer", { action: "search" })`), l'`ExplorerScreen` (e gli altri componenti) non leggevano questa proprietà. Il risultato era che l'azione veniva persa, e la UI si limitava a un banale cambio pagina senza avviare il tool richiesto.
- [x] **Fix:** In `app.jsx`, la prop `action={routeArgs.action}` viene ora propagata ad `ExplorerScreen` e `GraphScreen`. In `ExplorerScreen`, un `useEffect` reagisce a `action === "search"` mettendo il focus sull'input testuale, e a `action === "remember"` aprendo la modale di inserimento.

## 🟡 Criticità Minori (UX, Warning, Edge case)

### 1. Funzione "Remember" (Inserimento Memorie) inesistente
- **Problema:** L'API client includeva il metodo `CRAFT_API.remember` per la creazione di nuove memorie (POST), e c'era il pulsante `remember()` nella sidebar, ma mancava un'interfaccia utente per comporle.
- [x] **Fix:** Implementata `InsertMemoryModal` direttamente in `explorer.jsx`: form con textarea content, selettori category/scope/importance (1–10), campo tags (comma-separated), toggle isCore, bottone Save con `⌘↵` shortcut. Al salvataggio la nuova memoria viene preappesa a `window.CRAFT.MEMORIES` aggiornando immediatamente Dashboard e contatori senza ricaricare la pagina.

### 2. Azioni Dummy / Interattività Falsa (Handoff e Graph)
- **Problema:**
  - In `handoff.jsx`, i pulsanti "Copy markdown" e "Start next session with this" erano puri elementi decorativi (no `onClick`).
  - In `graph.jsx`, i bottoni "link_memories()" e "find_similar()" nel top-bar non avevano funzionalità.
- [x] **Fix:**
  - `handoff.jsx`: aggiunta funzione `buildMarkdown()` che serializza tutto il documento (sessione, stats, decisions, discoveries, facts, loops, next steps) come Markdown puro. Bottoni "Copy markdown" ora chiamano `navigator.clipboard.writeText()` con feedback visivo "Copied!" per 2s. Bottone "Start next session" mostra un alert informativo che invita a usare il client MCP.
  - `graph.jsx`: "link_memories()" mostra un tooltip inline informativo per 3s. "find_similar()" naviga verso l'Explorer con `action: "search"` per attivare la ricerca FTS5.

### 3. Edge Case: Fetch in loop in `GraphScreen` se il database è vergine
- **Problema:** L'`useEffect` in `graph.jsx` usava il check `if (relations.length > 0) return;` per evitare double-fetching. Tuttavia, se il workspace è nuovo e ci sono oggettivamente 0 relazioni nel DB, il fetch scattava ad ogni mount di `GraphScreen`.
- [x] **Fix:** Introdotto il flag booleano `window.CRAFT.RELATIONS_LOADED` (settato a `true` sia al successo che all'errore del fetch), il controllo ora è `if (window.CRAFT.RELATIONS_LOADED) return;`. Questo garantisce che il fetch avvenga esattamente una volta per session, indipendentemente dall'effettivo numero di edge nel DB.

### 4. Alert bloccante nativo in `loops.jsx`
- **Problema:** Il fallback di errore durante l'aggiunta di un loop (`CRAFT_API.addLoop().catch(...)`) usava `alert()` nativo, causando blocchi del thread principale della UI e risultando non coerente con il design estetico del resto dell'interfaccia.
- [x] **Fix:** Sostituito `alert()` con un aggiornamento dello stato locale `setError()`. L'errore viene ora mostrato inline in un banner dedicato per 4 secondi, offrendo un'esperienza utente molto più integrata.

### 5. `action` ignorata in altri componenti (`DashboardScreen`, `GraphScreen`)
- **Problema:** Sebbene in `app.jsx` la prop `action` fosse già parzialmente configurata, in `DashboardScreen` non veniva propagata, e `GraphScreen` la riceveva senza consumarla, di fatto vanificando il click dei tool `find_similar` e `maintenance` nella sidebar.
- [x] **Fix:** 
  - `app.jsx`: `action` esplicitamente propagata al `<DashboardScreen />`.
  - `graph.jsx`: Aggiunto `useEffect` per reagire a `action === "find_similar"`, mostrando un tooltip informativo tramite il sistema locale `showMsg`.
  - `dashboard.jsx`: Aggiunto handler locale per `action === "maintenance"`, anch'esso visivamente presentato in alto a destra tramite uno state `maintenanceMsg`.

## 🔵 Punti da verificare (Dipendenze dal backend/runtime)

1. **Ricerca Ibrida RRF:** Verificare che l'endpoint backend `/api/memories/search` ritorni i risultati ordinati per rank `rrf`, in modo che l'UI possa semplicemente mapparli così come arrivano senza dover re-implementare logiche di sort complesse.
2. **Aggiornamento Cache Globale:** Dopo aver inserito una nuova memoria (Fix 🟡.1), l'array globale `window.CRAFT.MEMORIES` viene aggiornato con prepend. Verificare che i componenti che leggono MEMORIES (Dashboard, Explorer) riflettano correttamente l'aggiornamento senza full reload.

## 📝 Next Steps (Piano di Azione)
- [x] Riscrivere la logica di `explorer.jsx` per eseguire vere query `searchMemories()`.
- [x] Connettere `routeArgs.action` tra Router e Componenti per i MCP Tools.
- [x] Creare l'interfaccia per inserire nuove memorie.
- [x] "Accendere" i pulsanti Copy to Clipboard e bottoni Graph.

## 🏛️ Decisioni prese (Log delle Architetture e Fix — Phase 2)

| # | Data | File | Decisione | Motivazione |
|---|------|------|-----------|-------------|
| 1 | 2026-05-01 | `explorer.jsx` | Debounce 300ms su `searchMemories()` invece di submit manuale | Evita chiamate ridondanti al server durante la digitazione; 300ms è soglia UX standard per search-as-you-type |
| 2 | 2026-05-01 | `explorer.jsx` | Badge "FTS5" visivo + spinner nel search bar | Comunicazione esplicita all'utente di quale modalità è attiva (server vs local), fondamentale per il debug |
| 3 | 2026-05-01 | `explorer.jsx` | `InsertMemoryModal` co-locata nello stesso file di `ExplorerScreen` | Coesione funzionale: la modale è strettamente legata all'Explorer; evita dipendenze circolari tra file |
| 4 | 2026-05-01 | `handoff.jsx` | `buildMarkdown()` serializza tutto il documento in-memory | Evita dipendenza da un endpoint API di export; il markdown è generato lato client da dati già disponibili |
| 5 | 2026-05-01 | `handoff.jsx` | Bottone "Start next session" → alert informativo invece di funzionalità completa | Feature non implementabile lato UI pura (richiede sessione MCP attiva); alert onesto è preferibile a CTA rotto |
| 6 | 2026-05-01 | `graph.jsx` | Flag `window.CRAFT.RELATIONS_LOADED` come sentinel | La `length` di un array non è un indicatore affidabile di "già caricato" per dataset potenzialmente vuoti; un booleano esplicito è la soluzione corretta |
| 7 | 2026-05-01 | `graph.jsx` | "find_similar()" naviga verso Explorer con `action: "search"` | Comportamento utile e realizzabile subito: porta l'utente nella ricerca FTS5 che è il modo più vicino a un find_similar semantico senza embedding |
