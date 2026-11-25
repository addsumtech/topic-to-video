#!/usr/bin/env python3
"""caption_spots — where each caption can sit ON the picture's own ground, covering nothing.

    python3 scripts/caption_spots.py <film_dir> --caps caps.json [--frames work/frames] [--size 56]
        [--x 960,760,1180,560,1400,420,1600,1700] [--y 1012,944] [--out work/caption_spots.json]

WHY (2026-11-25). A Numbers tutorial put its captions on a black band under the picture; the user: "底下那个黑色块，
虽然我知道是用于subtitle，但你可以让subtitle很好的融入背景且不影响内容吗" (that black block — make the subtitle blend into
the background without affecting the content). A director-path film has no fixed caption zone: its picture fills
the frame and moves (a chart dragged across, a popover, a push), so a caption's place is MEASURED, not assumed.

HOW. Render the film once with its captions hidden (the page's own switch), then run this. `caps.json` is
[[t0, t1, text], ...] in film seconds. For each caption, the first candidate centre (the previous caption's spot
first, so captions do not jump; then every --y row by every --x) whose box — the text's width at --size plus a
margin — is ONE uniform ground on every frame while the caption is on screen (sampled every 2nd frame) wins:
nothing drawn there, no edge or moving thing passing through. The ground's tone picks the ink: "light" ground →
dark text, "dark" ground → light text. The page then draws each caption at its spot.
A caption with no clean spot is printed and the exit is 1: change the edit (a framing with empty ground under its
content, a pause in the voice while something sweeps the frame, an action timed after the caption) — never a
strip, a scrim or a smaller caption.

OUTPUT {"<index>": [cx, cy, "light"|"dark"]} (frame px, the caption's centre). Exit 0 all placed, 1 some not,
2 usage error.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

_USAGE = ("usage: caption_spots.py <film_dir> --caps caps.json [--frames work/frames] [--size 56] [--x 960,760,...] "
          "[--y 1012,944] [--out work/caption_spots.json]")
FPS = 30
MARGIN = 24          # px of empty ground kept around the text on each side
OFF = 18             # a pixel this far (any channel) from the ground's median is not ground
TOLERANCE = 0.002    # share of a box's pixels allowed off the ground (JPEG noise)
FONTS = ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/SFNS.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def ground(regions):
    """'light' / 'dark' when every region (one per sampled frame) is one uniform ground of one tone, else None."""
    tones = set()
    for a in regions:
        a = np.asarray(a, dtype=int)
        med = np.median(a.reshape(-1, 3), 0)
        if (np.abs(a - med).max(2) > OFF).mean() > TOLERANCE:
            return None
        tones.add("light" if med.mean() > 128 else "dark")
    return tones.pop() if len(tones) == 1 else None


def box_of(cx, cy, width, size, frame_w, frame_h):
    x0, x1 = int(cx - width / 2 - MARGIN), int(cx + width / 2 + MARGIN)
    y0, y1 = int(cy - size * 0.8), int(cy + size * 0.8)
    if x0 < 16 or x1 > frame_w - 16 or y0 < 0 or y1 > frame_h - 4:
        return None
    return x0, y0, x1, y1


def place(caps, frame_at, widths, xs, ys, size, frame_w, frame_h, n_frames):
    """caps [[t0, t1, text]], frame_at(i) -> HxWx3 array; returns ({index: [cx, cy, tone]}, [unplaced indices])."""
    spots, bad, prev = {}, [], None
    for k, (t0, t1, _text) in enumerate(caps):
        f0, f1 = int(t0 * FPS), min(int(t1 * FPS), n_frames - 1)
        for c in ([prev] if prev else []) + [(x, y) for y in ys for x in xs]:
            b = box_of(c[0], c[1], widths[k], size, frame_w, frame_h)
            if b is None:
                continue
            tone = ground(frame_at(f)[b[1]:b[3], b[0]:b[2]] for f in range(f0, f1 + 1, 2))
            if tone:
                spots[str(k)] = [c[0], c[1], tone]
                prev = c
                break
        else:
            bad.append(k)
    return spots, bad


def main(argv):
    _c.refuse_unknown(argv, valued=("caps", "frames", "size", "x", "y", "out"), usage=_USAGE)
    args = [a for a in argv if not a.startswith("--") and a not in [_c.argflag(argv, v, None) for v in
                                                                     ("caps", "frames", "size", "x", "y", "out")]]
    if len(args) != 1 or not _c.argflag(argv, "caps", None):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    caps = json.load(open(os.path.join(d, _c.argflag(argv, "caps", None)), encoding="utf-8"))
    frames = os.path.join(d, _c.argflag(argv, "frames", None) or os.path.join("work", "frames"))
    names = sorted(n for n in os.listdir(frames) if n.startswith("f_") and n.endswith(".jpg"))
    if not names:
        print("caption_spots: no f_NNNNN.jpg frames in %s (render the film with its captions hidden first)" % frames,
              file=sys.stderr)
        return 2
    size = int(_c.argflag(argv, "size", None) or 56)
    xs = [int(v) for v in (_c.argflag(argv, "x", None) or "960,760,1180,560,1400,420,1600,1700").split(",")]
    ys = [int(v) for v in (_c.argflag(argv, "y", None) or "1012,944").split(",")]
    font = next((ImageFont.truetype(p, size) for p in FONTS if os.path.exists(p)), None)
    widths = [font.getlength(c[2]) if font else 0.55 * size * len(c[2]) for c in caps]
    cache = {}

    def frame_at(i):
        if i not in cache:
            if len(cache) > 64:
                cache.clear()
            cache[i] = np.asarray(Image.open(os.path.join(frames, "f_%05d.jpg" % i)).convert("RGB"))
        return cache[i]
    h, w = frame_at(0).shape[:2]
    spots, bad = place(caps, frame_at, widths, xs, ys, size, w, h, len(names))
    out = os.path.join(d, _c.argflag(argv, "out", None) or os.path.join("work", "caption_spots.json"))
    json.dump(spots, open(out, "w"), indent=0)
    for k, (t0, t1, text) in enumerate(caps):
        s = spots.get(str(k))
        print(("%2d %6.2f-%6.2f  %-26s %s" % (k, t0, t1, "(%d, %d) %s" % tuple(s) if s else "NO CLEAN SPOT", text)))
    print("[caption_spots] %s  %d of %d caption(s) placed on the picture's own ground -> %s" % (
        "OK" if not bad else "RED", len(spots), len(caps), out))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
