# Design: animated scene types (Phase 0/1) for slides-to-video

**Date:** 2026-06-18
**Skill:** slides-to-video
**Status:** approved (brainstorming) → ready for implementation plan
**Prior art:** two multi-agent design workflows (engine survey + no-slides authoring design). This spec is the **Phase 0/1** slice: local/free/deterministic animated scenes via PIL + matplotlib. Remotion, Manim, the facts-ledger/faithcheck/critic-R7 machinery, and cross-scene transitions are **explicitly out of scope** (Phase 2+).

## Problem & goal

Today every frame of the video is a **slide screenshot** (fit to canvas) with a Ken Burns zoom. The user wants frames that are **authored animation** (motion graphics that teach the content), not slides. Phase 0/1 adds the *faithful, free, deterministic* subset of that: animated **title**, **chart**, and **timeline** scenes generated from typed storyboard fields — with no new heavyweight dependencies — slotting into the existing pipeline so a deck can mix slides and animated scenes.

**Goals**
1. A scene-type dispatcher so a scene's clip can come from an animation renderer instead of a slide screenshot.
2. Three deterministic, local/free animated scene types: `title` (PIL), `chart` and `timeline` (matplotlib).
3. 100% backward compatibility: existing storyboards (all `type:"slide"`) render identically.
4. Reuse the per-scene-clip + `-c copy` concat + clip-cache + edge-tts/say narration + PIL caption machinery — no rewrite.

**Non-goals (Phase 2+):** Remotion / Manim / web-headless engines; the facts.json ledger, `faithcheck.py`, and critic rubric R7; cross-scene transitions (xfade); auto-layout. Faithfulness in Phase 0/1 is **by construction** — scenes render only explicit typed fields.

## Decisions (from brainstorming)

- **Lean faithfulness:** scenes render ONLY explicit `props` (text strings + literal `data` arrays); numbers come only from `data`. Required cache wiring (`_fingerprint`) is done now; the ledger/faithcheck/R7 are deferred to Phase 2. A one-line critic note is added.
- **Phase 0 MVP scene type:** `title` (cold-open / kinetic title card), PIL frame sequence.
- **Phase 1 scene types:** `chart` (animated data-viz) and `timeline`, both matplotlib PNG sequences.

## Architecture

Voice/pacing/captions/concat are unchanged. The only new idea is an **alternate frame source** behind the existing per-scene-clip boundary.

### How a scene becomes a clip today (`render.py`, verified)
`render()` iterates slides; for each it calls `_render_slide(slide, meta, W, H, out_clip, burn_captions, workdir)`, which: fits the slide image to a WxH PNG, builds a `zoompan` (Ken Burns) video chain, appends timed caption/callout PNG overlays into a `filter_complex`, and runs ONE ffmpeg invocation producing `out_clip` with `-r fps -pix_fmt yuv420p -c:v libx264 -c:a aac -t dur -map [v] -map 1:a` (audio input is `slide["audio"]`). Clips are cached by `_fingerprint` (sha1 over slide fields + render params + image/audio mtime/size) and joined with `ffmpeg -f concat -c copy`. `duration` is set earlier by `tts.py` from ffprobe — never guessed.

### The change: dispatch + shared encode
1. **Dispatcher.** `_render_slide` branches on `scene.get("type", "slide")`:
   - `"slide"` → existing code path, unchanged.
   - `"title" | "chart" | "timeline"` → call the matching renderer in a new `scripts/scenes.py` to write a **deterministic PNG frame sequence** (`scene_%04d.png`) into `workdir`, exactly `frames = round(duration*fps)` frames (reusing the existing `frames` computation so narration drives pacing). Then hand off to a shared encode step.
2. **Shared encode (`_encode_frames_clip`).** A small helper (factored so both the animated path and, later, external engines use it) that takes: the frame-sequence pattern, the scene's `audio`, `duration`, the caption segments from the existing `_captions_for(slide)`, and emits `out_clip` via the SAME codec command the slide path uses (`-framerate fps -i scene_%04d.png -i audio [caption overlay inputs] -filter_complex <overlay chain> -map [v] -map 1:a -t dur -r fps -pix_fmt yuv420p -c:v libx264 -c:a aac -shortest`). Caption overlays reuse `_captions_for` + `_caption_layer` with the same `overlay=0:0:enable='between(t,a,b)'` mechanism. Output codec/params are byte-compatible with slide clips, so `-c copy` concat and the clip cache are unaffected.
   - Animated scenes have **no Ken Burns** (motion lives in the frames); `motion`/`callouts` are ignored for them.
3. **Cache.** `_fingerprint` adds `type` and `props` to its hashed slide-field tuple, so editing a title string or a data value re-renders that scene (and only it). The renderer functions are pure → same `props`+`meta`+`duration` → identical frames.

### Determinism
Renderers use NO randomness and NO wall-clock. Animation is a pure function of the frame index `i in [0, frames)` (e.g. eased progress `p = ease(i/frames)`). matplotlib uses the Agg backend with fixed figure size/DPI and fixed axis limits. Re-running yields identical PNG bytes.

## Components

### `scripts/storyboard.py` — schema
- `new_slide(...)` gains optional `type="slide"` and `props=None` (kept `None`/absent for slides).
- `new_scene(index, type, props, narration="", notes="")` helper for animated scenes (image=None).
- `validate(data)`:
  - every scene needs `index` and `narration` (today's rule, minus image for animated types);
  - `type` ∈ {`slide`,`title`,`chart`,`timeline`};
  - `type=="slide"` → still REQUIRES `image` (back-compat);
  - animated types → REQUIRE a `props` dict valid for that type (closed per-type check, below); `image` not required;
  - existing callout validation unchanged.
- Per-type `props` validation:
  - `title`: `title` (non-empty str) required; `subtitle`,`kicker`,`accent` optional str.
  - `chart`: `kind` ∈ {`bars`,`line`,`counter`}; `data` is ALWAYS a non-empty list of `{label:str, value:number}` (for `counter`, the list's first item is the target number; any extras ignored). Optional `title`,`unit`,`x_label`,`y_label`,`y_max`(number). Every `value` must be a number (no strings/prose) — this is the lean faithfulness guard.
  - `timeline`: `events` non-empty list of `{date:str, label:str}`; optional `title`, `direction` ∈ {`horizontal`,`vertical`}.

### `scripts/scenes.py` — renderers (new file)
Each returns the frame pattern path (e.g. `<workdir>/scene_%04d.png`) after writing `frames` PNGs at WxH.
- `render_title(props, meta, W, H, fps, duration, workdir)` — PIL. Title fades/rises in over the first ~0.8s, subtitle/kicker stagger, then hold. Reuses `render._font_path` for CJK-safe fonts; honors `props["accent"]` for an accent rule/color; dark background consistent with the skill's caption aesthetic.
- `render_chart(props, meta, W, H, fps, duration, workdir)` — matplotlib Agg. `bars`: bars grow from 0 to their `value` over an eased intro then hold; `line`: line draws left→right; `counter`: number counts up to `value` (never past it). Y-axis pinned to `[0, y_max or max(values)*1.15]` from a true 0 baseline. Labels/units from props. CJK: set `matplotlib.rcParams["font.family"]` to a resolved CJK font (PingFang/Hiragino/AppleSDGothicNeo) when `meta.language` is CJK, else the bundled/Sans default.
- `render_timeline(props, meta, W, H, fps, duration, workdir)` — matplotlib Agg. Axis line draws, then dated events drop in one by one in order.
- A shared `_save_frames(draw_fn, frames, workdir)` writes `scene_%04d.png` by calling `draw_fn(i, frames)` deterministically.

### `scripts/render.py` — dispatch + encode
- `_render_slide`: add the `type` branch described above.
- `_encode_frames_clip(frame_pattern, audio_path, duration, caption_segs, meta, W, H, out_clip, workdir)`: the shared encode helper.
- `_fingerprint`: add `type`, `props` to the hashed `s` dict.
- `render()` sample/full loops unchanged (they already iterate scenes and cache by fingerprint).

### `agents/critic.md` — one-line note
Add to inputs/rubric: for animated scenes (`type` ≠ slide), every on-screen label/number must trace to the scene's `props`/source — flag invented or mis-stated values. (Lightweight; the full R7 rubric is Phase 2.)

## Data contract example
```json
{ "index": 1, "type": "title",
  "props": {"title": "进入商业航天发射市场", "subtitle": "直面 SpaceX 的市场进入评估", "kicker": "战略咨询报告", "accent": "#E8590C"},
  "narration": "欢迎。这是一份…", "audio": null, "duration": null }

{ "index": 4, "type": "chart",
  "props": {"kind": "bars", "title": "年发射次数", "unit": "次", "y_max": 180,
            "data": [{"label":"2022","value":61},{"label":"2025","value":165}]},
  "narration": "发射节奏从 2022 年的 61 次涨到 2025 年的 165 次。", "audio": null, "duration": null }
```

## Error handling
| Condition | Behavior |
|---|---|
| Unknown `type` | `validate()` raises `StoryboardError` (fail fast, before render). |
| Animated type missing/!invalid `props` | `validate()` raises with the specific missing/!typed field. |
| `chart.data` value not a number | `validate()` raises (guards faithfulness: numbers only). |
| Renderer produces wrong frame count | encode uses `-t duration`; `_save_frames` always writes exactly `frames` files. |
| CJK font unavailable for matplotlib | fall back to the bundled Sans (may tofu) + print a notice; same posture as caption fonts. |
| Animated clip codec drift | encode uses the skill's exact libx264/aac/yuv420p/-r fps command → `-c copy` concat holds. |

## Testing
All deterministic and offline (no network; audio mocked or a tiny `say` clip; frame renderers need no audio).
- **Schema:** default `type=="slide"`; slide still requires `image`; `title`/`chart`/`timeline` require valid `props`; unknown type rejected; `chart` non-numeric value rejected; `new_scene` round-trips.
- **Fingerprint:** changing `type` or a `props` value changes the fingerprint (cache invalidates); identical scene → identical fingerprint.
- **Renderer determinism & correctness:** each renderer writes exactly `round(duration*fps)` PNGs at WxH; final frame has real (non-blank) pixels; re-running yields byte-identical frames; `chart` bars reach the correct pixel heights for the data and never exceed `y_max`; a CJK `title` renders glyphs (non-blank) using a CJK font.
- **End-to-end (guarded by `have_tool('ffmpeg')`):** a 2-scene storyboard (one `title` + one `slide`) renders, both clips have video+audio streams at the same WxH/fps/codec, durations match the audio, and they concat into one `out.mp4` with `-c copy`. Captions burn over the title scene.
- Existing slide/tts/render tests stay green (back-compat).

## Phasing within this spec
- **Phase 0:** schema `type`/`props` + `validate` + `_fingerprint` wiring + dispatcher + `_encode_frames_clip` + `title` renderer + tests. (Proves the whole seam.)
- **Phase 1:** `chart` (bars/line/counter) + `timeline` renderers + their schema validation + tests.

## Out of scope / future (Phase 2+)
Remotion designed scenes + template library; Manim equation scenes; facts.json ledger + `faithcheck.py` + critic R7; cross-scene transitions; bespoke free-form scene components.
