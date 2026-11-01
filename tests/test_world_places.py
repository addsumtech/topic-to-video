"""The PLACE a beat happens in — drawn behind it, chosen from the beat's own subject (runtime/world.tsx, places.json).

WHY. A paper-cut reference film sets every scene inside an illustrated world; our styled film put small drawings on a
flat ground. A first spike drew ONE landscape behind every beat and the user rejected it: "卫星的背景怎么可能是山水，
请根据实际来弄" — then "你不要所有都换成太空场景，你要适配内容". A place is a FACT about a beat, named from what the
beat is about (a satellite is in orbit, "high above you" is the sky), and a beat about an idea names none.

A place stands on its own ground (space is dark), so it is a declared ground: only a register that FOLLOWS a declared
ground may stand in it, and validate says so before a render, not minutes into one.
"""
import json
import os

import pytest

import validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACES = os.path.join(ROOT, "remotion", "src", "runtime", "places.json")


def _places():
    return json.load(open(PLACES, encoding="utf-8"))


def test_every_place_names_its_ground_and_why():
    p = {k: v for k, v in _places().items() if not k.startswith("_")}
    assert {"orbit", "sky", "field", "room"} <= set(p)
    for name, spec in p.items():
        assert spec["ground"].startswith("#") and len(spec["ground"]) == 7, name
        assert len(spec.get("for", "")) > 10, "%s: say what subject this place is for" % name


def test_the_runtime_reads_the_same_places():
    import _tsprobe
    if not _tsprobe.available():
        pytest.skip("node/esbuild not available")
    out = _tsprobe.run_ts("import {PLACES, placeGround} from %s;" % _tsprobe.mod("world.tsx"),
                          "out.p = PLACES; out.g = PLACES.map((k: string) => placeGround(k));")
    p = {k: v for k, v in _places().items() if not k.startswith("_")}
    assert sorted(out["p"]) == sorted(p)
    assert out["g"] == [p[k]["ground"] for k in out["p"]]


def _board(world, shot="ObjectStage", style_world="place", ground=None):
    sl = {"index": 1, "shot": shot, "duration": 5.0, "narration": "x", "caption": "x", "shot_props": {}}
    if world:
        sl["world"] = world
    if ground:
        sl["ground"] = ground
    meta = {"renderer": "remotion", "style": {"name": "t", "refs": [], "refs_missing": "test",
                                              "surface": {"world": style_world}}}
    return {"meta": meta, "slides": [sl]}


def test_render_props_carry_the_place_and_its_ground(tmp_path):
    import shutil
    import subprocess
    import render_remotion as rr
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg needed for the audio stub")
    (tmp_path / "audio").mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "5",
                    str(tmp_path / "audio" / "01.wav")], check=True)
    b = _board("orbit")
    b["slides"][0]["audio"] = "audio/01.wav"
    scenes = rr.build_scenes(b["slides"], str(tmp_path), None, 30)
    assert scenes[0]["world"] == "orbit" and scenes[0]["ground"] == _places()["orbit"]["ground"]
    b = _board("sky", ground="#123456")                       # an authored ground wins
    b["slides"][0]["audio"] = "audio/01.wav"
    assert rr.build_scenes(b["slides"], str(tmp_path), None, 30)[0]["ground"] == "#123456"


def _check(board):
    errors, warnings = [], []
    validate._check_places(board["meta"], board["slides"], errors, warnings)
    validate._beat_grounds(validate._place_grounds(board["slides"]), errors, warnings)
    return errors, warnings


def test_an_unknown_place_is_an_error():
    errors, _ = _check(_board("castle"))
    assert any("castle" in e for e in errors), errors


def test_a_place_on_a_register_that_does_not_follow_a_ground_is_an_error_before_the_render():
    """Measured: an orbit place on KnowledgeGraph (cartoon GPS film, beat 4) — the runtime refused it mid-render and the
    census then waited out its timeout. Its dark ink would have vanished into space."""
    errors, _ = _check(_board("orbit", shot="KnowledgeGraph"))
    assert any("does not follow" in e for e in errors), errors
    errors, _ = _check(_board("orbit", shot="ObjectStage"))
    assert errors == [], errors


def test_a_place_the_style_does_not_draw_is_said():
    _, warnings = _check(_board("orbit", style_world="none"))
    assert any("surface.world" in w for w in warnings), warnings
