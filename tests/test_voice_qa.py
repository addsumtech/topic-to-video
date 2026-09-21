"""voice_qa's COVERAGE — what the narration report did NOT read.

The thresholds and the per-script routing are pinned in tests/test_rules_are_load_bearing.py, one mutation
at a time. This file pins the other half, which nothing covered: the set of beats the report is ABOUT.

Three drops used to happen in silence, and one of them changed what the headline meant:

  * a beat with an EMPTY narration was filtered out in `main` before `evaluate` ever saw it, so `metrics
    ["beats"]` — the number the headline printed — was the count of beats that HAD narration. An 8-beat
    film with one silent beat announced "7 beat(s)", which a reader takes for the film.
  * a board entry that is not an object went the same way.
  * the (A) vocabulary lists exist for two scripts. A beat in a third was scanned by NO list, and the
    report said nothing — so "no vocabulary tells" read as a result about the writing when it was a gap
    in the tool. The (B) note that covers the same gap only fired when the share collapsed to None, which
    a MIXED film prevents: seven Han beats keep `connective_share` a real number while a Cyrillic beat
    sits outside its denominator with nothing said.

voice_qa is ADVISORY and always exits 0, so every one of these is a report line, never a status.
"""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import voice_qa as vq          # noqa: E402

_ZH = "这一版把状态卡换掉了，因为原来那张卡读不出任务是在跑还是在等你。"
_EN = "The card now shows two states, and that is the whole product."
_RU = "Это кириллический такт, и у инструмента нет для него списка связок."
_TH = "นี่คือบีตภาษาไทยที่เครื่องมือนี้ตัดประโยคไม่ได้ จึงไม่เข้าเมตริกจังหวะใดเลย"


def _board(tmp_path, narrations, name="film"):
    d = tmp_path / name
    d.mkdir(parents=True)
    slides = []
    for i, t in enumerate(narrations):
        slides.append(t if not isinstance(t, str) and t is not None else {"index": i + 1, "narration": t})
    json.dump({"meta": {"language": "zh"}, "slides": slides},
              open(d / "storyboard.json", "w", encoding="utf-8"), ensure_ascii=False)
    return str(d)


@pytest.mark.parametrize("n", [3, 8])
def test_the_headline_states_coverage_derived_from_the_board(tmp_path, capsys, n):
    """M is `len(slides)`, parsed from the board — not a count of what survived the filters."""
    vq.main([_board(tmp_path, [_ZH] * n, name="f%d" % n)])
    assert "量了 %d/%d 拍" % (n, n) in capsys.readouterr().out


def test_a_silent_beat_is_counted_and_named_rather_than_dropped(tmp_path, capsys):
    out = _board(tmp_path, [_ZH, "", _ZH, _ZH, _ZH, _ZH])
    rc = vq.main([out])
    text = capsys.readouterr().out
    assert "量了 5/6 拍" in text, text
    assert "第 2 拍没有旁白" in text, text
    assert rc == 0, "voice_qa is advisory and must keep exiting 0 — the coverage is a LINE, not a status"


def test_a_malformed_entry_is_counted_and_named(tmp_path, capsys):
    out = _board(tmp_path, [_ZH, _ZH, _ZH, 12345])
    vq.main([out])
    text = capsys.readouterr().out
    assert "量了 3/4 拍" in text and "第 4 项不是一个拍子对象" in text, text


def test_a_script_with_no_vocabulary_list_is_declared_not_passed(tmp_path, capsys):
    """A mixed film kept every share a real number, so the old UNAVAILABLE note never fired and two beats
    were scanned by no vocabulary list at all with nothing said about it."""
    out = _board(tmp_path, [_ZH, _ZH, _ZH, _ZH, _EN, _RU, _TH])
    vq.main([out])
    text = capsys.readouterr().out
    assert "量了 7/7 拍" in text, text
    assert "没有词表" in text and "cyrillic" in text and "thai" in text, text
    # the (B) denominators are stated, not implied, even though neither share collapsed to None
    assert "否定对仗按 5/7 拍计" in text, text
    # and the unsegmentable beat is named by its number, not only counted
    assert "第 7 拍" in text and "thai" in text, text


def test_the_reasons_are_written_in_the_report_s_own_language(tmp_path, capsys):
    vq.main([_board(tmp_path, [_EN, "", _EN, _EN, _EN, _EN], name="en")])
    text = capsys.readouterr().out
    assert "measured 5 of 6 beat(s)" in text, text
    assert "carries no narration" in text, text


def test_the_mutation_that_hides_a_silent_beat_is_caught(tmp_path, capsys):
    """THE MUTATION. Drop the silent beat without recording it — the state before this fix. M still comes
    from the board, so the gap cannot close quietly; the report has to say a beat left with no reason."""
    src = open(vq.__file__, encoding="utf-8").read()
    old = '            dropped.append((idx, "no-narration"))\n            continue'
    assert old in src, "the mutation target has drifted out of the source"
    mod = types.ModuleType("voice_qa_mutant")
    mod.__file__ = vq.__file__
    exec(compile(src.replace(old, "            continue", 1), vq.__file__, "exec"), mod.__dict__)
    mod.main([_board(tmp_path, [_ZH, "", _ZH, _ZH, _ZH, _ZH], name="mut")])
    text = capsys.readouterr().out
    assert "量了 5/6 拍" in text, text                       # the universe did NOT shrink with the beat
    assert "第 2 拍没有旁白" not in text, "the mutant did not actually hide the beat"
    assert "没有留下任何原因" in text, text                   # …and the silence is itself reported
