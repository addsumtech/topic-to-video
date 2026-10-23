#!/usr/bin/env python3
"""THE COVER — a 3:4 still for a portrait film, the frame a Xiaohongshu feed shows before anyone presses play.

    python3 scripts/cover.py <out_dir>        # writes <out_dir>/out.cover.png (1080x1440)

WHY A COVER OF ITS OWN. Xiaohongshu shows a video note as a 3:4 card (1080x1440; references/craft-research.md §2).
A centre crop of the 9:16 film loses 240 px top and bottom — exactly where the title stands — so the feed showed a
card with its headline cut off. The cover is cut from the film's own frame instead, by a window anchored on the
title: the title, the picture under it, no caption (a still is read, not heard).

WHICH FRAME. The first beat's held state — a stage beat's last held frame (scripts/stage_frames.py), a register's
settled frame — or the beat `meta.cover = {"beat": N}` names (1-based). Only a portrait film has one; anything else
is refused with the reason.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

COVER_W, COVER_H = 1080, 1440


def _title_top(props, W, H):
    """Where the beat's title starts on the frame: the stage's own title line, or a register's TITLE_Y inside its
    platform-safe frame (runtime/safeZone.ts) — both read from the runtime, never restated."""
    import re
    import text_safe_qa as _tq
    lay = open(os.path.join(_HERE, "..", "remotion", "src", "runtime", "layout.ts"), encoding="utf-8").read()
    title_y = float(re.search(r"export const TITLE_Y\s*=\s*(\d+)", lay).group(1))
    if not props.get("safe"):
        return title_y
    prof = _tq.safe_profile()
    return min(max(title_y, prof["top"] * H), prof["y0"] * H + prof["k"] * title_y)


def cover(out_dir, beat=None):
    """The written cover's path. Raises SystemExit with the reason when this film has no cover to make."""
    import render_remotion as _rr
    import remotion_segments as _rs
    import stage_frames as _sf
    from _caption_band import aspect_table
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = board.get("meta") or {}
    payload = _sf.film_payload(out_dir, board)
    W, H = aspect_table().get(str(payload.get("aspect")), (1920, 1080))
    if H <= W:
        raise SystemExit("[cover] %s is %dx%d — a cover is cut for a portrait film only" % (out_dir, W, H))
    scenes = payload["scenes"]
    k = (beat or (meta.get("cover") or {}).get("beat") or 1) - 1
    if not 0 <= k < len(scenes):
        raise SystemExit("[cover] meta.cover.beat %d is not a beat of this film (1-%d)" % (k + 1, len(scenes)))
    ranges, _total = _rs.timeline(scenes, _rs.seam_frames())
    held = (_sf.sample_frames(scenes, _rs.seam_frames(), 30).get(k) or {}).get("held")
    frame = held[-1] if held else ranges[k][0] + int(round(_rr.frame_at_t(max(1, int(scenes[k]["durF"])), _rr.SETTLED_T)))
    png = os.path.join(out_dir, ".cover_frame.png")
    with _sf.Stills(out_dir, payload) as stills:
        rc, out = stills.still(frame, payload, png)
    if rc != 0 or not os.path.exists(png):
        raise SystemExit("[cover] the cover frame %d did not render: %s" % (frame, out[-300:]))
    from PIL import Image
    im = Image.open(png).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H))
    ch = round(W * COVER_H / COVER_W)
    y0 = int(max(0, min(H - ch, round(_title_top(payload, W, H) - 0.04 * H))))
    dest = os.path.join(out_dir, "out.cover.png")
    im.crop((0, y0, W, y0 + ch)).resize((COVER_W, COVER_H)).save(dest)
    os.remove(png)
    return dest


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    print("[cover] %s" % cover(os.path.abspath(argv[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
