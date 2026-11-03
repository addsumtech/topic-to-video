"""A hard cut on a kinetic film carries the motion THROUGH it (runtime/cutCarry) instead of joining two still frames.

WHY. Every beat is held still for SEAM_FRAMES at both ends (runtime/motion useT) so a dissolve never runs over a moving
shot — and a hard cut, which superimposes nothing, inherited the hold: the cut lands in the middle of the overlap, so
the frames either side of every cut of a promo were still (about 6 a side). The peer launch skills say the opposite
("nothing is allowed to sit still at a cut" — skillry's velocity-matched sting). The carry: the leaving beat drifts and
leans in, accelerating into the cut; the arriving beat comes out of the same drift, decelerating — the same direction
at the same speed on both sides of the cut frame, so the eye reads one move.
"""
import pytest

import _tsprobe as tp

pytestmark = pytest.mark.skipif(not tp.available(), reason="needs node + remotion/node_modules")


def _run(body):
    return tp.run_ts("import * as cc from %s;" % tp.mod("cutCarry.ts"), body)


def test_nothing_moves_outside_the_cut_windows_or_without_a_cut():
    out = _run("const W = 1920, d = 180, tr = 12;"
               "out.mid = cc.cutCarryAt(90, d, tr, true, true, W);"
               "out.none = [0, 6, 100, 170, 179].map((f) => cc.cutCarryAt(f, d, tr, false, false, W));")
    assert out["mid"] == {"x": 0, "s": 1}
    assert all(p == {"x": 0, "s": 1} for p in out["none"])


def test_the_two_sides_of_a_cut_move_the_same_way_at_the_same_speed():
    # leaving beat: visible until its frame d - tr + cut (exclusive); arriving: visible from frame cut
    out = _run("const W = 1920, d = 180, tr = 12, c = cc.cutFrame(tr);"
               "const a = (f: number) => cc.cutCarryAt(f, d, tr, false, true, W);"
               "const b = (f: number) => cc.cutCarryAt(f, d, tr, true, false, W);"
               "const lastA = d - tr + c - 1;"
               "out.vA = a(lastA).x - a(lastA - 1).x; out.vB = b(c + 1).x - b(c).x;"
               "out.sA = a(lastA).s - a(lastA - 1).s; out.sB = b(c + 1).s - b(c).s;"
               "out.endA = a(lastA); out.startB = b(c); out.settled = b(c + 30);")
    assert out["vA"] < 0 and out["vB"] < 0, "both sides drift the same way"
    assert out["vA"] == pytest.approx(out["vB"], rel=0.35), "at matching speed across the cut"
    assert out["endA"]["x"] < 0 < out["startB"]["x"], "the arriving beat comes out of the drift the leaving one went into"
    assert out["settled"] == {"x": 0, "s": 1}


def test_the_lean_always_covers_the_drift_so_no_edge_shows():
    out = _run("const W = 1920, d = 180, tr = 12; out.ok = true; out.worst = 0;"
               "for (let f = 0; f < d; f++) for (const [i, o] of [[true, false], [false, true]]) {"
               "  const p = cc.cutCarryAt(f, d, tr, i, o, W);"
               "  const room = ((p.s - 1) * W) / 2;"
               "  if (Math.abs(p.x) > room + 1e-9) { out.ok = false; }"
               "  out.worst = Math.max(out.worst, p.s); }")
    assert out["ok"], "a drift larger than the lean would show the ground's edge"
    assert out["worst"] <= 1.06 + 1e-9, "a raster is never drawn more than 6% past where it stood"


def test_a_short_beat_keeps_its_windows_apart():
    out = _run("const W = 1920, tr = 12; out.p = Array.from({length: 26}, (_, f) => cc.cutCarryAt(f, 26, tr, true, true, W));")
    assert any(p == {"x": 0, "s": 1} for p in out["p"]), "a beat with both cuts still has a still middle"


def test_the_render_turns_it_on_for_a_film_that_cuts_hard_and_only_then():
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import render_remotion as rr
    assert rr.cut_carry_on({"purpose": "promo"}) is True
    assert rr.cut_carry_on({"cuts": "scored"}) is True
    assert rr.cut_carry_on({"cuts": "calm"}) is False
    assert rr.cut_carry_on({"purpose": "promo", "cut_carry": False}) is False
    assert rr.cut_carry_on({"cuts": "calm", "cut_carry": True}) is True
