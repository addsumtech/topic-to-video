# Adaptive Build Implementation Plan (sub-project 1: the shared flow + the remotion tier)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A film builds the objects and templates it needs — in its own workshop, checked like library code, placed into library templates through object slots or run as film-local registers — and the good ones are promoted into the library by the user's choice, without changing anything a film without a workshop renders.

**Architecture:** A film's workshop (`<out_dir>/workshop/`) enters the remotion bundle through ONE webpack alias (`@workshop`, set by env `SLIDES_WORKSHOP`, which only `scripts/workshop.py` sets); unset, the alias is a tracked empty stub and the library bundles as before. `registry.ts` merges the workshop's shots (and their declared grounds) into the library's; `Root.tsx` registers one composition per workshop shot and provides every object by id through a React context that `runtime/objectSlot.tsx` reads. Python owns the workshop (`scripts/workshop.py`: layout, generated index, environment, checks, scaffolds, stills) and every film-scoped caller routes through it; library sweeps never do. Four new stage registers and slots on two existing registers and both device registers hold objects; `scripts/promote.py` moves a delivered film's item into the library and measures it.

**Tech Stack:** Remotion 4.0.486 CLI (`still`, `bundle`, `render`, `compositions`) with `Config.overrideWebpackConfig`, React, TypeScript 5.6 (`tsc` for the per-film type-check, `paths` for the aliases), esbuild (reads the same `paths`), the TypeScript compiler API in node for the baked-words scan, Python 3 + pytest, PIL, ffmpeg.

**Spec:** `docs/superpowers/specs/2026-09-27-adaptive-build-design.md`

## Global Constraints

- Remotion stays at 4.0.486; no new npm dependency; no new hard Python dependency.
- **No regression** (the user: 「不会降低当前的能力，更多是在当前基础进一步提升」): a film with no workshop renders frame-identically to before; a slotted register renders pixel-identically with its slot empty; every existing gate keeps its behaviour on a board without a workshop; the full suite stays green.
- `SLIDES_WORKSHOP` is set only by `scripts/workshop.py` (`prepare`). Library-mode sweeps (`register_energy.py`, `prop_reach.py`, `measure_ground_luma.py`, `measure_ground_reach.py`, `band_debt.py`, `ink_contrast_qa.py`, `dna_smoke.py`, `null_dna_pixel_gate.py`) are not changed and never see a workshop. The one change in what the library sweeps feed a register is Task 7's ruling: `cjk_type_qa.cjk_props` skips an `ObjectRef` prop, which no register had before this plan.
- `scripts/workshop.py` never writes outside `<out_dir>/workshop/`.
- Names: PascalCase, 3-32 letters and digits; unique across library registers, library objects, a film's workshop shots and its workshop objects. A workshop name equal to a library name is refused.
- Every register, object and runtime function is a pure function of the frame: no `Math.random`, no `Date`, no wall clock.
- Every colour comes from Design DNA tokens with `*_D0` fallbacks; the null-DNA standalone render works.
- Content contract: every word on screen comes from a prop. Library code declares exceptions the existing way (`// @decor|@positional|@fallback|@truncates|@cycles: <reason>`); workshop code declares a word that genuinely belongs to its form with `// @fixed-text: <reason>` on the line or the line above.
- Everything a built thing draws stays inside the content zone: above `contentBottom(W, H)`, below `CONTENT_TOP` except a kicker/title in the title band.
- `runtime/motion.ts`, `runtime/dna.tsx`, `runtime/layout.ts`, `runtime/light.tsx` and the CODE of `runtime/shotLuma.ts` are not edited — nearly every register imports them, and an edit stales every row of the measurement manifests (a ~50-minute sweep). `register_shot.py` and the measurement scripts rewrite shotLuma's per-register ROWS, which the source hashes are built to tolerate.
- `runtime/objectSlot.tsx` is written once, complete, in Task 1 and not edited after Task 6 starts: it is in the source hash of every register that holds an object.
- Every git commit stages NAMED paths only (never `git add -A` / `git add .`), never overrides git config with `-c`, and ends its message with `Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx`. Nothing is pushed.
- Never edit a register, a runtime file, or any file a test reads while `register_energy.py` / `prop_reach.py` / a measurement sweep / the full suite is running.
- Run the full suite (`python3 -m pytest tests -q -p no:cacheprovider`) on the exact tree before calling the branch done.

## Where it runs

In a git worktree of `~/.claude/skills/slides-to-video` (`.worktrees/adaptive-build`, branch `adaptive-build`): the
installed skill runs from the main checkout, which stays untouched until the branch is reviewed and merged. The
worktree needs `remotion/node_modules` (git-ignored): symlink it from the main checkout
(`ln -s ~/.claude/skills/slides-to-video/remotion/node_modules remotion/node_modules`). `.superpowers/` is excluded by
`.git/info/exclude`, so the regression renders and the acceptance films live there uncommitted.

## Rulings (where the spec is silent — decided here, with the reason)

- **Which registers get a slot** (spec §3 "a curated set chosen by a survey"). A read-only survey of all 187 registers (2026-09-27) ranked six candidates; two are taken. `TechnicalPlate` (its header already says "any film can draw its own object without a new register"; the slot is named **`art`** because `object` is already its caption prop, and renaming that would break every existing board) and `HudReticle` (`object`: a subject in the lock-on reticle). Rejected with reasons: `WorksThrough` (its section is seamed into bays whose borders would slice an inserted picture), `MoleculeBallStick` and `WireGlobe` (an object would discard the register's own meaning — a molecule, a globe), `AtomOrbital` (its nucleus is 46 px and its orbits cross the centre). The device screens get slots as the spec requires.
- **`ObjectProps` gains optional `yaw`** (radians), set only by `ObjectTurntable`. An object that draws its own 3D turn declares `META.turns = true`; any other object is turned as a card with CSS, at most ±60°, and a larger `sweep` on such an object is refused.
- **`ObjectMeta`** is `{aspect?, turns?, demo?, provenance?}`: `aspect` is the w/h the slot fits the object at; `demo` marks a stage's own preview object (refused in a film); `provenance` is the idiom world the object's look comes from (required for a workshop object).
- **The object's clock** is the beat's `t` unless its host passes one: `TechnicalPlate` passes its drawing phase, the stage registers pass their reveal windows. Each card says what `t` means there.
- **Workshop shots declare `GROUND` and `PROVENANCE`.** The burned caption picks its ink, and the seam guard judges a cut, from the ground a register paints; the library measures that per register, a workshop shot is never measured, so it declares it. `registry.ts` merges the declaration into `DNA_GROUND_TOKEN` at load (no edit to `shotLuma.ts`), `seam_plan.py` reads the same declaration, and `shot_proof.py` measures the rendered caption band against it — a wrong declaration is an error, not a trusted claim.
- **Stage registers name the props a film must set** in `export const REQUIRED_IN_FILM = [...]`; `validate.py` reads it. Without it, the standalone preview (a named `DEMO_*` constant) would print in a film.
- **An object that holds a beat supplies the beat's idiom world.** A beat holding an object is judged by `_idiom_world` on the object's `META.provenance`, not on the host register's, so a stage register does not force a film to declare `motion-graphics`.
- **A film that builds needs a Design DNA** (`validate.py` error): built things paint from its tokens, and a workshop shot's declared ground only resolves under one.
- **`verdict: "build"` without `ref`** is an error when the beat's shot is a workshop shot or the film declares `meta.build_list`; otherwise the existing library-build check runs unchanged (a board that was valid stays valid).
- **Promotion** requires a DELIVERED film (`out.mp4` present and `NOT_DELIVERED.md` absent — the critic passed it), the item unchanged since that render, and a clean workshop check. "The full luma run" in spec §6 means both ground-luma emits for the promoted register (`SHOT_LUMA` and `DNA_GROUND_TOKEN`), not a library-wide sweep. Measurement order: ground reach, both luma emits, then energy and prop reach, then CJK type at every aspect — every emit that rewrites the register's own row comes before the measurements that hash it.
- **The webpack cache.** Remotion keeps one webpack cache, keyed by the whole webpack config, and the workshop's path is part of that config: switching between the library and a film (or two films) rebuilds it — measured on this machine: warm bundle 2.7 s, uncached 5.1 s — and the CLI deletes the other config's cache when it switches. Films are rendered one at a time; two different films bundling at the same instant can race on that cache (Remotion retries a corrupted cache once).
- **The CJK fixture skips an `ObjectRef` prop** (`cjk_type_qa.cjk_props`): an object slot is not copy, and unset it shows
  the register's own picture — which is what the library sweeps measure. Without the rule every slotted register would
  report "props no Chinese copy could be shaped for" (exit 2). No existing register has such a prop, so no existing
  fixture changes; Task 7's before/after CJK diff is the corpus check. The stage registers also avoid the prop names
  the fixture's shared table already means something by (`left`, `right`, `items`, `layers`, …) — ObjectCompare's
  two things are `first` and `second`.
- **Acceptance films skip the direction contest.** The contest ends in the user picking a direction from sample videos; four films in a row would be four picks the user did not ask for. Each acceptance film sets `meta.audacity: "balanced"`, commits one direction conceived for its topic, and records validate's "no contest" warning in its report as deliberate.

## Review Focus

1. **A relative `out_dir`** (`render_remotion.py out`): `SLIDES_WORKSHOP` must be absolute, or the CLI (cwd=`remotion/`) bundles a different folder. → Task 2, `test_prepare_makes_the_workshop_path_absolute`.
2. **A film folder whose path has spaces** (`~/Downloads/My Film`): the alias, the env var and the generated tsconfig must all survive it. → Task 1, `test_a_workshop_in_a_folder_with_spaces_bundles`; Task 2, `test_the_typecheck_runs_in_a_folder_with_spaces`.
3. **Two films rendered back to back**: the second bundle must hold only the second film's workshop. → Task 1, `test_back_to_back_films_see_only_their_own_workshop`.
4. **A built object that throws** (a bug in film code): every gate must report the object's own message, not a stack line or a blank frame. → Task 3, `test_a_throwing_object_is_named_by_the_gates`.
5. **An object whose aspect is far from its box's** (a 4:1 banner in a square stage): it is letterboxed, never stretched or cropped. → Task 1, `test_fit_aspect_letterboxes_extreme_shapes` (pure) and Task 8, `test_a_wide_object_is_letterboxed_on_the_stage`.

## File Structure

| File | Responsibility |
|---|---|
| `remotion/remotion.config.ts` | The `@workshop` / `@runtime` / `@shots` aliases and `resolve.modules`; refuses a set-but-empty workshop path |
| `remotion/tsconfig.json` | The same three aliases as `paths`, read by `tsc` and esbuild |
| `remotion/src/workshop/none.ts` | The tracked empty workshop |
| `remotion/src/runtime/objectSlot.tsx` | `ObjectRef`, `ObjectProps`, `ObjectMeta`, `ObjectEntry`, `Rect`, `ObjectsContext`, `fitAspect`, `resolveObject`, `useObjectEntry`, `ObjectSlot` |
| `remotion/src/objects/index.ts`, `remotion/src/objects/DemoForm.tsx` | The library's objects; DemoForm is the stages' own preview |
| `remotion/src/registry.ts` | Merges the workshop's shots, grounds and objects; exports `OBJECTS`, `WORKSHOP_SHOTS` |
| `remotion/src/Root.tsx` | One composition per workshop shot; the objects provider for every composition; the `unfed` audit wiring |
| `remotion/src/runtime/textSafe.tsx` | A fifth audit mode, `unfed`: words on the frame that no prop supplied |
| `remotion/src/shots/DeviceDemo.tsx`, `DeviceHero.tsx`, `TechnicalPlate.tsx`, `HudReticle.tsx` | Object slots |
| `remotion/src/shots/ObjectStage.tsx`, `ObjectCompare.tsx`, `ObjectPath.tsx`, `ObjectTurntable.tsx` | The four stage registers |
| `scripts/workshop.py` | The workshop: layout, names, index, environment, code files, durations, grounds, provenance, object refs, uses, checks, scaffolds, stills |
| `scripts/jsx_words.cjs` | The static baked-words scan (TypeScript AST) |
| `scripts/promote.py` | Moves a delivered film's item into the library and measures it |
| `scripts/render_remotion.py`, `remotion_segments.py`, `text_safe_qa.py`, `shot_proof.py`, `cjk_type_qa.py`, `seam_plan.py` | Route film-scoped work through the workshop |
| `scripts/validate.py` | Workshop shots are valid ids; the build list both ways; object refs; required props; the workshop check; idiom worlds of held objects |
| `scripts/device_script.py` | Object screens |
| `scripts/content_contract_qa.py`, `scripts/critic_brief.py` | Library objects are scanned; the brief lists the built things |
| `references/building-blocks.md`, `references/object-authoring.md` | What to build with, and how to build an object that means something |
| `agents/shot-director.md`, `agents/shot-critic.md`, `SKILL.md`, `remotion/LIBRARY.md`, `remotion/cards/*.md` | The flow, S15, the catalogue |
| `tests/test_workshop_bundle.py`, `test_workshop.py`, `test_workshop_routing.py`, `test_build_list.py`, `test_unfed_text.py`, `test_device_object_screen.py`, `test_slot_identity.py`, `test_object_stage.py`, `test_object_compare.py`, `test_object_path.py`, `test_object_turntable.py`, `test_promote.py`, `test_building_blocks_doc.py` | One file per task |

## Shared test helpers

`tests/test_workshop_bundle.py` (Task 1) defines the helpers every later render test uses: `_env(ws=None)` (an
environment with exactly this workshop, or none — a stale `SLIDES_WORKSHOP` never leaks in), `_still(comp, png,
props, env, frame=15)` (one frame through the real CLI, props by file), `_index(shots, objects)` (the generated index
format) and the fixture sources `SHOT` / `OBJECT`. Later test files import them (`sys.path.insert(0, <tests dir>)`,
then `from test_workshop_bundle import …`); `tests/test_object_stage.py` (Task 8) adds `SQUARE` and `_mask`, which
Tasks 9–11 import the same way. Every render test is marked `needs_toolchain` (skipped without
`remotion/node_modules`).

---
### Task 1: The workshop reaches the bundle

**Files:**
- Modify: `remotion/remotion.config.ts`, `remotion/tsconfig.json`, `remotion/src/registry.ts`, `remotion/src/Root.tsx`
- Create: `remotion/src/workshop/none.ts`, `remotion/src/runtime/objectSlot.tsx`, `remotion/src/objects/index.ts`
- Test: `tests/test_workshop_bundle.py`

**Interfaces:**
- Consumes: `useT` (runtime/motion), `useDNA`, `DesignDNA` (runtime/dna), `DNA_GROUND_TOKEN`, `GroundSpec` (runtime/shotLuma).
- Produces (TS): `ObjectRef = {id: string; props?: Record<string, unknown>}`; `ObjectProps = {w: number; h: number; t: number; dna: DesignDNA | null; yaw?: number}`; `ObjectMeta = {aspect?: number; turns?: boolean; demo?: boolean; provenance?: string}`; `ObjectEntry = {C: React.FC<any>; meta?: ObjectMeta}`; `Rect = {x, y, w, h}`; `ObjectsContext`; `SLOT_KEYS`; `fitAspect(box: Rect, aspect?: number): Rect`; `resolveObject(objects, ref): ObjectEntry`; `useObjectEntry(ref): ObjectEntry`; `<ObjectSlot object box t? yaw? style?>` (draws `<div data-object-slot={id}>`). `registry.ts` exports `OBJECTS: Record<string, ObjectEntry>` and `WORKSHOP_SHOTS`. The generated workshop index exports `WORKSHOP_SHOTS: Record<string, {C, d, ground}>` and `WORKSHOP_OBJECTS: Record<string, ObjectEntry>` (format fixed in `_index()` below; Task 2's generator must produce exactly it).

- [ ] **Step 1: Record the reference render nothing may change — BEFORE editing anything**

In the worktree, on the unmodified tree, write `.superpowers/regression/props.json` (the directory is git-ignored):

```json
{"dna": "product", "aspect": "16:9", "captions": true, "scenes": [
  {"shot": "TechnicalPlate", "durF": 90, "caption": "一张技术图版。"},
  {"shot": "HudReticle", "durF": 90, "caption": "锁定目标。"},
  {"shot": "DeviceDemo", "durF": 90, "caption": "在设备上操作。"},
  {"shot": "DeviceHero", "durF": 90, "caption": "这就是产品。"},
  {"shot": "CinematicTitle", "durF": 90, "caption": "标题。"},
  {"shot": "TermTable", "durF": 90, "caption": "一张表。"},
  {"shot": "SameStuffChanged", "durF": 90, "caption": "同样的东西变了形。"},
  {"shot": "MaterialHero", "durF": 90, "caption": "一个物件。"}
]}
```

Run:
```bash
git rev-parse HEAD > .superpowers/regression/BASE
cd remotion && npx remotion render src/index.ts Film ../.superpowers/regression/before.mp4 --props=../.superpowers/regression/props.json --gl=angle --log=error && cd ..
ffmpeg -v error -i .superpowers/regression/before.mp4 -map 0:v:0 -f framemd5 .superpowers/regression/before.framemd5
wc -l .superpowers/regression/before.framemd5
```
Expected: the render succeeds; the framemd5 file lists one line per frame (636 frames: 8 × 90 − 7 × 12, plus its header lines). Task 16 renders the same props on the finished branch and requires every line to match.

- [ ] **Step 2: Write the failing tests** — `tests/test_workshop_bundle.py`:

```python
"""A FILM'S WORKSHOP REACHES THE BUNDLE THROUGH ONE ALIAS, AND NOTHING ELSE ABOUT THE LIBRARY CHANGES.

Proven through the real CLI — `still`, `bundle`, `render` from a bundle, `compositions` — because each of them
builds its own webpack config, and the per-beat path (bundle once, render every beat from that bundle) is the
one the design spike did not cover. The workshops here are written by hand in the exact form
scripts/workshop.py generates; tests/test_workshop.py holds the generator to `_index()` below."""
import json
import os
import subprocess
import sys

import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

SHOT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ObjectSlot, type ObjectRef} from '@runtime/objectSlot';
export const DURATION = 30;
export const GROUND = 'bg';
export const PROVENANCE = 'motion-graphics';
export const %(name)s: React.FC<{fill?: string; object?: ObjectRef}> = ({fill = '#00ff00', object}) => (
  <AbsoluteFill style={{background: fill}}>
    {object ? <ObjectSlot object={object} box={{x: 660, y: 240, w: 600, h: 600}} /> : null}
  </AbsoluteFill>
);
"""

OBJECT = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'motion-graphics'};
export const %(name)s: React.FC<ObjectProps & {color?: string}> = ({w, h, color = '#ff0000'}) => (
  <div style={{width: w, height: h, background: color}} />
);
"""


def _index(shots, objects):
    """The index scripts/workshop.py generates for these names — the one format both sides agree on."""
    L = ["// GENERATED by scripts/workshop.py from shots/ and objects/ — do not edit; rewritten before every render.",
         "import type React from 'react';",
         "import type {ObjectEntry} from '@runtime/objectSlot';",
         "import type {GroundSpec} from '@runtime/shotLuma';"]
    L += ["import * as S_%s from './shots/%s';" % (n, n) for n in shots]
    L += ["import * as O_%s from './objects/%s';" % (n, n) for n in objects]
    L += ["", "export const WORKSHOP_SHOTS: Record<string, {C: React.FC<any>; d: number; ground: GroundSpec}> = {"]
    L += ["  %s: {C: S_%s.%s, d: S_%s.DURATION, ground: S_%s.GROUND as GroundSpec}," % (n, n, n, n, n) for n in shots]
    L += ["};", "export const WORKSHOP_OBJECTS: Record<string, ObjectEntry> = {"]
    L += ["  %s: {C: O_%s.%s, meta: O_%s.META}," % (n, n, n, n) for n in objects]
    L += ["};", ""]
    return "\n".join(L)


def _workshop(root, shots=(), objects=(), shot_src=SHOT, obj_src=OBJECT):
    ws = os.path.join(str(root), "workshop")
    for kind, names, src in (("shots", shots, shot_src), ("objects", objects, obj_src)):
        os.makedirs(os.path.join(ws, kind), exist_ok=True)
        for n in names:
            with open(os.path.join(ws, kind, n + ".tsx"), "w", encoding="utf-8") as fh:
                fh.write(src % {"name": n})
    with open(os.path.join(ws, "index.ts"), "w", encoding="utf-8") as fh:
        fh.write(_index(sorted(shots), sorted(objects)))
    return ws


def _env(ws=None):
    """The environment for a render: this workshop, or none at all (a stale export must not leak in)."""
    env = {k: v for k, v in os.environ.items() if k != "SLIDES_WORKSHOP"}
    if ws:
        env["SLIDES_WORKSHOP"] = str(ws)
    return env


def _still(comp, png, props, env, frame=15):
    pf = str(png) + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(props, fh, ensure_ascii=False)
    return subprocess.run(["npx", "remotion", "still", "src/index.ts", comp, str(png), "--frame=%d" % frame,
                           "--gl=angle", "--log=error", "--props=" + pf],
                          cwd=_REM, env=env, capture_output=True, text=True, timeout=900)


def _px(png, x, y):
    return Image.open(str(png)).convert("RGB").getpixel((x, y))


def _near(a, b, tol=24):
    return all(abs(p - q) <= tol for p, q in zip(a, b))


def _compositions(target, env):
    """Composition ids, from `npx remotion compositions` (an entry point or a bundle directory)."""
    r = subprocess.run(["npx", "remotion", "compositions", str(target)], cwd=_REM, env=env,
                       capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    ids = set()
    for ln in r.stdout.splitlines():
        parts = ln.split()
        if len(parts) >= 4 and parts[1].isdigit() and "x" in parts[2]:
            ids.add(parts[0])
    assert ids, "no composition table in the output:\n" + r.stdout[-800:]
    return ids


@needs_toolchain
def test_without_a_workshop_the_library_is_unchanged():
    """No film in scope: `@workshop` is the empty stub — every library register is a composition and nothing is
    added. (The pixel half of this claim is the frame-identical regression render, Task 16.)"""
    ids = _compositions("src/index.ts", _env())
    shots = {f[:-4] for f in os.listdir(os.path.join(_REM, "src", "shots")) if f.endswith(".tsx")}
    assert shots <= ids and "Film" in ids
    assert not [i for i in ids if i.startswith("Ws")], sorted(ids)


@needs_toolchain
def test_a_workshop_shot_is_a_composition_that_draws(tmp_path):
    ws = _workshop(tmp_path, shots=["WsShotA"])
    r = _still("WsShotA", tmp_path / "a.png", {"fill": "#00ff00"}, _env(ws))
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    assert _near(_px(tmp_path / "a.png", 100, 100), (0, 255, 0))


@needs_toolchain
def test_an_object_resolves_by_id_inside_a_workshop_shot(tmp_path):
    ws = _workshop(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    r = _still("WsShotA", tmp_path / "o.png",
               {"fill": "#000000", "object": {"id": "WsDisc", "props": {"color": "#ff0000"}}}, _env(ws))
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    assert _near(_px(tmp_path / "o.png", 960, 540), (255, 0, 0))
    assert _near(_px(tmp_path / "o.png", 100, 100), (0, 0, 0))


@needs_toolchain
def test_an_unknown_object_is_refused_with_the_names_that_exist(tmp_path):
    ws = _workshop(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    r = _still("WsShotA", tmp_path / "u.png", {"object": {"id": "Nope"}}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and 'no object "Nope"' in out and "WsDisc" in out, out[-800:]


@needs_toolchain
def test_object_props_may_not_set_what_the_slot_gives(tmp_path):
    ws = _workshop(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    r = _still("WsShotA", tmp_path / "s.png", {"object": {"id": "WsDisc", "props": {"w": 5}}}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "sets w" in out, out[-800:]


@needs_toolchain
def test_a_workshop_name_that_is_a_library_register_is_refused(tmp_path):
    ws = _workshop(tmp_path, shots=["TermTable"])
    r = _still("TermTable", tmp_path / "t.png", {}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "has the name of a library register" in out, out[-800:]


@needs_toolchain
def test_a_workshop_path_that_holds_no_index_is_refused(tmp_path):
    empty = tmp_path / "nothing"
    empty.mkdir()
    r = _still("TermTable", tmp_path / "n.png", {}, _env(empty))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "has no index.ts" in out, out[-800:]


@needs_toolchain
def test_the_per_beat_path_renders_a_workshop_shot_and_its_object_inside_the_film(tmp_path):
    """Bundle once with the workshop, then render the Film FROM that bundle with --frames — exactly what
    scripts/remotion_segments.py does for every beat."""
    ws = _workshop(tmp_path / "film", shots=["WsShotA"], objects=["WsDisc"])
    pub = tmp_path / "public"
    pub.mkdir()
    b = subprocess.run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + str(tmp_path / "bundle"),
                        "--public-dir=" + str(pub), "--log=error"],
                       cwd=_REM, env=_env(ws), capture_output=True, text=True, timeout=900)
    assert b.returncode == 0, (b.stdout + b.stderr)[-800:]
    props = {"scenes": [{"shot": "WsShotA", "durF": 30,
                         "props": {"fill": "#0000ff", "object": {"id": "WsDisc", "props": {"color": "#ff0000"}}}},
                        {"shot": "TermTable", "durF": 30}]}
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(props), encoding="utf-8")
    mp4 = tmp_path / "f.mp4"
    r = subprocess.run(["npx", "remotion", "render", str(tmp_path / "bundle"), "Film", str(mp4), "--codec=h264",
                        "--frames=0-20", "--props=" + str(pf), "--gl=angle", "--log=error"],
                       cwd=_REM, env=_env(), capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    png = tmp_path / "f15.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf", "select=eq(n\\,15)", "-frames:v", "1",
                    str(png)], check=True)
    ground, mid = _px(png, 400, 540), _px(png, 960, 540)
    assert ground[2] > 150 and ground[0] < 90, ground     # the workshop shot's own ground, inside the Film
    assert mid[0] > 150 and mid[2] < 90, mid              # its object, found by id inside the Film


@needs_toolchain
def test_back_to_back_films_see_only_their_own_workshop(tmp_path):
    """Review focus: the webpack cache is keyed by the whole config, and the second bundle must hold only the
    second film's workshop — never a leftover of the first."""
    a = _workshop(tmp_path / "filmA", shots=["WsShotA"])
    b = _workshop(tmp_path / "filmB", shots=["WsShotB"])
    for ws, name in ((a, "a"), (b, "b")):
        r = subprocess.run(["npx", "remotion", "bundle", "src/index.ts",
                            "--out-dir=" + str(tmp_path / ("bundle_" + name)), "--log=error"],
                           cwd=_REM, env=_env(ws), capture_output=True, text=True, timeout=900)
        assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    ids_b = _compositions(tmp_path / "bundle_b", _env())
    assert "WsShotB" in ids_b and "WsShotA" not in ids_b, sorted(i for i in ids_b if i.startswith("Ws"))
    ids_a = _compositions(tmp_path / "bundle_a", _env())
    assert "WsShotA" in ids_a and "WsShotB" not in ids_a, sorted(i for i in ids_a if i.startswith("Ws"))


@needs_toolchain
def test_a_workshop_in_a_folder_with_spaces_bundles(tmp_path):
    ws = _workshop(tmp_path / "a film with spaces", shots=["WsShotA"])
    r = _still("WsShotA", tmp_path / "sp.png", {"fill": "#00ff00"}, _env(ws))
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    assert _near(_px(tmp_path / "sp.png", 100, 100), (0, 255, 0))


def test_fit_aspect_letterboxes_extreme_shapes():
    """Review focus: a 4:1 banner in a square box is letterboxed, never stretched; no aspect is the box itself."""
    import _tsprobe as tp
    if not tp.available():
        pytest.skip("needs the remotion toolchain")
    out = tp.run_ts("import {fitAspect} from %s;" % tp.mod("objectSlot.tsx"),
                    "out.wide = fitAspect({x: 0, y: 0, w: 600, h: 600}, 4);"
                    "out.tall = fitAspect({x: 100, y: 50, w: 600, h: 600}, 0.25);"
                    "out.none = fitAspect({x: 1, y: 2, w: 30, h: 40});"
                    "out.bad = fitAspect({x: 1, y: 2, w: 30, h: 40}, -1);")
    assert out["wide"] == {"x": 0, "y": 225, "w": 600, "h": 150}
    assert out["tall"] == {"x": 325, "y": 50, "w": 150, "h": 600}
    assert out["none"] == {"x": 1, "y": 2, "w": 30, "h": 40} and out["bad"] == out["none"]
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_workshop_bundle.py -q`
Expected: FAIL — `objectSlot.tsx` does not exist; a workshop composition is not registered.

- [ ] **Step 4: Write the object contract** — `remotion/src/runtime/objectSlot.tsx`:

```tsx
// OBJECTS IN TEMPLATES — the contract between a register that has room for a thing and the film that draws the
// thing (scripts/workshop.py; docs/superpowers/specs/2026-09-27-adaptive-build-design.md §3).
//
// A register that can hold an object declares a prop typed `ObjectRef` and draws `<ObjectSlot object=… box=…>`
// where the object goes. The object is a component the FILM wrote in its workshop, or one promoted into
// remotion/src/objects/. It receives its box's size, a clock and the film's Design DNA — nothing else — so the
// same object can sit on a device's screen, on a stage, or in a plate's drawing field.
//
// WHY BY ID, THROUGH A CONTEXT. A register cannot import a film's object: the register is library code and the
// object lives in one film's folder. So objects are looked up by name in a map the Root provides (the library's
// objects and the film's workshop), and the lookup REFUSES what it cannot find — naming what does exist —
// instead of drawing nothing. A blank slot on a delivered frame is the failure this is written against.
//
// THIS FILE IS IN THE SOURCE HASH OF EVERY REGISTER THAT HOLDS AN OBJECT (scripts/register_energy._deps), so an
// edit here stales their measured rows. Change it only together with a re-measure of those registers.
import React from 'react';
import {useT} from './motion';
import {useDNA, type DesignDNA} from './dna';

export type ObjectRef = {id: string; props?: Record<string, unknown>};

/** What every object is given. `t` runs 0 → 1 over the part of the beat its host gives it, then holds at 1;
 *  `yaw` (radians) is set only by a stage that turns its object (ObjectTurntable). */
export type ObjectProps = {w: number; h: number; t: number; dna: DesignDNA | null; yaw?: number};

/** `aspect` — the width / height the object is drawn at; the slot fits that shape inside its box.
 *  `turns` — the object draws its own 3D turn from `yaw`; otherwise a turning stage turns its card.
 *  `demo` — a stage's own standalone preview, never a film's object (validate.py refuses it in a film).
 *  `provenance` — the idiom world the object's look comes from (shot_director.IDIOM_WORLDS). */
export type ObjectMeta = {aspect?: number; turns?: boolean; demo?: boolean; provenance?: string};
export type ObjectEntry = {C: React.FC<any>; meta?: ObjectMeta};
export type Rect = {x: number; y: number; w: number; h: number};

export const ObjectsContext = React.createContext<Record<string, ObjectEntry>>({});

/** What the slot gives every object. A film that sets one of them in `object.props` is refused rather than
 *  silently overruled — an ignored prop is a prop its author believes was drawn. */
export const SLOT_KEYS = ['w', 'h', 't', 'dna', 'yaw'] as const;

/** The largest rect of `aspect` (width / height) centred in `box`. No aspect, or a nonsense one: the box. */
export const fitAspect = (box: Rect, aspect?: number): Rect => {
  if (!(typeof aspect === 'number' && Number.isFinite(aspect) && aspect > 0)) return box;
  const w = Math.min(box.w, box.h * aspect);
  const h = w / aspect;
  return {x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, h};
};

/** The object's entry — or a refusal that says what was sent and which objects exist. */
export const resolveObject = (objects: Record<string, ObjectEntry>, ref: unknown): ObjectEntry => {
  const r = ref as ObjectRef | null;
  if (!r || typeof r !== 'object' || typeof r.id !== 'string' || !r.id.trim()) {
    throw new Error(`ObjectSlot: an object is {"id": "<Name>", "props": {...}} — got ${JSON.stringify(ref)}`);
  }
  const e = objects[r.id];
  if (!e) {
    const known = Object.keys(objects).sort();
    throw new Error(`ObjectSlot: no object "${r.id}" — defined here: ${known.length ? known.join(', ') : '(none)'}. ` +
      `A film builds its own in <out_dir>/workshop/objects/${r.id}.tsx ` +
      `(python3 scripts/workshop.py <out_dir> new-object ${r.id} --means "...").`);
  }
  if (r.props != null && (typeof r.props !== 'object' || Array.isArray(r.props))) {
    throw new Error(`ObjectSlot: "${r.id}".props must be an object — got ${JSON.stringify(r.props)}`);
  }
  const clash = SLOT_KEYS.filter((k) => r.props != null && k in r.props);
  if (clash.length) {
    throw new Error(`ObjectSlot: "${r.id}".props sets ${clash.join(', ')}, which the slot gives every object ` +
      "(its box, its clock, the film's DNA) — remove them.");
  }
  return e;
};

/** A host that needs the object's META before it lays out (its aspect, whether it turns) asks here. */
export const useObjectEntry = (ref: unknown): ObjectEntry => resolveObject(React.useContext(ObjectsContext), ref);

export const ObjectSlot: React.FC<{object: ObjectRef; box: Rect; t?: number; yaw?: number;
  style?: React.CSSProperties}> = ({object, box, t, yaw, style}) => {
  const objects = React.useContext(ObjectsContext);
  const beatT = useT();
  const dna = useDNA();
  const {C, meta} = resolveObject(objects, object);
  const r = fitAspect(box, meta?.aspect);
  return (
    <div data-object-slot={object.id}
      style={{position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, ...style}}>
      <C {...(object.props ?? {})} w={r.w} h={r.h} t={t ?? beatT} dna={dna} yaw={yaw} />
    </div>
  );
};
```

- [ ] **Step 5: Write the stub and the library's (empty) object index**

`remotion/src/workshop/none.ts`:
```ts
// THE EMPTY WORKSHOP. `@workshop` resolves here whenever no film is in scope — every library render, sweep and
// test. A film's workshop (scripts/workshop.py) replaces it by PATH, through remotion.config.ts; this file is
// never edited to add one.
import type React from 'react';
import type {ObjectEntry} from '../runtime/objectSlot';
import type {GroundSpec} from '../runtime/shotLuma';

export const WORKSHOP_SHOTS: Record<string, {C: React.FC<any>; d: number; ground: GroundSpec}> = {};
export const WORKSHOP_OBJECTS: Record<string, ObjectEntry> = {};
```

`remotion/src/objects/index.ts`:
```ts
// THE LIBRARY'S OBJECTS — things drawn for a film and PROMOTED into the library by scripts/promote.py, which
// adds the import and the entry below. Any film can put one into any register with a slot for one (a prop typed
// ObjectRef) by its id. See references/object-authoring.md.
import type {ObjectEntry} from '../runtime/objectSlot';

export const LIBRARY_OBJECTS: Record<string, ObjectEntry> = {
};
```

- [ ] **Step 6: The aliases** — replace `remotion/remotion.config.ts` with:

```ts
import {Config} from '@remotion/cli/config';
import fs from 'fs';
import path from 'path';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);

// A FILM'S WORKSHOP — the objects and shots one film builds for itself (scripts/workshop.py) — enters the
// bundle through ONE alias, and nothing else about the library changes. `SLIDES_WORKSHOP` is set only by
// scripts/workshop.py, for a render scoped to one film; unset, `@workshop` is the tracked empty stub and the
// library bundles exactly as it did. A path that is set but holds no generated index is refused here rather
// than bundled as an empty workshop: a film whose built things silently vanish is the failure this prevents.
// (Every caller runs the CLI with cwd = this directory, so process.cwd() is the project root.)
const ROOT = process.cwd();
const WORKSHOP = process.env.SLIDES_WORKSHOP;
if (WORKSHOP && !fs.existsSync(path.join(WORKSHOP, 'index.ts'))) {
  throw new Error(`SLIDES_WORKSHOP=${WORKSHOP} has no index.ts — render through scripts/workshop.py (prepare), ` +
    'which generates it');
}
Config.overrideWebpackConfig((c) => ({
  ...c,
  resolve: {
    ...c.resolve,
    alias: {
      ...((c.resolve?.alias as Record<string, string>) ?? {}),
      '@workshop$': WORKSHOP ? path.join(WORKSHOP, 'index.ts') : path.join(ROOT, 'src', 'workshop', 'none.ts'),
      '@runtime': path.join(ROOT, 'src', 'runtime'),
      '@shots': path.join(ROOT, 'src', 'shots'),
    },
    // Workshop files live OUTSIDE this project, so a bare `react` / `remotion` import from one would search the
    // film's folders for node_modules and find none. This project's own node_modules is searched first.
    modules: [path.join(ROOT, 'node_modules'), ...(c.resolve?.modules ?? ['node_modules'])],
  },
}));
```

In `remotion/tsconfig.json`, add to `compilerOptions` (tsc and esbuild both read it; without it `tsc --noEmit` — tests/test_typecheck.py — cannot resolve `@workshop`):
```json
    "paths": {
      "@workshop": ["./src/workshop/none.ts"],
      "@runtime/*": ["./src/runtime/*"],
      "@shots/*": ["./src/shots/*"]
    }
```

- [ ] **Step 7: Merge the workshop into the registry** — in `remotion/src/registry.ts`, after `import React from 'react';` add:

```ts
import {WORKSHOP_SHOTS, WORKSHOP_OBJECTS} from '@workshop';
import {LIBRARY_OBJECTS} from './objects';
import {DNA_GROUND_TOKEN, type GroundSpec} from './runtime/shotLuma';
import type {ObjectEntry} from './runtime/objectSlot';
```

and replace the last line, `export const SHOT_IDS = Object.keys(REGISTRY);`, with:

```ts
// A FILM'S OWN SHOTS AND OBJECTS — its workshop (scripts/workshop.py) — join the library here, for a render scoped
// to that film. With no film in scope `@workshop` is the empty stub (src/workshop/none.ts) and nothing below adds
// anything. A workshop name that is already a library name is REFUSED rather than shadowed: the film would draw
// one of the two, and which one would depend on the order of two object spreads.
//
// A workshop shot's GROUND is its own declaration, merged into the table the burned caption and the seam guard
// read (runtime/shotLuma DNA_GROUND_TOKEN). The library measures that table per register; a film's shot is never
// measured, so it says which token it paints from, and scripts/shot_proof.py checks the claim against the
// rendered caption band.
for (const [id, s] of Object.entries(WORKSHOP_SHOTS)) {
  if (REGISTRY[id]) {
    throw new Error(`the film's workshop shot "${id}" has the name of a library register — rename it ` +
      '(scripts/workshop.py check refuses this before a render)');
  }
  REGISTRY[id] = s.C;
  (DNA_GROUND_TOKEN as Record<string, GroundSpec>)[id] = s.ground;
}
export {WORKSHOP_SHOTS};

/** Every object a slot can resolve: the library's, then the film's workshop's. */
export const OBJECTS: Record<string, ObjectEntry> = {...LIBRARY_OBJECTS};
for (const [id, o] of Object.entries(WORKSHOP_OBJECTS)) {
  if (OBJECTS[id]) {
    throw new Error(`the film's workshop object "${id}" has the name of a library object — rename it`);
  }
  OBJECTS[id] = o;
}

export const SHOT_IDS = Object.keys(REGISTRY);
```

- [ ] **Step 8: Register the workshop's compositions and provide the objects** — in `remotion/src/Root.tsx`:

1. After `import {DesignDNAContext, coerceDna} from './runtime/dna';` add:
```tsx
import {ObjectsContext} from './runtime/objectSlot';
import {OBJECTS, WORKSHOP_SHOTS} from './registry';
```
2. In `DnaPreview`, replace `const shot = <><C {...rest} />{audit}</>;` with:
```tsx
  const shot = <ObjectsContext.Provider value={OBJECTS}><C {...rest} />{audit}</ObjectsContext.Provider>;
```
3. Directly above `export const RemotionRoot`, add:
```tsx
// The film's scenes find their OBJECTS (runtime/objectSlot) by id among the library's and the film's workshop's,
// provided once for the whole Film — as DnaPreview provides them to a beat rendered on its own.
const FilmWithObjects: React.FC<React.ComponentProps<typeof Film>> = (p) => (
  <ObjectsContext.Provider value={OBJECTS}><Film {...p} /></ObjectsContext.Provider>
);
```
4. In `RemotionRoot`, change `<Composition id="Film" component={Film}` to `<Composition id="Film" component={FilmWithObjects}`.
5. As the last child before the closing `  </>` of `RemotionRoot` (after the last `{F('…')}` row, so `register_shot.py` keeps inserting library rows above it), add:
```tsx
    {/* THE FILM'S OWN SHOTS (its workshop): one composition each, so every film-mode gate renders a beat by its
        id exactly as it renders a library register's. Nothing here without a film in scope. */}
    {Object.entries(WORKSHOP_SHOTS).map(([id, s]) => <React.Fragment key={id}>{F(id, s.C, s.d)}</React.Fragment>)}
```

- [ ] **Step 9: Run the tests**

Run: `python3 -m pytest tests/test_workshop_bundle.py tests/test_typecheck.py -q`
Expected: PASS. Then `python3 -m pytest tests/test_remotion.py tests/test_rules_are_load_bearing.py tests/test_remotion_segments.py tests/test_shot_cards.py tests/test_library_signatures.py -q` — PASS (the registry/Root parsers and the `register_shot` anchors still hold).

- [ ] **Step 10: Commit**

```bash
git add remotion/remotion.config.ts remotion/tsconfig.json remotion/src/registry.ts remotion/src/Root.tsx remotion/src/workshop/none.ts remotion/src/runtime/objectSlot.tsx remotion/src/objects/index.ts tests/test_workshop_bundle.py
git commit -m "Workshop plumbing: a film's objects and shots reach the bundle through one alias; the library bundles as before

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---
### Task 2: `workshop.py` — the one door into a film's workshop

**Files:**
- Create: `scripts/workshop.py`, `scripts/jsx_words.cjs`
- Test: `tests/test_workshop.py`

**Interfaces:**
- Consumes: Task 1's index format (`tests/test_workshop_bundle._index`), `content_contract_qa.violations(src, name)`, `onscreen_text_qa._strip_comments(src)`, `shot_director.IDIOM_WORLDS`, `render_remotion.frame_at_t`, `render_remotion.SETTLED_T`, `render_remotion.film_shot_props`, `cjk_type_qa._why_it_refused`.
- Produces (all in `scripts/workshop.py`): `ENV_VAR = "SLIDES_WORKSHOP"`; `WorkshopError(problems)` with `.problems`; `workshop_dir(out_dir) -> str` (absolute); `shot_names(out_dir) -> set`; `object_names(out_dir) -> set`; `library_shot_names() -> set`; `library_object_names() -> set`; `has_items(out_dir) -> bool`; `shot_source(out_dir, name) -> str | None`; `shot_source_path(out_dir, name) -> str | None`; `object_source(out_dir, name) -> str | None`; `object_meta(src) -> dict | None`; `demo_objects() -> set`; `durations(out_dir) -> {name: int}`; `grounds(out_dir) -> {name: str | list}`; `provenances(out_dir) -> {name: str}` (shots and objects); `slot_keys(src) -> set`; `object_refs(src, props) -> [(path, value)]`; `required_in_film(src) -> set`; `uses(slides, out_dir) -> {name: [beat numbers]}`; `names_problems(out_dir) -> [str]` (every layout/declaration problem); `index_blockers(out_dir) -> [str]` (the subset an index cannot be written around); `write_index(out_dir) -> str`; `prepare(out_dir) -> dict | None`; `run_kwargs(out_dir) -> dict`; `code_files(out_dir) -> [str]`; `source_files(out_dir) -> [str]`; `import_problems(out_dir, files) -> [str]`; `contract_problems(out_dir, files) -> [str]`; `baked_words(out_dir, files) -> {"problems": [str], "declared": [str]}`; `typecheck(out_dir) -> [str]`; `check(out_dir) -> [str]`; `scaffold(out_dir, kind, name, means) -> str`; `still(out_dir, name, props=None, host="ObjectStage", frame=None, aspect=None) -> str`; CLI `list | check | new-object | new-shot | still`.

- [ ] **Step 1: Write the failing tests** — `tests/test_workshop.py`:

```python
"""scripts/workshop.py — the one door into a film's workshop: its layout, its generated index, the environment
every film-scoped render runs with, and the checks built code must pass before it is rendered."""
import json
import os
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
from test_workshop_bundle import _index, SHOT, OBJECT  # noqa: E402  (the one index format)

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _film(tmp_path, shots=(), objects=(), shot_src=SHOT, obj_src=OBJECT, name="film"):
    out = tmp_path / name
    for kind, names, src in (("shots", shots, shot_src), ("objects", objects, obj_src)):
        d = out / "workshop" / kind
        d.mkdir(parents=True, exist_ok=True)
        for n in names:
            (d / (n + ".tsx")).write_text(src % {"name": n}, encoding="utf-8")
    out.mkdir(exist_ok=True)
    return str(out)


def test_a_film_without_a_workshop_changes_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("SLIDES_WORKSHOP", raising=False)
    out = _film(tmp_path)
    assert ws.prepare(out) is None and ws.run_kwargs(out) == {}


def test_an_inherited_workshop_never_leaks_into_another_film(tmp_path, monkeypatch):
    monkeypatch.setenv("SLIDES_WORKSHOP", "/some/other/film/workshop")
    env = ws.prepare(_film(tmp_path))
    assert env is not None and "SLIDES_WORKSHOP" not in env and env.get("PATH") == os.environ.get("PATH")


def test_prepare_makes_the_workshop_path_absolute(tmp_path, monkeypatch):
    """Review focus: the CLI runs with cwd=remotion/, where a relative path names a different folder."""
    _film(tmp_path, shots=["WsShotA"])
    monkeypatch.chdir(tmp_path)
    env = ws.prepare("film")
    assert env["SLIDES_WORKSHOP"] == os.path.join(str(tmp_path), "film", "workshop")
    assert os.path.isabs(env["SLIDES_WORKSHOP"])


def test_the_index_is_generated_from_the_folders_in_the_one_format(tmp_path):
    out = _film(tmp_path, shots=["WsShotB", "WsShotA"], objects=["WsDisc"])
    path = ws.write_index(out)
    assert open(path, encoding="utf-8").read() == _index(["WsShotA", "WsShotB"], ["WsDisc"])
    mtime = os.path.getmtime(path)
    ws.write_index(out)                                   # unchanged names: the file is not rewritten
    assert os.path.getmtime(path) == mtime


def test_a_bad_layout_is_refused_before_an_index_is_written(tmp_path):
    out = _film(tmp_path, shots=["TermTable"])
    with pytest.raises(ws.WorkshopError) as e:
        ws.write_index(out)
    assert any("already a library register" in p for p in e.value.problems)
    assert not os.path.exists(os.path.join(out, "workshop", "index.ts"))


@pytest.mark.parametrize("files,expect", [
    ({"shots/bad_name.tsx": SHOT % {"name": "bad_name"}}, "PascalCase"),
    ({"shots/WsX.tsx": SHOT % {"name": "WsX"}, "objects/WsX.tsx": OBJECT % {"name": "WsX"}}, "both a shot and an object"),
    ({"stuff/a.txt": "x"}, "objects/, shots/ and assets/ only"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("export const DURATION = 30;\n", "")}, "DURATION"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("export const GROUND = 'bg';\n", "")}, "GROUND"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("'bg'", "'paper'")}, "not a DNA ground token"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("'motion-graphics'", "''")}, "PROVENANCE"),
    ({"shots/WsX.tsx": (SHOT % {"name": "WsX"}).replace("export const WsX", "export const Other")}, "export const WsX"),
    ({"objects/WsX.tsx": (OBJECT % {"name": "WsX"}).replace("export const META: ObjectMeta = {aspect: 1, provenance: 'motion-graphics'};\n", "")}, "META"),
    ({"objects/WsX.tsx": (OBJECT % {"name": "WsX"}).replace("'motion-graphics'", "'underwater'")}, "not one of"),
    ({"objects/WsX.tsx": (OBJECT % {"name": "WsX"}).replace("aspect: 1,", "aspect: 1, demo: true,")}, "`demo`"),
    ({"objects/WsX.tsx": "// @scaffold — replace\n" + OBJECT % {"name": "WsX"}}, "still the scaffold"),
    ({"objects/notes.md": "x"}, "only .tsx items and .ts helpers"),
])
def test_names_problems_say_what_is_wrong(tmp_path, files, expect):
    out = tmp_path / "film"
    for rel, text in files.items():
        p = out / "workshop" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    probs = ws.names_problems(str(out))
    assert any(expect in p for p in probs), probs


def test_a_clean_layout_has_no_names_problems(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    (tmp_path / "film" / "workshop" / "objects" / "discGeometry.ts").write_text("export const R = 1;\n")
    (tmp_path / "film" / "workshop" / "assets").mkdir()
    assert ws.names_problems(out) == []


def test_imports_are_held_to_react_remotion_the_runtime_the_library_and_the_workshop(tmp_path):
    out = _film(tmp_path, objects=["WsDisc"])
    bad = tmp_path / "film" / "workshop" / "objects" / "WsBad.tsx"
    bad.write_text("import x from 'lodash';\nimport {a} from '@runtime/nope';\nimport {B} from '@shots/Nope';\n"
                   "import {c} from '../../../outside';\nimport {d} from './missing';\n", encoding="utf-8")
    good = tmp_path / "film" / "workshop" / "objects" / "WsGood.tsx"
    good.write_text("import React from 'react';\nimport {useCurrentFrame} from 'remotion';\n"
                    "import {seg} from '@runtime/motion';\nimport {TermTable} from '@shots/TermTable';\n"
                    "import {R} from './discGeometry';\n", encoding="utf-8")
    (tmp_path / "film" / "workshop" / "objects" / "discGeometry.ts").write_text("export const R = 1;\n")
    probs = ws.import_problems(out, [str(bad), str(good)])
    for needle in ("'lodash'", "@runtime/nope", "@shots/Nope", "outside the film's workshop", "does not exist"):
        assert any(needle in p for p in probs), (needle, probs)
    assert not [p for p in probs if "WsGood" in p], probs


def test_contract_findings_are_reported_with_the_file_and_line(tmp_path):
    out = _film(tmp_path, objects=["WsDisc"])
    f = tmp_path / "film" / "workshop" / "objects" / "WsDisc.tsx"
    f.write_text(f.read_text() + "export const firstThree = (xs: string[]) => xs.slice(0, 3);\n", encoding="utf-8")
    probs = ws.contract_problems(out, [str(f)])
    assert any("WsDisc.tsx:" in p and "[truncate]" in p for p in probs), probs


_WORDS_BAD = """import React from 'react';
export const WsWords: React.FC<{v?: number; mode?: 'fill' | 'stroke'; label?: string}> =
  ({v = 0, mode = 'fill', label = 'hand written label'}) => (
  <div className="box" style={{textAlign: 'center', fontFamily: 'Inter'}}>
    <span>Pressure</span>
    <span>{'Flow rate'}</span>
    <span>{v > 1 ? 'high' : 'low'}</span>
    <span>{`压力 ${v}`}</span>
    <Chip title="Grinder" />
    <span>&nbsp;&nbsp;</span>
  </div>
);
const Chip: React.FC<{title: string}> = ({title}) => <b>{title}</b>;
const UNIT = '毫升';
"""

_WORDS_GOOD = """import React from 'react';
export const WsQuiet: React.FC<{label?: string; unit?: string; mode?: 'fill' | 'stroke'}> =
  ({label = '', unit = '', mode = 'fill'}) => (
  <div className="box" style={{textAlign: 'center', fontFamily: 'Inter, sans-serif', position: 'absolute'}}>
    <span>{label}</span>
    {/* a comment is not drawn */}
    <span>{mode === 'fill' ? label : unit}</span>
    <span>&nbsp;&nbsp;·&nbsp;&nbsp;</span>
    {/* @fixed-text: the SI symbol for the quantity the film names */}
    <span>bar</span>
  </div>
);
"""


@needs_toolchain
def test_the_baked_words_scan_catches_each_way_words_get_written_in(tmp_path):
    bad = tmp_path / "WsWords.tsx"
    bad.write_text(_WORDS_BAD, encoding="utf-8")
    got = ws.baked_words(str(tmp_path), [str(bad)])
    text = "\n".join(got["problems"])
    for word in ("Pressure", "Flow rate", "high", "low", "压力", "Grinder", "hand written label", "毫升"):
        assert word in text, (word, text)
    assert "nbsp" not in text and "Inter" not in text and "'fill'" not in text, text


@needs_toolchain
def test_the_baked_words_scan_leaves_honest_code_alone_and_reports_what_was_declared(tmp_path):
    good = tmp_path / "WsQuiet.tsx"
    good.write_text(_WORDS_GOOD, encoding="utf-8")
    got = ws.baked_words(str(tmp_path), [str(good)])
    assert got["problems"] == [], got
    assert "bar" in got["declared"], got


@needs_toolchain
def test_the_scan_on_the_library_finds_real_words_only():
    """Calibration, re-run: every hit on the library is a word a viewer would read (a demo default, an intrinsic
    label) — never an entity-only run, a CSS keyword or an import path. The library is ALLOWED these; the point
    is that the scanner's rules only fire on words."""
    import glob
    import re
    files = sorted(glob.glob(os.path.join(_REM, "src", "shots", "*.tsx")))
    got = ws.baked_words(_ROOT, files)
    assert len(got["problems"]) > 100, len(got["problems"])
    words = [re.search(r"\): (.+) — every word", p).group(1) for p in got["problems"]]
    assert not [w for w in words if "nbsp" in w or "&lt;" in w or w.startswith(("'./", "'../", "'@"))], words
    assert all(re.search(r"[^\W\d_]", w) for w in words), [w for w in words if not re.search(r"[^\W\d_]", w)]


@needs_toolchain
def test_the_typecheck_catches_a_type_error_and_passes_clean_code(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    assert ws.typecheck(out) == []
    f = tmp_path / "film" / "workshop" / "objects" / "WsDisc.tsx"
    f.write_text(f.read_text() + "export const oops = (n: number) => n.toFixed('x');\n", encoding="utf-8")
    probs = ws.typecheck(out)
    assert probs and "type error" in probs[0] and "WsDisc.tsx" in probs[0], probs


@needs_toolchain
def test_the_typecheck_runs_in_a_folder_with_spaces(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], name="my film")
    assert ws.typecheck(out) == []


@needs_toolchain
def test_check_is_empty_for_a_clean_workshop(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    assert ws.check(out) == []


def test_code_files_hash_the_sources_and_leave_out_what_is_generated(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    ws.write_index(out)
    root = tmp_path / "film" / "workshop"
    (root / "assets").mkdir()
    (root / "assets" / "grain.png").write_bytes(b"x")
    (root / "_stills").mkdir()
    (root / "_stills" / "WsDisc.png").write_bytes(b"x")
    (root / ".tsconfig.json").write_text("{}")
    names = sorted(os.path.relpath(p, str(root)) for p in ws.code_files(out))
    assert names == ["assets/grain.png", "objects/WsDisc.tsx", "shots/WsShotA.tsx"], names


def test_durations_grounds_and_provenances_are_read_from_the_sources(tmp_path):
    shot = (SHOT % {"name": "WsShotA"}).replace("= 30;", "= 180;").replace("'bg'", "['accent', 'accent2']")
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"], shot_src=shot.replace("%", "%%"))
    assert ws.durations(out) == {"WsShotA": 180}
    assert ws.grounds(out) == {"WsShotA": ["accent", "accent2"]}
    assert ws.provenances(out) == {"WsShotA": "motion-graphics", "WsDisc": "motion-graphics"}


def test_object_refs_are_found_under_every_key_the_register_types_objectref():
    src = ("type ScreenSrc = {image?: string; object?: ObjectRef};\n"
           "export const X: React.FC<{steps?: {screen?: ScreenSrc}[]; art?: ObjectRef; object?: string}> = () => null;")
    props = {"object": "a caption, not a ref", "art": {"id": "Puck"},
             "steps": [{"screen": {"object": {"id": "Phone"}}}, {"tap": [0.5, 0.5]}]}
    assert sorted(ws.object_refs(src, props)) == [("art", {"id": "Puck"}), ("steps[0].screen.object", {"id": "Phone"})]
    assert ws.slot_keys("// object?: ObjectRef in a comment\n") == set()


def test_required_in_film_is_read_from_the_register():
    assert ws.required_in_film("export const REQUIRED_IN_FILM = ['object', 'stations'] as const;") == {"object", "stations"}
    assert ws.required_in_film("export const X = 1;") == set()


def test_uses_maps_each_item_to_the_beats_that_show_it(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    slides = [{"index": 3, "shot": "WsShotA", "shot_props": {"object": {"id": "WsDisc"}}},
              {"index": 4, "shot": "WsShotA"}, {"index": 5, "shot": "TermTable"}]
    got = ws.uses(slides, out)
    assert got["WsShotA"] == [3, 4] and got["WsDisc"] == [3] and got["TermTable"] == [5]


def test_scaffolds_are_written_once_and_are_flagged_until_replaced(tmp_path):
    out = str(tmp_path / "film")
    p = ws.scaffold(out, "object", "EspressoPuck", "water forced through a packed bed")
    assert p.endswith(os.path.join("workshop", "objects", "EspressoPuck.tsx"))
    src = open(p, encoding="utf-8").read()
    assert "@scaffold" in src and "water forced through a packed bed" in src and "export const META" in src
    with pytest.raises(ws.WorkshopError):
        ws.scaffold(out, "object", "EspressoPuck", "again")
    with pytest.raises(ws.WorkshopError):
        ws.scaffold(out, "shot", "TermTable", "a library name")
    assert any("still the scaffold" in x for x in ws.names_problems(out))
    s = ws.scaffold(out, "shot", "ExtractionCurve", "how the flow changes over the shot")
    assert "export const DURATION" in open(s, encoding="utf-8").read()


def test_a_work_in_progress_object_can_still_be_rendered(tmp_path):
    """A scaffold still in place, or a provenance not yet named, is reported — but the author can still render the
    object and look at it while drawing it. Only what the index cannot be written around blocks."""
    out = str(tmp_path / "film")
    ws.scaffold(out, "object", "HalfDrawn", "a thing being drawn")
    assert any("still the scaffold" in p for p in ws.names_problems(out))
    assert ws.index_blockers(out) == []
    assert os.path.exists(ws.write_index(out))


def test_the_workshop_never_writes_outside_its_folder(tmp_path):
    out = _film(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    (tmp_path / "film" / "storyboard.json").write_text("{}")
    before = {os.path.join(dp, f) for dp, _dn, fn in os.walk(str(tmp_path)) for f in fn}
    ws.prepare(out)
    ws.scaffold(out, "object", "WsNew", "a new thing")
    ws.names_problems(out)
    after = {os.path.join(dp, f) for dp, _dn, fn in os.walk(str(tmp_path)) for f in fn}
    new = sorted(os.path.relpath(p, out) for p in after - before)
    assert all(p.startswith("workshop" + os.sep) for p in new), new
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_workshop.py -q`
Expected: FAIL — `No module named 'workshop'`.

- [ ] **Step 3: Write the baked-words scan** — `scripts/jsx_words.cjs`:

```js
#!/usr/bin/env node
// WORDS WRITTEN INTO A FILM'S CODE — the static half of "every word on screen comes from a prop", for
// scripts/workshop.py. Usage: node jsx_words.cjs <typescript module dir> <file.tsx|.ts>...
// Prints {"hits": [{file, line, text, rule}], "declared": [text]} as JSON.
//
// The rules, calibrated on the 187 library registers (2026-09-27: 300 hits, every one a word a viewer reads —
// demo defaults and intrinsic labels — once HTML entities are decoded; `&nbsp;` alone was the one false shape):
//   jsx-text      text written between JSX tags
//   jsx-literal   a string drawn as a JSX child: {'…'}, {x ? '…' : '…'}, {x ?? '…'}, `…${x}`
//   word-attr     a literal handed to a prop that carries words (text, label, title, caption, …)
//   default-copy  a destructuring default that is a phrase, or CJK — it prints whenever the film passes nothing
//   cjk-literal   Chinese/Japanese/Korean anywhere in the code (no CSS keyword or identifier is CJK)
// A line carrying `@fixed-text: <reason>`, or with it on the line above, is exempt; its literals are reported as
// `declared` so the render-side check (scripts/shot_proof.py, textSafe `unfed`) accepts the same words.
'use strict';
const fs = require('fs');
const ts = require(process.argv[2]);

const LETTER = /\p{L}/u;
const CJK = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}]/u;
const ENTITY = /&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);/g;
const WORD_ATTRS = new Set(['text', 'label', 'title', 'caption', 'kicker', 'note', 'subtitle', 'heading',
  'tagline', 'body', 'quote', 'children']);
const hasWord = (s) => LETTER.test(String(s).replace(ENTITY, ' '));

const literalParts = (e) => {
  if (!e) return [];
  if (ts.isParenthesizedExpression(e)) return literalParts(e.expression);
  if (ts.isStringLiteral(e) || ts.isNoSubstitutionTemplateLiteral(e)) return hasWord(e.text) ? [[e, e.text]] : [];
  if (ts.isTemplateExpression(e)) {
    return [[e.head, e.head.text], ...e.templateSpans.map((s) => [s.literal, s.literal.text])]
      .filter(([, t]) => hasWord(t));
  }
  if (ts.isConditionalExpression(e)) return [...literalParts(e.whenTrue), ...literalParts(e.whenFalse)];
  if (ts.isBinaryExpression(e) && [ts.SyntaxKind.QuestionQuestionToken, ts.SyntaxKind.BarBarToken,
    ts.SyntaxKind.AmpersandAmpersandToken].includes(e.operatorToken.kind)) return literalParts(e.right);
  return [];
};

const inTypeOrImport = (n) => {
  for (let p = n.parent; p; p = p.parent) {
    if (ts.isImportDeclaration(p) || ts.isExportDeclaration(p) || ts.isTypeNode(p)) return true;
  }
  return false;
};

const hits = [];
const declared = [];
for (const file of process.argv.slice(3)) {
  const src = fs.readFileSync(file, 'utf8');
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true,
    file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const lines = src.split('\n');
  const isDeclared = (ln) => [ln, ln - 1].some((k) => /@fixed-text:\s*\S/.test(lines[k] || ''));
  const add = (node, text, rule) => {
    const ln = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line;
    const t = String(text).replace(ENTITY, ' ').replace(/\s+/g, ' ').trim();
    if (isDeclared(ln)) {
      declared.push(t);
      return;
    }
    hits.push({file, line: ln + 1, text: t.slice(0, 60), rule});
  };
  const visit = (node) => {
    if (ts.isJsxText(node)) {
      if (hasWord(node.text)) add(node, node.text, 'jsx-text');
    } else if (ts.isJsxExpression(node) && node.expression &&
               (ts.isJsxElement(node.parent) || ts.isJsxFragment(node.parent))) {
      for (const [n, t] of literalParts(node.expression)) add(n, t, 'jsx-literal');
    } else if (ts.isJsxAttribute(node) && node.initializer && WORD_ATTRS.has(node.name.getText(sf))) {
      const init = node.initializer;
      if (ts.isStringLiteral(init)) {
        if (hasWord(init.text)) add(init, init.text, 'word-attr');
      } else if (ts.isJsxExpression(init)) {
        for (const [n, t] of literalParts(init.expression)) add(n, t, 'word-attr');
      }
    } else if (ts.isBindingElement(node) && node.initializer) {
      for (const [n, t] of literalParts(node.initializer)) {
        if (CJK.test(t) || /\S\s+\S/.test(t.trim())) add(n, t, 'default-copy');
      }
    }
    if ((ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) && CJK.test(node.text) &&
        !inTypeOrImport(node)) add(node, node.text, 'cjk-literal');
    ts.forEachChild(node, visit);
  };
  visit(sf);
}
const seen = new Set();
const out = hits.filter((h) => {
  const k = h.file + ':' + h.line + ':' + h.text;
  if (seen.has(k)) return false;
  seen.add(k);
  return true;
});
process.stdout.write(JSON.stringify({hits: out, declared: [...new Set(declared)]}));
```

- [ ] **Step 4: Write the workshop** — `scripts/workshop.py`:

```python
#!/usr/bin/env python3
"""A FILM'S WORKSHOP — the objects and shots one film builds for itself — and the only door into the bundle.

    python3 scripts/workshop.py <out_dir> list                       # what it holds, which beats use it
    python3 scripts/workshop.py <out_dir> new-object <Name> --means "<what the viewer must see>"
    python3 scripts/workshop.py <out_dir> new-shot <Name> --means "<the argument no register carries>"
    python3 scripts/workshop.py <out_dir> check                      # type-check, imports, content contract, words
    python3 scripts/workshop.py <out_dir> still <Name> [--props p.json] [--host ObjectStage] [--frame N]

WHY THIS EXISTS. A film that needed a thing the library does not have had two choices: settle for the nearest
register, or write a new register INTO THE SHARED LIBRARY mid-film and pay its full registration and
measurement. register_shot.py records how that went: "the library can grow… in practice it almost never did,
and the reason was friction". The workshop is the third choice. The film builds what it needs in its own
out_dir; every film-scoped render sees it; the library never does; at delivery the USER chooses what is
promoted (scripts/promote.py). Spec: docs/superpowers/specs/2026-09-27-adaptive-build-design.md.

LAYOUT (all optional):
    <out_dir>/workshop/objects/<Name>.tsx   export const <Name>: React.FC<ObjectProps & {...}>; export const META
    <out_dir>/workshop/shots/<Name>.tsx     export const <Name>; DURATION; GROUND; PROVENANCE
    <out_dir>/workshop/objects|shots/*.ts   helper modules, imported relatively
    <out_dir>/workshop/assets/...           imported by the tsx, so the bundler carries them
    <out_dir>/workshop/index.ts             GENERATED here — never hand-edited
    <out_dir>/workshop/.tsconfig.json       GENERATED here, for the type-check
    <out_dir>/workshop/_stills/             `still` writes the settled frames it renders here

ONE WAY IN. Every film-scoped remotion call takes its environment from `prepare(out_dir)`: SLIDES_WORKSHOP set to
this film's workshop (absolute) when it has one; when it has none, the variable REMOVED if this process inherited
it, so a stale export can never put another film's things into this one. Library sweeps never call it. Nothing
here writes outside `<out_dir>/workshop/`.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from onscreen_text_qa import _strip_comments   # the ONE comment stripper  # noqa: E402

SKILL = os.path.dirname(_HERE)
REMOTION = os.path.join(SKILL, "remotion")
LIB_SHOTS = os.path.join(REMOTION, "src", "shots")
LIB_OBJECTS = os.path.join(REMOTION, "src", "objects")
RUNTIME = os.path.join(REMOTION, "src", "runtime")
ENV_VAR = "SLIDES_WORKSHOP"
KINDS = ("objects", "shots")
GENERATED = ("index.ts", ".tsconfig.json", "_stills")
NAME = re.compile(r"^[A-Z][A-Za-z0-9]{2,31}$")
GROUND_TOKENS = ("bg", "bgGrad", "accent", "accent2", "surface")
SCAFFOLD_MARK = "@scaffold"


class WorkshopError(RuntimeError):
    """What is wrong, as sentences; `.problems` holds every one found."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def workshop_dir(out_dir):
    """<out_dir>/workshop, ABSOLUTE: the CLI runs with cwd=remotion/, where a relative path names a different
    folder."""
    return os.path.join(os.path.abspath(out_dir), "workshop")


def _tsx_names(folder):
    return sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(folder, "*.tsx")))


def shot_names(out_dir):
    return set(_tsx_names(os.path.join(workshop_dir(out_dir), "shots"))) if out_dir else set()


def object_names(out_dir):
    return set(_tsx_names(os.path.join(workshop_dir(out_dir), "objects"))) if out_dir else set()


def library_shot_names():
    return set(_tsx_names(LIB_SHOTS))


def library_object_names():
    return set(_tsx_names(LIB_OBJECTS))


def has_items(out_dir):
    return bool(shot_names(out_dir) or object_names(out_dir))


def _safe(name):
    return isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_]+", name) is not None


def shot_source_path(out_dir, name):
    """Where register `name` is defined for THIS film: the library's, else the film's own; None if neither."""
    if not _safe(name):
        return None
    for p in (os.path.join(LIB_SHOTS, name + ".tsx"),
              os.path.join(workshop_dir(out_dir), "shots", name + ".tsx") if out_dir else None):
        if p and os.path.isfile(p):
            return p
    return None


def shot_source(out_dir, name):
    p = shot_source_path(out_dir, name)
    return _read(p) if p else None


def object_source(out_dir, name):
    if not _safe(name):
        return None
    for p in (os.path.join(workshop_dir(out_dir), "objects", name + ".tsx") if out_dir else None,
              os.path.join(LIB_OBJECTS, name + ".tsx")):
        if p and os.path.isfile(p):
            return _read(p)
    return None


_META = re.compile(r"export const META\b[^=]*=\s*\{(.*?)\}\s*;", re.S)


def object_meta(src):
    """An object's META as {aspect, turns, demo, provenance} (only the keys it sets), or None if it has none."""
    m = _META.search(src or "")
    if not m:
        return None
    body, meta = m.group(1), {}
    a = re.search(r"\baspect\s*:\s*([0-9.]+(?:\s*/\s*[0-9.]+)?)", body)
    if a:
        num = a.group(1).replace(" ", "")
        meta["aspect"] = (float(num.split("/")[0]) / float(num.split("/")[1])) if "/" in num else float(num)
    for flag in ("turns", "demo"):
        f = re.search(r"\b%s\s*:\s*(true|false)" % flag, body)
        if f:
            meta[flag] = f.group(1) == "true"
    p = re.search(r"\bprovenance\s*:\s*['\"]([^'\"]*)['\"]", body)
    if p:
        meta["provenance"] = p.group(1)
    return meta


def demo_objects():
    """Library objects that are a stage's own preview (META.demo) — never a film's picture."""
    return {n for n in library_object_names() if (object_meta(_read(os.path.join(LIB_OBJECTS, n + ".tsx"))) or {}).get("demo")}


def durations(out_dir):
    """{workshop shot: DURATION} — the frame count every film-mode gate needs to find a beat's settled frame."""
    out = {}
    for n in shot_names(out_dir):
        m = re.search(r"export const DURATION\s*=\s*(\d+)", _read(os.path.join(workshop_dir(out_dir), "shots", n + ".tsx")))
        if m:
            out[n] = int(m.group(1))
    return out


_GROUND = re.compile(r"export const GROUND\b[^=]*=\s*(\[[^\]]*\]|'[^']*'|\"[^\"]*\")")
_PROVENANCE = re.compile(r"export const PROVENANCE\b[^=]*=\s*['\"]([^'\"]*)['\"]")


def _ground_of(src):
    m = _GROUND.search(src or "")
    if not m:
        return None
    raw = m.group(1)
    return re.findall(r"['\"]([^'\"]+)['\"]", raw) if raw.startswith("[") else raw[1:-1]


def _ground_ok(g):
    if isinstance(g, list):
        return bool(g) and all(x in GROUND_TOKENS for x in g)
    return g in GROUND_TOKENS or re.fullmatch(r"#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}", g or "") is not None


def grounds(out_dir):
    """{workshop shot: the ground it declares} — what the caption ink and the seam guard judge it on."""
    return {n: _ground_of(_read(os.path.join(workshop_dir(out_dir), "shots", n + ".tsx"))) for n in shot_names(out_dir)}


def provenances(out_dir):
    """{workshop shot or object: the idiom world it declares}."""
    out = {}
    for n in shot_names(out_dir):
        m = _PROVENANCE.search(_read(os.path.join(workshop_dir(out_dir), "shots", n + ".tsx")))
        if m and m.group(1):
            out[n] = m.group(1)
    for n in object_names(out_dir):
        meta = object_meta(_read(os.path.join(workshop_dir(out_dir), "objects", n + ".tsx"))) or {}
        if meta.get("provenance"):
            out[n] = meta["provenance"]
    return out


def _worlds():
    import shot_director
    return list(shot_director.IDIOM_WORLDS)


_SLOT_KEY = re.compile(r"\b([A-Za-z_]\w*)\s*\??\s*:\s*ObjectRef\b")


def slot_keys(src):
    """Every prop name a register types `ObjectRef`, in any of its types — nested ones included."""
    return set(_SLOT_KEY.findall(_strip_comments(src or "")))


def object_refs(src, props):
    """[(path, value)] for every object reference in a beat's props: each value under a key the register types
    ObjectRef, at any depth (a device's `steps[0].screen.object`, a compare's `left.object`)."""
    keys, found = slot_keys(src), []

    def walk(v, path):
        if isinstance(v, dict):
            for k, x in v.items():
                p = "%s.%s" % (path, k) if path else str(k)
                if k in keys and x is not None:
                    found.append((p, x))
                else:
                    walk(x, p)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, "%s[%d]" % (path, i))

    if keys:
        walk(props or {}, "")
    return found


_REQUIRED = re.compile(r"export const REQUIRED_IN_FILM\b[^=]*=\s*\[([^\]]*)\]")


def required_in_film(src):
    """The props a register says a FILM must set (its standalone preview fills them otherwise)."""
    m = _REQUIRED.search(src or "")
    return set(re.findall(r"['\"](\w+)['\"]", m.group(1))) if m else set()


def uses(slides, out_dir):
    """{shot or object id: [beat numbers]} — a shot by the beats cast on it, an object by the beats whose props
    name it. A beat number is the board's own `index` (its position when a slide has none)."""
    out = {}
    for pos, s in enumerate(slides or [], 1):
        num = s.get("index", pos)
        shot = s.get("shot")
        if isinstance(shot, str) and shot:
            out.setdefault(shot, []).append(num)
        for _path, ref in object_refs(shot_source(out_dir, shot), s.get("shot_props") or {}):
            if isinstance(ref, dict) and isinstance(ref.get("id"), str):
                lst = out.setdefault(ref["id"], [])
                if num not in lst:
                    lst.append(num)
    return out


def _problems(out_dir):
    """[(sentence, blocking)] for the workshop's layout and declarations. BLOCKING problems stop an index from being
    written (a name that is not an identifier, a shadowed library name, a component or DURATION the index cannot
    wire); the rest — a scaffold still in place, a missing provenance or GROUND — are reported by `check` and by
    validate.py, but a work-in-progress object can still be rendered and looked at."""
    ws = workshop_dir(out_dir)
    if not os.path.isdir(ws):
        return []
    out = []
    for entry in sorted(os.listdir(ws)):
        if entry in KINDS or entry == "assets" or entry in GENERATED or entry.startswith("."):
            continue
        out.append(("workshop/%s: a workshop holds objects/, shots/ and assets/ only" % entry, False))
    for n in sorted(shot_names(out_dir) & object_names(out_dir)):
        out.append(("workshop: %s is both a shot and an object — one name, one thing" % n, True))
    lib_s, lib_o, worlds = library_shot_names(), library_object_names(), _worlds()
    for kind in KINDS:
        folder = os.path.join(ws, kind)
        if not os.path.isdir(folder):
            continue
        for f in sorted(os.listdir(folder)):
            if f.startswith("."):
                continue
            if os.path.isdir(os.path.join(folder, f)) or not f.endswith((".tsx", ".ts")):
                out.append(("workshop/%s/%s: only .tsx items and .ts helpers belong here (pictures go in assets/)"
                            % (kind, f), False))
        for n in _tsx_names(folder):
            where = "workshop/%s/%s.tsx" % (kind, n)
            if not NAME.match(n):
                out.append(("%s: a name is PascalCase, 3-32 letters and digits" % where, True))
                continue
            if n in lib_s:
                out.append(("%s: %s is already a library register — rename it (the render refuses a shadowed name)"
                            % (where, n), True))
            if n in lib_o:
                out.append(("%s: %s is already a library object — rename it" % (where, n), True))
            src = _read(os.path.join(folder, n + ".tsx"))
            if not re.search(r"export const %s\b" % re.escape(n), src):
                out.append(("%s: export the component as `export const %s`" % (where, n), True))
            if SCAFFOLD_MARK in src:
                out.append(("%s: still the scaffold — draw the real %s, then delete the `%s` line"
                            % (where, kind[:-1], SCAFFOLD_MARK), False))
            if kind == "shots":
                if not re.search(r"export const DURATION\s*=\s*\d+", src):
                    out.append(("%s: export `DURATION` (frames at 30 fps) — the gates find its settled frame from it"
                                % where, True))
                g = _ground_of(src)
                if g is None:
                    out.append(("%s: export `GROUND` — the DNA token its ground is painted from (%s) or a '#hex'; "
                                "the burned caption picks its ink from it" % (where, ", ".join(GROUND_TOKENS)), False))
                elif not _ground_ok(g):
                    out.append(("%s: GROUND %r is not a DNA ground token (%s), a list of them, or a '#hex'"
                                % (where, g, ", ".join(GROUND_TOKENS)), False))
                pm = _PROVENANCE.search(src)
                if not pm or not pm.group(1):
                    out.append(("%s: export `PROVENANCE` — the idiom world its look comes from (%s)"
                                % (where, ", ".join(worlds)), False))
                elif pm.group(1) not in worlds:
                    out.append(("%s: PROVENANCE %r is not one of %s" % (where, pm.group(1), ", ".join(worlds)), False))
            else:
                meta = object_meta(src)
                if meta is None:
                    out.append(("%s: export `META: ObjectMeta` — {aspect, provenance}" % where, False))
                    continue
                if not meta.get("provenance"):
                    out.append(("%s: META.provenance names the idiom world its look comes from (%s)"
                                % (where, ", ".join(worlds)), False))
                elif meta["provenance"] not in worlds:
                    out.append(("%s: META.provenance %r is not one of %s"
                                % (where, meta["provenance"], ", ".join(worlds)), False))
                if meta.get("demo"):
                    out.append(("%s: `demo` marks a stage's own preview object; a film's object is never one" % where,
                                False))
    return out


def names_problems(out_dir):
    """Every layout and declaration problem, as sentences."""
    return [p for p, _blocking in _problems(out_dir)]


def index_blockers(out_dir):
    """The problems an index cannot be written around."""
    return [p for p, blocking in _problems(out_dir) if blocking]


def write_index(out_dir):
    """Regenerate <workshop>/index.ts from the two folders and return its path. A BLOCKING problem raises
    WorkshopError — an index is never written around a name the render would refuse; the rest wait for `check`."""
    probs = index_blockers(out_dir)
    if probs:
        raise WorkshopError(probs)
    shots, objs = sorted(shot_names(out_dir)), sorted(object_names(out_dir))
    L = ["// GENERATED by scripts/workshop.py from shots/ and objects/ — do not edit; rewritten before every render.",
         "import type React from 'react';",
         "import type {ObjectEntry} from '@runtime/objectSlot';",
         "import type {GroundSpec} from '@runtime/shotLuma';"]
    L += ["import * as S_%s from './shots/%s';" % (n, n) for n in shots]
    L += ["import * as O_%s from './objects/%s';" % (n, n) for n in objs]
    L += ["", "export const WORKSHOP_SHOTS: Record<string, {C: React.FC<any>; d: number; ground: GroundSpec}> = {"]
    L += ["  %s: {C: S_%s.%s, d: S_%s.DURATION, ground: S_%s.GROUND as GroundSpec}," % (n, n, n, n, n) for n in shots]
    L += ["};", "export const WORKSHOP_OBJECTS: Record<string, ObjectEntry> = {"]
    L += ["  %s: {C: O_%s.%s, meta: O_%s.META}," % (n, n, n, n) for n in objs]
    L += ["};", ""]
    text = "\n".join(L)
    path = os.path.join(workshop_dir(out_dir), "index.ts")
    if not (os.path.isfile(path) and _read(path) == text):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return path


def prepare(out_dir):
    """The environment for a remotion call scoped to this film — or None when nothing needs to change.

    A film with a workshop: its index regenerated, SLIDES_WORKSHOP set to it (absolute). A film without one:
    None — unless this process inherited SLIDES_WORKSHOP, in which case a copy of the environment WITHOUT it."""
    if out_dir and has_items(out_dir):
        write_index(out_dir)
        return dict(os.environ, **{ENV_VAR: workshop_dir(out_dir)})
    if ENV_VAR in os.environ:
        return {k: v for k, v in os.environ.items() if k != ENV_VAR}
    return None


def run_kwargs(out_dir):
    """`subprocess.run(..., **run_kwargs(out_dir))` — {} leaves a call exactly as it was before workshops."""
    env = prepare(out_dir)
    return {"env": env} if env is not None else {}


def code_files(out_dir):
    """Every workshop file a render is built from (objects/, shots/, assets/) — for the segment cache key. The
    generated files are left out: the index is a function of these names, and the names are hashed."""
    if not out_dir:
        return []
    ws, out = workshop_dir(out_dir), []
    for sub in KINDS + ("assets",):
        for dp, dn, fn in os.walk(os.path.join(ws, sub)):
            dn[:] = sorted(d for d in dn if not d.startswith("."))
            out += [os.path.join(dp, f) for f in fn if not f.startswith(".")]
    return sorted(out)


def source_files(out_dir):
    """The workshop's code: every .tsx and .ts in objects/ and shots/."""
    ws = workshop_dir(out_dir)
    return sorted(p for kind in KINDS for p in glob.glob(os.path.join(ws, kind, "*.ts*"))
                  if p.endswith((".ts", ".tsx")))


_IMPORT = re.compile(r"""(?:\bfrom\s+|\bimport\s*\(\s*|^\s*import\s+)['"]([^'"]+)['"]""", re.M)


def import_problems(out_dir, files):
    """A workshop may import react, remotion (and the project's other dependencies), the runtime as
    @runtime/<module>, library registers as @shots/<Name>, and its own files. Nothing else resolves."""
    pkg = json.loads(_read(os.path.join(REMOTION, "package.json")))
    deps = set(pkg.get("dependencies") or {}) | set(pkg.get("devDependencies") or {})
    ws, lib, probs = workshop_dir(out_dir), library_shot_names(), []
    for f in files:
        rel = os.path.relpath(f, os.path.dirname(ws))
        for spec in _IMPORT.findall(_strip_comments(_read(f))):
            if spec.startswith("@runtime/"):
                mod = spec[len("@runtime/"):]
                if not any(os.path.isfile(os.path.join(RUNTIME, mod + e)) for e in ("", ".ts", ".tsx", ".json")):
                    probs.append("%s imports %s — there is no runtime module %r (references/building-blocks.md "
                                 "lists them)" % (rel, spec, mod))
            elif spec.startswith("@shots/"):
                if spec[len("@shots/"):] not in lib:
                    probs.append("%s imports %s — there is no library register %r" % (rel, spec, spec[7:]))
            elif spec.startswith("."):
                target = os.path.normpath(os.path.join(os.path.dirname(f), spec))
                if not (target + os.sep).startswith(ws + os.sep):
                    probs.append("%s imports %s, outside the film's workshop — film code may use react, remotion, "
                                 "@runtime/…, @shots/… and its own workshop files" % (rel, spec))
                elif not any(os.path.exists(target + e) for e in ("", ".ts", ".tsx", ".json", "/index.ts")):
                    probs.append("%s imports %s, which does not exist" % (rel, spec))
            else:
                name = "/".join(spec.split("/")[:2]) if spec.startswith("@") else spec.split("/")[0]
                if name not in deps:
                    probs.append("%s imports %r, which is not a dependency of remotion/package.json — a workshop "
                                 "cannot add packages" % (rel, spec))
    return probs


def contract_problems(out_dir, files):
    """The content contract (scripts/content_contract_qa.py) over the workshop's code."""
    import content_contract_qa as cq
    ws, probs = workshop_dir(out_dir), []
    for f in files:
        name = os.path.basename(f).rsplit(".", 1)[0]
        for line, rule, text in cq.violations(_read(f), name):
            probs.append("%s:%d [%s] %s — every status, emphasis or quantity it shows must come from the film "
                         "(declare `// @%s: <why>` only when it is genuinely not a claim)"
                         % (os.path.relpath(f, os.path.dirname(ws)), line, rule, text.strip()[:100], rule))
    return probs


_RULE_WORDS = {"jsx-text": "text written in the JSX", "jsx-literal": "a literal drawn as text",
               "word-attr": "a literal handed to a words prop", "default-copy": "a default that prints when "
               "the film passes nothing", "cjk-literal": "Chinese written into the code"}


def baked_words(out_dir, files):
    """{"problems": [...], "declared": [...]} — words a viewer would read that no prop supplies (jsx_words.cjs)."""
    node = shutil.which("node")
    tsmod = os.path.join(REMOTION, "node_modules", "typescript")
    code = [f for f in files if f.endswith((".tsx", ".ts"))]
    if not code:
        return {"problems": [], "declared": []}
    if not node or not os.path.isdir(tsmod):
        return {"problems": ["the baked-words scan could not run: node or remotion/node_modules/typescript is "
                             "missing — nothing was checked"], "declared": []}
    r = subprocess.run([node, os.path.join(_HERE, "jsx_words.cjs"), tsmod] + code, capture_output=True, text=True)
    if r.returncode != 0:
        return {"problems": ["the baked-words scan failed: %s" % ((r.stderr or r.stdout).strip()[-300:] or
                                                                  "(no output)")], "declared": []}
    got = json.loads(r.stdout or "{}")
    base = os.path.dirname(workshop_dir(out_dir))
    probs = ["%s:%d words written into the code (%s): %r — every word on screen comes from a prop; a word that "
             "is genuinely part of the form (a unit symbol, an axis letter) is declared with "
             "`// @fixed-text: <why>`" % (os.path.relpath(h["file"], base), h["line"],
                                          _RULE_WORDS.get(h["rule"], h["rule"]), h["text"])
             for h in got.get("hits") or []]
    return {"problems": probs, "declared": list(got.get("declared") or [])}


def typecheck(out_dir):
    """tsc over the workshop, with the project's own settings and the three aliases. [] when it is clean."""
    tsc = os.path.join(REMOTION, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        return ["the type-check could not run: %s is missing (npm install in remotion/) — nothing was checked" % tsc]
    ws = workshop_dir(out_dir)
    write_index(out_dir)
    cfg = {"extends": os.path.join(REMOTION, "tsconfig.json"),
           "compilerOptions": {
               "noEmit": True,
               "typeRoots": [os.path.join(REMOTION, "node_modules", "@types")],
               "paths": {"@workshop": [os.path.join(ws, "index.ts")],
                         "@runtime/*": [os.path.join(RUNTIME, "*")],
                         "@shots/*": [os.path.join(LIB_SHOTS, "*")],
                         "*": [os.path.join(REMOTION, "node_modules", "*"),
                               os.path.join(REMOTION, "node_modules", "@types", "*")]}},
           "include": [os.path.join(ws, "objects"), os.path.join(ws, "shots"), os.path.join(ws, "index.ts"),
                       os.path.join(REMOTION, "src", "*.d.ts")]}
    path = os.path.join(ws, ".tsconfig.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=1)
    r = subprocess.run([tsc, "-p", path], cwd=REMOTION, capture_output=True, text=True)
    errs = [ln.strip() for ln in (r.stdout + r.stderr).splitlines() if "error TS" in ln]
    if r.returncode != 0 and not errs:
        return ["the type-check failed without naming an error: %s" % ((r.stdout + r.stderr).strip()[-300:] or
                                                                        "(no output)")]
    return ["type error: %s" % e for e in errs]


def check(out_dir):
    """Every problem in this film's workshop, as sentences — [] when it is clean or there is none."""
    if not os.path.isdir(workshop_dir(out_dir)):
        return []
    probs = names_problems(out_dir)
    files = source_files(out_dir)
    probs += import_problems(out_dir, files)
    probs += contract_problems(out_dir, files)
    probs += baked_words(out_dir, files)["problems"]
    if not index_blockers(out_dir) and has_items(out_dir):
        probs += typecheck(out_dir)
    return probs


OBJECT_SCAFFOLD = """// OBJECT · %(name)s — %(means)s
// A film-local object (scripts/workshop.py). It ENCODES its beat: hide the caption and it still carries the idea.
// Every word it draws comes from a prop; it sizes to its box (w × h); it is a pure function of t (0 → 1, then
// held) — no Math.random, no Date. Read references/object-authoring.md before drawing it and
// references/building-blocks.md for what to draw it with. It goes into a register with a slot for one (a prop
// typed ObjectRef): ObjectStage, ObjectCompare, ObjectPath, ObjectTurntable, TechnicalPlate `art`, HudReticle
// `object`, or a device's screen.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01, seg, easeOutCubic} from '@runtime/motion';

// provenance: the idiom world this object's look comes from — one of shot_director.IDIOM_WORLDS.
export const META: ObjectMeta = {aspect: 1, provenance: ''};

// @scaffold — replace this body with the real drawing, then delete this line.
export const %(name)s: React.FC<ObjectProps> = ({w, h, t, dna}) => {
  const ink = dna?.fg ?? '#1c2230', acc = dna?.accent ?? '#3563e9';
  const on = easeOutCubic(clamp01(seg(t, 0, 1)));
  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      <rect x={w * 0.1} y={h * 0.1} width={w * 0.8 * on} height={h * 0.8} fill="none" stroke={acc}
        strokeWidth={Math.max(2, w * 0.006)} />
      <line x1={w * 0.1} y1={h * 0.9} x2={w * 0.9} y2={h * 0.9} stroke={ink} strokeWidth={Math.max(1, w * 0.003)} />
    </svg>
  );
};
"""

SHOT_SCAFFOLD = """// SHOT · %(name)s — %(means)s
// A film-local register (scripts/workshop.py): a template this film needs because no library register's STRUCTURE
// carries this beat. Every word on screen comes from a prop; content stays inside the content zone (above
// contentBottom); colours come from the Design DNA with fallbacks; it is a pure function of the frame. Read
// references/remotion-shot-authoring.md (the frame-craft floor) and references/building-blocks.md. It may hold
// objects (a prop typed ObjectRef drawn with <ObjectSlot object=… box=…/>) and may wrap a library register
// (import {X} from '@shots/X').
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '@runtime/motion';
import {CONTENT_TOP, contentBottom} from '@runtime/layout';
import {useDNA} from '@runtime/dna';

export const DURATION = 150;
// the DNA token this shot paints its ground from ('bg', 'bgGrad', 'surface', 'accent', 'accent2') or a '#hex' —
// the burned caption picks its ink from it, and scripts/shot_proof.py measures the claim
export const GROUND = 'bg';
// the idiom world its look comes from — one of shot_director.IDIOM_WORLDS
export const PROVENANCE = '';

// @scaffold — replace this body with the real design, then delete this line.
export const %(name)s: React.FC<{title?: string}> = ({title = ''}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const on = easeOutCubic(clamp01(seg(t, 0.05, 0.3)));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? '#0a0f16', color: dna?.fg ?? '#e8eef6'}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: (CONTENT_TOP + contentBottom(W, H)) / 2,
        textAlign: 'center', opacity: on,
        font: `700 ${Math.round(W * 0.03)}px/1.2 var(--f-display, system-ui, sans-serif)`}}>{title}</div>
    </AbsoluteFill>
  );
};
"""


def scaffold(out_dir, kind, name, means):
    """Write a new object or shot into the workshop and return its path; refuse a bad or taken name."""
    folder = {"object": "objects", "shot": "shots"}.get(kind)
    if folder is None:
        raise WorkshopError(["kind is object or shot (got %r)" % (kind,)])
    probs = []
    if not NAME.match(name or ""):
        probs.append("%r: a name is PascalCase, 3-32 letters and digits" % (name,))
    elif name in library_shot_names() or name in library_object_names():
        probs.append("%s is already in the library — pick another name, or use the library's" % name)
    elif name in shot_names(out_dir) | object_names(out_dir):
        probs.append("%s is already in this film's workshop" % name)
    if not str(means or "").strip():
        probs.append("--means: say what the viewer must see — it heads the file and the build-list entry")
    if probs:
        raise WorkshopError(probs)
    d = os.path.join(workshop_dir(out_dir), folder)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name + ".tsx")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write((OBJECT_SCAFFOLD if kind == "object" else SHOT_SCAFFOLD)
                 % {"name": name, "means": " ".join(str(means).split())})
    return path


def _board(out_dir):
    try:
        return json.loads(_read(os.path.join(out_dir, "storyboard.json")))
    except (OSError, ValueError):
        return {}


def still(out_dir, name, props=None, host="ObjectStage", frame=None, aspect=None):
    """Render `name`'s settled frame on its own into <workshop>/_stills/<name>.png and return that path — a shot
    as its own composition (props: the given ones, else its first beat's), an object on `host` (props: the
    object's own)."""
    import render_remotion as rr
    board = _board(out_dir)
    meta = board.get("meta") or {}
    if name in shot_names(out_dir):
        comp = name
        payload = dict(props) if props is not None else {}
        if props is None:
            beat = next((s for s in board.get("slides") or [] if s.get("shot") == name), None)
            payload = rr.film_shot_props(beat, out_dir) if beat else {}
        dur = durations(out_dir)[name]
    elif name in object_names(out_dir) or name in library_object_names():
        comp = host
        payload = {"object": dict({"id": name}, **({"props": props} if props else {}))}
        src = shot_source(out_dir, host)
        if src is None:
            raise WorkshopError(["%s is not a register with a slot this film can use" % host])
        dur = int(re.search(r"export const DURATION\s*=\s*(\d+)", src).group(1))
    else:
        raise WorkshopError(["%s is not in this film's workshop or the library's objects" % name])
    dna = meta.get("design_dna") or meta.get("shot_template")
    if dna:
        payload.setdefault("dna", dna)
    if aspect or meta.get("aspect"):
        payload.setdefault("aspect", aspect or meta["aspect"])
    frame = int(round(rr.frame_at_t(dur, rr.SETTLED_T))) if frame is None else int(frame)
    outd = os.path.join(workshop_dir(out_dir), "_stills")
    os.makedirs(outd, exist_ok=True)
    pf = os.path.join(outd, name + ".props.json")
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    png = os.path.join(outd, name + ".png")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", comp, png, "--frame=%d" % frame, "--gl=angle",
                        "--log=error", "--props=" + pf, "--public-dir=" + os.path.abspath(out_dir)],
                       cwd=REMOTION, capture_output=True, text=True, **run_kwargs(out_dir))
    if r.returncode != 0 or not os.path.exists(png):
        import cjk_type_qa
        raise WorkshopError(["the still of %s failed: %s" % (name, cjk_type_qa._why_it_refused(r.stdout + r.stderr))])
    return png


def _list(out_dir):
    board = _board(out_dir)
    used = uses(board.get("slides") or [], out_dir)
    listed = {e.get("id") for e in (board.get("meta") or {}).get("build_list") or [] if isinstance(e, dict)}
    print("[workshop] %s" % workshop_dir(out_dir))
    rows = [("shot", n) for n in sorted(shot_names(out_dir))] + [("object", n) for n in sorted(object_names(out_dir))]
    for kind, n in rows:
        print("  %-6s %-24s beats %-12s %s" % (kind, n, ", ".join(map(str, used.get(n) or [])) or "-",
                                               "on the build list" if n in listed else "NOT on the build list"))
    if not rows:
        print("  (empty) — python3 scripts/workshop.py %s new-object <Name> --means \"...\"" % out_dir)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="A film's workshop: the objects and shots it builds for itself.")
    ap.add_argument("out_dir")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("check")
    for k in ("new-object", "new-shot"):
        p = sub.add_parser(k)
        p.add_argument("name")
        p.add_argument("--means", required=True)
    p = sub.add_parser("still")
    p.add_argument("name")
    p.add_argument("--props", help="a JSON file: the shot's props, or the object's own props")
    p.add_argument("--host", default="ObjectStage")
    p.add_argument("--frame", type=int)
    p.add_argument("--aspect")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "list":
            return _list(a.out_dir)
        if a.cmd == "check":
            probs = check(a.out_dir)
            for x in probs:
                print("  PROBLEM: " + x)
            print("[workshop] %s — %d problem(s)" % ("CLEAN" if not probs else "NOT CLEAN", len(probs)))
            if not probs:
                print("NEXT: python3 scripts/validate.py %s" % a.out_dir)
            return 1 if probs else 0
        if a.cmd in ("new-object", "new-shot"):
            path = scaffold(a.out_dir, a.cmd[4:], a.name, a.means)
            print("[workshop] wrote %s" % path)
            print("NEXT: draw it (references/object-authoring.md), then python3 scripts/workshop.py %s still %s"
                  % (a.out_dir, a.name))
            return 0
        props = json.loads(_read(a.props)) if a.props else None
        png = still(a.out_dir, a.name, props, host=a.host, frame=a.frame, aspect=a.aspect)
        print("[workshop] %s" % png)
        print("NEXT: open it and LOOK — does it carry its build-list entry's `means` with the caption hidden?")
        return 0
    except WorkshopError as e:
        for x in e.problems:
            print("  PROBLEM: " + x)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m pytest tests/test_workshop.py tests/test_workshop_bundle.py -q`
Expected: PASS. If `test_the_scan_on_the_library_finds_real_words_only` flags a new shape, look at the hit in the register before touching a rule — the calibration's claim is that every library hit is a real word, and a rule change must be re-run over the whole library (memory: a measurement change is diffed on a corpus of ordinary inputs, not the one case in front of it).

- [ ] **Step 6: Commit**

```bash
git add scripts/workshop.py scripts/jsx_words.cjs tests/test_workshop.py
git commit -m "workshop.py: a film's own objects and shots — layout, generated index, one environment, and the checks built code must pass

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---
### Task 3: Every film-scoped render goes through the workshop

**Files:**
- Modify: `scripts/render_remotion.py` (`film_props`, `_render_remotion`), `scripts/remotion_segments.py` (`code_files`, `code_hash`, `plan`, `_bundle`, `render_segment`, `render_film`, `_render_stale`), `scripts/text_safe_qa.py` (`audit_shot`, `scan_film`), `scripts/cjk_type_qa.py` (`_default_ink`, `_fed_missing`, `audit`, `sweep`, `main`), `scripts/shot_proof.py` (every register-source read, both still renders, `main`), `scripts/seam_plan.py` (`dna_ground_y`, `main`)
- Test: `tests/test_workshop_routing.py`

**Interfaces:**
- Consumes: `workshop.prepare`, `workshop.run_kwargs`, `workshop.shot_names`, `workshop.durations`, `workshop.grounds`, `workshop.code_files`, `workshop.workshop_dir` (Task 2).
- Produces: `remotion_segments.code_files(out_dir=None)`, `code_hash(out_dir=None)`, `_bundle(dest, public, run=subprocess.run, env=None)`, `render_segment(..., env=None)`; `text_safe_qa.audit_shot(shot, props, frame, tmp_png, public_dir=None, env=None)`; `cjk_type_qa.sweep(names, dna=DEFAULT_DNA, aspect=None, film_props=None, out_dir=None)` and module state `_RUN_ENV` (None outside a sweep); `shot_proof._FILM_SHOTS` (list of extra register folders), `shot_proof._FILM_ENV` (subprocess kwargs), `shot_proof._src_path(shot)`; `seam_plan._EXTRA_GROUNDS` ({shot: token list or '#hex'}).

- [ ] **Step 1: Write the failing tests** — `tests/test_workshop_routing.py`:

```python
"""Every film-scoped render goes through the film's workshop (scripts/workshop.py), and nothing else does.

The unit half proves each caller hands the workshop's environment to the CLI — and hands NOTHING when a film has
no workshop, so that film runs exactly the call it always did. The rendered half runs a real two-beat film with a
workshop through the per-beat renderer, and makes an object that throws say its own message in every gate."""
import json
import os
import shutil
import subprocess
import sys

import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
import remotion_segments as rs  # noqa: E402
from test_workshop_bundle import SHOT, OBJECT  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

BOOM = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};
export const %(name)s: React.FC<ObjectProps & {bars?: unknown}> = ({bars}) => {
  if (typeof bars !== 'number') throw new Error('WsBoom: pressure must be a number of bars, got ' + JSON.stringify(bars));
  return <div />;
};
"""


def _film(tmp_path, audio=False, obj="WsDisc", obj_src=OBJECT, second="WsShotA"):
    out = tmp_path / "film"
    for kind, n, src in (("shots", "WsShotA", SHOT), ("objects", obj, obj_src)):
        d = out / "workshop" / kind
        d.mkdir(parents=True, exist_ok=True)
        (d / (n + ".tsx")).write_text(src % {"name": n}, encoding="utf-8")
    slides = [{"index": 1, "shot": "WsShotA", "narration": "一", "shot_props":
               {"fill": "#0000ff", "object": {"id": obj, "props": {"color": "#ff0000"}}}},
              {"index": 2, "shot": second, "narration": "二", "shot_props": {"fill": "#000000"} if second == "WsShotA" else {}}]
    if audio:
        (out / "audio").mkdir()
        for s in slides:
            mp3 = "audio/%02d.mp3" % s["index"]
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                            "-t", "2", str(out / mp3)], check=True)
            s.update(audio=mp3, duration=2.0)
    board = {"meta": {"renderer": "remotion", "design_dna": "product", "language": "zh"}, "slides": slides}
    (out / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    return str(out)


def test_the_film_s_valid_ids_include_its_workshop(monkeypatch, tmp_path):
    import render_remotion as rr
    out = _film(tmp_path)
    seen = {}

    def fake_build(slides, out_dir, valid, fps=30, **kw):
        seen["valid"] = set(valid)
        return []
    monkeypatch.setattr(rr, "build_scenes", fake_build)
    rr.film_props(out, json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8")))
    assert "WsShotA" in seen["valid"] and "TermTable" in seen["valid"]


def _whole(monkeypatch, tmp_path, with_workshop):
    import render_remotion as rr
    calls = []
    monkeypatch.setattr(rr.subprocess, "run", lambda cmd, cwd=None, check=True, **kw: calls.append(kw))
    monkeypatch.setattr(rr, "_remotion_deliverables", lambda *a, **k: None)
    monkeypatch.setattr(rr, "build_scenes", lambda slides, out_dir, valid, fps=30, **kw: [{"shot": "TermTable", "durF": 60}])
    monkeypatch.setattr(rr.shutil, "which", lambda _x: "/usr/bin/npx")
    monkeypatch.delenv("SLIDES_WORKSHOP", raising=False)
    out = _film(tmp_path) if with_workshop else str(tmp_path)
    rr._render_remotion(out, {"meta": {"renderer": "remotion"}, "slides": [{"index": 1}]}, whole=True)
    return out, calls


def test_the_whole_film_render_runs_with_the_workshop(monkeypatch, tmp_path):
    out, calls = _whole(monkeypatch, tmp_path, True)
    assert calls and calls[0]["env"]["SLIDES_WORKSHOP"] == ws.workshop_dir(out)


def test_without_a_workshop_the_whole_film_render_is_the_call_it_always_was(monkeypatch, tmp_path):
    _out, calls = _whole(monkeypatch, tmp_path, False)
    assert calls == [{}]


def test_the_segment_bundle_carries_the_environment_it_is_given(tmp_path):
    calls = []

    def fake(cmd, cwd=None, check=True, **kw):
        calls.append(kw)
        dest = next(a for a in cmd if a.startswith("--out-dir=")).split("=", 1)[1]
        os.makedirs(dest, exist_ok=True)
        open(os.path.join(dest, "index.html"), "w").close()
    rs._bundle(str(tmp_path / "b"), str(tmp_path), run=fake, env={"SLIDES_WORKSHOP": "/x"})
    rs._bundle(str(tmp_path / "c"), str(tmp_path), run=fake)
    assert calls == [{"env": {"SLIDES_WORKSHOP": "/x"}}, {}]


def test_render_film_bundles_with_the_film_s_workshop(monkeypatch, tmp_path):
    out = _film(tmp_path)
    got = {}

    class Stop(Exception):
        pass

    def spy(dest, public, run=None, env=None):
        got["env"] = env
        raise Stop()
    monkeypatch.setattr(rs, "_bundle", spy)
    with pytest.raises(Stop):
        rs.render_film(out, {"scenes": [{"shot": "WsShotA", "durF": 60}]}, os.path.join(out, "p.json"),
                       os.path.join(out, "o.mp4"), [], {"gl": "angle"}, log=lambda *_: None)
    assert got["env"]["SLIDES_WORKSHOP"] == ws.workshop_dir(out)


def test_the_segment_cache_key_sees_the_workshop_and_not_where_the_film_lives(tmp_path):
    out = _film(tmp_path)
    plain = tmp_path / "plain"
    plain.mkdir()
    h0 = rs.code_hash(str(plain))
    assert h0 == rs.code_hash()
    h1 = rs.code_hash(out)
    assert h1 != h0
    ws.write_index(out)
    assert rs.code_hash(out) == h1                 # the generated index is not a source
    moved = tmp_path / "elsewhere" / "film"
    shutil.copytree(out, str(moved))
    assert rs.code_hash(str(moved)) == h1           # moving the film does not re-render it
    with open(os.path.join(ws.workshop_dir(out), "objects", "WsDisc.tsx"), "a", encoding="utf-8") as fh:
        fh.write("\n// edited\n")
    assert rs.code_hash(out) != h1                  # editing a built thing does


def test_text_safe_measures_workshop_beats_in_their_bundle(monkeypatch, tmp_path):
    import text_safe_qa as g
    out = _film(tmp_path)
    seen = []

    class R:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr(g.subprocess, "run", lambda cmd, **k: seen.append(k) or R())
    findings, checked, universe, skipped = g.scan_film(out)
    assert (checked, universe, skipped) == (2, 2, []), skipped
    assert seen and all(k.get("env", {}).get("SLIDES_WORKSHOP") == ws.workshop_dir(out) for k in seen)


def test_cjk_type_measures_workshop_beats_in_their_bundle(monkeypatch, tmp_path):
    import cjk_type_qa as c
    out = _film(tmp_path)
    seen = []

    class R:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr(c.subprocess, "run", lambda cmd, **k: seen.append((cmd, k)) or R())
    monkeypatch.setattr(c, "_ink_fraction", lambda p: 1.0)
    monkeypatch.setattr(c, "evidence_props", lambda: {})
    res = c.sweep(["WsShotA"], film_props={"WsShotA": {"fill": "#000000"}}, out_dir=out)
    assert res["WsShotA"]["failed"] is False
    assert seen and all(k.get("env", {}).get("SLIDES_WORKSHOP") == ws.workshop_dir(out) for _c, k in seen)
    assert "--frame=%d" % int(30 * c.PROBE_FRAC) in seen[0][0]      # the workshop shot's own DURATION
    assert c._RUN_ENV is None                                         # the sweep's environment, not the module's


def test_shot_proof_reads_a_workshop_register_from_the_film(tmp_path):
    import shot_proof as sp
    out = _film(tmp_path)
    sp._FILM_SHOTS[:] = [os.path.join(ws.workshop_dir(out), "shots")]
    try:
        assert sp.exported_props("WsShotA") == {"fill", "object"}
        assert sp._src_path("TermTable").endswith(os.path.join("src", "shots", "TermTable.tsx"))
    finally:
        sp._FILM_SHOTS[:] = []


def test_seam_plan_judges_a_workshop_shot_on_its_declared_ground(monkeypatch):
    import seam_plan
    monkeypatch.setattr(seam_plan, "_EXTRA_GROUNDS", {"WsShotA": ["surface"]})
    assert seam_plan.dna_ground_y("WsShotA", {"surface": "#ffffff", "bg": "#000000"}) == pytest.approx(1.0)
    assert seam_plan.dna_ground_y("NotAShot", {"surface": "#ffffff"}) is None


@needs_toolchain
def test_a_real_film_with_a_workshop_renders_per_beat(tmp_path):
    """The whole path: board -> film_props -> segments (bundle once with the workshop, one render per beat) ->
    joined film, with the workshop shot and its object on the frame."""
    import render_remotion as rr
    out = _film(tmp_path, audio=True, second="TermTable")
    data = json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8"))
    mp4 = rr._render_remotion(out, data)
    assert os.path.exists(mp4)
    segs = [f for f in os.listdir(os.path.join(out, rs.CACHE_DIR)) if f.endswith(".mov")]
    assert len(segs) == 2, segs
    png = str(tmp_path / "beat1.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.8", "-i", mp4, "-frames:v", "1", png], check=True)
    im = Image.open(png).convert("RGB")
    mid, ground = im.getpixel((960, 540)), im.getpixel((400, 540))
    assert mid[0] > 150 and mid[2] < 90, mid
    assert ground[2] > 150 and ground[0] < 90, ground


@needs_toolchain
def test_a_throwing_object_is_named_by_the_gates(tmp_path, capsys):
    """Review focus: a bug in film code must be reported as the film code's own message by every gate — not as
    the last line of a stack, and never as a clean or blank frame."""
    import text_safe_qa as g
    import cjk_type_qa as c
    import shot_proof as sp
    out = _film(tmp_path, obj="WsBoom", obj_src=BOOM)
    findings, _checked, _u, _s = g.scan_film(out)
    assert any("pressure must be a number" in f for f in findings), findings
    res = c.sweep(["WsShotA"], film_props={"WsShotA": json.load(open(os.path.join(out, "storyboard.json")))
                                           ["slides"][0]["shot_props"]}, out_dir=out)
    assert res["WsShotA"]["failed"] and "pressure must be a number" in (res["WsShotA"]["why"] or ""), res
    rc = sp.main([out])
    printed = capsys.readouterr().out
    assert rc != 0 and "pressure must be a number" in printed, printed[-1500:]
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_workshop_routing.py -q`
Expected: FAIL — the callers pass no environment, `code_hash` takes no argument, `sweep` takes no `out_dir`.

- [ ] **Step 3: The renderer** — in `scripts/render_remotion.py`:

In `film_props`, replace `valid = _remotion_shot_ids()` with:
```python
    import workshop as _ws
    # A FILM'S OWN SHOTS ARE SHOTS. The library's ids are the component files in remotion/src/shots; a film's
    # workshop (scripts/workshop.py) adds its own, which exist only in a render scoped to this film.
    valid = set(_remotion_shot_ids()) | _ws.shot_names(out_dir)
```

In `_render_remotion`, replace the whole-film block (`if not segmented:` through its retry) with:
```python
    if not segmented:
        import workshop as _ws
        wk = _ws.run_kwargs(out_dir)            # the film's workshop — or {}, exactly the call it always was
        cmd = ["npx", "remotion", "render", "src/index.ts", "Film", out_mp4,
               "--props=" + os.path.abspath(props_path), "--public-dir=" + os.path.abspath(out_dir)] + run_flags
        try:
            subprocess.run(cmd, cwd=_REMOTION2_DIR, check=True, **wk)
        except subprocess.CalledProcessError:
            print("[render_remotion] render failed with GL — retrying ONCE without --gl (software raster; slower).")
            subprocess.run([a for a in cmd if not a.startswith("--gl=")], cwd=_REMOTION2_DIR, check=True, **wk)
```

- [ ] **Step 4: The per-beat renderer** — in `scripts/remotion_segments.py`:

Add below `CACHE_VERSION`:
```python
def _wk(env):
    """subprocess kwargs for a film's environment — none at all when it has no workshop (scripts/workshop.py)."""
    return {"env": env} if env is not None else {}
```

Change `def code_files():` to `def code_files(out_dir=None):`, add to its docstring "…and, for a film with a workshop, every source of it (scripts/workshop.py)", and before its `return sorted(files)` add:
```python
    if out_dir:
        import workshop as _ws
        files.update(_ws.code_files(out_dir))
```

Replace `code_hash` with:
```python
def code_hash(out_dir=None):
    """The code a segment is built from. A workshop file is keyed by its path INSIDE the workshop, so moving a
    film folder does not re-render it and editing one of its built things does."""
    ws_root = None
    if out_dir:
        import workshop as _ws
        ws_root = _ws.workshop_dir(out_dir) + os.sep
    h = hashlib.sha256()
    for p in code_files(out_dir):
        rel = ("workshop/" + os.path.relpath(p, ws_root)) if ws_root and p.startswith(ws_root) else os.path.relpath(p, SKILL)
        h.update(rel.replace(os.sep, "/").encode("utf-8"))
        h.update(b"\0")
        h.update(file_sha(p).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()
```

In `plan`, change `code = code_hash() if code is None else code` to `code = code_hash(public_dir) if code is None else code` (every caller passes the film's out_dir as `public_dir`).

Change `_bundle` to take and pass the environment:
```python
def _bundle(dest, public, run=subprocess.run, env=None):
    """Bundle the film ONCE for all the segments of this render — with the film's workshop, when it has one."""
    run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + dest, "--public-dir=" + public,
         "--log=error"], cwd=REMOTION, check=True, **_wk(env))
    if not os.path.isfile(os.path.join(dest, "index.html")):
        raise ModelMismatch("`remotion bundle` produced no index.html in %s" % dest)
    return dest
```

Change `render_segment`'s signature to `render_segment(seg, last, props_path, public_dir, cache, cli_flags, run=subprocess.run, serve=None, env=None)` and both of its `run(...)` calls to end with `, **_wk(env))` (`run(cmd, cwd=REMOTION, check=True, **_wk(env))` and the retry likewise).

Change `_render_stale`'s signature to `_render_stale(stale, segs, props_path, out_dir, cache, cli_flags, run, serve, name, log, env=None)` and its call to `render_segment(s, s["k"] == len(segs) - 1, props_path, out_dir, cache, cli_flags, run=run, serve=serve, env=env)`.

In `render_film`, before `work = tempfile.mkdtemp(...)`, add `import workshop as _ws` and `env = _ws.prepare(out_dir)       # the film's workshop enters the bundle here`, then pass it on: `_bundle(os.path.join(work, "bundle"), minimal_public(props, out_dir, os.path.join(work, "public")), run=run, env=env)` and `_render_stale(stale, segs, props_path, out_dir, cache, cli_flags, run, serve, name, log, env=env)`.

- [ ] **Step 5: The film gates** —

`scripts/text_safe_qa.py`: change `audit_shot`'s signature to `audit_shot(shot, props, frame, tmp_png, public_dir=None, env=None)` and its render to `r = subprocess.run(cmd, capture_output=True, text=True, cwd=_REMOTION, **({"env": env} if env is not None else {}))`. In its render-failure return, replace the last-line reason with the thrown message:
```python
    if r.returncode != 0:
        from shot_proof import _stderr_reason        # the MESSAGE, never the last line of a stack
        return [{"text": "(render FAILED twice — nothing was measured on this frame: %s)"
                         % _stderr_reason(blob)[:160], "out": {}}]
```
In `scan_film`, after `durs = durations()` add:
```python
    import workshop as _ws
    # A FILM'S OWN SHOTS are registers too: measured the same way, rendered in a bundle that holds its workshop.
    durs.update(_ws.durations(out_dir))
    env = _ws.prepare(out_dir)
```
and pass `env=env` to `audit_shot(shot, props, frame, tmp, public_dir=out_dir, env=env)`.

`scripts/cjk_type_qa.py`: below `_MUTATING = ...` add:
```python
# The film's workshop environment for the renders of ONE film-mode sweep (scripts/workshop.py) — None outside it,
# so a library sweep never bundles a film's workshop.
_RUN_ENV = None


def _wk():
    return {"env": _RUN_ENV} if _RUN_ENV is not None else {}
```
Add `**_wk()` to the three `subprocess.run(...)` calls in `_default_ink`, `_fed_missing` and `audit` (after `cwd=_REMOTION, capture_output=True, text=True`). Replace `sweep` with the version below — the same body (keep its docstring and its inline comments where they
are), now taking `out_dir`, reading the film's workshop durations, and holding the film's environment for exactly
the length of the sweep:
```python
def sweep(names, dna=DEFAULT_DNA, aspect=None, film_props=None, out_dir=None):
    global _RUN_ENV
    durs = durations()
    if out_dir:
        import workshop as _ws
        durs.update(_ws.durations(out_dir))
        _RUN_ENV = _ws.prepare(out_dir)
    try:
        ev = evidence_props()
        out = {}
        tmp = os.path.join(_REMOTION, ".cjk_type_probe.%d.png" % os.getpid())
        for n in names:
            props, untestable = (film_props.get(n), []) if film_props else cjk_props(n)
            if props is None:
                props, untestable = cjk_props(n)
            if n in ev:
                given = film_props.get(n) if film_props else None
                props = dict(ev[n], **props) if given else dict(props, **ev[n])
            frame = int(durs.get(n, 150) * PROBE_FRAC)
            why = []
            hits = audit(n, props, frame, tmp, dna, aspect, why=why)
            out[n] = {"hits": hits or [], "untestable": untestable, "failed": hits is None,
                      "why": (why[0] if why else None),
                      "cjk_fed": len([x for x in _string_leaves(props) if _HAS_CJK.search(x)])}
        for p in (tmp, tmp + ".props.json"):
            if os.path.exists(p):
                os.remove(p)
        return out
    finally:
        _RUN_ENV = None
``` In `main`, change `res = sweep(names, a.dna, a.aspect, film_props)` to `res = sweep(names, a.dna, a.aspect, film_props, out_dir=a.out_dir if film_props is not None else None)`.

`scripts/shot_proof.py`: below `_SHOTS = ...` add:
```python
# THE FILM'S OWN REGISTERS. While a film is proofed, its workshop's shots/ folder (scripts/workshop.py) is read
# after the library's, and every still renders in a bundle that holds the workshop. Empty otherwise.
_FILM_SHOTS = []
_FILM_ENV = {}


def _src_path(shot):
    """Where register `shot` is defined for the film being proofed: the library first, then the film's own. One
    lookup, so no check here reads the library for a register the film built itself."""
    for d in [_SHOTS] + _FILM_SHOTS:
        p = os.path.join(d, shot + ".tsx")
        if os.path.isfile(p):
            return p
    return os.path.join(_SHOTS, shot + ".tsx")           # the path the caller's message names
```
Replace every `os.path.join(_SHOTS, shot + ".tsx")` in the file (eight places: `switch_props`, `shot_defaults`, `demo_content_props`, `icon_capable`, `exported_props`, `default_copy`, the welded-copy check, and `main`'s DURATION read) with `_src_path(shot)`. In `main`, after `board = json.load(...)`, add:
```python
    import workshop as _ws
    _FILM_SHOTS[:] = [os.path.join(_ws.workshop_dir(out_dir), "shots")]
    _FILM_ENV.clear()
    _FILM_ENV.update(_ws.run_kwargs(out_dir))
```
and add `**_FILM_ENV` to both `subprocess.run(["npx", "remotion", "still", ...], cwd=_REMOTION, capture_output=True, text=True)` calls.

`scripts/seam_plan.py`: below `_GROUND_TOKEN = None` add:
```python
# A film's own shots declare their ground (scripts/workshop.py GROUND) — the renderer merges the same declaration
# (remotion/src/registry.ts), so the planner must too, or it judges their seams on nothing. Set by main().
_EXTRA_GROUNDS = {}
```
In `dna_ground_y`, change `toks = _ground_tokens().get(shot)` to `toks = _ground_tokens().get(shot) or _EXTRA_GROUNDS.get(shot)`. In `main`, after `slides = board.get("slides", [])` add:
```python
    import workshop as _ws
    _EXTRA_GROUNDS.clear()
    for n, g in _ws.grounds(out_dir).items():
        if isinstance(g, str) and not g.startswith("#"):
            g = [g]
        if g:
            _EXTRA_GROUNDS[n] = g
```

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest tests/test_workshop_routing.py tests/test_remotion_segments.py tests/test_text_safe_qa.py tests/test_cjk_type_qa.py -q`
Expected: PASS — the existing segment, text-safe and CJK tests unchanged (their fakes receive no `env` because their boards have no workshop).

- [ ] **Step 7: Commit**

```bash
git add scripts/render_remotion.py scripts/remotion_segments.py scripts/text_safe_qa.py scripts/cjk_type_qa.py scripts/shot_proof.py scripts/seam_plan.py tests/test_workshop_routing.py
git commit -m "Film-scoped renders and gates run in a bundle that holds the film's workshop; everything else runs the call it always did

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---
### Task 4: `validate.py` knows what the film built

**Files:**
- Modify: `scripts/validate.py` (`_check_remotion`: the valid set and the build verdict; a new `_check_build`; `_idiom_world`; the remotion branch of `evaluate` that calls them)
- Test: `tests/test_build_list.py`

**Interfaces:**
- Consumes: `workshop.shot_names`, `object_names`, `library_shot_names`, `library_object_names`, `demo_objects`, `shot_source`, `object_source`, `object_meta`, `object_refs`, `required_in_film`, `uses`, `provenances`, `check` (Task 2).
- Produces: `validate._check_build(meta, slides, errors, warnings, out_dir, skips=None)`; `validate._idiom_world(meta, slides, errors, warnings, out_dir=None)`. The board fields it defines: `meta.build_list = [{id, kind: "object"|"shot", beats, means, slot, uses, accept, promoted?}]`, `slide.shot_fit.ref`.

- [ ] **Step 1: Write the failing tests** — `tests/test_build_list.py`:

```python
"""validate.py knows what a film built: the build list and the workshop agree both ways, every reference names
something that exists, and the stage registers' own previews never reach a film."""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate as v  # noqa: E402
import workshop as ws  # noqa: E402
from test_workshop_bundle import SHOT, OBJECT  # noqa: E402

REQUIRING = SHOT.replace("export const DURATION = 30;", "export const DURATION = 30;\n"
                                                        "export const REQUIRED_IN_FILM = ['object'] as const;")


@pytest.fixture(autouse=True)
def _code_check_is_task_2s(monkeypatch):
    """The workshop's own code check has its tests in tests/test_workshop.py; stubbed here so these judge the
    board. `test_the_workshop_code_check_reaches_validate` runs the wiring for real."""
    monkeypatch.setattr(ws, "check", lambda out_dir: [])


def _entry(eid, kind="object", **kw):
    e = {"id": eid, "kind": kind, "means": "what a viewer must see", "slot": "WsShotA" if kind == "object" else "own",
         "accept": "caption hidden, the viewer still sees it"}
    e.update(kw)
    return e


def _board(tmp_path, slides, build_list=None, shots=("WsShotA",), objects=("WsDisc",), meta=None,
           shot_src=SHOT, obj_src=OBJECT):
    for kind, names, src in (("shots", shots, shot_src), ("objects", objects, obj_src)):
        d = tmp_path / "workshop" / kind
        for n in names:
            d.mkdir(parents=True, exist_ok=True)
            (d / (n + ".tsx")).write_text(src % {"name": n}, encoding="utf-8")
    (tmp_path / "audio").mkdir(exist_ok=True)
    for i, s in enumerate(slides, 1):
        (tmp_path / "audio" / ("%02d.mp3" % i)).write_bytes(b"\0")
        s.setdefault("index", i)
        s.setdefault("narration", "这一拍说的事。")
        s.setdefault("audio", "audio/%02d.mp3" % i)
        s.setdefault("duration", 3.0)
    m = {"renderer": "remotion", "design_dna": "product", "language": "zh", "captions": False}
    m.update(meta or {})
    if build_list is not None:
        m["build_list"] = build_list
    return {"meta": m, "slides": slides}


def _errs(board, tmp_path):
    return v.evaluate(board, str(tmp_path))["errors"]


def _holding(obj="WsDisc", **fit):
    s = {"shot": "WsShotA", "shot_props": {"object": {"id": obj}}}
    if fit:
        s["shot_fit"] = dict({"verdict": "build", "why": "no register draws it"}, **fit)
    return s


def test_a_workshop_shot_is_a_valid_shot_id(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert not [e for e in errs if "unknown shot" in e or "WsShotA is" in e], errs


def test_the_build_list_and_the_workshop_agree_both_ways(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("Ghost")])
    errs = _errs(board, tmp_path)
    assert any("`Ghost` has no workshop/objects/Ghost.tsx" in e for e in errs), errs
    assert any("workshop/shots/WsShotA.tsx is not on meta.build_list" in e for e in errs), errs


def test_an_entry_says_what_it_is_for_and_how_it_is_judged(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")],
                   [_entry("WsDisc", kind="widget", means="", accept=" ", slot=""), _entry("WsShotA", "shot")])
    errs = " | ".join(_errs(board, tmp_path))
    for needle in ("`kind` is object or shot", "`means` is empty", "`accept` is empty", "`slot` names the template"):
        assert needle in errs, (needle, errs)


def test_an_entry_no_beat_uses_is_refused_and_a_wrong_beats_list_is_named(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {}}],
                   [_entry("WsDisc"), _entry("WsShotA", "shot", beats=[2])])
    res = v.evaluate(board, str(tmp_path))
    assert any("`WsDisc` is used by no beat" in e for e in res["errors"]), res["errors"]
    assert any("`WsShotA` says beats [2]" in w for w in res["warnings"]), res["warnings"]


def test_shot_fit_ref_must_name_an_entry_this_beat_uses(tmp_path):
    board = _board(tmp_path, [_holding(ref="Nope"), {"shot": "WsShotA", "shot_props": {},
                                                      "shot_fit": {"verdict": "build", "ref": "WsDisc", "why": "x"}}],
                   [_entry("WsDisc"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert any("scene #1: shot_fit.ref 'Nope' is not on meta.build_list" in e for e in errs), errs
    assert any("scene #2: shot_fit.ref 'WsDisc', but this beat" in e for e in errs), errs


def test_a_build_verdict_names_its_entry(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {"object": {"id": "WsDisc"}},
                               "shot_fit": {"verdict": "build", "why": "x"}}],
                   [_entry("WsDisc"), _entry("WsShotA", "shot")])
    assert any("shot_fit says build but names no `ref`" in e for e in _errs(board, tmp_path))


def test_a_board_that_builds_nothing_is_judged_exactly_as_before(tmp_path):
    """No workshop, no build list: a library beat with a legacy `build` verdict gets no new finding."""
    board = _board(tmp_path, [{"shot": "TermTable", "shot_props": {"cmd": "ls"},
                               "shot_fit": {"verdict": "build", "why": "x"}}], shots=(), objects=())
    errs = _errs(board, tmp_path)
    assert not os.path.exists(tmp_path / "workshop")
    assert not [e for e in errs if "shot_fit.ref" in e or "names no `ref`" in e or "build_list" in e
                or "workshop" in e or "Design DNA" in e], errs


def test_an_unknown_object_is_named_with_what_exists(tmp_path):
    board = _board(tmp_path, [_holding("Nope", ref="WsShotA")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert any("names object 'Nope'" in e and "WsDisc" in e for e in errs), errs


def test_object_props_are_the_film_s_and_never_the_slot_s(tmp_path):
    s = _holding(ref="WsDisc")
    s["shot_props"]["object"]["props"] = {"t": 0.5, "color": "#fff"}
    board = _board(tmp_path, [s], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    assert any("props sets t" in e for e in _errs(board, tmp_path))


def test_a_prop_the_register_requires_in_a_film_must_be_set(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {}}], [_entry("WsShotA", "shot")],
                   objects=(), shot_src=REQUIRING)
    assert any("WsShotA needs `object` in a film" in e for e in _errs(board, tmp_path))


def test_a_film_that_builds_needs_a_design_dna(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                   meta={"design_dna": None})
    assert any("builds things but has no Design DNA" in e for e in _errs(board, tmp_path))


def test_a_held_object_supplies_the_beat_s_idiom_world(tmp_path):
    industrial = OBJECT.replace("'motion-graphics'", "'industrial'")
    ok = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                meta={"idiom_world": ["industrial"]}, obj_src=industrial)
    assert not [e for e in _errs(ok, tmp_path) if "world" in e], _errs(ok, tmp_path)
    (tmp_path / "workshop" / "objects" / "WsDisc.tsx").write_text(OBJECT % {"name": "WsDisc"}, encoding="utf-8")
    errs = _errs(ok, tmp_path)
    assert any("holding WsDisc" in e and "motion-graphics" in e for e in errs), errs


def test_the_workshop_code_check_reaches_validate(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "check", lambda out_dir: ["workshop/objects/WsDisc.tsx:3 words written into the code"])
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    assert any(e.startswith("workshop: workshop/objects/WsDisc.tsx:3") for e in _errs(board, tmp_path))
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_build_list.py -q`
Expected: FAIL — `unknown shot 'WsShotA'`, and none of the build-list findings exist.

- [ ] **Step 3: Workshop shots are valid ids** — in `_check_remotion`, directly after the line that computes `valid = {f[:-4] for f in os.listdir(shots_dir) ...}`, add:
```python
    import workshop as _wsv
    # A FILM'S OWN SHOTS are valid ids for THIS film (scripts/workshop.py); _check_build judges them.
    _film_shots = _wsv.shot_names(out_dir)
    valid |= _film_shots
```
and change the build-verdict branch's condition from `if verdict == "build":` to `if verdict == "build" and shot not in _film_shots:` (a workshop shot is not registered in the library by design; `_check_build` judges its `ref`).

- [ ] **Step 4: The build list** — add to `scripts/validate.py`, after `_check_remotion`:

```python
def _check_build(meta, slides, errors, warnings, out_dir, skips=None):
    """WHAT THE FILM BUILT (docs/superpowers/specs/2026-09-27-adaptive-build-design.md). The build list and the
    workshop agree both ways; every `shot_fit.ref` names an entry the beat really uses; every object a beat names
    exists and is not a stage's own preview; every prop a register requires in a film is set; a film that builds
    has a Design DNA; and the workshop's own code passes scripts/workshop.py check (type-check, imports, content
    contract, words from props). Every finding names the beat or the entry and the fix."""
    import workshop as _ws
    items = {}
    if out_dir:
        items.update({n: "shot" for n in _ws.shot_names(out_dir)})
        items.update({n: "object" for n in _ws.object_names(out_dir)})
    bl = meta.get("build_list")
    if bl is not None and not isinstance(bl, list):
        errors.append("meta.build_list must be a list of {id, kind, beats, means, slot, uses, accept}")
        bl = []
    entries = {}
    for i, e in enumerate(bl or []):
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"].strip():
            errors.append("meta.build_list[%d] needs an `id` — the name of the object or shot it builds" % i)
            continue
        eid = e["id"]
        where = "meta.build_list `%s`" % eid
        if eid in entries:
            errors.append("%s is listed twice" % where)
        entries[eid] = e
        kind = e.get("kind")
        if kind not in ("object", "shot"):
            errors.append("%s: `kind` is object or shot (got %r)" % (where, kind))
        for f, why in (("means", "say what the viewer must see"),
                       ("accept", "say how it is judged — with the caption hidden, what does a viewer still see?")):
            if not str(e.get(f) or "").strip():
                errors.append("%s: `%s` is empty — %s" % (where, f, why))
        if not str(e.get("slot") or "").strip():
            errors.append("%s: `slot` names the template it goes into — a register with an object slot, a stage "
                          "register, or `own` for a shot" % where)
        if e.get("promoted"):
            lib = _ws.library_shot_names() if kind == "shot" else _ws.library_object_names()
            if eid not in lib:
                errors.append("%s is marked promoted but the library has no %s %s" % (where, kind, eid))
        elif eid not in items:
            k = kind if kind in ("object", "shot") else "object"
            errors.append("%s has no workshop/%ss/%s.tsx — build it: python3 scripts/workshop.py <out_dir> new-%s %s "
                          "--means \"...\"" % (where, k, eid, k, eid))
        elif kind in ("object", "shot") and items[eid] != kind:
            errors.append("%s is listed as a %s and the workshop holds it as a %s" % (where, kind, items[eid]))
    for name, kind in sorted(items.items()):
        if name not in entries:
            errors.append("workshop/%ss/%s.tsx is not on meta.build_list — every built thing says what it is for "
                          "(`means`) and how it is judged (`accept`)" % (kind, name))
    used = _ws.uses(slides, out_dir)
    for eid, e in sorted(entries.items()):
        beats = used.get(eid) or []
        if not beats:
            errors.append("meta.build_list `%s` is used by no beat" % eid)
        elif isinstance(e.get("beats"), list) and sorted(e["beats"]) != sorted(beats):
            warnings.append("meta.build_list `%s` says beats %s; the board uses it on beats %s"
                            % (eid, e["beats"], beats))
    for pos, s in enumerate(slides, 1):
        num = s.get("index", pos)
        tag = "scene #%s" % num
        fit = s.get("shot_fit") if isinstance(s.get("shot_fit"), dict) else {}
        ref = fit.get("ref")
        if ref is not None:
            if ref not in entries:
                errors.append("%s: shot_fit.ref %r is not on meta.build_list" % (tag, ref))
            elif num not in (used.get(ref) or []):
                errors.append("%s: shot_fit.ref %r, but this beat neither is that shot nor holds that object"
                              % (tag, ref))
        elif fit.get("verdict") == "build" and (s.get("shot") in items or bl is not None):
            errors.append("%s: shot_fit says build but names no `ref` — name the build-list entry this beat uses"
                          % tag)
    known = _ws.library_object_names() | _ws.object_names(out_dir)
    demo = _ws.demo_objects()
    for pos, s in enumerate(slides, 1):
        tag = "scene #%s" % s.get("index", pos)
        shot = s.get("shot")
        src = _ws.shot_source(out_dir, shot)
        if src is None:
            continue
        sp = s.get("shot_props") if isinstance(s.get("shot_props"), dict) else {}
        for path, ref in _ws.object_refs(src, sp):
            if not isinstance(ref, dict) or not isinstance(ref.get("id"), str) or not ref["id"].strip():
                errors.append('%s: %s.%s must be an object reference {"id": "<Name>", "props": {...}} (got %r)'
                              % (tag, shot, path, ref))
                continue
            oid = ref["id"]
            if oid in demo:
                errors.append("%s: %s.%s is `%s`, a stage's own preview form — draw the film's object "
                              "(python3 scripts/workshop.py <out_dir> new-object <Name> --means \"...\")"
                              % (tag, shot, path, oid))
            elif oid not in known:
                errors.append("%s: %s.%s names object %r, which neither the film's workshop nor the library "
                              "defines (defined: %s)" % (tag, shot, path, oid, ", ".join(sorted(known)) or "none"))
            props = ref.get("props")
            if props is not None and not isinstance(props, dict):
                errors.append("%s: %s.%s.props must be an object (got %r)" % (tag, shot, path, props))
            elif isinstance(props, dict):
                clash = sorted(k for k in props if k in ("w", "h", "t", "dna", "yaw"))
                if clash:
                    errors.append("%s: %s.%s.props sets %s, which the slot gives every object — remove them"
                                  % (tag, shot, path, ", ".join(clash)))
        for p in sorted(_ws.required_in_film(src)):
            if p not in sp:
                errors.append("%s: %s needs `%s` in a film — without it the register draws its own preview, which "
                              "is no film's picture" % (tag, shot, p))
    if items and not (meta.get("design_dna") or meta.get("shot_template")):
        errors.append("remotion: this film builds things but has no Design DNA — built things paint from its "
                      "tokens, and a workshop shot's declared GROUND resolves only under one (set meta.design_dna)")
    if out_dir and os.path.isdir(os.path.join(os.path.abspath(out_dir), "workshop")):
        for p in _ws.check(out_dir):
            errors.append("workshop: " + p)
```

In `evaluate`'s remotion branch, after `_check_remotion(meta, slides, errors, warnings, out_dir, skips=skips, vertical=vertical)` add `_check_build(meta, slides, errors, warnings, out_dir, skips=skips)`, and change `_idiom_world(meta, slides, errors, warnings)` to `_idiom_world(meta, slides, errors, warnings, out_dir=out_dir)`.

- [ ] **Step 5: A held object supplies the beat's idiom world** — in `_idiom_world`, change the signature to `def _idiom_world(meta, slides, errors, warnings, out_dir=None):`, and replace the loop `for _pos, s in enumerate(slides, start=1): ... elif w not in ok: off.append((_pos, shot, w))` with:

```python
    import workshop as _ws
    film_prov = _ws.provenances(out_dir) if out_dir else {}
    lib_obj_prov = {n: (_ws.object_meta(_ws.object_source(None, n)) or {}).get("provenance")
                    for n in _ws.library_object_names()}
    for _pos, s in enumerate(slides, start=1):
        shot = s.get("shot")
        # AN OBJECT THAT HOLDS A BEAT SUPPLIES THE BEAT'S IDIOM: the register frames it, the object is what the
        # viewer reads — so a stage register does not force a film to declare the stage's own world.
        held = [ref["id"] for _p, ref in _ws.object_refs(_ws.shot_source(out_dir, shot), s.get("shot_props") or {})
                if isinstance(ref, dict) and isinstance(ref.get("id"), str)]
        held_worlds = [film_prov.get(o) or lib_obj_prov.get(o) for o in held]
        if held and all(held_worlds):
            for o, hw in zip(held, held_worlds):
                if hw not in ok:
                    off.append((_pos, "%s (holding %s)" % (shot, o), hw))
            continue
        w = PROV.get(shot) or film_prov.get(shot)
        if w is None:
            # A register with no provenance is SILENTLY EXEMPT from this gate — validate looks it up, gets
            # nothing and moves on. That is how the check would have decayed to nothing as the library grew,
            # so an untagged register is a finding about the LIBRARY, not a pass for the beat.
            if shot:
                untagged.append((_pos, shot))
        elif w not in ok:
            off.append((_pos, shot, w))
```

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest tests/test_build_list.py tests/test_device_wiring.py tests/test_demo_copy_qa.py tests/test_beat_ground_delivery.py tests/test_declaration_readers.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/validate.py tests/test_build_list.py
git commit -m "validate: the build list and the workshop agree both ways, every object a beat names exists, and a stage's preview never reaches a film

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---
### Task 5: Words only from props, measured on the frame

**Files:**
- Modify: `remotion/src/runtime/textSafe.tsx` (a fifth mode, `unfed`), `remotion/src/Root.tsx` (`DnaPreview` wires it), `scripts/shot_proof.py` (the check on every beat that shows a built thing; a workshop shot's ground claim measured)
- Test: `tests/test_unfed_text.py`

**Interfaces:**
- Consumes: Task 1 (`data-object-slot` on every slot), Task 2 (`workshop.baked_words(...)["declared"]`, `grounds`, `object_refs`, `shot_source`, `shot_names`, `source_files`, `still`), Task 3 (`shot_proof._FILM_ENV`, `_src_path`), `seam_plan._resolve_dna`, `seam_plan._rel_lum`, `seam_plan.HARSH_GAP`, `_caption_band.caption_band_px(w, h)`.
- Produces: TS `UNFED_TEXT_TAG = 'UNFED-TEXT '`, `auditUnfedText(root, fed, scope: 'all' | 'slots'): string[]`; `TextSafeAudit` props `mode: 'safe' | 'collisions' | 'fed' | 'unfed'`, `scope`; a standalone composition given `unfedText: string[]` and `unfedScope: 'all' | 'slots'` cancels its render with `UNFED-TEXT {"unfed": [...]}`. Python `shot_proof.UNFED_TAG`, `shot_proof._unfed_text(shot, payload, frame, proof, beat, out_dir, scope, declared) -> list | None`, `shot_proof._ground_claim(png, shot, out_dir, board) -> str | None`, `shot_proof._band_luminance(png) -> float | None`.

- [ ] **Step 1: Write the failing tests** — `tests/test_unfed_text.py`:

```python
"""A built thing takes every word from the film's props — asked of the rendered DOM, not inferred from source.

The static scan (scripts/jsx_words.cjs) sees words written into the code; it cannot see a word that reaches the
screen through a constant list, a single-word default, or a wrapped library register's own copy. The frame can."""
import json
import os
import re
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shot_proof as sp  # noqa: E402
import workshop as ws  # noqa: E402
from test_workshop_bundle import OBJECT, _env, _still  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

LABELS = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ObjectSlot, type ObjectRef} from '@runtime/objectSlot';
import {useDNA} from '@runtime/dna';
export const DURATION = 60;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
const STEPS = ['Grind', 'Tamp'];
export const %(name)s: React.FC<{label?: string; a?: string; b?: string; object?: ObjectRef; paper?: boolean}> =
  ({label = '', a = '', b = '', object, paper = false}) => {
  const dna = useDNA();
  return (
    <AbsoluteFill style={{background: paper ? '#ffffff' : (dna?.bg ?? '#101010'), color: '#888888', fontSize: 60}}>
      <div style={{position: 'absolute', left: 100, top: 200}}>{label}</div>
      <div style={{position: 'absolute', left: 100, top: 300}}>{STEPS.map((s) => <span key={s}>{s} </span>)}</div>
      <div style={{position: 'absolute', left: 100, top: 400}}>{a && b ? `${a} · ${b}` : ''}</div>
      {object ? <ObjectSlot object={object} box={{x: 1100, y: 200, w: 500, h: 500}} /> : null}
    </AbsoluteFill>
  );
};
"""

INSIDE = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};
const WORD = ['INSIDE'];
export const %(name)s: React.FC<ObjectProps> = ({w, h}) => (
  <div style={{width: w, height: h, fontSize: 40, color: '#aaaaaa'}}>
    {WORD[0]}
    {/* @fixed-text: the SI symbol of the quantity the film names */}
    <span>bar</span>
  </div>
);
"""


def _workshop(tmp_path):
    out = tmp_path / "film"
    for kind, n, src in (("shots", "WsLabels", LABELS), ("objects", "WsInside", INSIDE)):
        d = out / "workshop" / kind
        d.mkdir(parents=True, exist_ok=True)
        (d / (n + ".tsx")).write_text(src % {"name": n}, encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


def _unfed(comp, props, env, png):
    r = _still(comp, png, props, env, frame=40)
    blob = r.stdout + r.stderr
    assert sp.UNFED_TAG in blob, blob[-800:]
    return json.JSONDecoder().raw_decode(blob.split(sp.UNFED_TAG, 1)[1])[0]["unfed"]


def test_the_tag_is_the_runtime_s():
    src = open(os.path.join(_REM, "src", "runtime", "textSafe.tsx"), encoding="utf-8").read()
    assert "export const UNFED_TEXT_TAG = '%s';" % sp.UNFED_TAG in src


@needs_toolchain
def test_a_word_no_prop_supplied_is_found_on_the_frame(tmp_path):
    out = _workshop(tmp_path)
    env = _env(ws.workshop_dir(out))
    got = _unfed("WsLabels", {"label": "研磨", "unfedText": ["研磨"], "unfedScope": "all"}, env, tmp_path / "a.png")
    assert sorted(got) == ["Grind", "Tamp"], got


@needs_toolchain
def test_words_the_film_supplied_are_not_reported_even_when_joined(tmp_path):
    out = _workshop(tmp_path)
    env = _env(ws.workshop_dir(out))
    fed = ["研磨", "Grind", "Tamp", "萃取", "压力"]
    got = _unfed("WsLabels", {"label": "研磨", "a": "萃取", "b": "压力", "unfedText": fed, "unfedScope": "all"},
                 env, tmp_path / "b.png")
    assert got == [], got


@needs_toolchain
def test_the_slots_scope_asks_only_what_the_object_draws(tmp_path):
    out = _workshop(tmp_path)
    env = _env(ws.workshop_dir(out))
    props = {"label": "研磨", "object": {"id": "WsInside"}, "unfedText": ["研磨"], "unfedScope": "slots"}
    got = _unfed("WsLabels", props, env, tmp_path / "c.png")
    assert sorted(got) == ["INSIDE", "bar"], got
    props["unfedScope"] = "all"
    assert sorted(_unfed("WsLabels", props, env, tmp_path / "d.png")) == ["Grind", "INSIDE", "Tamp", "bar"]


def _board(out, props, dna="product"):
    board = {"meta": {"renderer": "remotion", "design_dna": dna, "language": "zh"},
             "slides": [{"index": 1, "shot": "WsLabels", "narration": "一", "shot_props": props}]}
    with open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False)


@needs_toolchain
def test_shot_proof_names_the_words_no_prop_supplied_and_accepts_a_declared_one(tmp_path, capsys):
    out = _workshop(tmp_path)
    _board(out, {"label": "研磨", "object": {"id": "WsInside"}})
    sp.main([out])
    printed = capsys.readouterr().out
    line = next((l for l in printed.splitlines() if "no prop supplied" in l), "")
    assert "'Grind'" in line and "'Tamp'" in line and "'INSIDE'" in line, printed[-2000:]
    assert "'bar'" not in line, line                       # declared `@fixed-text` in the workshop code


@needs_toolchain
def test_a_ground_claim_the_frame_contradicts_is_an_error(tmp_path, capsys):
    out = _workshop(tmp_path)
    _board(out, {"label": "研磨", "paper": True})          # declares GROUND 'bg' (dark here) and paints white
    sp.main([out])
    printed = capsys.readouterr().out
    assert "declares GROUND 'bg'" in printed and "caption band renders at" in printed, printed[-2000:]
    _board(out, {"label": "研磨"})                         # paints dna.bg, as declared
    sp.main([out])
    assert "declares GROUND" not in capsys.readouterr().out


@needs_toolchain
def test_the_workshop_renders_a_shot_s_settled_frame_to_look_at(tmp_path):
    out = _workshop(tmp_path)
    _board(out, {"label": "研磨"})
    png = ws.still(out, "WsLabels")
    assert png == os.path.join(ws.workshop_dir(out), "_stills", "WsLabels.png") and os.path.getsize(png) > 1000
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_unfed_text.py -q`
Expected: FAIL — `shot_proof` has no `UNFED_TAG`; the audit has no `unfed` mode.

- [ ] **Step 3: The audit** — in `remotion/src/runtime/textSafe.tsx`, after `auditFedText`, add:

```tsx
/**
 * THE CONTENT CONTRACT, ON THE FRAME: the words a viewer can read that no prop supplied.
 *
 * `fed` asks whether the film's copy ARRIVED; this asks the opposite question — whether anything arrived that the
 * film never said. A built thing (scripts/workshop.py) takes every word from props; the static scan
 * (scripts/jsx_words.cjs) catches the words written into its code, and cannot see a word that reaches the
 * screen through a constant list, a one-word default, or a wrapped library register's own copy. This can.
 *
 * Compared on LETTERS only, case- and width-folded, because a register may re-case a label, join two of them
 * with a separator, or set each glyph in its own element — all of which are the register working. A run counts
 * as fed when its letters appear inside one fed string, or when nearly all of them are found among the fed
 * strings' letters. `scope: 'slots'` asks only the text inside objects (`[data-object-slot]`), for a library
 * register holding a film's object: the register's own words are judged elsewhere.
 */
export const UNFED_TEXT_TAG = 'UNFED-TEXT ';
const UNFED_COVERAGE = 0.9;
export const auditUnfedText = (root: Element, fed: unknown[], scope: 'all' | 'slots'): string[] => {
  const letters = (s: string) => [...s.normalize('NFKC').toLowerCase()].filter((ch) => /\p{L}/u.test(ch)).join('');
  const fedL = fed.map((f) => letters(String(f ?? ''))).filter((f) => f.length > 0);
  const pool = new Map<string, number>();
  for (const f of fedL) for (const ch of f) pool.set(ch, (pool.get(ch) ?? 0) + 1);
  const els = scope === 'slots'
    ? Array.from(root.querySelectorAll('[data-object-slot], [data-object-slot] *'))
    : Array.from(root.querySelectorAll('*'));
  const out: string[] = [];
  for (const el of els) {
    if (isEcho(el)) continue;
    const own = hasOwnText(el);
    const L = letters(own);
    if (!L) continue;
    if (fedL.some((f) => f.includes(L))) continue;
    const left = new Map(pool);
    let hit = 0;
    for (const ch of L) {
      const c = left.get(ch) ?? 0;
      if (c > 0) {
        hit += 1;
        left.set(ch, c - 1);
      }
    }
    if (hit / L.length >= UNFED_COVERAGE) continue;
    const shown = own.length > 40 ? own.slice(0, 40) + '…' : own;
    if (!out.includes(shown)) out.push(shown);
  }
  return out;
};
```

In `TextSafeAudit`, widen its props to `{enabled?: boolean; mode?: 'safe' | 'collisions' | 'fed' | 'unfed'; fed?: unknown[]; scope?: 'all' | 'slots'}` and destructure `scope = 'all'`; directly after the `mode === 'fed'` branch add:
```tsx
      if (mode === 'unfed') {
        cancelRender(new Error(UNFED_TEXT_TAG + JSON.stringify({unfed: auditUnfedText(body, fed ?? [], scope)})));
        return;
      }
```
and add `scope` to the effect's dependency list (`[enabled, handle, mode, fed, scope]`).

- [ ] **Step 4: Wire it for every standalone composition** — in `remotion/src/Root.tsx`, `DnaPreview`, replace the three lines that compute `_p`, `mode` and `audit` with:
```tsx
  const _p = p as {textSafe?: unknown; typeCollisions?: unknown; fedText?: unknown; unfedText?: unknown;
    unfedScope?: unknown};
  // `unfedText` asks a FOURTH question: which words on the frame did no prop supply? (runtime/textSafe
  // auditUnfedText — the content contract for a film's built things, asked by scripts/shot_proof.py.)
  const mode = _p.unfedText ? 'unfed' as const : _p.fedText ? 'fed' as const
    : _p.typeCollisions ? 'collisions' as const : 'safe' as const;
  const audit = <TextSafeAudit enabled={Boolean(_p.textSafe || _p.typeCollisions || _p.fedText || _p.unfedText)}
                               mode={mode}
                               fed={Array.isArray(_p.unfedText) ? _p.unfedText : Array.isArray(_p.fedText) ? _p.fedText : []}
                               scope={_p.unfedScope === 'slots' ? 'slots' : 'all'} />;
```
(keep the existing comment about `fedText` above them).

- [ ] **Step 5: shot_proof asks it, and measures a workshop shot's ground claim** — in `scripts/shot_proof.py`:

Below the `_FILM_ENV` block (Task 3) add:
```python
UNFED_TAG = "UNFED-TEXT "      # runtime/textSafe.tsx UNFED_TEXT_TAG — tests/test_unfed_text.py holds them equal


def _string_leaves(v, out=None):
    out = [] if out is None else out
    if isinstance(v, str):
        out.append(v)
    elif isinstance(v, dict):
        for x in v.values():
            _string_leaves(x, out)
    elif isinstance(v, (list, tuple)):
        for x in v:
            _string_leaves(x, out)
    return out


def _unfed_text(shot, payload, frame, proof, beat, out_dir, scope, declared):
    """The words on this beat's frame that no prop supplied — [] clean, None when the render gave no answer.
    `declared` are the words the workshop code names with `// @fixed-text:` (scripts/jsx_words.cjs)."""
    pj = os.path.join(proof, "beat_%02d.unfed.json" % beat)
    fed = [x for x in _string_leaves(payload) if x.strip()] + list(declared or [])
    with open(pj, "w", encoding="utf-8") as fh:
        json.dump(dict(payload, unfedText=fed, unfedScope=scope), fh, ensure_ascii=False)
    png = os.path.join(proof, "beat_%02d.unfed.png" % beat)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, png, "--frame=%d" % frame, "--gl=angle",
                        "--props=" + pj, "--log=error", "--public-dir=" + os.path.abspath(out_dir)],
                       cwd=_REMOTION, capture_output=True, text=True, **_FILM_ENV)
    for f in (pj, png):
        if os.path.exists(f):
            os.remove(f)
    blob = (r.stdout or "") + (r.stderr or "")
    if UNFED_TAG not in blob:
        return None
    try:
        return (json.JSONDecoder().raw_decode(blob.split(UNFED_TAG, 1)[1])[0] or {}).get("unfed") or []
    except json.JSONDecodeError:
        return None


def _band_luminance(png):
    """Median relative luminance of the caption band — the ground the burned caption is inked for."""
    try:
        from PIL import Image
        import numpy as np
        from _caption_band import caption_band_px
    except ImportError:
        return None
    im = Image.open(png).convert("RGB")
    band = int(caption_band_px(im.width, im.height))
    a = np.asarray(im.crop((0, im.height - band, im.width, im.height)), dtype=float) / 255.0
    lin = np.where(a <= 0.03928, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    return float(np.median(y))


def _ground_claim(png, shot, out_dir, board):
    """A film-local shot DECLARES the ground its caption is inked for (workshop GROUND); the library's registers
    are measured instead. Compare the claim with the caption band actually rendered. A gap past the seam guard's
    own flash threshold means the burned caption would be inked for a ground that is not there."""
    import workshop as _ws
    import seam_plan
    g = _ws.grounds(out_dir).get(shot)
    if g is None:
        return None
    dna = seam_plan._resolve_dna((board.get("meta") or {}).get("design_dna"))
    if isinstance(g, str) and g.startswith("#"):
        claim = seam_plan._rel_lum(g)
    else:
        toks = [g] if isinstance(g, str) else g
        ys = [seam_plan._rel_lum((dna or {}).get(t)) for t in toks]
        claim = None if not dna or any(y is None for y in ys) else sum(ys) / len(ys)
    measured = _band_luminance(png)
    if claim is None or measured is None:
        return None
    if abs(claim ** (1 / 2.2) - measured ** (1 / 2.2)) > seam_plan.HARSH_GAP:
        return ("declares GROUND %r (luminance %.2f under this film's DNA) but its caption band renders at %.2f — "
                "the burned caption would be inked for a ground that is not there; set GROUND to what the shot "
                "really paints" % (g, claim, measured))
    return None
```

In `main`, next to the `_FILM_SHOTS` lines (Task 3), add:
```python
    _film_shots = _ws.shot_names(out_dir)
    _declared = (_ws.baked_words(out_dir, _ws.source_files(out_dir))["declared"]
                 if _film_shots or _ws.object_names(out_dir) else [])
```
and in the per-beat loop, directly after `rendered += 1`, add:
```python
            # BUILT THINGS TAKE EVERY WORD FROM THE FILM — asked of the frame. On a film-local register every run
            # is asked; on a library register holding an object, only what is inside the object's slot. One more
            # render, only on beats that show a built thing.
            _held = [ref for _p, ref in _ws.object_refs(_ws.shot_source(out_dir, shot), s.get("shot_props") or {})
                     if isinstance(ref, dict)]
            if shot in _film_shots or _held:
                unfed = _unfed_text(shot, payload, frame, proof, beat, out_dir,
                                    "all" if shot in _film_shots else "slots", _declared)
                if unfed is None:
                    unmeasured.append("beat %d (%s): the words-from-props check gave no answer — its render "
                                      "failed or carried no payload" % (beat, shot))
                elif unfed:
                    errors.append("beat %d (%s): text on the frame that no prop supplied: %s — a built thing "
                                  "takes every word from the film's props (pass it in; a word that is part of "
                                  "the form is declared `// @fixed-text: <why>` in the workshop code)"
                                  % (beat, shot, " / ".join(repr(u) for u in unfed[:6])))
            if shot in _film_shots:
                _gc = _ground_claim(png, shot, out_dir, board)
                if _gc:
                    errors.append("beat %d (%s): %s" % (beat, shot, _gc))
```

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest tests/test_unfed_text.py tests/test_text_safe_qa.py tests/test_cjk_type_qa.py -q`
Expected: PASS (the existing `fed`/`safe`/`collisions` audits unchanged — including the rotation-guard mutation test, whose anchor `selfRotated` is untouched).

- [ ] **Step 7: Commit**

```bash
git add remotion/src/runtime/textSafe.tsx remotion/src/Root.tsx scripts/shot_proof.py tests/test_unfed_text.py
git commit -m "Words only from props, asked of the frame: an unfed-text audit, and a workshop shot's ground claim measured against its caption band

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---
### Task 6: A device's screen can show something the film drew

**Files:**
- Modify: `remotion/src/shots/DeviceDemo.tsx`, `remotion/src/shots/DeviceHero.tsx`, `scripts/device_script.py` (`check_shape`, `_hero_screen_problems`), `remotion/cards/DeviceDemo.md`, `remotion/cards/DeviceHero.md`, `remotion/LIBRARY.md` (entries 210, 211)
- Modify (by the measurement scripts): `remotion/register_energy.json`, `remotion/prop_reach.json`, `remotion/_ground_luma.json`, `remotion/_ground_reach.json`
- Test: `tests/test_device_object_screen.py`, `tests/test_slot_identity.py`

**Interfaces:**
- Consumes: `ObjectSlot`, `ObjectRef` (Task 1); `workshop.write_index`, `workshop_dir` (Task 2); `_index`, `_env`, `_still` (tests/test_workshop_bundle.py).
- Produces: a DeviceDemo `screen` step and DeviceHero's `screen` accept `{"object": ObjectRef}`; `tests/test_slot_identity.py` with `BEFORE = "90df454"`, `SLOTTED`, `CASES` (Task 7 extends both).

- [ ] **Step 1: Write the failing tests** — `tests/test_device_object_screen.py`:

```python
"""A device's screen can show something the FILM drew — an interface that does not exist yet, a scene — through
the object slot. Its taps land on coordinates; what needs a screenshot (a text target, typing, scrolling) is
refused by name, because there is no screenshot to find text in or to scroll."""
import os
import sys

import numpy as np
import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import device_script as ds  # noqa: E402
import workshop as ws  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

PHONE_UI = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {provenance: 'product-ui'};
export const %(name)s: React.FC<ObjectProps> = ({w, h}) => (
  <div style={{width: w, height: h, background: '#ff00ff'}} />
);
"""
SCREEN = {"object": {"id": "WsPhoneUi"}}


def test_an_object_screen_is_a_screen():
    props = {"device": "phone", "steps": [{"screen": SCREEN}, {"tap": [0.5, 0.5]},
                                          {"drag": {"from": [0.2, 0.8], "to": [0.2, 0.3]}}]}
    assert ds.check_shape(props) == []
    assert ds._hero_screen_problems({"screen": SCREEN}) == []


@pytest.mark.parametrize("steps,expect", [
    ([{"screen": {"object": "WsPhoneUi"}}], "a screen's object is {\"id\""),
    ([{"screen": SCREEN}, {"type": "你好", "into": [0.5, 0.2]}], "animate the typing inside the object"),
    ([{"screen": SCREEN}, {"scroll": 0.5}], "animate the scroll inside the object"),
    ([{"screen": SCREEN}, {"tap": {"text": "发送"}}], "on a film-drawn screen, target [x, y]"),
    ([{"screen": {"image": "a.png", "object": {"id": "WsPhoneUi"}}}], "exactly one of image / video / object / page"),
])
def test_what_an_object_screen_cannot_do_is_refused_by_name(steps, expect):
    probs = ds.check_shape({"device": "phone", "steps": steps})
    assert any(expect in p for p in probs), probs


def test_a_hero_object_screen_is_refused_when_malformed_and_passes_through_prepare(tmp_path):
    assert ds._hero_screen_problems({"screen": {"object": {"props": {}}}})
    out, warns = ds.prepare({"device": "laptop", "screen": {"object": {"id": "WsPhoneUi", "props": {"tone": 1}}}},
                            shot="DeviceHero", out_dir=str(tmp_path), dur_frames=150, fps=30, W=1920, H=1080,
                            lang="zh")
    assert out["screen"] == {"object": {"id": "WsPhoneUi", "props": {"tone": 1}}} and warns == []


def test_a_demo_object_screen_is_scheduled_and_the_camera_holds(tmp_path):
    props = {"device": "phone", "steps": [{"screen": SCREEN}, {"tap": [0.5, 0.5], "at": 0.5}]}
    out, _w = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=30, W=1920, H=1080,
                         lang="zh")
    assert all({"t0", "ta", "t1"} <= set(st) for st in out["steps"])
    assert "focus" not in out["steps"][1]              # nothing to measure a push-in against


def test_validate_names_an_unknown_object_on_a_device_screen(tmp_path):
    import validate as v
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "DeviceHero", "narration": "这就是它。", "audio": "audio/01.mp3",
                         "duration": 3.0, "shot_props": {"device": "laptop", "screen": {"object": {"id": "NoSuchUi"}}}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    assert any("names object 'NoSuchUi'" in e for e in errs), errs


@needs_toolchain
def test_a_film_drawn_screen_shows_on_the_phone_and_on_the_laptop(tmp_path):
    out = tmp_path / "film"
    d = out / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "WsPhoneUi.tsx").write_text(PHONE_UI % {"name": "WsPhoneUi"}, encoding="utf-8")
    ws.write_index(str(out))
    env = _env(ws.workshop_dir(str(out)))
    demo, _w = ds.prepare({"device": "phone", "steps": [{"screen": SCREEN}, {"tap": [0.5, 0.5]}]}, shot="DeviceDemo",
                          out_dir=str(out), dur_frames=180, fps=30, W=1920, H=1080, lang="zh")
    for comp, props, frame in (("DeviceDemo", demo, 150),
                               ("DeviceHero", {"device": "laptop", "screen": SCREEN}, 130)):
        png = tmp_path / (comp + ".png")
        r = _still(comp, png, dict(props, dna="product"), env, frame=frame)
        assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
        a = np.asarray(Image.open(str(png)).convert("RGB")).astype(int)
        magenta = int(((a[..., 0] > 200) & (a[..., 1] < 60) & (a[..., 2] > 200)).sum())
        assert magenta > a.shape[0] * a.shape[1] * 0.03, (comp, magenta)
```

And `tests/test_slot_identity.py`:

```python
"""A REGISTER THAT GAINED AN OBJECT SLOT DRAWS EXACTLY WHAT IT DREW BEFORE WHEN THE SLOT IS EMPTY.

The reference is the register's own source at the commit before any slot existed (BEFORE), rendered as a
film-local shot beside the current register — one bundle, the same props, the same frames — so the comparison is
exact on any machine and needs no stored pictures. Every pixel must match, at a moving frame and at the settled
one, at 16:9 and 9:16, for the register's standalone preview and for a film-like prop set."""
import json
import os
import re
import subprocess
import sys

import pytest
from PIL import Image, ImageChops, ImageDraw, ImageFont

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_workshop_bundle import _index, _env  # noqa: E402

BEFORE = "90df454"                       # the spec's commit: every register below, as it was before any slot
FONT = os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf")


def _before_source(name):
    r = subprocess.run(["git", "-C", _ROOT, "show", "%s:remotion/src/shots/%s.tsx" % (BEFORE, name)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip("the reference commit %s is not in this checkout (a git-archive copy has no history)" % BEFORE)
    src = r.stdout.replace("from '../runtime/", "from '@runtime/")
    src = re.sub(r"from '\./(\w+)'", r"from '@shots/\1'", src)
    src = re.sub(r"\bexport const %s\b" % name, "export const %sBefore" % name, src)
    src = re.sub(r"^export default %s;\s*$" % name, "", src, flags=re.M)
    return src + "\nexport const GROUND = 'bg';\n"


def _screenshot(path, h):
    im = Image.new("RGB", (1170, h), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 46)
    d.rounded_rectangle([60, 200, 1110, 320], radius=36, fill=(238, 241, 244))
    for i in range(max(1, (h - 500) // 180)):
        d.text((90, 420 + i * 180), "第%d条反馈" % (i + 1), fill=(20, 23, 28), font=f)
    im.save(path)


def _duration(name):
    src = open(os.path.join(_REM, "src", "shots", name + ".tsx"), encoding="utf-8").read()
    return int(re.search(r"export const DURATION\s*=\s*(\d+)", src).group(1))


def _prepared(shot, aspect, public):
    import device_script as ds
    W, H = {"16:9": (1920, 1080), "9:16": (1080, 1920)}[aspect]
    if shot == "DeviceDemo":
        props = {"device": "phone", "steps": [{"screen": {"image": "ui_long.png"}}, {"tap": [0.5, 0.2]}, {"scroll": 0.5}]}
    else:
        props = {"device": "phone", "screen": {"image": "ui.png"}}
    out, _w = ds.prepare(props, shot=shot, out_dir=public, dur_frames=_duration(shot), fps=30, W=W, H=H, lang="zh")
    return out


# {register: [(label, make_props(aspect, public_dir))]} — its standalone preview and a film-like set, slot unset
CASES = {
    "DeviceDemo": [("demo", lambda a, pub: {}), ("film", lambda a, pub: _prepared("DeviceDemo", a, pub))],
    "DeviceHero": [("demo", lambda a, pub: {}), ("film", lambda a, pub: _prepared("DeviceHero", a, pub))],
}
SLOTTED = sorted(CASES)


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    if not os.path.isdir(os.path.join(_REM, "node_modules")):
        pytest.skip("needs the remotion toolchain")
    root = tmp_path_factory.mktemp("identity")
    shots = root / "workshop" / "shots"
    shots.mkdir(parents=True)
    for n in SLOTTED:
        (shots / (n + "Before.tsx")).write_text(_before_source(n), encoding="utf-8")
    (root / "workshop" / "index.ts").write_text(_index(sorted(n + "Before" for n in SLOTTED), []), encoding="utf-8")
    pub = root / "public"
    pub.mkdir()
    _screenshot(str(pub / "ui.png"), 2532)
    _screenshot(str(pub / "ui_long.png"), 6000)
    out = root / "bundle"
    r = subprocess.run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + str(out), "--public-dir=" + str(pub),
                        "--log=error"], cwd=_REM, env=_env(root / "workshop"), capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    return {"bundle": str(out), "root": root, "public": str(pub)}


def _render(b, comp, props, frame, name):
    pf = b["root"] / (name + ".json")
    pf.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    png = str(b["root"] / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", b["bundle"], comp, png, "--frame=%d" % frame, "--gl=angle",
                        "--log=error", "--props=" + str(pf)], cwd=_REM, env=_env(), capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, (comp, (r.stdout + r.stderr)[-600:])
    return png


def _frames(name):
    import render_remotion as rr
    d = _duration(name)
    return [("mid", int(d * 0.4), ("16:9",)),
            ("settled", int(round(rr.frame_at_t(d, rr.SETTLED_T))), ("16:9", "9:16"))]


@pytest.mark.parametrize("name", SLOTTED)
def test_an_empty_slot_draws_exactly_what_the_register_drew_before(bundle, name):
    diffs = []
    for label, make in CASES[name]:
        for when, frame, aspects in _frames(name):
            for aspect in aspects:
                props = dict(make(aspect, bundle["public"]), dna="product", aspect=aspect)
                tag = "%s-%s-%s-%s" % (name, label, when, aspect.replace(":", "x"))
                now = Image.open(_render(bundle, name, props, frame, tag + "-now")).convert("RGB")
                was = Image.open(_render(bundle, name + "Before", props, frame, tag + "-before")).convert("RGB")
                box = ImageChops.difference(now, was).getbbox()
                if box:
                    diffs.append((tag, box))
    assert not diffs, "with its slot empty the register no longer draws what it drew before: %r" % diffs
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_device_object_screen.py tests/test_slot_identity.py -q`
Expected: the object-screen tests FAIL (`a screen is exactly one of image / video / page`); the identity tests PASS already (nothing has changed yet — this is the baseline they hold).

- [ ] **Step 3: The step script accepts an object screen** — in `scripts/device_script.py`:

Replace `_hero_screen_problems`'s body after `if isinstance(src, dict) and "page" in src: return [...]` with:
```python
    keys = [k for k in ("image", "video", "object") if isinstance(src, dict) and k in src]
    if len(keys) != 1:
        return ["`screen` is exactly one of image / video / object (got %r)" % (src,)]
    if keys[0] == "object":
        o = src["object"]
        if not isinstance(o, dict) or not isinstance(o.get("id"), str) or not o["id"].strip():
            return ['`screen` object is {"id": "<Name>", "props": {...}} — a screen the film drew (got %r)' % (o,)]
        return []
    if not isinstance(src[keys[0]], str) or not src[keys[0]].strip():
        return ["`screen` %s is a file path in the out dir (got %r)" % (keys[0], src[keys[0]])]
    return []
```
and change its first message to `"DeviceHero needs `screen` — a screenshot (`image`), a recording (`video`) or a screen the film drew (`object`)"`.

In `check_shape`, next to `on_video = False` add `on_object = False`. In the `if k == "screen":` branch replace the source detection and its first two checks with:
```python
            src = st["screen"]
            srcs = [s for s in ("image", "video", "page", "object") if isinstance(src, dict) and s in src]
            if len(srcs) != 1:
                probs.append("%s: a screen is exactly one of image / video / object / page (got %r)" % (where, src))
                continue
            on_video = srcs[0] == "video"
            on_object = srcs[0] == "object"
            if srcs[0] == "page":
                probs.append("%s: page %r is the register's own preview, never a film's — give an image or a video"
                             % (where, src.get("page")))
            elif on_object:
                o = src["object"]
                if not isinstance(o, dict) or not isinstance(o.get("id"), str) or not o["id"].strip():
                    probs.append('%s: a screen\'s object is {"id": "<Name>", "props": {...}} (got %r)' % (where, o))
            elif not isinstance(src[srcs[0]], str) or not src[srcs[0]].strip():
                probs.append("%s: a screen's %s is a file path in the out dir (got %r)" % (where, srcs[0], src[srcs[0]]))
```
(keep the `via` and recording checks that follow). Then, directly after the `elif on_video and k in (...)` branch, add:
```python
        elif on_object and k in ("type", "scroll"):
            # A SCREEN THE FILM DREW animates itself: its typing and its scrolling are the object's own motion,
            # from its `t`. There is no field to measure and no long screenshot to scroll.
            probs.append("%s (%s): the screen is drawn by the film (an object) — animate the %s inside the object "
                         "from its `t`, or show a screenshot" % (where, k, "typing" if k == "type" else "scroll"))
        elif on_object and any(isinstance(v, dict) and "text" in v for v in
                               ([st.get(k)] + ([st[k].get("from"), st[k].get("to")]
                                               if k == "drag" and isinstance(st.get(k), dict) else []))):
            probs.append("%s (%s): a text target needs a screenshot to find the text in — on a film-drawn screen, "
                         "target [x, y]" % (where, k))
```

- [ ] **Step 4: The registers draw it** — `remotion/src/shots/DeviceDemo.tsx`: add `import {ObjectSlot, type ObjectRef} from '../runtime/objectSlot';` after the `../runtime/gesture` import; change `type ScreenSrc` to `type ScreenSrc = {image?: string; video?: string; page?: 'demo'; object?: ObjectRef; from?: number; to?: number};`; and in `layer`, directly after `const src = x.st.screen!;`, add:
```tsx
    // A SCREEN THE FILM DREW (runtime/objectSlot): an interface or a scene built for this beat, drawn at the
    // screen's own size on the beat's clock. Its taps target coordinates — scripts/device_script.py refuses a
    // text target, typing and scrolling on it, since there is no screenshot to find text in or to scroll.
    if (src.object) return <ObjectSlot object={src.object} box={{x: 0, y: 0, w: s.w, h: s.h}} />;
```

`remotion/src/shots/DeviceHero.tsx`: add the same import after the `../runtime/screen` import; change `type HeroScreen` to add `object?: ObjectRef`; change the `demo` line and the refusal to:
```tsx
  const demo = !SCREEN.image && !SCREEN.video && !SCREEN.object && SCREEN.page === 'demo';
  if (!demo && !SCREEN.image && !SCREEN.video && !SCREEN.object) {
    throw new Error("DeviceHero: `screen` needs an image, a recording, an object, or page 'demo' — got " +
      JSON.stringify(SCREEN) + '. A screen with none of them used to draw the demo skeleton, as if the film had asked for it.');
  }
```
and replace the whole `const content = …;` statement with (the object is the first case; the other three are
the existing ones, character for character):
```tsx
  const content = SCREEN.object
    ? <ObjectSlot object={SCREEN.object} box={{x: 0, y: 0, w: s.w, h: s.h}} />
    : SCREEN.image
      ? <ScreenImage src={SCREEN.image} imageW={SCREEN.imageW!} imageH={SCREEN.imageH!} w={s.w} h={s.h} />
      : SCREEN.video
        ? <ScreenVideo src={SCREEN.video} spans={SCREEN.spans!} w={s.w} h={s.h} />
        : (
          <div style={{position: 'absolute', left: 0, top: 0, width: s.w, height: s.h, background: dna?.surface ?? '#ffffff'}}>
            {Array.from({length: 6}).map((_, i) => (   // @decor: skeleton rows of the register's own demo screen — no film ever sees them
              <div key={i} style={{position: 'absolute', left: s.w * 0.08, top: s.h * (0.14 + i * 0.12), width: s.w * 0.84,
                height: s.h * 0.07, borderRadius: s.h * 0.012, background: mix(dna?.surface ?? '#ffffff', dna?.fg ?? '#14171c', 0.07)}} />
            ))}
          </div>
        );
```

- [ ] **Step 5: The cards and the catalogue say so** —
`remotion/cards/DeviceDemo.md`: in the `steps` row, change "the script — `screen`, …" to "the script — `screen` (a screenshot, a recording, or `{\"object\": …}`: a screen the film drew), `type`, `tap`/`click`, `scroll`, `drag`, `mark` — prepared by `scripts/device_script.py`"; add a Known trap: `- A screen the film drew (an \`object\` from its workshop) is tapped and dragged by coordinates only: there is no screenshot to find text in, and typing or scrolling on it is the object's own animation — both are refused by name. The camera holds on it: there is no text height to push in to.`
`remotion/cards/DeviceHero.md`: in the `screen` row add "or `{\"object\": {\"id\": …}}` — a screen the film drew (scripts/workshop.py)"; change the Known trap "A film's hero must name its `screen` — a screenshot or a recording" to "— a screenshot, a recording, or a screen the film drew".
`remotion/LIBRARY.md`: in entry 210 (DeviceDemo) change "showing the product's OWN screenshots or recording" to "showing the product's OWN screenshots or recording — or a screen the film drew"; in entry 211 (DeviceHero) change "with its own screenshot or recording shown whole" to "with its own screenshot, recording, or a screen the film drew shown whole".

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest tests/test_device_object_screen.py tests/test_slot_identity.py tests/test_device_demo.py tests/test_device_hero.py tests/test_device_wiring.py tests/test_device_script.py tests/test_shot_cards.py tests/test_library_signatures.py -q`
Expected: PASS — including both identity cases: with no object on the screen, both device registers draw exactly what they drew at `90df454`.

- [ ] **Step 7: Re-measure the two registers** (their source hash now includes `runtime/objectSlot.tsx`; nothing else may be editing registers or sweeping)

Run:
```bash
python3 scripts/measure_ground_reach.py --only DeviceDemo,DeviceHero --emit
python3 scripts/measure_ground_luma.py --only DeviceDemo,DeviceHero --luma --emit
python3 scripts/measure_ground_luma.py --only DeviceDemo,DeviceHero --emit
python3 scripts/register_energy.py --only DeviceDemo,DeviceHero
python3 scripts/prop_reach.py --only DeviceDemo,DeviceHero
python3 scripts/measure_ground_reach.py --stale
git diff --stat remotion/ && git diff remotion/register_energy.json remotion/prop_reach.json | grep '^[-+]' | grep -v '"_source\|hash' | head -20
```
Expected: `--stale` lists nothing; `remotion/src/runtime/shotLuma.ts` is unchanged (the grounds are the same); in the manifests only the source hashes changed. **A changed measured value means the picture changed** — stop, look at the two renders, and find why before going on.

- [ ] **Step 8: Commit**

```bash
git add remotion/src/shots/DeviceDemo.tsx remotion/src/shots/DeviceHero.tsx scripts/device_script.py remotion/cards/DeviceDemo.md remotion/cards/DeviceHero.md remotion/LIBRARY.md remotion/register_energy.json remotion/prop_reach.json remotion/_ground_luma.json remotion/_ground_reach.json tests/test_device_object_screen.py tests/test_slot_identity.py
git commit -m "Device screens can show a screen the film drew; with none, both device registers draw exactly what they drew before

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```
(Stage only the manifests Step 7 actually changed.)

---
### Task 7: TechnicalPlate and HudReticle hold objects

**Files:**
- Modify: `remotion/src/shots/TechnicalPlate.tsx` (`art`), `remotion/src/shots/HudReticle.tsx` (`object`), `remotion/cards/TechnicalPlate.md`, `remotion/cards/HudReticle.md`, `remotion/LIBRARY.md` (entries 65 and 169), `tests/test_slot_identity.py` (two more cases), `scripts/cjk_type_qa.py` (`cjk_props`: an object slot is not copy)
- Modify (by the measurement scripts): `remotion/register_energy.json`, `remotion/prop_reach.json`, `remotion/_ground_luma.json`, `remotion/_ground_reach.json`
- Test: `tests/test_slotted_registers.py`

**Interfaces:**
- Consumes: `ObjectSlot`, `ObjectRef` (Task 1); `workshop.write_index`, `workshop_dir` (Task 2); `text_safe_qa.audit_shot(..., env=)` (Task 3); `CASES`/`SLOTTED` in `tests/test_slot_identity.py` (Task 6).
- Produces: `TechnicalPlate` prop `art?: ObjectRef` (the object gets `t` = the plate's drawing phase, 0.14–0.62); `HudReticle` prop `object?: ObjectRef` (the object gets `t` over 0.1–0.6, the name moves under it).

- [ ] **Step 1: Write the failing tests** — `tests/test_slotted_registers.py`:

```python
"""TechnicalPlate draws a film's own drawing in place of strokes (`art`); HudReticle locks onto a film's object
(`object`). Each keeps its own words where they were and its type inside the frame at every aspect."""
import os
import sys

import numpy as np
import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
import text_safe_qa as g  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

ART = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'survey-archive'};
export const %(name)s: React.FC<ObjectProps> = ({w, h, t}) => (
  <div style={{width: w, height: h, background: '#ff00ff', opacity: t}} />
);
"""
PARTS = [{"n": 1, "label": "压粉面", "x": 0.3, "y": 0.4, "side": "left"},
         {"n": 2, "label": "手柄", "x": 0.8, "y": 0.6, "side": "right"}]


@pytest.fixture(scope="module")
def film(tmp_path_factory):
    out = tmp_path_factory.mktemp("slotted") / "film"
    d = out / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "WsArt.tsx").write_text(ART % {"name": "WsArt"}, encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


def _magenta(png):
    a = np.asarray(Image.open(str(png)).convert("RGB")).astype(int)
    m = (a[..., 0] > 200) & (a[..., 1] < 60) & (a[..., 2] > 200)
    ys, xs = np.nonzero(m)
    return int(m.sum()), (xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None


@needs_toolchain
@pytest.mark.parametrize("aspect", ["16:9", "9:16"])
def test_the_plate_draws_the_film_s_art_with_its_callouts_on_it(film, tmp_path, aspect):
    props = {"art": {"id": "WsArt"}, "parts": PARTS, "object": "压粉器", "kicker": "图版", "dna": "product",
             "aspect": aspect}
    r = _still("TechnicalPlate", tmp_path / "p.png", props, _env(ws.workshop_dir(film)), frame=140)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    n, box = _magenta(tmp_path / "p.png")
    assert n > 40000 and box, (n, box)
    assert abs((box[2] - box[0]) - (box[3] - box[1])) <= 4, box          # the art keeps its square
    found = g.audit_shot("TechnicalPlate", props, 140, str(tmp_path / "a.png"), env=_env(ws.workshop_dir(film)))
    assert found == [], found


@needs_toolchain
def test_the_plate_refuses_art_and_strokes_together_and_art_without_parts(film, tmp_path):
    env = _env(ws.workshop_dir(film))
    both = _still("TechnicalPlate", tmp_path / "b.png", {"art": {"id": "WsArt"}, "parts": PARTS,
                  "strokes": [{"kind": "circle", "x": 0.5, "y": 0.5, "r": 0.2}]}, env)
    assert both.returncode != 0 and "both `art` and `strokes`" in both.stdout + both.stderr
    bare = _still("TechnicalPlate", tmp_path / "c.png", {"art": {"id": "WsArt"}}, env)
    assert bare.returncode != 0 and "`art` but no `parts`" in bare.stdout + bare.stderr


@needs_toolchain
@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1"])
def test_the_reticle_locks_onto_the_film_s_object_and_keeps_its_name_in_the_ring(film, tmp_path, aspect):
    props = {"object": {"id": "WsArt"}, "target": "咖啡机的冲煮头", "readouts": ["水温 · 稳定", "压力 · 上升"],
             "title": "锁定", "scanLabel": "扫描中", "lockLabel": "● 已锁定", "dna": "product", "aspect": aspect}
    r = _still("HudReticle", tmp_path / "h.png", props, _env(ws.workshop_dir(film)), frame=135)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    n, box = _magenta(tmp_path / "h.png")
    assert n > 20000 and box, (n, box)
    found = g.audit_shot("HudReticle", props, 135, str(tmp_path / "a.png"), env=_env(ws.workshop_dir(film)))
    assert found == [], found


def test_the_cjk_fixture_leaves_an_object_slot_to_the_register_s_preview():
    """An ObjectRef prop is not copy: the library sweeps (cjk_type_qa, prop_reach) feed a register Chinese words, and a
    slot left unset shows the register's own picture. Filed as untestable it would read as a coverage hole — exit 2 —
    on every register that can hold an object."""
    import cjk_type_qa as c
    for name, slot in (("TechnicalPlate", "art"), ("HudReticle", "object")):
        props, untestable = c.cjk_props(name)
        assert slot not in props and slot not in untestable, (name, props, untestable)


def test_validate_names_an_unknown_art_object(tmp_path):
    import validate as v
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "TechnicalPlate", "narration": "这是它。", "audio": "audio/01.mp3",
                         "duration": 3.0, "shot_props": {"art": {"id": "NoSuchArt"}, "parts": [], "object": "它"}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    assert any("TechnicalPlate.art names object 'NoSuchArt'" in e for e in errs), errs
```

In `tests/test_slot_identity.py`, add the two registers to `CASES` (standalone preview and a film-like set, slot unset):
```python
    "TechnicalPlate": [("demo", lambda a, pub: {}),
                       ("film", lambda a, pub: {"kicker": "图版", "object": "咖啡压粉器", "plateNo": "图 3",
                                                "strokes": [{"kind": "circle", "x": 0.5, "y": 0.45, "r": 0.25},
                                                            {"kind": "bar", "x": 0.3, "y": 0.72, "w": 0.4, "h": 0.05, "fill": True},
                                                            {"kind": "line", "x": 0.5, "y": 0.2, "x2": 0.5, "y2": 0.05}],
                                                "parts": [{"n": 1, "label": "压粉面", "x": 0.5, "y": 0.45},
                                                          {"n": 2, "label": "底座", "x": 0.5, "y": 0.74, "side": "left"}],
                                                "note": "它把粉压实"})],
    "HudReticle": [("demo", lambda a, pub: {}),
                   ("film", lambda a, pub: {"target": "冲煮头", "readouts": ["水温 · 稳定", "压力 · 上升", "流速 · 均匀"],
                                            "title": "锁定", "scanLabel": "扫描中", "lockLabel": "● 已锁定"})],
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_slotted_registers.py tests/test_slot_identity.py -q`
Expected: the slotted-register tests FAIL (`art` and `object` are not props yet); the four identity cases PASS (the baseline).

Record the CJK baseline of the two registers before touching them (Step 7 compares against it):
```bash
python3 scripts/cjk_type_qa.py --only TechnicalPlate --all-aspects > .superpowers/regression/cjk_TechnicalPlate_before.txt; echo "exit $?"
python3 scripts/cjk_type_qa.py --only HudReticle --all-aspects > .superpowers/regression/cjk_HudReticle_before.txt; echo "exit $?"
```

- [ ] **Step 3: The CJK fixture knows an object slot is not copy** — in `scripts/cjk_type_qa.py`, `cjk_props`, directly after the `if prop in ("accent", "accent2", …) or re.match(r"^src[A-Z]?", prop): … continue` block, add:
```python
        if re.fullmatch(r"ObjectRef(\|undefined|\|null)?", t):
            # AN OBJECT SLOT IS NOT COPY. It names a thing a film drew (runtime/objectSlot); left unset the register
            # shows its own picture, which is what a library sweep measures. Filed untestable it read as a coverage
            # hole on every register that can hold an object — and no register had one until now, so no existing
            # fixture changes.
            continue
```
(A nested ObjectRef — a device screen's `object`, a row's field — is already omitted by `_synth_field`'s named-type rule.)

- [ ] **Step 3b: TechnicalPlate takes `art`** — in `remotion/src/shots/TechnicalPlate.tsx`:

1. After `import {useDNA} from '../runtime/dna';` add `import {ObjectSlot, type ObjectRef} from '../runtime/objectSlot';`.
2. In the props type add, after `strokes?: Stroke[];       // the object, in unit space`:
```tsx
  art?: ObjectRef;          // a drawing the FILM made (runtime/objectSlot), in place of `strokes`
```
and in the destructuring add `art,` after `parts: PARTS = BIKE_PARTS,`.
3. Replace the `if (demoStrokes !== demoParts) { … }` block with:
```tsx
  if (art) {
    // A DRAWING THE FILM MADE takes the strokes' place — and is still ONE claim with its callouts.
    if (!demoStrokes) {
      throw new Error("TechnicalPlate got both `art` and `strokes` — one drawing per plate: the film's own " +
        '(`art`, from its workshop) or strokes, not both.');
    }
    if (demoParts) {
      throw new Error("TechnicalPlate got `art` but no `parts`, so it would pin the demo callouts to the film's " +
        'drawing. Pass `parts: [{n, label, x, y, side}]` at points on the art (0..1 of its square), or `parts: []`.');
    }
  } else if (demoStrokes !== demoParts) {
    throw new Error(demoStrokes
      ? 'TechnicalPlate got `parts` but no `strokes`, so it would number the film\'s parts on its demo BICYCLE. ' +
        'Pass `strokes` that draw the object those parts belong to (circle / line / bar in unit space), or cast ' +
        'a register that does not need a drawing.'
      : 'TechnicalPlate got `strokes` but no `parts`, so it would pin the demo callouts ("the part that does the ' +
        'work") to the demo bicycle\'s coordinates on top of the film\'s object. Pass `parts: [{n, label, x, y, ' +
        'side}]` naming the film\'s own parts, or `parts: []` for an unannotated drawing.');
  }
```
4. Replace the opening of the stroke drawing, `{STROKES.map((st, i) => {`, with `{art ? <ObjectSlot object={art} box={{x: ox, y: oy, w: unit, h: unit}} t={draw} /> : STROKES.map((st, i) => {` and its closing `})}` with `})}` unchanged — i.e. the map becomes the ternary's second branch (the object is drawn in the same square field, on the plate's own drawing phase `draw`).

- [ ] **Step 4: HudReticle locks onto `object`** — in `remotion/src/shots/HudReticle.tsx`:

1. After `import {CONTENT_TOP, contentBottom, fitBlockPx, fitTextPx, textWidthPx, wrapLines} from '../runtime/layout';` add `import {ObjectSlot, type ObjectRef} from '../runtime/objectSlot';`.
2. Change the component's props type to add `object?: ObjectRef` (`{target?: string; readouts?: string[]; title?: string; scanLabel?: string; lockLabel?: string; object?: ObjectRef}`) and add `object: OBJECT,` to the destructuring (no default).
3. After the `targetPx` line add:
```tsx
  // WITH AN OBJECT the reticle locks onto a THING the film drew (runtime/objectSlot): it sits in the upper part of
  // the inner ring and the name moves under it, smaller, still inside the ring (every corner of the box is within
  // 0.97 of the inner radius; the name's block ends by 0.7 of it). The object's clock is the lock-on window,
  // 0.1–0.6, so it is whole before the lock at 0.76.
  const objSide = innerR * 1.1;
  const objBox = {x: cx - objSide / 2, y: cy - innerR * 0.8, w: objSide, h: objSide};
  const nameW = Math.round(innerR * 1.3);
  const namePx = fitBlockPx(TARGET, nameW, innerR * 0.22, Math.round(40 * s), {usable: 1, leading: targetLead});
```
4. Replace the `{/* central subject */}` element (the `<div style={{position: 'absolute', left: cx, top: cy, width: targetW, …}}>…</div>`) with:
```tsx
      {/* central subject — the film's object when it gives one, else its name */}
      {OBJECT ? (
        <>
          <ObjectSlot object={OBJECT} box={objBox} t={clamp01(seg(t, 0.1, 0.6))}
            style={{transform: `scale(${lerp(0.9, 1, brackets)})`, transformOrigin: '50% 50%'}} />
          <div style={{position: 'absolute', left: cx, top: cy + innerR * 0.36, width: nameW,
            transform: 'translate(-50%, 0)', textAlign: 'center'}}>
            <div style={{color: dna?.fg ?? '#eafffb', font: `800 ${namePx}px/${targetLead} var(--f-display, Inter, system-ui, sans-serif)`,
              letterSpacing: '-0.01em', textWrap: 'balance'}}>{TARGET}</div>
            <div style={{marginTop: Math.round(10 * s), color: col, font: `700 ${Math.round(22 * s)}px/1 var(--f-mono, "JetBrains Mono", monospace)`,
              letterSpacing: '0.3em', opacity: locked ? lockIn : 0.6 * clamp01(seg(t, 0.4, 0.6))}}>{locked ? LOCK_LABEL : SCAN_LABEL}</div>
          </div>
        </>
      ) : (
        <div style={{position: 'absolute', left: cx, top: cy, width: targetW,
          transform: `translate(-50%,-50%) scale(${lerp(0.9, 1, brackets)})`, textAlign: 'center'}}>
          <div style={{color: dna?.fg ?? '#eafffb', font: `800 ${targetPx}px/${targetLead} var(--f-display, Inter, system-ui, sans-serif)`, letterSpacing: '-0.02em',
            textWrap: 'balance', textShadow: emits ? `0 0 40px ${col}66` : undefined}}>{TARGET}</div>
          <div style={{marginTop: Math.round(14 * s), color: col, font: `700 ${Math.round(26 * s)}px/1 var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.3em',
            opacity: locked ? lockIn : 0.6 * clamp01(seg(t, 0.4, 0.6))}}>{locked ? LOCK_LABEL : SCAN_LABEL}</div>
        </div>
      )}
```
(the `: (` branch is the existing element, character for character).

- [ ] **Step 5: Cards and catalogue** —
`remotion/cards/TechnicalPlate.md`: add a table row after `strokes`:
`| \`art\` | a drawing the FILM made (an object from its workshop, \`{"id": …, "props": …}\`), in place of \`strokes\` — drawn in the same square field on the plate's drawing phase (its t runs 0→1 over 0.14–0.62) | the parts' \`x,y\` are fractions of the art's square, so the callouts land on the film's drawing; one drawing per plate |`; add a Known trap `- \`art\` replaces \`strokes\` and still needs \`parts\` (or \`parts: []\`): the demo callouts would otherwise point at the film's drawing. An object is a designed drawing sized to its square — see references/object-authoring.md.`; append to **Refuses:** "; `art` together with `strokes`; `art` without `parts`".
`remotion/cards/HudReticle.md`: add a table row after `target`:
`| \`object\` | a thing the FILM drew (an object from its workshop), locked onto in the ring — the name moves under it, smaller | what is being identified, SHOWN rather than named; its t runs 0→1 over the lock-on window 0.1–0.6 |`; add a Known trap `- With \`object\`, the name is set under the object inside the ring at up to 40px (scaled): a long name wraps, balanced, and stays inside the ring.`
`remotion/LIBRARY.md`: entry 65 (HudReticle) — after "then LOCK (goes green)." add " With `object`, it locks onto a thing the film drew."; entry 169 (TechnicalPlate) — in its prop list change `strokes[],` to `strokes[], art,` and after "each with x and y." add " `art` = a drawing the film made, in place of strokes."

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest tests/test_slotted_registers.py tests/test_slot_identity.py tests/test_shot_cards.py tests/test_library_signatures.py tests/test_text_safe_qa.py tests/test_cjk_type_qa.py -q && python3 scripts/content_contract_qa.py TechnicalPlate HudReticle`
Expected: PASS; with no object both registers draw exactly what they drew at `90df454` (four identity cases now); no contract finding.

- [ ] **Step 7: Re-measure the two registers** (nothing else may be editing registers or sweeping)

Run:
```bash
python3 scripts/measure_ground_reach.py --only TechnicalPlate,HudReticle --emit
python3 scripts/measure_ground_luma.py --only TechnicalPlate,HudReticle --luma --emit
python3 scripts/measure_ground_luma.py --only TechnicalPlate,HudReticle --emit
python3 scripts/register_energy.py --only TechnicalPlate,HudReticle
python3 scripts/prop_reach.py --only TechnicalPlate,HudReticle
python3 scripts/cjk_type_qa.py --only TechnicalPlate --all-aspects > .superpowers/regression/cjk_TechnicalPlate_after.txt; echo "exit $?"
python3 scripts/cjk_type_qa.py --only HudReticle --all-aspects > .superpowers/regression/cjk_HudReticle_after.txt; echo "exit $?"
diff .superpowers/regression/cjk_TechnicalPlate_before.txt .superpowers/regression/cjk_TechnicalPlate_after.txt
diff .superpowers/regression/cjk_HudReticle_before.txt .superpowers/regression/cjk_HudReticle_after.txt
python3 scripts/measure_ground_reach.py --stale
```
Expected: `--stale` lists nothing; `shotLuma.ts` unchanged; only source hashes change in the manifests (a changed measured value means the empty-slot picture changed — stop and look); both `diff`s are empty and the exit codes match the baseline's.

- [ ] **Step 8: Commit**

```bash
git add remotion/src/shots/TechnicalPlate.tsx remotion/src/shots/HudReticle.tsx scripts/cjk_type_qa.py remotion/cards/TechnicalPlate.md remotion/cards/HudReticle.md remotion/LIBRARY.md remotion/register_energy.json remotion/prop_reach.json remotion/_ground_luma.json remotion/_ground_reach.json tests/test_slotted_registers.py tests/test_slot_identity.py
git commit -m "TechnicalPlate draws a film's own art in its field; HudReticle locks onto a film's object; both unchanged with the slot empty

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```
(Stage only the manifests Step 7 changed.)

---
### Task 8: DemoForm and ObjectStage — a thing, shown whole and named

**Files:**
- Create: `remotion/src/objects/DemoForm.tsx`
- Modify: `remotion/src/objects/index.ts` (DemoForm entry), `scripts/content_contract_qa.py` (library objects are scanned), `remotion/LIBRARY.md` (an Objects section)
- Scaffold, then write: `remotion/src/shots/ObjectStage.tsx`, `remotion/cards/ObjectStage.md`
- Modified by the scaffold: `remotion/src/registry.ts`, `remotion/src/Root.tsx`, `remotion/src/runtime/shotLuma.ts`, `scripts/shot_director.py`, `remotion/LIBRARY.md`
- Test: `tests/test_object_stage.py`

**Interfaces:**
- Consumes: `ObjectSlot`, `useObjectEntry`, `fitAspect`, `ObjectRef`, `ObjectProps`, `ObjectMeta` (Task 1); `project`, `yawPoint`, `Vec3` (runtime/project3d); `rows` (runtime/rows); `leading` (runtime/cjkType); `fitBlockPx`, `wrapLines`, `CONTENT_TOP`, `TITLE_Y`, `contentBottom` (runtime/layout); `onAccentInk` (runtime/onAccent); `workshop.still` (Task 2).
- Produces: `objects/DemoForm.tsx` exporting `DEMO_ID = 'DemoForm'`, `META` (`{aspect: 1, turns: true, demo: true, provenance: 'motion-graphics'}`), `DemoForm: React.FC<ObjectProps & {layers?: number}>` (layers 1-5); the register `ObjectStage` with props `object, labels, title, note, kicker`, `REQUIRED_IN_FILM = ['object']`, `MAX_STAGE_LABELS = 6`, `DURATION = 165`. The object's `t` runs 0→1 over 0.06-0.6 of the beat.

The library-wide manifest tests (measured luminance, energy, prop reach, ground reach) fail for `ObjectStage` until Task 12 measures the four stage registers together; this task runs the targeted tests below.

- [ ] **Step 1: Scaffold the register at every sync point**

Run:
```bash
python3 scripts/register_shot.py ObjectStage E --use-when "one thing the film drew, shown whole and named — its parts called out" --provenance motion-graphics
python3 scripts/register_shot.py ObjectStage --check
```
Expected: the stub `remotion/src/shots/ObjectStage.tsx` exists and `--check` reports nothing missing.

- [ ] **Step 2: Write the failing tests** — `tests/test_object_stage.py`:

```python
"""ObjectStage: a thing the film drew, standing on a floor, its parts called out, its name under it — at every
aspect, with its type inside the frame, and with a wide object letterboxed rather than stretched."""
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
import text_safe_qa as g  # noqa: E402
import cjk_type_qa as c  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

SQUARE = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: %(aspect)s, provenance: 'industrial'};
export const %(name)s: React.FC<ObjectProps & {color?: string}> = ({w, h, color = '#ff00ff'}) => (
  <div style={{width: w, height: h, background: color}} />
);
"""
LABELS = [{"text": "压实的粉饼", "x": 0.5, "y": 0.35}, {"text": "粉碗", "x": 0.2, "y": 0.7, "side": "left"},
          {"text": "出水口", "x": 0.85, "y": 0.9}]
FILM_PROPS = {"object": {"id": "WsSquare"}, "labels": LABELS, "title": "意式浓缩的粉饼",
              "note": "水要穿过它，阻力就是关键", "kicker": "萃取"}


@pytest.fixture(scope="module")
def film(tmp_path_factory):
    out = tmp_path_factory.mktemp("stage") / "film"
    d = out / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "WsSquare.tsx").write_text(SQUARE % {"name": "WsSquare", "aspect": "1"}, encoding="utf-8")
    (d / "WsBanner.tsx").write_text(SQUARE.replace("#ff00ff", "#00ffff") % {"name": "WsBanner", "aspect": "4"},
                                    encoding="utf-8")
    board = {"meta": {"renderer": "remotion", "design_dna": "product", "language": "zh"},
             "slides": [{"index": 1, "shot": "ObjectStage", "narration": "一", "shot_props": FILM_PROPS}]}
    (out / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


def _mask(png, rgb):
    a = np.asarray(Image.open(str(png)).convert("RGB")).astype(int)
    m = np.all(np.abs(a - np.array(rgb)) < 40, axis=-1)
    ys, xs = np.nonzero(m)
    return int(m.sum()), ((xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None)


@needs_toolchain
@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1", "4:5"])
def test_the_stage_shows_the_object_named_with_its_type_inside_the_frame(film, tmp_path, aspect):
    props = dict(FILM_PROPS, dna="product", aspect=aspect)
    env = _env(ws.workshop_dir(film))
    r = _still("ObjectStage", tmp_path / "s.png", props, env, frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    n, box = _mask(tmp_path / "s.png", (255, 0, 255))
    assert n > 60000 and box, (n, box)
    assert abs((box[2] - box[0]) - (box[3] - box[1])) <= 4, box
    assert g.audit_shot("ObjectStage", props, 150, str(tmp_path / "a.png"), env=env) == []
    hits = c.sweep(["ObjectStage"], dna="product", aspect=aspect, film_props={"ObjectStage": FILM_PROPS},
                   out_dir=film)["ObjectStage"]
    assert not hits["failed"] and not [h for h in hits["hits"] if h["kind"] in ("leading", "overlap", "orphan")], hits


@needs_toolchain
def test_a_wide_object_is_letterboxed_on_the_stage(film, tmp_path):
    """Review focus: a 4:1 object keeps its shape — never stretched to the stage's room."""
    props = {"object": {"id": "WsBanner"}, "title": "横幅", "dna": "product"}
    r = _still("ObjectStage", tmp_path / "w.png", props, _env(ws.workshop_dir(film)), frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    _n, box = _mask(tmp_path / "w.png", (0, 255, 255))
    ratio = (box[2] - box[0] + 1) / float(box[3] - box[1] + 1)
    assert abs(ratio - 4.0) < 0.08, (ratio, box)


@needs_toolchain
def test_the_standalone_preview_draws_its_own_form_and_no_words(tmp_path):
    r = _still("ObjectStage", tmp_path / "d.png", {"dna": "product"}, _env(), frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    a = np.asarray(Image.open(str(tmp_path / "d.png")).convert("RGB")).astype(int)
    ground = np.median(a.reshape(-1, 3), axis=0)
    ink = (np.abs(a - ground).sum(axis=-1) > 60).mean()
    assert ink > 0.05, ink


@needs_toolchain
@pytest.mark.parametrize("labels,expect", [
    ([{"text": "a", "x": 0.1 * i, "y": 0.5} for i in range(7)], "0-6 `labels`"),
    ([{"text": "粉碗", "y": 0.5}], "needs `x` and `y`"),
    ("粉碗", "must be a LIST"),
])
def test_malformed_labels_are_refused_by_name(film, tmp_path, labels, expect):
    r = _still("ObjectStage", tmp_path / "x.png", {"object": {"id": "WsSquare"}, "labels": labels},
               _env(ws.workshop_dir(film)))
    assert r.returncode != 0 and expect in r.stdout + r.stderr, (r.stdout + r.stderr)[-800:]


def test_a_film_must_name_its_object_and_never_the_preview(tmp_path):
    import validate as v
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    (tmp_path / "audio" / "02.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "ObjectStage", "narration": "一。", "audio": "audio/01.mp3",
                         "duration": 3.0, "shot_props": {"title": "它"}},
                        {"index": 2, "shot": "ObjectStage", "narration": "二。", "audio": "audio/02.mp3",
                         "duration": 3.0, "shot_props": {"object": {"id": "DemoForm"}, "title": "它"}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    assert any("scene #1: ObjectStage needs `object` in a film" in e for e in errs), errs
    assert any("scene #2" in e and "a stage's own preview form" in e for e in errs), errs


@needs_toolchain
def test_the_workshop_puts_an_object_on_the_stage_to_look_at(film):
    png = ws.still(film, "WsSquare")
    assert os.path.basename(png) == "WsSquare.png"
    n, _box = _mask(png, (255, 0, 255))
    assert n > 60000
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_object_stage.py -q`
Expected: FAIL — the stub renders its own name; `DemoForm` does not exist.

- [ ] **Step 4: The stages' own preview form** — `remotion/src/objects/DemoForm.tsx`:

```tsx
// OBJECT · DemoForm — the stages' own preview: slabs stacked into one form, drawn in 3D and turned by `yaw`.
// ObjectStage, ObjectCompare, ObjectPath and ObjectTurntable show it when rendered on their own, so a stage's
// preview — and its measurement — has a real object in it. A FILM never shows it: `demo` is in its META and
// validate.py refuses it by name. It carries no words.
//
// It is also the reference for an object that draws its own 3D turn (`turns: true`): its corners are rotated by
// `yaw` (runtime/project3d yawPoint) and projected into the object's own box (project); faces turned away are
// culled by their normals and the rest painted far to near. references/object-authoring.md points here.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '../runtime/objectSlot';
import {project, yawPoint, type Vec3} from '../runtime/project3d';
import {clamp01, seg, easeOutCubic} from '../runtime/motion';
import {mix} from '../runtime/dna';

export const DEMO_ID = 'DemoForm';
export const META: ObjectMeta = {aspect: 1, turns: true, demo: true, provenance: 'motion-graphics'};

const SURF_D0 = '#e9edf3', ACC_D0 = '#3563e9', INK_D0 = '#1c2230';
// the camera, fitted so the whole stack stays inside its box at any yaw (half-height 2.3 units at the aim)
const CAM: Vec3 = [0, 2.6, 8.2], AIM: Vec3 = [0, 0, 0], FOV = 30;
const LIGHT: Vec3 = [-0.45, 0.8, 0.4];

const sub = (a: Vec3, b: Vec3): Vec3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const unit = (a: Vec3): Vec3 => {
  const l = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
};

export const DemoForm: React.FC<ObjectProps & {layers?: number}> = ({w, h, t, dna, yaw, layers = 3}) => {
  if (!Number.isInteger(layers) || layers < 1 || layers > 5) {
    throw new Error(`DemoForm: \`layers\` is a whole number from 1 to 5 (got ${JSON.stringify(layers)})`);
  }
  const surf = dna?.surface ?? SURF_D0, acc = dna?.accent ?? ACC_D0, ink = dna?.fg ?? INK_D0;
  const Y = yaw ?? 0.6;
  const light = unit(LIGHT);
  const faces: {d: string; depth: number; fill: string}[] = [];
  for (let i = 0; i < layers; i++) {
    // each slab drops into its place in turn; the stack is whole by t = 0.9
    const at = (i / layers) * 0.5;
    const drop = easeOutCubic(clamp01(seg(t, at, at + 0.4)));
    const hx = 1.3 - i * 0.18, hz = 0.95 - i * 0.13, hy = 0.18;
    const cy = -0.72 + i * 0.5 + (1 - drop) * 1.4;
    const tone = mix(surf, acc, layers > 1 ? (i / (layers - 1)) * 0.6 : 0.3);
    const corner = (sx: number, sy: number, sz: number): Vec3 => yawPoint([sx * hx, cy + sy * hy, sz * hz], Y);
    const quads: {pts: Vec3[]; n: Vec3}[] = [
      {pts: [corner(-1, 1, -1), corner(1, 1, -1), corner(1, 1, 1), corner(-1, 1, 1)], n: [0, 1, 0]},
      {pts: [corner(-1, -1, 1), corner(1, -1, 1), corner(1, 1, 1), corner(-1, 1, 1)], n: yawPoint([0, 0, 1], Y)},
      {pts: [corner(-1, -1, -1), corner(1, -1, -1), corner(1, 1, -1), corner(-1, 1, -1)], n: yawPoint([0, 0, -1], Y)},
      {pts: [corner(1, -1, -1), corner(1, -1, 1), corner(1, 1, 1), corner(1, 1, -1)], n: yawPoint([1, 0, 0], Y)},
      {pts: [corner(-1, -1, -1), corner(-1, -1, 1), corner(-1, 1, 1), corner(-1, 1, -1)], n: yawPoint([-1, 0, 0], Y)},
    ];
    for (const q of quads) {
      const c: Vec3 = [0, 1, 2].map((k) => q.pts.reduce((a, p) => a + p[k], 0) / 4) as Vec3;
      if (dot(q.n, sub(CAM, c)) <= 0) continue;                  // turned away: never painted
      const proj = q.pts.map((p) => project(p, CAM, AIM, FOV, w, h));
      if (proj.some((p) => p === null)) continue;
      const lit = clamp01(0.55 + 0.45 * dot(q.n, light));
      const fill = q.n[1] > 0.5 ? mix(tone, '#ffffff', 0.22) : mix(tone, ink, 0.28 * (1 - lit));
      faces.push({d: 'M' + proj.map((p) => `${p!.x.toFixed(1)} ${p!.y.toFixed(1)}`).join(' L') + ' Z',
        depth: Math.hypot(...sub(c, CAM)), fill});
    }
  }
  faces.sort((a, b) => b.depth - a.depth);                         // far to near
  const edge = mix(ink, surf, 0.55);
  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      {faces.map((f, k) => (
        <path key={k} d={f.d} fill={f.fill} stroke={edge} strokeWidth={Math.max(1, w * 0.0025)} strokeLinejoin="round" />
      ))}
    </svg>
  );
};
```

In `remotion/src/objects/index.ts`, add after the `import type` line `import * as O_DemoForm from './DemoForm';` and inside `LIBRARY_OBJECTS` the entry `  DemoForm: {C: O_DemoForm.DemoForm, meta: O_DemoForm.META},`.

In `scripts/content_contract_qa.py`, add `OBJECTS = os.path.join(_REM, "objects")` below `EXTRA`, and in both `library()` and `main()` extend the file list with `sorted(glob.glob(os.path.join(OBJECTS, "*.tsx")))` (library objects answer to the same contract as registers).

- [ ] **Step 5: Write the register** — replace the stub `remotion/src/shots/ObjectStage.tsx` with:

```tsx
// SHOT · ObjectStage — one thing, shown whole and named: an object the FILM drew, standing on a quiet floor, its
// parts called out and its name set under it. Family E (a hero object).
//
// THE ARGUMENT SHAPE: "this is the thing — look at it." The library's hero registers each draw a thing of their
// own (MaterialHero's ring of parts, TechnicalPlate's stroked elevation); none could show an object a film drew
// for itself. This one holds any object (runtime/objectSlot) and frames it: a floor it stands on, callouts that
// point at named points on it, its name and one line under it.
//
// THE OBJECT OWNS ITS PICTURE AND THE STAGE OWNS THE WORDS. The object's clock runs 0 → 1 over 0.06–0.6 of the
// beat and then holds, so what is labelled is the object SETTLED, and the settled frame every gate reads shows
// the whole object with its names. Callout points are fractions of the object's own drawn box, so they stay on
// the part they name at every aspect. Where the frame is wide enough the callouts run to the side margins;
// where it is not (portrait, square) the object carries numbered dots and a numbered key sits under its name.
// The object and its words are centred together in the content zone.
//
// Standalone it shows its own preview form (objects/DemoForm, no words). A film must name its object —
// REQUIRED_IN_FILM, which validate.py reads.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';
import {onAccentInk} from '../runtime/onAccent';
import {rows} from '../runtime/rows';
import {ObjectSlot, useObjectEntry, fitAspect, type ObjectRef} from '../runtime/objectSlot';
import {DEMO_ID} from '../objects/DemoForm';

export const DURATION = 165;
export const MAX_STAGE_LABELS = 6;
export const REQUIRED_IN_FILM = ['object'] as const;
const BG_D0 = '#eef0f3', FG_D0 = '#1b1f27', DIM_D0 = '#5d6573', ACC_D0 = '#2f5bd8';
const DEMO_OBJECT: ObjectRef = {id: DEMO_ID};
const OBJ_A = 0.06, OBJ_B = 0.6;          // the object's own t runs 0 → 1 here, then holds
const LBL_A = 0.6, LAND_BY = 0.84;        // callouts, every one in before the settled frame

type Label = {text: string; x: number; y: number; side?: 'left' | 'right'};
const isUnit = (v: unknown) => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1;

export const ObjectStage: React.FC<{
  object?: ObjectRef;   // the thing the film drew (runtime/objectSlot) — absent: the stage's own preview form
  labels?: Label[];     // 0-6 callouts at points on the object, in its box's unit space
  title?: string;       // what it is, set under it
  note?: string;        // one line under the title
  kicker?: string;      // a spaced label above
}> = ({object: OBJECT = DEMO_OBJECT, labels, title = '', note = '', kicker = ''} = {}) => {
  const LABELS = rows<Label>(labels, 'labels', 'ObjectStage');
  if (LABELS.length > MAX_STAGE_LABELS) {
    throw new Error(`ObjectStage takes 0-${MAX_STAGE_LABELS} \`labels\` (got ${LABELS.length}) — past six the ` +
      'callouts crowd the thing they name; keep the parts the beat argues about.');
  }
  LABELS.forEach((l, i) => {
    if (!l || typeof l.text !== 'string' || !l.text.trim()) {
      throw new Error(`ObjectStage: label ${i + 1} has no \`text\` (got ${JSON.stringify(l)}).`);
    }
    if (!isUnit(l.x) || !isUnit(l.y)) {
      throw new Error(`ObjectStage: label ${i + 1} ("${l.text}") needs \`x\` and \`y\` in 0..1 of the object's box ` +
        `(got x=${String(l.x)}, y=${String(l.y)}) — the dot says "this part is HERE".`);
    }
  });
  const entry = useObjectEntry(OBJECT);
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0;
  const ON_ACC = onAccentInk(ACC, dna?.accent2, dna?.onAccent, FG);
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);

  // THE WORDS FIRST, SIZED TO THEIR COPY; THE OBJECT TAKES THE ROOM THEY LEAVE.
  const capW = Math.min(W * 0.84, 1240);
  const tLead = leading(title, 1.12), nLead = leading(note, 1.4);
  const titlePx = title ? fitBlockPx(title, capW, U * 0.13, Math.round(U * 0.05), {usable: 1, leading: tLead}) : 0;
  const titleH = title ? wrapLines(title, titlePx, capW) * titlePx * tLead : 0;
  const notePx = Math.round(U * 0.022);
  const noteH = note ? wrapLines(note, notePx, capW) * notePx * nLead : 0;
  const noteGap = title && note ? Math.round(U * 0.012) : 0;
  const wordsH = titleH + noteGap + noteH;
  const gap = wordsH ? Math.round(U * 0.03) : 0;

  // SIDE CALLOUTS where the frame has room beside the object; a NUMBERED KEY under the words where it does not.
  const nL = LABELS.length;
  const side = nL > 0 && W >= H * 1.2;
  const keyPx = Math.round(U * 0.02);
  const keyLines = LABELS.map((l, i) => `${i + 1}  ${l.text}`);
  const keyH = !side && nL
    ? keyLines.reduce((acc, s, i) => acc + (i ? keyPx * 0.45 : 0) + wrapLines(s, keyPx, capW) * keyPx * leading(s, 1.35), 0)
    : 0;
  const keyGap = keyH ? Math.round(U * 0.022) : 0;
  const colW = side ? Math.round(W * 0.19) : 0;
  const margin = Math.round(W * 0.045);
  const roomW = side ? W - 2 * (margin + colW + W * 0.03) : W * 0.84;
  const roomH = Math.max(U * 0.2, zBot - zTop - U * 0.02 - gap - wordsH - keyGap - keyH);
  const drawn = fitAspect({x: (W - roomW) / 2, y: 0, w: roomW, h: roomH}, entry.meta?.aspect);
  // the object and its words are one group, centred in the content zone
  const groupH = drawn.h + gap + wordsH + keyGap + keyH;
  const top0 = zTop + Math.max(U * 0.01, (zBot - zTop - groupH) / 2);
  const box = {x: drawn.x, y: top0, w: drawn.w, h: drawn.h};
  const floorY = box.y + box.h;
  const wordsTop = floorY + gap;

  const objT = clamp01(seg(t, OBJ_A, OBJ_B));
  const floorIn = easeOutCubic(clamp01(seg(t, 0.03, 0.2)));
  const step = nL > 1 ? Math.min(0.05, (LAND_BY - LBL_A - 0.12) / (nL - 1)) : 0;
  const onAt = (i: number) => easeOutCubic(clamp01(seg(t, LBL_A + i * step, LBL_A + i * step + 0.12)));
  const titleIn = easeOutCubic(clamp01(seg(t, 0.62, 0.78)));
  const noteIn = easeOutCubic(clamp01(seg(t, 0.66, 0.82)));

  // side callouts: each column ordered by height and pushed apart so no label overprints its neighbour; a column
  // that then runs past the content zone is lifted back as a whole
  const lblPx = Math.round(U * 0.02), lblLead = 1.3;
  const placed = LABELS.map((l, i) => ({l, i, p: {x: box.x + l.x * box.w, y: box.y + l.y * box.h},
    right: (l.side ?? (l.x >= 0.5 ? 'right' : 'left')) === 'right'}));
  const rowY: number[] = placed.map((q) => q.p.y);
  if (side) {
    for (const right of [true, false]) {
      const col = placed.filter((q) => q.right === right).sort((a, b) => a.p.y - b.p.y);
      let prev = -Infinity;
      for (const q of col) {
        rowY[q.i] = Math.max(q.p.y, prev + lblPx * 0.8);
        prev = rowY[q.i] + wrapLines(q.l.text, lblPx, colW) * lblPx * lblLead;
      }
      const over = prev - zBot;
      if (col.length && over > 0) col.forEach((q) => { rowY[q.i] -= over; });
    }
  }
  const dot = Math.max(4, Math.round(U * 0.006));
  const hair = Math.max(1, Math.round(W * 0.0012));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center', opacity: floorIn,
          font: `600 ${Math.round(U * 0.018)}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      ) : null}
      {/* the floor it stands on: a soft shadow in the film's own ink, at a whisper */}
      <div style={{position: 'absolute', left: box.x + box.w * 0.08, top: floorY - U * 0.012, width: box.w * 0.84,
        height: U * 0.03, borderRadius: '50%', background: FG, opacity: 0.1 * floorIn,
        filter: `blur(${Math.round(U * 0.01)}px)`}} />
      <ObjectSlot object={OBJECT} box={box} t={objT} />
      {placed.map(({l, i, p, right}) => {
        const on = onAt(i);
        if (on <= 0) return null;
        if (!side) {
          return (
            <div key={i} style={{position: 'absolute', left: p.x - dot * 2.2, top: p.y - dot * 2.2, width: dot * 4.4,
              height: dot * 4.4, borderRadius: '50%', background: ACC, color: ON_ACC, opacity: on, textAlign: 'center',
              font: `700 ${Math.round(dot * 2.6)}px/${dot * 4.4}px ${mono}`}}>{i + 1}</div>
          );
        }
        const y = rowY[i];
        const colX = right ? box.x + box.w + W * 0.03 : box.x - W * 0.03 - colW;
        const edgeX = right ? colX : colX + colW;
        const elbowX = right ? Math.max(p.x + W * 0.012, edgeX - W * 0.02) : Math.min(p.x - W * 0.012, edgeX + W * 0.02);
        return (
          <React.Fragment key={i}>
            <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity: on}}>
              <polyline points={`${p.x},${p.y} ${elbowX},${y} ${edgeX},${y}`} fill="none" stroke={ACC}
                strokeWidth={hair * 1.5} opacity={0.85} />
              <circle cx={p.x} cy={p.y} r={dot} fill={ACC} />
            </svg>
            <div style={{position: 'absolute', left: colX, top: y - lblPx * 0.68, width: colW, opacity: on,
              textAlign: right ? 'left' : 'right', font: `500 ${lblPx}px/${lblLead} ${bodyF}`, color: DIM,
              textWrap: 'balance'}}>{l.text}</div>
          </React.Fragment>
        );
      })}
      {title ? (
        <div style={{position: 'absolute', left: (W - capW) / 2, top: wordsTop, width: capW, textAlign: 'center',
          opacity: titleIn, font: `700 ${titlePx}px/${tLead} ${disp}`, color: FG, textWrap: 'balance'}}>{title}</div>
      ) : null}
      {note ? (
        <div style={{position: 'absolute', left: (W - capW) / 2, top: wordsTop + titleH + noteGap, width: capW,
          textAlign: 'center', opacity: noteIn, font: `400 ${notePx}px/${nLead} ${bodyF}`, color: DIM}}>{note}</div>
      ) : null}
      {!side && nL ? (
        <div style={{position: 'absolute', left: (W - capW) / 2, top: wordsTop + wordsH + keyGap, width: capW,
          display: 'flex', flexDirection: 'column', gap: keyPx * 0.45}}>
          {LABELS.map((l, i) => (
            <div key={i} style={{opacity: onAt(i), font: `500 ${keyPx}px/${leading(keyLines[i], 1.35)} ${bodyF}`, color: DIM}}>
              <span style={{color: ACC, fontWeight: 700}}>{i + 1}</span>{'  '}{l.text}</div>
          ))}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default ObjectStage;
```

- [ ] **Step 6: Write the card** — `remotion/cards/ObjectStage.md`:

```markdown
# ObjectStage

**Identity:** a thing the film drew for itself (an object from its workshop) stands whole on a quiet floor; numbered callouts point at named points on it and its name is set under it. The object owns the picture, the stage owns the words.

**Use when:** the beat says "this is the thing — look at it": the film has built an object no register draws (a coffee puck in section, a sensor, an artefact) and the argument names a few of its parts. **Not when:** the thing is a real photograph (`PhotoPlate`, `MuseumLabel`); the claim is a comparison (`ObjectCompare`), a process (`ObjectPath`) or the object's shape in the round (`ObjectTurntable`); the object is best read as a technical elevation (`TechnicalPlate` with `art`).

**Motion core:** the floor's shadow comes in over 0.03–0.2 while the object draws itself — its own t runs 0→1 over 0.06–0.6 and then holds. The callouts land one after another from 0.6, every one in by 0.84; the name and the note land over 0.62–0.82.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `object` | the thing the film drew — `{"id": …, "props": …}` from its workshop (`scripts/workshop.py`) | sized as large as the words leave room for, at its own aspect; required in a film (absent draws the stage's preview form) |
| `labels` | 0–6 callouts `{text, x, y, side?}` at points on the object (0..1 of its box) | wide frames run leaders to the side margins (`side` defaults to the half the point is in); portrait and square frames put numbered dots on the object and a numbered key under the name |
| `title` | what it is, set under the object | fitted to the width; long or Chinese names wrap, balanced |
| `note` | one line under the title | the place to say what the object's shape MEANS |
| `kicker` | a spaced label in the title band | follows the DNA's label casing |

**Known traps:**
- The object is drawn by the film, so everything the stage cannot see — its words, its colours, its motion — is the object's to get right; the stage's gates (text-safe, CJK type, words-from-props) still run on the whole frame.
- A callout point is a fraction of the object's DRAWN box, not of the frame: a wide object leaves its box shorter, and the points move with it.
- Past six labels the columns overprint; the register refuses.

**Refuses:** a malformed `labels` (not a list, more than six, a label with no `text` or without `x`/`y` in 0..1); an `object` that is not `{id, props?}`, names no object that exists, or sets `w`/`h`/`t`/`dna`/`yaw` in its props.

**Reference:** `remotion/src/shots/ObjectStage.tsx`

**Provenance:** motion-graphics (a beat holding an object is judged on the object's own world). **Family:** E.
```

- [ ] **Step 7: The catalogue** — in `remotion/LIBRARY.md`, replace the scaffold's placeholder line for ObjectStage (family E; keep the number it was given) with:
```markdown
N. **ObjectStage** — a thing the film drew, standing whole on a quiet floor, numbered callouts at points on it and its name under it. *Use: "this is the thing — look at it", for an object no register draws.* `object, labels[{text,x,y,side}], title, note, kicker` · `object` required in a film; 0-6 labels.
```
and append to the end of the file:
```markdown

## Objects — things a film drew, kept in the library

An object goes into any register with a slot for one — a prop typed `ObjectRef`: `ObjectStage`, `ObjectCompare`,
`ObjectPath`, `ObjectTurntable`, `TechnicalPlate` (`art`), `HudReticle` (`object`), a device's `screen` — by its id.
A film draws its own in its workshop (`scripts/workshop.py`); the good ones are promoted here (`scripts/promote.py`),
each naming the film it came from.

<!-- OBJECTS (scripts/promote.py appends below) -->
- **DemoForm** — slabs stacked into one form, drawn in 3D; the four stage registers' own standalone preview. *Never a film's object: `demo` in its META, and validate.py refuses it.* `layers` 1–5.
```

- [ ] **Step 8: Run the tests**

Run: `python3 -m pytest tests/test_object_stage.py tests/test_shot_cards.py tests/test_library_signatures.py tests/test_workshop_bundle.py -q && python3 scripts/content_contract_qa.py ObjectStage DemoForm && python3 scripts/register_shot.py ObjectStage --check && python3 scripts/text_safe_qa.py --library --only=ObjectStage --all-aspects`
Expected: PASS; no contract finding; nothing missing; no text-safe finding at any aspect. Then keep the renders and LOOK at them: `python3 -m pytest tests/test_object_stage.py -q -k shows_the_object --basetemp=.superpowers/look/stage` and open each `s.png` under that folder (one per aspect) — the object stands on its floor, every leader reaches its label, the key sits under the name in portrait and square, nothing crowds the caption band. Write down what you saw per aspect in the task report.

- [ ] **Step 9: Commit**

```bash
git add remotion/src/objects/DemoForm.tsx remotion/src/objects/index.ts scripts/content_contract_qa.py remotion/src/shots/ObjectStage.tsx remotion/cards/ObjectStage.md remotion/src/registry.ts remotion/src/Root.tsx remotion/src/runtime/shotLuma.ts scripts/shot_director.py remotion/LIBRARY.md tests/test_object_stage.py
git commit -m "ObjectStage: a thing the film drew, standing whole and named; DemoForm is the stages' own wordless preview

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---
### Task 9: ObjectCompare — two things, one difference named

**Files:**
- Scaffold, then write: `remotion/src/shots/ObjectCompare.tsx`, `remotion/cards/ObjectCompare.md`
- Modified by the scaffold: `remotion/src/registry.ts`, `remotion/src/Root.tsx`, `remotion/src/runtime/shotLuma.ts`, `scripts/shot_director.py`, `remotion/LIBRARY.md`
- Test: `tests/test_object_compare.py`

**Interfaces:**
- Consumes: Task 1 (`ObjectSlot`, `useObjectEntry`, `fitAspect`, `ObjectRef`, `Rect`), Task 8 (`DEMO_ID`, DemoForm's `layers`), `drawOn` (runtime/draw).
- Produces: the register `ObjectCompare` with props `first`, `second` (ObjectRefs), `firstLabel`, `secondLabel`, `difference`, `at: {x, y}`, `kicker`; `REQUIRED_IN_FILM = ['first', 'second', 'difference']`; `DURATION = 165`. The first object's `t` runs over 0.06–0.44, the second's over 0.16–0.54. (Not `left`/`right`: those names are rows in `cjk_type_qa`'s shared fixture table, which would feed this register another register's shape.)

- [ ] **Step 1: Scaffold**

Run:
```bash
python3 scripts/register_shot.py ObjectCompare H --use-when "two things the film drew, and the one difference between them named and marked on both" --provenance motion-graphics
python3 scripts/register_shot.py ObjectCompare --check
```

- [ ] **Step 2: Write the failing tests** — `tests/test_object_compare.py`:

```python
"""ObjectCompare: two things the film drew at the same size on one floor, their labels under them, a ring at the
same point on both, and the one difference named under the pair — side by side when wide, stacked when tall."""
import os
import sys

import numpy as np
import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
import text_safe_qa as g  # noqa: E402
import cjk_type_qa as c  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402
from test_object_stage import SQUARE, _mask  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")
PROPS = {"first": {"id": "WsLoose"}, "firstLabel": "松散的粉", "second": {"id": "WsTamped"},
         "secondLabel": "压实的粉饼", "difference": "压实以后，水必须用力才能穿过", "at": {"x": 0.5, "y": 0.3},
         "kicker": "对比"}


@pytest.fixture(scope="module")
def film(tmp_path_factory):
    out = tmp_path_factory.mktemp("compare") / "film"
    d = out / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "WsLoose.tsx").write_text(SQUARE % {"name": "WsLoose", "aspect": "1"}, encoding="utf-8")
    (d / "WsTamped.tsx").write_text(SQUARE.replace("#ff00ff", "#00ffff") % {"name": "WsTamped", "aspect": "1"},
                                    encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


@needs_toolchain
@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1", "4:3"])
def test_two_objects_at_one_size_the_difference_named_and_the_type_inside_the_frame(film, tmp_path, aspect):
    props = dict(PROPS, dna="product", aspect=aspect)
    env = _env(ws.workshop_dir(film))
    r = _still("ObjectCompare", tmp_path / "c.png", props, env, frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    nL, bL = _mask(tmp_path / "c.png", (255, 0, 255))
    nR, bR = _mask(tmp_path / "c.png", (0, 255, 255))
    assert bL and bR and nL > 20000 and nR > 20000, (nL, nR)
    wL, wR = bL[2] - bL[0], bR[2] - bR[0]
    assert abs(wL - wR) <= 4, (bL, bR)                               # fairness: one size for both
    if aspect in ("16:9", "4:3"):
        assert bL[2] < bR[0] and abs(bL[3] - bR[3]) <= 4, (bL, bR)   # side by side, on one floor
    else:
        assert bL[3] < bR[1], (bL, bR)                               # stacked: the first above the second
    assert g.audit_shot("ObjectCompare", props, 150, str(tmp_path / "a.png"), env=env) == []
    hits = c.sweep(["ObjectCompare"], dna="product", aspect=aspect, film_props={"ObjectCompare": PROPS},
                   out_dir=film)["ObjectCompare"]
    assert not hits["failed"] and not [h for h in hits["hits"] if h["kind"] in ("leading", "overlap", "orphan")], hits


@needs_toolchain
@pytest.mark.parametrize("bad,expect", [
    ({"first": "WsLoose"}, 'an object is {"id"'),
    ({"at": {"x": 0.5, "y": 1.4}}, '`at` is {"x": …, "y": …} in 0..1'),
    ({"at": [0.5, 0.3]}, '`at` is {"x": …, "y": …} in 0..1'),
])
def test_malformed_sides_are_refused_by_name(film, tmp_path, bad, expect):
    r = _still("ObjectCompare", tmp_path / "x.png", dict(PROPS, **bad), _env(ws.workshop_dir(film)))
    assert r.returncode != 0 and expect in r.stdout + r.stderr, (r.stdout + r.stderr)[-800:]


def test_a_film_names_both_things_and_the_difference(tmp_path):
    import validate as v
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "ObjectCompare", "narration": "一。", "audio": "audio/01.mp3",
                         "duration": 3.0, "shot_props": {"kicker": "对比"}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    for p in ("first", "second", "difference"):
        assert any("ObjectCompare needs `%s` in a film" % p in e for e in errs), (p, errs)


@needs_toolchain
def test_the_standalone_preview_compares_its_own_form_with_itself(tmp_path):
    r = _still("ObjectCompare", tmp_path / "d.png", {"dna": "product"}, _env(), frame=150)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_object_compare.py -q`
Expected: FAIL (the stub).

- [ ] **Step 4: Write the register** — replace the stub `remotion/src/shots/ObjectCompare.tsx` with:

```tsx
// SHOT · ObjectCompare — two things the film drew, side by side, and the ONE difference between them named and
// marked at the same place on both. Family H (comparison).
//
// THE ARGUMENT SHAPE: "these two differ HERE." The library's comparison registers set numbers, sentences or
// photographs against each other; this one sets two objects a film drew — one object in two states (a loose bed
// of coffee and a tamped one, the same street in 1900 and now) or two things with one decisive difference. A ring
// marks the same point on both (`at`, a fraction of each object's box), a dashed tie joins the rings, and the
// difference is set under the pair, in words.
//
// FAIRNESS IS PART OF THE CLAIM. Two objects of one aspect are drawn at ONE size on one floor line; the right one
// arrives a beat after the left, so the eye reads them in order, and nothing is emphasised by size. Wide frames
// set them side by side; tall frames stack them, left above right.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';
import {drawOn} from '../runtime/draw';
import {ObjectSlot, useObjectEntry, fitAspect, type ObjectRef, type Rect} from '../runtime/objectSlot';
import {DEMO_ID} from '../objects/DemoForm';

export const DURATION = 165;
export const REQUIRED_IN_FILM = ['first', 'second', 'difference'] as const;
const BG_D0 = '#eef0f3', FG_D0 = '#1b1f27', DIM_D0 = '#5d6573', ACC_D0 = '#2f5bd8';

const DEMO_FIRST: ObjectRef = {id: DEMO_ID, props: {layers: 3}};
const DEMO_SECOND: ObjectRef = {id: DEMO_ID, props: {layers: 2}};
const isUnit = (v: unknown) => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1;

export const ObjectCompare: React.FC<{
  first?: ObjectRef;              // the first thing the film drew (runtime/objectSlot)
  second?: ObjectRef;             // the second — the same object with other props, or another thing
  firstLabel?: string;            // what the first is, under it
  secondLabel?: string;           // what the second is, under it
  difference?: string;            // the one difference, in words, set under both
  at?: {x: number; y: number};    // where it is on both (0..1 of each object's box) — a ring on each, tied together
  kicker?: string;                // a spaced label in the title band
}> = ({first: FIRST = DEMO_FIRST, second: SECOND = DEMO_SECOND, firstLabel = '', secondLabel = '', difference = '',
  at, kicker = ''} = {}) => {
  if (at != null && !(typeof at === 'object' && !Array.isArray(at) && isUnit(at.x) && isUnit(at.y))) {
    throw new Error(`ObjectCompare: \`at\` is {"x": …, "y": …} in 0..1 of each object's box — got ${JSON.stringify(at)}`);
  }
  const eL = useObjectEntry(FIRST), eR = useObjectEntry(SECOND);
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0;
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const wide = W >= H * 1.2;
  const sw = Math.max(2, Math.round(U * 0.004));

  // THE WORDS FIRST: each label under its object, the difference under the pair.
  const capW = Math.min(W * 0.84, 1400);
  const gapX = Math.round(W * 0.06);
  const colW = wide ? (capW - gapX) / 2 : capW;
  const lblPx0 = Math.round(U * 0.026);
  const lblPx = Math.min(lblPx0, ...[firstLabel, secondLabel].filter((s) => !!s)
    .map((s) => fitBlockPx(s, colW, lblPx0 * 2.7, lblPx0, {usable: 1, leading: leading(s, 1.3)})));
  const lblH = (s?: string) => (s ? wrapLines(s, lblPx, colW) * lblPx * leading(s, 1.3) : 0);
  const dLead = leading(difference, 1.2);
  const diffPx = difference ? fitBlockPx(difference, capW, U * 0.1, Math.round(U * 0.038), {usable: 1, leading: dLead}) : 0;
  const ruleH = difference ? sw + Math.round(U * 0.016) : 0;
  const diffH = difference ? ruleH + wrapLines(difference, diffPx, capW) * diffPx * dLead : 0;
  const lblGap = Math.round(U * 0.018), diffGap = difference ? Math.round(U * 0.04) : 0;
  const x0 = (W - capW) / 2;

  let bL: Rect, bR: Rect, lblL: Rect, lblR: Rect, diffTop: number;
  if (wide) {
    const labelH = Math.max(lblH(firstLabel), lblH(secondLabel));
    const roomH = Math.max(U * 0.18, zBot - zTop - U * 0.02 - lblGap - labelH - diffGap - diffH);
    const dL = fitAspect({x: 0, y: 0, w: colW, h: roomH}, eL.meta?.aspect);
    const dR = fitAspect({x: 0, y: 0, w: colW, h: roomH}, eR.meta?.aspect);
    const h = Math.max(dL.h, dR.h);
    const top0 = zTop + Math.max(U * 0.01, (zBot - zTop - (h + lblGap + labelH + diffGap + diffH)) / 2);
    bL = {x: x0 + (colW - dL.w) / 2, y: top0 + h - dL.h, w: dL.w, h: dL.h};
    bR = {x: x0 + colW + gapX + (colW - dR.w) / 2, y: top0 + h - dR.h, w: dR.w, h: dR.h};
    lblL = {x: x0, y: top0 + h + lblGap, w: colW, h: lblH(firstLabel)};
    lblR = {x: x0 + colW + gapX, y: top0 + h + lblGap, w: colW, h: lblH(secondLabel)};
    diffTop = top0 + h + lblGap + labelH + diffGap;
  } else {
    const between = Math.round(U * 0.03);
    const roomH = Math.max(U * 0.14, (zBot - zTop - U * 0.02 - 2 * lblGap - lblH(firstLabel) - lblH(secondLabel) - between
      - diffGap - diffH) / 2);
    const dL = fitAspect({x: 0, y: 0, w: capW, h: roomH}, eL.meta?.aspect);
    const dR = fitAspect({x: 0, y: 0, w: capW, h: roomH}, eR.meta?.aspect);
    const groupH = dL.h + lblGap + lblH(firstLabel) + between + dR.h + lblGap + lblH(secondLabel) + diffGap + diffH;
    const top0 = zTop + Math.max(U * 0.01, (zBot - zTop - groupH) / 2);
    bL = {x: (W - dL.w) / 2, y: top0, w: dL.w, h: dL.h};
    lblL = {x: x0, y: top0 + dL.h + lblGap, w: capW, h: lblH(firstLabel)};
    const topR = lblL.y + lblL.h + between;
    bR = {x: (W - dR.w) / 2, y: topR, w: dR.w, h: dR.h};
    lblR = {x: x0, y: topR + dR.h + lblGap, w: capW, h: lblH(secondLabel)};
    diffTop = lblR.y + lblR.h + diffGap;
  }

  const tL = clamp01(seg(t, 0.06, 0.44)), tR = clamp01(seg(t, 0.16, 0.54));
  const inL = easeOutCubic(clamp01(seg(t, 0.4, 0.58))), inR = easeOutCubic(clamp01(seg(t, 0.46, 0.62)));
  const ringOn = clamp01(seg(t, 0.58, 0.7)), tieOn = clamp01(seg(t, 0.64, 0.76));
  const diffIn = easeOutCubic(clamp01(seg(t, 0.66, 0.82)));
  const r = U * 0.045;
  const pL = at ? {x: bL.x + at.x * bL.w, y: bL.y + at.y * bL.h} : null;
  const pR = at ? {x: bR.x + at.x * bR.w, y: bR.y + at.y * bR.h} : null;
  let tie: {x1: number; y1: number; x2: number; y2: number} | null = null;
  if (pL && pR) {            // the tie runs between the rings' edges, not through their centres
    const dx = pR.x - pL.x, dy = pR.y - pL.y, len = Math.hypot(dx, dy) || 1;
    tie = {x1: pL.x + (dx / len) * r, y1: pL.y + (dy / len) * r, x2: pR.x - (dx / len) * r, y2: pR.y - (dy / len) * r};
  }
  const label = (text: string | undefined, box: Rect, on: number) => (text ? (
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, textAlign: 'center', opacity: on,
      font: `500 ${lblPx}px/${leading(text, 1.3)} ${bodyF}`, color: DIM, textWrap: 'balance'}}>{text}</div>
  ) : null);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center',
          opacity: easeOutCubic(clamp01(seg(t, 0.03, 0.18))),
          font: `600 ${Math.round(U * 0.018)}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      ) : null}
      <ObjectSlot object={FIRST} box={bL} t={tL} />
      <ObjectSlot object={SECOND} box={bR} t={tR} />
      {label(firstLabel, lblL, inL)}
      {label(secondLabel, lblR, inR)}
      {pL && pR && tie ? (
        <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
          <line x1={tie.x1} y1={tie.y1} x2={tie.x2} y2={tie.y2} stroke={ACC} strokeWidth={sw * 0.75}
            strokeDasharray={`${sw * 3} ${sw * 3}`} opacity={0.8 * tieOn} />
          <circle cx={pL.x} cy={pL.y} r={r} fill="none" stroke={ACC} strokeWidth={sw} {...drawOn(ringOn)} />
          <circle cx={pR.x} cy={pR.y} r={r} fill="none" stroke={ACC} strokeWidth={sw} {...drawOn(ringOn)} />
        </svg>
      ) : null}
      {difference ? (
        <div style={{position: 'absolute', left: x0, top: diffTop, width: capW, textAlign: 'center', opacity: diffIn}}>
          <div style={{width: U * 0.06, height: sw, background: ACC, margin: `0 auto ${Math.round(U * 0.016)}px`}} />
          <div style={{font: `700 ${diffPx}px/${dLead} ${disp}`, color: FG, textWrap: 'balance'}}>{difference}</div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default ObjectCompare;
```

- [ ] **Step 5: Write the card** — `remotion/cards/ObjectCompare.md`:

```markdown
# ObjectCompare

**Identity:** two things the film drew stand at one size on one floor — or one above the other on a tall frame — each named under itself; a ring marks the same point on both, a dashed tie joins the rings, and the one difference is set under the pair.

**Use when:** the beat says "these two differ HERE": one object in two states (loose and tamped, before and after, 1900 and now) or two things with one decisive difference, and the film has built them. **Not when:** the difference is a number (`VersusSplit`, `EdCompare`), two photographs (`RealVersus`, `BeforeAfterSlider`), or more than two things.

**Motion core:** the first object draws itself over 0.06–0.44 and the second over 0.16–0.54, so they are read in order; their labels follow (0.4–0.62). The rings draw on over 0.58–0.7, the tie over 0.64–0.76, the difference lands over 0.66–0.82.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `first` | the first thing the film drew — `{"id": …, "props": …}` | required in a film; the same object with different `props` in `second` is the commonest compare (one thing, two states) |
| `second` | the second thing | required in a film; arrives a beat after the first |
| `firstLabel` | what the first is, under it | balanced, up to two lines |
| `secondLabel` | what the second is, under it | balanced, up to two lines |
| `difference` | the one difference, in words, under the pair | required in a film; wraps balanced in up to the width of both |
| `at` | `{x, y}` in 0..1 of each object's box — where the difference is | a ring on both at the same relative point, tied with a dashed line; absent: no rings |
| `kicker` | a spaced label in the title band | follows the DNA's label casing |

**Known traps:**
- Two objects of one aspect are drawn at one size on purpose: the register refuses to emphasise one by scale. Objects of different aspects each fit the same room.
- `at` is the SAME fraction on both boxes — it assumes the two objects share a layout (the same object in two states). For two different things, mark nothing, or draw the mark inside each object.

**Refuses:** an object that is not `{id, props?}` or that nobody defines; an `at` that is not `{x, y}` in 0..1.

**Reference:** `remotion/src/shots/ObjectCompare.tsx`

**Provenance:** motion-graphics (a beat holding objects is judged on their own world). **Family:** H.
```

- [ ] **Step 6: The catalogue** — replace the scaffold's placeholder line for ObjectCompare (family H, keep its number) with:
```markdown
N. **ObjectCompare** — two things the film drew at one size on one floor, each named, a ring at the same point on both and the one difference set under the pair. *Use: "these two differ HERE" — one object in two states, or two things.* `first, second, firstLabel, secondLabel, difference, at, kicker` · `first`, `second`, `difference` required in a film.
```

- [ ] **Step 7: Run the tests**

Run: `python3 -m pytest tests/test_object_compare.py tests/test_shot_cards.py tests/test_library_signatures.py -q && python3 scripts/content_contract_qa.py ObjectCompare && python3 scripts/register_shot.py ObjectCompare --check && python3 scripts/text_safe_qa.py --library --only=ObjectCompare --all-aspects`
Expected: PASS, no finding. Keep the renders (`-k two_objects --basetemp=.superpowers/look/compare`) and LOOK: one floor, one size, the rings on the same point of both, the difference under the pair.

- [ ] **Step 8: Commit**

```bash
git add remotion/src/shots/ObjectCompare.tsx remotion/cards/ObjectCompare.md remotion/src/registry.ts remotion/src/Root.tsx remotion/src/runtime/shotLuma.ts scripts/shot_director.py remotion/LIBRARY.md tests/test_object_compare.py
git commit -m "ObjectCompare: two things the film drew, one size, one floor, the one difference named and marked on both

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 10: ObjectPath — a thing that goes through stations and changes

**Files:**
- Scaffold, then write: `remotion/src/shots/ObjectPath.tsx`, `remotion/cards/ObjectPath.md`
- Modified by the scaffold: `remotion/src/registry.ts`, `remotion/src/Root.tsx`, `remotion/src/runtime/shotLuma.ts`, `scripts/shot_director.py`, `remotion/LIBRARY.md`
- Test: `tests/test_object_path.py`

**Interfaces:**
- Consumes: Task 1, Task 8 (`DEMO_ID`), `pointAt` (runtime/alongPath), `drawOn` (runtime/draw), `easeInOutCubic`.
- Produces: the register `ObjectPath` with props `object, stations, route ('line' | 'arc'), title, kicker`; `REQUIRED_IN_FILM = ['object', 'stations']`; `MAX_STATIONS = 5`; `DURATION = 180`; exported `pathProgress(t: number, n: number): number` — the object's own `t`: 0 at the first station, `(k-1)/(n-1)` while it dwells at station k, 1 at the last.

- [ ] **Step 1: Scaffold**

Run:
```bash
python3 scripts/register_shot.py ObjectPath I --use-when "one thing the film drew, carried through named stations in order and changing at each" --provenance motion-graphics
python3 scripts/register_shot.py ObjectPath --check
```

- [ ] **Step 2: Write the failing tests** — `tests/test_object_path.py`:

```python
"""ObjectPath: one thing the film drew rides a route through named stations; its own clock is its progress, so it
can look different at each station. Across the frame when wide, down it when tall; a line or a gentle arc."""
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
import text_safe_qa as g  # noqa: E402
import cjk_type_qa as c  # noqa: E402
import _tsprobe as tp  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402
from test_object_stage import _mask  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

# magenta before the halfway point of the route, cyan after — so the frame shows which clock the object got
STATEFUL = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};
export const %(name)s: React.FC<ObjectProps> = ({w, h, t}) => (
  <div style={{width: w, height: h, background: t < 0.5 ? '#ff00ff' : '#00ffff'}} />
);
"""
PROPS = {"object": {"id": "WsBean"}, "stations": ["烘焙", "研磨", "压粉", "萃取"], "title": "一颗豆子的路",
         "kicker": "流程"}


@pytest.fixture(scope="module")
def film(tmp_path_factory):
    out = tmp_path_factory.mktemp("path") / "film"
    d = out / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "WsBean.tsx").write_text(STATEFUL % {"name": "WsBean"}, encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


def test_progress_dwells_at_each_station_and_ends_at_the_last():
    if not tp.available():
        pytest.skip("needs the remotion toolchain")
    out = tp.run_ts("import {pathProgress} from %s;" % json.dumps(os.path.join(_REM, "src", "shots", "ObjectPath.tsx")),
                    "out.s = [0, 0.1, 0.23, 0.5, 0.84, 0.86, 1].map((t) => pathProgress(t, 4));"
                    "out.mono = Array.from({length: 101}, (_, i) => pathProgress(i / 100, 3));"
                    "out.two = pathProgress(0.9, 2);")
    s = out["s"]
    assert s[0] == 0 and s[1] == 0 and s[2] == 0 and s[4] == 1 and s[5] == 1 and s[6] == 1, s
    assert 0 < s[3] < 1, s
    assert all(b >= a - 1e-9 for a, b in zip(out["mono"], out["mono"][1:])), "progress must never go back"
    assert out["two"] == 1


@needs_toolchain
@pytest.mark.parametrize("aspect,route", [("16:9", "line"), ("16:9", "arc"), ("9:16", "line"), ("9:16", "arc"),
                                          ("1:1", "line")])
def test_the_object_ends_at_the_last_station_changed_with_the_type_inside_the_frame(film, tmp_path, aspect, route):
    props = dict(PROPS, route=route, dna="product", aspect=aspect)
    env = _env(ws.workshop_dir(film))
    r = _still("ObjectPath", tmp_path / "e.png", props, env, frame=170)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    n_late, box = _mask(tmp_path / "e.png", (0, 255, 255))
    assert n_late > 5000 and box, n_late                           # cyan: the object got t = 1 at the last station
    W, H = Image.open(str(tmp_path / "e.png")).size
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    if W >= H * 1.2:
        assert cx > W * 0.8, (cx, W)                              # wide: the last station is on the right
    else:
        assert cy > H * 0.55, (cy, H)                             # tall: the last station is at the bottom
    assert g.audit_shot("ObjectPath", props, 170, str(tmp_path / "a.png"), env=env) == []
    hits = c.sweep(["ObjectPath"], dna="product", aspect=aspect, film_props={"ObjectPath": dict(PROPS, route=route)},
                   out_dir=film)["ObjectPath"]
    assert not hits["failed"] and not [h for h in hits["hits"] if h["kind"] in ("leading", "overlap", "orphan")], hits


@needs_toolchain
def test_at_the_first_station_the_object_is_in_its_first_state(film, tmp_path):
    r = _still("ObjectPath", tmp_path / "s.png", dict(PROPS, dna="product"), _env(ws.workshop_dir(film)), frame=45)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    n, box = _mask(tmp_path / "s.png", (255, 0, 255))
    assert n > 5000 and (box[0] + box[2]) / 2 < 1920 * 0.2, box


@needs_toolchain
@pytest.mark.parametrize("stations,expect", [(["烘焙"], "2-5 `stations`"), (["a", "b", "c", "d", "e", "f"], "2-5 `stations`"),
                                             (["烘焙", " "], "station 2 has no name"), ("烘焙", "must be a LIST")])
def test_malformed_stations_are_refused_by_name(film, tmp_path, stations, expect):
    r = _still("ObjectPath", tmp_path / "x.png", dict(PROPS, stations=stations), _env(ws.workshop_dir(film)))
    assert r.returncode != 0 and expect in r.stdout + r.stderr, (r.stdout + r.stderr)[-800:]


def test_a_film_names_its_object_and_stations(tmp_path):
    import validate as v
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "ObjectPath", "narration": "一。", "audio": "audio/01.mp3",
                         "duration": 3.0, "shot_props": {"title": "路"}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    assert any("ObjectPath needs `object` in a film" in e for e in errs), errs
    assert any("ObjectPath needs `stations` in a film" in e for e in errs), errs
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_object_path.py -q`
Expected: FAIL (the stub; `pathProgress` does not exist).

- [ ] **Step 4: Write the register** — replace the stub `remotion/src/shots/ObjectPath.tsx` with:

```tsx
// SHOT · ObjectPath — a thing the film drew travels a route through named stations and changes as it goes: its own
// clock IS its progress along the route, so it can be beans at the first station and a cup at the last. Family I
// (process / section).
//
// THE ARGUMENT SHAPE: "it goes through these, in this order, and becomes this." ConveyorBelt and InOrder carry a
// sequence of LABELS; neither carries one THING whose state changes from station to station. Here the object's t
// runs 0 → 1 from the first station to the last — (k-1)/(n-1) while it dwells at station k — so a film's object can
// draw what it looks like at every stage (pathProgress, exported for its test and for an author to read).
//
// The route is a straight track or a gentle arc (`route`), across the frame when it is wide and down it when it is
// tall; stations sit at equal arc length along it (runtime/alongPath) and are named under — or, tall, beside —
// their marks. The station the object is at is set in the accent; those passed stay ink; those ahead wait dim.
// Standalone it carries its own preview form past three unnamed stations: no words to leak.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitTextPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {pointAt} from '../runtime/alongPath';
import {drawOn} from '../runtime/draw';
import {ObjectSlot, useObjectEntry, fitAspect, type ObjectRef} from '../runtime/objectSlot';
import {DEMO_ID} from '../objects/DemoForm';

export const DURATION = 180;
export const MAX_STATIONS = 5;
export const REQUIRED_IN_FILM = ['object', 'stations'] as const;
const BG_D0 = '#eef0f3', FG_D0 = '#1b1f27', DIM_D0 = '#5d6573', ACC_D0 = '#2f5bd8', LINE_D0 = '#c9ced6';
const DEMO_OBJECT: ObjectRef = {id: DEMO_ID};
const DEMO_STATIONS = ['', '', ''];        // the preview's three unnamed stops — no words to leak
const TRAVEL_A = 0.22, TRAVEL_B = 0.84, DWELL = 0.4;

/** Progress along the route (0 → 1) at the beat's t: a dwell at each station, an eased move between them. */
export const pathProgress = (t: number, n: number): number => {
  if (n < 2) return 1;
  const move = 1 - DWELL;
  const u = clamp01(seg(t, TRAVEL_A, TRAVEL_B)) * (n * DWELL + (n - 1) * move);
  let acc = 0;
  for (let k = 0; k < n; k++) {
    if (u <= acc + DWELL) return k / (n - 1);
    acc += DWELL;
    if (k === n - 1) return 1;
    if (u <= acc + move) return (k + easeInOutCubic((u - acc) / move)) / (n - 1);
    acc += move;
  }
  return 1;
};

export const ObjectPath: React.FC<{
  object?: ObjectRef;         // the thing the film drew (runtime/objectSlot); its t is its progress along the route
  stations?: string[];        // 2-5 station names, in order
  route?: 'line' | 'arc';     // the track's shape
  title?: string;             // one line over the route
  kicker?: string;            // a spaced label in the title band
}> = ({object: OBJECT = DEMO_OBJECT, stations: STATIONS_IN = DEMO_STATIONS, route = 'line', title = '', kicker = ''} = {}) => {
  const STATIONS = rows<string>(STATIONS_IN, 'stations', 'ObjectPath');
  const n = STATIONS.length;
  if (n < 2 || n > MAX_STATIONS) {
    throw new Error(`ObjectPath takes 2-${MAX_STATIONS} \`stations\` (got ${n}) — one station is not a route, and past ` +
      'five each stop is too brief to be seen.');
  }
  if (STATIONS_IN !== DEMO_STATIONS) {
    STATIONS.forEach((s, i) => {
      if (typeof s !== 'string' || !s.trim()) {
        throw new Error(`ObjectPath: station ${i + 1} has no name (got ${JSON.stringify(s)}).`);
      }
    });
  }
  if (route !== 'line' && route !== 'arc') {
    throw new Error(`ObjectPath: \`route\` is 'line' or 'arc' — got ${JSON.stringify(route)}`);
  }
  const entry = useObjectEntry(OBJECT);
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H), zH = zBot - zTop;
  const wide = W >= H;

  const titleLead = leading(title, 1.12);
  const titlePx = title ? fitTextPx(title, W * 0.84, Math.round(U * 0.042), {usable: 1}) : 0;
  const titleH = title ? titlePx * titleLead + U * 0.03 : 0;
  const lblPx = Math.round(U * 0.022);
  const sw = Math.max(2, Math.round(U * 0.004));

  // THE ROUTE, THE OBJECT'S ROOM AND THE NAMES, per orientation
  let d: string, ob: number, lblW: number, place: (p: {x: number; y: number}) => {x: number; y: number};
  let labelAt: (p: {x: number; y: number}) => {left: number; top: number; align: 'center' | 'left'};
  if (wide) {
    const x0 = W * 0.1, x1 = W * 0.9, spacing = (x1 - x0) / (n - 1);
    lblW = Math.min(spacing * 0.9, W * 0.24);
    const lblH = Math.max(lblPx * 1.3, ...STATIONS.map((s) => (s ? wrapLines(s, lblPx, lblW) * lblPx * leading(s, 1.3) : 0)));
    const lift = route === 'arc' ? zH * 0.22 : 0;              // the arc's control offset; its apex rises lift / 2
    const yTrack = zBot - lblH - U * 0.045;
    ob = Math.max(U * 0.1, Math.min(zH * 0.46, spacing * 0.95, W * 0.26, yTrack - lift / 2 - zTop - titleH));
    d = route === 'arc' ? `M ${x0} ${yTrack} Q ${W / 2} ${yTrack - lift} ${x1} ${yTrack}` : `M ${x0} ${yTrack} L ${x1} ${yTrack}`;
    place = (p) => ({x: p.x, y: p.y - ob / 2 - sw});          // the object stands on the track
    labelAt = (p) => ({left: p.x - lblW / 2, top: p.y + U * 0.025, align: 'center'});
  } else {
    const xT = W * 0.3;
    ob = Math.max(U * 0.1, Math.min(W * 0.34, (zH - titleH - U * 0.04) / (n + 0.4)));
    const yA = zTop + titleH + ob / 2 + U * 0.01, yB = zBot - ob / 2 - U * 0.01;
    d = route === 'arc' ? `M ${xT} ${yA} Q ${xT - W * 0.12} ${(yA + yB) / 2} ${xT} ${yB}` : `M ${xT} ${yA} L ${xT} ${yB}`;
    const lx = xT + ob / 2 + U * 0.035;
    lblW = W * 0.94 - lx;
    place = (p) => p;                                          // the object rides centred on the track
    labelAt = (p) => ({left: lx, top: p.y - lblPx * 0.68, align: 'left'});
  }
  const drawn = fitAspect({x: 0, y: 0, w: ob, h: ob}, entry.meta?.aspect);
  const stops = STATIONS.map((_, k) => pointAt(d, k / (n - 1)));
  const trackIn = easeOutCubic(clamp01(seg(t, 0.04, 0.2)));
  const p = pathProgress(t, n);
  const here = place(pointAt(d, p));
  const box = {x: here.x - drawn.w / 2, y: here.y - drawn.h / 2, w: drawn.w, h: drawn.h};
  const cur = p * (n - 1);                                      // stations reached: k <= cur
  const kicked = easeOutCubic(clamp01(seg(t, 0.03, 0.18)));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center', opacity: kicked,
          font: `600 ${Math.round(U * 0.018)}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      ) : null}
      {title ? (
        <div style={{position: 'absolute', left: W * 0.08, top: zTop, width: W * 0.84, textAlign: 'center',
          opacity: kicked, font: `700 ${titlePx}px/${titleLead} ${disp}`, color: FG, whiteSpace: 'nowrap'}}>{title}</div>
      ) : null}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <path d={d} fill="none" stroke={LINE} strokeWidth={sw} strokeLinecap="round" {...drawOn(trackIn)} />
        {stops.map((s, k) => {
          const shown = trackIn >= k / (n - 1) - 1e-6;
          const reached = k <= cur + 1e-6;
          return shown ? <circle key={k} cx={s.x} cy={s.y} r={Math.max(4, U * 0.008)} fill={reached ? ACC : 'none'}
            stroke={reached ? ACC : LINE} strokeWidth={sw} /> : null;
        })}
      </svg>
      <ObjectSlot object={OBJECT} box={box} t={p} />
      {STATIONS.map((s, k) => {
        if (!s) return null;
        const at = labelAt(stops[k]);
        const on = easeOutCubic(clamp01(seg(trackIn, k / (n - 1) - 0.25, k / (n - 1))));
        const isHere = Math.abs(cur - k) < 0.02;                  // dwelling at this station
        const passed = !isHere && k < cur;
        return (
          <div key={k} style={{position: 'absolute', left: at.left, top: at.top, width: lblW, textAlign: at.align,
            opacity: on, font: `${isHere ? 700 : 500} ${lblPx}px/${leading(s, 1.3)} ${bodyF}`,
            color: isHere ? ACC : passed ? FG : DIM, textWrap: 'balance'}}>{s}</div>
        );
      })}
    </AbsoluteFill>
  );
};
export default ObjectPath;
```

- [ ] **Step 5: Write the card** — `remotion/cards/ObjectPath.md`:

```markdown
# ObjectPath

**Identity:** one thing the film drew rides a route through named stations — across the frame when it is wide, down it when it is tall — pausing at each; its own clock is its progress along the route, so it can look different at every station. The station it is at is set in the accent.

**Use when:** the beat says "it goes through these, in this order, and becomes this": beans → grounds → puck → espresso; a signal through stages; a parcel through a network — ONE thing whose state is the story. **Not when:** the stations are only labels with nothing travelling (`InOrder`, `ConveyorBelt`); the stages are places on one object (`ObjectStage` with labels); the route is geography (`MapRoutes`, `SectionRoute`).

**Motion core:** the track draws on over 0.04–0.2 and each station's mark and name arrive as the track reaches it. From 0.22 the object dwells at each station and moves between them (eased), arriving at the last by 0.84; its own t is exactly that progress — 0 at the first station, (k−1)/(n−1) at station k, 1 at the last — so the settled frame shows it at the end, in its last state.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `object` | the thing the film drew — `{"id": …, "props": …}`; its `t` is its progress along the route | required in a film; draw its states against `t` (see `pathProgress` in the source) |
| `stations` | 2–5 names, in order | required in a film; wide: named under their marks; tall: beside them |
| `route` | `line` or `arc` | an arc rises across a wide frame and bows left down a tall one — for a route that is a journey, not a conveyor |
| `title` | one line over the route | fitted to one line |
| `kicker` | a spaced label in the title band | follows the DNA's label casing |

**Known traps:**
- The object's size is set by the spacing between stations: five stations across a square frame leave it small. Fewer stations, or `ObjectStage` for the one state that matters.
- The object is placed by its CENTRE on a tall route and by its FOOT on a wide one; an object with empty space at its foot will look like it floats.

**Refuses:** fewer than 2 or more than 5 stations; a station with no name; a `route` other than `line`/`arc`; `stations` that is not a list.

**Reference:** `remotion/src/shots/ObjectPath.tsx`

**Provenance:** motion-graphics (a beat holding an object is judged on the object's own world). **Family:** I.
```

- [ ] **Step 6: The catalogue** — replace the scaffold's placeholder line for ObjectPath (family I, keep its number) with:
```markdown
N. **ObjectPath** — one thing the film drew rides a route through named stations, pausing at each and changing as it goes (its t IS its progress). *Use: "it goes through these, in this order, and becomes this".* `object, stations[], route, title, kicker` · `object` and 2–5 `stations` required in a film.
```

- [ ] **Step 7: Run the tests**

Run: `python3 -m pytest tests/test_object_path.py tests/test_shot_cards.py tests/test_library_signatures.py -q && python3 scripts/content_contract_qa.py ObjectPath && python3 scripts/register_shot.py ObjectPath --check && python3 scripts/text_safe_qa.py --library --only=ObjectPath --all-aspects`
Expected: PASS, no finding. Keep the renders (`-k ends_at_the_last --basetemp=.superpowers/look/path`) and LOOK: the object stands on the track (wide) or rides it (tall), the current station reads in the accent, the arc clears the title.

- [ ] **Step 8: Commit**

```bash
git add remotion/src/shots/ObjectPath.tsx remotion/cards/ObjectPath.md remotion/src/registry.ts remotion/src/Root.tsx remotion/src/runtime/shotLuma.ts scripts/shot_director.py remotion/LIBRARY.md tests/test_object_path.py
git commit -m "ObjectPath: one thing the film drew rides a route through named stations, its clock its progress

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---
### Task 11: ObjectTurntable — a thing turned so its shape is seen

**Files:**
- Scaffold, then write: `remotion/src/shots/ObjectTurntable.tsx`, `remotion/cards/ObjectTurntable.md`
- Modified by the scaffold: `remotion/src/registry.ts`, `remotion/src/Root.tsx`, `remotion/src/runtime/shotLuma.ts`, `scripts/shot_director.py`, `remotion/LIBRARY.md`
- Test: `tests/test_object_turntable.py`

**Interfaces:**
- Consumes: Task 1 (`ObjectSlot`, `useObjectEntry`, `fitAspect`, `ObjectRef`; `ObjectProps.yaw`; `ObjectMeta.turns`), Task 8 (`DEMO_ID`; DemoForm is a `turns` object), `easeInOutCubic`.
- Produces: the register `ObjectTurntable` with props `object, sweep, title, note, kicker`; `REQUIRED_IN_FILM = ['object']`; `DURATION = 180`; `MAX_CARD_TURN = 60` (degrees each way for an object that does not draw its own 3D). The yaw runs from −sweep/2 to +sweep/2 over 0.08–0.92 (eased); the object's `t` runs over 0.04–0.4.

- [ ] **Step 1: Scaffold**

Run:
```bash
python3 scripts/register_shot.py ObjectTurntable K --use-when "one thing the film drew, turned on a turntable so its shape in the round is seen" --provenance motion-graphics
python3 scripts/register_shot.py ObjectTurntable --check
```

- [ ] **Step 2: Write the failing tests** — `tests/test_object_turntable.py`:

```python
"""ObjectTurntable: an object that draws its own 3D is handed the turn (yaw) and turns for real; any other object
turns as a card, at most ±60°, and a larger sweep on it is refused rather than flattened."""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
import text_safe_qa as g  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402
from test_object_stage import SQUARE, _mask  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

# a `turns` object that shows which way it was turned: magenta while yaw < 0, cyan after
TURNS = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, turns: true, provenance: 'industrial'};
export const %(name)s: React.FC<ObjectProps> = ({w, h, yaw}) => (
  <div style={{width: w, height: h, background: (yaw ?? 0) < 0 ? '#ff00ff' : '#00ffff'}} />
);
"""
PROPS = {"title": "冲煮头", "note": "从侧面看，水从这里分散开", "kicker": "结构"}


@pytest.fixture(scope="module")
def film(tmp_path_factory):
    out = tmp_path_factory.mktemp("turntable") / "film"
    d = out / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "WsTurns.tsx").write_text(TURNS % {"name": "WsTurns"}, encoding="utf-8")
    (d / "WsFlat.tsx").write_text(SQUARE % {"name": "WsFlat", "aspect": "1"}, encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


@needs_toolchain
def test_an_object_that_draws_its_own_3d_is_handed_the_turn(film, tmp_path):
    env = _env(ws.workshop_dir(film))
    props = dict(PROPS, object={"id": "WsTurns"}, sweep=80, dna="product")
    early = _still("ObjectTurntable", tmp_path / "e.png", props, env, frame=25)
    late = _still("ObjectTurntable", tmp_path / "l.png", props, env, frame=165)
    assert early.returncode == 0 and late.returncode == 0, (early.stderr + late.stderr)[-800:]
    assert _mask(tmp_path / "e.png", (255, 0, 255))[0] > 20000        # yaw < 0 at the start of the turn
    assert _mask(tmp_path / "l.png", (0, 255, 255))[0] > 20000        # yaw > 0 by its end


@needs_toolchain
def test_a_flat_object_turns_as_a_card_and_is_foreshortened(film, tmp_path):
    props = dict(PROPS, object={"id": "WsFlat"}, sweep=80, dna="product")
    r = _still("ObjectTurntable", tmp_path / "f.png", props, _env(ws.workshop_dir(film)), frame=165)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    _n, box = _mask(tmp_path / "f.png", (255, 0, 255))
    w, h = box[2] - box[0], box[3] - box[1]
    assert w < 0.92 * h, (w, h)                                        # turned ~40°: narrower than tall


@needs_toolchain
def test_a_flat_object_is_never_turned_past_its_edge(film, tmp_path):
    r = _still("ObjectTurntable", tmp_path / "x.png", dict(PROPS, object={"id": "WsFlat"}, sweep=200),
               _env(ws.workshop_dir(film)))
    assert r.returncode != 0 and "at most 120" in r.stdout + r.stderr, (r.stdout + r.stderr)[-800:]


@needs_toolchain
@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1"])
def test_the_type_stays_inside_the_frame(film, tmp_path, aspect):
    props = dict(PROPS, object={"id": "WsTurns"}, dna="product", aspect=aspect)
    assert g.audit_shot("ObjectTurntable", props, 165, str(tmp_path / "a.png"), env=_env(ws.workshop_dir(film))) == []


@needs_toolchain
def test_the_standalone_preview_turns_its_own_form(tmp_path):
    r = _still("ObjectTurntable", tmp_path / "d.png", {"dna": "product"}, _env(), frame=120)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_object_turntable.py -q`
Expected: FAIL (the stub).

- [ ] **Step 4: Write the register** — replace the stub `remotion/src/shots/ObjectTurntable.tsx` with:

```tsx
// SHOT · ObjectTurntable — a thing the film drew, turned on a turntable so its shape in the round is seen: a
// platter under it whose rim marks the turn, its name under the platter. Family K (3D form).
//
// THE ARGUMENT SHAPE: "this is what it is like from every side." A front view hides depth; a turn shows it. An
// object that draws its own 3D (META.turns — its points projected with runtime/project3d, like objects/DemoForm)
// is handed the yaw and turns for real. Any other object is turned as a CARD with CSS perspective, at most ±60°,
// so its back never faces the camera; a `sweep` past 120° on such an object is refused, not quietly flattened.
// The rim's ticks move with the yaw either way, so the turn reads even when the object itself is nearly symmetric.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, mix} from '../runtime/dna';
import {ObjectSlot, useObjectEntry, fitAspect, type ObjectRef} from '../runtime/objectSlot';
import {DEMO_ID} from '../objects/DemoForm';

export const DURATION = 180;
export const REQUIRED_IN_FILM = ['object'] as const;
export const MAX_CARD_TURN = 60;         // degrees each way for an object that does not draw its own 3D
const BG_D0 = '#eef0f3', FG_D0 = '#1b1f27', DIM_D0 = '#5d6573', ACC_D0 = '#2f5bd8', LINE_D0 = '#c9ced6';
const SURF_D0 = '#ffffff';
const DEMO_OBJECT: ObjectRef = {id: DEMO_ID};
const TICKS = 24;

export const ObjectTurntable: React.FC<{
  object?: ObjectRef;   // the thing the film drew (runtime/objectSlot); a `turns` object is handed the yaw
  sweep?: number;       // degrees turned across the beat, 20-360 (a flat object: at most 120)
  title?: string;       // what it is, under the platter
  note?: string;        // one line under the title
  kicker?: string;      // a spaced label in the title band
}> = ({object: OBJECT = DEMO_OBJECT, sweep = 80, title = '', note = '', kicker = ''} = {}) => {
  if (!(typeof sweep === 'number' && Number.isFinite(sweep) && sweep >= 20 && sweep <= 360)) {
    throw new Error(`ObjectTurntable: \`sweep\` is the turn in degrees, 20-360 — got ${JSON.stringify(sweep)}`);
  }
  const entry = useObjectEntry(OBJECT);
  const turns = entry.meta?.turns === true;
  if (!turns && sweep > 2 * MAX_CARD_TURN) {
    throw new Error(`ObjectTurntable: "${OBJECT.id}" is drawn flat, so it can turn at most ${2 * MAX_CARD_TURN}° ` +
      `(±${MAX_CARD_TURN}°) before its back faces the camera — give a sweep of ${2 * MAX_CARD_TURN} or less, or ` +
      'draw it in 3D from `yaw` and set META.turns (see objects/DemoForm).');
  }
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);

  const capW = Math.min(W * 0.84, 1240);
  const tLead = leading(title, 1.12), nLead = leading(note, 1.4);
  const titlePx = title ? fitBlockPx(title, capW, U * 0.12, Math.round(U * 0.048), {usable: 1, leading: tLead}) : 0;
  const titleH = title ? wrapLines(title, titlePx, capW) * titlePx * tLead : 0;
  const notePx = Math.round(U * 0.022);
  const noteH = note ? wrapLines(note, notePx, capW) * notePx * nLead : 0;
  const noteGap = title && note ? Math.round(U * 0.012) : 0;
  const wordsH = titleH + noteGap + noteH;
  const gap = wordsH ? Math.round(U * 0.035) : 0;

  // the object's room: as large as the words and the platter leave; the platter is a flattened ellipse under it
  const room = Math.max(U * 0.2, Math.min(W * 0.52, (zBot - zTop - U * 0.02 - gap - wordsH) / 1.13));
  const drawn = fitAspect({x: 0, y: 0, w: room, h: room}, entry.meta?.aspect);
  const pw = room * 1.15, ph = room * 0.22;
  const groupH = drawn.h + ph * 0.5 + gap + wordsH;
  const top0 = zTop + Math.max(U * 0.01, (zBot - zTop - groupH) / 2);
  const box = {x: (W - drawn.w) / 2, y: top0, w: drawn.w, h: drawn.h};
  const pcx = W / 2, pcy = box.y + box.h;                       // the object stands on the platter's centre line
  const wordsTop = pcy + ph * 0.5 + gap;

  const yawDeg = -sweep / 2 + sweep * easeInOutCubic(clamp01(seg(t, 0.08, 0.92)));
  const objT = clamp01(seg(t, 0.04, 0.4));
  const platIn = easeOutCubic(clamp01(seg(t, 0.02, 0.16)));
  const titleIn = easeOutCubic(clamp01(seg(t, 0.42, 0.6)));
  const noteIn = easeOutCubic(clamp01(seg(t, 0.48, 0.66)));
  const card = turns ? undefined : {
    transform: `perspective(${Math.round(room * 3)}px) rotateY(${Math.max(-MAX_CARD_TURN, Math.min(MAX_CARD_TURN, yawDeg))}deg)`,
    transformOrigin: '50% 100%'};
  const sw = Math.max(1, Math.round(U * 0.0025));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center', opacity: platIn,
          font: `600 ${Math.round(U * 0.018)}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      ) : null}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity: platIn}}>
        <ellipse cx={pcx} cy={pcy} rx={pw / 2} ry={ph / 2} fill={mix(SURF, FG, 0.04)} stroke={LINE} strokeWidth={sw} />
        {Array.from({length: TICKS}).map((_, k) => {   // @decor: the rim's marks carry the turn, not a reading
          const a = ((k * 360) / TICKS + yawDeg) * (Math.PI / 180);
          const front = Math.sin(a) > 0;
          const x = pcx + Math.cos(a) * (pw / 2), y = pcy + Math.sin(a) * (ph / 2);
          const x2 = pcx + Math.cos(a) * (pw / 2) * 0.92, y2 = pcy + Math.sin(a) * (ph / 2) * 0.92;
          return <line key={k} x1={x} y1={y} x2={x2} y2={y2} stroke={k === 0 ? ACC : LINE}
            strokeWidth={k === 0 ? sw * 2.5 : sw} opacity={front ? 0.95 : 0.35} />;
        })}
      </svg>
      <ObjectSlot object={OBJECT} box={box} t={objT} yaw={turns ? (yawDeg * Math.PI) / 180 : undefined} style={card} />
      {title ? (
        <div style={{position: 'absolute', left: (W - capW) / 2, top: wordsTop, width: capW, textAlign: 'center',
          opacity: titleIn, font: `700 ${titlePx}px/${tLead} ${disp}`, color: FG, textWrap: 'balance'}}>{title}</div>
      ) : null}
      {note ? (
        <div style={{position: 'absolute', left: (W - capW) / 2, top: wordsTop + titleH + noteGap, width: capW,
          textAlign: 'center', opacity: noteIn, font: `400 ${notePx}px/${nLead} ${bodyF}`, color: DIM}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default ObjectTurntable;
```

- [ ] **Step 5: Write the card** — `remotion/cards/ObjectTurntable.md`:

```markdown
# ObjectTurntable

**Identity:** a thing the film drew stands on a platter and turns, so its shape in the round is seen; the platter's rim marks the turn (one accent tick rides it), and the object's name sits under the platter.

**Use when:** the beat says "this is what it is like from every side": depth, a hidden face, the relation of a part at the back to one at the front. **Not when:** a front view carries the claim (`ObjectStage`); the object is a real photograph; the turn would show a flat drawing edge-on.

**Motion core:** the platter comes in over 0.02–0.16 while the object draws itself (its t over 0.04–0.4). The turn runs from −sweep/2 to +sweep/2 over 0.08–0.92, eased at both ends; the name lands over 0.42–0.66 and holds while it turns.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `object` | the thing the film drew — `{"id": …, "props": …}` | required in a film; an object whose META sets `turns` is handed the yaw and draws its own 3D (see objects/DemoForm); any other object is turned as a card |
| `sweep` | degrees turned across the beat, 20–360 | a flat object: at most 120 (±60°), past which its back would face the camera — refused, not flattened |
| `title` | what it is, under the platter | fitted to the width |
| `note` | one line under the title | what the turn reveals |
| `kicker` | a spaced label in the title band | follows the DNA's label casing |

**Known traps:**
- A card turn foreshortens the object's words too: keep an object's text off a turntable, or make it a `turns` object that keeps its type facing the camera.
- The object stands on the platter's centre line by its box's foot; an object with empty space at its foot looks like it hovers.

**Refuses:** a `sweep` outside 20–360; a sweep over 120 on an object that does not draw its own 3D; an object id nobody defines.

**Reference:** `remotion/src/shots/ObjectTurntable.tsx`

**Provenance:** motion-graphics (a beat holding an object is judged on the object's own world). **Family:** K.
```

- [ ] **Step 6: The catalogue** — replace the scaffold's placeholder line for ObjectTurntable (family K, keep its number) with:
```markdown
N. **ObjectTurntable** — a thing the film drew turns on a platter so its shape in the round is seen; a `turns` object draws its own 3D, any other turns as a card (±60°). *Use: "this is what it is like from every side".* `object, sweep, title, note, kicker` · `object` required in a film; sweep 20–360 (a flat object ≤ 120).
```

- [ ] **Step 7: Run the tests**

Run: `python3 -m pytest tests/test_object_turntable.py tests/test_shot_cards.py tests/test_library_signatures.py -q && python3 scripts/content_contract_qa.py ObjectTurntable && python3 scripts/register_shot.py ObjectTurntable --check && python3 scripts/text_safe_qa.py --library --only=ObjectTurntable --all-aspects`
Expected: PASS, no finding. Render the standalone preview at frames 20, 90 and 165 and LOOK: DemoForm's slabs turn in 3D (their sides change, not only their width), the accent tick rides the rim, nothing leaves the content zone at any yaw.

- [ ] **Step 8: Commit**

```bash
git add remotion/src/shots/ObjectTurntable.tsx remotion/cards/ObjectTurntable.md remotion/src/registry.ts remotion/src/Root.tsx remotion/src/runtime/shotLuma.ts scripts/shot_director.py remotion/LIBRARY.md tests/test_object_turntable.py
git commit -m "ObjectTurntable: a thing the film drew, turned so its shape is seen — in real 3D when it draws its own, as a card when it does not

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 12: The four stages measured, and the library whole again

**Files:**
- Modify (by the measurement scripts): `remotion/register_energy.json`, `remotion/prop_reach.json`, `remotion/_ground_luma.json`, `remotion/_ground_reach.json`, `remotion/src/runtime/shotLuma.ts`
- Modify: `remotion/cards/ObjectStage.md`, `ObjectCompare.md`, `ObjectPath.md`, `ObjectTurntable.md` (the Measured and Ground lines)

**Interfaces:**
- Consumes: Tasks 8–11.
- Produces: four fully measured, registered registers; a green full suite.

- [ ] **Step 1: Measure, in the order the device layer taught** (ground reach first — its emit adds each register's own row, which is in its energy and prop-reach hash; then both luma emits, which rewrite the register's own table rows; then the measurements that hash them). Nothing else may be editing registers or sweeping.

Run:
```bash
S=ObjectStage,ObjectCompare,ObjectPath,ObjectTurntable
python3 scripts/measure_ground_reach.py --only $S --emit
python3 scripts/measure_ground_luma.py --only $S --luma --emit
python3 scripts/measure_ground_luma.py --only $S --emit
python3 scripts/register_energy.py --only $S
python3 scripts/prop_reach.py --only $S
for s in ObjectStage ObjectCompare ObjectPath ObjectTurntable; do python3 scripts/cjk_type_qa.py --only $s --all-aspects; done
python3 scripts/measure_ground_reach.py --stale
```
Expected: the `SHOT_LUMA` and `DNA_GROUND_TOKEN` placeholders for the four are replaced with measured values; each manifest gains four rows; `--stale` lists nothing; `cjk_type_qa` exits 0 at every aspect (the previews carry no words; the fixtures feed the labels, titles and station names). A finding here is fixed in the register, then the measurements re-run from the top.

- [ ] **Step 2: Write the measured lines into the four cards** — read each register's row in `remotion/register_energy.json` and add, in the exact form the other cards use (numbers copied from the file, not restated from memory):
```markdown
**Measured:** <ink>% ink (clip median) · <footprint>% footprint · <motion> motion · <settled ink>% ink on the settled frame. Measured on the register's own preview — objects/DemoForm — so the numbers describe the stage with its preview form, not a film's object.
```
and complete each card's provenance line with `**Ground:** \`<token>\` (\`DNA_GROUND_TOKEN\`), measured <luma>.` from `remotion/src/runtime/shotLuma.ts`.

- [ ] **Step 3: Run the whole suite on this exact tree** (nothing else running)

Run: `python3 -m pytest tests -q -p no:cacheprovider`
Expected: every test passes; record the passed/skipped counts for the commit message. A failure in a library-wide test (census, headline count, luma coverage, energy freshness) names the register it is about — fix that, re-run.

- [ ] **Step 4: Commit**

```bash
git add remotion/register_energy.json remotion/prop_reach.json remotion/_ground_luma.json remotion/_ground_reach.json remotion/src/runtime/shotLuma.ts remotion/cards/ObjectStage.md remotion/cards/ObjectCompare.md remotion/cards/ObjectPath.md remotion/cards/ObjectTurntable.md
git commit -m "The four stage registers measured: ground reach, luminance, energy, prop reach, CJK type at every aspect

Full suite: <N> passed, <M> skipped.

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```
(Stage only the files Step 1 and Step 2 changed; fill in the real counts.)

---
### Task 13: `promote.py` — a delivered film's good thing joins the library

**Files:**
- Create: `scripts/promote.py`
- Test: `tests/test_promote.py`

**Interfaces:**
- Consumes: `workshop.shot_names`, `object_names`, `library_shot_names`, `library_object_names`, `workshop_dir`, `check`, `provenances`, `_IMPORT` (Task 2); `register_shot.register(shot, family, use_when, provenance)`, `register_shot.check(shot)`; `demo_copy_qa._declared_types(src, name)`; `storyboard.load/save`.
- Produces: `promote.PromoteError(problems)`; `preconditions(out_dir, name) -> (kind, src_path, entry, board)`; `library_source(text, kind, name) -> (text, problems)`; `prop_docs(src, name) -> (types, docs)`; `measurements(name) -> [[cmd...]]` (the order); `promote(out_dir, name, family=None, use_when=None, motion=None, dry_run=False, log=print) -> dict`; CLI `promote.py <out_dir> <Name> [--family X --use-when "…" --motion "…"] [--dry-run]`. Module paths `SHOTS`, `OBJECTS`, `CARDS`, `LIBRARY` and the hooks `_register`, `_run` exist so tests can redirect them.

- [ ] **Step 1: Write the failing tests** — `tests/test_promote.py`:

```python
"""promote.py moves a DELIVERED film's built thing into the library, and refuses — by name — anything else.

These tests redirect every library path into a sandbox and stub the registration and the measurement runs, so they
judge promote.py's own decisions: the preconditions, the rewritten source, the card, the catalogue, the object
index, the order of measurements, and what happens to the film. Task 21 runs a promotion for real."""
import json
import os
import shutil
import sys
import time

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import promote as pr  # noqa: E402
import workshop as ws  # noqa: E402

OBJ = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01} from '@runtime/motion';
export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};
export const %(name)s: React.FC<ObjectProps & {packed?: number}> = ({w, h, t, packed = 0}) => (
  <div style={{width: w, height: h * clamp01(t + packed)}} />
);
"""
SHOT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useT} from '@runtime/motion';
import {TermTable} from '@shots/TermTable';
export const DURATION = 150;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{
  title?: string;
  flow?: number;
}> = ({title = '', flow = 1}) => {
  const t = useT();
  return <AbsoluteFill>{title}{flow * t > 2 ? <TermTable /> : null}</AbsoluteFill>;
};
"""
DOCS = {"title?: string;": "title?: string;   // the curve's name — short, it heads the frame",
        "flow?: number;": "flow?: number;    // how fast the water moves, 0-3 — faster reads as pressure"}


def _film(tmp_path, delivered=True, name="EspressoPuck", kind="object", src=None):
    out = tmp_path / "film"
    d = out / "workshop" / (kind + "s")
    d.mkdir(parents=True)
    (d / (name + ".tsx")).write_text((src or (OBJ if kind == "object" else SHOT)) % {"name": name}, encoding="utf-8")
    board = {"meta": {"renderer": "remotion", "design_dna": "product", "title": "咖啡",
                      "build_list": [{"id": name, "kind": kind, "beats": [2], "slot": "ObjectStage" if kind == "object" else "own",
                                      "means": "water forced through a packed bed", "accept": "a viewer sees the bed resist"}]},
             "slides": [{"index": 2, "shot": "ObjectStage", "shot_props": {"object": {"id": name}}}]}
    (out / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    if delivered:
        time.sleep(0.01)
        (out / "out.mp4").write_bytes(b"\0")
    return str(out)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    lib = tmp_path / "lib"
    for sub in ("shots", "objects", "cards"):
        (lib / sub).mkdir(parents=True)
    shutil.copy(os.path.join(_ROOT, "remotion", "src", "objects", "index.ts"), str(lib / "objects" / "index.ts"))
    shutil.copy(os.path.join(_ROOT, "remotion", "LIBRARY.md"), str(lib / "LIBRARY.md"))
    monkeypatch.setattr(pr, "SHOTS", str(lib / "shots"))
    monkeypatch.setattr(pr, "OBJECTS", str(lib / "objects"))
    monkeypatch.setattr(pr, "CARDS", str(lib / "cards"))
    monkeypatch.setattr(pr, "LIBRARY", str(lib / "LIBRARY.md"))
    monkeypatch.setattr(ws, "check", lambda out_dir: [])
    calls = {"register": [], "run": []}

    def fake_register(name, family, use_when, provenance):
        calls["register"].append((name, family, use_when, provenance))
        with open(str(lib / "LIBRARY.md"), "a", encoding="utf-8") as fh:
            fh.write("\n999. **%s** — %s *Use: %s*\n" % (name, use_when, use_when))
    monkeypatch.setattr(pr, "_register", fake_register)
    monkeypatch.setattr(pr, "_run", lambda cmd, log=print: calls["run"].append(cmd[1:]))
    monkeypatch.setattr(pr, "_measured_line", lambda name: "**Measured:** 5.0% ink (clip median) · 40.0% footprint · 0.004 motion.")
    return lib, calls


def test_an_undelivered_film_is_refused(tmp_path, sandbox):
    out = _film(tmp_path, delivered=False)
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "EspressoPuck")
    assert any("no out.mp4" in p for p in e.value.problems)


def test_a_film_the_critic_has_not_passed_is_refused(tmp_path, sandbox):
    out = _film(tmp_path)
    open(os.path.join(out, "NOT_DELIVERED.md"), "w").close()
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "EspressoPuck")
    assert any("NOT_DELIVERED.md" in p for p in e.value.problems)


def test_an_item_changed_after_the_render_is_refused(tmp_path, sandbox):
    out = _film(tmp_path)
    time.sleep(0.02)
    p = os.path.join(ws.workshop_dir(out), "objects", "EspressoPuck.tsx")
    open(p, "a").write("\n// tweaked after delivery\n")
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "EspressoPuck")
    assert any("changed after the film was rendered" in x for x in e.value.problems)


def test_an_item_not_on_the_build_list_or_already_in_the_library_is_refused(tmp_path, sandbox, monkeypatch):
    out = _film(tmp_path, name="TermTable", kind="shot")
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "TermTable", family="I", use_when="x", motion="y")
    assert any("already has TermTable" in p for p in e.value.problems)


def test_an_object_moves_into_the_library_index_and_catalogue_and_the_film_follows_it(tmp_path, sandbox):
    lib, calls = sandbox
    out = _film(tmp_path)
    pr.promote(out, "EspressoPuck")
    src = open(str(lib / "objects" / "EspressoPuck.tsx"), encoding="utf-8").read()
    assert "from '../runtime/objectSlot'" in src and "from '../runtime/motion'" in src and "@runtime" not in src
    idx = open(str(lib / "objects" / "index.ts"), encoding="utf-8").read()
    assert "import * as O_EspressoPuck from './EspressoPuck';" in idx
    assert "EspressoPuck: {C: O_EspressoPuck.EspressoPuck, meta: O_EspressoPuck.META}," in idx
    cat = open(str(lib / "LIBRARY.md"), encoding="utf-8").read()
    assert "- **EspressoPuck** — water forced through a packed bed" in cat.split(pr.OBJECTS_ANCHOR)[1]
    assert not os.path.exists(os.path.join(ws.workshop_dir(out), "objects", "EspressoPuck.tsx"))
    entry = json.load(open(os.path.join(out, "storyboard.json")))["meta"]["build_list"][0]
    assert entry["promoted"] is True
    assert calls["register"] == [] and calls["run"] == []          # an object is catalogued, not measured


def test_a_shot_is_registered_carded_measured_in_order_and_the_film_follows_it(tmp_path, sandbox):
    lib, calls = sandbox
    src = SHOT
    for a, b in DOCS.items():
        src = src.replace(a, b)
    out = _film(tmp_path, name="ExtractionCurve", kind="shot", src=src)
    pr.promote(out, "ExtractionCurve", family="I", use_when="how flow changes through a shot", motion="the curve draws, then holds")
    code = open(str(lib / "shots" / "ExtractionCurve.tsx"), encoding="utf-8").read()
    assert "from '../runtime/motion'" in code and "from './TermTable'" in code
    assert "export const GROUND" not in code and "export const PROVENANCE" not in code
    assert calls["register"] == [("ExtractionCurve", "I", "how flow changes through a shot", "industrial")]
    assert calls["run"] == [c[1:] for c in pr.measurements("ExtractionCurve")], calls["run"]
    order = [c[0].split("/")[-1] for c in calls["run"]]
    assert order.index("measure_ground_reach.py") < order.index("measure_ground_luma.py") < order.index("register_energy.py")
    assert order.index("register_energy.py") < order.index("cjk_type_qa.py")
    card = open(str(lib / "cards" / "ExtractionCurve.md"), encoding="utf-8").read()
    for part in ("# ExtractionCurve\n", "**Identity:** water forced through a packed bed", "**Use when:** how flow changes",
                 "**Motion core:** the curve draws, then holds", "| `title` | the curve's name", "| `flow` | how fast",
                 "faster reads as pressure", "**Known traps:**", "`remotion/src/shots/ExtractionCurve.tsx`",
                 "**Measured:** 5.0% ink", "**Provenance:** industrial. **Family:** I."):
        assert part in card, (part, card)
    assert "999. **ExtractionCurve** — water forced through a packed bed *Use: how flow changes through a shot.*" in \
        open(str(lib / "LIBRARY.md"), encoding="utf-8").read()
    assert not os.path.exists(os.path.join(ws.workshop_dir(out), "shots", "ExtractionCurve.tsx"))


def test_a_shot_with_an_undocumented_prop_is_refused(tmp_path, sandbox):
    out = _film(tmp_path, name="ExtractionCurve", kind="shot")
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "ExtractionCurve", family="I", use_when="x", motion="y")
    assert any("`title`" in p and "comment" in p for p in e.value.problems), e.value.problems


def test_a_shot_needs_its_family_use_and_motion(tmp_path, sandbox):
    out = _film(tmp_path, name="ExtractionCurve", kind="shot")
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "ExtractionCurve")
    assert any("--family" in p for p in e.value.problems)


def test_an_import_the_library_cannot_resolve_is_refused(tmp_path):
    text, probs = pr.library_source("import {R} from './puckGeometry';\nimport art from '../assets/a.png';\n"
                                    "import {seg} from '@runtime/motion';\nimport {X} from '@shots/NoSuchShot';\n",
                                    "object", "EspressoPuck")
    assert "from '../runtime/motion'" in text
    assert any("./puckGeometry" in p for p in probs) and any("../assets/a.png" in p for p in probs), probs
    assert any("NoSuchShot" in p for p in probs), probs


def test_dry_run_changes_nothing(tmp_path, sandbox):
    lib, calls = sandbox
    out = _film(tmp_path)
    before = sorted(os.listdir(str(lib / "objects")))
    plan = pr.promote(out, "EspressoPuck", dry_run=True)
    assert plan["kind"] == "object" and sorted(os.listdir(str(lib / "objects"))) == before
    assert os.path.exists(os.path.join(ws.workshop_dir(out), "objects", "EspressoPuck.tsx"))
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_promote.py -q`
Expected: FAIL — `No module named 'promote'`.

- [ ] **Step 3: Write it** — `scripts/promote.py`:

```python
#!/usr/bin/env python3
"""PROMOTE a built thing from a delivered film into the library — the user's choice, never automatic.

    python3 scripts/promote.py <out_dir> <Name> --family <X> --use-when "<one line>" --motion "<one line>"   # a shot
    python3 scripts/promote.py <out_dir> <Name>                                                               # an object
    python3 scripts/promote.py <out_dir> <Name> ... --dry-run                                                 # say what it would do

WHY. A film builds what it needs in its own workshop (scripts/workshop.py) and the library stays measured and
unpolluted. When a built thing turns out to be good — the USER says so at delivery — it moves into the library here
and pays what a library register pays: registration at every sync point (register_shot.py), measurement in the order
the device layer taught — ground reach, then both ground-luma emits, then energy and prop reach, then CJK type at
every aspect (each emit rewrites the register's own row, which the later measurements hash) — and a card written
from its build-list entry and its props' own comments. An object goes to remotion/src/objects/, into the library's
object index and its catalogue section. The film then uses the library's copy: its workshop copy is removed and its
build-list entry marked `promoted`.

REFUSED, never guessed: a film that is not delivered (no out.mp4, or NOT_DELIVERED.md still there — the critic has
not passed it); an item changed after that render; an item the workshop check fails; an item not on the build list;
a name the library already has; a shot without --family/--use-when/--motion; an import the library cannot resolve (a
workshop helper, an asset); a shot prop with no trailing comment (the card's table is written from them).
If a measurement fails, the register is left registered but not fully measured, and the message names the steps that
remain — `git status` lists every library file promote touched.
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import workshop as ws  # noqa: E402

SKILL = os.path.dirname(_HERE)
REMOTION = os.path.join(SKILL, "remotion")
SHOTS = os.path.join(REMOTION, "src", "shots")
OBJECTS = os.path.join(REMOTION, "src", "objects")
CARDS = os.path.join(REMOTION, "cards")
LIBRARY = os.path.join(REMOTION, "LIBRARY.md")
OBJECTS_ANCHOR = "<!-- OBJECTS (scripts/promote.py appends below) -->"


class PromoteError(RuntimeError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _write(p, text):
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


def preconditions(out_dir, name):
    """(kind, source path, build-list entry, board) — or PromoteError naming EVERY reason it may not be promoted."""
    probs = []
    mp4 = os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(mp4):
        probs.append("the film has no out.mp4 — promote from a delivered film")
    if os.path.exists(os.path.join(out_dir, "NOT_DELIVERED.md")):
        probs.append("NOT_DELIVERED.md is still there — the critic has not passed this film "
                     "(critic_ledger.py --final removes it when the review passes)")
    kind = "shot" if name in ws.shot_names(out_dir) else ("object" if name in ws.object_names(out_dir) else None)
    if kind is None:
        raise PromoteError(probs + ["%s is not in this film's workshop" % name])
    src = os.path.join(ws.workshop_dir(out_dir), kind + "s", name + ".tsx")
    if os.path.isfile(mp4) and os.path.getmtime(src) > os.path.getmtime(mp4):
        probs.append("%s changed after the film was rendered — re-render and re-review the film before promoting"
                     % os.path.relpath(src, out_dir))
    if name in ws.library_shot_names() or name in ws.library_object_names() or \
            os.path.exists(os.path.join(SHOTS, name + ".tsx")) or os.path.exists(os.path.join(OBJECTS, name + ".tsx")):
        probs.append("the library already has %s" % name)
    probs += [p for p in ws.check(out_dir) if ("/%s.tsx" % name) in p]
    board = json.loads(_read(os.path.join(out_dir, "storyboard.json")))
    entry = next((e for e in (board.get("meta") or {}).get("build_list") or []
                  if isinstance(e, dict) and e.get("id") == name), None)
    if entry is None:
        probs.append("%s is not on this film's meta.build_list — only a built thing with a stated purpose is promoted"
                     % name)
    if probs:
        raise PromoteError(probs)
    return kind, src, entry, board


def library_source(text, kind, name):
    """The workshop source as library code: `@runtime/` and `@shots/` become relative imports. A relative import
    in workshop code names a workshop file or asset, which the library cannot resolve — refused by name, as is an
    alias naming nothing. A shot's GROUND and PROVENANCE declarations (and the comment lines directly above them)
    are dropped: the library MEASURES the ground, and the provenance goes to shot_director."""
    probs = []
    for spec in ws._IMPORT.findall(text):
        if spec.startswith("@runtime/"):
            mod = spec[len("@runtime/"):]
            if not any(os.path.isfile(os.path.join(ws.RUNTIME, mod + e)) for e in ("", ".ts", ".tsx", ".json")):
                probs.append("%s imports %s — there is no runtime module %r" % (name, spec, mod))
        elif spec.startswith("@shots/"):
            if spec[len("@shots/"):] not in ws.library_shot_names():
                probs.append("%s imports %s — there is no library register %r" % (name, spec, spec[len("@shots/"):]))
        elif spec.startswith("."):
            probs.append("%s imports %r — a workshop file or asset the library cannot resolve; inline it, or promote "
                         "it first" % (name, spec))
    shots_rel = "./" if kind == "shot" else "../shots/"
    out = text.replace("'@runtime/", "'../runtime/").replace('"@runtime/', '"../runtime/')
    out = out.replace("'@shots/", "'" + shots_rel).replace('"@shots/', '"' + shots_rel)
    if kind == "shot":
        out = re.sub(r"(?:^[ \t]*//[^\n]*\n)*^export const (?:GROUND|PROVENANCE)\b[^\n]*\n", "", out, flags=re.M)
    return out, probs


def prop_docs(src, name):
    """({prop: type}, {prop: (what it sets, feel of turning it)}) from the trailing comment on each prop."""
    import demo_copy_qa as dq
    types = dq._declared_types(src, name) or {}
    docs = {}
    for ln in src.splitlines():
        m = re.match(r"\s*(\w+)\??\s*:[^/\n]*;\s*//\s*(.+?)\s*$", ln)
        if m and m.group(1) in types:
            what, _sep, feel = m.group(2).partition(" — ")
            docs[m.group(1)] = (what.strip(), feel.strip() or "—")
    return types, docs


def measurements(name):
    """The order a new register is measured in — every emit that rewrites its own row before what hashes it."""
    py = sys.executable
    return [[py, "scripts/measure_ground_reach.py", "--only", name, "--emit"],
            [py, "scripts/measure_ground_luma.py", "--only", name, "--luma", "--emit"],
            [py, "scripts/measure_ground_luma.py", "--only", name, "--emit"],
            [py, "scripts/register_energy.py", "--only", name],
            [py, "scripts/prop_reach.py", "--only", name],
            [py, "scripts/cjk_type_qa.py", "--only", name, "--all-aspects"],
            [py, "scripts/measure_ground_reach.py", "--stale"]]


def _register(name, family, use_when, provenance):
    import register_shot as rs
    rs.register(name, family, use_when=use_when, provenance=provenance)
    missing = rs.check(name)
    if missing:
        raise PromoteError(["register_shot left %s unregistered in %s" % (name, ", ".join(missing))])


def _run(cmd, log=print):
    import subprocess
    log("[promote] $ " + " ".join(cmd[1:]))
    r = subprocess.run(cmd, cwd=SKILL)
    if r.returncode != 0:
        raise PromoteError(["`%s` exited %d" % (" ".join(cmd[1:]), r.returncode)])


def _measured_line(name):
    row = (json.loads(_read(os.path.join(REMOTION, "register_energy.json"))).get("registers") or {}).get(name)
    if not row:
        raise PromoteError(["register_energy.json has no row for %s after its measurement" % name])
    return ("**Measured:** %.1f%% ink (clip median) · %.1f%% footprint · %s motion. Measured on the register's own "
            "defaults." % (row["ink_median"] * 100, row["footprint"] * 100, row["motion_p75"]))


def _card(name, entry, use_when, motion, types, docs, provenance, family, film):
    rows = "\n".join("| `%s` | %s | %s |" % (p, docs[p][0], docs[p][1]) for p in sorted(types))
    return ("# %s\n\n**Identity:** %s\n\n**Use when:** %s.\n\n**Motion core:** %s\n\n"
            "| Prop | What it sets | Feel of turning it |\n|---|---|---|\n%s\n\n"
            "**Known traps:**\n- Promoted from the film %s, where it was judged against: %s. The first film that meets "
            "a trap here writes it down.\n\n**Reference:** `remotion/src/shots/%s.tsx`\n\n"
            "**Provenance:** %s. **Family:** %s.\n"
            % (name, entry["means"], use_when.rstrip("."), motion, rows, film, entry["accept"], name, provenance, family))


def _index_object(name):
    p = os.path.join(OBJECTS, "index.ts")
    s = _read(p)
    imports = list(re.finditer(r"^import .*;$", s, re.M))
    at = imports[-1].end() if imports else 0
    s = s[:at] + "\nimport * as O_%s from './%s';" % (name, name) + s[at:]
    m = re.search(r"export const LIBRARY_OBJECTS[^=]*=\s*\{\n", s)
    if not m:
        raise PromoteError(["objects/index.ts has no LIBRARY_OBJECTS map to add %s to" % name])
    end = s.index("};", m.end())
    _write(p, s[:end] + "  %s: {C: O_%s.%s, meta: O_%s.META},\n" % (name, name, name, name) + s[end:])


def _catalogue_shot(name, entry, use_when, types, film):
    s = _read(LIBRARY)
    m = re.search(r"^(\d+)\. \*\*%s\*\* — .*$" % re.escape(name), s, re.M)
    if not m:
        raise PromoteError(["register_shot wrote no LIBRARY.md entry for %s" % name])
    line = "%s. **%s** — %s *Use: %s.* `%s` · built for the film %s." % (
        m.group(1), name, entry["means"], use_when.rstrip("."), ", ".join(sorted(types)), film)
    _write(LIBRARY, s[:m.start()] + line + s[m.end():])


def _catalogue_object(name, entry, props, film):
    s = _read(LIBRARY)
    if OBJECTS_ANCHOR not in s:
        raise PromoteError(["LIBRARY.md has no objects section (%s)" % OBJECTS_ANCHOR])
    line = "- **%s** — %s *Built for the film %s.*%s" % (
        name, entry["means"], film, (" `%s`" % ", ".join(sorted(props))) if props else "")
    _write(LIBRARY, s.rstrip("\n") + "\n" + line + "\n")


def promote(out_dir, name, family=None, use_when=None, motion=None, dry_run=False, log=print):
    kind, src_path, entry, board = preconditions(out_dir, name)
    film = (board.get("meta") or {}).get("title") or os.path.basename(os.path.abspath(out_dir))
    src = _read(src_path)
    dest_dir = SHOTS if kind == "shot" else OBJECTS
    text, probs = library_source(src, kind, name)
    types, docs = prop_docs(src, name)
    provenance = ws.provenances(out_dir).get(name)
    if kind == "shot":
        for flag, v in (("--family", family), ("--use-when", use_when), ("--motion", motion)):
            if not str(v or "").strip():
                probs.append("a shot needs %s — its catalogue entry and card are written from it" % flag)
        for p in sorted(set(types) - set(docs)):
            probs.append("`%s` has no trailing comment in %s's props type — the card's table is written from them "
                         "(`%s?: T;   // what it sets — the feel of turning it`)" % (p, name, p))
    if probs:
        raise PromoteError(probs)
    plan = {"kind": kind, "to": os.path.join(dest_dir, name + ".tsx"), "measure": measurements(name) if kind == "shot" else []}
    if dry_run:
        log("[promote] would move %s (%s) into %s%s" % (name, kind, plan["to"],
            "; then register and measure it" if kind == "shot" else "; then index and catalogue it"))
        return plan
    _write(plan["to"], text)
    if kind == "shot":
        _register(name, family, use_when, provenance)
        _catalogue_shot(name, entry, use_when, types, film)
        for cmd in plan["measure"]:
            try:
                _run(cmd, log=log)
            except PromoteError as e:
                left = [" ".join(c[1:]) for c in plan["measure"][plan["measure"].index(cmd):]]
                raise PromoteError(e.problems + ["%s is registered but NOT fully measured; run, in order: %s"
                                                 % (name, "; ".join(left))])
        _write(os.path.join(CARDS, name + ".md"),
               _card(name, entry, use_when, motion, types, docs, provenance, family, film)
               .replace("**Provenance:**", _measured_line(name) + "\n\n**Provenance:**"))
    else:
        _index_object(name)
        _catalogue_object(name, entry, sorted(k for k in types if k not in ("w", "h", "t", "dna", "yaw")), film)
    # the film now uses the library's copy
    import storyboard as sb
    os.remove(src_path)
    for e in board["meta"]["build_list"]:
        if isinstance(e, dict) and e.get("id") == name:
            e["promoted"] = True
    sb.save(board, os.path.join(out_dir, "storyboard.json"))
    log("[promote] %s is in the library (%s). NEXT: python3 -m pytest tests -q -p no:cacheprovider" % (name, plan["to"]))
    return plan


def main(argv=None):
    ap = argparse.ArgumentParser(description="Promote a delivered film's built thing into the library.")
    ap.add_argument("out_dir")
    ap.add_argument("name")
    ap.add_argument("--family")
    ap.add_argument("--use-when")
    ap.add_argument("--motion")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        promote(a.out_dir, a.name, a.family, a.use_when, a.motion, a.dry_run)
        return 0
    except PromoteError as e:
        for p in e.problems:
            print("  REFUSED: " + p)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

The `_declared_types` reader gives an object's props including the slot keys (`w`, `h`, `t`, `dna`, `yaw` come from `ObjectProps` only when written inline); the object catalogue line lists the film-facing props only.

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/test_promote.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/promote.py tests/test_promote.py
git commit -m "promote.py: a delivered film's built thing joins the library — registered, measured in order, carded — or is refused by name

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---
### Task 14: What a builder reads — the building blocks, and how to make an object that means something

**Files:**
- Create: `references/building-blocks.md`, `references/object-authoring.md`
- Create: `references/object-examples/PuckInSection.tsx`, `StrataOverTime.tsx`, `ComposeScreen.tsx` (good), `ChromeMachine.tsx`, `LabeledPuck.tsx`, `SwirlOfCoffee.tsx` (bad), and their rendered `*.png`
- Create: `scripts/object_examples.py`
- Test: `tests/test_building_blocks_doc.py`, `tests/test_object_examples.py`

**Interfaces:**
- Consumes: every runtime module (read-only); `workshop.write_index`, `workshop.check`, `workshop.workshop_dir`, `workshop.run_kwargs` (Task 2); `ObjectStage` (Task 8).
- Produces: `references/building-blocks.md` with one `### \`<module>\`` section per runtime module and a `## Recipes` section; `references/object-authoring.md`; `python3 scripts/object_examples.py` → the six PNGs.

- [ ] **Step 1: Write the failing tests**

`tests/test_building_blocks_doc.py`:
```python
"""references/building-blocks.md covers EVERY runtime module a film's code can import — by the module's own name,
naming exports that really exist — because half of them used to be discoverable only from their source headers."""
import glob
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(_ROOT, "remotion", "src", "runtime")
DOC = os.path.join(_ROOT, "references", "building-blocks.md")


def _modules():
    """{module: its exports} — code modules by name, data files (deviceSpec.json) by file name and top-level keys."""
    import json
    out = {}
    for p in sorted(glob.glob(os.path.join(RUNTIME, "*.ts")) + glob.glob(os.path.join(RUNTIME, "*.tsx"))):
        name = os.path.basename(p).rsplit(".", 1)[0]
        if name.startswith("__probe"):
            continue
        out[name] = set(re.findall(r"^export (?:const|function|type) ([A-Za-z_]\w*)", open(p, encoding="utf-8").read(), re.M))
    for p in sorted(glob.glob(os.path.join(RUNTIME, "*.json"))):
        out[os.path.basename(p)] = set(json.load(open(p, encoding="utf-8")))
    return out


def _sections():
    doc = open(DOC, encoding="utf-8").read().split("## Recipes", 1)[0]     # the recipes name many modules on purpose
    parts = re.split(r"^### `([\w.]+)`\s*$", doc, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def test_every_runtime_module_has_a_section():
    missing = sorted(set(_modules()) - set(_sections()))
    assert not missing, "runtime modules the builder cannot read about: %s" % missing


def test_every_section_names_exports_that_exist():
    mods, secs = _modules(), _sections()
    bad = {}
    for name, body in secs.items():
        if name not in mods:
            bad[name] = "no such runtime module"
            continue
        named = set(re.findall(r"`(\w+)`", body))
        if not (named & mods[name]):
            bad[name] = "names none of its exports (%s)" % ", ".join(sorted(mods[name])[:8])
        ghosts = sorted(n for n in named - mods[name] if re.match(r"^[a-z][A-Za-z0-9]+$|^[A-Z][A-Z0-9_]+$", n)
                        and n in {e for m in mods.values() for e in m} and n not in mods[name])
        if ghosts:
            bad[name] = "names exports of OTHER modules as its own: %s" % ghosts
    assert not bad, bad


def test_the_recipes_the_films_keep_needing_are_written():
    doc = open(DOC, encoding="utf-8").read()
    recipes = doc.split("## Recipes", 1)[1]
    for r in ("A mechanism in cutaway", "Liquid or particles along a path", "A turntable", "Layered strata",
              "A route on a map", "An interface being operated"):
        assert "### " + r in recipes, r
```

`tests/test_object_examples.py`:
```python
"""The object-authoring examples do what the doc says they do: the three good ones pass every check a film's code
must pass; the one with words written into it is refused; and the two that MEAN nothing pass every check too —
which is the reason a critic looks at every built thing (agents/shot-critic.md S15)."""
import os
import shutil
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import workshop as ws  # noqa: E402

EX = os.path.join(_ROOT, "references", "object-examples")
GOOD, BAD_WORDS, BAD_MEANING = ["PuckInSection", "StrataOverTime", "ComposeScreen"], ["LabeledPuck"], \
    ["ChromeMachine", "SwirlOfCoffee"]
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_ROOT, "remotion", "node_modules")),
                                     reason="needs the remotion toolchain")


def _film(tmp_path, names):
    d = tmp_path / "film" / "workshop" / "objects"
    d.mkdir(parents=True)
    for n in names:
        shutil.copy(os.path.join(EX, n + ".tsx"), str(d / (n + ".tsx")))
    return str(tmp_path / "film")


@needs_toolchain
def test_the_good_examples_pass_every_check(tmp_path):
    assert ws.check(_film(tmp_path, GOOD)) == []


@needs_toolchain
def test_words_written_into_an_object_are_refused(tmp_path):
    probs = ws.check(_film(tmp_path, BAD_WORDS))
    assert any("LabeledPuck.tsx" in p and "粉饼" in p for p in probs), probs


@needs_toolchain
def test_objects_that_mean_nothing_pass_every_check_which_is_why_a_critic_looks(tmp_path):
    assert ws.check(_film(tmp_path, BAD_MEANING)) == []


def test_the_doc_shows_every_example_rendered():
    doc = open(os.path.join(_ROOT, "references", "object-authoring.md"), encoding="utf-8").read()
    for n in GOOD + BAD_WORDS + BAD_MEANING:
        assert "object-examples/%s.png" % n in doc and os.path.getsize(os.path.join(EX, n + ".png")) > 5000, n
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_building_blocks_doc.py tests/test_object_examples.py -q`
Expected: FAIL — neither doc nor the examples exist.

- [ ] **Step 3: The six examples** — `references/object-examples/`:

`PuckInSection.tsx` (GOOD — a mechanism in cutaway):
```tsx
// GOOD — A MECHANISM IN CUTAWAY. It ENCODES "water is forced through a packed bed": caption hidden, a viewer sees
// drops enter at the top and fight down through a dense layer — and the denser the layer (`packed`, 0..1) the thinner
// the bed, the fewer drops get through and the slower they go. It draws no words: the stage names the parts.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01, seg, easeOutCubic, hash01} from '@runtime/motion';
import {pointAt} from '@runtime/alongPath';
import {mix} from '@runtime/dna';

export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};

export const PuckInSection: React.FC<ObjectProps & {packed?: number}> = ({w, h, t, dna, packed = 0.8}) => {
  if (!(typeof packed === 'number' && packed >= 0 && packed <= 1)) {
    throw new Error(`PuckInSection: \`packed\` is 0..1 — got ${JSON.stringify(packed)}`);
  }
  const ink = dna?.fg ?? '#1c2230', acc = dna?.accent ?? '#3563e9', paper = dna?.surface ?? '#e9edf3';
  const wall = Math.max(3, w * 0.012);
  const x0 = w * 0.18, x1 = w * 0.82, top = h * 0.3, bot = h * 0.78;
  const bedTop = bot - (bot - top) * (0.55 - 0.25 * packed);     // packed harder, the bed is thinner and denser
  const bedIn = easeOutCubic(clamp01(seg(t, 0, 0.3)));
  const grains = Math.round(160 + 340 * packed);
  const lanes = 7, passing = Math.round(lanes * (1 - 0.6 * packed));
  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      <path d={`M ${x0} ${top} L ${x0} ${bot} L ${x1} ${bot} L ${x1} ${top}`} fill="none" stroke={ink}
        strokeWidth={wall} strokeLinejoin="round" />
      <rect x={x0} y={bedTop} width={x1 - x0} height={bot - bedTop} fill={mix(paper, ink, 0.25 + 0.35 * packed)}
        opacity={bedIn} />
      {Array.from({length: grains}).map((_, i) => (   // @decor: stipple texture; its density follows `packed`
        <circle key={i} cx={x0 + (x1 - x0) * hash01(i * 2 + 1)} cy={bedTop + (bot - bedTop) * hash01(i * 2 + 2)}
          r={w * 0.004} fill={ink} opacity={0.35 * bedIn} />
      ))}
      {Array.from({length: lanes}).map((_, k) => {
        const x = x0 + ((x1 - x0) * (k + 0.5)) / lanes;
        const d = `M ${x} ${h * 0.08} L ${x} ${bot + h * 0.12}`;
        // @positional: how MANY lanes pass follows `packed`; which ones is the order they are drawn in
        const through = k < passing;
        const u = clamp01(seg(t, 0.25 + k * 0.03, 0.25 + k * 0.03 + 0.35 + 0.35 * packed));
        const stop = through ? 1 : (bedTop - h * 0.08) / (bot + h * 0.04);
        const p = pointAt(d, Math.min(u, stop));
        return <circle key={k} cx={p.x} cy={p.y} r={w * 0.02} fill={acc} opacity={u > 0 ? 1 : 0} />;
      })}
    </svg>
  );
};
```

`StrataOverTime.tsx` (GOOD — layered strata):
```tsx
// GOOD — LAYERED STRATA. It ENCODES "each era was laid on the last": caption hidden, a viewer sees a column grow
// layer by layer from the bottom, each as thick as the film says it was (`layers`, oldest first), the newest on
// top in the accent. The stage's labels name the eras; the object draws only what the numbers say.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01, seg, easeOutCubic} from '@runtime/motion';
import {mix} from '@runtime/dna';

export const META: ObjectMeta = {aspect: 0.8, provenance: 'survey-archive'};

export const StrataOverTime: React.FC<ObjectProps & {layers?: number[]}> = ({w, h, t, dna, layers = []}) => {
  if (!Array.isArray(layers) || layers.length < 1 || layers.some((v) => !(typeof v === 'number' && v > 0))) {
    throw new Error('StrataOverTime: `layers` is a list of positive thicknesses, oldest first — got ' +
      JSON.stringify(layers));
  }
  const ink = dna?.fg ?? '#1c2230', acc = dna?.accent ?? '#3563e9', paper = dna?.surface ?? '#e9edf3';
  const total = layers.reduce((a, b) => a + b, 0);
  const n = layers.length;
  let y = h;
  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      {layers.map((v, i) => {
        const th = (v / total) * h * 0.96;
        y -= th;
        const on = easeOutCubic(clamp01(seg(t, (i / n) * 0.8, (i / n) * 0.8 + 0.2)));
        // @positional: the last layer is the newest — the order of the list is time
        const newest = i === n - 1;
        return <rect key={i} x={w * 0.1} y={y - (1 - on) * h * 0.05} width={w * 0.8} height={th}
          fill={newest ? acc : mix(paper, ink, 0.12 + (0.5 * i) / Math.max(1, n - 1))} opacity={on}
          stroke={ink} strokeWidth={Math.max(1, w * 0.003)} />;
      })}
    </svg>
  );
};
```

`ComposeScreen.tsx` (GOOD — an interface being operated, for a device's screen):
```tsx
// GOOD — AN INTERFACE BEING OPERATED, drawn for a device's screen (DeviceDemo `{"screen": {"object": …}}`). It
// ENCODES "you write it, it sends": the draft types itself in and the send button lights when it is done. Every
// word — the recipient, the draft, the button — comes from props, so the film writes them in its own language.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01, seg} from '@runtime/motion';
import {mix} from '@runtime/dna';
import {onAccentInk} from '@runtime/onAccent';

export const META: ObjectMeta = {aspect: 9 / 19.5, provenance: 'product-ui'};

export const ComposeScreen: React.FC<ObjectProps & {to?: string; draft?: string; send?: string}> =
  ({w, h, t, dna, to = '', draft = '', send = ''}) => {
  const surf = dna?.surface ?? '#ffffff', ink = dna?.fg ?? '#14171c', dim = dna?.dim ?? '#5b6472';
  const acc = dna?.accent ?? '#3563e9';
  const chars = [...draft];
  // @truncates: typing — every character of the draft has arrived by t = 0.7
  const typed = chars.slice(0, Math.round(chars.length * clamp01(seg(t, 0.15, 0.7)))).join('');
  const sent = t > 0.82;
  const px = Math.round(w * 0.055);
  return (
    <div style={{width: w, height: h, background: surf, position: 'relative', font: `400 ${px}px/1.5 var(--f-body, Inter, sans-serif)`}}>
      <div style={{position: 'absolute', left: w * 0.07, right: w * 0.07, top: h * 0.07, color: dim, fontSize: px * 0.8,
        borderBottom: `1px solid ${mix(surf, ink, 0.15)}`, paddingBottom: px * 0.4}}>{to}</div>
      <div style={{position: 'absolute', left: w * 0.07, right: w * 0.07, top: h * 0.15, color: ink}}>{typed}</div>
      <div style={{position: 'absolute', right: w * 0.07, bottom: h * 0.05, padding: `${px * 0.4}px ${px * 0.9}px`,
        borderRadius: px, fontWeight: 700, fontSize: px * 0.8,
        background: sent ? acc : mix(surf, ink, 0.1), color: sent ? onAccentInk(acc) : dim}}>{send}</div>
    </div>
  );
};
```

`ChromeMachine.tsx` (BAD — an imitation of a photograph):
```tsx
// BAD — AN IMITATION OF A PHOTOGRAPH. Gradients and a highlight dressing up an espresso machine: it looks like
// clip-art, it shows no mechanism, and it competes with the real thing a documentary image would show. When a
// beat needs the machine as it LOOKS, composite a real, credited image (references/remotion-shot-authoring.md,
// the documentary tier); when it needs how it WORKS, draw the mechanism (PuckInSection). It passes every gate.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';

export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};

export const ChromeMachine: React.FC<ObjectProps> = ({w, h}) => (
  <svg width={w} height={h} style={{display: 'block'}}>
    <defs>
      <linearGradient id="chrome" x1="0" x2="1">
        <stop offset="0" stopColor="#6b6f76" /><stop offset="0.45" stopColor="#f4f6f9" /><stop offset="1" stopColor="#50545b" />
      </linearGradient>
    </defs>
    <rect x={w * 0.15} y={h * 0.15} width={w * 0.7} height={h * 0.6} rx={w * 0.04} fill="url(#chrome)" />
    <circle cx={w * 0.5} cy={h * 0.5} r={w * 0.09} fill="#2b2e33" />
    <ellipse cx={w * 0.38} cy={h * 0.25} rx={w * 0.12} ry={h * 0.03} fill="#ffffff" opacity={0.6} />
    <rect x={w * 0.2} y={h * 0.78} width={w * 0.6} height={h * 0.05} fill="#3a3d42" />
  </svg>
);
```

`LabeledPuck.tsx` (BAD — words written into the object):
```tsx
// BAD — WORDS WRITTEN INTO THE OBJECT. The bed and the water are named in Chinese in the code itself, so a film in
// any other language prints Chinese, and no prop can change them. scripts/workshop.py check refuses it.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';

export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};

export const LabeledPuck: React.FC<ObjectProps> = ({w, h, dna}) => (
  <svg width={w} height={h} style={{display: 'block'}}>
    <rect x={w * 0.2} y={h * 0.55} width={w * 0.6} height={h * 0.2} fill={dna?.fg ?? '#1c2230'} opacity={0.5} />
    <text x={w * 0.5} y={h * 0.68} textAnchor="middle" fontSize={w * 0.06} fill={dna?.bg ?? '#ffffff'}>粉饼</text>
    <text x={w * 0.5} y={h * 0.3} textAnchor="middle" fontSize={w * 0.06} fill={dna?.accent ?? '#3563e9'}>水</text>
  </svg>
);
```

`SwirlOfCoffee.tsx` (BAD — decoration that carries nothing):
```tsx
// BAD — DECORATION THAT CARRIES NOTHING. A pretty spiral of coffee-coloured dots, turning: on topic by colour and
// by nothing else. Hide the caption and ask what it says about extraction — nothing. It passes every gate.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';

export const META: ObjectMeta = {aspect: 1, provenance: 'motion-graphics'};

export const SwirlOfCoffee: React.FC<ObjectProps> = ({w, h, t}) => (
  <svg width={w} height={h} style={{display: 'block'}}>
    {Array.from({length: 90}).map((_, i) => {   // @decor: a spiral — texture, and all it is
      const a = i * 0.35 + t * 4, r = (i / 90) * w * 0.45;
      return <circle key={i} cx={w / 2 + Math.cos(a) * r} cy={h / 2 + Math.sin(a) * r} r={w * 0.012}
        fill={i % 2 ? '#6f4e37' : '#c69c6d'} />;
    })}
  </svg>
);
```

- [ ] **Step 4: Render them** — `scripts/object_examples.py`:

```python
#!/usr/bin/env python3
"""Render the six object examples of references/object-authoring.md into references/object-examples/<Name>.png —
each on ObjectStage (ComposeScreen on DeviceHero's screen), at half size, settled. The doc embeds what this writes;
re-run it after changing an example.

    python3 scripts/object_examples.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import workshop as ws  # noqa: E402

SKILL = os.path.dirname(_HERE)
EX = os.path.join(SKILL, "references", "object-examples")
SHOTS = {  # name: (host, props) — every word on the frame comes from these props
    "PuckInSection": ("ObjectStage", {"object": {"id": "PuckInSection", "props": {"packed": 0.85}},
                                      "title": "压实的粉饼", "note": "越密，水越难穿过",
                                      "labels": [{"text": "粉饼", "x": 0.5, "y": 0.68}, {"text": "热水", "x": 0.3, "y": 0.1}]}),
    "StrataOverTime": ("ObjectStage", {"object": {"id": "StrataOverTime", "props": {"layers": [3, 2, 4, 1.5]}},
                                       "title": "一条街的四个年代",
                                       "labels": [{"text": "1900", "x": 0.5, "y": 0.9}, {"text": "今天", "x": 0.5, "y": 0.06}]}),
    "ComposeScreen": ("DeviceHero", {"device": "phone", "screen": {"object": {"id": "ComposeScreen", "props": {
        "to": "给：团队", "draft": "今天的实验结果已经整理好，请查看附件。", "send": "发送"}}}}),
    "ChromeMachine": ("ObjectStage", {"object": {"id": "ChromeMachine"}, "title": "一台咖啡机"}),
    "LabeledPuck": ("ObjectStage", {"object": {"id": "LabeledPuck"}, "title": "粉饼"}),
    "SwirlOfCoffee": ("ObjectStage", {"object": {"id": "SwirlOfCoffee"}, "title": "萃取"}),
}


def main():
    film = tempfile.mkdtemp(prefix="object_examples_")
    try:
        d = os.path.join(film, "workshop", "objects")
        os.makedirs(d)
        for n in SHOTS:
            shutil.copy(os.path.join(EX, n + ".tsx"), os.path.join(d, n + ".tsx"))
        ws.write_index(film)
        for n, (host, props) in SHOTS.items():
            pf = os.path.join(film, n + ".json")
            with open(pf, "w", encoding="utf-8") as fh:
                json.dump(dict(props, dna="product"), fh, ensure_ascii=False)
            png = os.path.join(EX, n + ".png")
            subprocess.run(["npx", "remotion", "still", "src/index.ts", host, png, "--frame=150", "--scale=0.5",
                            "--gl=angle", "--log=error", "--props=" + pf], cwd=ws.REMOTION, check=True,
                           **ws.run_kwargs(film))
            print("[object_examples] %s" % png)
    finally:
        shutil.rmtree(film, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `python3 scripts/object_examples.py`, then open each PNG and LOOK: the three good ones each say their one thing with the title covered by your hand; LabeledPuck prints its Chinese; ChromeMachine is clip-art; SwirlOfCoffee says nothing.

- [ ] **Step 5: Write `references/object-authoring.md`**:

```markdown
# Object authoring — building a thing a film needs

A film builds an OBJECT when its beat needs a thing no register draws: a coffee puck in section, a sensor, a street's
strata, an interface that does not exist yet. The object lives in the film's workshop
(`python3 scripts/workshop.py <out_dir> new-object <Name> --means "<what the viewer must see>"`), goes into a register
that has a slot for one — `ObjectStage`, `ObjectCompare`, `ObjectPath`, `ObjectTurntable`, `TechnicalPlate` (`art`),
`HudReticle` (`object`), a device's `screen` — and is named on the film's `meta.build_list`. What to draw it WITH is
`references/building-blocks.md`.

## The five rules

1. **It ENCODES its beat.** Hide the caption: the object must still carry THIS beat's idea — the build-list entry's
   `means`, tested by its `accept`. On topic by colour or subject is not enough (see SwirlOfCoffee below).
2. **It is a designed diagram, not an imitation of a photograph.** When a beat needs the thing as it LOOKS, the
   documentary tier composites a real, credited image (`scripts/imagefetch.py`, `PhotoPlate`, `MuseumLabel`); an
   object shows how a thing WORKS or what it MEANS — a section, a flow, a state, a count.
3. **Every word comes from props, and no figure is invented.** The film writes its words in its own language; an
   object that writes its own prints them in every film (`workshop.py check` and `shot_proof.py` both refuse it). A
   word that genuinely belongs to the form — a unit symbol, an axis letter — is declared `// @fixed-text: <why>`. A
   quantity the object shows comes from a prop the film sourced; texture is declared `// @decor: <why>`.
4. **It sizes to its box.** It is drawn at `w × h`, whatever those are; `META.aspect` says the shape it wants and the
   slot letterboxes it. No fixed pixels, nothing outside the box unless it is meant to overhang.
5. **It is a pure function of `t`.** `t` runs 0 → 1 over the part of the beat its host gives it and then holds; at
   any frame the object is fully determined — no `Math.random`, no `Date`. What its host does with `t` is on the
   host's card (ObjectPath hands it the object's progress along the route; TechnicalPlate its drawing phase).

`META` carries `aspect`, `provenance` (the idiom world its look comes from — the film's `idiom_world` is judged on
it) and, for an object that draws its own 3D from `yaw`, `turns: true` (objects/DemoForm is the reference).

## Three good objects

### A mechanism in cutaway — `PuckInSection`
![PuckInSection on ObjectStage](object-examples/PuckInSection.png)

Drops enter at the top and fight down through a packed bed; the more `packed`, the thinner and denser the bed and
the fewer drops get through. Caption hidden, the beat's claim — resistance is the point — is on the frame. It draws
no words: the stage's labels name the bed and the water. Source: `object-examples/PuckInSection.tsx`.

### Layered strata — `StrataOverTime`
![StrataOverTime on ObjectStage](object-examples/StrataOverTime.png)

A column grows layer by layer, each as thick as the film's numbers say, the newest on top in the accent. The eras'
names are the stage's labels; the object draws only what the numbers say. Source: `object-examples/StrataOverTime.tsx`.

### An interface being operated — `ComposeScreen`
![ComposeScreen on DeviceHero's screen](object-examples/ComposeScreen.png)

A screen that does not exist yet, drawn for a device (`{"screen": {"object": …}}`): the draft types itself in and
the send button lights when it is done. The recipient, the draft and the button are props. Source:
`object-examples/ComposeScreen.tsx`.

## Three bad objects — and which of them the gates catch

### An imitation of a photograph — `ChromeMachine`
![ChromeMachine on ObjectStage](object-examples/ChromeMachine.png)

Gradients and a highlight dressing up an espresso machine. It is clip-art, it shows no mechanism, and it competes
with the real machine a documentary image would show. **It passes every gate.**

### Words written into the object — `LabeledPuck`
![LabeledPuck on ObjectStage](object-examples/LabeledPuck.png)

The bed and the water are named in Chinese in the code, so every film prints Chinese there and no prop can change it.
**`workshop.py check` refuses it** (and `shot_proof.py` names the words on the frame).

### Decoration that carries nothing — `SwirlOfCoffee`
![SwirlOfCoffee on ObjectStage](object-examples/SwirlOfCoffee.png)

A turning spiral in coffee colours: on topic by colour and by nothing else. Hide the caption — it says nothing about
extraction. **It passes every gate.**

Two of the three bad objects pass every machine check. A gate measures type, words and geometry; it cannot measure
meaning. That is why the shot-critic judges every built thing on its rendered frames (`agents/shot-critic.md` S15),
and why the build list states `means` and `accept` before anything is drawn.

## The loop

1. Write the build-list entry first: `means` (what the viewer must see) and `accept` (how it is judged).
2. `workshop.py new-object`, draw it, `workshop.py still <out_dir> <Name>` — LOOK at the settled frame, caption hidden.
3. `workshop.py check` until it is clean; then `validate.py`, render, and the film gates.
4. The critic judges it against `means` and `accept` (S15). At delivery the user decides whether it is promoted
   (`scripts/promote.py`).
```

- [ ] **Step 6: Write `references/building-blocks.md`** — one `### \`<module>\`` section for every module in `remotion/src/runtime/` (not the `__probe_*` files), each with: one or two sentences on what it does, **Reach for it:** when, **Smallest real use:** one line of real code, **Exports:** the names that matter (only that module's own). Then `## Recipes`. The whole file:

```markdown
# Building blocks — what a film's code can draw with

Everything a register or an object in a film's workshop can import is here: the runtime (`@runtime/<module>` from a
workshop, `../runtime/<module>` in the library), React, Remotion, and the library's registers (`@shots/<Name>`).
Each module's own source header is the long form — this is the map. Objects are covered in
`references/object-authoring.md`; the frame-craft floor every register obeys is `references/remotion-shot-authoring.md`.

## Time and motion

### `motion`
The clock and easing kit every register and object runs on — a pure function of the frame, settled at both edges of
a beat so a cross-dissolve never runs over something moving.
**Reach for it:** always. A register reads `useT()`; an object is handed `t`.
**Smallest real use:** `const on = easeOutCubic(clamp01(seg(t, 0.1, 0.4)));`
**Exports:** `useT`, `seg`, `clamp01`, `lerp`, `easeOutCubic`, `easeInOutCubic`, `easeOutExpo`, `easeOutBack`, `springAt`, `useSpringAt`, `useAnimSpan`, `cadence`, `stepped`, `speedRamp`, `hash01`, `life`, `SEAM_FRAMES`, `ENTRY_T`, `REDUCED_MOTION_T`.

### `draw`
Draws a stroke on from its start without knowing its length (`pathLength = 1`), and slides a dashed stroke whose
dashes carry meaning.
**Reach for it:** a line, route, outline or ring that should draw itself.
**Smallest real use:** `<path d={d} fill="none" stroke={ink} {...drawOn(p)} />`
**Exports:** `drawOn`, `dashedStroke`, `boilPhase`.

### `alongPath`
Where a thing is when it travels along an SVG path, by arc length — so a travelling head stays welded to the line.
**Reach for it:** a drop, a packet, a marker or an object moving along a curve.
**Smallest real use:** `const p = pointAt(d, u); <circle cx={p.x} cy={p.y} r={6} />`
**Exports:** `pointAt`, `angleAt`, `pathLength`.

### `gesture`
The one implementation of typing, tapping, clicking and the caret, on frames or on a schedule — never on a
beat-relative rate.
**Reach for it:** an interface being operated (usually through `DeviceDemo`, which schedules these for you).
**Smallest real use:** `const shown = typedCount(t, step.ta, step.t1, typeChunks(text));`
**Exports:** `typeChunks`, `typedCount`, `caretOn`, `framesBetween`, `TapRipple`, `TouchPoint`, `CursorArrow`.

## Space, depth and camera

### `layout`
The frame-craft floor: the title band, the content zone, the caption band, and the text fitting that keeps type
inside its box in any script.
**Reach for it:** every layout decision — never hand-place against the frame.
**Smallest real use:** `const zTop = CONTENT_TOP, zBot = contentBottom(W, H); const px = fitTextPx(title, W * 0.8, 64);`
**Exports:** `CONTENT_TOP`, `TITLE_Y`, `contentBottom`, `captionBand`, `fitTextPx`, `fitBlockPx`, `wrapLines`, `textWidthPx`, `fitsBox`, `placeLabel`, `fitContentSquare`, `contentZoneBox`, `inkBlockH`, `bottomInset`.

### `pageCam2D`
A camera over a page bigger than the frame: keys it moves between, and where a page point lands on screen.
**Reach for it:** a tour across a document, a map, a long interface.
**Smallest real use:** `const cam = camAt(keys, t); const s = pageToScreen(cam, W, H, px, py);`
**Exports:** `PageCam2D`, `camAt`, `pageToScreen`, `clampToPage`, `fitScale`.

### `depth`
Planes at depth and a motivated camera (push, pull, hold, dolly), drawn in 2D so type stays sharp.
**Reach for it:** foreground and background that mean near and far; a camera move with a cause.
**Smallest real use:** `<Plane depth={DEPTH.context}>…</Plane>`
**Exports:** `DEPTH`, `Plane`, `SceneCamera`, `cameraAt`, `dollyAt`, `useCamera`, `panAt`, `clampPan`.

### `focus`
Depth of field as a signal — how far a thing is from what the shot is about, said in blur and dimming.
**Reach for it:** pulling attention to one element among several.
**Smallest real use:** `const f = focusAt(dist, U); <div style={{filter: focusFilter(f), opacity: f.opacity}} />`
**Exports:** `focusAt`, `focusFilter`, `focusDist`.

### `stage3d`
Cards posed anywhere in 3D and a camera that flies to face any one of them, with type that stays type (CSS 3D, not
WebGL).
**Reach for it:** a space of panels the camera travels through.
**Smallest real use:** `<Stage3D cam={pose}><Surface pose={p} w={400} h={300}>…</Surface></Stage3D>`
**Exports:** `Stage3D`, `Surface`, `Pose`, `matrixOf`, `inverseOf`, `fitStage`, `fitSurfaces`, `projectPose`, `faceShade`, `useStage`.

### `project3d`
Projects a 3D point to the frame — the arithmetic for drawing your own 3D (an object that turns) or for anchoring real
type to a thing in space.
**Reach for it:** an object with `META.turns` (see objects/DemoForm); a label on a WebGL object.
**Smallest real use:** `const q = project(yawPoint(p, yaw), CAM, AIM, 30, w, h);`
**Exports:** `project`, `yawPoint`, `onRing`, `Vec3`.

### `fitCamera`
Frames a 3D scene at the aspect it was given by asking the projection how far the camera must stand.
**Reach for it:** a 3D register or object that must fit at 16:9 and 9:16 alike.
**Smallest real use:** `const dist = fitDistance(corners, AIM, DIR, 30, W, H, box, 8);`
**Exports:** `fitDistance`, `fitDistanceMulti`, `frameCamera`, `screenBounds`, `boxCorners`.

### `aimCamera`
Points a react-three-fiber camera where the label arithmetic thinks it points (r3f aims at the origin otherwise).
**Reach for it:** any WebGL register that also places DOM labels.
**Smallest real use:** `<AimCamera at={[0, 0, 0]} from={[0, 2, 8]} />`
**Exports:** `AimCamera`.

## The design system, light and colour

### `dna`
The film's Design DNA — type, palette, surfaces, motion personality — and the colour arithmetic every register uses
so a film is one visual system.
**Reach for it:** every colour and face. `useDNA()` in a register; an object is handed `dna`.
**Smallest real use:** `const ink = dna?.fg ?? INK_D0, paper = mix(dna?.surface ?? SURF_D0, ink, 0.08);`
**Exports:** `useDNA`, `DesignDNA`, `mix`, `tint`, `shade`, `readableOn`, `contrastOf`, `dimOn`, `surfaceOn`, `separatedPair`, `dnaHas`, `coerceDna`, `DNA_PRESETS`.

### `light`
The beat's ground, resolved per frame — what a declared `ground` paints and which caption ink it deserves.
**Reach for it:** a register that must keep reading when a film grounds it light, or dark.
**Smallest real use:** `const lit = onLight(dna); const stroke = lit ? ink : glow;`
**Exports:** `onLight`, `groundFrom`, `readsOn`, `captionInk`, `useGround`, `paleEnd`, `deepEnd`, `GROUND_PRESETS`.

### `onAccent`
The ink for type set on a solid accent block — and the one place a DNA's second accent can speak.
**Reach for it:** a button, chip or badge filled with the accent.
**Smallest real use:** `color: onAccentInk(acc, dna?.accent2, dna?.onAccent, dna?.fg)`
**Exports:** `onAccentInk`, `ON_ACCENT_MIN`.

### `shotLuma`
The measured ground of every library register — what the burned caption and the seam guard read. A film's own shot
declares its `GROUND` instead (scripts/workshop.py), and the declaration is merged here at load.
**Reach for it:** rarely by hand; know it exists when a caption's ink looks wrong.
**Smallest real use:** `const y = dnaGroundY(shot, dna);`
**Exports:** `DNA_GROUND_TOKEN`, `SHOT_LUMA`, `dnaGroundY`, `dnaGroundLum`, `groundGap`, `HARSH_GROUND_GAP`, `GroundSpec`.

### `atmosphere`
The per-topic background world behind every beat — one low-contrast motif under the whole film.
**Reach for it:** from the film (meta.theme), not from a register.
**Smallest real use:** `<Atmosphere motif="grid" accent={acc} bg={bg} />`
**Exports:** `Atmosphere`, `Atmo`, `Motif`.

### `motif`
One topic-derived material drawn across the whole film, so a themed film is more than a set of registers.
**Reach for it:** from the Design DNA's `motif`; a register rarely draws it itself.
**Smallest real use:** `<FilmMotifLayer motif={dna?.motif} dna={dna} W={W} H={H} />`
**Exports:** `FilmMotifLayer`, `FilmMotif`, `MotifKind`.

### `finish`
The photographic layer between rendered and shot — grain, bloom, a vignette — from the DNA's `finish`.
**Reach for it:** from the film; a register never adds its own.
**Smallest real use:** `<FilmFinishLayer dna={dna} finish={dna?.finish} />`
**Exports:** `FilmFinishLayer`, `FilmFinish`.

### `fonts`
Loads the DNA's typefaces for the Film and for every standalone still — the reason the faces a DNA names are the
faces that render.
**Reach for it:** never directly; `var(--f-display)`, `var(--f-body)`, `var(--f-mono)` are what you write.
**Smallest real use:** `font: \`700 ${px}px/1.1 var(--f-display, Inter, sans-serif)\``
**Exports:** `FACES`, `Face`.

### `cjkType`
The leading a line of Chinese needs, derived from the copy — a Latin leading makes wrapped CJK collide with itself.
**Reach for it:** every block of type that may carry Chinese.
**Smallest real use:** `const lh = leading(title, 1.12);`
**Exports:** `leading`, `hasCJK`, `CJK_MIN_LEADING`, `fontWithLeading`, `fitIfCJK`.

## Content

### `atoms`
The parts a frame is built from — a bar, a figure, a list, a label — rendered in the FORM the Design DNA speaks.
**Reach for it:** a number, a scale, a list that should look like this film's system.
**Smallest real use:** `<Bar value={0.62} />`
**Exports:** `Bar`, `Figure`, `List`, `Label`, `Divider`, `Marker`.

### `figure`
The film's number printed as the film wrote it — never stripped to digits and re-typed.
**Reach for it:** any on-screen figure that came from the film (and from its sources).
**Smallest real use:** `const f = parseFigure(props.value); <span>{figureText(props.value)}</span>`
**Exports:** `parseFigure`, `figureText`, `figureAt`, `figureValue`, `Figure`.

### `icons`
One coherent line-icon family, so a category names what it is instead of pointing at a block.
**Reach for it:** a list of kinds, a legend, a row of features.
**Smallest real use:** `<Icon name="send" size={32} ink={ink} />`
**Exports:** `Icon`, `ICON_NAMES`, `IconName`.

### `rows`
A list prop, normalised — or a refusal that names what was actually sent.
**Reach for it:** every list prop, before `.map`.
**Smallest real use:** `const items = rows<Item>(props.items, 'items', 'MyShot');`
**Exports:** `rows`.

### `evidence`
For registers whose premise is a real artefact: refuses to draw without the image rather than drawing a stand-in.
**Reach for it:** a register or object that must show a real, credited image.
**Smallest real use:** `requireEvidence('MyShot', 'src', src, 'the real object');`
**Exports:** `requireEvidence`.

### `uiSurface`
The product itself as furniture: an application window a shot can put on screen, its copy from props.
**Reach for it:** an interface in a register (as opposed to on a device).
**Smallest real use:** `<UiSurface page="cards" W={w} H={h} dna={dna} content={content} />`
**Exports:** `UiSurface`, `UiPage`, `UiContent`, `uiCardRects`, `uiChromeH`.

### `voice`
The film's own narration as a signal a shot can draw — real levels from the beat's audio.
**Reach for it:** an audio-reactive element that must follow what is actually said.
**Smallest real use:** `<Voice samples={48} />`
**Exports:** `Voice`, `NarrationContext`, `VoiceLevels`.

## Devices

### `device`
The phone, tablet, laptop or monitor a device beat is performed on — its geometry and its three looks.
**Reach for it:** through `DeviceDemo` / `DeviceHero`; a film's own device shot can use `Device` directly.
**Smallest real use:** `const g = deviceGeometry('phone', 'flat', W, H, 'center', false); <Device g={g} dna={dna}>…</Device>`
**Exports:** `Device`, `deviceGeometry`, `deviceFace`, `defaultLook`, `isTouch`, `DeviceKind`, `DeviceLook`, `Rect`.

### `deviceSpec.json`
The device layer's numbers, read by the TypeScript and the Python alike: screen ratios, bezels, minimum step times.
**Reach for it:** never to change a number for one film; read it to know the limits (`screenRatio`, `minSeconds`).
**Smallest real use:** `import spec from '@runtime/deviceSpec.json'; const [rw, rh] = spec.screenRatio.phone;`
**Exports:** `screenRatio`, `minSeconds`, `maxZoom`.

### `screen`
What a device's screen shows: a screenshot (a long one scrolls), a recording, with the scroll bounded by the image's
real height.
**Reach for it:** through the device registers; a screen the film draws instead is an object (`objectSlot`).
**Smallest real use:** `<ScreenImage src={src} imageW={iw} imageH={ih} w={s.w} h={s.h} />`
**Exports:** `ScreenImage`, `ScreenVideo`, `scrollRangePx`, `flingAt`, `VideoSpan`.

## Objects

### `objectSlot`
The contract between a register with room for a thing and the film that draws the thing: the object's props, its
META, and the slot that finds it by id and draws it at its box's size.
**Reach for it:** every object (its props type) and every register or film shot that holds one.
**Smallest real use:** `<ObjectSlot object={props.object} box={{x, y, w, h}} t={objT} />`
**Exports:** `ObjectSlot`, `ObjectRef`, `ObjectProps`, `ObjectMeta`, `ObjectEntry`, `fitAspect`, `useObjectEntry`, `resolveObject`, `ObjectsContext`, `SLOT_KEYS`.

## The gates' own eyes

### `textSafe`
The audit a standalone render runs when a gate asks: type off the canvas, type in the caption band, type colliding,
copy that never arrived — and words on the frame no prop supplied.
**Reach for it:** never in a register; know it is what `text_safe_qa.py`, `cjk_type_qa.py` and `shot_proof.py` see.
**Smallest real use:** (rendered with `textSafe: true` by `scripts/text_safe_qa.py`)
**Exports:** `TextSafeAudit`, `auditTextSafety`, `auditTypeCollisions`, `auditFedText`, `auditUnfedText`, `UNFED_TEXT_TAG`.

## Recipes

### A mechanism in cutaway
Draw the section as SVG (walls, the part that does the work), give the working part a STATE prop from the film, and
let the mechanism act on `t` — flows along paths (`alongPath`), a part that moves (`seg`, `easeOutCubic`). Texture is
`// @decor:`. Reference: `references/object-examples/PuckInSection.tsx`. Host: `ObjectStage` (name the parts with
its labels) or `ObjectCompare` (the same object in two states).

### Liquid or particles along a path
One `d` per stream; each particle `pointAt(d, u)` with its own staggered window `seg(t, a + k * step, b + k * step)`;
how MANY pass is a prop, which ones is layout (`// @positional:`); a jitter from `hash01` is `// @decor:`. Draw the
stream's path with `drawOn` first so the particles have something to ride.

### A turntable
Draw the object in 3D: corners → `yawPoint(p, yaw)` → `project(...)` into the object's own box; cull faces whose normal
points away; paint far to near; set `META.turns = true`. Host: `ObjectTurntable`, which hands it `yaw`. Reference:
`remotion/src/objects/DemoForm.tsx`. A flat object turns as a card, at most ±60°.

### Layered strata
A list of thicknesses from the film, oldest first; stack rects bottom-up, reveal each on its own window, the newest in
the accent (`// @positional:` — the order is time). Reference: `references/object-examples/StrataOverTime.tsx`. Host:
`ObjectStage` with labels at each layer.

### A route on a map
The ROUTE is drawn (`drawOn` on its path, a marker at `pointAt`); the GEOGRAPHY is never invented — a real map is a
documentary image (`scripts/imagefetch.py`) under it, passed in as a prop and credited, or the route stands on its own
as a schematic with no coastline. Host: a film-local shot with the image, or `ObjectPath` when the route is a
sequence of named stations.

### An interface being operated
A screen that does not exist yet is an object drawn for a device: `DeviceDemo` `{"screen": {"object": {"id": …}}}`
with taps and drags at coordinates, and the typing and scrolling done inside the object from its `t` (a progressive
slice is `// @truncates:`). Every word — labels, the typed text, the button — is a prop. Reference:
`references/object-examples/ComposeScreen.tsx`. A REAL product's screens are screenshots, not objects.
```

(If `test_every_section_names_exports_that_exist` flags a name — a heading that names another module's export as its
own — move the name to the right section; the test holds the map to the code.)

- [ ] **Step 7: Run the tests**

Run: `python3 -m pytest tests/test_building_blocks_doc.py tests/test_object_examples.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add references/building-blocks.md references/object-authoring.md references/object-examples/PuckInSection.tsx references/object-examples/StrataOverTime.tsx references/object-examples/ComposeScreen.tsx references/object-examples/ChromeMachine.tsx references/object-examples/LabeledPuck.tsx references/object-examples/SwirlOfCoffee.tsx references/object-examples/PuckInSection.png references/object-examples/StrataOverTime.png references/object-examples/ComposeScreen.png references/object-examples/ChromeMachine.png references/object-examples/LabeledPuck.png references/object-examples/SwirlOfCoffee.png scripts/object_examples.py tests/test_building_blocks_doc.py tests/test_object_examples.py
git commit -m "What a builder reads: every runtime module mapped, six recipes, and object authoring shown in three good and three bad rendered objects

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---
### Task 15: The director builds what the film needs; the critic judges what it built

**Files:**
- Modify: `agents/shot-director.md` (Step 0.5's per-beat bullet; a new Step 0.55; Rule 0's building paragraph; Output), `agents/shot-critic.md` (S15), `scripts/critic_brief.py` (the built things), `SKILL.md` (the cinematic tier's per-beat step; promotion at delivery), `references/remotion-shot-authoring.md` (where the builder's two references are)
- Test: `tests/test_build_flow_docs.py`

**Interfaces:**
- Consumes: everything above; `critic_ledger.dimensions()`, `critic_ledger.precedents()`; `critic_brief.build(out_dir)`, `critic_brief._run`.
- Produces: the written flow an agent follows — need first, the build list, the workshop commands, S15, promotion at delivery.

- [ ] **Step 1: Write the failing tests** — `tests/test_build_flow_docs.py`:

```python
"""The flow reaches the agents that run it. A capability the authoring path cannot name is indistinguishable from
one that was never built — this repo has shipped that shape before (a seam vocabulary complete, tested and unused)."""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))


def _read(*p):
    return open(os.path.join(_ROOT, *p), encoding="utf-8").read()


def test_the_shot_director_is_told_to_build_and_how():
    d = _read("agents", "shot-director.md")
    for needle in ("## Step 0.55 — NEED FIRST", "meta.build_list", '"ref"', "workshop.py <out_dir> new-object",
                   "workshop.py <out_dir> new-shot", "workshop.py <out_dir> still", "ObjectStage", "ObjectCompare",
                   "ObjectPath", "ObjectTurntable", "references/object-authoring.md", "references/building-blocks.md",
                   "scripts/promote.py"):
        assert needle in d, needle


def test_s15_is_a_dimension_the_ledger_requires():
    import critic_ledger
    dims = dict(critic_ledger.dimensions())
    assert "S15" in dims and "BUILT THINGS" in dims["S15"]
    assert critic_ledger.precedents()["S15"] is None          # doctrine: no film has failed it yet


def test_the_critic_brief_lists_what_the_film_built(tmp_path, monkeypatch):
    import critic_brief
    monkeypatch.setattr(critic_brief, "_run", lambda *a, **k: "(stubbed)")
    board = {"meta": {"renderer": "remotion", "language": "zh",
                      "build_list": [{"id": "EspressoPuck", "kind": "object", "beats": [3], "slot": "ObjectStage",
                                      "means": "water forced through a packed bed",
                                      "accept": "caption hidden, the bed resists"}]},
             "slides": [{"index": 3, "shot": "ObjectStage", "shot_fit": {"verdict": "build", "ref": "EspressoPuck"}}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    text = critic_brief.build(str(tmp_path))
    assert "**Built things**" in text and "`EspressoPuck`" in text
    assert "water forced through a packed bed" in text and "caption hidden, the bed resists" in text


def test_skill_md_names_the_workshop_the_build_list_and_promotion():
    s = _read("SKILL.md")
    for needle in ("scripts/workshop.py", "meta.build_list", "scripts/promote.py", "references/object-authoring.md",
                   "PROMOTION IS THE USER'S CHOICE"):
        assert needle in s, needle


def test_the_authoring_reference_points_at_the_builder_s_two_references():
    a = _read("references", "remotion-shot-authoring.md")
    assert "references/building-blocks.md" in a and "references/object-authoring.md" in a
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `python3 -m pytest tests/test_build_flow_docs.py -q`
Expected: FAIL on every test.

- [ ] **Step 3: The shot director** — in `agents/shot-director.md`:

1. In "## Read first", add after item 2:
```markdown
3. **`references/building-blocks.md`** and **`references/object-authoring.md`** — what a film's own objects and
   shots are drawn WITH (every runtime module, six recipes) and how an object is made to MEAN its beat (five rules,
   three good and three bad rendered examples). Read them before the first build.
```
2. In Step 0.5 "### Then, per beat", replace the bullet
```
* nothing does → **BUILD it** (`"build"`, `scripts/register_shot.py`). This is the normal case on a subject
  the library has not met, not an emergency.
```
with
```
* nothing does → **BUILD it** (`"build"`) in the film's workshop — an OBJECT a library template holds, or a new
  film-local SHOT — and put it on the build list first (Step 0.55). This is the normal case on a subject the
  library has not met, not an emergency.
```
3. Directly before `## Step 0.6 — Extract the Design DNA`, add:
````markdown
## Step 0.55 — NEED FIRST: the ideal picture, then the catalogue; what the library lacks is BUILT

For every beat, BEFORE you open LIBRARY.md, write down the IDEAL picture: the specific thing a viewer must SEE for
this beat to land — an object (a coffee puck under pressure), a mechanism (water forced through it), a relation
(loose against packed). Then resolve it to one of:

* **fit** — a library register carries it as it is (`shot_fit.verdict: "fit"`);
* **adapt** — a library register carries it re-sized and re-worded, its structure unchanged (`"adapt"`, §B2);
* **object** — a library TEMPLATE holds it and the thing itself is built: a register with an object slot —
  `ObjectStage` (one thing, named), `ObjectCompare` (two, one difference), `ObjectPath` (through stations,
  changing), `ObjectTurntable` (in the round), `TechnicalPlate` `art`, `HudReticle` `object`, a device's
  `screen` — plus a new object (`"build"`, `ref` = the object);
* **shot** — no template arranges the frame the way the argument does: a new film-local register (`"build"`,
  `ref` = the shot).

Every object or shot you build goes on **`meta.build_list`** FIRST — before it is drawn — so the reason for it and
the test it must pass are written while the need is fresh:

```json
{"id": "EspressoPuck", "kind": "object", "beats": [3, 4],
 "means": "water forced through a compacted puck — the resistance is the point",
 "slot": "ObjectStage", "uses": ["draw", "alongPath", "light"],
 "accept": "caption hidden, a viewer still sees water pushed through a packed bed"}
```

and every beat that uses it says so: `shot_fit = {"verdict": "build", "ref": "EspressoPuck", "why": "…"}`.
`validate.py` holds the two together both ways (a listed item with no file, a file with no entry, an entry no beat
uses, a `ref` that names nothing), refuses an object id nobody defines and a stage's own preview form, and runs
`workshop.py check`. Then build it:

```
python3 scripts/workshop.py <out_dir> new-object EspressoPuck --means "water forced through a packed bed"
python3 scripts/workshop.py <out_dir> new-shot ExtractionFlow --means "pressure, flow and time on one frame"
python3 scripts/workshop.py <out_dir> still EspressoPuck      # LOOK at it, caption hidden, before it enters the film
python3 scripts/workshop.py <out_dir> check                   # type-check, imports, content contract, words from props
```

**Object or shot?** Build an OBJECT when a template's frame is right and only its subject is missing — the stage,
the compare, the route, the turntable, a plate's field, a device's screen already say what the beat's FORM is.
Build a SHOT when the form itself is new. An object is reusable across the film's beats (the same puck loose on
beat 3 and tamped on beat 4, through its `props`) and across templates; a shot is one composition. A film-local
shot declares `GROUND` (the DNA token its ground is painted from — the caption's ink is picked from it and
`shot_proof.py` measures the claim) and `PROVENANCE` (its idiom world).

**Do not be lazy about it.** Step 0.5 already requires half the form vocabulary to be forms the library lacks;
each of those is a build-list entry, or a written reason it is not. A topic the library has never met with an empty
build list is the signature of assembling from what exists — the critic's S14 and S15 look for exactly that. What
the film builds stays in its workshop; at delivery the USER decides what is promoted into the library
(`scripts/promote.py`).
````
4. In Rule 0, replace the paragraph that starts `**Building is one command, and cheap on purpose:**` and its code block, through `…every beat got matched to the closest existing register instead.`, with:
````markdown
   **Building happens in the film's own workshop, and is cheap on purpose** (Step 0.55; `scripts/workshop.py`):
   ```
   python3 scripts/workshop.py <out_dir> new-object <Name> --means "<what the viewer must see>"   # a thing a template holds
   python3 scripts/workshop.py <out_dir> new-shot <Name> --means "<the argument no register carries>"   # a new template
   python3 scripts/workshop.py <out_dir> still <Name>    # LOOK at its settled frame before it enters the film
   python3 scripts/workshop.py <out_dir> check           # type-check, imports, content contract, words from props
   ```
   Nothing it builds touches the library: every render of THIS film sees it and no other film does; at delivery the
   user decides what is promoted (`scripts/promote.py`, which registers and measures it). Writing a register
   straight into the library mid-film (`register_shot.py`) was the only way to build, and it cost a full
   registration and measurement — which is exactly why in practice nothing was ever built and every beat got
   matched to the closest existing register instead.
````
and add to the next paragraph (`**A new register must be REUSABLE, not a one-off.**`) the sentence: `A film-local shot is held to the same rule — its topic arrives through props — which is what makes it promotable.`
5. In "## Output", after the sentence that introduces `shot_fit`, add: `On a film that builds, also write **\`meta.build_list\`** (Step 0.55) and \`shot_fit.ref\` on every beat that uses a built item.`

- [ ] **Step 4: The critic** — in `agents/shot-critic.md`, directly after the line `> **Ask yourself:** Which beat's form did the catalogue not have — and what did the film do about it?`, add:
```markdown

**S15 · BUILT THINGS — does each thing the film built carry its beat?** For every `meta.build_list` entry (the
brief lists them with their beats, `means` and `accept`), judge it on its rendered frames — its settled frame
(`<out_dir>/workshop/_stills/<id>.png` when the maker rendered one) and its beats' keyframes: (a) with the caption
hidden, does it carry its entry's `means` — does it pass its own `accept`? (b) can a first-time viewer name what it
is in about a second? (c) does it belong to this film's Design DNA — its ink, type and motion — or read as another
film pasted in? (d) is it better than the library's nearest register would have been, or a worse copy of something
the library already had? And the other direction, which S1 and S14 begin: for each beat that did NOT build, name
why the library register's STRUCTURE — not just its words — carries that beat. `na` only when the film built
nothing AND every beat's structure fits; say which.
> **Precedent — none on record.** This is doctrine, not case law: a film's own built things are new. When one fails
> here, write it down as the first case.
> **Ask yourself:** Hide the caption on each built thing — what does it say, and is that its beat?
```

- [ ] **Step 5: The critic brief lists the built things** — in `scripts/critic_brief.py`, `build()`, directly after the block that appends the `**Library growth** — …` line and its `if not any(fits):` note, add:
```python
    # THE BUILT THINGS, for S15: each with its purpose and its own test, and its settled frame when one was rendered.
    bl = [e for e in meta.get("build_list") or [] if isinstance(e, dict)]
    if bl:
        L.append("")
        L.append("**Built things** — judge each on S15, against its own `means` and `accept`:")
        for e in bl:
            still = os.path.join("workshop", "_stills", "%s.png" % e.get("id"))
            L.append("- `%s` (%s in `%s`, beats %s%s) — means: %s · accept: %s%s"
                     % (e.get("id"), e.get("kind"), e.get("slot"), e.get("beats"),
                        ", promoted" if e.get("promoted") else "", e.get("means"), e.get("accept"),
                        " · settled frame: `%s`" % still if os.path.exists(os.path.join(out_dir, still)) else ""))
```
and in section 5, change the line computing `missing` to leave out the film's own shots and name them separately:
```python
    import workshop as _ws
    film_own = _ws.shot_names(out_dir)
    missing = sorted(set(shots) - set(_library_entries(set(shots))) - film_own)
    if film_own & set(shots):
        L.append("")
        L.append("Film-local registers (its workshop — see Built things): %s" % ", ".join(sorted(film_own & set(shots))))
```
(keep the existing `if missing:` lines after it).

- [ ] **Step 6: SKILL.md** — in the cinematic tier's step ②, replace
```
When no register encodes a topic-specific idea, BUILD a bespoke shot (real imagery where
     the topic is concrete) rather than force a near-miss.
```
with
```
**NEED FIRST, then the catalogue, then BUILD what it lacks** (shot-director Step 0.55): for each beat
     write the ideal picture, then resolve it to fit / adapt / an OBJECT a library template holds / a new film-local
     SHOT. Every built thing goes on `meta.build_list` with its `means` and `accept`, is written in the film's own
     workshop (`scripts/workshop.py new-object | new-shot | still | check`; what to build with:
     `references/building-blocks.md`; how to make it mean something: `references/object-authoring.md`) and never
     touches the library. Real imagery where the topic is concrete stays the documentary tier's.
```
and directly after the paragraph that ends `The maker holds the intent, and the intent is what makes a wrong frame look right.`, add:
```
     **PROMOTION IS THE USER'S CHOICE, AT DELIVERY.** When the film is delivered (`critic_ledger.py --final`
     passed), list its built things — each with its settled frame (`workshop/_stills/`) and its gate results — and
     ask the user with `AskUserQuestion` (multiSelect) which, if any, to promote into the library. For each one
     chosen: `python3 scripts/promote.py <out_dir> <Name>` (an object: it joins remotion/src/objects and the
     catalogue) or `... --family <X> --use-when "…" --motion "…"` (a shot: registered at every sync point and
     measured in the right order). Nothing is promoted without the user's pick; nothing a film builds reaches
     another film until it is.
```

- [ ] **Step 7: The authoring reference points at the builder's references** — in `references/remotion-shot-authoring.md`, directly before `## E · The gates still bind`, add:
```markdown
## Building what the library lacks

A film builds the objects and templates it needs in its own workshop (`scripts/workshop.py`) instead of settling for
the nearest register — see shot-director Step 0.55. What to build WITH is `references/building-blocks.md` (every
runtime module, and recipes for the objects films keep needing); how to make a built object MEAN its beat is
`references/object-authoring.md`. Everything in this file binds a film's own code exactly as it binds the library.
```

- [ ] **Step 8: Run the tests**

Run: `python3 -m pytest tests/test_build_flow_docs.py tests/test_gate_coverage.py tests/test_remotion.py -q`
Expected: PASS — S15 carries its `none on record` precedent, so the precedent test accepts it.

- [ ] **Step 9: Commit**

```bash
git add agents/shot-director.md agents/shot-critic.md scripts/critic_brief.py SKILL.md references/remotion-shot-authoring.md tests/test_build_flow_docs.py
git commit -m "The director builds what the film needs — need first, a build list, the workshop — and the critic judges what it built (S15); promotion is the user's call

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 16: Nothing a film without a workshop renders has changed

**Files:**
- Output (not committed): `.superpowers/regression/after.mp4`, `after.framemd5`, and the pipeline comparison below

**Interfaces:**
- Consumes: Task 1 Step 1's `.superpowers/regression/{props.json,BASE,before.framemd5}`.
- Produces: the evidence for success criterion 1, recorded in the task report.

- [ ] **Step 1: Re-render the reference film on the finished branch and compare every frame**

Run:
```bash
cd remotion && npx remotion render src/index.ts Film ../.superpowers/regression/after.mp4 --props=../.superpowers/regression/props.json --gl=angle --log=error && cd ..
ffmpeg -v error -i .superpowers/regression/after.mp4 -map 0:v:0 -f framemd5 .superpowers/regression/after.framemd5
diff <(grep -v '^#' .superpowers/regression/before.framemd5) <(grep -v '^#' .superpowers/regression/after.framemd5) && echo "FRAME-IDENTICAL"
```
Expected: `FRAME-IDENTICAL` (every decoded frame of the 8-beat, 636-frame film matches). Any line of difference is a regression: find the first differing frame (`diff` prints it; frame index / 90-ish tells the beat), render that frame from both trees with `npx remotion still`, look at both, fix the cause — never the reference.

- [ ] **Step 2: The same through the whole pipeline, when a real film is at hand**

If the device-layer session's five-beat film exists (`/private/tmp/claude-501/-Users-donghanglyu/6207e8ee-54d2-425f-9753-b7ed5b16ddd0/scratchpad/rv/filmA`, with its `audio/` and screenshots), copy it twice (`cp -R … .superpowers/regression/filmA_main` and `…/filmA_branch`), delete the `.remotion_segments/` folder in both copies, then render one with the MAIN checkout's renderer and one with the branch's:
```bash
python3 ~/.claude/skills/slides-to-video/scripts/render_remotion.py .superpowers/regression/filmA_main
python3 scripts/render_remotion.py .superpowers/regression/filmA_branch
for d in filmA_main filmA_branch; do ffmpeg -v error -i .superpowers/regression/$d/out.mp4 -map 0:v:0 -f framemd5 .superpowers/regression/$d.framemd5; done
diff <(grep -v '^#' .superpowers/regression/filmA_main.framemd5) <(grep -v '^#' .superpowers/regression/filmA_branch.framemd5) && echo "PIPELINE FRAME-IDENTICAL"
```
Expected: `PIPELINE FRAME-IDENTICAL`. If that film is gone, say so in the report; Step 1 is the check that must pass.

- [ ] **Step 3: The whole suite on this exact tree** (nothing else running)

Run: `python3 -m pytest tests -q -p no:cacheprovider`
Expected: every test passes. Record passed / skipped / failed and the tree's `git rev-parse HEAD` in the report.

- [ ] **Step 4: Report** — no commit. The report states the two diffs' results, the suite counts and the HEAD they were taken on. A non-empty diff or a failing test stops the plan here.

---
## The acceptance films (Tasks 17–20)

Four films, one per topic the user chose, each run end to end; each task below carries the requirements they share.

---

### Task 17: Acceptance film — MRI 成像原理

**Files:**
- Output: `.superpowers/films/mri/` (not committed); fixes to the skill if the run exposes defects (committed with tests)

**Interfaces:**
- Consumes: the whole skill.
- Produces: a delivered film and `REPORT.md`.

**Requirements (every acceptance film — the plan's four films share them):** each film runs the skill end to end, as a user's request would, and is where the plan finds out whether the skill really builds what a film needs.

- lives in `.superpowers/films/<slug>/` in the worktree (git-ignored); nothing of it is committed except fixes the
  run exposes in the skill itself, each in its own commit with a test;
- follows `SKILL.md` "Workflow (follow in order)" for a no-deck cinematic film. The user-facing pauses — the
  interview, the voice audition, the sample sign-off and the direction contest — are answered by the task's own
  brief below (rulings: the user fixed the four topics, Chinese narration and 4–6 beats; `meta.audacity: "balanced"`
  with no contest, one direction conceived for the topic). Record each such answer in the film's report as
  "decided by the plan";
- has 4–6 beats, `meta.language: "zh"`, a comprehension brief whose every fact and figure carries its source URL
  (no invented number — keep it qualitative when no source says it), and a `meta.form_vocabulary`;
- **builds at least two things** that are on `meta.build_list`, drawn in its workshop and used by its beats. The
  suggested builds below are what the need-first step is expected to find; the shot director may find better ones —
  the requirement is the count, the `means`/`accept` on each, and (across the four films) at least one object AND at
  least one film-local shot;
- passes, on the delivered tree: `validate.py` (0 errors), `text_safe_qa.py <out>`, `shot_proof.py <out>`,
  `cjk_type_qa.py <out>` (each exit 0, or its not-measured lines explained), and the shot-critic as a fresh subagent
  given only the out_dir, gated by `critic_ledger.py <out> --final` ending in PASS (a REVISE means fix and re-review);
- is LOOKED AT: every beat's settled keyframe (`_keyframes/`) and every built item's `workshop/_stills/<id>.png`,
  each described in one sentence in the report, with the caption covered — does the built thing say its `means`?
- ends with `REPORT.md` in its folder: the build list (with the stills), each gate's last line, the critic's verdict,
  the look-through, wall-clock time for the whole film and for the building, and every defect in the SKILL found on
  the way (with the commit that fixed it, or why it was left).

- [ ] **Step 1: Brief and plan** — create the folder and run SKILL.md steps 1–5 for a no-deck film with: topic 「磁共振成像（MRI）是怎么把人体内部变成图像的」; ① Purpose Teach/explain (expository); ② 中文 (`zh`); ③ Cinematic (Remotion); 5 beats. The brief's facts come from sourced pages (e.g. the Wikipedia articles 磁共振成像 / Magnetic resonance imaging, with URLs in `brief.json`): hydrogen nuclei as tiny magnets; alignment in a strong static field; an RF pulse tips them and they precess and emit a signal; gradient fields make the signal's frequency depend on position; the signal fills k-space and a Fourier transform gives the image. No field strength or timing figure unless the brief cites it.

- [ ] **Step 2: Need first, then build** — run the shot director (Step 0.55). Expected build list (the director may improve it): an object **`ProtonPrecess`** — a proton's spin axis precessing around the main field and tipped by the RF pulse, drawn in 3D from `yaw`/`t` (`META.turns`), held by `ObjectTurntable` or `ObjectStage`; a film-local shot **`KSpaceToPicture`** — k-space rows fill while the image resolves, every label a prop (the library's k-space registers write English labels into their code and cannot speak a Chinese film — say so in its `shot_fit.why`). For each: `workshop.py new-object|new-shot`, draw it with `references/building-blocks.md` open, `workshop.py still`, LOOK, `workshop.py check` until clean. Record `means`/`accept` BEFORE drawing.

- [ ] **Step 3: Voice, validate, cuts, render** — `python3 scripts/tts.py <out>` (the default zh edge-tts voice), then `python3 scripts/validate.py <out>` until 0 errors, `python3 scripts/seam_plan.py <out>`, `python3 scripts/render_remotion.py <out>`.

- [ ] **Step 4: The film gates** — `python3 scripts/text_safe_qa.py <out>`, `python3 scripts/shot_proof.py <out>`, `python3 scripts/cjk_type_qa.py <out>`; fix and re-render until each is clean.

- [ ] **Step 5: The critic** — `python3 scripts/critic_brief.py <out>`, `python3 scripts/critic_ledger.py <out> --emit-template`, dispatch `agents/shot-critic.md` as a fresh subagent whose ENTIRE input is the out_dir path, then `python3 scripts/critic_ledger.py <out> --final` — until the verdict line says PASS.

- [ ] **Step 6: Look at it and report** — open `_contact_sheet.png`, every `_keyframes/scene_*.png` and every `workshop/_stills/*.png`; write `REPORT.md` as described above. A defect in the skill found here is fixed in the skill (with a test), committed with the trailer, and named in the report.

---

### Task 18: Acceptance film — 咖啡机怎么萃取

**Files:**
- Output: `.superpowers/films/espresso/` (not committed); fixes to the skill if the run exposes defects (committed with tests)

**Interfaces:**
- Consumes: the whole skill.
- Produces: a delivered film and `REPORT.md`.

**Requirements (every acceptance film — the plan's four films share them):** each film runs the skill end to end, as a user's request would, and is where the plan finds out whether the skill really builds what a film needs.

- lives in `.superpowers/films/<slug>/` in the worktree (git-ignored); nothing of it is committed except fixes the
  run exposes in the skill itself, each in its own commit with a test;
- follows `SKILL.md` "Workflow (follow in order)" for a no-deck cinematic film. The user-facing pauses — the
  interview, the voice audition, the sample sign-off and the direction contest — are answered by the task's own
  brief below (rulings: the user fixed the four topics, Chinese narration and 4–6 beats; `meta.audacity: "balanced"`
  with no contest, one direction conceived for the topic). Record each such answer in the film's report as
  "decided by the plan";
- has 4–6 beats, `meta.language: "zh"`, a comprehension brief whose every fact and figure carries its source URL
  (no invented number — keep it qualitative when no source says it), and a `meta.form_vocabulary`;
- **builds at least two things** that are on `meta.build_list`, drawn in its workshop and used by its beats. The
  suggested builds below are what the need-first step is expected to find; the shot director may find better ones —
  the requirement is the count, the `means`/`accept` on each, and (across the four films) at least one object AND at
  least one film-local shot;
- passes, on the delivered tree: `validate.py` (0 errors), `text_safe_qa.py <out>`, `shot_proof.py <out>`,
  `cjk_type_qa.py <out>` (each exit 0, or its not-measured lines explained), and the shot-critic as a fresh subagent
  given only the out_dir, gated by `critic_ledger.py <out> --final` ending in PASS (a REVISE means fix and re-review);
- is LOOKED AT: every beat's settled keyframe (`_keyframes/`) and every built item's `workshop/_stills/<id>.png`,
  each described in one sentence in the report, with the caption covered — does the built thing say its `means`?
- ends with `REPORT.md` in its folder: the build list (with the stills), each gate's last line, the critic's verdict,
  the look-through, wall-clock time for the whole film and for the building, and every defect in the SKILL found on
  the way (with the commit that fixed it, or why it was left).

- [ ] **Step 1: Brief and plan** — create the folder and run SKILL.md steps 1–5 for a no-deck film with: topic 「一台意式咖啡机是怎么萃取出一杯浓缩咖啡的」; ① Purpose How-to/walkthrough (expository); ② 中文 (`zh`); ③ Cinematic (Remotion); 5 beats — grinding, tamping (loose grounds become a dense puck), pressure (hot water forced through the puck), extraction (the puck's resistance sets the time and the taste), the shot in the cup. Facts from sourced pages (e.g. Wikipedia 浓缩咖啡 / Espresso, URLs in `brief.json`); a pressure or time figure appears only if the brief cites it.

- [ ] **Step 2: Need first, then build** — run the shot director (Step 0.55). Expected build list: an object **`EspressoPuck`** — the puck in section with a `packed` prop, water forced through it (the `PuckInSection` recipe is the starting point, not the answer), used by `ObjectCompare` (loose vs tamped: one object, two `props`) and by `ObjectStage` (the pressure beat, its parts named by labels); and either an object **`BeanToCup`** carried through `ObjectPath` (bean → grounds → puck → espresso, its state drawn from its `t`) or a film-local shot **`ExtractionFlow`**. For each: `workshop.py new-object|new-shot`, draw, `workshop.py still`, LOOK, `workshop.py check` until clean; `means`/`accept` first.

- [ ] **Step 3: Voice, validate, cuts, render** — `python3 scripts/tts.py <out>`, `python3 scripts/validate.py <out>` until 0 errors, `python3 scripts/seam_plan.py <out>`, `python3 scripts/render_remotion.py <out>`.

- [ ] **Step 4: The film gates** — `python3 scripts/text_safe_qa.py <out>`, `python3 scripts/shot_proof.py <out>`, `python3 scripts/cjk_type_qa.py <out>`; fix and re-render until each is clean.

- [ ] **Step 5: The critic** — `python3 scripts/critic_brief.py <out>`, `python3 scripts/critic_ledger.py <out> --emit-template`, the shot-critic as a fresh subagent given only the out_dir, then `python3 scripts/critic_ledger.py <out> --final` until PASS.

- [ ] **Step 6: Look at it and report** — the contact sheet, every keyframe and every workshop still, described in `REPORT.md` as above; skill defects fixed with tests and committed.

---

### Task 19: Acceptance film — 产品发布：一个 App + 一件硬件

**Files:**
- Output: `.superpowers/films/launch/` (not committed); fixes to the skill if the run exposes defects (committed with tests)

**Interfaces:**
- Consumes: the whole skill.
- Produces: a delivered film and `REPORT.md`.

**Requirements (every acceptance film — the plan's four films share them):** each film runs the skill end to end, as a user's request would, and is where the plan finds out whether the skill really builds what a film needs.

- lives in `.superpowers/films/<slug>/` in the worktree (git-ignored); nothing of it is committed except fixes the
  run exposes in the skill itself, each in its own commit with a test;
- follows `SKILL.md` "Workflow (follow in order)" for a no-deck cinematic film. The user-facing pauses — the
  interview, the voice audition, the sample sign-off and the direction contest — are answered by the task's own
  brief below (rulings: the user fixed the four topics, Chinese narration and 4–6 beats; `meta.audacity: "balanced"`
  with no contest, one direction conceived for the topic). Record each such answer in the film's report as
  "decided by the plan";
- has 4–6 beats, `meta.language: "zh"`, a comprehension brief whose every fact and figure carries its source URL
  (no invented number — keep it qualitative when no source says it), and a `meta.form_vocabulary`;
- **builds at least two things** that are on `meta.build_list`, drawn in its workshop and used by its beats. The
  suggested builds below are what the need-first step is expected to find; the shot director may find better ones —
  the requirement is the count, the `means`/`accept` on each, and (across the four films) at least one object AND at
  least one film-local shot;
- passes, on the delivered tree: `validate.py` (0 errors), `text_safe_qa.py <out>`, `shot_proof.py <out>`,
  `cjk_type_qa.py <out>` (each exit 0, or its not-measured lines explained), and the shot-critic as a fresh subagent
  given only the out_dir, gated by `critic_ledger.py <out> --final` ending in PASS (a REVISE means fix and re-review);
- is LOOKED AT: every beat's settled keyframe (`_keyframes/`) and every built item's `workshop/_stills/<id>.png`,
  each described in one sentence in the report, with the caption covered — does the built thing say its `means`?
- ends with `REPORT.md` in its folder: the build list (with the stills), each gate's last line, the critic's verdict,
  the look-through, wall-clock time for the whole film and for the building, and every defect in the SKILL found on
  the way (with the commit that fixed it, or why it was left).

- [ ] **Step 1: Brief and plan** — create the folder and run SKILL.md steps 1–5 for a no-deck film with: topic 「发布一款概念产品：一台智能咖啡秤和它的 App」; ① Purpose Launch/announcement (narrative); ② 中文 (`zh`); ③ Cinematic (Remotion); 5 beats — the problem (pour-over by feel), the hardware (what is inside the scale), the app (a live brew curve, operated on the phone), the two in sync, the line to remember. The product is a CONCEPT, named as one in the brief and on screen (e.g. 「概念产品」 in the kicker); no market figure, price, review or claim about a real company — there are no sources for any, so there are none on screen.

- [ ] **Step 2: Need first, then build** — run the shot director (Step 0.55). Expected build list: an object **`ScaleCutaway`** — the scale's inside (load cell, board, battery) as a designed cutaway, held by `TechnicalPlate` (`art`, its parts as callouts) or `ObjectTurntable`; an object **`BrewCurveApp`** — the app's screen drawn by the film (a curve drawing itself, a button that lights), shown on `DeviceDemo` with `{"screen": {"object": …}}` and taps at coordinates, or on `DeviceHero`. A real product's screens would be screenshots; this concept's are objects — say so in `shot_fit.why`. For each: `workshop.py new-object`, draw, `workshop.py still`, LOOK, `workshop.py check` until clean; `means`/`accept` first.

- [ ] **Step 3: Voice, validate, cuts, render** — `python3 scripts/tts.py <out>`, `python3 scripts/validate.py <out>` until 0 errors, `python3 scripts/seam_plan.py <out>`, `python3 scripts/render_remotion.py <out>`.

- [ ] **Step 4: The film gates** — `python3 scripts/text_safe_qa.py <out>`, `python3 scripts/shot_proof.py <out>`, `python3 scripts/cjk_type_qa.py <out>`; fix and re-render until each is clean.

- [ ] **Step 5: The critic** — `python3 scripts/critic_brief.py <out>`, `python3 scripts/critic_ledger.py <out> --emit-template`, the shot-critic as a fresh subagent given only the out_dir, then `python3 scripts/critic_ledger.py <out> --final` until PASS.

- [ ] **Step 6: Look at it and report** — the contact sheet, every keyframe (the device beats at their tap moments too) and every workshop still, described in `REPORT.md` as above; skill defects fixed with tests and committed.

---

### Task 20: Acceptance film — 一座城市的变迁

**Files:**
- Output: `.superpowers/films/city/` (not committed); fixes to the skill if the run exposes defects (committed with tests)

**Interfaces:**
- Consumes: the whole skill, including the documentary tier (`scripts/imagefetch.py`).
- Produces: a delivered film and `REPORT.md`.

**Requirements (every acceptance film — the plan's four films share them):** each film runs the skill end to end, as a user's request would, and is where the plan finds out whether the skill really builds what a film needs.

- lives in `.superpowers/films/<slug>/` in the worktree (git-ignored); nothing of it is committed except fixes the
  run exposes in the skill itself, each in its own commit with a test;
- follows `SKILL.md` "Workflow (follow in order)" for a no-deck cinematic film. The user-facing pauses — the
  interview, the voice audition, the sample sign-off and the direction contest — are answered by the task's own
  brief below (rulings: the user fixed the four topics, Chinese narration and 4–6 beats; `meta.audacity: "balanced"`
  with no contest, one direction conceived for the topic). Record each such answer in the film's report as
  "decided by the plan";
- has 4–6 beats, `meta.language: "zh"`, a comprehension brief whose every fact and figure carries its source URL
  (no invented number — keep it qualitative when no source says it), and a `meta.form_vocabulary`;
- **builds at least two things** that are on `meta.build_list`, drawn in its workshop and used by its beats. The
  suggested builds below are what the need-first step is expected to find; the shot director may find better ones —
  the requirement is the count, the `means`/`accept` on each, and (across the four films) at least one object AND at
  least one film-local shot;
- passes, on the delivered tree: `validate.py` (0 errors), `text_safe_qa.py <out>`, `shot_proof.py <out>`,
  `cjk_type_qa.py <out>` (each exit 0, or its not-measured lines explained), and the shot-critic as a fresh subagent
  given only the out_dir, gated by `critic_ledger.py <out> --final` ending in PASS (a REVISE means fix and re-review);
- is LOOKED AT: every beat's settled keyframe (`_keyframes/`) and every built item's `workshop/_stills/<id>.png`,
  each described in one sentence in the report, with the caption covered — does the built thing say its `means`?
- ends with `REPORT.md` in its folder: the build list (with the stills), each gate's last line, the critic's verdict,
  the look-through, wall-clock time for the whole film and for the building, and every defect in the SKILL found on
  the way (with the commit that fixed it, or why it was left).

- [ ] **Step 1: Brief and plan** — create the folder and run SKILL.md steps 1–5 for a no-deck film with: topic 「深圳：从边境小镇到超大城市」; ① Purpose Overview/intro (expository) with a story arc; ② 中文 (`zh`); ③ Cinematic (Remotion); 5–6 beats. Every date and figure from a sourced page (e.g. the Wikipedia articles 深圳市 / 深圳经济特区, URLs in `brief.json`); where the sources disagree or say nothing, the film says it qualitatively. At least one beat shows the REAL city through the documentary tier (a license-clean Wikimedia Commons photo, credited on screen).

- [ ] **Step 2: Need first, then build** — run the shot director (Step 0.55). Expected build list: an object **`CityStrata`** — the city's eras as layers, each as thick as a sourced span of years, the newest in the accent (the `StrataOverTime` recipe as the starting point), held by `ObjectStage` with the eras as labels; a film-local shot **`GrowthRings`** — the built-up area spreading outward in rings along its roads as a SCHEMATIC (no invented coastline or district outline; if geography is shown it is a real, credited map image under the drawing). For each: `workshop.py new-object|new-shot`, draw, `workshop.py still`, LOOK, `workshop.py check` until clean; `means`/`accept` first.

- [ ] **Step 3: Voice, validate, cuts, render** — `python3 scripts/tts.py <out>`, `python3 scripts/validate.py <out>` until 0 errors, `python3 scripts/seam_plan.py <out>`, `python3 scripts/render_remotion.py <out>`.

- [ ] **Step 4: The film gates** — `python3 scripts/text_safe_qa.py <out>`, `python3 scripts/shot_proof.py <out>`, `python3 scripts/cjk_type_qa.py <out>`; fix and re-render until each is clean.

- [ ] **Step 5: The critic** — `python3 scripts/critic_brief.py <out>`, `python3 scripts/critic_ledger.py <out> --emit-template`, the shot-critic as a fresh subagent given only the out_dir, then `python3 scripts/critic_ledger.py <out> --final` until PASS.

- [ ] **Step 6: Look at it and report** — the contact sheet, every keyframe and every workshop still, described in `REPORT.md` as above; skill defects fixed with tests and committed.

---

### Task 21: One built thing promoted — the user's pick

**Files:**
- Modified by `promote.py`: the library files for the chosen item(s) (`remotion/src/shots|objects/…`, `remotion/src/objects/index.ts` or the registry/Root/shotLuma/shot_director sync points, `remotion/cards/<Name>.md`, `remotion/LIBRARY.md`, the measurement manifests); the film's `storyboard.json` and workshop (not committed)

**Interfaces:**
- Consumes: Task 13 (`promote.py`), Tasks 17–20 (four delivered films and their build lists).
- Produces: at least one built item fully registered and measured in the library (success criterion 3), and a green suite.

- [ ] **Step 1: Ask the user** — list every built item of the four films with its kind, its film, its settled still (`workshop/_stills/<id>.png`), its critic row (S15) and its gate results, and ask with `AskUserQuestion` (multiSelect) which to promote. This is the user's decision (spec §1.4); do not choose for them. If they pick none, record that success criterion 3 is unmet by their choice and stop here.

- [ ] **Step 2: Promote each chosen item** — for an object: `python3 scripts/promote.py .superpowers/films/<slug> <Name> --dry-run`, then without `--dry-run`. For a shot: the same with `--family <X> --use-when "<one line>" --motion "<one line>"` (the family from `remotion/LIBRARY.md`'s families; the use-when from its build-list entry). Nothing else may be editing registers or sweeping while a shot is measured.

- [ ] **Step 3: The film still renders from the library's copy** — `python3 scripts/validate.py .superpowers/films/<slug>` (0 errors: the entry is now `promoted` and the library holds it) and `python3 scripts/render_remotion.py .superpowers/films/<slug>`; then compare the re-render's frames with the delivered film's (`ffmpeg … -f framemd5`, as in Task 16) — the promoted item must draw exactly what it drew in the workshop.

- [ ] **Step 4: The whole suite on this exact tree** — `python3 -m pytest tests -q -p no:cacheprovider`; every test passes (the promoted register's card, census, headline count and measurements included).

- [ ] **Step 5: Commit**

```bash
git add <every library file promote.py changed — `git status` lists them; stage each by name>
git commit -m "Promoted <Name> from the <film> film into the library, at the user's pick: registered, measured, carded

Full suite: <N> passed, <M> skipped.

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

- [ ] **Step 6: Report** — what was promoted, from which film, the measured card lines, the frame comparison, the suite counts. Nothing is pushed.
