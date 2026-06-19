# gpt-image Generation Tier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in OpenAI **gpt-image-2** image tier to the slides-to-video skill — AI images become Ken-Burns scenes, generated once, cached, then rendered deterministically — with cost control, graceful fallback to the free tier, and a critic rule that keeps AI imagery faithful (decorative b-roll, never asserting specific facts).

**Architecture:** A new `imagegen.py` (sibling to `tts.py`, mirroring its `openai:` provider) is a one-time paid pre-step that fills each AI scene's `image` with a cached PNG; `render.py` then renders it as an ordinary `slide` (one small `cover`-fit addition). An AI scene is a `slide` carrying an `image_prompt`. `render.py`/render dispatch are otherwise untouched.

**Tech Stack:** Python 3, `requests` (lazy import, already used by `tts._openai`), Pillow, ffmpeg, pytest. No new hard dependency.

## Global Constraints
- Mirror `tts._openai`: lazy `import requests`, `OPENAI_API_KEY`, **graceful fallback to the free tier** on no-key / API error (never crash the pipeline).
- gpt-image-2 facts: `POST https://api.openai.com/v1/images/generations`, JSON `{model:"gpt-image-2", prompt, size, quality, n:1}`, response `data[0].b64_json` (base64 PNG). Default `size="1536x1024"`, `quality="medium"`.
- **Determinism by caching:** generation is non-deterministic; cache the PNG at `out_dir/.assets/<sha1(model|size|quality|prompt)>.png` so re-renders are free + offline. No `datetime.now()` / `random` in any code path (dates are passed in).
- **Faithful-decorative default:** AI images are `broll` (generic/atmospheric); real DATA stays in `chart` scenes. `meta.image_source:"openai"` full-AI is an explicit escape hatch the critic warns on.
- **Cost control:** one image per scene; `cost_estimate` shown before spend (workflow checkpoint); cached re-renders free.
- **Backward compatible:** `meta.image_source` defaults to absent/`"none"` (free tier, current behavior); a normal `slide` still requires `image`; existing tests stay green.
- Tests are fully **mocked** — NO real API spend, NO network.

---

### Task 1: `imagegen.py` — `generate` + cache key + `cost_estimate`

**Files:**
- Create: `scripts/imagegen.py`
- Test: `tests/test_imagegen.py` (new)

**Interfaces (Produces):**
- `API_URL`, `DEFAULT_MODEL="gpt-image-2"`
- `_cache_key(prompt, model, size, quality) -> str`; `_cache_path(out_dir, prompt, model, size, quality) -> str`
- `cost_estimate(n, quality="medium", size="1536x1024") -> float`
- `generate(prompt, out_path, key, size="1536x1024", quality="medium", model=DEFAULT_MODEL) -> None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_imagegen.py`:
```python
import os, sys, json, base64, types
import imagegen

# a 1x1 PNG, base64 (used as the fake API payload)
_PNG_B64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYGAAAAAEAAH2FzhV" "AAAAAElFTkSuQmCC")

def test_cache_key_stable_and_varies():
    a = imagegen._cache_key("a rocket", "gpt-image-2", "1536x1024", "medium")
    assert a == imagegen._cache_key("a rocket", "gpt-image-2", "1536x1024", "medium")
    assert a != imagegen._cache_key("a rocket", "gpt-image-2", "1536x1024", "high")
    assert a != imagegen._cache_key("a planet", "gpt-image-2", "1536x1024", "medium")

def test_cache_path_under_assets(tmp_path):
    p = imagegen._cache_path(str(tmp_path), "x", "gpt-image-2", "1536x1024", "medium")
    assert os.path.dirname(p).endswith(".assets") and p.endswith(".png")

def test_cost_estimate_monotonic():
    assert imagegen.cost_estimate(1, "low") < imagegen.cost_estimate(1, "medium") < imagegen.cost_estimate(1, "high")
    assert imagegen.cost_estimate(4, "medium") == round(4 * imagegen.cost_estimate(1, "medium"), 3)

def test_generate_builds_request_and_writes(tmp_path, monkeypatch):
    captured = {}
    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"data": [{"b64_json": _PNG_B64}]}
    fake = types.ModuleType("requests")
    def post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, body=json); return _Resp()
    fake.post = post
    monkeypatch.setitem(sys.modules, "requests", fake)
    out = str(tmp_path / "img.png")
    imagegen.generate("a generic rocket", out, "sk-test", size="1536x1024", quality="medium")
    assert captured["url"] == imagegen.API_URL
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["body"]["model"] == "gpt-image-2"
    assert captured["body"]["prompt"] == "a generic rocket"
    assert captured["body"]["size"] == "1536x1024" and captured["body"]["quality"] == "medium"
    assert captured["body"]["n"] == 1
    assert os.path.exists(out) and open(out, "rb").read()[:4] == b"\x89PNG"

def test_generate_no_key_raises(tmp_path):
    import pytest
    with pytest.raises(RuntimeError):
        imagegen.generate("x", str(tmp_path / "y.png"), "", )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/donghanglyu/.claude/skills/slides-to-video && python3 -m pytest tests/test_imagegen.py -v`
Expected: FAIL (`No module named 'imagegen'`).

- [ ] **Step 3: Write minimal implementation**

Create `scripts/imagegen.py`:
```python
"""gpt-image-2 image generation + deterministic cache. Mirrors tts._openai (lazy requests,
OPENAI_API_KEY, graceful fallback). Generation is non-deterministic, so we cache each PNG by
a sha1 of (model,size,quality,prompt) -> re-renders are free and offline."""
import argparse, base64, hashlib, json, os
import storyboard as sb

API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = "gpt-image-2"
# rough per-image USD by quality at landscape — for the confirm step, NOT a list price.
_COST = {"low": 0.01, "medium": 0.04, "high": 0.17}

def _cache_key(prompt, model, size, quality):
    return hashlib.sha1(f"{model}|{size}|{quality}|{prompt}".encode("utf-8")).hexdigest()[:16]

def _cache_path(out_dir, prompt, model, size, quality):
    return os.path.join(out_dir, ".assets", _cache_key(prompt, model, size, quality) + ".png")

def cost_estimate(n, quality="medium", size="1536x1024"):
    return round(n * _COST.get(quality, 0.04), 3)

def generate(prompt, out_path, key, size="1536x1024", quality="medium", model=DEFAULT_MODEL):
    """Generate ONE image via gpt-image-2 and write a PNG to out_path.
    Raises RuntimeError if no key; raises on HTTP error (caller catches for fallback)."""
    import requests
    if not key:
        raise RuntimeError("no OPENAI_API_KEY")
    r = requests.post(API_URL,
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "prompt": prompt, "size": size,
                            "quality": quality, "n": 1},
                      timeout=180)
    r.raise_for_status()
    b64 = r.json()["data"][0]["b64_json"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_imagegen.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/imagegen.py tests/test_imagegen.py
git commit -m "feat(imagegen): gpt-image-2 generate + sha1 cache key + cost estimate"
```

---

### Task 2: `imagegen.py` — `synthesize_images` + CLI

**Files:**
- Modify: `scripts/imagegen.py` (add `synthesize_images` + `main`)
- Test: `tests/test_imagegen.py`

**Interfaces:**
- Consumes: `generate`, `_cache_path`, `cost_estimate` (Task 1); `storyboard.load/save`.
- Produces: `synthesize_images(out_dir, key=None, date="") -> dict` (fills each pending scene's `image` from cache/generation; sets nothing for failures); `main()`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_imagegen.py`:
```python
import storyboard as sb

def _board(tmp_path, source="openai", prompt="a generic rocket"):
    out = tmp_path / "proj"; os.makedirs(out, exist_ok=True)
    d = sb.new_storyboard({"image_source": source, "image_quality": "medium", "image_size": "1536x1024"})
    s = sb.new_slide(1, None); s["image"] = None; s["image_prompt"] = prompt; s["image_tag"] = "broll"
    s["narration"] = "intro"
    d["slides"] = [s]
    sb.save(d, os.path.join(out, "storyboard.json"))
    return str(out)

def test_synthesize_noop_when_free(tmp_path, monkeypatch):
    out = _board(tmp_path, source="none")
    called = {"n": 0}
    monkeypatch.setattr(imagegen, "generate", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    imagegen.synthesize_images(out, key="sk-x")
    assert called["n"] == 0          # free tier -> no generation

def test_synthesize_generates_and_fills_image(tmp_path, monkeypatch):
    out = _board(tmp_path)
    def fake_gen(prompt, path, key, size, quality, model):
        os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "wb").write(b"\x89PNG")
    monkeypatch.setattr(imagegen, "generate", fake_gen)
    d = imagegen.synthesize_images(out, key="sk-x", date="2026-06-19")
    s = d["slides"][0]
    assert s["image"] and s["image"].startswith(".assets/") and s["image"].endswith(".png")
    assert os.path.exists(os.path.join(out, s["image"]))

def test_synthesize_uses_cache_skips_api(tmp_path, monkeypatch):
    out = _board(tmp_path)
    # pre-create the cache file so generate must NOT be called
    cp = imagegen._cache_path(out, "a generic rocket", imagegen.DEFAULT_MODEL, "1536x1024", "medium")
    os.makedirs(os.path.dirname(cp), exist_ok=True); open(cp, "wb").write(b"\x89PNG")
    called = {"n": 0}
    monkeypatch.setattr(imagegen, "generate", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    d = imagegen.synthesize_images(out, key="sk-x")
    assert called["n"] == 0 and d["slides"][0]["image"].endswith(".png")

def test_synthesize_no_key_falls_back(tmp_path, monkeypatch):
    out = _board(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    d = imagegen.synthesize_images(out, key=None)   # no key -> generate raises -> caught
    assert d["slides"][0]["image"] is None           # left for free-tier fallback, no crash
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_imagegen.py -k synthesize -v`
Expected: FAIL (`synthesize_images` undefined).

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/imagegen.py`:
```python
def synthesize_images(out_dir, key=None, date=""):
    path = os.path.join(out_dir, "storyboard.json")
    data = sb.load(path)
    meta = data["meta"]
    if meta.get("image_source") != "openai":
        return data                                    # free tier — nothing to generate
    key = key or os.environ.get("OPENAI_API_KEY")
    size = meta.get("image_size", "1536x1024")
    quality = meta.get("image_quality", "medium")
    model = DEFAULT_MODEL
    pending = [s for s in data["slides"]
               if (s.get("image_prompt") or "").strip() and not s.get("image")]
    made = cached = failed = 0
    for s in pending:
        prompt = s["image_prompt"]
        cp = _cache_path(out_dir, prompt, model, size, quality)
        rel = os.path.relpath(cp, out_dir)
        if os.path.exists(cp):                          # cache hit — free, offline
            s["image"] = rel; cached += 1; continue
        try:
            generate(prompt, cp, key, size, quality, model)
            with open(cp[:-4] + ".json", "w") as f:     # manifest sidecar
                json.dump({"prompt": prompt, "model": model, "size": size, "quality": quality,
                           "tag": s.get("image_tag", "broll"), "date": date}, f, indent=2)
            s["image"] = rel; made += 1
        except Exception as e:
            print(f"[imagegen] scene {s['index']} failed ({e}); leaving for free-tier fallback")
            failed += 1
    sb.save(data, path)
    print(f"[imagegen] generated {made}, cache-hit {cached}, fallback {failed}; "
          f"est ${cost_estimate(made, quality, size)}")
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--key", default=None)
    a = ap.parse_args()
    synthesize_images(a.out_dir, a.key)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_imagegen.py -v`
Expected: PASS (all imagegen tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/imagegen.py tests/test_imagegen.py
git commit -m "feat(imagegen): synthesize_images fills cached AI scene images + CLI + fallback"
```

---

### Task 3: storyboard schema — image fields + relaxed slide validation

**Files:**
- Modify: `scripts/storyboard.py`
- Test: `tests/test_storyboard.py`

**Interfaces:**
- Produces: `VALID_IMAGE_SOURCES`, `VALID_IMAGE_TAGS`, `VALID_FITS`, `VALID_IMAGE_QUALITIES`; `validate` accepts a `slide` with `image_prompt` + null `image`, validates the new optional fields + meta image keys.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_storyboard.py`:
```python
def _ai_slide():
    s = sb.new_slide(1, None); s["image"] = None
    s["image_prompt"] = "a generic rocket"; s["image_tag"] = "broll"; s["fit"] = "cover"
    s["narration"] = "n"
    return s

def test_validate_ai_slide_prompt_no_image_ok():
    sb.validate({"meta": {"image_source": "openai"}, "slides": [_ai_slide()]})

def test_validate_slide_needs_image_or_prompt():
    bad = sb.new_slide(1, None); bad["image"] = None  # no image, no prompt
    with pytest.raises(sb.StoryboardError):
        sb.validate({"meta": {}, "slides": [bad]})

def test_validate_bad_image_enums():
    for field, val in [("image_tag", "weird"), ("fit", "stretch")]:
        s = _ai_slide(); s[field] = val
        with pytest.raises(sb.StoryboardError):
            sb.validate({"meta": {"image_source": "openai"}, "slides": [s]})
    with pytest.raises(sb.StoryboardError):
        sb.validate({"meta": {"image_source": "satellite"}, "slides": [_ai_slide()]})
    with pytest.raises(sb.StoryboardError):
        sb.validate({"meta": {"image_source": "openai", "image_quality": "ultra"}, "slides": [_ai_slide()]})

def test_validate_plain_slide_still_ok():
    sb.validate({"meta": {}, "slides": [sb.new_slide(1, "frames/01.png")]})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_storyboard.py -k "ai_slide or image or enum or plain_slide" -v`
Expected: FAIL (AI slide with null image rejected by current `validate`; new enum checks absent).

- [ ] **Step 3: Write minimal implementation**

In `scripts/storyboard.py`, add constants after line 10:
```python
VALID_IMAGE_SOURCES = {"none", "openai"}
VALID_IMAGE_TAGS = {"motif", "broll", "asserted"}
VALID_FITS = {"contain", "cover"}
VALID_IMAGE_QUALITIES = {"low", "medium", "high"}
```
Replace the `slide` branch in `validate` (lines 90-92) with:
```python
        if t == "slide":
            has_img = bool(s.get("image"))
            has_prompt = bool((s.get("image_prompt") or "").strip())
            if not has_img and not has_prompt:
                raise StoryboardError(f"slide {s.get('index')}: type 'slide' requires 'image' or 'image_prompt'")
```
Add per-scene optional-field checks inside the `for s in data["slides"]:` loop (after the type/props branch, before the callout loop):
```python
        if "image_tag" in s and s["image_tag"] not in VALID_IMAGE_TAGS:
            raise StoryboardError(f"slide {s.get('index')}: image_tag must be one of {VALID_IMAGE_TAGS}")
        if "fit" in s and s["fit"] not in VALID_FITS:
            raise StoryboardError(f"slide {s.get('index')}: fit must be one of {VALID_FITS}")
```
Add meta checks at the top of `validate`, right after the `meta`/`slides` presence check:
```python
    m = data["meta"]
    if m.get("image_source") not in (None, *VALID_IMAGE_SOURCES):
        raise StoryboardError(f"meta.image_source must be one of {VALID_IMAGE_SOURCES}")
    if "image_quality" in m and m["image_quality"] not in VALID_IMAGE_QUALITIES:
        raise StoryboardError(f"meta.image_quality must be one of {VALID_IMAGE_QUALITIES}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_storyboard.py -v`
Expected: PASS (new + existing).

- [ ] **Step 5: Commit**

```bash
git add scripts/storyboard.py tests/test_storyboard.py
git commit -m "feat(storyboard): image_prompt/tag/fit + meta image_source/quality; slide accepts prompt-without-image"
```

---

### Task 4: render — `cover` fit + AI-scene guard

**Files:**
- Modify: `scripts/render.py` (`_fit_frame` line 82-88; `_render_slide` line 297-299)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `storyboard as sb` (already imported in render.py).
- Produces: `_fit_frame(src, dst, W, H, fit="contain")`; `_render_slide` honors `slide["fit"]` and guards null AI images.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_render.py`:
```python
def test_fit_frame_cover_fills_no_letterbox(tmp_path):
    from PIL import Image
    src = str(tmp_path / "s.png"); dst = str(tmp_path / "d.png")
    Image.new("RGB", (100, 100), (200, 80, 20)).save(src)   # square, non-black
    render._fit_frame(src, dst, 200, 100, fit="cover")       # target 2:1
    im = Image.open(dst).convert("RGB")
    assert im.size == (200, 100)
    # left & right edge columns are image content (no black letterbox bars)
    assert im.getpixel((0, 50)) != (0, 0, 0) and im.getpixel((199, 50)) != (0, 0, 0)

def test_fit_frame_contain_unchanged(tmp_path):
    from PIL import Image
    src = str(tmp_path / "s.png"); dst = str(tmp_path / "d.png")
    Image.new("RGB", (100, 100), (200, 80, 20)).save(src)
    render._fit_frame(src, dst, 200, 100)                    # default contain
    im = Image.open(dst).convert("RGB")
    assert im.size == (200, 100)
    assert im.getpixel((0, 50)) == (0, 0, 0)                 # letterbox bar present

def test_render_slide_ungenerated_ai_image_raises(tmp_path):
    s = sb.new_slide(1, None); s["image"] = None; s["image_prompt"] = "x"
    s["audio"] = "audio/01.aiff"; s["duration"] = 2.0
    meta = {"_out": str(tmp_path), "fps": 30}
    with pytest.raises(sb.StoryboardError):
        render._render_slide(s, meta, 1920, 1080, str(tmp_path / "c.mp4"), False, str(tmp_path))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_render.py -k "fit_frame or ungenerated" -v`
Expected: FAIL (`_fit_frame` has no `fit` arg → TypeError; no guard → tries `_fit_frame(None…)`).

- [ ] **Step 3: Write minimal implementation**

In `scripts/render.py`, replace `_fit_frame` (lines 82-88) with:
```python
def _fit_frame(src, dst, W, H, fit="contain"):
    """Scale a slide image onto a WxH canvas. contain = letterbox (default); cover = scale to
    fill then center-crop (full-frame, for AI b-roll)."""
    im = Image.open(src).convert("RGB")
    if fit == "cover":
        scale = max(W / im.width, H / im.height)
        nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
        im = im.resize((nw, nh), Image.LANCZOS)
        left, top = (nw - W) // 2, (nh - H) // 2
        im.crop((left, top, left + W, top + H)).save(dst)
        return
    im.thumbnail((W, H), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), (0, 0, 0))
    bg.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    bg.save(dst)
```
In `_render_slide`, replace lines 297-299 (`i = slide["index"]` … the `_fit_frame(...)` call) with:
```python
    i = slide["index"]
    if (slide.get("image_prompt") or "").strip() and not slide.get("image"):
        raise sb.StoryboardError(f"slide {i}: image_prompt set but image not generated — run imagegen.py first")
    frame = os.path.join(workdir, f"fit_{i:02d}.png")
    _fit_frame(os.path.join(meta["_out"], slide["image"]), frame, W, H, slide.get("fit", "contain"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_render.py -v`
Expected: PASS (new + existing render tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/render.py tests/test_render.py
git commit -m "feat(render): cover-fit for full-frame images + guard for ungenerated AI scenes"
```

---

### Task 5: SKILL.md — image-source interview, workflow steps, guardrails

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Add `imagegen.py` to Pipeline scripts**

In `SKILL.md` `## Pipeline scripts`, add after the `tts.py` bullet:
```markdown
- `scripts/imagegen.py <out_dir> [--key KEY]` — OPTIONAL paid tier: generate AI scene images
  via OpenAI `gpt-image-2` for scenes that carry an `image_prompt`, cached under `.assets/`
  (re-runs are free). Only acts when `meta.image_source == "openai"`; needs `OPENAI_API_KEY`.
```

- [ ] **Step 2: Add the image-source interview choice**

In `SKILL.md` Workflow step 1 (Interview), add after the voice clause:
```markdown
   image source — **Free** (programmatic animation / slides, the default) vs **gpt-image**
   (OpenAI `gpt-image-2`, **paid**, needs `OPENAI_API_KEY`). If gpt-image: ask for the key (env
   or paste), and ask a **style** (photoreal · cinematic · editorial illustration · 3D render ·
   watercolor · blueprint/diagram · minimal flat · or free-text) + a **focus** (subject emphasis).
   Set `meta.image_source`/`image_style`/`image_quality`(default medium)/`image_size`(default
   1536x1024). Default stays Free — AI imagery is opt-in and costs money.
```

- [ ] **Step 3: Add the gpt-image workflow + checkpoint**

In `SKILL.md`, after step 4 (Author narration) add a new step (renumber following steps or insert as step 4b):
```markdown
4b. **Image prompts (gpt-image tier only).** If `meta.image_source == "openai"`: for each
    VISUAL/conceptual scene, author a grounded `image_prompt` from the narration + the chosen
    style, tagged `image_tag:"broll"` and `fit:"cover"`; keep DATA in `chart` scenes (never AI).
    Generic/atmospheric prompts only — no real logos, faces, named vehicles, or text in-image.
    The critic (step 5, R1e) reviews the prompts.
    🔴 **CHECKPOINT · 🛑 STOP:** present every prompt + the estimated cost
    (`imagegen.cost_estimate(n, quality)`) and get sign-off BEFORE spending. Then run
    `imagegen.py <out_dir>` (the paid step; cached after). No key / API error → fall back to the
    free tier (drop `image_prompt`, use programmatic/slide) and tell the user.
```

- [ ] **Step 4: Guardrails + failure table**

In `SKILL.md` `## Guardrails`, add:
```markdown
- `meta.image_source` is `none` (default, free) or `openai` (gpt-image-2, paid). AI images are
  generated once by `imagegen.py` and CACHED under `.assets/` — re-renders are free + offline.
```
In the `## When a step fails` table, add:
```markdown
| `imagegen.py`: no `OPENAI_API_KEY` | It prints a notice and leaves those scenes for free-tier fallback — convert them to programmatic/slide and continue | Set the key (`export OPENAI_API_KEY=...`) and re-run `imagegen.py` |
| `imagegen.py`: image API error / rate limit | Per-scene catch → free-tier fallback for that scene; cached scenes unaffected | Retry later; cached images never re-charge |
```

- [ ] **Step 5: Verify + commit**

Run: `grep -n "imagegen\|image source\|image_source\|gpt-image" SKILL.md` (expect matches in Pipeline scripts, step 1, step 4b, Guardrails, failure table).
```bash
git add SKILL.md
git commit -m "docs(skill): gpt-image tier — interview choice, prompt+cost checkpoint, guardrails"
```

---

### Task 6: critic — imagery faithfulness policy + R1e

**Files:**
- Modify: `agents/critic.md`
- Modify: `SKILL.md` (imagery-faithfulness policy section)

- [ ] **Step 1: Add the SKILL.md imagery-faithfulness policy**

In `SKILL.md`, after the `## Guardrails` section, add:
```markdown
## Imagery faithfulness (AI / b-roll)
Every on-screen visual is one of three classes; the critic (R1e) enforces them:
- **`motif`** — a generic programmatic vector. Always allowed; asserts no fact.
- **`broll`** — a generic illustrative image, including an AI-generated one (`image_prompt`).
  Allowed ONLY as generic/atmospheric backdrop — no real logos, faces, named vehicles, or
  in-image text, and it must not sit as "evidence" beside a specific factual claim.
- **`asserted`** — imagery standing in for a specific named vehicle/mission/person/event/figure.
  For an AI image this is FABRICATION (the model invents it) and is NOT allowed.
DATA always stays in faithful `chart` scenes — never render numbers/figures as an AI image.
The full-AI escape hatch (`image_source:"openai"` with data as AI) is the user's call, but the
critic flags every data-bearing AI scene.
```

- [ ] **Step 2: Add critic rule R1e**

In `agents/critic.md`, after R1d (and reusing the `meta.voice`/inputs context), add:
```markdown
### R1e — Imagery faithfulness (motifs / AI b-roll)
A scene may carry an `image_prompt` (AI-generated image, `image_tag` one of motif/broll/asserted)
or be a programmatic motif. Classes (see SKILL.md "Imagery faithfulness"):
- `motif` / `broll`: PASS when GENERIC/atmospheric. **FAIL** if the prompt names or depicts a
  specific real vehicle/mission/person/company logo/insignia or embeds factual text/numbers, or
  if the image sits beside a specific claim implying it depicts that fact (it doesn't — the model
  invented it). Relabel as generic or move the claim to a faithful element (chart/caption).
- `asserted` AI imagery → **FAIL** (R0-class misattribution; a generated image is not the real
  thing).
- **FAIL** if data/numbers are rendered as an AI image instead of a faithful `chart`.
Cross-ref R1d (animated on-screen values). When `meta.image_source == "openai"`, scan every
scene's `image_prompt` against the adjacent `narration`.
```

- [ ] **Step 3: Verify + full suite + commit**

Run:
```bash
grep -n "Imagery faithfulness\|R1e\|asserted" SKILL.md agents/critic.md
python3 -m pytest -q
```
Expected: grep shows the new content in both files; full suite PASSES.
```bash
git add agents/critic.md SKILL.md
git commit -m "docs: imagery faithfulness policy + critic R1e (AI b-roll vs asserted; data stays charts)"
```

---

## Self-Review

**Spec coverage:** `imagegen.generate`+cache+cost (Task 1) ✓; `synthesize_images`+CLI+fallback (Task 2) ✓; schema image fields + prompt-without-image (Task 3) ✓; `cover` fit + render guard (Task 4) ✓; interview choice + style/focus + cost/prompt checkpoint + guardrails/failure (Task 5) ✓; `{motif|broll|asserted}` policy + critic R1e (Task 6) ✓; faithful-decorative (broll default, data stays charts — Tasks 3/5/6) ✓; cache-determinism + graceful fallback + no real spend in tests (Tasks 1/2) ✓. Spec non-goals (image edit, AI video, non-OpenAI, per-frame) correctly have NO task.

**Placeholder scan:** none — every code/test step has runnable content; the `_PNG_B64` constant and mock-`requests` pattern give real, network-free coverage.

**Type consistency:** `generate(prompt, out_path, key, size, quality, model)` is defined in Task 1 and `synthesize_images` (Task 2) calls it positionally with that exact arity (the Task-2 mock `fake_gen` matches). `_cache_path(out_dir, prompt, model, size, quality)` is used identically in Task 2's cache-hit test. `meta.image_source=="openai"` is the single gate across Tasks 2/5/6. `image_prompt`/`image_tag`/`fit` field names match across schema (Task 3), render guard (Task 4), and critic (Task 6).
