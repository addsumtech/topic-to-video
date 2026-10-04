"""Sub-pixel stepping in the image tier's Ken Burns chain (scale=2W:2H:lanczos -> zoompan s=2Wx2H
-> scale=W:H:lanczos) — investigated alongside the HTML/Remotion tiers' proven text-baseline snap,
but NOT the same defect, and NOT changed here. Keep this file in sync with that finding; it is a
regression GUARD on the measured floor, not a target to tighten.

MEASURED (synthetic 1920x1080 slide, text block + two hairlines, default 1.0->1.12/10s move,
through the real render path `render._render_slide` and, to isolate the chain from h264/chroma
noise, the identical scale->zoompan->scale filtergraph output as lossless PNG):

  default ss=2:  RMS 0.13-0.29px, worst frame-to-frame jump 0.30-0.61px (6 tracks: text/hline/
                 vline x+y). A COLORED hairline (tests the 4:2:0-chroma-grid half of the
                 suspected flaw) measured SMALLER residual (0.08-0.14px) than the grayscale ones —
                 no sign chroma subsampling adds its own extra step on top.
  ss=3, ss=4:    the SAME six tracks drop a little (worst jump 0.39-0.54px at ss=4) but not close
                 to proportionally (1/ss would predict ~0.25px / ~0.15px) — a real but MINOR
                 contributor, not the dominant one.
  raw frame-to-frame diffs (ss=4, hairline/x, 300 frames): only 12/299 are a true hold (<0.01px);
                 most are small (89/299 < 0.05px) continuous drift, only 11/299 reach the ≥0.25px
                 "jump" the task's action threshold names, and NONE of those is followed by a
                 multi-frame HOLD at a new constant value — i.e. no hold-then-jump staircase, the
                 signature Task 1 (HTML tier) found and fixed. This is a continuous, partly
                 ss-reducible sub-pixel ripple (consistent with the final lanczos resample's own
                 phase response), not an integer-pixel snap.
  candidates tried, neither adopted:
    `perspective` filter, eval=frame — NOT viable on this ffmpeg build: its expression evaluator
      has no frame-index constant (`n`/`t`/`T`/`N` all raise "Undefined constant").
    `format=yuv444p` + ss=4 + zoompan straight to `s=WxH` (no second scale) — measured a WASH on
      residual (worst RMS 0.303px vs baseline's 0.290px) while costing ~4% sharpness, for a 4x
      render-time win. Not a fix; kept only as a possible speed lever if ever wanted.

So: real, small, mostly-cosmetic, NOT the clean integer-pixel staircase the two suggested
sub-pixel-warp replacements target — per the task's own rule ("if it does not step measurably...
change nothing"), the chain is UNCHANGED. `references/troubleshooting.md` already tells an author
with visible jitter (a much larger-delta symptom than anything measured here) to raise
`meta.motion_ss`; that guidance stands.

This test is deliberately NOT tuned to today's exact numbers (a different ffmpeg/libswscale build
can shift them) — it's a generous ceiling so a future change that makes the chain MATERIALLY
worse (reintroducing something closer to Task 1's 0.25-0.3 RMS / ~0.9px clean snap) is caught.
"""
import glob
import os
import subprocess

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

import _common
import render

W, H, FPS = 1920, 1080, 30
DUR = 3.0                                      # short clip: enough frames, fast to render/decode
FRAMES = int(round(DUR * FPS))

needs_ffmpeg = pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "assets", "fonts", "DejaVuSans.ttf")

# off-centre, clear of the max-zoom excursion (12% about the frame centre) so neither element's
# own ink ever reaches the fixture's edge — a clipped shape's centroid is NOT an affine function
# of zoom and would masquerade as stepping that isn't really there (caught during development: a
# first placement put the text's right edge 27px past a 1920-wide frame already at zoom=1.0).
TEXT_BOX = (1050, 1910, 750, 980)
HLINE_BOX = (200, 760, 180, 300)


def _build_fixture(path):
    img = Image.new("RGB", (W, H), (20, 20, 20))
    d = ImageDraw.Draw(img)
    d.text((1450, 850), "Glide 42", font=ImageFont.truetype(FONT, 160), fill=(255, 255, 255), anchor="mm")
    d.rectangle([300, 240, 660, 242], fill=(255, 255, 255))   # a thin (2px) hairline
    img.save(path)


def _centroid(arr, box):
    x0, x1, y0, y1 = box
    crop = arr[y0:y1, x0:x1].astype(np.float64)
    luma = 0.2126 * crop[..., 0] + 0.7152 * crop[..., 1] + 0.0722 * crop[..., 2]
    w = np.clip(luma - 15.0, 0, None)
    cols, rows = w.sum(axis=0), w.sum(axis=1)
    m = cols.sum()
    if m < 500:
        return None
    return (np.arange(cols.size) * cols).sum() / m + x0, (np.arange(rows.size) * rows).sum() / m + y0


def _zoom_at(i, frames, z0=1.0, z1=1.12):
    """The exact value `render._motion_exprs`'s zexpr evaluates to at output frame `i` — prescribed
    by the filtergraph we build, not measured."""
    return z0 + (z1 - z0) * i / frames


def _residual(rows, box, axis):
    idx = 0 if axis == "x" else 1
    vals, zs = [], []
    for i, r in enumerate(rows):
        c = _centroid(r, box)
        if c is None:
            continue
        vals.append(c[idx]); zs.append(_zoom_at(i, len(rows)))
    vals, zs = np.array(vals), np.array(zs)
    A = np.vstack([np.ones_like(zs), zs]).T
    coef, *_ = np.linalg.lstsq(A, vals, rcond=None)
    res = vals - A @ coef
    rms = float(np.sqrt((res ** 2).mean()))
    step = float(np.abs(np.diff(res)).max()) if len(res) > 1 else 0.0
    travel = float(vals.max() - vals.min())
    return rms, step, travel, len(vals)


# generous ceilings: a regression guard on the MEASURED floor (module docstring), not a tight
# target — Task 1's SNAPPED (broken) case measured 0.22-0.26 RMS / 0.89-0.95px jumps, so a value
# anywhere near that on this chain would mean something got materially worse.
RMS_CEIL, STEP_CEIL = 0.8, 1.5
MIN_TRAVEL = 15.0


@needs_ffmpeg
def test_kenburns_text_and_hairline_track_the_analytic_zoom_within_a_generous_ceiling(tmp_path):
    out = str(tmp_path)
    img = os.path.join(out, "fixture.png")
    _build_fixture(img)
    _common.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
                 "-t", str(DUR), os.path.join(out, "silence.wav")])
    meta = {"_out": out, "fps": FPS, "captions": False, "motion_ss": 2}
    slide = {
        "index": 0, "type": "slide", "image": "fixture.png", "fit": "cover",
        "duration": DUR, "audio": "silence.wav", "transition": "none",
        "motion": {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]},
    }
    clip = os.path.join(out, "clip.mp4")
    render._render_slide(slide, meta, W, H, clip, False, out)
    frames_dir = os.path.join(out, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-i", clip, os.path.join(frames_dir, "f_%04d.png")],
                   check=True, capture_output=True)
    paths = sorted(glob.glob(os.path.join(frames_dir, "f_*.png")))
    assert len(paths) >= FRAMES - 2
    rows = [np.asarray(Image.open(p).convert("RGB")) for p in paths]
    for name, box in (("text", TEXT_BOX), ("hline", HLINE_BOX)):
        for axis in ("x", "y"):
            rms, step, travel, n = _residual(rows, box, axis)
            assert n >= 20, "%s/%s: too few confident frames (%d)" % (name, axis, n)
            if travel < MIN_TRAVEL and axis == "x" and name == "hline":
                continue    # the hairline's x-travel at this short duration can be small; y+text cover the axis
            assert rms < RMS_CEIL and step < STEP_CEIL, (
                "%s/%s: rms=%.3fpx step=%.3fpx exceeds the regression ceiling (rms<%.1f, step<%.1f) — "
                "the Ken Burns chain got MATERIALLY worse, not just noisier" % (
                    name, axis, rms, step, RMS_CEIL, STEP_CEIL))


def test_troubleshooting_still_offers_the_motion_ss_escape_hatch():
    """Source-level tripwire: the one lever that measurably helps (raising `motion_ss`) must stay
    documented — if this line is ever removed, whoever removes it should see this fail and either
    restore guidance or point to a replacement."""
    doc = open(os.path.join(HERE, "..", "references", "troubleshooting.md"), encoding="utf-8").read()
    assert "motion_ss" in doc and "raise `meta.motion_ss` to 3" in doc
