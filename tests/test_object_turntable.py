"""ObjectTurntable: an object that draws its own 3D is handed the turn (yaw) and turns for real; any other object
turns as a card, at most ±60°, and a larger sweep on it is refused rather than flattened."""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json  # noqa: E402
import workshop as ws  # noqa: E402
import text_safe_qa as g  # noqa: E402
import _tsprobe as tp  # noqa: E402
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


@pytest.mark.skipif(not tp.available(), reason="needs node and the remotion toolchain")
def test_the_rim_marks_travel_the_way_the_object_turns():
    """The accent mark on the platter's rim is there to show the turn, so at the platter's near edge it must move
    the same way as the near edge of the object it carries — a point turned by runtime/project3d's yawPoint, the
    convention a `turns` object draws with (and the card's CSS rotateY follows)."""
    shot = json.dumps(os.path.join(_REM, "src", "shots", "ObjectTurntable.tsx"))
    out = tp.run_ts(
        "import {rimTickDeg} from %s; import {yawPoint} from %s;" % (shot, tp.mod("project3d.ts")),
        "const rad = (d: number) => (d * Math.PI) / 180;"
        "const near = 6;"                       # 6 of 24 marks round = 90 degrees: the near edge at rest
        "const at = (yaw: number) => ({mark: Math.cos(rad(rimTickDeg(near, yaw))),"
        "                              point: yawPoint([0, 0, 1], rad(yaw))[0]});"
        "out.rest = at(0); out.turned = at(12); out.back = at(-12);")
    for later in ("turned", "back"):
        mark = out[later]["mark"] - out["rest"]["mark"]
        point = out[later]["point"] - out["rest"]["point"]
        assert mark * point > 0, (later, out)   # both to the right, or both to the left — never apart


@needs_toolchain
def test_a_negative_sweep_turns_the_object_the_other_way(film, tmp_path):
    env = _env(ws.workshop_dir(film))
    props = dict(PROPS, object={"id": "WsTurns"}, sweep=-80, dna="product")
    early = _still("ObjectTurntable", tmp_path / "e.png", props, env, frame=25)
    late = _still("ObjectTurntable", tmp_path / "l.png", props, env, frame=165)
    assert early.returncode == 0 and late.returncode == 0, (early.stderr + late.stderr)[-800:]
    assert _mask(tmp_path / "e.png", (0, 255, 255))[0] > 20000        # yaw > 0 at the start of a negative turn
    assert _mask(tmp_path / "l.png", (255, 0, 255))[0] > 20000        # yaw < 0 by its end


@needs_toolchain
@pytest.mark.parametrize("sweep", [-10, -400])
def test_a_negative_sweep_is_held_to_the_same_range(film, tmp_path, sweep):
    r = _still("ObjectTurntable", tmp_path / "x.png", dict(PROPS, object={"id": "WsTurns"}, sweep=sweep),
               _env(ws.workshop_dir(film)))
    assert r.returncode != 0 and "20-360 either way" in r.stdout + r.stderr, (r.stdout + r.stderr)[-800:]


@needs_toolchain
def test_a_flat_object_is_never_turned_past_its_edge_the_other_way_either(film, tmp_path):
    r = _still("ObjectTurntable", tmp_path / "x.png", dict(PROPS, object={"id": "WsFlat"}, sweep=-200),
               _env(ws.workshop_dir(film)))
    assert r.returncode != 0 and "at most 120" in r.stdout + r.stderr, (r.stdout + r.stderr)[-800:]
