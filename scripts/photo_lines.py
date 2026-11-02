#!/usr/bin/env python3
"""photo_lines — a real photograph's own outlines, as a transparent line layer (PhotoToDiagram draws it on).

    python3 scripts/photo_lines.py <photo> [<out.png>]       # default: <photo stem>.lines.png beside it

WHY. A film can show a real photograph and point at it (PhotoPlate), and it can draw a diagram, but nothing carried
the viewer from "this is the real thing" to "this is how it works" in ONE picture. These lines are the photograph's
own edges — computed, not drawn by anyone — so the diagram a PhotoToDiagram beat ends on is exactly what the
photograph showed, at the photograph's own pixel size (the line layer can never be sharper than its source).

HOW. Canny's recipe in numpy: a Gaussian blur (scaled to the image), Sobel gradients, non-maximum suppression along
the gradient (thin, one-pixel ridges), and hysteresis — weak edges kept only where they connect to strong ones,
which is what separates an object's outline from texture. The ridges are thickened to a stroke a little under 0.2%
of the image's long side and written as white with the edge as alpha. A photograph with no edges strong enough to
draw is an error: a beat that promises a drawing and shows an empty layer would be the furniture around an absent
picture, the failure runtime/evidence.ts exists to stop.

CACHED by content: `ensure()` re-traces only when the photograph's bytes (or this file's code version) change.
"""
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

VERSION = 3
HIGH_PCT = 90          # the strong-edge threshold: this percentile of the gradient where there is any gradient
LOW_FRAC = 0.45        # weak edges: this share of the strong threshold
MIN_INK = 0.002        # under this share of the frame drawn, the photograph has no outlines to speak of


def _nms(mag, gx, gy):
    ang = (np.rad2deg(np.arctan2(gy, gx)) + 180.0) % 180.0
    q = np.zeros_like(mag)
    pad = np.pad(mag, 1)
    H, W = mag.shape
    c = pad[1:H + 1, 1:W + 1]
    nbr = {0: (pad[1:H + 1, 2:W + 2], pad[1:H + 1, 0:W]),          # horizontal gradient -> compare left/right
           45: (pad[0:H, 2:W + 2], pad[2:H + 2, 0:W]),
           90: (pad[0:H, 1:W + 1], pad[2:H + 2, 1:W + 1]),
           135: (pad[0:H, 0:W], pad[2:H + 2, 2:W + 2])}
    bins = np.select([(ang < 22.5) | (ang >= 157.5), ang < 67.5, ang < 112.5], [0, 45, 90], 135)
    for b, (n1, n2) in nbr.items():
        m = (bins == b) & (c >= n1) & (c >= n2)
        q[m] = c[m]
    return q


def _hysteresis(q, high, low):
    strong = q >= high
    weak = (q >= low) & ~strong
    keep = strong.copy()
    for _ in range(64):                                    # grow strong edges into connected weak ones
        grown = keep.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy or dx:
                    grown |= np.roll(np.roll(keep, dy, 0), dx, 1)
        new = keep | (grown & weak)
        if (new == keep).all():
            break
        keep = new
    return keep


MIN_RUN = 0.02        # a connected run of edge shorter than this share of the long side is texture, not an outline


def _drop_specks(edge, long):
    """Keep the connected runs of edge at least MIN_RUN of the long side: a star, a speck of cloud, a grain of noise is
    a short isolated run, an object's outline a long connected one. Without scipy the edges are kept as they are."""
    try:
        from scipy import ndimage
    except ImportError:
        return edge
    # measured on runs GROUPED within a few pixels: non-maximum suppression leaves a diagonal outline as a chain of
    # short fragments, and labelling the bare ridges deleted a whole satellite while keeping the cloud texture
    near = ndimage.binary_dilation(edge, structure=np.ones((3, 3)), iterations=max(2, int(long / 400)))
    lab, n = ndimage.label(near, structure=np.ones((3, 3)))
    if n == 0:
        return edge
    sizes = np.bincount(lab.ravel(), weights=edge.ravel().astype(float))     # ridge pixels per group
    keep = sizes >= max(8, int(long * MIN_RUN))
    keep[0] = False
    return edge & keep[lab]


def lines(src, dst):
    """Trace `src` into `dst` (RGBA PNG, the photograph's own size). Returns dst."""
    im = Image.open(src).convert("L")
    W, H = im.size
    long = max(W, H)
    blur = im.filter(ImageFilter.GaussianBlur(radius=max(1.0, long / 700.0)))
    a = np.asarray(blur, dtype=np.float32) / 255.0
    gx = np.zeros_like(a)
    gy = np.zeros_like(a)
    p = np.pad(a, 1, mode="edge")
    gx = (p[0:H, 2:W + 2] + 2 * p[1:H + 1, 2:W + 2] + p[2:H + 2, 2:W + 2]
          - p[0:H, 0:W] - 2 * p[1:H + 1, 0:W] - p[2:H + 2, 0:W])
    gy = (p[2:H + 2, 0:W] + 2 * p[2:H + 2, 1:W + 1] + p[2:H + 2, 2:W + 2]
          - p[0:H, 0:W] - 2 * p[0:H, 1:W + 1] - p[0:H, 2:W + 2])
    mag = np.hypot(gx, gy)
    if mag.max() < 0.08:
        raise RuntimeError("photo_lines: %s has no outlines to trace (its strongest edge is %.3f) — a PhotoToDiagram "
                           "beat needs a photograph of a thing with visible edges" % (src, float(mag.max())))
    q = _nms(mag, gx, gy)
    nz = q[q > 0.02]
    high = float(np.percentile(nz, HIGH_PCT)) if nz.size else 1.0
    edge = _hysteresis(q, high, high * LOW_FRAC)
    edge = _drop_specks(edge, long)
    ink = Image.fromarray((edge * 255).astype(np.uint8))
    # thickened to a stroke of at least 2 px (an odd MaxFilter window), then softened by half a pixel: a 1-px ridge
    # softened that way fell under half alpha and the layer read as nearly empty
    stroke = max(2, int(round(long * 0.0018)))
    ink = ink.filter(ImageFilter.MaxFilter(2 * (stroke // 2) + 1))
    ink = ink.filter(ImageFilter.GaussianBlur(radius=0.5))
    alpha = np.asarray(ink)
    if (alpha > 128).mean() < MIN_INK:
        raise RuntimeError("photo_lines: %s has no outlines to trace (%.2f%% of it would be drawn) — a PhotoToDiagram "
                           "beat needs a photograph of a thing with visible edges" % (src, 100 * (alpha > 128).mean()))
    out = np.zeros((H, W, 4), dtype=np.uint8)
    out[:, :, :3] = 255
    out[:, :, 3] = alpha
    Image.fromarray(out, "RGBA").save(dst)
    return dst


def _key(src):
    h = hashlib.sha256(open(src, "rb").read()).hexdigest()
    return "%s:%d" % (h, VERSION)


def ensure(src, dst):
    """The line layer for `src` at `dst`, traced only when the photograph (or this code's VERSION) changed."""
    side = dst + ".json"
    k = _key(src)
    if os.path.exists(dst) and os.path.exists(side):
        try:
            if json.load(open(side, encoding="utf-8")).get("key") == k:
                return dst
        except (OSError, ValueError):
            pass
    lines(src, dst)
    with open(side, "w", encoding="utf-8") as fh:
        json.dump({"key": k, "src": os.path.basename(src)}, fh)
    return dst


def default_out(src):
    stem, _ = os.path.splitext(src)
    return stem + ".lines.png"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__.split("\n\n")[0])
        sys.exit(2)
    s = sys.argv[1]
    print(ensure(s, sys.argv[2] if len(sys.argv) > 2 else default_out(s)))
