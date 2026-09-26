#!/usr/bin/env python3
"""Scaffold and REGISTER a new bespoke shot at every sync point, in one command.

  python3 scripts/register_shot.py <Id> <FamilyLetter> --use-when "<one line>" --provenance <world>
      <world> = which world this shot's IDIOM comes from — the idiom-world gate reads it, and a
      register with none is silently exempt from it (see shot_director.IDIOM_WORLDS)
  python3 scripts/register_shot.py <Id> --check          # verify an existing shot is fully registered

WHY THIS EXISTS. The library can grow — `references/remotion-shot-authoring.md` has said so from the start
("build a NEW shot when the *structure* differs, not merely the sizing"). In practice it almost never did,
and the reason was friction, not permission: registering one shot by hand means editing `registry.ts`,
`Root.tsx`, `runtime/shotLuma.ts`, `shot_director.FAMILY` and `LIBRARY.md`, then re-measuring ground
luminance — five files and a gate, every one of which fails SILENTLY except the two that are tested. A
capability that costs that much is a capability nobody uses, so every beat got matched to one of the
existing registers whether or not one of them could actually carry its argument.

This makes it one command, so "no register can draw this" stops being a reason to settle.

AFTER RUNNING IT: write the shot's body (the stub renders its own name), then run BOTH emits — the scaffold
writes a placeholder into TWO tables (SHOT_LUMA and DNA_GROUND_TOKEN) and each has its own mode, so one
command leaves the other still flagged 'never measured' and `test_shot_luma_is_measured_not_guessed` failing:
  python3 scripts/measure_ground_luma.py --only <Id> --luma --emit   # SHOT_LUMA: its ground with NO DNA
  python3 scripts/measure_ground_luma.py --only <Id> --emit          # DNA_GROUND_TOKEN: which token it paints from
  python3 scripts/shot_proof.py <out_dir>                            # frame-craft + palette + reuse checks

DO NOT EDIT A REGISTER WHILE A LIBRARY SWEEP IS RUNNING. `register_energy.py` and `prop_reach.py` re-render
every register from the working tree, so a source saved mid-sweep is measured in whatever state it was in at
that instant and the manifest records it as the register's own behaviour. It happened: a half-applied edit
was swept and written up as `SameStuffChanged refused to render — ReferenceError cells is not defined`,
which is a true sentence about a file that existed for ninety seconds. Finish the edits, THEN sweep — and if
one slips through, `--only <Id>` re-measures the affected rows without repeating the other 183.
  python3 scripts/cjk_type_qa.py --only <Id> --all-aspects            # type in Chinese, at EVERY aspect
      (--all-aspects matters: this is the only audit that can see a string the register declined to
       DRAW. text_safe_qa reports type CUT OFF, so it can only see ink that exists — WordTunnel's
       final phrase was culled for width at 1:1 and the shot ended on an empty frame while
       text_safe_qa reported 0 findings at all five aspects in both languages.)
(The earlier text here named `--only <Id>` alone, which MEASURES and writes nothing, and an `--apply-json`
flag that does not exist. Following it left both placeholders in place with no hint that anything was left
to do — the first new register in a while is what found that.)
"""
import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(_HERE, "..", "remotion")
_SHOTS = os.path.join(_REM, "src", "shots")

STUB = '''// SHOT · {id} — {use_when}
// A NEW register: the ARGUMENT SHAPE lives here, the topic arrives entirely through props, so any later
// film making the same kind of claim can reach for it. Replace this stub with the real design.
//
// THREE RULES THIS TIER LEARNED THE HARD WAY — all three shipped past every gate before they were caught
// by a viewer, so they are stated here where they are unavoidable:
//
// 1. EVERY WORD ON SCREEN COMES FROM A PROP. Never write copy as a literal in the JSX. A literal has no
//    default to differ from, so shot_proof's demo-default check cannot see it, and it prints on every film
//    that ever uses this register — `WORKBUDDY`, `DASHBOARD`, `©2026 · LOCAL`, `x:960 y:540` all shipped
//    that way. If a word genuinely belongs to the FORM (an axis label, a REC light), declare it:
//       export const INTRINSIC_TEXT = ['REC', '▶ PLAY'];
//    `scripts/onscreen_text_qa.py` reports violations; a test holds the line.
//
// 2. NEVER INVENT A NUMBER — and give a measurement a prop with NO DEFAULT, unlike copy. A readout, a
//    coordinate, a measurement comes from props or is not drawn. `x:960 y:540` was the centre of a
//    1920x1080 frame printed beside a cathedral as though it measured it; `{{specN}}`, counting 0->100 off
//    the clock, printed "100%" over a beat whose claim was that the nave was NEVER finished. The second
//    one has no letters in it, so no word-scan can see it — `unsourced_numbers()` traces provenance
//    instead: a rendered value reaches back to a prop, or the readout does not render. It catches the inline
//    form too (`{{Math.round(t * 100)}}%`), because a number computed from the CLOCK measures nothing. If a
//    numeral genuinely belongs to the FORM — a tape deck's timecode, a frame counter — declare it:
//       export const INTRINSIC_READOUT = true;
//    And your entry in shotLuma.ts is written as 'dark' PROVISIONALLY: run
//    `python3 scripts/measure_ground_luma.py --luma --emit` to replace the guess with the pixels.
//
// 3. A LABEL BESIDE A POINT MUST BE CLAMPED INTO ITS BOX. Choosing a side by `x > 0.5` reads the point's
//    half, not the room left, so a point near an edge pushes its label out of the container. Use
//    `placeLabel(x, x0, x1, labelW, gap)` from runtime/layout. No raster check can catch this one: text
//    crossing a drawn border and a full-bleed field reaching the frame edge are the same pixels.
//
// And size type off `Math.min(W, H)`, never a bare px literal — a 44px caption is 2.3% of a 1920-wide
// frame and 4.1% of a 1080-wide portrait one.

import React from 'react';
import {{AbsoluteFill, useVideoConfig}} from 'remotion';
import {{useT, seg, clamp01, easeOutCubic}} from '../runtime/motion';
import {{captionBand, CONTENT_TOP}} from '../runtime/layout';
// import {{Plane, DEPTH}} from '../runtime/depth';   // DEPTH, when the beat's argument IS about depth
//   <Plane depth={{DEPTH.behind}}>…</Plane> puts a layer one step back: smaller, softer, and it parallaxes
//   against the camera. `DEPTH.lifted` puts one ON the surface — it keeps its registration exactly (it must,
//   if it is annotating a point) and casts a drop-shadow that follows the content's own alpha.
//   It is 2D on purpose: measured on this renderer, a text-dense shot under perspective+translateZ lost 38%
//   of its glyph edge strength and reads fuzzy; the same shot under a 2D scale is indistinguishable from
//   the baseline. Use it only where it ENCODES the beat — PlanPalimpsest puts the earlier survey one plane
//   back because "two plans in register on the same ground" is that register's whole claim. Scattering
//   things across planes for the look of it is decoration, and this library treats that as a defect.
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


def register(shot, family=None, use_when="", provenance=""):
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
            # PROVISIONAL, and it says so. This used to write a bare `'dark',` — a guess that looked exactly
            # like the measured entries around it, so nothing could tell them apart and nobody came back. Nine
            # registers created in one session were cream-coloured and all declared dark, and the luminance
            # guard that exists to prevent a bright-over-dark flash was reading the opposite of the truth.
            # Marked, `measure_ground_luma.py --luma --check` can see it is unmeasured and say so.
            s = re.sub(r"(export const SHOT_LUMA[^{]*\{\n)",
                       r"\g<1>  %s: 'dark',   // PROVISIONAL — placeholder, not a measurement; run "
                       r"measure_ground_luma.py --luma --emit\n" % shot, s, count=1)
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

    # A family whose existing members ALL come from a different idiom world is almost certainly the wrong
    # shelf. PhotoPlate was filed into the measured-drawing family on its author's say-so even though its
    # provenance is `photographic`, and the first film to use it tripped the adjacent-family gate — the
    # taxonomy error surfaced as a composition warning three steps downstream.
    if family and provenance:
        try:
            import shot_director as _sd
            peers = [n for n, f in _sd.FAMILY.items() if f == family and n != shot]
            worlds = {_sd.PROVENANCE.get(n) for n in peers if _sd.PROVENANCE.get(n)}
            if peers and worlds and provenance not in worlds:
                print("  note: family %s currently holds only %s registers, and this one is %r — check it "
                      "is the right shelf before the adjacency gate finds out for you."
                      % (family, "/".join(sorted(worlds)), provenance))
        except Exception:
            pass

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

    # shot_director.PROVENANCE — which WORLD this shot's idiom comes from. A register that is registered
    # everywhere but carries no provenance is silently EXEMPT from the idiom-world gate: validate looks the
    # shot up, gets nothing, and skips it. That would have made the gate decay to nothing as the library
    # grew, since every newly built register would arrive untagged. So it is a sync point like the others.
    if provenance:
        def _prov(s):
            if '"%s":' % shot in s.split("PROVENANCE = {", 1)[-1].split("\n}", 1)[0]:
                return s
            m = re.search(r"(PROVENANCE = \{\n)", s)
            if not m:
                return None
            return s[:m.end()] + '    %-26s %r,\n' % ('"%s":' % shot, provenance) + s[m.end():]
        fam_path = os.path.join(_HERE, "shot_director.py")
        out["shot_director.PROVENANCE"] = _edit(fam_path, ['"%s": %r' % (shot, provenance)], _prov, "provenance")

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
    "provenance": "shot_director.py",
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
        # A GROUND MAY BE A COLOUR, not a token: a register that paints its own stock whatever the palette is
        # (PaperSlot) declares `'#efe9dd'` there, and reading only the GroundToken union reported it as
        # never registered — a sync check that fails on a correct table is a sync check people switch off.
        "luma_ground": r"(?<![A-Za-z0-9_])%s:\s*('(%s)'|'#[0-9a-fA-F]{3,6}'|\[)" % (b, grounds),
        "family": r'"%s":\s*"[A-Z]{1,2}"' % b,
        "provenance": r'"%s":\s*\x27[a-z-]+\x27' % b,
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


def family_census_block():
    """The catalogue's family census, generated from shot_director.FAMILY.

    A director reading LIBRARY.md sees a long list of registers and no sense of how the families are
    stocked. Nine of twenty-five hold ONE register, so "vary the family" quietly pushes every film toward
    the four big ones, and a beat whose argument wants a thin family has no room to pick a better fit —
    which is the moment to BUILD, not to settle for the only member.
    """
    import collections
    sys.path.insert(0, _HERE)
    import shot_director as sd
    # RE-READ, do not trust the import. `register()` edits shot_director.py in this same process, and if
    # the module was imported BEFORE that edit — which it is, the family-peer hint at registration time
    # imports it — `sd.FAMILY` is the pre-edit dict from the module cache. The census was then rewritten
    # from stale memory and reported one register fewer than the file holds, which is exactly the drift the
    # sync test then failed on: a generator that cannot see the edit it was called to record.
    import importlib
    sd = importlib.reload(sd)
    c = collections.Counter(sd.FAMILY.values())
    rows = " · ".join("%s×%d" % (f, n) for f, n in sorted(c.items(), key=lambda x: (-x[1], x[0])))
    thin = sorted(f for f, n in c.items() if n <= 2)
    return (
        "<!-- FAMILY-CENSUS (generated: scripts/register_shot.py rewrites it; a test fails if it drifts) -->\n"
        "**Family census — %d registers across %d families.** %s\n\n"
        "**%d families hold two registers or fewer: %s.** That is a BUILD signal, not a menu. When a beat's\n"
        "argument wants one of those languages and the one register there does not carry it, the answer is\n"
        "`register_shot.py` — settling for the only member is how a film ends up with a beat whose design is\n"
        "merely adjacent to its meaning. The big families (D, A, C, G) are where a director drifts by default;\n"
        "notice when you are there because it fits, and when you are there because it was stocked.\n"
        "<!-- /FAMILY-CENSUS -->\n" % (sum(c.values()), len(c), rows, len(thin), ", ".join(thin)))


# BOTH emits, named explicitly, as a module CONSTANT rather than a literal inside print().
#
# The scaffold places a placeholder in SHOT_LUMA *and* in DNA_GROUND_TOKEN; each is written by a different
# mode of measure_ground_luma, and the old one-command hint left a new register permanently flagged as
# unmeasured with the sync test failing and no way to satisfy it. It lives here so a probe can READ it: a
# check that opens this file from disk cannot be mutated, so the rule it guards is not load-bearing and the
# mutation harness says so.
NEXT_STEPS = (
    "  next: write the shot body, then BOTH of:\n"
    "    python3 scripts/measure_ground_luma.py --only %(s)s --luma --emit   # SHOT_LUMA\n"
    "    python3 scripts/measure_ground_luma.py --only %(s)s --emit          # DNA_GROUND_TOKEN\n"
    "    python3 scripts/cjk_type_qa.py --only %(s)s --all-aspects            # type in Chinese, EVERY aspect\n"\
    "      (--all-aspects matters: this is the only audit that sees a string the register declined to DRAW —\n"\
    "       text_safe_qa reports type CUT OFF, so it can only see ink that EXISTS)"
)


def next_steps(shot):
    return NEXT_STEPS % {"s": shot}


def refresh_family_census():
    """Rewrite the census and the headline count in LIBRARY.md. Called after every registration so neither can
    go stale. The headline's "(N design languages)" is the one number a reader takes on trust, and no step
    touched it: it drifted by 41 once, and adding DeviceDemo left it one short at once. It counts what the gate
    in tests/test_library_signatures.py counts — the register files on disk."""
    p = os.path.join(_REM, "LIBRARY.md")
    try:
        src = open(p, encoding="utf-8").read()
    except OSError:
        return False
    block = family_census_block()
    if "<!-- FAMILY-CENSUS" not in src:
        return False
    new = re.sub(r"<!-- FAMILY-CENSUS.*?<!-- /FAMILY-CENSUS -->\n", lambda _m: block, src, flags=re.S)
    on_disk = len(glob.glob(os.path.join(_SHOTS, "*.tsx")))
    head, nl, rest = new.partition("\n")                 # the headline is LINE 1: never a later sentence
    new = re.sub(r"\((\d+)\s+design languages\)", "(%d design languages)" % on_disk, head, count=1) + nl + rest
    if new != src:
        open(p, "w", encoding="utf-8").write(new)
    return True


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
    provenance = ""
    if "--provenance" in argv:
        i = argv.index("--provenance")
        if i + 1 < len(argv):
            provenance = argv[i + 1].strip()
    if provenance:
        import shot_director as _sd
        if provenance not in _sd.IDIOM_WORLDS:
            print("[register_shot] --provenance %r is not a known idiom world. Known: %s"
                  % (provenance, ", ".join(_sd.IDIOM_WORLDS)))
            return 2
    if not family:
        print("[register_shot] give a family letter (A-Z, or a new two-letter one): register_shot.py Id D --use-when '…'")
        return 2
    use_when = re.sub(r"\s+", " ", use_when).strip()[:160]   # a newline here produced an invalid .tsx
    res = register(shot, family, use_when, provenance)
    for k, v in res.items():
        print("  %-28s %s" % (k, v))
    failed = [k for k, v in res.items() if str(v).startswith("FAILED")]
    if failed:
        # Printing FAILED and then reporting success two lines later is how a wrapper reading the exit
        # code sails past a half-registered shot.
        print("[register_shot] %s — could not edit: %s. Nothing else is trustworthy; fix the anchor."
              % (shot, ", ".join(failed)))
        return 1
    refresh_family_census()          # the census is a decision input; a stale one is worse than none
    miss = check(shot)
    print("[register_shot] %s — %s" % (shot, "registered everywhere" if not miss else "STILL MISSING: " + ", ".join(miss)))
    if not miss:
        print(next_steps(shot))
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
