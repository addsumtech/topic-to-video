#!/usr/bin/env python3
"""TYPESET A FILM'S EQUATIONS BEFORE ANYTHING RENDERS THEM.

    python3 scripts/mathtex.py <out_dir>            # every `tex` in the storyboard's shot_props -> <out_dir>/_math/
    python3 scripts/mathtex.py --check '<tex>'      # typeset one, print what it drew, write nothing

A register that draws maths (EquationMorph, and anything built on runtime/mathMorph.tsx) never typesets at render
time: the bundle reads glyph outlines that scripts/tex_glyphs.mjs (MathJax 3.2.2) wrote once, so a render is
deterministic and offline. The library's own equations ship inside the bundle (remotion/src/runtime/mathLibrary.json);
a FILM's are written here, into `<out_dir>/_math/<key>.json`, which every film-scoped render serves as its public dir.
`render_remotion.py` calls `ensure()` before its first render (the sync census included), so an author never has to
remember this step — and a TeX error stops the render here, with MathJax's own message, before a frame is drawn.

WHAT IS COLLECTED. Every string under a key named `tex`, at any depth of a scene's `shot_props` (EquationMorph's
`steps[].tex`, a plot's `tex` label, a film's own workshop shot that follows the convention). Display mode unless the
object carrying it says `"display": false`.
"""
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(_HERE, "tex_glyphs.mjs")
MATH_DIR = "_math"


def collect(scenes):
    """[(tex, display)] for every `tex` string under every scene's shot_props, first occurrence order, no repeats."""
    seen, out = set(), []

    def walk(v, display=True):
        if isinstance(v, dict):
            disp = v.get("display", display) is not False
            for k, x in v.items():
                if k == "tex":
                    if not isinstance(x, str):
                        raise ValueError("a `tex` must be a string of TeX, got %r" % (x,))
                    key = (x.strip(), disp)
                    if key[0] and key not in seen:
                        seen.add(key)
                        out.append(key)
                else:
                    walk(x, disp)
        elif isinstance(v, list):
            for x in v:
                walk(x, display)

    for s in scenes or []:
        if isinstance(s, dict):
            walk(s.get("shot_props") or {})
    return out


def typeset(items, out_dir=None, check=False):
    """Run the typesetter. Returns its report dict; raises RuntimeError naming every TeX that failed."""
    if not items:
        return {"written": [], "cached": [], "errors": []}
    cmd = ["node", "--no-warnings", TOOL]
    cmd += ["--check", items[0][0]] if check else ["--out", os.path.join(out_dir, MATH_DIR), "--stdin"]
    payload = json.dumps({"items": [{"tex": t, "display": d} for t, d in items]}, ensure_ascii=False)
    p = subprocess.run(cmd, input=payload, capture_output=True, text=True)
    try:
        rep = json.loads((p.stdout or "").strip().splitlines()[-1])
    except (IndexError, ValueError):
        raise RuntimeError("tex_glyphs.mjs failed before reporting (exit %d): %s" % (p.returncode, (p.stderr or "")[-800:]))
    if rep.get("errors"):
        lines = ["  %s\n    -> %s" % (e.get("tex"), e.get("error")) for e in rep["errors"]]
        raise RuntimeError("TeX that cannot be typeset (MathJax's message under each):\n" + "\n".join(lines))
    if p.returncode != 0:
        raise RuntimeError("tex_glyphs.mjs exited %d: %s" % (p.returncode, (p.stderr or "")[-800:]))
    return rep


def ensure(out_dir, data=None):
    """Typeset every equation the storyboard names into <out_dir>/_math. Returns the report (written / cached)."""
    if data is None:
        with open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8") as fh:
            data = json.load(fh)
    items = collect(data.get("slides") or data.get("scenes") or [])
    return typeset(items, out_dir=out_dir)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 2
    try:
        if argv[0] == "--check":
            rep = typeset([(argv[1], "--inline" not in argv)], check=True)
        else:
            rep = ensure(argv[0])
    except (RuntimeError, ValueError) as e:
        print("[mathtex] %s" % e)
        return 2
    print("[mathtex] %d typeset, %d already current" % (len(rep.get("written", [])), len(rep.get("cached", []))))
    if argv[0] == "--check":
        print(json.dumps(rep.get("written"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
