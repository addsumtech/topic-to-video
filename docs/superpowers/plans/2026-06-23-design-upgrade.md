# Visual-Design Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the high-value design-quality bundle (huashu-design principles, adapted) into our HTML design system — richer typography/depth/motion/layout, an anti-cliché palette guard, and a content-planner director discipline.

**Architecture:** Additive CSS (new `:root` tokens + classes in base.css/motifs.css — existing pages keep rendering), a deterministic palette clamp in theme.py, and prose rules in content-planner.md / html-pages.md / the two critics. All motion stays CSS-only + `animation-play-state:paused` (seek.js-freezable).

**Tech Stack:** CSS, Python 3 (PIL/colorsys), headless Chrome, pytest, Markdown agent/guide prompts.

## Global Constraints
- All new motion classes keep `animation-play-state:paused` (seek-safe). No network/CDN assets. Pages use semantic vars, never hardcoded hex.
- theme.py stays DETERMINISTIC; the bg clamp only nudges near-pure black/white (`#000`→`#0e0f11`, `#fff`→`#f8f7f4`); the ≥7:1 contrast loop still runs after.
- CSS additions are ADDITIVE (opt-in classes) — existing authored pages must still render unchanged.
- Existing test suite stays green.

---

### Task 1: `assets/html/base.css` — typography, depth, motion, layout primitives

**Files:**
- Modify: `assets/html/base.css`
- Test: `tests/test_scenes.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_scenes.py`:
```python
def test_base_css_design_tokens_and_classes():
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    css = open(os.path.join(skill, "assets", "html", "base.css")).read()
    for tok in ("--ease-expo", "--ease-over", "--font-mono", "--shadow-primary",
                "--shadow-float", "--hairline", "--stagger"):
        assert tok in css, f"missing token {tok}"
    for cls in (".reveal-pop", ".reveal-up-sm", ".mono", ".card", ".dash", ".grid-asym", ".dash-col"):
        assert cls in css, f"missing class {cls}"
    # seek-safe: the new spring reveal must be paused
    i = css.index(".reveal-pop")
    assert "animation-play-state:paused" in css[i:i+240]
    assert "tabular-nums" in css            # data figures use tabular numerals

@pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")
def test_reveal_pop_motion_captured(tmp_path):
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    page = tmp_path / "pop.html"
    page.write_text('<!doctype html><html><head><meta charset="utf-8">'
                    f'<link rel="stylesheet" href="file://{base}"></head>'
                    '<body><div class="stage"><div class="stat reveal-pop">42</div></div></body></html>')
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    scenes._chrome_shot(f"file://{page}?p=0", str(a), 960, 540, {})
    scenes._chrome_shot(f"file://{page}?p=1", str(b), 960, 540, {})
    from PIL import Image
    assert Image.open(a).convert("RGB").tobytes() != Image.open(b).convert("RGB").tobytes()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/donghanglyu/.claude/skills/slides-to-video && python3 -m pytest tests/test_scenes.py -k "design_tokens or reveal_pop" -v`
Expected: FAIL (tokens/classes absent).

- [ ] **Step 3: Implement the base.css additions**

In `assets/html/base.css`, **(a)** extend the `:root` block — add these lines inside `:root{ … }`:
```css
  /* design tokens (huashu-adapted): easing, type, depth, rhythm */
  --font-mono:"JetBrains Mono","SF Mono",ui-monospace,"Menlo",monospace;
  --ease-expo:cubic-bezier(.16,1,.3,1); --ease-over:cubic-bezier(.34,1.56,.64,1);
  --ease-exit:cubic-bezier(.55,0,1,.45);
  --dur-fast:.35s; --dur-slow:1.2s; --stagger:.03s;
  --shadow-primary:0 20px 60px -20px rgba(0,0,0,.22); --shadow-float:0 6px 18px -6px rgba(0,0,0,.12);
  --hairline:1px solid rgba(127,127,127,.18);
```
**(b)** Edit existing component classes:
- `.kicker{…}` → add `font-family:var(--font-mono);font-variant-numeric:tabular-nums;` (keep its existing props).
- `.title{… letter-spacing:-.01em}` → `letter-spacing:-.025em;text-wrap:balance` (append `text-wrap:balance`).
- `.stat{… letter-spacing:-.02em}` → `letter-spacing:-.04em;font-variant-numeric:tabular-nums`.
- `.label{font-size:54px;font-weight:700}` → add `font-variant-numeric:tabular-nums`.
- `.bar{… }` → add `font-variant-numeric:tabular-nums`.
- `.grid{display:grid;gap:40px}` → `gap:48px`.
- `.row{… gap:28px …}` → `gap:32px`.
- `.reveal-up{… cubic-bezier(.22,1,.36,1) …}` → replace that easing with `var(--ease-expo)`.

**(c)** Append new classes at the end of `base.css`:
```css
/* 8-pt grid: gaps/padding use multiples of 8. hierarchy contract: .title/.sub ≥ 2.5×, .title/.note ≥ 3×. */
.mono{font-family:var(--font-mono);letter-spacing:.04em;font-variant-numeric:tabular-nums}
/* spring overshoot for a hero stat / pop-in (paused -> seek.js freezes it) */
.reveal-pop{opacity:0;transform:scale(.88);animation:pop var(--dur) var(--ease-over) forwards;animation-play-state:paused}
@keyframes pop{to{opacity:1;transform:none}}
/* shorter rise for dense sub-items */
.reveal-up-sm{opacity:0;transform:translateY(10px);animation:rise var(--dur) var(--ease-expo) forwards;animation-play-state:paused}
/* card with depth + hairline */
.card{background:var(--surface);border-radius:14px;padding:28px 32px;border:var(--hairline);
  box-shadow:var(--shadow-primary),var(--shadow-float)}
/* layout primitives: asymmetric + 3-up dashboard */
.grid-asym{display:grid;grid-template-columns:2fr 1fr;gap:48px;align-items:start}
.dash{display:grid;grid-template-columns:1fr 1fr 1fr;gap:48px;align-items:start}
.dash-col{display:flex;flex-direction:column;gap:24px}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -k "design_tokens or reveal_pop" -v` (reveal_pop skips without Chrome; design_tokens always runs).
Run: `python3 -m pytest tests/test_scenes.py -q` (existing scenes tests stay green).

- [ ] **Step 5: Commit**

```bash
git add assets/html/base.css tests/test_scenes.py
git commit -m "feat(base.css): design tokens (expo easing, mono, depth, 8pt grid) + .reveal-pop/.card/.dash"
```

---

### Task 2: `assets/html/motifs.css` — focus depth, section divider, diagonal Ken-Burns

**Files:**
- Modify: `assets/html/motifs.css`
- Test: `tests/test_scenes.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_scenes.py`:
```python
def test_motifs_focus_divider_and_kenburns_drift():
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    css = open(os.path.join(skill, "assets", "html", "motifs.css")).read()
    for cls in (".defocus", ".accent-fill", ".bg-paper"):
        assert cls in css, f"missing {cls}"
    # Ken-Burns now drifts diagonally, not scale-only
    i = css.index("@keyframes mt-kenburns")
    assert "translate(" in css[i:i+160]
    assert "#0d1117" not in css                      # scrim still theme-derived
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scenes.py -k "focus_divider" -v`
Expected: FAIL (`.defocus` etc. absent).

- [ ] **Step 3: Implement**

In `assets/html/motifs.css`:
- Update the Ken-Burns keyframe: `@keyframes mt-kenburns{from{transform:scale(1.02)}to{transform:scale(1.14) translate(-2%,-1%)}}` → `to{transform:scale(1.14) translate(-3%,-1.5%)}` (stronger diagonal drift).
- Soften `.scrim` so the photo stays ≥45% visible: change its gradient to
  `background:linear-gradient(90deg, var(--scrim) 0%, color-mix(in srgb,var(--scrim) 55%,transparent) 42%, transparent 82%)` (less full-black on the left, fade-out sooner).
- Append:
```css
/* depth-of-field: defocus the NON-focal element (compare pages) — static filter, seek-safe */
.defocus{filter:brightness(.6) saturate(.7) blur(4px);opacity:.5}
/* full-bleed accent section divider (use on <body> of a transition beat) */
.accent-fill{background:var(--accent);color:var(--on-accent)}
/* faint light-mode paper texture behind content */
.bg-paper{position:absolute;inset:0;z-index:0;pointer-events:none;
  background:radial-gradient(ellipse at 30% 38%, color-mix(in srgb,var(--fg) 4%,transparent) 0%, transparent 70%)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scenes.py -k "focus_divider or themeable or light_theme or kenburns" -q` (these + the existing motif/theme tests stay green).

- [ ] **Step 5: Commit**

```bash
git add assets/html/motifs.css tests/test_scenes.py
git commit -m "feat(motifs.css): .defocus focus-depth + .accent-fill divider + diagonal Ken-Burns + softer scrim"
```

---

### Task 3: `scripts/theme.py` — anti-cliché palette guard (no pure black/white bg)

**Files:**
- Modify: `scripts/theme.py`
- Test: `tests/test_theme.py`

**Interfaces:** `derive_theme(out_dir, mode, accent, accent2, bg)` (unchanged signature) now never returns a pure `#000000`/`#ffffff` `bg`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_theme.py`:
```python
def test_pure_black_bg_is_tinted(tmp_path):
    t = theme.derive_theme(str(tmp_path), mode="dark", accent="#4C9BE8", bg="#000000")
    assert t["bg"].lower() != "#000000" and t["bg"].lower() == "#0e0f11"

def test_pure_white_bg_is_tinted(tmp_path):
    t = theme.derive_theme(str(tmp_path), mode="light", accent="#c0461f", bg="#ffffff")
    assert t["bg"].lower() != "#ffffff" and t["bg"].lower() == "#f8f7f4"

def test_clamped_bg_still_contrast_safe(tmp_path):
    t = theme.derive_theme(str(tmp_path), mode="dark", accent="#4C9BE8", bg="#000000")
    assert theme._contrast(theme._hex2rgb(t["fg"]), theme._hex2rgb(t["bg"])) >= 7.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_theme.py -k "pure_black or pure_white or clamped" -v`
Expected: FAIL (`#000000` returned as-is).

- [ ] **Step 3: Implement the clamp**

In `scripts/theme.py` `derive_theme`, immediately AFTER `bgc` is resolved (the `if bg: … elif m=="light": … else: …` block) and BEFORE `fg = …` / the contrast loop, insert:
```python
    # anti-cliché: never a pure-black/white background — nudge to a temperature-tinted neutral
    if _lum(bgc) <= 0.02:
        bgc = (14, 15, 17)        # #0e0f11
    elif _lum(bgc) >= 0.97:
        bgc = (248, 247, 244)     # #f8f7f4
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_theme.py -q`
Expected: PASS (all theme tests, incl. the 3 new + existing contrast tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/theme.py tests/test_theme.py
git commit -m "feat(theme): clamp pure black/white bg to a tinted neutral (anti-cliché)"
```

---

### Task 4: `agents/content-planner.md` — director discipline + variety + palette

**Files:**
- Modify: `agents/content-planner.md`

- [ ] **Step 1: Add the director/variety/palette rules**

Append to `agents/content-planner.md` (after the existing rules):
```markdown
## Director's discipline (the plan carries the quality)
Add these top-level fields to your plan JSON:
- **`director_note`** (REQUIRED when `target_seconds` > 60): `{ "thesis": "one sentence — what this
  video argues", "not": ["explicit exclusions — what it is NOT / will not do"], "tone": "one word" }`.
- **`anti_slop`** (REQUIRED array): the plan's self-imposed bans, e.g. `["no emoji in titles",
  "no gradient-mesh backgrounds", "no stat without a source_ref", "no more than 2 same-type beats in a row"]`.
- Mark exactly ONE beat **`"climax": true`** at ~75–80% of the runtime (the peak — the result/payoff
  moment). Mark the FINAL beat **`"hold": true`** — a sparse title or single stat; do NOT add a
  fade-out or blank-screen beat (the render's end-hold IS the ending).

## Visual variety (no monotony)
No more than **2 consecutive beats** may share the same `visual.type`. After two `keypoints`, insert a
`chart`/`compare`/`title`/illustrated beat. Scan your beat list before returning and break any same-type run.

## Palette discipline (anti-cliché)
Pick ONE dominant `--accent`; `--accent2` is a split-complement or tint of it, NOT an independent hue.
Never propose a pure `#000000`/`#ffffff` bg. Avoid the electric-blue-on-`#0d1117` AI cliché unless the
topic is literally code/GitHub — prefer a temperature-tinted bg + a topic-fitting accent.

## Before you emit the plan — two checks
1. **Squint test:** at low resolution, does each beat's hierarchy still read (big vs small, bright vs
   muted)? If a beat is a flat wall of same-size text, redesign it.
2. **Cover-text test:** covering `narration_intent`, can each beat be told apart from its neighbours by
   visual SHAPE alone? If two adjacent beats look identical, vary the layout.
```

- [ ] **Step 2: Verify + commit**

Run: `grep -n "director_note\|anti_slop\|\"climax\"\|\"hold\"\|Visual variety\|Squint test\|Cover-text\|Palette discipline" agents/content-planner.md` (expect matches).
```bash
git add agents/content-planner.md
git commit -m "feat(agents): content-planner director discipline + visual variety + palette rules"
```

---

### Task 5: `references/html-pages.md` patterns/checklists + critic visual checks

**Files:**
- Modify: `references/html-pages.md`, `agents/critic-content.md`, `agents/critic-av.md`

- [ ] **Step 1: Add the html-pages patterns + checklists**

Append to `references/html-pages.md`:
```markdown
## Typographic roles (use the named classes — never a raw font-size)
`.stat` = a single data value · `.title` = the primary claim · `.sub` = supporting context (always
`--muted`) · `.kicker` = a category label (mono, `--accent`) · `.note` = secondary annotation. Keep the
hierarchy contract: `.title`/`.sub` ≥ 2.5×, `.title`/`.note` ≥ 3×.

## New layout patterns
- **`.card`** — a panel with depth (`--surface` + shadow + hairline). Group related rows in cards.
- **`.dash`** (3-up) / **`.grid-asym`** (2fr 1fr) — dashboard + asymmetric layouts; break the centred-column monotony.
- **`.defocus`** — on a `compare` page, add to the NON-active column/bar for depth-of-field (blur, not flat dim).
- **`.accent-fill`** — on `<body>` of a section-divider beat: full-bleed accent background, `--on-accent` text.
- **`.reveal-pop`** — a spring overshoot for a hero `.stat`. **`.reveal-up-sm`** — shorter rise for dense sub-items.

## Stagger cadence (seek-safe, snappy)
kicker `0s`, rule `.05s`, title `.10s`, first content row `.25s`, then `+.03s` per sibling. Cap cumulative
delay at `.9s`. Never stagger more than `.06s` between closely-related elements.

## One-concept rule + whitespace floor
ONE primary per page (a stat OR a list OR a chart — not two stacked). Content must not fill more than
~60% of the canvas; if a row grid overflows below 960px, SPLIT the beat — never shrink `.stage` padding below 80px.

## Anti-slop checklist (do NOT)
emoji in titles · full-screen purple/pink/blue gradient-mesh backgrounds · circle+left-border accent
cards (use `.card`/`.row`) · SVG depicting realistic scenes/figures · decorative bottom progress bars /
timecodes / chapter counters (player-chrome) · hardcoded hex (use semantic vars) · network/CDN links.

## Pre-render checklist
absolute `file://` paths (files exist) · no `<link href="http…">` · base.css → theme.css → motifs.css
linked · no content overflow below 960px · semantic vars only · all `.reveal*`/`.kenburns` keep
`animation-play-state:paused` · no leftover debug overlays.
```

- [ ] **Step 2: Add the critic visual checks**

In `agents/critic-content.md`, add to its rubric: **Visual variety + anti-slop** — flag >2 consecutive
beats of the same `visual.type`; flag any emoji, gradient-mesh background, fabricated stat, or hardcoded
hex `#rrggbb` in an authored page (a REVISE-class slop violation).

In `agents/critic-av.md`, add to its rubric: **Squint + no player-chrome** — on the rendered sample,
the hierarchy must read at a glance (big/small, bright/muted); flag any element resembling a video-player
control, progress bar, timecode, or chapter counter as a slop REVISE.

- [ ] **Step 3: Verify + full suite + commit**

Run:
```bash
grep -n "Typographic roles\|.defocus\|.accent-fill\|Stagger cadence\|Anti-slop\|Pre-render" references/html-pages.md
grep -n "Visual variety\|anti-slop\|hardcoded hex" agents/critic-content.md
grep -n "Squint\|player-chrome\|progress bar" agents/critic-av.md
python3 -m pytest -q
```
Expected: the patterns/checks present; full suite PASSES.
```bash
git add references/html-pages.md agents/critic-content.md agents/critic-av.md
git commit -m "docs: html-pages design patterns + checklists; critic visual-variety/anti-slop/squint checks"
```

---

## Self-Review

**Spec coverage:** base.css tokens/typography/depth/motion/layout (Task 1) ✓; motifs focus/divider/diagonal-Ken-Burns/softer-scrim (Task 2) ✓; theme.py anti-cliché bg clamp (Task 3) ✓; content-planner director_note/anti_slop/climax/hold/variety/palette/squint+cover-text (Task 4) ✓; html-pages role table/patterns/stagger/one-concept/checklists + critic visual checks (Task 5) ✓; faithfulness invariants (paused motion, semantic vars, broll) preserved across Tasks 1/2/5 ✓. Out-of-scope (palette modes, style_pattern, rhythm, gallery/3D, compound-pan, full R_vars graders) has no task.

**Placeholder scan:** none — every CSS edit, the theme.py clamp, and the tests are complete + runnable; prose tasks specify exact text + grep verification.

**Type consistency:** `derive_theme`'s signature is unchanged; the clamp only mutates `bgc` before the existing contrast loop, so `_contrast`/`_hex2rgb`/`_lum` (already in theme.py) are reused. The CSS token names (`--ease-expo/--ease-over/--font-mono/--shadow-primary/--shadow-float/--hairline/--stagger`) and class names (`.reveal-pop/.reveal-up-sm/.mono/.card/.dash/.dash-col/.grid-asym/.defocus/.accent-fill/.bg-paper`) are identical across base.css/motifs.css (Tasks 1/2), the tests (Tasks 1/2), the html-pages patterns (Task 5), and the planner/critic prose. `.reveal-pop` + `.reveal-up-sm` keep `animation-play-state:paused` per the seek-safe invariant.
