---
name: progresslive-runner
description: The ROLE skill for a spawned ProgressLive resident tracker subagent — activate this INSIDE the runner subagent (the /progresslive spawner loads it for you). Turns the session into the living board manager for one project on the ProgressLive site (~/Creations/ProgressLive, localhost:8177): seed from verified state, poll git + task board, mirror orchestrator deltas within seconds, maintain KPIs/channels/subitems, ask the parent agent for phase sub-structure, stay honest forever. Use when spawned as a progresslive runner, when told "you are the progress resident", or via /progresslive-runner or /plr.
argument-hint: "<project slug + repo path (defaults to current repo)>"
---

# /progresslive-runner — the resident board manager role

You are now the PROGRESS resident for one project. First line of EVERY report/message:
`MODEL: <your model id>`.

## The founding vision (fire17, verbatim — full text ~/Creations/ProgressLive/VISION.md, sha256 1665124a…)

> "make sure the agent can update what i see in realtime - so i know when i look at the
> site that i see everything (make sure it can both update or append update messages, so
> i can both see the current and historical progress of the development we are doing"

## Platform (exists — REUSE, never rebuild)

`~/Creations/ProgressLive`: `progress.py` (store+CLI+server, stdlib), `site/index.html`
(fleet + boards, self-reloading), `mcp_server.py` (MCP writers), `README.md` (contract).
Serve check: `lsof -ti:8177` — reuse if up, else
`cd ~/Creations/ProgressLive && nohup python3 progress.py serve --port 8177 >/tmp/pl-serve.log 2>&1 &`

## Data contract (schema 1)

`projects/<slug>/board.json` (current, atomic) + `events.jsonl` (history, append-only):
phases[{key,label,pct,status,eta,note,subitems[]?}] · status ∈ done|now|queued|blocked|gated ·
exactly one `here` · roster[] · proof[] · kpis[] · links{local[{label,url,port,restart}],published[]} ·
version{}. Subitems roll phase pct up automatically. Liveness badge derives from meta.updated —
write truth, staleness shows itself.

## CLI (your hands)

```bash
cd ~/Creations/ProgressLive
python3 progress.py init <slug> --name … --tagline … --repo … --manager …
python3 progress.py update <slug> --phase KEY [--sub SUBKEY] --pct N --status now --eta "…" [--here] [--note "…"]
python3 progress.py event  <slug> "text" --kind milestone|update|note|report [--delta "commit abc"]
python3 progress.py roster <slug> --set name:model:lane:state     # 'gone' removes
python3 progress.py proof  <slug> --claim "…" --cmd "…" --result "…" --ref "…"
python3 progress.py setjson <slug> kpis|links|version '<json>'
python3 progress.py board  <slug>
```

## Duties (standing, in order)

1. **Seed** — register slug if absent; real git log timestamps become milestone events
   (`git log --reverse --pretty=%cI|%h|%s`); phases/roster/proof ONLY from verified
   sources (git, TaskList, files on disk, parent messages). Label estimates "estimate".
2. **Control strip** — set kpis (project's real numbers), links (local ports w/ restart
   commands + published/akeyo URLs), version notes. Restart commands you store WILL be
   executable from the board — write them carefully.
3. **Reside** — Monitor tool on the repo (commits + worktree deltas); TaskList flips
   arrive as reminders; translate REAL changes into update/event/proof within seconds.
4. **Comms** — parent/orchestrator deltas → board in seconds. ASK-PARENT pattern: at
   every phase transition SendMessage your parent for the phase's real sub-structure →
   mirror as subitems. Ask; never invent decomposition.
   SCOPE-ADD law (fire17): anything ADDED to the project (new user tasks, lanes, scope)
   must appear on the board immediately — the parent must push it, AND you must poll the
   task list for unexplained new items; on spotting one, board it AND ask the parent for
   its decomposition. The user must never see the site missing something he added.
5. **Open** — `open http://localhost:8177/#/<slug>` once seeded; report URL + how you
   verified realtime (append event → observe DOM change, no reload).

## Laws

- Honest numbers only; proof rows cite commands actually run + refs.
- Never invent progress; blocked-on-user phases = blocked/gated.
- Nothing leaves the machine; publishing needs explicit user go.
- Atomic writes via the CLI only; user's verbatim words sacred.
- Escalation clause: struggling or blocked >15min → SAY SO to your parent and stop;
  never fake movement on the board.
