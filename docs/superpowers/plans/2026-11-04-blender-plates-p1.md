# Blender Plates P1 (contract + core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A beat can carry a Blender plate: `blender_plate.py` builds it from a scene script (RGBA WebM plus per-frame anchors, object boxes and camera), a workshop shot draws it through `BlenderPlate`/`usePlate`, and `plate_qa.py` fails a film whose type sits on a plate object.

**Architecture:**
- Blender runs headless. `blender/runner.py` and `blender/kit/*` import a film's scene script (`<out_dir>/blender/<name>.py`, with `build(k)` and `pose(k, t)`) and render two passes per frame: EEVEE RGBA, plus a Workbench flat-colour ID pass at half size.
- The host script `scripts/blender_plate.py` keys each plate, budgets it, runs Blender, encodes VP9-alpha WebM, derives boxes from the ID pass and writes `workshop/assets/plates.ts`.
- Remotion plays the plate with `OffthreadVideo transparent` and exposes its anchors and boxes.
- A Film-only audit (`runtime/plateClear.tsx`) reports text-vs-plate-object overlaps. `plate_qa.py` judges them.

**Tech Stack:** Python 3 (host, pytest), bpy inside Blender ≥ 5.0, ffmpeg (libvpx-vp9), Remotion 4.0.486 / React / TypeScript.

**Spec:** `docs/superpowers/specs/2026-11-04-blender-plates-design.md` (P1 = §10 P1; contract §4; costs §8; decisions §9)

## Global Constraints

- Blender ≥ 5.0. The EEVEE engine id is `BLENDER_EEVEE`. Locate the binary in this order:
  `meta.blender`, env `TTV_BLENDER`, `/Applications/Blender.app/Contents/MacOS/Blender`, `blender` on PATH.
  A release candidate is usable, with a WARN.
- Cycles uses the GPU only (Metal/CUDA/OptiX devices `use=True`, CPU `use=False`). Measured on this machine:
  CPU+GPU at 128 spp took 67 s/frame; GPU-only at 64 spp took 13–19 s/frame.
- Plate time 0 = the beat's Sequence frame 0 = the beat's audio start. A cue's time is its word's `t` in
  `audio/NN.words.json`, matched with `cues._find`.
- An unmatched cue phrase is an error. Never interpolate it (`resolve_cues` does interpolate, so do not use it here).
- The plate's frame count = that scene's `durF` from `render_remotion.film_props`. Its size = the film's frame (`render._canvas` / meta width/height), never a fixed 1920×1080.
- The ID pass renders at half the frame size (Workbench, flat lighting, object colour, `render_aa = "OFF"`, Standard view transform). Boxes are scaled ×2 back to frame pixels.
- Plate video: `ffmpeg -c:v libvpx-vp9 -pix_fmt yuva420p -crf 12 -b:v 0 -auto-alt-ref 0` → `media/blender/<id>/plate.webm` (mode `env` uses `-pix_fmt yuv420p`).
- Cost constants, all measured (spec §8): `SEC_PER_FRAME = {"eevee": 4.6, "cycles": 16.0}`, ID pass 0.72 s/frame, Blender start-up 10 s per plate.
- Budget: `meta.blender_budget_min`, default 60. Over budget, `blender_plate.py` exits 3 with the estimate unless `--yes`. The agent asks the user before passing `--yes`.
- `blender_why` vocabulary is exactly: `real-world`, `material`, `physics`, `optics`, `space`.
- Never edit a runtime module that registers import (textSafe.tsx, layout.ts, motion.ts, fonts.ts, dna.ts, cue.ts …): that re-keys the library manifests. New logic goes in new modules. `Film.tsx` may change (only Root imports it).
- No downloads without the user's permission. In P1, every file a scene declares in `blender.assets` must have a `<file>.json` sidecar with `license` and `source`.
- Stage named paths only. Never `git add -A`. No push. The worktree is `.worktrees/blender-plates`. Before Task 1, symlink `remotion/node_modules` to the main checkout's (as in peer-round4).

## Review Focus

1. **A re-voiced beat.** A beat whose duration changed after its plate was built: `validate` must ERROR "plate stale" and `blender_plate.py` must rebuild it, because the key includes `frames`. → Task 2 `test_stale_plate_after_retime_is_an_error`, Task 4 `test_key_moves_with_each_input`.
2. **Partly hidden objects.** An object that leaves the frame or is fully occluded mid-plate: its box is `null` on those frames, and its anchor reports `visible: false` instead of a stale point. → Task 3 `test_offscreen_anchor_is_not_visible`, Task 4 `test_boxes_null_when_absent`.
3. **A 9:16 or otherwise non-1080p film.** The plate renders at the film's own size and anchors land in that frame. → Task 3 `test_portrait_frame_size`, Task 5 `test_plate_scales_to_frame`.
4. **Blender missing, older than 5.0, or broken.** `blender_plate.py` exits 2 naming the cause; doctor lists it; validate reports the plate missing. Never a silent skip. → Task 1 `test_version_floor_refused`, Task 4 `test_no_blender_exits_2`.
5. **A render that dies part-way.** The next run resumes only frames of the SAME key. A partial render of an older key is discarded, never mixed in. → Task 3 `test_resume_skips_done_frames`, Task 4 `test_partial_of_old_key_discarded`.

---

### Task 1: Locate Blender, check its version, report it in doctor

**Files:**
- Create: `scripts/blender_plate.py` (start of the module: locator + version only)
- Modify: `scripts/doctor.py` (one `CHECKS` row)
- Test: `tests/test_blender_plate.py`

**Interfaces:**
- Produces:
  - `blender_bin(meta: dict | None = None) -> str | None`
  - `blender_version(binary: str) -> tuple[int, int, int, bool]` (major, minor, patch, is_rc). Raises `PlateError` when the output has no version line.
  - `class PlateError(Exception)`
  - `MIN_BLENDER = (5, 0)`

- [ ] **Step 1: Write the failing tests**

```python
def test_blender_bin_order(tmp_path, monkeypatch):
    fake = tmp_path / "Blender"; fake.write_text("#!/bin/sh\n"); fake.chmod(0o755)
    monkeypatch.setenv("TTV_BLENDER", str(fake))
    assert bp.blender_bin({"blender": str(fake)}) == str(fake)
    assert bp.blender_bin({}) == str(fake)
    monkeypatch.setenv("TTV_BLENDER", str(tmp_path / "missing"))
    monkeypatch.setattr(bp, "_APP_PATHS", ())
    monkeypatch.setattr(bp.shutil, "which", lambda n: None)
    assert bp.blender_bin({}) is None

@pytest.mark.parametrize("line,want", [("Blender 5.2.4 LTS Release Candidate", (5, 2, 4, True)),
                                       ("Blender 5.0.1", (5, 0, 1, False))])
def test_version_parse(line, want, monkeypatch):
    monkeypatch.setattr(bp, "_version_line", lambda b: line)
    assert bp.blender_version("x") == want

def test_version_floor_refused(monkeypatch):
    monkeypatch.setattr(bp, "_version_line", lambda b: "Blender 4.2.0")
    with pytest.raises(bp.PlateError, match="5.0"):
        bp.require_blender({"blender": "x"})

def test_doctor_lists_blender():
    import doctor
    assert any(row[0] == "blender" and row[1] is False for row in doctor.CHECKS)
```

- [ ] **Step 2: Run them and see them fail**
  Run: `python3 -m pytest -q tests/test_blender_plate.py`. Expected: FAIL (`ModuleNotFoundError: blender_plate`).
- [ ] **Step 3: Implement**
  - `blender_bin`, `_version_line(binary)` (runs `binary --version`, first line), `blender_version`.
  - `require_blender(meta) -> str`: raises `PlateError` "Blender not found …" or "Blender X.Y is older than 5.0"; prints a WARN on an RC.
  - `_APP_PATHS = ("/Applications/Blender.app/Contents/MacOS/Blender",)`.
  - Doctor row: `("blender", False, lambda: bp.blender_bin() is not None, "Blender plates (remotion beats with slide.blender)", "install Blender ≥ 5.0 from blender.org, or set TTV_BLENDER")`.
- [ ] **Step 4: Run the tests and see them pass**
  Run: `python3 -m pytest -q tests/test_blender_plate.py tests/test_doctor.py`. Expected: PASS.
- [ ] **Step 5: Commit** `scripts/blender_plate.py scripts/doctor.py tests/test_blender_plate.py`: "blender_plate: locate Blender ≥ 5.0; doctor lists it"

### Task 2: The board contract (`slide.blender`), strict cue times, validate

**Files:**
- Modify: `scripts/blender_plate.py`, `scripts/validate.py` (one call in `evaluate`)
- Test: `tests/test_blender_plate.py`, `tests/test_validate_blender.py`

**Interfaces:**
- Consumes: `PlateError` (Task 1).
- Produces:
  - `BLENDER_WHY = ("real-world", "material", "physics", "optics", "space")`
  - `spec_of(slide: dict, out_dir: str) -> dict | None`. Returns the normalised spec `{id, scene, why, mode, engine, cues, anchors, objects, assets}`, or None when the slide has no `blender`. Raises `PlateError` listing every problem.
  - `cue_times(out_dir: str, index: int, phrases: list[str]) -> dict[str, float]` (raises on an unmatched phrase)
  - `plate_dir(out_dir, plate_id) -> str` = `<out_dir>/media/blender/<id>`
  - `plate_state(out_dir, slide, index, meta) -> "missing" | "stale" | "fresh"` (compares `plate.json["key"]` with `plate_key(...)` from Task 4; Task 2 ships it with a stub key that Task 4 replaces)
  - `validate_blender(board, out_dir) -> (errors: list[str], warns: list[str])`

Field rules for `spec_of`:
- `id` matches `^[a-z0-9][a-z0-9-]{0,39}$` and is unique across the board.
- `scene` is a path under `<out_dir>/blender/` ending `.py` that exists.
- `why` ∈ `BLENDER_WHY`.
- `mode` ∈ (`rgba`, `env`), default `rgba`.
- `engine` ∈ (`eevee`, `cycles`), default `eevee`.
- `cues`, `anchors` and `objects` are lists of non-empty strings, default `[]`.
- `assets` is a list of paths under out_dir, each with a `.json` sidecar carrying `license` and `source`.
- `shot` must be a workshop shot (the plate's overlay is the film's own code).

- [ ] **Step 1: Write the failing tests**

```python
def test_spec_rejects_each_bad_field(film):          # film fixture: out_dir with storyboard, audio/01.words.json, blender/s.py
    s = {"blender": {"id": "Bad Id", "scene": "blender/none.py", "why": "pretty", "mode": "x"}, "shot": "BroadcastPlate"}
    with pytest.raises(bp.PlateError) as e:
        bp.spec_of(s, film)
    for word in ("id", "scene", "why", "mode"):
        assert word in str(e.value)

def test_cue_times_strict(film):
    assert bp.cue_times(film, 1, ["广播"]) == {"广播": 2.32}
    with pytest.raises(bp.PlateError, match="不存在的词"):
        bp.cue_times(film, 1, ["不存在的词"])

def test_asset_without_sidecar_is_refused(film): ...   # assets: ["assets/earth.jpg"] with no .json → PlateError "sidecar"

# tests/test_validate_blender.py
def test_missing_plate_is_an_error(film): errs, _ = bp.validate_blender(board, film); assert any("not built" in e for e in errs)
def test_stale_plate_after_retime_is_an_error(film_with_plate): # change slides[0].duration → "stale"
def test_validate_evaluate_carries_blender_errors(film): assert any("blender" in e for e in validate.evaluate(film)["errors"])
```

- [ ] **Step 2: Run them and see them fail.** Run: `python3 -m pytest -q tests/test_blender_plate.py tests/test_validate_blender.py`. Expected: FAIL.
- [ ] **Step 3: Implement** `spec_of`, `cue_times` (a word index via `cues._find(words, phrase, 0)`; `<0` → `PlateError("cue %r is not spoken in beat %d")`), `plate_dir`, `plate_state`, `validate_blender`. In `validate.evaluate`, extend errors and warns from `validate_blender` inside a `try` that turns any exception into an ERROR line (never a silent pass).
- [ ] **Step 4: Run the tests and see them pass.** Run: `python3 -m pytest -q tests/test_blender_plate.py tests/test_validate_blender.py tests/test_validate.py`. Expected: PASS.
- [ ] **Step 5: Commit**: "blender_plate: the slide.blender contract, strict cue times, validate refuses a missing/stale plate"

### Task 3: The Blender side — kit + runner

**Files:**
- Create:
  - `blender/__init__.py` (empty)
  - `blender/kit/__init__.py`
  - `blender/kit/render.py`
  - `blender/kit/stage.py`
  - `blender/kit/anchors.py`
  - `blender/kit/idpass.py`
  - `blender/runner.py`
- Create: `tests/fixtures/blender/cube_scene.py` (a 1-object test scene)
- Test: `tests/test_blender_runner.py` (real Blender; `needs_blender = pytest.mark.skipif(bp.blender_bin() is None, …)`)

**Interfaces:**
- Consumes: nothing from earlier tasks at run time (the runner runs inside Blender's own Python).
- Produces:
  - Runner CLI: `Blender -b --factory-startup --python blender/runner.py -- --scene S --out DIR --frames N --fps F --w W --h H --engine eevee|cycles --mode rgba|env --cues JSON --anchors a,b --objects o,p [--still F]`
  - Runner outputs in `DIR/`: `rgba/%04d.png` (1-based), `ids/%04d.png`, `anchors.json`, `camera.json`, `run.json`. A still writes only `still_%04d.png`.
    - `anchors.json` = `{"w":W,"h":H,"fps":F,"frames":N,"anchors":{name:[[x,y,depth,visible]...]}}`
    - `camera.json` = `{"frames":[{"lens":mm,"sensor":mm,"matrix_world":[16]}...]}`
    - `run.json` = `{"blender": "5.2.4", "ids": {object: "#rrggbb"}, "seconds": s}`
  - Scene-script API:
    - `build(k) -> {"objects": {name: bpy_object}, "anchors": {name: (bpy_object, (x, y, z) local)}}`
    - `pose(k, t: float) -> None`
  - `k` is a `Kit` with `k.scene`, `k.camera`, `k.cue: dict[str, float]`, `k.fps`, `k.frames`, `k.w`, `k.h`, `k.duration`, `k.stage` (module), `k.hexc(hex) -> linear rgba`.
  - `stage.place(cam, obj, sx: float, sy: float, depth: float) -> None` puts obj's origin at screen fraction (sx, sy), 0..1 from the top-left, at `depth` along the view.
  - `stage.face_toward(obj, local_axis: str, target: Vector, toward_lens: float = 0.0) -> None`
  - `anchors.project(scene, cam, p_world) -> [x, y, depth, visible]`. Not visible when behind the camera, outside the frame or occluded. Occlusion is tested with `scene.ray_cast` from the camera, `hit` before the point by more than 1e-3.
  - `anchors.sphere_limb_crossing(scene, cam, centre, radius, from_px) -> [x, y]`: the NEAR crossing on the ray toward the centre (the bug fixed in the spike).

Per-frame passes:
- The RGBA pass uses the scene's engine, `film_transparent = (mode == "rgba")`, AgX.
- The ID pass switches to Workbench (flat, object colour, AA off, Standard transform) and writes at w//2 × h//2. Each named object gets a colour from `idpass.palette(n)`: distinct, fully saturated, `#rrggbb`, deterministic by sorted name. The pass then restores engine, view transform and resolution.
- Resume: a frame whose rgba and ids files both exist and are non-empty is skipped.

- [ ] **Step 1: Write the failing tests** (real Blender, 160×90, 3 frames)

```python
@needs_blender
def test_runner_writes_the_contract(tmp_path):
    out = run_fixture(tmp_path, frames=3, w=160, h=90)        # helper calls the CLI with tests/fixtures/blender/cube_scene.py
    assert sorted(os.listdir(out / "rgba")) == ["0001.png", "0002.png", "0003.png"]
    im = Image.open(out / "rgba/0002.png"); assert im.mode == "RGBA" and im.size == (160, 90)
    assert im.getextrema()[3][0] == 0                          # transparent somewhere
    ids = Image.open(out / "ids/0002.png"); assert ids.size == (80, 45)
    a = json.load(open(out / "anchors.json")); assert len(a["anchors"]["top"]) == 3 and a["anchors"]["top"][0][3] is True
    assert len(json.load(open(out / "camera.json"))["frames"]) == 3

@needs_blender
def test_offscreen_anchor_is_not_visible(tmp_path): # fixture's "far" anchor sits behind the camera → visible False
@needs_blender
def test_portrait_frame_size(tmp_path): out = run_fixture(tmp_path, frames=1, w=90, h=160); assert Image.open(out/"rgba/0001.png").size == (90, 160)
@needs_blender
def test_resume_skips_done_frames(tmp_path): # run 2 frames, note mtimes, run 3 → frames 1–2 untouched, 3 written
```

- [ ] **Step 2: Run them and see them fail.** Run: `python3 -m pytest -q tests/test_blender_runner.py`. Expected: FAIL (runner missing).
- [ ] **Step 3: Implement** the kit modules and the runner to the interfaces above.
  - Port the spike's helpers (`hexc`, limb crossing, camera-space composition) from `~/code_project/film_work/blender_spike/tools/gps_sat.py`.
  - The runner prints `RUNNER-DONE {json}` last. On any scene exception it exits non-zero with the traceback.
- [ ] **Step 4: Run the tests and see them pass.** Run: `python3 -m pytest -q tests/test_blender_runner.py`. Expected: 4 passed.
- [ ] **Step 5: Commit** `blender/ tests/fixtures/blender/cube_scene.py tests/test_blender_runner.py`: "blender kit + runner: RGBA + ID pass + anchors + camera per frame, resumable"

### Task 4: The host build — key, budget, run, encode, boxes, plates.ts

**Files:**
- Modify: `scripts/blender_plate.py` (build + CLI)
- Test: `tests/test_blender_plate.py`, `tests/test_blender_build.py` (one real-Blender end-to-end on the fixture)

**Interfaces:**
- Consumes: Task 1 locator, Task 2 `spec_of` / `cue_times` / `plate_dir`, Task 3 runner CLI and outputs.
- Produces:
  - `plate_key(spec, out_dir, frames, fps, w, h, cue_t: dict, blender_version: str) -> str`: sha256 over the scene bytes, every `blender/**/*.py` in the skill (sorted by relative path), each asset's sha256, sorted cue times rounded to ms, frames, fps, w, h, engine, mode and the version.
  - `boxes_from_ids(ids_dir, colors: dict[str, str], frames: int, scale: int = 2) -> dict[str, list[list[int] | None]]`: per object, per frame, `[x0, y0, x1, y1]` in frame px, or None. A pixel belongs to an object when its RGB lies within 8 of the object's colour on every channel.
  - `estimate_seconds(spec, frames) -> float` = `10 + frames * (SEC_PER_FRAME[engine] + 0.72)`
  - `build(out_dir, only=None, yes=False, still=None) -> list[dict]` (one report per plate)
  - `write_plates_ts(out_dir) -> str` writes `workshop/assets/plates.ts`:
    `export const PLATES: Record<string, Plate> = {"<id>": {src:"media/blender/<id>/plate.webm", w, h, fps, frames, mode, anchors, boxes}}` and `import type {Plate} from '@runtime/blenderPlate';`, with every path quoted in full.
  - CLI exit codes: `0` built or fresh · `1` a build failed · `2` Blender missing/too old · `3` over budget (prints the estimate and `--yes`).

The build runs in `<plate_dir>/.work-<key[:12]>/`. Any other `.work-*` folder is deleted first (an older key's partial). On success it:
1. encodes `plate.webm`;
2. writes `boxes.json`, `anchors.json`, `camera.json`;
3. writes `plate.json` = `{key, frames, fps, w, h, mode, engine, blender, seconds, cues, assets}`;
4. removes the PNG work folder;
5. rewrites plates.ts.

- [ ] **Step 1: Write the failing tests**

```python
def test_key_moves_with_each_input(film): # change scene bytes / a kit file (monkeypatched list) / cue t / frames / engine / version → 6 distinct keys
def test_boxes_from_ids(tmp_path):         # synthetic 4×4 PNGs: red block, a (254,0,1) edge pixel, a frame with no red
    b = bp.boxes_from_ids(d, {"sat": "#ff0000"}, 2, scale=2)
    assert b["sat"][0] == [2, 2, 6, 6] and b["sat"][1] is None
def test_boxes_null_when_absent(tmp_path): ...
def test_over_budget_exits_3(film, capsys): # meta.blender_budget_min = 0.01 → main([...]) == 3 and "--yes" in out
def test_no_blender_exits_2(film, monkeypatch): monkeypatch.setattr(bp, "blender_bin", lambda m=None: None); assert bp.main([film]) == 2
def test_partial_of_old_key_discarded(film): # make .work-deadbeef0000/rgba/0001.png → after build(...) it is gone
def test_plates_ts_names_its_files(film_with_plate):
    import remotion_segments as rs
    ts = open(os.path.join(film_with_plate, "workshop/assets/plates.ts")).read()
    assert "media/blender/sat/plate.webm" in rs.code_named_files(os.path.realpath(film_with_plate), ts)

@needs_blender
def test_build_end_to_end(tmp_path):        # fixture film + cube scene, 4 frames 160×90 → plate.webm has alpha_mode=1, frames == 4, plate_state == "fresh"
```

- [ ] **Step 2: Run them and see them fail.** Run: `python3 -m pytest -q tests/test_blender_plate.py tests/test_blender_build.py`. Expected: FAIL.
- [ ] **Step 3: Implement** to the interfaces. Replace Task 2's stub key in `plate_state` with `plate_key`.
  - Frames, fps, w and h come from `render_remotion.film_props(out_dir, board)` (scene k's `durF`) and the film frame.
  - ffprobe `TAG:alpha_mode=1` is asserted after an rgba encode; a missing alpha tag is a build failure.
- [ ] **Step 4: Run the tests and see them pass.** Run: `python3 -m pytest -q tests/test_blender_plate.py tests/test_blender_build.py tests/test_validate_blender.py`. Expected: PASS.
- [ ] **Step 5: Commit**: "blender_plate build: keyed, budgeted, resumable; VP9-alpha plate, boxes, plates.ts"

### Task 5: Remotion `BlenderPlate` + `usePlate`

**Files:**
- Create: `remotion/src/runtime/blenderPlate.tsx`
- Create: `tests/fixtures/blender_film/` (a one-beat film, built in the test from the Task 3 fixture via `blender_plate.build`, with workshop shot `PlateProbe.tsx`)
- Test: `tests/test_blender_plate_remotion.py` (real Blender + Remotion; skipped when either is absent)

**Interfaces:**
- Consumes: `plates.ts` shape (Task 4).
- Produces (TS):
  - `export type Plate = {src: string; w: number; h: number; fps: number; frames: number; mode: 'rgba' | 'env'; anchors: Record<string, number[][]>; boxes: Record<string, (number[] | null)[]>}`
  - `export const usePlate = (p: Plate) => ({f: number, anchor: (name: string) => {x: number; y: number; depth: number; visible: boolean}, box: (name: string) => {x: number; y: number; w: number; h: number} | null})`
    - The frame is `useCurrentFrame()` clamped to [0, frames−1].
    - Coordinates scale by `useVideoConfig().width / p.w` (and height).
    - An unknown name throws, naming the plate's names.
  - `export const BlenderPlate: React.FC<{plate: Plate}>`: a full-frame `OffthreadVideo` (`transparent` when mode is rgba, `muted`). For each object box on this frame it renders `<div data-plate-object={name} style={{position:'absolute', left, top, width, height, pointerEvents:'none'}} />`.

- [ ] **Step 1: Write the failing test**

```python
@needs_blender_and_remotion
def test_plate_composites_over_the_ground(tmp_path):
    film = make_plate_film(tmp_path)                    # PlateProbe paints #204060 under <BlenderPlate> and a 10 px dot at anchor("top")
    png = remotion_still(film, frame=2)                 # npx remotion still on the Film composition
    assert near(png.getpixel((5, 5)), (0x20, 0x40, 0x60))           # transparent corner shows the ground
    x, y, *_ = anchors_json(film)["anchors"]["top"][2]
    assert near(png.getpixel((round(x), round(y))), DOT_COLOUR)       # the dot sits on the projected anchor
@needs_blender_and_remotion
def test_plate_scales_to_frame(tmp_path): # the same film at 9:16 (meta width/height) → dot at the portrait anchor
```

- [ ] **Step 2: Run it and see it fail.** Run: `python3 -m pytest -q tests/test_blender_plate_remotion.py`. Expected: FAIL (`Cannot find module '@runtime/blenderPlate'`).
- [ ] **Step 3: Implement** `blenderPlate.tsx` to the interface. Only workshop shots import it, never a register.
- [ ] **Step 4: Run it and see it pass.** Run: `python3 -m pytest -q tests/test_blender_plate_remotion.py`. Expected: 2 passed. If the alpha corner check fails, the VP9-alpha decode is broken: stop and record a ruling before switching formats.
- [ ] **Step 5: Commit**: "runtime/blenderPlate: the plate under a workshop shot, its anchors and boxes per frame"

### Task 6: `plate_qa.py` — type must not sit on a plate object

**Files:**
- Create: `remotion/src/runtime/plateClear.tsx`, `scripts/plate_qa.py`
- Modify: `remotion/src/Film.tsx` (a `plateClear?: boolean` prop mounting `<PlateClearAudit/>`, beside `MediaResAudit`), `scripts/critic_ledger.py` (`DELIVERY_GATES` remotion: `plate_qa` when any slide has `blender`)
- Test: `tests/test_plate_qa.py`

**Interfaces:**
- Consumes: `data-plate-object` divs (Task 5); `media_res_qa.census_film` pattern (`ts.glide_bundle`, `ts.glide_run`).
- Produces:
  - Census line `PLATE-CLEAR {"f": frame, "hits": [[text, object, overlap_px2, text_px2]...], "texts": n, "objects": m}`. A text element is an element with a non-whitespace direct text node, computed opacity ≥ 0.25 along its ancestors, `visibility` not hidden, and a rect ≥ 1×1. Overlap is computed on client rects.
  - `judge(frames: dict, beat_of, labels) -> {"errors": [...], "warns": [...]}`
    - ERROR when `overlap / text_area ≥ 0.15` on at least `MIN_FRAMES = 2` sampled frames;
    - WARN at ≥ 0.05;
    - one finding per (beat, text, object), at its worst frame.
  - `main(argv)` exits 0 clean · 1 errors · 2 unmeasured, with the same scope lines and NOTHING TO JUDGE wording as media_res_qa.

- [ ] **Step 1: Write the failing tests**

```python
def test_judge_needs_two_frames():
    fr = {3: {"hits": [["我在哪", "sat", 400, 1000]], "texts": 1, "objects": 1}}
    assert bp_qa.judge(fr, lambda f: 0, [1])["errors"] == []
    fr[6] = fr[3]
    assert "我在哪" in bp_qa.judge(fr, lambda f: 0, [1])["errors"][0]
def test_judge_warn_band(): ...          # 0.08 → warn only
def test_gate_listed_only_with_blender_beats(): # critic_ledger.delivery_gates(board) has "plate_qa" iff a slide has "blender"
@needs_blender_and_remotion
def test_overlap_caught_then_cleared(tmp_path): # PlateProbe label placed on the cube box → exit 1; moved clear → exit 0
```

- [ ] **Step 2: Run them and see them fail.** Run: `python3 -m pytest -q tests/test_plate_qa.py`. Expected: FAIL.
- [ ] **Step 3: Implement** to the interfaces. `plateClear.tsx` mirrors `mediaRes.tsx` (delayRender, a census per frame, console tag).
- [ ] **Step 4: Run the tests and see them pass.** Run: `python3 -m pytest -q tests/test_plate_qa.py tests/test_critic_ledger.py tests/test_media_res_qa.py`. Expected: PASS.
- [ ] **Step 5: Commit**: "plate_qa: type that sits on a Blender plate's object is an ERROR (Film census)"

### Task 7: Docs

**Files:**
- Create: `references/blender-plates.md`. Sections:
  - when to route (the spec's §3 table and its rules);
  - the `slide.blender` fields;
  - the scene-script API;
  - commands;
  - costs (spec §8);
  - the composing-in-camera-space and reflection-dome lessons.
- Modify:
  - `SKILL.md`: one bullet under "Render: remotion cinematic tier" naming `blender_plate.py`, `plate_qa.py` and the reference, plus the budget question to the user;
  - `references/pipeline-scripts.md`: an entry for each of the two scripts.
- Test: `tests/test_blender_docs.py`

- [ ] **Step 1: Write the failing test.**
  - SKILL.md names `scripts/blender_plate.py`, `scripts/plate_qa.py` and `references/blender-plates.md`.
  - The reference lists every word of `BLENDER_WHY`.
  - pipeline-scripts.md has both entries.
- [ ] **Step 2: Run it and see it fail.** Run: `python3 -m pytest -q tests/test_blender_docs.py`. Expected: FAIL.
- [ ] **Step 3: Write the docs.** Keep SKILL.md's addition to 2–4 lines (the size tests count it).
- [ ] **Step 4: Run the tests and see them pass.** Run: `python3 -m pytest -q tests/test_blender_docs.py tests/test_build_flow_docs.py tests/test_packaging.py`. Expected: PASS.
- [ ] **Step 5: Commit**: "docs: Blender plates — routing, contract, scene API, costs"

### Task 8: Acceptance on the GPS film (beats 3 and 12)

This film work stays outside the repo (`~/code_project/film_work/blender_spike/accept`). The plate builds, the Remotion render and the gates are all real.

- [ ] **Step 1: Build the acceptance film.**
  - Use a `tools/mini.py` variant that keeps GPS beats 3 and 12 and copies the workshop.
  - Port the spike scene to `blender/sat_broadcast.py` on the kit API, with the Earth asset and its sidecar declared in `blender.assets`.
  - Write `blender/orbit_gain.py`: the same Earth plus the satellite on an emissive orbit ring. Remotion keeps the clocks and figures.
  - Shots `BroadcastPlate` and `OrbitPlate` use `BlenderPlate` / `usePlate`. Stars and ground come from the film (orbitKit `starField` + bgGrad), so mode is `rgba`.
- [ ] **Step 2: Build the plates and render.**
  - Run `python3 scripts/blender_plate.py <film>`, then `render_remotion.py`.
  - Expected: exit 0. Two plates built, with their estimate and actual seconds printed. validate shows no blender errors.
- [ ] **Step 3: Run plate_qa.**
  - Run `python3 scripts/plate_qa.py <film>`.
  - Expected: it names the label overlap if the wing still covers 我在哪. Fix the composition, then re-run until exit 0.
  - If it reports nothing on the frame where the spike showed the overlap, the gate is blind: stop and debug.
- [ ] **Step 4: Check that a timing edit rebuilds only one plate.**
  - Change beat 12's narration cue (one word) and re-voice beat 12 only (`tts.py --only 2`).
  - Expected: `blender_plate.py` rebuilds `orbit-gain` only and reports `sat-broadcast` as fresh. `remotion_segments.py` lists beat 2 only.
- [ ] **Step 5: Look at the result and deliver it.**
  - Look at the settled frames of both beats against the originals.
  - Deliver `~/Desktop/Blender实验/P1/` with both films and the side-by-side comparisons.
  - Write the measured seconds into `references/blender-plates.md` "costs".
  - Commit the doc update.
- [ ] **Step 6: Run the full suite.**
  - Run `python3 ~/code_project/film_work/tools/suite_by_file.py <worktree> <log>`.
  - Expected: no failures. Report any failure by name. No push: report the unpushed commits.
