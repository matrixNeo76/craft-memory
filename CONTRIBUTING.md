# Contributing to Craft Memory

Thank you for your interest in contributing. This is a community project — all contributions are welcome.

## Getting Started

```bash
git clone https://github.com/your-org/craft-memory.git
cd craft-memory
pip install -e ".[dev]"
```

## Development Setup

The package is in `src/craft_memory_mcp/`. The `src/server.py` and `src/db.py` files are shims that delegate to the package — do not add logic there.

```
src/
├── craft_memory_mcp/    # Edit here
│   ├── server.py        # FastMCP server + 7 tools
│   ├── db.py            # SQLite layer
│   ├── schema.sql       # Database schema
│   └── cli.py           # craft-memory CLI
├── server.py            # Shim (do not edit)
└── db.py                # Shim (do not edit)
```

## Running Tests

```bash
pytest
pytest --cov=craft_memory_mcp   # with coverage
```

Tests live in `tests/`. When adding features, add tests first (TDD preferred).

## Code Style

- Python 3.11+ syntax
- Type hints on all public functions
- No external dependencies beyond `fastmcp` and `uvicorn`
- SQLite-only storage (no ORM, no other databases)

## Architecture Decisions

Major design decisions are documented in `docs/adr/`. Read them before proposing changes that touch:

- Transport mechanism (ADR-001)
- FastMCP configuration (ADR-002)
- Storage backend (ADR-003)
- Session registration (ADR-004)
- Package structure (ADR-005)

If your change requires a new architectural decision, add an ADR.

## Submitting Changes

1. Fork the repository
2. Create a branch: `git checkout -b feat/your-feature`
3. Write tests for your change
4. Ensure all tests pass: `pytest`
5. Open a pull request with a clear description of the problem and solution

## Reporting Bugs

Open an issue with:
- OS and Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (run server with `--log-level debug`)

## Areas That Need Help

- Unix/macOS startup script (`start-memory.sh`)
- GitHub Actions CI matrix (3 OS × 3 Python versions)
- PyPI publish workflow
- Additional MCP tool ideas (e.g., `export_memory`, `import_memory`)
- i18n for skills and guide files

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
