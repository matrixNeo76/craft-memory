---
name: "Memory Protocol"
description: "Mandatory protocol for reading/writing persistent memory across sessions. Triggers on session start and when agent needs to store or retrieve context."
requiredSources:
  - memory
---

# Memory Protocol

This skill defines the mandatory protocol for using the Craft Memory system. Every session MUST follow this protocol to ensure cross-session continuity.

## Mandatory: Session Start Sequence

When a new session begins, you MUST execute this sequence BEFORE doing any other work:

1. **Call `get_recent_memory(scope="workspace", limit=10)`** — Recover the 10 most recent memories
2. **Call `list_open_loops()`** — Check for any incomplete tasks or follow-ups
3. **Synthesize context** — Briefly summarize what you recovered for the user

Example opening:
> "I recovered context from your previous sessions. Here's what I found: [summary]. There are N open loops: [list]."

## When to Use `remember`

Store a memory ONLY when it has real, lasting value:

| ✅ DO remember | ❌ DON'T remember |
|---|---|
| Architectural decisions and why | Trivial observations |
| Bug root causes and fixes | Every message or action |
| Important discoveries about the codebase | Information easily found in files |
| Breaking changes or migrations | Temporary state (file currently open) |
| User preferences or constraints | Redundant or duplicate info |

**Category guide:**
- `decision` — When a deliberate choice was made (include rationale)
- `discovery` — Important finding about the codebase/system
- `bugfix` — Root cause + fix for a bug
- `feature` — Feature implementation details
- `refactor` — Structural change and motivation
- `change` — Any other significant change
- `note` — General important note

**Importance guide:**
- `8-10` — Architectural decisions, breaking changes, critical bugs
- `5-7` — Normal decisions, discoveries, feature work
- `1-4` — Minor notes, low-priority observations

## When to Use `upsert_fact`

Store a fact when you have CONFIRMED, STABLE knowledge about the project:

- Tech stack choices (e.g., `tech_stack: "Python + FastMCP + SQLite"`)
- Database URLs or connection info
- Authentication providers and methods
- Project structure conventions
- API endpoints or schemas
- Third-party service integrations
- User preferences about the project

Facts should be:
- **Stable**: unlikely to change frequently
- **Confirmed**: verified, not guessed
- **Keyed**: use descriptive, namespaced keys (e.g., `auth_provider`, `db_schema_version`)

Set `confidence` to:
- `1.0` — Verified fact
- `0.8-0.9` — Very likely but not 100% confirmed
- `0.5-0.7` — Informed assumption, needs verification

## When to Create/Open/Close Loops

**Create an open loop** when:
- A task is started but not completed
- A follow-up is needed in a future session
- A decision is deferred and needs revisiting

**Close an open loop** when:
- The task is completed
- The follow-up has been addressed
- The decision has been made

## When to Use `search_memory`

Use search when:
- You need context about a past decision or discovery
- A user asks "did we already decide on X?"
- You want to check if something was tried before
- You need to recover context about a specific topic

## Anti-Patterns to Avoid

1. **Memory spam**: Don't remember every single action or message
2. **Fact without evidence**: Don't upsert facts that are guesses
3. **Orphan loops**: Don't create loops you never intend to close
4. **Ignoring context**: Don't skip the session start sequence
5. **Duplicate content**: The system auto-deduplicates, but try to be concise
