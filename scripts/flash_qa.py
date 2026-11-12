#!/usr/bin/env python3
"""flash_qa — a frame that FLASHES: one or two frames unlike both neighbours, which agree with each other.

    python3 scripts/flash_qa.py <out_dir | film.mp4> [--json]

WHY. Measured 2026-11-01 on a Grok Bot film: a 3D slab built as stacked translateZ layers ~2 px apart re-sorted for
ONE frame when its face's content changed, and an edge layer covered the face — near-black at 107.4 s and 109.1 s,
grey at 96.3 s. The user saw "black flashes"; all 16 delivery gates were green, because every one of them reads a
frame, a beat's motion or a line of type, and none compares a frame with its neighbours.

THE RULE. The delivered file is decoded small and grey. A run of 1-2 frames is a FLASH when it differs from the frame
before it AND from the frame after it by more than DIFF (mean absolute grey levels), while those two neighbours agree
to within AGREE x that difference. A hard cut changes and stays changed (its neighbours disagree); a fade changes a
little each frame (no frame differs from both by DIFF): neither is a flash. Exit 1 on any flash, naming its time and,
on a remotion board, its beat.
"""
import json
import os
import subprocess
import sys

import numpy as np

W, H = 160, 90
DIFF = 6.0                 # grey levels, mean absolute: the 96.3 s grey flash measured 8.9, ordinary motion under 3
AGREE = 0.35               # the neighbours' own difference, relative to the flash's
MAX_RUN = 2


def _frames(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=%d:%d,format=gray" % (W, H),
                          "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    out = []
    while True:
        b = p.stdout.read(W * H)
        if len(b) < W * H:
            break
        out.append(np.frombuffer(b, np.uint8).astype(np.int16))
    if p.wait() != 0 or not out:
        raise SystemExit("flash_qa: could not decode %s" % path)
    return np.array(out)


def flashes(path):
    """[{frame, frames, t, before, after, across}] — every run of 1..MAX_RUN frames unlike both of its agreeing
    neighbours. `before`/`after` are the run's differences from its neighbours, `across` the neighbours' own."""
    fr = _frames(path)
    n = len(fr)

    def d(a, b):
        return float(np.abs(fr[a] - fr[b]).mean())

    found, i = [], 1
    while i < n - 1:
        hit = None
        for w in range(1, MAX_RUN + 1):
            if i + w >= n:
                break
            before, after, across = d(i - 1, i), d(i + w - 1, i + w), d(i - 1, i + w)
            inside = max((d(i + k, i + k + 1) for k in range(w - 1)), default=0.0)
            if min(before, after) > DIFF and across < AGREE * min(before, after) and inside < AGREE * min(before, after):
                hit = {"frame": i, "frames": w, "t": round(i / 30.0, 2), "before": round(before, 1),
                       "after": round(after, 1), "across": round(across, 1)}
                break
        if hit:
            found.append(hit)
            i += hit["frames"] + 1
        else:
            i += 1
    return found


EDGE = 24                  # frames at each end the film's intro/outro veil spans (Film.tsx: 16), with room
WASH = 40.0                # grey levels (mean) a veil may stand ABOVE the picture it fades from or into


def edge_washes(path=None, fr=None):
    """[{edge, frame, t, peak, picture}] — a film that ENTERS or LEAVES through a ground brighter than its picture.

    WorkBuddy, 2026-11-12: a light DNA, a dark first and last beat; the veil was the DNA's near-white, so the film faded
    in from white and out to white — a flash at both ends, but a 16-frame one, so the rule above (1-2 frames) never saw
    it. Fading a picture to or from black, or to its own ground, keeps the veil at or below it."""
    fr = fr if fr is not None else _frames(path)
    n = len(fr)
    if n < 3 * EDGE:
        return []
    y = [float(f.mean()) for f in fr]
    out = []
    pic_in = float(np.median(y[EDGE:EDGE + 6]))
    k = int(np.argmax(y[:EDGE]))
    if y[k] - pic_in > WASH:
        out.append({"edge": "in", "frame": k, "t": round(k / 30.0, 2), "peak": round(y[k], 1), "picture": round(pic_in, 1)})
    pic_out = float(np.median(y[n - EDGE - 6:n - EDGE]))
    k = n - EDGE + int(np.argmax(y[n - EDGE:]))
    if y[k] - pic_out > WASH:
        out.append({"edge": "out", "frame": k, "t": round(k / 30.0, 2), "peak": round(y[k], 1), "picture": round(pic_out, 1)})
    return out


def _beat_of(out_dir, frame):
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import render_remotion as rr
        import remotion_segments as rs
        board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
        if (board.get("meta") or {}).get("renderer") != "remotion":
            return None
        props, _ = rr.film_props(out_dir, board)
        spans, _ = rs.timeline(props["scenes"], rr.SEAM_FRAMES)
        for k, (a, b) in enumerate(spans, start=1):
            if a <= frame <= b:
                return "beat %d (%s)" % (k, board["slides"][k - 1].get("shot"))
    except Exception:            # a film without a board, or one this can't lay out: the time is still reported
        return None
    return None


_USAGE = "usage: flash_qa.py <out_dir | film.mp4> [--json]"


def main(argv):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _common as _c
    _c.refuse_unknown(argv, valued=(), switches=("json",), usage=_USAGE)
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(_USAGE)
        return 2
    target = args[0]
    out_dir = target if os.path.isdir(target) else None
    path = os.path.join(target, "out.mp4") if out_dir else target
    if not os.path.isfile(path):
        print("flash_qa: no film at %s" % path)
        return 2
    found = flashes(path)
    washes = edge_washes(path)
    if "--json" in argv:
        print(json.dumps(found + washes))
    for w in washes:
        print("[flash] ERROR the film %s through a ground brighter than its picture: grey %.0f at %.2fs (frame %d) against "
              "a picture of %.0f — a flash at its %s; the intro/outro veil should be the edge beat's own ground (or black)"
              % ("enters" if w["edge"] == "in" else "leaves", w["peak"], w["t"], w["frame"], w["picture"],
                 "start" if w["edge"] == "in" else "end"))
    found = found + washes
    for f in found:
        where = _beat_of(out_dir, f["frame"]) if out_dir else None
        print("[flash] ERROR %s%s frame(s) at %.2fs (frame %d) unlike both neighbours (%.1f / %.1f grey levels; the "
              "neighbours differ by %.1f) — a layer that drops out or re-sorts for a frame"
              % ((where + ": ") if where else "", f["frames"], f["t"], f["frame"], f["before"], f["after"], f["across"]))
    print("[flash] %s  %d flash(es) in %s" % ("FAIL" if found else "OK", len(found), os.path.basename(path)))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
