"""P2b backstops (2026-08-02 audit): motion continuity/accessibility + 3D data-viz labels.

- carry continuity: an interior carry shot glides through at constant velocity (no stop at each waypoint).
- reduced motion: hard-cut to each shot's SETTLED framing (each beat at its intended scale), not a freeze
  on the widest establish.
- RACK_FOCUS pulls focus ONTO the subject (its payoff), not to a hardcoded z.
- extruded bars emit value labels (from data) + category labels (from `labels`) as billboard text planes —
  the numbers that make a 3D bar chart READ as data-viz (the validated `labels` field used to render nothing).
"""
import json
import os

import pytest
import render_remotion as rr
import storyboard as sb

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


def _b3d(planes):
    d = sb.new_storyboard({"aspect": "16:9", "fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic3d", {}, narration="x")
    s["audio"] = "audio/01.mp3"
    s["duration"] = 4.0
    s["planes"] = planes
    d["slides"] = [s]
    return d


# ── motion source guards ─────────────────────────────────────────────────────────────────────────────
def test_carry_run_glides_through_interior_waypoints():
    src = _src("remotion", "src", "stage", "camera.ts")
    assert "flowThrough" in src and "'linear'" in src, \
        "an interior carry shot must glide through at constant velocity (no stop at each waypoint)"


def test_reduced_motion_uses_settled_framing():
    cam = _src("remotion", "src", "stage", "camera.ts")
    stage = _src("remotion", "src", "stage", "SceneStage.tsx")
    assert "reducedPoseAtFrame" in cam and "return rs.endPose" in cam, "reduced pose = each shot's settled framing"
    assert "reducedPoseAtFrame" in stage, "SceneStage must use it under reduced motion"
    assert "timeline[0].startPose" not in stage, "must NOT freeze on the widest establish"


def test_rack_focus_pulls_onto_the_subject():
    src = _src("remotion", "src", "stage", "motions.ts")
    assert "subjectZ" in src and "openingZ" in src, "rack must land focus ON the subject"
    assert "const endZ = -200" not in src, "the hardcoded rack-to-fixed-z must be gone"


# ── bar labels (behavioural — PIL is available in the test env) ──────────────────────────────────────
def test_fmt_bar_value():
    assert rr._fmt_bar_value(42) == "42"
    assert rr._fmt_bar_value(4200) == "4,200"
    assert rr._fmt_bar_value(3.5) == "3.5"


def test_bars_emit_value_and_category_label_planes(tmp_path):
    d = _b3d([{"kind": "bars", "position": [1.5, 0, 0], "data": [42, 63, 95], "labels": ["A", "B", "C"]}])
    rr._rasterize_text3d(d, str(tmp_path))
    planes = d["slides"][0]["planes"]
    assert planes[0].get("kind") == "bars", "the bars element itself is preserved"
    labels = [p for p in planes if p.get("kind") == "plane" and p.get("billboard") and p.get("alpha")]
    val = [p for p in labels if "_val.png" in p.get("src", "")]
    cat = [p for p in labels if "_cat.png" in p.get("src", "")]
    assert len(val) == 3 and len(cat) == 3, "one value label per bar + one category per provided label"
    # the PNGs were actually written, and value labels sit ABOVE the bar base (y > floor)
    assert all(os.path.isfile(os.path.join(str(tmp_path), p["src"])) for p in labels)
    assert all(p["position"][1] > rr._BAR_BASE_Y for p in val), "value labels sit above the bars"


def test_bars_without_labels_still_get_value_labels(tmp_path):
    d = _b3d([{"kind": "bars", "position": [0, 0, 0], "data": [10, 20]}])  # no `labels`
    rr._rasterize_text3d(d, str(tmp_path))
    labels = [p for p in d["slides"][0]["planes"] if "_val.png" in (p.get("src") or "")]
    assert len(labels) == 2, "value labels come from data even when no category labels are given"


def test_bar_label_planes_pass_build_props(tmp_path):
    d = _b3d([{"kind": "bars", "position": [0, 0, 0], "data": [1, 2, 3], "labels": ["a", "b", "c"]},
              {"kind": "text", "position": [0, 2, 0], "text": "Hi"}])
    rr._rasterize_text3d(d, str(tmp_path))
    props = rr.build_props(d, str(tmp_path))          # _clean_planes must accept the appended label planes
    json.dumps(props, allow_nan=False)                # and everything stays finite JSON
