#!/usr/bin/env python3
"""jitter_qa — does the TYPE in a delivered film move the way its geometry says it moves? Read from the PIXELS.

    python3 scripts/jitter_qa.py <out_dir>                     # judge out.mp4 against the film's own census
    python3 scripts/jitter_qa.py <out_dir> --census=PATH.gz    # ...with a census kept by text_safe_qa --sync --census
    python3 scripts/jitter_qa.py <out_dir> --video=old.mp4     # ...a different render of the same film (a before)
    python3 scripts/jitter_qa.py --clip <file.mp4|png_dir> [--truth=census.json.gz]   # any clip; no census: tiles
    python3 scripts/jitter_qa.py --calibrate [--aspect=9:16]   # the synthetic controls, with their separation

BOTH TIERS. A remotion film's census is its Film composition's (text_safe_qa); an HTML-tier film's is built per scene
by scripts/jitter_html.py (the pages' own DOM on the capture plan, the image slides' Ken Burns geometry). EXIT 0 OK or
NOTHING TO JUDGE (said in those words) · 1 a line trembles · 2 UNMEASURED (no out.mp4, a census of another render,
or type that was found and could not be judged). Every run prints `scope:` lines.

WHY A PIXEL GATE. The type-glide census (text_safe_qa --glide) reads the DOM: it knows where each line of type truly
is on every frame, and it judges whether Skia will snap that line's baseline. It CANNOT judge type inside a
composited layer — a 3D surface, a will-change layer — because that type is rasterised into a layer and moved by
the compositor, a path the DOM does not describe; the census listed such lines (flag `c`) and judged nothing. A
delivered product film put its whole UI panel inside a 3D screen, panned and pushed a keyframed camera across it,
passed every gate, and the viewer saw the type tremble (字体抖动). Any structure the DOM rule does not model is a
place the next defect hides. The pixels have no such blind spot: whatever the renderer did, it is in the frame.

HOW. The census still says WHERE each line of type is and where it TRULY moves between two frames (its client rect
is computed from every transform, 3D included, before anything is rasterised). For every line on every pair of
consecutive frames the same window is cut from both decoded frames, and the line's displacement is measured by
phase correlation with a sub-pixel peak fit. What the viewer sees as jitter is the difference:

    error = measured displacement - true displacement            (px, per frame pair)

A line that glides has error ~0 on every pair whatever its speed; a baseline snapped to whole pixels holds
(error = -speed) and then jumps (error = 1 - speed); a layer re-rasterised at a new scale pops. Without a census
(`--clip`) the true displacement is estimated as the measured one smoothed (a local quadratic over SMOOTH_PAIRS),
which sees steps and wobble but would call a designed shake smooth; the census path is the gate.

WHAT IS FLAGGED (thresholds are a viewer's, see the constants):
  JITTER    a run of pairs whose error RMS over JIT_WINDOW pairs reaches JIT_RMS_ERROR px — a staircase, a
            wobble, a stall-and-jump. Each line is judged on its own track and reported once, at its worst window.
  POP       a single pair whose error reaches POP_PX on a line that otherwise glides — a raster-scale change, a
            one-frame re-layout.
  SHIMMER   a line that does not move (true and measured under STILL_PX) whose pixels change, after alignment, by
            SHIMMER_REL of its own edge energy — re-rasterised in place.

WHAT IS NOT JUDGED, and is printed as coverage rather than counted clean: pairs across a cut or a seam (opacity
changing), a line under GLIDE_MIN_OPACITY or partly off frame, a line moving faster than FAST_PX a frame (motion
that fast masks a sub-pixel error and the window would leave the line), a line growing more than SCALE_STEP a
frame, a line whose text changed, a pair where another line moving differently shares the window, and a pair whose
correlation peak is too weak to believe (MIN_CONF).
"""
import argparse
import gzip
import json
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TAG = "[jitter]"

# ── THRESHOLDS: what a viewer sees ──────────────────────────────────────────────────────────────────────────────
# The reference is two measured cases on this renderer. A delivered film whose type stepped a whole pixel at a time
# under a slow push measured 0.27px RMS against its drawing and the viewer reported it (字体还是会有很轻微的抖动);
# after the cure the same push measured 0.02-0.07px and nobody did. The ERROR line sits between them with room on
# both sides once the codec's own noise on real footage is counted (calibrated: --calibrate, and the numbers in
# references/engineering-case-law.md).
JIT_WINDOW = 8                 # consecutive pairs judged together: a quarter of a second at 30fps
JIT_RMS_ERROR = 0.15           # px RMS of the error over a window: visible trembling
JIT_RMS_WARN = 0.10            # px: measurable, at the edge of what is seen
POP_PX = 0.6                   # px in ONE pair, on a line otherwise gliding: a visible pop
SHIMMER_REL = 0.15             # aligned change / edge energy on a still line: re-rasterised in place
STILL_PX = 0.05                # px a frame: below this a line is not moving
FAST_PX = 6.0                  # px a frame: above this the error is masked and the window leaves the line
SCALE_STEP = 0.03              # relative growth in one frame above which a translation estimate is not trusted
MIN_CONF = 12.0                # correlation peak over the field's spread: below it the shift is a guess
CONF_REF = 25.0                # a line whose median peak is under this is judged against thresholds raised by
                               #     CONF_REF/conf: the estimator's own noise grows as the texture it reads shrinks.
                               #     Measured on the Agent HUD film: the one line under it is a lone 12px glyph
                               #     (conf 18) that read 0.21, 0.12 and 0.155px across three renders of fixes whose
                               #     other 30 lines all read 0.02-0.06 — noise, where the old render's 0.50 was not
GLIDE_MIN_OPACITY = 0.5        # fainter than this the line is arriving, not read
OPACITY_STEP = 0.06            # an opacity change larger than this in one frame is a fade or a seam, not a move
PAD = 8                        # px of margin round a line's box in the correlation window
SMOOTH_PAIRS = 9               # the --clip path's smoothing span (pairs)
DETREND_PAIRS = 9              # the span of the slow error taken out before judging (pairs): longer than a step's
                               #     period at any crawl a staircase shows at, so the steps stay in the residual
MAX_WIN = 640                  # px: a wider line is measured on its first MAX_WIN px (FFT cost, and a wide box
                               #     holds more than one layout run)
# EVERY px THRESHOLD ABOVE IS STATED AT A 1080 px SHORT SIDE — the size every renderer here delivers at every aspect
# (1920x1080, 1080x1920, 1080x1080, 1440x1080). What a viewer sees is a fraction of the picture, so a clip of another
# size is judged against the thresholds scaled by its short side over REF_SHORT (frame_scale); below MIN_SCALE the
# estimator's own floor (~0.06 px on the controls) would sit at the threshold, so the scale stops there and says so.
REF_SHORT = 1080
MIN_SCALE = 0.5
# A WINDOW MUST HOLD THE LINE, NOT THE GRAIN. On a dithered dark film a line can sit under the film's own static ±2
# dither: the correlation then locks onto the dither — which does not move — and reads "still" with a confident
# peak, and the detrend takes the constant error out: a line nobody can see measured CLEAN (found by the ink-18 control:
# no text at all, 29 pairs, clean). A window whose band-passed edges reach no more than MIN_EDGE grey levels (99th
# percentile) is skipped as too faint, and said so. Measured: the dither's own grain reads 1.1; type 4 grey levels
# over its ground reads 2.35 and is measured; 2 levels reads 1.5 and is not.
MIN_EDGE = 2.0
# A LINE WHOSE PIXELS DO NOT FOLLOW ITS GEOMETRY. The census says it travelled; the window's content did not (or went
# elsewhere). A frozen layer, an opaque overlay the census does not list, or a census of another render — each is
# worth a look and none of them is "clean" (the detrend would remove exactly this). Judged over a run of at least
# JIT_WINDOW pairs that truly travels FOLLOW_MIN_PX: a WARN when the measured travel is off by more than FOLLOW_REL.
FOLLOW_MIN_PX = 2.0
FOLLOW_REL = 0.5


def frame_scale(W, H):
    """The factor this frame's px thresholds are scaled by: its short side over REF_SHORT, floored at MIN_SCALE."""
    if not W or not H or W <= 0 or H <= 0:
        raise ValueError("frame_scale: a frame has a positive size (got %rx%r)" % (W, H))
    return max(MIN_SCALE, min(W, H) / float(REF_SHORT))


# ── DECODING ────────────────────────────────────────────────────────────────────────────────────────────────────
def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate", "-of", "json", path], capture_output=True, text=True)
    s = json.loads(r.stdout or "{}").get("streams") or []
    if not s:
        raise RuntimeError("%s: no video stream" % path)
    num, den = (s[0]["r_frame_rate"].split("/") + ["1"])[:2]
    return int(s[0]["width"]), int(s[0]["height"]), float(num) / float(den or 1)


def frames(path):
    """Yield (index, gray float32 HxW) for every frame of a video, or of a directory of PNGs in name order."""
    if os.path.isdir(path):
        from PIL import Image
        names = sorted((n for n in os.listdir(path) if n.lower().endswith(".png")),
                       key=lambda n: int("".join(c for c in n if c.isdigit()) or 0))
        for i, n in enumerate(names):
            yield i, np.asarray(Image.open(os.path.join(path, n)).convert("L"), dtype=np.float32)
        return
    W, H, _fps = probe(path)
    # -fps_mode passthrough: every decoded frame once, as stored. The default constant-rate output DUPLICATES a frame
    # where a stream's timestamps hiccup — measured on an HTML-tier film concatenated from per-scene clips with
    # `-c copy`: 360 frames stored, 361 decoded, and every pair after the seam compared with the wrong frame.
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-fps_mode", "passthrough", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    n, i = W * H, 0
    try:
        while True:
            buf = p.stdout.read(n)
            if len(buf) < n:
                break
            yield i, np.frombuffer(buf, np.uint8).reshape(H, W).astype(np.float32)
            i += 1
    finally:
        p.stdout.close()
        p.kill()
        p.wait()


# ── THE ESTIMATOR ───────────────────────────────────────────────────────────────────────────────────────────────
def _band(t):
    """Band-pass: drops the flat ground and its gradients (low) and the per-pixel dither/codec grain (high), keeps
    the glyph edges the eye tracks."""
    from scipy.ndimage import gaussian_filter
    a = gaussian_filter(t, 0.8)
    return a - gaussian_filter(a, 3.0)


def shift(a, b):
    """(dx, dy, conf): how far the content of window `b` sits from window `a`, sub-pixel.

    Two stages. The whole-pixel peak of the phase correlation of the band-passed, Hann-windowed windows (robust to a
    displacement of several pixels and to a change of brightness), then a Lucas-Kanade refinement: `b` is moved back
    by the current estimate (cubic spline) and the remaining displacement solved from the image gradients by least
    squares, three times. A peak fit alone (log-parabola on the correlation) is biased toward whole pixels — measured
    on the synthetic pan, 0.13px RMS against a true path known exactly, which is the size of the defect this gate
    exists to see; the refinement takes the same pan to the codec's floor."""
    from scipy.ndimage import shift as nshift
    h, w = a.shape
    win = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    ba, bb = _band(a), _band(b)
    A, B = np.fft.rfft2(ba * win), np.fft.rfft2(bb * win)
    R = np.conj(A) * B
    R /= np.abs(R) + 1e-3 * (np.abs(R).max() + 1e-9)
    c = np.fft.fftshift(np.fft.irfft2(R, s=(h, w)))
    iy, ix = np.unravel_index(int(np.argmax(c)), c.shape)
    conf = float(c[iy, ix]) / (float(c.std()) + 1e-9)
    dx, dy = float(ix - w // 2), float(iy - h // 2)
    gy, gx = np.gradient(ba)
    wgt = win
    m = 4                                                # the margin a spline shift fills by extrapolation
    core = np.zeros_like(win)
    core[m:h - m, m:w - m] = 1
    wgt = win * core
    Sxx, Syy, Sxy = (wgt * gx * gx).sum(), (wgt * gy * gy).sum(), (wgt * gx * gy).sum()
    det = Sxx * Syy - Sxy * Sxy
    if det <= 1e-9 * max(1.0, Sxx * Syy):
        return dx, dy, conf
    for _ in range(4):
        r = nshift(bb, (-dy, -dx), order=3, mode="nearest") - ba
        # b(x) = a(x - d)  =>  b moved back by the estimate leaves r ~ -grad(a) . e, e the estimate's error
        bx, by = -(wgt * gx * r).sum(), -(wgt * gy * r).sum()
        ex, ey = (Syy * bx - Sxy * by) / det, (Sxx * by - Sxy * bx) / det
        dx, dy = dx + ex, dy + ey
        if abs(ex) < 1e-3 and abs(ey) < 1e-3:
            break
    return dx, dy, conf


def aligned_change(a, b, dx, dy):
    """The change between two windows once `b` is moved back by (dx, dy), over the edge energy of `a` — 0 for the
    same drawing moved, large for a drawing re-rasterised."""
    from scipy.ndimage import shift as nshift
    ba, bb = _band(a), _band(b)
    bb = nshift(bb, (-dy, -dx), order=3, mode="nearest")
    m = 3
    ba, bb = ba[m:-m, m:-m], bb[m:-m, m:-m]
    # a FADE is not a re-raster: the line dimming under an overlay (the film's closing fade, a vignette breathing)
    # scales its edges without redrawing them, so the comparison is made after the best gain
    g = float((ba * bb).sum()) / (float((ba * ba).sum()) + 1e-6)
    e = float(np.abs(ba).mean()) * max(abs(g), 1e-3) + 1e-6
    return float(np.abs(bb - g * ba).mean()) / e


GLYPH_MARGIN = 2               # px round the census box kept as the glyph's own pixels in glyph_change
GLYPH_INK = 0.3                # a pixel is the glyph's ink when its edge reaches this share of the box's 99th pct
GLYPH_MIN_INK = 8              # fewer ink pixels than this and the glyph cannot be read on its own


def glyph_change(a, b, dx, dy, box):
    """aligned_change measured on the TYPE ITSELF: the glyph's own ink inside its census box, after everything outside
    the box (+GLYPH_MARGIN) has been replaced — in both frames — by the median of the box's own border. None when the
    box holds too little ink to read alone (the caller then uses aligned_change on the whole window).

    WHY. A shimmer is the type re-rasterised in place; the padded window also holds whatever is drawn round the type,
    and a STATIC label over MOVING content read as a shimmer. Validation film A: ObjectStage's numbered dots '2' '3'
    '4' sit on the escapement, and each time the lever snapped bank to bank the parts round the dot jumped — the
    window measured 0.87-2.08 of the dot's edge energy on those pairs, a median of 0.19-0.45 (ERROR) while the digit
    did not change at all (looked: the strips under film_work/batch5/gates/shimmer). Cutting the measure to the box
    is not enough — the band-pass (a 3 px Gaussian) carries a dark-to-light jump 9 px away into the box: 0.18-0.27 on
    the same pairs. Isolating the box first leaves 0.03-0.13, while the synthetic re-raster controls read the same as
    before (Latin 0.216, CJK 0.439, a lone digit 0.221: the change is ON the glyph, so the cut keeps all of it)."""
    from scipy.ndimage import binary_dilation, shift as nshift
    x0, y0, x1, y1 = box
    h, w = a.shape
    X0, Y0 = max(0, x0 - GLYPH_MARGIN), max(0, y0 - GLYPH_MARGIN)
    X1, Y1 = min(w, x1 + GLYPH_MARGIN), min(h, y1 + GLYPH_MARGIN)
    if X1 - X0 < 3 or Y1 - Y0 < 3:
        return None
    keep = np.zeros(a.shape, bool)
    keep[Y0:Y1, X0:X1] = True
    inner = np.zeros(a.shape, bool)
    inner[max(0, y0):min(h, y1), max(0, x0):min(w, x1)] = True
    if not inner.any():
        return None

    def isolate(img):
        rim = np.concatenate([img[Y0, X0:X1], img[Y1 - 1, X0:X1], img[Y0:Y1, X0], img[Y0:Y1, X1 - 1]])
        out = np.full(img.shape, float(np.median(rim)), np.float32)
        out[keep] = img[keep]
        return out
    ba = _band(isolate(a))
    bb = _band(isolate(nshift(b, (-dy, -dx), order=3, mode="nearest")))
    mag = np.maximum(np.abs(ba), np.abs(bb))
    top = float(np.percentile(np.abs(ba[inner]), 99))
    if top < MIN_EDGE:
        return None                                      # no glyph edge in the box above the grain (E19)
    ink = inner & (mag >= GLYPH_INK * top)
    ink = binary_dilation(ink, iterations=1) & inner
    if int(ink.sum()) < GLYPH_MIN_INK:
        return None
    g = float((ba[ink] * bb[ink]).sum()) / (float((ba[ink] ** 2).sum()) + 1e-6)
    e = float(np.abs(ba[ink]).mean()) * max(abs(g), 1e-3) + 1e-6
    return float(np.abs(bb - g * ba)[ink].mean()) / e


# ── THE CENSUS: where each line truly is ───────────────────────────────────────────────────────────────────────
def load_census(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        kept = json.load(fh)
    return {int(f): v for f, v in kept["frames"].items()}


def film_census(out_dir):
    """Render the film's census (every frame, no picture) exactly as text_safe_qa --sync does."""
    import render_remotion as rr
    import text_safe_qa as tq
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    props, _slides = rr.film_props(out_dir, board)
    res, segs, total = tq.film_census(out_dir, props)
    why = tq._glide_measured(res, total)
    if why:
        raise RuntimeError("the census did not measure the film: %s" % why)
    return res["frames"], segs


def seam_frames_of(scenes):
    """{frame} the Film's seams own: the `tr` frames on which two beats are drawn at once (Film.tsx's TransitionSeries,
    modelled exactly by remotion_segments.timeline). A beat that continues a stage run is joined to the one before it
    and has no seam. The HTML tier takes its scene-edge transitions out the same way (jitter_html)."""
    import remotion_segments as _rs
    import stage_runs as _sr
    tr = _rs.seam_frames()
    segs, _total = _rs.timeline(scenes, tr)
    joined = _sr.joined_flags(scenes)
    out = set()
    for k in range(1, len(segs)):
        if not joined[k]:
            out.update(range(segs[k][0], segs[k][0] + tr))
    return out


def film_seams(out_dir):
    """seam_frames_of the board AS IT IS NOW — the board the census was rendered from (a census of another render is
    refused later, by frame count). No renders: film_props builds the props and reads the beats' durations."""
    import render_remotion as rr
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    props, _slides = rr.film_props(out_dir, board)
    return seam_frames_of(props["scenes"])


def _box(ln):
    return float(ln["x"]), float(ln["y"]), float(ln["w"]), float(ln["h"])


SEAM_WHY = "inside a seam between beats (two beats drawn at once: the dissolve changes every window)"


def pairs_from_census(census, W, H, seams=None):
    """{f: [(key, text, box0, box1, flags)]} — every line judged between frame f and f+1, and {reason: count} of
    every line-pair that is NOT judged. `seams` is the set of frames a seam owns (seam_frames_of): a pair touching
    one is not judged. On a seam the beat being left stays OPAQUE under the arriving one (E15), so its lines pass
    every opacity test while the arriving picture dissolves over their windows — validation film A's three
    'shimmer' errors at frame 449 were TrainSlab's notes under the 2->3 dissolve (frames 446-457)."""
    fast = FAST_PX * frame_scale(W, H)
    skip = {}
    out = {}
    seams = seams or ()

    def no(why):
        skip[why] = skip.get(why, 0) + 1
    for f in sorted(census):
        nxt = census.get(f + 1)
        if nxt is None:
            continue
        if f in seams or (f + 1) in seams:
            for ln in census[f].get("lines") or []:
                if "x" in ln:
                    no(SEAM_WHY)
            continue
        b = {ln["k"]: ln for ln in (nxt.get("lines") or []) if "x" in ln}
        here = [ln for ln in (census[f].get("lines") or []) if "x" in ln]
        moves = {}
        for ln in here:
            if ln["k"] in b:
                x0, y0, w0, h0 = _box(ln)
                x1, y1, w1, h1 = _box(b[ln["k"]])
                moves[ln["k"]] = ((x1 + w1 / 2) - (x0 + w0 / 2), (y1 + h1 / 2) - (y0 + h0 / 2))
        for ln in here:
            k = ln["k"]
            if ln.get("g"):
                no("kinetic glyphs (judged glyph by glyph by text_safe_qa --glide)")
                continue
            if "d" in (ln.get("fl") or ""):
                # the census grants `d` only to type the author marked `data-distort` that is drawn under a spatial
                # filter (runtime/textSafe.tsx): a displacement warp moves the glyphs off their geometry on purpose
                no("deliberately distorted (data-distort under a filter: the author's warp, not a tremble)")
                continue
            if k not in b:
                no("gone on the next frame")
                continue
            l1 = b[k]
            o0, o1 = float(ln.get("o", 1)), float(l1.get("o", 1))
            if min(o0, o1) < GLIDE_MIN_OPACITY:
                no("fainter than %.2f" % GLIDE_MIN_OPACITY)
                continue
            if abs(o1 - o0) > OPACITY_STEP:
                no("fading (opacity step > %.2f)" % OPACITY_STEP)
                continue
            if (ln.get("t") or "") != (l1.get("t") or ""):
                no("text changed")
                continue
            if float(ln.get("v", 1)) < 0.98 or float(l1.get("v", 1)) < 0.98:
                no("partly clipped or off frame")
                continue
            x0, y0, w0, h0 = _box(ln)
            x1, y1, w1, h1 = _box(l1)
            if min(w0, h0, w1, h1) < 4:
                no("too small to measure")
                continue
            if x0 < 1 or y0 < 1 or x0 + w0 > W - 1 or y0 + h0 > H - 1:
                no("partly clipped or off frame")
                continue
            mx, my = moves[k]
            if max(abs(mx), abs(my)) > fast:
                no("faster than %.1fpx a frame" % fast)
                continue
            if abs(w1 / w0 - 1) > SCALE_STEP or abs(h1 / h0 - 1) > SCALE_STEP:
                no("growing faster than %d%% a frame" % round(SCALE_STEP * 100))
                continue
            out.setdefault(f, []).append((k, ln.get("t") or "", (x0, y0, w0, h0), (x1, y1, w1, h1),
                                          ln.get("fl") or "", ln.get("b"), moves))
    return out, skip


def _window(b0, b1, W, H):
    x0 = min(b0[0], b1[0]) - PAD
    y0 = min(b0[1], b1[1]) - PAD
    x1 = max(b0[0] + b0[2], b1[0] + b1[2]) + PAD
    y1 = max(b0[1] + b0[3], b1[1] + b1[3]) + PAD
    x1 = min(x1, x0 + MAX_WIN)
    X0, Y0 = max(0, int(np.floor(x0))), max(0, int(np.floor(y0)))
    X1, Y1 = min(W, int(np.ceil(x1))), min(H, int(np.ceil(y1)))
    return X0, Y0, X1, Y1


def _crowded(win, key, f, census, moves, mx, my):
    """Another line sharing the window and moving differently: the window would measure a mixture."""
    X0, Y0, X1, Y1 = win
    for ln in census[f].get("lines") or []:
        if ln["k"] == key or "x" not in ln or float(ln.get("o", 1)) < 0.15:
            continue
        x, y, w, h = _box(ln)
        if x + w <= X0 or x >= X1 or y + h <= Y0 or y >= Y1:
            continue
        ox, oy = moves.get(ln["k"], (None, None))
        if ox is None or abs(ox - mx) > 0.05 or abs(oy - my) > 0.05:
            return True
    return False


def measure_census(video, census, seams=None):
    """Per line, the track of [(f, true dx, true dy, measured dx, measured dy, conf, change)] — and the skip table.
    `seams`: the frames a film's seams own (seam_frames_of), never judged."""
    W, H, _fps = probe(video) if not os.path.isdir(video) else (None, None, None)
    tracks, skip, meta = {}, {}, {}
    beat_of = {}                     # DOM path -> the beat its first track belongs to
    todo = None
    prev = None
    last = -1
    for i, fr in frames(video):
        if todo is None:
            H, W = fr.shape
            todo, skip = pairs_from_census(census, W, H, seams)
        if prev is not None and (i - 1) in todo:
            for key, text, b0, b1, fl, beat, moves in todo[i - 1]:
                win = _window(b0, b1, W, H)
                mx, my = moves[key]
                if _crowded(win, key, i - 1, census, moves, mx, my):
                    skip["another line moving differently shares the window"] = \
                        skip.get("another line moving differently shares the window", 0) + 1
                    continue
                X0, Y0, X1, Y1 = win
                a, b = prev[Y0:Y1, X0:X1], fr[Y0:Y1, X0:X1]
                if a.shape[0] < 8 or a.shape[1] < 8:
                    continue
                # WHAT THE WINDOW SHOULD SEE MOVE: the displacement of the point at the window's centre, the line's
                # box carried from b0 to b1 (it may grow). The box centre's own motion is wrong for a line growing
                # under a push when the window is cut to MAX_WIN: measured on a probe's pull, a smooth 1px "error"
                # that was the left end of a long line moving differently from its middle.
                px, py = (X0 + X1) / 2.0, (Y0 + Y1) / 2.0
                c0x, c0y = b0[0] + b0[2] / 2, b0[1] + b0[3] / 2
                c1x, c1y = b1[0] + b1[2] / 2, b1[1] + b1[3] / 2
                mx = c1x + (px - c0x) * (b1[2] / b0[2]) - px
                my = c1y + (py - c0y) * (b1[3] / b0[3]) - py
                if float(np.percentile(np.abs(_band(a)), 99)) < MIN_EDGE:
                    why = "too faint in the pixels (edges under %.0f grey levels: the grain, not the type)" % MIN_EDGE
                    skip[why] = skip.get(why, 0) + 1
                    continue
                dx, dy, conf = (float(v) for v in shift(a, b))
                if conf < MIN_CONF:
                    skip["correlation too weak (conf < %.0f)" % MIN_CONF] = \
                        skip.get("correlation too weak (conf < %.0f)" % MIN_CONF, 0) + 1
                    continue
                ch, wide_here = None, False
                if max(abs(mx), abs(my)) < STILL_PX * frame_scale(W, H):
                    # the line's own box in the window (both frames' boxes: a still line's are the same)
                    gb = (int(np.floor(min(b0[0], b1[0]))) - X0, int(np.floor(min(b0[1], b1[1]))) - Y0,
                          int(np.ceil(max(b0[0] + b0[2], b1[0] + b1[2]))) - X0,
                          int(np.ceil(max(b0[1] + b0[3], b1[1] + b1[3]))) - Y0)
                    ch = glyph_change(a, b, dx, dy, gb)
                    if ch is None:
                        # too little ink to read alone: the whole window, which can only over-report (described)
                        wide_here = True
                        ch = aligned_change(a, b, dx, dy)
                # ONE TRACK PER LINE, NOT PER DOM PATH: two beats drawn by registers of the same shape give their
                # lines the same path, and keyed by path alone a beat-2 kicker's pop was reported under beat 4's
                # copy and beat number (meta took the LAST frame's). A path seen in a second beat starts its own track.
                first = beat_of.setdefault(key, beat)
                tkey = key if beat == first else "%s#b%s" % (key, beat)
                tracks.setdefault(tkey, []).append((i - 1, mx, my, dx, dy, conf, ch))
                wide = (meta.get(tkey) or {}).get("wide", 0) + (1 if wide_here else 0)
                meta[tkey] = dict({"t": text, "fl": fl, "b": beat}, **({"wide": wide} if wide else {}))
        prev = fr
        last = i
    # THE CENSUS AND THE PICTURE MUST BE THE SAME FILM. A census of the current board read against an out.mp4 from
    # an older render (or a different cut) would compare every line with somebody else's frame — garbage that can
    # read as clean. The frame counts must agree exactly.
    n_video = (last + 1) if todo is not None else 0
    n_census = (max(census) + 1) if census else 0
    if n_video != n_census:
        raise RuntimeError("the video has %d frames and the census %d — they are not the same render; re-render "
                           "(or pass the census of THIS video)" % (n_video, n_census))
    return tracks, skip, meta


# ── JUDGING ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _runs(track):
    """Split a track into runs of consecutive frames."""
    run = []
    for row in track:
        if run and row[0] != run[-1][0] + 1:
            yield run
            run = []
        run.append(row)
    if run:
        yield run


def _local_mean(e, n):
    """The centred running mean of each column over n samples (shrinking at the ends)."""
    out = np.empty_like(e)
    h = n // 2
    c = np.vstack([np.zeros((1, e.shape[1])), np.cumsum(e, axis=0)])
    for i in range(len(e)):
        a, b = max(0, i - h), min(len(e), i + h + 1)
        out[i] = (c[b] - c[a]) / (b - a)
    return out


def judge_track(track, scale=1.0):
    """{"rms", "a", "b", "pop", "pop_f", "shimmer", "pairs", "moving", "windowed", "popped"} for one line: the worst
    window's error RMS (px) and where it is, the largest single-pair error on a line that otherwise glides, the
    shimmer level — and how many of its pairs each test could JUDGE: `windowed` pairs sit in a run of at least
    JIT_WINDOW (the jitter window), `popped` in a run of at least 5 (the pop test's neighbourhood). A line seen for
    fewer consecutive pairs than that is tracked and not judged, and the coverage says so (a 1 s beat that fades in
    and out leaves a short run). `scale` is frame_scale() of the clip."""
    best = {"rms": 0.0, "a": None, "b": None, "pop": 0.0, "pop_f": None, "shimmer": 0.0, "shimmer_f": None,
            "pairs": len(track), "moving": 0, "windowed": 0, "popped": 0, "scale": scale,
            "conf": float(np.median([r[5] for r in track])) if track else None}
    for run in _runs(track):
        e = np.array([[r[3] - r[1], r[4] - r[2]] for r in run])
        if len(run) >= JIT_WINDOW:
            tt = np.array([sum(r[1] for r in run), sum(r[2] for r in run)])
            mt = np.array([sum(r[3] for r in run), sum(r[4] for r in run)])
            t_len = float(np.hypot(*tt))
            if t_len >= FOLLOW_MIN_PX * scale and float(np.hypot(*(mt - tt))) > FOLLOW_REL * t_len \
                    and (best.get("stall") is None or t_len > best["stall"][0]):
                best["stall"] = (t_len, float(np.hypot(*mt)), run[0][0], run[-1][0])
        # JITTER IS THE ERROR THAT CHANGES FROM FRAME TO FRAME. A slow, smooth bias — the estimator reading a growing
        # line's displacement a fraction off, the true path a hair off the box centre — moves the drawing smoothly
        # and no viewer sees it; a staircase, a wobble and a pop all live in the frame-to-frame part. So the error
        # is judged after its own local mean (DETREND_PAIRS) is taken out.
        e = e - _local_mean(e, DETREND_PAIRS)
        en = np.hypot(e[:, 0], e[:, 1])
        mv = np.array([max(abs(r[1]), abs(r[2])) >= STILL_PX * scale for r in run])
        best["moving"] += int(mv.sum())
        n = len(run)
        if n >= JIT_WINDOW:
            best["windowed"] += n
        if n >= 5:
            best["popped"] += n
        if n >= JIT_WINDOW:
            c = np.concatenate([[0.0], np.cumsum(en ** 2)])
            rms = np.sqrt((c[JIT_WINDOW:] - c[:-JIT_WINDOW]) / JIT_WINDOW)
            j = int(np.argmax(rms))
            if rms[j] > best["rms"]:
                best.update(rms=float(rms[j]), a=run[j][0], b=run[j + JIT_WINDOW - 1][0])
        # a POP: one pair far out on a line whose neighbours glide (median of the others is the line's floor)
        if n >= 5:
            for j in range(n):
                lo, hi = max(0, j - 4), min(n, j + 5)
                others = np.delete(en[lo:hi], j - lo)
                if en[j] >= POP_PX * scale and en[j] > 4 * (np.median(others) + 0.03) and en[j] > best["pop"]:
                    best.update(pop=float(en[j]), pop_f=run[j][0])
        ch = [(r[6], r[0]) for r in run if r[6] is not None and max(abs(r[3]), abs(r[4])) < 0.15 * scale]
        if len(ch) >= JIT_WINDOW:
            vals = np.array([v for v, _f in ch])
            # the median over a window: a line that keeps changing, not one odd frame (that is a POP)
            for j in range(len(vals) - JIT_WINDOW + 1):
                m = float(np.median(vals[j:j + JIT_WINDOW]))
                if m > best["shimmer"]:
                    best.update(shimmer=m, shimmer_f=ch[j][1])
    return best


def level_of(j, scale=None):
    """'error' | 'warn' | 'clean' — against the thresholds at this clip's frame_scale (the judgment's own, when it
    carries one)."""
    sc = scale if scale is not None else j.get("scale", 1.0)
    raise_ = max(1.0, CONF_REF / j["conf"]) if j.get("conf") else 1.0
    if j["rms"] >= JIT_RMS_ERROR * sc * raise_ or j["pop"] >= POP_PX * sc * raise_ or j["shimmer"] >= SHIMMER_REL:
        return "error"
    if j["rms"] >= JIT_RMS_WARN * sc or j.get("stall"):
        return "warn"
    return "clean"


def judge(tracks, meta, beat_of=None, label_of=None, scale=1.0):
    """[(level, line description, judgment)] worst first, one per line."""
    out = []
    for key, tr in tracks.items():
        j = judge_track(tr, scale)
        lv = level_of(j, scale)
        m = meta.get(key, {})
        out.append((lv, key, m, j))
    order = {"error": 0, "warn": 1, "clean": 2}
    return sorted(out, key=lambda r: (order[r[0]], -r[3]["rms"]))


def describe(m, j, fps=30.0, label=None):
    bits = []
    sc = j.get("scale", 1.0)
    if j["rms"] >= JIT_RMS_WARN * sc and j["a"] is not None:
        bits.append("trembles %.2fpx RMS against its own geometry over frames %d-%d (%.2f-%.2fs)"
                    % (j["rms"], j["a"], j["b"], j["a"] / fps, j["b"] / fps))
    if j["pop"] >= POP_PX * sc:
        bits.append("pops %.2fpx at frame %d (%.2fs)" % (j["pop"], j["pop_f"], j["pop_f"] / fps))
    if j.get("stall"):
        t_len, m_len, fa, fb = j["stall"]
        bits.append("does not follow its geometry: the census moves it %.1fpx over frames %d-%d, the pixels %.1fpx "
                    "(a frozen layer, an overlay the census does not list, or another render — look at it)"
                    % (t_len, fa, fb, m_len))
    if j["shimmer"] >= SHIMMER_REL:
        bits.append("shimmers in place (%.2f of its edge energy) from frame %d%s" % (
            j["shimmer"], j["shimmer_f"], " — read on its whole window on %d pair(s) (too little ink in its box to read "
            "the glyph alone): look whether the TYPE changes or only what is round it" % m["wide"]
            if m.get("wide") else ""))
    where = "composited layer" if "c" in (m.get("fl") or "") else "2D"
    if j.get("conf") and j["conf"] < CONF_REF:
        where += ", low texture: conf %.0f, thresholds x%.2f" % (j["conf"], CONF_REF / j["conf"])
    return "%s%r (%s): %s" % ((label + ": ") if label else "", (m.get("t") or "")[:40], where,
                              "; ".join(bits) or "glides (worst window %.2fpx RMS)" % j["rms"])


# ── THE FILM ────────────────────────────────────────────────────────────────────────────────────────────────────
def clip_size(path):
    """(W, H) of a video, or of the first PNG of a frame directory."""
    if os.path.isdir(path):
        from PIL import Image
        names = sorted(n for n in os.listdir(path) if n.lower().endswith(".png"))
        if not names:
            raise RuntimeError("%s holds no PNG frames" % path)
        return Image.open(os.path.join(path, names[0])).size
    W, H, _fps = probe(path)
    return W, H


def _seam_len():
    import remotion_segments as _rs
    return _rs.seam_frames()


def film_tier(out_dir):
    """'remotion' | 'html' | None — critic_ledger's (validate's) one definition."""
    import critic_ledger as cl
    return cl.film_tier(out_dir)


def scan_film(out_dir, video=None, census_path=None):
    """The judgment of a delivered film: its census (where every line of type truly is on every frame) read against
    out.mp4. A remotion film's census is the Film composition's own (text_safe_qa); an HTML-tier film's is built per
    scene by jitter_html (the page's DOM on the capture plan, the image slides' Ken Burns geometry)."""
    import time
    t0 = time.time()
    video = video or os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(video):
        raise RuntimeError("no %s to measure — render the film first; a gate with no picture has measured nothing"
                           % video)
    tier = "remotion" if census_path else film_tier(out_dir)
    extra_skip, scope, seams = {}, [], None
    if census_path:
        census = load_census(census_path)
    elif tier == "remotion":
        census, _segs = film_census(out_dir)
    if tier == "remotion":
        # A REMOTION FILM'S SEAMS ARE TAKEN OUT, AS THE HTML TIER'S ARE. Read off the board, so a kept census is
        # judged the same way; a board that cannot say where its seams are is not judged with them left in.
        try:
            seams = film_seams(out_dir)
        except Exception as e:                           # noqa: BLE001 - said, and the run stops: E9
            raise RuntimeError("could not place the film's seams (%s: %s) — without them every dissolve is judged "
                               "as type trembling" % (type(e).__name__, e))
        scope.append("%d seam frame(s) taken out (%d seam(s) of %d frames: two beats drawn at once)"
                     % (len(seams), len(seams) // max(1, _seam_len()), _seam_len()))
    else:
        # the HTML tier, and a board with no authored page (supplied slides with Ken Burns, programmatic scenes):
        # render.py drew both, and jitter_html reads both
        import jitter_html
        census, extra_skip, scope = jitter_html.film_census(out_dir, video)
        tier = tier or "local (no authored page)"
    try:
        board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
        labels = ["scene %02d (%s)" % (s.get("index", i + 1), s.get("shot") or s.get("type") or "?")
                  for i, s in enumerate(board.get("slides", []))]
    except (OSError, ValueError):
        labels = None
    tracks, skip, meta = measure_census(video, census, seams)
    for why, n in extra_skip.items():
        skip[why] = skip.get(why, 0) + n
    W, H, fps = probe(video)
    sc = frame_scale(W, H)

    def label(m):
        b = m.get("b")
        if labels and b is not None and str(b).isdigit() and int(b) < len(labels):
            return labels[int(b)]
        return "film chrome" if b is None else "beat %s" % b
    lines = judge(tracks, meta, scale=sc)
    universe = sum(1 for f in census for ln in (census[f].get("lines") or []) if (f + 1) in census)
    universe += sum(extra_skip.values())
    measured = sum(len(t) for t in tracks.values())
    comp = sum(len(t) for k, t in tracks.items() if "c" in (meta.get(k, {}).get("fl") or ""))
    return {"lines": [(lv, describe(m, j, fps, label(m)), m, j, k) for lv, k, m, j in lines], "skip": skip,
            "universe": universe, "measured": measured, "composited": comp, "fps": fps, "tier": tier,
            "size": (W, H), "scale": sc, "scope": scope,
            "seconds": time.time() - t0, "tracks": tracks, "meta": meta}


def verdict(rep):
    """'FAIL' | 'UNMEASURED' | 'NOTHING TO JUDGE' | 'OK', and the exit code (1 | 2 | 0 | 0).

    NOTHING TO JUDGE is a census that read every frame and found no type on any of them — a measured absence, said in
    those words, not an OK. UNMEASURED is type the census found and the pixels could not judge: every line-pair skipped
    (a dithered dark film whose correlation is too weak to believe, type that only ever fades), or every tracked line
    seen for fewer consecutive pairs than any test needs. That is exit 2 — a gate that looked at nothing has not
    passed anything."""
    errors = [r for r in rep["lines"] if r[0] == "error"]
    if errors:
        return "FAIL", 1
    if not rep["universe"]:
        return "NOTHING TO JUDGE", 0
    judged = sum(r[3].get("popped", 0) for r in rep["lines"])
    if not rep["measured"] or not judged:
        return "UNMEASURED", 2
    return "OK", 0


def scope_lines(rep):
    """What this run measured, and what it did not and why — printed by every run (E4: a count is coverage)."""
    W, H = rep.get("size") or (0, 0)
    windowed = sum(r[3].get("windowed", 0) for r in rep["lines"])
    popped = sum(r[3].get("popped", 0) for r in rep["lines"])
    short = rep["measured"] - popped
    out = ["scope: MEASURED — %d of %d line-pairs of type (%s tier, %dx%d, thresholds x%.2f of the 1080p ones), "
           "%d of them inside a jitter window of %d pairs, %d within reach of the pop test, %d on composited/3D layers"
           % (rep["measured"], rep["universe"], rep.get("tier") or "?", W, H, rep.get("scale", 1.0), windowed,
              JIT_WINDOW, popped, rep["composited"])]
    if short > 0:
        out.append("scope: tracked but NOT JUDGED — %d pair(s) on lines seen for fewer than 5 consecutive pairs "
                   "(a 1 s beat that fades in and out leaves runs this short)" % short)
    out.append("scope: NOT MEASURED, by design — pictures and non-type motion (media_res_qa, shake_qa judge those); "
               "kinetic per-glyph type (text_safe_qa --glide); the line-pairs listed under coverage, each with why")
    out.extend("scope: " + x for x in rep.get("scope") or [])
    return out


def report(rep, out=sys.stdout):
    errors = [r for r in rep["lines"] if r[0] == "error"]
    warns = [r for r in rep["lines"] if r[0] == "warn"]
    for lv, text, *_ in errors:
        out.write("%s ERROR %s\n" % (TAG, text))
    for lv, text, *_ in warns:
        out.write("%s WARN  %s\n" % (TAG, text))
    out.write("%s coverage: %d of %d line-pairs measured (%d on composited/3D layers) · not judged:\n"
              % (TAG, rep["measured"], rep["universe"], rep["composited"]))
    for why, n in sorted(rep["skip"].items(), key=lambda kv: -kv[1]):
        out.write("    %6d  %s\n" % (n, why))
    for ln in scope_lines(rep):
        out.write("%s %s\n" % (TAG, ln))
    word, code = verdict(rep)
    out.write("%s %s  %d line(s) jitter, %d warn — %d lines tracked · %.0fs\n"
              % (TAG, word, len(errors), len(warns), len(rep["lines"]), rep["seconds"]))
    if word == "FAIL":
        # how big, and what to do when it is too small to see: the ANC film's seven findings (0.12-0.26 px) were
        # accepted by the user, and the waiver that delivers over them was named nowhere in this report
        sizes = [float(x) for _lv, text, *_ in errors for x in re.findall(r"([\d.]+)px RMS", text)]
        if sizes:
            out.write("%s worst %.2f px RMS. Fix it in the shot (runtime/glide, a still layer under the type) — or, when "
                      "the user has watched it and accepts it, waive it by name: meta.delivery_waivers {\"jitter_qa\": "
                      "\"<their words>\"} (deliver.py and critic_ledger --final honour it)\n" % (TAG, max(sizes)))
    if word == "UNMEASURED":
        out.write("%s NOT MEASURED — the film has type and none of it could be judged from the pixels (see coverage); "
                  "this is not a pass\n" % TAG)
    elif word == "NOTHING TO JUDGE":
        out.write("%s the census read every frame and found no type on any of them — nothing to tremble\n" % TAG)
    return code


# ── NO CENSUS: tiles ────────────────────────────────────────────────────────────────────────────────────────────
def tiles_of(fr, tw=None, th=None, keep=12, gap=0):
    """The `keep` most edge-dense tiles of a frame (x0, y0, x1, y1): where there is type, or something like it. The
    tile is 160x64 at a 1080 short side and scales with the frame (a line of type does)."""
    b = np.abs(_band(fr))
    H, W = fr.shape
    sc = frame_scale(W, H)
    tw, th = int(tw or round(160 * sc)), int(th or round(64 * sc))
    cand = []
    for y in range(0, H - th, th // 2):
        for x in range(0, W - tw, tw // 2):
            cand.append((float(b[y:y + th, x:x + tw].mean()), (x, y, x + tw, y + th)))
    cand.sort(key=lambda c: -c[0])
    out = []
    for e, t in cand:
        if all(t[2] + gap <= o[0] or t[0] >= o[2] + gap or t[3] + gap <= o[1] or t[1] >= o[3] + gap for o in out):
            out.append(t)
        if len(out) >= keep:
            break
    return out


def measure_clip(path, truth=None, keep=12):
    """Track the clip's edge-dense tiles (chosen on its first frame, followed by their own measured motion).
    `truth` is a census for the clip: then the error is against it, as for a film."""
    if truth is not None:
        tracks, skip, meta = measure_census(path, truth)
        return tracks, meta
    from scipy.signal import savgol_filter
    pos, raw, prev, sc = None, {}, None, 1.0
    for i, fr in frames(path):
        H, W = fr.shape
        if pos is None:
            sc = frame_scale(W, H)
            pos = {n: [float(t[0]), float(t[1]), t[2] - t[0], t[3] - t[1]] for n, t in enumerate(tiles_of(fr, keep=keep))}
        else:
            for n, (x, y, w, h) in pos.items():
                X0, Y0 = int(round(x)), int(round(y))
                if X0 < 0 or Y0 < 0 or X0 + w > W or Y0 + h > H:
                    continue
                dx, dy, conf = shift(prev[Y0:Y0 + h, X0:X0 + w], fr[Y0:Y0 + h, X0:X0 + w])
                if conf < MIN_CONF:
                    continue
                pos[n][0] += dx
                pos[n][1] += dy
                raw.setdefault(n, []).append((i - 1, dx, dy, conf,
                                              aligned_change(prev[Y0:Y0 + h, X0:X0 + w], fr[Y0:Y0 + h, X0:X0 + w], dx, dy)))
        prev = fr
    tracks, meta = {}, {}
    for n, rows in raw.items():
        for run in _runs([(r[0],) + r[1:] for r in rows]):
            if len(run) < SMOOTH_PAIRS:
                continue
            d = np.array([[r[1], r[2]] for r in run])
            sm = savgol_filter(d, SMOOTH_PAIRS, 2, axis=0)
            for r, s in zip(run, sm):
                still = max(abs(s[0]), abs(s[1])) < STILL_PX * sc
                tracks.setdefault("tile%d" % n, []).append((r[0], float(s[0]), float(s[1]), r[1], r[2], r[3],
                                                             r[4] if still else None))
        meta["tile%d" % n] = {"t": "tile %d" % n, "fl": ""}
    return tracks, meta


# ── CALIBRATION ────────────────────────────────────────────────────────────────────────────────────────────────
# THE CONTROLS ARE DRAWN AT THE DELIVERED SIZE. They were first drawn in a 640x360 frame — a third of the frame every
# threshold is stated in (E8): the estimator's own noise floor is in pixels, so a control drawn at 360p and a film at
# 1080p are not the same experiment. Now the frame is any W x H (1920x1080 by default; the tests also run 1080x1920
# and 1080x1080), the line is placed by FRACTIONS of the frame, and only the region the line can reach is resampled
# (a full-frame resample per frame at 1080p is what made the 1080p controls cost minutes).
LATIN_TEXT = "Spark 5h  92%  14:32"
CJK_TEXT = "当前会话 92% · 每周限制"
_LATIN_FONTS = ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
_CJK_FONTS = ("/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
              "/System/Library/Fonts/PingFang.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
              "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc")


def _font_for(text):
    cjk = any("\u3400" <= c <= "\u9fff" for c in text)
    for p in (_CJK_FONTS if cjk else _LATIN_FONTS):
        if os.path.exists(p):
            return p
    raise RuntimeError("no %s font found for the synthetic clips (looked in: %s)"
                       % ("CJK" if cjk else "Latin", ", ".join(_CJK_FONTS if cjk else _LATIN_FONTS)))


def synth(kind, path, n=60, W=1920, H=1080, seed=3, text=LATIN_TEXT, px=26, ink=235, ground=18):
    """A synthetic clip of type with a KNOWN true path, encoded the way the films are (x264 yuv420p, plus the film's
    ±2 static dither), and its census (the TRUE path). `text` may be Latin or CJK; `ink`/`ground` set the contrast (a
    dithered DARK film is ink 40 on ground 18). kinds:
      still     type that does not move
      pan       a 0.37 px/frame vertical crawl, placed exactly (the glide)
      push      a 0.25%/frame zoom about the line's centre, placed exactly
      snapped   the pan drawn at whole pixels — the staircase a snapped baseline makes
      wobble    the pan plus a ±0.2px alternation — back-and-forth inside a smooth move
      pop       the push as a LAYER does it: the type rasterised at a scale (whole pixels in the raster's own grid)
                and scaled by the compositor, the raster refreshed only every 4th frame — so the drawing jumps
                when it is refreshed
      shimmer   still type re-rasterised every frame, alternately sharp and through a half-resolution raster —
                the drawing changes in place while nothing moves"""
    from PIL import Image, ImageDraw, ImageFont
    from scipy.ndimage import map_coordinates, uniform_filter, zoom as nzoom
    if kind not in CAL_KINDS:
        raise ValueError("synth: unknown kind %r" % kind)
    rng = np.random.default_rng(seed)
    S = 8                                                   # the master's supersampling
    dither = rng.integers(-2, 3, size=(H, W)).astype(np.float32)
    # ONE master drawing of the line, S times finer than the frame and box-filtered over S, so a frame is a pure
    # resampling of it: any place and any scale is exact (PIL places glyphs on its own grid and sizes fonts in
    # whole units, which by themselves put a 0.1px error on every frame — the size of what is being measured)
    font = ImageFont.truetype(_font_for(text), px * S)
    bb = ImageDraw.Draw(Image.new("L", (8, 8))).textbbox((0, 0), text, font=font)
    mw, mh = bb[2] - bb[0] + 8 * S, bb[3] - bb[1] + 8 * S
    m = Image.new("L", (mw, mh), 0)
    ImageDraw.Draw(m).text((4 * S - bb[0], 4 * S - bb[1]), text, font=font, fill=255)
    master = uniform_filter(np.asarray(m, np.float32), S) * ((ink - ground) / 255.0)
    mcx, mcy = mw / 2.0, mh / 2.0
    tw, th = (bb[2] - bb[0]) / float(S), (bb[3] - bb[1]) / float(S)     # the line's own box at scale 1
    cx0, cy0 = float(round(W * 0.516)), float(round(H * 0.453))
    if tw * 1.2 + 40 > W or th * 1.2 + 0.37 * n + 40 > H:
        raise ValueError("synth: a %dpx line of %r does not fit a %dx%d frame" % (px, text, W, H))
    # the region the line can reach over the clip (pan, push, wobble, the pop's raster grid), with a margin
    hw, hh = tw * 0.6 * 1.2 + 24, th * 0.6 * 1.2 + 0.37 * n + 24
    X0, X1 = max(0, int(cx0 - hw)), min(W, int(cx0 + hw) + 1)
    Y0, Y1 = max(0, int(cy0 - hh)), min(H, int(cy0 + hh) + 1)
    ys, xs = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)

    def place(cx, cy, s):
        """The ROI with the line centred on (cx, cy) at scale s: each pixel's centre read off the master."""
        u = mcx + (xs + 0.5 - cx) * S / s - 0.5
        v = mcy + (ys + 0.5 - cy) * S / s - 0.5
        return float(ground) + map_coordinates(master, [v, u], order=1, cval=0.0)
    lines, raw = [], []
    for f in range(n):
        cx, cy, s = cx0, cy0, 1.0
        if kind in ("pan", "snapped", "wobble"):
            cy = cy0 + 0.37 * f
        if kind in ("push", "pop"):
            s = 1.0 + 0.0025 * f
        if kind == "wobble":
            a = place(cx, cy + 0.2 * (1 if f % 2 else -1), s)
        elif kind == "snapped":
            a = place(cx, float(np.round(cy)), s)
        elif kind == "pop":
            rs = 1.0 + 0.0025 * (f - f % 4)                 # the raster's scale, refreshed every 4th frame
            k = s / rs                                      # the compositor's remaining scale, about the centre
            r = place(cx0 + 0.31, float(np.round(cy0 * rs)) / rs, rs)   # whole pixels in the raster's own grid
            a = map_coordinates(r, [cy0 + (ys - cy0) / k - Y0, cx0 + (xs - cx0) / k - X0], order=1, mode="nearest")
        elif kind == "shimmer":
            a = place(cx, cy, s)
            if f % 2:
                a = nzoom(nzoom(a, 0.5, order=1), 2.0, order=1)
                a = np.pad(a, ((0, max(0, ys.shape[0] - a.shape[0])), (0, max(0, ys.shape[1] - a.shape[1]))),
                           mode="edge")[:ys.shape[0], :ys.shape[1]]
        else:
            a = place(cx, cy, s)
        fr = np.full((H, W), float(ground), np.float32)
        fr[Y0:Y1, X0:X1] = a
        raw.append(np.clip(fr + dither, 0, 255).astype(np.uint8))
        bw, bh = tw * s, th * s
        lines.append({"lines": [{"k": "/line", "t": text, "x": cx - bw / 2, "y": cy - bh / 2, "w": bw, "h": bh,
                                 "o": 1, "fl": "c"}]})
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "%dx%d" % (W, H),
                          "-r", "30", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", path],
                         stdin=subprocess.PIPE)
    for a in raw:
        p.stdin.write(a.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg could not encode the synthetic clip %s" % path)
    return {f: v for f, v in enumerate(lines)}


CAL_KINDS = ("still", "pan", "push", "snapped", "wobble", "pop", "shimmer")
CAL_BAD = ("snapped", "wobble", "pop", "shimmer")
# the frames the controls are drawn in: the three shapes the renderers deliver (every one 1080 on its short side)
CAL_FRAMES = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:3": (1440, 1080)}


def calibrate(work, aspect="16:9", text=LATIN_TEXT, ink=235, kinds=CAL_KINDS):
    """{kind: (level, judgment)} for the synthetic controls drawn at `aspect`."""
    os.makedirs(work, exist_ok=True)
    W, H = CAL_FRAMES[aspect]
    rows = {}
    for kind in kinds:
        path = os.path.join(work, "cal_%s_%s.mp4" % (aspect.replace(":", "x"), kind))
        census = synth(kind, path, W=W, H=H, text=text, ink=ink)
        tracks, _skip, meta = measure_census(path, census)
        sc = frame_scale(W, H)
        j = judge_track(tracks.get("/line", []), scale=sc)
        rows[kind] = (level_of(j, scale=sc), j)
    return rows


def main(argv):
    ap = argparse.ArgumentParser(prog="jitter_qa.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--census", help="a census kept by text_safe_qa --sync --census=PATH (else rendered here)")
    ap.add_argument("--video", help="measure this render instead of <out_dir>/out.mp4")
    ap.add_argument("--clip", help="any clip (mp4 or PNG directory); no film needed")
    ap.add_argument("--truth", help="with --clip: a census for the clip (json.gz)")
    ap.add_argument("--calibrate", action="store_true", help="the synthetic controls and their separation")
    ap.add_argument("--aspect", default="16:9", choices=sorted(CAL_FRAMES),
                    help="with --calibrate: the frame the controls are drawn in (default %(default)s)")
    ap.add_argument("--json", help="write the judgment (and every line's track) here")
    ap.add_argument("--work", help="where --calibrate writes its clips (default: a temp dir)")
    a = ap.parse_args(argv)
    if a.calibrate:
        import tempfile
        work = a.work or tempfile.mkdtemp(prefix="jitter_cal_")
        rows = calibrate(work, aspect=a.aspect)
        bad_ok = all(rows[k][0] == "error" for k in CAL_BAD)
        good_ok = all(rows[k][0] == "clean" for k in CAL_KINDS if k not in CAL_BAD)
        for k in CAL_KINDS:
            lv, j = rows[k]
            print("%s cal %s %-8s %-5s rms %.3fpx  pop %.2fpx  shimmer %.3f  (%d pairs)"
                  % (TAG, a.aspect, k, lv, j["rms"], j["pop"], j["shimmer"], j["pairs"]))
        print("%s calibration %s" % (TAG, "OK — every control on its side" if bad_ok and good_ok else "FAILED"))
        return 0 if bad_ok and good_ok else 1
    if a.clip:
        try:
            W, H = clip_size(a.clip)
            sc = frame_scale(W, H)
            truth = load_census(a.truth) if a.truth else None
            tracks, meta = measure_clip(a.clip, truth)
        except (RuntimeError, OSError, ValueError) as e:
            print("%s NOT MEASURED — %s" % (TAG, e))
            return 2
        lines = judge(tracks, meta, scale=sc)
        for lv, k, m, j in lines:
            print("%s %-5s %s" % (TAG, lv.upper(), describe(m, j)))
        print("%s scope: %s, %dx%d (thresholds x%.2f); %d track(s) — %s" % (
            TAG, "census truth" if truth is not None else "NO census: edge-dense tiles against their own smoothed "
            "motion (sees steps and wobble; would call a designed shake smooth)", W, H, sc, len(lines),
            "judged" if lines else "NOTHING was tracked: not a pass"))
        if not lines:
            return 2
        return 1 if any(lv == "error" for lv, *_ in lines) else 0
    if not a.out_dir:
        ap.error("an out_dir, --clip or --calibrate")
    out_dir = os.path.abspath(a.out_dir)
    try:
        rep = scan_film(out_dir, a.video, a.census)
    except (RuntimeError, OSError, ValueError) as e:
        print("%s NOT MEASURED — %s" % (TAG, e))
        print("%s scope: nothing was measured (exit 2 is not a pass)" % TAG)
        return 2
    code = report(rep)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"lines": [{"level": lv, "text": t, "key": k, "judgment": j} for lv, t, _m, j, k in rep["lines"]],
                       "tracks": rep["tracks"], "meta": rep["meta"], "skip": rep["skip"],
                       "verdict": verdict(rep)[0]}, fh, ensure_ascii=False)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
