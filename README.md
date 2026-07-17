# ProgressLive

Realtime dev-progress mission control. An agent writes truth into files; you open a tab
and see exactly where every project is — current board AND full append-only history —
with a liveness badge that cannot lie (derived from data age, not claims).

Born 2026-07-17 tracking **AgentWorkAtlas**; generic from day one. Founding words:
`VISION.md` (verbatim, sha256 `.deify/vision.sha256`).

## Run

```bash
python3 progress.py serve --port 8177   # site + JSON API
open http://localhost:8177/             # fleet view; #/<slug> per project
```

## Inside the swarm (v1.3.0)

Subitems nest to any depth (`--sub A.B.C`, recursive rollup). Agent rows expand —
state, current task, pane, last signal, the agent's own work tree. ACTIVE/IDLE/CLOSED
derives machine-side from status-drop recency; `swarm-scan --quiet` observes drops +
tmux panes silently on no-change ticks (change-gated wake law: idle swarms cost zero
model tokens). Runners self-report as subagents — the watcher is watched.

## Three writer surfaces, one file contract

| Surface | Use |
|---|---|
| CLI `progress.py` | agents + humans: `init · update · event · roster · proof · board · serve` |
| MCP `mcp_server.py` | any harness: `claude mcp add progresslive -- python3 ~/Creations/ProgressLive/mcp_server.py` |
| files | anything else may write `projects/<slug>/board.json` + `events.jsonl` (schema 1, atomic temp+rename) |

Contract details: `IA.md` + docstring in `progress.py`. Update = rewrite board.json;
append = event line — current + historical both always visible (the founding demand).

## Reproduce the tracker in any session

`/dev-progress` (alias `/dvp`) — spawns a resident subagent (explicit model, never Fable)
that registers the current project, seeds from verified state (git log timestamps become
real history), serves, opens, and keeps the board truthful. Skill: `~/.claude/skills/dev-progress/`.

## Design

Meter-bridge instrument, not SaaS dashboard: white bench + plotter-green ink (dark theme
real, OKLCH, system fonts, zero external requests, no build step). Full rationale:
`PRODUCT.md`; budgets + tests: `BUDGETS.md`; verified screenshots: `.deify/shots/`.

## The future arc (fire17's vision — designed-for, deliberately not built)

- **Fleet platform**: many projects, many harnesses — the fleet view already iterates
  `projects/*`; new project = new directory, zero code edits.
- **MCP-first**: v1 ships a working stdio MCP server; a hosted/multi-machine variant is
  additive (same tools, same file contract).
- **Any-harness push**: Codex/Zenith/nexus lanes write the same two files — schema 1 is
  the interface, not this repo's code.
- **Views**: per-project deep boards (done) → cross-project rollups, time-scrubbed
  history replay, per-agent lanes — all derivable from events.jsonl without migration.

Honest status: v1 live-verified locally (realtime 1043ms append→pixel, no reload;
304-poll 0 bytes; cold load <1ms served). Not published anywhere — leaves this machine
only on explicit go.
