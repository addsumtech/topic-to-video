#!/usr/bin/env python3
"""Is the hero subject CRAFTED — lit, separated, detailed — or a flat drawing?

    python3 scripts/subject_craft_qa.py <out_dir> [--beat N --box x,y,w,h] [--json]

WHY. The user found the GPS film "lacking beauty" and the ANC film "okay but not stunning"; the HTTPS film's subjects
were line drawings in a mostly empty dark frame. The object-fidelity check asks whether the parts are THERE, and no
check could tell a lit, finished object from a line sketch. Apple-style product films separate the subject with a rim
light against a dark ground, light it softly with a real highlight and give the surface detail (references/craft-bar.md).
These are the measures of that, read on each hero beat's SETTLED frame (shot_proof's `_proof/beat_NN.png` — the frame
every other instrument judges), never mid-animation:

  lum_range   p95 - p5 of luminance inside the subject: one flat tone is ~0, a lit form spans its shading
  rim_sep     |mean luminance of the subject's own edge band - the ground just outside it|: is it separated
  highlight   p99 - median inside the subject: a real highlight, not one tone
  detail      mean luminance gradient inside the subject (its eroded interior): surface, not an empty shape
  flat_share  share of the subject in its single most common colour (16 levels a channel): ~1 = a flat fill

WHERE THE SUBJECT IS, in order: a Blender beat's plate boxes (media/blender/<id>/boxes.json, every object, over the
plate's last fifth); the beat's `slide.sketch` hero rect; `--box` for an old film. The box is then cut to the pixels
that differ from the ground at its border. A hero beat with none of these is NOT MEASURED and exits 1: a check that
cannot find the subject must say so, never pass it.

Thresholds come from our own films (GPS, HTTPS, ANC — references/craft-bar.md, "Calibration"); until a measure
separates the films the user judged, it is REPORTED, not enforced (THRESHOLDS stays empty for it).
"""
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

INK = 24 / 255.0          # a pixel this far from the ground colour belongs to the subject (shot_proof's ink line)
EDGE_FRAC = 0.03          # the edge bands are this share of the subject box's short side
FLAT_LEVELS = 16
THRESHOLDS = {}           # measure -> minimum, filled only by calibration (Task 8); empty = report only


def _lum(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def _morph(mask, r, grow):
    from PIL import Image, ImageFilter
    if r < 1:
        return mask.copy()
    im = Image.fromarray((mask * 255).astype(np.uint8))
    k = 2 * int(r) + 1
    im = im.filter(ImageFilter.MaxFilter(k) if grow else ImageFilter.MinFilter(k))
    return np.asarray(im) > 127


def measure(rgb, mask):
    """The five measures of a subject `mask` (bool HxW) on an image `rgb` (float HxWx3 in 0..1)."""
    mask = np.asarray(mask, bool)
    if not mask.any():
        raise ValueError("the subject mask is empty")
    rgb = np.asarray(rgb, float)
    lum = _lum(rgb)
    inside = lum[mask]
    ys, xs = np.nonzero(mask)
    short = max(1.0, min(np.ptp(ys) + 1, np.ptp(xs) + 1))
    r = max(1, int(round(short * EDGE_FRAC)))
    inner = mask & ~_morph(mask, r, grow=False)
    outer = _morph(mask, r, grow=True) & ~mask
    rim_sep = float(abs(lum[inner].mean() - lum[outer].mean())) if inner.any() and outer.any() else 0.0
    core = _morph(mask, r, grow=False)
    gy, gx = np.gradient(lum)
    grad = np.hypot(gx, gy)
    detail = float(grad[core].mean()) if core.any() else 0.0
    q = np.clip((rgb[mask] * FLAT_LEVELS).astype(int), 0, FLAT_LEVELS - 1)
    codes = q[:, 0] * FLAT_LEVELS * FLAT_LEVELS + q[:, 1] * FLAT_LEVELS + q[:, 2]
    flat = float(np.bincount(codes).max() / float(len(codes)))
    p5, p50, p95, p99 = np.percentile(inside, [5, 50, 95, 99])
    return {"lum_range": round(float(p95 - p5), 4), "rim_sep": round(rim_sep, 4),
            "highlight": round(float(p99 - p50), 4), "detail": round(detail, 5), "flat_share": round(flat, 4)}


def mask_from_box(rgb, box):
    """The pixels inside `box` (x0, y0, x1, y1 in px) that differ from the ground at the box's border."""
    rgb = np.asarray(rgb, float)
    h, w = rgb.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    m = np.zeros((h, w), bool)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return m
    sub = rgb[y0:y1, x0:x1]
    border = np.concatenate([sub[0], sub[-1], sub[:, 0], sub[:, -1]])
    q = np.round(border * 32).astype(int)
    codes, counts = np.unique(q[:, 0] * 1089 + q[:, 1] * 33 + q[:, 2], return_counts=True)
    c = codes[counts.argmax()]
    ground = np.array([c // 1089, (c // 33) % 33, c % 33]) / 32.0
    m[y0:y1, x0:x1] = np.abs(sub - ground).max(axis=-1) > INK
    return m


def _plate_box(out_dir, slide, w, h):
    bl = slide.get("blender") if isinstance(slide.get("blender"), dict) else None
    pid = (bl or {}).get("id")
    if not pid:
        return None
    try:
        with open(os.path.join(out_dir, "media", "blender", pid, "boxes.json"), encoding="utf-8") as fh:
            boxes = json.load(fh)
    except (OSError, ValueError):
        return None
    fw = 1920.0
    try:
        with open(os.path.join(out_dir, "media", "blender", pid, "plate.json"), encoding="utf-8") as fh:
            fw = float((json.load(fh) or {}).get("width") or fw)
    except (OSError, ValueError, TypeError):
        pass
    got = []
    for series in boxes.values():
        if not isinstance(series, list) or not series:
            continue
        tail = [b for b in series[int(len(series) * 0.8):] if isinstance(b, list) and len(b) == 4]
        got.extend(tail)
    if not got:
        return None
    s = w / fw
    a = np.array(got, float)
    return (a[:, 0].min() * s, a[:, 1].min() * s, a[:, 2].max() * s, a[:, 3].max() * s), "plate %s boxes" % pid


def _sketch_box(slide, w, h):
    sk = slide.get("sketch") if isinstance(slide.get("sketch"), dict) else {}
    for r in sk.get("layout") or []:
        if isinstance(r, dict) and r.get("hero") and isinstance(r.get("rect"), list) and len(r["rect"]) == 4:
            x, y, rw, rh = r["rect"]
            return (x * w, y * h, (x + rw) * w, (y + rh) * h), "sketch hero rect"
    return None


def subject_mask(out_dir, slide, rgb, box_frac=None):
    """(mask, source) for the beat's subject on `rgb`, or (None, why)."""
    h, w = rgb.shape[:2]
    if box_frac is not None:
        x, y, bw, bh = box_frac
        found = ((x * w, y * h, (x + bw) * w, (y + bh) * h), "--box")
    else:
        found = _plate_box(out_dir, slide, w, h) or _sketch_box(slide, w, h)
    if not found:
        return None, "no plate boxes, no sketch hero rect and no --box"
    m = mask_from_box(rgb, found[0])
    if m.sum() < 50:
        return None, "the %s holds no pixels that differ from the ground" % found[1]
    return m, found[1]


def _frame(out_dir, n):
    from PIL import Image
    p = os.path.join(out_dir, "_proof", "beat_%02d.png" % n)
    if not os.path.exists(p):
        return None, "no settled frame %s — run shot_proof.py first" % os.path.relpath(p, out_dir)
    return np.asarray(Image.open(p).convert("RGB"), float) / 255.0, None


def run(out_dir, beats=None, box=None):
    """[(beat, result_or_None, source_or_why, is_hero)]."""
    with open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8") as fh:
        board = json.load(fh)
    meta, slides = board.get("meta") or {}, board.get("slides") or []
    by = {s.get("index", i): s for i, s in enumerate(slides, 1)}
    heroes = [b for b in (meta.get("hero_moments") or []) if isinstance(b, int)]
    todo = beats if beats else heroes
    rows = []
    for n in todo:
        s = by.get(n)
        if s is None:
            rows.append((n, None, "beat %d is not on the board" % n, n in heroes))
            continue
        rgb, why = _frame(out_dir, n)
        if rgb is None:
            rows.append((n, None, why, n in heroes))
            continue
        m, src = subject_mask(out_dir, s, rgb, box)
        rows.append((n, measure(rgb, m) if m is not None else None, src, n in heroes))
    return rows


def _verdict(res):
    return [k for k, lo in THRESHOLDS.items() if res.get(k, 0) < lo]


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    out_dir, beats, box = argv[0], None, None
    if "--beat" in argv:
        beats = [int(argv[argv.index("--beat") + 1])]
    if "--box" in argv:
        box = [float(v) for v in argv[argv.index("--box") + 1].split(",")]
    rows = run(out_dir, beats, box)
    if "--json" in argv:
        print(json.dumps([{"beat": n, "measures": r, "source": s, "hero": h} for n, r, s, h in rows], indent=1))
    if not rows:
        print("[subject_craft] no hero beats (meta.hero_moments) — nothing to measure")
        return 0
    bad = 0
    for n, res, src, hero in rows:
        if res is None:
            print("[subject_craft] beat %d: NOT MEASURED (%s)%s" % (n, src, " — a HERO beat" if hero else ""))
            bad += hero
            continue
        low = _verdict(res)
        print("[subject_craft] beat %d (%s): %s%s" % (n, src, "  ".join("%s %.3f" % kv for kv in res.items()),
                                                     "  — under the bar on " + ", ".join(low) if low else ""))
        bad += bool(low) and hero
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
