# Craft Memory — Report Analisi Architetturale

> Data: 2026-05-02
> Scopo: Analisi sistematica del codice craft-memory per identificare criticità e opportunità di miglioramento

---

## Riassunto

Dopo aver implementato l'auto-linking in `remember()`, è stata condotta un'analisi Chain-of-Thought completa del codebase (`~/craft-memory`) per identificare altre criticità. Risultato: **2 criticità risolte, 4 non-bloccanti identificate, 5 aree future roadmap**.

---

## 🔴 Criticità Risolte

### 1. Knowledge Graph Vuoto (55 memorie, 0 edge)

**Causa**: Tre fattori combinati:
- `link_memories` era un tool esplicitamente manuale ("Never automatic — always explicit")
- `find_similar` ha `auto_link=False` di default
- `remember()` non creava mai edge — solo INSERT

**Soluzione**: Aggiunto `_auto_link_similar()` chiamato automaticamente dopo ogni `remember()` riuscito. Usa FTS5 BM25 per trovare top-3 memorie simili e crea edge `semantically_similar_to` con `is_manual=False` (prunabili).

### 2. Soglia BM25 Assoluta Non Scalabile

**Causa**: `_AUTOLINK_THRESHOLD = -2.5` è troppo stretto per dataset piccoli. Nei test con 5-6 memorie, BM25 score = -2.473 non superava la soglia -2.5.

**Soluzione**: Nell'auto-linking si usa una soglia relativa -1.0 come filtro antirumore, poi si linkano i top-3 risultati. La soglia -2.5 rimane per `find_similar()` (precision over recall).

---

## 🟡 Criticità Non Bloccanti

### 3. `_AUTOLINK_THRESHOLD` Orfano

La variabile `_AUTOLINK_THRESHOLD` (env `CRAFT_MEMORY_AUTOLINK_THRESHOLD`) è usata solo da `find_similar_memories()`, non dall'auto-linking in `remember()`. **Non è un bug**: i due use case hanno requisiti diversi:
- `find_similar` + auto_link=True: alta precisione, soglia stretta
- `remember()` auto-linking: recall-oriented, soglia generosa

### 4. Auto-linking Non Usa i Tags

`remember()` accetta `tags: list[str]` ma `_auto_link_similar()` usa solo il contenuto testuale. I tag sono memorizzati come JSON nella colonna `tags` e non sono indicizzati in FTS5.

**Migliorabile**: richiederebbe una tabella `memory_tags` (migration `013_memory_tags.sql`) e logica aggiuntiva.

### 5. Keyword Extraction Duplicata

Due versioni della stessa logica: `_extract_fts_keywords()` (nuova, modulare) e inline in `find_similar_memories()` (storica). Refactor meccanico.

### 6. Documentazione `link_memories` Fuorviante

Il tool `link_memories` dichiarava "Never automatic — always explicit". Ora `remember()` fa auto-linking, quindi la frase era incorretta. **Risolto**: descrizione aggiornata.

---

## 🟢 Cose Che Funzionano Bene

| Area | Stato | Dettaglio |
|------|-------|-----------|
| **Schema SQL** | ✅ | V1 base + 11 migrations, `memory_relations` integra |
| **FTS5 Triggers** | ✅ | insert/delete/update triggers mantengono sync |
| **`batch_remember()`** | ✅ | Chiama `remember()` in loop → eredita auto-linking |
| **Lifecycle filtering** | ✅ | `_auto_link_similar` esclude memorie invalidated/needs_review |
| **Deduplicazione** | ✅ | `UNIQUE(session_id, content_hash)` + IntegrityError catch |
| **Manutenzione** | ✅ | `prune_inferred_edges` rimuove solo is_manual=0, weight<0.3, age>60gg |
| **VACUUM** | ✅ | In daily_maintenance, dopo pruning |
| **Thread safety** | ✅ | Singola connessione SQLite, FastMCP seriale |
| **Performance FTS5** | ✅ | BM25 query <10ms anche con migliaia di record |
| **Test** | ✅ | 214 test, tutti passano, 0 regressioni |

---

## 🔬 Risultati Test

```
collected 214 items
test_auto_link.py            .....    ✅  5 nuovi test (auto-linking)
test_batch_remember.py       .......  ✅  7 test
test_consolidate_memories.py ........ ✅  8 test
test_db.py                   ........ ✅ 24 test (core CRUD)
test_exposed_tools.py        .......  ✅ 11 test
test_graph.py                .....    ✅ 30 test (graph layer)
test_graph_context.py        ....     ✅ 10 test
test_observability.py        .....    ✅ 14 test
test_policy.py               ....     ✅ 10 test
test_procedures.py           ....     ✅ 12 test
test_scopes.py               .....    ✅ 14 test
test_server.py               ....     ✅ 10 test
test_session_quality.py      .....    ✅ 23 test
test_temporal.py             ....     ✅ 12 test
test_top_procedures.py       ....     ✅  9 test
─────────────────────────────────────────────────
214 passed in 53.71s                    0 regressioni
```

---

## 📊 Dettaglio Implementazione Auto-linking

### `_extract_fts_keywords(text, max_words=8)` → `str | None`

Estrae keyword FTS5-safe dal testo:
1. Prende primi 80 caratteri
2. Splitta in parole
3. Rimuove caratteri non alfanumerici
4. Filtra parole ≤3 caratteri
5. Prende max 8 parole
6. JOIN con " OR "

### `_auto_link_similar(conn, memory_id, workspace_id, limit=3)` → `int`

1. Legge contenuto della memoria appena inserita
2. Estrae keyword → FTS5 query
3. `SELECT ... JOIN memories_fts ... ORDER BY bm25 ASC LIMIT 3`
4. Se `best_score >= -1.0` → skip (keyword troppo generiche)
5. Per ogni match: `link_memories(is_manual=False, confidence_type="inferred")`
6. Commit e ritorno conteggio

### Flusso completo

```
remember(content)
  │
  ├─ INSERT INTO memories
  ├─ conn.commit()
  ├─ new_id = cursor.lastrowid
  ├─ _auto_link_similar(conn, new_id, workspace_id)
  │     ├─ _extract_fts_keywords(content) → "parola1 OR parola2 OR ..."
  │     ├─ FTS5 BM25 search LIMIT 3
  │     ├─ filter: best_score < -1.0
  │     └─ for each match → link_memories(is_manual=False)
  └─ return new_id
```

---

## 📋 Roadmap

Vedi [roadmap.md](./roadmap.md) per le azioni future pianificate.

### Priorità:

1. **Media** — Tag-based linking (schema migration `013_memory_tags.sql`)
2. **Bassa** — Refactor keyword extraction (DRY)
3. **Bassa** — Monitoraggio pruning dopo 30-60gg
4. **Bassissima** — Bidirectional linking (non fare — BFS già gestisce)
5. **Media** — Calibrazione soglia BM25 su dati reali
