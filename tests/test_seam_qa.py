"""seam_qa: a cut the shot plan says is hidden must not be a bare swap in the pixels; a hard cut planned as one
(beat-cut / match / state) is what the plan said; without a plan, bare cuts are only noted."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import seam_qa  # noqa: E402


def _make(d, kind):
    a, b = d / "a.mp4", d / "b.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=2", "-vf",
                    "trim=0:1.6,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=0.4", str(a)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "smptebars=s=640x360:r=30:d=2", str(b)], check=True)
    out = d / "final.mp4"
    graph = {"bare": "[0][1]concat=n=2:v=1[v]",
             "flash": "[0][1]xfade=transition=fadewhite:duration=0.3:offset=1.85[v]",
             "push": "[0][1]xfade=transition=slideleft:duration=0.5:offset=1.75[v]",
             "dissolve": "[0][1]xfade=transition=fade:duration=0.3:offset=1.85[v]"}[kind]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a), "-i", str(b), "-filter_complex", graph, "-map", "[v]",
                    str(out)], check=True)
    (d / "_plan.json").write_text(json.dumps({"video": "final.mp4", "fps": 30, "cuts": [60]}))


def _shot_plan(d, seam):
    (d / "shot_plan.json").write_text(json.dumps({"shots": [
        {"id": "s1", "start": 0, "end": 2.0, "seam_out": seam}, {"id": "s2", "start": 2.0, "end": 4.0}]}))


@pytest.mark.parametrize("kind,bare", [("bare", True), ("flash", False), ("push", False)])
def test_measure_tells_a_bare_swap_from_a_carried_seam(tmp_path, kind, bare):
    _make(tmp_path, kind)
    cuts, planned = seam_qa.judge(str(tmp_path))
    assert not planned and cuts[0]["bare"] is bare


def test_a_bare_cut_planned_as_hidden_is_a_contradiction(tmp_path):
    _make(tmp_path, "bare")
    _shot_plan(tmp_path, "flash")
    assert seam_qa.main([str(tmp_path)]) == 1


@pytest.mark.parametrize("seam", ["beat-cut", "match", "state"])
def test_a_hard_cut_planned_as_one_passes(tmp_path, seam):
    _make(tmp_path, "bare")
    _shot_plan(tmp_path, seam)
    assert seam_qa.main([str(tmp_path)]) == 0


def test_a_hidden_seam_planned_as_hidden_passes(tmp_path):
    _make(tmp_path, "flash")
    _shot_plan(tmp_path, "flash")
    assert seam_qa.main([str(tmp_path)]) == 0


@pytest.mark.parametrize("kind,is_dissolve", [("dissolve", True), ("bare", False), ("flash", False), ("push", False)])
def test_dissolve_is_told_from_a_push_a_flash_and_a_cut(tmp_path, kind, is_dissolve):
    # a plain cross-dissolve is a blend of its two ends; a push, a flash or a hard cut is not
    _make(tmp_path, kind)
    cuts, _ = seam_qa.judge(str(tmp_path))
    assert cuts[0]["dissolve"] is is_dissolve, cuts[0]


def test_a_dissolve_passed_off_as_a_push_is_red_and_as_a_fade_passes(tmp_path):
    # Grok Bot 2026-11-18: 9-frame dissolves stood in for planned travel/push/light seams and double-exposed the cast
    _make(tmp_path, "dissolve")
    _shot_plan(tmp_path, "push")
    assert seam_qa.main([str(tmp_path)]) == 1
    _shot_plan(tmp_path, "fade")
    assert seam_qa.main([str(tmp_path)]) == 0
