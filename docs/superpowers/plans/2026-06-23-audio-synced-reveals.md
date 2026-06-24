# Audio-Synced Point Reveals — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reveal each on-screen point at the moment its phrase is spoken, by deriving per-point cue times from edge-tts word timings — with a graceful fallback to the current paced stagger.

**Architecture:** `tts.py` captures word timestamps → `audio/NN.words.json`. A pure `scripts/cues.py` resolves each point's anchor → cue time. `seek.js` gains a `?cues=&dur=` override that sets each `[data-cue-index]` element's delay to its cue. `render_html` (when a words file + cued points exist) resolves cues, captures frames around each cue across the full scene, and passes `?cues=&dur=`; otherwise the existing path runs unchanged.

**Tech Stack:** Python 3 (stdlib), edge-tts CLI, JS (seek.js), headless Chrome, pytest.

## Global Constraints
- CSS-only + frozen per frame (seek-safe) — no JS-timed/wall-clock motion. `cues.resolve_cues` is PURE (no I/O). Deterministic.
- Additive + fallback: no words file, no `[data-cue-index]` points, or `say`/openai voice → the current `anim_seconds` reveal path runs unchanged. Synthesis never fails if subtitle capture fails.
- `resolve_cues` returns a list the same length as `anchors`, **monotonic non-decreasing**, every entry a float.
- The html-scene clip fingerprint must include `audio/NN.words.json` so a re-synth busts the cached clip.
- Existing test suite stays green.

---

### Task 1: `scripts/cues.py` — pure cue resolver

**Files:**
- Create: `scripts/cues.py`
- Test: `tests/test_cues.py` (new)

**Interfaces (Produces):** `resolve_cues(words, anchors) -> list[float]` (words=`[{"w":str,"t":float}]`, anchors=`[str]`); helpers `_norm(s)`, `_find(words, phrase, start)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cues.py`:
```python
import cues

W = [{"w": "come", "t": 0.3}, {"w": "to", "t": 0.6}, {"w": "dujiangyan", "t": 2.0},
     {"w": "an irrigation system", "t": 3.1}, {"w": "leshan", "t": 6.0}, {"w": "buddha", "t": 6.4}]

def test_matches_in_order():
    assert cues.resolve_cues(W, ["Dujiangyan", "Leshan"]) == [2.0, 6.0]

def test_explicit_phrase_over_label():
    # anchor phrase "irrigation" matches the grouped cue, not the label "Dujiangyan"
    assert cues.resolve_cues(W, ["irrigation", "Leshan"]) == [3.1, 6.0]

def test_missing_anchor_interpolated_between_neighbors():
    r = cues.resolve_cues(W, ["Dujiangyan", "Mahjong", "Leshan"])  # middle not present
    assert r[0] == 2.0 and r[2] == 6.0
    assert 2.0 < r[1] < 6.0                # interpolated midpoint, monotonic

def test_no_match_even_spread():
    r = cues.resolve_cues(W, ["zzz", "qqq", "www"])
    assert len(r) == 3 and r == sorted(r) and all(0 < t < W[-1]["t"] + 1 for t in r)

def test_monotonic_nudge_on_collision():
    w = [{"w": "alpha beta", "t": 1.0}]
    r = cues.resolve_cues(w, ["alpha", "beta"])   # both match the same cue
    assert r[0] == 1.0 and r[1] > r[0]            # second nudged forward

def test_length_and_floats():
    r = cues.resolve_cues(W, ["come", "leshan"])
    assert len(r) == 2 and all(isinstance(x, float) for x in r)

def test_empty():
    assert cues.resolve_cues(W, []) == [] and cues.resolve_cues([], ["x"])  # no crash
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/donghanglyu/.claude/skills/slides-to-video && python3 -m pytest tests/test_cues.py -v`
Expected: FAIL (`No module named 'cues'`).

- [ ] **Step 3: Write `scripts/cues.py`**

```python
"""Resolve per-point reveal cue times from TTS word timings. PURE (no I/O) so it unit-tests without
edge-tts. Each point's anchor phrase is matched against the spoken word stream left-to-right and
monotonically; unmatched anchors are interpolated between resolved neighbors. Result is always the
same length as `anchors` and monotonic non-decreasing."""
import re

EPS = 0.15  # seconds — minimum gap nudge when two anchors resolve to the same/earlier time

def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").casefold()).strip()

def _find(words, phrase, start):
    """First index >= start whose (normalized) word/cue text contains the anchor's first token; -1 none."""
    toks = _norm(phrase).split()
    if not toks:
        return -1
    key = toks[0]
    for i in range(start, len(words)):
        wn = _norm(words[i].get("w", ""))
        if wn == key or key in wn.split():
            return i
    return -1

def resolve_cues(words, anchors):
    n = len(anchors)
    if n == 0:
        return []
    last = float(words[-1].get("t", n)) if words else float(n)
    raw = [None] * n
    cur = 0
    for i, a in enumerate(anchors):
        idx = _find(words, a, cur)
        if idx >= 0:
            raw[i] = float(words[idx].get("t", 0.0))
            cur = idx + 1
    known = [i for i in range(n) if raw[i] is not None]
    res = [0.0] * n
    if not known:                                   # nothing matched -> even spread over [0, last]
        return [round(last * (i + 1) / (n + 1), 3) for i in range(n)]
    for i in range(known[0]):                        # leading unknowns -> 0..first
        res[i] = round(raw[known[0]] * (i + 1) / (known[0] + 1), 3)
    res[known[0]] = raw[known[0]]
    for a, b in zip(known, known[1:]):               # interior gaps -> linear interpolate
        res[b] = raw[b]
        for m in range(a + 1, b):
            res[m] = round(raw[a] + (raw[b] - raw[a]) * (m - a) / (b - a), 3)
    for i in range(known[-1] + 1, n):                # trailing unknowns -> after last known
        res[i] = round(raw[known[-1]] + EPS * (i - known[-1]), 3)
    for i in range(1, n):                            # enforce monotonic non-decreasing
        if res[i] <= res[i - 1]:
            res[i] = round(res[i - 1] + EPS, 3)
    return [round(float(x), 3) for x in res]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_cues.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/cues.py tests/test_cues.py
git commit -m "feat(cues): pure anchor->cue-time resolver (monotonic, interpolated fallback)"
```

---

### Task 2: `scripts/tts.py` — capture edge word timings

**Files:**
- Modify: `scripts/tts.py` (`_edge` at ~line 30; add `_parse_subs`; write `audio/NN.words.json` in `synthesize`)
- Test: `tests/test_tts.py`

**Interfaces:** `_parse_subs(text) -> list[{"w":str,"t":float}]` (pure).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tts.py` (create if absent — it imports `tts`):
```python
import tts

SRT = """1
00:00:00,100 --> 00:00:00,500
Come

2
00:00:02,000 --> 00:00:02,400
Dujiangyan

3
00:00:06,000 --> 00:00:06,300
Leshan
"""
VTT = """WEBVTT

00:00:00.100 --> 00:00:00.500
Come

00:00:02.000 --> 00:00:02.400
Dujiangyan
"""

def test_parse_subs_srt():
    r = tts._parse_subs(SRT)
    assert r == [{"w": "Come", "t": 0.1}, {"w": "Dujiangyan", "t": 2.0}, {"w": "Leshan", "t": 6.0}]

def test_parse_subs_vtt():
    r = tts._parse_subs(VTT)
    assert r == [{"w": "Come", "t": 0.1}, {"w": "Dujiangyan", "t": 2.0}]

def test_parse_subs_empty():
    assert tts._parse_subs("") == [] and tts._parse_subs("WEBVTT\n") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_tts.py -k parse_subs -v`
Expected: FAIL (`_parse_subs` not defined).

- [ ] **Step 3: Implement**

In `scripts/tts.py`, add the parser (near `_edge`):
```python
def _parse_subs(text):
    """Parse an edge-tts subtitle file (SRT 'HH:MM:SS,mmm' or VTT 'HH:MM:SS.mmm') into
    [{'w': cue text, 't': start seconds}] in order. Robust to index lines + a WEBVTT header."""
    import re
    ts_re = re.compile(r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->")
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l.strip() for l in block.splitlines() if l.strip() and l.strip() != "WEBVTT"]
        t, words = None, []
        for l in lines:
            m = ts_re.search(l)
            if m:
                h, mm, s, ms = map(int, m.groups())
                t = round(h * 3600 + mm * 60 + s + ms / 1000.0, 3)
            elif not l.isdigit():
                words.append(l)
        if t is not None and words:
            out.append({"w": " ".join(words), "t": t})
    return out
```
Update `_edge` to also request subtitles:
```python
def _edge(text, out_path, voice):
    # edge-tts neural voice via its CLI module (sync subprocess avoids threading its
    # asyncio into our sync pipeline). Writes an mp3; also writes word-boundary subtitles.
    import sys, os, json
    subs = os.path.splitext(out_path)[0] + ".subs.srt"
    _common.run([sys.executable, "-m", "edge_tts", "--voice", voice, "--text", text,
                 "--write-media", out_path, "--write-subtitles", subs])
    try:
        if os.path.exists(subs):
            words = _parse_subs(open(subs, encoding="utf-8", errors="replace").read())
            if words:
                with open(os.path.splitext(out_path)[0] + ".words.json", "w") as f:
                    json.dump(words, f)
    except Exception as e:
        print(f"[tts] word-timing capture failed for {out_path}: {e}")
```
(If `--write-subtitles` is unsupported by the installed edge-tts, `_common.run` raises → the existing
synth fallback handles it; the words file simply won't exist → render falls back. The implementer:
run one real edge synth and confirm the `.subs.srt` format matches `_parse_subs`; adjust the parser if
edge writes VTT or groups words differently.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_tts.py -k parse_subs -v` then `python3 -m pytest tests/test_tts.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/tts.py tests/test_tts.py
git commit -m "feat(tts): capture edge word timings -> audio/NN.words.json (--write-subtitles + parser)"
```

---

### Task 3: `assets/html/seek.js` — `?cues=&dur=` reveal override

**Files:**
- Modify: `assets/html/seek.js`
- Test: `tests/test_scenes.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_scenes.py`:
```python
@pytest.mark.skipif(not _chrome_present(), reason="no Chrome")
def test_seekjs_cue_override_gates_reveals(tmp_path):
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    js = os.path.join(skill, "assets", "html", "seek.js")
    page = tmp_path / "c.html"
    page.write_text('<!doctype html><html><head><meta charset="utf-8">'
                    f'<link rel="stylesheet" href="file://{base}"></head><body><div class="stage">'
                    '<div class="row reveal-up-sm" data-cue-index="0">A</div>'
                    '<div class="row reveal-up-sm" data-cue-index="1">B</div></div>'
                    f'<script src="file://{js}"></script></body></html>')
    early, late = tmp_path / "e.png", tmp_path / "l.png"
    # dur=4s, cues at 0.2 and 2.0; at p=0.1 (t=0.4s) only point 0 is in; at p=0.6 (t=2.4s) both are
    scenes._chrome_shot(f"file://{page}?cues=0.2,2.0&dur=4&p=0.1", str(early), 960, 540, {})
    scenes._chrome_shot(f"file://{page}?cues=0.2,2.0&dur=4&p=0.6", str(late), 960, 540, {})
    from PIL import Image
    assert Image.open(early).convert("RGB").tobytes() != Image.open(late).convert("RGB").tobytes()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scenes.py -k cue_override -v`
Expected: FAIL (cues not honored → early == late) or skip if no Chrome (then verify Step 4 manually).

- [ ] **Step 3: Implement the override in `seek.js`**

Replace the body so it reads `cues`/`dur` and overrides cued elements' delay + the timeline total:
```javascript
(function () {
  function sec(v) { v = parseFloat(v); return isNaN(v) ? 0 : v; }
  var q = new URLSearchParams(location.search);
  var p = parseFloat(q.get('p')); if (isNaN(p)) p = 1;
  var dur = parseFloat(q.get('dur'));
  var cuesRaw = q.get('cues');
  var cues = cuesRaw ? cuesRaw.split(',').map(parseFloat) : null;
  var els = [].slice.call(document.querySelectorAll('*')).filter(function (el) {
    var n = getComputedStyle(el).animationName; return n && n !== 'none';
  });
  var spans = els.map(function (el) {
    var cs = getComputedStyle(el);
    return { el: el, d: sec(cs.animationDelay), dur: sec(cs.animationDuration) };
  });
  var useCues = cues && !isNaN(dur) && dur > 0;
  if (useCues) {
    spans.forEach(function (s) {
      var ci = s.el.getAttribute('data-cue-index');
      if (ci !== null && cues[+ci] != null && !isNaN(cues[+ci])) s.d = cues[+ci];
    });
  }
  var total = useCues ? dur : spans.reduce(function (m, s) { return Math.max(m, s.d + s.dur); }, 0.001);
  var T = p * total;
  spans.forEach(function (s) {
    s.el.style.animationDelay = (s.d - T) + 's';
    s.el.style.animationPlayState = 'paused';
  });
})();
```

- [ ] **Step 4: Run the test (+ confirm existing seek behavior)**

Run: `python3 -m pytest tests/test_scenes.py -k "cue_override or reveal or kenburns or themeable" -q`
Expected: PASS (the cue test with Chrome; the existing reveal/kenburns/theme tests stay green — no `cues` param → unchanged path).

- [ ] **Step 5: Commit**

```bash
git add assets/html/seek.js tests/test_scenes.py
git commit -m "feat(seek.js): ?cues=&dur= override — reveal [data-cue-index] elements at their cue time"
```

---

### Task 4: `scripts/scenes.py` `render_html` — cue-aware capture (+ fingerprint)

**Files:**
- Modify: `scripts/scenes.py` (`render_html`), `scripts/render.py` (`_fingerprint`)
- Test: `tests/test_scenes.py`, `tests/test_render.py`

**Interfaces (Consumes):** `cues.resolve_cues` (Task 1); `audio/NN.words.json` (Task 2); seek.js `?cues=&dur=` (Task 3).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scenes.py`:
```python
def test_render_html_cue_capture_passes_cues(tmp_path, monkeypatch):
    # a page with two cued points + a words.json -> render_html should resolve cues and pass ?cues= to chrome
    import json
    out = tmp_path; (out / "audio").mkdir(); (out / "pages").mkdir()
    (out / "audio" / "03.words.json").write_text(json.dumps(
        [{"w": "alpha", "t": 0.5}, {"w": "beta", "t": 3.0}]))
    (out / "pages" / "p.html").write_text('<div class="stage">'
        '<div class="row reveal-up-sm" data-cue-index="0" data-cue="alpha">A</div>'
        '<div class="row reveal-up-sm" data-cue-index="1" data-cue="beta">B</div></div>')
    seen = []
    monkeypatch.setattr(scenes, "_chrome_shot", lambda url, o, w, h, m: (seen.append(url),
                        __import__("pathlib").Path(o).write_bytes(b"\x89PNG\r\n")))
    meta = {"_out": str(out), "fps": 30}
    scenes.render_html({"html": "pages/p.html", "anim_seconds": 1.0}, meta, 1920, 1080, 120, str(out / "wd"), 3)
    assert any("cues=" in u and "dur=" in u for u in seen), "cue params not passed"

def test_render_html_no_words_uses_anim_path(tmp_path, monkeypatch):
    out = tmp_path; (out / "pages").mkdir()
    (out / "pages" / "p.html").write_text('<div class="stage"><div class="title reveal-up">X</div></div>')
    seen = []
    monkeypatch.setattr(scenes, "_chrome_shot", lambda url, o, w, h, m: (seen.append(url),
                        __import__("pathlib").Path(o).write_bytes(b"\x89PNG\r\n")))
    scenes.render_html({"html": "pages/p.html", "anim_seconds": 1.0}, {"_out": str(out), "fps": 30},
                       1920, 1080, 60, str(out / "wd"), 5)
    assert seen and all("cues=" not in u for u in seen), "should use anim path (no cues)"
```
Add to `tests/test_render.py`:
```python
def test_fingerprint_includes_words_json(tmp_path):
    import render
    out = tmp_path; (out / "audio").mkdir()
    slide = {"index": 3, "type": "html", "props": {"html": "pages/p.html"}, "audio": "audio/03.mp3"}
    meta = {"_out": str(out)}
    a = render._fingerprint(slide, meta, 1920, 1080, 2, True, False)
    (out / "audio" / "03.words.json").write_text('[{"w":"x","t":0.1}]')   # add timings
    assert render._fingerprint(slide, meta, 1920, 1080, 2, True, False) != a   # cache busts
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_scenes.py -k "cue_capture or no_words_uses" tests/test_render.py -k fingerprint_includes_words -v`
Expected: FAIL (render_html ignores words; fingerprint lacks words.json).

- [ ] **Step 3: Implement `render_html` cue-awareness**

In `scripts/scenes.py`, replace `render_html` with the cue-aware version (keeps the existing path when no cues):
```python
def render_html(props, meta, W, H, frames, workdir, index):
    """Render a designed HTML page (paused CSS reveals) into a frame sequence via headless Chrome.
    If a per-scene word-timing file (audio/NN.words.json) exists AND the page has [data-cue-index]
    points, reveal each point at its spoken cue time across the FULL scene (audio-synced); otherwise
    animate the reveals over anim_seconds then hold (the default)."""
    import json, re
    import cues as _cues
    src = os.path.join(meta["_out"], props["html"])
    fps = meta.get("fps", 30)
    dur = frames / float(fps)
    html = open(src, encoding="utf-8", errors="replace").read()
    words_path = os.path.join(meta["_out"], "audio", f"{index:02d}.words.json")
    # collect cued points: (cue-index, anchor) where anchor = data-cue="..." (required on cued points)
    pts = re.findall(r'data-cue-index="(\d+)"[^>]*?data-cue="([^"]*)"', html)
    pts += [(i, a) for (a, i) in re.findall(r'data-cue="([^"]*)"[^>]*?data-cue-index="(\d+)"', html)]
    cue_param = None
    if pts and os.path.exists(words_path):
        try:
            words = json.load(open(words_path))
            anchors = [a for _, a in sorted(((int(i), a) for i, a in pts), key=lambda x: x[0])]
            ctimes = _cues.resolve_cues(words, anchors)
            cue_param = ",".join(f"{t:.3f}" for t in ctimes)
        except Exception:
            cue_param = None
    pat = os.path.join(workdir, f"scene_{index:02d}_%04d.png")
    if cue_param is not None:
        # capture a fresh frame near each cue's reveal window (~0.6s); hold (copy) elsewhere
        ctimes = [float(x) for x in cue_param.split(",")]
        burst = 0.6
        def is_reveal(t):
            return t <= 0.001 or any(c <= t <= c + burst for c in ctimes)
        last = None
        for i in range(frames):
            outp = pat % i
            t = i / float(fps)
            if is_reveal(t) or last is None:
                p = min(1.0, t / dur)
                _chrome_shot(f"file://{src}?p={p:.4f}&cues={cue_param}&dur={dur:.3f}", outp, W, H, meta)
                last = outp
            else:
                shutil.copyfile(last, outp)
        return pat
    # default path (unchanged): animate over anim_seconds, then hold
    anim = float(props.get("anim_seconds", 0.8))
    reveal_frames = max(1, min(frames, int(round(anim * fps))))
    settle = None
    for i in range(frames):
        out = pat % i
        p = 1.0 if i >= reveal_frames - 1 else i / max(1, reveal_frames - 1)
        if p >= 1.0 and settle is not None:
            shutil.copyfile(settle, out); continue
        _chrome_shot(f"file://{src}?p={p:.4f}", out, W, H, meta)
        if p >= 1.0:
            settle = out
    return pat
```
In `scripts/render.py` `_fingerprint`, add the words-file stat next to the html/theme stats:
```python
        "html": stat((slide.get("props") or {}).get("html")),
        "theme": stat("theme.css"),   # re-theming (theme.py) busts html-scene clips
        "words": stat(os.path.join("audio", f"{slide.get('index'):02d}.words.json")),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -k "cue_capture or no_words_uses" tests/test_render.py -k fingerprint_includes_words -v`
Run: `python3 -m pytest tests/test_scenes.py tests/test_render.py -q` (existing render/scene tests stay green).

- [ ] **Step 5: Commit**

```bash
git add scripts/scenes.py scripts/render.py tests/test_scenes.py tests/test_render.py
git commit -m "feat(render_html): audio-synced cue capture (resolve cues, reveal at spoken time) + words.json fingerprint"
```

---

### Task 5: authoring — `data-cue` points (`html-pages.md`, `content-planner.md`)

**Files:**
- Modify: `references/html-pages.md`, `agents/content-planner.md`

- [ ] **Step 1: Add the data-cue authoring guidance**

Append to `references/html-pages.md`:
```markdown
## Audio-synced reveals (points appear when spoken)
On a multi-point page, tag each point's reveal element with `data-cue-index="0|1|2…"` (in SPOKEN
order) and `data-cue="<the spoken anchor phrase>"` — the word/phrase in the narration that introduces
that point (usually the point's keyword; set it to a different phrase only when the visible label is
not spoken verbatim). Example:
```html
<div class="row reveal-up-sm" data-cue-index="0" data-cue="Dujiangyan"> … </div>
<div class="row reveal-up-sm" data-cue-index="1" data-cue="Leshan"> … </div>
```
When edge-tts word timings exist (`audio/NN.words.json`), `render_html` reveals each point exactly when
its anchor is spoken (across the whole scene). With no word timings (macOS `say`, or a missing anchor)
it falls back to the paced `anim_seconds` stagger. Heroes/title pages don't use `data-cue`. The anchor
must be a phrase actually present in that scene's narration.
```

- [ ] **Step 2: Add the planner cue field**

In `agents/content-planner.md`, in the per-beat fields, add: each point in a multi-point beat may carry
an optional `cue` — the spoken anchor phrase that should trigger its reveal (defaults to the point's
label keyword). It must be a phrase the beat's narration actually says, in spoken order.

- [ ] **Step 3: Verify + full suite + commit**

Run:
```bash
grep -n "Audio-synced reveals\|data-cue-index\|data-cue=" references/html-pages.md
grep -n "cue" agents/content-planner.md | head
python3 -m pytest -q
```
Expected: guidance present; full suite PASSES.
```bash
git add references/html-pages.md agents/content-planner.md
git commit -m "docs: audio-synced reveal authoring (data-cue-index/data-cue points + planner cue field)"
```

---

## Self-Review

**Spec coverage:** `cues.resolve_cues` pure resolver (Task 1) ✓; tts `_parse_subs` + `--write-subtitles` + words.json (Task 2) ✓; seek.js `?cues=&dur=` override (Task 3) ✓; render_html cue-aware capture + words.json fingerprint (Task 4) ✓; html-pages/content-planner authoring (Task 5) ✓; fallback paths (no words / no cued points → anim path) — Tasks 4 ✓; faithfulness/seek-safe (CSS-only, paused) preserved (Tasks 3/4) ✓. Out-of-scope (one-point sub-scenes, non-edge timings) has no task.

**Placeholder scan:** none — `cues.py`, `_parse_subs`, the seek.js body, the `render_html` rewrite, and all tests are complete + runnable. The Task-2 note to verify the live edge subtitle format is an explicit implementer instruction, not a placeholder.

**Type consistency:** `resolve_cues(words, anchors) -> list[float]` (Task 1) is called by `render_html` (Task 4) with `words` from `audio/NN.words.json` (written by Task 2's `_parse_subs`, shape `[{"w","t"}]`) and `anchors` parsed from `data-cue` attributes (authored per Task 5). The `?cues=&dur=` URL params produced by `render_html` (Task 4) are exactly what seek.js consumes (Task 3). `data-cue-index` is written by the author (Task 5), read by seek.js (Task 3) and render_html's regex (Task 4). `_fingerprint`'s new `words` stat (Task 4) mirrors the existing `html`/`theme` stat pattern.
