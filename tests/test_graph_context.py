"""Sprint 7: multi-hop graph context traversal — get_graph_context."""
import pytest
from constants import TEST_SESSION_ID, TEST_WORKSPACE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mem(conn, content: str) -> int:
    from craft_memory_mcp.db import remember
    return remember(conn, TEST_SESSION_ID, TEST_WORKSPACE_ID, content)


def _edge(conn, src: int, tgt: int, relation: str = "extends") -> None:
    from craft_memory_mcp.db import link_memories
    link_memories(conn, src, tgt, relation, TEST_WORKSPACE_ID)


# ---------------------------------------------------------------------------
# Basic traversal
# ---------------------------------------------------------------------------

class TestGetGraphContext:
    def test_no_neighbors_returns_center_only(self, registered_conn):
        """Isolated memory returns context with just the center node."""
        from craft_memory_mcp.db import get_graph_context
        mid = _mem(registered_conn, "isolated memory")
        ctx = get_graph_context(registered_conn, mid, TEST_WORKSPACE_ID)
        assert ctx is not None
        assert ctx["center"]["id"] == mid
        assert ctx["total_nodes"] == 1
        assert ctx["total_edges"] == 0

    def test_depth_1_returns_direct_neighbors(self, registered_conn):
        """depth=1 returns center + direct neighbors only."""
        from craft_memory_mcp.db import get_graph_context
        root = _mem(registered_conn, "root memory")
        n1 = _mem(registered_conn, "neighbor one")
        n2 = _mem(registered_conn, "neighbor two")
        _edge(registered_conn, root, n1)
        _edge(registered_conn, root, n2)
        ctx = get_graph_context(registered_conn, root, TEST_WORKSPACE_ID, depth=1)
        node_ids = {n["id"] for n in ctx["nodes"]}
        assert root in node_ids
        assert n1 in node_ids
        assert n2 in node_ids
        assert ctx["total_nodes"] == 3

    def test_depth_2_follows_chain(self, registered_conn):
        """depth=2 follows A→B→C chain and includes C."""
        from craft_memory_mcp.db import get_graph_context
        a = _mem(registered_conn, "node A")
        b = _mem(registered_conn, "node B")
        c = _mem(registered_conn, "node C")
        _edge(registered_conn, a, b)
        _edge(registered_conn, b, c)
        ctx = get_graph_context(registered_conn, a, TEST_WORKSPACE_ID, depth=2)
        node_ids = {n["id"] for n in ctx["nodes"]}
        assert c in node_ids
        assert ctx["total_nodes"] == 3

    def test_depth_1_stops_at_one_hop(self, registered_conn):
        """depth=1 does NOT include second-hop nodes."""
        from craft_memory_mcp.db import get_graph_context
        a = _mem(registered_conn, "chain A")
        b = _mem(registered_conn, "chain B")
        c = _mem(registered_conn, "chain C - should be excluded")
        _edge(registered_conn, a, b)
        _edge(registered_conn, b, c)
        ctx = get_graph_context(registered_conn, a, TEST_WORKSPACE_ID, depth=1)
        node_ids = {n["id"] for n in ctx["nodes"]}
        assert c not in node_ids

    def test_depth_map_correct_distances(self, registered_conn):
        """depth_map records correct hop distance for each node."""
        from craft_memory_mcp.db import get_graph_context
        a = _mem(registered_conn, "dist A")
        b = _mem(registered_conn, "dist B")
        c = _mem(registered_conn, "dist C")
        _edge(registered_conn, a, b)
        _edge(registered_conn, b, c)
        ctx = get_graph_context(registered_conn, a, TEST_WORKSPACE_ID, depth=2)
        dm = ctx["depth_map"]
        assert dm[a] == 0
        assert dm[b] == 1
        assert dm[c] == 2

    def test_handles_cycle_no_infinite_loop(self, registered_conn):
        """Cyclic graph (A→B→A) does not cause infinite recursion."""
        from craft_memory_mcp.db import get_graph_context
        a = _mem(registered_conn, "cycle A")
        b = _mem(registered_conn, "cycle B")
        _edge(registered_conn, a, b, "extends")
        _edge(registered_conn, b, a, "implements")
        ctx = get_graph_context(registered_conn, a, TEST_WORKSPACE_ID, depth=3)
        assert ctx is not None
        assert ctx["total_nodes"] == 2

    def test_edges_included_with_relation(self, registered_conn):
        """Context edges carry relation type."""
        from craft_memory_mcp.db import get_graph_context
        src = _mem(registered_conn, "edge src")
        tgt = _mem(registered_conn, "edge tgt")
        _edge(registered_conn, src, tgt, "caused_by")
        ctx = get_graph_context(registered_conn, src, TEST_WORKSPACE_ID, depth=1)
        assert len(ctx["edges"]) >= 1
        assert any(e["relation"] == "caused_by" for e in ctx["edges"])

    def test_invalid_memory_returns_none(self, registered_conn):
        """Nonexistent memory_id returns None without error."""
        from craft_memory_mcp.db import get_graph_context
        result = get_graph_context(registered_conn, 99999, TEST_WORKSPACE_ID)
        assert result is None

    def test_workspace_isolation(self, tmp_db_dir):
        """Graph traversal does not cross workspace boundaries."""
        from craft_memory_mcp.db import init_db, register_session, remember, link_memories, get_graph_context
        db_a = init_db(tmp_db_dir / "ws_ctx_a.db")
        register_session(db_a, "s-a", "ws-a")
        a = remember(db_a, "s-a", "ws-a", "ws-a root")
        b = remember(db_a, "s-a", "ws-a", "ws-a neighbor")
        link_memories(db_a, a, b, "extends", "ws-a")
        # Query with wrong workspace_id should return None or just center
        ctx = get_graph_context(db_a, a, "ws-b")
        assert ctx is None


# ---------------------------------------------------------------------------
# Inbound edges traversal
# ---------------------------------------------------------------------------

class TestGraphContextInbound:
    def test_traverses_inbound_edges(self, registered_conn):
        """get_graph_context includes nodes connected via inbound edges."""
        from craft_memory_mcp.db import get_graph_context
        parent = _mem(registered_conn, "parent node")
        child = _mem(registered_conn, "child node")
        _edge(registered_conn, parent, child)
        # Query from child — should find parent via inbound edge
        ctx = get_graph_context(registered_conn, child, TEST_WORKSPACE_ID, depth=1)
        node_ids = {n["id"] for n in ctx["nodes"]}
        assert parent in node_ids
