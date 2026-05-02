# ADR-009: Bugfix API `/api/relations` — Knowledge Graph UI non visualizzava edges

**Date:** 2026-05-02
**Status:** Fixed
**Component:** `src/craft_memory_mcp/server.py` + `src/craft_memory_mcp/db.py`

## Contesto

La UI del Knowledge Graph (accessibile via `http://localhost:8392/ui/`) mostrava i nodi (memories) disposti in anelli concentrici ma **senza alcuna linea di connessione** tra di loro. Il grafo sembrava un pattern "hub and spoke" vuoto: tanti punti intorno a un centro, con zero relazioni visibili.

## Bug 1 — API non caricava mai tutti gli edges

### Causa

La UI chiama:
```javascript
CRAFT_API.relations(null, null)
// → GET /api/relations?workspace_id=ws_ecad0f3d
```

Nell'handler `api_relations` (server.py):
```python
memory_id_str = request.query_params.get("memory_id", "0")   # ← default "0"
if not memory_id_str or not memory_id_str.isdigit():
    return JSONResponse([])                                     # ← non raggiunto
conn = _get_conn()
results = _db_get_relations(conn, int(memory_id_str), ws, direction)  # ← chiama con id=0
```

- `memory_id` assente → default `"0"`
- `"0".isdigit()` → `True` → passa il controllo
- `_db_get_relations(conn, 0, ws, "both")` cerca edges con `source_id=0 OR target_id=0`
- Memory #0 non esiste → **ritorna array vuoto**

### Fix

Aggiunta funzione `get_all_relations()` in `db.py`:

```python
def get_all_relations(conn, workspace_id):
    """Return ALL relations for a workspace, normalized for graph UI."""
    rows = conn.execute("""
        SELECT mr.id, mr.source_id, mr.target_id, mr.relation AS relation_type,
               mr.confidence_type AS confidence, mr.confidence_score,
               mr.role, mr.weight, mr.is_manual,
               m1.content AS source_content, m2.content AS target_content
        FROM memory_relations mr
        JOIN memories m1 ON mr.source_id = m1.id
        JOIN memories m2 ON mr.target_id = m2.id
        WHERE mr.workspace_id = ?
    """, (workspace_id,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["source"] = d.pop("source_id")
        d["target"] = d.pop("target_id")
        d["relation"] = d.get("relation_type", "semantically_similar_to")
        result.append(d)
    return result
```

Handler aggiornato in `server.py`:
```python
memory_id_str = request.query_params.get("memory_id")  # ← None se assente
if memory_id_str and memory_id_str.isdigit():
    results = _db_get_relations(conn, int(memory_id_str), ws, direction)
    return JSONResponse(results or [])
# No memory_id → ALL edges for the graph UI
all_edges = _db_get_all_relations(conn, ws)
return JSONResponse(all_edges or [])
```

## Bug 2 — Property naming mismatch

### Causa

`get_relations()` in `db.py` ritorna:
```python
{"source_id": ..., "target_id": ..., "confidence_type": ..., "confidence_score": ..., ...}
```

Ma la UI (graph.jsx) si aspetta:
```javascript
r.source, r.target, r.role, r.weight, r.confidence, r.relation
```

`positions[r.source]` → `positions[undefined]` → tutte le linee sono `null` perché il controllo `if (!s || !t) return null` scarta ogni edge.

### Fix

Normalizzazione in `get_all_relations()` (vedi sopra):
- `source_id` → `source`
- `target_id` → `target`
- `relation_type` preservato come `relation_type` + alias `relation`
- `confidence_type` → `confidence` (già presente come alias SQL)
- `role`, `weight` → già presenti con nomi corretti

## Verifica

Prima del fix:
```
GET /api/relations?workspace_id=ws_ecad0f3d → 0 edges
```

Dopo il fix:
```
GET /api/relations?workspace_id=ws_ecad0f3d → 1513 edges
```

Ogni edge ha le proprietà necessarie per il rendering SVG:
```json
{
  "source": 1,
  "target": 2,
  "role": "context",
  "weight": 1.0,
  "confidence": "inferred",
  "relation": "semantically_similar_to"
}
```

## Root Cause

I due bug si sono verificati perché:
1. **API e UI sviluppate separatamente** — il backend `server.py` e il frontend `graph.jsx` usano nomi di proprietà diversi per gli stessi concetti
2. **Endpoint non testato senza memory_id** — il flusso "carica tutto il grafo" non era stato testato perché il graph UI era stato sviluppato quando il workspace aveva 0 edges (workspace mismatch, vedi session 2026-05-02)
3. **Default pericoloso** — `"0"` come default per un ID è ambiguo (potrebbe esistere o meno)

## File Modificati

- `src/craft_memory_mcp/db.py`: aggiunta `get_all_relations()`
- `src/craft_memory_mcp/server.py`: import + handler `api_relations` aggiornato
