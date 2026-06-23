# Design: visual-design upgrade (huashu-design principles, adapted)

**Date:** 2026-06-23
**Skill:** slides-to-video
**Status:** approved (study synthesis + scope choice) → ready for implementation plan

## Problem & goal
Our HTML-tier video pages are clean but plain. A parallel study of the mature **huashu-design**
skill's 24 design references surfaced concrete, transferable principles. Integrate the **high-value
bundle** (the biggest visual jump for moderate effort) into our design system — adapted to our
static-frame HTML/CSS + freeze-frame (`seek.js`) + ffmpeg Ken-Burns model, NOT copied. Out: the
larger-effort niche items (named palette modes, style_pattern hints, rhythm presets, gallery/3D
perspective, scenes.py compound-pan, full critic R_vars/R_slop) and everything React/Remotion/SFX.

## Principles adopted (adapted to our model)
Color depth (no pure #000/#fff, one dominant accent), data-mono typographic register + tabular nums
+ tighter tracking, 8-pt grid + real card depth + whitespace floor, depth-via-blur focus, expo-out
easing + spring pop + tight stagger + diagonal Ken-Burns, visual variety (no >2 same type in a row),
a director's discipline in the planner, and self-critique (squint / cover-text / anti-slop).

## Component 1 — `assets/html/base.css` (typography, depth, motion, layout primitives)
- **Easing + timing vars** in `:root`: `--ease-expo:cubic-bezier(.16,1,.3,1)`,
  `--ease-over:cubic-bezier(.34,1.56,.64,1)`, `--ease-exit:cubic-bezier(.55,0,1,.45)`,
  `--dur-fast:.35s`, `--dur-slow:1.2s`, `--stagger:.03s`. Re-point `.reveal-up` to `var(--ease-expo)`.
- **`.reveal-pop`** (spring overshoot for a hero stat): `opacity:0;transform:scale(.88);
  animation:pop var(--dur) var(--ease-over) forwards;animation-play-state:paused` +
  `@keyframes pop{to{opacity:1;transform:none}}`. **`.reveal-up-sm`** (translateY 10px) for dense sub-items.
- **Mono register**: `--font-mono:"JetBrains Mono","SF Mono",ui-monospace,monospace` in `:root`;
  `.mono{font-family:var(--font-mono);letter-spacing:.04em;font-variant-numeric:tabular-nums}`;
  apply mono + tabular to `.kicker`; add `font-variant-numeric:tabular-nums` to `.stat`/`.bar`/`.label`.
- **Tracking + balance**: `.stat` letter-spacing `-.02em→-.04em`; `.title` `-.01em→-.025em` + `text-wrap:balance`.
- **Depth tokens + card**: `:root` `--shadow-primary:0 20px 60px -20px rgba(0,0,0,.22)`,
  `--shadow-float:0 6px 18px -6px rgba(0,0,0,.12)`, `--hairline:1px solid rgba(127,127,127,.16)`;
  `.card{background:var(--surface);border-radius:14px;padding:28px 32px;border:var(--hairline);
  box-shadow:var(--shadow-primary),var(--shadow-float)}`.
- **8-pt grid + primitives**: `.grid` gap `40px→48px`, `.row` gap `28px→32px`;
  `.grid-asym{display:grid;grid-template-columns:2fr 1fr;gap:48px;align-items:start}`;
  `.dash{display:grid;grid-template-columns:1fr 1fr 1fr;gap:48px;align-items:start}` +
  `.dash-col{display:flex;flex-direction:column;gap:24px}`. A `/* 8-pt grid */` + hierarchy-contract comment.
- All new motion classes keep `animation-play-state:paused` (seek-safe).

## Component 2 — `assets/html/motifs.css` (focus depth, section divider, Ken-Burns drift)
- **`.defocus`**: `filter:brightness(.6) saturate(.7) blur(4px);opacity:.5` — depth on the non-focal element.
- **`.accent-fill`**: `background:var(--accent);color:var(--on-accent)` — full-bleed section-divider beats.
- **Diagonal Ken-Burns**: `@keyframes mt-kenburns{from{transform:scale(1.02)}to{transform:scale(1.14) translate(-3%,-1.5%)}}` (adds drift to the scale-only zoom; still paused/seek-safe).
- **Softer scrim**: keep the photo ≥45% visible — lighten the right edge so the image isn't half-blacked.
- **`.bg-paper`** (optional light-mode texture): a faint radial tint over `--bg`.

## Component 3 — `scripts/theme.py` (anti-cliché palette guard)
- In `derive_theme`, after resolving `bgc`: clamp a near-pure background — if the passed/derived `--bg`
  is `#000000`/very-near-black → `#0e0f11`; `#ffffff`/very-near-white → `#f8f7f4` (temperature-tinted
  neutrals, never pure). Deterministic; the contrast loop still runs after. Unit-tested.

## Component 4 — `agents/content-planner.md` (director discipline + variety + palette)
- **`director_note`** (required when target_seconds > 60): `{thesis, not:[...], tone}` — an explicit
  one-line thesis, a "what this is NOT" exclusion list, and a tone word.
- **`anti_slop`** (required array): the plan's self-imposed bans (no emoji, no gradient-mesh bg, no stat
  without `source_ref`, no >2 same-type beats in a row).
- **`climax`** marker on exactly one beat (~75–80% of the runtime); **`hold`** marker on the final
  beat (sparse title/stat, no fade-out beat).
- **Visual variety rule**: no more than 2 consecutive beats share `visual.type`; scan the beat list and
  break runs before returning.
- **Palette rule**: pick ONE dominant `--accent`; `--accent2` is a split-complement/tint, not an
  independent hue; never propose a pure `#000`/`#fff` bg; avoid the electric-blue-on-#0d1117 cliché
  unless the topic is literally code/GitHub.
- **Pre-output self-check**: the squint test (does each beat's hierarchy read at low-res?) + the
  cover-text test (are adjacent beats distinguishable by visual shape alone?).

## Component 5 — `references/html-pages.md` (patterns + checklists)
- **Typographic role table** (`.stat`/`.title`/`.sub`/`.kicker`/`.note` semantic roles; "use the named
  classes, never a raw font-size px").
- **New patterns**: `.card`/`.dash`/`.grid-asym` (dashboard + asymmetric), `.defocus` (focus depth on
  compare pages), `.accent-fill` (section divider), `.reveal-pop` (hero-stat spring).
- **One-concept rule** (one primary per page) + **whitespace floor** (content ≤ ~60% of the canvas).
- **Stagger cadence**: kicker 0s, rule .05s, title .10s, first row .25s, +.03s per sibling, cap .9s.
- **Anti-slop checklist** (no emoji / gradient-mesh bg / circle+left-border cards / player-chrome
  progress bars / hardcoded hex / CDN links) + **pre-render checklist** (absolute file://, no overflow
  below 960px, semantic vars only, paused animations).

## Component 6 — critics (light visual-quality checks)
- `agents/critic-content.md`: add a **visual-variety + anti-slop** check — flag >2 consecutive same
  `visual.type`, any emoji/gradient-mesh/fabricated-stat, and any hardcoded hex in an authored page.
- `agents/critic-av.md`: add a **squint + no-player-chrome** check on the rendered sample — the
  hierarchy must read at a glance; flag any element resembling a video player control / progress bar.

## Faithfulness & invariants (unchanged)
All motion stays CSS-only + paused (seek.js-freezable). No network/CDN assets. Pages use semantic
vars only (no hardcoded hex). Imagery stays broll. The theme bg clamp only nudges pure black/white.

## Error handling
| Condition | Behavior |
|---|---|
| `theme.py` passed a pure `#000`/`#fff` bg | Clamp to `#0e0f11`/`#f8f7f4`; contrast loop still runs. |
| A page omits the new classes | base.css defaults still render (additive — `.card`/`.dash`/etc. are opt-in). |
| `--font-mono` unavailable on the host | The stack falls back to `ui-monospace`/system mono — always resolves. |
| Planner omits `director_note` for a short video (≤60s) | Allowed — it's required only for >60s. |

## Testing (deterministic; Chrome-gated parts skipif)
- **theme.py**: pure-black bg → `#0e0f11`; pure-white bg → `#f8f7f4`; a normal bg passes through; contrast still ≥7.
- **base.css/motifs.css (grep)**: the new vars (`--ease-expo`, `--font-mono`, `--shadow-primary`,
  `--hairline`) + classes (`.reveal-pop`, `.card`, `.dash`, `.grid-asym`, `.defocus`, `.accent-fill`)
  present; `.reveal-pop`/`.defocus` keep `animation-play-state:paused`; no hardcoded scrim hex regressed.
- **opt-in Chrome**: a `.card` page renders non-blank; a `.reveal-pop` page differs at `?p=0` vs `?p=1`
  (the spring is captured); the existing themeable/light/kenburns tests stay green.
- **content-planner / html-pages / critics (prose)**: grep the new fields/rules/patterns/checks.
- Full suite stays green.

## Out of scope
Named palette modes, `style_pattern`/`rhythm` fields, gallery/3D perspective-wall, scenes.py
compound-sine pan, the full critic R_vars/R_slop graders, SFX/BGM, any React/Remotion/realtime motion.
