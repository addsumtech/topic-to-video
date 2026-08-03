"""Backstops for the 《终端→成稿》 primitives: a frame-driven streaming CLI (kind:"terminal") and the
`enterMotion:"materialize"` card entrance (a designed slide flying out of the terminal into 3D). Both are
pure functions of useCurrentFrame() — the terminal reveals lines by frame, the entrance eases scale/rise by
frame — so they render deterministically under Remotion's off-thread capture."""
import os
import sys

import pytest

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_SKILL, "scripts"))

import render_remotion as rr  # noqa: E402
import storyboard as sb  # noqa: E402
import validate as v  # noqa: E402


def _board(elements, shots=None):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "audio/01.mp3"; s["duration"] = 8.0
    s["stage"] = {"elements": elements}
    s["shots"] = shots or [{"type": "MEDIUM", "target": elements[0]["id"], "duration": 8.0}]
    d["slides"] = [s]
    return d


def test_terminal_lines_thread_through_build_props(tmp_path):
    el = {"id": "t", "kind": "terminal", "position": [0, 0, 0], "lineDelay": 30,
          "termTitle": "slidemaker — zsh", "lines": ["slidemaker ❯ 做一份", "❯ 访谈 ✓"]}
    sc = rr.build_props(_board([el]), str(tmp_path))["scenes"][0]
    out = sc["stage"]["elements"][0]
    assert out["kind"] == "terminal"
    assert out["lines"] == ["slidemaker ❯ 做一份", "❯ 访谈 ✓"]
    assert out["lineDelay"] == 30 and out["termTitle"] == "slidemaker — zsh"


def test_terminal_without_lines_fails_loud(tmp_path):
    el = {"id": "t", "kind": "terminal", "position": [0, 0, 0]}
    with pytest.raises(RuntimeError, match="terminal needs a non-empty"):
        rr.build_props(_board([el]), str(tmp_path))


def test_validate_flags_terminal_without_lines():
    errors, warnings = [], []
    v._shot_stage_fields({"elements": [{"id": "t", "kind": "terminal", "position": [0, 0, 0]}]},
                         [{"type": "MEDIUM", "target": "t"}], "s1", errors, warnings)
    assert any("terminal element" in e and "lines" in e for e in errors)


def test_terminal_is_a_known_kind():
    assert "terminal" in v._ELEM_KINDS


def test_lineDelay_floored_at_one(tmp_path):
    el = {"id": "t", "kind": "terminal", "position": [0, 0, 0], "lineDelay": 0, "lines": ["a"]}
    sc = rr.build_props(_board([el]), str(tmp_path))["scenes"][0]
    assert sc["stage"]["elements"][0]["lineDelay"] == 1  # 0 -> div-by-zero in the reveal; floored


def test_materialize_entrance_threads(tmp_path):
    els = [{"id": "t", "kind": "terminal", "position": [-360, 0, 0], "lines": ["❯ compose"]},
           {"id": "d", "kind": "card", "html": "pages/deck1.html", "position": [600, 0, 200],
            "size": [1180, 664], "enterMotion": "materialize", "enterAtFrame": 90}]
    sc = rr.build_props(_board(els, [{"type": "MEDIUM", "target": "t", "duration": 8.0}]), str(tmp_path))["scenes"][0]
    card = [e for e in sc["stage"]["elements"] if e["id"] == "d"][0]
    assert card["enterMotion"] == "materialize" and card["enterAtFrame"] == 90


def test_terminal_and_materialize_present_in_tsx():
    """Source backstops for the TS-only render logic (no Node in the unit suite)."""
    el = open(os.path.join(_SKILL, "remotion", "src", "stage", "elements.tsx"), encoding="utf-8").read()
    assert "kind === 'terminal'" in el, "terminal render branch lost"
    assert "enterMotion === 'materialize'" in el, "materialize entrance lost"
    assert "cursorOn" in el and "lineDelay" in el, "terminal streaming/cursor logic lost"


# ── v2: collapse-to-line, aperture bloom, crisp (dof opt-in) ───────────────────────────────────────────
def test_collapse_and_aperture_thread(tmp_path):
    els = [{"id": "t", "kind": "terminal", "position": [0, 0, 40], "lines": ["❯ x"], "collapseAtFrame": 100},
           {"id": "a", "kind": "card", "html": "pages/aurora_b1.html", "position": [0, 0, -40],
            "size": [2000, 1125], "enterMotion": "aperture", "enterAtFrame": 108}]
    sc = rr.build_props(_board(els, [{"type": "MEDIUM", "target": "t", "duration": 8.0}]), str(tmp_path))["scenes"][0]
    byid = {e["id"]: e for e in sc["stage"]["elements"]}
    assert byid["t"]["collapseAtFrame"] == 100, "terminal collapseAtFrame dropped (won't collapse-to-line)"
    assert byid["a"]["enterMotion"] == "aperture" and byid["a"]["enterAtFrame"] == 108


def test_dof_defaults_off_and_opts_in(tmp_path):
    b = _board([{"id": "p", "kind": "panel", "position": [0, 0, 0], "title": "X"}])
    sc = rr.build_props(b, str(tmp_path))["scenes"][0]
    assert sc["dof"] is False, "DoF must default OFF (crisp) — the sharp/blurry mix fix"
    b["slides"][0]["dof"] = True
    sc2 = rr.build_props(b, str(tmp_path))["scenes"][0]
    assert sc2["dof"] is True, "DoF opt-in did not thread"


def test_collapse_aperture_crisp_present_in_tsx():
    el = open(os.path.join(_SKILL, "remotion", "src", "stage", "elements.tsx"), encoding="utf-8").read()
    st = open(os.path.join(_SKILL, "remotion", "src", "stage", "SceneStage.tsx"), encoding="utf-8").read()
    assert "collapseAtFrame" in el and "hot bright filament" in el.lower() or "filament" in el, "collapse-to-line lost"
    assert "enterMotion === 'aperture'" in el and "scaleY" in el, "aperture bloom lost"
    assert "dof && focusZ" in st, "DoF must be gated on the opt-in flag (crisp by default)"
