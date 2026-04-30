"""Sprint 3 — Boundary Detection Policy tests.

8 tests covering classify_memory_event classification rules:
- DISCARD: too short or trivial
- OPEN_LOOP: task/todo keywords
- PROCEDURE_CANDIDATE: multi-step patterns
- CORE_CANDIDATE: high importance or invariant keywords
- FACT_CANDIDATE: factual statement patterns
- EPISODIC: default classification
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from craft_memory_mcp.db import MemoryClass, classify_memory_event


def test_classify_too_short_is_discard():
    """Content under 15 chars is classified as DISCARD."""
    cls, reason = classify_memory_event("ok")
    assert cls == MemoryClass.DISCARD


def test_classify_trivial_response_is_discard():
    """Conversational filler ('done.', 'yes', 'noted') is classified as DISCARD."""
    cls, reason = classify_memory_event("done.")
    assert cls == MemoryClass.DISCARD
    cls2, _ = classify_memory_event("understood")
    assert cls2 == MemoryClass.DISCARD


def test_classify_todo_is_open_loop():
    """Content with TODO/fixme keywords is classified as OPEN_LOOP."""
    cls, reason = classify_memory_event("TODO: fix the authentication bug in login flow")
    assert cls == MemoryClass.OPEN_LOOP


def test_classify_pending_is_open_loop():
    """Content with 'pending' or 'blocked' is classified as OPEN_LOOP."""
    cls, reason = classify_memory_event("Blocked: need approval from DevOps team to deploy")
    assert cls == MemoryClass.OPEN_LOOP


def test_classify_procedure_pattern_is_procedure_candidate():
    """Multi-step content ('Step 1... Step 2...') is PROCEDURE_CANDIDATE."""
    cls, reason = classify_memory_event(
        "Step 1: pull the branch. Step 2: run migrations. Step 3: deploy."
    )
    assert cls == MemoryClass.PROCEDURE_CANDIDATE


def test_classify_high_importance_is_core_candidate():
    """importance >= 8 in context_signals yields CORE_CANDIDATE."""
    cls, reason = classify_memory_event(
        "All API calls must include the Authorization header",
        context_signals={"importance": 9},
    )
    assert cls == MemoryClass.CORE_CANDIDATE


def test_classify_always_keyword_is_core_candidate():
    """'Always' / 'never' invariant keywords yield CORE_CANDIDATE."""
    cls, reason = classify_memory_event("Always use HTTPS for external endpoints")
    assert cls == MemoryClass.CORE_CANDIDATE


def test_classify_fact_pattern_is_fact_candidate():
    """Factual declarative statements are classified as FACT_CANDIDATE."""
    cls, reason = classify_memory_event("The DB URL is set to localhost:5432 in production")
    assert cls == MemoryClass.FACT_CANDIDATE


def test_classify_default_is_episodic():
    """General observations without special signals default to EPISODIC."""
    cls, reason = classify_memory_event(
        "Reviewed the pull request and left comments on the error handling section"
    )
    assert cls == MemoryClass.EPISODIC


def test_classify_returns_reason_string():
    """classify_memory_event always returns a non-empty reason string."""
    _, reason = classify_memory_event("Some random memory content for testing")
    assert isinstance(reason, str)
    assert len(reason) > 0
