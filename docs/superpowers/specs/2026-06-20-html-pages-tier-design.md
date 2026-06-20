# Design: "HTML pages" visual tier (Chrome-rendered, animated, free)

**Date:** 2026-06-20
**Skill:** slides-to-video
**Status:** approved (brainstorming) → ready for implementation plan

## Problem & goal

The skill has two visual tiers — free programmatic animation (`scenes.py`) and the paid gpt-image-2 tier. Users want a **designed** look: bespoke, beautiful pages (rich typography, real layout) that make content easy to grasp — like a hand-designed explainer deck — not charts-or-photos. Add a **third opt-in tier: HTML pages.** From the slides + material, design one HTML/CSS page per scene, render it with headless Chrome, and sequence the pages into the narrated video. **Local & free** (uses the already-installed Google Chrome — no Playwright/Puppeteer/new dependency), **deterministic**, and **faithful** (pages render only real content).

**Verified feasibility (this machine):**
- Google Chrome is installed (`/Applications/Google Chrome.app`); Playwright/Puppeteer/wkhtmltoimage are **not**. Node 24 present.
- `chrome --headless --screenshot` renders an HTML file to a crisp 1920×1080 PNG with correct CJK + serif.
- **Deterministic CSS-animation capture without CDP:** pausing animations and setting a *negative* `animation-delay` of `-(p × duration)` freezes the page at progress `p`. Measured a clean linear ramp (p=0/.25/.5/.75/1 → 0/400/800/1200/1600 px) and **byte-identical** re-renders. (Raw `--virtual-time-budget` was imprecise and is NOT used.)

## Decisions (from brainstorming)
- **Bespoke HTML on a bundled design system** (not fixed templates): I author each page from the content plan on a bundled huashu-aligned stylesheet.
- **CSS-animation capture** (not static + Ken Burns): the page's paused reveals are captured frame-by-frame via the `?p=` freeze-frame seek.
- **Chrome headless** (not Playwright): free, installed, proven.
- **Reveal-then-hold capture:** animate the entrance for `anim_seconds`, then hold the settled frame — keeps Chrome launches low.

## Architecture & data flow

An `html` scene is a **new animated scene type** that plugs into the EXISTING animated path with no dispatch change:
```
content-planner (beat sequence)  →  I author <out_dir>/pages/scene_NN.html on base.css (faithful)
  →  critic (faithful + subtitle + R2 audio↔visual)
  →  render: render._render_scene → getattr(scenes,"render_html") → frame sequence → _encode_frames_clip (frames+audio+captions)
  →  edge-tts → sample sign-off → ffmpeg concat
```
`render_html` screenshots `file://…/scene_NN.html?p=0 … p=1` via Chrome → `scene_{index:02d}_%04d.png`, exactly the shape `_encode_frames_clip` already consumes. Reused unchanged: content-planner, critic, edge-tts, PIL captions, ffmpeg concat, the animated-scene encoder.

## Component 1 — `scenes.py`: `_chrome_shot` + `render_html` (new)
- `_chrome_bin(meta)` — locate Chrome: `meta.chrome_path` override · the macOS app path · `chrome`/`chromium`/`chromium-browser`/`google-chrome` on PATH. Returns None if absent.
- `_chrome_shot(url, out_png, W, H, meta)` — `subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--no-sandbox", f"--window-size={W},{H}", f"--screenshot={out_png}", url], check=True, capture_output=True, timeout=60)`. Raises `RuntimeError` if no Chrome.
- `render_html(props, meta, W, H, frames, workdir, index) -> pattern_str`. props: `{html: "pages/scene_NN.html", anim_seconds?: 0.8}`. `src = os.path.join(meta["_out"], props["html"])`. `reveal_frames = max(1, min(frames, round(anim_seconds*fps)))`. For each video frame `i`: `p = 1.0 if i >= reveal_frames-1 else i/(reveal_frames-1)`; if `p>=1` and a settled shot exists, **copy** it (hold); else `_chrome_shot(f"file://{src}?p={p:.4f}", scene_NN_i.png, W, H, meta)` and remember the settle shot. ⇒ ~`reveal_frames` Chrome launches, the rest are file copies.

## Component 2 — bundled design system `assets/html/` (new)
- **`base.css`** — huashu-aligned, anti-AI-slop: dark stage `#0d1117`; **CJK-first serif stack** (`"PingFang SC","Hiragino Sans GB",…,Georgia,serif`); a `.stage` 1920×1080 padded flex; type scale (`.kicker .title .sub .stat .row`), accent palette (blue `#4C9BE8`, orange `#E8590C`), an accent `.rule`; CSS-Grid `.grid`. **No** purple gradients / emoji. **Seekable reveal classes** `.reveal` / `.reveal-up` (opacity / translateY), `animation-play-state: paused`, staggerable via an inline `--i`.
- **`seek.js`** — stagger-aware freezer: collects every element whose computed `animation-name != none`, computes `total = max(delay+duration)`, reads `?p=`, and sets each element's `animation-delay = (origDelay − p×total)` + `animation-play-state: paused`. This freezes each element at local time `(p×total − origDelay)`, so staggered reveals render correctly at any `p`. (Generic — works for any page built on `base.css`.)

## Component 3 — authoring guide `references/html-pages.md` (new)
How to author a faithful, designed page on `base.css`: the layout patterns (title · big-stat · split/breakdown · list · quote · timeline), the reveal classes + the seekability contract (use CSS animations / the reveal classes so `seek.js` can freeze them — no JS-driven motion, no `setTimeout`, no external network assets), and the **faithfulness rule** (every number/claim from the material; no invented data; data tables/numbers typed from the source). Include `<script src="…/seek.js">` + `<link rel="stylesheet" href="…/base.css">` boilerplate and one worked example page.

## Component 4 — schema (`scripts/storyboard.py`)
- `VALID_SCENE_TYPES`/`ANIMATED_TYPES += "html"`.
- `_validate_props` for `html`: requires a non-empty string `html`; optional `anim_seconds` must be a positive number if present.

## Component 5 — `render.py` `_fingerprint` (one-line addition)
The clip cache hashes `props` (which holds the html *path*) but not the page's *content*. Add the page file's stat so editing a page re-renders: in the `_fingerprint` payload add `"html": stat((slide.get("props") or {}).get("html"))` (reusing the existing `stat(rel)` helper, mirroring `"img"`/`"aud"`). No other render.py change (dispatch already routes `html` via `getattr(scenes,"render_html")`).

## Component 6 — workflow (`SKILL.md`)
- The interview's visual-mode choice gains **"HTML pages (designed, Chrome-rendered, free — needs Google Chrome)"**, alongside free-programmatic and gpt-image.
- When chosen: content-planner designs the beats → author one `pages/scene_NN.html` per beat on `base.css` (faithful, designed) → critic → 🔴 sample sign-off → render → edge-tts → full.
- Guardrails + failure table: Chrome requirement and `meta.chrome_path`; *Chrome missing → clear error + fall back to the free programmatic tier*; pages render only real content (no invented facts). The critic (R2 audio↔visual, R1d/R1e faithfulness) applies unchanged — no critic edit needed.

## Data contract example
```json
{ "index": 4, "type": "html",
  "props": { "html": "pages/scene_04.html", "anim_seconds": 0.8 },
  "narration": "这 165 次里，123 次是自己打星链，对外只有 42 次。" }
```
`pages/scene_04.html` is an authored designed page (a labeled 123-vs-42 split on `base.css`, reveal-animated) containing only the real numbers.

## Error handling
| Condition | Behavior |
|---|---|
| No Chrome found (and no `meta.chrome_path`) | `_chrome_shot` raises a clear RuntimeError naming the expected path; the workflow falls back to the free programmatic tier with a notice. |
| `pages/scene_NN.html` missing at render | `render_html` raises with the scene index. |
| Chrome screenshot non-zero exit / timeout | `subprocess` raises (captured) with the scene index; surfaced at render. |
| Page edited (same path) | `_fingerprint` includes the page file stat → the clip re-renders. |
| Page uses JS-timed motion / network assets | Authoring guide forbids it (non-seekable / non-deterministic); the seek contract requires pure CSS animations. |

## Testing (deterministic; no network; Chrome mocked except one opt-in test)
- **`_chrome_shot`:** mock `subprocess.run` → assert the Chrome binary + flags (`--headless`, `--window-size=WxH`, `--screenshot=out`, the `file://…?p=` url); `_chrome_bin` honors `meta.chrome_path` and returns None when absent (→ RuntimeError).
- **`render_html`:** monkeypatch `_chrome_shot` to write a 1×1 PNG → assert exactly `frames` PNGs named `scene_NN_%04d.png`; assert Chrome is called ≈ `reveal_frames` times and the hold frames are copies (call-count assertion); deterministic call sequence (`p` values).
- **schema:** `html` validates with a path; missing/empty `html` or non-numeric `anim_seconds` raise; existing types unchanged.
- **`_fingerprint`:** changing the page file's mtime/size changes the fingerprint (touch the file → different hash); unchanged page → stable.
- **integration (opt-in, `skipif` no Chrome):** screenshot a tiny `base.css` page at `?p=0` and `?p=1` and assert both are non-blank and differ (the reveal animated).
- **workflow:** prose — grep the SKILL.md additions; verified by the SpaceX HTML demo.
- Existing suite stays green.

## Out of scope (later increments)
A `--no-cache` flag / renderer-version in the fingerprint; an optional Playwright fast-path (one browser, CDP) for long fully-continuous animations; more bundled page patterns; HTML→PPTX export. YAGNI now. Increment 1 uses reveal-then-hold capture and bespoke author-time pages.
