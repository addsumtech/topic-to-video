#!/usr/bin/env python3
"""cut_rhythm_qa.py — the delivered film's CUT RHYTHM and SCALE RANGE, against published films (advisory).

WHY. The 2026-11-10 craft study decomposed 26 official brand films shot by shot (Apple, B&O, Nothing, Dyson, TE,
Linear, Arc, Raycast, Notion, Framer, OpenAI, Stripe, Kurzgesagt) and measured four of ours with the same instrument.
Two numbers separated them, nothing else did (tonal key, colourfulness and intra-shot change overlapped):
  * RHYTHM   p90/p10 of the shot lengths: ours 1.6-1.9 (one beat, one shot: a metronome); every reference film with
             cuts 2.7-37, most 4-8. Shots under 1.5 s: ours 0%; theirs 7-68%.
  * SCALE    p90-p10 of the foreground's share of the frame across shots: our explainers 0.18-0.26; Kurzgesagt 0.51,
             the product films 0.45-0.68 (they cut from a macro to the whole).
This reads the rendered out.mp4, not the plan: a planned coverage cut (runtime/coverage.tsx) the runtime refused is
not a cut, so each planned one is CONFIRMED in the pixels before it is counted.

    python scripts/cut_rhythm_qa.py <out_dir> [--json]

ADVISORY: it prints the film's numbers beside the reference band and never fails a render. Pacing is judgement; the
band says where published films sit, not where this one must.
"""
import json
import os
import subprocess
import sys
from io import BytesIO

FPS = 30
REF = {"rhythm_spread": (2.7, 8.0), "burst_share": (0.07, 0.68), "scale_variety": (0.45, 0.68)}
BURST_S = 1.5
CUT_DIFF = 6.0          # mean |Δluma| (0-255, 192 px) between the frames either side: above this a planned cut happened
BAND_IGNORE = 0.2       # the bottom share of the frame is not measured for scale (the burned caption lives there)


def _grab(mp4, t):
    import numpy as np
    from PIL import Image
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % max(0.0, t), "-i", mp4, "-frames:v", "1",
                        "-vf", "scale=192:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if r.returncode or not r.stdout:
        raise RuntimeError("could not read a frame at %.2fs of %s: %s" % (t, mp4, r.stderr.decode()[-200:]))
    return np.asarray(Image.open(BytesIO(r.stdout)).convert("RGB")).astype("float32")


def _luma(a):
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def _fg_share(a):
    """Foreground share of the frame above the caption band: pixels far from the most common (quantised) colour."""
    import numpy as np
    a = a[: int(a.shape[0] * (1 - BAND_IGNORE))]
    q = (a // 24).astype(int)
    codes = q[..., 0] * 10000 + q[..., 1] * 100 + q[..., 2]
    vals, cnt = np.unique(codes, return_counts=True)
    bg = a[codes == vals[cnt.argmax()]].mean(axis=0)
    return float((np.linalg.norm(a - bg, axis=-1) > 48).mean())


def shots(out_dir):
    """[(start s, end s)] of the delivered film: its beats (from the render record) cut further by every coverage step
    whose cut is confirmed in the pixels."""
    rec = json.load(open(os.path.join(out_dir, ".render_record.json"), encoding="utf-8"))
    props = json.load(open(os.path.join(out_dir, ".remotion-props.json"), encoding="utf-8"))
    segs = rec.get("segments")
    if not segs:
        raise RuntimeError("the render record has no per-beat segments (a whole render): re-render per beat")
    mp4 = os.path.join(out_dir, rec.get("out") or "out.mp4")
    bounds = [s[0] / float(FPS) for s in segs] + [(segs[-1][1] + 1) / float(FPS)]
    confirmed, planned = [], 0
    for (a, _b, _k), sc in zip(segs, props["scenes"]):
        for st in (sc.get("coverage") or [])[1:]:
            planned += 1
            t = a / float(FPS) + float(st["t"])
            before, after = _grab(mp4, t - 2.0 / FPS), _grab(mp4, t + 2.0 / FPS)
            if float(abs(_luma(before) - _luma(after)).mean()) > CUT_DIFF:
                confirmed.append(t)
    cuts = sorted(set(bounds) | set(confirmed))
    return mp4, list(zip(cuts, cuts[1:])), planned, len(confirmed)


def measure(out_dir):
    import numpy as np
    mp4, sh, planned, confirmed = shots(out_dir)
    lens = np.array([b - a for a, b in sh])
    shares = np.array([_fg_share(_grab(mp4, (a + b) / 2)) for a, b in sh])
    p10, p90 = np.percentile(lens, 10), np.percentile(lens, 90)
    return {"shots": len(sh), "median_shot": round(float(np.median(lens)), 2),
            "rhythm_spread": round(float(p90 / max(p10, 0.05)), 2), "burst_share": round(float((lens < BURST_S).mean()), 2),
            "scale_variety": round(float(np.percentile(shares, 90) - np.percentile(shares, 10)), 2),
            "coverage_cuts": {"planned": planned, "confirmed": confirmed}}


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__.strip().splitlines()[0])
        return 2
    r = measure(os.path.abspath(argv[0]))
    if "--json" in argv:
        print(json.dumps(r))
        return 0
    print("[cut_rhythm] %d shots, median %.2fs; coverage cuts %d of %d planned confirmed in the pixels"
          % (r["shots"], r["median_shot"], r["coverage_cuts"]["confirmed"], r["coverage_cuts"]["planned"]))
    for k, (lo, hi) in REF.items():
        v = r[k]
        where = "below" if v < lo else ("above" if v > hi else "inside")
        print("  %-14s %6.2f   published films %.2f-%.2f  (%s)" % (k, v, lo, hi, where))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
