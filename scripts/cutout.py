"""cutout — cut one shape (a character, a mark) out of a picture with a plain background, for stage3d's inflate().

    python3 scripts/cutout.py <in.png> <out.png> [--box x,y,w,h] [--tol 28] [--pad 6]

The background is found by FLOOD FILL from the edges of the picture (or of --box): only background-coloured pixels
connected to the edge become transparent, so the same colour INSIDE the shape (white eyes on a Bot, a white letter)
stays. The edge is anti-aliased: pixels close to the background colour fade with their distance from it. The result
is trimmed to the shape with a `--pad` transparent margin.

WHY. inflate() needs the whole shape on transparency; removing a colour everywhere punches out a character's white
eyes (inflate then refuses it), and a shape cropped by a phone frame cannot be traced.
REFUSES (exit 1) a shape that touches the edge of the picture or the box (it is cut off: choose a box around a whole
one), and a picture with no plain background (nothing filled). Exit 2 on a usage error.
"""
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

_USAGE = "usage: cutout.py <in.png> <out.png> [--box x,y,w,h] [--tol 28] [--pad 6]"


def cutout(img, tol=28, pad=6):
    """img: PIL RGBA/RGB. Returns the cut-out RGBA image. Raises ValueError when the shape touches the edge or no
    background is found."""
    import numpy as np
    from PIL import Image
    a = np.asarray(img.convert("RGBA")).astype(np.int32)
    h, w = a.shape[:2]
    rgb = a[..., :3]
    edge = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    # the background colour: the most common edge colour (quantised), averaged over the edge pixels near it
    q = (edge // 8) * 8
    vals, counts = np.unique(q.reshape(-1, 3), axis=0, return_counts=True)
    mode = vals[counts.argmax()]
    near = edge[np.abs(q - mode).max(axis=1) == 0]
    bg = near.mean(axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    is_bg = dist <= tol
    seen = np.zeros((h, w), bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_bg[y, x] and not seen[y, x]:
                seen[y, x] = True; dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg[y, x] and not seen[y, x]:
                seen[y, x] = True; dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= yy < h and 0 <= xx < w and not seen[yy, xx] and is_bg[yy, xx]:
                seen[yy, xx] = True; dq.append((yy, xx))
    if not seen.any():
        raise ValueError("no plain background found at the picture's edge (nothing within %d of the edge colour)" % tol)
    shape = ~seen
    if not shape.any():
        raise ValueError("the whole picture is background")
    if shape[0].any() or shape[-1].any() or shape[:, 0].any() or shape[:, -1].any():
        raise ValueError("the shape touches the edge of the picture/box: it is cut off (choose a box around a whole one)")
    # anti-aliased edge: a shape pixel next to the background fades by its distance from the background colour
    alpha = np.where(shape, 255, 0).astype(np.float64)
    ring = shape & (np.roll(seen, 1, 0) | np.roll(seen, -1, 0) | np.roll(seen, 1, 1) | np.roll(seen, -1, 1))
    alpha[ring] = np.clip((dist[ring] - tol * 0.5) / (tol * 2.5) * 255, 0, 255)
    out = a.copy()
    out[..., 3] = (alpha * a[..., 3] / 255).astype(np.int32)
    ys, xs = np.where(shape)
    y0, y1, x0, x1 = max(0, ys.min() - pad), min(h, ys.max() + 1 + pad), max(0, xs.min() - pad), min(w, xs.max() + 1 + pad)
    res = Image.fromarray(out[y0:y1, x0:x1].astype("uint8"), "RGBA")
    if pad and (y0 == 0 or x0 == 0 or y1 == h or x1 == w):      # keep a transparent margin all round
        canvas = Image.new("RGBA", (res.width + 2 * pad, res.height + 2 * pad), (0, 0, 0, 0))
        canvas.paste(res, (pad, pad)); res = canvas
    return res


def main(argv):
    _c.refuse_unknown(argv, valued=("box", "tol", "pad"), usage=_USAGE)
    vals = [_c.argflag(argv, k, None) for k in ("box", "tol", "pad")]
    args = [a for a in argv if not a.startswith("--") and a not in vals]
    if len(args) != 2:
        print(_USAGE, file=sys.stderr)
        return 2
    from PIL import Image
    src, dst = args
    if not os.path.isfile(src):
        print("cutout: no picture at %s" % src, file=sys.stderr)
        return 2
    img = Image.open(src)
    box = _c.argflag(argv, "box", None)
    if box:
        try:
            x, y, bw, bh = [int(v) for v in box.split(",")]
        except ValueError:
            print("cutout: --box is x,y,w,h in pixels\n" + _USAGE, file=sys.stderr)
            return 2
        img = img.crop((x, y, x + bw, y + bh))
    try:
        res = cutout(img, tol=float(_c.argflag(argv, "tol", 28)), pad=int(_c.argflag(argv, "pad", 6)))
    except ValueError as e:
        print("cutout: %s: %s" % (src, e), file=sys.stderr)
        return 1
    res.save(dst)
    print("[cutout] %s -> %s  %dx%d" % (src, dst, res.width, res.height))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
