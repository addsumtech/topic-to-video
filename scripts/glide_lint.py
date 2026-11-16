#!/usr/bin/env python3
"""glide_lint — every baseline unlock is held for its SPAN, never switched on and off with the motion.

    python3 scripts/glide_lint.py [dir ...]        # default: all of remotion/src; exit 1 on any switched call

runtime/glide's header: the unlock must be on over the whole stretch in which a transform CAN change; switched with
the motion itself, the type jumps from whole-pixel to quarter-pixel on the frame the motion starts and back on the
frame it lands. `glide(transform, on, under?)` is accepted when `on` is the literal `true`, or a name declared
constant for the beat — `const x = true`, or a declaration line carrying `@glide-span: <why constant>`. Anything
else (`e !== 1`, `open > 0 && open < 1`, `t < 0.62`, a name assigned from such an expression) is reported.
Measured: 0.6-1.0 px landing pops on 18 lines of one film; a 0.89 px step in the library's CommandSummon.
"""
import glob
import os
import re
import sys

_CALL = re.compile(r"(?<![\w.$])glide\(")
# THE WHOLE LIBRARY, NOT ONLY shots/ (the audit of 2026-11-15): the runtime, the stages and Film itself switch the
# unlock too, and type drawn there trembles the same way. These sites were found when the scope widened; each is
# PRINTED on every run as known debt, never passed in silence, and the source sweep (the audit's step 5) removes them.
# Keyed by file and the `on` expression, so a moved line stays matched and a new switched call is an ERROR.
KNOWN_SWITCHED = {}     # emptied by the source sweep of 2026-11-16: every site holds its unlock for the span now
# FORWARDERS pass their caller's flag through; the CALLERS are the switch, and are read in their turn: usePlaceGlide's
# `moving` is the first argument of every `place(` call, a kit Tile's `moving` is its JSX prop.
FORWARDS = {("runtime/glide.ts", "glide", "moving"), ("kits/Kit.tsx", "place", "moving")}
_PLACE = re.compile(r"(?:(?<=\.\.\.)|(?<![\w.$]))place\(")      # `...place(` (a spread) is a call; `x.place(` is not
_MOVING_PROP = re.compile(r"\bmoving=\{")
_USES_PLACE = re.compile(r"\bplace\s*=\s*usePlaceGlide\(\)")
# runtime/glide.ts's own forwarding call — `useGlide` passes its caller's `on` through, gated by the context
_FORWARD = ["transform", "allowed && on", "under"]


def _args(src, i):
    """The top-level arguments of the call whose '(' ends at index i, and the index after its ')'."""
    depth, cur, args, j, tmpl = 1, "", [], i, 0
    quote = None
    while j < len(src) and depth:
        c = src[j]
        if quote:
            cur += c
            if c == "\\":
                cur += src[j + 1] if j + 1 < len(src) else ""
                j += 2
                continue
            if quote == "`" and c == "$" and j + 1 < len(src) and src[j + 1] == "{":
                tmpl += 1
                quote = None
                cur += "{"
                j += 2
                depth += 1
                continue
            if c == quote:
                quote = None
            j += 1
            continue
        if c in "'\"`":
            quote = c
            cur += c
        elif c in "([{":
            depth += 1
            cur += c
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                break
            cur += c
            if c == "}" and tmpl:
                tmpl -= 1
                quote = "`"
        elif c == "," and depth == 1:
            args.append(cur.strip())
            cur = ""
        else:
            cur += c
        j += 1
    args.append(cur.strip())
    return args, j


def _constant_names(src):
    """Names declared constant for the beat: `const x = true` or a declaration marked `@glide-span:`."""
    out = set()
    for m in re.finditer(r"(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*([^;\n]*)(;?[^\n]*)", src):
        name, rhs, rest = m.group(1), m.group(2).strip(), m.group(3)
        if rhs == "true" or "@glide-span:" in rest:
            out.add(name)
    return out


def switched(src, path=""):
    """[(line, on)] for every unlock that is not held for the span: a `glide(t, on)` call's `on`, a `place(on, …)`
    call's first argument (runtime/glide usePlaceGlide), and a `moving={on}` prop (kits/Kit Tile)."""
    consts = _constant_names(src)
    rel = path.replace("\\", "/").split("remotion/src/")[-1]
    out = []

    def held(on):
        return on in ("true", "") or on in consts

    # `place` is usePlaceGlide's only where the file takes it from there (other files have a `place` of their own), and
    # `moving` is the unlock only on a kit Tile
    scans = [(_CALL, "glide")] + ([(_PLACE, "place")] if _USES_PLACE.search(src) else []) + [(_MOVING_PROP, "prop")]
    for rx, which in scans:
        for m in rx.finditer(src):
            if which == "prop" and not re.search(r"<Tile\b[^<>]*$", src[max(0, m.start() - 600):m.start()]):
                continue
            line_start = src.rfind("\n", 0, m.start()) + 1
            if src[line_start:m.start()].lstrip().startswith(("//", "*")):
                continue
            if which == "prop":
                on = _args(src, m.end())[0][0]
            else:
                args, _ = _args(src, m.end())
                if which == "glide" and (len(args) < 2 or args == _FORWARD):
                    continue
                if which == "place" and not args:
                    continue
                on = args[1] if which == "glide" else args[0]
            if held(on) or (rel, which, on) in FORWARDS:
                continue
            out.append((src.count("\n", 0, m.start()) + 1, on if which == "glide" else "%s: %s" % (
                "place(on, …)" if which == "place" else "<Tile moving>", on)))
    return out


def scan(*dirs):
    """[(file, line, on)] over every .tsx/.ts file under the given directories."""
    bad = []
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "**", "*.ts*"), recursive=True)):
            if not f.endswith((".ts", ".tsx")):
                continue
            src = open(f, encoding="utf-8").read()
            for ln, on in switched(src, f):
                bad.append((os.path.relpath(f, d), ln, on))
    return bad


def main(argv):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dirs = argv or [os.path.join(here, "remotion", "src")]
    bad = scan(*dirs)
    known = [b for b in bad if (b[0], b[2]) in KNOWN_SWITCHED] if not argv else []
    bad = [b for b in bad if b not in known]
    for f, ln, on in known:
        print("[glide_lint] KNOWN %s:%d glide(..., %s) — %s (the source sweep removes it)"
              % (f, ln, on, KNOWN_SWITCHED[(f, on)]))
    for f, ln, on in bad:
        print("[glide_lint] ERROR %s:%d %s — the unlock switches with the motion; hold it for the span "
              "(`true`, or a name marked `@glide-span: <why constant over the beat>`)"
              % (f, ln, on if ": " in on else "glide(..., %s)" % on))
    print("[glide_lint] %s  %d switched call(s)%s" % ("FAIL" if bad else "OK", len(bad),
                                                     ", %d known (listed above)" % len(known) if known else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
