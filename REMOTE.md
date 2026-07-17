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

## Order of work (next round)

1. `--remote` flag: token auth + CORS + 401-zero-data (testable locally w/ curl).
2. SSE endpoint + client wiring (local first).
3. Pages shell build + sign-in screen (deploy WITHOUT tunnel = provably no data).
4. Tunnel bring-up + end-to-end from a second device.
5. Only then DNS on akeyo.io — each step gated on fire17's go.
