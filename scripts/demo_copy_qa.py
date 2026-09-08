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


def _declared_types(src, name):
    """{prop: declared type} from the component's own props generic, brace-matched.

    Read so a SELECTOR can be told from COPY. `page?: UiPage` defaults to `'cards'`, which is a string that
    reads like a word and is never drawn — it names which page shape a surface renders. Flagged as demo copy
    it produced an error on every beat that used the register, and the author's only way out was to set the
    prop to "" and get no page at all. A default is only copy if the prop is TYPED as copy.
    """
    m = _PROPS_TYPE.sub("", "", count=0) if False else re.search(
        r"export const %s:\s*React\.FC<\{" % re.escape(name), src)
    if not m:
        return {}
    i, depth = m.end() - 1, 0
    for j in range(m.end() - 1, len(src)):
        depth += src[j] == "{"
        depth -= src[j] == "}"
        if depth == 0:
            i = j
            break
    body = src[m.end():i]
    out = {}
    for pm in re.finditer(r"(\w+)\s*\??\s*:\s*([^;]+);", body):
        out[pm.group(1)] = pm.group(2).strip()
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
        elif rest[:1] == "[":
            depth, e = 0, 0
            for e, ch in enumerate(rest):
                depth += ch == "["
                depth -= ch == "]"
                if depth == 0:
                    break
            lit = rest[:e + 1]
            k += e + 1
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


def library(shots_dir=None):
    """{register: {prop: demo default}} across the whole library."""
    out = {}
    for f in sorted(glob.glob(os.path.join(shots_dir or SHOTS, "*.tsx"))):
        n = os.path.basename(f)[:-4]
        d = demo_defaults(open(f, encoding="utf-8").read(), n)
        if d:
            out[n] = d
    return out


def audit_board(board, lib=None):
    """[(scene index, register, prop, the copy that will print)] for every beat that leaves a default in.

    A beat is judged on the props it SUPPLIES: absence is what makes the default render, so an omitted prop
    with a copy default is the finding. A prop supplied as an empty string is a deliberate 'leave it off'
    and passes — the register draws nothing rather than the demo line."""
    lib = library() if lib is None else lib
    found = []
    for s in board.get("slides", []):
        shot = s.get("shot")
        if not shot or shot not in lib:
            continue
        props = s.get("shot_props") or {}
        for prop, copy in sorted(lib[shot].items()):
            if prop not in props:
                found.append((s.get("index"), shot, prop, copy))
    return found


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("usage: demo_copy_qa.py <out_dir> | --library")
        return 0
    if argv[0] == "--library":
        lib = library()
        print("[demo_copy_qa] %d registers carry copy defaults, %d props total"
              % (len(lib), sum(len(v) for v in lib.values())))
        for n, d in sorted(lib.items()):
            print("  %-22s %s" % (n, json.dumps(d, ensure_ascii=False)[:120]))
        return 0
    board = json.load(open(os.path.join(argv[0], "storyboard.json"), encoding="utf-8"))
    found = audit_board(board)
    if not found:
        print("[demo_copy_qa] no beat leaves a demo default in place")
        return 0
    print("[demo_copy_qa] %d beat/prop pair(s) will print the register's DEMO COPY as content:" % len(found))
    for i, shot, prop, copy in found:
        print("    scene %s · %s.%s → %r" % (i, shot, prop, copy))
    print("  Supply the beat's own copy, or set the prop to \"\" to draw nothing there.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
