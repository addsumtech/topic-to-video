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
import _common as _c                                                  # noqa: E402
import render_remotion as rr                                    # noqa: E402  (needs the path above)
import shot_still_qa as q                                       # noqa: E402
import text_safe_qa as tsq                                      # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SHOTS = os.path.join(_ROOT, "remotion", "src", "shots")
_MANIFEST = os.path.join(_ROOT, "remotion", "band_debt.json")
REGEN = "python3 scripts/band_debt.py --write"
# Themed, for the reason register_energy.py records: the Design DNA sets the type family and therefore the
# geometry this measures, and EVERY delivered film has one. Measured bare, the manifest describes a fallback
# mode no film ships.
DNA = "product"


def durations():
    out = {}
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        m = re.search(r"export const DURATION\s*=\s*(\d+)", open(f, encoding="utf-8").read())
        if m:
            out[os.path.basename(f)[:-4]] = int(m.group(1))
    return out


def measure_all(png_dir, quiet=False):
    """Render every register at its settled frame into png_dir, then measure. Returns {name: {band, edge, text}}.

    THREE numbers, because two of them cannot see the worst case. `band`/`edge` are ink FRACTIONS, and a line
    of type is a tiny fraction of a 227px strip: CardStack3D sets its title wholly inside the caption band and
    measures 2.1%, under the threshold, while AuroraFlow — a generative field whose ground legitimately
    covers the frame — measures 53%. The instrument ranked the harmless case 25x above the fatal one, so a
    register that collides with every burned caption sat outside the manifest entirely.

    `text` is px of the register's own TYPE reaching down into that strip, asked of the DOM (textSafe.tsx)
    rather than of pixels. Any value at all is debt: unlike a ground, type in the band is not a look, it is
    two pieces of copy drawn on top of each other.
    """
    os.makedirs(png_dir, exist_ok=True)
    durs = durations()
    names = [os.path.basename(f)[:-4] for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx")))]
    missing = [n for n in names if n not in durs]
    if missing:
        raise RuntimeError("no exported DURATION for %s — the settled frame is derived from it" % missing[:5])
    # The four evidence registers REFUSE to render without a real image (runtime/evidence.ts), and
    # measure_all treats a failed render as an unknown debt and raises. Same drawn fixture the energy and
    # text sweeps use, from the same parsed call sites.
    try:
        import register_energy as _re
        _re.ensure_fixture()
        evidence = _re.evidence_props()
    except Exception:
        evidence = {}
    debt, failed = {}, []
    for i, n in enumerate(names):
        png = os.path.join(png_dir, n + ".png")
        side = png + ".textsafe.json"
        frame = int(round(rr.frame_at_t(durs[n], rr.SETTLED_T)))
        # The ARMED render first: it produces the png when the register is clean, so the common case costs
        # one render for both measurements rather than two. When it finds something it CANCELS the render
        # (that is the audit's only channel home) and no png exists — then, and only then, render again.
        props = dict(evidence.get(n) or {}); props["dna"] = DNA
        if not (os.path.exists(png) and os.path.exists(side)):
            viol = tsq.audit_shot(n, props, frame, png)
            json.dump(viol, open(side, "w", encoding="utf-8"), ensure_ascii=False)
        else:
            viol = json.load(open(side, encoding="utf-8"))
        if not os.path.exists(png):
            subprocess.run(["npx", "remotion", "still", "src/index.ts", n, png,
                            "--frame=%d" % frame, "--gl=angle", "--log=error",
                            "--props=" + json.dumps(props)],
                           capture_output=True, text=True, cwd=os.path.join(_ROOT, "remotion"))
        if not os.path.exists(png):
            failed.append(n)
            continue
        r = q.measure(png)
        in_band = max([v.get("band") or 0 for v in viol], default=0)
        if r["caption"] > q.CAPTION_FRAC_ERR or r["edge"] > q.EDGE_FRAC_ERR or in_band:
            debt[n] = {"band": round(r["caption"] * 100, 2), "edge": round(r["edge"] * 100, 2)}
            if in_band:
                # the piece of copy, so a reader can see WHAT collides without re-rendering
                worst = max(viol, key=lambda v: v.get("band") or 0)
                debt[n]["text"] = in_band
                debt[n]["says"] = (worst.get("text") or "")[:60]
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
    # Both spellings, and nothing silently ignored — `--stills DIR` used to write the frames somewhere the
    # caller never asked for, which is the mild end of the same family (scripts/_common.argflag).
    _c.refuse_unknown(argv, valued=("stills",), switches=("check", "write"),
                      usage="usage: band_debt.py (--check | --write) [--stills=DIR | --stills DIR]")
    png_dir = _c.argflag(argv, "stills",
                         os.path.join(os.environ.get("TMPDIR", "/tmp"), "band_debt_stills"))
    old = json.load(open(_MANIFEST, encoding="utf-8"))
    new = measure_all(png_dir)
    prev = old["registers"]

    gone = sorted(set(prev) - set(new))
    fresh = sorted(set(new) - set(prev))
    worse = [(n, prev[n], new[n]) for n in sorted(set(prev) & set(new))
             if new[n]["band"] > prev[n]["band"] + 0.5 or new[n]["edge"] > prev[n]["edge"] + 0.5
             or (new[n].get("text") or 0) > (prev[n].get("text") or 0)]
    print("[band_debt] recorded %d, measured %d" % (len(prev), len(new)))
    for n in gone:
        print("  FIXED   %s (was band %.1f%% edge %.1f%%)" % (n, prev[n]["band"], prev[n]["edge"]))
    for n in fresh:
        print("  NEW     %s band %.1f%% edge %.1f%%%s"
              % (n, new[n]["band"], new[n]["edge"],
                 "  TEXT %spx into the band: %r" % (new[n]["text"], new[n]["says"]) if new[n].get("text") else ""))
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
