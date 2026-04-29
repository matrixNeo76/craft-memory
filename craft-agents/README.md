# Craft Agents Integration

This directory contains ready-to-use automation templates for integrating Craft Memory with [Craft Agents](https://craft.do/agents).

## Files

| File | Description |
|------|-------------|
| `automations.json` | 4 automation templates (SessionStart, SessionEnd, SchedulerTick, LabelAdd) |

## Automations

| Event | Name | What it does |
|-------|------|-------------|
| `SessionStart` | Memory: Recover Session Context | Ensures server is running, recovers recent memories and open loops. Instructs the agent to **proactively trigger memory saves** via labels during the session. |
| `SessionEnd` | Memory: Save Session Handoff | Saves decisions, discoveries, facts; closes resolved loops; generates a handoff summary. |
| `SchedulerTick` | Memory: Daily Maintenance | Runs at 03:00 Europe/Rome. Consolidates memories, flags stale open loops, generates maintenance report. |
| `LabelAdd` | Memory: Promote Important/Fact-Candidate Labels | Triggered when agent adds `important` or `fact-candidate` label to the session. Saves memories or facts automatically. |

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

## Installation

Merge the automations from `automations.json` into your workspace `automations.json` (located at `~/.craft-agent/workspaces/{your-workspace}/automations.json`).

The `craft-memory install` CLI command handles this automatically if you run it from the Craft Agents workspace.
