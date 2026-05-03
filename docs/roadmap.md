# Craft Memory — Roadmap

> Azioni future identificate durante l'analisi architetturale del 2026-05-02.

## Completate (Sprint Corrente)

- [x] **Auto-linking in `remember()`** — ogni nuovo `remember()` cerca automaticamente le top-3 memorie simili via FTS5 BM25 e crea edge `semantically_similar_to` con `is_manual=False` (prunabili dalla manutenzione notturna). Soglia -1.0 per filtrare rumore.

---

## 1. 🔧 Tag-Based Linking (Media Priorità)

**Problema**: `_auto_link_similar()` usa solo il contenuto testuale per la similarità. I tag opzionali (`tags: list[str]`) sono memorizzati come JSON nella colonna `tags` ma non sono indicizzati in FTS5 e non vengono usati per il linking.

**Soluzione proposta**:
1. Aggiungere tabella `memory_tags` (many-to-many: memory_id, tag, workspace_id) con indice su tag
2. Migrazione SQL (nuovo file `013_memory_tags.sql`)
3. In `_auto_link_similar()`, dopo il FTS5 match, cercare anche memorie con tag in comune e creare edge aggiuntivi
4. Opzionale: aggiungere un weighted score (BM25 + tag overlap)

**Vantaggi**: migliora la qualità del linking per memorie con tag espliciti
**Rischio**: aumento scritture e complessità. I tag sono opzionali e poco usati — valutare se il ROI è sufficiente.

---

## 2. 🔧 Refactor Keyword Extraction (Bassa Priorità)

**Problema**: Due implementazioni separate della keyword extraction da testo:
- `_extract_fts_keywords()` in `db.py` (nuova, creata per auto-linking)
- Logica inline in `find_similar_memories()` in `db.py` (storica, con `import re as _re_local`)

**Soluzione proposta**:
1. Sostituire la logica inline in `find_similar_memories()` con una chiamata a `_extract_fts_keywords()`
2. Test che `find_similar_memories` si comporti identicamente

**Vantaggi**: DRY, manutenzione più semplice
**Rischio**: nullo — refactor meccanico

---

## 3. 🔍 Monitoraggio Pruning (Bassa Priorità, Continuativa)

**Problema**: I parametri di pruning `_PRUNE_WEIGHT_THRESHOLD = 0.3` e `_PRUNE_AGE_DAYS = 60` non sono mai stati calibrati su dati reali.

**Azione**: Dopo 30-60 giorni di auto-linking:
1. Verificare quanti edge vengono creati vs potati
2. Controllare il report `inferred_edges_pruned` da `daily_maintenance()`
3. Se troppi edge vengono potati → abbassare soglia
4. Se troppo pochi → alzare soglia

**Come**: `db.get_memory_stats(conn, workspace_id)` mostra `total_edges` / `manual_edges` / `inferred_edges`

---

## 4. 🔧 Bidirectional Linking (Bassissima Priorità)

**Problema**: Quando `_auto_link_similar` collega memoria A → B, NON crea B → A. Ma `semantically_similar_to` è una relazione simmetrica.

**Soluzione**: Aggiungere un secondo `link_memories()` per la direzione inversa in `_auto_link_similar()`.

**Contro**: Duplicazione di edge (A→B e B→A), più scritture. La BFS in `get_graph_context` già traversa entrambe le direzioni. **Non raccomandato** — edge singolo è sufficiente.

---

## 5. 🧪 Calibrazione Soglia BM25 (Media Priorità)

**Problema**: Sia l'auto-linking (-1.0) che `find_similar` (-2.5) usano soglie fisse BM25 non calibrate su dati reali.

**Azione**:
1. Raccogliere statistiche sui BM25 score delle memorie esistenti
2. Valutare se -1.0 è troppo permissivo o troppo restrittivo
3. Esporre come variabile d'ambiente, come già fatto per `_AUTOLINK_THRESHOLD`

---

## Riepilogo Priorità

| # | Azione | Sforzo | Impatto | Quando |
|---|--------|--------|---------|--------|
| 1 | Tag-based linking | 2-3h | Medio | Prossimo sprint |
| 2 | Refactor keyword extraction | 15min | Basso | Prossimo sprint |
| 3 | Monitoraggio pruning | 5min | Basso | Tra 30-60gg |
| 4 | Bidirectional linking | 10min | Molto basso | Non fare |
| 5 | Calibrazione soglia BM25 | 1h | Medio | Dopo raccolta dati |
