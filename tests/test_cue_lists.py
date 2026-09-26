"""Cues inside a list resolve in ORDER — a script's steps, a chat thread's messages.

`resolve_cue_props` used to resolve only top-level props, each searched from the start of the narration. A
list of timed items needs one ordered search: a phrase said twice must land on two successive items, and a
cue the narration reaches only before the previous item's is an error, not a silent swap.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import render_remotion as rr        # noqa: E402

FPS = 30


def _resolve(props, narration, tmp_path, words=None, dur=6.0):
    (tmp_path / "audio").mkdir(exist_ok=True)
    if words is not None:
        (tmp_path / "audio" / "01.words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    return rr.resolve_cue_props(props, str(tmp_path), "audio/01.mp3", narration, dur, FPS)


def test_items_resolve_in_the_order_the_voice_says_them(tmp_path):
    props = {"steps": [{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5], "at": {"cue": "搜索"}},
                       {"tap": [0.5, 0.6], "at": {"cue": "点开"}}]}
    out = _resolve(props, "先在上面搜索上周的反馈，然后点开第一条。", tmp_path)
    a, b = out["steps"][1]["at"], out["steps"][2]["at"]
    assert isinstance(a, float) and isinstance(b, float) and a < b
    assert "at" not in out["steps"][0]


def test_a_repeated_phrase_lands_on_successive_items(tmp_path):
    words = [{"w": w, "t": t} for w, t in [("点", 0.4), ("这里", 0.6), ("然后", 1.4), ("再", 2.0), ("点", 2.6),
                                            ("这里", 2.8)]]
    props = {"steps": [{"screen": {"image": "a.png"}}, {"tap": [0.2, 0.2], "at": {"cue": "点这里"}},
                       {"tap": [0.8, 0.8], "at": {"cue": "点这里"}}]}
    out = _resolve(props, "点这里，然后再点这里。", tmp_path, words=words)
    a, b = out["steps"][1]["at"], out["steps"][2]["at"]
    assert b > a + 0.2, "both items bound to the first 点这里: %r %r" % (a, b)


def test_a_cue_said_only_before_the_previous_one_is_an_error(tmp_path):
    props = {"steps": [{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5], "at": {"cue": "点开"}},
                       {"tap": [0.5, 0.6], "at": {"cue": "搜索"}}]}
    with pytest.raises(SystemExit) as e:
        _resolve(props, "先搜索，再点开。", tmp_path)
    assert "steps[2].at" in str(e.value) and "BEFORE" in str(e.value)


def test_a_cue_the_narration_never_says_names_the_item(tmp_path):
    props = {"messages": [{"side": "you", "text": "hi", "at": {"cue": "不存在的话"}}]}
    with pytest.raises(SystemExit) as e:
        _resolve(props, "这里什么都没说。", tmp_path)
    assert "messages[0].at" in str(e.value)


def test_top_level_cues_are_unchanged(tmp_path):
    out = _resolve({"turnAt": {"cue": "工作中"}}, "它现在是绿色的工作中状态。", tmp_path)
    assert isinstance(out["turnAt"], float)
