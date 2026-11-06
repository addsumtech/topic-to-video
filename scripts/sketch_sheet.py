#!/usr/bin/env python3
"""Every beat as a greybox, before anything is built.

    python3 scripts/sketch_sheet.py <out_dir> [--no-desktop]

WHY. On the ANC film (2026-11-05) every composition problem — header titles, labels inside the caption band, no
light arc across the film — was found by the delivery gates AFTER fourteen shots had been built, and each one cost a
re-render. Kurzgesagt settles each scene's visual metaphor in a sketching phase before anyone illustrates it. Here
each remotion beat carries `slide.sketch` {metaphor, hero, layout, camera, environment, carries?} (the
design-director writes it at 3.6); this draws them as one sheet — PIL only, seconds, no Chrome — and measures what a
sketch can already show. The user approves `_sketch_review.png` before any shot is built.

WHAT IT DRAWS. Per beat a tile at the film's aspect: the ground light, the caption band shaded, the hero filled dark,
the other rects as tone blocks with their names, the camera intent in the corner; under it the beat number, camera,
environment and the metaphor. The film's through-object (`meta.through_object`) is a ribbon over its beats' tiles.

WHAT IT MEASURES (exit 1 when any is found):
  * a beat with no sketch;
  * a hero under HERO_MIN of the frame — it cannot lead;
  * the film's median coverage under shot_proof's SPARSE line — the frames will be near-empty;
  * the same layout SAME_RUN beats running — one composition repeated;
  * a rect reaching into the caption band (the aspect's own band, the one registers lay out against).
Rects are fractions of the WHOLE frame, so a rect drawn into the shaded band is exactly the rect that will collide
with the caption.
"""
import json
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from PIL import Image, ImageDraw  # noqa: E402

import _caption_band as _cb  # noqa: E402

HERO_MIN = 0.12            # hero area / frame: under this the eye has nothing to land on (calibrated in craft-bar.md)
SAME_TOL = 0.05            # two rects within this on every coordinate are the same rect
SAME_RUN = 3               # this many beats running on one layout is a repeated composition
TILE_W, COLS, PAD, LABEL_H = 480, 4, 16, 58
GROUND, BAND, HERO, BLOCK, INK = (236, 236, 232), (206, 208, 218), (58, 60, 70), (160, 162, 168), (34, 34, 34)
SHEET_BG, LABEL_INK = (24, 24, 24), (235, 235, 235)
RIBBON = (230, 140, 40)
RIBBON_H = 8


def _sparse_line():
    try:
        import shot_proof
        return float(shot_proof.SPARSE_MEDIAN)
    except Exception:                                    # noqa: BLE001 — the line is a number; keep the sheet working
        return 14.0


def _font(size, text=""):
    import fidelity
    return fidelity._font(size, text)


def _rects(sk):
    out = []
    for r in (sk or {}).get("layout") or []:
        if isinstance(r, dict) and isinstance(r.get("rect"), (list, tuple)) and len(r["rect"]) == 4:
            out.append((str(r.get("name") or "?"), [float(v) for v in r["rect"]], bool(r.get("hero"))))
    return out


def _coverage(rects):
    """Share of the frame any rect covers (the union, on a 200-cell grid)."""
    n = 200
    hit = set()
    for _name, (x, y, w, h), _hero in rects:
        for i in range(max(0, int(x * n)), min(n, int((x + w) * n + 0.999))):
            for j in range(max(0, int(y * n)), min(n, int((y + h) * n + 0.999))):
                hit.add((i, j))
    return 100.0 * len(hit) / (n * n)


def _same(a, b):
    ra, rb = sorted(_rects(a)), sorted(_rects(b))
    if not ra or len(ra) != len(rb):
        return False
    return all(abs(p - q) <= SAME_TOL for (_n1, r1, _h1), (_n2, r2, _h2) in zip(ra, rb) for p, q in zip(r1, r2))


def findings(slides, W, H):
    """[finding] for the board's remotion beats, each naming its beat."""
    out = []
    beats = [(s.get("index", pos), s) for pos, s in enumerate(slides, 1)
             if isinstance(s, dict) and s.get("type") != "slide"]
    band_top = 1.0 - _cb.caption_reserve_px(W, H) / float(H)
    covers = []
    for n, s in beats:
        sk = s.get("sketch")
        if not isinstance(sk, dict):
            out.append("beat %d: no sketch — nothing to judge before building" % n)
            continue
        rects = _rects(sk)
        covers.append((n, _coverage(rects)))
        heroes = [r for r in rects if r[2]]
        if heroes:
            _name, (_x, _y, w, h), _ = heroes[0]
            if w * h < HERO_MIN:
                out.append("beat %d: the hero %r covers %.0f%% of the frame (under %.0f%%) — it cannot lead; make it "
                           "larger or closer" % (n, sk.get("hero"), 100 * w * h, 100 * HERO_MIN))
        for name, (_x, y, _w, h), _hero in rects:
            if y + h > band_top + 1e-6:
                out.append("beat %d: %r reaches into the caption band (its bottom at %.0f%% of the frame, the band "
                           "starts at %.0f%%) — the caption will sit on it" % (n, name, 100 * (y + h), 100 * band_top))
    if covers:
        med = sorted(c for _n, c in covers)[len(covers) // 2]
        if med < _sparse_line():
            thin = ", ".join("beat %d %.0f%%" % nc for nc in sorted(covers, key=lambda nc: nc[1])[:4])
            out.append("the film is SPARSE in sketch: median %.1f%% of the frame drawn (line %.0f%%). Sparsest: %s"
                       % (med, _sparse_line(), thin))
    run = []
    sk_beats = [(n, s["sketch"]) for n, s in beats if isinstance(s.get("sketch"), dict)]
    for k, (n, sk) in enumerate(sk_beats):
        run = run + [n] if run and _same(sk_beats[k - 1][1], sk) else [n]
        if len(run) == SAME_RUN:
            out.append("beats %d-%d share the same layout — one composition repeated; vary the hero's place, scale "
                       "or the camera" % (run[0], run[-1]))
    return out


def tile(slide, W, H, tile_w=TILE_W):
    """One beat's greybox at the film's aspect."""
    th = int(round(tile_w * H / float(W)))
    im = Image.new("RGB", (tile_w, th), GROUND)
    d = ImageDraw.Draw(im)
    band = int(round(th * _cb.caption_reserve_px(W, H) / float(H)))
    d.rectangle([0, th - band, tile_w, th], fill=BAND)
    sk = slide.get("sketch") if isinstance(slide.get("sketch"), dict) else {}
    for name, (x, y, w, h), hero in sorted(_rects(sk), key=lambda r: r[2]):     # the hero last, on top
        box = [int(x * tile_w), int(y * th), int((x + w) * tile_w), int((y + h) * th)]
        d.rectangle(box, fill=HERO if hero else BLOCK, outline=INK)
        f = _font(13, name)
        d.text((box[0] + 4, box[1] + 3), name, fill=LABEL_INK if hero else INK, font=f)
    cam = str(sk.get("camera") or "")
    if cam:
        d.text((tile_w - 8 - 9 * len(cam), 6), cam, fill=INK, font=_font(14, cam))
    if not sk:
        d.text((10, 10), "NO SKETCH", fill=(180, 30, 30), font=_font(18))
    return im


def _grid_xy(k, th):
    r, c = divmod(k, COLS)
    return PAD + c * (TILE_W + PAD), PAD + r * (th + LABEL_H + PAD)


def ribbon_probe(k1, th):
    """A pixel on the ribbon between tile position k1 and the next one in its row: in the gap between the tiles."""
    x1, y1 = _grid_xy(k1, th)
    return x1 + TILE_W + PAD // 2, y1 + LABEL_H + RIBBON_H // 2


def build(out_dir, desktop=True):
    with open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8") as fh:
        board = json.load(fh)
    meta, slides = board.get("meta") or {}, board.get("slides") or []
    W, H = _cb.aspect_wh(meta.get("aspect"))
    beats = [s for s in slides if isinstance(s, dict) and s.get("type") != "slide"]
    th = int(round(TILE_W * H / float(W)))
    rows = max(1, -(-len(beats) // COLS))
    size = (COLS * TILE_W + (COLS + 1) * PAD, rows * (th + LABEL_H + PAD) + PAD)
    sheet = Image.new("RGB", size, SHEET_BG)
    d = ImageDraw.Draw(sheet)
    pos = {}
    for k, s in enumerate(beats):
        n = s.get("index", k + 1)
        pos[n] = k
        x, y = _grid_xy(k, th)
        sk = s.get("sketch") if isinstance(s.get("sketch"), dict) else {}
        head = "%s · %s · %s" % (n, sk.get("camera") or "-", sk.get("environment") or "-")
        d.text((x, y + 4), head, fill=LABEL_INK, font=_font(16, head))
        met = str(sk.get("metaphor") or "")
        d.text((x, y + 26), met[:60], fill=(200, 200, 200), font=_font(15, met))
        sheet.paste(tile(s, W, H), (x, y + LABEL_H))
    tobj = meta.get("through_object") if isinstance(meta.get("through_object"), dict) else None
    if tobj and isinstance(tobj.get("beats"), list):
        on = [b for b in tobj["beats"] if b in pos]
        for b in on:
            x, y = _grid_xy(pos[b], th)
            d.rectangle([x, y + LABEL_H, x + TILE_W, y + LABEL_H + RIBBON_H], fill=RIBBON)
        for a, b in zip(on, on[1:]):
            ka, kb = pos[a], pos[b]
            if ka // COLS == kb // COLS and kb == ka + 1:
                x, y = _grid_xy(ka, th)
                d.rectangle([x + TILE_W, y + LABEL_H, x + TILE_W + PAD, y + LABEL_H + RIBBON_H], fill=RIBBON)
    out = os.path.join(out_dir, "_sketch_review.png")
    sheet.save(out)
    if desktop:
        dest = os.path.join(os.path.expanduser("~"), "Desktop",
                            "%s_sketch.png" % os.path.basename(os.path.abspath(out_dir)))
        try:
            shutil.copyfile(out, dest)
        except OSError as e:
            print("[sketch] could not copy the sheet to the Desktop (%s) — open %s" % (e, out), file=sys.stderr)
    return out


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    out_dir = argv[0]
    with open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8") as fh:
        board = json.load(fh)
    meta = board.get("meta") or {}
    if str(meta.get("renderer") or "").lower() != "remotion":
        print("[sketch] not a remotion film — the sketch stage is the remotion tier's")
        return 0
    W, H = _cb.aspect_wh(meta.get("aspect"))
    out = build(out_dir, desktop="--no-desktop" not in argv)
    found = findings(board.get("slides") or [], W, H)
    for f in found:
        print("[sketch] " + f)
    print("[sketch] %s — %s" % (out, "%d finding(s); fix the sketch, not a built shot" % len(found) if found
                                 else "no findings; show the sheet to the user before building"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
