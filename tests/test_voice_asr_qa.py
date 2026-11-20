"""voice_asr_qa: what the recogniser heard is held against each timeline line — a dropped clause or a doubled phrase is
red, a single misheard word is a place to listen, captions off the voice are red; numbers compare as numbers."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import voice_asr_qa as v  # noqa: E402


def _line(text, start=10.0, step=0.3, lid="l1"):
    ws = [{"w": w, "t": round(start + i * step, 3)} for i, w in enumerate(text.split())]
    return {"id": lid, "text": text, "start": start, "end": ws[-1]["t"] + step, "words": ws}


def _heard(text, start=10.0, step=0.3):
    return [(w, start + i * step) for i, w in enumerate(text.split())]


def test_numbers_and_plurals_compare_as_said():
    t = lambda s: [x[0] for x in v.tokens(s, False)]  # noqa: E731
    assert t("up to a hundred and twenty decibels") == t("up to 120 decibels")
    assert t("about sixty-four million times") == t("about 64 million times")
    assert t("the maths") == t("the math") and t("up to sixty percent") == t("up to 60%")
    z = lambda s: [x[0] for x in v.tokens(s, True)]  # noqa: E731
    assert z("最多百分之六十是水") == z("最多60%是水")


def test_a_line_said_as_written_is_clean():
    ln = _line("A proton acts like a tiny bar magnet.")
    r = v.judge_line(ln, _heard("A proton acts like a tiny bar magnet."), False, {})
    assert not r["dropped"] and not r["extra"] and not r["listen"] and r["drift"] == 0.0, r


def test_a_dropped_clause_is_red_and_one_misheard_word_is_a_listen():
    ln = _line("The scanner builds a magnetic field tens of thousands of times stronger than the Earth's.")
    r = v.judge_line(ln, _heard("The scanner builds a magnetic field stronger than the Earth's."), False, {})
    assert r["dropped"] and "ten" in r["dropped"][0]["said"], r
    r = v.judge_line(ln, _heard("The scanner builds a magnetic yield tens of thousands of times stronger than the Earth's."), False, {})
    assert not r["dropped"] and r["listen"] == [{"said": "field", "heard": "yield"}], r


def test_a_doubled_phrase_is_red_but_the_neighbours_words_at_the_edges_are_not():
    ln = _line("It listens to the echo and turns it into a picture.")
    heard = _heard("It listens to the echo and turns it into turns it into a picture.", step=0.3 * 11 / 14)   # in the line's own time
    assert v.judge_line(ln, heard, False, {})["extra"]
    heard = [("before", 9.5), ("this", 9.6)] + _heard("It listens to the echo and turns it into a picture.")
    assert not v.judge_line(ln, heard, False, {})["extra"]


def test_captions_off_the_voice_are_measured():
    ln = _line("Every note goes back into its place in the slice.")
    r = v.judge_line(ln, _heard("Every note goes back into its place in the slice.", start=10.5), False, {})
    assert r["drift"] is not None and abs(r["drift"] - 0.5) < 1e-6, r


def test_a_respelt_word_is_accepted_in_its_spoken_form():
    ln = _line("Run 51job and Slurm.")
    r = v.judge_line(ln, _heard("Run 五一job and Slurm."), False, {"51job": "五一job"})
    assert not r["dropped"] and not r["listen"], r


def test_without_the_recogniser_it_says_not_measured(tmp_path, monkeypatch, capsys):
    (tmp_path / "timeline.json").write_text(json.dumps({"lines": [_line("hello there")]}))
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "voice.wav").write_bytes(b"")
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    assert v.main([str(tmp_path)]) == 2
    assert "NOT MEASURED" in capsys.readouterr().out
