#!/usr/bin/env python3
"""Does any register draw a claim the film did not make? — the static half of the content contract.

    python3 scripts/content_contract_qa.py              # the whole library + runtime/uiSurface
    python3 scripts/content_contract_qa.py BentoReveal  # one or more registers

WHY THIS EXISTS. A user looked at a delivered frame whose six cells were labelled with anime characters and
asked what a sparkline, a loading ring and a sine wave had to do with 路飞. Nothing: `BentoReveal` chose each
cell's widget by its INDEX (`kind={(i - 1) % 6}`), computed the bar heights from the index and the clock, and
cycled the film's labels to fill six slots. The repair was made in that register, and a read of all 168
registers afterwards found the same class in roughly sixty more, in six shapes: a status set by position
(`k < 2 ? '✓'`), an emphasis set by position (`const HERO = 2`), a picture set by position, a quantity made
up (`hash01(i)` tower heights, a hardcoded rising series under a sourced figure), a film figure re-typed
(`parseFloat(v.replace(/[^\\d.]/g, ''))` turning "−12" into 12), and a missing piece filled with a constant
(`fill ?? 0.6`). Every gate in the repo was green on all of them, because every gate measures TYPE — whether
it is cut off, whether it was drawn — and none asks whether a PICTURE is a claim.

A picture, a status, an emphasis or a quantity beside a film's label is a claim about that label. This reads
the source for the shapes those claims were made in. It is a tripwire, not a judge: it finds the syntax the
defect has been written in, and the meaning is still the shot-critic's to decide. Anything it flags that is
genuinely not a claim — a palette, a polygon wrap, a layout that puts the first cell on the left — carries a
declaration on the line or the line above, WITH its reason:

    // @positional: <why position is the meaning here>
    // @cycles: <why repeating this list is not repeating content>
    // @fallback: <why this constant is not a reading about the item>
    // @decor: <why these made-up numbers are texture, not a reading about anything the film named>
    // @truncates: <why dropping the tail of this list is not dropping anything the film gave>

A declaration with no reason does not count.

THE RULES (`RULES` below names each):
  cycle      a list indexed modulo its own length or a literal, unless the list is a palette/font stack
  position   a status or emphasis decided by comparing an index to a non-zero literal (`i === 3`, `k < 2 ?`,
             `i % 3 === 0`)
  relabel    a default datum that already HAS a label, spread and given the film's label instead
  retype     a film figure stripped to digits (`.replace(/[^\\d.]/g, '')`) or rounded straight out of parseFloat
  fallback   a per-item quantity/coordinate filled with a numeric constant (`x.fill ?? 0.6`)
  truncate   a list cut with `.slice(0, N)` — the film's items past N vanish in silence; throw with the maximum
             instead (every item is drawn once, or the register says it cannot)
  invent     numbers the register makes up for something that reads as data: a hash feeding a height or a
             value, a hardcoded run of fractions (`[0.5, 0.82, 0.4, 0.95]`), a hardcoded table of index pairs
             (graph edges), a hardcoded per-index table of kinds, a constant that picks the emphasised item

CALIBRATED on the committed library before the repair, against an independent read of every register: it
found the index-picked widgets, the cycled labels, the positional done-marks, the re-typed figures and the
constant fills, and it flagged alternation (`i % 2`), cellular-automaton rules and stage-specific drawing as
false positives — which is why `% 2` and a bare `n` are not index tests here. What it does NOT see, by
construction: an index derived from the clock (`Math.floor(seg(t, ...) * 3)`), a fill that ignores its prop
and runs on the clock, and a first-item emphasis written `i === 0` (too common as honest layout to flag).
Those stay the shot-critic's.
"""
import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(_HERE, "..", "remotion", "src")
SHOTS = os.path.join(_REM, "shots")
EXTRA = [os.path.join(_REM, "runtime", "uiSurface.tsx")]

RULES = ("cycle", "position", "relabel", "retype", "fallback", "invent", "truncate")
_DECL = {
    "cycle": "cycles", "position": "positional", "relabel": "positional",
    "retype": "fallback", "fallback": "fallback", "invent": "decor", "truncate": "truncates",
}

_LINE_COMMENT = re.compile(r"//.*$")
_COLOUR = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\(|var\(--|oklch\()")
_FONTISH = re.compile(r"(serif|sans|mono|cursive|fantasy|system-ui|Impact|Georgia|Helvetica|Arial|Courier)", re.I)


def _declared(lines, idx, rule):
    """A declaration for `rule` on this line or the line above, with a reason after the colon."""
    tag = _DECL[rule]
    pat = re.compile(r"//[ \t]*@%s:[ \t]*\S" % re.escape(tag))
    return any(pat.search(lines[k]) for k in (idx, idx - 1) if 0 <= k < len(lines))


def _initializer(src, name):
    """The text assigned to `const|let name` (up to the statement's end at bracket depth 0), or None."""
    m = re.search(r"\b(?:const|let)\s+%s\b[^=\n]*=\s*" % re.escape(name), src)
    if not m:
        return None
    depth, j = 0, m.end()
    while j < len(src):
        ch = src[j]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                break
        elif ch in ";\n" and depth == 0:
            break
        j += 1
    return src[m.end():j]


def _is_style_list(src, name, seen=None):
    """A palette or a font stack: every string literal it holds is a colour or a face, or it comes from
    `dnaPalette`. Followed through `a ?? B` and plain aliases one name at a time."""
    seen = seen or set()
    if name in seen:
        return False
    seen.add(name)
    init = _initializer(src, name)
    if init is None:
        return False
    if "dnaPalette(" in init or "Palette(" in init:
        return True
    strings = re.findall(r"'([^']*)'|\"([^\"]*)\"", init)
    vals = [a or b for a, b in strings]
    if vals:
        return all(_COLOUR.match(v) or _FONTISH.search(v) for v in vals)
    refs = [r for r in re.findall(r"\b([A-Za-z_]\w*)\b", init) if r not in ("dna", "null", "undefined")]
    return bool(refs) and all(_is_style_list(src, r, seen) for r in refs if _initializer(src, r) is not None) \
        and any(_initializer(src, r) is not None for r in refs)


_CYCLE_LEN = re.compile(r"\b(\w+)\[[^\[\]]*%\s*(\w+)\.length\s*\]")
_CYCLE_LIT = re.compile(r"\b(\w+)\[[^\[\]]*%\s*\d+\s*\]")
_POS_EQ = re.compile(r"\b(i|j|k|idx|index)\s*===\s*([1-9]\d*)\b")
_POS_LT = re.compile(r"\b(i|j|k|idx|index)\s*(<|<=|>|>=)\s*([1-9]\d*)\s*\?")
_POS_MOD = re.compile(r"\b(i|j|k|idx|index)\s*%\s*([3-9]|\d\d+)\s*===\s*\d+")   # % 2 is alternation
_KIND_MOD = re.compile(r"\b(kind|shape|glyph|icon|widget|motif|variant|form|mark)\w*\s*[=:]\s*\{?\s*\(?[^;\n]*\b(i|j|k)\b[^;\n]*%\s*\d+")
# `.slice(0, 4)` / `.slice(0, MAX)` on a list — not on a hex string (`h.slice(0, 6)` parses a colour)
_TRUNCATE = re.compile(r"\b([A-Za-z_]\w*)\b[^;\n]*?\.slice\(\s*0\s*,\s*[A-Z0-9_]+\s*\)")
_SPREAD = re.compile(r"\{\s*\.\.\.\s*(\w+)(?:\[[^\]]*\])?\s*,\s*(label|name|title|text)\s*:")
# `DEFAULTS.map((d, i) => ({...d, label: ...}))` — the spread names the map's parameter, so follow it to the list
_MAP_SPREAD = re.compile(r"\b(\w+)\.map\(\s*\(\s*(\w+)[^)]*\)\s*=>\s*\(\s*\{\s*\.\.\.\s*\2\s*,\s*(label|name|title|text)\s*:")
_RETYPE = re.compile(r"\.replace\(\s*/\[\^\\d[^/]*\]/g|Math\.round\(\s*parseFloat\(")
_FALLBACK = re.compile(r"(?:\b\w+|\])\??\.\s*(fill|value|pct|share|count|mean|spread|x|y|w|h|height|size)\s*\?\?\s*-?\d*\.?\d+\b")
_PICK_CONST = re.compile(r"\bconst\s+(hero|focal|hot|target|active|selected|winner|highlight|current)\w*\s*=\s*[1-9]\d*\s*;", re.I)
# exact names: `h\w*` also matched `ha = hash01(...)`, and `fill=` is an SVG colour far more often than a level
_HASH_QTY = re.compile(r"\b(h|hFrac|height|heightFrac|barH|value|pct|count|level)\s*[:=][^;\n]*hash01\(")
_FRACTION_RUN = re.compile(r"=\s*\[\s*(?:0?\.\d+\s*,\s*){3,}0?\.\d+\s*,?\s*\]")
_PAIR_TABLE = re.compile(r"\[\s*\[\s*\d+\s*,\s*\d+\s*\]\s*,\s*\[\s*\d+\s*,\s*\d+\s*\]\s*,")
_UNIT_GRID = re.compile(r"^\[\s*(\[\s*[01]\s*,\s*[01]\s*\]\s*,?\s*)+\]$")   # [[0,0],[1,0],...] is a 2x2 layout
_KIND_TABLE = re.compile(r"\bconst\s+(kinds?|types?|shapes?|glyphs?|icons?|widgets?|forms?)\w*\s*(?::[^=]+)?=\s*\[\s*'")


def violations(src, name=""):
    """[(line_no, rule, line_text)] for one register's source."""
    out = []
    lines = src.split("\n")
    for idx, raw in enumerate(lines):
        code = _LINE_COMMENT.sub("", raw)
        if not code.strip() or code.lstrip().startswith("*"):
            continue

        def hit(rule):
            if not _declared(lines, idx, rule):
                out.append((idx + 1, rule, raw.strip()))

        for m in _CYCLE_LEN.finditer(code):
            if m.group(1) == m.group(2) and not _is_style_list(src, m.group(1)):
                hit("cycle")
                break
        else:
            for m in _CYCLE_LIT.finditer(code):
                if not _is_style_list(src, m.group(1)):
                    hit("cycle")
                    break
        if _KIND_MOD.search(code):
            hit("cycle")
        if _POS_EQ.search(code) or _POS_LT.search(code) or _POS_MOD.search(code):
            hit("position")
        sources = [m.group(1) for m in _SPREAD.finditer(code)] + [m.group(1) for m in _MAP_SPREAD.finditer(code)]
        for name_ in sources:
            init = _initializer(src, name_)
            if init and re.search(r"\b(label|name|title|text)\s*:", init):
                hit("relabel")
                break
        if _RETYPE.search(code):
            hit("retype")
        if _FALLBACK.search(code):
            hit("fallback")
        # A CAP IS A CAP WHATEVER IT IS SPELLED. This read `[A-Z0-9_]+` only, so `.slice(0, ROUTE.length)`
        # — a list cut to the length of the register's own table of poses — was invisible, and `SpatialSlides`
        # dropped a film's sixth step in silence while this checker reported it clean. Any expression that is
        # not a string index is a cap: a constant, a member (`X.length`), or a local.
        for m_tr in re.finditer(r"\.slice\(\s*0\s*,\s*([A-Za-z0-9_.\[\]]+)\s*\)", code):
            recv = re.search(r"([A-Za-z0-9_]+)\W*$", code[:m_tr.start()])
            cap = m_tr.group(1)
            name = recv.group(1) if recv else ""
            tail = code[m_tr.end():m_tr.end() + 24]
            # a string being shortened (a hex colour parsed, an error message quoting its input) is not a list
            if name in ("h", "hex", "v", "str", "txt", "text", "name", "id", "raw", "s"):
                continue
            # A REVEAL IS NOT A CUT. `command.slice(0, typed)` types a string out character by character and
            # shows all of it by the settled frame; flagging it teaches the reader to ignore this rule, which
            # is how a checker that cries wolf ends up protecting nothing.
            if cap in ("typed", "cut", "chars", "shown", "revealed", "visible", "nChars", "letters"):
                continue
            # A PREFIX SUM IS NOT A CUT EITHER: `metric.slice(0, i).reduce(...)` adds up what came before i.
            if tail.lstrip().startswith(".reduce("):
                continue
            # NOR IS A SPLIT: `[items.slice(0, half), items.slice(half)]` keeps both halves.
            if re.search(r"\.slice\(\s*%s\s*\)" % re.escape(cap), code):
                continue
            # NOR IS CUTTING THE REGISTER'S OWN DEFAULT TABLE DOWN TO THE FILM'S COUNT — `ROUTE.slice(0, n)`
            # takes as many poses as the film gave steps. The table is the register's, not the film's.
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
                continue
            hit("truncate")
            break
        if _PICK_CONST.search(code):
            hit("position")
        pair = _PAIR_TABLE.search(code)
        if pair:
            whole = re.match(r"\[(?:[^\[\]]|\[[^\[\]]*\])*\]", code[pair.start():])
            if whole and _UNIT_GRID.match(whole.group(0)):
                pair = None
        if _HASH_QTY.search(code) or _FRACTION_RUN.search(code) or pair or _KIND_TABLE.search(code):
            hit("invent")
    # one finding per (line, rule)
    seen, uniq = set(), []
    for v in out:
        if v[:2] not in seen:
            seen.add(v[:2])
            uniq.append(v)
    return uniq


def library(names=None):
    files = sorted(glob.glob(os.path.join(SHOTS, "*.tsx"))) + EXTRA
    out = {}
    for f in files:
        n = os.path.basename(f)[:-4]
        if names and n not in names:
            continue
        v = violations(open(f, encoding="utf-8").read(), n)
        if v:
            out[n] = v
    return out


def main(argv):
    names = set(argv[1:]) or None
    known = {os.path.basename(f)[:-4] for f in glob.glob(os.path.join(SHOTS, "*.tsx")) + EXTRA}
    unknown = sorted((names or set()) - known)
    if unknown:                     # a misspelt name read "0 finding(s) in 0 file(s)" — a clean bill for nothing
        print("[content_contract_qa] no such register(s): %s" % ", ".join(unknown))
        return 2
    found = library(names)
    for n, vs in found.items():
        for line, rule, text in vs:
            print("%s:%d  [%s]  %s" % (n, line, rule, text[:140]))
    print("%d finding(s) in %d file(s)" % (sum(len(v) for v in found.values()), len(found)))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
