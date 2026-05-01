# Craft Memory UI — Debug Plan
**Data Audit:** 2026-05-01 (Post-Phase 1 Fixes)
**Data Fix Phase 2:** 2026-05-01
**Data Fix Phase 3:** 2026-05-01 (Web Design & Security audit)

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

---

## 🟥 Phase 3 — Audit Statico Web Design, Responsiveness & Security (2026-05-01)

Audit condotto tramite analisi statica del codebase UI (`index.html`, `app.jsx`, `src/screens/*.jsx`, `src/*.jsx`) seguendo le checklist di layout, responsive design, accessibilità e sicurezza frontend.

### 🔴 Criticità Bloccanti

#### 1. Vettore XSS in `handoff.jsx` (`dangerouslySetInnerHTML`)
- **Problema:** Nel rendering della sezione "Next steps", il codice utilizza `<li dangerouslySetInnerHTML={{ __html: s.text || s }} />`. I dati `nextSteps` provengono dal backend (`generate_handoff`). Se un attore malevolo (o un bug) inietta HTML/JS nei campi testuali del backend, la UI eseguirà il rendering senza sanitizzazione, aprendo un vettore XSS stored.
- [ ] **Fix:** Sostituire `dangerouslySetInnerHTML` con rendering testuale sicuro (JSX `{s.text || s}`). Se il markdown/HTML è un requirement, introdurre una libreria di sanitizzazione (es. `DOMPurify`) oppure un parser markdown-safe lato client.

#### 2. `alert()` bloccante residuo in `handoff.jsx`
- **Problema:** Sebbene nella Phase 2 sia stato eliminato l'`alert()` da `loops.jsx`, in `handoff.jsx` (riga ~76) persiste un `alert("Clipboard API unavailable — copy failed")`. Questo blocca il thread principale e rompe l'esperienza utente coerente.
- [ ] **Fix:** Sostituire con un banner inline di errore (stesso pattern usato per `loops-error` o `setError` degli altri screen).

#### 3. Layout rigido assolutamente non responsive
- **Problema:** L'`App Shell` (`.shell`) usa `grid-template-columns: 240px 1fr` e `height: 100vh` senza alcuna media query. Su viewport < ~900px (tablet), e specialmente < 768px (mobile), la sidebar occupa invariabilmente 240px schiacciando il main content. Su viewport < 600px il layout diventa inusabile: testo trabocca, elementi si sovrappongono, e la sidebar non è collassabile. Non esiste un breakpoint mobile.
- **Impatto:** L'UI è utilizzabile solo su desktop. Su tablet/mobile gran parte dei controlli non è raggiungibile.
- [ ] **Fix:** Aggiungere media queries CSS per breakpoint `768px` e `480px`. Ad esempio: sotto `768px` passare a `grid-template-columns: 1fr` con sidebar trasformata in drawer overlay o hamburger menu; sotto `480px` ridurre padding e font-size.

#### 4. Assenza totale di Error Boundary
- **Problema:** `app.jsx` non implementa alcun React Error Boundary. Se un singolo screen (es. `GraphScreen`, `DashboardScreen` con dati malformati, o `HandoffScreen` con markup inatteso) lancia un'eccezione, l'intera applicazione React si smonta mostrando una schermata bianca (white screen of death). L'utente deve ricaricare la pagina per ripristinare.
- [ ] **Fix:** Aggiungere un componente `<ErrorBoundary>` che wrappi `<main className="main">` in `app.jsx`, con fallback UI che mostri l'errore, il log, e un pulsante "Reload app".

### 🟡 Criticità Minori (UX, Accessibility, Robustness)

#### 5. Azioni visibili solo su hover (inaccessibili su touch)
- **Problema:** In `loops.jsx`, le `.lcard-actions` hanno `opacity: 0` e diventano visibili solo su `.lcard:hover`. Su dispositivi touch non esiste hover; le azioni "priority" e "close" sui loop card non sono quindi raggiungibili.
- [ ] **Fix:** Rendi le azioni sempre visibili su touch / viewport mobile, oppure usa un pattern alternativo (es. swipe-to-reveal o menu a discesa).

#### 6. Touch targets sottodimensionati
- **Problema:** Diversi controlli interattivi hanno dimensioni inferiori alla soglia WCAG 2.5.5 / Apple HIG / Material di 44×44px. Esempi: `.role-toggle` (altezza ~16px), `.filter-item` (padding ridotto), `.nav-item`, `.pri-btn`. Questo causa difficoltà di interazione su touch.
- [ ] **Fix:** Aumentare padding/min-height dei target interattivi a almeno 36px (preferibilmente 44px) su viewport touch.

#### 7. Mancanza di supporto `prefers-reduced-motion`
- **Problema:** Il sistema ha un toggle manuale "Motion" nel tweaks panel, ma ignor completamente la media query CSS `prefers-reduced-motion: reduce` a livello di sistema operativo. Gli utenti con sensibilità ai movimenti non sono protetti automaticamente.
- [ ] **Fix:** Aggiungere `@media (prefers-reduced-motion: reduce)` in `index.html` che sovrascriva le animazioni (rain, pulse, transition) equivalentemente alla classe `.motion-off`.

#### 8. Form e navigazione non accessibili (ARIA / keyboard)
- **Problema:**
  - I `.nav-item` sono `<div>` con `onClick` ma senza `role="button"`, `tabIndex={0}`, o `aria-current="page"` per l'elemento attivo. Non sono navigabili da tastiera né annunciati da screen reader.
  - Le label nei form di `InsertMemoryModal` e `ConfigModal` sono `<div>` stilizzate anziché `<label htmlFor="...">`, senza `aria-label` sugli input.
  - I modali non chiudono con il tasto `Escape`.
- [ ] **Fix:**
  - Convertire `.nav-item` in `<button>` o aggiungere `role="button" tabIndex={0}` e gestire `onKeyDown` (Enter/Space).
  - Usare `<label>` semantiche o `aria-label` / `aria-describedby` su input.
  - Aggiungere listener `Escape` nei componenti modale per chiudere.

#### 9. Keyboard shortcut macOS-centric
- **Problema:** La topbar mostra `<kbd>⌘K</kbd>` e il salvataggio modale invoca `⌘↵`. Questi shortcut sono hardcoded per macOS; utenti Windows/Linux non hanno indicazioni corrette né listener per `Ctrl+K` / `Ctrl+Enter`.
- [ ] **Fix:** Rilevare la piattaforma (`navigator.platform`) e mostrare `Ctrl` o `⌘` dinamicamente. Aggiungere global event listener per `Ctrl/Cmd+K` che apra l'Explorer e `Ctrl/Cmd+Enter` che submit il form.

#### 10. Staleness delle posizioni nodi in `graph.jsx`
- **Problema:** Il calcolo `positions` all'interno di `useMemo(..., [])` in `graph.jsx` dipende da `MEMORIES` ma ha un array di dipendenze vuoto. Se vengono aggiunte o rimosse memorie dopo il mount, le posizioni non si aggiornano: nuovi nodi non compaiono o compaiono senza posizione (`null`).
- [ ] **Fix:** Aggiungere `MEMORIES` alle dipendenze di `useMemo`, oppure ricostruire le posizioni ad ogni aggiornamento del dataset.

#### 11. Font Google senza fallback locale e potenziale FOIT
- **Problema:** I font vengono caricati da Google Fonts CDN (`fonts.googleapis.com`). In assenza di connessione, il rendering attende fino al timeout del browser. Non c'è `@font-face` con font di sistema come fallback immediato (sebbene `font-family` li elenchi, il caricamento del CSS remoto può ritardare il rendering).
- [ ] **Fix:** Includere font web self-hosted o accettare il `display=swap` attuale come sufficiente (low priority).

### 🔵 Punti da verificare (Design/Visual)

1. **Contrasto WCAG AA per testo secondario:** Il colore `var(--ink-3)` (`#4d586e`) su `var(--bg-1)` (`#0a0f1a`) potrebbe essere al limite del rapporto di contrasto richiesto per testo piccolo (10px–11px). Verificare con strumenti (es. Lighthouse) che sia ≥ 4.5:1; in caso contrario, schiarire `var(--ink-3)`.
2. **Rendering SVG Graph su scaling:** Il testo SVG dei nodi usa `fontSize="9"`. Su display ad alta densità o quando il container viene scalato, la leggibilità potrebbe degradarsi. Verificare se occorre aggiungere `shape-rendering="crispEdges"` o aumentare il font size minimo.

## 📝 Next Steps (Piano di Azione)

### Phase 2 (Completata)
- [x] Riscrivere la logica di `explorer.jsx` per eseguire vere query `searchMemories()`.
- [x] Connettere `routeArgs.action` tra Router e Componenti per i MCP Tools.
- [x] Creare l'interfaccia per inserire nuove memorie.
- [x] "Accendere" i pulsanti Copy to Clipboard e bottoni Graph.

### Phase 3 (In corso — Web Design & Security)
- [ ] **Sicurezza:** Eliminare `dangerouslySetInnerHTML` in `handoff.jsx` e sostituirlo con rendering JSX sicuro (o sanitizzazione esplicita).
- [ ] **UX:** Sostituire l'`alert()` residuo in `handoff.jsx` con banner inline.
- [ ] **Responsive:** Aggiungere media queries per breakpoint `768px` e `480px` in `index.html` / `app.jsx` (sidebar collassabile o drawer).
- [ ] **Robustezza:** Implementare un `<ErrorBoundary>` in `app.jsx` per prevenire white-screen su crash.
- [ ] **Accessibility:** Aggiungere supporto `prefers-reduced-motion` in `index.html`.
- [ ] **Accessibility:** Correggere ARIA/keyboard dei `.nav-item` (role, tabIndex, aria-current) e dei form modali (`<label>`, Escape to close).
- [ ] **Touch:** Rifattorizzare `.lcard-actions` per essere accessibili su touch (opacity sempre 1 su mobile / touch-only).
- [ ] **Touch:** Aumentare touch target di `.role-toggle`, `.filter-item`, `.pri-btn` a ≥ 36px (target 44px).
- [ ] **Cross-platform:** Rilevare piattaforma e mostrare `Ctrl` vs `⌘` nei kbd shortcut; implementare listener globali per `Ctrl/Cmd+K` e `Ctrl/Cmd+Enter`.
- [ ] **Bug:** Correggere `useMemo` dipendenze in `graph.jsx` per aggiornare layout quando cambia `MEMORIES`.
- [ ] **Polish:** Verificare contrasto WCAG AA di `var(--ink-3)` con strumento Lighthouse (AA 4.5:1 per testo piccolo).

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

## 🏛️ Decisioni prese (Log delle Architetture e Fix — Phase 3)

| # | Data | Area | Decisione | Motivazione |
|---|------|------|-----------|-------------|
| 8 | 2026-05-01 | Security | `dangerouslySetInnerHTML` in `handoff.jsx` classificato come P1 | Qualsiasi rendering raw HTML da dati backend è un vettore XSS stored; deve essere eliminato o sanitizzato |
| 9 | 2026-05-01 | UX / Robustness | Introduzione Error Boundary classificata come P1 | White-screen su crash rende l'app inutilizzabile; un boundary isola il fallimento e permette recovery |
| 10 | 2026-05-01 | Responsive | Sidebar fissa a 240px classificata come P1 per mobile | Il layout non ha breakpoint; su tablet/mobile il content è inaccessibile |
| 11 | 2026-05-01 | Accessibility | `prefers-reduced-motion` deve avere priorità sul toggle manuale | Gli utenti con vestibular disorders o sensitivity la impostano a livello OS; rispettarla è un requisito WCAG |
