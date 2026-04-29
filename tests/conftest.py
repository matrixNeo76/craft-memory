"""Shared pytest fixtures for Craft Memory test suite."""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID


@pytest.fixture
def tmp_db_dir(tmp_path, monkeypatch):
    """Temporary directory for test databases. Sets CRAFT_MEMORY_DB_DIR env var."""
    monkeypatch.setenv("CRAFT_MEMORY_DB_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def db_conn(tmp_db_dir):
    """Fresh SQLite connection with schema applied, closed after test."""
    from craft_memory_mcp.db import init_db
    db_path = tmp_db_dir / f"{TEST_WORKSPACE_ID}.db"
    conn = init_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def registered_conn(db_conn):
    """DB connection with a test session already registered.

    Use this fixture for tests that call remember() or create_open_loop(),
    which require a session row (FK constraint on memories and open_loops).
    """
    from craft_memory_mcp.db import register_session
    register_session(db_conn, TEST_SESSION_ID, TEST_WORKSPACE_ID)
    return db_conn


@pytest.fixture
def server_module(tmp_db_dir, monkeypatch):
    """Server module with patched workspace/session globals and fresh DB connection.

    Patches WORKSPACE_ID and CRAFT_SESSION_ID at module level so tool handlers
    use the test database. Manually resets _conn before and after each test.
    """
    import craft_memory_mcp.server as srv

    # Patch module-level constants (read by tool handlers at call time)
    monkeypatch.setattr(srv, "WORKSPACE_ID", TEST_WORKSPACE_ID)
    monkeypatch.setattr(srv, "CRAFT_SESSION_ID", TEST_SESSION_ID)

    # Reset connection so tests start with a clean DB
    srv._conn = None

    yield srv

    # Close any connection opened during the test, then reset
    if srv._conn:
        try:
            srv._conn.close()
        except Exception:
            pass
        srv._conn = None


@pytest.fixture
def test_app(server_module):
    """ASGI application for HTTP testing via starlette.testclient.TestClient."""
    return server_module.mcp.streamable_http_app()


