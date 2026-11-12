"""jitter_qa — type that trembles against its own geometry, read from the PIXELS.

A delivered product film put its UI panel inside a 3D screen and re-laid it out at the camera's size every frame;
every gate passed (the type-glide census lists type on a composited layer and never judged it) and the viewer saw
the type tremble. These tests pin the estimator against controls whose true path is known exactly, the reader on
hand-made tracks, the census hand-off, and the gate's place among the blocking delivery gates.
"""
import os
import re
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


def test_a_remotion_films_seams_are_placed_from_its_timeline_and_taken_out():
    """Validation film A: three 'shimmer' ERRORs at frame 449 were TrainSlab's notes under the 2->3 dissolve (frames
    446-457) — the beat being left stays opaque under the arriving one, so every opacity test passed. The HTML tier
    already took its scene-edge transitions out; the remotion tier now does, from the Film's own timeline."""
    scenes = [{"durF": 214}, {"durF": 256}, {"durF": 229}]
    seams = jq.seam_frames_of(scenes)
    tr = 12
    assert seams == set(range(202, 202 + tr)) | set(range(446, 446 + tr)), sorted(seams)
    census = {f: {"lines": [_ln("/note", 100, 100)]} for f in range(440, 462)}
    pairs, skip = jq.pairs_from_census(census, 1080, 1920, seams)
    assert sorted(pairs) == [440, 441, 442, 443, 444, 458, 459, 460], sorted(pairs)
    assert skip[jq.SEAM_WHY] == 13            # 445->446 through 457->458: every pair that touches a seam frame
    assert jq.pairs_from_census(census, 1080, 1920)[0].keys() == set(range(440, 461)), "no seams: every pair"


def test_a_carried_cut_owns_the_frames_its_carry_moves():
    """WorkBuddy beats 13 and 19 (2026-11-12): the carry drifts and blurs the picture from CARRY_F frames before the cut
    frame (seam start + cutFrame) to CARRY_F after — two frames past the seam each side — and a label's blurred
    centroid read as a 0.2-0.4 px tremble there. Those frames are the cut's; frames clear of them are still judged."""
    scenes = [{"durF": 214}, {"durF": 256}]
    c, cf = jq.carry_reach()
    assert (c, cf) == (6, 8)
    plain, carried = jq.seam_frames_of(scenes), jq.seam_frames_of(scenes, carry=True)
    assert carried == plain | set(range(202 + c - cf, 202 + c + cf)) == set(range(200, 216)), sorted(carried)
    assert 199 not in carried and 216 not in carried


def _glyph_windows(background_jump=0, reraster=False):
    """Two 60x44 windows of a lone digit on a light dot over a dark ground, the dot's surround either jumping by
    `background_jump` px (a lever snapping bank to bank behind a static label) or the digit itself re-rasterised."""
    from PIL import Image, ImageDraw, ImageFont
    from scipy.ndimage import zoom
    font = ImageFont.truetype(jq._font_for("4"), 64)

    def draw(shift, blur):
        im = Image.new("L", (240, 176), 20)
        d = ImageDraw.Draw(im)
        d.polygon([(0, 0), (90 + shift, 0), (60 + shift, 176), (0, 176)], fill=210)    # moving content, left
        d.ellipse([68, 36, 172, 140], fill=170)                                        # the dot
        d.text((120, 88), "4", font=font, fill=30, anchor="mm")
        a = np.asarray(im, np.float32).reshape(44, 4, 60, 4).mean(axis=(1, 3))
        if blur:
            a = zoom(zoom(a, 0.5, order=1), 2.0, order=1)[:44, :60]
        return a
    a, b = draw(0, False), draw(background_jump * 4, reraster)
    return a, b, (25, 12, 35, 32)                  # the digit's own box inside the window


def test_a_static_label_over_moving_content_does_not_shimmer_and_a_redrawn_one_does():
    """ObjectStage's numbered dots over the escapement: the window round each digit holds the lever, which jumps;
    measured on the window the digit 'shimmered' 0.19-0.45 (ERROR) while it never changed. Measured on the digit's
    own ink, isolated from what is round it, it is still — and a digit re-rasterised in place still shimmers."""
    a, b, box = _glyph_windows(background_jump=6)
    assert jq.aligned_change(a, b, 0.0, 0.0) > jq.SHIMMER_REL, "the window measure is what read it as a shimmer"
    assert jq.glyph_change(a, b, 0.0, 0.0, box) < 0.5 * jq.SHIMMER_REL
    a, b, box = _glyph_windows(reraster=True)
    assert jq.glyph_change(a, b, 0.0, 0.0, box) > jq.SHIMMER_REL
    # a box with no ink in it cannot be read alone: None, and the caller falls back to the window (said in the line)
    flat = np.full((44, 60), 20.0, np.float32)
    assert jq.glyph_change(flat, flat, 0.0, 0.0, box) is None


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


def test_a_low_texture_line_is_judged_against_a_raised_threshold_and_says_so():
    """A lone small glyph gives the estimator little to read: its noise is the threshold's business, not a finding.
    The raise is proportional — a real staircase on the same glyph is still an error."""
    rows = [(f, 0.0, 0.37, 0.0, 0.37 + (0.19 if f % 2 else -0.19), 18.0, None) for f in range(20)]
    j = jq.judge_track(rows)
    assert j["conf"] == pytest.approx(18.0) and j["rms"] > jq.JIT_RMS_ERROR
    assert jq.level_of(j) == "warn"
    assert "low texture" in jq.describe({"t": "1"}, j)
    stair = [(f, 0.0, 0.37, 0.0, 0.37 + (0.5 if f % 2 else -0.5), 18.0, None) for f in range(20)]
    assert jq.level_of(jq.judge_track(stair)) == "error"


# ── every frame shape, every script, every contrast: the controls hold, or the gate says it could not look ─────────
def test_thresholds_are_stated_at_1080_and_scale_with_the_short_side():
    assert jq.frame_scale(1920, 1080) == jq.frame_scale(1080, 1920) == jq.frame_scale(1080, 1080) == 1.0
    assert jq.frame_scale(1440, 1080) == 1.0
    assert jq.frame_scale(1280, 720) == pytest.approx(720 / 1080)
    assert jq.frame_scale(640, 360) == jq.MIN_SCALE                 # floored: the estimator's own noise is in px
    with pytest.raises(ValueError):
        jq.frame_scale(0, 1080)
    # the same 0.12 px tremble: a WARN on a 1080 frame, an ERROR on a 720 one (a larger share of the picture)
    rows = [(f, 0.0, 0.37, 0.0, 0.37 + (0.12 if f % 2 else -0.12), 50.0, None) for f in range(30)]
    assert jq.level_of(jq.judge_track(rows, 1.0)) == "warn"
    assert jq.level_of(jq.judge_track(rows, 720 / 1080)) == "error"


@needs_ffmpeg
def test_the_controls_fall_on_their_sides_in_a_portrait_frame(tmp_path):
    """E8: the controls were once drawn in a 640x360 frame and placed at fixed px (a 300 px line at x=330 leaves a
    360-wide frame). Drawn at 1080x1920 they must still split clean from defect."""
    rows = jq.calibrate(str(tmp_path), aspect="9:16")
    for kind in jq.CAL_KINDS:
        assert rows[kind][0] == ("error" if kind in jq.CAL_BAD else "clean"), (kind, rows[kind])


@needs_ffmpeg
@pytest.mark.parametrize("aspect, text", [("1:1", jq.LATIN_TEXT), ("16:9", jq.CJK_TEXT), ("4:3", jq.CJK_TEXT)])
def test_a_glide_and_a_staircase_split_at_square_and_43_and_in_cjk(tmp_path, aspect, text):
    rows = jq.calibrate(str(tmp_path), aspect=aspect, text=text, kinds=("pan", "snapped", "wobble"))
    assert rows["pan"][0] == "clean" and rows["snapped"][0] == "error" and rows["wobble"][0] == "error", rows


@needs_ffmpeg
def test_dark_type_under_the_dither_degrades_loudly_never_to_a_silent_clean(tmp_path):
    """A dithered dark film. Faint type is still read (its staircase is still an ERROR); type at the dither's own
    level is skipped as too faint — and when that is all the film has, the verdict is UNMEASURED, exit 2. Before the
    MIN_EDGE floor, a line drawn at the ground's own grey (no type at all) measured 29 pairs CLEAN: the correlation
    locked onto the static dither."""
    faint = jq.calibrate(str(tmp_path), ink=24, kinds=("pan", "snapped"))
    assert faint["snapped"][0] == "error" and faint["pan"][0] in ("clean", "warn"), faint
    path = str(tmp_path / "invisible.mp4")
    census = jq.synth("pan", path, n=30, ink=18)
    tracks, skip, meta = jq.measure_census(path, census)
    assert not tracks and any("too faint" in k for k in skip), skip
    rep = {"lines": [], "skip": skip, "universe": 29, "measured": 0, "composited": 0, "size": (1920, 1080),
           "scale": 1.0, "seconds": 0.0}
    assert jq.verdict(rep) == ("UNMEASURED", 2)


@needs_ffmpeg
def test_a_line_whose_pixels_do_not_follow_its_geometry_is_said_not_cleaned_away(tmp_path):
    """Type 4 grey levels over a dithered ground: the window half-reads the dither, which does not move, so the
    measured travel falls short of the census. The detrend would take exactly that out; it is a WARN instead."""
    path = str(tmp_path / "faint.mp4")
    census = jq.synth("pan", path, n=30, ink=22)
    tracks, _skip, meta = jq.measure_census(path, census)
    j = jq.judge_track(tracks["/line"])
    assert j.get("stall") and jq.level_of(j) == "warn"
    assert "does not follow its geometry" in jq.describe(meta["/line"], j)


def _rep(lines, universe, measured):
    return {"lines": lines, "skip": {}, "universe": universe, "measured": measured, "composited": 0,
            "size": (1080, 1920), "scale": 1.0, "seconds": 0.0, "tier": "remotion"}


def test_a_film_with_no_type_is_nothing_to_judge_and_says_so(capsys):
    import io
    buf = io.StringIO()
    assert jq.report(_rep([], 0, 0), out=buf) == 0
    assert "NOTHING TO JUDGE" in buf.getvalue() and "scope: MEASURED — 0 of 0" in buf.getvalue()


def test_a_one_second_beat_whose_lines_are_seen_for_four_pairs_is_unmeasured_not_ok():
    """A 1 s beat that fades in and out can leave a line visible for a handful of pairs: too short for the jitter
    window and the pop test alike. Tracked and judged nothing is not OK."""
    short = [(f, 0.0, 0.37, 0.0, 0.37, 50.0, None) for f in range(4)]
    j = jq.judge_track(short)
    assert j["windowed"] == 0 and j["popped"] == 0 and jq.level_of(j) == "clean"
    rep = _rep([("clean", "x", {}, j, "/a")], 4, 4)
    assert jq.verdict(rep) == ("UNMEASURED", 2)
    assert any("NOT JUDGED" in ln and "4 pair" in ln for ln in jq.scope_lines(rep))
    long_ = jq.judge_track([(f, 0.0, 0.37, 0.0, 0.37, 50.0, None) for f in range(12)])
    assert jq.verdict(_rep([("clean", "x", {}, long_, "/a")], 12, 12)) == ("OK", 0)


def test_a_missing_out_mp4_is_unmeasured_exit_2(tmp_path, capsys):
    (tmp_path / "storyboard.json").write_text('{"meta": {"renderer": "remotion"}, "slides": []}')
    assert jq.main([str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert "NOT MEASURED" in out and "out.mp4" in out and "exit 2 is not a pass" in out


def test_a_clip_with_nothing_trackable_is_not_a_pass(tmp_path, capsys):
    from PIL import Image
    d = tmp_path / "flat"
    d.mkdir()
    for i in range(12):
        Image.new("L", (640, 360), 20).save(str(d / ("f%03d.png" % i)))
    assert jq.main(["--clip", str(d)]) == 2
    assert "NOTHING was tracked" in capsys.readouterr().out


def test_every_unmeasured_path_is_reachable_and_reported():
    """The gate's three non-OK words are each reachable from its own judgment, and only an error is exit 1."""
    j_err = jq.judge_track([(f, 0.0, 0.37, 0.0, 0.37 + (0.5 if f % 2 else -0.5), 50.0, None) for f in range(20)])
    assert jq.verdict(_rep([("error", "x", {}, j_err, "/a")], 20, 20))[1] == 1
    assert jq.verdict(_rep([], 10, 0)) == ("UNMEASURED", 2)            # type found, none measured
    assert jq.verdict(_rep([], 0, 0)) == ("NOTHING TO JUDGE", 0)


@pytest.mark.skipif(not os.environ.get("GATE_RENDER"), reason="renders SlabTypeProbe: set GATE_RENDER=1")
def test_the_slab_probe_at_9x16_splits_a_per_frame_layout_from_a_surface_view(tmp_path):
    """The probe the thresholds were set on (16:9: layout 0.54-0.65 px, SurfaceView 0.05-0.08), rendered at 9:16
    through the real renderer: the same split must hold on a portrait frame."""
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rem = os.path.join(root, "remotion")
    bundle = str(tmp_path / "bundle")
    r = subprocess.run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + bundle, "--log=error"], cwd=rem,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    variants = {k: {"content": k, "move": "pan", "aspect": "9:16"} for k in ("layout", "surface")}
    for k, props in variants.items():
        pf = str(tmp_path / (k + ".json"))
        open(pf, "w").write(__import__("json").dumps(props))
        r = subprocess.run(["npx", "remotion", "render", bundle, "SlabTypeProbe", str(tmp_path / k), "--sequence",
                            "--image-format=png", "--frames=0-119", "--gl=angle", "--log=error", "--props=" + pf],
                           cwd=rem, capture_output=True, text=True, timeout=900)
        assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    res = tq.glide_run([{"tag": k, "id": "SlabTypeProbe", "props": dict(v, typeGlide=True)}
                        for k, v in variants.items()], bundle)
    worst = {}
    for k in variants:
        census = {int(f): v for f, v in res[k]["frames"].items() if int(f) < 120}
        clip = str(tmp_path / k)
        assert jq.clip_size(clip) == (1080, 1920)
        tracks, _skip, meta = jq.measure_census(clip, census)
        lines = jq.judge(tracks, meta, scale=1.0)
        assert lines, k
        worst[k] = {lv for lv, *_ in lines}
    assert worst["layout"] == {"error"} and worst["surface"] == {"clean"}, worst


def test_type_an_author_distorts_under_a_filter_is_named_and_not_judged():
    """TwoWays (the topic-to-video promo) warps its figure with an feDisplacementMap — 'a figure that will not hold' is
    the beat — and jitter_qa reported the warp as a 0.96px tremble, an ERROR on an intended picture. The census marks a
    line `d` only when the author declared `data-distort` AND the line is drawn under a spatial filter (so the claim
    is a fact of the DOM, not a way to silence a tremble): such a pair is listed under its own reason, never judged."""
    census = {0: {"lines": [_ln("/warp", 100, 100, fl="fd"), _ln("/plain", 100, 400, fl="f")]},
              1: {"lines": [_ln("/warp", 100.4, 100.3, fl="fd"), _ln("/plain", 100.4, 400.3, fl="f")]}}
    pairs, skip = jq.pairs_from_census(census, 1920, 1080)
    assert [p[0] for p in pairs[0]] == ["/plain"], "a filtered line with no declaration is still judged"
    assert any("deliberately distorted" in why for why in skip), skip
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "runtime",
                            "textSafe.tsx"), encoding="utf-8").read()
    assert re.search(r"c\.spatial && [^\n]*closest\?\.\('\[data-distort\]'\)", src), \
        "the census grants `d` only under a spatial filter"
