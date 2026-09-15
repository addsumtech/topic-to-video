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
"""
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


def prop_pair(name):
    """(A, B, how different they are 0..1). B is identically shaped and carries different words."""
    a, _ = cq.cjk_props(name)
    b, _ = cq.cjk_props(name, offset=OFFSET)
    if not a:
        return None, None, 0.0
    same = sum(1 for k in a if json.dumps(a.get(k), ensure_ascii=False, sort_keys=True)
               == json.dumps(b.get(k), ensure_ascii=False, sort_keys=True))
    return a, b, 1.0 - (same / max(1, len(a)))


def _still(name, props, out_png, frame, dna):
    pf = out_png + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(dict(props, dna=dna), fh, ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", name, out_png,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=_REMOTION, capture_output=True, text=True)
    return r.returncode == 0


def reach_of(name, dna=DEFAULT_DNA, tmp=None, durs=None):
    """(reach, prop_diff) — or (None, prop_diff) when it could not be measured."""
    a, b, diff = prop_pair(name)
    if a is None:
        return None, diff
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return None, diff
    own = tmp is None
    tmp = tmp or tempfile.mkdtemp(prefix="prop_reach_")
    durs = durs if durs is not None else re_mod.durations()
    frame = int(durs.get(name, 150) * FRAME_FRAC)
    pa = os.path.join(tmp, "%s_a.png" % name)
    pb = os.path.join(tmp, "%s_b.png" % name)
    try:
        ev = cq.evidence_props()
        if name in ev:
            a, b = dict(a, **ev[name]), dict(b, **ev[name])
        if not _still(name, a, pa, frame, dna) or not _still(name, b, pb, frame, dna):
            return None, diff

        def grey(p):
            return np.asarray(Image.open(p).convert("L"), dtype=np.float32) / 255.0

        ga, gb = grey(pa), grey(pb)
        ia = np.abs(ga - np.median(ga)) > 0.10
        ib = np.abs(gb - np.median(gb)) > 0.10
        union = int((ia | ib).sum())
        if union < 500:                      # an empty frame has no reach to report, only a hole
            return None, diff
        # PIXELS THAT ACTUALLY CHANGED, over the inked area — not the XOR of two ink MASKS, which was the
        # first version and was blind to the thing it most needed to see. A mask XOR only counts pixels that
        # crossed the ink threshold, so a register with a textured or filled ground reports 0.000 while its
        # words visibly move: `Inscription` carves its lines into stone, 35% of its frame passes the ink
        # test either way, and moving every line changed shade without flipping a single boolean. Measured
        # against the rendered pair, the mask XOR said 0.000 and the frames differ by 6.7 grey levels on
        # average. Comparing the IMAGES instead reports 0.181 there and leaves the furniture cases where
        # they were (BentoReveal 0.094, PortRail 0.094, TermTable 0.863).
        return float(int((np.abs(ga - gb) > CHANGE_THR).sum()) / union), diff
    finally:
        if own:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


def stale(data):
    """[(register, why)] — the same shape and the same reason as register_energy.stale."""
    now = {n: re_mod.source_hash(n) for n in
           (f[:-4] for f in os.listdir(_SHOTS) if f.endswith(".tsx"))}
    rows, was, out = data.get("registers") or {}, data.get("_source") or {}, []
    for n in sorted(rows):
        if n not in now:
            out.append((n, "the register is gone"))
        elif n not in was:
            out.append((n, "measured before source hashes were recorded"))
        elif was[n] != now[n]:
            out.append((n, "source changed since it was measured"))
    for n in sorted(set(now) - set(rows)):
        out.append((n, "never measured"))
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
        print("[prop_reach] %s  %d of %d row(s) no longer describe their source"
              % ("FAIL" if rows else "OK", len(rows), len(data.get("registers") or {})))
        return 1 if rows else 0
    if "--report" in argv:
        data = json.load(open(MANIFEST, encoding="utf-8"))
    else:
        only = _c.argflag_list(argv, "only")
        dna = _c.argflag(argv, "dna", DEFAULT_DNA)
        durs = re_mod.durations()
        names = [f[:-4] for f in sorted(os.listdir(_SHOTS)) if f.endswith(".tsx")]
        if only:
            missing = [n for n in only if n not in names]
            if missing:
                print("[prop_reach] --only names %d register(s) that do not exist: %s"
                      % (len(missing), ", ".join(missing)))
                return 2
            names = [n for n in names if n in only]
        cq.ensure_cjk_font() if hasattr(cq, "ensure_cjk_font") else None
        rows, untrusted, failed, hashes = {}, [], [], {}
        tmp = tempfile.mkdtemp(prefix="prop_reach_")
        try:
            for i, n in enumerate(names, 1):
                hashes[n] = re_mod.source_hash(n)
                r, diff = reach_of(n, dna, tmp, durs)
                if r is None:
                    failed.append(n)
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
                "_failed": sorted(failed),
                "_source": {n: h for n, h in hashes.items() if n in rows},
                "registers": dict(sorted(rows.items()))}
        if only and os.path.exists(MANIFEST):
            prev = json.load(open(MANIFEST, encoding="utf-8"))
            merged = dict(prev.get("registers") or {}); merged.update(rows)
            src = dict(prev.get("_source") or {}); src.update({n: h for n, h in hashes.items() if n in rows})
            data["registers"] = dict(sorted(merged.items()))
            data["_source"] = src
            data["_untrusted"] = sorted(set(prev.get("_untrusted") or []) - set(names) | set(untrusted))
            data["_failed"] = sorted(set(prev.get("_failed") or []) - set(names) | set(failed))
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
    print("\n[prop_reach] %d of %d register(s) under %.2f — their picture is furniture; a beat may give them "
          "a title, not a list of things that must read as different"
          % (len(low), len(regs), data.get("_low_reach", LOW_REACH)))
    if data.get("_failed"):
        print("[prop_reach] %d could not be measured (empty frame or render failure): %s"
              % (len(data["_failed"]), ", ".join(data["_failed"][:8])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
