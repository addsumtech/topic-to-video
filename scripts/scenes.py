"""Deterministic animated scene renderers -> per-frame PNG sequences (no slides).
Each renderer is a PURE function of the frame index; no randomness, no wall-clock.
Frames are namespaced by scene index because the full render shares one workdir."""
import os
from PIL import Image, ImageDraw, ImageFont
import render  # reuse the CJK-aware font resolver

BG = (13, 17, 23)        # near-black, matches the caption aesthetic
FG = (255, 255, 255)

def _ease(p):
    """Smoothstep, clamped to [0,1]."""
    p = 0.0 if p < 0 else 1.0 if p > 1 else p
    return p * p * (3 - 2 * p)

def _hex_rgb(s):
    s = (s or "#E8590C").lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))

def _save_frames(draw_fn, frames, workdir, index):
    pat = os.path.join(workdir, f"scene_{index:02d}_%04d.png")
    for i in range(frames):
        draw_fn(i, frames).save(pat % i)
    return pat

def _font(meta, text, size):
    try:
        return ImageFont.truetype(render._font_path(meta, text), size)
    except Exception:
        return ImageFont.load_default()

def render_title(props, meta, W, H, frames, workdir, index):
    title = props.get("title", "")
    subtitle = props.get("subtitle")
    kicker = props.get("kicker")
    accent = _hex_rgb(props.get("accent"))
    fps = meta.get("fps", 30)
    intro = max(1, int(0.8 * fps))                  # title fades/rises over ~0.8s
    sub_delay = max(1, int(0.35 * fps))
    tfont = _font(meta, title, int(H * 0.085))
    sfont = _font(meta, subtitle or " ", int(H * 0.040))
    kfont = _font(meta, kicker or " ", int(H * 0.028))
    x = int(W * 0.08)

    def _prog(i, delay):
        if frames <= 1:
            return 1.0
        return _ease((i - delay) / max(1, min(intro, frames - 1)))

    def draw(i, n):
        base = Image.new("RGBA", (W, H), BG + (255,))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        p = _prog(i, 0)
        a = int(255 * p); dy = int((1 - p) * (H * 0.03))
        # accent rule above the title
        rule_y = int(H * 0.34) + dy
        d.rectangle([x, rule_y, x + int(W * 0.10), rule_y + max(3, int(H * 0.008))],
                    fill=accent + (a,))
        d.text((x, int(H * 0.40) + dy), title, font=tfont, fill=FG + (a,))
        if subtitle:
            p2 = _prog(i, sub_delay)
            d.text((x, int(H * 0.56)), subtitle, font=sfont,
                   fill=(180, 190, 205, int(255 * p2)))
        if kicker:
            p3 = _prog(i, 2 * sub_delay)
            d.text((x, int(H * 0.72)), kicker, font=kfont,
                   fill=(140, 150, 165, int(255 * p3)))
        return Image.alpha_composite(base, layer).convert("RGB")

    return _save_frames(draw, frames, workdir, index)
