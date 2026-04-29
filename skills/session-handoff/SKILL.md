---
name: "Session Handoff"
description: "Create a compact handoff document when ending a session or switching model/provider. Ensures next session can recover full context."
requiredSources:
  - memory
---

# Session Handoff

This skill creates a compact, structured handoff when a session ends. This is CRITICAL for ensuring continuity when switching model, provider, or opening a new session.

## When to Use This Skill

- When the user says "I'm done" or "let's wrap up"
- When the session is about to end (SessionEnd automation)
- Before switching to a different model or provider
- When explicitly asked to create a handoff

## Handoff Procedure

Execute these steps IN ORDER:

### Step 1: Save Key Decisions

For each significant decision made in this session, call:

```
remember(content="Decision: [what was decided] — Rationale: [why]", category="decision", importance=8, scope="workspace")
```

### Step 2: Save Discoveries

For each important discovery, call:

```
remember(content="Discovery: [what was found] — Impact: [what it means]", category="discovery", importance=7, scope="workspace")
```

### Step 3: Update Facts

For each confirmed, stable piece of knowledge, call:

```
upsert_fact(key="[descriptive_key]", value="[confirmed_value]", scope="workspace", confidence=[0.0-1.0])
```

### Step 4: Manage Open Loops

- **Close resolved loops**: `close_open_loop(id=[id], resolution="[how resolved]")`
- **Create new loops**: `remember` with category "note" or explicitly note the loop

For each new unresolved item, store it clearly:

```
remember(content="OPEN LOOP: [what needs doing] — Context: [why it matters]", category="note", importance=[6-9], scope="workspace")
```

### Step 5: Generate Summary

Call `summarize_scope(scope="workspace")` to generate a comprehensive snapshot.

### Step 6: Present Handoff to User

Show the user a compact summary:

```
📋 Session Handoff Complete

Decisions: [count]
  • [key decision 1]
  • [key decision 2]

Facts: [count]
  • [key]: [value]

Open Loops: [count]
  • [loop 1]
  • [loop 2]

Next Steps:
  • [step 1]
  • [step 2]
```

## Handoff Quality Rules

1. **Be specific**: "Decided to use SQLite+FTS5 over ChromaDB" > "Made a DB decision"
2. **Include rationale**: Always explain WHY a decision was made
3. **Note blockers**: If something is blocked, say what and why
4. **Flag uncertainties**: Mark things that need verification
5. **Keep it compact**: The handoff should be scannable in 30 seconds
6. **No noise**: Don't include trivial or obvious information

## Model/Provider Switch Checklist

When switching model or provider, ensure:

- [ ] All decisions are stored as memories (category: decision)
- [ ] All stable knowledge is stored as facts
- [ ] Open loops are listed and prioritized
- [ ] A summary has been generated via `summarize_scope`
- [ ] The user has seen the handoff summary

The NEXT session (with the new model) will automatically recover this context via the SessionStart automation and the memory-protocol skill.
