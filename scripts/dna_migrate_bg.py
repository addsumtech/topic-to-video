#!/usr/bin/env python3
"""dna_migrate_bg — LEVEL-B ground-only migration for DARK inline-palette shots the full codemod (dna_migrate.py)
skips. It does the SAFEST possible change: wrap ONLY the first `<AbsoluteFill style={{background: X}}>` with
`dna?.bgGrad ?? dna?.bg ?? (X)` and inject `const dna = useDNA()` — no const renaming, no subcomponent edits, so
none of the module-scope / param-default / TDZ traps apply. It DELIBERATELY leaves the accent hardcoded: on a
DARK-ground shot the ground is the dominant coherence signal and the shot's own accent is its generative identity
(same call as the batch-3 BG-only migrations). Null DNA = byte-identical (the original bg is the fallback).

ONLY for DARK-ground shots (shotLuma=='dark'): on a light-ground shot, changing the ground without the ink inverts
contrast (that's what level-C hand work is for). Guarded, like dna_migrate.py.

Usage:  python scripts/dna_migrate_bg.py [--dry] <ShotId> [ShotId...]
"""
import os, re, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHOTS = os.path.join(os.path.dirname(_HERE), "remotion", "src", "shots")
try:
    sys.path.insert(0, _HERE)
    from dna_migrate import _ground_lum
except Exception:
    def _ground_lum(_s):
        return "dark"

# first AbsoluteFill background value: a single/double-quoted string or a template literal (may hold commas / ${})
_BG = re.compile(r"(<AbsoluteFill style=\{\{background:\s*)('[^']*'|\"[^\"]*\"|`[^`]*`)")
_HOOK = re.compile(r"^(\s*)(const .*=\s*use(?:VideoConfig|CurrentFrame|T)\s*\([^)]*\)\s*;?)\s*$")


def _plan(src, shot):
    if re.search(r"\buseDNA\s*\(", src):
        return None, "already DNA-aware"
    lum = _ground_lum(shot)
    if lum != "dark":
        return None, f"ground is {lum or 'unknown'} (not dark) — level-B ground swap would invert; use level-C by hand"
    if not _BG.search(src):
        return None, "no `<AbsoluteFill style={{background: '...'}}>` with a literal value — hand-migrate"
    lines = src.split("\n")
    # SCOPE: the hook must be inserted inside the component that PAINTS the ground we are rewriting. Anchoring on the
    # first hook in the file is wrong whenever a module-scope SUBcomponent appears first — the shot then renders
    # `dna is not defined`, and neither the useDNA-call grep nor a type-free build notices. (MaterialHero was exactly
    # this: the hook landed in its <Hero> subcomponent while the background lives in the exported component.) So:
    # find the exported component, then the first hook BETWEEN it and the background line.
    exp_i = next((i for i, l in enumerate(lines) if re.match(rf"^export const {re.escape(shot)}\b", l)), None)
    if exp_i is None:
        return None, f"no `export const {shot}` found — hand-migrate"
    bg_line = next((i for i, l in enumerate(lines) if i > exp_i and _BG.search(l)), None)
    if bg_line is None:
        return None, "the literal background is not inside the exported component — hand-migrate"
    hook_i = next((i for i in range(exp_i, bg_line) if _HOOK.match(lines[i])), None)
    if hook_i is None:
        return None, ("no useVideoConfig/useCurrentFrame/useT hook between the component opener and its background "
                      "to anchor the dna read on — hand-migrate")
    indent = _HOOK.match(lines[hook_i]).group(1)
    lines.insert(hook_i + 1, f"{indent}const dna = useDNA();")
    out = "\n".join(lines)
    _l = out.split("\n")
    _target = next((i for i, l in enumerate(_l) if i > exp_i and _BG.search(l)), None)
    if _target is None:
        return None, "INTERNAL GUARD: lost the background line after inserting the hook — refused"
    _l[_target] = _BG.sub(lambda m: f"{m.group(1)}dna?.bgGrad ?? dna?.bg ?? ({m.group(2)})", _l[_target], count=1)
    out = "\n".join(_l)
    if "runtime/dna" in out:
        out = re.sub(r"import\s*\{([^}]*)\}\s*from\s*'(\.\./runtime/dna)'",
                     lambda m: m.group(0) if "useDNA" in m.group(1) else f"import {{{m.group(1).strip()}, useDNA}} from '{m.group(2)}'",
                     out, count=1)
    else:
        # NOT every shot imports from runtime/motion (a three.js shot, for instance). Anchor on the LAST import line
        # instead; if even that is impossible, REFUSE the transform. Writing a file that calls useDNA() without
        # importing it is a hard ReferenceError at render time, and dna_audit's `useDNA(` grep would still score it
        # as migrated — a green tick on a broken shot. Fail loud instead. (MaterialHero was exactly this bug.)
        if re.search(r"import .*from '\.\./runtime/motion';", out):
            out = re.sub(r"(import .*from '\.\./runtime/motion';)",
                         r"\1\nimport {useDNA} from '../runtime/dna';", out, count=1)
        else:
            _lines = out.split("\n")
            _imports = [i for i, l in enumerate(_lines) if l.startswith("import ")]
            if not _imports:
                return None, "no import statement to anchor the useDNA import on — hand-migrate"
            _lines.insert(_imports[-1] + 1, "import {useDNA} from '../runtime/dna';")
            out = "\n".join(_lines)
    if not re.search(r"import\s*\{[^}]*\buseDNA\b[^}]*\}\s*from\s*'\.{1,2}/runtime/dna'", out):
        return None, "INTERNAL GUARD: transform would call useDNA() without importing it — refused"
    return out, "root background -> dna.bgGrad/bg (ground-only)"


def main(argv):
    dry = "--dry" in argv
    ids = [a for a in argv if not a.startswith("-")]
    if not ids:
        print("usage: dna_migrate_bg.py [--dry] <ShotId>..."); return 2
    ok = skip = 0
    for shot in ids:
        p = os.path.join(_SHOTS, shot + ".tsx")
        if not os.path.isfile(p):
            print(f"  SKIP {shot}: no such shot file"); skip += 1; continue
        new, note = _plan(open(p, encoding="utf-8").read(), shot)
        if new is None:
            print(f"  SKIP {shot}: {note}"); skip += 1; continue
        if not dry:
            open(p, "w", encoding="utf-8").write(new)
        print(f"  {'PLAN' if dry else 'OK  '} {shot}: {note}"); ok += 1
    print(f"\n{ok} migrated{' (dry-run)' if dry else ''}, {skip} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
