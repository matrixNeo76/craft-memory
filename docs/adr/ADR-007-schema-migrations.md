# ADR-007: Internal Migration Runner Instead of executescript(schema.sql)

**Date:** 2026-04-30  
**Status:** Accepted  
**Deciders:** Matrix (AureSystem)

---

## Context

The original `init_db()` called `conn.executescript(schema.sql)` on every startup.
Since all CREATE statements use `IF NOT EXISTS`, this was safe but:

- Any schema change required manual migration (no versioning)
- Adding a column, changing a constraint, or dropping an index had no automated path
- Users upgrading from an older version would be stuck with the old schema

## Decision

Replace `executescript(schema.sql)` with a lightweight internal migration runner
(`run_migrations()` in `db.py`) that:

1. Reads `MAX(version)` from the `schema_version` table (already in schema.sql)
2. Applies `schema.sql` as version 1 only for fresh databases
3. Applies numbered SQL files from `src/craft_memory_mcp/migrations/` in order
4. Records each applied version in `schema_version` with a timestamp

Migration files are named `NNN_description.sql` where NNN is a zero-padded integer.
The runner applies all migrations with version > current in ascending order.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Alembic | Full-featured, widely used | Heavy dependency, overkill for SQLite |
| Flyway | Battle-tested | Java-based, wrong ecosystem |
| Manual scripts | Simple | Error-prone, not automated |
| **Internal runner** | Zero deps, ~30 lines | Less features than full ORMs |

## Consequences

**Positive:**
- Zero new dependencies
- Schema changes are versioned and automated
- Existing DBs upgrade cleanly on next server start
- Migrations are plain SQL — readable and auditable

**Negative:**
- No rollback support (SQLite limitations make this hard anyway)
- Mid-migration failure leaves partial state (acceptable for local dev tool)
- `PRAGMA foreign_keys=OFF` required during migrations that recreate tables
