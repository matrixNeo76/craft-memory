---
name: "Session Manager"
description: "Query and manage multi-session state across Craft Agents. Use when the user asks about active sessions, daily reports, orphaned sessions, or wants to monitor agentic activity (subagents, tool failures, task completions)."
requiredSources:
  - memory
---

# Session Manager

This skill allows you to query the state of all sessions across Craft Agents using the Craft Memory MCP tools. It covers **scheduled reports**, **event-based classifications**, and **agentic activity tracking** (subagents, tool failures, task completions, idle agents, permission bottlenecks).

## When to Use This Skill

- "mostra le sessioni attive" / "show active sessions"
- "riepilogo della giornata" / "daily summary"
- "cosa ho fatto oggi" / "what did I do today"
- "ci sono sessioni dimenticate" / "are there orphan sessions"
- "sessione [ID]" / "what happened in session [ID]"
- "tool più usati" / "most used tools"
- "ci sono blocchi" / "are there bottlenecks"
- "cosa hanno fatto i subagenti" / "subagent activity"

## Query Patterns

### Q1 — Active Sessions

```
search_memory(tag="session-start", limit=20)
```

Then for each result, check if a corresponding `save_summary` exists (search by temporal proximity or same day). Active = has session-start but no save_summary.

Present as:
```
📋 Sessioni Attive: [N]

| Ora Inizio | Durata | Tags | Stato |
|------------|--------|------|-------|
| 09:15      | 2h 30m | refactoring | ⏳ in corso |
| 14:00      | 45m    | bugfix     | ⏳ in corso |
```

### Q2 — Daily Report

```
search_memory(tag="session:report", query="daily", limit=5)
```

If no report for today exists, generate one on-the-fly:
1. `search_memory(tag="session-start")` for today
2. Cross-reference with `search_memory(category="decision")` today
3. Build report manually

### Q3 — Session Detail

```
search_memory(query="{session_id_or_topic}", limit=30)
```

To find memories for a specific session, search by:
- The session content keywords
- Related tags (session:refactoring, session:bugfix, etc.)
- Temporal proximity

### Q4 — Orphaned Sessions

```
search_memory(tag="session:orphan", limit=20)
```

Or compute manually:
1. `search_memory(tag="session-start", limit=50)` — get all session starts
2. For each, check for `save_summary` near the same timestamp
3. Sessions without summary after >4h are orphans

### Q5 — Agentic Activity

**Subagents spawned:**
```
search_memory(tag="agentic:subagent", limit=20)
```

**Tool failures:**
```
search_memory(tag="agentic:tool-failure", limit=20)
```

**Task completions:**
```
search_memory(tag="agentic:task-completed", limit=20)
```

**Idle agent events:**
```
search_memory(tag="agentic:idle", limit=10)
```

**Permission bottlenecks:**
```
search_memory(tag="agentic:permission-denied", limit=10)
```

### Q6 — Critical Issues

```
list_open_loops()
```

Filter by priority `high` or `critical` — these represent blocked agents, failing tools, or unresolved bottlenecks.

Also check:
```
search_memory(tag="agentic:critical-failure", limit=10)
```

### Q7 — Full Workspace Health

```
memory_stats()
```

Shows aggregate counts: memories by category, open loops, facts, procedures.

## Automation Landscape Reference

This skill is the query-side counterpart of the 13 automations in `craft-agents/automations.json`:

| Area | Automations | Query Skill |
|------|-------------|-------------|
| **Scheduled** | Daily Maintenance (03:00), Daily Report (18:00), Morning Reminder (09:00) | Q1, Q2, Q4 |
| **Event-based** | SessionStart, SessionEnd + Batch Save, LabelAdd, UserPromptSubmit | Q1, Q3 |
| **Agentic** | SubagentStop, PostToolUseFailure, TaskCompleted, TeammateIdle, PermissionDenied | Q5, Q6, Q7 |

## Troubleshooting

**No results found**:
- Check that the memory server is running: `craft-memory check`
- Check that automations are enabled in the workspace config
- If using a new workspace, automations need at least one session to fire
- Agentic events (SubagentStop, etc.) only fire if the agent actually spawns subagents or encounters those conditions

**Too many results**:
- Narrow by tag: `search_memory(tag="session:classified", limit=10)`
- Narrow by category: focus on `category="decision"` or `category="bugfix"`
- Use temporal filters: search only memories from today
