#!/usr/bin/env python3
"""How much of a register's picture does the FILM actually author? — the measurement behind "adapt, don't text-swap".

    python3 scripts/prop_reach.py                  # sweep the library, write the manifest, print the ranking
    python3 scripts/prop_reach.py --only=A,B       # a few
    python3 scripts/prop_reach.py --report         # re-print from the manifest, render nothing
    python3 scripts/prop_reach.py --check          # which rows no longer describe their source (no renders)

WHY THIS EXISTS, and it is the sharpest failure this project has. A user looked at a delivered frame and
asked what a sparkline, a loading ring and a sine wave have to do with 路飞 and 哆啦A梦. Nothing: the beat
was `BentoReveal` with six cells labelled with six characters, and the cells' contents — bars / ring /
sparkline / dots / toggle — are chosen by INDEX inside the register and cannot be reached by any prop. The
film wrote six names onto someone else's dashboard. The next beat was the same shape: six IDENTICAL grey
cubes labelled Claude Code / Codex CLI / ChatGPT App, where the narration's whole claim was that these are
THREE KINDS of thing.

Every gate in this repo was green on both frames, because every gate measures TYPE — is it cut off
(`text_safe_qa`), was it drawn at all (`cjk_type_qa`), does the film move (`film_energy_qa`). None of them
can ask whether the PICTURE means what the beat means. The skill's own rule (§B2, `shot_adaptation`) says a
beat must KEEP the register's style and REDESIGN its modules for the topic, and the only thing standing
behind that rule was a free-text note written by the same agent that cast the beat — which in this case
said "the cells are the product's real characters" about a frame whose cells were a bar chart.

WHAT IT MEASURES, and it turns that judgement into a number. Render the register TWICE, at the same frame,
same DNA, same aspect — once with one prop set and once with a set that is identically SHAPED and carries
entirely different words (`cjk_type_qa.cjk_props(name, offset=)`). Then:

    reach = |{p : |A(p) - B(p)| > CHANGE_THR}| / |ink(A) OR ink(B)|

the fraction of the frame's inked area whose APPEARANCE changed because the film said something different.

THE FIRST VERSION XOR'd TWO INK MASKS and was blind to exactly what it most needed to see. A mask XOR only
counts pixels that crossed the ink threshold, so a register with a textured or filled ground scores 0.000
while its words visibly move: `Inscription` carves its lines into stone, 35% of its frame passes the ink
test either way, and rotating every line changed shade without flipping a single boolean. Rendered and
compared by hand, those two frames differ by 6.7 grey levels on average and the XOR reported them identical.
Comparing the IMAGES fixes it and leaves the furniture cases where they were:

    register            XOR (wrong)   change (used)
    Inscription             0.000         0.181     <- the bug: text moved, mask did not
    BentoReveal             0.008         0.094     <- the frame the user objected to
    PortRail                0.082         0.094     <- the same shape, found afterwards
    TermSpace               0.587         0.632
    KineticManifesto        0.688         0.830     <- a full-bleed accent flood, still mostly words
    TermTable               0.829         0.863

THIS NUMBER IS A READING AID FOR CASTING, NOT A GATE. Nothing fails on it. Turning it into a threshold was
the first plan and it was wrong twice over: the separation depends on how different the two prop sets are
(hand-written topic pairs put PortRail at 0.082, the fixture pairs at 0.094), and "these six items are drawn
as six copies" is a judgement about MEANING that no pixel statistic decides. The gate for that is the
independent shot-critic and `critic_ledger.py --final`; this is the fact that makes the casting decision an
informed one instead of a hopeful one.

A LOW NUMBER IS NOT A BAD REGISTER. `BentoReveal` is a correct register for "a product dashboard
assembling", and its furniture is the point. What the number says is what a beat may ASK of it: a register
at 0.008 can carry a title, and it cannot carry six items that are supposed to read as six different
things. That is a casting question, which is why `validate` reads this manifest at the beat level rather
than ranking registers against a quality bar.

WHAT IT CANNOT DO. It compares two prop sets, so it is only as honest as their difference: a register whose
two sets come out mostly identical (number props, shared object fixtures) is reported as UNTRUSTED rather
than as a low score, because "this register ignores its props" and "this register was never given two
different ones" are the same picture and opposite facts.

THE EXIT CODE IS ABOUT COVERAGE, NOT ABOUT FINDINGS. A low reach fails nothing — that judgement belongs to
the shot-critic, as above. But a register this sweep could not measure has no reading at all, and the run
used to exit 0 over nine of them while printing a headline that read as the whole library. So: 0 when every
register in the library has a row, 1 when any does not, with each one named and why.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c                                             # noqa: E402
import cjk_type_qa as cq                                         # noqa: E402
import register_energy as re_mod                                 # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")
_SHOTS = os.path.join(_REMOTION, "src", "shots")
MANIFEST = os.path.join(_REMOTION, "prop_reach.json")
REGEN = "python3 scripts/prop_reach.py"
_USAGE = "usage: prop_reach.py [--only=A,B | --only A,B] [--dna=NAME] [--report] [--check]"

DEFAULT_DNA = "product"
OFFSET = 2                 # how far the second prop set is rotated through every role pool
FRAME_FRAC = 0.88          # the settled frame, the same one cjk_type_qa samples
# A prop set pair that is this alike says nothing about the register — see the header's last paragraph.
MIN_PROP_DIFF = 0.5
# A pixel counts as CHANGED at this many grey levels — above camera/AA jitter, below a shade shift a viewer
# would call the same picture.
CHANGE_THR = 0.08
# The floor is NOT a quality bar. It is the point below which a beat must stop expecting its ITEMS to be
# drawn as different things, and it is set from the library's own distribution once the sweep has run.
LOW_REACH = 0.15          # a READING aid for casting, not a threshold anything fails on


def prop_diff(a, b):
    """How different two prop sets are, 0..1 — the share of A's props B does not repeat verbatim."""
    same = sum(1 for k in a if json.dumps(a.get(k), ensure_ascii=False, sort_keys=True)
               == json.dumps(b.get(k), ensure_ascii=False, sort_keys=True))
    return 1.0 - (same / max(1, len(a)))


def prop_pair(name):
    """(A, B, how different they are 0..1). B is identically shaped and carries different words."""
    a, _ = cq.cjk_props(name)
    b, _ = cq.cjk_props(name, offset=OFFSET)
    if not a:
        return None, None, 0.0
    return a, b, prop_diff(a, b)


def _still(name, props, out_png, frame, dna):
    """(ok, why). The REASON is carried home: `returncode == 0` alone turned a register that threw, a
    register whose fixture 404'd and a register rendered past its last frame into one word, "failed"."""
    pf = out_png + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(dict(props, dna=dna), fh, ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", name, out_png,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=_REMOTION, capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(out_png):
        return True, None
    return False, _c.render_error(r.stdout, r.stderr)


def reach_of(name, dna=DEFAULT_DNA, tmp=None, durs=None):
    """(reach, prop_diff, why) — `reach` is None when it could not be measured, and `why` says WHICH of the
    five ways, in the words of whatever refused."""
    try:
        a, b, diff = prop_pair(name)
    except Exception as exc:                             # noqa: BLE001 — an unreadable type is an answer
        # ...AND IT USED TO KILL THE SWEEP. `cjk_props` parses a register's own prop type; one it cannot
        # read raised here, out of a loop with no guard, and 160 measured rows died with it.
        return None, 0.0, "its prop type could not be read, so no two prop sets could be shaped: %s" % exc
    if a is None:
        return None, diff, ("no prop set could be shaped from its type — there is nothing for a film to "
                            "say differently, so there is no reach to measure")
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return None, diff, "numpy/Pillow are not installed, so no pixels could be compared"
    durs = durs if durs is not None else re_mod.durations()
    if name not in durs:
        return None, diff, ("no `export const DURATION` — the settled frame is a fraction of it, and a "
                            "guessed 150 is past the end of any register shorter than that")
    own = tmp is None                        # ...created AFTER the early returns, or a spot check leaks one
    tmp = tmp or tempfile.mkdtemp(prefix="prop_reach_")
    # Clamped to a frame the register HAS. A fraction of its own duration already is, but the clamp is what
    # makes that true rather than nearly true, and `remotion still` refuses a frame past the end instead of
    # clamping it — which is how seven short registers went unmeasured in ink_contrast_qa's first sweep.
    frame = max(0, min(durs[name] - 1, int(durs[name] * FRAME_FRAC)))
    pa = os.path.join(tmp, "%s_a.png" % name)
    pb = os.path.join(tmp, "%s_b.png" % name)
    try:
        ev = fixtures()
        if name in ev:
            a, b = dict(a, **ev[name]), dict(b, **ev[name])
            # THE DIFFERENCE IS BETWEEN THE PROPS ACTUALLY FED, not the ones cjk_type_qa shaped. The fixture
            # overwrites a picture prop with the SAME stand-in in both sets, so a register whose content is
            # pictures is handed two nearly identical sets and scores a low reach that says nothing about
            # it — the exact case `_untrusted` exists to separate, defeated by measuring the wrong pair.
            diff = prop_diff(a, b)
        ok_a, why_a = _still(name, a, pa, frame, dna)
        if not ok_a:
            return None, diff, "refused to render (first prop set, frame %d): %s" % (frame, why_a)
        ok_b, why_b = _still(name, b, pb, frame, dna)
        if not ok_b:
            return None, diff, "refused to render (second prop set, frame %d): %s" % (frame, why_b)

        def grey(p):
            return np.asarray(Image.open(p).convert("L"), dtype=np.float32) / 255.0

        ga, gb = grey(pa), grey(pb)
        ia = np.abs(ga - np.median(ga)) > 0.10
        ib = np.abs(gb - np.median(gb)) > 0.10
        union = int((ia | ib).sum())
        if union < 500:                      # an empty frame has no reach to report, only a hole
            return None, diff, ("both renders are effectively EMPTY (%d inked pixels across the pair, "
                                "floor 500) — there is no picture to ask what the film authors of"
                                % union)
        # PIXELS THAT ACTUALLY CHANGED, over the inked area — not the XOR of two ink MASKS, which was the
        # first version and was blind to the thing it most needed to see. A mask XOR only counts pixels that
        # crossed the ink threshold, so a register with a textured or filled ground reports 0.000 while its
        # words visibly move: `Inscription` carves its lines into stone, 35% of its frame passes the ink
        # test either way, and moving every line changed shade without flipping a single boolean. Measured
        # against the rendered pair, the mask XOR said 0.000 and the frames differ by 6.7 grey levels on
        # average. Comparing the IMAGES instead reports 0.181 there and leaves the furniture cases where
        # they were (BentoReveal 0.094, PortRail 0.094, TermTable 0.863).
        return float(int((np.abs(ga - gb) > CHANGE_THR).sum()) / union), diff, None
    finally:
        if own:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


_FIXTURES = None


def fixtures():
    """`evidence_props()` once per process — the sweep calls it per register, and it parses every shot file.

    Cached because the same dict is now read twice per register (once to feed the render, once to hash what
    was fed) and re-parsing 175 `.tsx` files 350 times is how a correctness fix turns into a slowdown; this
    repo has already shipped one of those."""
    global _FIXTURES
    if _FIXTURES is None:
        _FIXTURES = cq.evidence_props()
    return _FIXTURES


def props_hash(name):
    """A row is a measurement of TWO INPUTS — the register's source, and the two prop sets it was fed. Only
    the first was ever hashed, and the second is not a constant: `cjk_props` is a fixture GENERATOR whose
    reader changes. On 2026-09-15 that reader stopped being blind in five ways at once and 24 of 166
    registers began receiving props they had never been given — `MadeOf` 1 prop of 5 before, `AcceptanceStamp`
    none of 4. Every one of their reach numbers became meaningless and `--check` reported the manifest clean,
    because not one `.tsx` had changed.

    Hashing the FED PROPS rather than the generator's source is exact and costs nothing: computing them
    requires no render. Hashing the module instead would invalidate all 161 rows on any edit to any part of
    `cjk_type_qa` — the over-broad dep-hash that `open-work.md` D1 accepts for `register_energy` only because
    there it cannot be made exact. Here it can.

    ...AND THE PROPS ACTUALLY FED INCLUDE THE EVIDENCE FIXTURE. `reach_of` overlays `evidence_props()` onto
    both sets before rendering, so six registers' stills are drawn from an artefact that appears nowhere in
    `cjk_props` — re-capture the page and both frames move while neither this hash nor `_source` does. The
    artefact hash is taken from `register_energy.fed_hash`, fed THIS sweep's own fixture dict, so there is
    one definition of "hash an artefact set" rather than a second copy to drift from it."""
    try:
        a = cq.cjk_props(name, 0)[0]
        b = cq.cjk_props(name, OFFSET)[0]
    except Exception:                                      # noqa: BLE001 — unreadable is its own answer
        return "unreadable"
    blob = json.dumps([a, b], sort_keys=True, ensure_ascii=False, default=str)
    h = hashlib.sha256(blob.encode("utf-8"))
    fed = re_mod.fed_hash(name, fixtures())
    if fed:
        h.update(("|fed:" + fed).encode())
    return h.hexdigest()[:16]


def universe():
    """EVERY register this sweep claims to cover, parsed from the shots directory — never a list."""
    return sorted(f[:-4] for f in os.listdir(_SHOTS) if f.endswith(".tsx"))


def failures(data):
    """{register: why} as the manifest recorded them. Reads both shapes: `_failed` was a bare list of
    NAMES, which is the same silence as "skipped" — a reader could see that five registers had no row and
    not one word about what happened to any of them."""
    f = data.get("_failed")
    if isinstance(f, dict):
        return dict(f)
    return {n: "recorded as unmeasurable before this sweep kept reasons — re-run to find out why"
            for n in (f or [])}


def stale(data):
    """[(register, why)] — the same shape and the same reason as register_energy.stale, plus the fixture."""
    now = {n: re_mod.source_hash(n) for n in universe()}
    rows, was, out = data.get("registers") or {}, data.get("_source") or {}, []
    re_mod.ensure_fixture()                                # a fresh install draws it first (register_energy.stale)
    fed = data.get("_props") or {}
    failed = failures(data)
    for n in sorted(rows):
        if n not in now:
            out.append((n, "the register is gone"))
        elif n not in was:
            out.append((n, "measured before source hashes were recorded"))
        elif was[n] != now[n]:
            out.append((n, "source changed since it was measured"))
        elif n not in fed:
            out.append((n, "measured before the FIXTURE was hashed — the props it was fed are unknown"))
        elif fed[n] != props_hash(n):
            out.append((n, "the fixture now feeds it different props than it was measured with"))
    for n in sorted(set(now) - set(rows)):
        # A REGISTER THE SWEEP TRIED AND COULD NOT MEASURE IS NOT ONE IT NEVER LOOKED AT. Both reach this
        # branch — no row — and printing "never measured" over a recorded refusal throws away the only
        # thing anyone could act on. Five of the nine here were of the second kind.
        out.append((n, failed.get(n) and "could not be measured: " + failed[n] or "never measured"))
    return out


def load(strict=True):
    """{register: reach} from the committed sweep, refusing a stale or missing manifest."""
    if not os.path.exists(MANIFEST):
        raise RuntimeError("no %s — run `%s`; this reads measured pixels, never an opinion about a "
                           "register" % (MANIFEST, REGEN))
    d = json.load(open(MANIFEST, encoding="utf-8"))
    if strict:
        bad = stale(d)
        if bad:
            raise RuntimeError("%s is STALE for %d register(s) (%s…) — re-run `%s`"
                               % (MANIFEST, len(bad), ", ".join(n for n, _ in bad[:4]), REGEN))
    return {k: v["reach"] for k, v in (d.get("registers") or {}).items() if v.get("reach") is not None}


def main(argv):
    _c.refuse_unknown(argv, valued=("only", "dna"), switches=("report", "check"), usage=_USAGE)
    if "--check" in argv:
        data = json.load(open(MANIFEST, encoding="utf-8"))
        rows = stale(data)
        for n, why in rows:
            print("[prop_reach] STALE %-24s %s" % (n, why))
        # "166 of 161" — the two categories were being added together and then compared against one of
        # them. A register that was NEVER measured has no row to be stale, and reporting it inside the row
        # count makes the total exceed the manifest's size, which reads as a bug in the check rather than
        # as the two real facts it is stating.
        measured = data.get("registers") or {}
        absent = {n: why for n, why in rows if n not in measured}
        print("[prop_reach] %s  %d of %d measured row(s) no longer describe what they measured%s"
              % ("FAIL" if rows else "OK", len(rows) - len(absent), len(measured),
                 "; %d register(s) have no row at all" % len(absent) if absent else ""))
        univ = universe()
        _c.coverage("prop_reach", len([n for n in measured if n in set(univ)]), len(univ), absent)
        return 1 if rows else 0
    if "--report" in argv:
        data = json.load(open(MANIFEST, encoding="utf-8"))
    else:
        only = _c.argflag_list(argv, "only")
        dna = _c.argflag(argv, "dna", DEFAULT_DNA)
        durs = re_mod.durations()
        names = universe()
        if only:
            missing = [n for n in only if n not in names]
            if missing:
                print("[prop_reach] --only names %d register(s) that do not exist: %s"
                      % (len(missing), ", ".join(missing)))
                return 2
            names = [n for n in names if n in only]
        cq.ensure_cjk_font() if hasattr(cq, "ensure_cjk_font") else None
        rows, untrusted, failed, hashes = {}, [], {}, {}
        tmp = tempfile.mkdtemp(prefix="prop_reach_")
        try:
            for i, n in enumerate(names, 1):
                hashes[n] = re_mod.source_hash(n)
                try:
                    r, diff, why = reach_of(n, dna, tmp, durs)
                except Exception as exc:                 # noqa: BLE001 — one register, not the sweep
                    # A SWEEP IS TWENTY MINUTES OF RENDERS. An unreadable PNG or a fixture that throws
                    # used to take the other 169 measurements down with it, and an aborted sweep leaves
                    # the manifest describing whatever it described yesterday.
                    r, diff, why = None, 0.0, "the sweep itself raised on this register: %r" % (exc,)
                if r is None:
                    failed[n] = why or "unmeasurable, and the sweep recorded no reason"
                    print("  [%3d/%d] %-24s NOT MEASURED — %s" % (i, len(names), n, failed[n]), flush=True)
                else:
                    rows[n] = {"reach": round(r, 3), "prop_diff": round(diff, 2)}
                    if diff < MIN_PROP_DIFF:
                        untrusted.append(n)
                if i % 10 == 0:
                    print("  measured %d/%d" % (i, len(names)), flush=True)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        data = {"_regenerate": REGEN,
                "_what": "fraction of a register's ink that MOVES when every prop it can read changes — "
                         "how much of the picture the FILM authors, not the register",
                "_dna": dna, "_offset": OFFSET, "_frame_frac": FRAME_FRAC,
                "_low_reach": LOW_REACH, "_min_prop_diff": MIN_PROP_DIFF,
                "_untrusted": sorted(untrusted),
                # {name: why}, not a list of names: "5 could not be measured (empty frame or render
                # failure)" is a guess between two opposite facts, printed because the sweep threw the
                # actual message away.
                "_failed": dict(sorted(failed.items())),
                "_universe": len(universe()),
                "_source": {n: h for n, h in hashes.items() if n in rows},
                "_props": {n: props_hash(n) for n in rows},
                "registers": dict(sorted(rows.items()))}
        if only and os.path.exists(MANIFEST):
            prev = json.load(open(MANIFEST, encoding="utf-8"))
            merged = dict(prev.get("registers") or {}); merged.update(rows)
            src = dict(prev.get("_source") or {}); src.update({n: h for n, h in hashes.items() if n in rows})
            fed = dict(prev.get("_props") or {}); fed.update({n: props_hash(n) for n in rows})
            # A REGISTER THIS RUN COULD NOT MEASURE MUST LOSE ITS OLD ROW. Merging only what succeeded left
            # the previous number in place beside a fresh failure line, so the manifest said both "0.094"
            # and "unmeasurable" about the same register and the coverage count believed the row.
            for n in failed:
                merged.pop(n, None); src.pop(n, None); fed.pop(n, None)
            data["registers"] = dict(sorted(merged.items()))
            data["_source"] = src
            data["_props"] = fed
            data["_untrusted"] = sorted(set(prev.get("_untrusted") or []) - set(names) | set(untrusted))
            kept = {n: w for n, w in failures(prev).items() if n not in names}
            data["_failed"] = dict(sorted(dict(kept, **failed).items()))
        json.dump(data, open(MANIFEST, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("[prop_reach] wrote %s (%d rows%s)" % (MANIFEST, len(data["registers"]),
                                                     ", merged" if only else ""))

    regs = data.get("registers") or {}
    ranked = sorted(regs.items(), key=lambda kv: kv[1]["reach"])
    print("\n  register            reach   the film authors this much of the frame")
    for n, v in ranked[:14]:
        mark = "  UNTRUSTED (two prop sets too alike)" if n in (data.get("_untrusted") or []) else ""
        print("  %-20s %.3f  %-22s%s" % (n, v["reach"], "█" * int(v["reach"] * 20), mark))
    low = [n for n, v in ranked if v["reach"] < data.get("_low_reach", LOW_REACH)
           and n not in (data.get("_untrusted") or [])]
    print("\n[prop_reach] %d of %d MEASURED register(s) under %.2f — their picture is furniture; a beat may "
          "give them a title, not a list of things that must read as different"
          % (len(low), len(regs), data.get("_low_reach", LOW_REACH)))
    # THE COVERAGE, against the library rather than against the table. "36 of 161" was printed over a
    # 170-register library, and nine of those registers had no row: five the sweep tried and lost, four it
    # never reached. Both read as 161 being all there is.
    gaps = dict(failures(data))
    for n in universe():
        if n not in regs and n not in gaps:
            gaps[n] = "never swept — this manifest has no row for it and no recorded failure"
    univ = universe()
    k = _c.coverage("prop_reach", len([n for n in regs if n in set(univ)]), len(univ), gaps)
    # ADVISORY ON ITS FINDINGS, NEVER ON ITS COVERAGE. Nothing fails on a low reach — that judgement belongs
    # to the shot-critic, and the header says so. But "I could not measure this" is not a reading about a
    # register, it is the absence of one, and exiting 0 over it is how a hole reads as a clean sweep.
    return 1 if k else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
