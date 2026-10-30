"""jitter_qa — type that trembles against its own geometry, read from the PIXELS.

A delivered product film put its UI panel inside a 3D screen and re-laid it out at the camera's size every frame;
every gate passed (the type-glide census lists type on a composited layer and never judged it) and the viewer saw
the type tremble. These tests pin the estimator against controls whose true path is known exactly, the reader on
hand-made tracks, the census hand-off, and the gate's place among the blocking delivery gates.
"""
import os
import shutil

import numpy as np
import pytest

import critic_ledger as cl
import jitter_qa as jq
import text_safe_qa as tq

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def _track(errs, true=(0.0, 0.37), start=100):
    """A line's track whose measured displacement is the true one plus `errs` (vertical)."""
    return [(start + i, true[0], true[1], true[0], true[1] + e, 50.0, None) for i, e in enumerate(errs)]


def test_a_gliding_line_is_clean_and_a_staircase_is_an_error():
    rng = np.random.default_rng(1)
    glide = _track(rng.normal(0, 0.04, 40))                      # the codec's floor on real footage
    assert jq.level_of(jq.judge_track(glide)) == "clean"
    # the staircase of a snapped baseline crawling at 0.37px a frame: holds (error -0.37), jumps (error +0.63)
    y, drawn, stair = 0.0, 0.0, []
    for _ in range(40):
        y += 0.37
        nd = float(np.floor(y))
        stair.append((nd - drawn) - 0.37)
        drawn = nd
    j = jq.judge_track(_track(stair))
    assert jq.level_of(j) == "error" and j["rms"] > 0.4


def test_one_pop_on_a_gliding_line_is_an_error_and_names_its_frame():
    errs = [0.0] * 30
    errs[17] = 0.9
    j = jq.judge_track(_track(errs, start=200))
    # judged after its local mean (DETREND_PAIRS) is taken out: a lone 0.9 keeps 8/9 of itself
    assert j["pop"] == pytest.approx(0.9 * 8 / 9) and j["pop_f"] == 217
    assert jq.level_of(j) == "error"


def test_a_still_line_that_is_redrawn_in_place_shimmers():
    rows = [(f, 0.0, 0.0, 0.0, 0.0, 50.0, 0.3) for f in range(20)]
    j = jq.judge_track(rows)
    assert j["shimmer"] == pytest.approx(0.3) and jq.level_of(j) == "error"
    calm = [(f, 0.0, 0.0, 0.0, 0.0, 50.0, 0.02) for f in range(20)]
    assert jq.level_of(jq.judge_track(calm)) == "clean"


def test_runs_are_split_where_frames_are_missing():
    rows = _track([0.0] * 5) + _track([0.0] * 5, start=110)
    assert [len(r) for r in jq._runs(rows)] == [5, 5]


def _ln(k, x, y, w=120.0, h=30.0, o=1.0, t="word", **kw):
    return dict({"k": k, "x": x, "y": y, "w": w, "h": h, "o": o, "t": t}, **kw)


def test_the_census_pairs_judge_composited_lines_and_name_every_skip():
    census = {
        0: {"lines": [_ln("/a", 100, 100, fl="c"), _ln("/fade", 100, 300, o=0.9), _ln("/fast", 400, 100),
                      _ln("/gone", 400, 300), _ln("/faint", 600, 300, o=0.2)]},
        1: {"lines": [_ln("/a", 100.3, 100.2, fl="c"), _ln("/fade", 100, 300, o=0.7), _ln("/fast", 420, 100),
                      _ln("/faint", 600, 300, o=0.2)]},
    }
    pairs, skip = jq.pairs_from_census(census, 1920, 1080)
    assert [p[0] for p in pairs[0]] == ["/a"], "a composited line is judged, not skipped"
    joined = " | ".join(skip)
    for why in ("fading", "faster than", "gone on the next frame", "fainter than"):
        assert why in joined, (why, skip)


def test_the_glide_census_hands_composited_lines_over_and_counts_them():
    frames = {0: {"lines": [_ln("/a", 1, 1, fl="c"), _ln("/b", 1, 1)]}, 1: {"lines": [_ln("/a", 1, 1, fl="c")]}}
    assert tq.composited_lines(frames) == (1, 2)
    assert "jitter_qa.py" in tq.COMPOSITED_HANDOFF


def test_jitter_qa_is_a_blocking_remotion_delivery_gate():
    gates = {g[1]: g for g in cl.DELIVERY_GATES["remotion"]}
    assert "jitter_qa.py" in gates and gates["jitter_qa.py"][4] is True


def test_an_unknown_flag_is_refused():
    with pytest.raises(SystemExit) as e:
        jq.main(["--calibratee"])
    assert e.value.code == 2


@needs_ffmpeg
def test_the_synthetic_controls_fall_on_their_sides(tmp_path):
    """The calibration the thresholds were set on: glides clean, every defect an error — x264 and the dither in."""
    rows = jq.calibrate(str(tmp_path))
    for kind in jq.CAL_KINDS:
        lv, j = rows[kind]
        want = "error" if kind in jq.CAL_BAD else "clean"
        assert lv == want, (kind, lv, j)
    # the separation, not only the sides: the worst clean control well under the line, the mildest defect well over
    clean = max(rows[k][1]["rms"] for k in jq.CAL_KINDS if k not in jq.CAL_BAD)
    assert clean < jq.JIT_RMS_ERROR * 0.6
    assert rows["snapped"][1]["rms"] > jq.JIT_RMS_ERROR * 2


def test_the_estimator_reads_a_known_sub_pixel_shift():
    from scipy.ndimage import shift as nshift
    rng = np.random.default_rng(4)
    base = np.zeros((60, 200), np.float32)
    for _ in range(30):
        y, x = rng.integers(10, 50), rng.integers(10, 190)
        base[y - 3:y + 3, x - 1:x + 1] = 220
    for dx, dy in ((0.0, 0.37), (0.25, -0.6), (-1.4, 0.1)):
        moved = nshift(base, (dy, dx), order=3, mode="nearest")
        mx, my, conf = jq.shift(base, moved)
        assert abs(mx - dx) < 0.03 and abs(my - dy) < 0.03, ((dx, dy), (mx, my))
        assert conf > jq.MIN_CONF


@needs_ffmpeg
def test_a_census_of_another_render_is_refused_not_compared(tmp_path):
    """A census of the current board against a stale out.mp4 compares every line with somebody else's frame."""
    path = str(tmp_path / "pan.mp4")
    census = jq.synth("pan", path, n=12)
    census[12] = census[11]                       # one frame more than the video has
    with pytest.raises(RuntimeError, match="not the same render"):
        jq.measure_census(path, census)
