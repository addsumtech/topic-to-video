#!/usr/bin/env python3
"""clock_qa — find CONTINUOUS drivers that never complete a cycle within the beat they run in.

    python3 scripts/clock_qa.py                 # the confirmed findings
    python3 scripts/clock_qa.py --all           # ...and every candidate, for a human to judge
    python3 scripts/clock_qa.py --json          # machine-readable

WHY THIS EXISTS, AND WHY IT IS A SCRIPT RATHER THAN A LESSON. `useT()` returns 0→1 across the WHOLE clip,
so `Math.sin(t * 2)` delivers two radians of phase in five seconds — a third of one cycle. Written down it
looks like radians per second and it is nothing of the kind. Every register that has one was authored as
"this keeps breathing" and renders as a slow one-way drift, which is a large part of why this library
measures as frozen against the delivery gate.

Thirteen such oscillators were found by grepping `Math.sin(t *`, and the grep MISSED an entire second class
— drivers with no trig at all, like a conveyor's `(t * 0.85) % 1` or a helix's `spin = t * 2.4` — which had
to be found by grepping again, differently. A defect class that needs the right grep to be seen will be
missed by whoever adds register 153. This is that grep, made repeatable and made to state its reasoning.

THE HARD PART IS TELLING THE THREE CLASSES APART, because two of them are correct:

  SATURATING RAMP   `clamp01(t * 4)` on a title's opacity is a fade-in over the first quarter of the clip.
                    It is a reveal, not an oscillator, and k is how FAST it arrives. Never a finding.
  CYCLIC            `(t * k) % m` and `Math.sin(t * k)` repeat. Cycles per clip = k/m and k/2π. Under one,
                    the thing that was supposed to repeat never does. THE FINDING.
  RAW LINEAR        `spin = t * 26` is 26 of some unit the source does not name — degrees, radians, pixels.
                    Reported separately, with the number, for a human to judge: 26 degrees is a creep and
                    26 radians is four turns, and nothing in the text says which.

The modulus matters and reading past it is how a false finding is made: `NeonGrid`'s `(t * 0.6) % (1/16)`
looks like 0.6 of a cycle and is 9.6 of them.

AND "UNDER ONE CYCLE" IS NOT BY ITSELF A DEFECT — the first version of this file claimed it was and
over-reported immediately. `HoloFoil`'s `(t * 220) % 360` is 0.61 of a hue rotation and 220 degrees of
visible colour change; `SwissEditorial`'s `(t * 420) % 1000` is 0.42 of a loop and 420 pixels of ticker
travel. Whether an incomplete cycle is perceptible depends on the amplitude and on what it drives, and
neither is in the text. So the report is an INTERSECTION with measurement: a register whose frame difference
is under the delivery floor AND which contains a cyclic driver that never repeats. That pairs a symptom with
a specific cause, which is the only form of this finding worth acting on — and it is what the five fixed by
hand had in common. `--all` prints the unfiltered scan for a human who wants to judge the rest.

EVEN A CONFIRMED FINDING IS A CANDIDATE, NOT A WORK ORDER — this cost three reverted edits to learn. Of the
four material registers confirmed on the first run, only ONE improved when its driver was corrected:

    FrequencyEncode  0.00097 -> 0.00119 settled-half frame difference   (+23%, kept)
    SpectrumPulse    already swinging 94% of its mean with 8 direction changes in 2.2s — its low score
                     comes from THIN BARS, not from stillness; the correction changed nothing  (reverted)
    LiquidFill       +2%   (reverted)
    EmberFlame       -1%   (reverted)

A register can measure under the motion floor because the thing that moves is SMALL, which correcting a
clock cannot change; and a stalled driver can be one term among several where the others already carry the
motion. So: render the register before and after, measure the settled half, and keep the change only where
the number moves. An edit with no demonstrable gain is an edit with no reason.

AND THIS IS NOT THE LEVER FOR THE MOTION AXIS. Correcting a clock is a FIDELITY fix — the thing the author
wrote now actually happens — and across the registers corrected this way the median gain was a few percent
against a floor that needs multiples. What moved the delivery number was film-level: the camera bed
(depth.tsx bedPan) took a film from 0.0035 to 0.0042 on its own.
"""
import glob
import json
import math
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(_HERE, "..", "remotion", "src", "shots")

# k below this in a RAW LINEAR driver is worth a look whatever the unit: 1.5 degrees, radians or pixels
# across a whole beat is imperceptible in every one of them.
LINEAR_SUSPECT = 1.5


def _cycles_from_modulus(line, k, at):
    """`(t * k ...) % m` → k/m. The modulus can be a literal or a division like `1 / 16`."""
    m = re.match(r"\s*\)?\s*%\s*\(?\s*([0-9]*\.?[0-9]+)\s*(?:/\s*([0-9]*\.?[0-9]+))?\s*\)?", line[at:])
    if not m:
        return None
    mod = float(m.group(1))
    if m.group(2):
        mod /= float(m.group(2))
    return None if mod == 0 else k / mod


def scan_source(src, name):
    """[{register, line, k, kind, cycles, code}] for one shot file."""
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        code = line.split("//")[0]
        if not code.strip():
            continue
        for m in re.finditer(r"\bt\s*\*\s*([0-9]*\.?[0-9]+)", code):
            k = float(m.group(1))
            before = code[:m.start()]
            after_i = m.end()
            # SATURATING: the driver is inside a clamp01(...) — it arrives and stops. Not a cycle.
            if re.search(r"clamp01\s*\([^()]*$", before) or re.search(r"clamp01\s*\(\s*$", before):
                out.append({"register": name, "line": i, "k": k, "kind": "ramp",
                            "cycles": None, "code": code.strip()[:100]})
                continue
            cyc = _cycles_from_modulus(code, k, after_i)
            if cyc is not None:
                kind = "modulo"
            elif re.search(r"Math\.(sin|cos)\s*\([^()]*$", before):
                kind, cyc = "trig", k / (2 * math.pi)
            else:
                kind = "linear"
            out.append({"register": name, "line": i, "k": k, "kind": kind,
                        "cycles": None if cyc is None else round(cyc, 2), "code": code.strip()[:100]})
    return out


def scan_library(shots_dir=None):
    rows = []
    for f in sorted(glob.glob(os.path.join(shots_dir or SHOTS, "*.tsx"))):
        rows += scan_source(open(f, encoding="utf-8").read(), os.path.basename(f)[:-4])
    return rows


def findings(rows):
    """The two candidate classes, BEFORE measurement narrows them: a cyclic driver that never repeats, and a
    raw linear one small enough to be a creep in any unit."""
    stalled = [r for r in rows if r["kind"] in ("modulo", "trig") and (r["cycles"] or 0) < 1.0]
    creeping = [r for r in rows if r["kind"] == "linear" and r["k"] < LINEAR_SUSPECT]
    return stalled, creeping


def measured_motion():
    """{register: motion_p75} and the floor, from the energy sweep. None when it is absent or stale — a
    finding built on a stale measurement is worse than no finding."""
    try:
        import register_energy as reg
        data = json.load(open(reg.MANIFEST, encoding="utf-8"))
        if reg.stale(data):
            return None, None, "the sweep is STALE — run `python3 scripts/register_energy.py`"
        return ({n: r["motion_p75"] for n, r in data["registers"].items()},
                data["_floors"]["motion_p75"], None)
    except Exception as e:
        return None, None, "no usable sweep (%s) — run `python3 scripts/register_energy.py`" % e


def confirmed(rows, motion, floor):
    """The intersection: a register measured under the motion floor that also holds a driver authored to
    repeat and never repeating. Symptom paired with a named cause."""
    out = []
    for r in rows:
        if r["kind"] not in ("modulo", "trig") or (r["cycles"] or 0) >= 1.0:
            continue
        m = motion.get(r["register"])
        if m is not None and m < floor:
            out.append(dict(r, motion=m))
    return out


def main(argv):
    rows = scan_library()
    stalled, creeping = findings(rows)
    motion, floor, why = measured_motion()
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    hits = confirmed(rows, motion, floor) if motion else []
    if "--json" in argv:
        print(json.dumps({"confirmed": hits, "stalled": stalled, "creeping": creeping,
                          "measurement": why or "ok"}, ensure_ascii=False, indent=2))
        return 1 if hits else 0
    print("[clock_qa] %d drivers against `t`: %s" % (len(rows), ", ".join(
        "%s %d" % (k, v) for k, v in sorted(kinds.items()))))
    if motion is None:
        print("\n  NOT NARROWED BY MEASUREMENT: %s" % why)
    else:
        print("\nCONFIRMED — measured UNDER the %.4f motion floor, and holding a driver authored to repeat "
              "that never does:" % floor)
        for r in sorted(hits, key=lambda r: r["motion"]):
            print("    %-22s motion %.4f  L%-4d %.2f cycles/clip   %s"
                  % (r["register"], r["motion"], r["line"], r["cycles"], r["code"][:52]))
        if not hits:
            print("    none")
    if "--all" in argv:
        print("\nALL cyclic drivers under one cycle (NOT findings on their own — 0.61 of a hue rotation is "
              "220 degrees of visible colour):")
        for r in sorted(stalled, key=lambda r: r["cycles"] or 0):
            print("    %-22s L%-4d %.2f cycles   %s" % (r["register"], r["line"], r["cycles"], r["code"][:56]))
        print("\nALL raw linear drivers under %.1f — the unit is not in the source, so a human judges these:"
              % LINEAR_SUSPECT)
        for r in sorted(creeping, key=lambda r: r["k"]):
            print("    %-22s L%-4d k=%-6s %s" % (r["register"], r["line"], r["k"], r["code"][:56]))
    print("\nThe fix is `radians()` / `life()` in runtime/motion.ts: say the period in SECONDS, which is the "
          "unit a period is actually in. Both enforce a 3s floor by throwing.")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
