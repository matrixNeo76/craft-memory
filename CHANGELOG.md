# Changelog

## [0.2.0] (2026-05-04)

### Features

* **compression:** deterministic text compression ~39% (level 1, 48 patterns, reversible) — `remember(compress_level=1)`, `search_memory(decompress=True)` (Phase 1)
* **cache:** `remember(force=True)` bypasses dedup for re-saving updated content (Phase 1)
* **query:** `shortest_path(source_id, target_id)` — BFS shortest path in knowledge graph (Phase 1)
* **query:** `subgraph(memory_id, depth)` — BFS local context extraction (Phase 1)
* **query:** `query_graph(tag, category, min_importance, limit)` — filtered node+edge query (Phase 1)
* **visualization:** `get_communities(resolution)` — Leiden/Louvain community detection without embeddings (Phase 2)
* **visualization:** `export_graph_html(output_path)` — self-contained D3.js force-directed graph with community colors, tooltips, search, filters (Phase 2)
* **export:** `export_graphml(output_path)` — GraphML format for Gephi/yEd (Phase 2)
* **export:** `export_cypher(output_path)` — Cypher queries for Neo4j (Phase 2)
* **code-analyzer:** new external project `craft-code-mapper` — AST extraction for Python (stdlib), JavaScript/TypeScript (tree-sitter). Scans directories, stores classes/functions/imports/call graph as memories + relations in craft-memory (Phase 3)
* **cavekit:** `save_procedure(mode="cavekit", verify_command, acceptance_criteria, spec_text)` — spec-driven workflow mode (Phase 4)
* **cavekit:** `spec_to_plan(spec_text)` — converts natural language spec to structured plan with tasks (Phase 4)
* **cavekit:** `record_procedure_outcome_and_advance()` — record execution result, confidence evolves via Bayesian blend (Phase 4)
* **middleware:** `McpClientPool.addMiddleware(pattern, handler)` — interceptor system for MCP tool calls in `craft-agents-oss` (Phase 5)
* **cli:** `craft-memory analyze <dir>` — orchestrates code analysis via craft-code-mapper (Phase 6)
* **cli:** `craft-memory graph [output]` — generates interactive HTML knowledge graph (Phase 6)
* **cli:** `craft-memory watch <dir>` — periodic code re-analysis (Phase 6)
* **docs:** complete guide.md updated with all new tools, CLI commands, external tools (Phase 6)

## [0.1.1](https://github.com/matrixNeo76/craft-memory/compare/v0.1.0...v0.1.1) (2026-05-01)


### Features

* add core memory promotion (μ2) ([f76e86d](https://github.com/matrixNeo76/craft-memory/commit/f76e86debc19ebcf0c5c138fbbfe472d5b58a259))
* add hyperedge roles and weights to knowledge graph (μ3) ([9bdf937](https://github.com/matrixNeo76/craft-memory/commit/9bdf937172a7e5d580146b6c53e848b7c9173a77))
* add knowledge graph layer inspired by graphify ([7aa9ee7](https://github.com/matrixNeo76/craft-memory/commit/7aa9ee795cd7209a2dda4d62294129a6e0b615af))
* add recommended flow layer and stability-first design principles (Fase A+B) ([d099dae](https://github.com/matrixNeo76/craft-memory/commit/d099dae68da35e4ec827defb67e0fc8d1fca13c0))
* add REST API layer + Craft-Memory-UI real client ([69c82b7](https://github.com/matrixNeo76/craft-memory/commit/69c82b7dcbae9c83f454899cb8649d7cf7320ebd))
* add RRF hybrid search (μ1) ([25c8693](https://github.com/matrixNeo76/craft-memory/commit/25c8693952209bca8f0866dcd92548f5eb54882a))
* add update_open_loop tool (μ0) ([64184a3](https://github.com/matrixNeo76/craft-memory/commit/64184a3453451bfd335fbae88c24e81877ab6717))
* **graph:** add is_manual flag, configurable thresholds, prune_inferred_edges ([5421539](https://github.com/matrixNeo76/craft-memory/commit/5421539a20219904613b40fbedbf848737906553))
* **install:** merge-safe install with --merge, --overwrite, --dry-run ([2d61828](https://github.com/matrixNeo76/craft-memory/commit/2d61828c7447f6c7b85f803fa88920067a084f13))
* **observability:** memory_stats, explain_retrieval, generate_handoff, save_decision_record ([1a6caa9](https://github.com/matrixNeo76/craft-memory/commit/1a6caa9b02fea9fd0b22e3ca8a18a349dd5ae61f))
* Phase 9 — bug fixes, save_summary/update_memory tools, privacy stripping ([68e1aca](https://github.com/matrixNeo76/craft-memory/commit/68e1aca50cb8035244e15fd1d3ad68bf58c606d9))
* **phase-8:** anti-bloat & robustness improvements ([9453122](https://github.com/matrixNeo76/craft-memory/commit/94531226068d73a077294cdad6b637d19d2ae0bb))
* **policy:** boundary detection — MemoryClass enum + classify_event tool (Sprint 3) ([e80c413](https://github.com/matrixNeo76/craft-memory/commit/e80c413b49b38c9033eca737f325b2e363e72e2a))
* **procedures:** procedural memory — save_procedure, search_procedures, get_applicable_procedures (Sprint 4) ([c221691](https://github.com/matrixNeo76/craft-memory/commit/c2216915ede33af360e5f11603754026542f2ba1))
* **scopes:** scope hierarchy + get_memory_bundle batch retrieval (Sprint 5) ([16c1654](https://github.com/matrixNeo76/craft-memory/commit/16c16541601f28016b3fdb80f00bcd93701e381c))
* **sprint5-close+sprint6:** expose hidden tools + procedure outcome evolution ([b147be0](https://github.com/matrixNeo76/craft-memory/commit/b147be095b2e1e621e1c2fdace7448ee0a17c9c3))
* **sprint7:** multi-hop graph context + batch remember ([d5e6b67](https://github.com/matrixNeo76/craft-memory/commit/d5e6b67b3ed38bd7a012b86ad693b2296143dc1f))
* **sprint8-10:** top_procedures, consolidate_memories, session quality, /metrics, SKILL enrichment ([e23e0a1](https://github.com/matrixNeo76/craft-memory/commit/e23e0a13a5b0e3d1515883869c9682f743c32d30))
* **temporal:** lifecycle invalidation, review flag, memory history (Sprint 2) ([c8d929a](https://github.com/matrixNeo76/craft-memory/commit/c8d929ac7709a749bfdd095f59936b8b84aef1cd))
* **ui:** serve UI from server at /ui/ and rename to index.html ([ab1ac72](https://github.com/matrixNeo76/craft-memory/commit/ab1ac72cb3a3d8b55cf3ce40af1835cea1101b12))


### Bug Fixes

* **ui:** resolve Babel XHR cache, workspace ID display, and stale version badge ([97a2c9b](https://github.com/matrixNeo76/craft-memory/commit/97a2c9bcc83b8a8f9a1c40151d39ced9e006dcb0))
* **ui:** workspace auto-detection, no-cache static files, dashboard fixes ([a1ba47a](https://github.com/matrixNeo76/craft-memory/commit/a1ba47a115bec1b4d7fffefee14964d26fc168e0))


### Documentation

* **architecture:** v6.0 — Sprint 5-close, 6, 7 fully documented ([84ac41a](https://github.com/matrixNeo76/craft-memory/commit/84ac41a041dbb6e13594d25e53f333ab7d6e3e5b))
* **readme:** update to Sprint 7 state — 41 tools, 168 tests, migrations 011 ([8efab96](https://github.com/matrixNeo76/craft-memory/commit/8efab967e9d1839c891e539164db05d6801243d9))
* translate ARCHITECTURE.md to English for community use ([d737859](https://github.com/matrixNeo76/craft-memory/commit/d7378592cea567687b2c2ab25ea5bb6f09faa7a8))
* update ARCHITECTURE and README to v4.0 (19 tools, schema v6) ([8ec3d66](https://github.com/matrixNeo76/craft-memory/commit/8ec3d66511effebab7f45f37f440a0a53675059e))
* update ARCHITECTURE.md and README for Sprint 1-5 completion ([f3f7cb7](https://github.com/matrixNeo76/craft-memory/commit/f3f7cb79854645a5cbfe2b879dd9edc8a55b1015))
* update ARCHITECTURE.md and README.md for v3.0 knowledge graph layer ([ff593f5](https://github.com/matrixNeo76/craft-memory/commit/ff593f5bf6607fdf161a4d4553c1bb2f89a8f85b))
* update ARCHITECTURE.md to v2.0 (Phase 8 + Phase 9 complete) ([bae95ce](https://github.com/matrixNeo76/craft-memory/commit/bae95ce3f77be58910d71b19d411f41e916f8424))
* update README to reflect Phase 8 and Phase 9 changes ([2b8ba34](https://github.com/matrixNeo76/craft-memory/commit/2b8ba345f4bb6d84215cd22fab25dfedffe5a464))
* v7.0 — Sprint 8-10 documented (46 tools, 12 migrations, 209 tests) ([cdc99ca](https://github.com/matrixNeo76/craft-memory/commit/cdc99ca53a0383f37b298192a068d1bd0abf2156))
