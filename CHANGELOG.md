# Changelog

## [0.1.2](https://github.com/matrixNeo76/craft-memory/compare/v0.1.1...v0.1.2) (2026-05-03)


### Features

* add project:&lt;name&gt; tag to session scanner memories ([bc869de](https://github.com/matrixNeo76/craft-memory/commit/bc869de130f23267f586a83511002d3c5da3c5a1))
* **automations:** add 9 new automations across 3 types + session-manager skill ([aa385a2](https://github.com/matrixNeo76/craft-memory/commit/aa385a2af030485ed2b3303125f8cbf84fbcfd96))
* implement 13 automation expansion plan (4→13 automations) ([edc118c](https://github.com/matrixNeo76/craft-memory/commit/edc118c58fcf220229291fece49489baa67c1a32))
* Knowledge Graph UI zoom/pan/drag + API /api/relations all-edges fix ([cdd5196](https://github.com/matrixNeo76/craft-memory/commit/cdd51966aa52f161690969d3605dfd233f8747ef))
* lint_wiki, export_wiki, source_url migration — wiki health + Obsidian export + source tracking ([04fc750](https://github.com/matrixNeo76/craft-memory/commit/04fc750f49983c5b1d8d6903ed613e82f6703374))
* Memory Explorer — edge counts, inline neighbors, pagination, Escape key, dynamic category counts ([488cde0](https://github.com/matrixNeo76/craft-memory/commit/488cde0b4876a27c624725cc03dd299b95aa48f0))
* **memory:** add auto-linking in remember() via FTS5 BM25 + analysis docs ([14fd5fd](https://github.com/matrixNeo76/craft-memory/commit/14fd5fd090bbcb740f1c2ad10ee0e1d9e36f8957))
* session scanner + fix Windows Job Object auto-restart ([ccf52db](https://github.com/matrixNeo76/craft-memory/commit/ccf52db8830bf0ff767e47308050461c2b12af19))
* **ui:** Dashboard — lint_wiki health check + export_wiki panels integrated ([a4c6141](https://github.com/matrixNeo76/craft-memory/commit/a4c61418da3b7a4e92a4100db5f7597bc1410072))


### Bug Fixes

* auto-link test assertion for bidirectional edges ([3d56382](https://github.com/matrixNeo76/craft-memory/commit/3d563829cbee8e403a6cbe4d45cac1c3d439d111))
* **automations:** resolve 6 critical issues found during review ([1f5d23c](https://github.com/matrixNeo76/craft-memory/commit/1f5d23ca896c82dffb208ba430198957e4db1cea))
* **handoff:** fix unterminated string literal in buildMarkdown() ([07b60ad](https://github.com/matrixNeo76/craft-memory/commit/07b60ad623ca77dfabf33d060286276d814aab31))
* Memory Explorer V4 — show accurate loaded/total counts, RELATIONS_LOADED flag, load-more from server ([8948c27](https://github.com/matrixNeo76/craft-memory/commit/8948c27d471af389338ae8c1de126c15dde757b7))
* remember() silent duplicate on invalid category — now reports meaningful ValueError ([cfa3674](https://github.com/matrixNeo76/craft-memory/commit/cfa367405d5b25b0a4070184034ba9fe5323f91b))
* test_bundle_workspace_isolation argument order ([cb358ec](https://github.com/matrixNeo76/craft-memory/commit/cb358ecbb08712209532dc7d97aa67a2d24301f7))
* test_health_check version assertion ([e46da4f](https://github.com/matrixNeo76/craft-memory/commit/e46da4f8e1e605e910d6253adb4595457f7272f4))
* **ui:** minor polish for loops and actions propagation ([c316a0a](https://github.com/matrixNeo76/craft-memory/commit/c316a0a868dbd2bcaf190472e110f5d131fc643f))
* **ui:** Phase 2 — FTS5 search, InsertMemoryModal, clipboard, graph fixes ([02db46b](https://github.com/matrixNeo76/craft-memory/commit/02db46bf9ac0e9a54d13ead5f15a57cb8918eb92))
* **ui:** resolve all DEBUG_PLAN criticalities ([fb83f24](https://github.com/matrixNeo76/craft-memory/commit/fb83f24f3d361b47ad907c74880454555ff5e9ab))


### Performance

* Memory Explorer v2 — O(1) edge lookups, memoized highlight, loading state, ⌘K, content truncation ([7452191](https://github.com/matrixNeo76/craft-memory/commit/7452191e5bc3ff837664f76ea7f52e0c9bfdc9d3))


### Refactoring

* **ui:** extract cache-bust to separate file, add fetch() patch ([7ce31d3](https://github.com/matrixNeo76/craft-memory/commit/7ce31d30a3e5c176c83d8887352b048e5c38ba0f))


### Documentation

* add automation expansion plan (13 automations, 7 phases) ([57d110f](https://github.com/matrixNeo76/craft-memory/commit/57d110f7fa3ad6933cedeb1b03b41f1c58f1e40f))
* add final architectural analysis with 11-phase refactoring plan ([ffc5873](https://github.com/matrixNeo76/craft-memory/commit/ffc5873bf8c006372d71eef6350ca7386fe0bcfb))
* add project-wide DEBUG_PLAN.md covering backend, db, and cli ([20bc1d0](https://github.com/matrixNeo76/craft-memory/commit/20bc1d0085a8f2d596e04516c4cb69f1565eadad))
* add sources roadmap - todo list of 23 API/MCP candidates for workspace enrichment ([7a4b968](https://github.com/matrixNeo76/craft-memory/commit/7a4b96831f3857e21981337475b9b304d6856654))
* README — knowledge base health (lint_wiki, export_wiki, source_url) explained in plain terms ([6641bad](https://github.com/matrixNeo76/craft-memory/commit/6641bad080548736dc24d2e451b94628565c7177))
* **ui:** add DEBUG_PLAN.md from code audit ([5920dea](https://github.com/matrixNeo76/craft-memory/commit/5920dea9645bd110a68faf6e451a22aad5b2c595))
* **ui:** add UI-specific README and ARCHITECTURE documentation ([6f13346](https://github.com/matrixNeo76/craft-memory/commit/6f13346ae458fc53bc85e6f34fea7bfe43359c4b))
* **ui:** aggiorna DEBUG_PLAN con Phase 3 — Web Design, Responsiveness & Security audit ([062e13b](https://github.com/matrixNeo76/craft-memory/commit/062e13b8ff69f43ea71663c0a0b306fe1c5a8934))
* **ui:** correct README and ARCHITECTURE to reflect actual backend integration ([1716c2c](https://github.com/matrixNeo76/craft-memory/commit/1716c2c7fa9cce48c8157f4117d7aa897fec3d39))
* **ui:** enhance DEBUG_PLAN.md with date, progress tracking, and decisions log ([59d7703](https://github.com/matrixNeo76/craft-memory/commit/59d7703f2e13954ad7b50ac30e45a91e64228c3b))
* **ui:** update DEBUG_PLAN.md with Phase 2 UI audit results ([175ff20](https://github.com/matrixNeo76/craft-memory/commit/175ff20564b45115862c516255054ac325fc14bb))

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
