"""caption_size_qa — are the burned captions big enough to read on a phone? Read from the pixels.

    python3 scripts/caption_size_qa.py <film.mp4 | dir> [--json]

WHAT IT MEASURES: 16 frames from 8 % to 92 % of the film; in each, the caption band (the bottom 22 %), the tallest
contiguous run of ink rows that differ from the band's own median by more than 60 levels — one caption line, from
its tallest glyph to its lowest. The film's caption height is the median over the frames that have one, as a share
of the frame height. Reported when it is under FLOOR.

WHY THIS FLOOR. Captions must read at phone size: about 56 px at 1080p (5.2 % of the frame) is the floor a mature
product-film practice set after its user found 38-40 px captions "too small to see" (video-shotcraft aesthetic rule
Q11; references/promo-shotcraft.md). Calibrated 2026-11-17 by rendering captions at known sizes: the glyph ink of a
line is ~0.93 of the font size in Chinese (Hiragino Sans GB) and English (Helvetica), 56 px font -> 52-53 px ink
(4.8-4.9 %); a Latin line with no descenders reads lower (~0.75), which the median over 16 frames absorbs. FLOOR =
4.6 % ink, i.e. a ~54 px font. The skill's own films measured 3.5-4.1 % (fonts ~40-47 px) when this was written.
A film without burned captions (fewer than half the frames carry a line) is not judged.
Exit 0 clean or not judged, 1 when the captions are too small, 2 on a usage error.
"""
import json
import os
import subprocess
import sys

import numpy as np

import _common as _c

FLOOR = 0.046
BAND = 0.22
_USAGE = "usage: caption_size_qa.py <film.mp4 | dir> [--json]"


def line_height(gray):
    """Height in px of the tallest caption line in the bottom band of a grey frame, or None."""
    h = gray.shape[0]
    band = gray[int(h * (1 - BAND)):].astype(np.int16)
    ink = np.abs(band - np.median(band)) > 60
    rows = np.where(ink.sum(1) > 8)[0]
    if len(rows) == 0:
        return None
    runs = np.split(rows, np.where(np.diff(rows) > 3)[0] + 1)
    r = max(runs, key=len)
    return int(r[-1] - r[0] + 1)


def _frame(video, t, w, h):
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.uint8).reshape(h, w) if len(b) == w * h else None


def judge(video):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", video], capture_output=True, text=True)
    info = json.loads(p.stdout or "{}")
    st, dur = info["streams"][0], float(info["format"]["duration"])
    w, h = int(st["width"]), int(st["height"])
    heights = []
    for x in np.linspace(0.08, 0.92, 16):
        g = _frame(video, dur * x, w, h)
        v = line_height(g) if g is not None else None
        if v:
            heights.append(v)
    if len(heights) < 8:
        return {"judged": False, "frames_with_caption": len(heights)}
    share = float(np.median(heights)) / h
    return {"judged": True, "median_px": float(np.median(heights)), "share": round(share, 4), "frame_h": h,
            "ok": share >= FLOOR, "frames_with_caption": len(heights)}


def main(argv):
    _c.refuse_unknown(argv, valued=(), switches=("json",), usage=_USAGE)
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(_USAGE, file=sys.stderr)
        return 2
    video = args[0]
    if os.path.isdir(video):
        video = next((os.path.join(video, n) for n in ("final.mp4", "out.mp4") if os.path.isfile(os.path.join(video, n))), video)
    if not os.path.isfile(video):
        print("caption_size_qa: no video at %s" % video, file=sys.stderr)
        return 2
    r = judge(video)
    if "--json" in argv:
        print(json.dumps(r))
    elif not r["judged"]:
        print("[caption_size_qa] OK  no burned captions to judge (%d of 16 frames carry a line)" % r["frames_with_caption"])
    elif r["ok"]:
        print("[caption_size_qa] OK  captions %.0f px tall (%.1f%% of the frame, floor %.1f%%)"
              % (r["median_px"], r["share"] * 100, FLOOR * 100))
    else:
        print("SMALL  captions %.0f px tall (%.1f%% of the frame): under the %.1f%% floor — set the caption font to about "
              "%d px at this frame height so it reads on a phone" % (r["median_px"], r["share"] * 100, FLOOR * 100,
                                                                     round(0.052 * r["frame_h"])))
    return 0 if (not r["judged"] or r["ok"]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
