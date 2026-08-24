#!/usr/bin/env python3
"""Scaffold and REGISTER a new bespoke shot at every sync point, in one command.

  python3 scripts/register_shot.py <Id> <FamilyLetter> --use-when "<one line>"
  python3 scripts/register_shot.py <Id> --check          # verify an existing shot is fully registered

WHY THIS EXISTS. The library can grow — `references/remotion-shot-authoring.md` has said so from the start
("build a NEW shot when the *structure* differs, not merely the sizing"). In practice it almost never did,
and the reason was friction, not permission: registering one shot by hand means editing `registry.ts`,
`Root.tsx`, `runtime/shotLuma.ts`, `shot_director.FAMILY` and `LIBRARY.md`, then re-measuring ground
luminance — five files and a gate, every one of which fails SILENTLY except the two that are tested. A
capability that costs that much is a capability nobody uses, so every beat got matched to one of the
existing registers whether or not one of them could actually carry its argument.

This makes it one command, so "no register can draw this" stops being a reason to settle.

AFTER RUNNING IT: write the shot's body (the stub renders its own name), then
  python3 scripts/measure_ground_luma.py --only <Id>      # sanity-check its ground
  python3 scripts/measure_ground_luma.py && … --apply-json # fold it into the measured table
  python3 scripts/shot_proof.py <out_dir> --stills         # frame-craft + palette + reuse checks
"""
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(_HERE, "..", "remotion")
_SHOTS = os.path.join(_REM, "src", "shots")

STUB = '''// SHOT · {id} — {use_when}
// A NEW register: the ARGUMENT SHAPE lives here, the topic arrives entirely through props, so any later
// film making the same kind of claim can reach for it. Replace this stub with the real design.

import React from 'react';
import {{AbsoluteFill, useVideoConfig}} from 'remotion';
import {{useT, seg, clamp01, easeOutCubic}} from '../runtime/motion';
import {{captionBand, CONTENT_TOP}} from '../runtime/layout';
import {{useDNA}} from '../runtime/dna';

export const DURATION = 150; // 5s
const BG_D0 = '#0a0f16', FG_D0 = '#e8eef6';

export const {id}: React.FC<{{title?: string}}> = ({{title: TITLE = '{id}'}} = {{}}) => {{
  const dna = useDNA();
  const t = useT();
  const {{width: W, height: H}} = useVideoConfig();
  const zoneBottom = H - captionBand(W, H);   // content must never enter the burned-caption band
  const inn = easeOutCubic(clamp01(seg(t, 0.05, 0.3)));
  return (
    <AbsoluteFill style={{{{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: dna?.fg ?? FG_D0}}}}>
      <div style={{{{position: 'absolute', top: (CONTENT_TOP + zoneBottom) / 2, left: 0, right: 0,
        textAlign: 'center', opacity: inn,
        font: `700 ${{Math.round(W * 0.03)}}px/1.2 var(--f-display, system-ui, sans-serif)`}}}}>{{TITLE}}</div>
    </AbsoluteFill>
  );
}};
export default {id};
'''


def _edit(path, checks, apply_fn, label):
    # `checks` must be NON-EMPTY: all(c in src for c in []) is vacuously True, so an empty list reported
    # "already registered" while doing nothing — which is exactly the silent-miss this script exists to stop.
    assert checks, "_edit(%s) needs at least one presence check" % label
    src = open(path, encoding="utf-8").read()
    if all(c in src for c in checks):
        return "already"
    new = apply_fn(src)
    if new is None:
        return "FAILED (anchor not found)"
    open(path, "w", encoding="utf-8").write(new)
    return "added"


def register(shot, family=None, use_when=""):
    out = {}
    tsx = os.path.join(_SHOTS, shot + ".tsx")
    if not os.path.exists(tsx):
        open(tsx, "w", encoding="utf-8").write(STUB.format(id=shot, use_when=use_when or "TODO: use when …"))
        out["src/shots/%s.tsx" % shot] = "created (stub)"
    else:
        out["src/shots/%s.tsx" % shot] = "already"

    # registry.ts — import + the exported map
    def _registry(s):
        if ("import {%s}" % shot) not in s:
            m = re.search(r"(import \{\w+\} from '\./shots/\w+';\n)(?!import)", s)
            if not m:
                return None
            s = s[:m.end()] + "import {%s} from './shots/%s';\n" % (shot, shot) + s[m.end():]
        m2 = re.search(r"\n(\s+)(\w+,\s*\w+,[^\n]*\n)(\};)", s)
        if m2:
            return s[:m2.start(3)] + "  %s,\n" % shot + s[m2.start(3):]
        return None
    out["registry.ts"] = _edit(os.path.join(_REM, "src", "registry.ts"),
                               ["import {%s}" % shot, "\n  %s,\n" % shot], _registry, "registry")

    # Root.tsx — import with a DURATION alias + the F() preview row
    alias = "D_" + shot.upper()[:10]

    def _root(s):
        if ("from './shots/%s'" % shot) not in s:
            m = re.search(r"(import \{\w+, DURATION as \w+\} from '\./shots/\w+';\n)", s)
            if not m:
                return None
            s = s[:m.end()] + "import {%s, DURATION as %s} from './shots/%s';\n" % (shot, alias, shot) + s[m.end():]
        if ("F('%s'" % shot) not in s:
            m2 = re.search(r"(\n\s+\{F\('\w+', \w+, \w+\)\})(?![\s\S]*\{F\(')", s)
            if not m2:
                return None
            s = s[:m2.end()] + "\n    {F('%s', %s, %s)}" % (shot, shot, alias) + s[m2.end():]
        return s
    out["Root.tsx"] = _edit(os.path.join(_REM, "src", "Root.tsx"),
                            ["from './shots/%s'" % shot, "F('%s'" % shot], _root, "root")

    # shotLuma.ts — the coarse map AND the measured table (declared 'bg' until measured for real)
    def _luma(s):
        if ("\n  %s: " % shot) not in s.split("DNA_GROUND_TOKEN")[0]:
            s = re.sub(r"(export const SHOT_LUMA[^{]*\{\n)", r"\g<1>  %s: 'dark',\n" % shot, s, count=1)
        tail = s.split("DNA_GROUND_TOKEN", 1)
        if len(tail) == 2 and ("\n  %s: " % shot) not in tail[1]:
            s = s.replace("DNA_GROUND_TOKEN", "DNA_GROUND_TOKEN", 1)
            m = re.search(r"(export const DNA_GROUND_TOKEN[^{]*\{\n)", s)
            if not m:
                return None
            s = (s[:m.end()] + "  %s: 'bg',   // declared on registration; run measure_ground_luma to confirm\n"
                 % shot + s[m.end():])
        return s
    out["shotLuma.ts"] = _edit(os.path.join(_REM, "src", "runtime", "shotLuma.ts"),
                               ["%s: 'dark'," % shot, "%s: 'bg'," % shot], _luma, "luma")

    # shot_director.FAMILY
    if family:
        def _fam(s):
            if '"%s":' % shot in s:
                return s
            m = re.search(r'(\n\s+)("(\w+)": "%s",)' % re.escape(family), s)
            if m:
                return s[:m.end()] + '%s"%s": "%s",' % (m.group(1), shot, family) + s[m.end():]
            m2 = re.search(r"(FAMILY[^=]*=\s*\{\n)", s)
            if not m2:
                return None
            return s[:m2.end()] + '    "%s": "%s",\n' % (shot, family) + s[m2.end():]
        out["shot_director.FAMILY"] = _edit(os.path.join(_HERE, "shot_director.py"),
                                            ['"%s":' % shot], _fam, "family")

    # LIBRARY.md — the catalogue entry the shot-director actually reads
    def _lib(s):
        if "**%s**" % shot in s:
            return s
        nums = [int(x) for x in re.findall(r"^(\d+)\. \*\*", s, re.M)]
        nxt = (max(nums) + 1) if nums else 1
        line = "%d. **%s** — %s *Use: %s*\n" % (nxt, shot, use_when or "TODO: describe the design.",
                                                use_when or "TODO")
        anchor = re.search(r"\n## [A-Z]{1,2} · ", s[s.index("## A ·"):]) if "## A ·" in s else None
        m = None
        if family:
            m = re.search(r"\n## %s · [^\n]*\n" % re.escape(family), s)
        if m:
            return s[:m.end()] + line + s[m.end():]
        return s.rstrip() + "\n" + line
    out["LIBRARY.md"] = _edit(os.path.join(_REM, "LIBRARY.md"), ["**%s**" % shot], _lib, "library")
    return out


def check(shot):
    files = {
        "src/shots/%s.tsx" % shot: os.path.join(_SHOTS, shot + ".tsx"),
        "registry.ts": os.path.join(_REM, "src", "registry.ts"),
        "Root.tsx": os.path.join(_REM, "src", "Root.tsx"),
        "shotLuma.ts": os.path.join(_REM, "src", "runtime", "shotLuma.ts"),
        "shot_director.py": os.path.join(_HERE, "shot_director.py"),
        "LIBRARY.md": os.path.join(_REM, "LIBRARY.md"),
    }
    miss = []
    for label, path in files.items():
        if label.startswith("src/shots/"):
            if not os.path.exists(path):
                miss.append(label)
            continue
        try:
            src = open(path, encoding="utf-8").read()
        except OSError:
            miss.append(label)
            continue
        if shot not in src:
            miss.append(label)
    return miss


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    shot = argv[0]
    if not re.match(r"^[A-Z][A-Za-z0-9]{2,31}$", shot):
        print("[register_shot] id must be PascalCase, 3-32 chars: %r" % shot)
        return 2
    if "--check" in argv:
        miss = check(shot)
        print("[register_shot] %s: %s" % (shot, "fully registered" if not miss else "MISSING from " + ", ".join(miss)))
        return 1 if miss else 0
    family = argv[1] if len(argv) > 1 and re.match(r"^[A-Z]{1,2}$", argv[1]) else None
    use_when = ""
    if "--use-when" in argv:
        i = argv.index("--use-when")
        if i + 1 < len(argv):
            use_when = argv[i + 1]
    if not family:
        print("[register_shot] give a family letter (A-Z, or a new two-letter one): register_shot.py Id D --use-when '…'")
        return 2
    res = register(shot, family, use_when)
    for k, v in res.items():
        print("  %-28s %s" % (k, v))
    miss = check(shot)
    print("[register_shot] %s — %s" % (shot, "registered everywhere" if not miss else "STILL MISSING: " + ", ".join(miss)))
    if not miss:
        print("  next: write the shot body, then `python3 scripts/measure_ground_luma.py --only %s`" % shot)
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
