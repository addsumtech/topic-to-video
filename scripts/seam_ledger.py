#!/usr/bin/env python3
"""seam_ledger — does each hard cut land on MOTION, or join two still frames? Measured on the delivered out.mp4.

    python3 scripts/seam_ledger.py <out_dir> [--json]

WHY THIS EXISTS. Every beat is held still for SEAM_FRAMES at both ends (runtime/motion useT) so a dissolve never runs
over a moving shot, and a hard cut inherited that hold: on the topic-to-video promo (2026-11-03) all 20 hard cuts of a
kinetic film joined two still frames, about six a side. The launch-film peers make the cut a moment of motion —
"nothing is allowed to sit still at a cut", with a seam ledger per film (skillry's velocity-matched sting). The cut
carry (runtime/cutCarry) moves a kinetic film's cuts; this measures that every cut the viewer sees actually moves.

WHAT IT MEASURES. The cut frames come from the render's own timeline (.remotion-props.json, laid out as Film.tsx lays
it: remotion_segments.timeline) — a seam the board marks `cut`, or an unmarked one on a DNA whose native seam is the
cut. For each: the mean frame-to-frame change (0..1 of full scale, the frames at 192 px) over the WINDOW steps before the
cut frame and the WINDOW after it. A side under STILL is still. Written to <out_dir>/_seam_ledger.json.

EXIT. 1 when a film that cuts hard by tempo (render_remotion.cut_carry_on) has more than MAX_STILL_SHARE of its hard
cuts still on BOTH sides; 0 otherwise (a calm film's rare cut may rest); 2 when it could not measure.
"""
import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# a side whose mean per-frame change (at 30 fps, 192 px wide) is under this reads as a held frame. Calibrated on the
# promo before the carry: its held cut sides measured <= 0.0004 (encoder noise and grain), its moving beats >= 0.002.
STILL = 0.001
MAX_STILL_SHARE = 0.25
# frames each side of the cut frame averaged: ~0.13 s at 30 fps, the span a held frame is SEEN to hold over. Two frames
# called a cut still when its arriving beat was mid-entrance by its fourth frame (a counter fading in).
WINDOW = 4
_W = 192


def hard_cuts(props, tr):
    """[(scene index k, cut frame)] — every seam the viewer sees as a hard cut, where the picture changes."""
    import remotion_segments as rs
    scenes = props.get("scenes") or []
    ranges, _total = rs.timeline(scenes, tr)
    dna = props.get("dna") if isinstance(props.get("dna"), dict) else {}
    native_cut = ((dna or {}).get("seam") or {}).get("type") == "cut"
    import stage_runs as _sr
    joined = _sr.joined_flags(scenes)
    out = []
    for k in range(1, len(scenes)):
        if joined[k]:
            continue
        t = ((scenes[k].get("transitionIn") or {}).get("type"))
        if t == "cut" or (not t and native_cut and not (scenes[k - 1].get("camera") or {}).get("handoff")):
            out.append((k, ranges[k][0] + int(round(tr * 0.5))))
    return out


def _frames(mp4, n_max):
    """The film's frames, grey, _W wide, as float arrays (one decode)."""
    import numpy as np
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", mp4], capture_output=True, text=True).stdout.strip().split(",")
    w, h = int(probe[0]), int(probe[1])
    hh = int(round(_W * h / w / 2)) * 2
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp4, "-vf", "scale=%d:%d" % (_W, hh), "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.uint8)
    n = min(len(a) // (_W * hh), n_max)
    return a[: n * _W * hh].reshape(n, hh, _W).astype(np.float32) / 255.0


def measure(out_dir):
    import numpy as np
    import render_remotion as rr
    pj = os.path.join(out_dir, ".remotion-props.json")
    mp4 = os.path.join(out_dir, "out.mp4")
    if not (os.path.exists(pj) and os.path.exists(mp4)):
        raise FileNotFoundError("needs out.mp4 and its .remotion-props.json — render the film first")
    props = json.load(open(pj, encoding="utf-8"))
    cuts = hard_cuts(props, rr.SEAM_FRAMES)
    F = _frames(mp4, 10 ** 7)
    step = lambda i: float(np.abs(F[i] - F[i - 1]).mean()) if 1 <= i < len(F) else None
    rows = []
    for k, c in cuts:
        before = [step(c - i) for i in range(1, WINDOW + 1)]
        after = [step(c + i) for i in range(1, WINDOW + 1)]
        if None in before + after:
            continue
        b, a = sum(before) / WINDOW, sum(after) / WINDOW
        rows.append({"beat": k + 1, "cut_frame": c, "before": round(b, 5), "after": round(a, 5),
                     "still_before": b < STILL, "still_after": a < STILL, "still_both": b < STILL and a < STILL})
    meta = {}
    try:
        meta = (json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8")).get("meta") or {})
    except (OSError, ValueError):
        pass
    kinetic = rr.cut_carry_on(meta)
    still = sum(1 for r in rows if r["still_both"])
    return {"cuts": rows, "hard_cuts": len(rows), "still_both": still, "kinetic": kinetic,
            "share": round(still / len(rows), 3) if rows else 0.0}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        led = measure(a.out_dir)
    except Exception as e:                                # noqa: BLE001 — an unmeasured film is said, never passed
        print("[seam_ledger] NOT MEASURED — %s: %s" % (type(e).__name__, e))
        return 2
    with open(os.path.join(a.out_dir, "_seam_ledger.json"), "w", encoding="utf-8") as fh:
        json.dump(led, fh, indent=1)
    if a.json:
        print(json.dumps(led, indent=1))
    for r in led["cuts"]:
        if r["still_both"]:
            print("[seam_ledger] still cut into beat %d (frame %d): %.4f before, %.4f after" %
                  (r["beat"], r["cut_frame"], r["before"], r["after"]))
    bad = led["kinetic"] and led["hard_cuts"] and led["share"] > MAX_STILL_SHARE
    print("[seam_ledger] %s  %d of %d hard cut(s) join two still frames (%.0f%%)%s" % (
        "ERROR" if bad else "OK", led["still_both"], led["hard_cuts"], 100 * led["share"],
        " — a film that cuts hard by tempo carries its cuts (runtime/cutCarry, on with render_remotion.cut_carry_on)"
        if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
