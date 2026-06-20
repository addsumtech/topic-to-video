# Educational Content + Informative Visuals (Increment 1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make slides-to-video design *content* before authoring — add a content-planner director agent plus two new **informative** visual renderers (`keypoints`, `compare`) so conceptual beats teach instead of falling back to empty AI photos, at an energetic many-cuts rhythm, all faithful.

**Architecture:** Two new deterministic renderers in `scripts/scenes.py` (PIL `keypoints` like `render_title`; matplotlib `compare` like `render_chart`) plug into the existing animated-scene path unchanged (`render._render_scene` → `getattr(scenes,"render_"+type)`; `_fingerprint` already hashes `type`+`props`). `storyboard.py` learns the two types. Three docs land the workflow: a new `agents/content-planner.md` director, a `SKILL.md` step 3.5 + informative-first/pacing policy, and a critic rule **R2** (audio↔visual coherence).

**Tech Stack:** Python 3, Pillow, matplotlib (Agg), pytest. No new dependency.

## Global Constraints
- Renderers are **PURE functions of the frame index** — no randomness, no wall-clock. Signature: `render_<type>(props, meta, W, H, frames, workdir, index) -> pattern_str`; frames written via `_save_frames(draw_fn, frames, workdir, index)` as `scene_{index:02d}_%04d.png`.
- **Faithful-by-construction:** render ONLY the given props (no invented text/values/labels).
- Reuse existing helpers in `scenes.py`: `_ease`, `_hex_rgb`, `_font` (PIL/CJK), `_save_frames`, `_mpl_font`, `_chart_values`, `BG`, `FG`.
- **Deterministic:** identical props ⇒ byte-identical frames (the test asserts this with `_pix`).
- New types route through the EXISTING dispatch + fingerprint — **no `render.py` change**.
- Faithfulness preserved everywhere: data stays in real charts; the planner traces every beat to the material; nothing invented. Existing suite stays green.

---

### Task 1: `render_keypoints` (PIL kinetic labeled points)

**Files:**
- Modify: `scripts/scenes.py` (add `render_keypoints` after `render_title`)
- Test: `tests/test_scenes.py`

**Interfaces:**
- Consumes: `_ease`, `_hex_rgb`, `_font`, `_save_frames`, `BG`, `FG` (existing).
- Produces: `render_keypoints(props, meta, W, H, frames, workdir, index) -> pattern_str`. props: `{title?:str, points:[{label:str, sub?:str}] (1–5), accent?:"#rrggbb"}`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scenes.py`:
```python
def test_keypoints_writes_exact_frames_and_nonblank(tmp_path):
    props = {"title": "市场可争夺的部分",
             "points": [{"label": "对外发射 ≈ 42 次", "sub": "可被争夺"},
                        {"label": "且多为政府 / 国安订单"}], "accent": "#4C9BE8"}
    pat = scenes.render_keypoints(props, META_ZH, 1280, 720, 12, str(tmp_path), 4)
    files = sorted(f for f in os.listdir(tmp_path) if f.endswith(".png"))
    assert len(files) == 12 and files[0] == "scene_04_0000.png"
    last = Image.open(pat % 11).convert("RGB")
    assert last.size == (1280, 720)
    assert last.getextrema() != ((0, 0), (0, 0), (0, 0))   # text drawn
    assert "%04d" in pat

def test_keypoints_deterministic(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    props = {"points": [{"label": "One"}, {"label": "Two"}, {"label": "Three"}]}
    pa = scenes.render_keypoints(props, META, 640, 360, 6, str(a), 1)
    pb = scenes.render_keypoints(props, META, 640, 360, 6, str(b), 1)
    assert all(_pix(pa % i) == _pix(pb % i) for i in range(6))

def test_keypoints_single_point_and_single_frame(tmp_path):
    pat = scenes.render_keypoints({"points": [{"label": "Solo"}]}, META, 640, 360, 1, str(tmp_path), 2)
    last = Image.open(pat % 0).convert("RGB")
    assert last.getextrema() != ((0, 0), (0, 0), (0, 0))    # settled, non-blank
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/donghanglyu/.claude/skills/slides-to-video && python3 -m pytest tests/test_scenes.py -k keypoints -v`
Expected: FAIL (`module 'scenes' has no attribute 'render_keypoints'`).

- [ ] **Step 3: Write the implementation**

In `scripts/scenes.py`, add after `render_title` (after its `return _save_frames(...)` line):
```python
def render_keypoints(props, meta, W, H, frames, workdir, index):
    """Conceptual beat -> kinetic labeled points that reveal one-by-one. PURE; renders only props."""
    title = props.get("title")
    points = props.get("points", [])
    accent = _hex_rgb(props.get("accent"))
    fps = meta.get("fps", 30)
    intro = max(1, int(0.5 * fps))                  # each row fades/slides in over ~0.5s
    stagger = max(1, int(0.35 * fps))               # rows appear staggered
    x = int(W * 0.10)
    tfont = _font(meta, title or " ", int(H * 0.058))
    lfont = _font(meta, "x", int(H * 0.050))
    sfont = _font(meta, "x", int(H * 0.030))
    top = int(H * 0.30) if title else int(H * 0.24)
    row_h = int(H * 0.135)

    def _prog(i, delay):
        if frames <= 1:
            return 1.0
        return _ease((i - delay) / max(1, min(intro, frames - 1)))

    def draw(i, n):
        base = Image.new("RGBA", (W, H), BG + (255,))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if title:
            a0 = int(255 * _prog(i, 0))
            d.text((x, int(H * 0.15)), title, font=tfont, fill=FG + (a0,))
        for k, pnt in enumerate(points):
            p = _prog(i, (k + 1) * stagger)
            if p <= 0:
                continue
            a = int(255 * p); dx = int((1 - p) * (W * 0.02))
            y = top + k * row_h
            mr = max(4, int(H * 0.018))
            d.rectangle([x - dx, y + int(row_h * 0.18), x - dx + mr, y + int(row_h * 0.18) + mr * 3],
                        fill=accent + (a,))
            lx = x - dx + mr + int(W * 0.018)
            d.text((lx, y), str(pnt.get("label", "")), font=lfont, fill=FG + (a,))
            if pnt.get("sub"):
                d.text((lx, y + int(row_h * 0.52)), str(pnt["sub"]), font=sfont,
                       fill=(150, 160, 175, a))
        return Image.alpha_composite(base, layer).convert("RGB")

    return _save_frames(draw, frames, workdir, index)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -k keypoints -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/scenes.py tests/test_scenes.py
git commit -m "feat(scenes): render_keypoints — kinetic labeled points for conceptual beats"
```

---

### Task 2: `render_compare` (matplotlib split/versus breakdown)

**Files:**
- Modify: `scripts/scenes.py` (add `render_compare` after `render_chart`)
- Test: `tests/test_scenes.py`

**Interfaces:**
- Consumes: `_ease`, `_chart_values`, `_mpl_font`, `_save_frames` (existing).
- Produces: `render_compare(props, meta, W, H, frames, workdir, index) -> pattern_str`. props: `{title?:str, kind:"split"|"versus", parts:[{label:str, value:num, note?:str}] (≥2), total?:num, accent?:"#rrggbb"}`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scenes.py`:
```python
def test_compare_split_writes_frames_and_nonblank(tmp_path):
    props = {"title": "2025 年的 165 次发射", "kind": "split", "total": 165,
             "parts": [{"label": "自用 Starlink", "value": 123, "note": "不可争夺"},
                       {"label": "对外（可争夺）", "value": 42}], "accent": "#E8590C"}
    pat = scenes.render_compare(props, META_ZH, 1280, 720, 10, str(tmp_path), 6)
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".png")]) == 10
    last = Image.open(pat % 9).convert("RGB")
    assert last.size == (1280, 720)
    assert last.getextrema() != ((0, 0), (0, 0), (0, 0))

def test_compare_versus_writes_frames(tmp_path):
    props = {"kind": "versus", "parts": [{"label": "A", "value": 10}, {"label": "B", "value": 25}]}
    pat = scenes.render_compare(props, META, 1280, 720, 8, str(tmp_path), 2)
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".png")]) == 8
    assert Image.open(pat % 7).convert("RGB").getextrema() != ((0, 0), (0, 0), (0, 0))

def test_compare_deterministic(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    props = {"kind": "split", "parts": [{"label": "X", "value": 3}, {"label": "Y", "value": 7}]}
    pa = scenes.render_compare(props, META, 640, 360, 5, str(a), 1)
    pb = scenes.render_compare(props, META, 640, 360, 5, str(b), 1)
    assert all(_pix(pa % i) == _pix(pb % i) for i in range(5))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_scenes.py -k compare -v`
Expected: FAIL (`module 'scenes' has no attribute 'render_compare'`).

- [ ] **Step 3: Write the implementation**

In `scripts/scenes.py`, add after `render_chart` (after its `return _save_frames(...)` line):
```python
def render_compare(props, meta, W, H, frames, workdir, index):
    """Decomposition/contrast -> a labeled 'split' (100% stacked bar) or 'versus' (side-by-side).
    PURE; values come straight from props (faithful)."""
    kind = props.get("kind", "split")
    parts = props.get("parts", [])
    labels = [str(p.get("label", "")) for p in parts]
    values = [p["value"] for p in parts]
    title = props.get("title")
    famly = _mpl_font(meta)
    dpi = 100; figsize = (W / dpi, H / dpi)
    palette = [props.get("accent", "#4C9BE8"), "#E8590C", "#46A758", "#9B7EDE", "#C0C8D4"]

    def draw(i, n):
        p = i / max(1, n - 1) if n > 1 else 1.0
        e = _ease(p)
        fig = plt.figure(figsize=figsize, dpi=dpi); fig.patch.set_facecolor("#0d1117")
        ax = fig.add_subplot(111); ax.set_facecolor("#0d1117")
        if title:
            ax.set_title(title, color="white", fontsize=18, fontfamily=famly, pad=16)
        if kind == "versus":
            cur = _chart_values(values, p)
            ax.bar(labels, cur, color=[palette[k % len(palette)] for k in range(len(parts))])
            ax.set_ylim(0, (max(values + [0]) * 1.15 or 1))
            for sp in ax.spines.values():
                sp.set_color("#3a4150")
            ax.tick_params(colors="#c0c8d4")
            for t in ax.get_xticklabels():
                t.set_fontfamily(famly)
        else:  # split — one 100% stacked horizontal bar
            ax.axis("off")
            total = props.get("total") or sum(values) or 1
            left = 0.0
            for k, v in enumerate(values):
                w = (v / total) * e
                ax.barh([0], [w], left=[left], color=palette[k % len(palette)], height=0.5)
                if w > 0.05:
                    ax.text(left + w / 2, 0, f"{labels[k]}\n{v:g}", ha="center", va="center",
                            color="white", fontsize=13, fontfamily=famly)
                left += w
            ax.set_xlim(0, 1); ax.set_ylim(-0.5, 0.5)
        fig.tight_layout(); fig.canvas.draw()
        img = Image.frombytes("RGBA", fig.canvas.get_width_height(),
                              bytes(fig.canvas.buffer_rgba())).convert("RGB")
        plt.close(fig)
        return img.resize((W, H), Image.LANCZOS) if img.size != (W, H) else img

    return _save_frames(draw, frames, workdir, index)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -k compare -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/scenes.py tests/test_scenes.py
git commit -m "feat(scenes): render_compare — labeled split/versus breakdown"
```

---

### Task 3: storyboard schema for `keypoints` + `compare`

**Files:**
- Modify: `scripts/storyboard.py`
- Test: `tests/test_storyboard.py`

**Interfaces:**
- Consumes: `render_keypoints`, `render_compare` (Tasks 1–2) — proves dispatch resolves them.
- Produces: `keypoints`/`compare` accepted by `validate`; bad props raise `StoryboardError`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_storyboard.py`:
```python
import scenes  # dispatch-resolution check

def test_validate_keypoints_ok_and_dispatchable():
    d = {"meta": {}, "slides": [sb.new_scene(1, "keypoints",
         {"title": "T", "points": [{"label": "a", "sub": "s"}, {"label": "b"}]}, "n")]}
    sb.validate(d)
    assert callable(getattr(scenes, "render_keypoints"))   # animated dispatch will resolve it

def test_validate_keypoints_bad():
    for bad in [{"points": []}, {"points": [{"sub": "no label"}]}, {"points": [{"label": ""}]},
                {"points": [{"label": "x"}] * 6}]:
        with pytest.raises(sb.StoryboardError):
            sb.validate({"meta": {}, "slides": [sb.new_scene(1, "keypoints", bad, "n")]})

def test_validate_compare_ok_and_dispatchable():
    d = {"meta": {}, "slides": [sb.new_scene(1, "compare",
         {"kind": "split", "parts": [{"label": "A", "value": 3}, {"label": "B", "value": 7}]}, "n")]}
    sb.validate(d)
    assert callable(getattr(scenes, "render_compare"))

def test_validate_compare_bad():
    for bad in [{"kind": "pie", "parts": [{"label": "A", "value": 1}, {"label": "B", "value": 2}]},
                {"kind": "split", "parts": [{"label": "A", "value": 1}]},
                {"kind": "split", "parts": [{"label": "A", "value": 1}, {"label": "B"}]}]:
        with pytest.raises(sb.StoryboardError):
            sb.validate({"meta": {}, "slides": [sb.new_scene(1, "compare", bad, "n")]})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_storyboard.py -k "keypoints or compare" -v`
Expected: FAIL (unknown type `keypoints`/`compare`).

- [ ] **Step 3: Write the implementation**

In `scripts/storyboard.py`, update the two sets (lines 8–9):
```python
VALID_SCENE_TYPES = {"slide", "title", "chart", "timeline", "keypoints", "compare"}
ANIMATED_TYPES = {"title", "chart", "timeline", "keypoints", "compare"}
```
In `_validate_props`, after the `timeline` branch (before the function ends), add:
```python
    elif t == "keypoints":
        pts = p.get("points")
        if not isinstance(pts, list) or not (1 <= len(pts) <= 5):
            raise StoryboardError(f"slide {s.get('index')}: keypoints needs 1-5 'points'")
        for it in pts:
            if not (isinstance(it, dict) and isinstance(it.get("label"), str) and it["label"].strip()):
                raise StoryboardError(f"slide {s.get('index')}: each keypoint needs a non-empty 'label' string")
    elif t == "compare":
        if p.get("kind") not in {"split", "versus"}:
            raise StoryboardError(f"slide {s.get('index')}: compare 'kind' must be 'split' or 'versus'")
        parts = p.get("parts")
        if not isinstance(parts, list) or len(parts) < 2:
            raise StoryboardError(f"slide {s.get('index')}: compare needs a 'parts' list of >=2 items")
        for it in parts:
            if not (isinstance(it, dict) and isinstance(it.get("label"), str) and _is_num(it.get("value"))):
                raise StoryboardError(f"slide {s.get('index')}: each compare part needs a 'label' string + numeric 'value'")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_storyboard.py -v`
Expected: PASS (new + existing).

- [ ] **Step 5: Commit**

```bash
git add scripts/storyboard.py tests/test_storyboard.py
git commit -m "feat(storyboard): validate keypoints + compare scene types"
```

---

### Task 4: content-planner agent (`agents/content-planner.md`, new)

**Files:**
- Create: `agents/content-planner.md`

- [ ] **Step 1: Write the agent**

Create `agents/content-planner.md` verbatim:
```markdown
# Content Planner (director / educator)

You are the DIRECTOR of a short educational video. Given a deep **comprehension brief**
of the source material (+ the slide text and any source docs, the audience, goal, language,
and a target length), you design the *content* — what the video teaches and how it is shown —
BEFORE any narration is written. You do not write final narration; you design beats.

## Inputs
- The comprehension brief (one-sentence message, key contributions, method essence, and per-slide point).
- The raw slide text + any source material; audience, goal, `meta.language`, target seconds.

## Output — a CONTENT PLAN (JSON)
```json
{ "arc": "hook → build → payoff → takeaway (one line)",
  "beats": [
    { "id": 1,
      "learning_point": "the ONE idea this beat teaches",
      "source_ref": "slide 2 / paper §3 / web-verified — REQUIRED, no beat without a source",
      "visual": { "type": "compare", "props": { } },
      "narration_intent": "what the line must convey (not final words)",
      "est_seconds": 5 } ] }
```

## Rules (your rubric)
1. **Deep understanding first.** Every `learning_point` must trace to the material via
   `source_ref`. Never invent facts, numbers, names, or citations. If the material does not
   support a point, drop it.
2. **Informative-visual selection.** Choose the MOST informative `visual.type` for the point:
   - a number / trend → `chart` (`props.kind` bars/line/counter)
   - a decomposition or contrast → `compare` (`kind` split/versus, `parts`)
   - a conceptual claim or short list → `keypoints` (1–5 `points`, each a `label` (+ optional `sub`))
   - a sequence of dated events → `timeline`
   - a section / transition → `title`
   `visual.type ∈ {title, chart, timeline, keypoints, compare, slide}`.
   **Never** assign a decorative photoreal image to a beat that states a fact. Photoreal
   (`slide` + `image_prompt`, tagged `broll`) is allowed ONLY as a rare atmospheric opener or
   closer — at most one or two in the whole video — and never as the carrier of a claim.
3. **Energetic pacing.** Many short beats; ONE idea per beat; `est_seconds` 3–6. Split a dense
   point into two beats rather than holding one long frame. Target beat count ≈
   `target_seconds / 4`.
4. **Earn its place.** Every beat must teach something. Cut filler, throat-clearing, and
   restatement.
5. **Audio↔visual.** Write `narration_intent` so the spoken line will MATCH what is on screen
   (the beat's visual). The downstream critic enforces this.

## Output contract
Return ONLY the JSON content plan (no prose around it). The assistant maps each `beat.visual`
to a storyboard scene and authors the short narration from `narration_intent`; the critic then
checks faithfulness, subtitles, and audio↔visual coherence.
```

- [ ] **Step 2: Verify + commit**

Run: `grep -n "Informative-visual selection\|source_ref\|Energetic pacing\|keypoints\|compare" agents/content-planner.md` (expect matches).
```bash
git add agents/content-planner.md
git commit -m "feat(agents): content-planner director — informative beats from deep understanding"
```

---

### Task 5: SKILL.md — step 3.5 planner, informative-first, pacing, audio↔visual

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Add the content-planner to Pipeline / agents and a workflow step**

In `SKILL.md`, in the `## Pipeline scripts` or agents area, add a line noting the new agent, then insert a new workflow step between step 3 (Understand deeply) and step 4 (Author narration):
```markdown
3.5. **Content plan (director) — design the video as CONTENT before authoring.** Dispatch
   `agents/content-planner.md` on the comprehension brief + material. It returns an ordered set
   of **informative beats** — each with a learning point (traced to the material), the most
   informative visual (`chart`/`compare`/`keypoints`/`timeline`/`title`, NOT decorative photos),
   a narration intent, and a short `est_seconds`. Build the storyboard scenes from the plan
   (**informative-first**); author the short per-beat narration in step 4.
   🔴 **CHECKPOINT · 🛑 STOP:** show the content plan (arc + beats + chosen visuals) and get the
   user's OK before authoring narration.
```

- [ ] **Step 2: Add the informative-first + pacing policy**

In `SKILL.md` `## Guardrails`, add:
```markdown
- **Informative-first visuals.** A beat that states a fact or concept uses an INFORMATIVE
  visual — `chart`, `compare` (split/versus breakdown), `keypoints` (kinetic labeled points),
  or `timeline` — never a decorative photoreal image. AI photoreal (`image_prompt`/`broll`) is
  allowed ONLY as a rare atmospheric opener/closer, never as the carrier of a claim.
- **Energetic pacing.** Prefer MANY short beats (~3–6s, one idea each; ≈ `video_seconds/4`
  beats) over a few long holds; the animated renderers' internal reveals keep the screen moving.
- **Audio↔visual.** Each narration line must MATCH what is on screen (its beat's visual) — the
  critic (R2) fails a mismatch.
```

- [ ] **Step 3: Verify + full suite + commit**

Run:
```bash
grep -n "Content plan (director)\|Informative-first\|Energetic pacing\|Audio↔visual" SKILL.md
python3 -m pytest -q
```
Expected: grep shows the additions; full suite PASSES.
```bash
git add SKILL.md
git commit -m "docs(skill): step 3.5 content-planner + informative-first/pacing/audio-visual policy"
```

---

### Task 6: critic R2 — audio↔visual coherence + informative-first

**Files:**
- Modify: `agents/critic.md`

- [ ] **Step 1: Add rule R2**

In `agents/critic.md`, after the existing R1e rule, add:
```markdown
### R2 — Audio↔visual coherence & informative-first
The video is now planned as content (see SKILL.md step 3.5 + `agents/content-planner.md`).
Check, per scene:
- **Audio↔visual match.** The narration must describe / be supported by what is ON SCREEN
  (the scene's visual). **FAIL** a mismatch — e.g. a generic photo or an unrelated visual under
  a specific factual claim (the classic "satellite photo under a government-orders line").
- **Informative-first.** A beat that states a fact or concept must use an informative visual
  (`chart`/`compare`/`keypoints`/`timeline`), NOT decorative photoreal b-roll. **FAIL** a
  factual/conceptual beat rendered as a photo where an informative visual should carry the
  point. Photoreal (`broll`) is allowed only as a rare atmospheric opener/closer.
- **Sourcing.** Each beat's claim must trace to the material (the planner's `source_ref`);
  flag any unsourced or unsupported claim (cross-ref R1d data faithfulness, R1e imagery).
Apply required EDITS (relabel the visual to an informative type, or fix the narration to match)
and re-check until clean.
```

- [ ] **Step 2: Verify + full suite + commit**

Run:
```bash
grep -n "R2 — Audio↔visual\|Informative-first\|Audio↔visual match" agents/critic.md
python3 -m pytest -q
```
Expected: grep shows R2; full suite PASSES (prose change).
```bash
git add agents/critic.md
git commit -m "docs(critic): R2 audio<->visual coherence + informative-first check"
```

---

## Self-Review

**Spec coverage:** content-planner agent (Task 4) ✓; `keypoints` (Task 1) ✓; `compare` (Task 2) ✓; schema for both + dispatch-resolution (Task 3) ✓; step 3.5 + informative-first + pacing + audio↔visual policy (Task 5) ✓; critic R2 (Task 6) ✓; faithful-by-construction renderers (Tasks 1/2 render only props; tests assert determinism) ✓; energetic pacing (planner rubric + SKILL guardrail) ✓; "no render.py change" — confirmed (new types route through the existing `getattr(scenes,"render_"+type)` dispatch + `_fingerprint`, verified by Task 3's dispatch-resolution assertion). Out-of-scope items (diagram/flow renderer, AI-demotion automation, plan→storyboard compiler) correctly have NO task.

**Placeholder scan:** none — every code/test step is complete and runnable; the two agent/doc tasks contain the full verbatim text.

**Type consistency:** renderer signature `(props, meta, W, H, frames, workdir, index) -> pattern` matches existing `render_title`/`render_chart` and the dispatch in `render._render_scene`. `keypoints` props (`points[].label/sub`) and `compare` props (`kind`, `parts[].label/value`, `total`) are identical across the renderer (Tasks 1/2), the schema validation (Task 3), the planner's visual menu (Task 4), and the critic (Task 6). `VALID_SCENE_TYPES`/`ANIMATED_TYPES` extended in one place (Task 3). `_is_num` (used in Task 3) already exists in `storyboard.py`.
