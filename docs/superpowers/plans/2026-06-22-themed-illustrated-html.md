# Creative Themed Illustrated HTML Video — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the HTML-pages video tier creative + topic-fitting and general: a topic-driven color theme (`theme.py` → `theme.css`), a content-planner that re-conceives the material (not slide-order) and assigns selective imagery, and themeable illustrated/animated pages.

**Architecture:** A new `scripts/theme.py` derives a curated palette (sample `frames/` else topic) and writes `theme.css`. `assets/html/base.css`+`motifs.css` are refactored so every color is a semantic CSS var (`--bg --surface --fg --muted --accent --accent2 --rule --scrim`, with `--blue/--orange/--panel` back-compat aliases) and gain `.kenburns`/`.split`. The content-planner re-conceives the arc + proposes a theme + per-beat `media`. Docs (`content-planner.md`, `references/html-pages.md`, `SKILL.md`) wire it together. `render_html`/`seek.js` are unchanged.

**Tech Stack:** Python 3 (PIL, stdlib `colorsys`), CSS, headless Chrome, pytest. No new dependency.

## Global Constraints
- **Themeable:** every color in `base.css`/`motifs.css` component classes is `var(--…)`; `theme.css` (linked AFTER base.css) overrides `:root`. Back-compat aliases `--blue:var(--accent)`, `--orange:var(--accent2)`, `--panel:var(--surface)` keep existing pages working. base.css defaults = current dark look.
- **`theme.py` is deterministic** (no randomness/wall-clock); derives a **curated** palette (clean bg/fg/surface with **≥ ~7:1 fg/bg contrast**), not raw pixels; samples `frames/` when present, else uses passed `--mode/--accent/--bg`.
- **Re-conception stays faithful:** every beat traces to `source_ref`; no invented facts. Per-beat `media` images are generic atmospheric **broll** (no fabricated specific landmark/logo/text; data stays as on-page text). Critic R1e/R2 unchanged.
- **Motion:** `.kenburns` is a paused, seekable CSS transform (seek.js freezes it). No `render.py`/`render_html`/`seek.js` change.
- Existing tests stay green.

---

### Task 1: `scripts/theme.py` — topic palette → `theme.css`

**Files:**
- Create: `scripts/theme.py`
- Test: `tests/test_theme.py` (new)

**Interfaces (Produces):**
- `derive_theme(out_dir, mode=None, accent=None, accent2=None, bg=None) -> dict` (keys: mode, bg, surface, fg, muted, accent, accent2, scrim — all `#hex` except mode)
- `write_theme_css(theme: dict, path: str) -> None`
- `_contrast(rgb_a, rgb_b) -> float`; CLI `main()`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_theme.py`:
```python
import os
from PIL import Image
import theme

def _frame(path, rgb):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGB", (160, 90), rgb).save(path)

def test_light_frames_give_light_mode(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (245, 240, 228))   # warm near-white
    t = theme.derive_theme(str(tmp_path))
    assert t["mode"] == "light"
    assert theme._lum(theme._hex2rgb(t["bg"])) > 0.6                # bg is light

def test_dark_frames_give_dark_mode(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (12, 16, 24))
    t = theme.derive_theme(str(tmp_path))
    assert t["mode"] == "dark"
    assert theme._lum(theme._hex2rgb(t["bg"])) < 0.4

def test_contrast_enforced(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (245, 240, 228))
    t = theme.derive_theme(str(tmp_path))
    assert theme._contrast(theme._hex2rgb(t["fg"]), theme._hex2rgb(t["bg"])) >= 7.0

def test_overrides_and_no_frames(tmp_path):
    t = theme.derive_theme(str(tmp_path), mode="dark", accent="#4C9BE8")   # no frames
    assert t["mode"] == "dark" and t["accent"].lower() == "#4c9be8"

def test_writes_theme_css_with_all_vars(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (200, 70, 30))
    t = theme.derive_theme(str(tmp_path))
    p = str(tmp_path / "theme.css"); theme.write_theme_css(t, p)
    css = open(p).read()
    for v in ("--bg", "--surface", "--fg", "--muted", "--accent", "--accent2", "--rule", "--scrim"):
        assert v in css
    assert ":root" in css

def test_deterministic(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (200, 70, 30))
    assert theme.derive_theme(str(tmp_path)) == theme.derive_theme(str(tmp_path))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/donghanglyu/.claude/skills/slides-to-video && python3 -m pytest tests/test_theme.py -v`
Expected: FAIL (`No module named 'theme'`).

- [ ] **Step 3: Write the implementation**

Create `scripts/theme.py`:
```python
"""Derive a topic-fitting color theme and write theme.css. Samples the source slide frames when
present (PIL quantize + luminance -> light/dark + a vivid accent), else uses a passed topic palette.
Curated, contrast-safe derivation (not raw pixels). Deterministic: no randomness, no wall-clock."""
import argparse, colorsys, glob, os

def _hex(rgb): return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)
def _hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def _lum(rgb):
    r, g, b = [c / 255 for c in rgb]; return 0.2126 * r + 0.7152 * g + 0.0722 * b
def _sat(rgb):
    r, g, b = [c / 255 for c in rgb]; return colorsys.rgb_to_hls(r, g, b)[2]
def _hue(rgb):
    r, g, b = [c / 255 for c in rgb]; return colorsys.rgb_to_hls(r, g, b)[0]
def _mix(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
def _contrast(a, b):
    la, lb = _lum(a) + 0.05, _lum(b) + 0.05
    return max(la, lb) / min(la, lb)

def _sample_frames(out_dir, k=4, n_colors=5):
    from PIL import Image
    paths = sorted(glob.glob(os.path.join(out_dir, "frames", "*.png")))[:k]
    if not paths:
        return None
    cols = []
    for p in paths:
        im = Image.open(p).convert("RGB"); im.thumbnail((120, 120))
        q = im.quantize(colors=n_colors).convert("RGB")
        cols += [rgb for _, rgb in q.getcolors(maxcolors=100000)]
    return cols or None

def derive_theme(out_dir, mode=None, accent=None, accent2=None, bg=None):
    sampled = None if (accent and bg) else _sample_frames(out_dir)
    if mode in ("light", "dark"):
        m = mode
    elif sampled:
        avg = sum(_lum(c) for c in sampled) / len(sampled)
        m = "light" if avg >= 0.5 else "dark"
    else:
        m = "dark"
    acc = _hex2rgb(accent) if accent else (max(sampled, key=_sat) if sampled else (76, 155, 232))
    if accent2:
        acc2 = _hex2rgb(accent2)
    else:
        h, l, s = colorsys.rgb_to_hls(*[c / 255 for c in acc])
        acc2 = tuple(c * 255 for c in colorsys.hls_to_rgb((h + 0.5) % 1.0, 0.5, max(0.5, s)))
    hue = _hue(acc)
    if bg:
        bgc = _hex2rgb(bg)
    elif m == "light":
        bgc = tuple(c * 255 for c in colorsys.hls_to_rgb(hue, 0.96, 0.18))
    else:
        bgc = tuple(c * 255 for c in colorsys.hls_to_rgb(hue, 0.09, 0.22))
    fg = (22, 20, 18) if m == "light" else (240, 243, 248)
    if _contrast(fg, bgc) < 7.0:
        fg = (8, 8, 8) if m == "light" else (255, 255, 255)
    return {"mode": m, "bg": _hex(bgc), "surface": _hex(_mix(bgc, fg, 0.06)),
            "fg": _hex(fg), "muted": _hex(_mix(fg, bgc, 0.42)),
            "accent": _hex(acc), "accent2": _hex(acc2), "scrim": _hex(bgc)}

def write_theme_css(theme, path):
    css = (":root{\n"
           f"  --bg:{theme['bg']}; --surface:{theme['surface']}; --fg:{theme['fg']};\n"
           f"  --muted:{theme['muted']}; --accent:{theme['accent']}; --accent2:{theme['accent2']};\n"
           f"  --rule:var(--accent2); --scrim:{theme['scrim']};\n}}\n")
    with open(path, "w") as f:
        f.write(css)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--mode"); ap.add_argument("--accent"); ap.add_argument("--accent2"); ap.add_argument("--bg")
    a = ap.parse_args()
    t = derive_theme(a.out_dir, a.mode, a.accent, a.accent2, a.bg)
    write_theme_css(t, os.path.join(a.out_dir, "theme.css"))
    print(f"[theme] mode={t['mode']} bg={t['bg']} fg={t['fg']} accent={t['accent']} accent2={t['accent2']}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_theme.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/theme.py tests/test_theme.py
git commit -m "feat(theme): theme.py — curated topic palette from frames/topic -> theme.css"
```

---

### Task 2: themeable `base.css` + `motifs.css` (+ `.kenburns` / `.split`)

**Files:**
- Modify: `assets/html/base.css`, `assets/html/motifs.css`
- Test: `tests/test_scenes.py`

**Interfaces:**
- Produces: semantic vars + aliases; `.kenburns`, `.split`, `.media` classes. `theme.css` (Task 1) overrides the `:root` vars.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scenes.py`:
```python
def test_design_system_is_themeable():
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = open(os.path.join(skill, "assets", "html", "base.css")).read()
    motifs = open(os.path.join(skill, "assets", "html", "motifs.css")).read()
    # canonical semantic vars + back-compat aliases present in base.css :root
    for v in ("--bg", "--surface", "--fg", "--muted", "--accent", "--accent2", "--rule", "--scrim"):
        assert v in base, f"missing {v}"
    assert "--blue:var(--accent)" in base.replace(" ", "") or "--blue: var(--accent)" in base
    assert "--orange:var(--accent2)" in base.replace(" ", "") or "--orange: var(--accent2)" in base
    # motion + illustrated-page helpers live in motifs.css
    assert ".kenburns" in motifs and ".split" in motifs
    # the photo scrim now derives from the theme bg (no hardcoded #0d1117 in motifs scrim)
    assert "#0d1117" not in motifs

@pytest.mark.skipif(not _chrome_present(), reason="no Chrome")
def test_light_theme_renders_light(tmp_path):
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    theme_css = tmp_path / "theme.css"
    theme_css.write_text(":root{--bg:#f5f0e6;--surface:#fffdf8;--fg:#201a14;--muted:#6b5e4f;"
                         "--accent:#c0461f;--accent2:#2f7d4f;--rule:var(--accent2);--scrim:#f5f0e6;}")
    page = tmp_path / "p.html"
    page.write_text('<!doctype html><html><head><meta charset="utf-8">'
                    f'<link rel="stylesheet" href="file://{base}">'
                    f'<link rel="stylesheet" href="file://{theme_css}"></head>'
                    '<body><div class="stage"><h1 class="title">Hello</h1></div></body></html>')
    out = tmp_path / "o.png"
    scenes._chrome_shot(f"file://{page}", str(out), 480, 270, {})
    from PIL import Image
    px = Image.open(out).convert("RGB").getpixel((10, 10))
    assert sum(px) / 3 > 180, f"expected light bg, got {px}"   # theme.css overrode the dark default
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_scenes.py -k "themeable or light_theme" -v`
Expected: FAIL (vars/aliases/classes absent; `#0d1117` still in motifs; light render still dark).

- [ ] **Step 3: Implement the refactor**

In `assets/html/base.css`, replace the `:root{…}` block with:
```css
:root{
  /* canonical semantic theme vars (a per-video theme.css overrides these) */
  --bg:#0d1117; --surface:#161b22; --fg:#f0f3f8; --muted:#8b97a8;
  --accent:#4C9BE8; --accent2:#E8590C; --rule:var(--accent2); --scrim:#0d1117;
  /* back-compat aliases (existing pages/inline styles) */
  --blue:var(--accent); --orange:var(--accent2); --green:#46A758; --panel:var(--surface);
  --dur:.7s;
}
```
Then in `base.css`, replace any remaining hardcoded color in a component class with a var:
- `.bar{… color:#fff …}` → `color:var(--bg)` is wrong on a colored bar; instead keep readable: change `#fff` → `var(--surface)` only if light — simplest: set `.bar{… color:#fff …}` → `color:#fff` is acceptable on saturated bars in both modes, so **leave `.bar` text as `#fff`** (saturated accent fills read with white in light or dark). No change needed if `.bar` only hardcodes its text color; do NOT hardcode its background (it's set inline per use).
- Confirm `.kicker`/`.rule` use `var(--orange)` (→ alias `--accent2`) and `.dot`/`.stat` use `var(--blue)` (→ `--accent`); leave as-is (they resolve through aliases).

In `assets/html/motifs.css`:
- `.scrim` — replace the hardcoded gradient with a theme-derived one:
  ```css
  .scrim{position:absolute;inset:0;z-index:0;pointer-events:none;
    background:linear-gradient(90deg, var(--scrim) 0%, var(--scrim) 36%, transparent 78%)}
  ```
  (Darkens for dark themes, lightens for light themes — `--scrim` = theme bg.)
- `.ghost` — `color:#fff` → `color:var(--fg)`.
- `.bg-glow.blue{background:#4C9BE8}` → `background:var(--accent)`; `.bg-glow.orange{background:#E8590C}` → `background:var(--accent2)`.
- `.bg-stars` radial dots use `#ffffff…` — leave (white stars read on any dark; for light themes stars are subtle — acceptable).
- Append the motion + layout helpers:
  ```css
  /* Ken-Burns on an embedded image — paused + seekable (seek.js freezes it per frame).
     Wrap the img in a media panel with overflow:hidden. */
  .media{position:relative;overflow:hidden;border-radius:14px}
  .media img,img.kenburns{width:100%;height:100%;object-fit:cover;display:block}
  img.kenburns{animation:mt-kenburns 6s ease-out forwards;animation-play-state:paused;
    transform-origin:50% 50%}
  @keyframes mt-kenburns{from{transform:scale(1.02)}to{transform:scale(1.14) translate(-2%,-1%)}}
  /* two-column illustrated content page: text + a media panel */
  .split{display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:center;
    width:1920px;height:1080px;padding:120px 150px}
  .split .media{height:760px}
  ```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -k "themeable or light_theme" -v` (light test PASS with Chrome, else skipped — but `themeable` always runs).
Run: `python3 -m pytest tests/test_scenes.py -q` (existing scenes tests stay green).

- [ ] **Step 5: Commit**

```bash
git add assets/html/base.css assets/html/motifs.css tests/test_scenes.py
git commit -m "feat(assets): themeable base.css/motifs.css (semantic vars + aliases) + .kenburns/.split"
```

---

### Task 3: content-planner re-conception + theme + media (`agents/content-planner.md`)

**Files:**
- Modify: `agents/content-planner.md`

- [ ] **Step 1: Add the three principles + output fields**

In `agents/content-planner.md`, add to the rubric (after the existing rules):
```markdown
## Re-conceive the material into a VIDEO (don't mirror the deck)
You are not transcribing slides in order. Design the best instructional *video*: open with a
**hook**, find a **throughline**, freely **resequence / merge / split** the source's points, and
cut what doesn't earn screen time — while covering the source's substance and staying **strictly
faithful** (every beat still has a `source_ref`; invent no facts/numbers).

## Propose a topic-fitting THEME (top-level field)
Add a top-level `"theme"` to your plan: `{ "mode": "light"|"dark", "accent": "#hex",
"accent2": "#hex", "bg": "#hex"? , "why": "one line" }` — a palette that fits the SUBJECT
(travel/food/lifestyle → warm light; tech/space/finance → dark; etc.). If the source has slide
frames, you may instead set `"theme": {"from_frames": true}` to sample them. The downstream
`theme.py` turns this into `theme.css`.

## Attach selective MEDIA to beats (illustrated pages)
For a content beat where an image genuinely strengthens the point (NOT every beat), add
`"media": { "image_prompt": "generic, atmospheric, illustrative …", "motion": "kenburns" }`.
Rules: generic **broll** only — no real logos, faces, named/specific landmarks, or in-image
text/numbers; the fact stays as on-page text. Keep most beats typographic; section/hero beats keep
their backdrop. Aim for a few illustrated content beats, not all.
```

- [ ] **Step 2: Verify + commit**

Run: `grep -n "Re-conceive\|throughline\|\"theme\"\|\"media\"\|kenburns\|broll" agents/content-planner.md` (expect matches).
```bash
git add agents/content-planner.md
git commit -m "feat(agents): content-planner re-conceives arc + proposes theme + selective media"
```

---

### Task 4: authoring guide — theming + illustrated page (`references/html-pages.md`)

**Files:**
- Modify: `references/html-pages.md`

- [ ] **Step 1: Add the Theming + Illustrated-page sections**

Append to `references/html-pages.md`:
```markdown
## Theming (topic-fitting color)
Link the stylesheets in THIS order: `base.css` → **`theme.css`** → `motifs.css`. `theme.css` is
written by `scripts/theme.py <out_dir>` (it samples `frames/` for a curated light/dark palette, or
takes `--mode/--accent/--bg` for a topic palette) and overrides the `:root` vars. **Author pages
with the semantic vars only** — `var(--bg) var(--surface) var(--fg) var(--muted) var(--accent)
var(--accent2) var(--rule)` (older `var(--blue)/var(--orange)` still alias to the accents). Never
hardcode a hex in a page — that's how a page goes off-theme.

## Illustrated content page (image + Ken-Burns)
A content beat with `media` becomes a two-column `.split` page: text on one side, an image panel on
the other. The image animates with a slow Ken-Burns (paused + seek-safe):
```html
<div class="split">
  <div><div class="kicker reveal">SECTION</div>
    <div class="title reveal-up" style="animation-delay:.1s">Headline</div>
    <div class="grid" style="margin-top:28px;gap:22px">
      <div class="row reveal-up" style="animation-delay:.3s"><span class="dot"></span><span class="label">Point</span></div>
    </div></div>
  <div class="media"><img class="kenburns" src="file:///ABS/out_dir/assets/scene_07.png" alt=""></div>
</div>
```
The image is a generic atmospheric **broll** (generated via `imagegen`); the facts stay as text.
Only CSS animation (`.kenburns` + reveals) — no JS-timed motion, no network assets — so `seek.js`
captures it deterministically.
```

- [ ] **Step 2: Verify + commit**

Run: `grep -n "Theming\|theme.css\|Illustrated\|kenburns\|.split" references/html-pages.md` (expect matches).
```bash
git add references/html-pages.md
git commit -m "docs(reference): theming + illustrated content-page (Ken-Burns) patterns"
```

---

### Task 5: SKILL.md workflow (theme step + re-conception + illustrated) + critic note

**Files:**
- Modify: `SKILL.md`, `agents/critic.md`

- [ ] **Step 1: Wire the theme step + re-conception + illustrated pages into the HTML workflow**

In `SKILL.md`, in the HTML-pages-tier guidance (step 3.5 / the workflow), add:
```markdown
- **Theme (HTML tier):** after the content plan, run `scripts/theme.py <out_dir>` to write
  `theme.css` — it samples `frames/` for a curated light/dark palette fitting the topic (or pass
  `--mode/--accent/--bg` from the planner's `theme` suggestion when there are no frames). Pages link
  `base.css` → `theme.css` → `motifs.css`. 🔴 the plan checkpoint now also shows the palette + mode.
- **Re-conceive, don't mirror:** the content-planner designs a video arc (hook + throughline +
  resequencing), not the slide order — faithful to the substance.
- **Illustrated pages:** build a beat's `media` as a `.split` page (text + a `.kenburns` image
  panel, see `references/html-pages.md`); generate the image via `imagegen` (codex/key); keep it a
  generic broll. Most pages stay typographic.
```

- [ ] **Step 2: Add a Guardrails line + critic note**

In `SKILL.md` `## Guardrails`, add:
```markdown
- **Theming:** the HTML tier is themeable via `theme.py` → `theme.css` (semantic `:root` vars);
  pick a palette/mode that fits the TOPIC (not always dark). Author pages with the vars, never raw hex.
```
In `agents/critic.md`, after R2, add one line:
```markdown
- **Re-conceived coverage:** when the video re-conceives the deck (not slide order), confirm the
  arc still COVERS the source's substance and invents nothing; per-beat `media` images stay generic
  broll (R1e) — no fabricated specific landmark/logo, no text/data in the image.
```

- [ ] **Step 3: Verify + full suite + commit**

Run:
```bash
grep -n "theme.py\|theme.css\|Re-conceive\|Illustrated\|Theming" SKILL.md
grep -n "Re-conceived coverage" agents/critic.md
python3 -m pytest -q
```
Expected: grep shows the additions; full suite PASSES.
```bash
git add SKILL.md agents/critic.md
git commit -m "docs(skill): theme step + re-conception + illustrated pages; critic coverage note"
```

---

## Self-Review

**Spec coverage:** themeable base.css/motifs.css + aliases + `.kenburns`/`.split` (Task 2) ✓; `theme.py` curated palette from frames/topic + contrast + theme.css (Task 1) ✓; content-planner re-conception + `theme` + selective `media` (Task 3) ✓; authoring guide theming + illustrated page (Task 4) ✓; SKILL.md theme step + re-conception + illustrated + palette-at-checkpoint, critic coverage note (Task 5) ✓; faithfulness preserved (re-conception traces to source; media = broll; critic gates) — Tasks 3/5 ✓; feasibility (CSS vars, PIL sampling, seek-safe Ken-Burns) — Tasks 1/2 ✓. Out-of-scope (transitions, collages, other providers) has no task.

**Placeholder scan:** none — `theme.py`, the CSS edits, and tests are complete + runnable; `/ABS/out_dir/` in the guide is intentional instructional text.

**Type consistency:** `derive_theme(out_dir, mode, accent, accent2, bg) -> dict` and `write_theme_css(theme, path)` are defined in Task 1 and referenced consistently (CLI + SKILL.md). The theme var names (`--bg --surface --fg --muted --accent --accent2 --rule --scrim`) match across `theme.py`'s output (Task 1), base.css `:root` (Task 2), the guide (Task 4), and SKILL.md (Task 5). `--blue/--orange/--panel` aliases (Task 2) keep existing pages valid. `.kenburns`/`.split`/`.media` are defined in Task 2 and used in Task 4. The planner's `theme`/`media` fields (Task 3) feed `theme.py` (Task 1) + the illustrated page (Task 4).
