#!/usr/bin/env python3
"""RETIRED — superseded by scripts/measure_ground_luma.py.

This generated a BOOLEAN set (`DNA_GROUND`) meaning "this shot takes its ground from the DNA", which
dnaGroundLum then read as "…therefore its ground luminance is luminance(dna.bg)". That inference is
false for any shot grounded in a different token: KineticManifesto floods accent->accent2 and CrashZoom
accent2->surface. Worse, --check compared the file against THIS SAME detector, so a detection gap was
invisible to it by construction and it reported "up to date" while the set was wrong.

Its replacement does not infer from source at all: it RENDERS each shot under a probe DNA whose token
luminances are far apart and reads the answer off the pixels.

    python3 scripts/measure_ground_luma.py           # measure + print
    python3 scripts/measure_ground_luma.py --check   # fail when the committed table drifts
"""
import sys

def main(argv=None):
    sys.stderr.write(__doc__)
    return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
