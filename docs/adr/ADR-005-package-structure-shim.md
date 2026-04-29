# ADR-005: Canonical Package in craft_memory_mcp with Shim Entry Points

**Status:** Accepted  
**Date:** 2026-04-29  

---

## Context

The original repository had two nearly-identical copies of the server logic:

- `src/server.py` (371 lines) — standalone entry point used by `start-http.bat` and `ensure-running.py`
- `src/craft_memory_mcp/server.py` (387 lines) — package version used when installed via `pip install -e .`

Similarly for the database layer:
- `src/db.py` (527 lines)
- `src/craft_memory_mcp/db.py` (identical logic)

Any bug fix had to be applied in two places. The FK fix (ADR-004) was originally missed in one copy. This dual-maintenance burden is unacceptable for a project intended for distribution.

The root cause: the project started as a standalone script (`src/server.py`) and was later packaged (`src/craft_memory_mcp/`), but the original files were not removed.

---

## Decision

Designate `src/craft_memory_mcp/` as the **single canonical source of truth**.

Reduce `src/server.py` and `src/db.py` to **shims** — minimal files that delegate entirely to the package:

```python
# src/server.py
"""Craft Memory — entry point shim. Delegates to craft_memory_mcp.server."""
from craft_memory_mcp.server import run_server
if __name__ == "__main__":
    run_server()
```

```python
# src/db.py
"""Craft Memory — database layer shim."""
from craft_memory_mcp.db import *  # noqa: F401, F403
```

The `craft_memory_mcp` package is installed via `pip install -e .` (hatchling build, `src/craft_memory_mcp` wheel target). The `craft-memory` CLI entry point in `pyproject.toml` points directly to `craft_memory_mcp.cli:main`.

**Additional change:** `src/craft_memory_mcp/schema.sql` was created by copying `src/schema.sql`, because `craft_memory_mcp/db.py` resolves the schema path relative to `__file__` (`Path(__file__).parent / "schema.sql"`).

---

## Consequences

**Positive:**
- Single source of truth — all fixes, features, and changes in one place
- `pip install -e .` + `craft-memory` CLI works correctly
- Shim files can be removed in a future version once all callers use the CLI
- Schema file is co-located with the code that uses it

**Negative:**
- `src/server.py` and `src/db.py` still exist (as shims) — potential confusion for new contributors who might edit them instead of the package
- Two copies of `schema.sql` (`src/schema.sql` and `src/craft_memory_mcp/schema.sql`) — must be kept in sync manually until `src/schema.sql` is removed

**Future cleanup:**
- Remove `src/server.py`, `src/db.py`, and `src/schema.sql` once all references point to the CLI or the package directly
- Update `start-http.bat` to use `craft-memory serve` instead of calling `python src/server.py`
