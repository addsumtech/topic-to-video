"""P2 backstop — the shot-based staging schema in build_props.

A cinematic scene may carry a `stage` (elements placed once) + an ordered `shots` list (framings the
camera moves between over ONE set — the shot paradigm, replacing the old singular per-scene move).
These lock the contract SceneStage relies on: shot windows tile the scene EXACTLY (so audio/caption
sync can't be broken by authored shot durations), targets must be real staged ids, and every malformed
shape fails loud (never reaches Remotion as garbage)."""
import pytest
import render_remotion as rr
import storyboard as sb


def _board(shots, elements=None, dur=12.0):
    d = sb.new_storyboard({"aspect": "16:9", "fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "audio/01.mp3"; s["duration"] = dur
    s["stage"] = {"perspective": 1300, "elements": elements or [
        {"id": "grid", "kind": "grid", "position": [0, 0, -1200]},
        {"id": "gateway", "kind": "panel", "position": [0, -40, 120], "title": "API Gateway"},
        {"id": "db", "kind": "hero", "position": [1200, 0, -400], "heroText": "PRIMARY"}]}
    s["shots"] = shots
    d["slides"] = [s]
    return d


def test_shot_windows_tile_scene_exactly(tmp_path):
    d = _board([{"type": "ESTABLISH", "duration": 3.0, "target": "grid"},
                {"type": "MEDIUM", "duration": 4.0, "target": "gateway", "carry": True},
                {"type": "HERO", "duration": 5.0, "target": "db"}])  # 3+4+5 = 12s @30 = 360f
    sh = rr.build_props(d, str(tmp_path))["scenes"][0]["shots"]
    assert [(x["startFrame"], x["durationFrames"]) for x in sh] == [(0, 90), (90, 120), (210, 150)]
    assert sh[-1]["startFrame"] + sh[-1]["durationFrames"] == 360  # covers the whole scene
    assert sh[1]["carry"] is True


def test_shot_windows_sum_when_durations_absent(tmp_path):
    d = _board([{"type": "ESTABLISH", "target": "grid"}, {"type": "HERO", "target": "db"}], dur=10.0)
    sh = rr.build_props(d, str(tmp_path))["scenes"][0]["shots"]
    assert sh[-1]["startFrame"] + sh[-1]["durationFrames"] == 300  # still tiles 10s exactly


def test_stage_and_shots_threaded_not_legacy(tmp_path):
    sc = rr.build_props(_board([{"type": "HERO", "target": "db"}]), str(tmp_path))["scenes"][0]
    assert sc["stage"] and len(sc["stage"]["elements"]) == 3
    assert sc["shots"] and sc["camera"] is None and sc["lens"] is None and sc["layers"] is None


def test_shot_based_scene_not_unsupported(tmp_path):
    d = _board([{"type": "MEDIUM", "target": "gateway"}])
    assert rr.unsupported_scenes(d) == []  # stage+shots renders without an image


def test_legacy_singular_shot_wrapped(tmp_path):
    """Back-compat: a legacy singular `shot` object is accepted as a one-shot list."""
    d = _board([{"type": "HERO", "target": "db"}])
    d["slides"][0]["shot"] = d["slides"][0].pop("shots")[0]
    sh = rr.build_props(d, str(tmp_path))["scenes"][0]["shots"]
    assert len(sh) == 1 and sh[0]["type"] == "HERO"


def test_motion_normalized_and_validated(tmp_path):
    sc = rr.build_props(_board([{"type": "MEDIUM", "target": "gateway", "motion": "push-in"}]), str(tmp_path))
    assert sc["scenes"][0]["shots"][0]["motion"] == "PUSH_IN"  # normalized
    with pytest.raises(RuntimeError, match="unknown motion"):
        rr.build_props(_board([{"type": "MEDIUM", "target": "gateway", "motion": "wiggle"}]), str(tmp_path))


def test_unknown_target_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="not a staged element id"):
        rr.build_props(_board([{"type": "HERO", "target": "ghost"}]), str(tmp_path))


def test_unknown_shot_type_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="unknown type"):
        rr.build_props(_board([{"type": "ZOOMZOOM", "target": "db"}]), str(tmp_path))


def test_duplicate_element_id_fails_loud(tmp_path):
    els = [{"id": "a", "kind": "grid", "position": [0, 0, -1]},
           {"id": "a", "kind": "hero", "position": [0, 0, 0], "heroText": "x"}]
    with pytest.raises(RuntimeError, match="duplicate element id"):
        rr.build_props(_board([{"type": "HERO", "target": "a"}], elements=els), str(tmp_path))


@pytest.mark.parametrize("bad_pos", [[0, float("nan"), -1], [0, "x", -1], [0, 0]])
def test_bad_element_position_fails_loud(tmp_path, bad_pos):
    els = [{"id": "a", "kind": "hero", "position": bad_pos, "heroText": "x"}]
    with pytest.raises(RuntimeError):
        rr.build_props(_board([{"type": "HERO", "target": "a"}], elements=els), str(tmp_path))


def test_empty_stage_elements_fails_loud(tmp_path):
    d = _board([{"type": "HERO", "target": "a"}])
    d["slides"][0]["stage"] = {"elements": []}  # set directly (the helper's `elements or …` hides [])
    with pytest.raises(RuntimeError, match="non-empty list"):
        rr.build_props(d, str(tmp_path))


def test_legacy_layers_still_work(tmp_path):
    """Legacy layers+lens scenes (no stage/shots) render unchanged."""
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion"})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "audio/01.mp3"; s["duration"] = 2.0
    s["layers"] = [{"kind": "fill"}, {"kind": "panel", "title": "Legacy", "z": -500}]
    s["lens"] = [{"atFrame": 0, "dolly": 0}, {"atFrame": 60, "dolly": 150, "easing": "out"}]
    d["slides"] = [s]
    sc = rr.build_props(d, str(tmp_path))["scenes"][0]
    assert sc["layers"] and sc["lens"] and sc["stage"] is None and sc["shots"] is None


def test_shot_props_are_json_finite(tmp_path):
    import json
    p = rr.build_props(_board([{"type": "MEDIUM", "target": "gateway", "motion": "PUSH_IN"}]), str(tmp_path))
    json.dumps(p, allow_nan=False)  # no NaN/Inf survived into the props


# ── validate.py pre-render gate (the ~1s catch before a multi-minute render) ──────────────────────
def _vgate(stage, shots):
    import validate as v
    errs, warns = [], []
    v._shot_stage_fields(stage, shots, "scene 1", errs, warns)
    return errs


_GOOD_STAGE = {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 120], "title": "X"},
                            {"id": "b", "kind": "hero", "position": [1000, 0, -400], "heroText": "Y"}]}


def test_validate_gate_warns_unknown_element_kind():
    import validate as v
    errs, warns = [], []
    stage = {"elements": [{"id": "a", "kind": "widget", "position": [0, 0, 0]}]}
    v._shot_stage_fields(stage, [{"type": "HERO", "target": "a"}], "scene 1", errs, warns)
    assert any("unknown" in w and "kind" in w for w in warns)  # unknown kind -> warn (renders as panel)


def test_validate_gate_passes_valid_shot_scene():
    assert _vgate(_GOOD_STAGE, [{"type": "ESTABLISH", "target": "a"},
                                {"type": "HERO", "target": "b", "motion": "PUSH_IN", "carry": True}]) == []


@pytest.mark.parametrize("stage,shots,needle", [
    (_GOOD_STAGE, [{"type": "HERO", "target": "ghost"}], "not a staged element id"),
    (_GOOD_STAGE, [{"type": "ZOOM", "target": "a"}], "unknown type"),
    (_GOOD_STAGE, [{"type": "HERO", "target": "a", "motion": "wiggle"}], "unknown motion"),
    ({"elements": [{"id": "a", "kind": "hero", "position": [0, float("nan"), 0]}]}, [{"type": "HERO", "target": "a"}], "NaN/Infinity"),
    ({"elements": []}, [{"type": "HERO"}], "non-empty list"),
])
def test_validate_gate_flags_bad_shot_scene(stage, shots, needle):
    assert any(needle in e for e in _vgate(stage, shots))
