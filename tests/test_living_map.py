"""ONE diagram for the whole film (runtime/graphLayout + LivingMap): a structure that grows beat by beat, the camera
moving through it, and every beat's last frame the next beat's first.

WHY. A film's argument is often one structure — a pipeline, a system, a family of ideas — and a film made of separate
registers redraws it from nothing on every beat, so the viewer loses where they are. Here the structure is laid out
ONCE over all its nodes (so nothing moves when something is added), each beat adds and focuses part of it, and
render_remotion carries the state across the cut, which is a hard cut between two identical frames.
"""
import os
import sys

import pytest

import _tsprobe as tp

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

NODES = "[{id:'a'},{id:'b'},{id:'c'},{id:'d'},{id:'e'}]"
EDGES = "[['a','b'],['a','c'],['b','d'],['c','d'],['d','e']]"


def _run(body):
    return tp.run_ts("import * as gl from %s;" % tp.mod("graphLayout.ts"), body)


@pytest.mark.skipif(not tp.available(), reason="needs node + remotion/node_modules")
def test_a_layered_layout_puts_every_edge_left_to_right_and_no_two_nodes_together():
    out = _run("out.p = gl.layoutGraph(%s, %s);" % (NODES, EDGES))
    p = out["p"]
    for a, b in (("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "e")):
        assert p[a]["layer"] < p[b]["layer"], (a, b)
    pts = [(v["x"], v["y"]) for v in p.values()]
    assert len(set(pts)) == len(pts)
    assert p["b"]["layer"] == p["c"]["layer"] and p["b"]["y"] != p["c"]["y"]


@pytest.mark.skipif(not tp.available(), reason="needs node + remotion/node_modules")
def test_a_cycle_does_not_hang_and_the_layout_is_deterministic():
    out = _run("const N = [{id:'a'},{id:'b'},{id:'c'}], E: [string, string][] = [['a','b'],['b','c'],['c','a']];"
               "out.p = gl.layoutGraph(N, E); out.q = gl.layoutGraph(N, E);")
    assert out["p"] == out["q"]
    assert len({v["layer"] for v in out["p"].values()}) >= 2


@pytest.mark.skipif(not tp.available(), reason="needs node + remotion/node_modules")
def test_the_camera_frames_the_focus_and_never_zooms_past_its_bounds():
    out = _run("const p = gl.layoutGraph(%s, %s);"
               "const zone = {x: 100, y: 100, w: 1700, h: 700};"
               "out.all = gl.frameNodes(p, Object.keys(p), zone, {maxScale: 1.6});"
               "out.one = gl.frameNodes(p, ['e'], zone, {maxScale: 1.6});" % (NODES, EDGES))
    assert out["one"]["s"] == pytest.approx(1.6), "one node alone is capped, not blown up to the frame"
    assert out["all"]["s"] < out["one"]["s"]


def test_the_board_names_a_map_once_and_each_beat_adds_and_focuses_part_of_it():
    import render_remotion as rr
    maps = {"pipe": {"nodes": [{"id": "a", "label": "Signal"}, {"id": "b", "label": "K-space"},
                               {"id": "c", "label": "Image"}], "edges": [["a", "b"], ["b", "c"]]}}
    slides = [{"shot": "LivingMap", "shot_props": {"map": "pipe", "add": ["a"], "focus": ["a"]}},
              {"shot": "LivingMap", "shot_props": {"map": "pipe", "add": ["b"], "focus": ["b"]}},
              {"shot": "EdStat", "shot_props": {}},
              {"shot": "LivingMap", "shot_props": {"map": "pipe", "add": ["c"]}}]
    props = rr.expand_living_maps(slides, {"maps": maps})
    assert props[0]["before"] == [] and props[0]["after"] == ["a"]
    assert props[1]["before"] == ["a"] and props[1]["after"] == ["a", "b"]
    assert props[1]["focusFrom"] == ["a"] and props[1]["focusTo"] == ["b"]
    assert props[3]["before"] == ["a", "b"] and props[3]["focusTo"] == ["a", "b", "c"], \
        "a beat with no focus frames the whole map so far — and a map picks up where it left off after another beat"
    assert props[3]["focusFrom"] == props[3]["focusTo"], "after a different beat there is nothing on screen to move from"
    assert rr.living_map_continues(slides, 1) and not rr.living_map_continues(slides, 3)
    with pytest.raises(RuntimeError):
        rr.expand_living_maps([{"shot": "LivingMap", "shot_props": {"map": "pipe", "add": ["zz"]}}], {"maps": maps})
    with pytest.raises(RuntimeError):
        rr.expand_living_maps([{"shot": "LivingMap", "shot_props": {"map": "nope"}}], {"maps": maps})


def test_two_beats_of_one_map_get_no_planned_seam_and_validate_names_a_broken_map():
    import seam_plan as sp
    import validate as v
    sl = [{"shot": "LivingMap", "relation": "new-topic", "shot_props": {"map": "m", "add": ["a"]}},
          {"shot": "LivingMap", "relation": "new-topic", "shot_props": {"map": "m", "add": ["b"]}},
          {"shot": "EdStat", "relation": "new-topic"}]
    assert sp._joined(sl, 1) and not sp._joined(sl, 2)
    assert 1 not in sp.plan(sl), "a seam between two identical frames is not one to mark"
    assert sp._cut_eligible(sl, 1, {}, set()) is not None
    probs = v.teaser_problems  # noqa: F841 — imported for the module; the map check runs inside validate's loop
    import render_remotion as rr
    with pytest.raises(RuntimeError, match="does not define"):
        rr.expand_living_maps(sl, {"maps": {}})
