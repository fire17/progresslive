---
name: dev-progress
description: Spawn a resident PROGRESS subagent that tracks the CURRENT project's development live on the ProgressLive site (~/Creations/ProgressLive) — registers the project, seeds its board from verified state (git log, task board), serves + opens the realtime page, then stays alive translating real changes (commits, task statuses, orchestrator messages) into board updates + append-only history events. Honest numbers only — the agent never invents progress. Use when the user types /dev-progress or /dvp, says "track progress live", "progress site for this project", "spin up the progress board", "I want to watch the dev progress", or a mission wants a live stakeholder-visible dev board.
argument-hint: "<project slug + one-line description (defaults to current repo)>"
---

# /dev-progress — reproduce the ProgressLive resident tracker for any project

This skill reproduces, for the session it runs in, the tracking cell first built for
AgentWorkAtlas on 2026-07-17. Platform lives at `~/Creations/ProgressLive` (own git repo).

> **Disambiguation (2026-07-17):** this is the LEGACY member of the family — `/progresslive`
> (spawner) + `/progresslive-runner` (role) are the canonical pair; when both could match a
> request, `/progresslive` wins. This skill now delegates to them (below) so capabilities
> never diverge.

## The founding vision (fire17, verbatim — preserved in ProgressLive/VISION.md; founding-BLOCK sha256 1665124a… — the block between the first two `---` separators; the whole-file hash drifts as verbatim addenda append)

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

## Procedure (delegates to the canonical pair — capabilities never diverge)

1. If port 8177 already serves ProgressLive, reuse it; else start `serve` in background.
2. Read the spawn model from `~/Creations/ProgressLive/runner.config.json` (`model` key —
   the ONE source of truth for the whole family; default sonnet). **NEVER Fable** (rule 4,
   ~/Creations/CLAUDE.md). 🔴 CHECKPOINT: config read + slug non-empty before spawning.
3. Spawn via the Agent tool with the prompt template below — it activates
   `/progresslive-runner`, which carries ALL duties (seed/strip/reside/comms/ask-parent/
   scope-add/swarm-visibility/honesty/escalation). Do not re-embed duties here.
4. Confirm first report line `MODEL: <id>` (matches config) and the board renders at
   `http://localhost:8177/#/<slug>` — then hand fire17 the URL (`open` it). Either check
   failing → respawn once; still failing → STOP and report which verification failed.

## Spawn prompt template (fill <>)

```
Activate the Skill tool with skill "progresslive-runner" as your FIRST action — it is
your role and carries all duties. You are the PROGRESS resident for <slug> (<repo>).
Parent agent: me — SendMessage me your MODEL line, ask-parent queries, and escalations.
Serve/reuse localhost:8177, seed from verified state only, open the board, then reside.
First line of every report: MODEL: <your model id>.
```

## Laws inherited by every spawn

- Honest numbers only — proof rows cite commands actually run + commit refs.
- Nothing leaves the machine (site is localhost; publishing needs explicit user go).
- Atomic writes (the CLI already does temp+rename; never hand-edit board.json mid-write).
- The user's verbatim words are sacred — VISION.md is never paraphrased.
