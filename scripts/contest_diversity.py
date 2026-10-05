"""Mechanical DIVERSITY check for register-contest candidate frames — the contest's anti-theater gate.

Phase A asks for pairwise-divergent candidates and the judge runs an anti-collapse check, but both are
the same model checking itself: candidates can subtly cluster (four light-paper looks out of five) and
the ceremony proceeds anyway. This script measures divergence DETERMINISTICALLY from the rendered
pixels, per pair:
  - mode        light/dark from mean luminance (a mode flip alone is strong divergence)
  - palette     distance between luminance-weighted mean colours + dominant saturated accents
  - silhouette  hamming distance between 16x9 ink-occupancy grids (where content sits)
A pair is TOO SIMILAR when the modes match AND the palette distance and silhouette distance both fall
under threshold — that's two skins of one idea, and the flagged pair should REDIVERGE (mechanical
trigger, complementing the judge's semantic anti-collapse).

CLI: python scripts/contest_diversity.py A.png B.png C.png ... [--json]
Exit: 0 = all pairs diverge · 2 = >=1 too-similar pair (printed) · 1 = unreadable input.
"""
import argparse
import itertools
import json
import sys

PALETTE_T = 60.0      # mean-colour euclidean distance under which palettes read "the same family"
SILHOUETTE_T = 0.20   # fraction of 16x9 cells differing under which layouts read "the same shape"



def _pixels(im):
    """Every pixel of `im` as a list. Pillow 12 deprecates getdata() (gone in 14); get_flattened_data()
    is its replacement, with getdata() kept only for an older Pillow."""
    flat = getattr(im, "get_flattened_data", None)
    return list(flat() if flat else im.getdata())

def _structure(im):
    """The frame's COMPOSITION, independent of its colours: how many things there are, how much of the
    frame they cover, how rectilinear they are, and where they sit.

    WHY THIS IS MANDATORY AND PALETTE IS NOT. The mode/palette/silhouette triple was an AND, so a pair only
    read as one idea when the colours matched too — which means a recolour rescued it. A viewer looking at
    three conceived directions said they could be one film: they differed in palette and in which registers
    were named, and not at all in how a frame was ORGANISED. Every one was rectangular containers on a dark
    ground with a left-aligned label and one focal element. Measured, two of the three had their ink
    centroid at (0.48, 0.72) and (0.45, 0.71) with near-identical long-run ratios — the same composition,
    twice, in two colourways. A direction is a way of building a frame, not a swatch.
    """
    import numpy as np
    g = im.convert("L").resize((64, 36))
    a = np.asarray(g, dtype=np.float32)
    ink = np.abs(a - np.median(a)) > 18
    cov = float(ink.mean())
    # connected ink regions: one centred block, four tiles and a scattered field are different patterns
    lab = np.zeros_like(ink, dtype=int)
    cur = 0
    H, W = ink.shape
    for y in range(H):
        for x in range(W):
            if ink[y, x] and lab[y, x] == 0:
                cur += 1
                stack, size = [(y, x)], 0
                lab[y, x] = cur
                while stack:
                    cy, cx = stack.pop()
                    size += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < H and 0 <= nx < W and ink[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = cur
                            stack.append((ny, nx))
                if size < 3:                       # a speck is not a component
                    lab[lab == cur] = 0
                    cur -= 1
    # long horizontal runs separate CONTAINER worlds (cards, tables, rules) from typographic fields
    runs = 0
    for row in ink:
        c = 0
        for v in row:
            c = c + 1 if v else 0
            if c >= 8:
                runs += 1
    tot = max(1, int(ink.sum()))
    ys, xs = np.nonzero(ink)
    cx = float(xs.mean()) / W if len(xs) else 0.5
    cy = float(ys.mean()) / H if len(ys) else 0.5
    spread = float(xs.std()) / W if len(xs) else 0.0
    return {"clusters": cur, "coverage": cov, "runs": runs / tot, "cx": cx, "cy": cy, "spread": spread}


def _structure_dist(a, b):
    """Normalised distance between two compositions. Calibrated on the three directions that prompted it:
    the two that were one composition in two colourways score 0.62, the genuinely different pairs 1.12 and
    1.20. The bar sits at 0.85, between them."""
    import math
    terms = (
        (a["clusters"] - b["clusters"]) / 8.0,
        (a["coverage"] - b["coverage"]) / 0.15,
        (a["runs"] - b["runs"]) / 0.40,
        math.hypot(a["cx"] - b["cx"], a["cy"] - b["cy"]) / 0.30,
        (a["spread"] - b["spread"]) / 0.15,
    )
    return round(math.sqrt(sum(t * t for t in terms)), 2)


STRUCTURE_T = 0.85    # below this two candidates are the same composition, whatever their colours


def _features(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((320, 320))
    px = _pixels(im)
    n = len(px)
    mean = tuple(sum(c[i] for c in px) / n for i in range(3))
    lum = 0.2126 * mean[0] + 0.7152 * mean[1] + 0.0722 * mean[2]
    mode = "dark" if lum < 110 else "light"
    # dominant saturated accent (the hue that carries the register's colour identity)
    best, best_s = mean, -1
    q = im.quantize(colors=6).convert("RGB")
    for cnt, rgb in q.getcolors(maxcolors=64) or []:
        mx, mn = max(rgb), min(rgb)
        s = (mx - mn) / (mx + 1e-6)
        if s > best_s and cnt > n * 0.005:
            best, best_s = rgb, s
    # ink-occupancy silhouette: 16x9 grid of "does this cell differ from the frame's ground"
    g = im.convert("L").resize((16, 9))
    gp = _pixels(g)
    ground = sorted(gp)[len(gp) // 2]                    # median ≈ background level
    sil = [1 if abs(v - ground) > 24 else 0 for v in gp]
    return {"mode": mode, "mean": mean, "accent": tuple(best), "sil": sil, "struct": _structure(im)}


def _dist(a, b):
    pal = sum((a["mean"][i] - b["mean"][i]) ** 2 for i in range(3)) ** 0.5
    acc = sum((a["accent"][i] - b["accent"][i]) ** 2 for i in range(3)) ** 0.5
    ham = sum(1 for x, y in zip(a["sil"], b["sil"]) if x != y) / len(a["sil"])
    return {"palette": round(max(pal, acc * 0.5), 1), "silhouette": round(ham, 3),
            "structure": _structure_dist(a["struct"], b["struct"]),
            "same_mode": a["mode"] == b["mode"]}


def check(paths):
    feats = {p: _features(p) for p in paths}
    pairs, flagged = [], []
    for a, b in itertools.combinations(paths, 2):
        d = _dist(feats[a], feats[b])
        # TWO WAYS TO BE ONE IDEA, and only the first was checked. Same mode + close palette + close ink
        # silhouette catches a re-skin. But a pair can differ in every colour and still be the SAME
        # COMPOSITION — the same containers in the same places with the same rhythm — and that is what a
        # viewer meant by "these three could be one film". Structure is therefore its own verdict, not a
        # term in an AND: a recolour must not be able to rescue a pair.
        similar = (d["same_mode"] and d["palette"] < PALETTE_T and d["silhouette"] < SILHOUETTE_T) \
            or d["structure"] < STRUCTURE_T
        pairs.append({"a": a, "b": b, **d, "too_similar": similar})
        if similar:
            flagged.append((a, b))
    return {"pairs": pairs, "flagged": [[a, b] for a, b in flagged],
            "modes": {p: feats[p]["mode"] for p in paths}}


def main():
    ap = argparse.ArgumentParser(description="mechanical contest-candidate diversity check")
    ap.add_argument("frames", nargs="+")
    ap.add_argument("--json", action="store_true", dest="as_json")
    a = ap.parse_args()
    try:
        r = check(a.frames)
    except Exception as e:
        print(f"[diversity] could not read frames: {e}")
        sys.exit(1)
    if a.as_json:
        print(json.dumps(r))
    else:
        for p in r["pairs"]:
            mark = "✗ TOO SIMILAR" if p["too_similar"] else "✓"
            import os
            an, bn = os.path.basename(os.path.dirname(p["a"]) or p["a"]), os.path.basename(os.path.dirname(p["b"]) or p["b"])
            print(f"  {mark}  {an} vs {bn}: palette {p['palette']} · silhouette {p['silhouette']} · "
                  f"structure {p['structure']} · "
                  f"{'same' if p['same_mode'] else 'diff'} mode")
        if r["flagged"]:
            print(f"[diversity] {len(r['flagged'])} pair(s) read as skins of one idea — REDIVERGE them")
    sys.exit(2 if r["flagged"] else 0)


if __name__ == "__main__":
    main()
