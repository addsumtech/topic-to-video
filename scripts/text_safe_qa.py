#!/usr/bin/env python3
"""Is any TYPE being cut off by the frame? — asked of the DOM, per beat.

    python3 scripts/text_safe_qa.py <out_dir>      # audit this film's beats, with their real copy
    python3 scripts/text_safe_qa.py --library      # sweep every register at its default props

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
    sides = ", ".join("%s %spx" % (k, val) for k, val in sorted((v.get("out") or {}).items()))
    return "%r %s%s" % (v.get("text", ""), "cut off — " + sides if sides else "",
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


def scan_library(limit=None):
    durs = durations()
    names = sorted(durs)[: limit or None]
    tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "_textsafe_lib.png")
    findings = []
    for i, n in enumerate(names, 1):
        frame = int(round(rr.frame_at_t(durs[n], rr.SETTLED_T)))
        for v in audit_shot(n, {}, frame, tmp):
            findings.append("%s: %s" % (n, _describe(v)))
        if i % 20 == 0:
            print("  swept %d/%d" % (i, len(names)), flush=True)
    return findings, len(names)


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: text_safe_qa.py <out_dir> | --library")
        return 2
    if argv[0] == "--library":
        limit = next((int(a.split("=", 1)[1]) for a in argv if a.startswith("--limit=")), None)
        findings, n = scan_library(limit)
        scope = "%d registers at default props" % n
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
