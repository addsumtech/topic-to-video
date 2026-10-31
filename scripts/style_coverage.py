#!/usr/bin/env python3
"""Which registers each part of the style engine reaches — said out loud, never assumed.

The engine restyles what registers draw (runtime/style.tsx), but some reach is by construction rather than by
rewrite: the easing personality bends the shared easings in runtime/motion.ts, so a register that rolls its own
easing moves as it always did. This lists those, so a film's coverage is reported instead of implied.

    python3 scripts/style_coverage.py --motion       # who the easing personality reaches
    python3 scripts/style_coverage.py <out_dir>      # which of a film's beats the style cannot reach, and why
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "remotion", "src", "shots")
_SHARED = re.compile(r"import\s*\{[^}]*\b(easeOutCubic|easeOutExpo|easeInOutCubic)\b[^}]*\}\s*from\s*'\.\./runtime/motion'")
_MOVES = re.compile(r"\b(useT|useCurrentFrame|interpolate|spring)\s*\(")


def motion_coverage():
    """{"shared": n, "own": [shot]} — registers that move and import the shared easings, and those that move without
    them (their easing is their own: stepping still reaches them, the personality does not)."""
    shared, own = 0, []
    for f in sorted(os.listdir(SHOTS)):
        if not f.endswith(".tsx"):
            continue
        src = open(os.path.join(SHOTS, f), encoding="utf-8").read()
        if _SHARED.search(src):
            shared += 1
        elif _MOVES.search(src):
            own.append(f[:-4])
    return {"shared": shared, "own": own}


_CANVAS = re.compile(r"<canvas|getContext\(|@react-three|ThreeCanvas|@remotion/three")
EXEMPT_WARN = 0.25          # past this fraction of beats exempt, the film reads mixed: styled and not


def exempt_registers():
    """{register: why the style cannot reach its picture} — DERIVED, never listed: a register that puts a real
    photograph on the frame (its own `requireEvidence(...)` call, scripts/register_energy.evidence_props) or draws on a
    canvas (beyond the DOM the engine rewrites). The engine still styles their DOM; their picture stays as drawn."""
    import register_energy as _re
    out = {}
    for s in _re.evidence_props():
        out[s] = "its picture is a real photograph: evidence is framed, never repainted"
    for f in sorted(os.listdir(SHOTS)):
        if f.endswith(".tsx") and _CANVAS.search(open(os.path.join(SHOTS, f), encoding="utf-8").read()):
            out.setdefault(f[:-4], "its picture is drawn on a canvas, beyond the DOM the style engine rewrites")
    return out


def film_coverage(board):
    """{"exempt": [{beat, shot, why}], "exempt_fraction", "warnings"} for a storyboard."""
    ex = exempt_registers()
    slides = board.get("slides") or []
    rows = [{"beat": s.get("index", i + 1), "shot": s.get("shot"), "why": ex[s.get("shot")]}
            for i, s in enumerate(slides) if s.get("shot") in ex]
    frac = len(rows) / float(len(slides)) if slides else 0.0
    warnings = []
    if frac > EXEMPT_WARN:
        warnings.append("%d of %d beats (more than a quarter) are pictures the style cannot reach — the film will read "
                        "as part styled, part not: %s" % (len(rows), len(slides), ", ".join(r["shot"] for r in rows)))
    return {"exempt": rows, "exempt_fraction": frac, "warnings": warnings}


GROUND_CLOSE = 1.6         # the engine's one-ground rule (runtime/style.tsx GROUND_CLOSE): grounds within 1.6:1 are one


def _lum(hexc):
    h = hexc.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def ground_conflicts(board):
    """[{beat, shot, ground, film}] — beats whose register keeps a ground FAR from the film's (> 1.6:1) under its DNA
    (runtime/shotLuma.ts DNA_GROUND_TOKEN: a literal colour is a world of its own; a token is the film's own). A style
    with one ground cannot repaint them — their type is set for their own ground — so the register has to change."""
    meta = board.get("meta") or {}
    dna = meta.get("design_dna")
    if not isinstance(meta.get("style"), dict) or not isinstance(dna, dict) or not str(dna.get("bg", "")).startswith("#"):
        return []
    import measure_ground_luma as mgl
    table = mgl.declared_tokens(open(mgl._SHOTLUMA, encoding="utf-8").read())
    film = _lum(dna["bg"])
    out = []
    for i, s in enumerate(board.get("slides") or []):
        tok = table.get(s.get("shot"))
        if tok is None:
            continue
        colour = tok if isinstance(tok, str) else next((dna[t] for t in tok if isinstance(dna.get(t), str)
                                                        and dna[t].startswith("#")), None)
        own = _lum(colour) if colour else None
        if own is not None and (max(own, film) + 0.05) / (min(own, film) + 0.05) > GROUND_CLOSE:
            out.append({"beat": s.get("index", i + 1), "shot": s["shot"], "ground": colour, "film": dna["bg"]})
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out_dir", nargs="?", help="a film: which of its beats the style cannot reach, and why")
    ap.add_argument("--motion", action="store_true", help="which registers the easing personality reaches")
    a = ap.parse_args(argv)
    if a.motion:
        cov = motion_coverage()
        print("easing personality reaches %d registers through the shared easings" % cov["shared"])
        print("%d move on their own easing (stepping reaches them, the personality does not): %s"
              % (len(cov["own"]), ", ".join(cov["own"])))
        return 0
    if not a.out_dir:
        ap.error("give an out_dir or --motion")
    board = json.load(open(os.path.join(a.out_dir, "storyboard.json"), encoding="utf-8"))
    rep = film_coverage(board)
    for r in rep["exempt"]:
        print("beat %s (%s): %s" % (r["beat"], r["shot"], r["why"]))
    for r in ground_conflicts(board):
        print("beat %s (%s): keeps its own ground %s on the film's %s — cast a register that draws on the film's ground"
              % (r["beat"], r["shot"], r["ground"], r["film"]))
    for w in rep["warnings"]:
        print("WARN   " + w)
    print("%d of %d beats outside the style's reach" % (len(rep["exempt"]), len(board.get("slides") or [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
