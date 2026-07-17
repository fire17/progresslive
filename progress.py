#!/usr/bin/env python3
"""progress — file-based realtime dev-progress store + CLI + server.

Data contract (schema 1, additive-by-design):
  projects/<slug>/board.json    current state  (atomic rewrite)
  projects/<slug>/events.jsonl  history        (append-only, never rewritten)

board.json:
  { schema, slug, name, tagline,
    meta:   { updated, started, repo, manager },
    here:   "<phase key>"            # exactly one YOU ARE HERE
    phases: [ {key,label,pct,status,eta,note} ],   # status: done|now|queued|blocked|gated
    roster: [ {name,model,lane,state} ],
    proof:  [ {claim,cmd,result,ref,ts} ] }

events.jsonl line: { ts, kind, text, delta? }     # kind: update|milestone|note|report

Any harness (CLI, MCP, future push API) writing these shapes is a first-class
citizen — that is the whole expansion contract. stdlib only, no deps.
"""
import argparse, hashlib, json, os, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / "projects"
SITE = ROOT / "site"
STATUSES = ("done", "now", "queued", "blocked", "gated")
KINDS = ("update", "milestone", "note", "report")


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def board_path(slug):
    return PROJECTS / slug / "board.json"


def events_path(slug):
    return PROJECTS / slug / "events.jsonl"


def load_board(slug):
    p = board_path(slug)
    if not p.exists():
        sys.exit(f"no project '{slug}' — run: progress init {slug} --name ...")
    return json.loads(p.read_text())


def save_board(slug, board):
    board["meta"]["updated"] = now_iso()
    atomic_write(board_path(slug), json.dumps(board, indent=1, ensure_ascii=False) + "\n")


def append_event(slug, kind, text, delta=None, ts=None):
    if kind not in KINDS:
        sys.exit(f"kind must be one of {KINDS}")
    ev = {"ts": ts or now_iso(), "kind": kind, "text": text}
    if delta:
        ev["delta"] = delta
    line = json.dumps(ev, ensure_ascii=False) + "\n"
    with open(events_path(slug), "a") as f:  # append-only; O_APPEND is atomic per line
        f.write(line)
    return ev


# ---------------- commands ----------------

def cmd_init(a):
    p = board_path(a.slug)
    if p.exists():
        sys.exit(f"'{a.slug}' already exists")
    board = {
        "schema": 1, "slug": a.slug, "name": a.name or a.slug, "tagline": a.tagline or "",
        "meta": {"updated": now_iso(), "started": now_iso(), "repo": a.repo or "", "manager": a.manager or ""},
        "here": None, "phases": [], "roster": [], "proof": [],
    }
    atomic_write(p, json.dumps(board, indent=1, ensure_ascii=False) + "\n")
    events_path(a.slug).touch()
    append_event(a.slug, "milestone", f"project '{a.slug}' registered in ProgressLive")
    print(f"registered {a.slug}")


def _apply_fields(t, a):
    """Apply update-args onto a phase or subitem dict; returns (old, changed-name)."""
    old = dict(t)
    if a.label is not None:
        t["label"] = a.label
    if a.pct is not None:
        t["pct"] = max(0, min(100, a.pct))
    if a.status is not None:
        if a.status not in STATUSES:
            sys.exit(f"status must be one of {STATUSES}")
        t["status"] = a.status
        if a.status == "done" and a.pct is None:
            t["pct"] = 100
    if a.eta is not None:
        t["eta"] = a.eta or None
    if a.note is not None:
        t["note"] = a.note
    return old


def cmd_update(a):
    b = load_board(a.slug)
    ph = next((p for p in b["phases"] if p["key"] == a.phase), None)
    if ph is None:
        ph = {"key": a.phase, "label": a.label or a.phase, "pct": 0, "status": "queued", "eta": None, "note": "", "born": now_iso()}
        b["phases"].append(ph)
    if getattr(a, "sub", None):
        # dotted path = arbitrary nesting: --sub UXE.E2E.SMOKE creates/updates down the tree
        node, path = ph, []
        for part in a.sub.split("."):
            subs = node.setdefault("subitems", [])
            nxt = next((s for s in subs if s["key"] == part), None)
            if nxt is None:
                nxt = {"key": part, "label": (a.label or part) if part == a.sub.split(".")[-1] else part,
                       "pct": 0, "status": "queued", "eta": None, "note": "", "born": now_iso()}
                subs.append(nxt)
            node, _ = nxt, path.append(part)
        t = node
        old = _apply_fields(t, a)

        def rollup(n):  # honest recursive rollup: parent pct = mean of children
            for s in n.get("subitems", []):
                rollup(s)
            if n.get("subitems"):
                n["pct"] = round(sum(s["pct"] for s in n["subitems"]) / len(n["subitems"]))
        rollup(ph)
        name = f"{ph['key']} ▸ {' ▸ '.join(path)}"
    else:
        t = ph
        old = _apply_fields(t, a)
        name = ph["key"]
    if a.here:
        b["here"] = a.phase
    save_board(a.slug, b)
    bits = [f"{k} {old[k]}→{t[k]}" for k in ("pct", "status", "eta") if old.get(k) != t.get(k)]
    delta = ", ".join(bits) or None
    append_event(a.slug, "update", a.event or f"{name} · {t['label']}: {t['pct']}% {t['status']}"
                 + (f" · eta {t['eta']}" if t.get("eta") else ""), delta=delta)
    print(f"{a.slug}/{name}: pct={t['pct']} status={t['status']} eta={t['eta']}"
          + (f" | phase rollup {ph['pct']}%" if getattr(a, "sub", None) else ""))


def cmd_here(a):
    b = load_board(a.slug)
    if not any(p["key"] == a.phase for p in b["phases"]):
        sys.exit(f"no phase '{a.phase}' in {a.slug}")
    b["here"] = a.phase
    save_board(a.slug, b)
    print(f"{a.slug}: YOU ARE HERE → {a.phase}")


def cmd_event(a):
    ev = append_event(a.slug, a.kind, a.text, delta=a.delta)
    # bump meta.updated so liveness reflects the append too
    save_board(a.slug, load_board(a.slug))
    print(f"appended {ev['kind']} @ {ev['ts']}")


AGENT_STATES = ("working", "building", "parked", "waiting", "blocked", "done", "finished", "gone")

def cmd_roster(a):
    b = load_board(a.slug)
    if a.clear:
        b["roster"] = []
    for spec in a.set or []:
        parts = (spec.split(":") + ["", "", ""])[:4]
        name, model, lane, state = parts
        b["roster"] = [r for r in b["roster"] if r["name"] != name]
        if state != "gone":
            b["roster"].append({"name": name, "model": model, "lane": lane, "state": state or "building"})
    if getattr(a, "agent", None):
        # rich single-agent upsert: swarm-visibility fields (state/pct/current/pane)
        r = next((r for r in b["roster"] if r["name"] == a.agent), None)
        if a.state == "gone" and r:
            b["roster"].remove(r)
        else:
            if r is None:
                r = {"name": a.agent, "model": "", "lane": "", "state": "working"}
                b["roster"].append(r)
            for k in ("model", "lane", "state", "current", "pane"):
                v = getattr(a, k, None)
                if v is not None:
                    r[k] = v
            if a.pct is not None:
                r["pct"] = max(0, min(100, a.pct))
            if getattr(a, "items", None):
                r["items"] = json.loads(a.items)  # per-agent work tree: [{key,label,pct,status,note,subitems?...}]
            r["since"] = now_iso()
            r["seen"] = now_iso()
    save_board(a.slug, b)
    print(f"{a.slug} roster: " + ", ".join(f"{r['name']}({r['state']}{'' if r.get('pct') is None else ' ' + str(r['pct']) + '%'})" for r in b["roster"]))


def cmd_ingest(a):
    """Apply a STATUS-REPLY (SIP JSON) mechanically — the runner never interprets prose.
    Shape: {phases:[{key,label?,pct?,status?,eta?,note?,subitems:[…recursive]}],
            roster:[{name,model?,lane?,state?,pct?,current?,pane?,items?}],
            events:[{kind,text,delta?}], proof:[{claim,cmd?,result?,ref?}]}"""
    payload = json.loads(Path(a.file).read_text() if a.file else a.json)
    b = load_board(a.slug)

    def upsert_tree(parent_list, spec):
        node = next((s for s in parent_list if s["key"] == spec["key"]), None)
        if node is None:
            node = {"key": spec["key"], "label": spec.get("label", spec["key"]),
                    "pct": 0, "status": "queued", "eta": None, "note": "", "born": now_iso()}
            parent_list.append(node)
        for k in ("label", "pct", "status", "eta", "note"):
            if k in spec:
                node[k] = spec[k] if k != "pct" else max(0, min(100, spec[k]))
        for child in spec.get("subitems", []):
            upsert_tree(node.setdefault("subitems", []), child)
        if node.get("subitems"):
            node["pct"] = round(sum(s["pct"] for s in node["subitems"]) / len(node["subitems"]))

    n = {"phases": 0, "roster": 0, "events": 0, "proof": 0}
    for spec in payload.get("phases", []):
        upsert_tree(b["phases"], spec)
        n["phases"] += 1
    if payload.get("here"):
        b["here"] = payload["here"]
    for spec in payload.get("roster", []):
        r = next((r for r in b["roster"] if r["name"] == spec["name"]), None)
        if r is None:
            r = {"name": spec["name"], "model": "", "lane": "", "state": "working"}
            b["roster"].append(r)
        for k in ("model", "lane", "state", "pct", "current", "pane", "items"):
            if k in spec:
                r[k] = spec[k]
        r["since"] = now_iso()
        n["roster"] += 1
    for spec in payload.get("proof", []):
        b["proof"].append({"claim": spec["claim"], "cmd": spec.get("cmd", ""),
                           "result": spec.get("result", ""), "ref": spec.get("ref", ""), "ts": now_iso()})
        n["proof"] += 1
    save_board(a.slug, b)
    for spec in payload.get("events", []):
        append_event(a.slug, spec.get("kind", "update"), spec["text"], delta=spec.get("delta"))
        n["events"] += 1
    print(f"ingested {a.slug}: phases={n['phases']} roster={n['roster']} events={n['events']} proof={n['proof']}")


def cmd_swarm_scan(a):
    """ZERO-LLM-token swarm observation: tmux panes + status-drop files + cship snapshots
    → machine-derived roster states. Runner cron-runs this; no model in the loop."""
    import subprocess, glob
    b = load_board(a.slug)
    seen = {}
    # 1. status drops (subagents append one JSON line per state change)
    drops = Path.home() / ".progresslive" / "swarm" / a.slug
    for f in sorted(drops.glob("*.jsonl")) if drops.exists() else []:
        try:
            last = json.loads(f.read_text().splitlines()[-1])
            seen[f.stem] = {"state": last.get("state", "working"), "pct": last.get("pct"),
                            "current": last.get("current"), "src": "drop", "ts": last.get("ts"),
                            "seen": last.get("ts")}  # drop recency drives the ACTIVE/idle chip (machine-derived)
        except (IndexError, json.JSONDecodeError):
            pass
    # 2. tmux panes (if a session was declared)
    if a.session:
        r = subprocess.run(["tmux", "-L", a.socket, "list-panes", "-s", "-t", a.session,
                            "-F", "#{pane_id}|#{pane_title}|#{pane_dead}|#{pane_current_command}"]
                           if a.socket else
                           ["tmux", "list-panes", "-s", "-t", a.session,
                            "-F", "#{pane_id}|#{pane_title}|#{pane_dead}|#{pane_current_command}"],
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            pane, title, dead, cmd = (line.split("|") + ["", "", ""])[:4]
            agent = next((x["name"] for x in b["roster"] if x["name"] in title), None)
            if agent:
                s = seen.setdefault(agent, {})
                s["pane"] = pane
                if dead == "1":
                    s.setdefault("state", "finished")
    changed = []
    seen_changed = False
    for name, s in seen.items():
        r = next((r for r in b["roster"] if r["name"] == name), None)
        if r is None:
            r = {"name": name, "model": "", "lane": "", "state": "working"}
            b["roster"].append(r)
        if s.get("seen") and r.get("seen") != s["seen"]:
            r["seen"] = s["seen"]  # freshness updates silently — never an event, never a wake
            seen_changed = True
        delta = {k: v for k, v in s.items() if k in ("state", "pct", "current", "pane") and v is not None and r.get(k) != v}
        if delta:
            r.update(delta)
            r["since"] = now_iso()
            changed.append(f"{name}:{delta}")
    if changed or seen_changed:
        save_board(a.slug, b)
    if changed:
        append_event(a.slug, "update", "swarm scan: " + "; ".join(changed)[:300], delta="machine-derived")
    if changed or not a.quiet:
        # --quiet: total silence when nothing changed — inside a Monitor, a printed line
        # wakes the supervising agent (a model turn); idle swarms must cost ZERO tokens.
        print(f"swarm-scan {a.slug}: {len(seen)} observed, {len(changed)} changed"
              + (f" ({'; '.join(changed)[:200]})" if changed else ""))


def cmd_proof(a):
    b = load_board(a.slug)
    b["proof"].append({"claim": a.claim, "cmd": a.cmd or "", "result": a.result or "",
                       "ref": a.ref or "", "ts": now_iso()})
    save_board(a.slug, b)
    print(f"proof recorded: {a.claim}")


def cmd_board(a):
    b = load_board(a.slug)
    G, C, Y, D, R = "\033[32m", "\033[36m", "\033[33m", "\033[2m", "\033[0m"
    print(f"\n {b['name']}  {D}{b['tagline']}{R}\n {D}updated {b['meta']['updated']}{R}\n")
    for p in b["phases"]:
        full = round(p["pct"] / 5)
        bar = "█" * full + "░" * (20 - full)
        col = {"done": G, "now": C, "blocked": R + "\033[31m", "gated": Y}.get(p["status"], D)
        mark = f"  {G}◀ YOU ARE HERE{R}" if b.get("here") == p["key"] else ""
        eta = f" eta {p['eta']}" if p.get("eta") else ""
        print(f" {p['key']:>7} {col}{bar}{R} {p['pct']:>3}% {col}{p['status']:<7}{R}{eta}{mark}")
    if b["roster"]:
        print("\n agents: " + ", ".join(f"{r['name']}[{r['model']}:{r['state']}]" for r in b["roster"]))
    print()


# ---------------- state assembly + server ----------------

def state_sig():
    """Cheap change signature: stats only, zero parsing. Feeds the 304 fast path."""
    sig = []
    if PROJECTS.exists():
        for f in sorted(PROJECTS.glob("*/*")):
            if f.is_file():
                st = f.stat()
                sig.append(f"{f.parent.name}/{f.name}:{st.st_mtime_ns}:{st.st_size}")
    site_v = str((SITE / "index.html").stat().st_mtime_ns)
    return hashlib.sha1("|".join(sig).encode()).hexdigest()[:16] + "-" + site_v[-6:], site_v


def assemble_state(tail=200):
    etag, site_v = state_sig()
    projects = {}
    if PROJECTS.exists():
        for d in sorted(PROJECTS.iterdir()):
            bp, ep = d / "board.json", d / "events.jsonl"
            if not bp.exists():
                continue
            try:
                board = json.loads(bp.read_text())
            except json.JSONDecodeError:
                continue  # mid-write race; next poll gets it (writes are atomic)
            events = []
            if ep.exists():
                for line in ep.read_text().splitlines()[-tail:]:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            projects[d.name] = {"board": board, "events": events}
    return {"projects": projects, "server_ts": now_iso(), "site_v": site_v}, etag


def cmd_setjson(a):
    if a.field not in ("kpis", "links", "version"):
        sys.exit("field must be kpis|links|version")
    b = load_board(a.slug)
    b[a.field] = json.loads(a.json)
    save_board(a.slug, b)
    print(f"{a.slug}.{a.field} set")


_links_cache = {"t": 0.0, "data": None}

def links_status():
    """Probe every local link port + live git version per project. 5s cache."""
    import socket, subprocess
    now = time.time()
    if _links_cache["data"] is not None and now - _links_cache["t"] < 5:
        return _links_cache["data"]
    out = {}
    if PROJECTS.exists():
        for d in sorted(PROJECTS.iterdir()):
            bp = d / "board.json"
            if not bp.exists():
                continue
            try:
                b = json.loads(bp.read_text())
            except json.JSONDecodeError:
                continue
            links = b.get("links", {})
            st = {}
            for l in links.get("local", []):
                port = l.get("port")
                ok = False
                if port:
                    try:
                        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.25):
                            ok = True
                    except OSError:
                        ok = False
                st[l["label"]] = ok
            ver = None
            repo = Path(b.get("meta", {}).get("repo", "")).expanduser()
            if repo.is_dir():
                r = subprocess.run(["git", "-C", str(repo), "describe", "--tags", "--always", "--dirty"],
                                   capture_output=True, text=True)
                if r.returncode == 0:
                    ver = r.stdout.strip()
            out[d.name] = {"status": st, "local_version": ver}
    _links_cache.update(t=now, data=out)
    return out


TOKENS_PATH = Path.home() / ".progresslive" / "tokens.json"

def load_tokens():
    try:
        return json.loads(TOKENS_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def cmd_token(a):
    import secrets, hmac as _
    toks = load_tokens()
    if a.action == "add":
        if not a.name:
            sys.exit("token add needs a name")
        toks[a.name] = secrets.token_urlsafe(24)
        atomic_write(TOKENS_PATH, json.dumps(toks, indent=1))
        os.chmod(TOKENS_PATH, 0o600)
        print(f"token for '{a.name}': {toks[a.name]}\n(hand this to them; revoke anytime: progress token revoke {a.name})")
    elif a.action == "revoke":
        if toks.pop(a.name, None) is None:
            sys.exit(f"no token named '{a.name}'")
        atomic_write(TOKENS_PATH, json.dumps(toks, indent=1))
        print(f"revoked '{a.name}'")
    else:  # list
        print("\n".join(f"{n}  {t[:6]}…" for n, t in toks.items()) or "no tokens")


def cmd_serve(a):
    import hmac, threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    remote = getattr(a, "remote", False)
    origin = getattr(a, "origin", "https://progress.akeyo.io")

    def authed(tok):
        return any(hmac.compare_digest(tok, t) for t in load_tokens().values())

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):  # quiet
            pass

        def _cors(self):
            if remote:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Headers", "Authorization, If-None-Match, Content-Type")
                self.send_header("Access-Control-Expose-Headers", "ETag")

        def _send(self, code, body, ctype, extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _auth_ok(self):
            """Remote mode: every /api/* needs a valid token. 401 carries ZERO data."""
            if not remote:
                return True
            tok = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
            if not tok:  # EventSource can't set headers — allow ?t= for /api/stream only
                from urllib.parse import parse_qs, urlparse
                if urlparse(self.path).path == "/api/stream":
                    tok = parse_qs(urlparse(self.path).query).get("t", [""])[0]
            return bool(tok) and authed(tok)

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_stream(self):
            # Chunked transfer — proxies (Cloudflare tunnel) stream chunked bodies but
            # buffer unknown-length ones. Manual framing; each SSE payload = one chunk.
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self._cors()
            self.end_headers()
            self.close_connection = True

            def chunk(b):
                self.wfile.write(f"{len(b):x}\r\n".encode() + b + b"\r\n")
                self.wfile.flush()

            chunk(b": " + b"p" * 2048 + b"\n\n: hello\n\n")
            last = None
            beat = 0
            try:
                while True:
                    sig = max((f.stat().st_mtime_ns for f in PROJECTS.glob("*/*") if f.is_file()), default=0)
                    if sig != last and last is not None:
                        chunk(b"data: changed\n\n")
                    last = sig
                    beat += 1
                    if beat % 30 == 0:  # heartbeat ~15s keeps proxies open
                        chunk(b": beat\n\n")
                    time.sleep(0.5)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            path = self.path.split("?")[0]
            try:
                if path.startswith("/api/") and not self._auth_ok():
                    self._send(401, b'{"error":"unauthorized"}', "application/json")
                    return
                if path in ("/", "/index.html") or path.startswith("/#"):
                    self._send(200, (SITE / "index.html").read_bytes(), "text/html; charset=utf-8")
                elif path == "/api/stream":
                    self.do_stream()
                elif path == "/api/state":
                    etag, _ = state_sig()  # stat-only — idle polls never parse JSON
                    if self.headers.get("If-None-Match") == etag:
                        self.send_response(304)
                        self.send_header("ETag", etag)
                        self._cors()
                        self.end_headers()
                        return
                    state, etag = assemble_state()
                    self._send(200, json.dumps(state, ensure_ascii=False).encode(), "application/json", {"ETag": etag})
                elif path == "/api/links":
                    self._send(200, json.dumps(links_status()).encode(), "application/json")
                elif path == "/api/remote-info" and not remote:
                    # LOCAL server only (never exposed through the tunnel): current remote
                    # connection recipe so the local board always shows working values.
                    info = {"shell": "https://progress.akeyo.io/", "tunnel_url": None,
                            "tunnel_up": False, "tokens": load_tokens()}
                    f = Path.home() / ".progresslive" / "tunnel_url"
                    if f.exists():
                        info["tunnel_url"] = f.read_text().strip()
                    else:  # fallback: newest tunnel log
                        import glob, re
                        logs = sorted(glob.glob("/tmp/pl-tunnel*.log"), key=os.path.getmtime, reverse=True)
                        for lg in logs[:3]:
                            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", open(lg).read())
                            if m:
                                info["tunnel_url"] = m.group(0)
                                break
                    if info["tunnel_url"]:
                        try:
                            import urllib.request
                            r = urllib.request.urlopen(info["tunnel_url"] + "/api/state", timeout=3)
                        except Exception as e:
                            info["tunnel_up"] = getattr(e, "code", None) == 401  # 401 = alive + auth on
                        else:
                            info["tunnel_up"] = True
                    self._send(200, json.dumps(info).encode(), "application/json")
                elif path.startswith("/api/events/"):
                    slug = path.rsplit("/", 1)[1]
                    ep = events_path(slug)
                    if not ep.exists():
                        self._send(404, b"{}", "application/json")
                    else:
                        self._send(200, ep.read_bytes(), "application/x-ndjson")
                else:
                    self._send(404, b"not found", "text/plain")
            except BrokenPipeError:
                pass

        def do_POST(self):
            # /api/restart {slug,label}: run the restart command STORED IN board.json
            # (trusted, agent-written file) — request only selects which one. 127.0.0.1 only.
            try:
                if not self._auth_ok():
                    self._send(401, b'{"error":"unauthorized"}', "application/json")
                    return
                if self.path.split("?")[0] != "/api/restart":
                    self._send(404, b"not found", "text/plain")
                    return
                n = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(n) or b"{}")
                b = json.loads(board_path(req.get("slug", "")).read_text())
                link = next((l for l in b.get("links", {}).get("local", [])
                             if l["label"] == req.get("label")), None)
                if not link or not link.get("restart"):
                    self._send(400, b'{"ok":false,"err":"no restart command stored for this link"}', "application/json")
                    return
                import subprocess
                subprocess.Popen(["/bin/sh", "-c", link["restart"]], start_new_session=True,
                                 stdout=open("/tmp/pl-restart.log", "ab"), stderr=subprocess.STDOUT)
                append_event(b["slug"], "note", f"restart issued for '{link['label']}' from the board UI")
                _links_cache["t"] = 0  # bust probe cache
                self._send(200, b'{"ok":true}', "application/json")
            except Exception as e:
                self._send(500, json.dumps({"ok": False, "err": str(e)}).encode(), "application/json")

    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    print(f"ProgressLive serving http://localhost:{a.port}/  (Ctrl-C stops)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    ap = argparse.ArgumentParser(prog="progress", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="register a project")
    p.add_argument("slug"); p.add_argument("--name"); p.add_argument("--tagline")
    p.add_argument("--repo"); p.add_argument("--manager"); p.set_defaults(f=cmd_init)

    p = sub.add_parser("update", help="update a phase (creates if missing); auto-appends event; --sub targets a nested subitem")
    p.add_argument("slug"); p.add_argument("--phase", required=True); p.add_argument("--sub"); p.add_argument("--label")
    p.add_argument("--pct", type=int); p.add_argument("--status", choices=STATUSES)
    p.add_argument("--eta"); p.add_argument("--note"); p.add_argument("--here", action="store_true")
    p.add_argument("--event", help="override the auto event text"); p.set_defaults(f=cmd_update)

    p = sub.add_parser("here", help="move the YOU ARE HERE marker")
    p.add_argument("slug"); p.add_argument("phase"); p.set_defaults(f=cmd_here)

    p = sub.add_parser("event", help="append a history event")
    p.add_argument("slug"); p.add_argument("text")
    p.add_argument("--kind", default="note", choices=KINDS); p.add_argument("--delta")
    p.set_defaults(f=cmd_event)

    p = sub.add_parser("roster", help="set agents: --set name:model:lane:state (bulk) or --agent NAME w/ rich fields (state 'gone' removes)")
    p.add_argument("slug"); p.add_argument("--set", action="append"); p.add_argument("--clear", action="store_true")
    p.add_argument("--agent"); p.add_argument("--model"); p.add_argument("--lane")
    p.add_argument("--state", choices=AGENT_STATES); p.add_argument("--pct", type=int)
    p.add_argument("--current", help="what the agent is doing right now"); p.add_argument("--pane")
    p.add_argument("--items", help="JSON array: the agent's own work tree [{key,label,pct,status,note,subitems?}]")
    p.set_defaults(f=cmd_roster)

    p = sub.add_parser("ingest", help="apply a SIP status-reply JSON (phases/subitems/roster/events/proof) mechanically")
    p.add_argument("slug"); p.add_argument("--json"); p.add_argument("--file", help="path to SIP JSON")
    p.set_defaults(f=cmd_ingest)

    p = sub.add_parser("swarm-scan", help="zero-token swarm observation: status drops + tmux panes → roster")
    p.add_argument("slug"); p.add_argument("--session", help="tmux session name")
    p.add_argument("--socket", help="tmux -L socket (e.g. claude-swarm-<pid>)")
    p.add_argument("--quiet", action="store_true", help="print NOTHING when 0 changed (Monitor-safe: no output = no agent wake)")
    p.set_defaults(f=cmd_swarm_scan)

    p = sub.add_parser("proof", help="record a verified claim")
    p.add_argument("slug"); p.add_argument("--claim", required=True); p.add_argument("--cmd")
    p.add_argument("--result"); p.add_argument("--ref"); p.set_defaults(f=cmd_proof)

    p = sub.add_parser("setjson", help="set kpis|links|version on a board from a JSON string")
    p.add_argument("slug"); p.add_argument("field"); p.add_argument("json"); p.set_defaults(f=cmd_setjson)

    p = sub.add_parser("board", help="print the board (ANSI)")
    p.add_argument("slug"); p.set_defaults(f=cmd_board)

    p = sub.add_parser("serve", help="serve site + JSON API (--remote adds token auth + CORS + SSE for tunnel exposure)")
    p.add_argument("--port", type=int, default=8177); p.add_argument("--remote", action="store_true")
    p.add_argument("--origin", default="https://progress.akeyo.io"); p.set_defaults(f=cmd_serve)

    p = sub.add_parser("token", help="remote access tokens: add <name> | revoke <name> | list")
    p.add_argument("action", choices=("add", "revoke", "list")); p.add_argument("name", nargs="?")
    p.set_defaults(f=cmd_token)

    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
