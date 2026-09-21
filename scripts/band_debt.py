#!/usr/bin/env python3
"""Re-measure the caption-band / action-safe debt across every register, and rewrite the manifest.

    python3 scripts/band_debt.py --check      # measure and report the diff; writes nothing
    python3 scripts/band_debt.py --write      # ...and update remotion/band_debt.json
    python3 scripts/band_debt.py --check --only=A,B    # a spot check; NEVER writes, whatever else is passed

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
import hashlib
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


def universe():
    """EVERY register this sweep claims to cover, parsed from the shots directory — never a list."""
    return sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(_SHOTS, "*.tsx")))


def durations():
    out = {}
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        m = re.search(r"export const DURATION\s*=\s*(\d+)", open(f, encoding="utf-8").read())
        if m:
            out[os.path.basename(f)[:-4]] = int(m.group(1))
    return out


# THE TEXT MEASUREMENT HAS ITS OWN WAYS OF MEASURING NOTHING, and they arrive as ordinary findings.
# `text_safe_qa.audit_shot` reports a failed render and an unparseable payload as entries in the list it
# returns. `max([v.get("band") or 0 ...], default=0)` reads both as ZERO PX OF TYPE IN THE BAND, which is
# exactly the answer a clean register gives — so a register whose type could not be measured at all was
# recorded as carrying no text debt, in the manifest, indistinguishable from one that was measured and is
# clean.
def _audit_failure(viol):
    """The audit's own report that it measured NOTHING, or None.

    Told from a finding by SHAPE, not by a message restated here. A finding always names what is wrong with
    a piece of type: pixels off the canvas (`out`) or pixels down into the caption band (`band`). An entry
    carrying neither is the audit saying it could not look — and it says so in prose, which a copy of the
    prose in this file would stop matching the day someone rewords it.
    """
    for v in viol or []:
        if not (v.get("out") or v.get("band")):
            return str(v.get("text") or "the audit returned an entry with no measurement in it")
    return None


def _probe_key(name, props):
    """What the cached still and its audit DEPEND ON: the register's source (and the runtime it draws
    with), the DNA, and the props it was fed.

    `--stills DIR` defaults to a directory under $TMPDIR that SURVIVES between runs, and the reuse test was
    "does the png exist". So a register edited after a sweep was measured again from the previous sweep's
    pixels, and `--check` compared the new manifest against a picture that no longer exists — the same
    `a record nobody can tell is stale` failure this file was written to end, in its own cache.
    """
    try:
        import register_energy as _re
        src = _re.source_hash(name)
    except Exception as exc:                                   # noqa: BLE001
        src = "unhashable:%s" % exc
    blob = json.dumps([src, props], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def measure_all(png_dir, quiet=False, only=None):
    """Render every register at its settled frame into png_dir, then measure.

    Returns ({name: {band, edge, text}}, {name: why it was NOT measured}, [names actually measured]).

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
    names = [n for n in universe() if not only or n in only]
    not_measured = {}
    # NAMED, NOT DROPPED. A register exporting no DURATION has no settled frame, so it cannot be measured —
    # and it used to take the whole sweep down with a message listing five of them and eliding the rest.
    for n in list(names):
        if n not in durs:
            not_measured[n] = ("no `export const DURATION` — the settled frame is derived from it, so "
                               "there is no frame to measure this register at")
            names.remove(n)
    # The evidence registers REFUSE to render without a real image (runtime/evidence.ts), and a failed
    # render here is an unknown debt. Same drawn fixture the energy and text sweeps use, from the same
    # parsed call sites — and when that fixture cannot be built, SAY SO: swallowed, the four registers it
    # feeds simply fail to render and the sweep blames them for a hole in its own input.
    evidence, ev_err = {}, None
    try:
        import register_energy as _re
        _re.ensure_fixture()
        evidence = _re.evidence_props()
    except Exception as exc:                                   # noqa: BLE001
        ev_err = "the sweep could not build its evidence fixtures (%s), so this register had no picture " \
                 "to draw" % exc
    debt, measured = {}, []
    for i, n in enumerate(names):
        png = os.path.join(png_dir, n + ".png")
        side = png + ".textsafe.json"
        frame = int(round(rr.frame_at_t(durs[n], rr.SETTLED_T)))
        # The ARMED render first: it produces the png when the register is clean, so the common case costs
        # one render for both measurements rather than two. When it finds something it CANCELS the render
        # (that is the audit's only channel home) and no png exists — then, and only then, render again.
        props = dict(evidence.get(n) or {}); props["dna"] = DNA
        # ...AND THE CACHE IS KEYED ON WHAT THE PIXELS DEPEND ON, not on the file existing. See _probe_key.
        key, keyf = _probe_key(n, props), png + ".key"
        fresh = (os.path.exists(png) and os.path.exists(side) and os.path.exists(keyf)
                 and open(keyf, encoding="utf-8").read().strip() == key)
        if not fresh:
            for p in (png, side, keyf):
                if os.path.exists(p):
                    os.remove(p)
            viol = tsq.audit_shot(n, props, frame, png)
            json.dump(viol, open(side, "w", encoding="utf-8"), ensure_ascii=False)
        else:
            viol = json.load(open(side, encoding="utf-8"))
        why = _audit_failure(viol)
        if why:
            not_measured[n] = "its TYPE could not be measured — %s%s" % (
                why, "; " + ev_err if ev_err and n in (evidence or {}) else "")
            continue
        proc = None
        if not os.path.exists(png):
            proc = subprocess.run(["npx", "remotion", "still", "src/index.ts", n, png,
                                   "--frame=%d" % frame, "--gl=angle", "--log=error",
                                   "--props=" + json.dumps(props)],
                                  capture_output=True, text=True, cwd=os.path.join(_ROOT, "remotion"))
        if not os.path.exists(png):
            not_measured[n] = "refused to render at frame %d: %s%s" % (
                frame, _c.render_error(proc.stdout, proc.stderr) if proc else "no render was attempted",
                "; " + ev_err if ev_err else "")
            continue
        open(keyf, "w", encoding="utf-8").write(key)
        measured.append(n)
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
    # MEASURED, not ATTEMPTED. Returning the attempted list made the coverage line print "measured 170 of
    # 170 · 1 NOT measured", which is two statements that cannot both be true.
    return debt, not_measured, measured


def main(argv):
    if not ({"--check", "--write"} & set(argv)):
        print(__doc__.strip())
        return 2
    # Both spellings, and nothing silently ignored — `--stills DIR` used to write the frames somewhere the
    # caller never asked for, which is the mild end of the same family (scripts/_common.argflag).
    _c.refuse_unknown(argv, valued=("stills", "only"), switches=("check", "write"),
                      usage="usage: band_debt.py (--check | --write) [--only=A,B] "
                            "[--stills=DIR | --stills DIR]")
    png_dir = _c.argflag(argv, "stills",
                         os.path.join(os.environ.get("TMPDIR", "/tmp"), "band_debt_stills"))
    only = _c.argflag_list(argv, "only")
    if only:
        unknown = [n for n in only if n not in universe()]
        if unknown:
            print("[band_debt] --only names %d register(s) that do not exist: %s"
                  % (len(unknown), ", ".join(unknown)))
            return 2
    old = json.load(open(_MANIFEST, encoding="utf-8"))
    new, not_measured, swept = measure_all(png_dir, only=only)
    prev = old["registers"] if not only else {k: v for k, v in old["registers"].items() if k in only}

    gone = sorted(set(prev) - set(new))
    fresh = sorted(set(new) - set(prev))
    worse = [(n, prev[n], new[n]) for n in sorted(set(prev) & set(new))
             if new[n]["band"] > prev[n]["band"] + 0.5 or new[n]["edge"] > prev[n]["edge"] + 0.5
             or (new[n].get("text") or 0) > (prev[n].get("text") or 0)]
    # COVERAGE FIRST. "recorded 48, measured 51" counts DEBT ROWS, and a reader cannot tell whether 51 came
    # out of a 51-register sweep or a 170-register one — which is the whole question when a register drops
    # out of the manifest: fixed, or never looked at.
    _c.coverage("band_debt", len(swept), len(only or universe()), not_measured)
    print("[band_debt] of those, %d carry debt; the manifest records %d" % (len(new), len(prev)))
    for n in gone:
        print("  FIXED   %s (was band %.1f%% edge %.1f%%)" % (n, prev[n]["band"], prev[n]["edge"]))
    for n in fresh:
        print("  NEW     %s band %.1f%% edge %.1f%%%s"
              % (n, new[n]["band"], new[n]["edge"],
                 "  TEXT %spx into the band: %r" % (new[n]["text"], new[n]["says"]) if new[n].get("text") else ""))
    for n, o, w in worse:
        print("  GREW    %s band %.1f -> %.1f, edge %.1f -> %.1f" % (n, o["band"], w["band"], o["edge"], w["edge"]))

    if "--write" in argv:
        # A SPOT CHECK MUST NOT DESTROY THE RECORD, and here it would not even look like a loss: the
        # manifest is a list of registers IN DEBT, so writing a three-register sweep over it reads as 167
        # registers repaired. `measure_ground_reach` records the day a two-register method check replaced a
        # 149-shot sweep; this file had no --only at all, which is the other way to make it unrunnable.
        if only:
            print("[band_debt] REFUSING to write a --only sweep: the manifest is the whole library's debt, "
                  "and %d register(s) were measured. Re-run `%s` without --only." % (len(swept), REGEN))
            return 2
        # ...AND NEVER WRITE A MANIFEST WITH A HOLE IN IT. A register that could not be measured has an
        # UNKNOWN debt; written out, it is simply absent, which is the same shape as "repaired" and makes
        # the ratchet in tests/test_remotion.py read a hole as an improvement.
        if not_measured:
            print("[band_debt] REFUSING to write: %d register(s) were not measured (named above), so their "
                  "debt is unknown and dropping them from the manifest would read as FIXED."
                  % len(not_measured))
            return 2
        old["registers"] = dict(sorted(new.items()))
        old["_regenerate"] = REGEN
        old["_swept"] = {"registers": len(swept), "of": len(universe()),
                         "why": "the rows below are the registers IN DEBT; this is how many were measured "
                                "to find them, so a row that disappears can be told from one never looked at"}
        old["_measured_at"] = ("the frame useT() calls SETTLED (REDUCED_MOTION_T), derived per register from "
                               "its own exported DURATION — the frame every visual gate reads")
        json.dump(old, open(_MANIFEST, "w", encoding="utf-8"), indent=2, ensure_ascii=False, sort_keys=False)
        print("[band_debt] wrote %s" % _MANIFEST)
        return 0
    # A HOLE IS NOT A CLEAN CHECK. `fresh or worse` are findings; a register that could not be measured is
    # the absence of one, and it exited 0.
    return 1 if (fresh or worse or not_measured) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
