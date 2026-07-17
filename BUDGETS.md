# BUDGETS.md — vision adjectives → numeric budgets → test

Every quality adjective in VISION.md, translated to a measured threshold on the real
target. A regression here is a build failure, not a ticket.

| # | Vision adjective (verbatim) | Metric | Threshold | Test command |
|---|---|---|---|---|
| 1 | "realtime updating" | board change → pixel change, no reload | ≤ 2.0s p95 | `.deify/verify/realtime.sh` (writes event, polls DOM) |
| 2 | "reactive" | poll cost per tick (idle) | ≤ 1 req, ≤ 2 KB, 304 when unchanged | `.deify/verify/poll.sh` (curl etag twice) |
| 3 | "super amazing and polished / state of the art" | impeccable absolute-bans scan + contrast | 0 bans, body ≥ 4.5:1, large ≥ 3:1 | `.deify/verify/design.sh` (detect.mjs + contrast.py) |
| 4 | "nice and polished page" | cold load (localhost, no build step) | ≤ 300ms DOMContentLoaded | `.deify/verify/perf.sh` |
| 5 | "pleasing to see" | frame budget while bars animate | ≤ 16ms/frame, idle CPU ≈ 0% | manual + reduced-motion honored |
| 6 | "see everything" | board shows all phases + roster + events + proof | 0 truncated sections | `.deify/verify/completeness.sh` |
| 7 | "current and historical progress" | both surfaces present | board.json + events.jsonl both rendered | same as #6 |
| 8 | "generic and expandable" | register a 2nd project with 0 code edits | `progress init <slug>` works | `.deify/verify/generic.sh` |
| 9 | honest data (house law) | staleness visible | last-updated + live/stale badge from data age | `.deify/verify/stale.sh` |

## Zero-overhead law

No build step. No external requests (no CDN, no webfont, no analytics). System fonts.
Server = python3 stdlib only. Idle server CPU ≈ 0% (no busy loop; poll is client-driven).
