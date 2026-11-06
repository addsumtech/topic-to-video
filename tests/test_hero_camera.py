"""The hero camera grammar (spec 2026-11-06 F). Apple-style product films run hero → detail → context with a slow,
restrained camera; and a DOLLY changes perspective where a zoom only enlarges, which is why our 2D push read flat.
`reveal`, `macro` and `context` move a hero beat's layers by their depth (parallax), blur by depth on `macro`, and
hold every label until the move has settled — type under a moving camera measured 0.16 px tremble (jitter_qa)."""
import json
import os
import sys

import pytest

import _tsprobe as tp

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import render_remotion as rr  # noqa: E402
import validate as v  # noqa: E402

needs_node = pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")
IMP = "import {heroCamera, labelOpacity, HERO_SETTLE} from %s;" % tp.mod("heroCamera.tsx")


@needs_node
def test_layers_at_different_depths_move_different_amounts():
    o = tp.run_ts(IMP, "out.a = heroCamera('reveal', 0.2, [1, 3]); out.z = heroCamera('reveal', 1, [1, 3]);")
    near, far = o["a"]
    assert abs(near["tx"]) > abs(far["tx"]) > 0 and near["scale"] != far["scale"]
    assert all(l == {"tx": 0, "ty": 0, "scale": 1, "blur": 0} for l in o["z"])      # settled: the composed frame


@needs_node
def test_macro_blurs_by_distance_from_the_focus_plane_and_context_pulls_back():
    o = tp.run_ts(IMP, """out.m = heroCamera('macro', 1, [1, 2, 0.6]); out.c0 = heroCamera('context', 0, [1]);
out.c1 = heroCamera('context', 1, [1]);""")
    sharp, back, front = o["m"]
    assert sharp["blur"] == 0 and back["blur"] > 0 and front["blur"] > 0 and sharp["scale"] > 1
    assert o["c0"][0]["scale"] > o["c1"][0]["scale"] == 1


@needs_node
def test_labels_wait_for_the_move_to_settle():
    o = tp.run_ts(IMP, """out.s = HERO_SETTLE; out.v = [0, 0.3, 0.69].map((t) => labelOpacity('reveal', t));
out.after = labelOpacity('reveal', 0.95); out.none = labelOpacity(null, 0.1);""")
    assert all(x == 0 for x in o["v"]) and o["after"] == 1 and o["none"] == 1 and o["s"] == 0.7


@needs_node
def test_an_unknown_move_is_refused():
    with pytest.raises(AssertionError, match="heroCamera"):
        tp.run_ts(IMP, "out.a = heroCamera('orbit' as any, 0.5, [1]);")


def test_the_renderer_passes_the_hero_moves():
    for m in ("reveal", "macro", "context"):
        assert rr._camera({"camera": {"move": m}}) == {"move": m}


def _film(tmp_path, shot_src, hero=True):
    d = tmp_path / "f"
    (d / "workshop" / "shots").mkdir(parents=True)
    (d / "workshop" / "shots" / "SwitchMacro.tsx").write_text(shot_src)
    slides = [{"index": 1, "shot": "SwitchMacro", "camera": {"move": "macro"}}, {"index": 2, "shot": "SwitchMacro"}]
    meta = {"renderer": "remotion", "hero_moments": [1] if hero else [2]}
    return meta, slides, str(d)


def test_a_hero_move_on_a_shot_that_reads_its_layers_is_clean(tmp_path):
    meta, slides, d = _film(tmp_path, "const p = useHeroLayer(2);")
    assert v._hero_camera(meta, slides, d) == ([], [])


def test_a_hero_move_on_a_shot_with_no_layers_is_an_error_not_a_silent_hold(tmp_path):
    meta, slides, d = _film(tmp_path, "export const SwitchMacro = () => null;")
    errs, _w = v._hero_camera(meta, slides, d)
    assert errs and "useHeroLayer" in errs[0] and "beat 1" in errs[0]


def test_a_hero_move_off_a_hero_beat_warns(tmp_path):
    meta, slides, d = _film(tmp_path, "const p = useHeroLayer(2);", hero=False)
    errs, warns = v._hero_camera(meta, slides, d)
    assert not errs and any("hero_moments" in w for w in warns)


def test_validate_knows_the_hero_moves():
    board = {"meta": {"renderer": "remotion"}, "slides": [
        {"index": 1, "shot": "CinematicTitle", "camera": {"move": "reveal"}, "narration": "x", "duration": 4.0,
         "audio": "a.mp3"}]}
    r = v.evaluate(board, "/tmp")
    assert not any("silently drop" in m for m in r["errors"] + r["warnings"]), r["errors"] + r["warnings"]
