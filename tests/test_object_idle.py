"""A HELD OBJECT KEEPS ITS OWN CYCLE GOING — the idle clock (runtime/objectSlot).

The stage registers run a built object's `t` over a reveal window and then HOLD it so the words can name a settled
thing; from there to the cut the frame was frozen (four acceptance films had to waive film_energy's MOTION axis).
The slot now also hands `idle`: seconds held since the host's reveal ended, gliding up from rest and back down to
rest before the cut. Off under reduced motion, on a beat that says `"object_idle": false`, for an object whose META
says `idle: false`, and on a host that names no `idleFrom`.

The object below paints its idle clock as a colour (magenta while 0, cyan once it runs), so a frame says
which clock the object was handed. (A twentieth of a second, not more: a turntable's
own short standalone preview holds its object for under half a second.)"""
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
import render_remotion as rr  # noqa: E402
import _tsprobe as tp  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402
from test_object_stage import _mask  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

IDLE_COLOUR = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'%(extra)s};
export const %(name)s: React.FC<ObjectProps> = ({w, h, idle}) => (
  <div style={{width: w, height: h, background: (idle ?? 0) > 0.05 ? '#00ffff' : '#ff00ff'}} />
);
"""
CYAN, MAGENTA = (0, 255, 255), (255, 0, 255)
OBJ = {"id": "WsIdle"}


@pytest.fixture(scope="module")
def film(tmp_path_factory):
    out = tmp_path_factory.mktemp("idle") / "film"
    d = out / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "WsIdle.tsx").write_text(IDLE_COLOUR % {"name": "WsIdle", "extra": ""}, encoding="utf-8")
    (d / "WsStatic.tsx").write_text(IDLE_COLOUR % {"name": "WsStatic", "extra": ", idle: false"}, encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


def _duration(comp):
    import re
    src = open(os.path.join(_REM, "src", "shots", comp + ".tsx"), encoding="utf-8").read()
    return int(re.search(r"export const DURATION = (\d+);", src).group(1))


def _probe(body):
    if not tp.available():
        pytest.skip("needs the remotion toolchain")
    return tp.run_ts("import {idleSeconds, IDLE_RAMP_S} from %s;\n"
                     "import {pathArrival, pathProgress} from %s;"
                     % (tp.mod("objectSlot.tsx"), json.dumps(os.path.join(_REM, "src", "shots", "ObjectPath.tsx"))),
                     body)


def test_the_idle_clock_starts_and_stops_at_rest_and_runs_at_one_second_per_second_between():
    out = _probe("""
      const span = 420, fps = 30, from = 0.6, N = 4000;   // a 15 s beat: a 6 s hold, room for both ramps
      out.ts = Array.from({length: N + 1}, (_, i) => i / N);
      out.v = out.ts.map((t: number) => idleSeconds(t, from, span, fps));
      out.H = (1 - from) * span / ((1 - 0.06) * fps);
      out.r = IDLE_RAMP_S;
      out.short = idleSeconds(1, 0.97, span, fps);
      out.bad = [idleSeconds(NaN, 0.6, span, fps), idleSeconds(0.9, 1, span, fps), idleSeconds(0.9, 0.6, 0, fps)];
    """)
    ts, v, H = out["ts"], out["v"], out["H"]
    assert all(x == 0 for t, x in zip(ts, v) if t <= 0.6), "the idle clock must not run during the reveal"
    assert all(b >= a - 1e-12 for a, b in zip(v, v[1:])), "the idle clock never runs backwards"
    steps = [b - a for a, b in zip(v, v[1:])]
    dt = H / (0.4 * 4000)                                   # seconds per sample inside the hold
    assert max(steps) <= dt * 1.0001, "it never runs faster than one second per second"
    hold = [s for t, s in zip(ts, steps) if t > 0.6]
    assert hold[0] < dt * 0.01 and hold[-1] < dt * 0.01, "it must start and stop at rest (no jolt at either end)"
    mid = [s for t, s in zip(ts, steps) if 0.75 < t < 0.85]
    assert all(abs(s - dt) < dt * 1e-6 for s in mid), "between the ramps it is a plain clock"
    assert abs(v[-1] - (H - out["r"])) < 1e-9, (v[-1], H)
    assert 0 < out["short"] < 0.5, "a hold shorter than two ramps still glides, never jumps"
    assert out["bad"] == [0, 0, 0], "a nonsense clock is no idle, not NaN"


def test_the_path_object_idles_from_the_moment_it_stands_at_its_last_station():
    out = _probe("""
      out.r = [2, 3, 4, 5].map((n: number) => {
        const a = pathArrival(n);
        return [pathProgress(a - 1e-4, n), pathProgress(a + 1e-9, n)];
      });
      out.one = pathArrival(1);
    """)
    for before, after in out["r"]:
        assert before < 1 and after == 1, out["r"]
    assert out["one"] == 0.22


@needs_toolchain
@pytest.mark.parametrize("comp,props", [
    ("ObjectStage", {"object": OBJ, "title": "一个东西"}),
    ("ObjectCompare", {"first": OBJ, "second": OBJ, "difference": "不同"}),
    ("ObjectPath", {"object": OBJ, "stations": ["甲", "乙", "丙"]}),
    ("ObjectTurntable", {"object": OBJ}),
    ("TechnicalPlate", {"art": OBJ, "parts": [], "object": "一个东西"}),
])
def test_every_stage_hands_its_held_object_a_running_idle_clock(film, tmp_path, comp, props):
    frame = _duration(comp) - 1 - 12 - 2           # just before useT lands at 1 (the outgoing dissolve's hold)
    env = _env(ws.workshop_dir(film))
    early = _still(comp, tmp_path / "early.png", dict(props, dna="product"), env, frame=40)
    assert early.returncode == 0, (early.stdout + early.stderr)[-800:]
    assert _mask(tmp_path / "early.png", MAGENTA)[0] > 2000, "mid-reveal the idle clock must still be 0"
    late = _still(comp, tmp_path / "late.png", dict(props, dna="product"), env, frame=frame)
    assert late.returncode == 0, (late.stdout + late.stderr)[-800:]
    assert _mask(tmp_path / "late.png", CYAN)[0] > 2000, "%s froze its held object: idle never ran" % comp
    assert _mask(tmp_path / "late.png", MAGENTA)[0] == 0


@needs_toolchain
def test_an_object_that_declares_idle_false_is_never_moved(film, tmp_path):
    env = _env(ws.workshop_dir(film))
    r = _still("ObjectStage", tmp_path / "s.png", {"object": {"id": "WsStatic"}, "dna": "product"}, env, frame=158)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    assert _mask(tmp_path / "s.png", MAGENTA)[0] > 2000 and _mask(tmp_path / "s.png", CYAN)[0] == 0


def _film_still(film, png, scene_extra=None, reduced=False):
    scene = {"shot": "ObjectStage", "props": {"object": OBJ}, "durF": 165}
    scene.update(scene_extra or {})
    return _still("Film", png, {"scenes": [scene], "captions": False, "reducedMotion": reduced},
                  _env(ws.workshop_dir(film)), frame=150)


@needs_toolchain
@pytest.mark.parametrize("why,extra,reduced,want", [
    ("on by default (the control: the two below must not pass vacuously)", None, False, CYAN),
    ("a beat that turns it off", {"objectIdle": False}, False, MAGENTA),
    ("reduced motion", None, True, MAGENTA),
])
def test_the_film_runs_it_unless_the_beat_or_reduced_motion_turns_it_off(film, tmp_path, why, extra, reduced, want):
    r = _film_still(film, tmp_path / "f.png", extra, reduced)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    other = MAGENTA if want == CYAN else CYAN
    assert _mask(tmp_path / "f.png", want)[0] > 2000 and _mask(tmp_path / "f.png", other)[0] == 0, why


def _beat(**extra):
    s = {"index": 0, "shot": "ObjectStage", "duration": 5.0, "audio": "audio/00.mp3", "narration": "一拍",
         "shot_props": {"object": OBJ}}
    s.update(extra)
    return [s]


def test_the_storyboard_switch_reaches_the_scene_and_a_non_boolean_is_refused():
    assert rr.build_scenes(_beat(object_idle=False), "/tmp", {"ObjectStage"})[0]["objectIdle"] is False
    assert "objectIdle" not in rr.build_scenes(_beat(), "/tmp", {"ObjectStage"})[0]
    assert "objectIdle" not in rr.build_scenes(_beat(object_idle=True), "/tmp", {"ObjectStage"})[0]
    with pytest.raises(RuntimeError, match="object_idle must be true or false"):
        rr.build_scenes(_beat(object_idle="false"), "/tmp", {"ObjectStage"})


def test_idle_is_a_slot_key_a_film_cannot_set():
    assert "idle" in ws.SLOT_KEYS
