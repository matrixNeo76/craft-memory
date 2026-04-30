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

Use the built-in consolidation pipeline:

**2a. Find candidates** (memories that have become low-value):
```
consolidation_candidates(importance_threshold=2.0, age_days=30)
```
Returns old, non-core memories with low effective importance. Review the list.

**2b. Dry-run the consolidation** (no changes):
```
consolidate_memories(
  candidate_ids_json="[id1, id2, id3]",
  procedure_name="[descriptive_name]",
  trigger_context="[when this knowledge is relevant]",
  steps_md="## Summary\n[synthesized content]",
  confirm=False
)
```
Review what would be created and invalidated.

**2c. Confirm if the plan looks right**:
```
consolidate_memories(
  candidate_ids_json="[id1, id2, id3]",
  procedure_name="[descriptive_name]",
  trigger_context="[when this knowledge is relevant]",
  steps_md="## Summary\n[synthesized content]",
  confirm=True
)
```
This creates the procedure and marks all candidate memories as `invalidated`.
Memories are NOT deleted — use `approve_memory(id)` to reverse if needed.

### Step 2b: Review Procedure Performance

Check which procedures are actually working:
```
top_procedures(limit=10)
```
Returns procedures ranked by `confidence × success_rate × use_count`.

For low-confidence procedures with many failures, consider:
- Updating steps with `save_procedure()` (upsert by name)
- Deprecating with `save_procedure(..., status="deprecated")`

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

Consolidated: [N] memories → [M] procedures created
Facts promoted: [N] new facts from memories
Loops closed: [N] resolved
Loops flagged stale: [N]
Facts updated: [N]
Procedures updated: [N] (confidence evolved from outcomes)

Current stats:
  Memories: [total] (core: [N], active: [N], invalidated: [N])
  Facts: [total]
  Open loops: [total]
  Procedures: [total] (top: [name] at [score])
```

## Maintenance Principles

1. **Conservative deletion**: Prefer consolidation over deletion
2. **Preserve decisions**: Never remove decision memories — they record rationale
3. **Promote don't duplicate**: When knowledge becomes stable, create a fact, don't just re-remember
4. **Close loops promptly**: Don't let loops linger — close them when resolved
5. **User confirmation**: For significant changes (deleting memories, closing critical loops), ask the user first
6. **Keep it lean**: The goal is signal-to-noise ratio, not maximum storage
