"""Backstops for the Phase-2 cinematic COMPONENTS (frame-driven, generalisable): spotlight (travelling
light-pool), hud (FUI reticle + corner readout), connector (draw-on line/arrow). Each is a pure function of
the frame; these guard that the fields thread through build_props and that the TS render branches survive."""
import os
import sys

import pytest

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_SKILL, "scripts"))
import render_remotion as rr  # noqa: E402
import storyboard as sb  # noqa: E402
import validate as v  # noqa: E402


def _board(elements):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "audio/01.mp3"; s["duration"] = 6.0
    s["stage"] = {"elements": elements}
    s["shots"] = [{"type": "MEDIUM", "target": elements[0]["id"], "duration": 6.0}]
    d["slides"] = [s]
    return d


def test_new_kinds_are_known():
    for k in ("spotlight", "hud", "connector"):
        assert k in v._ELEM_KINDS


def test_spotlight_fields_thread(tmp_path):
    el = {"id": "s", "kind": "spotlight", "position": [0, 0, 0], "sweep": [-0.5, 0.5], "sweepSpan": 120, "hue": "#37E0FF"}
    out = rr.build_props(_board([el]), str(tmp_path))["scenes"][0]["stage"]["elements"][0]
    assert out["sweep"] == [-0.5, 0.5] and out["sweepSpan"] == 120 and out["hue"] == "#37E0FF"


def test_hud_fields_thread(tmp_path):
    el = {"id": "h", "kind": "hud", "position": [0, 0, 0], "hudLabel": "SYS", "hudStatus": "locked", "lockAtFrame": 70}
    out = rr.build_props(_board([el]), str(tmp_path))["scenes"][0]["stage"]["elements"][0]
    assert out["hudLabel"] == "SYS" and out["hudStatus"] == "locked" and out["lockAtFrame"] == 70


def test_connector_fields_thread(tmp_path):
    el = {"id": "c", "kind": "connector", "position": [0, 0, 0], "to": [560, 0], "arrow": True,
          "strokeColor": "#ffb020", "drawAtFrame": 40}
    out = rr.build_props(_board([el]), str(tmp_path))["scenes"][0]["stage"]["elements"][0]
    assert out["to"] == [560, 0] and out["arrow"] is True and out["strokeColor"] == "#ffb020" and out["drawAtFrame"] == 40


def test_bad_tuple_fails_loud(tmp_path):
    el = {"id": "s", "kind": "spotlight", "position": [0, 0, 0], "sweep": [0.5]}  # must be [a,b]
    with pytest.raises(RuntimeError, match="must be"):
        rr.build_props(_board([el]), str(tmp_path))


def test_component_branches_present_in_tsx():
    el = open(os.path.join(_SKILL, "remotion", "src", "stage", "elements.tsx"), encoding="utf-8").read()
    assert "kind === 'spotlight'" in el and "kind === 'hud'" in el and "kind === 'connector'" in el
    assert "strokeDashoffset" in el, "connector draw-on lost"
    assert "mixBlendMode" in el, "spotlight light-pool lost"
