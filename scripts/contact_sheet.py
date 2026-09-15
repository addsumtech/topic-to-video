#!/usr/bin/env python3
"""One CONTACT SHEET of every beat, so a reviewer can read the whole film in a single look.

  python3 scripts/contact_sheet.py <out_dir> [--cols N] [--cell W]

WHY. The shot-critic used to open 37 keyframes one at a time. Most of a review's cost is those images,
and most of them are fine — the reviewer is triaging. A contact sheet is how that has always been done on
film: look at the strip, mark the frames worth enlarging, then pull those. Each cell carries its beat
number and register id, so a finding can be named without opening anything.

The sheet is for TRIAGE, not for verdicts. A 320px cell shows composition, palette, gross overflow and
whether two beats are the same picture; it cannot show whether a caption collides with a label or whether
a figure is legible. Those need the full frame — which is the point: pull the three or four that look
wrong instead of all thirty-seven.
"""
import json
import os
import sys


def build(out_dir, cols=5, cell_w=320, out_path=None):
    from PIL import Image, ImageDraw

    kdir = os.path.join(out_dir, "_keyframes")
    frames = sorted(f for f in os.listdir(kdir) if f.startswith("scene_") and f.endswith(".png"))
    if not frames:
        raise SystemExit("[contact_sheet] no keyframes in %s" % kdir)

    # BY POSITION, NOT BY THE `index` FIELD. `render_remotion` names keyframes `scene_%02d % (i + 1)` from
    # the scene's POSITION, while this read `index + 1` — and boards in this repo use both a 0-based and a
    # 1-based `index`. On a 1-based board every label shifted by one: cell 1 showed a register name of
    # nothing and cell 2 labelled the SplitFlap board as TermSpace, for all eight beats. An independent
    # reviewer caught it by cropping the label strip and cross-reading the storyboard, and noted the cost
    # exactly: a reviewer who trusted this sheet would attribute every frame to the wrong register — the
    # one artifact a review is built on, quietly lying about which register drew what.
    shots = {}
    try:
        board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
        for pos, s in enumerate(board.get("slides", []), start=1):
            shots[pos] = str(s.get("shot") or "")
    except (OSError, ValueError):
        pass

    # ADAPT THE GRID to the beat count. A fixed 5 columns turned a 120-beat film into a 4902px-tall strip,
    # which any reader downsamples until the cells are unreadable — the opposite of a triage aid. Widen the
    # grid and shrink the cell so the sheet stays roughly page-shaped whatever the film's length.
    import math
    if len(frames) > cols * 8:
        cols = max(cols, int(math.ceil(math.sqrt(len(frames) * 1.4))))
    probe = Image.open(os.path.join(kdir, frames[0]))
    cell_h = max(1, round(cell_w * probe.size[1] / probe.size[0]))
    rows_est = (len(frames) + cols - 1) // cols
    if rows_est * (cell_h + 24) > 2600:                     # keep the sheet inside a readable envelope
        scale = 2600.0 / (rows_est * (cell_h + 24))
        cell_w = max(140, int(cell_w * scale))
        cell_h = max(1, round(cell_w * probe.size[1] / probe.size[0]))
    label_h = 18
    rows = (len(frames) + cols - 1) // cols
    pad = 6
    sheet = Image.new("RGB", (cols * (cell_w + pad) + pad, rows * (cell_h + label_h + pad) + pad), (24, 24, 28))
    d = ImageDraw.Draw(sheet)

    for i, name in enumerate(frames):
        beat = int(name[len("scene_"):-len(".png")])
        im = Image.open(os.path.join(kdir, name)).convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
        x = pad + (i % cols) * (cell_w + pad)
        y = pad + (i // cols) * (cell_h + label_h + pad)
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline=(70, 70, 78))
        d.text((x + 3, y + cell_h + 3), "%d  %s" % (beat, shots.get(beat, "")), fill=(200, 200, 208))

    out_path = out_path or os.path.join(out_dir, "_contact_sheet.png")
    sheet.save(out_path)
    return out_path, len(frames), sheet.size


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    out_dir = os.path.abspath(argv[0])
    cols = int(argv[argv.index("--cols") + 1]) if "--cols" in argv else 5
    cell = int(argv[argv.index("--cell") + 1]) if "--cell" in argv else 320
    path, n, size = build(out_dir, cols=cols, cell_w=cell)
    print("[contact_sheet] %d beat(s) -> %s (%dx%d)" % (n, path, size[0], size[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
