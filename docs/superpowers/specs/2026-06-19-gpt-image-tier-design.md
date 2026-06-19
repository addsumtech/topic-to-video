# Design: opt-in gpt-image generation tier (general)

**Date:** 2026-06-19
**Skill:** slides-to-video
**Status:** approved (brainstorming) → ready for implementation plan

## Problem & goal

The free tier (programmatic animation / slide screenshots) is faithful and deterministic but visually plain. Users want the option of **fancy, AI-generated imagery**. Add a **general, opt-in** image-source tier: when the user chooses it and provides an OpenAI key, scenes are illustrated with **gpt-image-2** images (generated once, cached, then rendered deterministically as Ken-Burns scenes with narration + captions). The default stays free and faithful; AI imagery is **decorative/conceptual** (faithful-decorative) with a full-AI escape hatch, and the **critic** is extended to police it.

**Verified facts (web, Jun 2026):** OpenAI `gpt-image-2` (released Apr 21 2026), standard endpoint `POST https://api.openai.com/v1/images/generations`, JSON `{model:"gpt-image-2", prompt, size, quality, n}`, returns base64 PNG (`data[0].b64_json`), sizes up to 2048×2048 (landscape available, e.g. `1536x1024`), token-based pricing (~$0.01–0.21/image by quality/size). Mirror the existing `tts._openai` provider (lazy `requests`, `OPENAI_API_KEY`, graceful fallback).

**Goals**
1. A reusable `imagegen.py` that turns a per-scene prompt into a **cached** PNG via gpt-image-2, mirroring the openai TTS provider.
2. A runtime **choice** (free vs gpt-image), key prompt, and **style/focus** selection.
3. AI images render through the **existing slide Ken-Burns path** (one small `cover`-fit addition) — no render rewrite.
4. **Cost control** (estimate + confirm, medium quality, one image/scene, cached) and **graceful fallback** to free when no key / API error.
5. **Faithfulness**: faithful-decorative default (data stays in real charts); full `{motif|broll|asserted}` policy + critic **R1e** extended to AI images.

**Non-goals (YAGNI):** image editing/inpainting, multiple images per scene / AI video models, non-OpenAI image providers, per-frame generation. Determinism of *generation* is not attempted (it's inherently non-deterministic) — determinism is achieved by **caching** the generated PNG and rendering from it.

## Decisions (from brainstorming)
- **Faithful-decorative default:** AI for visual/conceptual scenes (title, dividers, mood/b-roll); real DATA stays in `chart` scenes. `meta.image_source:"openai"` full-AI is an explicit escape hatch the critic warns on.
- **Prompts: I author, user signs off** — every per-scene prompt is shown for approval before any paid generation.
- **Cost: estimate + confirm, `quality:"medium"`, one image per scene, cached** (re-renders free).

## Architecture

A new image-source tier parallel to the TTS provider tier. Generation is a **one-time paid pre-step** (`imagegen.py`, sibling to `tts.py`) that fills each AI scene's `image` with a cached PNG; **`render.py` then renders it as an ordinary slide** (fit → Ken Burns → captions → TTS mux → concat). Pipeline order: ingest/author → **imagegen** (fills `image`) → tts (fills `audio`/`duration`) → render.

### Component 1 — `scripts/imagegen.py` (new)
- `generate(prompt, out_path, key, size="1536x1024", quality="medium", model="gpt-image-2")` — lazy `import requests`; `POST /v1/images/generations` with `{model, prompt, size, quality, n:1}` + `Authorization: Bearer <key>`; decode `data[0].b64_json` → write PNG to `out_path`. Mirrors `tts._openai`.
- **Cache:** `_cache_path(out_dir, prompt, model, size, quality)` = `out_dir/.assets/<sha1(model|size|quality|prompt)>.png`; a sidecar `<sha1>.json` manifest (`{prompt, model, size, quality, tag, date}` — date passed in, never `datetime.now()` in render). If the cached PNG exists, **skip the API call** (free, offline re-gen).
- `cost_estimate(n, quality, size) -> float` — rough per-image table (`low≈$0.01, medium≈$0.04, high≈$0.17` at landscape; adjustable constants) × n, for the confirm step.
- `synthesize_images(out_dir, key=None, date="")` — load storyboard; for each scene with a non-empty `image_prompt` and no cached `image`, generate+cache and set `scene["image"]` to the cached path (relative to out_dir). Key from arg or `OPENAI_API_KEY`. On no key / API error: leave `image` unset, print a notice, and mark the scene for **free-tier fallback** (the workflow converts it back to a programmatic/slide scene). Save storyboard.
- CLI: `python imagegen.py <out_dir> [--quality medium] [--size 1536x1024]` — the paid pre-step; prints `n images, est $X` and which were cache-hits.

### Component 2 — schema (`scripts/storyboard.py`)
An AI scene is a **`slide`** with a prompt (reuses Ken Burns + concat + captions):
- `meta`: `image_source ∈ {"none"(default), "openai"}`, `image_style`(str, e.g. "cinematic"), `image_quality ∈ {"low","medium","high"}` (default "medium"), `image_size`(str, default "1536x1024").
- scene (slide): optional `image_prompt`(str), `image_tag ∈ {"motif","broll","asserted"}` (default "broll"), `fit ∈ {"contain"(default),"cover"}` (AI scenes use "cover"), and `image` (filled by imagegen; may be null pre-generation when `image_prompt` is set).
- `validate`: a `slide` may have `image` null **only if** `image_prompt` is set (a pending-generation scene); otherwise `slide` still requires `image` (back-compat). `image_tag`/`fit`/`image_source`/`image_quality` validated against their enums when present. `chart`/`timeline`/`title` unchanged.

### Component 3 — render (`scripts/render.py`, one small addition)
- `_fit_frame(src, dst, W, H, fit="contain")`: add a `cover` mode — scale to **cover** (`max` ratio) then center-crop to `W×H` (full-frame, no letterbox) — used for AI b-roll. `contain` is the existing letterbox (default, unchanged).
- `_render_slide` passes `slide.get("fit","contain")` to `_fit_frame`. If a slide has `image_prompt` but `image` is still null at render time, raise a clear `StoryboardError` ("run imagegen.py first"). Everything else unchanged.

### Component 4 — workflow (`SKILL.md`)
- **Interview** gains an **image source** choice: *Free (programmatic / slides)* (default) vs *gpt-image (OpenAI, paid — needs `OPENAI_API_KEY`)*. If gpt-image: prompt for the key (env or paste), and ask **style** (menu: photoreal · cinematic · editorial illustration · 3D render · watercolor · blueprint/diagram · minimal flat · free-text) + **focus**. Set `meta.image_source/style/quality/size`.
- **New steps** (between authoring and TTS): (a) author a **grounded per-scene `image_prompt`** (faithful-decorative: AI scenes tagged `broll`, data left as `chart`); (b) **critic** reviews prompts (R1e); (c) 🔴 **CHECKPOINT** — present all prompts + `cost_estimate` and get sign-off **before any spend**; (d) run `imagegen.py` (paid); (e) 🔴 sample sign-off; (f) full render. No key / API error ⇒ fall back to the free tier with a notice.
- **Guardrails / failure table:** add rows for *no OPENAI_API_KEY → free fallback* and *image API error → free fallback*; document `meta.image_source` and the cache.

### Component 5 — critic (`agents/critic.md` + SKILL.md policy)
Re-add the full **`{motif|broll|asserted}`** imagery policy (SKILL.md) and a critic rule **R1e — Imagery faithfulness**, covering AI images:
- `motif` (generic vector) — always allowed (Spec-1 territory; may be absent now).
- `broll` (generic illustrative image, incl. AI-generated) — allowed; must be **generic/atmospheric**, asserting no specific fact.
- `asserted` (imagery standing for a specific named vehicle/mission/person/event/figure) — for an AI image this is **misattribution** (the model invents it) → **FAIL** (R0-class).
- **Data must stay in faithful charts** — FAIL if numeric/data content is rendered as an AI image (garbled numbers).
- The critic checks each scene's `image_prompt` + `image_tag` against the **adjacent narration**: an AI b-roll beside general narration passes; an AI image beside a specific factual claim that implies it depicts that fact fails (relabel as generic or move the claim to a faithful element). Full-AI (`meta.image_source` with data scenes as AI) → the critic **flags** every data-bearing AI scene.

## Data contract example
```json
{ "meta": {"image_source": "openai", "image_style": "cinematic, dark, high-contrast",
           "image_quality": "medium", "image_size": "1536x1024", "language": "zh", "voice": "auto"} }

{ "index": 1, "type": "slide", "fit": "cover", "image_tag": "broll",
  "image_prompt": "A cinematic wide shot of a generic rocket silhouette rising over a dark horizon at dawn, volumetric light, no logos, no text",
  "image": null,
  "narration": "欢迎。我们来看商业航天发射市场的格局。" }

{ "index": 2, "type": "chart",
  "props": {"kind":"bars","title":"年发射次数","data":[{"label":"2022","value":61},{"label":"2025","value":165}]},
  "narration": "发射节奏快速攀升……" }
```
(Scene 1 = AI b-roll, full-frame Ken Burns; scene 2 = faithful chart, never AI.)

## Error handling
| Condition | Behavior |
|---|---|
| No `OPENAI_API_KEY` (and not passed) | `imagegen` prints a notice; affected scenes fall back to the free tier (programmatic/slide); no spend. |
| Image API error / rate limit | Catch per-image; notice; that scene falls back to free; other cached scenes unaffected. |
| Cached PNG present | Skip the API call (free, offline). |
| `image_tag:"asserted"` on an AI image | `validate` allows it but the critic FAILS it (R1e) — caught before render. |
| Slide has `image_prompt` but `image` null at render | `render` raises `StoryboardError` ("run imagegen.py first"). |
| gpt-image size ≠ 16:9 | `cover` fit center-crops to the canvas (full-frame). |

## Testing (all mocked — NO real API spend, NO network)
- **imagegen:** `_cache_path` is a stable sha1 of (model,size,quality,prompt); `generate` builds the correct request (mock `requests.post` → assert URL/model/prompt/size/quality and that b64 is decoded+written); `synthesize_images` fills `scene["image"]` from cache and SKIPS the API when cached (mock asserts no second call); no-key ⇒ graceful fallback (no exception, scene left for free tier); `cost_estimate` monotonic in quality.
- **schema:** AI slide (`image_prompt` + `image:null`) validates; a plain slide with no image still rejected; `image_tag`/`fit`/`image_source`/`image_quality` enums validated; `chart` unchanged.
- **render:** `_fit_frame(..., fit="cover")` outputs exactly W×H with no black bars (cover); `contain` unchanged (existing tests); a slide with `image_prompt` and null `image` raises at render.
- **critic:** prose — grep R1e + the policy; verified by reading.
- Existing render/tts/scenes/storyboard tests stay green.

## Out of scope / future
Non-OpenAI image providers, image editing/variation, AI video, per-frame generation, automatic prompt-from-GPT expansion (the `image_prompt` is author-written + user-approved in this spec; a GPT-expands-brief mode can be a later option).
