---
name: dev-progress
description: Spawn a resident PROGRESS subagent that tracks the CURRENT project's development live on the ProgressLive site (~/Creations/ProgressLive) — registers the project, seeds its board from verified state (git log, task board), serves + opens the realtime page, then stays alive translating real changes (commits, task statuses, orchestrator messages) into board updates + append-only history events. Honest numbers only — the agent never invents progress. Use when the user types /dev-progress or /dvp, says "track progress live", "progress site for this project", "spin up the progress board", "I want to watch the dev progress", or a mission wants a live stakeholder-visible dev board.
argument-hint: "<project slug + one-line description (defaults to current repo)>"
---

# /dev-progress — reproduce the ProgressLive resident tracker for any project

This skill reproduces, for the session it runs in, the tracking cell first built for
AgentWorkAtlas on 2026-07-17. Platform lives at `~/Creations/ProgressLive` (own git repo).

## The founding vision (fire17, verbatim — preserved in ProgressLive/VISION.md, sha256 1665124a…)

> "make sure the agent can update what i see in realtime - so i know when i look at the
> site that i see everything (make sure it can both update or append update messages, so
> i can both see the current and historical progress of the development we are doing …
> generic and expandable so that it could be used either to see dev progress for other
> projects independently, or even a larger platform (that comes with skills and mcp) that
> would let any harness manage and project live work progress for any project, and also
> see all of the projects im working on"

## What exists already (do NOT rebuild — reuse)

| Piece | Path | Note |
|---|---|---|
| store + CLI + server | `~/Creations/ProgressLive/progress.py` | stdlib only |
| site (fleet + project views) | `~/Creations/ProgressLive/site/index.html` | no build step, polls `/api/state` w/ ETag every 1.5s |
| MCP server (any harness can push) | `~/Creations/ProgressLive/mcp_server.py` | `claude mcp add progresslive -- python3 ~/Creations/ProgressLive/mcp_server.py` |
| data contract | `projects/<slug>/board.json` + `events.jsonl` | schema 1, below |

## Data contract (schema 1)

- `board.json` — CURRENT state, atomic rewrite: `{schema, slug, name, tagline, meta{updated,started,repo,manager}, here, phases[{key,label,pct,status,eta,note,subitems[]?}], roster[{name,model,lane,state}], proof[{claim,cmd,result,ref,ts}], kpis[]?, links{local[],published[]}?, version{}?}`. `status ∈ done|now|queued|blocked|gated`. `here` = exactly one YOU-ARE-HERE phase key.
- **Subitems**: `phase.subitems[] = {key,label,pct,status,eta,note}` — nested tracking under a phase (site renders expand/collapse; phase pct auto-rolls-up from subitem mean). CLI: `progress update <slug> --phase HARD --sub UXE --pct 60 --status now`. MCP: `progress_update` w/ `sub` param.
- **links/kpis/version** (control strip): `progress setjson <slug> links|kpis|version '<json>'` — local links `{label,url,port,restart}` get server-side TCP probes + a board restart button (restart command executes ONLY from board.json, never from the request).
- `events.jsonl` — HISTORY, append-only, never rewritten: `{ts, kind: update|milestone|note|report, text, delta?}`.
- Both surfaces render: board = current, events = historical. Update = rewrite board; append = event line. Liveness badge derives from `meta.updated` age client-side — stale can never look fresh.

## CLI (the agent's hands)

```bash
cd ~/Creations/ProgressLive
python3 progress.py init <slug> --name "…" --tagline "…" --repo "…" --manager "…"
python3 progress.py update <slug> --phase API --pct 40 --status now --eta "1h" [--here] [--note "…"]
python3 progress.py event  <slug> "text" --kind milestone [--delta "commit abc123"]
python3 progress.py roster <slug> --set name:model:lane:state    # state 'gone' removes
python3 progress.py proof  <slug> --claim "…" --cmd "…" --result "…" --ref "…"
python3 progress.py board  <slug>          # ANSI print
python3 progress.py serve  --port 8177    # site + JSON API (check: lsof -ti:8177 — may already run)
```

## Procedure

1. If port 8177 already serves ProgressLive, reuse it; else start `serve` in background.
2. Spawn the resident tracker via the Agent tool — **EXPLICIT `model: "opus"`. NEVER Fable**
   (rule 4, ~/Creations/CLAUDE.md: Fable is the one-of-a-kind main-session orchestrator;
   spawns always carry an explicit non-Fable model). Prompt template below.
3. Confirm its first report line reads `MODEL: <id>` and the board renders at
   `http://localhost:8177/#/<slug>` — then hand fire17 the URL (`open` it).

## Spawn prompt template (fill <>)

```
You are the PROGRESS resident for <project>. FIRST line of every report: MODEL: <your model id>.
Mission: keep ~/Creations/ProgressLive/projects/<slug>/ truthful in realtime.
1. Seed: register <slug> (progress.py init) if absent; build phases/roster/proof ONLY from
   verified sources — git log of <repo> (real timestamps as milestone events), the shared
   TaskList, files on disk. Label every estimate "estimate". Never invent progress.
2. Reside: poll `git -C <repo> log --oneline` + TaskList every few minutes (Monitor tool or
   270s loop); translate REAL deltas into `progress.py update/event/roster/proof`.
3. Comms: the orchestrator SendMessages you milestone deltas — push to the board within
   seconds; SendMessage back when you need state.
   ASK-PARENT PATTERN (standing duty): at every phase transition, ASK your parent/lead
   (SendMessage) for the current phase's sub-structure — real subitems w/ pct/status each —
   and mirror them as phase.subitems (expand/collapse on the site). Ask; never invent
   decomposition. Refine subitems whenever the parent pushes deltas.
4. Honesty laws: numbers from evidence only; blocked-on-user phases marked blocked/gated;
   the site's live/stale badge must never lie (it derives from meta.updated — just write truth).
5. Escalation clause: if you are struggling or blocked >15min, SAY SO to your lead and stop
   — never fake movement on the board.
Data contract + CLI: read ~/.claude/skills/dev-progress/SKILL.md and ~/Creations/ProgressLive/README.md.
```

## Laws inherited by every spawn

- Honest numbers only — proof rows cite commands actually run + commit refs.
- Nothing leaves the machine (site is localhost; publishing needs explicit user go).
- Atomic writes (the CLI already does temp+rename; never hand-edit board.json mid-write).
- The user's verbatim words are sacred — VISION.md is never paraphrased.
