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
