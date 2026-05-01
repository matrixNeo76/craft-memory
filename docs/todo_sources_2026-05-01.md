# 🧩 Piano Aggiunta Sources (API & MCP)

> **Data**: 2026-05-01  
> **Progetto**: Craft Memory  
> **Versione**: v5 (schema v6, 46 tool MCP, 65 test, 4 automazioni)  
> **Workspace attivo**: `auresys-backend`  
> **Sources esistenti**: claude-mem, craft-agents-oss, everos, graphify, hermes-agent, memory (craft-memory MCP)

---

## 📊 Stato Attuale

| Source | Tipo | Stato | Ruolo |
|--------|------|-------|-------|
| `memory` | MCP (craft-memory) | ✅ Attivo | Memoria persistente SQLite+FTS5 |
| `claude-mem` | locale (repo) | ✅ Attivo | Plugin Claude Code per memoria sessioni |
| `craft-agents-oss` | locale (repo) | ✅ Attivo | Framework open-source agenti |
| `everos` | locale (repo) | ✅ Attivo | Long-term memory OS patterns |
| `graphify` | locale (repo) | ✅ Attivo | Knowledge graph builder |
| `hermes-agent` | locale (repo) | ✅ Attivo | Self-improving agent |

**Gap evidenziato**: Tutte le fonti sono locale/repo o il MCP memory server. Manca completamente:
- Integrazione con piattaforme esterne (GitHub, Linear, Slack, etc.)
- Capacità di browser automation e web scraping
- Accesso a documentazione e knowledge base esterne
- Integrazione email/calendar per context catching
- Strumenti di produttività (diagrammi, PDF, immagini)

---

## 🗂️ Categorie Sources

### 1. 🔗 Sviluppo & Code

#### 1.1 GitHub (MCP via GitHub CLI o GitHub MCP Server)

**Cosa fa**: Accesso a issues, PR, repository, Actions, Projects, Gists, releases
**Endpoint**: `gh api` + MCP integration
**Tipo**: MCP (remoto)

**Perché aggiungerlo**:
- Il workspace `auresys-backend` è centrato su sviluppo — GitHub è la sorgente primaria
- Permette all'agente di: creare issues, revieware PR, leggere codice, gestire progetti
- Integrazione nativa con `gh cli` già installato
- Le memories possono includere contesto da issue/PR discussioni

**Esempi d'uso con craft-memory**:
- `remember(category='decision')` dopo aver approvato una PR
- `upsert_fact(key='pr-#42_conclusion', value='...')` da commenti di review
- Collegamento automatico tra decisioni architetturali e relative PR/issues

**Installazione**: `gh extension install github/gh-mcp`

---

#### 1.2 Linear MCP

**Cosa fa**: Gestione issue tracker — creare, leggere, aggiornare issue, sprint, teams
**Endpoint**: Linear API via MCP server
**Tipo**: MCP (remoto con OAuth)

**Perché aggiungerlo**:
- Se il team usa Linear per project management, ogni issue contiene contesto prezioso
- Permette di tracciare decisioni collegate a specifici ticket
- Le memories possono referenziare issue ID per collegamento bidirezionale

**Esempi d'uso con craft-memory**:
- `remember(content='Risolto bug ENG-42: ...', tags=['linear', 'bugfix'])`
- Auto-creare open loop da issue assegnate
- Arricchire memories con contesto da commenti su ticket

---

#### 1.3 GitLab MCP

**Cosa fa**: Accesso a GitLab repos, merge request, CI pipeline, issues
**Endpoint**: GitLab API via MCP server
**Tipo**: MCP (remoto con token)

**Perché aggiungerlo**:
- Alternativa a GitHub se si lavora su progetti self-hosted
- Accesso a CI/CD pipeline status per debugging

---

### 2. 💬 Comunicazione & Collaborazione

#### 2.1 Slack MCP (ufficiale)

**Cosa fa**: Leggere e scrivere messaggi, cercare in canali, gestire thread, accedere a file
**Endpoint**: Slack API via Slack MCP server
**Tipo**: MCP (remoto con OAuth, già disponibile via `source_slack_oauth_trigger`)

**Perché aggiungerlo**:
- **Fonte più ricca di contesto decisionale**: decisioni architetturali, discussioni tecniche, link condivisi
- Recuperare contesto da conversazioni mentre si lavora su un ticket
- Le memories possono catturare decisioni emerse in chat prima che vadano perse

**Esempi d'uso con craft-memory**:
- `remember(content='Decisione in #arch: adottiamo ...', category='decision', tags=['slack'])`
- Cercare in canali per trovare discussioni passate su un tema
- Integrare con automazioni: quando arriva una decisione in Slack, salvarla in memoria

**Priorità**: 🔴 **Alta** — massimo valore informativo

---

#### 2.2 Gmail MCP (ufficiale)

**Cosa fa**: Leggere email, cercare, organizzare, inviare
**Endpoint**: Gmail API via MCP server
**Tipo**: MCP (remoto con OAuth Google, già disponibile via `source_google_oauth_trigger`)

**Perché aggiungerlo**:
- Email contiene decisioni formali, meeting setup, feedback da clienti
- Recuperare thread email come contesto per una sessione
- Catturare promesse/commitment da email come open loop

**Priorità**: 🟡 **Alta**

---

#### 2.3 Outlook/Calendar MCP (ufficiale)

**Cosa fa**: Leggere email, calendario, contatti su Microsoft 365
**Endpoint**: Microsoft Graph API via MCP server
**Tipo**: MCP (remoto con OAuth Microsoft, già disponibile via `source_microsoft_oauth_trigger`)

**Perché aggiungerlo**:
- Calendario: sapere impegni per pianificare sessioni
- Email: stesso valore di Gmail ma per utenti Microsoft
- Il workspace ha timezone Europe/Rome — utile per scheduling

**Priorità**: 🟢 **Media** (se si usa ecosistema Microsoft)

---

### 3. 🌐 Browser & Web Automation

#### 3.1 Chrome DevTools MCP

**Cosa fa**: Browser automation completa — navigare, click, fill form, screenshot, network, console
**Endpoint**: Chrome DevTools Protocol via MCP
**Tipo**: MCP (locale)

**Perché aggiungerlo**:
- **Abilita test E2E, debugging web, scraping** — fino ad ora inaccessibile
- Testare UI della webapp Craft-Memory-UI
- Eseguire azioni su piattaforme web senza API (CMS, dashboard, admin panel)
- Prendere screenshot per documentazione

**Esempi d'uso con craft-memory**:
- `remember(content='Trovato bug nella UI: ...', category='bugfix')` dopo un test browser
- Catturare screenshot di stato come memories visuali

**Priorità**: 🔴 **Alta** — abilita capability fondamentalmente nuove

---

#### 3.2 Playwright MCP

**Cosa fa**: Playwright automation — click, fill, snapshot, test execution
**Endpoint**: Playwright MCP server
**Tipo**: MCP (locale o remoto)

**Perché aggiungerlo**:
- Complementare a Chrome DevTools per testing strutturato
- Migliore per test E2E e generazione test
- Supporta multipli browser (Chrome, Firefox, Safari)

**Priorità**: 🟢 **Media** (se Chrome DevTools non basta)

---

### 4. 📚 Documentazione & Knowledge

#### 4.1 Notion MCP

**Cosa fa**: Leggere/scrivere pagine Notion, database, search
**Endpoint**: Notion API via MCP server
**Tipo**: MCP (remoto con token)

**Perché aggiungerlo**:
- Fonte primaria di documentazione per molti team
- Contiene PRD, specifiche tecniche, meeting note
- Le memories potrebbero arricchirsi con link a pagine Notion rilevanti

**Esempi d'uso con craft-memory**:
- `remember(content='Nuovo requirement dal PRD: ...', tags=['notion', 'requirement'])`
- Cercare documentazione Notion durante una sessione per contesto

**Priorità**: 🟡 **Alta**

---

#### 4.2 Confluence MCP

**Cosa fa**: Leggere/scrivere pagine Confluence, cercare, gestire spazi
**Endpoint**: Confluence API via MCP server
**Tipo**: MCP (remoto con token)

**Perché aggiungerlo**:
- Alternativa enterprise a Notion
- Molte aziende hanno intere knowledge base su Confluence

**Priorità**: 🟢 **Media** (solo se si usa Atlassian stack)

---

#### 4.3 Tavily / Brave Search (API Search)

**Cosa fa**: Web search ottimizzato per LLM — ricerca, estrazione contenuti, crawling
**Endpoint**: API REST
**Tipo**: API (remoto con API key)

**Perché aggiungerlo**:
- **L'unico modo per l'agent di accedere a informazioni live dal web**
- Ricerca documentazione tecnica, API docs, best practices
- Fact-checking in tempo reale

**Esempi d'uso con craft-memory**:
- `remember(content='Scoperto che ...', tags=['research', 'web'])` dopo una ricerca
- Validare facts con fonti esterne prima di salvarli in memoria

**Priorità**: 🔴 **Alta**

---

### 5. 🗄️ Database & Storage

#### 5.1 Supabase MCP

**Cosa fa**: Gestione database PostgreSQL, auth, storage, edge functions, Realtime
**Endpoint**: Supabase Management API + Postgres via MCP
**Tipo**: MCP (remoto con token)

**Perché aggiungerlo**:
- Se craft-memory usa Supabase come backend opzionale
- Gestione diretta del database, tabelle, migrazioni
- RLS policies, auth configuration

**Priorità**: 🟡 **Media** (se si adotta Supabase)

---

#### 5.2 PostgreSQL MCP

**Cosa fa**: Query e manutenzione database PostgreSQL
**Endpoint**: PostgreSQL via MCP server
**Tipo**: MCP (locale o remoto con credenziali)

**Perché aggiungerlo**:
- Il cuore di craft-memory è SQLite, ma avere accesso a Postgres permetterebbe migrazioni
- Query dirette su database di produzione/staging per debugging
- Data migration patterns

**Priorità**: 🟢 **Bassa** (valore solo in scenari specifici)

---

#### 5.3 Filesystem MCP

**Cosa fa**: Lettura/scrittura file, listing directory, watch, search
**Endpoint**: Filesystem locale via MCP
**Tipo**: MCP (locale)

**Perché aggiungerlo**:
- Già parzialmente coperto da tool esistenti, ma un MCP dedicato offre operazioni più ricche
- Lettura/scrittura batch di file
- Pattern matching avanzato

**Priorità**: 🔵 **Bassa** (ridondante con tool nativi)

---

### 6. 🎨 Multimedia & Content Creation

#### 6.1 PDF Tool MCP

**Cosa fa**: Manipolazione PDF — estrarre testo, unire, dividere, creare
**Endpoint**: PDF library via MCP
**Tipo**: MCP (locale)

**Perché aggiungerlo**:
- Leggere PDF di documentazione, report, contratti
- Generare report PDF da memories
- Estrarre testo da PDF per arricchire memories

**Esempi d'uso con craft-memory**:
- `remember(content='Dal report PDF: ...', tags=['pdf', 'research'])`
- Generare snapshot PDF della memoria per backup

**Priorità**: 🟡 **Media**

---

#### 6.2 Excalidraw MCP

**Cosa fa**: Generare diagrammi Excalidraw da descrizioni testuali
**Endpoint**: Excalidraw JSON generator via MCP
**Tipo**: MCP (locale)

**Perché aggiungerlo**:
- Visualizzare architettura del sistema con diagrammi
- Generare diagrammi da memories (es. flusso decisionale visuale)
- Comunicare concetti complessi visivamente

**Esempi d'uso con craft-memory**:
- `remember(content='Diagramma architettura: ...', tags=['diagram'])`
- Auto-generare diagrammi delle relazioni tra memories

**Priorità**: 🟢 **Media**

---

#### 6.3 Image Generation API (Stability AI / OpenRouter / Gemini)

**Cosa fa**: Generazione immagini da prompt testuali
**Endpoint**: API REST (remoto con API key)

**Perché aggiungerlo**:
- Generare immagini per documentazione, presentazioni, social
- Creare visual assets per progetti
- L'agent ha già accesso a OpenRouter via connection `pi-api-key`

**Priorità**: 🔵 **Bassa** (valore marginale per craft-memory)

---

### 7. 🔧 DevOps & Infrastructure

#### 7.1 Docker MCP

**Cosa fa**: Gestione container Docker — list, start, stop, logs, exec
**Endpoint**: Docker socket via MCP
**Tipo**: MCP (locale)

**Perché aggiungerlo**:
- Gestire il container di craft-memory (quando containerizzato)
- Leggere logs, restartare servizi
- Eseguire comandi dentro container per debugging

**Priorità**: 🟡 **Media**

---

#### 7.2 Vercel CLI / Deploy MCP

**Cosa fa**: Deploy applicazioni su Vercel, gestione environment variables
**Endpoint**: Vercel API
**Tipo**: CLI o API

**Perché aggiungerlo**:
- Se Craft-Memory-UI è deployata su Vercel
- Deploy preview per testing
- Gestione environment variables

**Priorità**: 🟢 **Bassa** (se si usa Vercel)

---

### 8. 📊 Analytics & Observability

#### 8.1 Sentry MCP

**Cosa fa**: Accesso a error tracking, issue, performance, breadcrumbs
**Endpoint**: Sentry API via MCP
**Tipo**: MCP (remoto con token)

**Perché aggiungerlo**:
- Catturare errori come memories per debugging futuro
- Context sulle cause radice di bug
- Tracciare issue risolte come decision memories

**Esempi d'uso con craft-memory**:
- `remember(content='Fixato errore SENTRY-123: ...', tags=['sentry', 'bugfix'])`
- Auto-creare open loop da nuovi errori Sentry

**Priorità**: 🟡 **Media**

---

#### 8.2 Arize AI MCP

**Cosa fa**: LLM observability — tracing, evaluation, experiments, dataset management
**Endpoint**: Arize API via MCP/CLI
**Tipo**: API o MCP (remoto)

**Perché aggiungerlo**:
- Tracciamento delle performance degli LLM usati
- Evaluation dei prompt templates
- Benchmarking di diversi modelli

**Priorità**: 🔵 **Bassa** (valore solo se si fanno molti test LLM)

---

### 9. 🤖 AI & ML Specialized

#### 9.1 Copilot SDK / Copilot MCP

**Cosa fa**: Embedding di capacità agentiche, creazione di custom agents, gestione sessioni
**Endpoint**: GitHub Copilot SDK
**Tipo**: SDK + MCP

**Perché aggiungerlo**:
- Estendere le capacità agentiche oltre craft-memory
- Creare agenti specializzati con tool dedicati
- MCP server per tools custom

**Priorità**: 🟡 **Media**

---

#### 9.2 Tavily Research (Deep Research)

**Cosa fa**: Ricerca web approfondita multi-step con citazioni
**Endpoint**: Tavily Research API
**Tipo**: API (remoto con API key)

**Perché aggiungerlo**:
- Ricerche complesse su temi architetturali
- Competitive analysis, market research
- Studiare best practices prima di implementare

**Priorità**: 🟢 **Media**

---

#### 9.3 Embedding API (OpenAI / Voyage / Cohere)

**Cosa fa**: Generare embeddings per arricchire ricerche semantiche
**Endpoint**: API REST (remoto con API key)

**Perché aggiungerlo**:
- Craft-memory usa FTS5 per full-text search
- Aggiungere embeddings permetterebbe hybrid search (semantica + keyword)
- Migliorerebbe significativamente la qualità del retrieval

**Priorità**: 🟡 **Alta** — puoi usare OpenRouter già configurato

---

## 📋 Matrice Valore/Effort

| Source | Valore | Effort | Priorità |
|--------|--------|--------|----------|
| **GitHub MCP** | 🔴 Altissimo | 🟢 Basso (gh ext) | **1** |
| **Chrome DevTools** | 🔴 Altissimo | 🟢 Basso (built-in) | **2** |
| **Tavily Search** | 🔴 Altissimo | 🟢 Basso (API key) | **3** |
| **Slack MCP** | 🔴 Altissimo | 🟡 Medio (OAuth) | **4** |
| **Notion MCP** | 🟡 Alto | 🟡 Medio (token) | **5** |
| **Gmail MCP** | 🟡 Alto | 🟡 Medio (OAuth) | **6** |
| **Embedding API** | 🟡 Alto | 🟡 Medio (integrazione) | **7** |
| **Sentry MCP** | 🟡 Medio | 🟢 Basso (token) | **8** |
| **PDF Tool** | 🟡 Medio | 🟢 Basso (npm/pkg) | **9** |
| **Docker MCP** | 🟢 Medio | 🟢 Basso (socket) | **10** |
| **Excalidraw** | 🟢 Medio | 🟢 Basso (MCP) | **11** |
| **Outlook/Calendar** | 🟢 Medio | 🟡 Medio (OAuth) | **12** |
| **Supabase MCP** | 🟢 Medio | 🟡 Medio (config) | **13** |
| **Playwright MCP** | 🟢 Medio | 🟢 Basso (npm) | **14** |
| **Copilot SDK** | 🟡 Medio | 🟠 Alto (SDK) | **15** |
| **Confluence MCP** | 🟢 Basso | 🟡 Medio (token) | **16** |
| **Vercel Deploy** | 🔵 Basso | 🟢 Basso (CLI) | **17** |
| **Image Gen** | 🔵 Basso | 🟢 Basso (API key) | **18** |
| **GitLab MCP** | 🔵 Basso | 🟢 Basso (token) | **19** |
| **Linear MCP** | 🔵 Basso | 🟡 Medio (OAuth) | **20** |
| **Arize AI** | 🔵 Basso | 🟠 Alto (setup) | **21** |
| **PostgreSQL MCP** | 🔵 Basso | 🟡 Medio (creds) | **22** |
| **Filesystem MCP** | 🔵 Basso | 🟢 Basso (locale) | **23** |

---

## 🎯 Raccomandazione Roadmap

### Sprint 1: Foundation 🔴
Aggiungere le fonti con **massimo valore a minimo effort**:

```
[ ] GitHub MCP
    └── gh extension install github/gh-mcp
    └── Abilita: gestione issues, PR, progetti dal workspace

[ ] Chrome DevTools MCP
    └── Già disponibile come source type nel framework
    └── Abilita: browser automation, screenshot, debugging UI

[ ] Tavily / Web Search
    └── Registrarsi a tavily.com per API key
    └── Configurare come source type 'api'
    └── Abilita: ricerca web, fact-checking, documentazione live
```

**Perché questi tre**:
- Richiedono solo pochi minuti di setup (no OAuth complesso)
- Abilitano capability completamente nuove per l'agent
- Si integrano naturalmente con craft-memory: ogni risultato può diventare una memory

---

### Sprint 2: Context Enrichment 🟡
Aggiungere fonti di contesto esterno:

```
[ ] Slack MCP
    └── OAuth via source_slack_oauth_trigger
    └── Abilita: cattura decisioni da chat, cercare discussioni passate

[ ] Gmail MCP
    └── OAuth via source_google_oauth_trigger
    └── Abilita: contesto da email, decisioni formali

[ ] Notion MCP
    └── Configurare Notion Integration + token
    └── Abilita: lettura documentazione, specifiche, meeting note
```

**Perché questi tre**:
- Sono le fonti più ricche di **contesto decisionale informale**
- Ogni giorno generano informazioni che altrimenti vanno perse
- Permettono a craft-memory di catturare decisioni in tempo reale

---

### Sprint 3: Intelligence Layer 🟡
Aggiungere capacità di ragionamento più avanzato:

```
[ ] Embedding API (via OpenRouter già configurato)
    └── Usa la connection 'pi-api-key' (OpenRouter)
    └── Abilita: hybrid search in craft-memory
    └── Opzioni: voyage-3, jina-embeddings-v3, o同类 su OpenRouter

[ ] Tavily Research (deep research)
    └── Livello premium di Tavily
    └� Abilita: ricerche multi-step con citazioni
```

**Perché questi due**:
- Le embeddings migliorano la qualità del retrieval di craft-memory
- Il deep research permette analisi approfondite automatiche

---

### Sprint 4: Platform Integration 🟢
Completare con fonti specializzate:

```
[ ] Docker MCP
[ ] Sentry MCP
[ ] PDF Tool MCP
[ ] Excalidraw MCP
[ ] Outlook/Calendar (se Microsoft ecosystem)
```

**Perché in ritardo**:
- Valore più situazionale
- Richiedono configurazioni specifiche
- Non bloccanti per il core workflow

---

## 🔧 Note di Configurazione

### Come aggiungere un Source

```bash
# 1. Crea directory nel workspace
mkdir -p ~/.craft-agent/workspaces/auresys-backend/sources/<slug>/

# 2. Crea config.json
# Vedi esempio sotto

# 3. Aggiungi icon (opzionale)
# 4. Testa il source
# Usa il tool mcp__session__source_test per validare e attivare
```

### Template config.json per MCP esterno

```json
{
  "name": "Nome Source",
  "slug": "nome-source",
  "enabled": false,
  "type": "mcp",
  "icon": "🔌",
  "tagline": "Breve descrizione",
  "mcp": {
    "url": "http://localhost:<port>/mcp",
    "transport": "http",
    "authType": "none"
  }
}
```

### Template config.json per API esterna

```json
{
  "name": "Nome API",
  "slug": "nome-api",
  "enabled": false,
  "type": "api",
  "icon": "🔌",
  "tagline": "Breve descrizione",
  "api": {
    "baseUrl": "https://api.esempio.com",
    "authType": "bearer"
  }
}
```

---

## 🔗 Integrazione con Craft Memory

Ogni source dovrebbe, idealmente, integrarsi con craft-memory in uno di questi modi:

1. **Label-triggered**: Quando un'azione importante avviene tramite il source, l'agent aggiunge una label (`important`, `fact-candidate`) che triggera l'automazione `LabelAdd` → salvataggio in memoria

2. **Automazione dedicata**: Creare automazioni specifiche per eventi del source (es. `PostToolUse` per `gh create issue` → `remember`)

3. **Session context**: All'inizio sessione, usare i sources per recuperare contesto rilevante (es. issue assegnate, email non lette, notifiche Slack)

---

## 📝 Riferimenti

- **ADRs**: `docs/adr/` — decisioni architetturali craft-memory
- **Automazioni esistenti**: `craft-agents/automations.json`
- **Architettura**: `ARCHITECTURE.md`
- **Docs framework**: `~/.craft-agent/docs/`
