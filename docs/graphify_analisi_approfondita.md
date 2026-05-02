# Graphify — Analisi Architetturale Approfondita

> **Documento di analisi** basato su studio incrociato di Graphify (safishamsi/graphify) e  
> EverOS (EverMind-AI/EverOS) come contesto di riferimento.
>
> *Data:* 2026-05-02  
> *Versione analizzata:* Graphify v0.6.2 (39.6k ★ GitHub) | EverOS (4.3k ★ GitHub)

---

## Indice

1. [Premessa: Perché EverOS come Contesto](#1-premessa-perché-everos-come-contesto)
2. [Cos'è Graphify](#2-cosè-graphify)
3. [Architettura della Pipeline](#3-architettura-della-pipeline)
4. [Estrazione Multi-Modale](#4-estrazione-multi-modale)
   - 4.1 [AST Deterministico (Tree-sitter)](#41-ast-deterministico-tree-sitter)
   - 4.2 [Estrazione Semantica (LLM)](#42-estrazione-semantica-llm)
   - 4.3 [Trascrizione Audio/Video](#43-trascrizione-audiovideo)
   - 4.4 [Estrazione da Documenti Office](#44-estrazione-da-documenti-office)
   - 4.5 [SQL Deterministico](#45-sql-deterministico)
5. [Knowledge Graph Builder](#5-knowledge-graph-builder)
6. [Leiden Community Detection](#6-leiden-community-detection)
7. [God Nodes e Surprising Connections](#7-god-nodes-e-surprising-connections)
8. [Sistema di Confidence](#8-sistema-di-confidence)
9. [Output e Formati](#9-output-e-formati)
10. [Integrazione con AI Coding Assistants](#10-integrazione-con-ai-coding-assistants)
    - 10.1 [Sempre-on vs Trigger Esplicito](#101-sempre-on-vs-trigger-esplicito)
    - 10.2 [Piattaforme Supportate](#102-piattaforme-supportate)
11. [CLI Command Reference](#11-cli-command-reference)
12. [Team Workflows e Git Hooks](#12-team-workflows-e-git-hooks)
13. [Grafici Cross-Repo e Merge](#13-grafici-cross-repo-e-merge)
14. [Sicurezza e Privacy](#14-sicurezza-e-privacy)
15. [Metriche e Benchmark](#15-metriche-e-benchmark)
16. [Confronto con Alternative](#16-confronto-con-alternative)
17. [Penpax — L'Enterprise Layer](#17-penpax--lenterprise-layer)
18. [Analisi Critica](#18-analisi-critica)
    - 18.1 [Punti di Forza](#181-punti-di-forza)
    - 18.2 [Limitazioni](#182-limitazioni)
    - 18.3 [Rischio Lock-in su Assistants](#183-rischio-lock-in-su-assistants)
19. [Conclusioni e Applicabilità](#19-conclusioni-e-applicabilità)

---

## 1. Premessa: Perché EverOS come Contesto

Questo documento analizza **Graphify** alla luce del contesto fornito da **EverOS** (EverMind-AI), un Memory Operating System per agenti AI. Il parallelismo è significativo:

| Dimensione | Graphify | EverOS (EverMind) |
|---|---|---|
| **Focus primario** | Knowledge graph da codebase per coding assistants | Memoria a lungo termine per agenti autonomi |
| **Input** | Codice, documenti, paper, immagini, video, audio | Conversazioni, interazioni multi-sessione |
| **Core** | Grafo NetworkX + Leiden clustering | EverCore (memoria biologica) + HyperMem (ipergrafo) |
| **Output** | graph.html + GRAPH_REPORT.md + graph.json | API REST per retrieval memoria |
| **Destinatari** | Sviluppatori, AI coding assistants | Agenti AI, companion, sistemi multi-agente |
| **Licenza** | MIT License | Apache 2.0 |
| **Stars** | 39.6k | 4.3k |

**Punto chiave:** Mentre Graphify costruisce una **mappa strutturale e concettuale statica** di una codebase, EverOS fornisce una **memoria persistente ed evolutiva** per agenti. I due approcci sono ortogonali e potenzialmente complementari.

---

## 2. Cos'è Graphify

Graphify è un **knowledge graph skill open-source** per AI coding assistants (Claude Code, OpenAI Codex, Cursor, Gemini CLI, GitHub Copilot CLI, e oltre 15 piattaforme). Trasforma qualsiasi repository — codice, documentazione, paper accademici, diagrammi, screenshot, video, audio — in un grafo interattivo e interrogabile.

**Mantainer:** Safi Shamsi (@safishamsi su GitHub)  
**Linguaggio:** Python 3.10+  
**Dipendenze Core:** NetworkX + Tree-sitter + vis.js + graspologic (Leiden)  
**Distribuzione:** `pip install graphifyy` (PyPI)  
**Licenza:** MIT  
**Repo:** `github.com/safishamsi/graphify` (~241 commit, v0.6.2)

### Filosofia di Design

Graphify si basa su quattro principi fondamentali:

1. **Struttura > Embedding.** Il grafo è costruito su relazioni strutturali reali (call graph, import, ereditarietà), non su similarità vettoriale. Le connessioni semantiche si aggiungono *dopo*.
2. **Multi-modale nativo.** Codice, documenti, immagini, video, audio — tutto converge nello stesso grafo con lo stesso schema di nodi/archi.
3. **Onesto sulle congetture.** Ogni arco è targato EXTRACTED (certezza), INFERRED (inferenza ragionata con confidence score) o AMBIGUOUS (da verificare).
4. **Niente server, niente telemetria.** L'unica chiamata di rete è verso il modello LLM configurato per l'estrazione semantica.

---

## 3. Architettura della Pipeline

Graphify è una **pipeline multi-stadio**, dove ogni stadio è un modulo isolato e indipendente:

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌────────────┐    ┌──────────┐
│ detect  │───→│ extract  │───→│  build   │───→│ cluster  │───→│  analyze  │───→│   report   │───→│  export  │
│         │    │          │    │          │    │          │    │           │    │            │    │          │
│ raccolta│    │ AST +    │    │ NetworkX │    │ Leiden   │    │ god nodes │    │ GRAPH_REP │    │ HTML /   │
│ files   │    │ LLM      │    │ graph    │    │ comunità │    │ surprises │    │ ORT.md    │    │ JSON /   │
└─────────┘    └──────────┘    └──────────┘    └──────────┘    └───────────┘    └────────────┘    └──────────┘
```

### Moduli di Supporto

| Modulo | File | Funzione |
|---|---|---|
| **ingest.py** | Download URL | Download di paper, tweet, contenuti web con limiti di size/timeout |
| **cache.py** | SHA256 cache | Cache incrementale — le re-run processano solo file cambiati |
| **security.py** | Validazione input | Path containment, URL validation (solo http/https), HTML-escaping |
| **watch.py** | Auto-sync | Ricostruzione automatica del grafo al cambiamento dei file |
| **serve.py** | MCP server | Espone graph.json come server MCP stdio per query strutturate |

### Flusso a Tre Passate

1. **AST Pass (locale, deterministico).** Tree-sitter analizza ogni file di codice. Nessuna chiamata LLM, nessuna rete. Il risultato è un insieme di nodi strutturali (classi, funzioni, metodi) e archi (call graph, import, ereditarietà).
2. **Trascrizione (locale, opzionale).** Whisper (faster-whisper) trascrive file audio/video. L'audio non lascia mai la macchina.
3. **Semantic Pass (LLM).** Sub-agenti AI (Claude, GPT-4, ecc.) processano in parallelo documenti (.md, .pdf), immagini, trascrizioni e file YAML per estrarre concetti, relazioni e razionale di design.

**Nota importante:** Il codice sorgente non viene mai inviato al modello LLM. Solo descrizioni semantiche di documenti e immagini attraversano la rete.

---

## 4. Estrazione Multi-Modale

Graphify supporta un'ampia gamma di tipi di file, ciascuno con un'estrazione specializzata:

| Tipo | Estensioni | Metodo di Estrazione |
|---|---|---|
| **Codice** | `.py .ts .js .jsx .tsx .mjs .go .rs .java .c .cpp .rb .cs .kt .scala .php .swift .lua .zig .ps1 .ex .exs .m .mm .jl .vue .svelte` | Tree-sitter AST + call graph + docstring/comment rationale |
| **SQL** | `.sql` | AST deterministico: tabelle, viste, funzioni, foreign key, FROM/JOIN |
| **Documenti** | `.md .mdx .html .txt .rst .yaml .yml` | Estrazione semantica via LLM (concetti + relazioni + razionale) |
| **Office** | `.docx .xlsx` | Convertiti in markdown → estrazione semantica |
| **Paper** | `.pdf` | Citation mining + concept extraction |
| **Immagini** | `.png .jpg .webp .gif` | Vision LLM (screenshot, diagrammi, testo in altre lingue) |
| **Video/Audio** | `.mp4 .mov .mkv .webm .avi .m4v .mp3 .wav .m4a .ogg` | Whisper (locale) + estrazione semantica |
| **YouTube/URL** | Qualsiasi URL video | yt-dlp → Whisper → estrazione |

### 4.1 AST Deterministico (Tree-sitter)

Graphify utilizza **Tree-sitter**, un parser incrementale con grammatiche collaudate per tutti i linguaggi mainstream. Vantaggi:

- **Zero rete.** Il codice sorgente non lascia mai la macchina durante il passaggio AST.
- **Performance.** Parsing O(dimensione file). L'intero passaggio AST su un repository modesto richiede secondi.
- **Uniformità.** Ogni linguaggio espone la stessa struttura nodo/arco al graph builder.

#### Cosa viene estratto dall'AST

- **Nodi strutturali:** classi, funzioni, metodi, moduli, traits/interfacce, variabili top-level.
- **Call-graph edges:** ogni sito di chiamata risolto diventa un arco `calls` targato `EXTRACTED` (confidence 1.0). Cross-file per tutti i linguaggi.
- **Import edges:** archi `imports` a livello di modulo per coesione delle comunità.
- **Rationale nodes:** docstring e commenti di razionale (`# NOTE:`, `# IMPORTANT:`, `# HACK:`, `# WHY:`) sollevati come nodi separati con archi `rationale_for`.

#### Linguaggi Supportati (25)

| Famiglia | Linguaggi |
|---|---|
| **Scripting** | Python, JavaScript, TypeScript, Ruby, PHP, Lua, PowerShell, Dart |
| **Systems** | Go, Rust, C, C++, Zig, Swift, Objective-C |
| **JVM/.NET** | Java, Kotlin, Scala, C# |
| **BEAM** | Elixir |
| **Frontend** | Vue, Svelte |
| **Hardware** | Verilog, SystemVerilog |
| **Altri** | Julia |

### 4.2 Estrazione Semantica (LLM)

Questa passata utilizza il modello LLM configurato dall'assistant (Claude per Claude Code, GPT-4 per Codex, ecc.) per estrarre:

- **Concetti** da documentazione in linguaggio naturale
- **Relazioni semantiche** non evidenti dalla struttura del codice
- **Design rationale** da commenti, commit messaggi, discussioni
- **Relazioni cross-file** tra codice e documentazione

**Caching:** SHA256 sui file processati. Le re-run estraggono solo file cambiati.

### 4.3 Trascrizione Audio/Video

- Dipendenza opzionale: `pip install graphifyy[video]`
- **faster-whisper** per trascrizione locale (l'audio non lascia la macchina)
- **yt-dlp** per download audio da URL video
- Modello Whisper configurabile: `--whisper-model medium` per accuratezza maggiore
- Le trascrizioni sono cachate in `graphify-out/transcripts/`
- Il prompt di trascrizione è domain-aware, derivato dai god nodes del corpus

### 4.4 Estrazione da Documenti Office

- Dipendenza opzionale: `pip install graphifyy[office]`
- Supporto per `.docx` e `.xlsx`
- Conversione a markdown → estrazione semantica via LLM

### 4.5 SQL Deterministico

- Dipendenza opzionale: `pip install graphifyy[sql]`
- Estrazione AST diretta senza LLM
- Tabelle, viste, funzioni, foreign key, e archi FROM/JOIN mappati direttamente nel grafo

---

## 5. Knowledge Graph Builder

Il terzo stadio della pipeline unisce tutti i nodi e archi in un **grafo NetworkX**.

### Schema del Grafo

**Nodi:**
- `class`, `function`, `method`, `module`, `interface`, `variable`
- `concept`, `design_decision`, `rationale`
- `paper_section`, `diagram`, `screenshot`
- `sql_table`, `sql_view`, `sql_function`

**Archi:**
- `calls` — chiamata di funzione (EXTRACTED)
- `imports` — dipendenza tra moduli (EXTRACTED)
- `inherits` — ereditarietà (EXTRACTED)
- `rationale_for` — spiega perché esiste (EXTRACTED da commenti)
- `semantically_similar_to` — relazione concettuale (INFERRED)
- `part_of` — appartenenza a gruppo (EXTRACTED/INFERRED)
- `implements` — implementazione interfaccia (EXTRACTED, Java)
- `extends` — estensione classe (EXTRACTED, Java)
- `foreign_key` — relazione FK (EXTRACTED, SQL)
- `from_join` — relazione da clausole FROM/JOIN (EXTRACTED, SQL)

### Costo di Query

Il grafo compresso ha un costo di query molto inferiore alla lettura dei file raw:

> Su un corpus misto (52 file: 3 repo Karpathy + 5 paper + 4 diagrammi):  
> **Query media: ~1.7k token** sul grafo vs **~123k token** leggendo i file raw  
> → **Riduzione 71.5×**

La compressione scala con la dimensione del corpus. Per corpus piccoli (es. 6 file), il valore è nella chiarezza strutturale più che nella compressione.

---

## 6. Leiden Community Detection

Graphify raggruppa nodi correlati in **comunità** usando l'algoritmo **Leiden** sulla topologia del grafo. Nessun embedding vettoriale, nessun vector database.

### Perché Leiden invece di embedding

La maggior parte dei sistemi code-RAG:
1. Chunkizza il repository
2. Embedia ogni chunk
3. Clusterizza i vettori risultanti

Graphify evita questo approccio perché:

| Problema | Soluzione Graphify |
|---|---|
| **Struttura persa.** La similarità per embedding ignora call graph e import | Leiden opera sugli archi reali del grafo |
| **Cluster opachi.** Due chunk nello stesso bucket senza sapere perché | Ogni arco ha tipo, fonte e confidence score |
| **Infrastruttura extra.** Vector store = altro servizio, altro auth, altro costo | Zero infrastruttura: puro Python, tutto locale |

### Come la similarità semantica partecipa

Il semantic pass emette archi `semantically_similar_to` tra nodi concettualmente correlati ma senza connessione strutturale. Leiden li vede e li include nella densità di archi, quindi le comunità si formano sia per affinità strutturale che concettuale.

### Stack Tecnologico

- **Leiden:** implementato via `graspologic`
- **Graph layer:** NetworkX
- **Output:** ogni comunità diventa una sezione in `GRAPH_REPORT.md`

---

## 7. God Nodes e Surprising Connections

### God Nodes

I **god nodes** sono i nodi con il grado più alto nel grafo — i concetti attraverso cui passa tutto. Esempi reali:

- Corpus httpx: `Client`, `AsyncClient`, `Response`, `Request`
- Corpus Karpathy: i nodi relativi a `CfgNode`, `GPT`, `Transformer`

I god nodes danno immediatamente la mappa mentale di un sistema: "se vuoi capire questo progetto, inizia da questi concetti".

### Surprising Connections

Graphify identifica e ranka le connessioni inaspettate usando uno score composito. Le connessioni codice→paper rankano più in alto di codice→codice, perché cross-domain. Ogni surprising connection include una spiegazione in linguaggio naturale.

**Esempio dal corpus httpx:** l'arco `DigestAuth → Response` è stato segnalato come sorprendente perché collega autenticazione e risposta HTTP attraverso strati diversi dell'architettura.

### Suggested Questions

Il report genera 4-5 domande che il grafo è unicamente in grado di rispondere, basate sulla struttura delle comunità e sulle connessioni sorprendenti.

---

## 8. Sistema di Confidence

Graphify implementa un **sistema di provenance** per ogni arco nel grafo:

| Tag | Significato | Confidence | Origine |
|---|---|---|---|
| `EXTRACTED` | Trovato direttamente nel codice sorgente | 1.0 (certezza) | Tree-sitter AST pass |
| `INFERRED` | Inferenza ragionevole | 0.0–1.0 (score) | LLM semantic pass |
| `AMBIGUOUS` | Il modello non è sicuro | Segnalato per revisione | LLM semantic pass |

Questo sistema è cruciale perché permette a chi esamina il grafo di distinguere sempre tra **fatti** (struttura del codice) e **interpretazioni** (relazioni semantiche inferite dal LLM).

---

## 9. Output e Formati

Tutti gli output sono scritti in `graphify-out/`:

```
graphify-out/
├── graph.html          # Grafo interattivo (vis.js) - clicca, cerca, filtra per comunità
├── GRAPH_REPORT.md     # Report di una pagina: god nodes, sorprese, domande suggerite
├── graph.json          # Grafo persistente e interrogabile (riusabile tra sessioni)
├── cache/              # Cache SHA256 per estrazione incrementale
├── transcripts/        # Trascrizioni audio/video (opzionale)
├── manifest.json       # Manifest mtime-based (sempre in .gitignore)
└── cost.json           # Tracciamento token (locale, non condiviso)
```

### Formati di Esportazione

| Formato | Flag | Utilizzo |
|---|---|---|
| HTML interattivo | (default) | `vis.js` - nodi cliccabili, ricerca, filtro comunità |
| Markdown (wiki) | `--wiki` | Articoli stile Wikipedia per comunità + index.md |
| Obsidian vault | `--obsidian` | Vault navigabile in Obsidian |
| SVG | `--svg` | Grafo statico vettoriale |
| GraphML | `--graphml` | Importabile in Gephi, yEd |
| Neo4j Cypher | `--neo4j` | Script cypher.txt da eseguire su Neo4j |
| Neo4j push | `--neo4j-push bolt://...` | Push diretto a Neo4j live |
| MCP stdio | `--mcp` | Server MCP per query strutturate ripetute |

---

## 10. Integrazione con AI Coding Assistants

Graphify supporta oltre **15 piattaforme** di AI coding assistant, ognuna con un meccanismo di integrazione specifico.

### 10.1 Sempre-On vs Trigger Esplicito

Graphify opera su due livelli di integrazione:

**Sempre-on (hook/plugin/rule):**
- Il `GRAPH_REPORT.md` (riassunto di una pagina con god nodes, comunità e connessioni sorprendenti) viene iniettato in ogni conversazione.
- L'assistant legge il report prima di cercare file, navigando per struttura invece che per keyword matching.
- Copre la maggior parte delle domande quotidiane.

**Trigger esplicito (`/graphify` commands):**
- `/graphify query`, `/graphify path`, `/graphify explain` navigano il `graph.json` raw, hop per hop.
- Tracciano path esatti tra nodi e mostrano dettagli a livello di arco (tipo relazione, confidence, source location).
- Si usano per domande specifiche, non per orientamento generale.

> **Metafora:** il sempre-on dà all'assistant una **mappa**. I comandi `/graphify` gli permettono di **navigare la mappa con precisione**.

### 10.2 Piattaforme Supportate

| Piattaforma | Comando Install | Meccanismo Always-On |
|---|---|---|
| **Claude Code** | `graphify claude install` | CLAUDE.md + PreToolUse hook (prima di Glob/Grep) |
| **OpenAI Codex** | `graphify codex install` | AGENTS.md + PreToolUse hook in `.codex/hooks.json` |
| **OpenCode** | `graphify opencode install` | AGENTS.md + `tool.execute.before` plugin |
| **Cursor** | `graphify cursor install` | `.cursor/rules/graphify.mdc` con `alwaysApply: true` |
| **Gemini CLI** | `graphify gemini install` | GEMINI.md + BeforeTool hook |
| **GitHub Copilot CLI** | `graphify copilot install` | Skill file in `~/.copilot/skills/` |
| **VS Code Copilot Chat** | `graphify vscode install` | `.github/copilot-instructions.md` |
| **Aider** | `graphify aider install` | AGENTS.md |
| **OpenClaw** | `graphify claw install` | AGENTS.md |
| **Factory Droid** | `graphify droid install` | AGENTS.md (parallel dispatch con Task tool) |
| **Trae** | `graphify trae install` | AGENTS.md (parallel dispatch con Agent tool) |
| **Hermes** | `graphify hermes install` | AGENTS.md + `~/.hermes/skills/` |
| **Kiro IDE/CLI** | `graphify kiro install` | `.kiro/skills/` + `.kiro/steering/graphify.md` (`inclusion: always`) |
| **Google Antigravity** | `graphify antigravity install` | `.agents/rules/` + `.agents/workflows/` |
| **Codex (skill call)** | Usa `$graphify .` invece di `/graphify .` | Richiede `multi_agent = true` in config |

---

## 11. CLI Command Reference

### Build & Scan

| Comando | Descrizione |
|---|---|
| `/graphify` | Esegui sulla directory corrente |
| `/graphify ./raw` | Esegui su una cartella specifica |
| `/graphify ./raw --mode deep` | Estrazione più aggressiva di archi INFERRED |
| `/graphify ./raw --update` | Re-estrai solo file cambiati, mergia nel grafo esistente |
| `/graphify ./raw --cluster-only` | Rielabora clustering su grafo esistente |
| `/graphify ./raw --no-viz` | Salta HTML, solo report + JSON |
| `/graphify ./raw --watch` | Auto-sync in background |

### Add External Sources

| Comando | Descrizione |
|---|---|
| `/graphify add <URL>` | Scarica paper/tweet/URL e aggiorna grafo |
| `/graphify add <URL> --author "Name"` | Tagga l'autore originale |
| `/graphify add <URL> --contributor "Name"` | Tagga chi ha aggiunto il contenuto |
| `/graphify add <video-url>` | Download audio, trascrizione, aggiunta al grafo |

### Query & Navigation

| Comando | Descrizione |
|---|---|
| `/graphify query "..."` | Query semantica sul grafo |
| `/graphify query "..." --dfs` | Trace specific path |
| `/graphify query "..." --budget 1500` | Limita token restituiti |
| `/graphify path "NodeA" "NodeB"` | Shortest path tra due nodi |
| `/graphify explain "Node"` | Spiegazione completa di un nodo |

### Export

| Comando | Descrizione |
|---|---|
| `/graphify ./raw --wiki` | Wiki markdown per comunità |
| `/graphify ./raw --obsidian` | Vault Obsidian |
| `/graphify ./raw --svg` | Grafo SVG |
| `/graphify ./raw --graphml` | GraphML (Gephi, yEd) |
| `/graphify ./raw --neo4j` | Script Cypher |
| `/graphify ./raw --neo4j-push ...` | Push a Neo4j |
| `/graphify ./raw --mcp` | Avvia server MCP stdio |

### Git Hooks

| Comando | Descrizione |
|---|---|
| `graphify hook install` | Installa hook post-commit e post-checkout |
| `graphify hook uninstall` | Rimuove hook |
| `graphify hook status` | Verifica stato hook |

### Cross-Repo

| Comando | Descrizione |
|---|---|
| `graphify clone <URL>` | Clona repo e builda grafo |
| `graphify clone <URL> --branch b --out ./dir` | Clone con opzioni |
| `graphify merge-graphs g1.json g2.json` | Merge di due grafi |

---

## 12. Team Workflows e Git Hooks

Graphify è progettato per essere **committato in git**:

```
# Tieni graphify-out/ nel repo
graphify-out/
├── graph.html
├── GRAPH_REPORT.md
└── graph.json

# Ignora (opzionale)
graphify-out/cache/        # pesante, ricostruibile
graphify-out/manifest.json # sempre ignorato (mtime-based)
graphify-out/cost.json     # locale
```

### Flusso Team Consigliato

1. Un membro del team esegue `/graphify .` e committa `graphify-out/`
2. Tutti pullano — l'assistant legge `GRAPH_REPORT.md` immediatamente
3. Hook post-commit (`graphify hook install`) ricostruisce automaticamente il grafo
4. Per modifiche a documenti/paper, eseguire `/graphify --update`

### .graphifyignore

Stessa sintassi di `.gitignore`, incluso `!` per re-includere. Funziona su sotto-cartelle. Rispetta i confini VCS (`.git`, `.hg`). Supporta commenti inline:

```
vendor/
node_modules/
*.generated.py
AGENTS.md           # non estrarre le tue stesse istruzioni come conoscenza
CLAUDE.md
docs/translations/  # contenuto generato
```

---

## 13. Grafici Cross-Repo e Merge

Graphify supporta la fusione di grafi da repository diversi:

```bash
graphify merge-graphs repo1/graphify-out/graph.json repo2/graphify-out/graph.json
graphify merge-graphs g1.json g2.json g3.json --out cross-repo.json
```

Questo permette di:
- Unire grafo del backend + grafo del frontend + grafo dell'infrastruttura
- Creare una vista unificata di un sistema distribuito
- Incrociare dipendenze tra servizi

---

## 14. Sicurezza e Privacy

Graphify ha un posture **security-first**:

### Protezioni Implementate

| Protezione | Implementazione |
|---|---|
| **URL validation** | Solo protocolli http/https |
| **Size limits** | Download con limiti di dimensione |
| **Timeout** | Download con timeout configurabili |
| **Path containment** | Output paths verificati per directory traversal |
| **HTML-escaping** | Node labels escapati per prevenire XSS |
| **No telemetria** | Zero analytics, zero tracking |
| **SSRF prevention** | Restrizione URL a protocolli consentiti |

### Privacy del Codice

- **Il codice sorgente non viene mai inviato al modello LLM.**
- Tree-sitter processa tutto il codice localmente.
- Solo **descrizioni semantiche** di documenti e immagini vanno al modello API.
- Audio/video rimangono locali via faster-whisper.
- L'unica chiamata di rete è per l'estrazione semantica, usando l'API key già configurata.

---

## 15. Metriche e Benchmark

### Token Reduction

| Corpus | Files | Riduzione | Output |
|---|---|---|---|
| Karpathy repos + 5 paper + 4 immagini | 52 | **71.5×** | `worked/karpathy-repos/` |
| Graphify source + Transformer paper | 4 | **5.4×** | `worked/mixed-corpus/` |
| httpx (libreria Python sintetica) | 6 | ~1× | `worked/httpx/` |

La riduzione scala con la dimensione del corpus. Per 6 file (~1×), il valore è nella chiarezza strutturale, non nella compressione.

### Scalabilità

- Tree-sitter parsing e NetworkX scaling lineare con la dimensione del codice.
- Su un corpus di ~500k parole, le query BFS subgraph restano intorno a ~2k token (vs ~670k naive).

---

## 16. Confronto con Alternative

| Progetto | Focus | Forza | Limite vs Graphify |
|---|---|---|---|
| **Sourcegraph** | Cross-repo code search | Navigazione enterprise-grade | Non è un knowledge graph; limitato su design semantics |
| **Code2Vec** | Function-level embeddings | Retrieval vettoriale & classificazione | Nessuna struttura a grafo, nessun input multi-modale |
| **Neo4j** | Database grafo generale | Query Cypher potenti | Non genera grafi dal codice |

### Perché Graphify è Diverso

1. **Zero infrastruttura:** Non richiede server, database, o vector store.
2. **Multi-modale nativo:** Codice + documenti + immagini + video + audio nello stesso grafo.
3. **Provenance:** Ogni arco è tracciato alla fonte (EXTRACTED/INFERRED/AMBIGUOUS).
4. **Design rationale:** Cattura non solo *cosa* fa il codice, ma *perché* è stato scritto così.
5. **Integrazione assistant:** Funziona nativamente con oltre 15 piattaforme di AI coding.

---

## 17. Penpax — L'Enterprise Layer

**Penpax** è il layer enterprise costruito sopra Graphify. Mentre Graphify trasforma una cartella di file in un knowledge graph, Penpax applica lo stesso grafo all'intera vita lavorativa — in modo continuo.

| Dimensione | Graphify | Penpax |
|---|---|---|
| **Input** | Una cartella di file | Cronologia browser, meeting, email, file, codice — tutto |
| **Esecuzione** | On demand | Continua in background |
| **Scope** | Un progetto | L'intera vita lavorativa |
| **Query** | CLI / MCP / AI skill | Linguaggio naturale, sempre attivo |
| **Privacy** | Locale di default | Completamente on-device, nessun cloud |

Penpax è pensato per avvocati, consulenti, dirigenti, medici, ricercatori — chiunque lavori centinaia di conversazioni e documenti che non può mai ricostruire completamente. Free trial in arrivo.

---

## 18. Analisi Critica

### 18.1 Punti di Forza

1. **Rivoluzionario per codebase comprehension.** Graphify risolve il problema di Karpathy ("tengo una cartella `/raw` con paper, tweet, screenshot, note, ma non riesco a navigarla"). La compressione 71.5× è un dato oggettivo e misurabile.

2. **Approccio ibrido AST + LLM.** La separazione tra fatti strutturali (EXTRACTED, deterministici) e inferenze semantiche (INFERRED, probabilistici) è elegante e pragmatica. Il codice non viene mai esposto al LLM.

3. **Zero infrastruttura.** A differenza di Sourcegraph (server) o Neo4j (database), Graphify è `pip install` e via. Questo abbatte la barriera all'adozione.

4. **Integrazione multi-piattaforma.** Il supporto per oltre 15 piattaforme con meccanismi sempre-on diversi è un lavoro di ingegneria notevole.

5. **Grafo interrogabile persistentemente.** Il `graph.json` permette query anche settimane dopo, senza dover re-processare la codebase.

### 18.2 Limitazioni

1. **Dipendenza da LLM per estrazione semantica.** La quality del grafo dipende dalla quality del modello LLM sottostante. Se il modello produce inferenze scadenti, il grafo ne risente.

2. **Costo della prima run.** La prima estrazione costa token (LLM per documenti/immagini). Anche se l'autore sostiene che sia la qualità del grafo a giustificare il costo, per repository molto grandi il costo iniziale potrebbe essere significativo.

3. **Non è una memoria persistente.** A differenza di EverOS, Graphify non mantiene stato tra sessioni di agenti. È una mappa statica, non una memoria evolutiva.

4. **Scalabilità su repository enterprise.** Su repository con milioni di righe di codice e migliaia di file, la gestione del grafo NetworkX in memoria potrebbe diventare problematica.

5. **Lock-in sul formato.** Una volta che l'assistant si abitua a navigare via grafo, il formato `.graphifyignore` e la struttura `graphify-out/` diventano dipendenze del progetto.

6. **Assenza di ranking temporale.** Graphify non modella l'evoluzione temporale del codice. Non distingue tra codice attivo e legacy, o tra pattern recenti e obsoleti.

### 18.3 Rischio Lock-in su Assistants

Graphify si integra con 15+ piattaforme, ma ogni integrazione ha meccanismi diversi (hook, rules, AGENTS.md, skill). Questo significa che:

- **Cambiare assistant richiede re-installazione.**
- **Non tutti i meccanismi sono equivalenti.** Alcune piattaforme (Claude Code) supportano PreToolUse hook, altre (Aider, OpenClaw) solo AGENTS.md.
- **Il comportamento sempre-on varia.** Su alcune piattaforme è inaggirabile (hooks), su altre è solo una raccomandazione (AGENTS.md).

---

## 19. Conclusioni e Applicabilità

### Casi d'Uso Ideali

1. **Onboarding su codebase complesse.** Nuovo sviluppatore? `/graphify .` e ottieni una mappa navigabile in secondi.
2. **Repository misti codice + documentazione + paper.** Perfetto per repo di ricerca che includono paper, notebook, e codice.
3. **Cross-repo analysis.** Progetti che coinvolgono più repository (microservizi, monorepo).
4. **Code review architetturale.** Identificare rapidamente connessioni sorprendenti e dipendenze inaspettate.
5. **Team distributed.** Il `graphify-out/` committato in git fornisce una base di conoscenza condivisa.

### Relazione con EverOS

Graphify e EverOS operano a **layer diversi** del problema memoria/conoscenza:

```
Graphify:   Mappa strutturale di una codebase (conoscenza statica)
EverOS:     Memoria persistente per agenti (conoscenza dinamica ed evolutiva)
```

**Possibile integrazione:**
- Graphify fornisce la **comprensione strutturale iniziale** di una codebase
- EverOS mantiene la **memoria delle sessioni** e l'evoluzione delle conoscenze nel tempo
- Insieme potrebbero formare un sistema completo: Graphify come bootstrap layer, EverOS come persistence layer

### Verdetto

Graphify è uno strumento **eccezionale** per il suo dominio specifico: rendere le codebase navigabili da AI coding assistants. La combinazione di AST deterministico + estrazione semantica LLM + clustering Leiden è innovativa e ben implementata. La licenza MIT e l'assenza di telemetria lo rendono adatto anche per ambienti enterprise sensibili.

La limitazione principale è che risolve un problema di **comprensione statica** (capire il codice esistente), non di **memoria persistente** (ricordare tra sessioni). Per quest'ultimo, EverOS (o sistemi simili) sono complementari.

**Raccomandazione:** Utilizzare Graphify come layer di comprensione iniziale per codebase complesse, integrato con un sistema di memoria persistente (EverOS o equivalente) per mantenere il contesto attraverso le sessioni di sviluppo.

---

*Fine del documento — Analisi condotta su fonti pubbliche: graphify.net, github.com/safishamsi/graphify, github.com/EverMind-AI/EverOS, evermind.ai/everos.*
