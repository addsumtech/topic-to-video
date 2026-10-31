# Style Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Any drawing style a user names (or shows) is decomposed into a fixed-axis style spec and applied to every beat and object of a Remotion film at render time. A gate proves the drawing changed, not just the colours, and a mandatory sample sheet gets the user's sign-off before the full render.

**Architecture:**
- `meta.style` is validated in Python (`scripts/style_spec.py`), mirrored in TS (`runtime/styleSpec.ts`), and passed to `Film` as `props.style`.
- `runtime/style.tsx` is mounted around each beat's register only when a style exists. It restyles what registers finally draw, in this order: scoped CSS, then an idempotent per-frame DOM pass, then per-element SVG filters, then a surface layer. Stepping lives in `BeatClock`.
- `scripts/style_qa.py` compares styled and unstyled stills per beat.
- `scripts/style_sample.py` builds the sign-off sheet.

**Tech Stack:** Remotion 4 / React / SVG filters / TypeScript; Python 3 + numpy + PIL; pytest; `tests/_tsprobe.py` for pure TS; `npx remotion still|render` for pixels.

**Spec:** `docs/superpowers/specs/2026-10-31-style-engine-design.md`. Read it first. Its "Settled after the builder check" section is binding.

## Global Constraints
- No `meta.style` → the engine is not mounted. Frames are pixel-identical (frame-PNG pixel hashes) to the pre-change commit `87c708d` on a fixed corpus.
- Every effect is a pure function of the frame. Seeds come from `boilPhase(t, durF, fps, hz, phases)` (`runtime/draw.ts`). Never use `Math.random`, `Date`, timers, or frame-order state.
- Captions are never restyled. Body text is never wobbled, posterized or textured. Display type may take an outline and a face.
- Evidence images are never repainted: frame, border and grade only.
- Text is never moved in z-order. Filters and outlines go per element: on shapes, and on groups that hold no text.
- Axes are general drawing properties. No axis, value or code path is named after a style.
- Stepping quantizes the register clock AFTER the sync warp (floor to the step). Captions, audio, seams and camera stay on ones.
- `--reduced-motion` / `meta.reduced_motion`: boil off, stepping off, wobble static.
- A paid image API is never called without per-run user permission. Codex is the generation path.
- Px values are stated at a 1080 px short side and scaled by short side (as `jitter_qa.frame_scale`).
- Library sweeps run once at the end (Task 11). The dev loop uses the corpus in `tests/fixtures/style/corpus.json`.
- Run renders under the lock: `L=/Users/donghanglyu/code_project/film_work/tools/rlock.py; python3 $L -- <cmd>`.
- Stage named paths only. No push.

## Review Focus
1. **CJK and Latin text inside SVG `<text>`/`<tspan>`, and HTML text inside a shape group.** It must be classified as text, never wobbled or outlined, and keep its geometry. Owner: Task 3, test `test_svg_text_is_text`.
2. **9:16 platform-safe film.** The register is drawn on the `regFrame` path, with a `SafeEcho` margin. The style must apply on that path, and the ground-only echo must not get outlines or texture over its hidden children. Owner: Task 3, test `test_style_mounts_on_both_register_paths`.
3. **Dark ground with `line.color:'ink'`.** The outline must resolve to whichever of DNA `fg`/`bg` contrasts with the shape it outlines, never to an invisible colour. Owner: Task 3, test `test_ink_outline_contrasts_on_dark_and_light_grounds`.
4. **A beat drawn twice in a seam** (a container seam's copy). Both copies are styled identically on the same frame, with the same boil phase. Owner: Task 4, test `test_seam_copies_boil_in_phase`.
5. **Reduced motion.** No boil, no stepping, and two adjacent frames of a static beat are identical. Owner: Task 5, test `test_reduced_motion_freezes_style_motion`.

---

### Task 1: The style spec — schema, validation, plumbing

**Files:**
- Create: `scripts/style_spec.py`, `remotion/src/runtime/styleSpec.ts`, `tests/test_style_spec.py`
- Modify: `scripts/validate.py` (remotion meta block, near the `design_dna` checks), `scripts/render_remotion.py:841-852` (pass `props["style"]`), `remotion/src/Film.tsx` (accept `style?: StyleSpec | null`, provide `StyleContext`)

**Interfaces:**
- Produces (Py):
  - `AXES: dict[str, dict[str, Spec]]`: the axis table, one source of truth.
  - `validate_spec(spec: dict) -> tuple[list[str], list[str]]`: errors, warnings.
  - `spec_sha256(spec: dict) -> str`: canonical JSON, sorted keys, `shortfalls` and `refs[].credit` excluded.
  - `is_recolour_only(spec) -> bool`: no structural axis away from `as-drawn`.
  - `structural_axes(spec) -> list[str]`: dotted names set away from `as-drawn`.
- Produces (TS):
  - `type StyleSpec`;
  - `StyleContext`;
  - `useStyle(): StyleSpec | null`;
  - `AXIS_DEFAULTS`, which must equal the Py table (parity test).

Axis set to start from (the builder may extend it, never with style-named values):

- `line {weight:number|'as-drawn', variance:0..1, color:'as-drawn'|'ink'|'fill-dark'|hex|'none', outline:'none'|'outer'|'all', join:'as-drawn'|'round'|'miter', wobble:px≥0, boil_hz:0|6..12}`
- `fill {mode:'as-drawn'|'flat'|'cel'|'texture', steps:2..5}`
- `shade {mode:'as-drawn'|'none'|'cel'|'soft'|'hatch'}`
- `shadow {mode:'as-drawn'|'none'|'hard-offset'|'soft', offset:px}`
- `form {corner:scale≥0, simplify:0..1}`
- `surface {kind:'none'|'paper'|'canvas'|'brush'|'grain', strength:0..1, source:'procedural'|'generated'}`
- `type {display:'as-dna'|string, display_outline:bool}`
- `motion {stepping:1|2|3, easing:'as-drawn'|'overshoot'|'snappy'|'floaty', squash:0..1}`
- Provenance: `name, refs[{src, from:'user'|'found', credit?}], refs_missing?, notes, shortfalls[{axis,wanted,got,why}]`.

- [ ] **Step 1: Write failing tests** in `tests/test_style_spec.py`:
  - `test_unknown_axis_or_value_is_an_error`: `{'line':{'boldness':3}}` and `{'fill':{'mode':'watercolour'}}` each give an error naming the axis.
  - `test_refs_required_unless_reason_given`: `refs:[]` → error; `refs:[]` with `refs_missing:'offline'` → no error.
  - `test_all_as_drawn_is_recolour_only_and_warns`: `is_recolour_only` is True and there is one warning containing "only the palette changes".
  - `test_no_axis_is_named_after_a_style`: no key or enum value in `AXES` matches `cartoon|anime|ghibli|watercolou?r|ink-wash|pixel|comic|manga|clay` (case-insensitive).
  - `test_sha_ignores_shortfalls_and_credit`.
  - `test_ts_axis_table_matches_python` (`_tsprobe`, skip if unavailable).
  - `test_render_passes_style_prop`: `render_remotion` props builder puts `meta.style` into `props["style"]` unchanged, and omits it when absent.
  - `test_validate_rejects_bad_style` (via `validate.py --json` on a fixture board).
- [ ] **Step 2: Run** `python3 -m pytest tests/test_style_spec.py -q` and check it fails.
- [ ] **Step 3: Implement** the Py module, the TS mirror, validate.py wiring (errors block, warnings print), the render_remotion prop, and the Film prop plus context. Film still mounts nothing else.
- [ ] **Step 4: Run** the tests, `cd remotion && npx tsc --noEmit`, and `python3 -m pytest tests/test_finish_layer.py tests/test_film_board.py -q`. All pass.
- [ ] **Step 5: Commit** the named files: `style: the style spec — fixed general axes, validation, plumbing`.

### Task 2: Spike — is a per-frame DOM pass robust? (decision gate)

**Files:**
- Create: `remotion/src/runtime/style.tsx` (minimal: `StyleLayer` with the DOM pass for `line.weight` and `fill.mode:'flat'` only), `tests/fixtures/style/corpus.json`, `tests/fixtures/style/spike_spec.json`, `scripts/style_spike.py`, `references/style-engine-spike.md`
- Modify: `remotion/src/Film.tsx`: conditional mount of `StyleLayer` around `<BeatClock>` on both register paths (with `regFrame` inside `SafeEcho`, and without). It is a fragment pass-through when `useStyle()` is null.

**Interfaces:**
- Produces: `StyleLayer: React.FC<{beat: number; durF: number; children}>`, and `applyDomPass(root: Element, spec: StyleSpec, frame: number, fps: number): DomPassReport`. The report is `{shapes:number; text:number; images:number; canvas:number; changed:number}`.
- `corpus.json`: ~15 shots, including at least:
  - raw-SVG registers with inline gradients;
  - a CSS-3D / `stage3d` register;
  - a camera-heavy register;
  - a labelled diagram;
  - a CJK-text register;
  - one evidence register with a fixture image;
  - one workshop library object (`GearTrain`);
  - one canvas register.

  Each entry has `{shot, props, frame}`.

- [ ] **Step 1:** `scripts/style_spike.py` renders each corpus entry styled through `determinism_qa`'s `Renderer`. It asks three determinism questions: twice, concurrency, cold. It also dumps the text census (`textSafe`), styled and unstyled, and compares text boxes.
- [ ] **Step 2: Run** it under the lock. Record per shot: deterministic yes/no, text boxes moved (max px), `DomPassReport`, and the settled-frame PNGs.
- [ ] **Step 3: Look** at each styled PNG beside its unstyled twin.
- [ ] **Step 4: Decide and write it down** in `references/style-engine-spike.md`, with the numbers. The DOM pass is kept only if ALL of these hold:
  - every corpus shot is deterministic;
  - no text box moves by more than 0.5 px;
  - the visible change matches the spec.

  Otherwise it is **codemod**, and execution STOPS here. Report to the user with the measurements, and revise Tasks 3–4 to "route strokes/gradients/shadows through `runtime/draw` primitives plus a lint" before continuing.
- [ ] **Step 5: Commit**: `style: spike — the per-frame DOM pass measured on 15 hard registers`.

### Task 3: Engine — shape axes (CSS + DOM pass)

**Files:**
- Modify: `remotion/src/runtime/style.tsx`
- Create: `remotion/src/runtime/styleClassify.ts`, `tests/test_style_engine.py`

**Interfaces:**
- Consumes: `StyleSpec`, `useStyle`, `applyDomPass` (Task 2).
- Produces:
  - `classify(el: Element): 'text'|'display'|'shape'|'image'|'canvas'|'echo'|'caption'`. Display = an element marked `data-type-role="display"`, or the largest-type heading of the beat by computed px (as `titleProbe`).
  - `inkFor(shapeFill: string, dna: DesignDNA): string`.
  - `styleCss(spec, dna, scale): string`.
  - `DomPassReport` gains `byAxis: Record<string, number>`.

- [ ] **Step 1: Write failing tests** (`_tsprobe` against jsdom-free pure helpers where possible; still renders behind `STYLE_RENDER=1`):
  - `test_svg_text_is_text`: `<text>`, `<tspan>`, `<foreignObject>` HTML text and CJK text all classify as `text`.
  - `test_caption_and_echo_untouched`: elements under the caption track and `[data-echo]` classify as `caption`/`echo`, and the pass changes nothing there.
  - `test_ink_outline_contrasts_on_dark_and_light_grounds`: `inkFor('#f4d35e', TERMINAL_DNA)` and `inkFor('#1b2a41', EDITORIAL_DNA)` each meet a WCAG ratio ≥ 3 against the fill.
  - `test_gradient_flattens_to_mean_and_cel_quantizes`: a two-stop gradient gives one colour (flat), or `steps` bands whose colours are ordered (cel).
  - `test_outline_all_adds_a_stroke_to_every_filled_shape_and_no_text`.
  - `test_style_mounts_on_both_register_paths`: static check of `Film.tsx` that `StyleLayer` wraps `BeatClock` in both branches, and no `StyleLayer` is inside `SafeEcho`'s hidden children.
  - `test_unstyled_film_tree_is_unchanged`: with `style` null, `StyleLayer` returns its children (static source check, as `test_finish_layer`).
  - `test_evidence_images_are_never_repainted` (`STYLE_RENDER`): PhotoPlate with a fixture image. The image's pixel region is identical styled and unstyled, except the frame/border ring.
- [ ] **Step 2: Run** and check they fail.
- [ ] **Step 3: Implement** the remaining shape axes: line weight/color/outline/join/variance, fill flat/cel, shade (cel = two-tone split along the DNA key light; hatch = pattern fill), shadow (none/hard-offset/soft), form corner scale and simplify (simplify drops decorative strokes below a width threshold, never a fidelity part: elements under `[data-part]` are excluded), and display type outline/face.
- [ ] **Step 4: Run** the tests, tsc, `python3 -m pytest tests/test_fidelity.py tests/test_text_safe*.py -q`, and `FIDELITY_RENDER=1` fidelity sheets of the 4 library objects under `spike_spec.json`, which must show no new finding.
- [ ] **Step 5: Commit**: `style: shape axes — line, fill, shade, shadow, form, display type`.

### Task 4: Engine — per-pixel filters and the surface

**Files:**
- Modify: `remotion/src/runtime/style.tsx`
- Create: `remotion/src/runtime/styleFilters.tsx`, `remotion/src/runtime/styleSurface.tsx`
- Test: `tests/test_style_engine.py`

**Interfaces:**
- Produces:
  - `<StyleFilterDefs spec frame fps durF scale/>`, which renders `<filter id="style-wobble">`, `style-posterize` and `style-edge`.
  - `wobbleSeed(frame, durF, fps, hz): number`, derived from `boilPhase`; constant when `hz=0` or reduced motion.
  - `<StyleSurface spec dna texture?: string/>`.

- [ ] **Step 1: Failing tests:**
  - `test_wobble_seed_is_a_pure_function_of_frame`: same args give the same seed; the seed changes at `hz` and is constant within a hold.
  - `test_seam_copies_boil_in_phase` (`STYLE_RENDER`): render a container seam frame; the two copies' wobble seeds (read from the `data-style-seed` attribute) are equal.
  - `test_text_never_wobbles` (`STYLE_RENDER`): run `jitter_qa` on a 2 s styled clip of a CJK-text register with `wobble:3, boil_hz:8`. There is zero text finding, and the shapes measurably move between holds.
  - `test_surface_is_static_and_below_text`: the surface layer is static (no `useCurrentFrame`), and is mounted under display and body text in z-order.
- [ ] **Step 2: Run** and check they fail.
- [ ] **Step 3: Implement.** Filters attach per element through the DOM pass (Task 3's classification), never on a layer that holds text. Edge-outline is the fallback for shapes the pass could not stroke (`DomPassReport.byAxis` records it).
- [ ] **Step 4: Run** the tests, then `scripts/determinism_qa.py` on a styled corpus film (twice/concurrency/cold), which must be all clean.
- [ ] **Step 5: Commit**: `style: wobble, boil, posterize, edge fallback, surface`.

### Task 5: Motion — stepping, easing, squash

**Files:**
- Modify: `remotion/src/Film.tsx` (`BeatClock`), `remotion/src/runtime/motion.ts` (+ `glide.ts`/`springAt` callers through one helper), `scripts/sync_qa.py`
- Test: `tests/test_style_motion.py`

**Interfaces:**
- Produces:
  - `stepFrame(f: number, step: 1|2|3): number` = `f - (f % step)`, applied after `warpFrame`.
  - `useStyleEase(): (p:number)=>number`.
  - `squashAt(p, amount): {sx, sy}` with `sx*sy === 1`.
  - `sync_qa` tolerance `+= (stepping-1)` frames only when `meta.style.motion.stepping > 1`, printed in its report.

- [ ] **Step 1: Failing tests:**
  - `test_stepping_after_warp_is_monotone`: for a sample warp, `stepFrame(warpFrame(f))` is non-decreasing over 0..300.
  - `test_reduced_motion_freezes_style_motion`: under reduced motion, `stepFrame` is the identity, and `wobbleSeed` is constant.
  - `test_captions_audio_camera_stay_on_ones`: static check that only `BeatClock` reads `stepping`.
  - `test_squash_preserves_area`.
  - `test_sync_tolerance_only_when_stepping`.
  - `test_easing_coverage_listed`: `scripts/style_coverage.py --motion` lists the registers that hand-roll easing (no import of the shared helpers). The list is non-empty and printed, not hidden.
- [ ] **Step 2: Run** and check they fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the tests, plus `python3 -m pytest tests/test_sync*.py tests/test_cue*.py -q`.
- [ ] **Step 5: Commit**: `style: motion — stepping after the warp, easing and squash through the shared helpers`.

### Task 6: Hooks, exemptions, coverage

**Files:**
- Create: `scripts/style_coverage.py`, `tests/test_style_coverage.py`
- Modify: the 2 canvas shots and the 18 image shots (add `export const STYLE_EXEMPT = {reason: '...'}`; an evidence register is exempt for `fill`/`surface`/filters on its image only), `remotion/src/registry.ts` (export a map of `STYLE_HOOKS`/`STYLE_EXEMPT` per shot), `remotion/src/runtime/style.tsx` (honour them)

**Interfaces:**
- Produces: `coverage(out_dir|--library, spec) -> {axis: {reached:[shot], exempt:[(shot,reason)], hooked:[shot]}}` and `exempt_fraction(board) -> float`.

- [ ] **Step 1: Failing tests:**
  - `test_every_canvas_shot_is_exempt_with_a_reason`: grep `<canvas|getContext(|@react-three` and assert each such shot has `STYLE_EXEMPT`.
  - `test_every_evidence_register_is_exempt_on_its_image`.
  - `test_exempt_reason_is_not_empty`.
  - `test_coverage_reports_the_quarter_rule`: a board with 3 of 10 beats exempt → `exempt_fraction` 0.3 plus the warning line.
- [ ] **Step 2: Run** and check they fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the tests.
- [ ] **Step 5: Commit**: `style: hooks, exemptions and the coverage report`.

### Task 7: The style gate

**Files:**
- Create: `scripts/style_qa.py`, `tests/test_style_qa.py`, `tests/fixtures/style/` (small styled/unstyled PNG pairs made by the test from rendered stills, not checked-in renders)
- Modify: `scripts/jitter_qa.py` (on a styled board, line-boil on non-text ink is not a finding; text movement still is), `scripts/media_res_qa.py` (a generated surface texture is a raster held to the floor)

**Interfaces:**
- Consumes: `structural_axes(spec)`, `coverage()`.
- Produces: `measure(png_styled, png_unstyled, spec, scale) -> dict[axis, {before, after, changed:bool}]`, `check(out_dir) -> list[Finding]`, and the CLI `style_qa.py <out_dir> [--json]` writing `_style/sheet.png`. Exit 0 clean, 2 on ERROR.
- Measures:
  - edge thickness: distance transform on an edge mask;
  - closed dark contours around filled regions;
  - distinct fill levels inside shape masks, and the residual gradient fraction;
  - texture energy on flat regions: high-pass variance;
  - stepping: identical consecutive frames in a 1 s clip;
  - boil: shape-edge displacement between holds;
  - text stillness: glyph-ink change, reusing `jitter_qa.glyph_change`.
- Tolerances: set from the measured spread of the corpus, and written as constants with the measurement in the comment.
- Manifests: also report each beat's ink and motion energy, styled versus unstyled. When a style moves a beat
  across an energy floor that `register_energy` judged it by, that is a WARN naming the beat. The manifests are
  not re-measured (spec, Constraints).

- [ ] **Step 1: Failing tests** (`STYLE_RENDER`):
  - `test_noop_engine_is_recolour_only_error`: a spec with outline/cel, but `StyleLayer` forced to pass-through via the env `STYLE_FORCE_NOOP=1`, and the DNA hue rotated → ERROR "recolour only".
  - `test_one_unstyled_beat_breaks_consistency`: a 4-beat board with one beat `style_off:true` → ERROR naming that beat.
  - `test_exempt_beats_are_outside_consistency`.
  - `test_cartoon_like_spec_passes`.
  - `test_axis_left_as_drawn_is_not_checked`.
  - `test_jitter_ignores_boil_but_not_text_on_styled_board`.
- [ ] **Step 2: Run** and check they fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the tests, then look at `_style/sheet.png` for the cartoon-like case.
- [ ] **Step 5: Commit**: `style: style_qa — recolour-only and consistency, measured against the unstyled render`.

### Task 8: Sample sheet and sign-off

**Files:**
- Create: `scripts/style_sample.py`, `tests/test_style_sample.py`
- Modify: `scripts/validate.py` (sign-off ERROR), `scripts/render_remotion.py` (refuse the full render without a sign-off; `--sample` allowed), `scripts/deliver.py` (if needed)

**Interfaces:**
- Produces:
  - `pick_beats(board) -> list[int]` (2–3: one diagram/data family, one with `object`, one type-led; the family comes from `shot_director.FAMILY`).
  - `build(out_dir) -> {png, mp4, sample_sha256}` → `~/Desktop/<film> 风格样张.png/.mp4` via `deliver.destination`.
  - `record_signoff(out_dir)` writes `meta.style_signoff {spec_sha256, sample_sha256, user_ok:true}`. It is run by the agent ONLY after the user says yes in chat. The docstring and the SKILL.md line say so.
- Sheet: references on the left, beats at ~90% on the right, and under them the shortfalls, the exempt beats, the `refs_missing` notice (in the title when set), and the recolour-only notice when `is_recolour_only`.

- [ ] **Step 1: Failing tests:**
  - `test_full_render_refused_without_signoff`.
  - `test_signoff_goes_stale_when_spec_changes`.
  - `test_sample_render_allowed_without_signoff`.
  - `test_pick_beats_spans_families`.
  - `test_sheet_states_refs_missing_in_title`.
  - `test_sheet_lists_shortfalls`.
- [ ] **Step 2–4: Run** and check they fail; implement; run them again and check they pass. Look at one real sheet.
- [ ] **Step 5: Commit**: `style: the sample sheet and the sign-off the full render waits for`.

### Task 9: Generated texture (Codex) with procedural fallback

**Files:**
- Modify: `scripts/imagegen.py` (add `texture(out_dir, kind, palette) -> path|None`), `scripts/style_sample.py`/`render_remotion.py` (resolve `surface.source:'generated'`)
- Test: `tests/test_style_texture.py`

**Interfaces:** `texture()` returns a cached tileable PNG via the Codex path. When `_codex_available()` is false it returns None and appends `shortfalls += {axis:'surface.source', wanted:'generated', got:'procedural', why:<codex reason>}`. It never calls the metered path unless `meta.image_source == 'openai'` and the user granted the run.

- [ ] **Step 1: Failing tests:**
  - `test_no_codex_falls_back_with_a_shortfall` (stub `_codex_available` → False).
  - `test_texture_prompt_forbids_text_and_subjects`.
  - `test_stub_texture_is_used_when_present`.
  - `test_metered_path_not_called_by_default`.
- [ ] **Step 2–4: Run** and check they fail; implement; run them again and check they pass.
- [ ] **Step 5: Commit**: `style: generated surface texture through Codex, procedural fallback stated as a shortfall`.

Real generation stays **unverified** while Codex is on the free plan. Say so in the final report.

### Task 10: Decomposition step and docs

**Files:**
- Create: `references/style-engine.md` (the axes, each axis value shown on one register via `scripts/style_axis_gallery.py`, the decomposition procedure, and the rules from Global Constraints), `scripts/style_axis_gallery.py`
- Modify: `agents/design-director.md` (new step: gather refs, write `meta.style` citing a ref per non-default axis, then the sample), `SKILL.md` (index lines for style_spec/style_qa/style_sample/style_coverage, plus the mandatory-sample rule), `references/pipeline-scripts.md` (entries), `remotion/LIBRARY.md` ("Style follows the film's spec" section beside "Type follows the film's DNA")
- Test: extend `tests/test_build_flow_docs.py` (or the existing docs test) with `test_style_scripts_are_indexed_and_documented`.

- [ ] **Steps:**
  - Write the failing doc test, run it, write the docs, and run it again to check it passes.
  - Generate the axis gallery and LOOK at it.
  - Commit: `style: the decomposition step, the axis gallery and the docs`.

### Task 11: Acceptance

- [ ] **Step 1: Cartoon test film.** A self-written topic (not the user's material), ~6 beats, including a workshop object and a CJK display beat, at 9:16.
  - Decompose with found refs.
  - Run `style_sample.py` and deliver the sheet to the Desktop.
  - **STOP and send the sheet to the user.** Continue only on their yes, then `record_signoff`.
  - Full render, then `style_qa` and the existing film gates.
  - Look at frames at ~50% and ~90% of each beat. Deliver the mp4.
- [ ] **Step 2: Full-library sweep**, once: all registers plus library objects under the cartoon spec at 16:9 and 9:16. Record crashes (must be 0), the coverage report and fidelity findings (must be no new ones).
- [ ] **Step 3: Pixel identity.** No `meta.style`: the corpus frames' pixel hashes at HEAD equal those at `87c708d`.
- [ ] **Step 4: Full suite** via `suite_by_file.py`, all green.
- [ ] **Step 5: Held-out styles.** Ask the user (AskUserQuestion) to pick 2–3 styles. Run each through decomposition → sample sheet with no code change. Report per axis what worked, plus every shortfall. A style that needs code is reported, not fixed inside acceptance.
- [ ] **Step 6:** Update the memory entry for topic-to-video with the commit range. Do not push; report what is unpushed.
