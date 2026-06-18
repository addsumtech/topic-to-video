# Animated Scene Types (Phase 0/1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local/free/deterministic animated scene types (`title`, `chart`, `timeline`) to the slides-to-video skill so frames can be authored animation, not slide screenshots — slotting into the existing per-scene-clip → ffmpeg-concat → TTS pipeline with full backward compatibility.

**Architecture:** `render._render_slide` becomes a dispatcher on `scene["type"]`. Animated types render a deterministic PNG frame sequence (PIL for `title`, matplotlib-Agg for `chart`/`timeline`) into the shared workdir, then a new `_encode_frames_clip` muxes it with the scene's TTS audio + the same timed caption overlays through the skill's exact libx264/aac/yuv420p encode command — so `-c copy` concat and the clip cache are unaffected. Slides (`type:"slide"`, the default) take the existing path unchanged.

**Tech Stack:** Python 3, Pillow (installed), matplotlib 3.10 Agg (installed), ffmpeg 8.1.1, pytest. No new dependencies.

## Global Constraints

- LOCAL & FREE only — use Pillow + matplotlib (both already installed); add NO new dependency.
- DETERMINISTIC — renderers use NO `random`/`Math.random`, NO wall-clock; animation is a pure function of frame index `i in [0, frames)`. matplotlib uses the `Agg` backend with fixed figsize/DPI and fixed axis limits. (Determinism tests compare PIL *pixel* bytes `Image.open(p).convert("RGB").tobytes()`, NOT raw file bytes, because PNG file headers can carry library metadata.)
- FAITHFUL BY CONSTRUCTION — scenes render ONLY explicit `props`; chart numbers come ONLY from the `data` array (validation rejects non-numeric values); no invented imagery.
- BACKWARD COMPATIBLE — `type` defaults to `"slide"`; `type=="slide"` still requires `image`; all existing storyboards/tests must render identically.
- CONCAT-SAFE — every animated clip is encoded with the SAME command params the slide path uses: `-r {fps} -pix_fmt yuv420p -c:v libx264 -c:a aac` at the same WxH, so `ffmpeg -f concat -c copy` still works.
- SHARED-WORKDIR SAFE — the full render reuses ONE tempdir for all scenes, so animated frame files MUST be namespaced by scene index: `scene_{index:02d}_%04d.png`.
- PACING FROM AUDIO — `duration` comes from `tts.py`/ffprobe; renderers receive a frame COUNT (`frames = max(1, round(duration*fps))`, the existing formula) and write exactly that many frames. Never guess timing.
- Scripts run with `scripts/` on `sys.path` (pytest `conftest.py` already does this); `render.py` imports `_common` and `storyboard as sb` as modules.

---

### Task 1: Schema — `type` + `props` fields, `new_scene`, per-type validation

**Files:**
- Modify: `scripts/storyboard.py` (`new_slide`, add `new_scene`, `validate`)
- Test: `tests/test_storyboard.py`

**Interfaces:**
- Produces: `new_slide(index, image, narration="", notes="")` (now also sets `type="slide"`, `props=None`); `new_scene(index, scene_type, props, narration="", notes="")`; `validate(data)` enforcing the type/props rules; module constants `VALID_SCENE_TYPES`, `ANIMATED_TYPES`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_storyboard.py`:
```python
def test_new_slide_defaults_type_slide():
    s = sb.new_slide(1, "frames/01.png")
    assert s["type"] == "slide" and s["props"] is None

def test_new_scene_roundtrip(tmp_path):
    sc = sb.new_scene(2, "title", {"title": "Hello"}, narration="Hi.")
    assert sc["type"] == "title" and sc["props"] == {"title": "Hello"} and sc["image"] is None
    p = tmp_path / "s.json"; sb.save({"meta": {}, "slides": [sc]}, str(p))
    assert sb.load(str(p))["slides"][0]["props"]["title"] == "Hello"

def _wrap(scene):
    return {"meta": {"aspect": "16:9"}, "slides": [scene]}

def test_validate_slide_still_requires_image():
    bad = _wrap({"index": 1, "type": "slide", "narration": "x"})  # no image
    with pytest.raises(sb.StoryboardError):
        sb.validate(bad)

def test_validate_unknown_type_rejected():
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap({"index": 1, "type": "hologram", "narration": "x", "props": {}}))

def test_validate_title_ok_and_requires_title_str():
    sb.validate(_wrap(sb.new_scene(1, "title", {"title": "T", "subtitle": "S"}, "n")))
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(sb.new_scene(1, "title", {"subtitle": "S"}, "n")))  # missing title

def test_validate_chart_numbers_only():
    ok = sb.new_scene(1, "chart", {"kind": "bars", "data": [{"label": "a", "value": 5}]}, "n")
    sb.validate(_wrap(ok))
    bad = sb.new_scene(1, "chart", {"kind": "bars", "data": [{"label": "a", "value": "five"}]}, "n")
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(bad))
    badkind = sb.new_scene(1, "chart", {"kind": "pie", "data": [{"label": "a", "value": 5}]}, "n")
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(badkind))

def test_validate_timeline_requires_events():
    sb.validate(_wrap(sb.new_scene(1, "timeline", {"events": [{"date": "2026", "label": "x"}]}, "n")))
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(sb.new_scene(1, "timeline", {"events": []}, "n")))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/donghanglyu/.claude/skills/slides-to-video && python3 -m pytest tests/test_storyboard.py -k "type or scene or chart or timeline or title" -v`
Expected: FAIL (`new_scene` missing; `validate` doesn't enforce new rules).

- [ ] **Step 3: Write minimal implementation**

In `scripts/storyboard.py`, update `new_slide` to include the new keys, add `new_scene`, the constants, and extend `validate`. Replace the existing `new_slide` and `validate` and add the rest:
```python
VALID_SCENE_TYPES = {"slide", "title", "chart", "timeline"}
ANIMATED_TYPES = {"title", "chart", "timeline"}
VALID_CHART_KINDS = {"bars", "line", "counter"}

def new_slide(index, image, narration="", notes=""):
    return {
        "index": index, "image": image, "narration": narration, "notes": notes,
        "type": "slide", "props": None,
        "audio": None, "duration": None,
        "motion": {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]},
        "callouts": [], "captions": [],
    }

def new_scene(index, scene_type, props, narration="", notes=""):
    return {
        "index": index, "image": None, "narration": narration, "notes": notes,
        "type": scene_type, "props": props,
        "audio": None, "duration": None,
        "motion": {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]},
        "callouts": [], "captions": [],
    }

def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)

def _validate_props(s):
    t = s["type"]; p = s.get("props")
    if not isinstance(p, dict):
        raise StoryboardError(f"slide {s.get('index')}: type '{t}' needs a props dict")
    if t == "title":
        if not (isinstance(p.get("title"), str) and p["title"].strip()):
            raise StoryboardError(f"slide {s.get('index')}: title scene needs non-empty 'title'")
    elif t == "chart":
        if p.get("kind") not in VALID_CHART_KINDS:
            raise StoryboardError(f"slide {s.get('index')}: chart 'kind' must be one of {VALID_CHART_KINDS}")
        data = p.get("data")
        if not isinstance(data, list) or not data:
            raise StoryboardError(f"slide {s.get('index')}: chart needs non-empty 'data' list")
        for d in data:
            if not isinstance(d, dict) or not _is_num(d.get("value")):
                raise StoryboardError(f"slide {s.get('index')}: every chart data item needs a numeric 'value'")
    elif t == "timeline":
        events = p.get("events")
        if not isinstance(events, list) or not events:
            raise StoryboardError(f"slide {s.get('index')}: timeline needs non-empty 'events' list")
        for e in events:
            if not (isinstance(e, dict) and isinstance(e.get("date"), str) and isinstance(e.get("label"), str)):
                raise StoryboardError(f"slide {s.get('index')}: every timeline event needs 'date' and 'label' strings")

def validate(data):
    if "meta" not in data or "slides" not in data:
        raise StoryboardError("storyboard needs 'meta' and 'slides'")
    if not data["slides"]:
        raise StoryboardError("storyboard has no slides")
    for s in data["slides"]:
        if "index" not in s or "narration" not in s:
            raise StoryboardError(f"slide missing 'index'/'narration': {s.get('index')}")
        t = s.get("type", "slide")
        if t not in VALID_SCENE_TYPES:
            raise StoryboardError(f"slide {s.get('index')}: unknown type '{t}'")
        if t == "slide":
            if "image" not in s or not s["image"]:
                raise StoryboardError(f"slide {s.get('index')}: type 'slide' requires 'image'")
        else:
            _validate_props(s)
        for co in s.get("callouts", []):
            box = co.get("box", [])
            if len(box) != 4 or not _in_unit(*box):
                raise StoryboardError(f"callout box must be 4 unit coords: {box}")
            if co.get("style") not in VALID_STYLES:
                raise StoryboardError(f"bad callout style: {co.get('style')}")
    return True
```
(Leave `new_storyboard`, `load`, `save`, `_in_unit`, `VALID_STYLES`, `StoryboardError` as-is.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_storyboard.py -v`
Expected: PASS (new tests + the pre-existing storyboard tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/storyboard.py tests/test_storyboard.py
git commit -m "feat(storyboard): scene type + props schema with per-type validation (animated scenes)"
```

---

### Task 2: Cache — `_fingerprint` hashes `type` + `props`

**Files:**
- Modify: `scripts/render.py` (`_fingerprint`, around line 251-253)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `render._fingerprint(slide, meta, W, H, ss, burn, vertical)` (existing signature, unchanged).
- Produces: fingerprint now varies with `type` and `props`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_render.py`:
```python
def test_fingerprint_includes_type_and_props():
    meta = {"_out": "/tmp", "fps": 30}
    base = {"index": 1, "image": None, "audio": None, "duration": 3.0, "motion": {},
            "narration": "n", "captions": [], "callouts": [], "type": "title",
            "props": {"title": "A"}}
    fp = lambda s: render._fingerprint(s, meta, 1920, 1080, 2, True, False)
    a = fp(base)
    b = fp({**base, "props": {"title": "B"}})       # prop change -> different
    c = fp({**base, "type": "chart", "props": {"kind": "bars", "data": [{"label":"x","value":1}]}})
    assert a != b and a != c and a == fp(dict(base))  # stable for identical input
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_render.py::test_fingerprint_includes_type_and_props -v`
Expected: FAIL (`a == b` because `type`/`props` aren't hashed).

- [ ] **Step 3: Write minimal implementation**

In `scripts/render.py` `_fingerprint`, add `type` and `props` to the hashed `s` tuple:
```python
    payload = json.dumps({
        "s": {k: slide.get(k) for k in
              ("image", "audio", "duration", "motion", "narration", "captions", "callouts",
               "type", "props")},
        "r": [W, H, meta.get("fps", 30), ss, burn, vertical,
              meta.get("language", "auto"), meta.get("font")],
        "img": stat(slide.get("image")), "aud": stat(slide.get("audio")),
    }, sort_keys=True, default=str)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_render.py::test_fingerprint_includes_type_and_props -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/render.py tests/test_render.py
git commit -m "feat(render): fingerprint hashes scene type+props so edits invalidate the clip cache"
```

---

### Task 3: `scenes.py` — frame-writer + `title` renderer (PIL, CJK-safe)

**Files:**
- Create: `scripts/scenes.py`
- Test: `tests/test_scenes.py` (new)

**Interfaces:**
- Consumes: `render._font_path(meta, text)` (existing CJK-aware font resolver).
- Produces: `_save_frames(draw_fn, frames, workdir, index) -> pattern_str` (writes `scene_{index:02d}_NNNN.png`, returns the `%04d` printf pattern path); `_ease(p) -> float` (smoothstep, clamped); `_hex_rgb(s) -> (r,g,b)`; `render_title(props, meta, W, H, frames, workdir, index) -> pattern_str`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scenes.py`:
```python
import os
from PIL import Image
import scenes

META = {"fps": 30, "language": "en"}
META_ZH = {"fps": 30, "language": "zh"}

def _pix(p):  # pixel bytes (metadata-independent determinism check)
    return Image.open(p).convert("RGB").tobytes()

def test_ease_clamped_monotonic():
    assert scenes._ease(-1) == 0.0 and scenes._ease(2) == 1.0
    assert scenes._ease(0.0) == 0.0 and scenes._ease(1.0) == 1.0
    assert scenes._ease(0.25) < scenes._ease(0.75)

def test_title_writes_exact_frames_and_nonblank(tmp_path):
    pat = scenes.render_title({"title": "Hello World", "subtitle": "A test"},
                              META, 1920, 1080, 12, str(tmp_path), 3)
    files = sorted(f for f in os.listdir(tmp_path) if f.endswith(".png"))
    assert len(files) == 12
    assert files[0] == "scene_03_0000.png"            # index-namespaced
    last = Image.open(pat % 11).convert("RGB")
    assert last.size == (1920, 1080)
    assert last.getextrema() != ((0,0),(0,0),(0,0))   # not all-black: text drawn
    assert "%04d" in pat

def test_title_deterministic(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    pa = scenes.render_title({"title": "Repeat"}, META, 640, 360, 6, str(a), 1)
    pb = scenes.render_title({"title": "Repeat"}, META, 640, 360, 6, str(b), 1)
    assert all(_pix(pa % i) == _pix(pb % i) for i in range(6))

def test_title_cjk_renders_glyphs(tmp_path):
    pat = scenes.render_title({"title": "进入商业航天发射市场"}, META_ZH, 1280, 720, 4, str(tmp_path), 1)
    last = Image.open(pat % 3).convert("RGB")
    assert last.getextrema() != ((0,0),(0,0),(0,0))   # CJK glyphs drawn (no blank/tofu-only)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_scenes.py -v`
Expected: FAIL (`No module named 'scenes'`).

- [ ] **Step 3: Write minimal implementation**

Create `scripts/scenes.py`:
```python
"""Deterministic animated scene renderers -> per-frame PNG sequences (no slides).
Each renderer is a PURE function of the frame index; no randomness, no wall-clock.
Frames are namespaced by scene index because the full render shares one workdir."""
import os
from PIL import Image, ImageDraw, ImageFont
import render  # reuse the CJK-aware font resolver

BG = (13, 17, 23)        # near-black, matches the caption aesthetic
FG = (255, 255, 255)

def _ease(p):
    """Smoothstep, clamped to [0,1]."""
    p = 0.0 if p < 0 else 1.0 if p > 1 else p
    return p * p * (3 - 2 * p)

def _hex_rgb(s):
    s = (s or "#E8590C").lstrip("#")
    return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))

def _save_frames(draw_fn, frames, workdir, index):
    pat = os.path.join(workdir, f"scene_{index:02d}_%04d.png")
    for i in range(frames):
        draw_fn(i, frames).save(pat % i)
    return pat

def _font(meta, text, size):
    try:
        return ImageFont.truetype(render._font_path(meta, text), size)
    except Exception:
        return ImageFont.load_default()

def render_title(props, meta, W, H, frames, workdir, index):
    title = props.get("title", "")
    subtitle = props.get("subtitle")
    kicker = props.get("kicker")
    accent = _hex_rgb(props.get("accent"))
    fps = meta.get("fps", 30)
    intro = max(1, int(0.8 * fps))                  # title fades/rises over ~0.8s
    sub_delay = max(1, int(0.35 * fps))
    tfont = _font(meta, title, int(H * 0.085))
    sfont = _font(meta, subtitle or " ", int(H * 0.040))
    kfont = _font(meta, kicker or " ", int(H * 0.028))
    x = int(W * 0.08)

    def draw(i, n):
        base = Image.new("RGBA", (W, H), BG + (255,))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        p = _ease(i / intro)
        a = int(255 * p); dy = int((1 - p) * (H * 0.03))
        # accent rule above the title
        rule_y = int(H * 0.34) + dy
        d.rectangle([x, rule_y, x + int(W * 0.10), rule_y + max(3, int(H * 0.008))],
                    fill=accent + (a,))
        d.text((x, int(H * 0.40) + dy), title, font=tfont, fill=FG + (a,))
        if subtitle:
            p2 = _ease((i - sub_delay) / intro)
            d.text((x, int(H * 0.56)), subtitle, font=sfont,
                   fill=(180, 190, 205, int(255 * p2)))
        if kicker:
            p3 = _ease((i - 2 * sub_delay) / intro)
            d.text((x, int(H * 0.72)), kicker, font=kfont,
                   fill=(140, 150, 165, int(255 * p3)))
        return Image.alpha_composite(base, layer).convert("RGB")

    return _save_frames(draw, frames, workdir, index)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/scenes.py tests/test_scenes.py
git commit -m "feat(scenes): deterministic title renderer (PIL, CJK-safe) + frame writer"
```

---

### Task 4: `render.py` — scene dispatcher + `_encode_frames_clip`

**Files:**
- Modify: `scripts/render.py` (`_render_slide` head: add dispatch; add `_render_scene` + `_encode_frames_clip`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `scenes.render_title` (Task 3); `render._captions_for`, `render._caption_layer` (existing); `_common.run`.
- Produces: `_render_scene(slide, meta, W, H, out_clip, burn_captions, workdir)`; `_encode_frames_clip(pattern, audio_rel, dur, caption_segs, meta, W, H, out_clip, workdir)`. `_render_slide` dispatches on `slide.get("type","slide")`.

- [ ] **Step 1: Write the failing test** (end-to-end; guarded by ffmpeg + say)

Add to `tests/test_render.py` (uses the existing `import` block: `ingest, tts, render, storyboard as sb, _common`):
```python
@pytest.mark.skipif(not _common.have_tool("ffmpeg") or not _common.have_tool("say"),
                    reason="needs ffmpeg + say")
def test_title_scene_renders_and_concats_with_slide(tmp_path, fixtures_dir, monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: False)   # offline-deterministic audio
    out = str(tmp_path / "proj")
    ingest.ingest(os.path.join(fixtures_dir, "deck.pdf"), out)   # gives >=1 real slide
    data = sb.load(os.path.join(out, "storyboard.json"))
    data["meta"]["voice"] = "say:Samantha"
    slide1 = data["slides"][0]; slide1["narration"] = "This is the slide."
    title = sb.new_scene(99, "title", {"title": "Title Scene", "subtitle": "Sub"},
                         narration="Welcome to the talk.")
    data["slides"] = [title, slide1]
    sb.save(data, os.path.join(out, "storyboard.json"))
    tts.synthesize(out)                                     # sets audio+duration for both
    mp4 = render.render(out)
    assert os.path.exists(mp4)
    # both clips concatenated -> total duration ~= sum of scene durations
    total = sum(s["duration"] for s in sb.load(os.path.join(out, "storyboard.json"))["slides"])
    assert abs(_common.audio_duration(mp4) - total) < 0.6
    # the title clip exists and has an audio stream
    import json as _j
    clip = os.path.join(out, ".clips", "clip_99.mp4")
    streams = _j.loads(_common.run(["ffprobe","-v","error","-show_entries","stream=codec_type",
                                    "-of","json", clip]))["streams"]
    kinds = {s["codec_type"] for s in streams}
    assert "video" in kinds and "audio" in kinds
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_render.py::test_title_scene_renders_and_concats_with_slide -v`
Expected: FAIL (`_render_slide` calls `_fit_frame` on `slide["image"]` which is `None` for the title scene → error).

- [ ] **Step 3: Write minimal implementation**

In `scripts/render.py`, add `import scenes` is NOT needed at top (import lazily to avoid a circular import, since `scenes` imports `render`). At the very start of `_render_slide` (before `frame = ...`), add the dispatch:
```python
def _render_slide(slide, meta, W, H, out_clip, burn_captions, workdir):
    if slide.get("type", "slide") != "slide":
        return _render_scene(slide, meta, W, H, out_clip, burn_captions, workdir)
    i = slide["index"]
    # ... existing slide body unchanged ...
```
Then add these two functions (place them just above `_render_slide`):
```python
def _encode_frames_clip(pattern, audio_rel, dur, caption_segs, meta, W, H, out_clip, workdir):
    """Encode a per-frame PNG sequence + the scene's TTS audio (+ timed captions) into a
    clip using the SAME codec params as the slide path, so the '-c copy' concat still works."""
    fps = meta.get("fps", 30)
    parts = [f"[0:v]scale={W}:{H}[v0]"]               # frames are already WxH; scale = safety
    vlabel = "v0"; extra_inputs = []; n_in = 2        # 0=frames, 1=audio
    for k, seg in enumerate(caption_segs):
        if not (seg.get("text") or "").strip():
            continue
        cap_png = os.path.join(workdir, f"scap_{k:03d}.png")
        _caption_layer(seg["text"], W, H, cap_png, meta)
        extra_inputs += ["-i", cap_png]
        en = f"between(t,{seg['start']},{seg['end']})"
        parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0:enable='{en}'[v{n_in}]")
        vlabel = f"v{n_in}"; n_in += 1
    cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", pattern,
           "-i", os.path.join(meta["_out"], audio_rel)] + extra_inputs + [
        "-filter_complex", ";".join(parts), "-map", f"[{vlabel}]", "-map", "1:a",
        "-t", f"{dur}", "-r", str(fps), "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", out_clip]
    _common.run(cmd)
    return out_clip

def _render_scene(slide, meta, W, H, out_clip, burn_captions, workdir):
    import scenes
    fps = meta.get("fps", 30)
    dur = slide["duration"]
    frames = max(1, int(round(dur * fps)))
    renderers = {"title": scenes.render_title, "chart": scenes.render_chart,
                 "timeline": scenes.render_timeline}
    renderer = renderers[slide["type"]]
    pattern = renderer(slide.get("props") or {}, meta, W, H, frames, workdir, slide["index"])
    segs = _captions_for(slide) if burn_captions else []
    return _encode_frames_clip(pattern, slide["audio"], dur, segs, meta, W, H, out_clip, workdir)
```
NOTE: `_render_scene` references `scenes.render_chart`/`render_timeline` which arrive in Tasks 5/6. For Task 4 only `title` is exercised; the dict lookup for an unimplemented type would `AttributeError` only if such a scene is rendered, which no test does yet. (Tasks 5/6 add them; do not stub them here — that would be dead code.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_render.py -v`
Expected: PASS, including the new end-to-end test and ALL pre-existing render tests (slide path unchanged).

- [ ] **Step 5: Commit**

```bash
git add scripts/render.py tests/test_render.py
git commit -m "feat(render): dispatch animated scene types through a shared frame-sequence encoder"
```

---

### Task 5: `scenes.py` — `chart` renderer (matplotlib, faithful data)

**Files:**
- Modify: `scripts/scenes.py` (add `_chart_values`, `_mpl_font`, `render_chart`)
- Test: `tests/test_scenes.py`

**Interfaces:**
- Produces: `_chart_values(values, p) -> list` (per-frame eased values, never exceeding targets); `render_chart(props, meta, W, H, frames, workdir, index) -> pattern_str`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scenes.py`:
```python
def test_chart_values_never_overshoot_and_settle():
    vals = [61, 165, 90]
    assert scenes._chart_values(vals, 0.0) == [0, 0, 0]
    mid = scenes._chart_values(vals, 0.5)
    assert all(0 <= m <= v for m, v in zip(mid, vals))     # never past target
    assert scenes._chart_values(vals, 1.0) == [61, 165, 90]  # settles exactly on data

def test_chart_writes_frames_and_final_nonblank(tmp_path):
    props = {"kind": "bars", "title": "Launches", "unit": "x",
             "data": [{"label": "2022", "value": 61}, {"label": "2025", "value": 165}]}
    pat = scenes.render_chart(props, META, 1280, 720, 10, str(tmp_path), 4)
    from PIL import Image
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".png")]) == 10
    assert Image.open(pat % 9).convert("RGB").getextrema() != ((0,0),(0,0),(0,0))

def test_chart_deterministic(tmp_path):
    props = {"kind": "bars", "data": [{"label": "a", "value": 3}, {"label": "b", "value": 7}]}
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    pa = scenes.render_chart(props, META, 640, 360, 5, str(a), 1)
    pb = scenes.render_chart(props, META, 640, 360, 5, str(b), 1)
    assert all(_pix(pa % i) == _pix(pb % i) for i in range(5))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_scenes.py -k chart -v`
Expected: FAIL (`render_chart`/`_chart_values` missing).

- [ ] **Step 3: Write minimal implementation**

In `scripts/scenes.py`, add at the top after the existing imports:
```python
import matplotlib
matplotlib.use("Agg")                       # deterministic, headless raster backend
import matplotlib.pyplot as plt
from matplotlib import font_manager
```
Then add:
```python
def _chart_values(values, p):
    e = _ease(p)
    out = []
    for v in values:
        x = v * e
        out.append(round(x) if isinstance(v, int) and v == int(v) else x)
    return [min(o, v) if v >= 0 else max(o, v) for o, v in zip(out, values)]

def _mpl_font(meta):
    """Register and select a CJK font for matplotlib when the narration language is CJK,
    so axis/labels don't tofu; else use matplotlib's bundled DejaVu Sans."""
    lang = (meta.get("language") or "").lower().split("-")[0]
    if lang in ("zh", "ja", "ko"):
        path = render._font_path({"language": lang}, "中")     # reuse the CJK resolver
        try:
            font_manager.fontManager.addfont(path)
            return font_manager.FontProperties(fname=path).get_name()
        except Exception:
            pass
    return "DejaVu Sans"

def render_chart(props, meta, W, H, frames, workdir, index):
    kind = props.get("kind", "bars")
    data = props.get("data", [])
    labels = [str(d.get("label", "")) for d in data]
    values = [d["value"] for d in data]
    title = props.get("title"); unit = props.get("unit", "")
    y_max = props.get("y_max") or (max(values + [0]) * 1.15 or 1)
    famly = _mpl_font(meta)
    dpi = 100
    figsize = (W / dpi, H / dpi)
    accent = props.get("accent", "#4C9BE8")

    def draw(i, n):
        cur = _chart_values(values, i / max(1, n - 1) if n > 1 else 1.0)
        fig = plt.figure(figsize=figsize, dpi=dpi)
        fig.patch.set_facecolor("#0d1117")
        ax = fig.add_subplot(111); ax.set_facecolor("#0d1117")
        for sp in ax.spines.values():
            sp.set_color("#3a4150")
        ax.tick_params(colors="#c0c8d4")
        if title:
            ax.set_title(title, color="white", fontsize=18, fontfamily=famly, pad=16)
        if kind == "counter":
            ax.axis("off")
            ax.text(0.5, 0.5, f"{cur[0]:g}{unit}", ha="center", va="center",
                    color="white", fontsize=72, fontfamily=famly, transform=ax.transAxes)
        elif kind == "line":
            k = max(1, int(len(values) * (i / max(1, n - 1)))) if n > 1 else len(values)
            ax.plot(range(k), values[:k], color=accent, linewidth=3)
            ax.set_xlim(-0.5, len(values) - 0.5); ax.set_ylim(0, y_max)
            ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, fontfamily=famly)
        else:  # bars
            ax.bar(labels, cur, color=accent)
            ax.set_ylim(0, y_max)
            for t in ax.get_xticklabels():
                t.set_fontfamily(famly)
        if props.get("y_label"):
            ax.set_ylabel(props["y_label"], color="#c0c8d4", fontfamily=famly)
        fig.tight_layout()
        fig.canvas.draw()                       # Agg requires a draw before buffer_rgba()
        img = Image.frombytes("RGBA", fig.canvas.get_width_height(),
                              bytes(fig.canvas.buffer_rgba())).convert("RGB")
        plt.close(fig)
        return img.resize((W, H), Image.LANCZOS) if img.size != (W, H) else img

    return _save_frames(draw, frames, workdir, index)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -k chart -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/scenes.py tests/test_scenes.py
git commit -m "feat(scenes): matplotlib chart renderer (bars/line/counter, faithful data, CJK fonts)"
```

---

### Task 6: `scenes.py` — `timeline` renderer (matplotlib)

**Files:**
- Modify: `scripts/scenes.py` (add `_visible_count`, `render_timeline`)
- Test: `tests/test_scenes.py`

**Interfaces:**
- Produces: `_visible_count(total, p) -> int` (events revealed by progress p); `render_timeline(props, meta, W, H, frames, workdir, index) -> pattern_str`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scenes.py`:
```python
def test_visible_count_grows_with_progress():
    assert scenes._visible_count(4, 0.0) >= 0
    assert scenes._visible_count(4, 1.0) == 4
    assert scenes._visible_count(4, 0.5) <= 4
    assert scenes._visible_count(4, 0.0) <= scenes._visible_count(4, 0.6) <= scenes._visible_count(4, 1.0)

def test_timeline_writes_frames_and_final_nonblank(tmp_path):
    props = {"title": "Milestones", "events": [
        {"date": "2026-01", "label": "Kickoff"}, {"date": "2026-06", "label": "MVP"},
        {"date": "2026-12", "label": "Ship"}]}
    pat = scenes.render_timeline(props, META, 1280, 720, 9, str(tmp_path), 7)
    from PIL import Image
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".png")]) == 9
    assert Image.open(pat % 8).convert("RGB").getextrema() != ((0,0),(0,0),(0,0))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_scenes.py -k "visible or timeline" -v`
Expected: FAIL (`render_timeline`/`_visible_count` missing).

- [ ] **Step 3: Write minimal implementation**

In `scripts/scenes.py`, add:
```python
def _visible_count(total, p):
    return max(0, min(total, int(_ease(p) * total + 1e-9)))

def render_timeline(props, meta, W, H, frames, workdir, index):
    events = props.get("events", [])
    title = props.get("title")
    famly = _mpl_font(meta)
    dpi = 100; figsize = (W / dpi, H / dpi)
    accent = props.get("accent", "#4C9BE8")
    n_ev = len(events)
    xs = list(range(n_ev))

    def draw(i, n):
        vis = _visible_count(n_ev, i / max(1, n - 1) if n > 1 else 1.0)
        fig = plt.figure(figsize=figsize, dpi=dpi); fig.patch.set_facecolor("#0d1117")
        ax = fig.add_subplot(111); ax.set_facecolor("#0d1117"); ax.axis("off")
        if title:
            ax.set_title(title, color="white", fontsize=18, fontfamily=famly, pad=16)
        if n_ev:
            ax.plot([-0.3, n_ev - 0.7], [0, 0], color="#3a4150", linewidth=2)
            for j in range(vis):
                ax.scatter([xs[j]], [0], s=120, color=accent, zorder=3)
                ax.text(xs[j], 0.12, events[j].get("date", ""), ha="center",
                        color="#c0c8d4", fontsize=12, fontfamily=famly)
                ax.text(xs[j], -0.18, events[j].get("label", ""), ha="center",
                        color="white", fontsize=14, fontfamily=famly)
            ax.set_xlim(-0.6, n_ev - 0.4); ax.set_ylim(-0.5, 0.5)
        fig.tight_layout()
        fig.canvas.draw()
        img = Image.frombytes("RGBA", fig.canvas.get_width_height(),
                              bytes(fig.canvas.buffer_rgba())).convert("RGB")
        plt.close(fig)
        return img.resize((W, H), Image.LANCZOS) if img.size != (W, H) else img

    return _save_frames(draw, frames, workdir, index)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -v`
Expected: PASS (all scene tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/scenes.py tests/test_scenes.py
git commit -m "feat(scenes): matplotlib timeline renderer (events reveal in order)"
```

---

### Task 7: Docs — critic note + SKILL.md scene-type mention

**Files:**
- Modify: `agents/critic.md` (inputs + a brief rule)
- Modify: `SKILL.md` (Pipeline/Guardrails: mention animated scene types)

**Interfaces:** none (prose). Verified by grep + the full suite staying green.

- [ ] **Step 1: Add the critic note**

In `agents/critic.md`, in the "Your inputs" list item 1, append after the existing sentence:
```markdown
   For ANIMATED scenes (`type` is `title`/`chart`/`timeline`, not `slide`), the on-screen
   content is the scene's `props` (title/subtitle text, chart `data` numbers, timeline events)
   — there is no slide image.
```
And add a short rule after R1c:
```markdown
### R1d — Animated scenes show only sourced content
- For `type` ≠ `slide`: every on-screen string and number must come from the scene's `props`
  and trace to the source (chart numbers live in `data`; titles/events are verbatim text).
- FAIL on any invented or mis-stated on-screen value (a chart bar whose number isn't in the
  source, a fabricated timeline event). Form (motion, color, layout) is free; facts are not.
```

- [ ] **Step 2: Add the SKILL.md mention**

In `SKILL.md`, under `## Pipeline scripts`, add a line after the `render.py` bullet:
```markdown
- `scripts/scenes.py` — deterministic ANIMATED scene renderers (no slides): `title` (PIL),
  `chart`/`timeline` (matplotlib). A storyboard scene with `type` `title`/`chart`/`timeline`
  (+ a typed `props` block) renders an animation instead of a slide image; `type` defaults to
  `slide` (unchanged). Animated scenes render ONLY their `props` (faithful by construction).
```

- [ ] **Step 3: Verify prose + full suite**

Run:
```bash
grep -n "R1d\|scenes.py\|Animated scenes" agents/critic.md SKILL.md
python3 -m pytest -q
```
Expected: grep shows the new lines; full suite PASSES (all tasks' tests + pre-existing).

- [ ] **Step 4: Commit**

```bash
git add agents/critic.md SKILL.md
git commit -m "docs: document animated scene types + critic R1d (sourced-content-only)"
```

---

## Self-Review

**Spec coverage:**
- Dispatcher → Task 4 ✓; schema `type`/`props` + per-type validation → Task 1 ✓; `_fingerprint` → Task 2 ✓; `title` renderer → Task 3 ✓; `chart` → Task 5 ✓; `timeline` → Task 6 ✓; shared encode reusing skill codec + captions → Task 4 (`_encode_frames_clip`) ✓; CJK fonts (PIL via `_font_path`, matplotlib via `_mpl_font`) → Tasks 3/5 ✓; faithful-by-construction (props-only, numeric `data`) → Tasks 1/5 ✓; lean critic note → Task 7 ✓; backward compat (slide path untouched, `type` default) → Tasks 1/4 + existing tests ✓; determinism (pure frame fn, pixel-byte tests) → Tasks 3/5/6 ✓; cache-safe + concat-safe → Tasks 2/4 ✓. No gaps.
- Out-of-scope items (Remotion/Manim/facts-ledger/faithcheck/R7/transitions) correctly have NO task.

**Placeholder scan:** none — every code step has full code; the Task 4 note about `render_chart`/`render_timeline` arriving in Tasks 5/6 is a sequencing fact, not a placeholder (the `title` path is fully implemented and tested in Task 4).

**Type consistency:** renderer signature `(props, meta, W, H, frames, workdir, index) -> pattern_str` is identical across Tasks 3/5/6 and matches the call in `_render_scene` (Task 4). `_encode_frames_clip(pattern, audio_rel, dur, caption_segs, meta, W, H, out_clip, workdir)` matches its caller. `_save_frames`/`_ease`/`_mpl_font` are defined before first use. `_chart_values`/`_visible_count` names match their tests. `_fingerprint` keeps its existing signature.
