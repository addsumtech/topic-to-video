"""shot_plan_qa: the craft plan is checked before a frame is built — features mapped, each technique the hero once,
a full opening arc, a closing hold, no bare cuts, one motion voice, shots tiling the film."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import shot_plan_qa as sq  # noqa: E402

GOOD = {
    "kind": "product",
    "motion_voice": {"preset": "trusted", "main_frames": 21, "easing": "cubic-bezier(0,0,0.2,1)", "overshoot": 1.0},
    "features": ["One sentence in", "Finished files out"],
    "signature": {"idea": "the prompt line deals out the finished files", "shot": "s02"},
    "shots": [
        {"id": "s01", "start": 0, "end": 4.0, "job": "open", "technique": "spotlight-hero", "hero": True,
         "features": ["One sentence in"], "seam_out": "travel"},
        {"id": "s02", "start": 4.0, "end": 9.0, "job": "demo", "technique": "cursor-tour", "hero": True,
         "features": ["Finished files out"], "seam_out": "flash"},
        {"id": "s03", "start": 9.0, "end": 12.0, "job": "close", "technique": "ui-to-brand", "hero": True,
         "hold": 1.2, "seam_out": "end"},
    ],
}


def _with(**changes):
    p = copy.deepcopy(GOOD)
    for k, v in changes.items():
        p[k] = v
    return p


def test_a_sound_plan_passes():
    assert sq.evaluate(GOOD) == ([], [])


def test_an_unmapped_feature_is_a_hole():
    err, _ = sq.evaluate(_with(features=GOOD["features"] + ["Runs on a schedule"]))
    assert any("Runs on a schedule" in e for e in err)


def test_a_technique_is_the_hero_once():
    p = copy.deepcopy(GOOD)
    p["shots"][1]["technique"] = "spotlight-hero"
    err, _ = sq.evaluate(p)
    assert any("each technique is the star once" in e for e in err)


def test_short_opening_and_missing_closing_hold():
    p = copy.deepcopy(GOOD)
    p["shots"][0]["end"] = 2.0
    p["shots"][1]["start"] = 2.0
    p["shots"][2]["hold"] = 0.4
    err, _ = sq.evaluate(p)
    assert any("at least 3 s" in e for e in err) and any("at least 1 s" in e for e in err)


def test_bare_cut_and_unknown_seam():
    p = copy.deepcopy(GOOD)
    p["shots"][0]["seam_out"] = "cut"
    p["shots"][1]["seam_out"] = "dissolve-ish"
    err, _ = sq.evaluate(p)
    assert any("bare" in e for e in err) and any("dissolve-ish" in e for e in err)


def test_gaps_and_overlaps_and_no_voice():
    p = copy.deepcopy(GOOD)
    p["shots"][1]["start"] = 4.5
    p["motion_voice"] = {}
    err, _ = sq.evaluate(p)
    assert any("no gap or overlap" in e for e in err) and any("motion voice" in e for e in err)


def test_explainers_need_no_feature_list_and_sameness_warns():
    p = copy.deepcopy(GOOD)
    p["kind"], p["features"] = "explainer", []
    p["shots"][1]["job"], p["shots"][1]["technique"] = "open", "spotlight-hero"
    p["shots"][1]["hero"] = False
    err, warn = sq.evaluate(p)
    assert err == [] and any("same job and technique" in w for w in warn)


def test_a_film_needs_its_own_signature_idea():
    err, _ = sq.evaluate(_with(signature={}))
    assert any("signature idea" in e for e in err)
    err, _ = sq.evaluate(_with(signature={"idea": "x", "shot": "s99"}))
    assert any("s99" in e for e in err)


def test_cli(tmp_path):
    (tmp_path / "shot_plan.json").write_text(json.dumps(GOOD))
    assert sq.main([str(tmp_path)]) == 0
    assert sq.main([str(tmp_path / "missing")]) == 2
