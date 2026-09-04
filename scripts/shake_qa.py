#!/usr/bin/env python3
"""shake_qa — tell SHAKE apart from MOTION, which frame difference cannot.

    python3 scripts/shake_qa.py <out_dir|file.mp4>       # judge a rendered film
    python3 scripts/shake_qa.py <file.mp4> --verbose     # ...with the per-window trace

WHY THIS HAS TO EXIST BEFORE ANY MOTION WORK. `film_energy_qa` scores motion as the p75 of the mean absolute
frame difference. That number rises for a camera push, for a reveal — and just as happily for a frame
vibrating in place. It is the same statistic for the best and the worst thing a film can do with movement,
so a tier optimised against it can reintroduce shake and turn the gate GREENER while doing it. This repo has
made that mistake more than once; the camera is locked by default today precisely because the last fix had
no way to prove the difference. A locked camera is a floor on shake AND a ceiling on motion, and the ceiling
can only be raised safely once the floor is measured rather than assumed.

WHAT SEPARATES THEM, PHYSICALLY. Both are movement; the difference is where the movement GOES.

    a push / pan / drift   the frame travels. Displacement over a second is a smooth ramp: the path the
                           frame walks and the distance it ends up from where it started are nearly equal.
    shake                  the frame vibrates. It walks a long path and ends up where it began, reversing
                           direction many times a second.

So the discriminant is a RATIO, not a magnitude: `wander = path / net` over a short window. A locked frame
has no path and is silent. A one-second push walks 30 small steps in one direction — path == net, wander 1.
A vibrating frame walks the same total distance and returns — wander climbs without bound. Magnitude alone
cannot do this: a violent push and a gentle jitter can have identical frame differences.

WHAT IT MEASURES, AND WHAT IT DELIBERATELY DOES NOT. The displacement is the GLOBAL translation between
consecutive frames, by phase correlation with a sub-pixel peak fit. That choice is the other half of the
design: content moving INSIDE a still frame — a card sliding in, a bar growing, a field flowing — produces
no global translation, so it is invisible here. That is correct and intended. This instrument is about the
CAMERA. Raising motion by animating content is not something it should ever have an opinion on, and a gate
that objected to a reveal would be switched off within a week.

SEAMS. A cross-dissolve is not translation, but it does perturb the correlation peak. Windows are judged
independently and the verdict is a FRACTION of shaky windows, so a seam contaminates at most its own window
rather than the film's verdict. `--verbose` prints them so a surprising number can be read rather than
guessed at.
"""
import json
import os
import subprocess
import sys

# A window short enough that a real oscillation completes inside it, long enough that a smooth ramp has
# somewhere to go. At 30fps this is 15 samples.
WINDOW_SECONDS = 0.5
# Below this, the frame is not moving enough for the ratio to mean anything: two pixels of travel across half
# a second is a still frame plus codec noise, and dividing one small number by another manufactures verdicts.
MIN_PATH_PX = 1.2
# Peak height over the correlation field's own spread — HOW MUCH TO BELIEVE THE DISPLACEMENT.
#
# Calibrated on real renders. Every real film frame measured here sits far above it: the library's
# lowest-texture register (a minimal title card, two lines of type on a flat ground) runs a per-window
# median of 359 locked and 222 shaken, with a worst window of 69. Frames with nothing to lock onto run
# 24-38 and their "displacement" is whichever way the noise leaned. Below this line the answer is UNKNOWN,
# which the instrument reports as unjudged — a different thing from clean, and a different thing from shaky.
#
# THE BLIND SPOT THIS LEAVES, stated rather than hidden: a frame with genuinely no structure that genuinely
# shakes is reported as unjudged. Nothing in this library renders such a frame — the worst case measured 69
# — but a future all-black beat with no type would be invisible here.
MIN_PEAK_CONFIDENCE = 60.0
# Calibrated on controls (see `--calibrate`): a locked film and a smooth push sit at ~1.0-1.6; 1px of
# per-frame jitter measures 6+. The gap is wide, so the threshold does not have to be delicate.
WANDER_SHAKE = 2.6
# One shaky window in a long film is a seam or a decode artefact. A film that SHAKES does it continuously.
SHAKE_FRACTION_FAIL = 0.15
SAMPLE_FPS = 30
LONG_SIDE = 480


def probe_size(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height", "-of", "csv=p=0:s=x", path], capture_output=True, text=True)
    try:
        w, h = r.stdout.strip().split("x")[:2]
        return int(w), int(h)
    except Exception:
        return None


def _frames(path, fps=SAMPLE_FPS, long_side=LONG_SIDE):
    import numpy as np
    size = probe_size(path)
    if not size:
        return None
    W0, H0 = size
    if W0 >= H0:
        w, h = long_side, max(2, int(round(long_side * H0 / W0)) // 2 * 2)
    else:
        h, w = long_side, max(2, int(round(long_side * W0 / H0)) // 2 * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf",
                          "fps=%d,scale=%d:%d" % (fps, w, h), "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    n = len(raw) // (w * h)
    if n < 8:
        return None
    return np.frombuffer(raw[:n * w * h], dtype=np.uint8).reshape(n, h, w).astype(np.float64) / 255.0


def _shift(a, b, np):
    """Global translation from a to b, in pixels of the sampled frame, with a sub-pixel peak fit.

    Sub-pixel matters more than it sounds: the ugliest shake is the smallest. A frame trembling by half a
    pixel is deeply unpleasant to watch and rounds to zero on an integer-only peak, so the instrument would
    call the worst case perfectly clean.
    """
    h, w = a.shape
    # A window kills the wrap-around edge response, which otherwise puts a false peak at (0,0) and makes
    # everything look locked.
    win = np.outer(np.hanning(h), np.hanning(w))
    A = np.fft.rfft2(a * win)
    B = np.fft.rfft2(b * win)
    R = A * np.conj(B)
    m = np.abs(R)
    R = np.divide(R, m, out=np.zeros_like(R), where=m > 1e-12)
    r = np.fft.irfft2(R, s=a.shape)
    peak = np.unravel_index(np.argmax(r), r.shape)

    def refine(axis, i):
        n = r.shape[axis]
        prev = r[(i - 1) % n, peak[1]] if axis == 0 else r[peak[0], (i - 1) % n]
        nxt = r[(i + 1) % n, peak[1]] if axis == 0 else r[peak[0], (i + 1) % n]
        cur = r[peak]
        d = prev - 2 * cur + nxt
        off = 0.0 if abs(d) < 1e-12 else 0.5 * (prev - nxt) / d
        return i + max(-1.0, min(1.0, off))

    dy, dx = refine(0, peak[0]), refine(1, peak[1])
    if dy > h / 2:
        dy -= h
    if dx > w / 2:
        dx -= w
    # HOW MUCH TO BELIEVE IT. Phase correlation needs texture: on a nearly featureless frame the peak is
    # ambiguous and the "displacement" is whichever way the noise leaned. That is not a hypothetical here —
    # this library is full of minimal title cards on flat grounds, and a smooth synthetic gradient produced
    # a wander of 6.2 while travelling in a perfectly straight line. Confidence is the peak against the
    # field it stands in; a flat field means the answer is unknown, which is a different thing from zero.
    conf = float(r[peak] / (r.std() + 1e-12))
    return dx, dy, conf


def measure(path):
    """{windows, shaky, fraction, wander_p90, path_per_sec} or None when unmeasurable."""
    try:
        import numpy as np
    except ImportError:
        return None
    F = _frames(path)
    if F is None:
        return None
    steps = [_shift(F[i], F[i + 1], np) for i in range(len(F) - 1)]
    dx = np.array([s[0] for s in steps])
    dy = np.array([s[1] for s in steps])
    conf = np.array([s[2] for s in steps])
    step_len = np.hypot(dx, dy)
    # Cumulative position, so a window's NET displacement is the distance between its endpoints.
    px = np.concatenate([[0.0], np.cumsum(dx)])
    py = np.concatenate([[0.0], np.cumsum(dy)])
    n = int(round(WINDOW_SECONDS * SAMPLE_FPS))
    rows = []
    for a in range(0, len(step_len) - n + 1, n):
        b = a + n
        path_len = float(step_len[a:b].sum())
        net = float(np.hypot(px[b] - px[a], py[b] - py[a]))
        wander = path_len / max(net, 1e-6)
        sure = float(np.median(conf[a:b])) >= MIN_PEAK_CONFIDENCE
        moving = path_len >= MIN_PATH_PX
        judged = moving and sure
        rows.append({"t": round(a / SAMPLE_FPS, 2), "path": round(path_len, 2), "net": round(net, 2),
                     "conf": round(float(np.median(conf[a:b])), 1),
                     "wander": round(wander, 2) if judged else None,
                     "shaky": bool(judged and wander > WANDER_SHAKE)})
    judged = [r for r in rows if r["wander"] is not None]
    shaky = [r for r in rows if r["shaky"]]
    return {
        "windows": len(rows),
        "judged": len(judged),
        "shaky": len(shaky),
        "fraction": round(len(shaky) / max(1, len(rows)), 3),
        "wander_p90": round(float(np.percentile([r["wander"] for r in judged], 90)), 2) if judged else None,
        "path_per_sec": round(float(step_len.sum() / (len(step_len) / SAMPLE_FPS)), 2),
        "rows": rows,
    }


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: shake_qa.py <out_dir|file.mp4> [--verbose]")
        return 2
    target = argv[0]
    path = target if target.endswith(".mp4") else os.path.join(target, "out.mp4")
    if not os.path.exists(path):
        print("[shake_qa] no such film: %s" % path)
        return 2
    m = measure(path)
    if m is None:
        print("[shake_qa] UNMEASURABLE %s — needs numpy + ffmpeg and a film of at least 8 sampled frames"
              % path)
        return 2
    if "--verbose" in argv:
        for r in m["rows"]:
            print("  t=%5.1fs  path %6.2f  net %6.2f  wander %s%s"
                  % (r["t"], r["path"], r["net"], r["wander"], "   SHAKY" if r["shaky"] else ""))
    if "--json" in argv:
        print(json.dumps({k: v for k, v in m.items() if k != "rows"}, ensure_ascii=False))
    bad = m["fraction"] > SHAKE_FRACTION_FAIL
    print("[shake_qa] %s  %d/%d windows shake (%.0f%%, fail over %.0f%%) · %d judged · wander p90 %s · "
          "travel %.1f px/s" % ("SHAKE" if bad else "OK", m["shaky"], m["windows"], 100 * m["fraction"],
                                100 * SHAKE_FRACTION_FAIL, m["judged"], m["wander_p90"], m["path_per_sec"]))
    if bad:
        print("  The frame is walking a long path and ending up where it started — that is vibration, not a "
              "move. A camera move must TRAVEL: one direction, eased, over at least half a second.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
