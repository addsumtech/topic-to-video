"""Motion blur from the speed a thing is actually moving at — one runtime for every register (runtime/motionBlur).

WHY. The peer library (video-shotcraft, reviewed card by card on 2026-11-02) drives blur from per-frame speed in
about ten shots — a scroll braking to a row, a card sweeping past the lens, a dial's digits whipping round, a page
gliding with speed ghosting — and this library had three hand-drawn streak layers, each with its own constants.
A blur keyed to speed is what makes fast motion read as fast instead of as a jump, and it must be EXACTLY zero
at rest, or settled type stays soft.
"""
import math
import pytest

import _tsprobe as tp

pytestmark = pytest.mark.skipif(not tp.available(), reason="needs node + remotion/node_modules")


def _run(body):
    return tp.run_ts("import * as mb from %s;" % tp.mod("motionBlurCore.ts"), body)


def test_a_thing_at_rest_gets_no_blur_at_all():
    out = _run("out.r = mb.smear({x: 10, y: 20}, {x: 10, y: 20});"
               "out.slow = mb.smear({x: 10.4, y: 20}, {x: 10, y: 20});")
    assert out["r"] is None, "a still element must not be filtered — settled type stays crisp"
    assert out["slow"] is None, "under a pixel of smear is noise, not motion"


def test_the_smear_runs_along_the_motion_and_scales_with_the_shutter():
    out = _run("out.h = mb.smear({x: 140, y: 0}, {x: 100, y: 0});"
               "out.d = mb.smear({x: 30, y: 40}, {x: 0, y: 0}, {shutter: 1});")
    h, d = out["h"], out["d"]
    assert h["angle"] == pytest.approx(0)
    assert h["length"] == pytest.approx(20), "a 180-degree shutter smears half a frame's travel"
    assert h["sigma"] == pytest.approx(20 / math.sqrt(12), rel=1e-6), "a box of length L has sd L/sqrt(12)"
    assert d["angle"] == pytest.approx(math.degrees(math.atan2(40, 30)))
    assert d["length"] == pytest.approx(50)


def test_the_blur_is_capped_so_a_whip_never_turns_into_a_grey_bar():
    out = _run("out.w = mb.smear({x: 2000, y: 0}, {x: 0, y: 0}, {maxSigma: 18});")
    assert out["w"]["sigma"] == pytest.approx(18)


def test_ghosts_trail_behind_the_motion_and_vanish_at_rest():
    out = _run("const at = (f: number) => ({x: f * 30, y: 0});"
               "out.g = mb.ghosts(at, 10, {count: 3});"
               "const still = (f: number) => ({x: 5, y: 5});"
               "out.none = mb.ghosts(still, 10, {count: 3});")
    g = out["g"]
    assert len(g) == 3
    assert all(a["x"] < 300 for a in g), "every ghost lies BEHIND the current position"
    assert [a["opacity"] for a in g] == sorted([a["opacity"] for a in g], reverse=True), "older ghosts are fainter"
    assert out["none"] == [], "a resting element casts no ghosts"
