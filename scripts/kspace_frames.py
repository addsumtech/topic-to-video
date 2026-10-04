#!/usr/bin/env python3
"""A real image's k-space and its partial reconstructions, as KSpaceToPicture takes them.

    python3 scripts/kspace_frames.py <out_dir> <image> [--name kspace] [--rows 256] [--frames 24] [--order centre]

An image and its k-space are a 2-D Fourier pair: the k-space is the 2-D FFT of the image, and every partial frame is
the inverse FFT of the rows written so far with the rest left at zero — filled in the order the register's reveal
lights them ('centre': the middle row, then alternately one above and one below; 'top': top to bottom). Nothing is
drawn by hand, and the full inverse is checked to return the image before anything is written.

The image is read as grey levels, padded with black to a square (a scan's background is black, and padding keeps
every part of it) and resized to rows × rows. Written into <out_dir>/media/:
  <name>.png             the k-space's log magnitude above its median (its 99.95th percentile white), shown at
                         --display px with each k-space row a block of whole pixels
  <name>_recon_NN.png    |inverse FFT| with round(rows * NN / frames) rows written, NN = 01 .. frames, all on ONE
                         white point (the full image's 99.7th percentile) so a frame's brightness says how much is
                         there; the last is the whole image
  <name>.json            the matrix, the fill order, the frames and the share of rows each holds
and, when <image> carries an attribution sidecar (<image>.json, as scripts/imagefetch.py writes one), a sidecar
beside every derived picture carrying that attribution and how the picture was derived — so the film's credit
check reads them like any other image.

Prints the beat's `shot_props` for KSpaceToPicture (the paths are relative to <out_dir>, its public dir).
"""
import argparse
import json
import os
import sys

MAX_FRAMES = 64          # KSpaceToPicture's own limit: every frame is an image the render loads


def fill_order(n, order):
    """The k-space rows (0 at the top, the zero frequency at n // 2) in the order they are written."""
    if order == "top":
        return list(range(n))
    c, out = n // 2, [n // 2]
    for d in range(1, n):
        for r in (c - d, c + d):
            if 0 <= r < n and r not in out:
                out.append(r)
    return out


def compute(gray, rows, frames, order):
    """(k-space bytes, [frame bytes], [rows written per frame]) for a rows × rows grey image (floats)."""
    import numpy as np
    a = np.asarray(gray, dtype=np.float64)
    if a.shape != (rows, rows):
        raise ValueError("the image is %r, not %d × %d" % (a.shape, rows, rows))
    if not a.max() > 0:
        raise ValueError("the image is blank — there is nothing for a k-space to hold")
    F = np.fft.fftshift(np.fft.fft2(a))
    full = np.abs(np.fft.ifft2(np.fft.ifftshift(F)))
    if not np.allclose(full, a, atol=1e-6 * max(1.0, float(a.max()))):
        raise AssertionError("the inverse transform of the full k-space does not return the image")
    hi = float(np.percentile(full, 99.7))
    if not hi > 0:
        raise ValueError("the image's 99.7th percentile is 0 — it is almost entirely black")
    seq, written, out = fill_order(rows, order), [], []
    for k in range(1, frames + 1):
        m = int(round(rows * k / frames))
        mask = np.zeros_like(F)
        mask[seq[:m], :] = 1
        rec = np.abs(np.fft.ifft2(np.fft.ifftshift(F * mask)))
        out.append(np.round(np.clip(rec / hi, 0, 1) * 255).astype(np.uint8))
        written.append(m)
    mag = np.log1p(np.abs(F))
    lo, top = np.percentile(mag, 50), np.percentile(mag, 99.95)
    kbytes = np.round(np.clip((mag - lo) / (top - lo), 0, 1) * 255).astype(np.uint8)
    return kbytes, out, written


def square_gray(path, rows):
    """The image as grey levels, padded with black to a square, resized to rows × rows."""
    from PIL import Image
    im = Image.open(path).convert("L")
    side = max(im.size)
    sq = Image.new("L", (side, side), 0)
    sq.paste(im, ((side - im.size[0]) // 2, (side - im.size[1]) // 2))
    return sq.resize((rows, rows), Image.LANCZOS)


def write(out_dir, image, name="kspace", rows=256, frames=24, order="centre", display=512):
    from PIL import Image
    import numpy as np
    if not (8 <= rows <= 4096):
        raise ValueError("--rows is the k-space's row count, 8-4096 — got %r" % rows)
    if not (1 <= frames <= MAX_FRAMES):
        raise ValueError("--frames is 1-%d (every frame is an image the render loads) — got %r" % (MAX_FRAMES, frames))
    if order not in ("centre", "top"):
        raise ValueError("--order is centre or top — got %r" % order)
    if display < rows:
        raise ValueError("--display (%d px) is smaller than the k-space (%d rows): its rows would not stay whole"
                         % (display, rows))
    kbytes, recon, written = compute(np.asarray(square_gray(image, rows), dtype=np.float64), rows, frames, order)
    media = os.path.join(out_dir, "media")
    os.makedirs(media, exist_ok=True)
    kname = "media/%s.png" % name
    Image.fromarray(kbytes, "L").resize((display, display), Image.NEAREST).save(os.path.join(out_dir, kname))
    fnames = []
    for k, b in enumerate(recon, 1):
        fn = "media/%s_recon_%02d.png" % (name, k)
        Image.fromarray(b, "L").resize((display, display), Image.BICUBIC).save(os.path.join(out_dir, fn))
        fnames.append(fn)
    rel_src = os.path.relpath(os.path.abspath(image), os.path.abspath(out_dir))
    side = image + ".json"
    if os.path.isfile(side):
        with open(side, encoding="utf-8") as fh:
            meta = json.load(fh)
        how = [(kname, "log magnitude of the 2-D FFT of the source image")] + [
            (fn, "inverse 2-D FFT of the source's k-space with %d of %d rows (%s)" % (m, rows, order))
            for fn, m in zip(fnames, written)]
        for fn, derivation in how:
            with open(os.path.join(out_dir, fn + ".json"), "w", encoding="utf-8") as fh:
                json.dump(dict(meta, derived_from=rel_src, derivation=derivation), fh, indent=2, ensure_ascii=False)
    with open(os.path.join(media, name + ".json"), "w", encoding="utf-8") as fh:
        json.dump({"source": rel_src, "matrix": rows, "fill_order": order, "frames": fnames,
                   "rows_written": written}, fh, indent=1)
    return {"srcKspace": kname, "srcFrames": fnames, "rows": rows, "order": order}


def main(argv=None):
    ap = argparse.ArgumentParser(description="A real image's k-space and partial reconstructions for KSpaceToPicture.")
    ap.add_argument("out_dir")
    ap.add_argument("image")
    ap.add_argument("--name", default="kspace")
    ap.add_argument("--rows", type=int, default=256)
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--order", default="centre", choices=("centre", "top"))
    ap.add_argument("--display", type=int, default=512)
    a = ap.parse_args(argv)
    try:
        props = write(a.out_dir, a.image, a.name, a.rows, a.frames, a.order, a.display)
    except (ValueError, AssertionError, OSError) as e:
        print("[kspace_frames] REFUSED: %s" % e)
        return 1
    print("[kspace_frames] wrote %s and %d reconstructions into %s/media/" % (props["srcKspace"], len(props["srcFrames"]),
                                                                            a.out_dir))
    print("[kspace_frames] the beat's shot_props (KSpaceToPicture; add its words and credit):")
    print(json.dumps(props, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
