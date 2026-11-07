"""Is out.mp4 a render of the board as it is NOW?

jitter_qa judges the delivered picture against a census it renders from the CURRENT board. Its only guard was that
the two have the same number of frames — and an edit that keeps every beat's length (a prop, a fade, a label moved)
keeps the count. On the WorkBuddy film (2026-11-07) the shots were edited, out.mp4 was not re-rendered, and the
gate reported dozens of trembles ("does not follow its geometry … another render") that were not in any frame.
The render already records each beat's cache key (.render_record.json); the board's keys now say which beats
changed since.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import remotion_segments as rs   # noqa: E402


def _rec(keys):
    return {"mode": "segments", "gl": "angle", "out": "out.mp4",
            "segments": [[i * 10, i * 10 + 9, k] for i, k in enumerate(keys)]}


def _segs(keys):
    return [{"k": i, "a": i * 10, "b": i * 10 + 9, "key": k} for i, k in enumerate(keys)]


def test_the_same_keys_mean_nothing_changed():
    assert rs.stale_beats(_rec(["a", "b", "c"]), _segs(["a", "b", "c"])) == []


def test_a_changed_key_names_that_beat():
    assert rs.stale_beats(_rec(["a", "b", "c"]), _segs(["a", "B", "c"])) == [1]


def test_a_different_number_of_beats_makes_every_beat_stale():
    assert rs.stale_beats(_rec(["a", "b"]), _segs(["a", "b", "c"])) == [0, 1, 2]


@pytest.mark.parametrize("record", [None, {}, {"mode": "whole"}, {"segments": []}, "garbage"])
def test_a_record_that_cannot_say_is_none_not_current(record):
    assert rs.stale_beats(record, _segs(["a"])) is None


def _film(tmp_path, record):
    (tmp_path / "out.mp4").write_bytes(b"\0")
    if record is not None:
        (tmp_path / rs.RECORD).write_text(json.dumps(record))
    return str(tmp_path)


def _board(monkeypatch, keys, labels=None):
    import render_remotion as rr
    import storyboard as sb
    slides = [{"index": (labels or list(range(1, len(keys) + 1)))[i]} for i in range(len(keys))]
    monkeypatch.setattr(sb, "load", lambda path: {"slides": slides, "meta": {}})
    monkeypatch.setattr(rr, "film_props", lambda out_dir, data, **kw: ({"scenes": slides}, slides))
    seen = {}

    def plan(props, public_dir, flags, **kw):
        seen["flags"] = flags
        return _segs(keys), len(keys) * 10
    monkeypatch.setattr(rs, "plan", plan)
    return seen


def test_render_currency_names_the_beats_by_their_board_index(tmp_path, monkeypatch):
    out = _film(tmp_path, _rec(["a", "b", "c"]))
    _board(monkeypatch, ["a", "b", "X"], labels=[4, 5, 6])
    state, beats, why = rs.render_currency(out)
    assert state == "stale" and beats == [6]
    assert "6" in why


def test_render_currency_is_current_when_every_key_agrees(tmp_path, monkeypatch):
    out = _film(tmp_path, _rec(["a", "b"]))
    _board(monkeypatch, ["a", "b"])
    assert rs.render_currency(out)[0] == "current"


def test_the_plan_is_asked_with_the_backend_the_film_was_drawn_on(tmp_path, monkeypatch):
    # a film that fell back to software ANGLE was keyed with those flags; asking with the default backend would call
    # every beat stale
    rec = dict(_rec(["a"]), gl="swangle")
    out = _film(tmp_path, rec)
    seen = _board(monkeypatch, ["a"])
    rs.render_currency(out)
    assert seen["flags"] == rs.pixel_flags("swangle")


def test_no_record_is_unknown_and_says_so(tmp_path, monkeypatch):
    out = _film(tmp_path, None)
    _board(monkeypatch, ["a"])
    state, beats, why = rs.render_currency(out)
    assert state == "unknown" and beats == [] and "record" in why


def test_a_record_older_than_the_video_is_unknown(tmp_path, monkeypatch):
    # out.mp4 replaced after the render that wrote the record (re-encoded, copied in): the keys describe some other file
    out = _film(tmp_path, _rec(["a"]))
    rp, vp = os.path.join(out, rs.RECORD), os.path.join(out, "out.mp4")
    os.utime(rp, (1000, 1000))
    os.utime(vp, (5000, 5000))
    _board(monkeypatch, ["a"])
    assert rs.render_currency(out)[0] == "unknown"


def test_jitter_qa_refuses_a_stale_render_before_rendering_a_census(tmp_path, monkeypatch):
    import jitter_qa as jq
    out = _film(tmp_path, _rec(["a"]))
    monkeypatch.setattr(jq, "film_tier", lambda d: "remotion")
    monkeypatch.setattr(rs, "render_currency", lambda d, v=None: ("stale", [6, 9], "beat(s) 6, 9 changed since out.mp4"))

    def no_census(d):
        raise AssertionError("the census was rendered for a picture that is not this board's")
    monkeypatch.setattr(jq, "film_census", no_census)
    with pytest.raises(RuntimeError) as e:
        jq.scan_film(out)
    assert "6" in str(e.value) and "re-render" in str(e.value)


def test_a_whole_render_records_every_beat_s_key(monkeypatch, tmp_path):
    """A film rendered in one pass (--whole, meta.segment_cache false, a model disagreement) kept no keys, so its
    currency was unknowable for good. It records the keys the board's plan gives on the backend it was drawn on."""
    import render_remotion as rr
    want = [{"k": 0, "a": 0, "b": 59, "key": "K0"}]
    monkeypatch.setattr(rs, "plan", lambda props, public_dir, flags, **kw: (want, 60))
    monkeypatch.setattr(rr.subprocess, "run", lambda cmd, cwd=None, check=True, **kw: None)
    monkeypatch.setattr(rr, "_remotion_deliverables", lambda *a, **k: None)
    monkeypatch.setattr(rr, "build_scenes", lambda slides, out_dir, valid, fps=30, **kw: [{"shot": "TermTable", "durF": 60}])
    monkeypatch.setattr(rr, "_remotion_shot_ids", lambda: {"TermTable"})
    monkeypatch.setattr(rr.shutil, "which", lambda _x: "/usr/bin/npx")
    monkeypatch.setenv("REMOTION_SYNC", "0")
    rr._render_remotion(str(tmp_path), {"meta": {"renderer": "remotion"}, "slides": [{"index": 1}]}, whole=True)
    record = json.load(open(os.path.join(str(tmp_path), rs.RECORD), encoding="utf-8"))
    assert record["mode"] == "whole"
    assert record["segments"] == [[0, 59, "K0"]]
