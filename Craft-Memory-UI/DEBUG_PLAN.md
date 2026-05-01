# Craft Memory UI — Debug Plan
**Data Audit:** 2026-05-01 (Post-Phase 1 Fixes)

Questo documento delinea i risultati del **secondo audit** del codice sorgente della UI, dopo la risoluzione delle criticità iniziali. Nonostante la UI ora si avvii e carichi correttamente le relazioni, il diff e le sessioni, permangono severi colli di bottiglia logici che degradano l'esperienza o bypassano le capacità del backend.

## 🔴 Criticità Bloccanti (Cosa impedisce il funzionamento)

### 1. Ricerca "Fake" (FTS5 bypassato) in `explorer.jsx`
- **Problema:** L'`ExplorerScreen` vanta "RRF hybrid search FTS5 BM25 + Jaccard", ma in realtà la logica di filtro è un semplice `.includes()` Javascript in memoria (`hay.includes(q)` riga 20). Dato che l'array globale `MEMORIES` viene popolato al boot con i soli 50 elementi più recenti, la ricerca non scaverà mai nel database FTS5 reale. Qualsiasi memoria oltre le ultime 50 è di fatto introvabile. L'endpoint `CRAFT_API.searchMemories()` è definito in `api.jsx` ma mai utilizzato.
- [ ] **Fix:** Aggiornare l'`ExplorerScreen` per usare uno state differenziato tra "recent" (mostrato a query vuota) e "search_results" (mostrato quando l'utente digita). Collegare un debounce (es. 300ms) all'input di ricerca che invochi `CRAFT_API.searchMemories(query)` e renderizzi i risultati reali del server.

### 2. Routing dei Tools MCP incompleto (`routeArgs` orfani)
- **Problema:** Sebbene in `app.jsx` i click sulla sidebar dei Tools MCP ora istruiscano il router a passare argomenti (es. `navigate("explorer", { action: "search" })`), l'`ExplorerScreen` (e gli altri componenti) non leggono questa proprietà. Il risultato è che l'azione viene persa, e la UI si limita a un banale cambio pagina senza avviare il tool richiesto (nessun focus sull'input di ricerca, ecc.).
- [ ] **Fix:** In `app.jsx`, propagare le `routeArgs` ai componenti (`<ExplorerScreen action={routeArgs.action} />`). In `ExplorerScreen`, usare un `useEffect` che reagisce a `action === "search"` mettendo automaticamente il focus sull'input testuale, per una UX coerente.

## 🟡 Criticità Minori (UX, Warning, Edge case)

### 1. Funzione "Remember" (Inserimento Memorie) inesistente
- **Problema:** L'API client include il metodo `CRAFT_API.remember` per la creazione di nuove memorie (POST), e c'è il pulsante `remember()` nella sidebar, ma manca un'interfaccia utente (form o modale) per comporle. L'utente non può registrare nuove memorie direttamente dalla UI.
- [ ] **Fix:** Implementare una modale `<InsertMemoryModal />` (simile al form inline dei Loops) che gestisca l'inserimento manuale e chiami l'endpoint, aggiornando poi la lista.

### 2. Azioni Dummy / Interattività Falsa (Handoff e Graph)
- **Problema:** 
  - In `handoff.jsx`, i pulsanti "Copy markdown" e "Start next session with this" sono puri elementi decorativi (no `onClick`). L'handoff generato non può essere effettivamente esportato dall'utente se non copiandolo manualmente.
  - In `graph.jsx`, i bottoni "link_memories()" e "find_similar()" nel top-bar non hanno funzionalità.
- [ ] **Fix:** Collegare "Copy markdown" a `navigator.clipboard.writeText(...)` per copiare un dump raw del documento. Rimuovere temporaneamente le CTA non supportate (link_memories) oppure agganciarle a un allert "Not implemented yet".

### 3. Edge Case: Fetch in loop in `GraphScreen` se il database è vergine
- **Problema:** L'`useEffect` in `graph.jsx` usa il check `if (relations.length > 0) return;` per evitare double-fetching. Tuttavia, se il workspace è nuovo e ci sono oggettivamente 0 relazioni nel DB, il fetch scatterà a *ogni mount* di `GraphScreen`, dato che la length rimarrà a 0.
- [ ] **Fix:** Introdurre un flag logico booleano globale (es. `window.CRAFT.RELATIONS_LOADED`) invece di affidarsi solo alla `length` dell'array, o usare una reference interna al router.

## 🔵 Punti da verificare (Dipendenze dal backend/runtime)

1. **Ricerca Ibrida RRF:** Verificare che l'endpoint backend `/api/memories/search` ritorni i risultati ordinati per rank `rrf`, in modo che l'UI possa semplicemente mapparli così come arrivano senza dover re-implementare logiche di sort complesse.
2. **Aggiornamento Cache Globale:** Dopo aver inserito una nuova memoria (Fix 🟡.1), bisognerà assicurarsi che l'array globale `window.CRAFT.MEMORIES` (usato dalla Dashboard) venga invalidato o aggiornato senza ricaricare la pagina.

## 📝 Next Steps (Piano di Azione)
- [ ] Riscrivere la logica di `explorer.jsx` per eseguire vere query `searchMemories()`.
- [ ] Connettere `routeArgs.action` tra Router e Componenti per i MCP Tools.
- [ ] Creare l'interfaccia per inserire nuove memorie.
- [ ] "Accendere" i pulsanti Copy to Clipboard.

## 🏛️ Decisioni prese (Log delle Architetture e Fix)
*(Spazio riservato ai futuri fix architetturali relativi a questa Phase 2)*
