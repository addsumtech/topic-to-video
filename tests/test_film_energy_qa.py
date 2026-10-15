"""The film-energy INSTRUMENT, proved against rendered video rather than a synthesised measurement.

tests/test_rules_are_load_bearing.py proves the three FLOORS are load-bearing by handing `check()` a
measurement dict. That leaves the half that actually touches pixels unproven: whether `measure()` can
tell a slideshow from a film at all. A gate whose thresholds are perfect and whose instrument reads the
same number for both is exactly as useless as no gate, and it looks healthier.

So these render two videos with ffmpeg and measure them for real. They are deliberately at opposite
extremes — a held frame with one static block, and a full-frame moving pattern under a brightness ramp —
because the claim being tested is separation, not calibration. Calibration comes from the four reference
films recorded in scripts/film_energy_qa.py.
"""
import json
import os
import shutil
import subprocess

import pytest

import film_energy_qa as g

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None or g.measure.__module__ is None,
                                reason="needs ffmpeg")


def _render(path, filters):
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + filters + ["-pix_fmt", "yuv420p", path], check=True)


@pytest.fixture(scope="module")
def slideshow(tmp_path_factory):
    """A held dark frame with one small static block — the shape of the film that prompted this gate."""
    d = tmp_path_factory.mktemp("slideshow")
    _render(str(d / "out.mp4"), [
        "-f", "lavfi", "-i", "color=c=0x0a0f16:s=320x180:r=24:d=6",
        "-f", "lavfi", "-i", "color=c=0x4f8cff:s=60x24:r=24:d=6",
        "-filter_complex", "[0][1]overlay=x=40:y=40,fade=t=in:st=0:d=0.5"])
    return str(d)


@pytest.fixture(scope="module")
def alive(tmp_path_factory):
    """Full-frame motion under a dark-to-bright ramp: movement, density and light all present."""
    d = tmp_path_factory.mktemp("alive")
    _render(str(d / "out.mp4"), [
        "-f", "lavfi", "-i", "testsrc2=s=320x180:r=24:d=6",
        "-vf", "eq=brightness='-0.35+0.7*t/6':eval=frame"])
    return str(d)


def test_the_instrument_separates_a_slideshow_from_a_film(slideshow, alive):
    a, b = g.measure(os.path.join(slideshow, "out.mp4")), g.measure(os.path.join(alive, "out.mp4"))
    assert a is not None and b is not None
    # Separation on all three axes independently — a gate that only works because one axis happens to
    # correlate with the others would pass a film that fixed the easy axis and nothing else.
    assert b["motion_p75"] > a["motion_p75"] * 10
    assert b["luma_range"] > a["luma_range"] * 10
    # density moved to its own decode at its own resolution (see DENSITY_LONG_SIDE), so it is asked of
    # `density()` rather than `measure()` — but it is still asked, because "the instrument can tell these
    # apart on every axis independently" is the claim, not "on the axes that happen to share a decode".
    da = g.density(os.path.join(slideshow, "out.mp4"))
    db = g.density(os.path.join(alive, "out.mp4"))
    assert da and db, (da, db)
    assert db["median"] > da["median"] * 10, (da["median"], db["median"])


def test_a_rendered_slideshow_fails_the_gate(slideshow):
    errs, warns, m = g.check(slideshow)
    assert m["motion_p75"] < g.MOTION_P75_FLOOR
    blob = " ".join(errs)
    # DENSITY is deliberately absent from this list now: its floor retired with the metric that could not
    # tell a drawn frame from a blurred blank one, and it reports per beat instead of gating. The axes that
    # still have defensible floors still gate, and that is what this asserts.
    assert "MOTION" in blob and "LIGHT" in blob
    assert not any(e.startswith("DENSITY") for e in errs), errs
    assert any("DENSITY (measured, not gated)" in w for w in warns), warns


def test_a_rendered_film_clears_every_floor(alive):
    errs, _warns, m = g.check(alive)
    assert not errs, "a moving, dense, lit film failed the floors: %r (%r)" % (errs, m)


def test_a_written_waiver_accepts_the_slideshow_and_keeps_the_numbers(slideshow):
    board = {"meta": {"energy_waiver": "one held frame is the point of this piece"}}
    json.dump(board, open(os.path.join(slideshow, "storyboard.json"), "w", encoding="utf-8"))
    try:
        errs, warns, _m = g.check(slideshow)
        assert not errs
        assert any("MOTION" in w for w in warns), "a waiver must not hide what was waived"
    finally:
        os.remove(os.path.join(slideshow, "storyboard.json"))


def test_a_waiver_named_for_one_axis_does_not_absolve_the_others(slideshow):
    """The hole this closes shipped within a day of the waiver being used: a paragraph reasoning about
    DENSITY — a deck's warm-white design language — silently excused a MOTION failure that appeared later
    from an unrelated change (the camera bed going opt-in). One stated reason must not absolve the axes
    nobody reasoned about."""
    # The axis pair moved from DENSITY/MOTION to LIGHT/MOTION when the density floor retired — the claim
    # is about one named axis not absolving an unnamed one, and it needs two axes that still GATE.
    board = {"meta": {"energy_waiver": {"light": "this piece is deliberately one unlit tone"}}}
    json.dump(board, open(os.path.join(slideshow, "storyboard.json"), "w", encoding="utf-8"))
    try:
        errs, warns, _m = g.check(slideshow)
        assert any(e.startswith("MOTION") for e in errs), "motion was never reasoned about; it stays gated"
        assert any("waived (LIGHT)" in w for w in warns), "the named axis IS waived, and says so"
        assert not any(e.startswith("LIGHT:") for e in errs)
    finally:
        os.remove(os.path.join(slideshow, "storyboard.json"))


def test_a_plain_string_waiver_still_covers_every_axis_and_says_so(slideshow):
    """Existing boards mean 'all of it' by a string, so that behaviour is kept — but it now announces the
    breadth instead of leaving a reader to assume it was per-axis."""
    board = {"meta": {"energy_waiver": "one held frame is the point of this piece"}}
    json.dump(board, open(os.path.join(slideshow, "storyboard.json"), "w", encoding="utf-8"))
    try:
        errs, warns, _m = g.check(slideshow)
        assert not errs
        assert any("waived (MOTION)" in w for w in warns), "a waiver must name what it waived"
    finally:
        os.remove(os.path.join(slideshow, "storyboard.json"))


def test_an_unnamed_axis_is_told_how_to_be_waived_narrowly(slideshow):
    json.dump({"meta": {}}, open(os.path.join(slideshow, "storyboard.json"), "w", encoding="utf-8"))
    try:
        errs, _w, _m = g.check(slideshow)
        assert any('"density"' in e and "waives only what it names" in e for e in errs), errs[-1:]
    finally:
        os.remove(os.path.join(slideshow, "storyboard.json"))


def test_validate_and_the_gate_read_the_waiver_through_ONE_parser(tmp_path):
    """validate.py kept its own copy that assumed a string, so the day the gate began accepting an object a
    legitimate per-axis waiver was rejected at the board and accepted by the gate. Two copies of one rule is
    how this repo's caption band became four disagreeing numbers."""
    import sys as _s
    _s.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
    import validate as v
    src = open(os.path.join(os.path.dirname(g.__file__), "validate.py"), encoding="utf-8").read()
    assert "_fe.parse_waiver" in src, "validate must not re-implement the waiver reading"
    board = {"meta": {"renderer": "remotion", "title": "t", "energy_waiver": {"density": "the deck is sparse"}},
             "slides": [{"index": 0, "shot": "ChatThread", "shot_props": {}, "narration": "one"}]}
    r = v.evaluate(board, str(tmp_path), pre_tts=True)
    assert not [e for e in r["errors"] if "energy_waiver" in e], r["errors"]


def test_a_mistyped_axis_is_an_error_not_a_waiver_that_covers_nothing(tmp_path):
    import sys as _s
    _s.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
    import validate as v
    board = {"meta": {"renderer": "remotion", "title": "t", "energy_waiver": {"desnity": "typo"}},
             "slides": [{"index": 0, "shot": "ChatThread", "shot_props": {}, "narration": "one"}]}
    r = v.evaluate(board, str(tmp_path), pre_tts=True)
    assert [e for e in r["errors"] if "no floor is called" in e], r["errors"]


def test_the_negative_result_travels_with_the_motion_floor():
    """Six motivated camera pushes at the documented 0.045 amplitude moved motion p75 by 0.0000 on a real
    161s film. Recorded so nobody repeats the trial expecting a bigger camera to reach this statistic."""
    src = open(os.path.join(os.path.dirname(g.__file__), "film_energy_qa.py"), encoding="utf-8").read()
    assert "0.0000   exactly no change" in src and "+0.0005" in src


def test_the_cli_exits_non_zero_on_a_slideshow(slideshow):
    import sys
    rc = subprocess.run([sys.executable, os.path.join(os.path.dirname(g.__file__), "film_energy_qa.py"),
                         slideshow], capture_output=True, text=True)
    assert rc.returncode == 1, rc.stdout + rc.stderr
    assert "FAIL" in rc.stdout

@pytest.fixture(scope="module")
def one_bright_block(tmp_path_factory):
    """A dark film with ONE flat bright passage — the exact shape that broke the light axis.

    Appending four seconds of a blank white rectangle to a 56-second film took its measured luminance RANGE
    from 0.0972 to 0.9101: past the floor by 6.7x, landing on Figma's own number, with every other frame
    byte-identical. A blank rectangle is not a luminance arc, and a gate that cannot say so is decoration.
    """
    # The film must be LONG for the attack to work: the axis is a RATE over adjacent seconds, so one change
    # in fifteen seconds is 7.1% (a real, if minimal, arc) while one change in sixty seconds is 1.7%. A short
    # fixture would not reproduce what actually shipped.
    d = tmp_path_factory.mktemp("bright_block")
    _render(str(d / "out.mp4"), [
        "-f", "lavfi", "-i", "color=c=0x0a0f16:s=320x180:r=24:d=56",
        "-f", "lavfi", "-i", "color=c=0xf2f2f2:s=320x180:r=24:d=4",
        "-filter_complex", "[0:v]setsar=1[a];[1:v]setsar=1[b];[a][b]concat=n=2:v=1:a=0[v]",
        "-map", "[v]"])
    return str(d)


@pytest.fixture(scope="module")
def light_that_works(tmp_path_factory):
    """The same amount of bright footage, DISTRIBUTED — light that actually changes across the film."""
    d = tmp_path_factory.mktemp("light_works")
    parts = []
    for i in range(5):
        parts += ["-f", "lavfi", "-i", "color=c=0x0a0f16:s=320x180:r=24:d=2",
                  "-f", "lavfi", "-i", "color=c=0xf2f2f2:s=320x180:r=24:d=1"]
    chain = "".join("[%d:v]setsar=1[p%d];" % (i, i) for i in range(10))
    chain += "".join("[p%d]" % i for i in range(10)) + "concat=n=10:v=1:a=0[v]"
    _render(str(d / "out.mp4"), parts + ["-filter_complex", chain, "-map", "[v]"])
    return str(d)


def test_one_bright_passage_clears_the_range_and_is_still_caught(one_bright_block):
    """The regression this axis exists for: RANGE says excellent, and nothing in the film moves."""
    errs, _warns, m = g.check(one_bright_block)
    assert m["luma_range"] >= g.LUMA_RANGE_FLOOR, (
        "the fixture no longer reproduces the attack — its range is %.3f" % m["luma_range"])
    assert m["luma_steps"] < g.LUMA_STEP_FLOOR
    assert any("LIGHT ARC" in e for e in errs), errs


def test_light_distributed_through_the_film_clears_the_arc(light_that_works):
    """The POSITIVE control. Without it, an arc floor set above anything reachable would look like a gate."""
    _errs, _warns, m = g.check(light_that_works)
    assert m["luma_steps"] >= g.LUMA_STEP_FLOOR, (
        "light that changes ten times in fifteen seconds reads as %r" % (m["luma_steps"],))


def test_the_arc_floor_sits_under_every_reference_film():
    for name, rec in g.REFERENCE.items():
        assert len(rec) == 4, "%s has no recorded light-steps value" % name
        assert g.LUMA_STEP_FLOOR <= rec[3], "%s sits under the arc floor" % name


def test_a_film_too_short_for_an_arc_says_so_instead_of_scoring_zero(slideshow):
    """Zero would read as 'measured, and the light never moves'. Not asking is a different claim."""
    m = g.measure(os.path.join(slideshow, "out.mp4"), fps=12)
    assert m["luma_windows"] >= g.MIN_WINDOWS or m["luma_steps"] is None


# ── COVERAGE: the numbers describe the frames ffmpeg handed back, not the file ────────────────────────
#
# `-v error` sends ffmpeg's complaints to a stderr this gate discarded and its exit code was never read, so
# a partial decode arrived as a SHORTER FILM. Measured on a real 88.9s delivered film truncated to 40% of
# its bytes: ffmpeg printed `partial file`, exited non-zero, handed back 371 frames — and the gate printed
# `31s`, `OK 0 error(s)` and exited 0 over 35% of the film.

@pytest.fixture(scope="module")
def truncated(tmp_path_factory):
    """A film cut off mid-stream: the container still CLAIMS its full duration, the decode stops early.

    `+faststart` on purpose — the moov atom has to survive the cut, or ffprobe cannot read a duration and
    the fixture proves the wrong thing (no-duration, not short-decode). A delivered out.mp4 is faststart,
    so this is the shape a damaged delivery actually has. Note that ffmpeg EXITS 0 here and complains only
    on stderr, which is why the return code alone is not the signal.
    """
    d = tmp_path_factory.mktemp("truncated")
    full = str(d / "full.mp4")
    _render(full, ["-f", "lavfi", "-i", "testsrc2=s=320x180:r=24:d=12", "-movflags", "+faststart"])
    src = open(full, "rb").read()
    open(str(d / "out.mp4"), "wb").write(src[: int(len(src) * 0.4)])
    return str(d)


def test_the_universe_is_the_container_duration_not_the_decode(alive):
    m = g.measure(os.path.join(alive, "out.mp4"))
    assert m["declared_seconds"] and abs(m["declared_seconds"] - m["seconds"]) < 1.0, m
    assert m["frames"] == int(round(m["seconds"] * m["fps"]))
    assert "of the" in g.coverage_line(m) and "100%" in g.coverage_line(m), g.coverage_line(m)


def test_a_half_decoded_film_is_an_error_naming_what_was_missed(truncated):
    errs, _warns, m = g.check(truncated)
    assert m["seconds"] < 0.9 * m["declared_seconds"], (
        "the fixture no longer truncates — it decoded %.1fs of %.1fs" % (m["seconds"], m["declared_seconds"]))
    cov = [e for e in errs if e.startswith("COVERAGE:")]
    assert cov, errs
    assert "never reached the instrument" in cov[0] and "%.1fs" % m["declared_seconds"] in cov[0], cov


def test_no_waiver_can_absolve_a_short_decode(truncated):
    """A waiver is a judgement about a film someone WATCHED. This is a report that the film was not read,
    so a blanket string waiver — which turns off every other axis — must leave it standing."""
    json.dump({"meta": {"energy_waiver": "this film is deliberately quiet"}},
              open(os.path.join(truncated, "storyboard.json"), "w", encoding="utf-8"))
    try:
        errs, warns, _m = g.check(truncated)
        assert any(e.startswith("COVERAGE:") for e in errs), errs
        assert not any("COVERAGE" in w for w in warns), warns
    finally:
        os.remove(os.path.join(truncated, "storyboard.json"))


def test_a_file_with_no_declared_duration_says_coverage_is_unknown(alive):
    m = dict(g.measure(os.path.join(alive, "out.mp4")), declared_seconds=None)
    assert "UNKNOWN" in g.coverage_line(m)
    errs = g.coverage_errors(m)
    assert errs and "cannot say how much of the film it measured" in errs[0], errs


def test_the_headline_leads_with_coverage(truncated):
    import sys
    rc = subprocess.run([sys.executable, os.path.join(os.path.dirname(g.__file__), "film_energy_qa.py"),
                         truncated], capture_output=True, text=True)
    first = rc.stdout.splitlines()[0]
    assert "measured" in first and " of the " in first, first
    assert rc.returncode == 1, rc.stdout


def test_the_mutation_that_ignores_a_short_decode_is_caught(truncated):
    """THE MUTATION. Drop `declared_seconds` back out of the measurement — exactly the state before this
    fix — and the gate goes back to reporting a third of a film as the film."""
    import types
    src = open(g.__file__, encoding="utf-8").read()
    old = '        "declared_seconds": probe_duration(path),'
    assert old in src, "the mutation target has drifted out of the source"
    mod = types.ModuleType("film_energy_qa_mutant")
    mod.__file__ = g.__file__
    exec(compile(src.replace(old, '        "declared_seconds": None,', 1), g.__file__, "exec"), mod.__dict__)
    errs, _w, _m = mod.check(truncated)
    # It does NOT go quiet — it says it cannot state coverage, which is the weakest honest claim available.
    assert any("cannot say how much of the film it measured" in e for e in errs), errs
    assert not any("never reached the instrument" in e for e in errs), (
        "the mutant still knew how much it missed, so this probe is not testing the derivation")


# ── density measures whether a frame is DRAWN ON, not whether it is a coloured area ──────────────────

@pytest.fixture(scope="module")
def drawn_vs_blurred(tmp_path_factory):
    """The exact inversion the old metric shipped, rendered so the claim is testable without the film.

    `ruled` is a page of thin rules: every pixel sits NEAR the page tone, and the frame is drawn all over.
    `plate` is a large grey block on the same page, blurred: every pixel of it sits FAR from the page tone,
    and there is no structure anywhere. The delivered film's confirmed-emptiest beat was exactly the second
    — five heavily blurred plates carrying no readable information — and the old metric ranked it the
    SECOND DENSEST frame of thirty."""
    d = tmp_path_factory.mktemp("drawn")
    _render(str(d / "ruled.mp4"), [
        "-f", "lavfi", "-i", "color=c=0xf2ede3:s=384x216:r=12:d=3",
        "-vf", "geq=lum='if(lt(mod(Y,6),1),150,235)':cb=128:cr=128"])
    _render(str(d / "plate.mp4"), [
        "-f", "lavfi", "-i", "color=c=0xf2ede3:s=384x216:r=12:d=3",
        "-f", "lavfi", "-i", "color=c=0x9a9a9a:s=240x130:r=12:d=3",
        "-filter_complex", "[0][1]overlay=x=72:y=43,boxblur=10:2"])
    return d


def _old_metric(path):
    """The definition `_drawn` replaced: share of pixels far from the frame's modal tone."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "fps=12,scale=384:216",
                          "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (384 * 216)
    F = np.frombuffer(raw[:n * 384 * 216], dtype=np.uint8).reshape(n, 216, 384).astype(np.float32) / 255
    return float(np.median([(np.abs(f - np.median(f)) > 0.10).mean() for f in F]))


def test_density_reads_structure_not_coloured_area(drawn_vs_blurred):
    """Both halves are asserted, and the second is what makes this a regression test rather than a
    tautology: the OLD metric must get this pair BACKWARDS. If it did not, the probe would not be testing
    the thing that was wrong."""
    d = drawn_vs_blurred
    ruled = g.density(str(d / "ruled.mp4"))
    plate = g.density(str(d / "plate.mp4"))
    assert ruled and plate, (ruled, plate)
    assert ruled["median"] > 0.10 and plate["median"] < 0.02, (
        "a page of rules is drawn on and a blurred field is not: %.3f vs %.3f"
        % (ruled["median"], plate["median"]))
    o_ruled, o_plate = _old_metric(str(d / "ruled.mp4")), _old_metric(str(d / "plate.mp4"))
    assert o_plate > o_ruled, (
        "the old metric is supposed to rank these BACKWARDS (blurred field %.3f over ruled page %.3f) — if "
        "it does not, this probe is not reproducing the defect" % (o_plate, o_ruled))


def test_density_reports_per_beat_and_no_longer_floors_the_film(slideshow):
    """The absolute floor retired with the old metric rather than being re-guessed from reference films
    measured under it. What replaces it is the question an author can act on: which of MY beats is least
    drawn on. So a sparse film must no longer ERROR on density, and must still be told."""
    board = {"meta": {"renderer": "remotion", "fps": 30},
             "slides": [{"index": i + 1, "shot": "S%d" % i, "duration": 2.0} for i in range(3)]}
    json.dump(board, open(os.path.join(slideshow, "storyboard.json"), "w", encoding="utf-8"))
    try:
        errs, warns, m = g.check(slideshow)
        assert not any("DENSITY" in e for e in errs), errs
        assert any("DENSITY (measured, not gated)" in w for w in warns), warns
        assert m["beats"] and all("drawn" in b and "index" in b for b in m["beats"]), m.get("beats")
        # MOTION is untouched: it still ERRORs on a held frame, so retiring one floor did not retire them all
        assert any("MOTION" in e for e in errs), errs
    finally:
        os.remove(os.path.join(slideshow, "storyboard.json"))


# ── the motion floor says WHICH beats hold the film under it, and which of those are actually frozen ──────────

@pytest.fixture(scope="module")
def held_moving_creep(tmp_path_factory):
    """Three 4 s beats, each under the motion floor for a different reason: a HELD frame (nothing changes), a small
    box sliding across a still page (a mechanism moving in a corner — under a whole-frame floor, never frozen), and
    a low-contrast box CREEPING a pixel at a time (between two sampled frames mostly nothing changes, within a
    second it has visibly moved — the idle clock's kind of motion)."""
    d = tmp_path_factory.mktemp("held_moving_creep")
    page = "color=c=0x14181f:s=320x180:r=24:d=4"
    _render(str(d / "a.mp4"), ["-f", "lavfi", "-i", page])
    _render(str(d / "b.mp4"), ["-f", "lavfi", "-i", page, "-f", "lavfi", "-i", "color=c=0xe8e2d0:s=12x12:r=24:d=4",
                               "-filter_complex", "[0][1]overlay=x='40+t*20':y=60"])
    _render(str(d / "c.mp4"), ["-f", "lavfi", "-i", page, "-f", "lavfi", "-i", "color=c=0x34404e:s=40x40:r=24:d=4",
                               "-filter_complex", "[0][1]overlay=x='120+t*4':y=60"])
    open(d / "list.txt", "w").write("".join("file '%s'\n" % (d / x) for x in ("a.mp4", "b.mp4", "c.mp4")))
    _render(str(d / "out.mp4"), ["-f", "concat", "-safe", "0", "-i", str(d / "list.txt")])
    return str(d)


def _three_beats(out_dir):
    import render_remotion as rr
    seam = rr._REMOTION2_TR / 30.0              # the renderer overlaps each cut by its seam; the board says so
    board = {"meta": {"renderer": "remotion", "fps": 30},
             "slides": [{"index": 1, "shot": "Held", "duration": 4.0 + seam},
                        {"index": 2, "shot": "Mechanism", "duration": 4.0 + seam},
                        {"index": 3, "shot": "Creep", "duration": 4.0}]}
    json.dump(board, open(os.path.join(out_dir, "storyboard.json"), "w", encoding="utf-8"))
    return board


def test_the_motion_split_tells_frozen_from_a_small_thing_moving(held_moving_creep):
    _three_beats(held_moving_creep)
    try:
        errs, _warns, m = g.check(held_moving_creep)
        rows = {r["shot"]: r for r in m["motion_beats"]}
        assert set(rows) == {"Held", "Mechanism", "Creep"}, m["motion_beats"]
        for r in rows.values():                 # all three hold the film under the whole-frame floor...
            assert r["under_s"] >= 0.8 * r["seconds"], r
        # ...but only the held beat is frozen: the box never stops, and the creep moves within every second
        assert rows["Held"]["frozen_s"] >= 0.8 * rows["Held"]["seconds"], rows["Held"]
        assert rows["Mechanism"]["frozen_s"] <= 0.1 * rows["Mechanism"]["seconds"], rows["Mechanism"]
        assert rows["Creep"]["frozen_s"] <= 0.3 * rows["Creep"]["seconds"], rows["Creep"]
        for r in rows.values():
            assert r["frozen_s"] <= r["under_s"] + 1e-9, "a frozen second is always also under the floor"
        motion = [e for e in errs if e.startswith("MOTION:")]
        assert motion and "beat 2 (Mechanism)" in motion[0] and "frozen" in motion[0], motion
    finally:
        os.remove(os.path.join(held_moving_creep, "storyboard.json"))


def test_the_motion_split_rides_into_a_waived_line_so_the_critic_sees_it(held_moving_creep):
    board = _three_beats(held_moving_creep)
    board["meta"]["energy_waiver"] = {"motion": "a diagram film whose motion is its mechanism"}
    json.dump(board, open(os.path.join(held_moving_creep, "storyboard.json"), "w", encoding="utf-8"))
    try:
        errs, warns, _m = g.check(held_moving_creep)
        assert not any(e.startswith("MOTION") for e in errs), errs
        waived = [w for w in warns if w.startswith("waived (MOTION)")]
        assert waived and "By beat" in waived[0] and "beat 1 (Held)" in waived[0], warns
    finally:
        os.remove(os.path.join(held_moving_creep, "storyboard.json"))


def test_no_board_no_split_and_the_film_level_finding_stands(held_moving_creep):
    errs, _warns, m = g.check(held_moving_creep)
    assert m["motion_beats"] == [] and any(e.startswith("MOTION:") and "By beat" not in e for e in errs), errs


def test_a_failed_density_decode_does_not_crash_the_summary(held_moving_creep, monkeypatch, capsys):
    monkeypatch.setattr(g, "density", lambda *a, **k: None)
    g.main([held_moving_creep])
    out = capsys.readouterr().out
    assert "ink n/a" in out and "DENSITY: not measured" in out, out
