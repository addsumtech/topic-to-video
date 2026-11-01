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
    # ABSOLUTE, because the still renders from the renderer's own directory: given a relative out_dir it wrote the frame
    # under remotion/, this looked for it here, and the film shipped with no cover (tests/test_cover_path.py).
    out_dir = os.path.abspath(out_dir)
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
    dest = os.path.join(out_dir, "out.cover.png")
    card(im, _title_top(payload, W, H) - 0.04 * H, _content_bottom(payload, W, H)).save(dest)
    os.remove(png)
    return dest


def _content_bottom(props, W, H):
    """Where the picture ends: above the caption band (captions are off in the still, the band is empty) — inside the
    platform-safe frame when the film has one."""
    from _caption_band import caption_band_px
    import text_safe_qa as _tq
    bottom = H - caption_band_px(W, H)
    if not props.get("safe"):
        return bottom
    prof = _tq.safe_profile()
    return prof["y0"] * H + prof["k"] * bottom


def card(im, top, bottom):
    """The 3:4 card cut from a portrait frame `im`, keeping rows top..bottom (the title down to the end of the picture):
      · a frame taller than 3:4 whose picture fits a 3:4 window: the window from `top` (shifted up when the frame ends);
      · a picture taller than that window: the picture whole, scaled to the card's height, its sides filled with the
        frame's own edge colour — never a cut through the picture;
      · a frame wider than 3:4 (4:5): its centre, cut at the sides.
    A crop past the frame's edge padded the card black (a 4:5 film's card had a 90 px black strip)."""
    from PIL import Image
    W, H = im.size
    if W * COVER_H > H * COVER_W:                       # wider than 3:4 — cut the sides
        cw = int(round(H * COVER_W / COVER_H))
        x0 = (W - cw) // 2
        return im.crop((x0, 0, x0 + cw, H)).resize((COVER_W, COVER_H), Image.LANCZOS)
    ch = int(round(W * COVER_H / COVER_W))
    top = int(max(0, min(H, round(top))))
    bottom = int(max(top + 1, min(H, round(bottom))))
    if bottom - top <= ch:
        y0 = max(0, min(H - ch, top))
        return im.crop((0, y0, W, y0 + ch)).resize((COVER_W, COVER_H), Image.LANCZOS)
    pic = im.crop((0, top, W, bottom))
    scale = COVER_H / pic.height
    pic = pic.resize((max(1, int(round(W * scale))), COVER_H), Image.LANCZOS)
    edge = im.crop((0, top, 4, bottom)).resize((1, 1), Image.BOX).getpixel((0, 0))
    out = Image.new("RGB", (COVER_W, COVER_H), edge)
    out.paste(pic, ((COVER_W - pic.width) // 2, 0))
    return out


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    print("[cover] %s" % cover(os.path.abspath(argv[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
