"""scripts/type_clock.py: a film told in type gets a clock in the voice clock's shape — every line long enough to read,
every cut on a whole beat, the requested length met, words timed inside their line — and an over-long script is
refused with how much to cut, never squeezed. film_qc skips the voice check on it; mix.py masters music with no voice."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import film_qc  # noqa: E402
import type_clock as tc  # noqa: E402

SCRIPT = {"language": "en", "sequences": [
    {"name": "hook", "lines": [{"id": "l1", "text": "Most AI gives you a reply."}, {"id": "p1", "text": "", "show": 2.0}]},
    {"name": "proof", "lines": [{"id": "l2", "text": "WorkBuddy hands back the files."}, {"id": "p2", "text": "", "show": 3.0}]},
    {"name": "close", "lines": [{"id": "l3", "text": "WorkBuddy", "hold": 1.2}]}]}


def test_lines_fit_beats_and_length():
    tl = tc.clock(SCRIPT, 30, 120)
    beat = 0.5
    assert tl["clock"] == "type" and abs(tl["duration"] - 30) < 1e-6
    for ln in tl["lines"]:
        n = (ln["end"] - ln["start"]) / beat
        assert abs(n - round(n)) < 1e-6 and round(n) >= 2          # whole beats, at least two
        if ln["kind"] == "type":
            assert ln["end"] - ln["start"] >= tc.read_time(ln["text"], 0.6) - 1e-6 or ln["id"] == "l3"
        assert all(ln["start"] <= w["t"] < ln["end"] for w in ln["words"])
    assert tl["seams"] == [tl["lines"][2]["start"], tl["lines"][4]["start"]]
    # the spare time went to the pictures, not to the type
    import math
    for ln in tl["lines"]:
        if ln["kind"] == "type" and ln["id"] != "l3":
            need = tc.read_time(ln["text"], 0.6)
            assert abs((ln["end"] - ln["start"]) - math.ceil(need / beat) * beat) < 1e-6


def test_cjk_counts_characters():
    s = {"sequences": [{"name": "a", "lines": [{"id": "z", "text": "一句话交给它"}]}]}
    tl = tc.clock(s, 10, 120)
    assert [w["w"] for w in tl["lines"][0]["words"]] == list("一句话交给它")
    assert tc.read_time("一句话交给它", 0.6) > tc.read_time("one", 0.6)


def test_too_long_is_refused():
    s = {"sequences": [{"name": "a", "lines": [{"id": str(i), "text": "a long line of many many words to read"} for i in range(12)]}]}
    with pytest.raises(OverflowError, match="cut about"):
        tc.clock(s, 15, 120)


def test_empty_beat_is_refused():
    with pytest.raises(ValueError, match="no text and no `show`"):
        tc.clock({"sequences": [{"name": "a", "lines": [{"id": "x", "text": ""}]}]}, 10, 120)


def test_film_qc_skips_voice_on_type_clock(tmp_path):
    json.dump(tc.clock(SCRIPT, 30, 120), open(tmp_path / "timeline.json", "w"))
    names = [c[0] for c in film_qc.checks(str(tmp_path), str(tmp_path / "final.mp4"), {})]
    assert "voice" not in names
    json.dump({"lines": [], "duration": 3}, open(tmp_path / "timeline.json", "w"))
    assert "voice" in [c[0] for c in film_qc.checks(str(tmp_path), str(tmp_path / "final.mp4"), {})]


def test_mix_music_only(tmp_path):
    import subprocess
    import mix
    src = tmp_path / "score.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=220:d=3", "-ar", "48000", str(src)], check=True)
    out = tmp_path / "audio" / "mix.wav"
    out.parent.mkdir()
    rep = mix.mix(None, str(src), None, str(out))
    assert rep["voice"] is False and abs(rep["lufs"] + 14) < 1.0
    rep.update(sha1=mix._sha1(str(out)))
    json.dump(rep, open(mix.report_path(str(out)), "w"))
    (tmp_path / "audio" / "score.wav").write_bytes(src.read_bytes())
    assert mix.check(str(tmp_path)) == 0
