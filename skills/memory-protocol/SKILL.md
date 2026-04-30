---
name: "Memory Protocol"
description: "Mandatory protocol for reading/writing persistent memory across sessions. Triggers on session start and when agent needs to store or retrieve context."
requiredSources:
  - memory
---

# Memory Protocol

This skill defines the mandatory protocol for using the Craft Memory system. Every session MUST follow this protocol to ensure cross-session continuity.

## Mandatory: Session Start Sequence

When a new session begins, you MUST execute this sequence BEFORE doing any other work:

1. **Call `get_recent_memory(scope="workspace", limit=10)`** — Recover the 10 most recent memories
2. **Call `list_open_loops()`** — Check for any incomplete tasks or follow-ups
3. **Synthesize context** — Briefly summarize what you recovered for the user

Example opening:
> "I recovered context from your previous sessions. Here's what I found: [summary]. There are N open loops: [list]."

## Decision Tree: Which Storage Tool to Use?

```
Something happened in this session (event, decision, fix, discovery)?
  └── ONE item → remember()
  └── MANY items at once (session end, bulk) → batch_remember()

You have confirmed, stable knowledge that won't change?
  └── → upsert_fact()

You have a repeatable multi-step workflow for a trigger?
  └── → save_procedure()

Not sure which category? → classify_event(content)
  Returns: DISCARD / EPISODIC / FACT_CANDIDATE / OPEN_LOOP / PROCEDURE_CANDIDATE / CORE_CANDIDATE
```

**Anti-pattern trap**: Do NOT use `remember()` for stable facts — they decay over time.
Do NOT use `upsert_fact()` for one-off events — you lose the temporal context.
Do NOT use `save_procedure()` for a single past event — procedures describe recurring workflows.

## When to Use `remember`

Store a memory ONLY when it has real, lasting value:

| ✅ DO remember | ❌ DON'T remember |
|---|---|
| Architectural decisions and why | Trivial observations |
| Bug root causes and fixes | Every message or action |
| Important discoveries about the codebase | Information easily found in files |
| Breaking changes or migrations | Temporary state (file currently open) |
| User preferences or constraints | Redundant or duplicate info |

**Category guide:**
- `decision` — When a deliberate choice was made (include rationale)
- `discovery` — Important finding about the codebase/system
- `bugfix` — Root cause + fix for a bug
- `feature` — Feature implementation details
- `refactor` — Structural change and motivation
- `change` — Any other significant change
- `note` — General important note

**Importance guide:**
- `8-10` — Architectural decisions, breaking changes, critical bugs
- `5-7` — Normal decisions, discoveries, feature work
- `1-4` — Minor notes, low-priority observations

## When to Use `upsert_fact`

Store a fact when you have CONFIRMED, STABLE knowledge about the project:

- Tech stack choices (e.g., `tech_stack: "Python + FastMCP + SQLite"`)
- Database URLs or connection info
- Authentication providers and methods
- Project structure conventions
- API endpoints or schemas
- Third-party service integrations
- User preferences about the project

Facts should be:
- **Stable**: unlikely to change frequently
- **Confirmed**: verified, not guessed
- **Keyed**: use descriptive, namespaced keys (e.g., `auth_provider`, `db_schema_version`)

Set `confidence` to:
- `1.0` — Verified fact
- `0.8-0.9` — Very likely but not 100% confirmed
- `0.5-0.7` — Informed assumption, needs verification

## When to Create/Open/Close Loops

**Create an open loop** when:
- A task is started but not completed
- A follow-up is needed in a future session
- A decision is deferred and needs revisiting

**Close an open loop** when:
- The task is completed
- The follow-up has been addressed
- The decision has been made

## When to Use `search_memory`

Use search when:
- You need context about a past decision or discovery
- A user asks "did we already decide on X?"
- You want to check if something was tried before
- You need to recover context about a specific topic

## When to Use `save_procedure`

Use when you discover a **repeatable multi-step workflow**:

```
save_procedure(
  name="deploy_staging",
  trigger_context="when asked to deploy to staging",
  steps_md="## Steps\n1. Run tests\n2. Build Docker image\n3. Push to registry\n4. Apply k8s manifest",
  confidence=0.8
)
```

After executing a procedure, record the result:
- `record_procedure_outcome(procedure_id, outcome="success")` — it was effective
- `record_procedure_outcome(procedure_id, outcome="partial")` — partially worked
- `record_procedure_outcome(procedure_id, outcome="failure", notes="step 3 failed due to X")` — it failed

This evolves procedure confidence automatically via daily maintenance.

## When to Use `batch_remember`

Use at session end or when saving multiple related memories to reduce MCP round-trips:

```json
[
  {"content": "Fixed auth bug — root cause: missing await", "category": "bugfix", "importance": 8},
  {"content": "API uses JWT with 1h expiry", "category": "discovery", "importance": 7},
  {"content": "Deployed v1.3.2 to production successfully", "category": "change", "importance": 6}
]
```

Duplicates are silently skipped (return `null` for that slot).

## Retrieval: Coarse-to-Fine Pattern

When you need deep context on a topic, escalate through the 3 layers:

1. **Layer 1 — Find** (fast): `search_memory(query, limit=5)` → get relevant snippet IDs
2. **Layer 2 — Context** (medium): `get_relations(memory_id)` → expand via knowledge graph
3. **Layer 3 — Detail** (precise): `get_memory_bundle([id1, id2, ...])` → fetch full rows
4. **Layer 4 — Neighborhood** (deep): `get_graph_context(memory_id, depth=2)` → BFS multi-hop

Don't skip to Layer 4 directly — it's expensive. Use it only after Layer 1-2 identify the anchor.

## Anti-Patterns to Avoid

1. **Memory spam**: Don't remember every single action or message
2. **Fact without evidence**: Don't upsert facts that are guesses
3. **Orphan loops**: Don't create loops you never intend to close
4. **Ignoring context**: Don't skip the session start sequence
5. **Duplicate content**: The system auto-deduplicates, but try to be concise
6. **Using remember() for procedures**: If you find yourself writing the same steps in multiple memories, that's a procedure
7. **Skipping outcome tracking**: Always call `record_procedure_outcome` after executing a procedure
