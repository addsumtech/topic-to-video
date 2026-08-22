#!/usr/bin/env python3
"""font_gate — prove each declared typeface ACTUALLY renders.

A render exiting 0 says nothing about which face was used: for a long time every remotion film in
this repo rendered Georgia and SF Mono while the DNA declared Playfair Display and JetBrains Mono,
and nothing anywhere complained. This gate renders `FontProbe`, which draws each family beside its
bare generic fallback, and asserts the two tiles differ. It then renders the weight ladder and
asserts the light and heavy tiles differ, which catches a variable font loaded without its range.

Exit 0 = every face loaded and every variable face honours its weight range.
Exit 1 = at least one face is silently falling back (the message names it).
"""
import hashlib, json, os, re, subprocess, sys, tempfile

from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")


def tiles_differ(png_path, rows, cols=2):
    """Split the image into rows x cols tiles and report, per row, whether the tiles differ."""
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    out = []
    for r in range(rows):
        digests = []
        for c in range(cols):
            box = (c * w // cols, r * h // rows, (c + 1) * w // cols, (r + 1) * h // rows)
            digests.append(hashlib.sha256(img.crop(box).tobytes()).hexdigest())
        out.append(len(set(digests)) > 1)
    return out


def _families(ladder):
    """Read the face list out of fonts.ts so the gate cannot drift from what is loaded."""
    src = open(os.path.join(_REMOTION, "src", "runtime", "fonts.ts"), encoding="utf-8").read()
    faces = re.findall(r"\{family: '([^']+)'.*?variable: (true|false)\}", src)
    if not faces:
        sys.exit("font_gate: could not parse FACES out of fonts.ts")
    return [f for f, v in faces if (v == "true" or not ladder)]


def _render(out_png, ladder, expected_rows):
    # expected_rows is cross-checked INSIDE FontProbe against FACES.filter(...).length — a count
    # derived from real JS module evaluation, independent of this file's regex parse of fonts.ts. If
    # the regex under- or over-counts (e.g. a future formatting change silently drops a line instead
    # of matching nothing), the component throws by name and this render fails loudly instead of
    # silently misaligning tiles_differ's crop grid against the wrong number of rows.
    props = json.dumps({"ladder": ladder, "expectedRows": expected_rows})
    r = subprocess.run(
        ["npx", "remotion", "still", "src/index.ts", "FontProbe", out_png,
         "--frame=0", "--gl=angle", "--props=" + props],
        cwd=_REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("font_gate: probe render failed\n" + r.stderr[-2000:])


def main():
    failures = []
    with tempfile.TemporaryDirectory() as td:
        for ladder in (False, True):
            fams = _families(ladder)
            png = os.path.join(td, "ladder.png" if ladder else "faces.png")
            _render(png, ladder, expected_rows=len(fams))
            for fam, ok in zip(fams, tiles_differ(png, rows=len(fams))):
                if not ok:
                    failures.append(
                        "%s: %s" % (fam, "weight range not honoured (light == heavy)" if ladder
                                    else "SILENT FALLBACK - renders identically to its generic"))
    if failures:
        print("font_gate FAILED:")
        for f in failures:
            print("  " + f)
        return 1
    print("font_gate: every declared face loaded and honours its weight range")
    return 0


if __name__ == "__main__":
    sys.exit(main())
