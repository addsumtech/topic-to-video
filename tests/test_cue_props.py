"""A shot prop can be put ON a spoken word: `{"cue": "<words>"}` resolves to the register's `t` at that word.

Measured on a delivered film: CompanionCard turned its card grey at a fixed 0.40 of the clip, ~0.6s BEFORE the
voice said 「绿色的工作中」 — the frame said 等待中 under a sentence saying 工作中. The words' times are on disk
(tts.py writes audio/NN.words.json), so the board names the words and the renderer places the event.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import render_remotion as rr  # noqa: E402

NARR = "界面上只有两种状态：绿色的工作中，灰色的等待中。点一下，回到那个任务。"


def _words(tmp_path):
    os.makedirs(tmp_path / "audio", exist_ok=True)
    json.dump([{"w": "界面", "t": 1.0}, {"w": "绿色", "t": 3.0}, {"w": "灰色", "t": 6.0}, {"w": "点", "t": 8.0},
               {"w": "一下", "t": 8.2}], open(tmp_path / "audio" / "02.words.json", "w"), ensure_ascii=False)


def test_t_mirrors_useT_held_edges():
    """useT holds the first SEAM_FRAMES at ENTRY_T and runs linearly to 1 over the rest — the same numbers."""
    assert rr.t_at_seconds(0, 300, 30) == 0.06
    assert rr.t_at_seconds(10, 300, 30) == 1.0
    mid = rr.t_at_seconds(5, 300, 30)
    assert 0.5 < mid < 0.56, mid


def test_a_cue_lands_on_its_word(tmp_path):
    _words(tmp_path)
    out = rr.resolve_cue_props({"task": "x", "turnAt": {"cue": "灰色"}, "pressAt": {"cue": "点一下"}},
                               str(tmp_path), "audio/02.mp3", NARR, 10.0, 30)
    assert out["task"] == "x"
    assert out["turnAt"] == rr.t_at_seconds(6.0, 300, 30)
    assert out["pressAt"] == rr.t_at_seconds(8.0, 300, 30)
    shifted = rr.resolve_cue_props({"turnAt": {"cue": "灰色", "offset": 0.5}}, str(tmp_path), "audio/02.mp3",
                                   NARR, 10.0, 30)
    assert shifted["turnAt"] == rr.t_at_seconds(6.5, 300, 30)


def test_a_cue_the_narration_never_says_is_refused(tmp_path):
    _words(tmp_path)
    with pytest.raises(SystemExit):
        rr.resolve_cue_props({"turnAt": {"cue": "红色"}}, str(tmp_path), "audio/02.mp3", NARR, 10.0, 30)


def test_without_word_times_the_text_position_is_used(tmp_path):
    """say / MiniMax write no word times: the cue falls back to its place in the narration, never to 0."""
    out = rr.resolve_cue_props({"turnAt": {"cue": "灰色"}}, str(tmp_path), "audio/09.mp3", NARR, 10.0, 30)
    assert 0.3 < out["turnAt"] < 0.7, out


def test_the_gates_render_what_the_film_plays(tmp_path):
    """text_safe_qa / cjk_type_qa / shot_proof read a beat through film_shot_props — a raw {"cue": ...} object
    reaching a register that expects a number is a render failure the film would never have."""
    _words(tmp_path)
    slide = {"shot_props": {"turnAt": {"cue": "灰色"}}, "narration": NARR, "audio": "audio/02.mp3", "duration": 10.0}
    assert isinstance(rr.film_shot_props(slide, str(tmp_path))["turnAt"], float)
    before_tts = {"shot_props": {"turnAt": {"cue": "灰色"}}, "narration": NARR}
    assert isinstance(rr.film_shot_props(before_tts, str(tmp_path))["turnAt"], float)
    for gate in ("text_safe_qa.py", "cjk_type_qa.py", "shot_proof.py"):
        src = open(os.path.join(os.path.dirname(_HERE), "scripts", gate), encoding="utf-8").read()
        assert "film_shot_props(" in src, "%s reads shot_props raw again" % gate
