#!/usr/bin/env python3
"""dna_audit — which REGISTERED remotion shots are Design-DNA-aware (read useDNA) vs still wear a hardcoded
palette. The single source of truth for "is shot X DNA-aware?", shared by validate.py's themed-film lint and by
whoever is migrating the library. SELF-UPDATING: it greps remotion/src/shots/*.tsx at call time, so a shot that
gains a `useDNA()` call is counted immediately — no manifest to keep in sync (a manual list would rot; see the
'opt-in gates don't detect' lesson). File basename == component == registry id by the library's convention.

An un-migrated register is not broken on its OWN (null DNA = its original look), only on a DNA-THEMED film, where
it renders its hardcoded identity instead of the global visual system — that is exactly what the validate lint
surfaces. This tool just makes the migration worklist VISIBLE (never a silent "done").

CLI:  python scripts/dna_audit.py            # summary + the un-migrated registered list, grouped by family
      python scripts/dna_audit.py --json     # machine-readable
      python scripts/dna_audit.py --check     # exit 1 if any REGISTERED shot is un-migrated (for a completeness gate)
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


def dna_aware_shots(remotion_dir=None):
    """Ids of shots whose source CALLS useDNA() — i.e. they read the Design DNA tokens and unify on a themed film.
    Requires an actual call `useDNA(`, not just the import, so a dangling import doesn't count as migrated."""
    d = _shots_dir(remotion_dir)
    if not os.path.isdir(d):
        return set()
    out = set()
    for f in os.listdir(d):
        if not f.endswith(".tsx"):
            continue
        try:
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                if re.search(r"\buseDNA\s*\(", fh.read()):
                    out.add(f[:-4])
        except OSError:
            pass
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


def audit(remotion_dir=None):
    reg = registered_shots(remotion_dir)
    aware = dna_aware_shots(remotion_dir)
    reg_aware = reg & aware
    reg_unmigrated = sorted(reg - aware)
    return {
        "registered": len(reg),
        "dna_aware": len(reg_aware),
        "unmigrated": reg_unmigrated,
        "unmigrated_count": len(reg_unmigrated),
    }


def _family_of(shot):
    try:
        sys.path.insert(0, _HERE)
        import shot_director as _sd  # FAMILY maps shot id -> family letter
        return _sd.FAMILY.get(shot)
    except Exception:
        return None


def main(argv):
    a = audit()
    if "--json" in argv:
        print(json.dumps(a, indent=2)); return 0
    print(f"registered shots : {a['registered']}")
    print(f"DNA-aware        : {a['dna_aware']}")
    print(f"un-migrated      : {a['unmigrated_count']}")
    if a["unmigrated"]:
        by_fam = {}
        for s in a["unmigrated"]:
            by_fam.setdefault(_family_of(s) or "?", []).append(s)
        print("\nun-migrated registered shots (read a hardcoded palette; will not unify on a themed film):")
        for fam in sorted(by_fam):
            print(f"  [{fam}] " + " ".join(sorted(by_fam[fam])))
    if "--check" in argv and a["unmigrated"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
