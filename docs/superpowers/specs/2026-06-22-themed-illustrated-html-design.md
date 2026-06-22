# Design: creative, themed, illustrated HTML video (general)

**Date:** 2026-06-22
**Skill:** slides-to-video
**Status:** approved (brainstorming) → ready for implementation plan

## Problem & goal

The HTML-pages tier produces good designed videos, but three limits make every output feel the
same: (1) the content-planner **mirrors the source deck 1:1** instead of designing a *video*;
(2) the palette is **always dark** (`#0d1117`) regardless of topic; (3) content pages are
**text-only cards** — imagery is hero-only. Generalize three upgrades into the skill so any topic
gets a creative, topic-fitting, illustrated result:
1. **Re-conceive** the material into the best instructional video arc (faithful, not slide-order).
2. **Topic-driven color theme** — derive a fitting palette from the source material (else topic/web), light *or* dark.
3. **Illustrated + animated content pages** — selective generated images on content beats with Ken-Burns motion + reveals.

## Decisions (from brainstorming)
- **Palette:** auto-sample from `frames/` when present; else a topic/web-informed palette. `theme.py` derives a **curated** palette (not raw muddy pixels). Shown at the plan checkpoint.
- **Mode:** topic-driven light OR dark.
- **Imagery:** **selective** — the planner adds an image only where it helps a point (+ section heroes); Ken-Burns + reveals on all.
- **Re-conception:** re-conceive freely (same substance, faithful), not slide order.

## Architecture

The HTML pipeline is unchanged in shape (content-planner → scriptwriter → critic → author pages →
imagegen → tts → render via `render_html`). Three additions: a **theme step** (`theme.py` →
`theme.css`), a **re-conceiving + media-assigning** content-planner, and an **illustrated content
page** pattern with Ken-Burns. Pages link `base.css` + `theme.css` + `motifs.css`.

## Component 1 — themeable design system (`assets/html/base.css` + `motifs.css`)
Refactor so **every** color is a semantic CSS variable consumed via `var()` — no hardcoded hex in
component classes:
- `:root` canonical vars (defaults = current dark look): `--bg`, `--surface` (cards/panels),
  `--fg`, `--muted`, `--accent`, `--accent2`, `--rule` (= `var(--accent2)`), `--scrim` (the photo
  scrim base, derived from `--bg`). **Back-compat aliases:** `--blue: var(--accent)`,
  `--orange: var(--accent2)`, `--panel: var(--surface)` (existing pages/inline styles keep working).
- Replace remaining hardcoded colors in `base.css` (`.bar`, `.dot`, `.stat`, etc.) and `motifs.css`
  (`.scrim` `#0d1117…` → `var(--scrim)`; `.ghost` `#fff` → `var(--fg)`; `.bg-glow.blue/.orange` →
  `var(--accent)`/`var(--accent2)`) with the vars.
- Add **`.kenburns`** (in motifs.css): a slow, paused, seekable scale/pan on an `<img>` — e.g.
  `img.kenburns{animation:mt-kenburns 6s ease-out forwards;animation-play-state:paused}` +
  `@keyframes mt-kenburns{from{transform:scale(1)}to{transform:scale(1.12) translate(-2%,-1%)}}`;
  used inside an `overflow:hidden` media panel. (seek.js already freezes it per frame.)
- Add a **`.split`** layout helper (2-column: text + a `.media` panel) for illustrated content pages.

## Component 2 — `scripts/theme.py` (new) → `theme.css`
`theme.py <out_dir> [--mode auto|light|dark] [--accent #hex] [--accent2 #hex] [--bg #hex]`:
- **If `frames/` exist and no color overrides:** load up to ~4 frames, downscale, quantize (PIL)
  to ~5 colors; **mode** = mean luminance (light if ≳0.55, dark if ≲0.45, else majority); **accent**
  = most-saturated quantized color; **accent2** = a second distinct saturated color (or a
  complementary hue).
- **Curated derivation (not raw pixels):** `--bg` = a near-white tint (light) or near-black tint
  (dark) nudged toward the dominant hue; `--fg` = high-contrast ink/cream (enforce ≥ ~7:1 contrast
  vs `--bg`); `--surface` = `--bg` shifted toward `--fg` a few %; `--muted` = a mid tone.
- **No frames:** use the passed `--accent/--bg/--mode` (the planner/assistant supplies a
  topic/web-informed palette) and derive the rest the same way.
- **Output:** write `<out_dir>/theme.css` = `:root{ --bg:…; --surface:…; --fg:…; --muted:…;
  --accent:…; --accent2:…; --rule:var(--accent2); --scrim:… }` and print the chosen swatch + mode.
- Deterministic (no randomness/wall-clock).

## Component 3 — content-planner re-conception + media + theme (`agents/content-planner.md`)
Add principles:
- **Re-conceive, don't mirror.** Design the best instructional *video* arc — a hook, a throughline,
  free resequencing, merged/split beats — covering the source's substance, **strictly faithful**
  (no invented facts/numbers; every beat still traces to `source_ref`).
- **Theme suggestion (top-level field):** propose `theme` = `{mode: light|dark, accent, accent2,
  bg?}` fitting the topic (a few words of rationale). When source frames exist, note "sample the
  frames"; else give concrete hexes from the subject's aesthetic.
- **Per-beat `media` (selective):** for content beats where an image genuinely helps, add
  `media: {image_prompt: "...generic/atmospheric...", motion: "kenburns"}` — illustrative **broll**
  only (no fabricated specific landmarks/logos/text). Most beats stay typographic; heroes keep
  their backdrop.

## Component 4 — illustrated/animated pages + imagery (authoring + render)
- **Authoring guide (`references/html-pages.md`):** add a **Theming** section (link order:
  base.css → theme.css → motifs.css; use the semantic vars; `theme.py` writes theme.css) and an
  **Illustrated content page** pattern (`.split` text + `.media`/`.kenburns` image; or a full-bleed
  `.bg-photo` + `.scrim`), plus the `.kenburns` contract (paused CSS, seek-safe).
- **Imagery:** the per-beat `media` images are generated via the existing `imagegen` providers
  (codex / OpenAI key), cached under `.assets/`, embedded by `file://`. Faithful broll.
- **Render:** unchanged — `render_html` screenshots the page (now with theme + Ken-Burns) frame by
  frame; `seek.js` freezes the Ken-Burns + reveals. No `render.py`/`render_html` change needed.

## Component 5 — workflow (`SKILL.md`) + critic
- Workflow (HTML mode): deep-understanding → **content-planner re-conceives** the arc + proposes
  `theme` + per-beat `media` → run **`theme.py`** (writes `theme.css`) → 🔴 plan checkpoint now also
  shows the **palette swatch + light/dark mode** → scriptwriter → critic → author pages (link
  base.css + theme.css + motifs.css; illustrate where the plan says) → generate media images
  (codex/key) → edge-tts → 🔴 sample → render.
- **Critic:** a one-line note that the re-conceived arc must still **cover the source faithfully**
  (no dropped-into-invention); imagery stays broll (R1e/R2 unchanged).

## Faithfulness
Re-conception keeps every claim/number traceable to the material; the critic verifies the arc
covers the substance and invents nothing. Theme is pure aesthetics. Per-beat images are generic
atmospheric **broll** (critic R1e) — never a fabricated specific landmark/logo, never text/data in
the image; data/claims live as real on-page text.

## Error handling
| Condition | Behavior |
|---|---|
| No `frames/` (web-research topic) | `theme.py` uses the planner's topic palette (`--accent/--bg/--mode`); if none given, falls back to the default dark theme. |
| Sampled palette low-contrast | `theme.py` enforces ≥ ~7:1 fg/bg contrast (overrides fg toward ink/cream). |
| A `media` image fails to generate | The page omits the image (text-only fallback) — same per-scene fallback as the imagegen tier; the page still renders. |
| Page links `theme.css` but it's absent | base.css defaults (dark) apply — page still renders. |

## Testing (deterministic; Chrome/imagegen mocked except opt-in integration)
- **`theme.py`:** on a synthetic light frame → mode "light" + a light `--bg`; on a dark frame →
  "dark"; writes a valid `theme.css` with all vars; `--accent` is the saturated sampled color;
  fg/bg contrast ≥ threshold; `--mode`/`--accent` overrides honored; deterministic (same frames →
  same theme.css).
- **design system:** `base.css`/`motifs.css` contain no hardcoded color hex in component classes
  (grep) — all `var()`; `.kenburns` + `.split` present; back-compat aliases present.
- **opt-in (skipif no Chrome):** a page linking base.css + a light `theme.css` renders **non-dark**
  (sample a pixel — bg is light), proving theming flows end-to-end; a `.kenburns` page at `?p=0` vs
  `?p=1` differs (motion captured).
- **content-planner / SKILL / guide:** prose — grep the new principles/fields/patterns.
- Existing render/scenes/imagegen/storyboard tests stay green.

## Out of scope
Cross-scene video transitions; multi-image collages per page; non-codex/key image providers;
fully-automatic taste (the curated palette is heuristic — the checkpoint lets the user tweak).
