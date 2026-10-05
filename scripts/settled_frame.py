#!/usr/bin/env python3
"""Pull the SETTLED frame out of a clip — the one worth judging a design on.

WHY THIS EXISTS. Every register in this library animates in: type sets word by word, a plate draws on, a
stamp lands last, a list ticks in staggered, a counter rolls toward its final string. A frame grabbed at
the middle of a clip shows that machinery mid-flight, and judging a composition on it produces confident,
wrong conclusions. Measured on one session's review pass, from mid-clip grabs:

  * "MagazineSpread drops the film's `deck` line"      — it fades in over 0.72–0.90 of the shot; it was there
  * "the climax bar's ink is 3.36:1, under the floor"  — the bar was still fading up; settled it is 10.94:1
  * "StatedBy never draws its source stamp"            — the stamp lands at 0.62–0.78, by design

Each of those cost a re-render and an investigation, and two of them nearly cost a "fix" to code that was
correct. The remedy is not judgement, it is arithmetic: sample late, at a fixed fraction, every time.

WHY 0.90 AND NOT 1.0. The last frames of a clip are inside the seam the renderer cross-dissolves into the
next beat, so they carry the NEXT beat's pixels. 0.90 is past every entrance this library schedules (the
latest is `land` at 0.74–0.92, and a register whose payoff arrives after that would be unreadable at
delivery anyway) and clear of the seam.

    python3 scripts/settled_frame.py out.mp4 shot.png
    python3 scripts/settled_frame.py out.mp4 shot.png --at 0.75
    python3 scripts/settled_frame.py <out_dir> frames/ --beat 7        # a beat of a rendered film
"""
import argparse
import json
import os
import subprocess
import sys

SETTLED = 0.90


def _frames(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v",
                        "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return int(r.stdout.strip().rstrip(",").splitlines()[0])
    except (ValueError, IndexError):
        raise SystemExit("[settled_frame] ffprobe could not count frames in %s:\n%s" % (path, r.stderr.strip()))


def grab(clip, out_png, at=SETTLED):
    """Write the frame at `at` of `clip` to `out_png`. Returns the frame index used."""
    n = _frames(clip)
    if n < 2:
        raise SystemExit("[settled_frame] %s has %d frame(s) — nothing to settle" % (clip, n))
    i = max(0, min(n - 1, int(n * at)))
    os.makedirs(os.path.dirname(os.path.abspath(out_png)) or ".", exist_ok=True)
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", clip,
                        "-vf", "select='eq(n\\,%d)'" % i, "-vframes", "1", out_png], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out_png):
        raise SystemExit("[settled_frame] ffmpeg failed on %s:\n%s" % (clip, r.stderr.strip()))
    return i, n


def beat_window(out_dir, beat):
    """(start, end) of `beat` in the film's OWN timeline — the renderer compresses each cut by SEAM frames,
    so a beat's position in out.mp4 is not the running sum of the board's durations."""
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    slides = board.get("slides") or []
    if not 1 <= beat <= len(slides):
        raise SystemExit("[settled_frame] beat %d is outside this board's 1..%d" % (beat, len(slides)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import render_remotion as rr                                   # for the seam length, so the two cannot drift
    fps = float((board.get("meta") or {}).get("fps") or 30)
    seam = rr._REMOTION2_TR / fps
    t = 0.0
    for i, s in enumerate(slides):
        d = float(s.get("duration") or 0)
        if i + 1 == beat:
            return t, t + d
        t += d - seam
    raise SystemExit("[settled_frame] unreachable")


def main():
    ap = argparse.ArgumentParser(description="Pull the settled frame out of a clip.")
    ap.add_argument("clip", help="an mp4, or with --beat a film's out_dir or its out.mp4")
    ap.add_argument("out", help="the PNG to write (a directory when --beat is given)")
    ap.add_argument("--at", type=float, default=SETTLED, help="fraction of the clip (default %.2f)" % SETTLED)
    ap.add_argument("--beat", type=int, help="grab this beat of a rendered film instead of a whole clip")
    a = ap.parse_args()
    if not 0.0 < a.at <= 1.0:
        raise SystemExit("[settled_frame] --at must be in (0, 1]")

    if a.beat is None:
        i, n = grab(a.clip, a.out, a.at)
        print("[settled_frame] %s frame %d/%d (%.0f%%) -> %s" % (a.clip, i, n, a.at * 100, a.out))
        return

    if a.clip.endswith(".mp4"):                  # a film's out.mp4 names its out_dir too
        mp4, out_dir = a.clip, os.path.dirname(os.path.abspath(a.clip))
    else:
        mp4, out_dir = os.path.join(a.clip, "out.mp4"), a.clip
    if not os.path.exists(mp4):
        raise SystemExit("[settled_frame] no out.mp4 in %s — render the film first" % out_dir)
    if not os.path.exists(os.path.join(out_dir, "storyboard.json")):
        raise SystemExit("[settled_frame] --beat needs the film's storyboard.json beside %s" % mp4)
    s, e = beat_window(out_dir, a.beat)
    png = a.out if a.out.endswith(".png") else os.path.join(a.out, "beat%02d.png" % a.beat)
    os.makedirs(os.path.dirname(os.path.abspath(png)) or ".", exist_ok=True)
    at = s + (e - s) * a.at
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.3f" % at, "-i", mp4,
                        "-vframes", "1", png], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(png):
        raise SystemExit("[settled_frame] ffmpeg failed:\n%s" % r.stderr.strip())
    print("[settled_frame] beat %d spans %.2f–%.2fs; grabbed %.2fs (%.0f%%) -> %s"
          % (a.beat, s, e, at, a.at * 100, png))


if __name__ == "__main__":
    main()
