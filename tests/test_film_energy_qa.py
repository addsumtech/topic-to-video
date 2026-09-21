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
    assert b["ink_median"] > a["ink_median"] * 10
    assert b["luma_range"] > a["luma_range"] * 10


def test_a_rendered_slideshow_fails_the_gate(slideshow):
    errs, _warns, m = g.check(slideshow)
    assert m["motion_p75"] < g.MOTION_P75_FLOOR
    blob = " ".join(errs)
    assert "MOTION" in blob and "DENSITY" in blob and "LIGHT" in blob


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
    board = {"meta": {"energy_waiver": {"density": "this deck's own warm-white design language is sparse"}}}
    json.dump(board, open(os.path.join(slideshow, "storyboard.json"), "w", encoding="utf-8"))
    try:
        errs, warns, _m = g.check(slideshow)
        assert any(e.startswith("MOTION") for e in errs), "motion was never reasoned about; it stays gated"
        assert any("waived (DENSITY)" in w for w in warns), "the named axis IS waived, and says so"
        assert not any(e.startswith("DENSITY") for e in errs)
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
