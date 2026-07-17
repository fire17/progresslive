# REMOTE.md — the remote-viewing arc (designed 2026-07-17, NOT yet built)

fire17's requirement (2026-07-17, mid-build): view any/all project boards live from any
computer via GitHub Pages, with the LOCAL machine as the only backend, sign-in so only
he + people he verifies see data, and realtime push to all open clients. Constraint,
his words: "no true project data should be on akeyo.io without passing the authorisation
from the computer".

## Design (additive to schema 1 — no migration)

```
[browser anywhere] → https://progress.akeyo.io (GitHub Pages: STATIC SHELL ONLY, zero data baked)
        │  sign-in: access token → localStorage
        ▼
[secure tunnel]  cloudflared tunnel / tailscale funnel → https://pl-api.<domain>
        │  TLS by the tunnel; stable hostname; local port never raw-exposed
        ▼
[this machine]  progress.py serve --remote
        - Bearer-token auth on EVERY /api/* route (allowlist file ~/.progresslive/tokens.json,
          per-person named tokens, revocable; constant-time compare)
        - CORS allow only the Pages origin
        - SSE /api/stream (server push on every board/event write) → all open clients update
          in realtime; ETag polling stays as fallback
        - unauthorized → 401 with ZERO data (not even project names)
```

- Pages shell = same `site/index.html` + a data-source config screen (backend URL + token).
  Local mode keeps working unchanged (no token when bound to 127.0.0.1 only).
- Auth lives ON the machine (server-side), never in the client: shell without a valid
  token renders only the sign-in screen. Data flows outward per-request, post-auth.
- Realtime push: the store already funnels every write through save_board/append_event —
  one hook there feeds the SSE broadcaster. Designed-for since v1 (file contract = interface).
- Token issuing: `progress token add <name>` / `revoke <name>` — fire17 hands tokens to
  people he verifies.

## Why this shape

- Pages can't run servers; baking data violates the auth rule → shell-only is forced.
- Tunnel (not port-forward): TLS + no router config + revocable + hides home IP.
- SSE (not WebSocket): stdlib-friendly, auto-reconnect, one-way push is all we need.

## Status (2026-07-17 — BUILT, live-verified)

1. ✅ `--remote`: token auth (Bearer + `?t=` for SSE) + CORS (origin-locked) + 401-zero-data.
   Verified: no-token 401 · bad-token 401 · good-token 200 · preflight 204.
2. ✅ SSE `/api/stream` (chunked framing) — verified DIRECT (hello + changed within 1s).
   ⚠ KNOWN LIMITATION: Cloudflare QUICK tunnels buffer streaming responses — SSE
   delivers 0 bytes through them (3 framings tried: close-delimited, padded, chunked).
   Remote realtime therefore rides the 2s ETag poll (304 = 0 bytes idle) — worst-case
   ~2s to pixel. Fix path: named CF tunnel or `tailscale funnel` (both stream SSE).
3. ✅ Pages shell live: https://progress.akeyo.io (gh-pages, data-free, sign-in gated).
4. ✅ Tunnel e2e: quick tunnel → token → full board data over TLS. OPERATIONAL LAW:
   start server BEFORE tunnel; any server restart requires a tunnel restart (quick
   tunnels 530 on origin restart); quick-tunnel URL changes each run — paste into the
   shell's sign-in. Tokens: `progress token add <name>` / `revoke` / `list`
   (~/.progresslive/tokens.json, 0600).
5. ⏳ Stable hostname (named tunnel on fire17's CF account or tailscale) — his go.
