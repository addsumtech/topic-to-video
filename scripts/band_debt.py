#!/usr/bin/env python3
"""Re-measure the caption-band / action-safe debt across every register, and rewrite the manifest.

    python3 scripts/band_debt.py --check      # measure and report the diff; writes nothing
    python3 scripts/band_debt.py --write      # ...and update remotion/band_debt.json

WHY THIS EXISTS. `remotion/band_debt.json` names the registers whose own content reaches into the strip the
renderer reserves for the burned caption, or past the action-safe border. It was produced once, by hand, and
the ratchet over it asserted only how MANY registers were listed — with four spare slots, so four more could
join the debt and the "ratchet" would stay green. The 48 measured percentages beside the names were read by
nothing at all: re-measured, three registers' debt had grown (AsciiField 6.5 -> 8.1, ClothWave 5.4 -> 7.1,
RidgeField 5.1 -> 6.3) and no gate anywhere had noticed.

A record nobody can regenerate is not a measurement, it is a memory. This is the command that regenerates it,
so the numbers can be checked against the library instead of trusted.

WHICH FRAME. Each register is rendered at the frame `useT()` calls SETTLED — the same frame every visual gate
and the shot-critic reads — derived per register from its own exported DURATION. The original pass used a
fixed frame 120 for everything, which for a short register is past the end and for a long one is mid-reveal.
"""
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_remotion as rr                                    # noqa: E402  (needs the path above)
import shot_still_qa as q                                       # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SHOTS = os.path.join(_ROOT, "remotion", "src", "shots")
_MANIFEST = os.path.join(_ROOT, "remotion", "band_debt.json")
REGEN = "python3 scripts/band_debt.py --write"


def durations():
    out = {}
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        m = re.search(r"export const DURATION\s*=\s*(\d+)", open(f, encoding="utf-8").read())
        if m:
            out[os.path.basename(f)[:-4]] = int(m.group(1))
    return out


def measure_all(png_dir, quiet=False):
    """Render every register at its settled frame into png_dir, then measure. Returns {name: {band, edge}}."""
    os.makedirs(png_dir, exist_ok=True)
    durs = durations()
    names = [os.path.basename(f)[:-4] for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx")))]
    missing = [n for n in names if n not in durs]
    if missing:
        raise RuntimeError("no exported DURATION for %s — the settled frame is derived from it" % missing[:5])
    debt, failed = {}, []
    for i, n in enumerate(names):
        png = os.path.join(png_dir, n + ".png")
        if not os.path.exists(png):
            frame = int(round(rr.frame_at_t(durs[n], rr.SETTLED_T)))
            subprocess.run(["npx", "remotion", "still", "src/index.ts", n, png,
                            "--frame=%d" % frame, "--gl=angle", "--log=error"],
                           capture_output=True, text=True, cwd=os.path.join(_ROOT, "remotion"))
        if not os.path.exists(png):
            failed.append(n)
            continue
        r = q.measure(png)
        if r["caption"] > q.CAPTION_FRAC_ERR or r["edge"] > q.EDGE_FRAC_ERR:
            debt[n] = {"band": round(r["caption"] * 100, 2), "edge": round(r["edge"] * 100, 2)}
        if not quiet and (i + 1) % 25 == 0:
            print("  measured %d/%d" % (i + 1, len(names)), flush=True)
    if failed:
        # LOUD, not skipped. A register that fails to render measures as no debt, which would quietly
        # REMOVE it from the manifest and make the ratchet read as an improvement.
        raise RuntimeError("%d register(s) failed to render, so their debt is unknown: %s"
                           % (len(failed), failed))
    return debt


def main(argv):
    if not ({"--check", "--write"} & set(argv)):
        print(__doc__.strip())
        return 2
    png_dir = os.path.join(os.environ.get("TMPDIR", "/tmp"), "band_debt_stills")
    for a in argv:
        if a.startswith("--stills="):
            png_dir = a.split("=", 1)[1]
    old = json.load(open(_MANIFEST, encoding="utf-8"))
    new = measure_all(png_dir)
    prev = old["registers"]

    gone = sorted(set(prev) - set(new))
    fresh = sorted(set(new) - set(prev))
    worse = [(n, prev[n], new[n]) for n in sorted(set(prev) & set(new))
             if new[n]["band"] > prev[n]["band"] + 0.5 or new[n]["edge"] > prev[n]["edge"] + 0.5]
    print("[band_debt] recorded %d, measured %d" % (len(prev), len(new)))
    for n in gone:
        print("  FIXED   %s (was band %.1f%% edge %.1f%%)" % (n, prev[n]["band"], prev[n]["edge"]))
    for n in fresh:
        print("  NEW     %s band %.1f%% edge %.1f%%" % (n, new[n]["band"], new[n]["edge"]))
    for n, o, w in worse:
        print("  GREW    %s band %.1f -> %.1f, edge %.1f -> %.1f" % (n, o["band"], w["band"], o["edge"], w["edge"]))

    if "--write" in argv:
        old["registers"] = dict(sorted(new.items()))
        old["_regenerate"] = REGEN
        old["_measured_at"] = ("the frame useT() calls SETTLED (REDUCED_MOTION_T), derived per register from "
                               "its own exported DURATION — the frame every visual gate reads")
        json.dump(old, open(_MANIFEST, "w", encoding="utf-8"), indent=2, ensure_ascii=False, sort_keys=False)
        print("[band_debt] wrote %s" % _MANIFEST)
        return 0
    return 1 if (fresh or worse) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
