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


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 1 and not argv[0].startswith("--"):
        board = json.load(open(os.path.join(argv[0], "storyboard.json"), encoding="utf-8"))
        rep = film_coverage(board)
        for r in rep["exempt"]:
            print("beat %s (%s): %s" % (r["beat"], r["shot"], r["why"]))
        for w in rep["warnings"]:
            print("WARN   " + w)
        print("%d of %d beats outside the style's reach" % (len(rep["exempt"]), len(board.get("slides") or [])))
        return 0
    if argv != ["--motion"]:
        print("usage: style_coverage.py --motion | <out_dir>", file=sys.stderr)
        return 1
    cov = motion_coverage()
    print("easing personality reaches %d registers through the shared easings" % cov["shared"])
    print("%d move on their own easing (stepping reaches them, the personality does not): %s"
          % (len(cov["own"]), ", ".join(cov["own"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
