#!/usr/bin/env python3
"""type_specimens — render one representative shot per DNA direction into a contact sheet, so the
type pairings are judged on real frames rather than on family names in a table.

Usage: python3 scripts/type_specimens.py <out_dir>
"""
import os, subprocess, sys, json

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")

# One shot per direction, chosen because each shows a display size, a body size and a label together.
ROWS = [
    ("terminal", "TermCounter"), ("editorial", "EdStat"), ("product", "MaterialHero"),
    ("blueprint", "BlueprintGrid"), ("cinematic", "CinematicTitle"), ("data", "ChartLive"),
    ("retro", "NeonGrid"), ("neutral", "KnowledgeGraph"),
]


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    pngs = []
    for dna_id, shot in ROWS:
        png = os.path.join(out_dir, "spec_%s.png" % dna_id)
        props = json.dumps({"shot": shot, "dnaId": dna_id})
        r = subprocess.run(
            ["npx", "remotion", "still", "src/index.ts", "TypeSpecimen", png,
             "--frame=140", "--gl=angle", "--props=" + props],
            cwd=_REMOTION, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("specimen render failed for %s/%s\n%s" % (dna_id, shot, r.stderr[-1500:]))
        pngs.append(png)
    sheet = os.path.join(out_dir, "specimens.png")
    inputs = sum([["-i", p] for p in pngs], [])
    fc = "".join("[%d:v]scale=760:-1[v%d];" % (i, i) for i in range(len(pngs)))
    fc += "".join("[v%d]" % i for i in range(len(pngs))) + "vstack=inputs=%d" % len(pngs)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, sheet], check=True)
    print(sheet)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/type-specimens")
