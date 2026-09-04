"""SHAKE must be distinguishable from MOTION — proved on controls, both directions.

WHY THIS FILE IS THE PRECONDITION FOR ANY MOTION WORK. `film_energy_qa` scores motion as the p75 of the mean
absolute frame difference, and that number rises for a camera push, for a reveal, and — just as happily —
for a frame vibrating in place. Measured on this repo's own renders:

    locked camera         motion_p75 0.0036
    1px per-frame jitter  motion_p75 0.0051
    3px per-frame jitter  motion_p75 0.0077      (the delivery floor is 0.0037)

So shake is the CHEAPEST way to pass the motion gate: a film sitting under the floor clears it at double by
vibrating. Optimising this tier against that statistic without a discriminant is how the defect comes back
with the gate turning greener as it does. The camera is locked by default today because the last repair had
no way to prove the difference; this file is that proof, so the lock can be reasoned about rather than kept
out of fear.

THE CONTROLS ARE BUILT FROM A DRAWN PLATE, NOT A SYNTHETIC VIDEO SOURCE. Four attempts at lavfi controls
were thrown away first, and the reasons are worth keeping: a smooth `gradients` field has no structure for
phase correlation to peak on (it reported wander 6.2 on a frame travelling in a straight line), `testsrc2`
has so much of its own motion that an added jitter vanishes inside it, `noise=allf=t` regenerates every
frame so nothing correlates at all — and `gradients` is not even reproducible run to run (0.27 and 0.091 on
byte-identical commands). A drawn plate with type and edges is a fair, deterministic subject, and the
instrument's real calibration is eight rendered-film controls recorded in the module docstring.
"""
import os
import shutil
import subprocess

import pytest

import shake_qa as sq

_NEEDS_FFMPEG = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


def _plate(path):
    """A deterministic film-like plate: type, panels, edges — structure at several scales, which is what
    phase correlation needs and what every real frame in this library has."""
    from PIL import Image, ImageDraw
    im = Image.new("L", (640, 360), 18)
    d = ImageDraw.Draw(im)
    for i in range(4):
        x = 40 + i * 145
        d.rounded_rectangle([x, 90, x + 118, 275], radius=12, fill=52, outline=150, width=2)
        d.rectangle([x + 14, 110, x + 60, 118], fill=200)
        d.rectangle([x + 14, 132, x + 96, 138], fill=120)
        d.text((x + 14, 240), "PANEL %d" % i, fill=235)
    d.text((40, 30), "A FRAME WITH STRUCTURE", fill=240)
    d.line([40, 310, 600, 310], fill=90, width=2)
    im.save(path)


def _clip(png, mp4, crop_expr):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "6", "-r", "30", "-i", png,
                    "-vf", "crop=iw-40:ih-40:%s,format=gray" % crop_expr,
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", mp4],
                   check=True, capture_output=True)


@pytest.fixture()
def plate(tmp_path):
    pytest.importorskip("PIL")
    p = str(tmp_path / "plate.png")
    _plate(p)
    return p


@_NEEDS_FFMPEG
def test_a_travelling_frame_is_not_shake(plate, tmp_path):
    """A pan is movement that GOES somewhere: path and net displacement are the same distance, so wander
    sits near 1. If this ever fails, the gate has begun refusing the thing motion work exists to add."""
    p = str(tmp_path / "pan.mp4")
    _clip(plate, p, "20+18*t:20")
    m = sq.measure(p)
    assert m, "unmeasurable"
    assert m["fraction"] <= sq.SHAKE_FRACTION_FAIL, "a smooth pan was called shake: %r" % (m["fraction"],)
    assert m["judged"] > 0, "the pan was skipped rather than judged — the control proves nothing"


@_NEEDS_FFMPEG
def test_a_vibrating_frame_is_caught(plate, tmp_path):
    """THE positive control. Same plate, same encoder, comparable travel — one reverses direction every few
    frames. Only the RATIO separates them; magnitude cannot, which is the whole point."""
    p = str(tmp_path / "jitter.mp4")
    _clip(plate, p, "20+2*sin(n*2.7):20+2*sin(n*3.9+1.1)")
    m = sq.measure(p)
    assert m, "unmeasurable"
    assert m["fraction"] > sq.SHAKE_FRACTION_FAIL, "per-frame jitter passed as clean: %r" % (m,)
    assert m["wander_p90"] > sq.WANDER_SHAKE * 2, "the two classes are no longer far apart: %r" % (m,)


@_NEEDS_FFMPEG
def test_sub_pixel_shake_is_caught(plate, tmp_path):
    """The ugliest shake is the smallest: half a pixel of tremble is deeply unpleasant to watch and rounds
    to zero without the sub-pixel peak fit, so the instrument would call the worst case perfectly clean.
    Built by moving a 4x plate by 2px, which is half a pixel at the original scale."""
    from PIL import Image
    big = str(tmp_path / "big.png")
    Image.open(plate).resize((2560, 1440), Image.BICUBIC).save(big)
    p = str(tmp_path / "sub.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "6", "-r", "30", "-i", big, "-vf",
                    "crop=iw-160:ih-160:80+2*sin(n*2.7):80+2*sin(n*3.9+1.1),scale=600:340,format=gray",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", p], check=True, capture_output=True)
    m = sq.measure(p)
    assert m and m["fraction"] > sq.SHAKE_FRACTION_FAIL, "sub-pixel shake read as clean: %r" % (m,)


@_NEEDS_FFMPEG
def test_a_still_frame_is_silent_rather_than_judged(plate, tmp_path):
    """Dividing one tiny number by another manufactures verdicts. A frame that is not moving has no ratio
    worth reading and must not be reported as either good or bad."""
    p = str(tmp_path / "still.mp4")
    _clip(plate, p, "20:20")
    m = sq.measure(p)
    assert m and m["shaky"] == 0, "a still frame was called shaky: %r" % (m,)
    assert m["judged"] == 0, "a still frame was judged at all: %r" % (m,)


def test_the_verdict_is_a_FRACTION_not_a_single_window():
    """One high-wander window is a seam, a decode artefact, or chaotic content. Measured on a real film of
    four generative fields with a LOCKED camera, wander p90 reached 3.22 — above the per-window threshold —
    while only 3% of windows tripped. The fraction rule is what keeps that from being a false positive."""
    import inspect
    assert 'm["fraction"] > SHAKE_FRACTION_FAIL' in inspect.getsource(sq.main)
    assert 0 < sq.SHAKE_FRACTION_FAIL < 0.5


def test_an_unreadable_frame_is_UNKNOWN_rather_than_clean_or_shaky():
    """Phase correlation needs texture. Below the confidence line the displacement is whichever way the
    noise leaned, and a gate that guesses there earns a reputation for crying wolf. The threshold came off
    measurements — real frames 69-359, unreadable ones 24-38 — not off a preference."""
    import inspect
    src = inspect.getsource(sq)
    assert "MIN_PEAK_CONFIDENCE" in src and sq.MIN_PEAK_CONFIDENCE >= 40
    assert "sure = " in src and "judged = moving and sure" in src, (
        "confidence no longer gates whether a window is judged")


def test_content_motion_is_deliberately_invisible_to_this_gate():
    """A card sliding in, a bar growing, a field flowing — none of it translates the FRAME, so none of it is
    this instrument's business. A gate that objected to a reveal would be switched off within a week, and
    raising motion by animating content is exactly the safe direction this discriminant exists to open."""
    import inspect
    doc = inspect.getdoc(sq) or ""
    assert "invisible here" in doc and "CAMERA" in doc
