"""The image tier's Ken Burns move lands where its curve says, to a fraction of a pixel (render._kenburns_window ->
render._kenburns_frames: each frame is the float crop window resampled whole by Pillow's Lanczos, streamed to ffmpeg
as rawvideo).

WHY. The old chain (scale to motion_ss x W -> zoompan -> scale back) placed zoompan's crop at whole SUPERSAMPLED
pixels: a slow push or pan moved in steps of 1/motion_ss px with a hold between them, and the pixel jitter gate
(scripts/jitter_qa.py -> jitter_html.py) read every tile of a Ken Burns slide at 0.22-0.59 px RMS at the default
motion_ss 2 (ERROR), 0.10-0.14 at motion_ss 8 (WARN) — at ~5.7 s of render per second of video at ss 2. Measured on
the bench in film_work/kenburns (two public-domain photos, a UI screenshot with 13 px type, a chart; a push, a slow
push and a slow pan; 16:9, 9:16, 1:1): see references/ffmpeg-recipes.md "Ken Burns" for the table.

The fast tests pin the sampling math (the window is a float, linear in the frame, held still under reduced motion,
held inside the picture as zoompan held it) and that the resample really moves the picture by a FRACTION of a pixel.
The render test drives the real render._render_slide and tracks two shapes against the analytic move; the gate test
(GATE_RENDER=1) is in tests/test_jitter_html.py, which renders Ken Burns slides at 16:9, 9:16 and 1:1 and requires
the jitter gate to read them clean.
"""
import glob
import inspect
import os
import subprocess

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

import _common
import render

W, H, FPS = 1920, 1080, 30
DUR = 3.0
FRAMES = int(round(DUR * FPS))

needs_ffmpeg = pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "assets", "fonts", "DejaVuSans.ttf")
PUSH = {"from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]}


# ── the sampling math ───────────────────────────────────────────────────────────────────────────────────────────
def test_the_window_starts_on_the_frame_and_ends_on_the_curves_zoom():
    p = render._motion_params(PUSH)
    assert render._kenburns_window(p, 90, 0, W, H) == (0.0, 0.0, float(W), float(H))
    l, t, w, h = render._kenburns_window(p, 90, 90, W, H)
    assert w == pytest.approx(W / 1.12) and h == pytest.approx(H / 1.12)
    assert l == pytest.approx((W - W / 1.12) / 2) and t == pytest.approx((H - H / 1.12) / 2)   # centred anchor
    assert render._kenburns_window(p, 90, 200, W, H) == render._kenburns_window(p, 90, 90, W, H)  # held at its end


def test_a_slow_pan_moves_by_a_fraction_of_a_pixel_every_frame_never_a_step():
    """The defect was a window quantised to whole (supersampled) pixels: a hold, then a jump. The window is a float
    that moves by the SAME sub-pixel amount on every frame."""
    p = render._motion_params({"from": [0.35, 0.5, 1.10], "to": [0.65, 0.5, 1.10]})
    lefts = np.array([render._kenburns_window(p, 150, on, W, H)[0] for on in range(151)])
    d = np.diff(lefts)
    assert 0.1 < d.mean() < 1.0, "a slow pan: under a pixel a frame"
    assert np.allclose(d, d.mean(), atol=1e-9), "every frame moves by the same fraction — no hold, no jump"
    assert any(abs(x - round(x)) > 0.1 for x in lefts), "the window sits between pixels"


def test_reduced_motion_holds_the_window_and_the_intensity_dial_scales_it():
    still = render._motion_params(PUSH, reduced_motion=True)
    assert {render._kenburns_window(still, 90, on, W, H) for on in range(91)} == {(0.0, 0.0, float(W), float(H))}
    bold = render._motion_params(PUSH, amp=render._intensity_amp({"intensity": "bold"}))
    assert render._kenburns_window(bold, 90, 90, W, H)[2] < render._kenburns_window(render._motion_params(PUSH), 90,
                                                                                     90, W, H)[2]


def test_the_window_is_held_inside_the_picture_as_zoompan_held_it():
    """zoompan clipped zoom to [1, 10] and its crop corner to the picture; an anchor authored outside 0..1 or a zoom
    under 1 renders as it always did instead of reading past the frame."""
    p = render._motion_params({"from": [1.4, -0.3, 0.9], "to": [1.4, -0.3, 0.9]})
    l, t, w, h = render._kenburns_window(p, 30, 10, W, H)
    assert (w, h) == (float(W), float(H)) and (l, t) == (0.0, 0.0)
    p = render._motion_params({"from": [1.4, -0.3, 1.2], "to": [1.4, -0.3, 1.2]})
    l, t, w, h = render._kenburns_window(p, 30, 10, W, H)
    assert l == pytest.approx(W - w) and t == 0.0


def _bar_track(src, w, h, p, n):
    """The x-centroid of a vertical bar on each frame of the move (ground subtracted, NOT clipped: Lanczos rings
    below the ground on both sides, and clipping one side biases the centroid by the frame's phase)."""
    xs = []
    for buf in render._kenburns_frames(src, w, h, p, n, n):
        g = np.frombuffer(buf, np.uint8).reshape(h, w, 3)[60:120, :, 1].astype(np.float64) - 20.0
        col = g.sum(axis=0)
        xs.append((np.arange(w) * col).sum() / col.sum())
    return np.array(xs)


def test_the_resample_moves_the_picture_by_the_fraction_the_window_says(tmp_path, monkeypatch):
    """Through the real resample (_kenburns_frames), a vertical bar's centroid follows a slow pan (0.29 px a frame)
    to a few hundredths of a pixel. The mutation — the window's corner floored to a whole pixel, which is what
    zoompan did at ss 1 — reads a step of most of a pixel on the same measurement (E7)."""
    w, h = 320, 180
    im = Image.new("RGB", (w, h), (20, 20, 20))
    ImageDraw.Draw(im).rectangle([150, 40, 153, 140], fill=(240, 240, 240))
    src = str(tmp_path / "bar.png")
    im.save(src)
    p = render._motion_params({"from": [0.3, 0.5, 1.10], "to": [0.7, 0.5, 1.10]})
    n = 40
    # Pillow samples output pixel x at source left + (x + 0.5) / z - 0.5: the bar's centre (151.5) lands here
    true = np.array([(152.0 - render._kenburns_window(p, n, on, w, h)[0]) * 1.10 - 0.5 for on in range(n)])
    err = _bar_track(src, w, h, p, n) - true
    assert np.abs(err).max() < 0.05 and np.abs(np.diff(err)).max() < 0.05, err
    exact = render._kenburns_window
    monkeypatch.setattr(render, "_kenburns_window", lambda *a: (float(int(exact(*a)[0])),) + exact(*a)[1:])
    stepped = _bar_track(src, w, h, p, n) - true
    assert np.abs(np.diff(stepped)).max() > 0.5, "the measurement must see a whole-pixel step when there is one"


def test_a_move_that_does_not_move_is_the_fitted_frame_itself(tmp_path):
    src = str(tmp_path / "s.png")
    Image.effect_noise((64, 36), 60).convert("RGB").save(src)
    frames = list(render._kenburns_frames(src, 64, 36, render._motion_params(PUSH, reduced_motion=True), 30, 5))
    assert len(frames) == 5 and all(f == Image.open(src).convert("RGB").tobytes() for f in frames)
    first = next(render._kenburns_frames(src, 64, 36, render._motion_params(PUSH), 30, 3))
    assert first == Image.open(src).convert("RGB").tobytes(), "frame 0 of a push from 1.0 is not resampled (no blur)"


def test_a_source_of_the_wrong_size_is_refused(tmp_path):
    src = str(tmp_path / "s.png")
    Image.new("RGB", (60, 36)).save(src)
    with pytest.raises(ValueError, match="not the 64x36"):
        next(render._kenburns_frames(src, 64, 36, render._motion_params(PUSH), 30, 3))


def test_the_slide_path_has_no_zoompan_and_no_supersample_knob():
    src = inspect.getsource(render._render_slide)
    assert "zoompan=" not in src and 'meta.get("motion_ss"' not in src
    assert "_kenburns_frames(" in src and "_run_fed(" in src


@needs_ffmpeg
def test_a_failing_ffmpeg_is_raised_with_its_reason():
    with pytest.raises(subprocess.CalledProcessError) as e:
        render._run_fed(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "8x8", "-i", "pipe:0",
                         "-c:v", "no_such_codec", "-f", "null", "-"], iter([b"\0" * 192] * 3))
    assert "no_such_codec" in (e.value.stderr or "")


# ── through the real render path ────────────────────────────────────────────────────────────────────────────────
# off-centre, clear of the max-zoom excursion so neither element's ink reaches the frame's edge (a clipped shape's
# centroid is not an affine function of zoom and would read as stepping that is not there)
TEXT_BOX = (1050, 1910, 750, 980)
HLINE_BOX = (200, 760, 180, 300)


def _build_fixture(path):
    img = Image.new("RGB", (W, H), (20, 20, 20))
    d = ImageDraw.Draw(img)
    # ink at 200, not 255: Lanczos overshoots an edge, and an overshoot clipped at 255 (while the undershoot into the
    # ground of 20 is kept) moves the centroid with the frame's phase — measured as 0.1 px of noise on perfect frames
    d.text((1450, 850), "Glide 42", font=ImageFont.truetype(FONT, 160), fill=(200, 200, 200), anchor="mm")
    d.rectangle([300, 240, 660, 242], fill=(200, 200, 200))   # a thin (3 px) hairline
    img.save(path)


def _centroid(arr, box):
    """The ink's centroid in the box: luma over the frame's OWN ground (the median of the box's border), unclipped.
    The old version weighed `luma - 15` clipped at 0 on a ground of 20 — the ground itself then carried a constant
    mass whose centroid does not scale, so the measure was not affine in z and read 0.14-0.25 px of "residual" on
    perfect, unencoded frames (its own floor, which the zoompan chain's 0.13-0.29 was partly made of). Clipping at
    the ground instead biases by phase (Lanczos rings below it on both sides)."""
    x0, x1, y0, y1 = box
    crop = arr[y0:y1, x0:x1].astype(np.float64)
    luma = 0.2126 * crop[..., 0] + 0.7152 * crop[..., 1] + 0.0722 * crop[..., 2]
    ground = np.median(np.concatenate([luma[0], luma[-1], luma[:, 0], luma[:, -1]]))
    w = luma - ground
    cols, rows = w.sum(axis=0), w.sum(axis=1)
    m = cols.sum()
    if m < 500:
        return None
    return (np.arange(cols.size) * cols).sum() / m + x0, (np.arange(rows.size) * rows).sum() / m + y0


def _residual(rows, box, axis):
    """RMS and worst frame-to-frame step of the centroid's residual against the analytic zoom (a linear fit in z)."""
    idx = 0 if axis == "x" else 1
    vals, zs = [], []
    for i, r in enumerate(rows):
        c = _centroid(r, box)
        if c is None:
            continue
        vals.append(c[idx]); zs.append(1.0 + 0.12 * i / FRAMES)
    vals, zs = np.array(vals), np.array(zs)
    A = np.vstack([np.ones_like(zs), zs]).T
    coef, *_ = np.linalg.lstsq(A, vals, rcond=None)
    res = vals - A @ coef
    return float(np.sqrt((res ** 2).mean())), float(np.abs(np.diff(res)).max()), float(np.ptp(vals)), len(vals)


# The old zoompan chain measured 0.13-0.29 px RMS on this fixture at motion_ss 2 (with the old, ground-biased centroid);
# the float resample measures 0.01-0.065 through the real encode. Only the RMS is judged: a centroid over a large glyph
# moves by up to 0.2 px on single PERFECT (unencoded) frames as Lanczos's edge response changes with phase, so a
# one-frame step is this measure's noise, not the move's. jitter_qa (tests/test_jitter_html.py) is the gate.
RMS_CEIL = 0.08


@needs_ffmpeg
def test_kenburns_text_and_hairline_track_the_analytic_zoom(tmp_path):
    out = str(tmp_path)
    _build_fixture(os.path.join(out, "fixture.png"))
    _common.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
                 "-t", str(DUR), os.path.join(out, "silence.wav")])
    meta = {"_out": out, "fps": FPS, "captions": False}
    slide = {"index": 0, "type": "slide", "image": "fixture.png", "fit": "cover", "duration": DUR,
             "audio": "silence.wav", "transition": "none", "motion": dict(PUSH, type="kenburns")}
    clip = os.path.join(out, "clip.mp4")
    render._render_slide(slide, meta, W, H, clip, False, out)
    frames_dir = os.path.join(out, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-i", clip, os.path.join(frames_dir, "f_%04d.png")], check=True,
                   capture_output=True)
    paths = sorted(glob.glob(os.path.join(frames_dir, "f_*.png")))
    assert len(paths) == FRAMES
    rows = [np.asarray(Image.open(p).convert("RGB")) for p in paths]
    for name, box in (("text", TEXT_BOX), ("hline", HLINE_BOX)):
        for axis in ("x", "y"):
            rms, step, travel, n = _residual(rows, box, axis)
            assert n >= 20, "%s/%s: too few confident frames (%d)" % (name, axis, n)
            if travel < 15.0 and axis == "x" and name == "hline":
                continue    # the hairline's x-travel at this short duration can be small; y + text cover the axis
            assert rms < RMS_CEIL, ("%s/%s: rms=%.3fpx (worst step %.3fpx) over the ceiling %.2f — the Ken Burns "
                                    "move is stepping again" % (name, axis, rms, step, RMS_CEIL))


def _param_sets(clip):
    """The SPS and PPS NAL units of a clip's H.264 stream, as bytes (annex-B, start codes split off)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", clip, "-c:v", "copy", "-bsf:v", "h264_mp4toannexb", "-an",
                          "-frames:v", "1", "-f", "h264", "-"], capture_output=True, check=True).stdout
    nals = [n.lstrip(b"\x00") for n in raw.split(b"\x00\x00\x01") if n.strip(b"\x00")]
    return sorted(n.rstrip(b"\x00") for n in nals if n and (n[0] & 0x1F) in (7, 8))


@needs_ffmpeg
def test_a_ken_burns_clip_concats_with_the_films_other_clips(tmp_path):
    """The Ken Burns clip is encoded with its own x264 tune (render._KB_X264). The film is joined with `-c copy`, which
    decodes every clip with the FIRST clip's SPS/PPS — so the slide clip's must be byte-identical to a programmatic
    scene's, or its picture decodes wrong (measured: `-tune grain` alone moves the PPS chroma QP offset -2 -> -4)."""
    out = str(tmp_path)
    _build_fixture(os.path.join(out, "fixture.png"))
    _common.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "1.0",
                 os.path.join(out, "a.wav")])
    meta = {"_out": out, "fps": FPS, "captions": False}
    slide = {"index": 1, "type": "slide", "image": "fixture.png", "fit": "cover", "duration": 1.0, "audio": "a.wav",
             "transition": "none", "motion": dict(PUSH, type="kenburns")}
    title = {"index": 2, "type": "title", "props": {"title": "Concat", "subtitle": "headers"}, "duration": 1.0,
             "audio": "a.wav", "transition": "none", "narration": ""}
    a, b = os.path.join(out, "a.mp4"), os.path.join(out, "b.mp4")
    render._render_slide(slide, meta, W, H, a, False, out)
    render._render_slide(title, meta, W, H, b, False, out)
    assert _param_sets(a) == _param_sets(b), "the Ken Burns clip's SPS/PPS differ from a programmatic clip's"
    lst = os.path.join(out, "l.txt")
    open(lst, "w").write("file '%s'\nfile '%s'\n" % (b, a))
    joined = os.path.join(out, "j.mp4")
    _common.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    # decoded through the TITLE's headers, the slide's frame 0 is its own picture (the fitted frame, zoom 1.0)
    direct = np.asarray(Image.open(_frame_png(a, 0, out)).convert("L"), np.float64)
    via = np.asarray(Image.open(_frame_png(joined, 30, out)).convert("L"), np.float64)
    assert np.abs(direct - via).mean() < 0.5


def _frame_png(video, n, out):
    p = os.path.join(out, "f_%s_%d.png" % (os.path.basename(video), n))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vf", "select=eq(n\\,%d)" % n, "-frames:v", "1", p],
                   check=True)
    return p


def test_troubleshooting_names_the_jitter_gate_not_the_retired_knob():
    """The old escape hatch ("raise meta.motion_ss") no longer does anything; the doc must not prescribe it."""
    doc = open(os.path.join(HERE, "..", "references", "troubleshooting.md"), encoding="utf-8").read()
    assert "raise `meta.motion_ss`" not in doc
    assert "jitter_qa.py" in doc and "_kenburns_window" in doc
