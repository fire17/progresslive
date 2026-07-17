---
name: progresslive
description: MAIN-AGENT spawner — one command that stands up live dev-progress tracking for the current project. Spawns a resident tracker subagent (tmux teammate, model from ~/Creations/ProgressLive/runner.config.json — default sonnet, NEVER Fable) that activates /progresslive-runner and does everything automagically — register + seed the board from verified state, serve + open the site (localhost:8177), maintain KPIs/channels/subitems, poll git + tasks, mirror your deltas, ask you for phase sub-structure. Use when the user types /progresslive or /plv, says "track this project live", "spin up progresslive", "progress board for this repo", or a build mission should be watchable in realtime.
argument-hint: "<project slug + one-line description (defaults to current repo)>"
---

# /progresslive — stand up live tracking for THIS project

You are the MAIN agent. Do not become the tracker — SPAWN it, then keep working.
(Disambiguation: /progresslive vs /dev-progress — near-identical triggers, ONE
implementation: /dev-progress is the legacy alias family and now defers here; when both
could match, THIS skill wins.)

## Procedure

1. **Config**: read `~/Creations/ProgressLive/runner.config.json` → `model` (default
   `sonnet`; NEVER fable — rule 4), `teammate_mode` (tmux), `port`. Changing the runner
   model/harness later = edit that file, nothing else.
2. **Slug**: from the argument, else current repo dir-name lowercased.
3. **Spawn** via the Agent tool: name `progresslive-<slug>`, EXPLICIT `model` from config,
   prompt below. 🔴 CHECKPOINT before spawning: config was READ (model value in hand, not
   assumed) AND slug is non-empty — a bad value here propagates into a live agent. Tmux
   attachability requires the session was launched with `--teammate-mode tmux`; if absent,
   spawn proceeds paneless — note the downgrade honestly, never fake a pane. (`--resume`
   silently drops the flag — relaunch fresh if panes matter.)
4. **Verify**: first report line must read `MODEL: <id>` (matching config, not Fable) and
   the board must render at `http://localhost:8177/#/<slug>`. Missing either → respawn
   once; still failing → STOP: SendMessage/report to the user naming exactly which
   verification failed and mark the tracking task blocked — never proceed on an
   unverified tracker.
5. **Feed it**: SendMessage it milestone deltas as you work; answer its ask-parent
   queries (phase sub-structure) with REAL decomposition. It pushes everything to the
   site within seconds.
6. **Scope-add law (fire17, 2026-07-17)**: ANYTHING added to the project after spawn —
   new tasks from the user, new lanes, new phases, scope changes, even during a gated/
   feeltest phase — MUST be pushed to the runner (SendMessage) the moment it lands, so
   the board never lags reality. The user checking the site must see every addition.
   This is a standing duty of the MAIN agent, not just the runner's polling.

## Spawn prompt template (fill <>)

```
Activate the Skill tool with skill "progresslive-runner" as your FIRST action — it is
your role. You are the PROGRESS resident for <slug> (<repo path>). <one-line description>
Parent agent: me — SendMessage me your MODEL line, your ask-parent queries, and
escalations. Serve/reuse localhost:<port>, seed from verified state only, open the board,
then reside per the runner skill's duties. First line of every report: MODEL: <your model id>.
```

## Laws

Explicit model on the spawn always; never Fable. Nothing published without the user's
explicit go. The runner's honesty laws are in /progresslive-runner — do not weaken them
in the spawn prompt.

## Swarm visibility (fire17 directive 2026-07-17 — VISION addendum, verbatim there)

When you (main agent) run a tmux swarm, the runner must see INSIDE it (numbering
continues the Procedure + scope-add law above):
7. **Tell the runner its swarm** on spawn + every roster change: tmux session name +
   socket (`claude-swarm-<pid>`), team name, and each subagent's name/model/lane/pane as
   you spawn them (SendMessage). The runner cannot monitor what it cannot name.
8. **Give every spawned subagent the status-drop duty** (2 prompt lines, near-zero
   tokens): "On every state change append one JSON line
   {ts,state,pct,current,note} (state ∈ working|parked|waiting|blocked|done|finished)
   to ~/.progresslive/swarm/<slug>/<your-name>.jsonl". Direct file drops — no relay
   through you, no message round-trips; SendMessage stays for escalations only.
9. Runner observes the rest machine-side at ZERO model tokens (`progress.py swarm-scan`:
   drops + tmux list-panes + pane liveness) and renders per-agent status glyphs +
   progress bars + arbitrarily-nested subitems (`--sub A.B.C…`). Token economics: you
   push milestones; drops carry state; the model only writes when something CHANGED.
