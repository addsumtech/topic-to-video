"""WorldStage — one world a camera travels through across a run of beats (remotion/src/stage/WorldStage.tsx).

What is held here:
  * the lens maths (stage/worldCore.ts), run under node against the real module: a framing puts its object where it
    says; a tilt keeps the lens and turns; a crane keeps the distance; an orbit keeps to its arc; a scale-zoom holds
    its fixed point still on screen at a constant rate of zoom; the summed camera lands EXACTLY on the last framing;
    parallax is depth's, not a constant;
  * the board check (scripts/world_stage.py) names every defect that would otherwise throw half way through a render;
  * the beat-level `move` is the same number in the runtime and in the gates' mirror (scripts/stage_frames.py);
  * a world that frames nothing is a LOUD error on render, never an empty frame.
"""
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)

import _tsprobe  # noqa: E402
import stage_frames  # noqa: E402
import stage_runs  # noqa: E402
import world_stage  # noqa: E402

_REM = os.path.join(os.path.dirname(_HERE), "remotion")
CORE = json.dumps(os.path.join(_REM, "src", "stage", "worldCore"))
RUNTIME_STAGE = _tsprobe.mod("stageRun")

needs_node = pytest.mark.skipif(not _tsprobe.available(), reason="needs node + remotion/node_modules")

# a small world: two objects a camera can visit, one nested pair, and a far and a near plane for parallax
WORLD_TS = """
const U = 1080, W = 1920, H = 1080;
const v = {W, H, P: U * 1.15};
const zone = {x0: 96, y0: 120, x1: 1824, y1: 850};
const lay = C.layoutWorld({
  a: {kind: 'disc', at: [-3, 0, 0], w: 1},
  b: {kind: 'disc', at: [3, -1, -1], w: 0.5},
  big: {kind: 'frame', at: [0, 0, 0], w: 2, aspect: 1.5},
  inner: {kind: 'frame', in: 'big', uv: [0.7, 0.3], span: 0.1, aspect: 1.5},
  far: {kind: 'disc', at: [0, 0, -6], w: 1},
  near: {kind: 'disc', at: [0, 0, 1.5], w: 1},
}, U);
const S = {x: (zone.x0 + zone.x1) / 2, y: (zone.y0 + zone.y1) / 2};
const at = (cam: any, id: string) => { const o = lay.get(id)!; return C.project(cam, v, [o.x, o.y, o.z]); };
"""


def _ts(body):
    return _tsprobe.run_ts("import * as C from %s;\nimport * as R from %s;\n" % (CORE, RUNTIME_STAGE), WORLD_TS + body)


@needs_node
def test_a_framing_puts_its_object_where_it_says():
    r = _ts("""
      const c = C.targetCam({frame: 'a', fill: 0.5}, lay, v, zone, null);
      const p = at(c, 'a');
      out.contain = {x: p.x, y: p.y, w: lay.get('a')!.w * p.k};
      const off = C.targetCam({frame: 'b', fill: 0.4, offset: [0.2, -0.1]}, lay, v, zone, null);
      const q = at(off, 'b');
      out.off = {x: q.x, y: q.y};
      const cov = C.targetCam({frame: 'big', fit: 'cover'}, lay, v, zone, null);
      const g = at(cov, 'big'), o = lay.get('big')!;
      out.cover = {x: g.x, y: g.y, w: o.w * g.k, h: o.h * g.k};
      out.S = S;
    """)
    zw, zh = 1824 - 96, 850 - 120
    # contain: the object's box is `fill` of the zone on its tighter side, centred in the zone
    assert abs(r["contain"]["x"] - r["S"]["x"]) < 1e-6 and abs(r["contain"]["y"] - r["S"]["y"]) < 1e-6
    assert abs(r["contain"]["w"] - 0.5 * min(zw, zh)) < 1e-6, r["contain"]
    assert abs(r["off"]["x"] - (r["S"]["x"] + 0.2 * zw)) < 1e-6 and abs(r["off"]["y"] - (r["S"]["y"] - 0.1 * zh)) < 1e-6
    # cover: the picture ABOVE the caption band is covered (the frame's width, the top down to the zone's bottom),
    # centred there — the band stays the world's own space for the burned caption
    assert abs(r["cover"]["x"] - 960) < 1e-6 and abs(r["cover"]["y"] - 850 / 2) < 1e-6
    assert r["cover"]["w"] >= 1920 - 1e-6 and r["cover"]["h"] >= 850 - 1e-6


@needs_node
def test_tilt_keeps_the_lens_crane_keeps_the_distance_and_both_land_on_the_zone():
    r = _ts("""
      const A = C.targetCam({frame: 'a', fill: 0.4}, lay, v, zone, null);
      const T = C.targetCam({frame: 'b', move: 'tilt'}, lay, v, zone, A);
      const K = C.targetCam({frame: 'b', move: 'crane'}, lay, v, zone, A);
      const da = at(A, 'a').depth;
      out.tilt = {e: T.e, eA: A.e, p: at(T, 'b'), yaw: T.yaw, pitch: T.pitch};
      out.crane = {p: at(K, 'b'), yaw: K.yaw, pitch: K.pitch};
      // the crane's distance to b's plane is the distance A had to b's plane
      const ob = lay.get('b')!;
      out.craneDepth = at(K, 'b').depth;
      out.aDepthToB = A.e[2] - ob.z;
    """)
    assert r["tilt"]["e"] == r["tilt"]["eA"], "a tilt must not move the lens"
    assert abs(r["tilt"]["p"]["x"] - 960) < 0.5 and abs(r["tilt"]["p"]["y"] - 485) < 0.5, r["tilt"]["p"]
    assert abs(r["tilt"]["yaw"]) > 1e-3, "b is off to the side: the lens must have turned"
    assert abs(r["crane"]["p"]["x"] - 960) < 1e-6 and abs(r["crane"]["p"]["y"] - 485) < 1e-6
    assert r["crane"]["yaw"] == 0 and r["crane"]["pitch"] == 0
    assert abs(r["craneDepth"] - r["aDepthToB"]) < 1e-6


@needs_node
def test_a_scale_zoom_holds_its_fixed_point_and_zooms_at_a_constant_rate():
    """POWERS OF TEN: k runs exponentially from one framing to the next, and the one world point that lands on the same
    screen place in both framings stays there through the whole zoom (no swing, no drift)."""
    r = _ts("""
      const A = C.targetCam({frame: 'big', fill: 0.8}, lay, v, zone, null);
      const B = C.targetCam({frame: 'inner', fill: 0.8, move: 'scale-zoom'}, lay, v, zone, A);
      const ob = lay.get('inner')!;
      const centre: any = [ob.x, ob.y, ob.z];
      // the fixed point, solved on the plane: kA (F - eA) = kB (F - eB)
      const ka = 1 / (A.e[2] - ob.z), kb = 1 / (B.e[2] - ob.z);
      const F = [(ka * A.e[0] - kb * B.e[0]) / (ka - kb), (ka * A.e[1] - kb * B.e[1]) / (ka - kb), ob.z];
      out.pts = []; out.logk = [];
      for (const s of [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1]) {
        const c = C.pathCam('scale-zoom', A, B, s, centre);
        const p = C.project(c, v, F as any);
        out.pts.push([p.x, p.y]);
        out.logk.push(Math.log(p.k));
      }
      out.end = C.pathCam('scale-zoom', A, B, 1, centre); out.B = B;
    """)
    x0, y0 = r["pts"][0]
    assert all(abs(x - x0) < 1e-6 and abs(y - y0) < 1e-6 for x, y in r["pts"]), r["pts"]
    lk, ss = r["logk"], [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1]
    rate = (lk[-1] - lk[0])
    assert rate > 2, "the inner layer is a tenth of the outer: the zoom must cover that scale"
    assert all(abs((lk[i] - lk[0]) - rate * ss[i]) < 1e-9 for i in range(len(ss))), "log k must be linear in s"
    assert r["end"] == r["B"]


@needs_node
def test_a_new_framing_does_not_inherit_the_last_ones_fill():
    """The probe film's defect: camera fields merge like all state, so a cover zoom into the orbital photo inherited the
    orbit's `fill: 0.13` and stopped at a thirteenth of its size (and the next dolly inherited `cover`). A keyframe that
    names a new frame frames it its own way; only the lens's turn carries on; a keyframe naming no frame adjusts."""
    r = _ts("""
      out.newFrame = C.framingOf({frame: 'a', fill: 0.13, fit: 'cover', offset: [0.1, 0], yaw: 28}, {frame: 'b', move: 'dolly'});
      out.adjust = C.framingOf({frame: 'a', fill: 0.13, yaw: 28}, {fill: 0.8});
      out.none = C.framingOf({frame: 'a', fill: 0.13}, null);
    """)
    assert r["newFrame"] == {"frame": "b", "move": "dolly", "yaw": 28}
    assert r["adjust"] == {"frame": "a", "fill": 0.13, "yaw": 28}, "the merged state already holds the adjustment"
    assert r["none"] == {"frame": "a", "fill": 0.13}


@needs_node
def test_cruise_is_continuous_lands_exactly_and_holds_a_constant_rate():
    r = _ts("""
      out.v = []; for (let i = 0; i <= 100; i++) out.v.push(C.cruise(i / 100));
    """)
    v = r["v"]
    assert v[0] == 0 and v[-1] == 1 and all(b >= a for a, b in zip(v, v[1:]))
    steps = [b - a for a, b in zip(v, v[1:])]
    mid = steps[25:72]
    assert max(mid) - min(mid) < 1e-9, "the middle of a scale-zoom is a CONSTANT rate"
    assert steps[0] < mid[0] * 0.2 and steps[-1] < mid[0] * 0.2, "it starts and lands at rest"


@needs_node
def test_the_summed_camera_lands_on_the_last_framing_and_never_jumps():
    r = _ts("""
      const A = C.targetCam({frame: 'a', fill: 0.4}, lay, v, zone, null);
      const B = C.targetCam({frame: 'b', fill: 0.4, yaw: 20, move: 'orbit'}, lay, v, zone, A);
      const D = C.targetCam({frame: 'big', fill: 0.7}, lay, v, zone, B);
      const ob = lay.get('b')!, og = lay.get('big')!;
      // the third move starts BEFORE the second has landed: the speed carries on, the landing is still exact
      const keys = [{from: 0, to: 0, kind: 'dolly', target: A, centre: null},
                    {from: 10, to: 50, kind: 'orbit', target: B, centre: [ob.x, ob.y, ob.z]},
                    {from: 40, to: 80, kind: 'dolly', target: D, centre: [og.x, og.y, og.z]}];
      out.jumps = []; let prev: any = null;
      for (let f = 0; f <= 100; f++) {
        const c = C.camAtFrame(keys as any, f, 30, false);
        if (prev) out.jumps.push(Math.hypot(c.e[0] - prev.e[0], c.e[1] - prev.e[1], c.e[2] - prev.e[2]));
        prev = c;
      }
      out.end = C.camAtFrame(keys as any, 100, 30, false); out.D = D;
      out.start = C.camAtFrame(keys as any, 5, 30, false); out.A = A;
    """)
    for k in ("e",):
        assert all(abs(a - b) < 1e-6 for a, b in zip(r["end"][k], r["D"][k]))
        assert all(abs(a - b) < 1e-9 for a, b in zip(r["start"][k], r["A"][k]))
    assert abs(r["end"]["yaw"] - r["D"]["yaw"]) < 1e-9 and abs(r["end"]["pitch"] - r["D"]["pitch"]) < 1e-9
    j = r["jumps"]
    # no frame moves the lens more than a small multiple of its neighbours: a jump would stand out ~10x
    for i in range(2, len(j) - 2):
        local = max(j[i - 2], j[i - 1], j[i + 1], j[i + 2], 1e-6)
        assert j[i] < 3 * local + 1e-6, (i, j[i - 2:i + 3])


@needs_node
def test_parallax_is_depth():
    """A dolly sideways moves a near plane further across the screen than the framed one, and a far plane less, in
    the ratio the depths give — the differential that reads as a camera (references/motion-research.md §2)."""
    r = _ts("""
      const c0 = {e: [0, 0, 3000] as any, yaw: 0, pitch: 0, fd: 3000};
      const c1 = {...c0, e: [200, 0, 3000] as any};
      const d = (id: string) => at(c1, id).x - at(c0, id).x;
      out.near = d('near'); out.mid = d('big'); out.far = d('far');
      out.depths = ['near', 'big', 'far'].map((id) => at(c0, id).depth);
    """)
    assert r["near"] < r["mid"] < r["far"] < 0, r
    # screen shift = -dx * P / depth
    for name, dep in zip(("near", "mid", "far"), r["depths"]):
        assert abs(r[name] - (-200 * 1080 * 1.15 / dep)) < 1e-6


@needs_node
def test_a_world_that_cannot_lay_out_throws_naming_the_object():
    r = _ts("""
      const tryIt = (o: any) => { try { C.layoutWorld(o, 1080); return 'ok'; } catch (e: any) { return String(e.message); } };
      out.parent = tryIt({x: {in: 'nope', span: 0.5}});
      out.loop = tryIt({x: {in: 'y', span: 0.5}, y: {in: 'x', span: 0.5}});
      out.span = tryIt({p: {at: [0, 0, 0], w: 1}, x: {in: 'p', span: 1.2}});
      out.at = tryIt({x: {w: 1}});
      out.frame = (() => { try { C.targetCam({frame: 'ghost'}, C.layoutWorld({a: {at: [0,0,0], w: 1}}, 1080), v, zone, null);
        return 'ok'; } catch (e: any) { return String(e.message); } })();
    """)
    assert '"nope"' in r["parent"]
    assert "nested inside itself" in r["loop"]
    assert "span" in r["span"] and '"x"' in r["span"]
    assert "`at`" in r["at"]
    assert '"ghost"' in r["frame"] and "not an object of the world" in r["frame"]


@needs_node
def test_a_beats_own_move_is_the_same_number_in_the_runtime_and_in_the_gates_mirror():
    r = _ts("""
      const beats = [{index: 0, start: 0, durF: 120, props: {}}, {index: 1, start: 120, durF: 150, props: {move: 3}},
                     {index: 2, start: 270, durF: 60, props: {move: 9}}, {index: 3, start: 330, durF: 90, props: {}}];
      out.keys = R.buildKeys(beats as any, 30).map((k: any) => [k.from, k.to]);
      out.stateHasMove = R.buildKeys(beats as any, 30).some((k: any) => 'move' in k.state);
    """)
    scenes = [{"durF": 120, "stage": {"run": "r"}, "props": {}}, {"durF": 150, "stage": {"run": "r"}, "props": {"move": 3}},
              {"durF": 60, "stage": {"run": "r"}, "props": {"move": 9}}, {"durF": 90, "stage": {"run": "r"}, "props": {}}]
    py = [[k["from"], k["to"]] for k in stage_frames.keyframes(scenes, 0, 3, 30)]
    assert r["keys"] == py == [[0, 0], [120, 210], [270, 315], [330, 354]]
    assert not r["stateHasMove"], "a beat's `move` is timing, not state an actor reads"


def _run(**over):
    world = {"objects": {"sun": {"kind": "image", "image": "media/sun.jpg", "at": [-3, 0, 0], "w": 1, "label": "太阳"},
                         "earth": {"kind": "globe", "at": [0, 0, 0], "w": 1},
                         "ring": {"kind": "frame", "in": "earth", "uv": [0.5, 0.2], "span": 0.3},
                         "moon": {"kind": "disc", "at": [2, 0, 0], "w": 0.3}}}
    b1 = {"world": world, "camera": {"frame": "sun"}, "labels": ["sun"]}
    b1.update(over.get("b1", {}))
    b2 = over.get("b2", {"camera": {"frame": "earth", "move": "dolly"}})
    b3 = over.get("b3", {"camera": {"frame": "ring", "move": "scale-zoom"}})
    return [{"index": i + 1, "shot": "WorldStage", "stage": {"run": "w"}, "shot_props": p, "narration": "太阳 地球"}
            for i, p in enumerate((b1, b2, b3))]


def test_a_sound_world_has_no_problems(tmp_path):
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "sun.jpg").write_bytes(b"x")
    assert world_stage.check(_run(), 0, 2, str(tmp_path)) == []
    assert stage_runs.check(_run()) == []


def test_the_board_check_names_what_the_stage_would_throw_on(tmp_path):
    cases = {
        "frames 'ghost'": _run(b2={"camera": {"frame": "ghost"}}),
        "`labels` names 'pluto'": _run(b1={"labels": ["pluto"]}),
        "which has no `label`": _run(b1={"labels": ["moon"]}),
        "not on one nest chain": _run(b3={"camera": {"frame": "moon", "move": "scale-zoom"}}),
        "keeps the lens's turn": _run(b3={"camera": {"frame": "ring", "move": "scale-zoom", "yaw": 10}}),
        "is not one the stage draws": _run(b2={"camera": {"frame": "earth", "move": "whip"}}),
        "nested inside itself": _run(b2={"world": {"objects": {"earth": {"in": "ring", "span": 0.5, "at": None}}}}),
        "SMALLER than its parent": _run(b2={"world": {"objects": {"ring": {"span": 1.5}}}}),
        "has kind 'cube'": _run(b2={"world": {"objects": {"moon": {"kind": "cube"}}}}),
        "is not a file": _run(),
    }
    for want, slides in cases.items():
        got = world_stage.check(slides, 0, 2, str(tmp_path))
        assert any(want in p for p in got), (want, got)
    # the camera framing an object the world REMOVED at that keyframe is named too (`null` removes)
    gone = _run(b2={"world": {"objects": {"moon": None}}, "camera": {"frame": "moon"}})
    assert any("frames 'moon'" in p for p in world_stage.check(gone, 0, 2))
    # and validate/render see it through stage_runs.check, per run
    assert any("frames 'ghost'" in p for p in stage_runs.check(_run(b2={"camera": {"frame": "ghost"}})))


def test_a_world_picture_carries_its_drawn_shape_and_a_missing_one_is_loud(tmp_path):
    from PIL import Image
    (tmp_path / "media").mkdir()
    Image.new("RGB", (300, 200), "white").save(str(tmp_path / "media" / "sun.jpg"))
    props = _run()[0]["shot_props"]
    out = stage_runs.stamp_faces(props, str(tmp_path))
    sun = out["world"]["objects"]["sun"]
    assert sun["imageAspect"] == 1.5 and sun["imageW"] == 300
    assert "imageAspect" not in props["world"]["objects"]["sun"], "the board's own props are never written"
    os.remove(str(tmp_path / "media" / "sun.jpg"))
    with pytest.raises(FileNotFoundError):
        stage_runs.stamp_faces(props, str(tmp_path))


def test_a_choreographed_world_is_this_films_built_signature():
    import validate
    routes = {n: r for n, r, _why in validate.design_routes({}, _run(), None)}
    assert routes == {1: "built", 2: "built", 3: "built"}


@pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")), reason="needs the remotion toolchain")
def test_a_camera_that_frames_nothing_is_a_loud_render_error(tmp_path):
    scene = {"shot": "WorldStage", "durF": 60, "stage": {"run": "w"},
             "props": {"world": {"objects": {"a": {"kind": "disc", "at": [0, 0, 0], "w": 1}}}, "camera": {"frame": "ghost"}}}
    pf = str(tmp_path / "p.json")
    json.dump({"scenes": [scene], "dna": "cinematic", "captions": False, "camera": 0, "cameraBed": False},
              open(pf, "w", encoding="utf-8"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", str(tmp_path / "x.png"), "--frame=10",
                        "--gl=angle", "--log=error", "--props=" + pf], cwd=_REM, capture_output=True, text=True,
                       timeout=900)
    assert r.returncode != 0
    assert 'frames "ghost"' in (r.stdout + r.stderr), (r.stdout + r.stderr)[-800:]
