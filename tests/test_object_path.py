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
