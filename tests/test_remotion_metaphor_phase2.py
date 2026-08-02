"""Metaphor phase-2 backstops: diverging-pair + converging-scatter (2.5D) + the 3D stacking-accretion verb.
Verified from renders; here we lock the coercion, determinism (hash1 not Math.random; analytical draw-on
not getTotalLength), and the python<->TS stack-layout constant match (else labels float off the columns)."""
import os

import pytest
import render_remotion as rr
import storyboard as sb

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


def _mb(el):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "a"
    s["duration"] = 5.0
    s["stage"] = {"elements": [{"id": "g", "kind": "grid", "position": [0, 0, -1]},
                               {**el, "id": "m", "position": [0, 0, 0]}]}
    s["shots"] = [{"type": "HERO", "target": "m"}]
    d["slides"] = [s]
    return d


def _b3d(planes):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic3d", {}, narration="x")
    s["audio"] = "a"
    s["duration"] = 4.0
    s["planes"] = planes
    d["slides"] = [s]
    return d


def test_diverging_pair_coerces(tmp_path):
    m = rr.build_props(_mb({"kind": "metaphor", "concept": "diverging-pair", "values": [40, 90]}), str(tmp_path))["scenes"][0]["stage"]["elements"][-1]
    assert m["values"] == [40.0, 90.0]


def test_converging_scatter_any_arity(tmp_path):
    m = rr.build_props(_mb({"kind": "metaphor", "concept": "converging-scatter", "values": [1200]}), str(tmp_path))["scenes"][0]["stage"]["elements"][-1]
    assert m["concept"] == "converging-scatter" and m["values"] == [1200.0]


def test_phase2_verbs_present_and_safe():
    src = _src("remotion", "src", "stage", "elements.tsx")
    assert "'diverging-pair'" in src and "'converging-scatter'" in src
    assert "hash1" in src, "deterministic scatter helper"
    assert "getTotalLength" not in src, "draw-on length must be analytical (getTotalLength is 0/unstable off-thread)"


def test_stack_kind_accepted_and_data_required(tmp_path):
    p = rr.build_props(_b3d([{"kind": "stack", "position": [0, 0, 0], "data": [4, 7, 11]}]), str(tmp_path))["scenes"][0]["planes"][0]
    assert p["kind"] == "stack" and p["data"] == [4.0, 7.0, 11.0]


def test_stack_without_data_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="stack need"):
        rr.build_props(_b3d([{"kind": "stack", "position": [0, 0, 0]}]), str(tmp_path))


def test_stack_layout_constants_match_between_python_and_ts():
    assert "Stack3D" in _src("remotion", "src", "three", "ThreeScene.tsx")
    assert "STACK_U = 0.5" in _src("remotion", "src", "three", "ThreeScene.tsx")
    assert "_STACK_U, _STACK_GAP, _STACK_BASE_Y = 0.5, 0.5, -1.3" in _src("scripts", "render_remotion.py"), \
        "python stack constants MUST match ThreeScene Stack3D (else totals float off the columns)"


def test_stack_emits_per_column_labels(tmp_path):
    d = _b3d([{"kind": "stack", "position": [0, 0, 0], "data": [4, 7], "labels": ["A", "B"]}])
    rr._rasterize_text3d(d, str(tmp_path))
    labels = [p for p in d["slides"][0]["planes"] if "_stk" in (p.get("src") or "")]
    assert len(labels) >= 2, "each column gets a total label"
