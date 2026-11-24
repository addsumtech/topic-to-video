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
    "moments": [
        {"thing": "the prompt line", "from": "a typed sentence", "to": "the task's title", "why": "the sentence IS the task", "shot": "s01"},
        {"thing": "the task row", "from": "running", "to": "done, its files dealt out", "why": "done means files", "shot": "s02"},
        {"thing": "the send button", "from": "a control", "to": "the logo's mark", "why": "what you used is the brand", "shot": "s03"}],
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


def test_clever_moments_are_required_and_placed():
    err, _ = sq.evaluate(_with(moments=GOOD["moments"][:2]))
    assert any("2 clever moment(s)" in e for e in err)
    bad = copy.deepcopy(GOOD["moments"])
    bad[0]["why"] = ""
    bad[1]["shot"] = "s09"
    err, _ = sq.evaluate(_with(moments=bad))
    assert any("moment 1: no why" in e for e in err) and any("moment 2 is placed in shot 's09'" in e for e in err)


def _covered(framings=("wide", "close"), seqs=("a", "a")):
    """GOOD with s01 split into two framings of one sequence joined by a straight cut (references/shot-language.md)."""
    p = copy.deepcopy(GOOD)
    s01 = p["shots"][0]
    p["shots"][0:1] = [dict(s01, id="s01", end=2.4, seam_out="cut", framing=framings[0], sequence=seqs[0]),
                       dict(s01, id="s01b", start=2.4, hero=False, framing=framings[1], sequence=seqs[1])]
    return p


def test_a_straight_cut_inside_one_sequence_is_coverage_not_a_bare_cut():
    err, warn = sq.evaluate(_covered())
    assert err == [] and warn == [], (err, warn)


def test_a_straight_cut_between_sequences_or_unsequenced_is_still_bare():
    err, _ = sq.evaluate(_covered(seqs=("a", "b")))
    assert any("bare" in e for e in err)
    err, _ = sq.evaluate(_covered(seqs=("", "")))
    assert any("bare" in e for e in err)


def test_the_opening_arc_is_its_whole_first_sequence():
    # 2.4 s + 1.6 s of one opening sequence is a 4 s arc; an unsequenced 2.4 s opener is still too short
    err, _ = sq.evaluate(_covered())
    assert not any("at least 3 s" in e for e in err)
    p = copy.deepcopy(GOOD)
    p["shots"][0]["end"], p["shots"][1]["start"] = 2.4, 2.4
    err, _ = sq.evaluate(p)
    assert any("at least 3 s" in e for e in err)


def test_framing_is_checked_and_a_same_size_straight_cut_warns_as_a_jump_cut():
    err, _ = sq.evaluate(_covered(framings=("wide", "extreme")))
    assert any("framing" in e and "extreme" in e for e in err)
    err, warn = sq.evaluate(_covered(framings=("close", "close")))
    assert err == [] and any("jump cut" in w for w in warn)


def test_coverage_of_one_technique_at_two_framings_is_not_sameness():
    # s01 and s01b share job and technique on purpose; the framing change is what makes them two shots
    _, warn = sq.evaluate(_covered())
    assert not any("same job and technique" in w for w in warn)
