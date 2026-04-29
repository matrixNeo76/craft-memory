# ADR-004: Auto-Register Session on First DB Connection

**Status:** Accepted  
**Date:** 2026-04-29  

---

## Context

The `memories` table has a foreign key constraint:

```sql
FOREIGN KEY(session_id) REFERENCES sessions(craft_session_id)
```

The original design required the server startup code to call `register_session()` explicitly before any `remember()` call. In practice, this call was never made. The `sessions` table remained empty for every server invocation.

When `remember()` executed `INSERT OR IGNORE INTO memories (...)`, the FK constraint silently rejected the row (no matching session in `sessions`). The `INSERT OR IGNORE` clause treated this as a conflict and returned without error. The tool returned "Duplicate memory skipped" — a false positive — instead of an actual error.

**Evidence:** `sessions COUNT = 0`, `memories COUNT = 0`, `facts COUNT = 13` (facts table has no FK to sessions — worked fine).

This bug caused **zero memories to be saved** since the system was first deployed, despite the server reporting healthy on every status check.

---

## Decision

Auto-call `_db_register_session()` inside `_get_conn()`, immediately after creating the database connection:

```python
def _get_conn():
    global _conn
    if _conn is None:
        _conn = _db_get_connection(WORKSPACE_ID)
        # Ensure session row exists before any memory INSERT (FK constraint)
        _db_register_session(_conn, CRAFT_SESSION_ID, WORKSPACE_ID)
    return _conn
```

`_db_register_session` uses `INSERT OR IGNORE` on `sessions(craft_session_id)` which is UNIQUE — the call is idempotent. Multiple calls with the same session ID are safe.

---

## Consequences

**Positive:**
- `remember()` works correctly from the first call in any session
- Session registration is guaranteed — no caller can forget it
- Idempotent: multiple invocations of `_get_conn()` are safe
- Fixes a silent data loss bug with no user-visible change to the API

**Negative:**
- Session metadata fields (`model`, `provider`, `prompt_tokens`) remain empty — we only have `craft_session_id` and `workspace_id` at connection time. These fields were optional and are not yet used in queries.

**Alternatives rejected:**
- **Call `register_session()` in `remember()` directly**: Mixes infrastructure concern (session tracking) into a business tool. Rejected in favor of centralizing it in the connection layer.
- **Remove the FK constraint**: Would lose referential integrity. Rejected — integrity is valuable for future analytics and data export.
- **Call `register_session()` at server startup**: Fragile — startup code is separate from the connection. The FK violation re-appears if someone calls the DB layer directly. Rejected in favor of enforcing it at the connection level.

**Regression test:** `test_session_auto_registration()` in `tests/test_server.py` verifies that calling `remember()` without explicit `register_session()` succeeds and creates a row in `sessions`.
