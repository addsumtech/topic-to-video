#!/usr/bin/env python3
"""dna_audit — which REGISTERED remotion shots are Design-DNA-aware (read useDNA) vs still wear a hardcoded
palette. The single source of truth for "is shot X DNA-aware?", shared by validate.py's themed-film lint and by
whoever is migrating the library. SELF-UPDATING: it greps remotion/src/shots/*.tsx at call time, so a shot that
gains a `useDNA()` call is counted immediately — no manifest to keep in sync (a manual list would rot; see the
'opt-in gates don't detect' lesson). File basename == component == registry id by the library's convention.

An un-migrated register is not broken on its OWN (null DNA = its original look), only on a DNA-THEMED film, where
it renders its hardcoded identity instead of the global visual system — that is exactly what the validate lint
surfaces. This tool just makes the migration worklist VISIBLE (never a silent "done").

MIGRATION DEPTH (`--depth`) is a HEURISTIC WORKLIST, never a verdict, and deliberately NOT wired into validate.py as
a gate. It counts CHROMATIC hex literals painted on lines that never consult `dna`. Two honest caveats: (1) it
over-counts when a fallback is passed as a function ARGUMENT rather than via `??` on the same line (e.g. ClayStack's
`clay(0, '#f7b7a3', …)` fallbacks); (2) a high count is often CORRECT — syntax-highlight colours, CPK element
colours, MRI physics vectors, per-collaborator cursor colours and other SEMANTIC or identity palettes must survive a
theme. Read it as "where would a themed film still show this register's own hues", then judge each case.

CLI:  python scripts/dna_audit.py            # summary + the un-migrated registered list, grouped by family
      python scripts/dna_audit.py --depth    # + the partial / ground-only worklist with residual counts
      python scripts/dna_audit.py --json     # machine-readable
      python scripts/dna_audit.py --check     # exit 1 if any REGISTERED shot is un-migrated (for a completeness gate)
      python scripts/dna_audit.py --type     # per-role (display/body/mono) TYPE reach across every shot
"""
import os, re, sys, json

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(os.path.dirname(_HERE), "remotion")


def _shots_dir(remotion_dir=None):
    return os.path.join(remotion_dir or _REMOTION, "src", "shots")


def all_shot_files(remotion_dir=None):
    """Every shots/*.tsx basename (== component id), whether registered or not."""
    d = _shots_dir(remotion_dir)
    if not os.path.isdir(d):
        return set()
    return {f[:-4] for f in os.listdir(d) if f.endswith(".tsx")}


_USE_CALL = re.compile(r"\buseDNA\s*\(")
_USE_IMPORT = re.compile(r"import\s*\{[^}]*\buseDNA\b[^}]*\}\s*from\s*'\.{1,2}/runtime/dna'")


def broken_shots(remotion_dir=None):
    """Ids that CALL useDNA() but never IMPORT it — a hard `useDNA is not defined` ReferenceError at render time.
    A codemod that inserts the call but misses the import produces exactly this, and a naive `useDNA(` grep would
    still score it as migrated: a green tick on a shot that cannot render. Surfaced separately, and never counted
    as aware. (MaterialHero shipped in this state; the codemods now refuse the transform instead.)"""
    d = _shots_dir(remotion_dir)
    if not os.path.isdir(d):
        return set()
    out = set()
    for f in os.listdir(d):
        if not f.endswith(".tsx"):
            continue
        try:
            src = open(os.path.join(d, f), encoding="utf-8").read()
        except OSError:
            continue
        if _USE_CALL.search(src) and not _USE_IMPORT.search(src):
            out.add(f[:-4])
    return out


def dna_aware_shots(remotion_dir=None):
    """Ids of shots that read the Design DNA and therefore unify on a themed film. Requires BOTH an actual call
    `useDNA(` AND the matching import — a call without the import is not 'migrated', it is BROKEN (see
    broken_shots), and a dangling import without a call changes nothing."""
    d = _shots_dir(remotion_dir)
    if not os.path.isdir(d):
        return set()
    out = set()
    for f in os.listdir(d):
        if not f.endswith(".tsx"):
            continue
        try:
            src = open(os.path.join(d, f), encoding="utf-8").read()
        except OSError:
            continue
        if _USE_CALL.search(src) and _USE_IMPORT.search(src):
            out.add(f[:-4])
    return out


def registered_shots(remotion_dir=None):
    """Ids present in the REGISTRY (registry.ts) — the shots a film can actually select. Parsed from the import
    lines `import {X} from './shots/X'` so it tracks the real registry, not the raw file list (some *.tsx are
    topic-locked bespoke shots wired in elsewhere)."""
    reg = os.path.join(remotion_dir or _REMOTION, "src", "registry.ts")
    ids = set()
    try:
        with open(reg, encoding="utf-8") as fh:
            for m in re.finditer(r"from\s+'\./shots/([A-Za-z0-9_]+)'", fh.read()):
                ids.add(m.group(1))
    except OSError:
        pass
    return ids


# A hex literal is FINE when it is the null-DNA fallback of a guarded expression (`dna?.x ?? '#hex'`, `dna ? a : '#hex'`)
# or a `NAME0`/`NAME_D0` fallback declaration. It is a RESIDUAL when it is painted unconditionally — the shot reads the
# DNA somewhere but still hardcodes THAT element, so a themed film only partly unifies. Counting residuals turns the
# binary "reads useDNA" into a MIGRATION DEPTH, so a shallow migration can't hide behind a green tick.
_HEX = re.compile(r"['\"]#[0-9a-fA-F]{3,8}['\"]")
_FALLBACK_DECL = re.compile(r"^\s*(?:export\s+)?const\s+[A-Za-z_][A-Za-z0-9_]*(?:0|_D0)\s*(?::|=)")


def _chromatic(hex_literal):
    """True when a hex literal carries a HUE. Neutral black/white/grey (shadows, speculars, scrims, hairlines) are
    physically correct under any DNA — counting them as 'un-migrated' would punish correct code, so they don't count."""
    h = hex_literal.strip("'\"").lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c + c for c in h[:3])
    if len(h) < 6:
        return False
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return False
    return (max(r, g, b) - min(r, g, b)) > 14      # >14 spread = a real hue, not a grey


def residual_hardcodes(shot, remotion_dir=None):
    """(residual_count, dna_reads) for one shot. `residual` = CHROMATIC hex literals on lines that never mention `dna`."""
    f = os.path.join(_shots_dir(remotion_dir), shot + ".tsx")
    try:
        src = open(f, encoding="utf-8").read()
    except OSError:
        return (0, 0)
    reads = len(re.findall(r"dna\?\.|dna \?|useDNA\s*\(", src))
    residual = 0
    for line in src.split("\n"):
        st = line.strip()
        if st.startswith("//") or st.startswith("*"):
            continue
        if _FALLBACK_DECL.match(line):          # a NAME0 fallback declaration — legitimate
            continue
        if "dna" in line:                       # the expression consults the DNA — guarded, fine
            continue
        residual += sum(1 for hx in _HEX.findall(line) if _chromatic(hx))
    return (residual, reads)


def depth(shot, remotion_dir=None):
    """'deep' | 'partial' | 'ground-only' | 'none' — how far the DNA actually reaches into this shot."""
    aware = shot in dna_aware_shots(remotion_dir)
    if not aware:
        return "none"
    residual, reads = residual_hardcodes(shot, remotion_dir)
    if reads <= 2 and residual > 0:
        return "ground-only"
    if residual >= 8:
        return "partial"
    return "deep"


def audit(remotion_dir=None):
    reg = registered_shots(remotion_dir)
    aware = dna_aware_shots(remotion_dir)
    reg_aware = reg & aware
    reg_unmigrated = sorted(reg - aware)
    aware_set = dna_aware_shots(remotion_dir)
    by_depth = {"deep": [], "partial": [], "ground-only": [], "none": []}
    detail = {}
    for shot in sorted(reg):
        residual, reads = residual_hardcodes(shot, remotion_dir)
        d = "none" if shot not in aware_set else (
            "ground-only" if reads <= 2 and residual > 0 else ("partial" if residual >= 8 else "deep"))
        by_depth[d].append(shot)
        detail[shot] = {"depth": d, "residual_hardcodes": residual, "dna_reads": reads}
    return {
        "registered": len(reg),
        "dna_aware": len(reg_aware),
        "unmigrated": reg_unmigrated,
        "unmigrated_count": len(reg_unmigrated),
        "depth_counts": {k: len(v) for k, v in by_depth.items()},
        "by_depth": by_depth,
        "detail": detail,
    }


def _family_of(shot):
    try:
        sys.path.insert(0, _HERE)
        import shot_director as _sd  # FAMILY maps shot id -> family letter
        return _sd.FAMILY.get(shot)
    except Exception:
        return None


_TYPE_ROLES = ("display", "body", "mono")


def type_report(shots_dir):
    """Per-role type reach across the library. The spec's baseline, before this layer, was
    display 4 / body 3 / mono 10 of 134 shots - the tokens were declared and almost never read."""
    reach = {r: set() for r in _TYPE_ROLES}
    total = 0
    for name in sorted(os.listdir(shots_dir)):
        if not name.endswith(".tsx"):
            continue
        total += 1
        src = open(os.path.join(shots_dir, name), encoding="utf-8").read()
        for role in _TYPE_ROLES:
            token = role.capitalize() if role != "display" else "Display"
            if ("var(--f-%s" % role) in src or ("dna?.font%s" % token) in src:
                reach[role].add(name)
    print("type reach across %d shots:" % total)
    for role in _TYPE_ROLES:
        print("  %-8s %3d" % (role, len(reach[role])))
    silent = [n for n in sorted(os.listdir(shots_dir))
              if n.endswith(".tsx") and not any(n in reach[r] for r in _TYPE_ROLES)]
    if silent:
        print("  %d shots read no type token at all:" % len(silent))
        for n in silent[:10]:
            print("    " + n)
    return 0


def main(argv):
    if "--type" in argv:
        return type_report(_shots_dir())
    a = audit()
    if "--json" in argv:
        print(json.dumps(a, indent=2)); return 0
    dc = a["depth_counts"]
    print(f"registered shots : {a['registered']}")
    print(f"DNA-aware        : {a['dna_aware']}")
    print(f"un-migrated      : {a['unmigrated_count']}")
    print(f"migration depth  : deep {dc['deep']} | partial {dc['partial']} | ground-only {dc['ground-only']} | none {dc['none']}")
    if "--depth" in sys.argv[1:]:
        for d in ("partial", "ground-only"):
            if a["by_depth"][d]:
                print(f"\n{d} (a themed film only PARTLY unifies these — residual hardcoded colours):")
                for sname in a["by_depth"][d]:
                    print(f"  {sname:24s} residual={a['detail'][sname]['residual_hardcodes']:3d}  dna_reads={a['detail'][sname]['dna_reads']}")
    if a["unmigrated"]:
        by_fam = {}
        for s in a["unmigrated"]:
            by_fam.setdefault(_family_of(s) or "?", []).append(s)
        print("\nun-migrated registered shots (read a hardcoded palette; will not unify on a themed film):")
        for fam in sorted(by_fam):
            print(f"  [{fam}] " + " ".join(sorted(by_fam[fam])))
    brk = sorted(broken_shots() & registered_shots())
    if brk:
        print("\n*** BROKEN — call useDNA() without importing it (hard ReferenceError at render): " + " ".join(brk))
    if "--check" in argv and (a["unmigrated"] or brk):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
