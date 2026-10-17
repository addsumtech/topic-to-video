#!/usr/bin/env python3
"""A register must not print its own DEMO COPY on a delivered frame.

WHAT THIS CATCHES. Every register carries illustrative defaults so it can be previewed standalone
(`npx remotion still src/index.ts <Id> out.png`) — the authoring path documents that preview, so the
defaults have to stay. But a default is copy, and copy renders: a beat that supplies `src` and `title` and
omits `caption` ships PhotoPlate's "the thing itself" over a real photograph; one that omits `title` on a
dozen registers ships the word **WorkBuddy** onto a film about something else entirely. Nothing anywhere
says so. The render succeeds, `validate.py` sees a non-empty `shot_props`, the energy sweep measures healthy
ink — because placeholder text is ink — and the frame reads as finished English prose about the wrong
subject. I shipped exactly this twice in one session while testing these registers by hand, and only noticed
because I opened the PNG.

It is the same defect as the empty plate and the opposite failure mode: the empty plate says nothing, the
demo default says something FALSE. The house rule it breaks is the first one — never present invented
content as real.

WHY A PARSER AND NOT A LIST. 152 registers, 283 defaulted props, and both numbers move every time someone
adds a register. A checked-in list would be stale before it was reviewed; the signature IS the record.

EXIT 0 = judged its whole universe and found nothing · 1 = findings · 2 = part of the universe was NOT
judged (a beat naming a register that does not exist; a register file that could not be read or whose
signature could not be parsed, so a default it carries is invisible to every film check).
"""
import glob
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(_HERE, "..", "remotion", "src", "shots")

# Colours, CSS keywords and units are configuration, not copy: shipping the default `accent` is a design
# decision the DNA overrides anyway, and no viewer reads "#22d3ee" off the frame.
_NOT_COPY = re.compile(r"^(#|var\(|rgb|hsl|none$|round$|butt$|square$|center$|left$|right$|top$|bottom$"
                       r"|row$|column$|nowrap$|auto$|hidden$|visible$|currentColor$|transparent$)", re.I)


# `= DEFAULT_PANELS` — a default given by naming a module-level constant rather than writing the literal.
_CONST_REF = re.compile(r"([A-Z][A-Z0-9_]*)\b(?!\s*[.(\[])")
# keys whose string values name a picture or a style, not words on the frame
_NOT_COPY_KEYS = re.compile(r"\b(icon|glyph|kind|shape|tone|color|colour)\s*:\s*(['\"])[^'\"]*\2")


def _destructure(src, name):
    """The parameter destructuring block of `export const <name>: React.FC<{...}> = ({ ... } = {}) =>`.

    Brace-matched rather than regexed to the first `} = {})`: a props type containing an object literal
    (`marks?: {n: number}[]`) makes a non-greedy match stop inside the TYPE, and the earlier version of this
    silently read SVG attributes out of the component body as though they were defaults."""
    i = src.find("export const %s:" % name)
    if i < 0:
        i = src.find("export const %s " % name)
    if i < 0:
        return None
    # the arrow function's argument list starts at the first "= (" after the type annotation
    m = re.search(r"=\s*\(\s*\{", src[i:])
    if not m:
        return None
    start = i + m.end() - 1                      # the '{' of the destructure
    depth, j = 0, start
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[start + 1:j]
        j += 1
    return None


_PROPS_TYPE = re.compile(r"export const %s:\s*React\.FC<\{")
_COMMENTS = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def _brace_body(src, i):
    """The inside of the `{...}` block that starts at or after `i`, brace-matched. None if there is none."""
    while i < len(src) and src[i].isspace():
        i += 1
    if i >= len(src) or src[i] != "{":
        return None
    depth = 0
    for j in range(i, len(src)):
        depth += src[j] == "{"
        depth -= src[j] == "}"
        if depth == 0:
            return src[i + 1:j]
    return None


_INTERSECTED = re.compile(r"\s*\w+\s*&")


def _past_intersected(src, i):
    """The index past every `Name &` an intersection type opens with at `i` — `ObjectProps & {...}` declares its
    own props in the `{...}` that follows."""
    m = _INTERSECTED.match(src, i)
    while m:
        i = m.end()
        m = _INTERSECTED.match(src, i)
    return i


def _declared_types(src, name):
    """{prop: declared type} from the component's own props generic, brace-matched.

    Read so a SELECTOR can be told from COPY. `page?: UiPage` defaults to `'cards'`, which is a string that
    reads like a word and is never drawn — it names which page shape a surface renders. Flagged as demo copy
    it produced an error on every beat that used the register, and the author's only way out was to set the
    prop to "" and get no page at all. A default is only copy if the prop is TYPED as copy.

    A NAMED props type counts too. `React.FC<Props>` with `type Props = {...}` above it is the same
    declaration written in two places, and reading only the inline form returned {} for those registers —
    every prop then fell back to the "string" assumption, which is the loosest possible reading of the one
    thing this function exists to be strict about. One register in the library is written that way today
    (AcceptanceStamp), and it is the one whose tuple arity `tuple_arity` has to see.

    An INTERSECTION counts as well: `React.FC<ObjectProps & {...}>` (or an alias of it) is how every object is
    declared — the slot's own w/h/t/dna come from `ObjectProps`, and the object's own props are the `{...}`
    after the `&`. Read only up to the base type's name, an object's props came back {} and promote.py
    catalogued every promoted object with no props.
    """
    m = re.search(r"export const %s:\s*React\.FC<" % re.escape(name), src)
    if not m:
        return {}
    body = _brace_body(src, _past_intersected(src, m.end()))
    if body is None:                                             # `React.FC<Alias>` — resolve the alias
        alias = re.match(r"\s*(\w+)", src[m.end():])
        if not alias:
            return {}
        am = re.search(r"\btype\s+%s\s*=\s*" % re.escape(alias.group(1)), src)
        body = _brace_body(src, _past_intersected(src, am.end())) if am else None
        if body is None:
            return {}
    # Comments are stripped FIRST: a doc comment is prose, and prose that happens to hold `word: text;`
    # parses as a prop declaration. The tuple check below turns a mis-read type into an error on a
    # correct board, so the parser may not guess.
    body = _COMMENTS.sub("", body)
    out = {}
    for chunk in _split_top(body, ";"):
        pm = re.match(r"\s*(\w+)\s*\??\s*:\s*(.+)$", chunk, re.S)
        if pm:
            out[pm.group(1)] = pm.group(2).strip()
    return out


_PRIMITIVE = re.compile(r"(?:string|number|boolean)")


def _split_top(s, sep):
    """Split on `sep` only where no bracket is open.

    Two things here were being read wrongly by a plain split. A prop list's LAST entry carries no `;`
    (`React.FC<{cmd?: string; lines?: Line[]; framed?: boolean}>`), so a rule that required one dropped the
    last prop of every inline register and let it fall back to the "string" assumption. And a nested object
    type (`rows?: {label: string; v: number}[]`) holds its own `;`, so splitting on every one of them
    invents a prop called `v`. Depth-aware splitting is the same operation both need.
    """
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "[<({":
            depth += 1
        elif ch in "])>}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [m for m in (x.strip() for x in out) if m and m != "undefined"]


def _union_members(t):
    """Split a type on its TOP-LEVEL `|` — `[string|number,string]|string[]` is two members, not three."""
    return _split_top(t, "|")


def tuple_arity(src, name):
    """{prop: how many items its declared type FIXES} — only where the type fixes a number.

    `items?: [string, string, string]` is a declaration that the register draws three slots. A board that
    hands it four is wrong before anything renders, and until now nothing said so: the fourth item was
    dropped silently by one register (A4 found it in `IsometricAssembly`) and threw mid-render in another
    (`AcceptanceStamp`, which costs a whole bundle + render to discover).

    A claim is made ONLY when every member of the type fixes the SAME length. `[string, string] | string[]`
    fixes nothing — the union says any length is legal — so this stays silent on it rather than enforcing
    the half of the type it likes. That is deliberate: the fix for such a register is to narrow the type to
    what its own runtime already requires, and a checker that guessed past the union would hide the fact
    that the declaration and the code disagree.
    """
    out = {}
    for prop, ty in _declared_types(src, name).items():
        lens = set()
        for mem in _union_members(ty.replace(" ", "")):
            if not (mem.startswith("[") and mem.endswith("]")):
                lens.add(None)
                break
            parts = mem[1:-1].split(",")
            if not parts or not all(_PRIMITIVE.fullmatch(p) for p in parts):
                lens.add(None)
                break
            lens.add(len(parts))
        if len(lens) == 1 and None not in lens:
            out[prop] = lens.pop()
    return out


def arity_library(shots_dir=None):
    """{register: {prop: fixed length}} across the whole library — parsed, never listed."""
    out = {}
    for f in sorted(glob.glob(os.path.join(shots_dir or SHOTS, "*.tsx"))):
        n = os.path.basename(f)[:-4]
        a = tuple_arity(open(f, encoding="utf-8").read(), n)
        if a:
            out[n] = a
    return out


def demo_defaults(src, name):
    """{prop: default} for props whose default is COPY — text a viewer would read as content.

    Includes array defaults holding labelled items (PhotoPlate's two callout chips are a default, and they
    point at nothing while reading as instructions)."""
    block = _destructure(src, name)
    if block is None:
        return {}
    types = _declared_types(src, name)
    def _is_copy(prop):
        t = (types.get(prop) or "string").replace(" ", "")
        return t.startswith("string") or t.startswith("(string")
    out, k = {}, 0
    while k < len(block):
        m = re.compile(r"(\w+)\s*(?::\s*\w+\s*)?=\s*").match(block, k)
        if not m:
            k += 1
            continue
        rest, k = block[m.end():], m.end()
        if rest[:1] in "'\"":
            q = rest[0]
            end = rest.find(q, 1)
            if end < 0:
                continue
            v = rest[1:end]
            k += end + 1
            if re.search(r"[A-Za-z]{3}", v) and not _NOT_COPY.match(v) and _is_copy(m.group(1)):
                out[m.group(1)] = v
        elif rest[:1] == "[" or _CONST_REF.match(rest):
            ref = _CONST_REF.match(rest)
            if ref:
                # A DEFAULT NAMED BY A MODULE CONST is still a default. `panels: PANELS = DEFAULT_PANELS` rendered
                # its four English labels on any film that omitted `panels`, and this reader — which only knew
                # an inline `[...]` — reported the register clean. Resolve the name to its literal in the same
                # file; a name it cannot resolve is skipped, never guessed at.
                # The literal may be an array, an object (`DEMO_FIRST = {label: ..., when: ...}`) or a plain
                # string (`DEMO_ACTION = 'One click'`) — all three print on a film that omits the prop.
                k += ref.end()
                decl = re.search(r"\bconst\s+%s\b(?:\s*:[^=]+)?\s*=\s*([\[{'\"])" % re.escape(ref.group(1)), src)
                if not decl:
                    continue
                arr = src[decl.start(1):]
                if arr[0] in "'\"":
                    end = arr.find(arr[0], 1)
                    v = arr[1:end] if end > 0 else ""
                    if re.search(r"[A-Za-z]{3}", v) and not _NOT_COPY.match(v) and _is_copy(m.group(1)):
                        out[m.group(1)] = v
                    continue
            else:
                arr = rest
            open_, close_ = ("[", "]") if arr[:1] == "[" else ("{", "}")
            depth, e = 0, 0
            for e, ch in enumerate(arr):
                depth += ch == open_
                depth -= ch == close_
                if depth == 0:
                    break
            lit = arr[:e + 1]
            if not ref:
                k += e + 1
            # A picture NAME is configuration, not copy: `icon: 'file'` is not a word a viewer reads.
            lit = _NOT_COPY_KEYS.sub("", lit)
            # SHOW the strings. "[2 items of placeholder copy]" tells an author a prop is missing but not
            # what a viewer will read, so they cannot tell a harmless default from six English labels landing
            # on a Chinese frame — which is the finding this exists to report.
            words = re.findall(r"['\"]([A-Za-z][^'\"]{2,})['\"]", lit)
            words = [w for w in words if not _NOT_COPY.match(w)]
            if words:
                shown = ", ".join(repr(w) for w in words[:6])
                out[m.group(1)] = "[%s%s]" % (shown, ", …" if len(words) > 6 else "")
        else:
            k += 1
    return out


def declared_library(shots_dir=None):
    """{register: set(declared prop names)} — only for registers whose props this reader can see."""
    out = {}
    for f in sorted(glob.glob(os.path.join(shots_dir or SHOTS, "*.tsx"))):
        n = os.path.basename(f)[:-4]
        types = _declared_types(open(f, encoding="utf-8").read(), n)
        if types:
            out[n] = set(types)
    return out


def library(shots_dir=None):
    """{register: {prop: demo default}} across the whole library."""
    return library_covered(shots_dir)[0]


def library_covered(shots_dir=None):
    """({register: {prop: default}}, coverage) — and the coverage is the half that was missing.

    166 OF 170 REGISTERS CARRY A COPY DEFAULT, AND THE REPORT ONLY EVER PRINTED THE 166. Two very different
    things produce an empty `{}` here: a register that genuinely declares no copy default, and one whose
    parameter destructuring or props type this reader could not see — `_destructure` returns None and
    `demo_defaults` returns `{}` with nothing said. The second is a register that can ship its demo copy on a
    delivered frame while this gate reports the film clean, which is the exact defect the header describes.
    So they are separated, and both are named."""
    out, unreadable, no_signature, clean = {}, [], [], []
    files = sorted(glob.glob(os.path.join(shots_dir or SHOTS, "*.tsx")))
    for f in files:
        n = os.path.basename(f)[:-4]
        try:
            src = open(f, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as e:
            unreadable.append((n, "%s: %s" % (type(e).__name__, e)))
            continue
        if _destructure(src, n) is None or not _declared_types(src, n):
            # No signature this reader can see == no defaults it can find. That is not "no defaults".
            no_signature.append((n, "its %s could not be parsed, so no default it carries can be seen"
                                 % ("parameter destructuring" if _declared_types(src, n)
                                    else "props type")))
            continue
        d = demo_defaults(src, n)
        if d:
            out[n] = d
        else:
            clean.append(n)
    cov = {"universe": len(files), "read": len(files) - len(unreadable),
           "with_defaults": len(out), "props": sum(len(v) for v in out.values()),
           "no_defaults": clean, "unreadable": unreadable, "no_signature": no_signature}
    return out, cov


def audit_board(board, lib=None):
    """[(scene index, register, prop, the copy that will print)] for every beat that leaves a default in.

    A beat is judged on the props it SUPPLIES: absence is what makes the default render, so an omitted prop
    with a copy default is the finding. A prop supplied as an empty string is a deliberate 'leave it off'
    and passes — the register draws nothing rather than the demo line."""
    return audit_board_covered(board, lib)[0]


def audit_board_covered(board, lib=None, shots_dir=None, out_dir=None):
    """(findings, coverage) — WHICH BEATS THIS RUN ACTUALLY JUDGED.

    `if not shot or shot not in lib: continue` skipped three different things in one silent branch, and the
    film report then printed "no beat leaves a demo default in place" with no count of beats at all — a line
    that reads as the whole film whether it judged eight beats or none:

      a beat with no `shot`         a still/image beat. Nothing to check, and it should still be counted.
      a `shot` that is not a        a typo, or a register removed since the board was written. Nothing was
      register at all               checked and nothing said so — the beat renders whatever the registry
                                    does with an unknown id, and this gate reported the film clean.
      a register with no copy       genuinely checked: there is no default to leave in. Counted as judged.
      default

    The register universe is read from the shots directory, never restated."""
    lib = library(shots_dir) if lib is None else lib
    known = set(lib) | {os.path.basename(f)[:-4]
                        for f in glob.glob(os.path.join(shots_dir or SHOTS, "*.tsx"))}
    found, judged, skipped, own = [], [], [], []
    slides = board.get("slides") or []
    try:
        import workshop as _ws
        film_shots = _ws.shot_names(out_dir) if out_dir else set()
    except Exception:                                    # noqa: BLE001 — no workshop, no built shots
        film_shots = set()
    for pos, s in enumerate(slides, 1):
        idx = s.get("index", pos)
        shot = s.get("shot")
        if not shot:
            skipped.append((idx, None, "the beat selects no register (a still or image beat) — this gate "
                                       "has nothing to judge on it"))
            continue
        if shot in film_shots and shot not in known:
            # A FILM'S OWN SHOT HAS NO DEMO COPY TO LEAVE IN: every word it draws must come from its props, and
            # `workshop.py check` + shot_proof's words-from-props ask exactly that. Reporting it as "not a register,
            # nothing checked" (exit 2) made a mostly-built film fail this gate over beats it was never for.
            own.append((idx, shot))
            continue
        if shot not in known:
            skipped.append((idx, shot, "%r is not a register in shots/ — nothing on this beat was checked"
                                       % shot))
            continue
        judged.append((idx, shot))
        props = s.get("shot_props") or {}
        # A SUPERSEDED PROP'S DEFAULT NEVER REACHES THE FRAME, so reporting it is a wolf. `PortRail` declares
        # `// @supersedes groups: items`: a beat that supplies `groups` makes `items` dead, whatever the
        # register's own default says — and this CLI reported the delivered AgentHalo film's beat 3 as
        # leaving `PortRail.items → ['Docs','Chat','Mail','Calendar','Wiki']` in place, on a beat whose rail
        # is three named groups. `validate.py` has applied this rule since the declaration existed
        # (validate.py's shot-props lint); the standalone path never did, and the two therefore disagreed
        # about the same board. One reader, `supersedes()`, parsed from the registers themselves.
        dead = set()
        for given, killed in (supersedes().get(shot) or {}).items():
            if given in props:
                dead.update(killed)
        for prop, copy in sorted(lib.get(shot, {}).items()):
            if prop not in props and prop not in dead:
                found.append((idx, shot, prop, copy))
    return found, {"beats": len(slides), "judged": len(judged), "skipped": skipped, "own": own}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("usage: demo_copy_qa.py <out_dir> | --library")
        return 0
    if argv[0] == "--library":
        lib, cov = library_covered()
        # TWO UNIVERSES, AND ONLY ONE OF THEM WAS EVER PRINTED. "166 registers carry copy defaults" is a
        # findings count; the universe is the 170 files it read to get there.
        print("[demo_copy_qa] read %d of %d register file(s) · %d carry copy defaults (%d props) · "
              "%d carry none" % (cov["read"], cov["universe"], cov["with_defaults"], cov["props"],
                                 len(cov["no_defaults"])))
        for n, d in sorted(lib.items()):
            print("  %-22s %s" % (n, json.dumps(d, ensure_ascii=False)[:120]))
        if cov["no_defaults"]:
            print("\n  NO COPY DEFAULT TO LEAVE IN — measured, nothing to report:\n    %s"
                  % " ".join(cov["no_defaults"]))
        for label, rows in (("COULD NOT BE READ", cov["unreadable"]),
                            ("NOT MEASURED — the signature this reader needs could not be parsed, so a "
                             "default it carries would be invisible to every film check", cov["no_signature"])):
            if rows:
                print("\n  %s (%d):" % (label, len(rows)))
                for n, whynot in rows:
                    print("    %-22s %s" % (n, whynot))
        return 2 if (cov["unreadable"] or cov["no_signature"]) else 0
    board = json.load(open(os.path.join(argv[0], "storyboard.json"), encoding="utf-8"))
    found, cov = audit_board_covered(board, out_dir=argv[0])
    print("[demo_copy_qa] judged %d of %d beat(s) · %d beat/prop pair(s) will print the register's DEMO "
          "COPY as content" % (cov["judged"], cov["beats"] - len(cov["own"]), len(found)))
    if cov["own"]:
        print("  n/a on %d beat(s) on this film's own shots (%s): no demo copy exists; their words-from-props are "
              "checked by `workshop.py check` and shot_proof" % (len(cov["own"]),
                                                                 ", ".join("%s %s" % x for x in cov["own"])[:200]))
    for i, shot, prop, copy in found:
        print("    scene %s · %s.%s → %r" % (i, shot, prop, copy))
    if cov["skipped"]:
        print("\n  NOT JUDGED — %d beat(s) this gate said nothing about:" % len(cov["skipped"]))
        for i, shot, whynot in cov["skipped"]:
            print("    scene %s · %s" % (i, whynot))
    if found:
        print("  Supply the beat's own copy, or set the prop to \"\" to draw nothing there.")
        return 1
    # A beat with no register is not a hole (a still has no demo copy); a beat naming a register that does
    # not exist is — this gate checked nothing on it and must not be read as having cleared it.
    return 2 if any(shot for _, shot, _ in cov["skipped"]) else 0



# A PROP CAN BE SUPPLIED BY ANOTHER PROP, and the demo-copy check had no way to know. `PortRail` grew
# `groups` — items that belong to named kinds — and when a board gives groups, `items` is never read; the
# checker saw `items` unset, found demo copy behind it, and reported that 'Docs / Chat / Mail' would print
# on a delivered frame that does not contain them. `SurfaceCarousel` has carried the same shape for weeks
# (`surfaces[]` OR `items[]`+`nav[]`) and would have produced the same false error the first time a board
# used the richer prop.
#
# The relation is DECLARED in the register and parsed here, never listed in this file: a register that grows
# an alternative says so next to the props, where the person adding it is already looking.
#
#     // @supersedes groups: items
#
_SUPERSEDES = re.compile(r"//[ \t]*@supersedes[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*:([^\n]*)")


def supersedes():
    """{register: {provider_prop: [props it supplies]}} — read from the registers' own declarations."""
    out = {}
    for f in sorted(glob.glob(os.path.join(SHOTS, "*.tsx"))):
        name = os.path.basename(f)[:-4]
        for m in _SUPERSEDES.finditer(open(f, encoding="utf-8").read()):
            props = [x.strip() for x in m.group(2).split(",") if x.strip()]
            if props:
                out.setdefault(name, {}).setdefault(m.group(1), []).extend(props)
    return out


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
