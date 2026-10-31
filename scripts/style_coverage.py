#!/usr/bin/env python3
"""Which registers each part of the style engine reaches — said out loud, never assumed.

The engine restyles what registers draw (runtime/style.tsx), but some reach is by construction rather than by
rewrite: the easing personality bends the shared easings in runtime/motion.ts, so a register that rolls its own
easing moves as it always did. This lists those, so a film's coverage is reported instead of implied.

    python3 scripts/style_coverage.py --motion
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


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv != ["--motion"]:
        print("usage: style_coverage.py --motion", file=sys.stderr)
        return 1
    cov = motion_coverage()
    print("easing personality reaches %d registers through the shared easings" % cov["shared"])
    print("%d move on their own easing (stepping reaches them, the personality does not): %s"
          % (len(cov["own"]), ", ".join(cov["own"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
