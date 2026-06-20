# HTML Pages Visual Tier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third, opt-in visual tier — bespoke designed **HTML pages** rendered by the already-installed headless Chrome — where each page's paused CSS reveals are captured frame-by-frame and sequenced into the narrated video, faithfully and free.

**Architecture:** A new animated scene type `html` plugs into the EXISTING animated path (`render._render_scene` → `getattr(scenes,"render_html")` → `_encode_frames_clip`). `render_html` screenshots `file://page.html?p=0…1` via Chrome (`scenes._chrome_shot`); a bundled `seek.js` freezes the page at progress `p` by setting a negative `animation-delay`. A bundled `base.css` gives the designed look. Schema + a one-line `_fingerprint` change + SKILL.md workflow complete it.

**Tech Stack:** Python 3, Pillow, ffmpeg, **headless Google Chrome** (already installed; no Playwright/Puppeteer/new dependency), pytest, HTML/CSS/JS.

## Global Constraints
- **Local & free, no new dependency:** rendering uses the installed Chrome via `--headless --screenshot`. No pip/npm install.
- **Deterministic capture:** the page is frozen at progress `p` by `seek.js` setting each animated element's `animation-delay = (its-delay − p×total)` + `animation-play-state: paused` (proven: clean ramp + byte-identical re-renders). Renderers stay pure of randomness/wall-clock; `render_html`'s only nondeterminism is Chrome itself (stable on a machine).
- Renderer signature: `render_<type>(props, meta, W, H, frames, workdir, index) -> pattern_str`; frames named `scene_{index:02d}_%04d.png` (use `os.path.join(workdir, f"scene_{index:02d}_%04d.png")`).
- **Faithful:** pages render only real content (authored from the material); the existing critic (R1d/R1e/R2) applies unchanged — no critic edit.
- New type routes through the EXISTING dispatch; the only `render.py` change is one line in `_fingerprint`.
- **Reveal-then-hold:** animate for `anim_seconds`, then hold the settled frame (Chrome launched ≈ `reveal_frames` times, the rest are file copies).
- Existing suite stays green. Tests mock Chrome except ONE opt-in integration test (`skipif` no Chrome).

---

### Task 1: `scenes.py` — `_chrome_bin` + `_chrome_shot`

**Files:**
- Modify: `scripts/scenes.py` (add imports + the two helpers, after the module constants near the top)
- Test: `tests/test_scenes.py`

**Interfaces (Produces):**
- `_CHROME_CANDIDATES` (list); `_chrome_bin(meta) -> str|None`; `_chrome_shot(url, out_png, W, H, meta) -> None` (raises `RuntimeError` if no Chrome).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scenes.py`:
```python
import pytest

def test_chrome_bin_honors_meta_path(tmp_path):
    fake = tmp_path / "chrome"; fake.write_text("x")
    assert scenes._chrome_bin({"chrome_path": str(fake)}) == str(fake)

def test_chrome_bin_none_when_absent(monkeypatch):
    monkeypatch.setattr(scenes, "_CHROME_CANDIDATES", [])
    monkeypatch.setattr(scenes.shutil, "which", lambda n: None)
    assert scenes._chrome_bin({}) is None

def test_chrome_shot_builds_command(tmp_path, monkeypatch):
    fake = tmp_path / "chrome"; fake.write_text("x")
    cap = {}
    def fake_run(cmd, **kw):
        cap["cmd"] = cmd; cap["kw"] = kw
    monkeypatch.setattr(scenes.subprocess, "run", fake_run)
    scenes._chrome_shot("file:///p.html?p=0.5", str(tmp_path / "o.png"), 1920, 1080,
                        {"chrome_path": str(fake)})
    cmd = cap["cmd"]
    assert cmd[0] == str(fake)
    assert "--headless" in cmd and "--window-size=1920,1080" in cmd
    assert f"--screenshot={tmp_path / 'o.png'}" in cmd
    assert cmd[-1] == "file:///p.html?p=0.5"
    assert cap["kw"].get("check") is True and cap["kw"].get("timeout") == 60

def test_chrome_shot_no_chrome_raises(monkeypatch):
    monkeypatch.setattr(scenes, "_chrome_bin", lambda meta: None)
    with pytest.raises(RuntimeError):
        scenes._chrome_shot("file:///p.html", "/tmp/o.png", 1920, 1080, {})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/donghanglyu/.claude/skills/slides-to-video && python3 -m pytest tests/test_scenes.py -k chrome -v`
Expected: FAIL (`module 'scenes' has no attribute '_chrome_bin'` / `_chrome_shot` / `_CHROME_CANDIDATES`).

- [ ] **Step 3: Write the implementation**

In `scripts/scenes.py`: add `import shutil, subprocess` to the imports at the top (alongside `import os`). Then add, after the `BG`/`FG` constants near the top:
```python
_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

def _chrome_bin(meta):
    """Locate a Chrome/Chromium binary: meta.chrome_path, the macOS app, or PATH. None if absent."""
    c = (meta or {}).get("chrome_path")
    if c and os.path.exists(c):
        return c
    for p in _CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        w = shutil.which(n)
        if w:
            return w
    return None

def _chrome_shot(url, out_png, W, H, meta):
    """Screenshot an HTML url to out_png via headless Chrome. Raises if no Chrome is found."""
    chrome = _chrome_bin(meta)
    if not chrome:
        raise RuntimeError("no Chrome/Chromium for the HTML tier — install Chrome or set meta.chrome_path")
    subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                    f"--window-size={W},{H}", f"--screenshot={out_png}", url],
                   check=True, capture_output=True, timeout=60)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -k chrome -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/scenes.py tests/test_scenes.py
git commit -m "feat(scenes): _chrome_bin + _chrome_shot — headless Chrome screenshot helper"
```

---

### Task 2: `scenes.py` — `render_html`

**Files:**
- Modify: `scripts/scenes.py` (add `render_html` after `render_compare`)
- Test: `tests/test_scenes.py`

**Interfaces:**
- Consumes: `_chrome_shot` (Task 1); `shutil` (imported in Task 1); `_save_frames` naming convention.
- Produces: `render_html(props, meta, W, H, frames, workdir, index) -> pattern_str`. props: `{html: str (path rel to meta["_out"]), anim_seconds?: float (default 0.8)}`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scenes.py`:
```python
def _tiny_png(path):
    Image.new("RGB", (4, 4), (10, 20, 30)).save(path)

def test_render_html_frames_launch_count_and_p_ramp(tmp_path, monkeypatch):
    out_dir = tmp_path / "proj"; (out_dir / "pages").mkdir(parents=True)
    (out_dir / "pages" / "scene_03.html").write_text("<html></html>")
    calls = []
    def fake_shot(url, out_png, W, H, meta):
        calls.append(url); _tiny_png(out_png)
    monkeypatch.setattr(scenes, "_chrome_shot", fake_shot)
    meta = {"_out": str(out_dir), "fps": 30}
    pat = scenes.render_html({"html": "pages/scene_03.html", "anim_seconds": 0.2},
                             meta, 1920, 1080, 12, str(tmp_path), 3)
    files = sorted(f for f in os.listdir(tmp_path) if f.endswith(".png"))
    assert len(files) == 12 and files[0] == "scene_03_0000.png" and "%04d" in pat
    # anim 0.2s * 30fps = 6 reveal frames -> 6 Chrome launches; the other 6 frames are copies
    assert len(calls) == 6
    assert [c.split("?p=")[1] for c in calls] == ["0.0000","0.2000","0.4000","0.6000","0.8000","1.0000"]
    assert calls[0].startswith("file://") and "scene_03.html" in calls[0]

def test_render_html_single_frame_holds(tmp_path, monkeypatch):
    out_dir = tmp_path / "proj"; (out_dir / "pages").mkdir(parents=True)
    (out_dir / "pages" / "s.html").write_text("<html></html>")
    calls = []
    monkeypatch.setattr(scenes, "_chrome_shot",
                        lambda url, out_png, W, H, meta: (calls.append(url), _tiny_png(out_png)))
    pat = scenes.render_html({"html": "pages/s.html"}, {"_out": str(out_dir), "fps": 30},
                             640, 360, 1, str(tmp_path), 1)
    assert os.path.exists(pat % 0) and len(calls) == 1 and calls[0].endswith("?p=1.0000")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_scenes.py -k render_html -v`
Expected: FAIL (`module 'scenes' has no attribute 'render_html'`).

- [ ] **Step 3: Write the implementation**

In `scripts/scenes.py`, add after `render_compare`:
```python
def render_html(props, meta, W, H, frames, workdir, index):
    """Render a designed HTML page (paused CSS reveals) into a frame sequence by screenshotting
    it at progress p=0..1 via headless Chrome. Animate for anim_seconds, then hold the settle frame."""
    src = os.path.join(meta["_out"], props["html"])
    fps = meta.get("fps", 30)
    anim = float(props.get("anim_seconds", 0.8))
    reveal_frames = max(1, min(frames, int(round(anim * fps))))
    pat = os.path.join(workdir, f"scene_{index:02d}_%04d.png")
    settle = None
    for i in range(frames):
        out = pat % i
        p = 1.0 if i >= reveal_frames - 1 else i / max(1, reveal_frames - 1)
        if p >= 1.0 and settle is not None:
            shutil.copyfile(settle, out)              # hold: reuse the settled screenshot
            continue
        _chrome_shot(f"file://{src}?p={p:.4f}", out, W, H, meta)
        if p >= 1.0:
            settle = out
    return pat
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -k render_html -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/scenes.py tests/test_scenes.py
git commit -m "feat(scenes): render_html — capture paused-CSS pages frame-by-frame (reveal-then-hold)"
```

---

### Task 3: storyboard schema for `html`

**Files:**
- Modify: `scripts/storyboard.py`
- Test: `tests/test_storyboard.py`

**Interfaces:**
- Consumes: `render_html` (Task 2) — dispatch-resolution check; `_is_num` (existing).
- Produces: `html` accepted by `validate`; bad props raise `StoryboardError`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_storyboard.py`:
```python
import scenes

def test_validate_html_ok_and_dispatchable():
    d = {"meta": {}, "slides": [sb.new_scene(1, "html", {"html": "pages/s.html", "anim_seconds": 0.8}, "n")]}
    sb.validate(d)
    assert callable(getattr(scenes, "render_html"))

def test_validate_html_bad():
    for bad in [{}, {"html": ""}, {"html": "   "},
                {"html": "p.html", "anim_seconds": 0}, {"html": "p.html", "anim_seconds": -1}]:
        with pytest.raises(sb.StoryboardError):
            sb.validate({"meta": {}, "slides": [sb.new_scene(1, "html", bad, "n")]})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_storyboard.py -k html -v`
Expected: FAIL (unknown type `html`).

- [ ] **Step 3: Write the implementation**

In `scripts/storyboard.py`, update the two sets (lines 8–9):
```python
VALID_SCENE_TYPES = {"slide", "title", "chart", "timeline", "keypoints", "compare", "html"}
ANIMATED_TYPES = {"title", "chart", "timeline", "keypoints", "compare", "html"}
```
In `_validate_props`, after the `compare` branch, add:
```python
    elif t == "html":
        if not (isinstance(p.get("html"), str) and p["html"].strip()):
            raise StoryboardError(f"slide {s.get('index')}: html scene needs a non-empty 'html' path")
        if "anim_seconds" in p and not (_is_num(p["anim_seconds"]) and p["anim_seconds"] > 0):
            raise StoryboardError(f"slide {s.get('index')}: html 'anim_seconds' must be a positive number")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_storyboard.py -v`
Expected: PASS (new + existing).

- [ ] **Step 5: Commit**

```bash
git add scripts/storyboard.py tests/test_storyboard.py
git commit -m "feat(storyboard): validate html scene type"
```

---

### Task 4: `render.py` — `_fingerprint` includes the page file

**Files:**
- Modify: `scripts/render.py` (`_fingerprint` payload, line 265)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: the existing `stat(rel)` helper inside `_fingerprint`.
- Produces: editing an `html` scene's page file changes its clip fingerprint.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_render.py`:
```python
def test_fingerprint_busts_on_html_page_edit(tmp_path):
    pg = tmp_path / "pages"; pg.mkdir(); f = pg / "s.html"; f.write_text("a")
    meta = {"_out": str(tmp_path), "fps": 30}
    slide = {"index": 1, "type": "html", "props": {"html": "pages/s.html"},
             "image": None, "audio": None, "duration": 3.0, "motion": {}, "narration": "n",
             "captions": [], "callouts": [], "fit": "contain"}
    fp = lambda: render._fingerprint(slide, meta, 1920, 1080, 2, True, False)
    a = fp()
    f.write_text("a much longer page body that changes the file size")   # edit the page
    assert fp() != a                                                     # cache busts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_render.py -k html_page_edit -v`
Expected: FAIL (fingerprint ignores the page file → unchanged hash → assert fails).

- [ ] **Step 3: Write the implementation**

In `scripts/render.py` `_fingerprint`, change the `"img"/"aud"` payload line (line 265) to also stat the page:
```python
        "img": stat(slide.get("image")), "aud": stat(slide.get("audio")),
        "html": stat((slide.get("props") or {}).get("html")),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_render.py -k html_page_edit -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/render.py tests/test_render.py
git commit -m "fix(render): include html page file in clip fingerprint (edits re-render)"
```

---

### Task 5: bundled design system `assets/html/base.css` + `seek.js`

**Files:**
- Create: `assets/html/base.css`, `assets/html/seek.js`
- Test: `tests/test_scenes.py` (one opt-in integration test)

**Interfaces:**
- Produces: a stylesheet + the seek freezer the authored pages link to.

- [ ] **Step 1: Write the opt-in integration test**

Add to `tests/test_scenes.py`:
```python
def _chrome_present():
    return scenes._chrome_bin({}) is not None

@pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")
def test_base_css_page_renders_and_reveals(tmp_path):
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))   # skill root
    css = os.path.join(skill, "assets", "html", "base.css")
    js = os.path.join(skill, "assets", "html", "seek.js")
    assert os.path.exists(css) and os.path.exists(js)
    page = tmp_path / "p.html"
    page.write_text(
        '<!doctype html><html><head><meta charset="utf-8">'
        f'<link rel="stylesheet" href="file://{css}"></head>'
        '<body><div class="stage"><h1 class="title reveal-up">测试 42</h1></div>'
        f'<script src="file://{js}"></script></body></html>')
    a = tmp_path / "a.png"; b = tmp_path / "b.png"
    scenes._chrome_shot(f"file://{page}?p=0", str(a), 960, 540, {})
    scenes._chrome_shot(f"file://{page}?p=1", str(b), 960, 540, {})
    ia = Image.open(a).convert("RGB"); ib = Image.open(b).convert("RGB")
    assert ib.getextrema() != ((0, 0), (0, 0), (0, 0))     # settled page is non-blank
    assert ia.tobytes() != ib.tobytes()                    # reveal animated (hidden at p=0)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest tests/test_scenes.py -k base_css_page -v`
Expected: FAIL (assets don't exist yet) — or `skipped` if no Chrome (then verify by file existence in Step 4).

- [ ] **Step 3: Create the assets**

Create `assets/html/base.css`:
```css
/* slides-to-video — HTML page design system (huashu-aligned, anti-AI-slop).
   Dark stage, CJK-first serif, accent palette, seekable reveals. Authored pages link this. */
:root{
  --bg:#0d1117; --panel:#161b22; --fg:#f0f3f8; --muted:#8b97a8;
  --blue:#4C9BE8; --orange:#E8590C; --green:#46A758; --dur:.7s;
}
*{box-sizing:border-box}
html,body{margin:0;width:1920px;height:1080px;background:var(--bg);color:var(--fg);
  font-family:"PingFang SC","Hiragino Sans GB","Songti SC","Source Han Serif SC",
              -apple-system,Georgia,"Times New Roman",serif;
  overflow:hidden;text-wrap:pretty;-webkit-font-smoothing:antialiased}
.stage{width:1920px;height:1080px;padding:120px 150px;display:flex;flex-direction:column;
  justify-content:center;gap:36px}
.kicker{color:var(--orange);font-size:30px;font-weight:600;letter-spacing:.12em;text-transform:uppercase}
.rule{height:6px;width:140px;background:var(--orange);border-radius:3px}
.title{font-size:104px;font-weight:800;line-height:1.08;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:42px;line-height:1.4}
.stat{font-size:240px;font-weight:800;color:var(--blue);line-height:.95;letter-spacing:-.02em}
.unit{font-size:64px;color:var(--muted);font-weight:600}
.grid{display:grid;gap:40px}
.row{display:flex;align-items:baseline;gap:28px;font-size:52px}
.dot{width:22px;height:22px;border-radius:50%;background:var(--blue);flex:none;align-self:center}
.label{font-size:54px;font-weight:700}
.note{color:var(--muted);font-size:34px}
.bar{height:90px;border-radius:10px;display:flex;align-items:center;padding:0 28px;color:#fff;font-size:40px;font-weight:700}
/* seekable reveals — paused so render_html/seek.js can freeze them at any progress p.
   Stagger by adding an inline positive animation-delay (e.g. style="animation-delay:.18s"). */
.reveal{opacity:0;animation:fade var(--dur) ease forwards;animation-play-state:paused}
.reveal-up{opacity:0;transform:translateY(48px);
  animation:rise var(--dur) cubic-bezier(.22,1,.36,1) forwards;animation-play-state:paused}
@keyframes fade{to{opacity:1}}
@keyframes rise{to{opacity:1;transform:none}}
```
Create `assets/html/seek.js`:
```javascript
/* slides-to-video — freeze CSS reveals at progress ?p=0..1 for deterministic frame capture.
   Each animated element is frozen at local time (p*total − itsDelay) and paused, so staggered
   reveals render correctly at any p. total = max(delay+duration) across animated elements. */
(function () {
  function sec(v) { v = parseFloat(v); return isNaN(v) ? 0 : v; }
  var els = [].slice.call(document.querySelectorAll('*')).filter(function (el) {
    var n = getComputedStyle(el).animationName; return n && n !== 'none';
  });
  var spans = els.map(function (el) {
    var cs = getComputedStyle(el);
    return { el: el, d: sec(cs.animationDelay), dur: sec(cs.animationDuration) };
  });
  var total = spans.reduce(function (m, s) { return Math.max(m, s.d + s.dur); }, 0.001);
  var p = parseFloat(new URLSearchParams(location.search).get('p'));
  if (isNaN(p)) p = 1;
  var T = p * total;
  spans.forEach(function (s) {
    s.el.style.animationDelay = (s.d - T) + 's';
    s.el.style.animationPlayState = 'paused';
  });
})();
```

- [ ] **Step 4: Verify**

Run: `python3 -m pytest tests/test_scenes.py -k base_css_page -v` (PASS with Chrome, else `skipped`).
Run (always): `ls assets/html/base.css assets/html/seek.js` (both exist); `python3 -m pytest -q` (full suite green).

- [ ] **Step 5: Commit**

```bash
git add assets/html/base.css assets/html/seek.js tests/test_scenes.py
git commit -m "feat(assets): HTML design system base.css + seek.js (seekable reveals)"
```

---

### Task 6: authoring guide `references/html-pages.md`

**Files:**
- Create: `references/html-pages.md`

- [ ] **Step 1: Write the guide**

Create `references/html-pages.md` verbatim:
```markdown
# Authoring HTML pages (the "HTML pages" visual tier)

Each `html` scene is one designed full-screen page (1920×1080) you author at
`<out_dir>/pages/scene_NN.html`, rendered by headless Chrome. The page is screenshotted at
progress `p=0..1`; `seek.js` freezes its CSS reveals so the entrance animates then holds.

## Boilerplate (link the bundled design system)
```html
<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="file:///ABS/PATH/TO/skill/assets/html/base.css"></head>
<body>
  <div class="stage"><!-- your layout --></div>
  <script src="file:///ABS/PATH/TO/skill/assets/html/seek.js"></script>
</body></html>
```
Use absolute `file://` paths to the skill's `assets/html/base.css` and `seek.js`.

## Layout patterns (compose with base.css classes)
- **Title:** `.kicker` + `.rule` + `.title` (+ `.sub`).
- **Big stat:** a `.stat` number + `.unit`, with a `.sub` caption.
- **Split / breakdown:** a `.grid` of `.bar` rows (widths set inline as `style="width:74%;background:var(--blue)"`), each labeled — for decompositions like 165 = 123 + 42.
- **List / key points:** `.grid` of `.row`s, each `.dot` + `.label` (+ `.note`).
- **Quote / takeaway:** a large `.title` line + `.sub` attribution.
- **Timeline:** a `.grid`/flex row of dated `.row`s.

## Reveal animation (so the page captures cleanly)
- Add `class="reveal"` or `class="reveal-up"` to elements you want to animate in.
- Stagger by giving later elements an inline positive delay: `style="animation-delay:.18s"`.
- ONLY use CSS animations via these classes. **No** `setTimeout`/JS-driven motion, **no** external
  network assets (images/fonts/CDNs) — they break deterministic, offline, seekable capture.

## Faithfulness (required)
Every number, name, date, and claim on the page must come from the material (or a verified
source) — type the real data into the HTML. Never invent figures or labels. Data lives on the
page as real text/bars, not as a decorative picture. The critic checks the page against the
narration (R2 audio↔visual) and the facts (R1d/R1e).

## Example (a faithful split page)
```html
<div class="stage">
  <div class="kicker reveal">2025 · 165 次发射</div>
  <div class="rule reveal" style="animation-delay:.05s"></div>
  <div class="title reveal-up" style="animation-delay:.1s">真正能争夺的，只有一小块</div>
  <div class="grid" style="margin-top:40px">
    <div class="bar reveal-up" style="animation-delay:.25s;width:74%;background:var(--blue)">自用 Starlink · 123</div>
    <div class="bar reveal-up" style="animation-delay:.4s;width:26%;background:var(--orange)">对外发射 · 42</div>
  </div>
</div>
```
```

- [ ] **Step 2: Verify + commit**

Run: `grep -n "Faithfulness\|seek.js\|reveal-up\|No.*setTimeout\|base.css" references/html-pages.md` (expect matches).
```bash
git add references/html-pages.md
git commit -m "docs(reference): HTML page authoring guide (patterns, reveals, faithfulness)"
```

---

### Task 7: SKILL.md — HTML pages mode + Chrome requirement

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Add the tier to Pipeline scripts / tools**

In `SKILL.md` `## Tools` or `## Pipeline scripts`, add:
```markdown
- **HTML pages tier** (optional, free): `scenes.py:render_html` screenshots bespoke designed
  HTML pages (authored on `assets/html/base.css`, see `references/html-pages.md`) via headless
  **Google Chrome** — no new dependency. Each page's paused CSS reveals are captured frame-by-frame.
```

- [ ] **Step 2: Add HTML pages to the visual-mode interview choice**

In `SKILL.md` Workflow step 1 (Interview), in the image-source/visual clause, add the third option:
```markdown
   A third visual mode is **HTML pages** — bespoke, designed pages (`type:"html"`) rendered by
   headless Google Chrome (free, no dependency; needs Chrome installed). Choose it for a
   "designed deck" look. The content-planner designs the beats; you author one
   `pages/scene_NN.html` per beat on `assets/html/base.css` (faithful — real content only),
   following `references/html-pages.md`. Set `meta.chrome_path` if Chrome isn't at the default
   macOS location.
```

- [ ] **Step 3: Guardrails + failure table**

In `SKILL.md` `## Guardrails`, add:
```markdown
- **HTML pages tier:** `type:"html"` scenes render an authored page via headless Chrome
  (`render_html`), captured as seekable CSS reveals. Pages render only real content (faithful);
  the per-clip cache busts when the page file changes. Locate Chrome via `meta.chrome_path` if needed.
```
In the `## When a step fails` table, add:
```markdown
| `render.py`: no Chrome for an `html` scene | `render_html` errors clearly; set `meta.chrome_path`, or switch those scenes to the free programmatic tier (title/chart/keypoints/compare) | Install Google Chrome, then re-render |
| `html` page renders blank / unstyled | Confirm the page links `assets/html/base.css` + `seek.js` by ABSOLUTE `file://` path; no external/network assets | Open the page in a browser to debug, then re-render (the cache busts on edit) |
```

- [ ] **Step 4: Verify + full suite + commit**

Run:
```bash
grep -n "HTML pages\|render_html\|chrome_path\|type:\"html\"" SKILL.md
python3 -m pytest -q
```
Expected: grep shows the additions; full suite PASSES.
```bash
git add SKILL.md
git commit -m "docs(skill): HTML pages visual tier — interview mode, Chrome requirement, guardrails"
```

---

## Self-Review

**Spec coverage:** `_chrome_bin`/`_chrome_shot` (Task 1) ✓; `render_html` reveal-then-hold (Task 2) ✓; schema for `html` + dispatch-resolution (Task 3) ✓; `_fingerprint` page-stat (Task 4) ✓; `base.css` + stagger-aware `seek.js` + opt-in integration test (Task 5) ✓; authoring guide with faithfulness + seek contract (Task 6) ✓; SKILL.md mode + Chrome requirement + failure rows (Task 7) ✓. No-new-dependency (Chrome only) — Tasks 1/5. Faithful + critic-unchanged (R2/R1d/R1e apply) — Tasks 6/7. "Only render.py change is one `_fingerprint` line" — Task 4 (dispatch routes `html` via the existing `getattr(scenes,"render_html")`). Out-of-scope items (Playwright fast-path, `--no-cache`, more patterns, html→pptx) correctly have NO task.

**Placeholder scan:** none — every code/test/asset step is complete and runnable; the guide and assets are verbatim. The `/ABS/PATH/TO/skill/` in the authoring guide is intentional instructional text (the author substitutes the real absolute path), not a plan placeholder.

**Type consistency:** renderer signature `(props, meta, W, H, frames, workdir, index) -> pattern` matches `render_html` and the dispatch. `_chrome_shot(url, out_png, W, H, meta)` is defined in Task 1 and called identically in Task 2 (`render_html`) and Task 5 (the integration test). `_chrome_bin(meta)` consistent across Tasks 1/5. `props.html` / `props.anim_seconds` names match across renderer (Task 2), schema (Task 3), fingerprint (Task 4: `props.get("html")`), and the guide (Task 6). `meta.chrome_path` consistent across Tasks 1/7. `VALID_SCENE_TYPES`/`ANIMATED_TYPES` extended once (Task 3). `_is_num` (Task 3) already exists in storyboard.py.
