#!/usr/bin/env python3
"""The axis gallery — every drawing axis value on one register, so a spec author SEES what each value does.

    python3 scripts/style_axis_gallery.py [--out references/style-axes.jpg] [--shot ClayStack]

One still per case: the register unstyled, then each axis value alone (everything else as drawn). Motion axes
(stepping, easing) and provenance (`surface.source`) are not stills and are not shown. references/style-engine.md
points at the sheet; regenerate it after an axis or the engine changes.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOT_A_STILL = {"stepping", "easing", "source"}
# a value shown alone needs its companions to be visible at all (a weight needs a line to weigh, steps need cel)
COMPANION = {"line.weight": {"line": {"outline": "all"}}, "line.variance": {"line": {"outline": "all", "weight": 5}},
             "line.wobble": {"line": {"outline": "all"}}, "line.boil_hz": {"line": {"outline": "all", "wobble": 2}},
             "line.join": {"line": {"outline": "all", "weight": 6}}, "line.color": {"line": {"outline": "all"}},
             "fill.steps": {"fill": {"mode": "cel"}}, "shadow.offset": {"shadow": {"mode": "hard-offset"}},
             "surface.strength": {"surface": {"kind": "paper"}}, "type.display_outline": {}}
NUMERIC_SAMPLES = {"line.weight": [2, 6], "line.variance": [0.8], "line.wobble": [3], "line.boil_hz": [8],
                   "fill.steps": [2, 4], "shadow.offset": [12], "form.corner": [0, 3], "form.simplify": [1],
                   "surface.strength": [1.0], "motion.squash": []}


def cases():
    """[{"axis", "value", "spec"}] — one per enum value (not the default) and per sampled number."""
    import style_spec as ss
    out = []
    for group, params in ss.AXES.items():
        for name, p in params.items():
            if name in NOT_A_STILL:
                continue
            axis = "%s.%s" % (group, name)
            values = [v for v in p.get("values", []) if v != p["default"]] if p["kind"] == "enum" else \
                [True] if p["kind"] == "bool" else NUMERIC_SAMPLES.get(axis, [])
            for v in values:
                spec = {"name": "%s=%s" % (axis, v), "refs": [], "refs_missing": "the axis gallery"}
                for g, kv in COMPANION.get(axis, {}).items():
                    spec[g] = dict(kv)
                spec.setdefault(group, {})[name] = v
                out.append({"axis": axis, "value": v, "spec": spec})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "references", "style-axes.jpg"))
    ap.add_argument("--shot", default="ClayStack")
    ap.add_argument("--frame", type=int, default=144)      # ClayStack settled; a crop of the frame's middle
    a = ap.parse_args(argv)
    import tempfile
    from PIL import Image, ImageDraw
    import fidelity as fid
    work = tempfile.mkdtemp(prefix="axis_gallery_")
    cs = [{"axis": "(unstyled)", "value": "", "spec": None}] + cases()
    jobs = []
    for i, c in enumerate(cs):
        props = {"style": c["spec"]} if c["spec"] else {}
        jobs.append({"tag": str(i), "id": a.shot, "props": props, "frame": a.frame, "png": os.path.join(work, "%02d.png" % i)})
    fid._render_all(None, jobs, parts=False)
    # the middle of the frame, near its own size: a 2.5 px outline shrunk to a fifth is half a pixel, and the gallery
    # first showed `line.outline: all` as no change at all
    tw, th, cols = 620, 349, 3
    crop = (560, 200, 1360, 650)
    rows = (len(cs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + 12) + 12, rows * (th + 40) + 12), (246, 244, 239))
    d = ImageDraw.Draw(sheet)
    for i, c in enumerate(cs):
        x, y = 12 + (i % cols) * (tw + 12), 12 + (i // cols) * (th + 40)
        sheet.paste(Image.open(jobs[i]["png"]).convert("RGB").crop(crop).resize((tw, th)), (x, y + 28))
        d.text((x, y + 4), "%s %s" % (c["axis"], c["value"]), fill=(20, 20, 20), font=fid._font(18))
    sheet.save(a.out, quality=85, optimize=True)        # a JPEG: the sheet ships inside the skill
    print("axis gallery: %d cases on %s -> %s" % (len(cs) - 1, a.shot, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
