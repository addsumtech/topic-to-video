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


def test_the_cli_exits_non_zero_on_a_slideshow(slideshow):
    import sys
    rc = subprocess.run([sys.executable, os.path.join(os.path.dirname(g.__file__), "film_energy_qa.py"),
                         slideshow], capture_output=True, text=True)
    assert rc.returncode == 1, rc.stdout + rc.stderr
    assert "FAIL" in rc.stdout
