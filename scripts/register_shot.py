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


def insert_registry_entry(src, shot):
    """Add `shot` as a key of the exported REGISTRY object, or None if the object cannot be found.

    Anchored on the object's own closing brace, NOT on the shape of the line above it. The first version
    required that line to hold two comma-separated names — true of the hand-written file, and false the
    moment this script had added one entry on its own line. Registration therefore worked exactly once
    and reported "FAILED (anchor not found)" every time after.
    """
    m = re.search(r"export const REGISTRY[^=]*=\s*\{", src)
    if not m:
        return None
    depth, i = 0, m.end() - 1
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    else:
        return None
    line_start = src.rfind("\n", 0, i) + 1
    return src[:line_start] + "  %s,\n" % shot + src[line_start:]


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
        return insert_registry_entry(s, shot)
    # The presence test must match how entries ACTUALLY look: names share a line. Requiring the id alone
    # on its own line could never be true for a real entry, so re-running appended a DUPLICATE key.
    reg_path = os.path.join(_REM, "src", "registry.ts")
    reg_present = not [x for x in check(shot) if x == "registry.ts"]
    out["registry.ts"] = "already" if reg_present else _edit(reg_path, ["\x00never"], _registry, "registry")

    # Root.tsx — import with a DURATION alias + the F() preview row
    # The alias was "D_" + shot.upper()[:10], so any two ids sharing ten characters got the SAME binding.
    # esbuild does not reject the duplicate import; it resolves both to one, and a shot silently renders
    # at another shot's frame count — which every standalone consumer then measures at the wrong moment.
    alias = "D_" + re.sub(r"[^A-Z0-9]", "", shot.upper())

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
    root_present = not [x for x in check(shot) if x == "Root.tsx"]
    out["Root.tsx"] = "already" if root_present else _edit(os.path.join(_REM, "src", "Root.tsx"),
                                                           ["\x00never"], _root, "root")

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
            s = (s[:m.end()] + "  %s: 'bg',   // PROVISIONAL — replaced by measure_ground_luma; NOT the declared-only marker\n"
                 % shot + s[m.end():])
        return s
    out["shotLuma.ts"] = _edit(os.path.join(_REM, "src", "runtime", "shotLuma.ts"),
                               ["%s: 'dark'," % shot, "%s: 'bg'," % shot], _luma, "luma")

    # shot_director.FAMILY
    if family:
        def _fam(s):
            if '"%s":' % shot in s:
                return s
            # Insert on its OWN line, at the END of a line that already carries this family. Appending
            # directly after a matched declaration put the new entry INSIDE a multi-declaration line, so a
            # later line-oriented edit removed a neighbour along with it — which is exactly how
            # "SharedBlindspot": "H" was silently deleted while cleaning up a probe.
            m = None
            for line in s.split("\n"):
                if re.search(r'"\w+": "%s",' % re.escape(family), line):
                    m = line
                    break
            if m:
                indent = re.match(r"\s*", m).group(0)
                return s.replace(m, m + "\n" + indent + '"%s": "%s",' % (shot, family), 1)
            m2 = re.search(r"(FAMILY[^=]*=\s*\{\n)", s)
            if not m2:
                return None
            return s[:m2.end()] + '    "%s": "%s",\n' % (shot, family) + s[m2.end():]
        fam_path = os.path.join(_HERE, "shot_director.py")
        cur = re.search(r'"%s":\s*"([A-Z]{1,2})"' % re.escape(shot), open(fam_path, encoding="utf-8").read())
        if cur and cur.group(1) != family:
            # Silently keeping the old letter meant a re-registration that MEANT to move families did
            # nothing, and said "registered everywhere".
            out["shot_director.FAMILY"] = ("already, but as family %s — NOT %s. Change it by hand if you "
                                           "meant to move it." % (cur.group(1), family))
        else:
            out["shot_director.FAMILY"] = _edit(fam_path, ['"%s": "%s"' % (shot, family)], _fam, "family")

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
        # No section for this family yet — CREATE one. Appending at the end of the file put the entry
        # outside every section, where the catalogue's own structure hides it from the reader.
        if family:
            return s.rstrip() + "\n\n## %s · (new family — name it)\n%s" % (family, line)
        return s.rstrip() + "\n" + line
    out["LIBRARY.md"] = _edit(os.path.join(_REM, "LIBRARY.md"), ["**%s**" % shot], _lib, "library")
    return out


def _uncommented(src):
    """The file with // and /* */ comments removed.

    check() matched raw file text, so a REGISTRY entry that had been COMMENTED OUT still satisfied it and
    the shot reported "fully registered" — the exact silence this function exists to break, reached by a
    different route than the substring bug it replaced. Its docstring's promise ("checked for the
    STRUCTURE that makes the registration work, never for the id appearing somewhere in the text") is only
    true once comments are gone.
    """
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return "\n".join(re.sub(r"//.*$", "", ln) for ln in src.split("\n"))


# The six sync points, each named by the RULE it enforces rather than by the file it lives in, so a test
# can probe one rule at a time. Every rule here was, at some point, satisfiable without the registration
# actually working — by a substring, by a comment, by a filename the OS matched case-insensitively.
SYNC_LABEL = {
    "tsx_file": "src/shots/%s.tsx",
    "registry_import": "registry.ts", "registry_map": "registry.ts",
    "root_import": "Root.tsx", "root_preview": "Root.tsx",
    "luma_coarse": "shotLuma.ts", "luma_ground": "shotLuma.ts",
    "family": "shot_director.py",
    "library_entry": "LIBRARY.md",
}
_LUM_FALLBACK = ("dark", "mid", "light")
_GROUND_FALLBACK = ("bg", "bgGrad", "accent", "accent2", "surface")


def _union_values(src, type_name, fallback):
    """The string members of a TypeScript union, read from the source so the checker cannot drift from it.

    Hardcoding them drifted in BOTH directions at once: the ground-token alternation listed 'line' and
    'fg', which are not GroundTokens at all, and omitted 'bgGrad', which is.
    """
    m = re.search(r"export type %s\s*=\s*([^;]+);" % re.escape(type_name), src or "")
    vals = re.findall(r"'([^']+)'", m.group(1)) if m else []
    return tuple(vals) or tuple(fallback)


def sync_patterns(shot, luma_src=None):
    """{rule: compiled-pattern-string} — the STRUCTURE each sync point must show for `shot`.

    `tsx_file` has no pattern: it is a filename test, and deliberately a CASE-EXACT one.
    """
    b = re.escape(shot)
    lums = "|".join(_union_values(luma_src, "Lum", _LUM_FALLBACK))
    grounds = "|".join(_union_values(luma_src, "GroundToken", _GROUND_FALLBACK))
    return {
        "tsx_file": None,
        "registry_import": r"import\s*\{\s*%s\s*\}\s*from\s*'\./shots/%s'" % (b, b),
        "registry_map": r"(?<![A-Za-z0-9_])%s\s*," % b,
        "root_import": r"import\s*\{\s*%s\s*,\s*DURATION as \w+\s*\}" % b,
        "root_preview": r"F\('%s'\s*,\s*%s\s*," % (b, b),
        "luma_coarse": r"(?<![A-Za-z0-9_])%s:\s*'(%s)'" % (b, lums),
        "luma_ground": r"(?<![A-Za-z0-9_])%s:\s*('(%s)'|\[)" % (b, grounds),
        "family": r'"%s":\s*"[A-Z]{1,2}"' % b,
        # The catalogue ENTRY shape, not the id in bold anywhere: a bold cross-reference inside somebody
        # else's entry satisfied the loose form, so a shot with no entry of its own read as documented.
        "library_entry": r"^\d+\. \*\*%s\*\*" % b,
    }


def missing_rules(shot, sources, filenames=()):
    """Which RULES `shot` fails, given file text per sync-point label and a directory listing.

    Pure: no filesystem. `check()` supplies the real sources; a test supplies synthetic ones, which is the
    only way to probe one rule at a time.
    """
    pats = sync_patterns(shot, sources.get("shotLuma.ts"))
    out = []
    for rule, pat in pats.items():
        if rule == "tsx_file":
            if ("%s.tsx" % shot) not in list(filenames):
                out.append(rule)
            continue
        src = sources.get(SYNC_LABEL[rule])
        if src is None:
            out.append(rule)
            continue
        if not re.search(pat, _uncommented(src), re.M):
            out.append(rule)
    return out


def check(shot):
    """Which sync points this shot is MISSING from.

    Each file is checked for the STRUCTURE that makes the registration work, never for the id appearing
    somewhere in the text. A naked `shot not in src` — which this function used to do — is satisfied by
    the import line alone, so a registry.ts that kept `import {X}` but lost its entry in the REGISTRY map
    reported "fully registered" while the film rendered a red `unknown shot` card in place of that beat.
    Comments are stripped first, because a COMMENTED-OUT entry satisfied the structural form too. This is
    the only backstop for a capability whose failure mode is silence, and validate.py's build-claim gate
    calls it, so a check that cannot fail is worse than none.
    """
    paths = {
        "registry.ts": os.path.join(_REM, "src", "registry.ts"),
        "Root.tsx": os.path.join(_REM, "src", "Root.tsx"),
        "shotLuma.ts": os.path.join(_REM, "src", "runtime", "shotLuma.ts"),
        "shot_director.py": os.path.join(_HERE, "shot_director.py"),
        "LIBRARY.md": os.path.join(_REM, "LIBRARY.md"),
    }
    sources = {}
    for label, path in paths.items():
        try:
            sources[label] = open(path, encoding="utf-8").read()
        except OSError:
            sources[label] = None
    # os.path.exists is CASE-BLIND on APFS, the platform this skill runs on: registering "Termlog" while
    # TermLog.tsx exists reported the file present, wrote no stub, registered the id in the other five
    # files and called it done — and the Film rendered a red unknown-shot card.
    names = os.listdir(_SHOTS) if os.path.isdir(_SHOTS) else []
    labels = []
    for rule in missing_rules(shot, sources, names):
        lab = SYNC_LABEL[rule] % shot if "%s" in SYNC_LABEL[rule] else SYNC_LABEL[rule]
        if lab not in labels:
            labels.append(lab)
    return labels


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
    use_when = re.sub(r"\s+", " ", use_when).strip()[:160]   # a newline here produced an invalid .tsx
    res = register(shot, family, use_when)
    for k, v in res.items():
        print("  %-28s %s" % (k, v))
    failed = [k for k, v in res.items() if str(v).startswith("FAILED")]
    if failed:
        # Printing FAILED and then reporting success two lines later is how a wrapper reading the exit
        # code sails past a half-registered shot.
        print("[register_shot] %s — could not edit: %s. Nothing else is trustworthy; fix the anchor."
              % (shot, ", ".join(failed)))
        return 1
    miss = check(shot)
    print("[register_shot] %s — %s" % (shot, "registered everywhere" if not miss else "STILL MISSING: " + ", ".join(miss)))
    if not miss:
        print("  next: write the shot body, then `python3 scripts/measure_ground_luma.py --only %s`" % shot)
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
