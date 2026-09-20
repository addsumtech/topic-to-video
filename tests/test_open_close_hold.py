"""The film opens and closes on a held picture — `tts._apply_holds`.

Measured on a delivered film: the first word arrived 0.20s into the first frame and the sign-off held 0.95s.
The peer study's R1 asks for at least a second at both ends. It could not be done while captions were timed
over the clip (a longer clip dragged the last caption late); they now follow the voice's word times, so the
hold goes into the audio — which sets each beat's length — and the first clip's word times move with it.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import tts  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def _tone(path, secs=1.5, lead=0.1, tail=0.3):
    """A clip shaped like speech: a little silence, a tone, a little silence."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=%s" % secs,
                    "-af", "adelay=%d:all=1,apad=pad_dur=%s" % (lead * 1000, tail), path], check=True)


def _board(tmp_path, n=2):
    os.makedirs(tmp_path / "audio", exist_ok=True)
    slides = []
    for i in range(1, n + 1):
        p = tmp_path / "audio" / ("%02d.mp3" % i)
        _tone(str(p))
        json.dump([{"w": "你", "t": 0.1}, {"w": "好", "t": 0.5}], open(str(p)[:-4] + ".words.json", "w"))
        slides.append({"index": i, "narration": "你好", "audio": "audio/%02d.mp3" % i,
                       "duration": tts._common.audio_duration(str(p))})
    return {"meta": {}, "slides": slides}


def test_the_first_word_waits_a_second_and_its_timings_move_with_it(tmp_path):
    d = _board(tmp_path)
    before, _ = tts._apply_holds(str(tmp_path), d)
    first = str(tmp_path / "audio" / "01.mp3")
    assert abs(tts._lead_silence(first) - tts.OPEN_HOLD_S) < 0.06, tts._lead_silence(first)
    words = json.load(open(first[:-4] + ".words.json"))
    assert abs(words[0]["t"] - (0.1 + before)) < 0.002, (words, before)
    assert abs(d["slides"][0]["duration"] - tts._common.audio_duration(first)) < 0.01


def test_the_close_holds_and_the_middle_is_untouched(tmp_path):
    d = _board(tmp_path, n=3)
    mid = str(tmp_path / "audio" / "02.mp3")
    mid_before = tts._common.audio_duration(mid)
    tts._apply_holds(str(tmp_path), d)
    last = str(tmp_path / "audio" / "03.mp3")
    assert tts._tail_silence(last) >= tts.CLOSE_HOLD_S - 0.06, tts._tail_silence(last)
    assert abs(tts._common.audio_duration(mid) - mid_before) < 0.01, "a middle beat's clip was padded"
    assert json.load(open(mid[:-4] + ".words.json"))[0]["t"] == 0.1, "a middle beat's word times moved"


def test_a_hold_already_there_is_not_added_twice_and_zero_turns_it_off(tmp_path):
    d = _board(tmp_path)
    tts._apply_holds(str(tmp_path), d)
    again = tts._apply_holds(str(tmp_path), d)
    assert again == (0.0, 0.0), again
    d2 = _board(tmp_path / "b")
    d2["meta"] = {"open_hold": 0, "close_hold": 0}
    assert tts._apply_holds(str(tmp_path / "b"), d2) == (0.0, 0.0)
