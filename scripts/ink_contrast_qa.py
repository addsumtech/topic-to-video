#!/usr/bin/env python3
"""ink_contrast_qa — does a register's ink still READ when the film's ground turns light?

WHY THIS EXISTS. All eight DNA presets are dark (the brightest, `editorial`, is Y=0.0053), so a register can
hardcode a light ink, be reviewed a hundred times, and never once be seen on a light ground. Real films do
have light grounds: `dna_from_deck` derives a film's DNA from the client's own deck, and a violet-branded
deck came out violet on warm white. On that film, a register whose type is a literal near-white draws white
on white — the words are all present, every type gate is satisfied (nothing is missing, nothing overflows,
nothing collides), and the frame is blank.

That is the exact shape this repository keeps paying for: a gate that measures type cannot see INK. Probed by
hand on 2026-09-20, `OpenQuestions` set its questions — the whole content of the beat — at about 1.4:1 on a
warm-white ground.

HOW IT MEASURES, and why this way.

Two DNAs that are IDENTICAL except for the ground and the inks: same fonts, same radius, same everything that
moves a glyph. So the two renders of a register differ in colour only, and the same pixel is the same mark in
both. That is what makes the measurement possible:

  1. the DARK render says WHERE the ink is — the pixels that clearly differ from that frame's ground;
  2. the LIGHT render says whether those same marks still read, as a gamma-correct WCAG contrast ratio
     against the light frame's own ground.

A register that reads the DNA inverts and keeps its contrast. A register that hardcodes near-white ink keeps
its PIXELS and loses its contrast, and that is reported as the share of its ink that fell under 3:1.

WHAT IT DOES NOT CLAIM. It says nothing about beauty, and nothing about a register whose ink is a deliberate
identity colour (a syntax palette, CPK element colours, a brand's own hue) — those keep their contrast, since
they are not near-white. It also cannot see a register that draws NO ink in either render; `register_energy`
measures that.

Usage:
  python3 scripts/ink_contrast_qa.py                  # sweep the library, print the offenders
  python3 scripts/ink_contrast_qa.py --only A,B       # a few (this is a render per register per ground)
  python3 scripts/ink_contrast_qa.py --json           # the measurements, for a test or a ledger
"""
import json
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _common as _c                                                            # noqa: E402

_REM = os.path.join(_HERE, "..", "remotion")
_SHOTS = os.path.join(_REM, "src", "shots")

# The two grounds, and NOTHING else different. Every field that could move a glyph — the three faces, the
# radius — is shared, so a pixel is the same mark in both renders and the comparison is about colour alone.
_TYPE = {"fontDisplay": "Inter, sans-serif", "fontBody": "Inter, sans-serif",
         "fontMono": "ui-monospace, monospace", "radius": 14}
DARK = dict(_TYPE, id="inkprobe-dark", bg="#0b0d12", fg="#f2f5fa", dim="#8b97a8", accent="#5ac8fa",
            accent2="#ff9f0a", onAccent="#05070b", surface="rgba(255,255,255,0.05)",
            surfaceBorder="rgba(255,255,255,0.14)", line="rgba(255,255,255,0.14)")
LIGHT = dict(_TYPE, id="inkprobe-light", bg="#f6f3ee", fg="#15181d", dim="#5d6570", accent="#1d63d6",
             accent2="#c2410c", onAccent="#ffffff", surface="#ffffff",
             surfaceBorder="#d8d3ca", line="#ded8cf")

INK_DELTA = 0.25        # how far from its own ground a pixel must sit in the DARK render to count as a mark
FAIL_RATIO = 3.0        # WCAG's floor for large text — a mark under this on the light ground is a finding
# WHAT IS REPORTED IS THE BULK, NOT THE WORST PIXEL. After the filtering above the surviving marks are
# glyphs and rules, and a register can still hold one low-contrast hairline without a reader losing anything —
# `BentoReveal`'s hero tile keeps a 1px border that is blue-on-white at 1.2:1 while every word on it reads at
# 4.5:1 or better. The MEDIAN mark is the honest headline: under the floor, the register's ink has gone. The
# share is kept as context, and a register that loses HALF its marks is reported too, because a beat whose
# left column vanished is not saved by a right column that did not.
SHARE_FLOOR = 0.50
FRAME = 142             # the settled frame this library reviews at


def _y(rgb):
    """Gamma-correct relative luminance (WCAG), from a float RGB triple in 0..1."""
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(v)) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _luma(img):
    """The same WCAG luminance as `_y`, for a whole image at once.

    `np.apply_along_axis(_y, 2, frame)` calls a Python function ONCE PER PIXEL — half a million calls per
    frame, two frames per register, and it turned a 2.4-second render into a two-and-a-half-minute
    measurement. The sweep measured six registers in sixteen minutes before this was found; vectorised, the
    arithmetic is milliseconds and the renders are the cost again.
    """
    import numpy as np
    c = np.asarray(img, dtype=np.float64)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722


def _contrast(y1, y2):
    a, b = (y1, y2) if y1 >= y2 else (y2, y1)
    return (a + 0.05) / (b + 0.05)


def bundle(out_dir):
    """Build the compositions ONCE and render every probe from that build.

    `npx remotion still src/index.ts` re-bundles the whole library on every call: measured at ~24s per render
    against ~2.4s from a prepared bundle, which is the difference between a sweep of three hours and one of
    fifteen minutes. A gate nobody can afford to run is a gate nobody runs, and this file measures 340 frames.
    The bundle is built at the START of a run, so it always describes the tree being measured."""
    r = subprocess.run(["npx", "remotion", "bundle", "--out-dir=" + out_dir],
                       cwd=_REM, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError("could not bundle the library:\n" + (r.stderr or r.stdout)[-2000:])
    return out_dir


def _still(shot, dna, out_png, props=None, frame=FRAME, serve=None):
    payload = dict(props or {}, dna=dna)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
        pf = fh.name
    try:
        r = subprocess.run(["npx", "remotion", "still", serve or "src/index.ts", shot, out_png,
                            "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                           cwd=_REM, capture_output=True, text=True, timeout=900)
        return r
    finally:
        os.unlink(pf)


def _interior(mask, r):
    """True where EVERY pixel within r is also ink — the inside of a fill, as opposed to a stroke or an edge."""
    import numpy as np
    m = mask.astype(np.float64)
    s = np.pad(m.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    h, w = mask.shape
    r0 = np.clip(np.arange(h) - r, 0, h)[:, None]
    r1 = np.clip(np.arange(h) + r + 1, 0, h)[:, None]
    c0 = np.clip(np.arange(w) - r, 0, w)[None, :]
    c1 = np.clip(np.arange(w) + r + 1, 0, w)[None, :]
    got = s[r1, c1] - s[r0, c1] - s[r1, c0] + s[r0, c0]
    area = (r1 - r0) * (c1 - c0)
    return got >= area - 0.5


def _band(y, radius, op):
    """A separable 2-D max/min filter of half-width `radius` — the two passes a grey-scale opening needs."""
    import numpy as np
    out = y
    for axis in (0, 1):
        acc = out
        for k in range(1, radius + 1):
            acc = op(acc, np.roll(out, k, axis=axis))
            acc = op(acc, np.roll(out, -k, axis=axis))
        out = acc
    return out


def _ground_behind(y, radius):
    """The ground BEHIND each mark, whatever the mark's polarity — the local maximum where the mark is dark
    on its surround, the local minimum where it is light on it.

    This is the document-imaging answer, and it is used because the two cheaper ones were wrong in ways that
    matter. Averaging the non-ink pixels around a mark needs to know which pixels are ink, and using the DARK
    render's mask for that erases a whole accent TILE — so `BentoReveal`'s white wordmark, sitting on its blue
    hero tile, was compared against the warm-white paper two hundred pixels away and scored 1.0:1. The frame's
    median is worse still: it says every mark in the register is read against the paper, which is false for
    anything drawn on a panel, a chip or a fill.
    """
    import numpy as np
    hi, lo = _band(y, radius, np.maximum), _band(y, radius, np.minimum)
    mid = (hi + lo) / 2.0
    return np.where(y < mid, hi, lo)


def measure(shot, tmpdir, props=None, mark_png=None, serve=None):
    """{ink, under, share, worst} for one register, or {'skipped': why}."""
    import numpy as np
    from PIL import Image

    dark_png = os.path.join(tmpdir, shot + ".dark.png")
    light_png = os.path.join(tmpdir, shot + ".light.png")
    rd = _still(shot, DARK, dark_png, props, serve=serve)
    if rd.returncode != 0:
        # A REFUSAL IS NOT A FINDING. An evidence register with no `src`, or any register refusing props it
        # was not given, fails both renders identically and has nothing to say about ink.
        return {"skipped": "refused to render: " + (rd.stderr or rd.stdout or "").strip().splitlines()[-1][:160]}
    rl = _still(shot, LIGHT, light_png, props, serve=serve)
    if rl.returncode != 0:
        return {"skipped": "rendered dark but not light: " +
                           (rl.stderr or rl.stdout or "").strip().splitlines()[-1][:160]}

    d = np.asarray(Image.open(dark_png).convert("RGB"), dtype=np.float32) / 255.0
    l = np.asarray(Image.open(light_png).convert("RGB"), dtype=np.float32) / 255.0
    if d.shape != l.shape:
        return {"skipped": "the two renders are different sizes"}

    # each frame's own ground: the median pixel, which is the paper in every register this library draws
    dg = _y(np.median(d.reshape(-1, 3), axis=0))
    dy = _luma(d[::2, ::2])                            # every other pixel: this is a share, not a count
    ly = _luma(l[::2, ::2])
    # WHAT IS JUDGED IS WHAT WAS PLAINLY LEGIBLE ON THE DARK GROUND — nothing else. Two cheaper definitions
    # of "ink" were tried and both cried wolf, in opposite directions: a plain distance from the frame's
    # median counted `BentoReveal`'s white CARDS (which on warm-white paper read by their border and shadow,
    # not by their fill) and reported a third of the register unreadable; dropping thick marks as "fills"
    # then dropped its bold display type and reported three quarters. A mark that was under 4.5:1 on the dark
    # ground was never carrying anything on its own, and a mark that was over it is exactly what must survive
    # the change of ground.
    # A GLOW IS NOT A MARK EITHER. The ground is taken THREE pixels away, not eight: a soft halo around a
    # panel differs from the paper far away but barely from itself nearby, so at this radius it scores low and
    # drops out, while a glyph — which is sharp by construction — still stands clear of the paper beside it.
    # Before this, the pink tracing `BentoReveal` was the hero tile's shadow, whose disappearance on light
    # paper costs a reader nothing.
    dark_local = _ground_behind(dy, radius=3)
    d_hi = np.maximum(dy, dark_local) + 0.05
    d_lo = np.minimum(dy, dark_local) + 0.05
    mask = (d_hi / d_lo) >= 4.5
    # ...AND ONLY THE CORE OF A MARK, never its edge. An anti-aliased boundary pixel sits BETWEEN two regions
    # by construction, so against the far side of that boundary it always half-fails: the ring of pink tracing
    # `BentoReveal`'s hero tile was every edge pixel of the tile, not a word anybody cannot read. A pixel
    # counts only when its four neighbours are marks too.
    mask = mask & np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1)
    ink = int(mask.sum())
    if ink < 200:
        return {"skipped": "nothing on the dark ground was legible enough to judge (register_energy sees that)"}

    # ...AND THE GROUND A MARK IS READ AGAINST IS THE ONE BEHIND IT, not the frame's. Compared against the
    # frame median, `BentoReveal`'s white wordmark on its blue accent tile scored 19% of its ink "unreadable"
    # — white on blue, which is exactly what `onAccent` is for. A gate that reports that teaches the reader
    # to discount it, and this repository has already recorded where that ends. The local ground is the mean
    # luminance of the NON-ink pixels around each mark, by box filter.
    local = _ground_behind(ly, radius=3)
    hi = np.maximum(ly[mask], local[mask]) + 0.05
    lo = np.minimum(ly[mask], local[mask]) + 0.05
    ratios = hi / lo
    under = int((ratios < FAIL_RATIO).sum())
    if mark_png:
        # WHERE the failing marks are, on the light render — because a share is not a diagnosis, and a gate
        # nobody can check by looking is a gate that gets believed when it is wrong.
        out = (l[::2, ::2] * 255).astype(np.uint8).copy()
        bad = np.zeros(mask.shape, dtype=bool)
        bad[mask] = ratios < FAIL_RATIO
        out[bad] = [255, 0, 128]
        Image.fromarray(out).save(mark_png)
    return {"ink": ink, "under": under, "share": round(under / ink, 4),
            "worst": round(float(ratios.min()), 2), "median": round(float(np.median(ratios)), 2)}


def main(argv):
    _c.refuse_unknown(argv, valued=("only", "mark", "store"), switches=("json",),
                      usage="usage: ink_contrast_qa.py [--only=A,B] [--mark=DIR] [--store=FILE] [--json]")
    only = _c.argflag_list(argv, "only")
    mark_dir = _c.argflag(argv, "mark")
    # A SWEEP THAT PRINTS ONLY AT THE END LOSES EVERYTHING IT MEASURED. This one renders 340 frames, and the
    # first full run was stopped by the machine's memory watchdog at 160 of 170 registers with nothing written
    # anywhere. Each measurement is appended as it is taken, and a run started against an existing file skips
    # what that file already holds — so an interrupted sweep is resumed, not repeated.
    store = _c.argflag(argv, "store")
    done = {}
    if store and os.path.exists(store):
        with open(store, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    row = json.loads(line)
                    done[row["shot"]] = row["m"]
    names = sorted(os.path.basename(f)[:-4] for f in os.listdir(_SHOTS) if f.endswith(".tsx"))
    if only:
        missing = [n for n in only if n not in names]
        if missing:
            print("[ink_contrast] --only names %d register(s) that do not exist: %s"
                  % (len(missing), ", ".join(missing)))
            return 2
        names = [n for n in names if n in only]

    out, findings = {}, []
    with tempfile.TemporaryDirectory(prefix="ink_contrast_") as tmp:
        if not ("--json" in argv):
            print("[ink_contrast] bundling the library once...", flush=True)
        todo = [n for n in names if n not in done]
        serve = bundle(os.path.join(tmp, "bundle")) if todo else None
        if done and not ("--json" in argv):
            print("[ink_contrast] %d register(s) already measured in %s" % (len(done), store), flush=True)
        for i, n in enumerate(names, 1):
            if n in done:
                out[n] = done[n]
                continue
            out[n] = measure(n, tmp, serve=serve,
                             mark_png=(os.path.join(mark_dir, n + ".mark.png") if mark_dir else None))
            if store:
                with open(store, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"shot": n, "m": out[n]}, ensure_ascii=False) + "\n")
            if "share" in out[n] and (out[n]["median"] < FAIL_RATIO or out[n]["share"] >= SHARE_FLOOR):
                findings.append(n)
            if not ("--json" in argv) and i % 10 == 0:
                print("  measured %d/%d" % (i, len(names)), flush=True)

    if "--json" in argv:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 1 if findings else 0

    skipped = [n for n, v in out.items() if "skipped" in v]
    print("\n[ink_contrast] %d register(s) measured · %d skipped · reported when the MEDIAN mark is under "
          "%.1f:1 on a light ground, or when %d%% of the marks are"
          % (len(out) - len(skipped), len(skipped), FAIL_RATIO, int(SHARE_FLOOR * 100)))
    if findings:
        print("\nINK THAT STOPS READING WHEN THE GROUND TURNS LIGHT:")
        for n in sorted(findings, key=lambda k: -out[k]["share"]):
            v = out[n]
            print("    %-24s %4.0f%% of its ink under %.1f:1   worst %.2f:1   median %.2f:1"
                  % (n, v["share"] * 100, FAIL_RATIO, v["worst"], v["median"]))
        print("\n    Each of these draws a literal ink instead of the film's. Read the colour from `useDNA()`"
              "\n    (fg / dim / accent / onAccent) — or, when the colour IS the meaning (a syntax palette, an"
              "\n    element's CPK colour, a brand hue), keep it and say so in the register's header.")
    else:
        print("\n    every register's ink still reads on a light ground")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
