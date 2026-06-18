"""Deterministic animated scene renderers -> per-frame PNG sequences (no slides).
Each renderer is a PURE function of the frame index; no randomness, no wall-clock.
Frames are namespaced by scene index because the full render shares one workdir."""
import os
from PIL import Image, ImageDraw, ImageFont
import render  # reuse the CJK-aware font resolver
import matplotlib
matplotlib.use("Agg")                       # deterministic, headless raster backend
import matplotlib.pyplot as plt
from matplotlib import font_manager

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


def _chart_values(values, p):
    e = _ease(p)
    out = []
    for v in values:
        x = v * e
        out.append(round(x) if isinstance(v, int) and v == int(v) else x)
    return [min(o, v) if v >= 0 else max(o, v) for o, v in zip(out, values)]

def _mpl_font(meta):
    """Register and select a CJK font for matplotlib when the narration language is CJK,
    so axis/labels don't tofu; else use matplotlib's bundled DejaVu Sans."""
    lang = (meta.get("language") or "").lower().split("-")[0]
    if lang in ("zh", "ja", "ko"):
        path = render._font_path({"language": lang}, "中")     # reuse the CJK resolver
        try:
            font_manager.fontManager.addfont(path)
            return font_manager.FontProperties(fname=path).get_name()
        except Exception:
            pass
    return "DejaVu Sans"

def render_chart(props, meta, W, H, frames, workdir, index):
    kind = props.get("kind", "bars")
    data = props.get("data", [])
    labels = [str(d.get("label", "")) for d in data]
    values = [d["value"] for d in data]
    title = props.get("title"); unit = props.get("unit", "")
    y_max = props.get("y_max") or (max(values + [0]) * 1.15 or 1)
    famly = _mpl_font(meta)
    dpi = 100
    figsize = (W / dpi, H / dpi)
    accent = props.get("accent", "#4C9BE8")

    def draw(i, n):
        cur = _chart_values(values, i / max(1, n - 1) if n > 1 else 1.0)
        fig = plt.figure(figsize=figsize, dpi=dpi)
        fig.patch.set_facecolor("#0d1117")
        ax = fig.add_subplot(111); ax.set_facecolor("#0d1117")
        for sp in ax.spines.values():
            sp.set_color("#3a4150")
        ax.tick_params(colors="#c0c8d4")
        if title:
            ax.set_title(title, color="white", fontsize=18, fontfamily=famly, pad=16)
        if kind == "counter":
            ax.axis("off")
            ax.text(0.5, 0.5, f"{cur[0]:g}{unit}", ha="center", va="center",
                    color="white", fontsize=72, fontfamily=famly, transform=ax.transAxes)
        elif kind == "line":
            k = max(1, int(len(values) * (i / max(1, n - 1)))) if n > 1 else len(values)
            ax.plot(range(k), values[:k], color=accent, linewidth=3)
            ax.set_xlim(-0.5, len(values) - 0.5); ax.set_ylim(0, y_max)
            ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, fontfamily=famly)
        else:  # bars
            ax.bar(labels, cur, color=accent)
            ax.set_ylim(0, y_max)
            for t in ax.get_xticklabels():
                t.set_fontfamily(famly)
        if props.get("y_label"):
            ax.set_ylabel(props["y_label"], color="#c0c8d4", fontfamily=famly)
        fig.tight_layout()
        fig.canvas.draw()                       # Agg requires a draw before buffer_rgba()
        img = Image.frombytes("RGBA", fig.canvas.get_width_height(),
                              bytes(fig.canvas.buffer_rgba())).convert("RGB")
        plt.close(fig)
        return img.resize((W, H), Image.LANCZOS) if img.size != (W, H) else img

    return _save_frames(draw, frames, workdir, index)
