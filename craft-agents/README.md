# Craft Agents Integration

This directory contains ready-to-use automation templates for integrating Craft Memory with [Craft Agents](https://craft.do/agents).

## Files

| File | Description |
|------|-------------|
| `source/config.json` | MCP source configuration — tells Craft Agents how to connect to the memory server |
| `source/guide.md` | Usage guide loaded by the agent before using memory tools |
| `automations.json` | 13 automation templates across 3 types (scheduled, event-based, agentic) |

## MCP Source Setup

Copy `source/config.json` and `source/guide.md` to your workspace sources directory:

```
~/.craft-agent/workspaces/{your-workspace}/sources/memory/config.json
~/.craft-agent/workspaces/{your-workspace}/sources/memory/guide.md
```

The `config.json` registers the source as an HTTP MCP connection to `http://localhost:8392/mcp`. The server must be running before the agent can use it — start it with `craft-memory start` or `start-http.bat` (Windows) / `start-memory.sh` (Unix).

Then add `"memory"` to the `enabledSourceSlugs` array in your workspace config.

## Automations (13 total)

### 📅 Scheduled (SchedulerTick)

| Event | Name | Cron | What it does |
|-------|------|------|-------------|
| `SchedulerTick` | Memory: Daily Maintenance | `0 3 * * *` | Consolidates memories, promotes facts, flags stale loops (pre-existing) |
| `SchedulerTick` | Session: Daily Report | `0 18 * * 1-5` | Generates end-of-day session report with metrics (total, completed, orphaned) |
| `SchedulerTick` | Session: Morning Reminder | `0 9 * * 1-5` | Checks for orphaned sessions and open loops, presents morning briefing |

### ⚡ Event-based

| Event | Name | What it does |
|-------|------|-------------|
| `SessionStart` | Memory: Recover Session Context | Ensures server is running, recovers recent memories and open loops. Instructs the agent to proactively trigger memory saves via labels. |
| `SessionEnd` | Memory: Save Session Handoff | Saves decisions, discoveries, facts; closes resolved loops; generates a handoff summary. |
| `SessionEnd` | Memory: Batch Save Discoveries (complement) | After the handoff protocol, saves minor discoveries/changes/notes via `batch_remember()` for atomic search. |
| `LabelAdd` | Memory: Promote Important/Fact-Candidate Labels | Triggered when agent adds `important` or `fact-candidate` label. Saves memories or facts automatically. |
| `UserPromptSubmit` | Session: Classify Intent | Classifies the first user prompt as refactoring/bugfix/feature/deploy/exploration. Tags the session for later query. |

### 🤖 Agentic

| Event | Name | What it does |
|-------|------|-------------|
| `SubagentStop` | Agentic: Track Subagent Activity | Records when a sub-agent completes its work, with tags for monitoring |
| `PostToolUseFailure` | Agentic: Tool Failure Alert | Records tool failures; escalates to open loop if >3 failures on same tool |
| `TaskCompleted` | Agentic: Track Task Completion | Records significant task completions; closes related open loops |
| `TeammateIdle` | Agentic: Detect Idle Agent | Creates open loops when agents are detected idle; escalates on frequent idle events |
| `PermissionDenied` | Agentic: Permission Bottleneck Tracker | Tracks permission denials; suggests rule exceptions for repeatedly blocked tools |

## How the proactive trigger pattern works

The agent calls `set_session_labels(['important'])` when it completes significant work — this fires the `LabelAdd` automation which saves to memory automatically, without waiting for the user or session end.

```
Agent completes phase → set_session_labels(['important'])
                              ↓
                    LabelAdd automation fires
                              ↓
                    remember() called automatically
                              ↓
                    Memory saved, user informed
```

## Skill: session-manager

A companion skill in `skills/session-manager/` provides natural-language query patterns for all 3 automation types:

| Query | What it finds |
|-------|---------------|
| "mostra sessioni attive" | Active sessions via `search_memory(tag="session-start")` |
| "riepilogo giornata" | Daily report via `search_memory(tag="session:report")` |
| "sessione [ID]" | Session detail via temporal/contextual search |
| "sessioni orfane" | Orphaned sessions without save_summary |
| "attività agenti/subagenti" | Agentic events via `search_memory(tag="agentic:*")` |
| "colli di bottiglia" | Permission denials and tool failures |
| "stato salute workspace" | Aggregate stats via `memory_stats()` |

## Installation

Merge the automations from `automations.json` into your workspace `automations.json` (located at `~/.craft-agent/workspaces/{your-workspace}/automations.json`).

The `craft-memory install` CLI command handles this automatically if you run it from the Craft Agents workspace.
