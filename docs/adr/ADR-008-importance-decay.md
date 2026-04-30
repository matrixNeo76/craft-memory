# ADR-008: Importance Decay for Memory Recall

**Date:** 2026-04-30  
**Status:** Accepted  
**Deciders:** Matrix (AureSystem)

---

## Context

Without decay, a memory with `importance=8` stored 365 days ago competes equally
with a memory with `importance=8` stored yesterday in recall results. This makes
`get_recent_memory` return stale high-importance memories that may no longer be relevant.

## Decision

Apply exponential decay to importance scores at query time:

```
effective_importance = importance × exp(−λ × age_days)
```

Default λ = 0.005, configurable via `CRAFT_MEMORY_DECAY_LAMBDA` env var.

### Effect of λ = 0.005

| Importance | Age | Effective |
|-----------|-----|-----------|
| 8 | 0 days | 8.0 |
| 8 | 90 days | ~5.1 |
| 8 | 180 days | ~3.3 |
| 8 | 365 days | ~1.3 |
| 5 | 0 days | 5.0 |
| 5 | 30 days | ~4.3 |

High-importance memories remain relevant for months; low-importance memories
fade within weeks.

## Implementation

- Computed in Python at query time — no schema change required
- `get_recent_memory()` fetches 5× the requested limit, re-ranks by `effective_importance`,
  returns top N
- `search_memory()` uses SQL bm25 ranking (relevance × 0.7 + importance × 0.3)
  — decay not applied here since relevance already dominates
- λ = 0.005 chosen empirically: half-life ≈ 139 days (comfortable for long-running projects)

## Consequences

**Positive:**
- Session-start recall surfaces recent, relevant memories first
- Old noise fades naturally without manual cleanup
- Configurable λ without code changes

**Negative:**
- Slightly higher CPU cost at recall time (Python sort on fetched rows)
- Decay is approximated at query time, not stored — slightly inconsistent between calls
  if clock advances between two identical queries (negligible in practice)
