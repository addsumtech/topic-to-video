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

# fix round 1 fixtures — F1: a workshop object reaching a real project dependency Remotion does not alias.
OBJECT_THREE = """import React from 'react';
import {Color} from 'three';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'motion-graphics'};
export const %(name)s: React.FC<ObjectProps> = ({w, h}) => (
  <div style={{width: w, height: h, background: new Color(0, 1, 0).getStyle()}} />
);
"""

# F8 — the object receives the beat's `t` (its fill depends on it, two frames give two colours).
OBJECT_T = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'motion-graphics'};
export const %(name)s: React.FC<ObjectProps> = ({w, h, t}) => (
  <div style={{width: w, height: h,
    background: `rgb(${Math.round(255 * t)}, 0, ${Math.round(255 * (1 - t))})`}} />
);
"""

# F8 — the object receives the film's Design DNA.
OBJECT_DNA = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'motion-graphics'};
export const %(name)s: React.FC<ObjectProps> = ({w, h, dna}) => (
  <div style={{width: w, height: h, background: dna ? dna.accent : '#888888'}} />
);
"""

# F5 — an object whose export name does not match its filename: WORKSHOP_OBJECTS[id].C is undefined.
OBJECT_NOCOMPONENT = """import React from 'react';
import type {ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'motion-graphics'};
export const NotTheRightExport: React.FC<any> = () => null;
"""

# F4 — a shot whose box is configurable from props, so a still can send it a NaN width or a zero height.
SHOT_BOX = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ObjectSlot, type ObjectRef} from '@runtime/objectSlot';
export const DURATION = 30;
export const GROUND = 'bg';
export const PROVENANCE = 'motion-graphics';
export const %(name)s: React.FC<{object?: ObjectRef; bw?: number | 'nan'; bh?: number}> =
  ({object, bw = 600, bh = 600}) => (
  <AbsoluteFill style={{background: '#000000'}}>
    {object ? <ObjectSlot object={object} box={{x: 660, y: 240, w: bw === 'nan' ? 0 / 0 : bw, h: bh}} /> : null}
  </AbsoluteFill>
);
"""

# F5 — a shot whose DURATION is not a positive integer.
SHOT_BADDUR = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION = 29.5;
export const GROUND = 'bg';
export const PROVENANCE = 'motion-graphics';
export const %(name)s: React.FC<{}> = () => <AbsoluteFill style={{background: '#00ff00'}} />;
"""

# F5 — a shot whose export name does not match its filename: WORKSHOP_SHOTS[id].C is undefined.
SHOT_NOCOMPONENT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION = 30;
export const GROUND = 'bg';
export const PROVENANCE = 'motion-graphics';
export const NotTheRightExport: React.FC<{}> = () => <AbsoluteFill style={{background: '#00ff00'}} />;
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


# ── fix round 1 (task-1-fix-1.md) ──────────────────────────────────────────────────────────────────────────

@needs_toolchain
def test_a_workshop_object_reaches_a_project_dependency_remotion_does_not_alias(tmp_path):
    """F1: `three` is a real dependency of THIS project (remotion/node_modules; MaterialHero uses it), never
    aliased by remotion.config.ts — so it can only reach a workshop object through resolve.modules. Rendered
    from a film folder under tmp_path, well outside the project, which has no node_modules of its own."""
    ws = _workshop(tmp_path / "film", shots=["WsShotA"], objects=["WsThree"], obj_src=OBJECT_THREE)
    r = _still("WsShotA", tmp_path / "three.png", {"fill": "#000000", "object": {"id": "WsThree"}}, _env(ws))
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    assert _near(_px(tmp_path / "three.png", 960, 540), (0, 255, 0))


@needs_toolchain
def test_an_id_shaped_like_a_prototype_property_is_refused(tmp_path):
    """F2: `objects[id]` reads the prototype chain too — an id of "constructor" resolves to Object.prototype's
    own function and must still be refused as an unknown object, not fail later inside React."""
    ws = _workshop(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    r = _still("WsShotA", tmp_path / "proto.png", {"object": {"id": "constructor"}}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and 'no object "constructor"' in out, out[-800:]


@needs_toolchain
def test_a_ref_with_props_at_the_top_level_is_refused(tmp_path):
    """F3: the object's own prop put beside "id" instead of inside "props" must be refused — not silently
    dropped, drawing the object's defaults."""
    ws = _workshop(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    r = _still("WsShotA", tmp_path / "stray.png", {"object": {"id": "WsDisc", "color": "#f00"}}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and 'outside "props"' in out and "color" in out, out[-800:]


@needs_toolchain
def test_key_in_props_is_refused(tmp_path):
    """F3: React strips `key` off the props object before the component ever runs — an object author who
    wrote it into props believing it would reach their component is silently wrong without this refusal."""
    ws = _workshop(tmp_path, shots=["WsShotA"], objects=["WsDisc"])
    r = _still("WsShotA", tmp_path / "keyprop.png",
               {"object": {"id": "WsDisc", "props": {"key": "x"}}}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "JSX's own" in out and "key" in out, out[-800:]


@needs_toolchain
def test_a_nan_box_is_refused(tmp_path):
    """F4: a NaN box draws a NaN rect — a blank slot with no error."""
    ws = _workshop(tmp_path, shots=["WsBox"], objects=["WsDisc"], shot_src=SHOT_BOX)
    r = _still("WsBox", tmp_path / "nan.png", {"object": {"id": "WsDisc"}, "bw": "nan"}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "box is unusable" in out, out[-800:]


@needs_toolchain
def test_a_zero_height_box_is_refused(tmp_path):
    """F4: a zero-height box draws a 0×0 object — also a blank slot with no error."""
    ws = _workshop(tmp_path, shots=["WsBox"], objects=["WsDisc"], shot_src=SHOT_BOX)
    r = _still("WsBox", tmp_path / "zero.png", {"object": {"id": "WsDisc"}, "bh": 0}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "box is unusable" in out, out[-800:]


@needs_toolchain
def test_a_workshop_shot_with_a_non_integer_duration_is_refused(tmp_path):
    """F5: Remotion needs an integer durationInFrames; caught at load, for every shot in the workshop at once."""
    ws = _workshop(tmp_path, shots=["WsBadDur"], shot_src=SHOT_BADDUR)
    r = _still("WsBadDur", tmp_path / "dur.png", {}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "DURATION" in out and "positive integer" in out, out[-800:]


@needs_toolchain
def test_a_workshop_shot_missing_its_component_is_refused(tmp_path):
    """F5: the generated index imports `S_X.X` — an export name that does not match the filename resolves to
    undefined, and REGISTRY[id] must not silently become that."""
    ws = _workshop(tmp_path, shots=["WsNoComp"], shot_src=SHOT_NOCOMPONENT)
    r = _still("WsNoComp", tmp_path / "nocomp.png", {}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "has no component" in out, out[-800:]


@needs_toolchain
def test_a_workshop_object_missing_its_component_is_refused(tmp_path):
    """F5: the same check, for a workshop object."""
    ws = _workshop(tmp_path, shots=["WsShotA"], objects=["WsNoComp"], obj_src=OBJECT_NOCOMPONENT)
    r = _still("WsShotA", tmp_path / "onocomp.png", {"object": {"id": "WsNoComp"}}, _env(ws))
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "has no component" in out, out[-800:]


@needs_toolchain
def test_the_object_receives_the_beats_t(tmp_path):
    """F8: an object whose fill depends on `t`, rendered at two frames far apart in the shot, must come back
    two different colours."""
    ws = _workshop(tmp_path, shots=["WsShotA"], objects=["WsTObj"], obj_src=OBJECT_T)
    props = {"fill": "#000000", "object": {"id": "WsTObj"}}
    r0 = _still("WsShotA", tmp_path / "t0.png", props, _env(ws), frame=0)
    r1 = _still("WsShotA", tmp_path / "t1.png", props, _env(ws), frame=25)
    assert r0.returncode == 0, (r0.stdout + r0.stderr)[-800:]
    assert r1.returncode == 0, (r1.stdout + r1.stderr)[-800:]
    early, late = _px(tmp_path / "t0.png", 960, 540), _px(tmp_path / "t1.png", 960, 540)
    assert early[2] > early[0], early     # early t (held near ENTRY_T): mostly blue
    assert late[0] > late[2], late        # t settled at 1: mostly red


@needs_toolchain
def test_the_object_receives_the_films_dna(tmp_path):
    """F8: an object that paints `dna.accent`, rendered under a named DNA preset, must show that preset's
    accent colour."""
    ws = _workshop(tmp_path, shots=["WsShotA"], objects=["WsDnaObj"], obj_src=OBJECT_DNA)
    r = _still("WsShotA", tmp_path / "dna.png",
               {"fill": "#000000", "dna": "terminal", "object": {"id": "WsDnaObj"}}, _env(ws))
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    assert _near(_px(tmp_path / "dna.png", 960, 540), (61, 214, 164))
