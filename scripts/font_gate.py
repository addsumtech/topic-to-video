#!/usr/bin/env python3
"""font_gate — prove each declared typeface ACTUALLY renders.

A render exiting 0 says nothing about which face was used: for a long time every remotion film in
this repo rendered Georgia and SF Mono while the DNA declared Playfair Display and JetBrains Mono,
and nothing anywhere complained. This gate renders `FontProbe`, which draws each family beside its
bare generic fallback, and asserts the two tiles differ. It then renders the weight ladder and
asserts the light and heavy tiles differ, which catches a variable font loaded without its range.

Exit 0 = every face loaded and every variable face honours its weight range.
Exit 1 = at least one face is silently falling back (the message names it).

KNOWN BLIND SPOT: this gate cannot detect a silent fallback for a family whose exact name is ALSO a
system font already installed on the render host — the fallback and the real face are then two
different fonts with the same CSS family name, so tile A (family + generic) still differs from tile B
(generic alone) even though loadFont() never actually loaded our file. Reproduced twice: macOS ships a
"Baloo 2" (Baloo-Devanagari.ttc) as a system font, so deliberately dropping our Baloo 2 from
`loadFont()` in fonts.ts still passes this gate — every other one of the nine faces IS caught, because
none of them collides with an installed system font name. Practical exposure is limited (loadFont()
registering the real face in document.fonts takes precedence at actual render time), but a FUTURE load
failure for Baloo 2 specifically would render Apple's Devanagari cut instead of the bundled Google
Baloo 2 and this gate would not notice. No general fix is known; noted here so it isn't silently lost.
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


def _all_faces():
    """[(family, is_variable)] read out of fonts.ts, so the gate cannot drift from what is loaded.

    THE COUNT IS THE COVERAGE. A face whose declaration this regex cannot match does not fail — it
    vanishes, and every remaining tile still compares cleanly, so the gate prints its success line over a
    smaller library than the one that ships. `FontProbe` cross-checks the count against a real JS
    evaluation of FACES and throws on a mismatch (see `_render`), which is what makes the number below
    trustworthy rather than merely printed."""
    src = open(os.path.join(_REMOTION, "src", "runtime", "fonts.ts"), encoding="utf-8").read()
    faces = re.findall(r"\{family: '([^']+)'.*?variable: (true|false)\}", src)
    if not faces:
        sys.exit("font_gate: could not parse FACES out of fonts.ts")
    return [(f, v == "true") for f, v in faces]


def _families(ladder):
    return [f for f, var in _all_faces() if (var or not ladder)]


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
    all_faces = _all_faces()
    static = [f for f, var in all_faces if not var]
    failures, checked = [], {False: 0, True: 0}
    with tempfile.TemporaryDirectory() as td:
        for ladder in (False, True):
            fams = _families(ladder)
            png = os.path.join(td, "ladder.png" if ladder else "faces.png")
            _render(png, ladder, expected_rows=len(fams))
            for fam, ok in zip(fams, tiles_differ(png, rows=len(fams))):
                # COUNTED HERE, ONE PER COMPARISON ACTUALLY MADE — not restated from the face list. A count
                # taken from `len(fams)` would print "12 of 12" even if the zip above had run dry, which is
                # the shape of every hole this pass is about.
                checked[ladder] += 1
                if not ok:
                    failures.append(
                        "%s: %s" % (fam, "weight range not honoured (light == heavy)" if ladder
                                    else "SILENT FALLBACK - renders identically to its generic"))
    # COVERAGE, NOT JUST THE VERDICT. "every declared face loaded" was true of one face and of twelve, and
    # the line did not say which — nor that a NON-variable face has no weight range to honour and so is
    # measured on one of the gate's two questions, not both. The denominators come from fonts.ts, the
    # numerators from the comparisons that were made.
    head = ("font_gate: %d of %d declared face(s) proved loaded · %d of %d variable face(s) proved to "
            "honour their weight range" % (checked[False], len(all_faces),
                                           checked[True], len(all_faces) - len(static)))
    if checked[False] != len(all_faces) or checked[True] != len(all_faces) - len(static):
        print("font_gate: NOT EVERY DECLARED FACE WAS COMPARED — " + head)
        print("  fonts.ts declares %d face(s) (%d variable) and this run compared %d and %d. The probe's "
              "row grid and the face list have come apart; do not read the result below as coverage."
              % (len(all_faces), len(all_faces) - len(static), checked[False], checked[True]))
        return 1
    if failures:
        print("font_gate FAILED (%d of %d face-check(s) failed):"
              % (len(failures), checked[False] + checked[True]))
        for f in failures:
            print("  " + f)
        return 1
    print(head)
    if static:
        print("  NOT WEIGHT-TESTED — declared non-variable, so there is no range to honour: %s"
              % ", ".join(static))
    print("  NOT PROVABLE HERE — a family whose name also matches a font installed on this render host "
          "cannot be\n  told apart from it by this instrument (see the docstring; 'Baloo 2' is the known "
          "case on macOS).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
