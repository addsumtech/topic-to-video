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
import re
import sys

# ONE KEYFRAME PER BEAT: `scene_NN.png`, and nothing else in `_keyframes/`. The remotion tier writes exactly that
# (its motion frames live in `_keyframes/motion/`), but the HTML tier's keyframe_qa writes each scene's montage
# `scene_NN.png` BESIDE its progress frames `scene_NN_p050.png` and its `scene_NN_resting.png` — and the old
# `startswith("scene_")` took all of them, then died parsing "01_p000" as a beat number. Same pattern as the
# staleness check in critic_ledger.py, so the sheet and the check read the same files.
KEYFRAME = re.compile(r"^scene_(\d+)\.png$")


def labels(out_dir):
    """{keyframe number: the cell's label}. A remotion film labels each beat with its register; an HTML film with
    its page's design route (validate.html_design_routes: BUILT / BESPOKE / AS-IS / EXEMPT) and scene type, since
    an HTML beat has no `shot` and an empty label tells the reviewer nothing."""
    try:
        board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    slides = [s for s in board.get("slides") or [] if isinstance(s, dict)]
    meta = board.get("meta") if isinstance(board.get("meta"), dict) else {}
    if str(meta.get("renderer", "")).lower() in ("remotion", "remotion-bespoke"):
        # BY POSITION, NOT BY THE `index` FIELD. `render_remotion` names keyframes `scene_%02d % (i + 1)` from
        # the scene's POSITION, while this read `index + 1` — and boards in this repo use both a 0-based and a
        # 1-based `index`. On a 1-based board every label shifted by one: cell 1 showed a register name of
        # nothing and cell 2 labelled the SplitFlap board as TermSpace, for all eight beats. An independent
        # reviewer caught it by cropping the label strip and cross-reading the storyboard, and noted the cost
        # exactly: a reviewer who trusted this sheet would attribute every frame to the wrong register — the
        # one artifact a review is built on, quietly lying about which register drew what.
        return {pos: str(s.get("shot") or "") for pos, s in enumerate(slides, start=1)}
    # THE HTML TIER NAMES BY THE `index` FIELD: keyframe_qa writes `scene_%02d % s["index"]` — so the label is keyed
    # the same way, or a 0-based board would shift every label by one, the defect above in its other direction.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import validate as _v
        routes = {num: (route, rel) for num, route, _w, rel in _v.html_design_routes(meta, slides, out_dir)}
    except Exception:                                          # noqa: BLE001 — a label is never worth a crash
        routes = {}
    out = {}
    for pos, s in enumerate(slides, start=1):
        num = s.get("index", pos)
        route, rel = routes.get(num, (None, None))
        kind = str(s.get("type") or "slide")
        out[num] = "%s%s" % ((route.upper() + " · ") if route else "",
                             os.path.basename(rel) if rel else kind)
    return out


def _tiles(size, out_dir):
    """How many frames side by side one keyframe image holds: 1 for a frame, N for an N-tile filmstrip. Read from the
    image's aspect against the film's own canvas (meta.aspect / width / height; 16:9 when unset), so a 9:16 strip is
    counted right and a 9:16 single frame is not mistaken for a strip."""
    try:
        meta = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8")).get("meta") or {}
    except (OSError, ValueError, AttributeError):
        meta = {}
    if meta.get("aspect") == "9:16":
        frame = 9 / 16.0
    elif isinstance(meta.get("width"), (int, float)) and isinstance(meta.get("height"), (int, float)) \
            and meta["width"] > 0 and meta["height"] > 0:
        frame = meta["width"] / float(meta["height"])
    else:
        frame = 16 / 9.0
    w, h = size
    return max(1, int(round((w / float(max(1, h))) / frame)))


def build(out_dir, cols=5, cell_w=320, out_path=None):
    from PIL import Image, ImageDraw

    kdir = os.path.join(out_dir, "_keyframes")
    frames = sorted((f for f in os.listdir(kdir) if KEYFRAME.match(f)), key=lambda f: int(KEYFRAME.match(f).group(1)))
    if not frames:
        raise SystemExit("[contact_sheet] no keyframes (scene_NN.png) in %s" % kdir)

    shots = labels(out_dir)

    import math
    probe = Image.open(os.path.join(kdir, frames[0]))
    tiles = _tiles(probe.size, out_dir)
    if tiles > 1:
        # A FILMSTRIP PER BEAT (the HTML tier: keyframe_qa's `scene_NN.png` is the page swept across its cue
        # timeline, left = the frame at t=0, right = the frame that ships). Squeezed into a single-frame cell each
        # of its five tiles was 64px wide — a sheet that showed nothing. Each tile gets a single cell's width, so a
        # strip is one wide cell; a long film puts strips side by side, shrinking a tile to no less than 160px,
        # before the height envelope below is allowed to squeeze it.
        tile_w, cols = cell_w, 1
        cell_w = tile_w * tiles
        cell_h = max(1, round(cell_w * probe.size[1] / probe.size[0]))
        while cols < 4 and ((len(frames) + cols - 1) // cols) * (cell_h + 24) > 2600:
            cols += 1
            cell_w = max(tiles * 160, (tile_w * tiles) // cols)
            cell_h = max(1, round(cell_w * probe.size[1] / probe.size[0]))
    else:
        # ADAPT THE GRID to the beat count. A fixed 5 columns turned a 120-beat film into a 4902px-tall strip,
        # which any reader downsamples until the cells are unreadable — the opposite of a triage aid. Widen the
        # grid and shrink the cell so the sheet stays roughly page-shaped whatever the film's length.
        if len(frames) > cols * 8:
            cols = max(cols, int(math.ceil(math.sqrt(len(frames) * 1.4))))
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
        beat = int(KEYFRAME.match(name).group(1))
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
