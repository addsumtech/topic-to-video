"""The zoom follows the action (spec 2026-11-06 E3). Screen-recording tools that make launch videos read well follow
the clicks with the close-up and smooth the path; a FilmScreen close-up was one fixed region. `focusTrack` moves the
region's centre along the action, at the region's own magnification — so the picture is never drawn past its pixels —
and refuses a track it would have to whip across the frame to follow."""
import os
import re

import pytest

import _tsprobe as tp

pytestmark = pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")
IMP = "import {focusAt, checkFocusTrack, MAX_STEP} from %s;" % tp.mod("focusTrack.ts")
REGION = "{x: 0.1, y: 0.1, w: 0.4}"


def test_the_close_up_follows_the_track_and_holds_at_its_ends():
    o = tp.run_ts(IMP, """const tr = [{t: 0, x: 0.3, y: 0.3}, {t: 2, x: 0.6, y: 0.4}];
out.a = focusAt(tr, -1, %s, 9/16); out.b = focusAt(tr, 0, %s, 9/16); out.c = focusAt(tr, 2, %s, 9/16);
out.d = focusAt(tr, 9, %s, 9/16); out.m = focusAt(tr, 1, %s, 9/16);""" % ((REGION,) * 5))
    assert o["a"] == o["b"] and o["c"] == o["d"]
    assert abs(o["b"]["x"] - (0.3 - 0.2)) < 1e-9                      # the region's centre on the key
    assert o["b"]["x"] < o["m"]["x"] < o["c"]["x"]


def test_the_region_never_leaves_the_picture():
    o = tp.run_ts(IMP, "out.p = focusAt([{t: 0, x: 0.98, y: 0.99}], 0, %s, 9/16);" % REGION)["p"]
    assert o["x"] + 0.4 <= 1 + 1e-9 and o["x"] >= 0 and o["y"] >= 0


def test_no_frame_steps_more_than_the_limit():
    o = tp.run_ts(IMP, """const tr = [{t: 0, x: 0.25, y: 0.3}, {t: 1.5, x: 0.7, y: 0.5}, {t: 3, x: 0.3, y: 0.4}];
checkFocusTrack(tr, %s, 30);
const ps = Array.from({length: 91}, (_, i) => focusAt(tr, i / 30, %s, 9/16));
out.max = Math.max(...ps.slice(1).map((p, i) => Math.hypot(p.x - ps[i].x, p.y - ps[i].y))); out.lim = MAX_STEP;""" % (REGION, REGION))
    assert o["max"] <= o["lim"] + 1e-9


def test_a_track_too_fast_to_follow_or_malformed_is_refused():
    with pytest.raises(AssertionError, match="too fast"):
        tp.run_ts(IMP, "checkFocusTrack([{t: 0, x: 0.2, y: 0.2}, {t: 0.2, x: 0.8, y: 0.8}], %s, 30);" % REGION)
    with pytest.raises(AssertionError, match="focusTrack"):
        tp.run_ts(IMP, "checkFocusTrack([{t: 1, x: 0.2, y: 0.2}, {t: 0.5, x: 0.3, y: 0.3}], %s, 30);" % REGION)
    with pytest.raises(AssertionError, match="focusTrack"):
        tp.run_ts(IMP, "checkFocusTrack([{t: 0, x: 2, y: 0.2}], %s, 30);" % REGION)


def test_filmscreen_reads_the_track_and_needs_a_region():
    src = open(os.path.join(os.path.dirname(tp.RUNTIME), "shots", "FilmScreen.tsx"), encoding="utf-8").read()
    assert "focusTrack" in src and re.search(r"checkFocusTrack\(", src) and re.search(r"focusAt\(", src)
    assert "a focus track moves a close-up" in src
