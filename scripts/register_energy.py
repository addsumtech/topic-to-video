#!/usr/bin/env python3
"""Measure EVERY register as a moving picture, not a still — the library-wide energy diagnostic.

    python3 scripts/register_energy.py            # measure all, write the manifest, print the ranking
    python3 scripts/register_energy.py --only A,B  # a few
    python3 scripts/register_energy.py --report    # re-print the ranking from the manifest, render nothing

WHY. `film_energy_qa.py` judges a delivered FILM. It found one this skill shipped measuring 3.3x under the
quietest reference launch film on motion, 5.6x on density and 3.4x on light — but a film is only as alive as
the beats in it, and nothing has ever measured a beat. Every visual gate here reads a STILL: shot_still_qa,
frame_safe_qa, keyframe_qa_remotion, the contact sheet the critic reads. A register can be perfectly composed
in every still and completely inert as five seconds of film, and the entire pipeline will call it good.

So this renders each register as VIDEO at its own DURATION with its own default props and measures the same
three axes. Default props are the only uniform basis (the same choice band_debt.py makes); a register that
looks dead here may come alive with real content, which is why the manifest records numbers rather than
verdicts.

It also writes three frames per register (early / settled / late) into `--stills`, so a design review can look
at what the numbers are describing instead of trusting them.
"""
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import film_energy_qa as fe                                      # noqa: E402
import render_remotion as rr                                     # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REMOTION = os.path.join(_ROOT, "remotion")
_SHOTS = os.path.join(_REMOTION, "src", "shots")
MANIFEST = os.path.join(_REMOTION, "register_energy.json")
# Below this footprint an empty frame is empty because the COMPOSITION is small; above it, because the
# composition spans the frame and has no tone. Set between the two clusters measured on the sparsest
# registers a delivered film used (9-19% against 53-57%), which is where the gap actually is.
FOOTPRINT_SPLIT = 0.35
REGEN = "python3 scripts/register_energy.py"


def floors():
    """The floors, TAKEN from film_energy_qa — never restated.

    Restating them is how this repo's caption band became four disagreeing copies. A diagnostic that ranks
    registers against a private copy of the numbers would keep ranking against them after the real gate moved.
    """
    return {"motion_p75": fe.MOTION_P75_FLOOR, "ink_median": fe.INK_FLOOR, "luma_range": fe.LUMA_RANGE_FLOOR}


def durations():
    out = {}
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        m = re.search(r"export const DURATION\s*=\s*(\d+)", open(f, encoding="utf-8").read())
        if m:
            out[os.path.basename(f)[:-4]] = int(m.group(1))
    return out


def footprint(png):
    """What FRACTION OF THE FRAME the register's content spans — its ink's bounding box.

    Ink alone cannot tell the two ways a frame is empty apart, and they need opposite fixes. Measured on the
    six sparsest registers a delivered film used:

        TermTree      ink 1.1%  footprint  9.0%   |  CardStack3D  ink 2.9%  footprint 57.1%
        QuadSplit     ink 3.9%  footprint 11.3%   |  VersusSplit  ink 3.2%  footprint 53.2%

    The left column is content composed at a ninth of the frame — the fix is to fill it. The right column
    already spans the frame and is TONELESS: every element sits within 0.10 of the ground, so the composition
    is there and invisible. CardStack3D paints its cards from `dna.surface` and VersusSplit paints two halves
    outright; neither needs a new layout, both need real tone. One number cannot ask for both.
    """
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return None
    a = np.asarray(Image.open(png).convert("L").resize((192, 108))).astype(np.float32) / 255.0
    ink = np.abs(a - np.median(a)) > 0.10
    if not ink.any():
        return 0.0
    ys, xs = np.nonzero(ink)
    return float(((xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1)) / (192 * 108))


def render_one(name, mp4):
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", name, mp4,
                        "--gl=angle", "--log=error"], capture_output=True, text=True, cwd=_REMOTION)
    return os.path.exists(mp4), ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-1:] or [""]


def stills_from(mp4, out_dir, name, durF, fps=30):
    os.makedirs(out_dir, exist_ok=True)
    secs = durF / fps
    for tag, frac in (("a", 0.15), ("b", rr.SETTLED_T), ("c", 0.97)):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % (secs * frac), "-i", mp4,
                        "-frames:v", "1", os.path.join(out_dir, "%s_%s.png" % (name, tag))],
                       capture_output=True)


def main(argv):
    if "--report" in argv:
        data = json.load(open(MANIFEST, encoding="utf-8"))
    else:
        only = next((a.split("=", 1)[1].split(",") for a in argv if a.startswith("--only=")), None)
        stills = next((a.split("=", 1)[1] for a in argv if a.startswith("--stills=")), None)
        tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "_register_energy")
        os.makedirs(tmp, exist_ok=True)
        durs = durations()
        names = [n for n in sorted(durs) if not only or n in only]
        rows, failed = {}, []
        for i, n in enumerate(names, 1):
            mp4 = os.path.join(tmp, n + ".mp4")
            if not os.path.exists(mp4):
                ok, tail = render_one(n, mp4)
                if not ok:
                    failed.append("%s (%s)" % (n, tail[0][:100]))
                    continue
            m = fe.measure(mp4)
            if not isinstance(m, dict):
                failed.append("%s (unmeasurable: %r)" % (n, m))
                continue
            rows[n] = {"motion_p75": round(m["motion_p75"], 4),
                       "ink_median": round(m["ink_median"], 3),
                       "luma_range": round(m["luma_range"], 3),
                       "seconds": round(m["seconds"], 1)}
            # The settled still, for the footprint. Written whether or not --stills was asked for, into a
            # temp dir if not: a diagnosis that cannot distinguish "too small" from "too flat" sends every
            # register the same advice, and the two need opposite work.
            sd = stills or os.path.join(tmp, "_fp")
            stills_from(mp4, sd, n, durs[n])
            fp = footprint(os.path.join(sd, "%s_b.png" % n))
            if fp is not None:
                rows[n]["footprint"] = round(fp, 3)
            if i % 10 == 0:
                print("  measured %d/%d" % (i, len(names)), flush=True)
        if failed:
            print("[register_energy] %d FAILED to render or measure (their energy is UNKNOWN, not fine):"
                  % len(failed))
            for f in failed:
                print("    " + f)
        data = {"_regenerate": REGEN,
                "_basis": "each register rendered as VIDEO at its own DURATION with its DEFAULT props, 16:9",
                "_floors": floors(),
                # RECORDED, not just printed. A register that failed to render has no energy reading, and an
                # absent row in a ranking reads as "fine" — the exact silent-improvement failure band_debt.py
                # refuses. Keeping the names in the artifact makes the hole visible to whoever reads it next.
                "_failed": sorted(failed),
                "registers": dict(sorted(rows.items()))}
        if not only:
            json.dump(data, open(MANIFEST, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            print("[register_energy] wrote %s" % MANIFEST)

    regs = data["registers"]
    fl = data["_floors"]
    unknown = data.get("_failed") or []
    def fails(r):
        return ((r["motion_p75"] < fl["motion_p75"]) + (r["ink_median"] < fl["ink_median"])
                + (r["luma_range"] < fl["luma_range"]))

    def why(r):
        """Which KIND of empty, when it is empty. The two need opposite fixes, so naming one is the
        difference between directable work and a number."""
        if r["ink_median"] >= fl["ink_median"]:
            return ""
        fp = r.get("footprint")
        if fp is None:
            return "?"
        return "small" if fp < FOOTPRINT_SPLIT else "flat"
    ranked = sorted(regs.items(), key=lambda kv: (-fails(kv[1]), kv[1]["motion_p75"]))
    n3 = sum(1 for _, r in ranked if fails(r) == 3)
    n2 = sum(1 for _, r in ranked if fails(r) == 2)
    n1 = sum(1 for _, r in ranked if fails(r) == 1)
    n0 = sum(1 for _, r in ranked if fails(r) == 0)
    print("\n[register_energy] %d registers · floors motion %.4f / ink %.0f%% / light %.3f"
          % (len(regs), fl["motion_p75"], fl["ink_median"] * 100, fl["luma_range"]))
    if unknown:
        print("[register_energy] %d register(s) UNMEASURED — absent from the ranking below, not passing it: %s"
              % (len(unknown), ", ".join(u.split(" ")[0] for u in unknown)))
    print("[register_energy] under all three: %d · two: %d · one: %d · clear: %d" % (n3, n2, n1, n0))
    print("\n%-24s %8s %7s %7s %7s  %-4s %s"
          % ("register", "motion", "ink", "light", "footprnt", "why", "under"))
    for n, r in ranked[:40]:
        marks = "".join(m for m, bad in (("M", r["motion_p75"] < fl["motion_p75"]),
                                         ("D", r["ink_median"] < fl["ink_median"]),
                                         ("L", r["luma_range"] < fl["luma_range"])) if bad)
        print("%-24s %8.4f %6.1f%% %7.3f %7s  %-4s %s"
              % (n, r["motion_p75"], r["ink_median"] * 100, r["luma_range"],
                 "-" if r.get("footprint") is None else "%.0f%%" % (r["footprint"] * 100),
                 why(r), marks or "-"))
    return 1 if unknown else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
