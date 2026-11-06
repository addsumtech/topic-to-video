# Design Craft Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give topic-to-video a memory of the user's taste, a picture-before-build stage, real object continuity, a
subject-craft check, a density floor and a hero camera grammar — then prove them on one new film.

**Architecture:** New Python scripts beside the existing gates (`taste_ledger.py`, `sketch_sheet.py`,
`subject_craft_qa.py`), new rules inside `validate.py` next to `_through_object`, new pure-function runtime modules
(`reacts.ts`, `character.ts`, `lighting.tsx`, `heroCamera.tsx`) kept OUT of modules every register imports, so the
library's hash manifests stay fresh. Each check is calibrated on our own films before it blocks anything.

**Tech Stack:** Python 3 + PIL + numpy (scripts), TypeScript/React + Remotion (runtime), Blender 5.2 (kit), pytest +
`tests/_tsprobe.py` (TS pure functions in node).

**Spec:** `docs/superpowers/specs/2026-11-06-design-craft-design.md`

## Global Constraints
- The taste ledger lives at `~/.topic-to-video/taste-ledger.json` (override `TTV_TASTE_LEDGER` for tests); the user's
  words never enter this PUBLIC repo.
- No paid API, no download without asking the user (filename, source, size).
- Never use the user's own materials as test input; the corpus is GPS (`.superpowers/films/gps`), HTTPS
  (`.superpowers/films/https`), ANC (`~/code_project/film_work/anc`).
- A new check ships only if it fired on an old film and stayed quiet on ANC (spec anti-goals); otherwise it is cut and
  the finding written into `references/craft-bar.md`.
- New runtime code goes in NEW modules; do not edit `depth.tsx`, `glide.ts`, `layout.ts`, `dna.tsx` unless a task says
  so. After any `remotion/src` edit run `python3 scripts/stale_measurements.py` before committing and re-measure what
  it lists.
- The worktree needs `ln -s ../../../remotion/node_modules remotion/node_modules` once (as in `.worktrees/rest`).
- Comments follow the house style: WHY first, the measured incident, then the rule.
- Commit per task, named paths only. Full suite before any push; push only when the user says so.

## Review Focus
1. Ledger file missing, corrupt or unwritable → `check` and `--final` name the file and the fault; a corrupt file is
   never read as an empty ledger. (Task 1, 2)
2. An html-tier or 原样配音 board → no sketch, hero or density rule fires. (Task 3, 9)
3. 9:16 / 1:1 boards → sketch tiles and their caption-band check use the aspect's band (257 px), not 200. (Task 4)
4. A hero beat whose subject cannot be located → `subject_craft_qa` reports NOT MEASURED and errors on a hero, never a
   silent pass. (Task 7)
5. `through_object.beats` out of order or skipping indexes → pairs follow the declared list, and an index not on the
   board is named. (Task 5)

---

### Task 1: Taste ledger store and commands

**Files:**
- Create: `scripts/taste_ledger.py`, `references/taste-ledger.example.json`
- Test: `tests/test_taste_ledger.py`

**Interfaces:**
- Produces: `load(path=None) -> dict` (raises `LedgerError` on corrupt JSON, naming the path); `add(said, rule, stage,
  film=None, gate=None, path=None) -> dict` (new entry, `status` active, `id` = slug of rule, unique);
  `retire(id, gate, path=None)`; `brief(stage, path=None) -> list[str]` (active rules for that stage, one line
  each); `STAGES = ("plan", "design", "build", "render")`; CLI `add|list|retire|brief`.

- [ ] **Step 1: Write the failing tests**
```python
def test_add_then_brief_lists_only_active_rules_of_that_stage(tmp_path, monkeypatch):
    monkeypatch.setenv("TTV_TASTE_LEDGER", str(tmp_path / "l.json"))
    tl.add("视频不是 PPT", "no header title per beat", "design")
    tl.add("背景要按实际来", "environment per beat from its subject", "design")
    tl.retire("no-header-title-per-beat", gate="validate SLIDE TITLES")
    assert tl.brief("design") == ["environment per beat from its subject"]
    assert tl.brief("render") == []

def test_corrupt_ledger_is_an_error_not_an_empty_ledger(tmp_path, monkeypatch):
    p = tmp_path / "l.json"; p.write_text("{not json"); monkeypatch.setenv("TTV_TASTE_LEDGER", str(p))
    with pytest.raises(tl.LedgerError, match=str(p)):
        tl.load()

def test_missing_ledger_is_empty_and_bad_stage_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("TTV_TASTE_LEDGER", str(tmp_path / "none.json"))
    assert tl.load()["entries"] == []
    with pytest.raises(ValueError):
        tl.add("x", "y", "colour")
```
- [ ] **Step 2:** `pytest tests/test_taste_ledger.py -v` → FAIL (no module).
- [ ] **Step 3:** Implement. Writes are atomic (tmp + `os.replace`), the directory is created on first add.
- [ ] **Step 4:** Tests PASS.
- [ ] **Step 5:** Commit `taste ledger: the user's taught rules, outside the repo, retired once a gate enforces them`.

### Task 2: Ledger check, `--final` refusal, director briefs, craft bar

**Files:**
- Modify: `scripts/taste_ledger.py` (add `check`), `scripts/critic_ledger.py` (`validate(final=True)`),
  `agents/design-director.md`, `agents/shot-director.md`, `agents/shot-builder.md`, `agents/shot-critic.md`,
  `SKILL.md` (index line), `references/pipeline-scripts.md`
- Create: `references/craft-bar.md`
- Test: `tests/test_taste_ledger.py`, `tests/test_critic_ledger_taste.py`

**Interfaces:**
- Consumes: Task 1 `load`, `brief`.
- Produces: `check(out_dir, path=None) -> list[str]` (one problem per active rule with no answer in
  `meta.taste_review`); `meta.taste_review = {<rule id>: {"answer": str, "sha256": <hex of a file in out_dir>}}`.

- [ ] **Step 1: Write the failing tests**
```python
def test_check_names_each_unanswered_active_rule(film, ledger):        # film: tmp out_dir with storyboard.json
    tl.add("每个元素1秒看懂", "every element decodable in ~1 s", "design")
    assert any("every-element-decodable" in p for p in tl.check(film))

def test_an_answer_must_pin_a_file_that_exists_in_the_film(film, ledger):
    # answer with sha of _sketch_review.png passes; a sha matching no file in out_dir is named
    ...

def test_final_refuses_unanswered_rule_and_a_user_waiver_passes(film, ledger):
    # critic_ledger.validate(film, final=True) errors mention "taste"; meta.delivery_waivers {"taste_ledger": ...}
    # (the existing waiver shape) clears it
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `check`; `critic_ledger.validate(final=True)` calls it (a `LedgerError` is an error
  naming the file). Add one line to each of the four agent briefs: run `python3 scripts/taste_ledger.py brief
  --stage <theirs>` and apply every line. Write `references/craft-bar.md` from the spec's A4 list with its sources and
  a "what the research did not give" paragraph; each technique names the task below that carries it.
- [ ] **Step 4:** Tests PASS; `pytest tests/test_critic_ledger*.py -q` still green.
- [ ] **Step 5:** Seed the real ledger (NOT committed): `add` the user's recorded feedback (memory files
  film-no-slide-titles, craft-vs-skillry, direction-contest-design-first, frame-element-decodability,
  design-must-be-meaningful, slides-to-video-tactile-redesign, caption-frame-bg-no-occlude, video-resolution-gate,
  lining-figures-always, device-fidelity), quoting their words; retire the gated ones with the gate's name.
- [ ] **Step 6:** Commit code + docs only.

### Task 3: `slide.sketch` and `meta.hero_moments` in validate

**Files:**
- Modify: `scripts/validate.py` (new `_sketch_problems(meta, slides, tier)` beside `_through_object`, wired at
  line ~5155), `agents/design-director.md` (3.6 writes sketches), `SKILL.md` 3.6 checkpoint text
- Test: `tests/test_sketch_rules.py`

**Interfaces:**
- Produces: sketch schema `{metaphor: str, hero: str, layout: [{name, rect:[x,y,w,h], hero?: bool}], camera: str,
  environment: str, carries?: str}`, rects in content-zone fractions 0..1; `SKETCH_LAYOUT_MIN, MAX = 2, 6`;
  `_sketch_problems -> (errors, warnings)`.

- [ ] **Step 1: Write the failing tests**
```python
def test_built_remotion_beat_without_sketch_is_an_error(): ...
def test_keep_design_beat_is_exempt(): ...                 # meta.design_first.kept lists the beat
def test_layout_needs_exactly_one_hero_and_2_to_6_rects(): ...
def test_rect_outside_0_1_is_named_with_the_beat(): ...
def test_eight_beat_film_without_hero_moments_warns_and_a_seven_beat_one_does_not(): ...
def test_html_tier_and_slide_type_boards_get_no_sketch_rule(): ...   # Review Focus 2
```
- [ ] **Step 2:** Run → FAIL.  - [ ] **Step 3:** Implement.  - [ ] **Step 4:** PASS + `pytest tests/test_validate*.py -q`.
- [ ] **Step 5:** Commit.

### Task 4: `sketch_sheet.py` — greybox tiles and what they measure

**Files:**
- Create: `scripts/sketch_sheet.py`
- Modify: `SKILL.md` (3.6: show `_sketch_review.png` BEFORE building; the built `_design_review.png` stays second),
  `references/pipeline-scripts.md`
- Test: `tests/test_sketch_sheet.py`

**Interfaces:**
- Consumes: Task 3 schema; `_caption_band.caption_reserve_px` / the per-aspect band.
- Produces: `tile(slide, W, H) -> PIL.Image`; `findings(slides, W, H) -> list[str]`; CLI writes
  `<out_dir>/_sketch_review.png` and copies it to `~/Desktop/<film>_sketch.png` (`--no-desktop` for tests); exit 1 on
  findings. Findings: hero share < `HERO_MIN = 0.12` of the content zone; ink share below `shot_proof.SPARSE_MEDIAN`
  at film median; the same layout (rects within 0.05) on 3 beats running; a rect inside the caption band; empty
  metaphor.

- [ ] **Step 1: Write the failing tests** — one per finding, plus `test_vertical_board_uses_the_257px_band`
  (Review Focus 3), plus `test_through_object_ribbon_joins_tiles_of_its_beats` (pixel probe between two tiles).
- [ ] **Step 2:** FAIL.  - [ ] **Step 3:** Implement with PIL only (no Chrome).  - [ ] **Step 4:** PASS.
- [ ] **Step 5: Corpus check.** In a scratch copy of the GPS board, hand-write sketches from its `_design_review.png`
  (what each beat actually shows) and run the sheet. Record findings in `references/craft-bar.md`. If it finds
  nothing, apply the spec's anti-goal (sheet only, findings to WARN) as a ledgered ruling.
- [ ] **Step 6:** Commit.

### Task 5: Through-object hand-on (C1)

**Files:**
- Modify: `scripts/validate.py` `_through_object` (advisory → ERROR), `scripts/render_remotion.py` (pass `track`),
  `remotion/src/Film.tsx` (context), create `remotion/src/runtime/track.ts`
- Test: `tests/test_through_object.py`, `tests/test_track.py`

**Interfaces:**
- Produces: `slide.track = {object: str, in: Pose, out: Pose}`, `Pose = {x, y, scale, rot, state?}` (frame fractions,
  degrees); `trackAt(track, t01) -> Pose` (eased, in `track.ts`); a shot receives prop `track`. A pair on
  `through_object` is joined when stage/container/same shot (as today) OR `out` of N equals `in` of N+1 within 0.01.
  `through_object.waive = [{pair: "3→4", reason}]` clears a pair.

- [ ] **Step 1: Failing tests:** unjoined pair is now in errors; matching poses join; mismatched poses name both
  values; `beats: [4, 2, 9]` with no beat 9 → pairs follow the list and 9 is named (Review Focus 5); `trackAt`
  returns `in` at 0 and `out` at 1 (tsprobe).
- [ ] **Step 2-4:** FAIL → implement → PASS; `stale_measurements.py` shows nothing stale (Film.tsx is not a register).
- [ ] **Step 5:** Commit.

### Task 6: The environment answers, and characters move like characters (C2, C3)

**Files:**
- Create: `remotion/src/runtime/reacts.ts`, `remotion/src/runtime/character.ts`
- Modify: `references/building-blocks.md` (one example each)
- Test: `tests/test_reacts_character.py` (tsprobe)

**Interfaces:**
- Produces: `react(kind: 'rise'|'light'|'press'|'ripple', d: number, opts?) -> {dy, scale, glow}` where `d` is the
  object's distance to the element in element widths (0 = on it); `contactTimes(path, items) -> number[]`;
  `hop(t01, opts) -> {y, sx, sy}` with anticipation squash before take-off, arc, landing squash; `sx * sy == 1`
  (volume kept); `stagger(i, n, t01, lag)`.

- [ ] **Step 1: Failing tests:** `press` peaks at d=0 and is 0 beyond d=1; `hop` has `sy < 1` just before take-off
  and just after landing; `abs(sx*sy-1) < 1e-6` over 200 samples; reactions are pure (same input → same output).
- [ ] **Step 2-4.**  - [ ] **Step 5:** Commit. (Ruling recorded: the generic proof register is built in the
  validation film's workshop, Task 12, not the library — a library register re-keys four manifests; promote later.)

### Task 7: `subject_craft_qa.py` — measures (D1)

**Files:**
- Create: `scripts/subject_craft_qa.py`
- Test: `tests/test_subject_craft.py`

**Interfaces:**
- Consumes: `fidelity` FIDELITY-PARTS record (`fidelity.union(boxes)`), plate ID pass for Blender beats, settled frame
  at 90 % of the beat (shot_proof's `_proof/beat_NN.png` when current).
- Produces: `measure(rgb: np.ndarray, mask: np.ndarray) -> {lum_range, rim_sep, highlight, detail, flat_share}`;
  `subject_mask(out_dir, beat) -> np.ndarray | None`; CLI prints a row per hero beat, `NOT MEASURED (<why>)` when the
  mask is None.

- [ ] **Step 1: Failing tests** on synthetic images: a lit sphere with a rim light beats a flat disc on
  `lum_range`, `rim_sep`, `highlight`; a flat disc has `flat_share > 0.9`; a hero with no mask → NOT MEASURED and
  exit 1 (Review Focus 4); a non-hero with no mask → listed, exit 0.
- [ ] **Step 2-4.**  - [ ] **Step 5:** Commit.

### Task 8: Calibrate subject craft on the corpus (D2)

**Files:**
- Modify: `scripts/subject_craft_qa.py` (thresholds), `references/craft-bar.md` (the table)
- Test: `tests/test_subject_craft.py` (threshold test on recorded corpus numbers, stored as a small JSON fixture of
  measured values — numbers only, no frames)

- [ ] **Step 1:** Run the measures on GPS, HTTPS and ANC hero-like beats (the subject beats each film already has);
  write the table.
- [ ] **Step 2:** Pick thresholds only if they FAIL the HTTPS line subjects + the GPS beats and PASS ANC plates.
  Otherwise ledger a ruling and ship measures as report-only.
- [ ] **Step 3:** Test pins the fixture verdicts. - [ ] **Step 4:** Commit.

### Task 9: Light to build with (D3)

**Files:**
- Create: `remotion/src/runtime/lighting.tsx`
- Modify: `blender/kit/stage.py` (`product_rig`), `references/blender-plates.md`, `references/building-blocks.md`
- Test: `tests/test_lighting.py` (tsprobe), `tests/test_blender_rig.py` (skips without Blender)

**Interfaces:**
- Produces: `rimGradient(box, side, strength) -> {stops, angle}`, `keyFalloff(box, key:[x,y]) -> radial stops`,
  `contactShadow(box, ground) -> {rx, ry, opacity}`; `product_rig(subject, cam, key_az=35, rim_strength=1.0) ->
  {key, fill, rim}` with the rim light linked to `subject` only.
- [ ] **Step 1: Failing tests:** rim stops are brightest at the chosen edge; rig's rim light-linking collection holds
  exactly the subject (Blender background run).
- [ ] **Step 2-4.**  - [ ] **Step 5:** Commit.

### Task 10: Density and real use (E1, E2, E4)

**Files:**
- Modify: `scripts/shot_proof.py` `tonal_warnings` → returns `(errors, warnings)`; SPARSE is an error unless
  `meta.sparse_reason`; hero and title beats excluded from the median. `scripts/validate.py` (real-use share on
  launch/promo: beats with `slide.real_use: true` or a FilmScreen/media shot ≥ 1/3 else WARN; promo with
  `hero_moments` and none previewed in the first 5 s — ColdOpen naming it — WARN). `agents/content-planner.md` rule 7c.
- Test: `tests/test_density_real_use.py`
- [ ] **Step 1: Failing tests:** median 7 % → error; with `sparse_reason` → warning; hero beats excluded change the
  median; html tier untouched; explainer film gets no real-use warning; promo at 2/9 real-use warns.
- [ ] **Step 2-4.** Update the callers of `tonal_warnings`.  - [ ] **Step 5:** Corpus: HTTPS errors, GPS and ANC
  pass; record it. - [ ] **Step 6:** Commit.

### Task 11: The zoom follows the action (E3)

**Files:**
- Modify: `remotion/src/shots/FilmScreen.tsx` (prop `focusTrack`), `scripts/workshop.py` (`media add --track
  <json>`), its LIBRARY.md entry; re-measure FilmScreen in the four manifests
- Test: `tests/test_filmscreen_track.py`
- [ ] **Step 1: Failing tests:** the track is smoothed (no step > 2 % of the frame per frame); the close-up never
  exceeds the recording's own pixels (media_res bound) even when the track asks; a malformed track is refused loudly.
- [ ] **Step 2-4.**  - [ ] **Step 5:** `stale_measurements.py` → re-measure FilmScreen only. - [ ] **Step 6:** Commit.

### Task 12: Hero camera grammar (F1-F4)

**Files:**
- Create: `remotion/src/runtime/heroCamera.tsx`
- Modify: `scripts/render_remotion.py` `_CAMERA_MOVES` += `reveal, macro, context`; `remotion/src/Film.tsx`
  (route those moves to heroCamera); `scripts/validate.py` cam_vocab (~2077) and the push/pull rule (~1927);
  `references/camera-and-bridges.md`
- Test: `tests/test_hero_camera.py`
- **Interfaces:** `heroCamera(move, t01, layers: {depth}[]) -> per-layer {tx, ty, scale, blur}` — layers move by
  depth (parallax, F1); `macro` blurs by depth distance from the focus layer (F4); labels get `labelOpacity(t01) = 0`
  until the move settles (F3). Hero moves are valid only on `hero_moments` beats (else WARN).
- [ ] **Step 1: Failing tests:** two layers at different depths move different amounts on `reveal`; `labelOpacity`
  is 0 while moving and 1 after settle; validate accepts `macro` on a hero beat and warns on a non-hero.
- [ ] **Step 2-4.**  - [ ] **Step 5:** Render one macro beat still + 1 s and measure its cost; write it in the doc.
- [ ] **Step 6:** jitter_qa on that beat: 0 ERROR. - [ ] **Step 7:** Commit.

### Task 13: Full suite, then the validation film (G)

- [ ] **Step 1:** Full suite (`suite_par.py` driver in film_work); every failure named and fixed or explained.
- [ ] **Step 2:** Film `机械键盘为什么好按`, Chinese narration, through the normal pipeline in
  `~/code_project/film_work/keyboard`: interview answers already given (purpose teach, zh, Remotion + Blender, 2-3 min,
  16:9); research; ask before any reference-photo download.
- [ ] **Step 3:** Sketch sheet to the Desktop and the user's OK before any shot is built.
- [ ] **Step 4:** Build: the switch as the lit hero (Blender `product_rig`, `macro` on the stem), the hopping object on
  keycaps that `press` (Task 6, workshop shot), the typing UI rebuilt natively, `through_object` handed on.
- [ ] **Step 5:** Gates + `subject_craft_qa` + `taste_ledger check`; measure craft_qa against ANC; hand the film to
  the user (Desktop) before chasing near-floor findings.
- [ ] **Step 6:** Skill defects found by the film get their own TDD fix commits.
