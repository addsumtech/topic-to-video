"""A beat's TIME as grammar: hit-stop on an impact, a freeze to look, held drawings that break into ones at the climax.

WHY. The peer library (video-shotcraft, reviewed 2026-11-02) cuts time itself in five shots: every hit freezes
two frames (impact-feedback), movement steps on held drawings and switches to frame-by-frame at the climax
(sakuga-timing-shift), a freeze holds a moment for a look before motion resumes (speed-ramp-freeze,
tension-camera-moves). This tier could only WARP a beat's clock (a monotone map derived for sync) or step a whole
styled film. runtime/timeGrammar maps the film frame to the frame the register draws; every pause is REPAID within
a few frames, so the clock rejoins the identity and nothing said later in the beat lands late.
"""
import pytest

import _tsprobe as tp

pytestmark = pytest.mark.skipif(not tp.available(), reason="needs node + remotion/node_modules")


def _map(spec, frames, fps=30):
    out = tp.run_ts("import * as tg from %s;" % tp.mod("timeGrammar.ts"),
                    "const spec = %s; out.f = %s.map((f: number) => tg.grammarFrame(f, spec, %d));"
                    % (spec, frames, fps))
    return out["f"]


def test_no_grammar_is_the_identity():
    assert _map("{}", "[0, 10, 57.5, 90]") == [0, 10, 57.5, 90]


def test_a_hit_freezes_for_its_hold_then_rejoins_the_clock():
    f = _map("{hits: [1], hold: 2}", "[29, 30, 31, 32, 33, 34, 35, 36, 60]")   # hit at 1 s = frame 30
    assert f[:4] == [29, 30, 30, 30], "the impact frame is held for 2 frames past its own"
    assert 30 < f[4] < 33, "after the hold the clock runs fast to repay"
    assert f[-2] == 36 and f[-1] == 60, "past the repay window the clock is the film's again"
    assert all(b >= a for a, b in zip(f, f[1:])), "time never runs backwards"


def test_a_freeze_eases_to_a_stop_holds_and_repays():
    fr = list(range(40, 140))
    f = _map("{freeze: {at: 2, hold: 1}}", str(fr))                       # at frame 60, hold 30 frames
    held = [g for g in f if abs(g - f[fr.index(75)]) < 1e-9]
    assert len(held) >= 25, "the frame is held for about the hold"
    assert all(b >= a - 1e-9 for a, b in zip(f, f[1:]))
    steps = [b - a for a, b in zip(f, f[1:])]
    assert max(steps) <= 2.0 + 1e-9, "the repay never runs the register more than twice as fast"
    assert f[-1] == 139, "the clock has rejoined the film's by the end"


def test_held_drawings_switch_to_ones_at_the_climax():
    f = _map("{sakuga: {until: 1, every: 3}}", "[0, 1, 2, 3, 4, 5, 29, 30, 31, 32]")
    assert f[:6] == [0, 0, 0, 3, 3, 3], "on threes before the climax"
    assert f[-3:] == [30, 31, 32], "on ones from it"


def test_a_malformed_spec_is_refused_not_guessed():
    out = tp.run_ts("import * as tg from %s;" % tp.mod("timeGrammar.ts"),
                    "const bad = [{hits: [1], hold: 9}, {sakuga: {until: 1, every: 5}}, {freeze: {at: 1, hold: 4}}];"
                    "out.e = bad.map((b: any) => { try { tg.checkTime(b, 'x', 6, 30); return null; }"
                    " catch (e: any) { return String(e.message); } });")
    assert all(out["e"]), out["e"]


def test_a_board_names_its_hits_by_the_words_and_the_render_turns_them_into_seconds(tmp_path):
    import json, os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
    import render_remotion as rr
    (tmp_path / "audio").mkdir()
    words = [{"w": w, "t": 0.5 + 0.5 * i}
             for i, w in enumerate("the price drops to zero today".split())]
    (tmp_path / "audio" / "01.words.json").write_text(json.dumps(words), encoding="utf-8")
    spec = {"hits": [{"cue": "zero"}, 3.1], "hold": 3, "freeze": {"at": {"cue": "today"}, "hold": 0.6},
            "sakuga": {"until": {"cue": "drops"}, "every": 2}}
    out = rr.resolve_time(spec, str(tmp_path), "audio/01.mp3", "the price drops to zero today", 6.0, 30, "#1")
    assert out["hits"][0] == pytest.approx(2.5) and out["hits"][1] == pytest.approx(3.1)
    assert out["hold"] == 3 and out["sakuga"] == {"until": pytest.approx(1.5), "every": 2}
    assert out["freeze"]["at"] == pytest.approx(3.0) and out["freeze"]["hold"] == 0.6
    with pytest.raises((SystemExit, RuntimeError)):
        rr.resolve_time({"hits": [{"cue": "tomorrow"}]}, str(tmp_path), "audio/01.mp3",
                        "the price drops to zero today", 6.0, 30, "#1")
    with pytest.raises(RuntimeError):
        rr.resolve_time({"hitz": [1]}, str(tmp_path), None, "", 6.0, 30, "#1")


def test_validate_names_a_time_the_runtime_would_refuse_before_any_render():
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
    import validate as v
    narr = "the price drops to zero today"
    ok = {"narration": narr, "time": {"hits": [{"cue": "zero"}], "hold": 2}}
    assert v.time_problems(ok) == []
    bad = [{"narration": narr, "time": {"hits": [{"cue": "zero"}], "hold": 9}},
           {"narration": narr, "time": {"hits": [{"cue": "tomorrow"}]}},
           {"narration": narr, "time": {"sakuga": {"until": 1.0, "every": 4}}},
           {"narration": narr, "time": {"freeze": {"at": 1.0, "hold": 3}}},
           {"narration": narr, "time": {"hitz": [1]}}]
    for s in bad:
        assert v.time_problems(s), s["time"]
