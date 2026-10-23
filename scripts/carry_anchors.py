#!/usr/bin/env python3
"""Which CARRY ANCHORS each register draws — read from the source, the way the renderer will find them on the frame.

  python3 scripts/carry_anchors.py                 # every register that declares an anchor, and its ids
  python3 scripts/carry_anchors.py DeviceHero      # one register's anchors

WHY THIS EXISTS. Three seams take hold of ONE marked element (remotion/src/seams.tsx): `container` carries it from
one beat into the next, `grow` opens the next beat out of it, `through-window` pushes into it. A register marks the
element with `data-carry="<id>"` (or `<CarryAnchor id="<id>">`, runtime/carry.tsx). A board that asks for a seam on
an anchor the register does not draw would reach the render and stop there (the seam cancels it) — so `validate.py`
asks this module first and refuses the board in a second, and `seam_plan.py` only proposes an anchored seam between
beats whose registers actually share an anchor.

WHAT IT READS. A register's own source, plus the anchors of the runtime components it DRAWS: `runtime/device.tsx`
marks the screen inside `Device`, so every register that writes `<Device` carries `screen` — and one that only
imports `deviceGeometry` from the same file does not. A template id (`card:${id}`) is recorded as a PREFIX: the
part after it comes from the beat's props, which only the render can see.

A register whose source cannot be found (a film's workshop shot this run was not told about) answers None —
"unknown", never "none": the caller says it could not check, rather than reporting a missing anchor that may exist.
"""
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.realpath(os.path.join(_HERE, "..", "remotion", "src"))

# `data-carry="id"`, `data-carry={'id'}`, and a template `data-carry={`card:${...}`}` (a prefix). `data-carry-part`
# and `data-carry-radius` are other attributes and do not match: the `=` must follow `carry` directly.
_ATTR = re.compile(r"""data-carry=(?:"([^"{}]+)"|\{\s*(['"])([^'"]+)\2\s*\}|\{\s*`([^`$]*)\$\{[^`]*`\s*\})""")
_COMPONENT = re.compile(r"""<CarryAnchor\b[^>]*?\bid=(?:"([^"]+)"|\{\s*(['"])([^'"]+)\2\s*\})""", re.S)
_EXPORT = re.compile(r"^export\s+const\s+([A-Za-z_$][\w$]*)", re.M)
_IMPORT = re.compile(r"""^\s*import\s*\{([^}]*)\}\s*from\s*['"](\.[^'"]+)['"]""", re.M)
ID_RE = re.compile(r"^[a-z][a-z0-9_-]*(:[A-Za-z0-9_-]+)?$")


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def _resolve(spec, base):
    for ext in (".tsx", ".ts", "/index.tsx", "/index.ts"):
        cand = os.path.realpath(os.path.join(base, spec + ext))
        if os.path.isfile(cand):
            return cand
    return None


def _literal_anchors(src):
    """[(position, id, is_prefix)] for every anchor written in this text."""
    out = []
    for m in _ATTR.finditer(src):
        if m.group(1):
            out.append((m.start(), m.group(1), False))
        elif m.group(3):
            out.append((m.start(), m.group(3), False))
        elif m.group(4) is not None and m.group(4):
            out.append((m.start(), m.group(4), True))
    for m in _COMPONENT.finditer(src):
        out.append((m.start(), m.group(1) or m.group(3), False))
    return out


_MODULE_CACHE = {}


def _component_anchors(path):
    """{exported component name: (ids, prefixes)} for a runtime module — an anchor belongs to the export it sits in."""
    if path in _MODULE_CACHE:
        return _MODULE_CACHE[path]
    src = _read(path) or ""
    exports = [(m.start(), m.group(1)) for m in _EXPORT.finditer(src)]
    out = {}
    for pos, aid, pre in _literal_anchors(src):
        owner = None
        for epos, name in exports:
            if epos <= pos:
                owner = name
        if owner is None:
            continue
        ids, prefixes = out.setdefault(owner, (set(), set()))
        (prefixes if pre else ids).add(aid)
    _MODULE_CACHE[path] = out
    return out


def source_of(shot, out_dir=None):
    """The register's source path: the library's shots and stages, then this film's workshop."""
    cands = [os.path.join(SRC, "shots", shot + ".tsx"), os.path.join(SRC, "stage", shot + ".tsx")]
    if out_dir:
        cands.append(os.path.join(out_dir, "workshop", "shots", shot + ".tsx"))
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def anchors_of(shot, out_dir=None):
    """{"ids": set, "prefixes": set} this register draws, or None when its source is not found."""
    path = source_of(shot, out_dir) if shot else None
    if not path:
        return None
    src = _read(path) or ""
    ids, prefixes = set(), set()
    for _pos, aid, pre in _literal_anchors(src):
        (prefixes if pre else ids).add(aid)
    base = os.path.dirname(path)
    for names, spec in _IMPORT.findall(src):
        dep = _resolve(spec, base)
        if not dep:
            continue
        comps = _component_anchors(dep)
        for n in names.split(","):
            n = n.strip().split(" as ")[-1].strip()
            if n in comps and re.search(r"<%s\b" % re.escape(n), src):
                ids |= comps[n][0]
                prefixes |= comps[n][1]
    return {"ids": ids, "prefixes": prefixes}


def has_anchor(shot, aid, out_dir=None):
    """True / False — or None when the register's source could not be read (unknown, not absent)."""
    a = anchors_of(shot, out_dir)
    if a is None:
        return None
    if aid in a["ids"]:
        return True
    return any(aid.startswith(p) and len(aid) > len(p) for p in a["prefixes"])


# When two registers share several anchors, the container carries the one that is most the SAME THING: a whole
# device before its screen (the screen alone is for carrying what is on it into a different frame), a window, a
# stage's hero, a figure. Anything else follows alphabetically.
PREFERENCE = ("device", "window", "hero", "figure", "screen")


def shared(shot_a, shot_b, out_dir=None):
    """The literal anchor ids two registers both draw, most-preferred first, for a container between them."""
    a, b = anchors_of(shot_a, out_dir), anchors_of(shot_b, out_dir)
    if not a or not b:
        return []
    common = a["ids"] & b["ids"]
    return [x for x in PREFERENCE if x in common] + sorted(common - set(PREFERENCE))


def all_registers():
    names = []
    for sub in ("shots", "stage"):
        d = os.path.join(SRC, sub)
        names += sorted(f[:-4] for f in os.listdir(d) if f.endswith(".tsx") and f != "index.tsx")
    return names


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    names = argv or all_registers()
    for n in names:
        a = anchors_of(n)
        if a is None:
            print("%-22s (no source found)" % n)
        elif a["ids"] or a["prefixes"] or argv:
            print("%-22s %s" % (n, ", ".join(sorted(a["ids"]) + ["%s<id>" % p for p in sorted(a["prefixes"])]) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
