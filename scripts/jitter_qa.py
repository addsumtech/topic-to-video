#!/usr/bin/env python3
"""jitter_qa — does the TYPE in a delivered film move the way its geometry says it moves? Read from the PIXELS.

    python3 scripts/jitter_qa.py <out_dir>                     # judge out.mp4 against the film's own census
    python3 scripts/jitter_qa.py <out_dir> --census=PATH.gz    # ...with a census kept by text_safe_qa --sync --census
    python3 scripts/jitter_qa.py <out_dir> --video=old.mp4     # ...a different render of the same film (a before)
    python3 scripts/jitter_qa.py --clip <file.mp4|png_dir> [--truth=census.json.gz]   # any clip; no census: tiles
    python3 scripts/jitter_qa.py --calibrate                   # the synthetic controls, with their separation

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
GLIDE_MIN_OPACITY = 0.5        # fainter than this the line is arriving, not read
OPACITY_STEP = 0.06            # an opacity change larger than this in one frame is a fade or a seam, not a move
PAD = 8                        # px of margin round a line's box in the correlation window
SMOOTH_PAIRS = 9               # the --clip path's smoothing span (pairs)
DETREND_PAIRS = 9              # the span of the slow error taken out before judging (pairs): longer than a step's
                               #     period at any crawl a staircase shows at, so the steps stay in the residual
MAX_WIN = 640                  # px: a wider line is measured on its first MAX_WIN px (FFT cost, and a wide box
                               #     holds more than one layout run)


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
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         stdout=subprocess.PIPE)
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


def _box(ln):
    return float(ln["x"]), float(ln["y"]), float(ln["w"]), float(ln["h"])


def pairs_from_census(census, W, H):
    """{f: [(key, text, box0, box1, flags)]} — every line judged between frame f and f+1, and {reason: count} of
    every line-pair that is NOT judged."""
    skip = {}
    out = {}

    def no(why):
        skip[why] = skip.get(why, 0) + 1
    for f in sorted(census):
        nxt = census.get(f + 1)
        if nxt is None:
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
            if max(abs(mx), abs(my)) > FAST_PX:
                no("faster than %.0fpx a frame" % FAST_PX)
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


def measure_census(video, census):
    """Per line, the track of [(f, true dx, true dy, measured dx, measured dy, conf, change)] — and the skip table."""
    W, H, _fps = probe(video) if not os.path.isdir(video) else (None, None, None)
    tracks, skip, meta = {}, {}, {}
    todo = None
    prev = None
    last = -1
    for i, fr in frames(video):
        if todo is None:
            H, W = fr.shape
            todo, skip = pairs_from_census(census, W, H)
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
                dx, dy, conf = (float(v) for v in shift(a, b))
                if conf < MIN_CONF:
                    skip["correlation too weak (conf < %.0f)" % MIN_CONF] = \
                        skip.get("correlation too weak (conf < %.0f)" % MIN_CONF, 0) + 1
                    continue
                ch = aligned_change(a, b, dx, dy) if max(abs(mx), abs(my)) < STILL_PX else None
                tracks.setdefault(key, []).append((i - 1, mx, my, dx, dy, conf, ch))
                meta[key] = {"t": text, "fl": fl, "b": beat}
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


def judge_track(track):
    """{"rms", "a", "b", "pop", "pop_f", "shimmer", "pairs", "moving"} for one line: the worst window's error RMS
    (px) and where it is, the largest single-pair error on a line that otherwise glides, and the shimmer level."""
    best = {"rms": 0.0, "a": None, "b": None, "pop": 0.0, "pop_f": None, "shimmer": 0.0, "shimmer_f": None,
            "pairs": len(track), "moving": 0}
    for run in _runs(track):
        e = np.array([[r[3] - r[1], r[4] - r[2]] for r in run])
        # JITTER IS THE ERROR THAT CHANGES FROM FRAME TO FRAME. A slow, smooth bias — the estimator reading a growing
        # line's displacement a fraction off, the true path a hair off the box centre — moves the drawing smoothly
        # and no viewer sees it; a staircase, a wobble and a pop all live in the frame-to-frame part. So the error
        # is judged after its own local mean (DETREND_PAIRS) is taken out.
        e = e - _local_mean(e, DETREND_PAIRS)
        en = np.hypot(e[:, 0], e[:, 1])
        mv = np.array([max(abs(r[1]), abs(r[2])) >= STILL_PX for r in run])
        best["moving"] += int(mv.sum())
        n = len(run)
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
                if en[j] >= POP_PX and en[j] > 4 * (np.median(others) + 0.03) and en[j] > best["pop"]:
                    best.update(pop=float(en[j]), pop_f=run[j][0])
        ch = [(r[6], r[0]) for r in run if r[6] is not None and max(abs(r[3]), abs(r[4])) < 0.15]
        if len(ch) >= JIT_WINDOW:
            vals = np.array([v for v, _f in ch])
            # the median over a window: a line that keeps changing, not one odd frame (that is a POP)
            for j in range(len(vals) - JIT_WINDOW + 1):
                m = float(np.median(vals[j:j + JIT_WINDOW]))
                if m > best["shimmer"]:
                    best.update(shimmer=m, shimmer_f=ch[j][1])
    return best


def level_of(j):
    if j["rms"] >= JIT_RMS_ERROR or j["pop"] >= POP_PX or j["shimmer"] >= SHIMMER_REL:
        return "error"
    if j["rms"] >= JIT_RMS_WARN:
        return "warn"
    return "clean"


def judge(tracks, meta, beat_of=None, label_of=None):
    """[(level, line description, judgment)] worst first, one per line."""
    out = []
    for key, tr in tracks.items():
        j = judge_track(tr)
        lv = level_of(j)
        m = meta.get(key, {})
        out.append((lv, key, m, j))
    order = {"error": 0, "warn": 1, "clean": 2}
    return sorted(out, key=lambda r: (order[r[0]], -r[3]["rms"]))


def describe(m, j, fps=30.0, label=None):
    bits = []
    if j["rms"] >= JIT_RMS_WARN and j["a"] is not None:
        bits.append("trembles %.2fpx RMS against its own geometry over frames %d-%d (%.2f-%.2fs)"
                    % (j["rms"], j["a"], j["b"], j["a"] / fps, j["b"] / fps))
    if j["pop"] >= POP_PX:
        bits.append("pops %.2fpx at frame %d (%.2fs)" % (j["pop"], j["pop_f"], j["pop_f"] / fps))
    if j["shimmer"] >= SHIMMER_REL:
        bits.append("shimmers in place (%.2f of its edge energy) from frame %d" % (j["shimmer"], j["shimmer_f"]))
    where = "composited layer" if "c" in (m.get("fl") or "") else "2D"
    return "%s%r (%s): %s" % ((label + ": ") if label else "", (m.get("t") or "")[:40], where,
                              "; ".join(bits) or "glides (worst window %.2fpx RMS)" % j["rms"])


# ── THE FILM ────────────────────────────────────────────────────────────────────────────────────────────────────
def scan_film(out_dir, video=None, census_path=None):
    import time
    t0 = time.time()
    video = video or os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(video):
        raise RuntimeError("no %s to measure" % video)
    segs, labels = None, None
    if census_path:
        census = load_census(census_path)
    else:
        census, segs = film_census(out_dir)
    try:
        board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
        labels = ["scene %02d (%s)" % (s.get("index", i + 1), s.get("shot") or "?")
                  for i, s in enumerate(board.get("slides", []))]
    except (OSError, ValueError):
        labels = None
    tracks, skip, meta = measure_census(video, census)
    _W, _H, fps = probe(video)

    def label(m):
        b = m.get("b")
        if labels and b is not None and str(b).isdigit() and int(b) < len(labels):
            return labels[int(b)]
        return "film chrome" if b is None else "beat %s" % b
    lines = judge(tracks, meta)
    universe = sum(1 for f in census for ln in (census[f].get("lines") or []) if (f + 1) in census)
    measured = sum(len(t) for t in tracks.values())
    comp = sum(len(t) for k, t in tracks.items() if "c" in (meta.get(k, {}).get("fl") or ""))
    return {"lines": [(lv, describe(m, j, fps, label(m)), m, j, k) for lv, k, m, j in lines], "skip": skip,
            "universe": universe, "measured": measured, "composited": comp, "fps": fps,
            "seconds": time.time() - t0, "tracks": tracks, "meta": meta}


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
    out.write("%s %s  %d line(s) jitter, %d warn — %d lines tracked · %.0fs\n"
              % (TAG, "FAIL" if errors else "OK", len(errors), len(warns), len(rep["lines"]), rep["seconds"]))
    return 1 if errors else 0


# ── NO CENSUS: tiles ────────────────────────────────────────────────────────────────────────────────────────────
def tiles_of(fr, tw=160, th=64, keep=12):
    """The `keep` most edge-dense tiles of a frame (x0, y0, x1, y1): where there is type, or something like it."""
    b = np.abs(_band(fr))
    H, W = fr.shape
    cand = []
    for y in range(0, H - th, th // 2):
        for x in range(0, W - tw, tw // 2):
            cand.append((float(b[y:y + th, x:x + tw].mean()), (x, y, x + tw, y + th)))
    cand.sort(key=lambda c: -c[0])
    out = []
    for e, t in cand:
        if all(t[2] <= o[0] or t[0] >= o[2] or t[3] <= o[1] or t[1] >= o[3] for o in out):
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
    pos, raw, prev = None, {}, None
    for i, fr in frames(path):
        H, W = fr.shape
        if pos is None:
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
                still = max(abs(s[0]), abs(s[1])) < STILL_PX
                tracks.setdefault("tile%d" % n, []).append((r[0], float(s[0]), float(s[1]), r[1], r[2], r[3],
                                                             r[4] if still else None))
        meta["tile%d" % n] = {"t": "tile %d" % n, "fl": ""}
    return tracks, meta


# ── CALIBRATION ────────────────────────────────────────────────────────────────────────────────────────────────
def synth(kind, path, n=60, W=640, H=360, seed=3):
    """A synthetic clip of type with a KNOWN true path, encoded the way the films are (x264 yuv420p, plus the film's
    ±2 static dither), and its census (the TRUE path). kinds:
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
    rng = np.random.default_rng(seed)
    S = 8                                                   # the master's supersampling
    font_path = next((p for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                                  "/System/Library/Fonts/Supplemental/Arial.ttf",
                                  "/Library/Fonts/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
                      if os.path.exists(p)), None)
    if font_path is None:
        raise RuntimeError("no font found for the synthetic clips")
    if kind not in CAL_KINDS:
        raise ValueError("synth: unknown kind %r" % kind)
    text = "Spark 5h  92%  14:32"
    dither = rng.integers(-2, 3, size=(H, W)).astype(np.float32)
    # ONE master drawing of the line, S times finer than the frame and box-filtered over S, so a frame is a pure
    # resampling of it: any place and any scale is exact (PIL places glyphs on its own grid and sizes fonts in
    # whole units, which by themselves put a 0.1px error on every frame — the size of what is being measured)
    font = ImageFont.truetype(font_path, 26 * S)
    bb = ImageDraw.Draw(Image.new("L", (8, 8))).textbbox((0, 0), text, font=font)
    mw, mh = bb[2] - bb[0] + 8 * S, bb[3] - bb[1] + 8 * S
    m = Image.new("L", (mw, mh), 0)
    ImageDraw.Draw(m).text((4 * S - bb[0], 4 * S - bb[1]), text, font=font, fill=217)
    master = uniform_filter(np.asarray(m, np.float32), S)
    mcx, mcy = mw / 2.0, mh / 2.0

    def place(cx, cy, s):
        """The line centred on (cx, cy) at scale s: each frame pixel's centre read off the master."""
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        u = mcx + (xs + 0.5 - cx) * S / s - 0.5
        v = mcy + (ys + 0.5 - cy) * S / s - 0.5
        return 18.0 + map_coordinates(master, [v, u], order=1, cval=0.0)
    lines, raw = [], []
    cx0, cy0 = 330.0, 163.0
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
            ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
            a = map_coordinates(r, [cy0 + (ys - cy0) / k, cx0 + (xs - cx0) / k], order=1, mode="nearest")
        elif kind == "shimmer":
            a = place(cx, cy, s)
            if f % 2:
                a = nzoom(nzoom(a, 0.5, order=1), 2.0, order=1)[:H, :W]
        else:
            a = place(cx, cy, s)
        raw.append(np.clip(a + dither, 0, 255).astype(np.uint8))
        bw, bh = 300 * s, 26 * s
        lines.append({"lines": [{"k": "/line", "t": text, "x": cx - bw / 2, "y": cy - bh / 2, "w": bw, "h": bh,
                                 "o": 1, "fl": "c"}]})
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "%dx%d" % (W, H),
                          "-r", "30", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", path],
                         stdin=subprocess.PIPE)
    for a in raw:
        p.stdin.write(a.tobytes())
    p.stdin.close()
    p.wait()
    return {f: v for f, v in enumerate(lines)}


CAL_KINDS = ("still", "pan", "push", "snapped", "wobble", "pop", "shimmer")
CAL_BAD = ("snapped", "wobble", "pop", "shimmer")


def calibrate(work):
    os.makedirs(work, exist_ok=True)
    rows = {}
    for kind in CAL_KINDS:
        path = os.path.join(work, "cal_%s.mp4" % kind)
        census = synth(kind, path)
        tracks, _skip, meta = measure_census(path, census)
        j = judge_track(tracks.get("/line", []))
        rows[kind] = (level_of(j), j)
    return rows


def main(argv):
    ap = argparse.ArgumentParser(prog="jitter_qa.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--census", help="a census kept by text_safe_qa --sync --census=PATH (else rendered here)")
    ap.add_argument("--video", help="measure this render instead of <out_dir>/out.mp4")
    ap.add_argument("--clip", help="any clip (mp4 or PNG directory); no film needed")
    ap.add_argument("--truth", help="with --clip: a census for the clip (json.gz)")
    ap.add_argument("--calibrate", action="store_true", help="the synthetic controls and their separation")
    ap.add_argument("--json", help="write the judgment (and every line's track) here")
    ap.add_argument("--work", help="where --calibrate writes its clips (default: a temp dir)")
    a = ap.parse_args(argv)
    if a.calibrate:
        import tempfile
        work = a.work or tempfile.mkdtemp(prefix="jitter_cal_")
        rows = calibrate(work)
        bad_ok = all(rows[k][0] == "error" for k in CAL_BAD)
        good_ok = all(rows[k][0] == "clean" for k in CAL_KINDS if k not in CAL_BAD)
        for k in CAL_KINDS:
            lv, j = rows[k]
            print("%s cal %-8s %-5s rms %.3fpx  pop %.2fpx  shimmer %.3f  (%d pairs)"
                  % (TAG, k, lv, j["rms"], j["pop"], j["shimmer"], j["pairs"]))
        print("%s calibration %s" % (TAG, "OK — every control on its side" if bad_ok and good_ok else "FAILED"))
        return 0 if bad_ok and good_ok else 1
    if a.clip:
        truth = None
        if a.truth:
            truth = load_census(a.truth)
        tracks, meta = measure_clip(a.clip, truth)
        lines = judge(tracks, meta)
        for lv, k, m, j in lines:
            print("%s %-5s %s" % (TAG, lv.upper(), describe(m, j)))
        return 1 if any(lv == "error" for lv, *_ in lines) else 0
    if not a.out_dir:
        ap.error("an out_dir, --clip or --calibrate")
    out_dir = os.path.abspath(a.out_dir)
    try:
        rep = scan_film(out_dir, a.video, a.census)
    except (RuntimeError, OSError, ValueError) as e:
        print("%s NOT MEASURED — %s" % (TAG, e))
        return 2
    code = report(rep)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"lines": [{"level": lv, "text": t, "key": k, "judgment": j} for lv, t, _m, j, k in rep["lines"]],
                       "tracks": rep["tracks"], "meta": rep["meta"], "skip": rep["skip"]}, fh, ensure_ascii=False)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
