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

COVERAGE: the universe is the REGISTERED set (registry.ts imports), printed beside the number of
shots/*.tsx on disk. A registry that cannot be read, or that parses to zero shots, RAISES — it used to
return an empty set, and an empty universe reports 0 registered / 0 un-migrated and exits 0.
`--check` also refuses a registry entry with no file and a shot whose source could not be read: both
score `depth: none`, which is the same row a genuinely un-migrated register gets.
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
        except (OSError, UnicodeDecodeError):
            continue                       # named by unreadable_shots(), never scored here
        if _USE_CALL.search(src) and not _USE_IMPORT.search(src):
            out.add(f[:-4])
    return out


def dna_aware_shots(remotion_dir=None):
    """Ids of shots that read the Design DNA and therefore unify on a themed film. Requires BOTH an actual call
    `useDNA(` AND the matching import — a call without the import is not 'migrated', it is BROKEN (see
    broken_shots), and a dangling import without a call changes nothing."""
    out = set()
    # the stage components too (remotion/src/stage/): a beat on a stage run selects one, and it unifies on a themed
    # film exactly as a register does — it was warned "never reads useDNA" while it read it on its first line
    for d in (_shots_dir(remotion_dir), os.path.join(remotion_dir or _REMOTION, "src", "stage")):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.endswith(".tsx"):
                continue
            try:
                src = open(os.path.join(d, f), encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue                       # named by unreadable_shots(), never scored here
            if _USE_CALL.search(src) and _USE_IMPORT.search(src):
                out.add(f[:-4])
    return out


def registered_shots(remotion_dir=None):
    """Ids present in the REGISTRY (registry.ts) — the shots a film can actually select. Parsed from the import
    lines `import {X} from './shots/X'` so it tracks the real registry, not the raw file list (some *.tsx are
    topic-locked bespoke shots wired in elsewhere)."""
    reg = os.path.join(remotion_dir or _REMOTION, "src", "registry.ts")
    ids = set()
    # AN UNREADABLE REGISTRY USED TO PRODUCE AN EMPTY UNIVERSE, AND AN EMPTY UNIVERSE READS AS CLEAN.
    # `except OSError: pass` returned set(), so the report printed `registered shots : 0 · un-migrated : 0`
    # and `--check` exited 0 — a perfect pass over nothing at all, which is precisely the shape of hole this
    # audit's own header warns about ("a manual list would rot"). A universe that cannot be derived is a
    # hard failure, and so is one that parses to nothing.
    try:
        with open(reg, encoding="utf-8") as fh:
            src = fh.read()
    except OSError as e:
        raise RuntimeError("dna_audit: cannot read the registry at %s (%s) — the set of REGISTERED shots is "
                           "this audit's whole universe, and an unreadable registry would otherwise report "
                           "0 registered / 0 un-migrated, which is indistinguishable from a clean library"
                           % (reg, e))
    for m in re.finditer(r"from\s+'\./shots/([A-Za-z0-9_]+)'", src):
        ids.add(m.group(1))
    if not ids:
        raise RuntimeError("dna_audit: the registry at %s parsed to ZERO shots — the import-line grep has "
                           "drifted from registry.ts's real shape; fix the parse before trusting this audit"
                           % reg)
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
    except (OSError, UnicodeDecodeError):
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


def unreadable_shots(remotion_dir=None):
    """[(id, reason)] for shot files whose SOURCE could not be read.

    Three greps in this file (`dna_aware_shots`, `broken_shots`, `residual_hardcodes`) each carry their own
    `except OSError: continue / return (0, 0)`. Individually each is defensible; together they mean a shot
    whose file cannot be opened is scored `not aware · 0 residuals · 0 dna_reads` — a row that looks exactly
    like a measured un-migrated register, with nothing saying it was never read. The reason belongs in the
    report, so the reader can tell "this shot hardcodes its palette" from "nobody looked"."""
    d = _shots_dir(remotion_dir)
    out = []
    if not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        if not f.endswith(".tsx"):
            continue
        try:
            open(os.path.join(d, f), encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as e:
            out.append((f[:-4], "%s: %s" % (type(e).__name__, e)))
    return out


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
    files = all_shot_files(remotion_dir)
    unread = unreadable_shots(remotion_dir)
    return {
        "registered": len(reg),
        "dna_aware": len(reg_aware),
        "unmigrated": reg_unmigrated,
        "unmigrated_count": len(reg_unmigrated),
        "depth_counts": {k: len(v) for k, v in by_depth.items()},
        "by_depth": by_depth,
        "detail": detail,
        # COVERAGE. The universe is the REGISTERED set and always was — but the report never said so next
        # to the other universe in the same directory, and the two are only equal by convention. A `.tsx`
        # nobody imported is a shot no film can select AND a shot this audit never scores; a registry entry
        # with no file is an import that cannot resolve. Both are derived here, never listed.
        "shot_files": len(files),
        "files_not_registered": sorted(files - reg),
        "registered_without_file": sorted(reg - files),
        "unreadable": unread,
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
    # A DIFFERENT UNIVERSE FROM THE MAIN REPORT, said out loud: this walks every shots/*.tsx, the migration
    # report walks the REGISTERED set. They are equal by convention, not by construction.
    print("type reach across %d shots/*.tsx (every file, not only the registered ones):" % total)
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
    print(f"registered shots : {a['registered']}  (scored {a['registered'] - len(a['registered_without_file'])}"
          f" of {a['registered']} · universe = registry.ts imports, of {a['shot_files']} shots/*.tsx on disk)")
    print(f"DNA-aware        : {a['dna_aware']}")
    print(f"un-migrated      : {a['unmigrated_count']}")
    print(f"migration depth  : deep {dc['deep']} | partial {dc['partial']} | ground-only {dc['ground-only']} | none {dc['none']}")
    # WHAT THIS RUN DID NOT SCORE. Each of these three reads as a clean row otherwise: an unregistered file
    # is simply absent, a registry entry with no file scores `none` like any un-migrated shot, and an
    # unreadable one scores `none · residual 0 · reads 0` — the same row a genuinely un-migrated register
    # gets. All three are advisory (this tool is a worklist, per the header), so they are NAMED here and
    # the `--check` gate below refuses only the ones that make its own answer unsound.
    if a["files_not_registered"]:
        print("\nNOT SCORED — %d shots/*.tsx that no registry import names, so no film can select them and "
              "this audit never scores them:\n  %s"
              % (len(a["files_not_registered"]), " ".join(a["files_not_registered"])))
    if a["registered_without_file"]:
        print("\nNOT SCORED — %d registry import(s) with no shots/*.tsx behind them (the import cannot "
              "resolve; they are counted as registered and measured as nothing):\n  %s"
              % (len(a["registered_without_file"]), " ".join(a["registered_without_file"])))
    if a["unreadable"]:
        print("\nNOT READ — %d shot file(s) whose source could not be opened. Their depth above is the "
              "default 'none · residual 0', which is what a genuinely un-migrated register also scores:"
              % len(a["unreadable"]))
        for sname, whynot in a["unreadable"]:
            print(f"  {sname:24s} {whynot}")
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
    # `--check` is the completeness gate. A registry entry with no file, or a file it could not read, means
    # the gate's own answer about that shot is "unknown" — and unknown must not exit 0 in a gate. The
    # unregistered-file list stays advisory: those shots are outside this audit's universe by definition,
    # and refusing over them would turn a worklist into a gate over a set it never claimed.
    if "--check" in argv and (a["unmigrated"] or brk or a["registered_without_file"] or a["unreadable"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
