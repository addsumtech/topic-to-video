#!/usr/bin/env python3
"""Is any TYPE being cut off by the frame? — asked of the DOM, per beat.

    python3 scripts/text_safe_qa.py <out_dir>      # audit this film's beats, with their real copy
    python3 scripts/text_safe_qa.py --library      # sweep every register (dna=product, the themed path)
    python3 scripts/text_safe_qa.py --library --aspect=9:16     # ...at the aspect the film actually ships at
    python3 scripts/text_safe_qa.py --library --only=Id,Id      # iterate on one finding without 160 renders
    python3 scripts/text_safe_qa.py --library --all-aspects     # every aspect the renderer offers
    python3 scripts/text_safe_qa.py --library --cjk             # ...with CHINESE copy, not the demo strings
    python3 scripts/text_safe_qa.py --library --all-dna         # ...in every FACE the renderer offers

WHY THIS REPLACES A PIXEL GATE. `frame_safe_qa.py`'s EDGE-BLEED check asks how much ink sits in the outer
border and calls a high answer an overflow. Measured on real cases, it is INVERTED:

    genuinely cut by the canvas   AtomOrbital 1.45%   BlockAssembly 1.00%   (its 4.5% ERROR floor: all pass)
    deliberately full-bleed       FlowField 9.6%   GameOfLife 12.7%   AuroraFlow 14.1%   HalftonePop 35.2%
                                  (all four blocked)

It would also refuse 100% of the sampled frames of OpenAI's launch film, 57% of Figma's and 57% of
Anthropic's, while passing all 30 frames of a film that measured as inert. The inversion is structural: a cut
word makes a THIN band and a flood makes a SOLID field, so coverage runs opposite to the defect. Moving the
threshold cannot fix a sign error. Two structural statistics were tried on the same samples (run structure
along the border; row-occupancy of border ink) and neither separated the classes.

The browser has the answer exactly. `remotion/src/runtime/textSafe.tsx` walks the DOM at the settled frame,
intersects each text element's box with any ancestor that CLIPS, and reports what still crosses the canvas.

DELIBERATE CROPS ARE NOT FINDINGS, and no flag is needed to say so: text clipped by an `overflow: hidden`
ancestor SMALLER than the frame is a marquee, a mask, a crop window — the author built the container, and the
container is the intent. Text cut by the canvas with no such ancestor is a layout that did not fit. (A
container the size of the frame is the frame, not a crop; Remotion's own AbsoluteFill sets `overflow: hidden`,
and the first version of this audit exempted every register in the library by counting it.)
"""
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_remotion as rr                                     # noqa: E402  (needs the path above)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REMOTION = os.path.join(_ROOT, "remotion")
_SHOTS = os.path.join(_REMOTION, "src", "shots")
TAG = "TEXT-SAFE-VIOLATIONS "


def durations():
    out = {}
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        m = re.search(r"export const DURATION\s*=\s*(\d+)", open(f, encoding="utf-8").read())
        if m:
            out[os.path.basename(f)[:-4]] = int(m.group(1))
    return out


def audit_shot(shot, props, frame, tmp_png):
    """Render one shot with the audit armed. Returns [] (clean) or the violation list it reported.

    Props travel by FILE, never on the command line: a beat's real copy is routinely CJK, and a multibyte
    character in a --props argument breaks the arg before remotion ever sees it.
    """
    payload = dict(props or {})
    payload["textSafe"] = True
    pf = tmp_png + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, allow_nan=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, tmp_png,
                        "--frame=%d" % frame, "--gl=angle", "--log=error",
                        "--props=" + os.path.abspath(pf)],
                       capture_output=True, text=True, cwd=_REMOTION)
    blob = (r.stdout or "") + (r.stderr or "")
    if TAG in blob:
        # The payload arrives inside a render-cancelling error, wrapped in a stack trace. Let the JSON parser
        # find its own end: a hand-rolled bracket counter closes early on a ']' inside a string, and a beat's
        # copy is exactly where such a character shows up. (A test drove that bug out.)
        raw = blob.split(TAG, 1)[1]
        try:
            found, _end = json.JSONDecoder().raw_decode(raw)
            return found
        except json.JSONDecodeError:
            return [{"text": "(unparseable payload)", "out": {}}]
    if r.returncode != 0:
        # A render that failed for another reason measured NOTHING. Reporting it as clean is how a gate
        # quietly stops gating; this surfaces as its own finding.
        return [{"text": "(render failed: %s)" % (blob.strip().splitlines() or ["?"])[-1][:160], "out": {}}]
    return []


def _describe(v):
    """Name the DEFECT, not just the string. A finding that prints a line of copy and a font size leaves the
    reader to work out what is wrong with it, and the two defects this audit reports want opposite fixes:
    text off the canvas is a layout that did not fit, text in the caption band is a layout that fit into
    space it does not own."""
    parts = []
    sides = ", ".join("%s %spx" % (k, val) for k, val in sorted((v.get("out") or {}).items()))
    if sides:
        parts.append("CUT OFF — " + sides)
    if v.get("band"):
        parts.append("IN THE CAPTION BAND by %spx — the burned caption draws over it" % v["band"])
    return "%r %s%s" % (v.get("text", ""), "; ".join(parts),
                        "  [%s]" % v["font"] if v.get("font") else "")


def scan_film(out_dir):
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = board.get("meta") or {}
    durs = durations()
    findings, checked = [], 0
    tmp = os.path.join(out_dir, "._textsafe.png")
    for i, s in enumerate(board.get("slides") or [], 1):
        shot = s.get("shot")
        if not shot or shot not in durs:
            continue
        props = dict(s.get("shot_props") or {})
        if meta.get("design_dna") is not None:
            props.setdefault("dna", meta["design_dna"])
        if meta.get("aspect"):
            props.setdefault("aspect", meta["aspect"])
        frame = int(round(rr.frame_at_t(durs[shot], rr.SETTLED_T)))
        checked += 1
        for v in audit_shot(shot, props, frame, tmp):
            findings.append("scene %02d (%s): %s" % (i, shot, _describe(v)))
    for p in (tmp, tmp + ".props.json"):
        if os.path.exists(p):
            os.remove(p)
    return findings, checked


DEFAULT_DNA = "product"


def scan_library(limit=None, aspect=None, dna=DEFAULT_DNA, only=None, cjk=False):
    """Sweep the catalogue. `aspect` matters: a register laid out for 16:9 can hold its type comfortably and
    still clip it at 9:16, which is the failure mode a portrait film meets and a landscape sweep never sees.

    `dna` matters for the same reason it does in register_energy.py: the Design DNA sets the type family and
    therefore every metric this audit measures, and EVERY delivered film has one. Sweeping with bare props
    measures the un-themed fallback, a mode no film ships."""
    durs = durations()
    # `--only` is for ITERATING on a finding. A sweep is 160 renders and ~10 minutes; fixing the 21 registers
    # the 1:1 sweep found meant either re-running all of it per edit or trusting the edit, and trusting the
    # edit is how a fix that moves the number without clearing the band gets committed. Names that are not
    # registers are named back, rather than silently sweeping nothing and printing OK.
    if only:
        unknown = [n for n in only if n not in durs]
        if unknown:
            raise SystemExit("[text_safe] not a register: %s" % ", ".join(unknown))
        names = sorted(only)
    else:
        names = sorted(durs)[: limit or None]
    tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "_textsafe_lib.png")
    base = {}
    if aspect:
        base["aspect"] = aspect
    if dna:
        base["dna"] = dna
    # The four evidence registers REFUSE to render without a real image (runtime/evidence.ts), so a bare
    # sweep reports them as four render failures — a true statement about the sweep and a useless one about
    # the registers. Same fixture the energy sweep uses, from the same parsed call sites: one definition.
    try:
        import register_energy as _re
        _re.ensure_fixture()
        evidence = _re.evidence_props()
    except Exception:
        evidence = {}
    # THE BAND WAS ONLY EVER CHECKED IN ENGLISH. This sweep feeds each register its own demo strings, which
    # are short Latin ones; `cjk_type_qa` feeds Chinese but asks a different question (does the type collide
    # with itself), and neither asked whether CHINESE copy lands in the caption band. Chinese is where it
    # would: a Han glyph is a full em wide, the leading floor is higher, so the same sentence takes more
    # lines and reaches further down. Same fixtures as the CJK gate — one definition of "what Chinese copy
    # for this register looks like", shaped from its own prop signature.
    cjk_fixture = {}
    if cjk:
        import cjk_type_qa as _cjk
        for n in names:
            try:
                props, _untestable = _cjk.cjk_props(n)
                cjk_fixture[n] = props
            except Exception:
                cjk_fixture[n] = {}
    findings = []
    for i, n in enumerate(names, 1):
        frame = int(round(rr.frame_at_t(durs[n], rr.SETTLED_T)))
        props = dict(base)
        props.update(cjk_fixture.get(n) or {})
        props.update(evidence.get(n) or {})
        for v in audit_shot(n, props, frame, tmp):
            findings.append("%s: %s" % (n, _describe(v)))
        if i % 20 == 0:
            print("  swept %d/%d" % (i, len(names)), flush=True)
    return findings, len(names)


def dna_presets():
    """The DNA names the renderer actually offers, read from runtime/dna.tsx rather than listed here — a
    list written in this file is a list that goes stale the day a preset is added."""
    src = open(os.path.join(_REMOTION, "src", "runtime", "dna.tsx"), encoding="utf-8").read()
    m = re.search(r"export const DNA_PRESETS[^=]*=\s*\{(.*?)\n\};", src, re.S)
    if not m:
        raise RuntimeError("could not read DNA_PRESETS from runtime/dna.tsx — the sweep cannot enumerate "
                           "the faces it is supposed to cover, and guessing the list is how it came to "
                           "sweep exactly one")
    names = re.findall(r"^\s*([A-Za-z0-9_]+)\s*:", m.group(1), re.M)
    if not names:
        raise RuntimeError("DNA_PRESETS parsed to an EMPTY list — see above")
    return names


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: text_safe_qa.py <out_dir> | --library")
        return 2
    if argv[0] == "--library" and "--all-dna" in argv:
        # THE SWEEP SWEPT ONE DNA, AND THE DNA IS WHAT CHOOSES THE FACE. `scan_library`'s own docstring says
        # the Design DNA "sets the type family and therefore every metric this audit measures" — and then
        # the sweep only ever ran `product`, whose display face is a narrow grotesque. Under `editorial`'s
        # serif, VariableTypeMorph's one enormous word was sliced at BOTH edges of a 1:1 frame while the
        # product sweep reported the register clean at all five aspects. A register that passes in one face
        # has been tested in one face. The list is READ from the renderer's own presets, so a ninth DNA is
        # covered the day it is added.
        rest = [a for a in argv if not a.startswith("--dna=") and a != "--all-dna"]
        worst = 0
        for name in dna_presets():
            print("## dna %s" % name, flush=True)
            worst = max(worst, main(rest + ["--dna=" + name]))
        return worst
    if argv[0] == "--library" and "--all-aspects" in argv:
        # THE LIBRARY WAS SWEPT AT TWO OF THE FIVE ASPECTS IT SHIPS. `--aspect` has existed since the
        # portrait work and 1:1, 4:5 and 4:3 had never been passed to it — the square sweep then found 21
        # registers drawing into the caption band, one of them ('DONE!' at 190px) by 81. The list is READ
        # from Root.tsx's ASPECTS rather than written here, so a sixth aspect is covered the day it is added
        # instead of the day someone remembers this file.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import _caption_band as _cb
        rest = [a for a in argv if not a.startswith("--aspect=") and a != "--all-aspects"]
        worst = 0
        for asp in _cb.aspect_table():
            print("### aspect %s" % asp, flush=True)
            worst = max(worst, main(rest + ["--aspect=" + asp]))
        return worst
    if argv[0] == "--library":
        limit = next((int(a.split("=", 1)[1]) for a in argv if a.startswith("--limit=")), None)
        aspect = next((a.split("=", 1)[1] for a in argv if a.startswith("--aspect=")), None)
        dna = next((a.split("=", 1)[1] for a in argv if a.startswith("--dna=")), DEFAULT_DNA)
        only = next((a.split("=", 1)[1].split(",") for a in argv if a.startswith("--only=")), None)
        cjk = "--cjk" in argv
        if dna in ("", "none"):
            dna = None
        findings, n = scan_library(limit, aspect, dna, only, cjk)
        scope = "%d registers at %s · dna=%s%s" % (n, "CJK fixtures" if cjk else "default props", dna or "none",
                                                   " · aspect %s" % aspect if aspect else "")
    else:
        findings, n = scan_film(os.path.abspath(argv[0]))
        scope = "%d beats" % n
    for f in findings:
        print("[text_safe] ERROR %s" % f)
    print("[text_safe] %s  %d finding(s) across %s"
          % ("FAIL" if findings else "OK", len(findings), scope))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
