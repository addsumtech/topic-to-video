#!/usr/bin/env python3
"""A film's palette READ from its drawing style's references — the DNA a style's pictures imply.

    python3 scripts/dna_from_refs.py <out_dir> [--force] [--dry-run]

The style engine draws (meta.style); the DNA colours (meta.design_dna). A style's references carry both: a cartoon's
paper-white field and saturated primaries, an ink painting's rice paper and black. This reads them, the way
scripts/dna_from_deck.py reads a deck's theme, so the palette is repeatable and says where each colour came from:

  * ground  — the most common colour of the side the references live on (light or dark, by their median tone);
  * ink     — the most common colour at the other end, pushed until it holds 7:1 on the ground;
  * accents — the most saturated frequent colours, of hues at least 40° apart;
  * the rest (dim, surface, line, onAccent) mixed from those.

It writes `meta.design_dna` with a `provenance` block, and never overwrites a DNA the board already has unless that
DNA was itself read from references or `--force` is passed. Fonts: the board's own DNA faces when it has them,
otherwise a sans stack that names the bundled Noto CJK faces (validate refuses a CJK film's DNA without them).
"""
import argparse
import colorsys
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as _t  # noqa: E402 — the one WCAG implementation

TAG = "[dna_from_refs]"
SANS = ('"Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif')
MONO = ('"JetBrains Mono", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC", '
        'ui-monospace, monospace')


def _hex(rgb):
    return "#" + "".join("%02x" % int(max(0, min(255, round(c)))) for c in rgb)


def _pixels(path, side=160):
    im = Image.open(path).convert("RGB")
    im.thumbnail((side, side))
    return np.asarray(im).reshape(-1, 3).astype(float)


def _bins(px, q=24):
    """{binned colour: (count, mean rgb)} — a coarse histogram that keeps each bin's true mean colour."""
    keys = (px // q).astype(int)
    out = {}
    for k, p in zip(map(tuple, keys), px):
        c, s = out.get(k, (0, np.zeros(3)))
        out[k] = (c + 1, s + p)
    return {k: (c, s / c) for k, (c, s) in out.items()}


def _lum(rgb):
    return _t._rel_lum(tuple(rgb))


def _sat_val(rgb):
    h, s, v = colorsys.rgb_to_hsv(*(c / 255.0 for c in rgb))
    return h, s, v


def derive(paths):
    """The DNA colours the references imply, with where each came from."""
    px = np.concatenate([_pixels(p) for p in paths])
    hist = sorted(_bins(px).values(), key=lambda t: -t[0])
    total = float(len(px))
    light = float(np.median([_lum(p) for p in px[:: max(1, len(px) // 4000)]])) >= 0.35
    on_side = [(c, m) for c, m in hist if (_lum(m) >= 0.35) == light]
    ground = on_side[0][1] if on_side else hist[0][1]
    other = [(c, m) for c, m in hist if (_lum(m) < 0.12) == light and c / total > 0.002]
    ink = (min if light else max)(other or hist, key=lambda t: _lum(t[1]))[1]
    target = (0, 0, 0) if light else (255, 255, 255)
    t = 0.0
    while _t._contrast(tuple(ink), tuple(ground)) < 7.0 and t < 1.0:         # pushed until it reads
        t += 0.05
        ink = _t._mix(tuple(ink), target, t)
    accents = []
    for c, m in sorted(hist, key=lambda t: -(_sat_val(t[1])[1] * min(1.0, t[0] / (0.01 * total)))):
        h, s, v = _sat_val(m)
        if s < 0.35 or v < 0.25 or c / total < 0.003:
            continue
        if all(min(abs(h - _sat_val(a)[0]), 1 - abs(h - _sat_val(a)[0])) > 40 / 360.0 for a in accents):
            accents.append(m)
        if len(accents) == 2:
            break
    while len(accents) < 2:
        accents.append(_t._mix(tuple(ink), tuple(ground), 0.35))
    g, k, a1, a2 = map(_hex, (ground, ink, accents[0], accents[1]))
    on_a = "#ffffff" if _t._contrast((255, 255, 255), tuple(accents[0])) >= _t._contrast(tuple(ink), tuple(accents[0])) else k
    return {
        "id": "from-style-refs", "fontDisplay": SANS, "fontBody": SANS, "fontMono": MONO,
        "bg": g, "fg": k, "dim": _hex(_t._mix(tuple(ink), tuple(ground), 0.42)), "accent": a1, "accent2": a2,
        "onAccent": on_a, "surface": _hex(_t._mix(tuple(ground), tuple(accents[0]), 0.1)), "surfaceBorder": k,
        "line": _hex(_t._mix(tuple(ink), tuple(ground), 0.6)), "finish": "none",
        "provenance": {"from": "style refs", "refs": [os.path.basename(p) for p in paths],
                       "colours": {"bg": "the most common %s colour of the references" % ("light" if light else "dark"),
                                   "fg": "their most common %s colour, pushed to 7:1 on bg" % ("dark" if light else "light"),
                                   "accent": "the most saturated frequent colour", "accent2": "the next, at least 40° of hue away"}},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--force", action="store_true", help="replace a DNA the board already has")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    path = os.path.join(a.out_dir, "storyboard.json")
    board = json.load(open(path, encoding="utf-8"))
    meta = board.setdefault("meta", {})
    # a reference marked `palette: false` shows how a line is drawn and nothing about colour (a white line drawing on
    # black): read for the palette, it outvoted two colour references and gave a cartoon on cream a black ground
    refs = [os.path.join(a.out_dir, r["src"]) for r in ((meta.get("style") or {}).get("refs") or [])
            if isinstance(r, dict) and isinstance(r.get("src"), str) and r.get("palette") is not False
            and os.path.isfile(os.path.join(a.out_dir, r["src"]))]
    if not refs:
        print("%s REFUSED: meta.style has no reference image on disk to read a palette from" % TAG)
        return 2
    have = meta.get("design_dna")
    if have and not a.force and not (isinstance(have, dict) and (have.get("provenance") or {}).get("from") == "style refs"):
        print("%s REFUSED: the board already has a design_dna it did not read from references — --force replaces it" % TAG)
        return 2
    dna = derive(refs)
    if isinstance(have, dict):
        for f in ("fontDisplay", "fontBody", "fontMono"):
            if have.get(f):
                dna[f] = have[f]
    print("%s bg %s · fg %s · accent %s · accent2 %s (from %d refs)" % (TAG, dna["bg"], dna["fg"], dna["accent"],
                                                                         dna["accent2"], len(refs)))
    if not a.dry_run:
        meta["design_dna"] = dna
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(board, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
