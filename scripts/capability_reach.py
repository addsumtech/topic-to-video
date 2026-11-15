#!/usr/bin/env python3
"""capability_reach — which of the skill's built capabilities a film USES, and which it leaves unused without a reason.

    python3 scripts/capability_reach.py <film_dir> [--strict]

WHY (the user, 2026-11-14): "做了这么多优化，都展示出来呀 ... 你优化完了得学会用呀，要不这是在干嘛". The skill gained
a lit stage, materials, optics, staging, composition variety, links, live acts — and a rebuilt film used almost none of
them: its improvements stayed on the shelf. This lists, per film, every capability FAMILY with used / unused, and
names each unused one that has no stated reason. A reason lives in the board's `meta.capability_waivers` (or a promo
table's `waivers`): `{family: "why this film does not use it"}`.

A narrated film (storyboard.json) is read with the source of every shot it uses (the film's workshop/shots first,
then the library); a promo film (promo.json) is read from its table. Advisory: exit 0, or 1 with --strict when an
unused family has no reason.
"""
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.join(_HERE, "..", "remotion", "src", "shots")

# narrated films: family -> (what it is, how it is seen in the shots' source or the board)
NARRATED = {
    "light": "a lit ground (LitStage / LitGround / a lit world), not a flat fill",
    "material": "parts drawn as materials (runtime/material, the craft kit's surface/softShadow, specular lighting, or a "
                "film kit marked `@material`)",
    "optics": "one anchored optic on a beat that has a light (slide.optic: bloom / halation / sweep / aberration / leak)",
    "camera": "a motivated camera move (slide.camera)",
    "seams": "a marked seam where beats relate (transition_in other than a cut or a fade)",
    "time": "time grammar on an impact or a climax (slide.time: hits / freeze / sakuga)",
}
# a page film (the HTML tier): its own vocabulary — reading it with the Remotion families scored a finished, cue-timed,
# transition-marked film 0 of 6 (the QR film, 2026-11-14)
PAGES = {
    "seams": "marked seams where beats relate (slide.transition in / out / dip, a chosen transition_style)",
    "cues": "reveals timed to the spoken word (data-cue in the pages)",
    "light": "a lit or textured ground (a style with grain, a lit page ground, documentary or atmosphere imagery)",
    "motion": "motion that serves the line (slide.motion / intensity, an animated page)",
    "emphasis": "the point the voice names, emphasised on the page (callouts, data-cue targets, highlights)",
}
PROMO = {
    "staging": "the product as objects in a world (`object` shots)",
    "breadth": "a `wall` of components",
    "links": "a `links` line from where something is to what the product says about it",
    "acts": "the claim acted on the card (count / type / write / ring / focus)",
    "composition": "feature shots composed differently (3+ label places, or no label)",
    "outro": "a staged outro (`world`) that gathers the film's parts",
}


def _shot_source(film_dir, shot, seen=None):
    """A shot's source and the sources it imports relatively (its kit), the film's workshop first."""
    seen = set() if seen is None else seen
    roots = [os.path.join(film_dir, "workshop", "shots"), _LIB]
    start = None
    for r in roots:
        for ext in (".tsx", ".ts"):
            p = os.path.join(r, shot + ext)
            if os.path.isfile(p):
                start = p
                break
        if start:
            break
    out, todo = [], [start] if start else []
    while todo:
        p = todo.pop()
        if not p or p in seen or not os.path.isfile(p):
            continue
        seen.add(p)
        src = open(p, encoding="utf-8").read()
        out.append(src)
        for m in re.finditer(r"from\s+'(\./[^']+)'", src):
            base = os.path.join(os.path.dirname(p), m.group(1))
            for ext in ("", ".ts", ".tsx"):
                if os.path.isfile(base + ext):
                    todo.append(base + ext)
                    break
    return "\n".join(out)


def narrated(film_dir, board):
    slides = board.get("slides") or []
    meta = board.get("meta") or {}
    shots = sorted({s.get("shot") for s in slides if isinstance(s, dict) and s.get("shot")})
    src = "\n".join(_shot_source(film_dir, sh) for sh in shots)
    # a STRING design_dna is a preset NAME (Film's coerceDna expands it); it carries no material/optics keys this can
    # read, and .get on it crashed every film that named a preset (AttributeError — render_remotion printed and moved on)
    dna = meta.get("design_dna") if isinstance(meta.get("design_dna"), dict) else {}
    used = {
        "light": bool(re.search(r"\bLitStage\b|\bLitGround\b", src)) or bool((meta.get("style") or {}).get("surface")),
        "material": bool(re.search(r"@runtime/material|\bsurface\(|\bsoftShadow\(|feSpecularLighting|@material\b", src))
                    or bool(dna.get("material")),
        "optics": any(s.get("optic") for s in slides if isinstance(s, dict)) or dna.get("optics") == "auto",
        "camera": any(isinstance(s.get("camera"), dict) and s["camera"].get("move") not in (None, "hold")
                      for s in slides if isinstance(s, dict)),
        "seams": any(isinstance(s.get("transition_in"), dict) and s["transition_in"].get("type") not in (None, "cut", "fade")
                     for s in slides if isinstance(s, dict)),
        "time": any(s.get("time") for s in slides if isinstance(s, dict)),
    }
    return NARRATED, used, meta.get("capability_waivers") or {}


def pages(film_dir, board):
    import glob
    slides = [s for s in board.get("slides") or [] if isinstance(s, dict)]
    meta = board.get("meta") or {}
    html = ""
    for p in sorted(glob.glob(os.path.join(film_dir, "pages", "*.html"))):
        try:
            html += open(p, encoding="utf-8").read()
        except OSError:
            pass
    theme = os.path.join(film_dir, "theme.css")
    theme_src = open(theme, encoding="utf-8").read() if os.path.isfile(theme) else ""
    used = {
        "seams": any(s.get("transition") in ("in", "out", "dip") for s in slides) or bool(meta.get("transition_style")),
        "cues": "data-cue" in html,
        "light": bool(re.search(r"grain|radial-gradient|LitGround|feSpecularLighting", html + theme_src))
                 or any((s.get("media") or {}).get("treatment") in ("documentary", "atmosphere") for s in slides),
        "motion": any(s.get("motion") or s.get("intensity") for s in slides) or bool(meta.get("intensity"))
                  or bool(re.search(r"@keyframes|animation|transition:", html)),
        "emphasis": any(s.get("callouts") for s in slides) or "data-cue-index" in html or bool(re.search(r"highlight|mark>", html)),
    }
    return PAGES, used, meta.get("capability_waivers") or {}


def promo(spec):
    shots = [s for s in spec.get("shots") or [] if isinstance(s, dict)]
    acts = {a.get("kind") for s in shots for it in s.get("items") or [] for a in (it.get("acts") or []) if isinstance(a, dict)}
    # a PAGE shot's own acts are the claim acted on the product too (they were missed: a film that read, marked and
    # scanned its pages was told "acts unused")
    acts |= {a.get("kind") for s in shots if s.get("kind") == "page" for a in (s.get("layers") or s.get("acts") or []) if isinstance(a, dict)}
    places = [s["label"].get("side", "left") for s in shots if s.get("kind") == "object" and isinstance(s.get("label"), dict)]
    nolabel = any(s.get("kind") == "object" and not s.get("label") for s in shots)
    used = {
        "staging": any(s.get("kind") == "object" for s in shots),
        "breadth": any(s.get("kind") == "wall" for s in shots),
        "links": any(s.get("links") for s in shots),
        "acts": bool(acts & {"count", "type", "write", "ring", "focus", "read", "mark", "scan"}),
        "composition": len(places) < 4 or len(set(places)) >= 3 or (nolabel and len(set(places)) >= 2),
        # an outro that lands in a world, or over the film's own last picture (`backdrop`), ends on the product
        "outro": any(s.get("kind") == "outro" and (s.get("world") or isinstance(s.get("backdrop"), int)) for s in shots),
    }
    return PROMO, used, spec.get("waivers") or {}


def reach(film_dir):
    """(families, used, waivers) for the film in `film_dir`, or None when it has neither table nor board."""
    pp, bp = os.path.join(film_dir, "promo.json"), os.path.join(film_dir, "storyboard.json")
    if os.path.isfile(pp):
        return promo(json.load(open(pp, encoding="utf-8")))
    if os.path.isfile(bp):
        board = json.load(open(bp, encoding="utf-8"))
        if (board.get("meta") or {}).get("renderer") not in ("remotion",):
            return pages(film_dir, board)
        return narrated(film_dir, board)
    return None


def unused_lines(fams, used, waivers):
    return ["%s unused and no reason given: %s — use it, or say why in waivers {\"%s\": \"...\"}" % (k, fams[k], k)
            for k in fams if not used.get(k) and not waivers.get(k)]


def main(argv):
    sys.path.insert(0, _HERE)
    from _common import refuse_unknown
    refuse_unknown(argv, switches=("strict",), usage="usage: capability_reach.py <film_dir> [--strict]")
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__.strip())
        return 2
    r = reach(os.path.abspath(args[0]))
    if r is None:
        print("[capability_reach] %s has no promo.json or storyboard.json" % args[0])
        return 2
    fams, used, waivers = r
    for k, why in fams.items():
        mark = "used" if used.get(k) else ("waived: %s" % waivers[k] if waivers.get(k) else "UNUSED")
        print("  %-12s %-8s %s" % (k, mark if len(mark) < 9 else "", why if len(mark) < 9 else mark))
    miss = unused_lines(fams, used, waivers)
    print("[capability_reach] %d of %d families used%s" % (sum(1 for k in fams if used.get(k)), len(fams),
                                                         "" if not miss else " — %d unused without a reason" % len(miss)))
    return 1 if miss and "--strict" in argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
