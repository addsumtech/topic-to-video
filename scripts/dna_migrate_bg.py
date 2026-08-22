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
    hook_i = next((i for i, l in enumerate(lines) if _HOOK.match(l)), None)
    if hook_i is None:
        return None, "no useVideoConfig/useCurrentFrame/useT hook to anchor the dna read — hand-migrate"
    indent = _HOOK.match(lines[hook_i]).group(1)
    lines.insert(hook_i + 1, f"{indent}const dna = useDNA();")
    out = "\n".join(lines)
    out = _BG.sub(lambda m: f"{m.group(1)}dna?.bgGrad ?? dna?.bg ?? ({m.group(2)})", out, count=1)
    if "runtime/dna" in out:
        out = re.sub(r"import\s*\{([^}]*)\}\s*from\s*'(\.\./runtime/dna)'",
                     lambda m: m.group(0) if "useDNA" in m.group(1) else f"import {{{m.group(1).strip()}, useDNA}} from '{m.group(2)}'",
                     out, count=1)
    else:
        out = re.sub(r"(import .*from '\.\./runtime/motion';)", r"\1\nimport {useDNA} from '../runtime/dna';", out, count=1)
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
