"""Deterministic animated scene renderers -> per-frame PNG sequences (no slides).
Each renderer is a PURE function of the frame index; no randomness, no wall-clock.
Frames are namespaced by scene index because the full render shares one workdir."""
import os
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont
import render  # reuse the CJK-aware font resolver
import matplotlib
matplotlib.use("Agg")                       # deterministic, headless raster backend
import matplotlib.pyplot as plt
from matplotlib import font_manager

BG = (13, 17, 23)        # near-black, matches the caption aesthetic
FG = (255, 255, 255)

_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

def _chrome_bin(meta):
    """Locate a Chrome/Chromium binary: meta.chrome_path, the macOS app, or PATH. None if absent."""
    c = (meta or {}).get("chrome_path")
    if c and os.path.exists(c):
        return c
    for p in _CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        w = shutil.which(n)
        if w:
            return w
    return None

def _chrome_shot(url, out_png, W, H, meta):
    """Screenshot an HTML url to out_png via headless Chrome. Raises if no Chrome is found."""
    chrome = _chrome_bin(meta)
    if not chrome:
        raise RuntimeError("no Chrome/Chromium for the HTML tier — install Chrome or set meta.chrome_path")
    subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                    f"--window-size={W},{H}", f"--screenshot={out_png}", url],
                   check=True, capture_output=True, timeout=60)

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


def render_keypoints(props, meta, W, H, frames, workdir, index):
    """Conceptual beat -> kinetic labeled points that reveal one-by-one. PURE; renders only props."""
    title = props.get("title")
    points = props.get("points", [])
    accent = _hex_rgb(props.get("accent"))
    fps = meta.get("fps", 30)
    intro = max(1, int(0.5 * fps))                  # each row fades/slides in over ~0.5s
    stagger = max(1, int(0.35 * fps))               # rows appear staggered
    x = int(W * 0.10)
    # Resolve fonts from the ACTUAL text that will be drawn (a Latin stand-in would tofu CJK).
    lbl_sample = "".join(str(p.get("label", "")) for p in points) or "x"
    sub_sample = "".join(str(p.get("sub", "")) for p in points) or "x"
    tfont = _font(meta, title or " ", int(H * 0.058))
    lfont = _font(meta, lbl_sample, int(H * 0.050))
    sfont = _font(meta, sub_sample, int(H * 0.030))
    top = int(H * 0.30) if title else int(H * 0.24)
    row_h = int(H * 0.135)

    def _prog(i, delay):
        if frames <= 1:
            return 1.0
        return _ease((i - delay) / max(1, min(intro, frames - 1)))

    def draw(i, n):
        base = Image.new("RGBA", (W, H), BG + (255,))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if title:
            a0 = int(255 * _prog(i, 0))
            d.text((x, int(H * 0.15)), title, font=tfont, fill=FG + (a0,))
        for k, pnt in enumerate(points):
            p = _prog(i, (k + 1) * stagger)
            if p <= 0:
                continue
            a = int(255 * p); dx = int((1 - p) * (W * 0.02))
            y = top + k * row_h
            mr = max(4, int(H * 0.018))
            d.rectangle([x - dx, y + int(row_h * 0.18), x - dx + mr, y + int(row_h * 0.18) + mr * 3],
                        fill=accent + (a,))
            lx = x - dx + mr + int(W * 0.018)
            d.text((lx, y), str(pnt.get("label", "")), font=lfont, fill=FG + (a,))
            if pnt.get("sub"):
                d.text((lx, y + int(row_h * 0.52)), str(pnt["sub"]), font=sfont,
                       fill=(150, 160, 175, a))
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

def _visible_count(total, p):
    return max(0, min(total, int(_ease(p) * total + 1e-9)))

def render_timeline(props, meta, W, H, frames, workdir, index):
    events = props.get("events", [])
    title = props.get("title")
    famly = _mpl_font(meta)
    dpi = 100; figsize = (W / dpi, H / dpi)
    accent = props.get("accent", "#4C9BE8")
    n_ev = len(events)
    xs = list(range(n_ev))

    def draw(i, n):
        vis = _visible_count(n_ev, i / max(1, n - 1) if n > 1 else 1.0)
        fig = plt.figure(figsize=figsize, dpi=dpi); fig.patch.set_facecolor("#0d1117")
        ax = fig.add_subplot(111); ax.set_facecolor("#0d1117"); ax.axis("off")
        if title:
            ax.set_title(title, color="white", fontsize=18, fontfamily=famly, pad=16)
        if n_ev:
            ax.plot([-0.3, n_ev - 0.7], [0, 0], color="#3a4150", linewidth=2)
            for j in range(vis):
                ax.scatter([xs[j]], [0], s=120, color=accent, zorder=3)
                ax.text(xs[j], 0.12, events[j].get("date", ""), ha="center",
                        color="#c0c8d4", fontsize=12, fontfamily=famly)
                ax.text(xs[j], -0.18, events[j].get("label", ""), ha="center",
                        color="white", fontsize=14, fontfamily=famly)
            ax.set_xlim(-0.6, n_ev - 0.4); ax.set_ylim(-0.5, 0.5)
        fig.tight_layout()
        fig.canvas.draw()
        img = Image.frombytes("RGBA", fig.canvas.get_width_height(),
                              bytes(fig.canvas.buffer_rgba())).convert("RGB")
        plt.close(fig)
        return img.resize((W, H), Image.LANCZOS) if img.size != (W, H) else img

    return _save_frames(draw, frames, workdir, index)


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


def render_compare(props, meta, W, H, frames, workdir, index):
    """Decomposition/contrast -> a labeled 'split' (100% stacked bar) or 'versus' (side-by-side).
    PURE; values come straight from props (faithful)."""
    kind = props.get("kind", "split")
    parts = props.get("parts", [])
    labels = [str(p.get("label", "")) for p in parts]
    values = [p["value"] for p in parts]
    title = props.get("title")
    famly = _mpl_font(meta)
    dpi = 100; figsize = (W / dpi, H / dpi)
    palette = [props.get("accent", "#4C9BE8"), "#E8590C", "#46A758", "#9B7EDE", "#C0C8D4"]

    def draw(i, n):
        p = i / max(1, n - 1) if n > 1 else 1.0
        e = _ease(p)
        fig = plt.figure(figsize=figsize, dpi=dpi); fig.patch.set_facecolor("#0d1117")
        ax = fig.add_subplot(111); ax.set_facecolor("#0d1117")
        if title:
            ax.set_title(title, color="white", fontsize=18, fontfamily=famly, pad=16)
        if kind == "versus":
            cur = _chart_values(values, p)
            ax.bar(labels, cur, color=[palette[k % len(palette)] for k in range(len(parts))])
            ax.set_ylim(0, (max(values + [0]) * 1.15 or 1))
            for sp in ax.spines.values():
                sp.set_color("#3a4150")
            ax.tick_params(colors="#c0c8d4")
            for t in ax.get_xticklabels():
                t.set_fontfamily(famly)
        else:  # split — one 100% stacked horizontal bar
            ax.axis("off")
            total = props.get("total") or sum(values) or 1
            left = 0.0
            for k, v in enumerate(values):
                w = (v / total) * e
                ax.barh([0], [w], left=[left], color=palette[k % len(palette)], height=0.5)
                if w > 0.05:
                    ax.text(left + w / 2, 0, f"{labels[k]}\n{v:g}", ha="center", va="center",
                            color="white", fontsize=13, fontfamily=famly)
                left += w
            ax.set_xlim(0, 1); ax.set_ylim(-0.5, 0.5)
        fig.tight_layout(); fig.canvas.draw()
        img = Image.frombytes("RGBA", fig.canvas.get_width_height(),
                              bytes(fig.canvas.buffer_rgba())).convert("RGB")
        plt.close(fig)
        return img.resize((W, H), Image.LANCZOS) if img.size != (W, H) else img

    return _save_frames(draw, frames, workdir, index)


def render_html(props, meta, W, H, frames, workdir, index):
    """Render a designed HTML page (paused CSS reveals) into a frame sequence via headless Chrome.
    If a per-scene word-timing file (audio/NN.words.json) exists AND the page has [data-cue-index]
    points, reveal each point at its spoken cue time across the FULL scene (audio-synced); otherwise
    animate the reveals over anim_seconds then hold (the default)."""
    import json, re
    import cues as _cues
    src = os.path.join(meta["_out"], props["html"])
    fps = meta.get("fps", 30)
    dur = frames / float(fps)
    html = open(src, encoding="utf-8", errors="replace").read()
    words_path = os.path.join(meta["_out"], "audio", f"{index:02d}.words.json")
    # collect cued points: (cue-index, anchor) where anchor = data-cue="..." (required on cued points)
    pts = re.findall(r'data-cue-index="(\d+)"[^>]*?data-cue="([^"]*)"', html)
    pts += [(i, a) for (a, i) in re.findall(r'data-cue="([^"]*)"[^>]*?data-cue-index="(\d+)"', html)]
    cue_param = None
    if pts and os.path.exists(words_path):
        try:
            words = json.load(open(words_path))
            anchors = [a for _, a in sorted(((int(i), a) for i, a in pts), key=lambda x: x[0])]
            ctimes = _cues.resolve_cues(words, anchors)
            cue_param = ",".join(f"{t:.3f}" for t in ctimes)
        except Exception:
            cue_param = None
    pat = os.path.join(workdir, f"scene_{index:02d}_%04d.png")
    os.makedirs(workdir, exist_ok=True)
    if cue_param is not None:
        # capture a fresh frame near each cue's reveal window (~0.6s); hold (copy) elsewhere
        ctimes = [float(x) for x in cue_param.split(",")]
        burst = 0.6
        def is_reveal(t):
            return t <= 0.001 or any(c <= t <= c + burst for c in ctimes)
        last = None
        for i in range(frames):
            outp = pat % i
            t = i / float(fps)
            if is_reveal(t) or last is None:
                p = min(1.0, t / dur)
                _chrome_shot(f"file://{src}?p={p:.4f}&cues={cue_param}&dur={dur:.3f}", outp, W, H, meta)
                last = outp
            else:
                shutil.copyfile(last, outp)
        return pat
    # default path (unchanged): animate over anim_seconds, then hold
    anim = float(props.get("anim_seconds", 0.8))
    reveal_frames = max(1, min(frames, int(round(anim * fps))))
    settle = None
    for i in range(frames):
        out = pat % i
        p = 1.0 if i >= reveal_frames - 1 else i / max(1, reveal_frames - 1)
        if p >= 1.0 and settle is not None:
            shutil.copyfile(settle, out); continue
        _chrome_shot(f"file://{src}?p={p:.4f}", out, W, H, meta)
        if p >= 1.0:
            settle = out
    return pat
