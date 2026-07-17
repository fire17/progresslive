# IA.md — information architecture (ladder-aware)

Zoom levels, declared before the views are built. Each tier answers one question and
drills into the next.

## Entities

| Entity | Is | Lives in |
|---|---|---|
| **Project** | one tracked build (agentworkatlas, moneyloop, …) | `projects/<slug>/` |
| **Phase** | one lane of work in a project | `board.json → phases[]` |
| **Agent** | a live worker on the project | `board.json → roster[]` |
| **Event** | an immutable moment in history | `events.jsonl` (append-only) |
| **Proof** | a verified claim (what was actually run) | `board.json → proof[]` |

## View tiers (the ladder)

**Tier 1 — FLEET (`#/`)** · "Where is everything, right now?"
Every project, one live row each: overall bar, phase-you-are-here, live/stale dot, last
event, agent count. KPIs: overall %, phases done/total, seconds-since-update.
→ drills into Tier 2.

**Tier 2 — PROJECT (`#/<slug>`)** · "Where exactly are we on this one, and is it true?"
The board fire17 asked for, rendered: phase rows w/ bars + % + status + honest ETA,
exactly one ◀ YOU ARE HERE, the agent roster, the proof table, the event feed.
KPIs: per-phase %, ETA, delta since last report.
→ drills into Tier 3.

**Tier 3 — HISTORY (`#/<slug>` event feed, filterable)** · "How did we get here?"
Append-only timeline: every update/milestone/note/report with timestamp + delta.
Current state (board) and history (events) are BOTH always visible — the vision demands
"both see the current and historical progress".

## Data sources per KPI (no synthetic data, ever)

| KPI | Source | Honest? |
|---|---|---|
| phase pct/status/eta | `board.json`, written by the managing agent from verified facts | agent-asserted; agent must verify before writing |
| roster | `board.json`, from SWARM.md + live task board | agent-asserted |
| proof rows | `board.json → proof[]`, each = a command actually run + its result | evidence-backed |
| events | `events.jsonl`, append-only, never rewritten | immutable record |
| live/stale | computed client-side from `board.meta.updated` age | machine-derived, cannot be faked |

## Additive-by-design (the future arc, not built yet)

The data contract is a directory of files. Therefore: an MCP server, a push API, or any
other harness writing the same `board.json` / `events.jsonl` shapes is **additive** — no
schema change, no migration. Fleet view already iterates `projects/*/`, so a new project
appears with zero code edits. That is the whole reason the store is files, not a DB.
