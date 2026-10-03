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
