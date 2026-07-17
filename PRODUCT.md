# PRODUCT.md — ProgressLive

**Register:** product (design SERVES the product — this is a live instrument, not a
marketing page).

## What it is

A realtime dev-progress instrument. An agent writes truth into files; fire17 opens a tab
and sees exactly where every project is — current state AND full history — without
asking anyone. Per VISION.md: *"so i know when i look at the site that i see everything"*.

## Who / where / when

fire17, at any hour, glancing at a browser tab while agent fleets build. Beside him:
dark terminal panes. He wants a truthful answer in under two seconds of looking, then
back to work. He is the only user. He distrusts claims; he trusts observed facts.

## Jobs

1. Where is every project right now? (fleet view)
2. Where exactly is *this* project, and what proves it? (project view)
3. How did we get here? (event history)
4. Is what I'm looking at actually fresh? (live/stale — machine-derived, unfakeable)

## Design direction (committed)

**Scene:** a mastering suite's meter bridge — needles breathing, honest, nothing
decorative — but read in daylight, next to dark terminal panes. → **light-first, with a
real dark theme.**

**Reflex rejections (the AI-slop test, both altitudes):**
- 1st order: "dev dashboard" → dark navy/purple SaaS, identical stat cards, hero metric. **Rejected.**
- 2nd order: "dashboard that isn't SaaS-dark" → green-on-black CRT terminal — precisely where
  the green brand seed would lazily land. **Rejected.**
- Landing: **white bench + plotter-green ink + clay alarms.** Deliberately distinct from
  AgentWorkAtlas (amber-on-ink cartography); the two must never be confused at a glance.

**Color strategy:** committed. Green (seed hue 145) is the brand AND the meaning — the
product is literally "things going green". A bar filling green is the hero, so green
carries it; nothing else competes.

| Role | Meaning |
|---|---|
| green 145 | done / live / the pulse |
| clay 40 | blocked — needs a human |
| amber 75 | gated — waiting on a decision |
| muted | queued — not started |

**Form:** rows, not cards. A dense typographic meter bridge / departure board. Bars are
the hero and get the craft. `ch`-based monospace columns so numbers align like an
instrument, not a webpage.

**Bans in force** (impeccable absolute bans, all): no side-stripe borders, no gradient
text, no glassmorphism, no hero-metric template, no identical card grids, no tracked
uppercase eyebrows, no `01/02/03` section scaffolding, no text overflow at any width.
Also self-imposed: no cream/sand/beige body bg (the 2026 AI default), no CDN, no webfont.

**Motion:** the live phase's bar breathes (opacity/transform only, ≤16ms/frame). Event
arrivals fade in. Everything crossfades or snaps under `prefers-reduced-motion: reduce`.
Content is visible by default — reveals never gate visibility (headless renderers).

## Non-goals (v1)

Auth, multi-user, cloud, DB, build step, framework, MCP server. All deliberately deferred;
the file-based data contract makes each additive later (see IA.md).
