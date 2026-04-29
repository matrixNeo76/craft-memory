---
name: "Memory Maintenance"
description: "Deduplicate, consolidate, and clean up persistent memory. Run periodically or on demand to keep memory lean and accurate."
requiredSources:
  - memory
---

# Memory Maintenance

This skill handles periodic maintenance of the Craft Memory system: deduplication, consolidation, and cleanup of stale data.

## When to Use This Skill

- When the scheduled maintenance automation fires
- When explicitly asked to clean up memory
- When memory search results seem noisy or redundant
- Periodically (recommended: daily via SchedulerTick automation)

## Maintenance Procedure

### Step 1: Review Current State

```
summarize_scope(scope="workspace")
```

Review the output. Look for:
- High memory count (potential noise)
- Many open loops (potential staleness)
- Duplicate or near-duplicate facts
- Low-importance memories that may not be worth keeping

### Step 2: Consolidate Redundant Memories

If you find multiple memories about the same topic, create ONE consolidated memory and note the originals:

```
remember(
  content="Consolidated: [merged content from multiple memories]",
  category="note",
  importance=[max of originals],
  scope="workspace"
)
```

Then note in your response which memories could be removed (manual review recommended).

### Step 3: Promote Stable Knowledge to Facts

Review recent memories for knowledge that has become stable:

- A `discovery` that is now confirmed → promote to `upsert_fact`
- A `decision` that is now established policy → create a fact
- Repeated mentions of the same information → consolidate into one fact

```
upsert_fact(key="[descriptive_key]", value="[stable_knowledge]", confidence=1.0)
```

### Step 4: Review Open Loops

1. **List all open loops**: `list_open_loops()`
2. **Close resolved ones**: `close_open_loop(id, resolution)`
3. **For stale loops** (older than 30 days with no activity): Note them for the user to decide
4. **Prioritize**: Ensure critical/high loops are visible

### Step 5: Verify Fact Accuracy

Review existing facts:
- Are any facts outdated or incorrect? Update them with `upsert_fact`
- Are any facts low-confidence that should be verified? Flag for user

### Step 6: Report

Present a maintenance report:

```
🧹 Memory Maintenance Report

Consolidated: [N] memories merged into [M]
Facts promoted: [N] new facts from memories
Loops closed: [N] resolved
Loops flagged stale: [N]
Facts updated: [N]

Current stats:
  Memories: [total]
  Facts: [total]
  Open loops: [total]
```

## Maintenance Principles

1. **Conservative deletion**: Prefer consolidation over deletion
2. **Preserve decisions**: Never remove decision memories — they record rationale
3. **Promote don't duplicate**: When knowledge becomes stable, create a fact, don't just re-remember
4. **Close loops promptly**: Don't let loops linger — close them when resolved
5. **User confirmation**: For significant changes (deleting memories, closing critical loops), ask the user first
6. **Keep it lean**: The goal is signal-to-noise ratio, not maximum storage
