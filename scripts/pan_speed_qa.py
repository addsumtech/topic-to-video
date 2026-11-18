#!/usr/bin/env python3
"""pan_speed_qa — does the camera ever whip so fast that the picture strobes instead of moving?

    python3 scripts/pan_speed_qa.py <film_dir> [--limit 48] [--json]     # reads _plan.json "video" (final.mp4) and "cuts"

The whole frame's motion between consecutive frames, by phase correlation on a quarter-size picture (so a 77 px shift
is still inside what the correlation can see), in px a frame at the film's own width. Frames within 3 of a cut are
not judged (the cut itself is not a move). A run of SUSTAIN frames or more above `--limit` is a whip: at 30 fps the
eye sees separate pictures, and small type and fine texture judder (Grok Bot 2026-11-18: a follow-pan at up to 77 px a
frame; picture_glide judges smoothness, not speed, and read it as a glide). A planned whip seam is a cut, not a pan.
Exit 0 no whip, 1 a whip, 2 usage error or a missing video / plan.
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

LIMIT = 48.0      # px a frame at 1920 wide: the frame width crossed in 1.3 s
SUSTAIN = 6       # frames in a row
EDGE = 3          # frames either side of a cut not judged
_USAGE = "usage: pan_speed_qa.py <film_dir> [--limit 48] [--json]"


def _frames(video, w, h):
    """The video's frames, grey, at w x h, one at a time (the whole film held as float64 was ~4 GB at quarter size: with
    the other checks running beside it the machine swapped and this check took 46 min instead of ~2)."""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", "scale=%d:%d" % (w, h), "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    n = w * h
    try:
        while True:
            buf = p.stdout.read(n)
            if len(buf) < n:
                break
            yield np.frombuffer(buf, np.uint8).reshape(h, w).astype(np.float32)
    finally:
        p.stdout.close()
        p.wait()


def _peak(r):
    """The correlation peak's signed (dy, dx), refined to a fraction of a pixel by a parabola through its neighbours."""
    h, w = r.shape
    y, x = np.unravel_index(int(np.argmax(r)), r.shape)
    out = []
    for c, n, prev, nxt in ((y, h, r[(y - 1) % h, x], r[(y + 1) % h, x]), (x, w, r[y, (x - 1) % w], r[y, (x + 1) % w])):
        den = prev - 2 * r[y, x] + nxt
        f = c + (0.5 * (prev - nxt) / den if den < 0 else 0.0)
        out.append(f - n if f > n / 2 else f)
    return out


def speeds(frames, scale):
    """Per pair (i-1 -> i): the dominant shift magnitude, in px at full size. Cross-correlation over the whole
    (windowed) frame, each frame's spectrum computed once."""
    out, prev, win = [], None, None
    for f in frames:
        if win is None:
            win = np.outer(np.hanning(f.shape[0]), np.hanning(f.shape[1])).astype(np.float32)
        flat = f.std() < 2
        spec = None if flat else np.fft.rfft2(f * win)
        if not out:
            out.append(0.0)
        elif spec is None or prev is None:            # a flat frame: nothing to track
            out.append(0.0)
        else:
            r = np.fft.irfft2(prev * np.conj(spec), s=f.shape)
            out.append(float(np.hypot(*_peak(r))) * scale)
        prev = spec
    return out


def whips(sp, cuts, limit, sustain=SUSTAIN):
    near = set()
    for c in cuts:
        near.update(range(int(c) - EDGE, int(c) + EDGE + 1))
    runs, start = [], None
    for i, v in enumerate(sp + [0.0]):
        fast = v > limit and i not in near
        if fast and start is None:
            start = i
        elif not fast and start is not None:
            if i - start >= sustain:
                runs.append((start, i, max(sp[start:i])))
            start = None
    return runs


def main(argv):
    _c.refuse_unknown(argv, valued=("limit",), switches=("json",), usage=_USAGE)
    lim = _c.argflag(argv, "limit", None)
    args = [a for a in argv if not a.startswith("--") and a != lim]
    if len(args) != 1:
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    plan_p = os.path.join(d, "_plan.json")
    if not os.path.isfile(plan_p):
        print("pan_speed_qa: %s has no _plan.json" % d, file=sys.stderr)
        return 2
    plan = json.load(open(plan_p, encoding="utf-8"))
    video = os.path.join(d, plan.get("video", "final.mp4"))
    if not os.path.isfile(video):
        print("pan_speed_qa: no video at %s" % video, file=sys.stderr)
        return 2
    fps = float(plan.get("fps", 30))
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", video], capture_output=True, text=True)
    W, H = [int(x) for x in p.stdout.strip().split(",")[:2]]
    w, h = max(64, W // 4), max(36, H // 4)
    limit = float(lim or LIMIT) * W / 1920.0
    sp = speeds(_frames(video, w, h), W / float(w))
    found = whips(sp, plan.get("cuts") or [], limit)
    if "--json" in argv:
        print(json.dumps({"whips": [{"start": a / fps, "end": b / fps, "max_px": round(m, 1)} for a, b, m in found],
                          "max_px": round(max(sp), 1) if sp else 0}))
    else:
        for a, b, m in found:
            print("WHIP  %.2f-%.2fs  the camera moves up to %.0f px a frame (limit %.0f): it strobes; slow it, frame wider,"
                  " or cut" % (a / fps, b / fps, m, limit))
        print("[pan_speed_qa] %s  fastest sustained move %.0f px/frame%s" % (
            "OK" if not found else "RED", max([m for _, _, m in found] or [0]), "" if found else " (none over the limit)"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
