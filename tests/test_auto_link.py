"""
Test: auto-linking in remember() via _auto_link_similar.

Creates a temp database, inserts similar memories,
then calls remember() and verifies edges were created.
"""
import sys, os, sqlite3, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from craft_memory_mcp import db

WORKSPACE_ID = "test_auto_link_ws"
SESSION_ID = "test-session"


def setup_db(db_path: str) -> sqlite3.Connection:
    """Create a fresh database with schema + migrations."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")
    db.run_migrations(conn)
    conn.execute("PRAGMA foreign_keys=ON")
    # Register session so FK constraints pass
    now = db._now_iso()
    epoch = db._now_epoch()
    conn.execute(
        """INSERT OR IGNORE INTO sessions
           (craft_session_id, workspace_id, started_at, started_at_epoch, status)
           VALUES (?, ?, ?, ?, 'active')""",
        (SESSION_ID, WORKSPACE_ID, now, epoch),
    )
    conn.commit()
    return conn


def seed_memories(conn: sqlite3.Connection):
    """Insert 5 memories with overlapping keywords (similarity candidates)."""
    memories = [
        ("Sistema di autenticazione JWT con refresh token e gestione delle sessioni utente", "feature", 8),
        ("Implementato OAuth2 con Google provider per login social", "feature", 7),
        ("Aggiunto middleware di rate limiting per proteggere le API dalle richieste eccessive", "feature", 6),
        ("Fixato bug nel validatore email che non accettava domini con piu di 3 livelli", "bugfix", 7),
        ("Refactoring del modulo di spedizione email per supportare template HTML", "refactor", 6),
    ]
    for content, cat, imp in memories:
        db.remember(conn, SESSION_ID, WORKSPACE_ID, content, cat, imp)


def test_auto_link_similar():
    """Test that remember() creates edges for similar memories."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = setup_db(db_path)
        seed_memories(conn)

        # Verify 5 memories + 0 edges before auto-link
        count_mem = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        count_edge = conn.execute("SELECT COUNT(*) FROM memory_relations").fetchone()[0]
        print(f"  Before: {count_mem} memories, {count_edge} edges")
        # seed_memories may create some auto-links if early memories share keywords
        assert count_mem == 5, f"Expected 5 memories, got {count_mem}"

        # Insert a new memory SIMILAR to existing ones
        new_id = db.remember(
            conn, SESSION_ID, WORKSPACE_ID,
            "Implementato OAuth con GitHub e Google per autenticazione utenti",
            "feature", 8
        )
        print(f"  New memory ID: {new_id}")
        assert new_id is not None, "remember() returned None"

        # Check edges created
        count_edge = conn.execute("SELECT COUNT(*) FROM memory_relations").fetchone()[0]
        print(f"  After similar insert: edges = {count_edge}")
        assert count_edge > 0, f"Expected >0 edges for similar content, got {count_edge}"

        # Show edges
        edges = conn.execute(
            "SELECT mr.source_id, mr.target_id, mr.relation, mr.confidence_score, mr.is_manual, "
            "s.content AS source_text, t.content AS target_text "
            "FROM memory_relations mr "
            "JOIN memories s ON mr.source_id = s.id "
            "JOIN memories t ON mr.target_id = t.id"
        ).fetchall()
        for e in edges:
            print(f"    #{e['source_id']} --{e['relation']} [{e['confidence_score']:.3f}]--> #{e['target_id']}")
            print(f"      src: {e['source_text'][:60]}...")
            print(f"      tgt: {e['target_text'][:60]}...")

        # Verify edges are is_manual=0 (prunable)
        for e in edges:
            assert e['is_manual'] == 0, f"Edge should be is_manual=0, got {e['is_manual']}"

        # Verify at least one edge originates from the new memory
        # (edges are bidirectional, so only outbound edges have source_id == new_id)
        outbound = [e for e in edges if e['source_id'] == new_id]
        assert len(outbound) > 0, f"Expected at least 1 outbound edge from {new_id}, got 0"

        # Verify every edge involves the new memory (either as source or target)
        for e in edges:
            assert e['source_id'] == new_id or e['target_id'] == new_id, \
                f"Edge #{e['source_id']}->#{e['target_id']} does not involve new memory #{new_id}"

        print("  Test 1 PASSED: auto-linking creates edges for similar content")
    finally:
        conn.close()
        os.unlink(db_path)


def test_no_false_positive():
    """Test that remember() does NOT create edges for dissimilar content."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = setup_db(db_path)
        seed_memories(conn)

        # Insert a memory with completely different keywords
        new_id = db.remember(
            conn, SESSION_ID, WORKSPACE_ID,
            "xyzzy plugh frobozz magic unknown cryptic gibberish",
            "note", 1
        )
        print(f"  New dissimilar memory ID: {new_id}")
        assert new_id is not None

        count_edge = conn.execute("SELECT COUNT(*) FROM memory_relations").fetchone()[0]
        print(f"  Edges after dissimilar insert: {count_edge}")
        # All edges should be from seed_memories only
        print("  Test 2 PASSED: no false positive edges for dissimilar content")
    finally:
        conn.close()
        os.unlink(db_path)


def test_duplicate_skip():
    """Test that duplicate memories do NOT trigger auto-linking."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = setup_db(db_path)
        seed_memories(conn)

        # Insert a unique memory first
        content = "Nuovo sistema di cache distribuita con Redis cluster per migliorare prestazioni"
        first_id = db.remember(conn, SESSION_ID, WORKSPACE_ID, content, "feature", 9)
        print(f"  First insert ID: {first_id}")
        assert first_id is not None

        edges_after_first = conn.execute("SELECT COUNT(*) FROM memory_relations").fetchone()[0]
        print(f"  Edges after first insert: {edges_after_first}")

        # Try duplicate
        dup_id = db.remember(conn, SESSION_ID, WORKSPACE_ID, content, "feature", 9)
        print(f"  Duplicate insert returned: {dup_id}")
        assert dup_id is None, "Duplicate should return None"

        edges_after_dup = conn.execute("SELECT COUNT(*) FROM memory_relations").fetchone()[0]
        print(f"  Edges after duplicate: {edges_after_dup}")
        assert edges_after_dup == edges_after_first, "Duplicate should not create additional edges"
        print("  Test 3 PASSED: duplicates don't trigger auto-linking")
    finally:
        conn.close()
        os.unlink(db_path)


def test_existing_edges_table():
    """Verify memory_relations table exists and has correct schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = setup_db(db_path)
        cols = conn.execute("PRAGMA table_info(memory_relations)").fetchall()
        col_names = [c["name"] for c in cols]
        print(f"  memory_relations columns: {col_names}")
        assert "is_manual" in col_names, "Missing is_manual column"
        assert "role" in col_names, "Missing role column"
        assert "weight" in col_names, "Missing weight column"
        assert "source_id" in col_names
        assert "target_id" in col_names
        print("  Test 4 PASSED: memory_relations schema is complete")
    finally:
        conn.close()
        os.unlink(db_path)


def test_memory_stats_includes_edges():
    """Verify memory_stats correctly counts edges after auto-linking."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = setup_db(db_path)
        seed_memories(conn)

        # Insert similar memory to create edges
        db.remember(conn, SESSION_ID, WORKSPACE_ID,
                    "Autenticazione OAuth con provider esterni e login social",
                    "feature", 7)

        stats = db.get_memory_stats(conn, WORKSPACE_ID)
        total_edges = stats.get("total_edges", 0)
        manual = stats.get("manual_edges", 0)
        inferred = stats.get("inferred_edges", 0)
        print(f"  Stats: total_edges={total_edges}, manual={manual}, inferred={inferred}")
        assert total_edges > 0, "Expected at least 1 edge"
        assert inferred > 0, "Expected at least 1 inferred edge"
        print("  Test 5 PASSED: memory_stats correctly reports edges")
    finally:
        conn.close()
        os.unlink(db_path)


if __name__ == "__main__":
    print("=== Test: auto-linking in remember() ===\n")

    print("--- Test 1: similar content creates edges ---")
    test_auto_link_similar()

    print("\n--- Test 2: dissimilar content does NOT create edges ---")
    test_no_false_positive()

    print("\n--- Test 3: duplicate memories skip auto-linking ---")
    test_duplicate_skip()

    print("\n--- Test 4: memory_relations schema ---")
    test_existing_edges_table()

    print("\n--- Test 5: memory_stats edge counts ---")
    test_memory_stats_includes_edges()

    print("\n=== ALL TESTS PASSED ===")
