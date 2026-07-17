#!/usr/bin/env python3
"""ProgressLive MCP server (stdio, JSON-RPC 2.0, stdlib only — no SDK dep).

Lets ANY MCP-capable harness push live dev progress into ProgressLive:
same file contract as the CLI (projects/<slug>/board.json + events.jsonl),
so CLI, MCP, and future push surfaces are interchangeable writers.

Register (Claude Code): claude mcp add progresslive -- python3 ~/Creations/ProgressLive/mcp_server.py
ponytail: happy-path JSON-RPC subset (initialize/tools) — full spec only if a harness demands it.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import progress as P

TOOLS = [
    {"name": "progress_init", "description": "Register a project board",
     "inputSchema": {"type": "object", "properties": {
         "slug": {"type": "string"}, "name": {"type": "string"}, "tagline": {"type": "string"},
         "repo": {"type": "string"}, "manager": {"type": "string"}}, "required": ["slug"]}},
    {"name": "progress_update", "description": "Update a phase (creates if missing); auto-appends a history event. status: done|now|queued|blocked|gated. Pass 'sub' to target a nested subitem (phase pct auto-rolls-up from subitem mean)",
     "inputSchema": {"type": "object", "properties": {
         "slug": {"type": "string"}, "phase": {"type": "string"}, "sub": {"type": "string"},
         "label": {"type": "string"},
         "pct": {"type": "integer"}, "status": {"type": "string"}, "eta": {"type": "string"},
         "note": {"type": "string"}, "here": {"type": "boolean"}}, "required": ["slug", "phase"]}},
    {"name": "progress_event", "description": "Append a history event (kind: update|milestone|note|report)",
     "inputSchema": {"type": "object", "properties": {
         "slug": {"type": "string"}, "text": {"type": "string"}, "kind": {"type": "string"},
         "delta": {"type": "string"}}, "required": ["slug", "text"]}},
    {"name": "progress_roster", "description": "Upsert an agent on the roster (state 'gone' removes)",
     "inputSchema": {"type": "object", "properties": {
         "slug": {"type": "string"}, "name": {"type": "string"}, "model": {"type": "string"},
         "lane": {"type": "string"}, "state": {"type": "string"}}, "required": ["slug", "name"]}},
    {"name": "progress_proof", "description": "Record a verified claim (what was actually run)",
     "inputSchema": {"type": "object", "properties": {
         "slug": {"type": "string"}, "claim": {"type": "string"}, "cmd": {"type": "string"},
         "result": {"type": "string"}, "ref": {"type": "string"}}, "required": ["slug", "claim"]}},
    {"name": "progress_board", "description": "Read a project board (or all boards when slug omitted)",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}}},
    {"name": "pl_detect", "description": "AUTO-TRACK step 1: detect the working project (cwd git root → slug), whether it is registered in ProgressLive, and whether the site server is up",
     "inputSchema": {"type": "object", "properties": {"cwd": {"type": "string", "description": "session cwd (defaults to server cwd)"}}}},
    {"name": "pl_ensure", "description": "AUTO-TRACK step 2: idempotently register the detected project (board skeleton + real git history as events) and ensure the site server is serving",
     "inputSchema": {"type": "object", "properties": {"cwd": {"type": "string"}, "slug": {"type": "string"}, "name": {"type": "string"}, "tagline": {"type": "string"}}}},
    {"name": "pl_runner_brief", "description": "AUTO-TRACK step 3: returns the spawn config (model — default sonnet, NEVER fable — tmux mode, port) + the exact Agent-tool prompt to spawn the resident /progresslive-runner subagent for this project",
     "inputSchema": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
]

INSTRUCTIONS = """ProgressLive auto-tracking is ACTIVE. When this session is working inside a
project (any git repo, existing or new) and substantive build/dev work begins: call pl_detect,
then pl_ensure, then pl_runner_brief, and spawn the resident tracker subagent via the Agent
tool exactly per the brief (explicit model from the brief — NEVER Fable; tmux teammate mode when
available). One runner per project per session — if pl_detect says a runner already resides or
the board is actively managed (updated <10 min ago), do NOT spawn a duplicate. Skip for trivial
Q&A sessions. The user (fire17) opted into this by activating this MCP server globally."""


def call(name, a):
    slug = a.get("slug")
    if name == "progress_init":
        if P.board_path(slug).exists():
            return f"'{slug}' already exists"
        b = {"schema": 1, "slug": slug, "name": a.get("name", slug), "tagline": a.get("tagline", ""),
             "meta": {"updated": P.now_iso(), "started": P.now_iso(),
                      "repo": a.get("repo", ""), "manager": a.get("manager", "mcp")},
             "here": None, "phases": [], "roster": [], "proof": []}
        P.atomic_write(P.board_path(slug), json.dumps(b, indent=1) + "\n")
        P.events_path(slug).touch()
        P.append_event(slug, "milestone", f"project '{slug}' registered via MCP")
        return f"registered {slug}"
    if name == "progress_update":
        b = P.load_board(slug)
        ph = next((p for p in b["phases"] if p["key"] == a["phase"]), None)
        if ph is None:
            ph = {"key": a["phase"], "label": a.get("label", a["phase"]), "pct": 0,
                  "status": "queued", "eta": None, "note": ""}
            b["phases"].append(ph)
        if a.get("sub"):
            subs = ph.setdefault("subitems", [])
            t = next((s for s in subs if s["key"] == a["sub"]), None)
            if t is None:
                t = {"key": a["sub"], "label": a.get("label", a["sub"]), "pct": 0,
                     "status": "queued", "eta": None, "note": ""}
                subs.append(t)
        else:
            t, subs = ph, None
        old = dict(t)
        for k in ("label", "note"):
            if k in a: t[k] = a[k]
        if "pct" in a: t["pct"] = max(0, min(100, a["pct"]))
        if "status" in a:
            if a["status"] not in P.STATUSES: return f"bad status; use {P.STATUSES}"
            t["status"] = a["status"]
            if a["status"] == "done" and "pct" not in a: t["pct"] = 100
        if "eta" in a: t["eta"] = a["eta"] or None
        if subs:
            ph["pct"] = round(sum(s["pct"] for s in subs) / len(subs))
        if a.get("here"): b["here"] = a["phase"]
        P.save_board(slug, b)
        name_str = f"{ph['key']} ▸ {t['key']}" if subs else ph["key"]
        delta = ", ".join(f"{k} {old[k]}→{t[k]}" for k in ("pct", "status", "eta")
                          if old.get(k) != t.get(k)) or None
        P.append_event(slug, "update",
                       f"{name_str} · {t['label']}: {t['pct']}% {t['status']}"
                       + (f" · eta {t['eta']}" if t.get("eta") else ""), delta=delta)
        return f"{slug}/{name_str}: {t['pct']}% {t['status']}"
    if name == "progress_event":
        ev = P.append_event(slug, a.get("kind", "note"), a["text"], delta=a.get("delta"))
        P.save_board(slug, P.load_board(slug))
        return f"appended {ev['kind']} @ {ev['ts']}"
    if name == "progress_roster":
        b = P.load_board(slug)
        b["roster"] = [r for r in b["roster"] if r["name"] != a["name"]]
        if a.get("state") != "gone":
            b["roster"].append({"name": a["name"], "model": a.get("model", ""),
                                "lane": a.get("lane", ""), "state": a.get("state", "building")})
        P.save_board(slug, b)
        return "roster: " + ", ".join(f"{r['name']}({r['state']})" for r in b["roster"])
    if name == "progress_proof":
        b = P.load_board(slug)
        b["proof"].append({"claim": a["claim"], "cmd": a.get("cmd", ""), "result": a.get("result", ""),
                           "ref": a.get("ref", ""), "ts": P.now_iso()})
        P.save_board(slug, b)
        return f"proof recorded: {a['claim']}"
    if name == "pl_detect":
        import subprocess, os
        cwd = a.get("cwd") or os.getcwd()
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True)
        root = r.stdout.strip() if r.returncode == 0 else None
        slug = Path(root).name.lower().replace(" ", "-") if root else None
        registered = bool(slug and P.board_path(slug).exists())
        fresh = False
        if registered:
            from datetime import datetime, timezone
            b = P.load_board(slug)
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(b["meta"]["updated"])).total_seconds()
                fresh = age < 600
            except (KeyError, ValueError):
                pass
        import socket
        cfg = json.loads((Path(__file__).parent / "runner.config.json").read_text())
        try:
            with socket.create_connection(("127.0.0.1", cfg.get("port", 8177)), timeout=0.25):
                server_up = True
        except OSError:
            server_up = False
        return json.dumps({"cwd": cwd, "git_root": root, "slug": slug, "registered": registered,
                           "actively_managed": fresh, "server_up": server_up,
                           "verdict": "skip — no git project" if not root else
                                      "skip — board actively managed (runner likely resides)" if fresh else
                                      "proceed: pl_ensure then pl_runner_brief then spawn"})
    if name == "pl_ensure":
        import subprocess, os
        cwd = a.get("cwd") or os.getcwd()
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True)
        root = r.stdout.strip() if r.returncode == 0 else cwd
        slug = a.get("slug") or Path(root).name.lower().replace(" ", "-")
        made = []
        if not P.board_path(slug).exists():
            call("progress_init", {"slug": slug, "name": a.get("name", Path(root).name),
                                   "tagline": a.get("tagline", ""), "repo": root, "manager": "progresslive runner (auto)"})
            log = subprocess.run(["git", "-C", root, "log", "--reverse", "--pretty=%cI|%h|%s"],
                                 capture_output=True, text=True).stdout.strip().splitlines()
            for line in log[-200:]:
                ts, h, msg = line.split("|", 2)
                P.append_event(slug, "milestone", msg, delta=f"commit {h}", ts=ts)
            made.append(f"registered {slug} + {min(len(log),200)} git-history events")
        cfg = json.loads((Path(__file__).parent / "runner.config.json").read_text())
        import socket
        try:
            with socket.create_connection(("127.0.0.1", cfg.get("port", 8177)), timeout=0.25):
                pass
        except OSError:
            import subprocess as sp
            sp.Popen(["/bin/sh", "-c",
                      f"cd {Path(__file__).parent} && nohup python3 progress.py serve --port {cfg.get('port', 8177)} >/tmp/pl-serve.log 2>&1 &"],
                     start_new_session=True)
            made.append("server started")
        return json.dumps({"slug": slug, "done": made or ["already registered + serving"],
                           "board_url": f"http://localhost:{cfg.get('port', 8177)}/#/{slug}"})
    if name == "pl_runner_brief":
        cfg = json.loads((Path(__file__).parent / "runner.config.json").read_text())
        prompt = (f'Activate the Skill tool with skill "progresslive-runner" as your FIRST action — it is your role. '
                  f'You are the PROGRESS resident for {a["slug"]}. Parent agent: the session that spawned you — '
                  f'SendMessage it your MODEL line, ask-parent queries, and escalations. Serve/reuse '
                  f'localhost:{cfg.get("port", 8177)}, seed from verified state only, open the board, then reside. '
                  f'Swarm visibility: ask the parent for the tmux session/socket/team + subagent roster, then cron '
                  f'`python3 progress.py swarm-scan {a["slug"]} --session <s> --quiet` (60-120s, zero-token; --quiet '
                  f'= no output on no-change ticks, so idle swarms never wake you); subagents report via status-drop '
                  f'files; SELF-REPORT META LAW: register your own roster row w/ --items duty tree + drop on every '
                  f'transition (the ACTIVE/IDLE chip derives from drop recency machine-side). '
                  f'First line of every report: MODEL: <your model id>.')
        return json.dumps({"spawn": {"tool": "Agent", "name": f"progresslive-{a['slug']}",
                                     "model": cfg.get("model", "sonnet"), "never": "fable",
                                     "teammate_mode": cfg.get("teammate_mode", "tmux"),
                                     "prompt": prompt},
                           "config_file": str(Path(__file__).parent / "runner.config.json")})
    if name == "progress_board":
        if slug:
            return json.dumps(P.load_board(slug), indent=1)
        state, _ = P.assemble_state(tail=5)
        return json.dumps({s: v["board"] for s, v in state["projects"].items()}, indent=1)
    return f"unknown tool {name}"


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid, method = req.get("id"), req.get("method", "")
        if method == "initialize":
            res = {"protocolVersion": req["params"].get("protocolVersion", "2024-11-05"),
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": "progresslive", "version": "1.1.0"},
                   "instructions": INSTRUCTIONS}
        elif method == "tools/list":
            res = {"tools": TOOLS}
        elif method == "tools/call":
            try:
                out = call(req["params"]["name"], req["params"].get("arguments", {}))
                res = {"content": [{"type": "text", "text": str(out)}]}
            except SystemExit as e:  # load_board exits on missing project
                res = {"content": [{"type": "text", "text": str(e)}], "isError": True}
            except Exception as e:
                res = {"content": [{"type": "text", "text": f"error: {e}"}], "isError": True}
        elif method == "ping":
            res = {}
        elif rid is None:  # notification (e.g. notifications/initialized)
            continue
        else:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid,
                                         "error": {"code": -32601, "message": f"unknown method {method}"}}) + "\n")
            sys.stdout.flush()
            continue
        if rid is not None:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": res}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
