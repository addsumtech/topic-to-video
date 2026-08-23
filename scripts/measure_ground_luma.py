#!/usr/bin/env python3
"""measure_ground_luma — MEASURE which DNA token each shot actually paints its ground from.

The model this replaces was a DECLARATION: a boolean set (`DNA_GROUND`) saying "this shot takes its
ground from the DNA", which `dnaGroundLum` then read as "…therefore its ground luminance is
luminance(dna.bg)". That is false for any shot whose ground comes from a DIFFERENT token.
KineticManifesto paints `linear-gradient(135deg, dna.accent, dna.accent2)` — an accent flood — and was
in the set, so the model reported it DARK while the pixels were BRIGHT. Two things read that answer:
caption ink, and pickPresentation's luminance-safe seam. The seam therefore computed a gap of ZERO
across a measured 20.8 -> 149.3 jump and applied no safety: a visible flash.

So: render each shot under a PROBE DNA whose tokens are deliberately far apart in luminance, measure
the frame's actual outer-border luminance (the ground is full-bleed; content is central), and infer
the token from the pixels. The measurement is the authority — a shot whose ground matches no token is
reported UNCLASSIFIED, never guessed.

  python3 scripts/measure_ground_luma.py            # measure all, print the table
  python3 scripts/measure_ground_luma.py --only A,B # measure a few (method check)
  python3 scripts/measure_ground_luma.py --emit     # write DNA_GROUND_TOKEN into shotLuma.ts
  python3 scripts/measure_ground_luma.py --check    # non-zero when the committed table has drifted
"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import dna_audit

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")

# Tokens chosen so their RELATIVE LUMINANCES are far apart and unambiguous.
PROBE_TOKENS = {"bg": "#050505", "surface": "#7a7a7a", "accent2": "#b4b4b4", "accent": "#fafafa"}
PROBE_DNA = {
    "id": "lumprobe",
    "fontDisplay": "Inter, system-ui, sans-serif", "fontBody": "Inter, system-ui, sans-serif",
    "fontMono": '"JetBrains Mono", ui-monospace, monospace',
    "bg": PROBE_TOKENS["bg"], "fg": "#ff2ec4", "dim": "#c86ab0",
    "accent": PROBE_TOKENS["accent"], "accent2": PROBE_TOKENS["accent2"], "onAccent": "#101010",
    "surface": PROBE_TOKENS["surface"], "surfaceBorder": "#4d4d4d", "line": "#3a3a3a",
    "radius": 10, "borderWidth": 1, "motion": "smooth", "decoration": [],
    "uppercaseLabels": False, "labelSpacing": "0.08em",
}


def _srgb_lum(rgb):
    def ch(v):
        c = v / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def token_lums():
    return {k: _srgb_lum(tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))) for k, v in PROBE_TOKENS.items()}


def border_luminance(png, band=14):
    """Median luminance of the outer ring — the ground, unobstructed by centred content."""
    im = Image.open(png).convert("RGB")
    w, h = im.size
    px = im.load()
    vals = []
    for x in range(0, w, 3):
        for y in list(range(0, band)) + list(range(h - band, h)):
            vals.append(_srgb_lum(px[x, y]))
    for y in range(band, h - band, 3):
        for x in list(range(0, band)) + list(range(w - band, w)):
            vals.append(_srgb_lum(px[x, y]))
    vals.sort()
    return vals[len(vals) // 2]


def classify(lum, lums, tol=0.06):
    """Return (token-or-mix, error). A MIX is a sorted 2-token list.

    The single-token model was not enough, and the measurement is what revealed it: KineticManifesto
    paints `linear-gradient(accent -> accent2)`, so its border luminance (0.665 under the probe) sits
    between the two and matches NEITHER. Rather than force it into the nearest token — which is the
    exact move that produced the original bug — treat a two-token blend as its own class and average
    the pair's luminance at runtime."""
    cands = [((k,), v) for k, v in lums.items()]
    keys = sorted(lums)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            cands.append(((a, b), (lums[a] + lums[b]) / 2.0))
    ranked = sorted(cands, key=lambda kv: abs(kv[1] - lum))
    best, second = ranked[0], ranked[1]
    if abs(best[1] - lum) > tol:
        return None, abs(best[1] - lum)
    if abs(second[1] - lum) - abs(best[1] - lum) < 0.03:
        return None, abs(best[1] - lum)      # genuinely ambiguous — do not guess
    tok = best[0][0] if len(best[0]) == 1 else list(best[0])
    return tok, abs(best[1] - lum)


def measure(shot, td):
    props = os.path.join(td, "p.json")
    png = os.path.join(td, shot + ".png")
    json.dump({"scenes": [{"shot": shot, "durF": 150}], "dna": PROBE_DNA,
               "captions": False, "camera": 0}, open(props, "w"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png,
                        "--frame=110", "--gl=angle", "--timeout=90000", "--props=" + props],
                       cwd=_REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr or "")[-300:]
    return border_luminance(png), None


def main(argv):
    only = None
    for a in argv:
        if a.startswith("--only"):
            only = a.split("=", 1)[1].split(",") if "=" in a else None
    shots = only or sorted(dna_audit.registered_shots())
    lums = token_lums()
    print("probe token luminances: " + ", ".join("%s=%.3f" % (k, v) for k, v in sorted(lums.items(), key=lambda kv: kv[1])))
    out, unclassified, failed = {}, [], []
    with tempfile.TemporaryDirectory() as td:
        for i, s in enumerate(shots, 1):
            lum, err = measure(s, td)
            if err is not None:
                failed.append(s); print("  [%3d/%d] %-24s RENDER FAILED" % (i, len(shots), s)); continue
            tok, d = classify(lum, lums)
            if tok is None:
                unclassified.append((s, lum)); print("  [%3d/%d] %-24s lum=%.3f  UNCLASSIFIED" % (i, len(shots), s, lum))
            else:
                out[s] = tok; print("  [%3d/%d] %-24s lum=%.3f  -> %s" % (i, len(shots), s, lum, tok if isinstance(tok,str) else "+".join(tok)))
    print("\nmeasured %d · unclassified %d · failed %d" % (len(out), len(unclassified), len(failed)))
    if "--check" in argv:
        cur = open(os.path.join(_REMOTION, "src", "runtime", "shotLuma.ts"), encoding="utf-8").read()
        bad = []
        for shot, tok in sorted(out.items()):
            want = ("'%s'" % tok) if isinstance(tok, str) else ("[%s]" % ", ".join("'%s'" % x for x in tok))
            if ("  %s: %s," % (shot, want)) not in cur:
                bad.append("%s -> %s" % (shot, tok if isinstance(tok, str) else "+".join(tok)))
        if bad:
            print("DNA_GROUND_TOKEN has DRIFTED from the pixels (%d shot(s)):" % len(bad))
            for b in bad:
                print("  " + b)
            print("re-run: python3 scripts/measure_ground_luma.py --emit")
            return 1
        print("DNA_GROUND_TOKEN matches the measured pixels (%d shots)" % len(out))
        return 0
    dest = os.path.join(_HERE, "..", "remotion", "_ground_luma.json")
    if only:
        # A --only run is a SPOT CHECK; it must never overwrite the full-library table. It did once,
        # silently, and a 134-shot measurement was lost to a 1-shot rerun.
        print("(--only run: spot check, table NOT written)")
    else:
        json.dump({"table": out, "unclassified": [s for s, _ in unclassified], "failed": failed},
                  open(dest, "w"), indent=1)
        print("wrote " + os.path.relpath(dest, os.path.join(_HERE, "..")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
