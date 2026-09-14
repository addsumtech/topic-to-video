#!/usr/bin/env python3
"""How CRISP is the type a register draws? — the measurement behind this library's "no text on a Z plane" rule.

    python3 scripts/type_sharpness.py <Register> [--frame=N] [--dna=NAME] [--aspect=16:9]
    python3 scripts/type_sharpness.py <Register> --ab='rotateY(=>rotateNone('   # the same shot, two ways

WHY THIS IS A SCRIPT AND NOT A MEMORY. Two of this repo's load-bearing decisions rest on one number that
nobody can currently re-measure: `runtime/depth.tsx` refuses Z because "a text-dense shot under
`perspective(1200px) translateZ(50px)` lost 38% of its glyph edge strength", and `runtime/stage3d.tsx`
carries surfaces in 3D while projecting every label as flat 2D DOM for the same reason (91 flat, 86 under a
2D scale, 56 under Z). Those figures live in comments and in a test's docstring. The instrument that
produced them was never committed, so the next person to ask "is this register's type actually soft?" has to
invent it again — and this repo has already recorded what that costs, twice, under a different name
(`measure_ground_reach`'s own header).

WHAT IT MEASURES. Sobel gradient magnitude, averaged over the pixels that are ON an ink edge. Ink is
`|f - median(frame)| > 0.10`, the same definition `film_energy_qa` uses, so a register's ink here means what
it means there; the edge band is that mask minus its own erosion, so flat interiors of a glyph and the flat
ground both drop out and what is left is the transition a viewer reads as sharpness. A frame with no ink is
reported as such rather than as zero — an unmeasurable frame is not a soft one.

WHAT IT CANNOT DO. The number is only comparable BETWEEN TWO RENDERS OF THE SAME CONTENT. Different
registers draw different words at different sizes on different grounds, and a big bold word on a flat ground
outscores a small one on a texture whatever the compositing does. So the useful form is `--ab`, which
renders the register twice — once as committed, once with one source substitution applied — and reports the
difference. That is how the 91/56 pair was produced and it is the only form that answers the question.
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c                                             # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")
_SHOTS = os.path.join(_REMOTION, "src", "shots")
_USAGE = ("usage: type_sharpness.py <Register> [--frame=N] [--dna=NAME] [--aspect=16:9] "
          "[--ab='OLD=>NEW']")


def render(name, out_png, frame=145, dna="product", aspect=None, props=None):
    """One still of a register, straight from the committed source. Returns None when it will not render."""
    import json
    pf = out_png + ".props.json"
    p = dict(props or {})
    p["dna"] = dna
    if aspect:
        p["aspect"] = aspect
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(p, fh, ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", name, out_png,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=_REMOTION, capture_output=True, text=True)
    return out_png if r.returncode == 0 else None


def sharpness(path):
    """(edge strength 0-255, ink fraction) — or (None, 0.0) when the frame carries no ink to measure."""
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return None, 0.0
    a = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    ground = float(np.median(a))
    ink = np.abs(a - ground) > (0.10 * 255)
    if ink.sum() < 64:
        return None, float(ink.mean())
    # The EDGE BAND: ink minus its own erosion, so a glyph's flat interior and the flat ground drop out and
    # only the transition a viewer reads as sharpness is left.
    e = ink.copy()
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        e &= np.roll(ink, d, axis=(0 if d[0] else 1))
    band = ink & ~e
    if band.sum() < 32:
        return None, float(ink.mean())
    gx = np.zeros_like(a)
    gy = np.zeros_like(a)
    gx[:, 1:-1] = a[:, 2:] - a[:, :-2]
    gy[1:-1, :] = a[2:, :] - a[:-2, :]
    mag = np.hypot(gx, gy)
    return float(mag[band].mean()), float(ink.mean())


def main(argv):
    _c.refuse_unknown(argv, valued=("frame", "dna", "aspect", "ab"), usage=_USAGE)
    names = [a for a in argv if not a.startswith("-")]
    # `--frame 145` puts its value in the positional list too; the flag reader already owns it, so drop it.
    for flag in ("frame", "dna", "aspect", "ab"):
        v = _c.argflag(argv, flag)
        if v is not None and v in names:
            names.remove(v)
    if len(names) != 1:
        print(_USAGE)
        return 2
    name = names[0]
    if not os.path.isfile(os.path.join(_SHOTS, name + ".tsx")):
        print("[type_sharpness] no such register: %s" % name)
        return 2
    frame = int(_c.argflag(argv, "frame", 145))
    dna = _c.argflag(argv, "dna", "product")
    aspect = _c.argflag(argv, "aspect")
    ab = _c.argflag(argv, "ab")

    tmp = tempfile.mkdtemp(prefix="type_sharp_")
    src_path = os.path.join(_SHOTS, name + ".tsx")
    try:
        got = render(name, os.path.join(tmp, "a.png"), frame, dna, aspect)
        if not got:
            print("[type_sharpness] %s did not render" % name)
            return 1
        s_a, ink_a = sharpness(got)
        if s_a is None:
            print("[type_sharpness] %s frame %d carries no measurable ink (%.2f%%) — nothing to judge"
                  % (name, frame, ink_a * 100))
            return 1
        print("[type_sharpness] %-18s edge %.1f   ink %.1f%%" % (name, s_a, ink_a * 100))
        if not ab:
            return 0
        if "=>" not in ab:
            print("[type_sharpness] --ab needs OLD=>NEW")
            return 2
        old, new = ab.split("=>", 1)
        orig = open(src_path, encoding="utf-8").read()
        if old not in orig:
            print("[type_sharpness] --ab OLD text not found in %s.tsx: %r" % (name, old[:60]))
            return 2
        try:
            open(src_path, "w", encoding="utf-8").write(orig.replace(old, new))
            got_b = render(name, os.path.join(tmp, "b.png"), frame, dna, aspect)
            s_b, ink_b = (sharpness(got_b) if got_b else (None, 0.0))
        finally:
            open(src_path, "w", encoding="utf-8").write(orig)      # ALWAYS, even on a failed render
        if s_b is None:
            print("[type_sharpness] the B variant did not render or carries no ink — no comparison")
            return 1
        print("[type_sharpness] %-18s edge %.1f   ink %.1f%%   (B: %s)" % (name, s_b, ink_b * 100, new[:40]))
        print("[type_sharpness] B is %+.1f%% against A%s"
              % ((s_b - s_a) / s_a * 100,
                 "   <-- the 3D layer is costing sharpness" if s_b > s_a * 1.08 else ""))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
