"""empty_frame_qa — does the picture sit nearly BLANK for a second or more? Read from the pixels.

    python3 scripts/empty_frame_qa.py <film.mp4 | out_dir> [--json]

WHAT IT MEASURES (4 frames a second at 320x180, above the caption band = the top 80 %): the share of the frame that
is OCCUPIED — pixels that differ from the frame's own dominant colour, or sit on an edge, with every closed outline
filled (a white card on white paper is occupied; a big black fill is occupied). A stretch of >= MIN_S seconds under
FLOOR is reported: the screen holds the ground with at most a label on it while the voice goes on.

WHY A FLOOR THIS LOW: it is for blank HOLDS, not minimalism. A hero object alone on a clean ground (a mascot, a logo
end card, one card being built) reads 5-15 % and is not reported. Calibrated 2026-11-16 on six finished films: it
reported exactly two stretches, both real — a page with only its step label for 1 s between two shots (proto_zh
30.0 s) and a near-black screen with one small label for 2 s (qr_html 114.2 s) — and nothing else. The last
END_GRACE seconds are exempt (a fade to black at the end is a close, not a hole).
Exit 0 clean, 1 when a stretch is reported, 2 on a usage error.
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage

import _common as _c

W, H, FPS = 320, 180, 4
FLOOR = 0.03          # occupied share of the frame above the caption band
MIN_S = 1.0           # a blank shorter than this is a cut or a breath
END_GRACE = 2.0       # the closing fade
CAPTION_TOP = 0.80
_USAGE = "usage: empty_frame_qa.py <film.mp4 | out_dir> [--json]"


def occupancy(rgb):
    """Share of the frame (above the caption band) that is occupied. rgb: HxWx3 uint8/int array."""
    f = rgb[: int(rgb.shape[0] * CAPTION_TOP)].astype(np.int16)
    q = (f // 16).reshape(-1, 3)
    key = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    bg = int(np.bincount(key).argmax())
    bgc = np.array([bg // 256, (bg // 16) % 16, bg % 16]) * 16 + 8
    diff = np.abs(f - bgc).max(2) > 28
    g = f.mean(2)
    edge = np.hypot(ndimage.sobel(g, 0), ndimage.sobel(g, 1)) > 40
    m = ndimage.binary_fill_holes(ndimage.binary_dilation(edge, iterations=2) | diff)
    return float(ndimage.binary_opening(m).mean())


def _frames(video):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", "fps=%d,scale=%d:%d" % (FPS, W, H),
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.wait()
    if p.returncode:
        raise RuntimeError("ffmpeg could not decode %s" % video)


def stretches(occ, fps=FPS, floor=FLOOR, min_s=MIN_S, end_grace=END_GRACE):
    """[(start_s, end_s, min_occupancy)] of runs under the floor lasting >= min_s, the closing grace excluded."""
    occ = list(occ)
    last = len(occ) - int(round(end_grace * fps))
    out, s = [], None
    for i in range(len(occ) + 1):
        low = i < last and occ[i] < floor
        if low and s is None:
            s = i
        elif not low and s is not None:
            if (i - s) / fps >= min_s:
                out.append((s / fps, i / fps, min(occ[s:i])))
            s = None
    return out


def judge(video):
    occ = [occupancy(f) for f in _frames(video)]
    if not occ:
        raise RuntimeError("no frames decoded from %s" % video)
    return stretches(occ), occ


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
        print("empty_frame_qa: no video at %s" % video, file=sys.stderr)
        return 2
    found, occ = judge(video)
    if "--json" in argv:
        print(json.dumps({"video": video, "stretches": [{"start": a, "end": b, "min": round(m, 4)} for a, b, m in found]}))
    elif found:
        for a, b, m in found:
            print("EMPTY  %.1f-%.1fs  the frame is nearly blank (%.1f%% occupied) for %.1fs — put the shot's subject "
                  "on screen, or cut sooner" % (a, b, m * 100, b - a))
    else:
        print("[empty_frame_qa] OK  no blank hold >= %.1fs (median occupancy %.0f%%)" % (MIN_S, 100 * float(np.median(occ))))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
