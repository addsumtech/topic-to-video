"""Materialized-metaphor backstops (#4): a stage element kind:'metaphor' whose `concept` verb encodes the
beat's MEANING as a frame-driven physical action (fill rises = adoption, token falls = the cliff, gap opens
= the loss). Verified from renders; here we lock the fail-loud coercion, the gate, determinism, and the
lining-figures rule for the numbers the verbs print."""
import os

import pytest
import render_remotion as rr
import storyboard as sb
import validate as v

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


def test_metaphor_threads_concept_and_values(tmp_path):
    sc = rr.build_props(_mb({"kind": "metaphor", "concept": "filling-vessel", "values": [87], "unit": "%"}), str(tmp_path))["scenes"][0]
    m = [e for e in sc["stage"]["elements"] if e["id"] == "m"][0]
    assert m["concept"] == "filling-vessel" and m["values"] == [87.0] and m["unit"] == "%"


def test_unknown_concept_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="concept"):
        rr.build_props(_mb({"kind": "metaphor", "concept": "boom", "values": [1]}), str(tmp_path))


def test_wrong_arity_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="needs exactly 2"):
        rr.build_props(_mb({"kind": "metaphor", "concept": "widening-gap", "values": [1]}), str(tmp_path))


def test_empty_values_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="non-empty"):
        rr.build_props(_mb({"kind": "metaphor", "concept": "filling-vessel", "values": []}), str(tmp_path))


def test_nan_value_fails_loud(tmp_path):
    with pytest.raises(RuntimeError):
        rr.build_props(_mb({"kind": "metaphor", "concept": "filling-vessel", "values": [float("nan")]}), str(tmp_path))


def test_verbs_present_and_deterministic():
    src = _src("remotion", "src", "stage", "elements.tsx")
    for c in ("filling-vessel", "widening-gap", "physical-fall"):
        assert ("'" + c + "'") in src, "verb %s must be implemented" % c
    assert "easeGravity" in src and "counted(" in src, "gravity fall + counted number helpers"
    assert "Math.random" not in src and "Date.now(" not in src, "metaphor verbs must be pure fns of frame"


def test_metaphor_numbers_use_the_lining_face():
    src = _src("remotion", "src", "stage", "elements.tsx")
    assert src.count("lining-nums tabular-nums") >= 3, "every metaphor number must use the lining number face"


def test_validate_metaphor_gate():
    errs, warns = [], []
    stage = {"elements": [{"id": "m", "kind": "metaphor", "concept": "physical-fall", "values": [1], "position": [0, 0, 0]}]}
    v._shot_stage_fields(stage, [{"type": "HERO", "target": "m"}], "s1", errs, warns)
    assert any("needs 2 values" in e for e in errs)


def test_catalog_documents_native_verbs():
    doc = _src("references", "shot-archetypes.md")
    for c in ("filling-vessel", "widening-gap", "physical-fall"):
        assert c in doc, "the archetype catalogue must name the native verb %s" % c
