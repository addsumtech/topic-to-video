#!/usr/bin/env python3
"""glide_lint — every baseline unlock is held for its SPAN, never switched on and off with the motion.

    python3 scripts/glide_lint.py [dir ...]        # default: remotion/src/shots; exit 1 on any switched call

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
    """[(line, on)] for every glide call whose `on` is not held for the span."""
    consts = _constant_names(src)
    out = []
    for m in _CALL.finditer(src):
        line_start = src.rfind("\n", 0, m.start()) + 1
        if src[line_start:m.start()].lstrip().startswith(("//", "*")):
            continue
        args, _ = _args(src, m.end())
        if len(args) < 2 or args == _FORWARD:
            continue
        on = args[1]
        if on == "true" or on in consts:
            continue
        out.append((src.count("\n", 0, m.start()) + 1, on))
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
    dirs = argv or [os.path.join(here, "remotion", "src", "shots")]
    bad = scan(*dirs)
    for f, ln, on in bad:
        print("[glide_lint] ERROR %s:%d glide(..., %s) — the unlock switches with the motion; hold it for the span "
              "(`true`, or a name marked `@glide-span: <why constant over the beat>`)" % (f, ln, on))
    print("[glide_lint] %s  %d switched call(s)" % ("FAIL" if bad else "OK", len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
