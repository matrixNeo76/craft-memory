# Craft Memory System — Project Debug Plan
**Data Audit:** 2026-05-01

Questo documento aggrega le criticità e le vulnerabilità architetturali individuate in tutto il repository `craft-memory` (Backend MCP, CLI, Database layer e integrazione UI). Funge da roadmap per la stabilizzazione e l'evoluzione del progetto.

## 🔴 Criticità Bloccanti (Architettura e Concorrenza)

### 1. Global DB Connection e Thread Safety
- **Problema:** In `server.py` viene creata una connessione globale unica (`_conn = None`) con `check_same_thread=False`, condivisa tra tutte le chiamate asincrone FastMCP e le richieste REST. Sotto carico concorrente (es. l'LLM chiama più tool in parallelo mentre la UI fa polling), questo pattern causa lock del database (`database is locked`), colli di bottiglia o violazioni di thread-safety.
- [ ] **Fix:** Sostituire la connessione globale con un Connection Pool (es. tramite `sqlite3` o librerie come `aiosqlite`/`SQLAlchemy`) o implementare un pattern `Dependency Injection` che apra/chiuda una connessione per singola request o thread.

### 2. Race Condition sul Contatore WAL Checkpoint
- **Problema:** La variabile globale `_write_count` in `server.py` viene incrementata senza lock per lanciare i `wal_checkpoint(PASSIVE)`. In esecuzione multi-thread (uvicorn), l'incremento `+= 1` genera race condition che possono sballare la frequenza dei checkpoint.
- [ ] **Fix:** Utilizzare un `threading.Lock()` per proteggere l'aggiornamento di `_write_count` oppure delegare il checkpointing a un background task periodico.

## 🟡 Criticità Minori (API, CLI e Funzionalità)

### 1. Endpoint REST Mancanti per la UI (Integrazione Loops)
- **Problema:** La UI permette teoricamente di ciclare la priorità dei Loop, ma `server.py` implementa solo `POST /api/loops/{id}/close`. Manca un endpoint generico di aggiornamento che esponga `_db_update_open_loop` al frontend.
- [ ] **Fix:** Aggiungere un nuovo decorator `@mcp.custom_route("/api/loops/{loop_id}", methods=["PATCH"])` in `server.py` per permettere l'aggiornamento di `priority`, `status` e `title`.

### 2. Risoluzione Porte e PID in `cli.py` (Windows)
- **Problema:** La logica di stop del server in Windows cerca `:PORT` nell'output di `netstat`. Un controllo impreciso (`f":{port}" in line`) farà collidere la porta 80 con la 8080. 
- [ ] **Fix:** Parsare l'output di `netstat` separando le colonne ed effettuando un match esatto sulla colonna *Local Address* (`address.endswith(f":{port}")`).

### 3. Hardcoding dei Path di Sistema
- **Problema:** In `cli.py` e `server.py` i path di default sono hardcodati su `~/.craft-agent/...`. Con la transizione verso architetture enterprise (es. AILoud / auresys), questo accoppiamento può causare fallimenti se la directory base non esiste o se l'agente gira in container con path diversi.
- [ ] **Fix:** Introdurre una variabile d'ambiente unificata (es. `CRAFT_AGENT_HOME`) sia per il discovery dei workspace che per i file di memoria, usando `~/.craft-agent` solo come fallback ultimo.

## 🔵 Punti da verificare (Test e Automazioni)

1. **RRF Search Performance:** La `hybrid_search` (BM25 + Word Overlap) implementata in `db.py` è eseguita in memoria su array Python. Verificare se su un workspace grande (>10k memorie) il fetch di `limit * 3` documenti e il calcolo del coefficiente di Jaccard in Python blocchi l'event loop di FastAPI, causando lag alla UI.
2. **Schema Migrations:** Il file `schema.sql` definisce tutto in blocco. La funzione `run_migrations` cerca i file in `migrations/`, ma questa cartella non sembra attualmente versionata o presente con script attivi. Verificare che il workflow di evoluzione schema sia testato.

## 📝 Next Steps (Piano di Azione Globale)
- [ ] Ristrutturare la gestione delle connessioni DB in `server.py`.
- [ ] Esporre i restanti endpoint REST in `server.py` (es. `PATCH /api/loops`).
- [ ] Rendere path e configurazioni CLI agnostiche rispetto alla root directory.
- [ ] Fixare il parser di `netstat` per il comando `craft-memory stop`.

## 🏛️ Decisioni prese (Log delle Architetture e Fix)
*(Nessuna decisione registrata finora. Aggiornare qui man mano che si risolvono i fix).*
