#!/usr/bin/env python3
"""light_match_qa — a straight cut INSIDE one sequence that flips the light from warm to cool (advisory).

    python3 scripts/light_match_qa.py <film_dir> [--video=PATH] [--json]     # reads _plan.json and shot_plan.json

WHY (2026-11-24). A sequence keeps one light colour as it keeps one light direction (references/director-craft.md §3);
a change of temperature belongs at a seam. Measured on 28 delivered films (352 neighbouring shots inside a sequence):
tone, contrast and saturation jumped as often inside a sequence as across a seam, and the biggest jumps were design
(a dark brand card into the light lockup, light UI against dark 3D, noon against sunset). What the user called
jarring ("Yes, they jar") was only the KEY flipping warm <-> cool between neighbours: MRI's cool grey scanner into a
warm amber brain, job-hunt's sepia CV into the same CV under grey light, QR's blue-grey wall into a warm wood table.

Each shot (between the plan's cuts, 0.4 s or longer) is read at its settled frame (90 % of its span), the caption band
(bottom 20 %) left out. Its KEY is the median CIELAB b* (blue -, yellow +) of its near-neutral pixels (chroma < 12):
the colour the light gives to what has no colour of its own. A shot with under 5 % neutral pixels gives no reading.
Two neighbours inside one sequence (shot_plan.json's `sequence`, else timeline.json "seams") FLIP when one key is
>= +KEY_T and the other <= -KEY_T. Measured: the three cuts above at -4.4/+5.5, +6.9/-2.3, -4.9/+4.1; deliberate pairs mostly stay on one
side (a cream UI at +0.8 beside a warmer one at +9.8). A flip the story asks for (sunset after noon) is fine: the
warning says the flip is there, not that it is wrong. ADVISORY: exit 0 with WARN lines; 2 on a usage error or a missing
plan, sequences or video.
"""
import io
import json
import os
import subprocess
import sys

import numpy as np

import _common as _c

KEY_T = 2.0
SETTLE = 0.9
CAPTION = 0.8
NEUTRAL_C, NEUTRAL_MIN = 12.0, 0.05
MIN_SHOT = 0.4
_USAGE = "usage: light_match_qa.py <film_dir> [--video=PATH] [--json]"


def key(rgb):
    """Median b* of the near-neutral pixels of an RGB uint8 frame (caption band excluded), or None."""
    a = np.asarray(rgb, np.float32)[: int(rgb.shape[0] * CAPTION)] / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]], np.float32)
    xyz = lin @ m.T / np.array([0.9505, 1.0, 1.089], np.float32)
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    aa, bb = 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])
    neutral = np.hypot(aa, bb) < NEUTRAL_C
    return float(np.median(bb[neutral])) if neutral.mean() >= NEUTRAL_MIN else None


def flips(shots, seams):
    """shots: [(start, end, key)], seams: sequence boundaries in seconds -> the flipping neighbour pairs."""
    seq = lambda t: sum(1 for s in seams if s <= t + 0.05)   # noqa: E731
    out = []
    for (a0, a1, ka), (b0, b1, kb) in zip(shots, shots[1:]):
        if ka is None or kb is None or seq(a0) != seq(b0):
            continue
        if (ka >= KEY_T and kb <= -KEY_T) or (ka <= -KEY_T and kb >= KEY_T):
            out.append({"from": a0 + SETTLE * (a1 - a0), "to": b0 + SETTLE * (b1 - b0), "key_from": ka, "key_to": kb})
    return out


def sequence_seams(d):
    """Seconds where a new sequence starts: shot_plan.json's shots, where `sequence` changes (the plan the film was built
    to), else timeline.json "seams" (seconds or {"t": s}). The Airbnb film (2026-11-25) had to hand-write "seams" into
    its timeline for this check, though its shot plan already named every shot's sequence."""
    sp = os.path.join(d, "shot_plan.json")
    if os.path.isfile(sp):
        shots = json.load(open(sp, encoding="utf-8")).get("shots") or []
        if shots and all(isinstance(x.get("start"), (int, float)) and x.get("sequence") for x in shots):
            return [b["start"] for a, b in zip(shots, shots[1:]) if b["sequence"] != a["sequence"]]
    tp = os.path.join(d, "timeline.json")
    if not os.path.isfile(tp):
        raise ValueError("no sequences: shot_plan.json shots with start and sequence, or timeline.json seams")
    seams = [s["t"] if isinstance(s, dict) and "t" in s else s for s in json.load(open(tp, encoding="utf-8")).get("seams") or []]
    if not all(isinstance(s, (int, float)) for s in seams):
        raise ValueError("timeline.json seams must be seconds or {\"t\": seconds}, got %r" % seams[:3])
    return seams


def _frame(video, t):
    from PIL import Image
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1", "-vf", "scale=480:-2",
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    return np.asarray(Image.open(io.BytesIO(p.stdout)).convert("RGB"))


def judge(d, video=None):
    plan = json.load(open(os.path.join(d, "_plan.json"), encoding="utf-8"))
    seams = sequence_seams(d)
    fps = float(plan.get("fps", 30))
    video = video or os.path.join(d, plan.get("video", "final.mp4"))
    if not os.path.isfile(video):
        raise FileNotFoundError(video)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout)
    bounds = [0.0] + sorted(c / fps for c in plan.get("cuts") or []) + [dur]
    shots = [(a, b, key(_frame(video, min(a + SETTLE * (b - a), dur - 0.05))))
             for a, b in zip(bounds, bounds[1:]) if b - a >= MIN_SHOT]
    return flips(shots, seams), len(shots)


def main(argv):
    _c.refuse_unknown(argv, valued=("video",), switches=("json",), usage=_USAGE)
    video = _c.argflag(argv, "video")
    args = [a for a in argv if not a.startswith("--") and a != video]
    if len(args) != 1:
        print(_USAGE, file=sys.stderr)
        return 2
    try:
        found, n = judge(args[0], video)
    except (OSError, ValueError) as e:
        print("light_match_qa: %s" % e, file=sys.stderr)
        return 2
    if "--json" in argv:
        print(json.dumps({"flips": found, "shots": n}))
        return 0
    for f in found:
        print("WARN   %.1f s -> %.1f s: the light flips %s inside one sequence (key b* %+.1f -> %+.1f); keep one light "
              "colour per sequence and change it at a seam, unless the story asks for it"
              % (f["from"], f["to"], "warm to cool" if f["key_from"] > 0 else "cool to warm", f["key_from"], f["key_to"]))
    print("[light_match_qa] %d shot(s), %d warm/cool flip(s) inside a sequence" % (n, len(found)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
