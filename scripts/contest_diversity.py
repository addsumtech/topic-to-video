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


def _features(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((320, 320))
    px = list(im.getdata())
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
    gp = list(g.getdata())
    ground = sorted(gp)[len(gp) // 2]                    # median ≈ background level
    sil = [1 if abs(v - ground) > 24 else 0 for v in gp]
    return {"mode": mode, "mean": mean, "accent": tuple(best), "sil": sil}


def _dist(a, b):
    pal = sum((a["mean"][i] - b["mean"][i]) ** 2 for i in range(3)) ** 0.5
    acc = sum((a["accent"][i] - b["accent"][i]) ** 2 for i in range(3)) ** 0.5
    ham = sum(1 for x, y in zip(a["sil"], b["sil"]) if x != y) / len(a["sil"])
    return {"palette": round(max(pal, acc * 0.5), 1), "silhouette": round(ham, 3),
            "same_mode": a["mode"] == b["mode"]}


def check(paths):
    feats = {p: _features(p) for p in paths}
    pairs, flagged = [], []
    for a, b in itertools.combinations(paths, 2):
        d = _dist(feats[a], feats[b])
        similar = d["same_mode"] and d["palette"] < PALETTE_T and d["silhouette"] < SILHOUETTE_T
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
                  f"{'same' if p['same_mode'] else 'diff'} mode")
        if r["flagged"]:
            print(f"[diversity] {len(r['flagged'])} pair(s) read as skins of one idea — REDIVERGE them")
    sys.exit(2 if r["flagged"] else 0)


if __name__ == "__main__":
    main()
