"""P3/P4 backstops (2026-08-02 audit): gate/doc coherence + the small correctness nits.

P3 (traps the docs would otherwise walk an author into):
- the documented survey motions PAN/TILT/ORBIT (+ DOLLY/ZOOM) alias to a real direction (were rejected).
- shot `easing` is validated (was silently unchecked; _EASINGS was dead code).
- the move-diversity lint fires on the MOST-REPEATED (type,motion) pair, not only all-identical shots.
- validate mirrors _clean_shots' energy/targetPos checks (were only caught after a multi-minute render).
- shot_qa reports an un-measurable scene as UNSCORED (passed:None), never a silent pass.

P4 (nits): native `window` frame != browser URL bar; camera3d `pitch` phantom removed; KineticText spring
is really overshoot-clamped; ThreeScene isolated-fallback camera is a real 2-key crane.
"""
import os

import pytest
import render_remotion as rr
import storyboard as sb
import validate as v

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


def _shot_board(shots):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "audio/01.mp3"
    s["duration"] = 6.0
    s["stage"] = {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0], "title": "X"}]}
    s["shots"] = shots
    d["slides"] = [s]
    return d


def _plane_board(planes):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic3d", {}, narration="x")
    s["audio"] = "audio/01.mp3"
    s["duration"] = 4.0
    s["planes"] = planes
    d["slides"] = [s]
    return d


# ── P3: motion aliases + easing validation ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("bare,resolved", [("PAN", "PAN_RIGHT"), ("TILT", "TILT_UP"),
                                           ("ORBIT", "ORBIT_RIGHT"), ("DOLLY", "PUSH_IN")])
def test_bare_motion_names_alias(tmp_path, bare, resolved):
    sc = rr.build_props(_shot_board([{"type": "MEDIUM", "target": "a", "motion": bare}]), str(tmp_path))
    assert sc["scenes"][0]["shots"][0]["motion"] == resolved


def test_validate_accepts_bare_motion_names():
    errs, warns = [], []
    v._shot_stage_fields({"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0]}]},
                         [{"type": "MEDIUM", "target": "a", "motion": "PAN"}], "s1", errs, warns)
    assert not any("unknown motion" in e for e in errs)


def test_bad_shot_easing_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="easing"):
        rr.build_props(_shot_board([{"type": "MEDIUM", "target": "a", "easing": "bouncy"}]), str(tmp_path))


# ── P3: stronger gates ───────────────────────────────────────────────────────────────────────────────
def test_diversity_lint_fires_on_repeated_pair_not_only_all_identical():
    errs, warns = [], []
    shots = [{"type": "ESTABLISH", "target": "a"}, {"type": "ESTABLISH", "target": "a"},
             {"type": "ESTABLISH", "target": "a"}, {"type": "HERO", "target": "a", "motion": "PUSH_IN"}]
    v._shot_stage_fields({"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0]}]}, shots, "s1", errs, warns)
    assert any("same framing+motion" in w for w in warns), "3 identical shots + 1 different must still warn"


def test_validate_flags_bad_energy_and_targetpos():
    errs, warns = [], []
    stage = {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0]}]}
    v._shot_stage_fields(stage, [{"type": "HERO", "target": "a", "energy": "medium"}], "s1", errs, warns)
    v._shot_stage_fields(stage, [{"type": "HERO", "target": "a", "targetPos": [0, 0]}], "s1", errs, warns)
    assert any("energy" in e for e in errs) and any("targetPos" in e for e in errs)


def test_shot_qa_abstain_is_not_a_pass():
    src = _src("scripts", "shot_qa.py")
    assert '"passed": None' in src and '"abstained": True' in src, "an un-measurable scene must be UNSCORED"


# ── P4: nits ─────────────────────────────────────────────────────────────────────────────────────────
def test_window_frame_is_not_a_browser_url_bar():
    src = _src("remotion", "src", "stage", "elements.tsx")
    assert "isBrowser" in src and "native app window" in src, "a native window must not wear a URL pill"


def test_camera3d_has_no_phantom_pitch(tmp_path):
    sc = rr.build_props(_plane_board([{"kind": "bars", "position": [0, 0, 0], "data": [1, 2]}]), str(tmp_path))["scenes"][0]
    assert sc["camera3d"] and all("pitch" not in k for k in sc["camera3d"]), "the no-op pitch field must be gone"
    assert "pitch: number" not in _src("remotion", "src", "three", "ThreeScene.tsx")


def test_kinetictext_spring_is_overshoot_clamped():
    assert "overshootClamping: true" in _src("remotion", "src", "theme", "KineticText.tsx")


def test_threescene_fallback_camera_is_a_two_key_crane():
    src = _src("remotion", "src", "three", "ThreeScene.tsx")
    # the isolated-use fallback must move (height 6 -> 2.6), not be a single static keyframe.
    assert "height: 6}" in src and "height: 2.6}" in src
