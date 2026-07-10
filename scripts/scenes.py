"""Deterministic animated scene renderers -> per-frame PNG sequences (no slides).
Each renderer is a PURE function of the frame index; no randomness, no wall-clock.
Frames are namespaced by scene index because the full render shares one workdir."""
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont
import render  # reuse the CJK-aware font resolver
import _common
import _cdp
import matplotlib
matplotlib.use("Agg")                       # deterministic, headless raster backend
import matplotlib.pyplot as plt
from matplotlib import font_manager

# (the old module-level BG/FG constants are gone — all renderers resolve colors through
#  _scene_palette; _DARK_PALETTE below is the no-theme fallback)

def _chrome_bin(meta):
    """Locate a Chrome/Chromium binary (shared with doctor.py via _common.find_chrome)."""
    return _common.find_chrome(meta)

def _chrome_workers(meta):
    """How many Chrome shots to run at once. `meta.chrome_workers` overrides; default scales with
    cores but is capped (each worker is a full Chrome process — too many thrashes memory)."""
    n = (meta or {}).get("chrome_workers")
    if n:
        return max(1, int(n))
    return max(1, min(8, (os.cpu_count() or 4) - 1))

def _chrome_shot(url, out_png, W, H, meta):
    """Screenshot an HTML url to out_png via headless Chrome. Raises if no Chrome is found.
    NOTE: deliberately NO `--user-data-dir` — an explicit profile makes a headless launch HANG on
    macOS when the user's Chrome app is already running (it gets coalesced onto the live instance).
    Omitting it lets each `--headless` launch spin up its own throwaway profile, which is also what
    makes concurrent shots safe (no shared-profile singleton lock)."""
    chrome = _chrome_bin(meta)
    if not chrome:
        raise RuntimeError("no Chrome/Chromium for the HTML tier — install Chrome or set meta.chrome_path")
    subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                    f"--window-size={W},{H}", f"--screenshot={out_png}", url],
                   check=True, capture_output=True, timeout=90)

def _capture_frames(shots, copies, workdir, index, W, H, meta, label):
    """Materialise a scene's frame sequence and return the ffmpeg frame PATTERN.

    FAST path (default): one persistent headless Chrome per worker, JPEG screenshots over CDP
    (`_cdp.capture`) — one launch + many fast grabs instead of a cold Chrome per frame. If CDP is
    unavailable or errors, fall back to the robust SLOW path: a fresh `--headless --screenshot` per
    frame, run through a thread pool so the cold-starts at least overlap.

    `shots`=[(frame_index, url)] are captured fresh; `copies`=[(frame_index, source_frame_index)]
    are held frames filled by copying a captured shot (cheap). A live progress bar tracks the shots."""
    workers = _chrome_workers(meta)
    if (meta or {}).get("capture", "cdp") != "screenshot":
        try:
            return _cdp.capture(shots, copies, workdir, index, W, H, meta, label,
                                _chrome_bin(meta), workers, _common.progress)
        except _cdp.CDPUnavailable as e:
            print(f"[render_html] scene {index}: CDP capture unavailable ({e}) — "
                  f"falling back to --screenshot", flush=True)
    # fallback: per-frame --screenshot (PNG), thread-pooled
    pat = os.path.join(workdir, f"scene_{index:02d}_%04d.png")
    os.makedirs(workdir, exist_ok=True)
    total = len(shots)
    n = min(workers, total) or 1
    done = [0]
    _common.progress(0, total, label)
    def shoot(i, url):
        _chrome_shot(url, pat % i, W, H, meta)
    if n <= 1:
        for i, url in shots:
            shoot(i, url); done[0] += 1; _common.progress(done[0], total, label)
    else:
        with ThreadPoolExecutor(max_workers=n) as ex:
            futs = [ex.submit(shoot, i, url) for i, url in shots]
            for f in as_completed(futs):
                f.result()                       # propagate the first failure
                done[0] += 1; _common.progress(done[0], total, label)
    for i, src_i in copies:
        shutil.copyfile(pat % src_i, pat % i)
    return pat

def _ease(p):
    """Smoothstep, clamped to [0,1]."""
    p = 0.0 if p < 0 else 1.0 if p > 1 else p
    return p * p * (3 - 2 * p)

def _hex_rgb(s):
    s = (s or "#E8590C").lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))

def _on_fill(hex_color):
    """Text color for a colored FILL (segment/bar): near-black or white, whichever has the higher
    true WCAG contrast — same argmax theme.py uses for --on-accent."""
    import theme as _theme
    rgb = _hex_rgb(hex_color)
    return "#111111" if _theme._contrast((17, 17, 17), rgb) >= _theme._contrast((255, 255, 255), rgb) else "#ffffff"

# C1 — ONE COLOR WORLD. The programmatic tier historically hardcoded a dark palette, so a
# light-themed HTML deck would jarringly cut to a dark chart. _scene_palette parses the SAME
# theme.css :root vars the HTML tier uses (from meta["_out"]) into a small dict; when no
# theme.css exists (dark decks, unit tests) it returns the original dark constants byte-for-byte.
_DARK_PALETTE = {
    "bg": "#0d1117", "surface": "#161b22", "fg": "#ffffff", "muted": "#c0c8d4",
    # on_accent matches what theme.py's WCAG argmax derives for the default #4C9BE8 accent
    # (near-black 6.4:1 vs white 2.9:1 — white fails even the 3:1 large-text bar).
    "rule": "#3a4150", "accent": "#4C9BE8", "accent2": "#E8590C", "on_accent": "#111111",
}
_PAL_CACHE = {}

def _scene_palette(meta):
    """Parse <out_dir>/theme.css :root semantic vars into an RGB-hex palette dict, resolving
    var(--x) references; fall back to the dark constants when theme.css is absent."""
    out = (meta or {}).get("_out") or ""
    if out in _PAL_CACHE:
        return _PAL_CACHE[out]
    pal = dict(_DARK_PALETTE)
    try:
        css = open(os.path.join(out, "theme.css")).read()
        raw = dict(re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", css))

        def resolve(v, depth=0):
            v = (v or "").strip()
            m = re.match(r"var\(--([a-z0-9-]+)\)", v)
            if m and depth < 6:
                return resolve(raw.get(m.group(1), ""), depth + 1)
            return v if v.startswith("#") else None

        for css_name, key in [("bg", "bg"), ("surface", "surface"), ("fg", "fg"),
                              ("muted", "muted"), ("rule", "rule"), ("accent", "accent"),
                              ("accent2", "accent2"), ("on-accent", "on_accent")]:
            if css_name in raw:
                hexv = resolve(raw[css_name])
                if hexv:
                    pal[key] = hexv
    except Exception:
        pass
    _PAL_CACHE[out] = pal
    return pal

def _save_frames(draw_fn, frames, workdir, index):
    pat = os.path.join(workdir, f"scene_{index:02d}_%04d.png")
    for i in range(frames):
        draw_fn(i, frames).save(pat % i)
    return pat

# C8 — serif/sans type contrast. Editorial roles (title/kicker) get a serif; data/UI roles
# (stats, labels, axes) stay sans/mono. Bundled DejaVuSerif alongside DejaVuSans (same license).
BUNDLED_SERIF = os.path.join(os.path.dirname(render.BUNDLED_FONT), "DejaVuSerif.ttf")
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REDUCED_MOTION_CSS = os.path.join(_SKILL_ROOT, "assets", "html", "reduced-motion.css")

def _inject_reduced_motion(html, css_path):
    """Insert a reduced-motion.css <link> LAST in the page <head> (after base/theme/motifs) so its
    opacity-only reveal overrides win. Falls back to prepending if there's no </head>."""
    link = f'<link rel="stylesheet" href="file://{css_path}">'
    return html.replace("</head>", link + "</head>", 1) if "</head>" in html else link + html
_CJK_SERIF = [
    "/System/Library/Fonts/Supplemental/Songti.ttc", "/System/Library/Fonts/Songti.ttc",
    "/System/Library/Fonts/Supplemental/Hiragino Mincho ProN.ttc",
    "/System/Library/Fonts/AppleMyungjo.ttf",
]

def _serif_path(meta, text):
    """A serif for the given text: a system CJK serif for CJK text, else the bundled Latin serif;
    return None to signal 'no serif available' so the caller falls back to the sans resolver."""
    script = render._script_of(text or "", (meta or {}).get("language", "auto"))
    if script != "latin":
        for p in _CJK_SERIF:
            if os.path.exists(p):
                return p
        return None                       # let render._font_path pick the CJK sans (no tofu)
    return BUNDLED_SERIF if os.path.exists(BUNDLED_SERIF) else None

def _font(meta, text, size, role="sans"):
    path = None
    if role == "serif" and not (meta or {}).get("font"):   # an explicit meta.font wins for all roles
        path = _serif_path(meta, text)
    try:
        return ImageFont.truetype(path or render._font_path(meta, text), size)
    except Exception:
        return ImageFont.load_default()

def _wrap_pil(draw, text, font, max_w):
    """Greedy word-wrap `text` to lines each ≤ max_w px (PIL). Never returns []. For scripts with no
    spaces (CJK), falls back to character wrapping so a long line still fits instead of overflowing."""
    words = str(text).split()
    if not words:
        return [""]
    if len(words) == 1 and draw.textlength(words[0], font=font) > max_w:  # CJK / one long token
        out, cur = [], ""
        for ch in words[0]:
            if draw.textlength(cur + ch, font=font) <= max_w or not cur:
                cur += ch
            else:
                out.append(cur); cur = ch
        return out or [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        if draw.textlength(cur + " " + w, font=font) <= max_w:
            cur += " " + w
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines


def _fit_lines(meta, text, max_w, start_px, max_lines, role=None):
    """Largest font (down to ~55% of start_px) at which `text` wraps to ≤ max_lines lines within max_w.
    Returns (font, lines). Prevents the single-line clip that overflowed long titles/labels off-frame."""
    scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    px = int(start_px)
    f = _font(meta, text, px, role=role)
    lines = _wrap_pil(scratch, text, f, max_w)
    while px > int(start_px * 0.55):
        f = _font(meta, text, px, role=role)
        lines = _wrap_pil(scratch, text, f, max_w)
        if len(lines) <= max_lines and all(scratch.textlength(ln, font=f) <= max_w for ln in lines):
            break
        px = int(px * 0.92)
    return f, lines


def render_title(props, meta, W, H, frames, workdir, index):
    title = props.get("title", "")
    subtitle = props.get("subtitle")
    kicker = props.get("kicker")
    pal = _scene_palette(meta)
    accent = _hex_rgb(props.get("accent") or pal["accent"])
    bg = _hex_rgb(pal["bg"]); fg = _hex_rgb(pal["fg"]); muted = _hex_rgb(pal["muted"])
    fps = meta.get("fps", 30)
    intro = max(1, int(0.8 * fps))                  # title fades/rises over ~0.8s
    sub_delay = max(1, int(0.35 * fps))
    x = int(W * 0.08)
    max_w = W - 2 * x                               # keep text INSIDE the frame (fixes long-title clip)
    # wrap + shrink-to-fit each block so a long title/subtitle no longer overruns the right edge
    tfont, title_lines = _fit_lines(meta, title, max_w, int(H * 0.085), max_lines=3, role="serif")
    sfont, sub_lines = _fit_lines(meta, subtitle, max_w, int(H * 0.040), max_lines=2) if subtitle else (None, [])
    kfont, kick_lines = _fit_lines(meta, kicker, max_w, int(H * 0.028), max_lines=1) if kicker else (None, [])
    t_lh = int(tfont.size * 1.14)
    s_lh = int(sfont.size * 1.28) if sfont else 0
    # lay the blocks out top-down from a fixed anchor so multi-line titles never collide with the subtitle
    rule_y0 = int(H * 0.30)
    title_y0 = int(H * 0.36)
    sub_y0 = title_y0 + len(title_lines) * t_lh + int(H * 0.045)
    kick_y0 = sub_y0 + len(sub_lines) * s_lh + int(H * 0.035)

    def _prog(i, delay):
        if frames <= 1:
            return 1.0
        return _ease((i - delay) / max(1, min(intro, frames - 1)))

    def draw(i, n):
        base = Image.new("RGBA", (W, H), bg + (255,))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        p = _prog(i, 0)
        a = int(255 * p)
        dy = 0 if meta.get("reduced_motion") else int((1 - p) * (H * 0.03))
        d.rectangle([x, rule_y0 + dy, x + int(W * 0.10), rule_y0 + dy + max(3, int(H * 0.008))],
                    fill=accent + (a,))
        for k, ln in enumerate(title_lines):
            d.text((x, title_y0 + dy + k * t_lh), ln, font=tfont, fill=fg + (a,))
        if sub_lines:
            a2 = int(255 * _prog(i, sub_delay))
            for k, ln in enumerate(sub_lines):
                d.text((x, sub_y0 + k * s_lh), ln, font=sfont, fill=muted + (a2,))
        if kick_lines:
            a3 = int(255 * _prog(i, 2 * sub_delay))
            d.text((x, kick_y0), kick_lines[0], font=kfont, fill=muted + (a3,))
        return Image.alpha_composite(base, layer).convert("RGB")

    return _save_frames(draw, frames, workdir, index)


def render_keypoints(props, meta, W, H, frames, workdir, index):
    """Conceptual beat -> kinetic labeled points that reveal one-by-one. PURE; renders only props."""
    title = props.get("title")
    points = props.get("points", [])
    pal = _scene_palette(meta)
    accent = _hex_rgb(props.get("accent") or pal["accent"])
    bg = _hex_rgb(pal["bg"]); fg = _hex_rgb(pal["fg"]); muted = _hex_rgb(pal["muted"])
    fps = meta.get("fps", 30)
    intro = max(1, int(0.5 * fps))                  # each row fades/slides in over ~0.5s
    # SPREAD the row reveals across the scene (track the speaking pace) instead of cramming them into
    # the first ~1s and holding — same principle as render_timeline/render_chart, and the html tier's
    # spread default. The title is the first slot; points fill the rest (floor 0.32s for short scenes).
    n_pts = max(1, len(points))
    stagger = max(int(0.32 * fps), frames // (n_pts + 1))
    x = int(W * 0.10)
    sub_sample = "".join(str(p.get("sub", "")) for p in points) or "x"
    tfont = _font(meta, title or " ", int(H * 0.058), role="serif")   # editorial headline
    top = int(H * 0.28) if title else int(H * 0.22)
    # DYNAMIC row height so N points fit the vertical zone (was fixed 0.135H → the 6th row clipped off-frame)
    avail_h = int(H * 0.92) - top
    row_h = min(int(H * 0.135), max(int(H * 0.085), avail_h // n_pts))
    mr = max(4, int(H * 0.018))
    lx0 = x + mr + int(W * 0.018)
    lbl_max_w = W - lx0 - int(W * 0.05)
    # fit the label font so the LONGEST label fits on ONE line within the row width (was single-line d.text
    # with no width-fit → long labels overran the right edge), capped by the row height.
    longest = max((str(p.get("label", "")) for p in points), key=len, default="x") or "x"
    lfont, _ = _fit_lines(meta, longest, lbl_max_w, min(int(H * 0.050), int(row_h * 0.42)), max_lines=1)
    sfont = _font(meta, sub_sample, min(int(H * 0.030), max(14, int(row_h * 0.26))))

    def _prog(i, delay):
        if frames <= 1:
            return 1.0
        return _ease((i - delay) / max(1, min(intro, frames - 1)))

    def draw(i, n):
        base = Image.new("RGBA", (W, H), bg + (255,))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if title:
            a0 = int(255 * _prog(i, 0))
            d.text((x, int(H * 0.15)), title, font=tfont, fill=fg + (a0,))
        for k, pnt in enumerate(points):
            p = _prog(i, (k + 1) * stagger)
            if p <= 0:
                continue
            a = int(255 * p)
            # reduced motion: fade only — no slide-in (translate) on the rows
            dx = 0 if meta.get("reduced_motion") else int((1 - p) * (W * 0.02))
            y = top + k * row_h
            mr = max(4, int(H * 0.018))
            d.rectangle([x - dx, y + int(row_h * 0.18), x - dx + mr, y + int(row_h * 0.18) + mr * 3],
                        fill=accent + (a,))
            lx = x - dx + mr + int(W * 0.018)
            d.text((lx, y), str(pnt.get("label", "")), font=lfont, fill=fg + (a,))
            if pnt.get("sub"):
                d.text((lx, y + int(row_h * 0.52)), str(pnt["sub"]), font=sfont,
                       fill=muted + (a,))
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
    pal = _scene_palette(meta)
    accent = props.get("accent") or pal["accent"]
    c_bg, c_fg, c_muted, c_rule = pal["bg"], pal["fg"], pal["muted"], pal["rule"]
    n_ev = len(events)
    xs = list(range(n_ev))

    def draw(i, n):
        vis = _visible_count(n_ev, i / max(1, n - 1) if n > 1 else 1.0)
        fig = plt.figure(figsize=figsize, dpi=dpi); fig.patch.set_facecolor(c_bg)
        ax = fig.add_subplot(111); ax.set_facecolor(c_bg); ax.axis("off")
        if title:
            ax.set_title(title, color=c_fg, fontsize=18, fontfamily=famly, pad=16)
        if n_ev:
            ax.plot([-0.3, n_ev - 0.7], [0, 0], color=c_rule, linewidth=2)
            for j in range(vis):
                ax.scatter([xs[j]], [0], s=120, color=accent, zorder=3)
                # accept BOTH key conventions: programmatic `date`/`label` AND the HTML tier's `when`/`what`
                # (an author following the .timeline archetype uses when/what — never silently drop the label).
                _when = events[j].get("date") or events[j].get("when") or ""
                _what = events[j].get("label") or events[j].get("what") or ""
                ax.text(xs[j], 0.12, str(_when), ha="center",
                        color=c_muted, fontsize=12, fontfamily=famly)
                ax.text(xs[j], -0.18, str(_what), ha="center",
                        color=c_fg, fontsize=14, fontfamily=famly)
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
    values = [d.get("value", 0) for d in data]
    title = props.get("title"); unit = props.get("unit", "")
    # gather magnitudes across ALL data shapes (value / values[] / v1,v2 / y) for a sensible y ceiling,
    # so slope/dumbbell/scatter/dist kinds (which don't use `value`) still get a fitting axis.
    _allv = list(values)
    for d in data:
        vv = d.get("values")
        if isinstance(vv, list):
            _allv += [x for x in vv if isinstance(x, (int, float))]
        for _k in ("v1", "v2", "y"):
            if isinstance(d.get(_k), (int, float)):
                _allv.append(d[_k])
    y_max = props.get("y_max") or (max(_allv + [0]) * 1.15 or 1)
    famly = _mpl_font(meta)
    dpi = 100
    figsize = (W / dpi, H / dpi)
    pal = _scene_palette(meta)
    accent = props.get("accent") or pal["accent"]
    c_bg, c_fg, c_muted, c_rule = pal["bg"], pal["fg"], pal["muted"], pal["rule"]
    climax = bool(props.get("climax"))

    def draw(i, n):
        p_raw = i / max(1, n - 1) if n > 1 else 1.0
        if kind == "small_multiples":
            # the SAME mini-trend per category on a SHARED scale — spot the outlier/common shape at a glance
            series = [(str(d.get("label", "")), (d.get("values") or [])) for d in data]
            m = len(series) or 1
            cols = 2 if m <= 4 else 3
            rows = (m + cols - 1) // cols
            fig, axes = plt.subplots(rows, cols, figsize=figsize, dpi=dpi, facecolor=c_bg)
            axes = list(axes.flatten()) if hasattr(axes, "flatten") else [axes]
            smax = max([max(v) for _, v in series if v] + [1]) * 1.1
            for ax2, (lab, vals) in zip(axes, series):
                ax2.set_facecolor(c_bg)
                k = max(1, int(len(vals) * p_raw)) if vals else 0
                if vals:
                    ax2.plot(range(k), vals[:k], color=accent, linewidth=2.5)
                ax2.set_title(lab, color=c_fg, fontsize=13, fontfamily=famly)
                ax2.set_ylim(0, smax); ax2.set_xticks([]); ax2.set_yticks([])
                for sp in ax2.spines.values():
                    sp.set_color(c_rule)
            for ax2 in axes[m:]:
                ax2.axis("off")
            if title:
                fig.suptitle(title, color=c_fg, fontsize=18, fontfamily=famly)
            fig.tight_layout()
            fig.canvas.draw()
            img = Image.frombytes("RGBA", fig.canvas.get_width_height(),
                                  bytes(fig.canvas.buffer_rgba())).convert("RGB")
            plt.close(fig)
            return img.resize((W, H), Image.LANCZOS) if img.size != (W, H) else img
        cur = _chart_values(values, p_raw)
        fig = plt.figure(figsize=figsize, dpi=dpi)
        fig.patch.set_facecolor(c_bg)
        ax = fig.add_subplot(111); ax.set_facecolor(c_bg)
        for sp in ax.spines.values():
            sp.set_color(c_rule)
        ax.tick_params(colors=c_muted)
        if title:
            ax.set_title(title, color=c_fg, fontsize=18, fontfamily=famly, pad=16)
        if kind == "counter":
            ax.axis("off")
            # C7 — hero-number landing beat: on a CLIMAX counter, reach the true final at ~68%
            # of the scene then HOLD it static (identical frames) so the key figure registers.
            # No overshoot/bounce (would misrepresent a plain number). Non-climax = unchanged.
            cp = min(1.0, p_raw / 0.68) if climax else p_raw
            cval = _chart_values(values, cp)[0]
            ax.text(0.5, 0.5, f"{cval:g}{unit}", ha="center", va="center",
                    color=c_fg, fontsize=72, fontfamily=famly, transform=ax.transAxes)
        elif kind == "line":
            k = max(1, int(len(values) * (i / max(1, n - 1)))) if n > 1 else len(values)
            ax.plot(range(k), values[:k], color=accent, linewidth=3)
            ax.set_xlim(-0.5, len(values) - 0.5); ax.set_ylim(0, y_max)
            ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, fontfamily=famly)
        elif kind == "slope":
            # two points per category; the STORY is direction + rank crossover. The right end animates in.
            for d in data:
                vv = d.get("values") or [d.get("v1", 0), d.get("v2", 0)]
                a, b = vv[0], vv[1]
                bb = a + (b - a) * p_raw
                on = bool(d.get("on"))
                col = accent if on else c_muted
                ax.plot([0, 1], [a, bb], color=col, linewidth=4 if on else 2.5,
                        marker="o", markersize=8, solid_capstyle="round")
                ax.text(-0.03, a, f"{d.get('label','')}  {a:g}{unit}", ha="right", va="center",
                        color=c_fg, fontsize=13, fontfamily=famly)
                ax.text(1.03, bb, f"{b:g}{unit}", ha="left", va="center", color=col, fontsize=13, fontfamily=famly)
            ax.set_xlim(-0.5, 1.5); ax.set_ylim(0, y_max)
            ax.set_xticks([0, 1])
            ax.set_xticklabels([props.get("left", "before"), props.get("right", "after")], fontfamily=famly)
            for side in ("left", "right", "top"):
                ax.spines[side].set_visible(False)
            ax.set_yticks([])
        elif kind == "dumbbell":
            for j, d in enumerate(data):
                vv = d.get("values") or [d.get("v1", 0), d.get("v2", 0)]
                a = vv[0]; b = a + (vv[1] - a) * p_raw
                y = len(data) - 1 - j
                ax.plot([a, b], [y, y], color=c_rule, linewidth=6, solid_capstyle="round", alpha=0.6)
                ax.plot([a], [y], marker="o", markersize=13, color=c_muted)
                ax.plot([b], [y], marker="o", markersize=13, color=accent)
            ax.set_ylim(-0.6, len(data) - 0.4); ax.set_xlim(0, y_max)
            ax.set_yticks(range(len(data))); ax.set_yticklabels(list(reversed(labels)), fontfamily=famly)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
        elif kind == "scatter":
            xs = [d.get("x", 0) for d in data]; ys = [d.get("y", 0) for d in data]
            ax.scatter(xs, ys, s=150, color=accent, alpha=min(1.0, 0.3 + p_raw),
                       edgecolors=c_bg, linewidths=1.5)
            for d in data:
                if d.get("label"):
                    ax.annotate(str(d["label"]), (d.get("x", 0), d.get("y", 0)), color=c_muted,
                                fontsize=11, fontfamily=famly, xytext=(7, 7), textcoords="offset points")
            if props.get("x_label"):
                ax.set_xlabel(props["x_label"], color=c_muted, fontfamily=famly)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
        elif kind == "dist":
            # spread of a variable across groups (median/IQR/whiskers) + a strip of the real observations
            groups = [(d.get("values") or []) for d in data]
            bp = ax.boxplot(groups, patch_artist=True, widths=0.5, showfliers=False)
            for patch in bp["boxes"]:
                patch.set_facecolor(accent); patch.set_alpha(0.28); patch.set_edgecolor(accent)
            for part in ("whiskers", "caps", "medians"):
                for ln in bp[part]:
                    ln.set_color(c_muted if part != "medians" else accent)
                    ln.set_linewidth(2.5)
            for gi, g in enumerate(groups):
                ax.plot([gi + 1] * len(g), g, ".", color=accent,
                        alpha=min(0.5, 0.15 + p_raw * 0.5), markersize=7)
            ax.set_xticks(range(1, len(data) + 1)); ax.set_xticklabels(labels, fontfamily=famly)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
        else:  # bars
            ax.bar(labels, cur, color=accent)
            ax.set_ylim(0, y_max)
            for t in ax.get_xticklabels():
                t.set_fontfamily(famly)
            # direct value labels (guide §11: "use direct labels; annotation appears last") —
            # fade in over the last ~20% as the bars settle, anchored to the animated bar tip,
            # clamped below y_max so a tight user-supplied ceiling can't clip the text.
            la = max(0.0, min(1.0, (p_raw - 0.8) / 0.2))
            if la > 0:
                for j, v in enumerate(values):
                    ax.text(j, min(cur[j], y_max * 0.98) + y_max * 0.02, f"{v:g}{unit}",
                            ha="center", va="bottom", color=c_fg, alpha=la,
                            fontsize=14, fontfamily=famly)
        if props.get("y_label"):
            ax.set_ylabel(props["y_label"], color=c_muted, fontfamily=famly)
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
    pal = _scene_palette(meta)
    c_bg, c_fg, c_muted, c_rule = pal["bg"], pal["fg"], pal["muted"], pal["rule"]
    # categorical palette: color IS data here, so lead with the theme accent + accent2 and keep
    # the remaining distinct hues (do NOT desaturate — the skeptic flagged that as data-flattening).
    palette = [props.get("accent") or pal["accent"], pal["accent2"], "#46A758", "#9B7EDE", pal["muted"]]

    def draw(i, n):
        p = i / max(1, n - 1) if n > 1 else 1.0
        e = _ease(p)
        fig = plt.figure(figsize=figsize, dpi=dpi); fig.patch.set_facecolor(c_bg)
        ax = fig.add_subplot(111); ax.set_facecolor(c_bg)
        if title:
            ax.set_title(title, color=c_fg, fontsize=18, fontfamily=famly, pad=16)
        if kind == "versus":
            cur = _chart_values(values, p)
            ax.bar(labels, cur, color=[palette[k % len(palette)] for k in range(len(parts))])
            ax.set_ylim(0, (max(values + [0]) * 1.15 or 1))
            for sp in ax.spines.values():
                sp.set_color(c_rule)
            ax.tick_params(colors=c_muted)
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
                    # label sits ON the segment fill — pick black/white by true contrast per segment
                    ax.text(left + w / 2, 0, f"{labels[k]}\n{v:g}", ha="center", va="center",
                            color=_on_fill(palette[k % len(palette)]), fontsize=13, fontfamily=famly)
                left += w
            ax.set_xlim(0, 1); ax.set_ylim(-0.5, 0.5)
        fig.tight_layout(); fig.canvas.draw()
        img = Image.frombytes("RGBA", fig.canvas.get_width_height(),
                              bytes(fig.canvas.buffer_rgba())).convert("RGB")
        plt.close(fig)
        return img.resize((W, H), Image.LANCZOS) if img.size != (W, H) else img

    return _save_frames(draw, frames, workdir, index)


def _dedup_cue_pts(pts):
    """Collapse scraped (cue-index, anchor) pairs to ONE anchor per index, sorted by index.
    Co-revealing elements share a cue-index (a connector, or a group borrowing a block's slot). Keeping
    a REPEATED anchor would break resolve_cues' SEQUENTIAL match (it can't find a 2nd occurrence of the
    same phrase, defaults it late, and poisons EVERY later cue) — so keep the first non-empty anchor per
    index and the whole group co-reveals on that one moment."""
    by_idx = {}
    for i, a in pts:
        ii = int(i)
        if ii not in by_idx and (a or "").strip():
            by_idx[ii] = a
    return sorted(by_idx.items())


def render_html(props, meta, W, H, frames, workdir, index):
    """Render a designed HTML page (paused CSS reveals) into a frame sequence via headless Chrome.
    If a per-scene word-timing file (audio/NN.words.json) exists AND the page has [data-cue-index]
    points, reveal each point at its spoken cue time across the FULL scene (audio-synced); otherwise
    animate the reveals over anim_seconds then hold (the default)."""
    import json, re
    import cues as _cues
    # ABSOLUTE path: the file:// URL must be absolute. The `--screenshot` CLI tolerated a relative
    # path (it resolved it against cwd), but CDP Page.navigate rejects it (ERR_INVALID_URL) — which
    # silently produced Chrome error-page frames. abspath makes both paths correct.
    src = os.path.abspath(os.path.join(meta["_out"], props["html"]))
    fps = meta.get("fps", 30)
    dur = frames / float(fps)
    html = open(src, encoding="utf-8", errors="replace").read()
    # A living backdrop (.bg-live/.bg-drift/[data-ambient]) is driven by seek.js across the WHOLE
    # scene progress, so the frame-copy HOLD optimization below would freeze it for seconds then SNAP
    # to the next captured position (a render glitch). When one is present (and motion isn't reduced),
    # capture EVERY frame at true scene progress so the backdrop drifts smoothly. Opt-in + rare
    # (hero/hold beats), so the extra shots are affordable. Detect from the ORIGINAL page html
    # (reduced-motion strips the motion, so the copy optimization is correct there).
    # Token-exact + quote-agnostic — MUST match what seek.js's el.matches('.bg-live,.bg-drift,
    # [data-ambient]') treats as ambient, or a page ambient to the DOM but not here would silently fall
    # back to the freeze/snap copy path. Split each class attr into tokens (like the class list) so
    # 'my-bg-live'/'bg-live-2' don't false-match; accept single OR double quotes. (validate.py mirrors.)
    _cls = [a or b for a, b in re.findall(r'''class\s*=\s*(?:"([^"]*)"|'([^']*)')''', html)]
    _has_ambient = (not meta.get("reduced_motion")) and (
        any({"bg-live", "bg-drift"} & set(c.split()) for c in _cls)
        or bool(re.search(r'\bdata-ambient(?![\w-])', html)))
    # D — reduced-motion: capture a temp copy of the page with reduced-motion.css linked LAST (after
    # base/theme/motifs), so reveals become opacity-only and ambient/Ken-Burns motion is off. The page
    # uses absolute file:// links, so the temp file resolves them fine; cue parsing uses the original html.
    if meta.get("reduced_motion"):
        os.makedirs(workdir, exist_ok=True)
        src = os.path.join(workdir, f"rm_scene_{index:02d}.html")
        open(src, "w", encoding="utf-8").write(_inject_reduced_motion(html, _REDUCED_MOTION_CSS))
        src = os.path.abspath(src)
    words_path = os.path.join(meta["_out"], "audio", f"{index:02d}.words.json")
    # collect cued points: (cue-index, anchor) where anchor = data-cue="..." (required on cued points)
    pts = re.findall(r'data-cue-index="(\d+)"[^>]*?data-cue="([^"]*)"', html)
    pts += [(i, a) for (a, i) in re.findall(r'data-cue="([^"]*)"[^>]*?data-cue-index="(\d+)"', html)]
    cue_param = None        # comma list for seek.js, indexed by data-cue-index (sparse-safe)
    cue_times = []          # the resolved reveal moments (for the capture bursts)
    cue_err = None
    cue_src = None          # "words" (edge per-word timings) | "text" (narration char-position estimate)
    ordered = _dedup_cue_pts(pts)
    ctimes = None
    if ordered and os.path.exists(words_path):        # BEST: exact per-word timings (edge-tts)
        try:
            words = json.load(open(words_path))
            ctimes = _cues.resolve_cues(words, [a for _, a in ordered]); cue_src = "words"
        except Exception as e:
            ctimes, cue_err = None, str(e)
    if ordered and ctimes is None:                    # NO word timings (MiniMax/say/openai): estimate
        narration = (meta.get("_narration") or "")    # from each anchor's position in the narration text
        if narration.strip():
            ctimes = _cues.estimate_cues_from_text([a for _, a in ordered], narration, dur); cue_src = "text"
    if ordered and ctimes is not None:
        margin = max(0.0, dur - 0.5)                  # a cue must fire before the final frame, else hidden
        cue_times = [min(t, margin) for t in ctimes]
        sparse = [0.0] * (ordered[-1][0] + 1)         # index by the element's actual data-cue-index
        for (orig_i, _), t in zip(ordered, cue_times):
            sparse[orig_i] = t
        cue_param = ",".join(f"{t:.3f}" for t in sparse)
    os.makedirs(workdir, exist_ok=True)
    if cue_param is None and 'data-cue-index' in html:
        why = (f"malformed words.json: {cue_err}" if cue_err else
               ("no word-timings and no narration to estimate from" if not os.path.exists(words_path)
                else "points missing a data-cue= anchor attribute"))
        print(f"[render_html] scene {index}: audio-sync skipped ({why}) — using paced stagger")
    elif cue_src == "text":
        print(f"[render_html] scene {index}: no word-timings — reveals estimated from narration text position")
    if cue_param is not None:
        # capture a fresh frame during (a) the initial header-entrance window and (b) near each
        # cue's reveal window (~0.6s); hold (copy) elsewhere. The HEAD_WINDOW is essential: the
        # header chrome (kicker/rule/title/sub) animates in on plain time-based .reveal delays, NOT
        # on cues — without capturing [0, HEAD_WINDOW] the only early frame is p=0 (everything
        # hidden), which then gets copied until the first cue, leaving the whole page blank until
        # the first spoken anchor. ~1.2s covers the header stagger (delay ≤ .3s + .7s reveal).
        ctimes = cue_times
        burst = 0.6
        HEAD_WINDOW = 1.2
        def is_reveal(t):
            # _has_ambient forces every frame (the backdrop moves continuously); else burst around cues
            return _has_ambient or t <= HEAD_WINDOW or any(c <= t <= c + burst for c in ctimes)
        shots, copies, last_i = [], [], None
        for i in range(frames):
            t = i / float(fps)
            if is_reveal(t) or last_i is None:
                p = min(1.0, t / dur)
                shots.append((i, f"file://{src}?p={p:.4f}&cues={cue_param}&dur={dur:.3f}"))
                last_i = i
            else:
                copies.append((i, last_i))
        return _capture_frames(shots, copies, workdir, index, W, H, meta, f"scene {index:02d} (cued)")
    # paced fallback (no audio cues): animate over anim_seconds, then hold. When anim_seconds is
    # NOT set, default it to SPREAD the reveals across most of the scene (~0.7×duration) instead of
    # cramming them into the first ~0.8s — otherwise the content appears long before the voice
    # reaches it. Audio-synced `data-cue` reveals (above) are still the precise, preferred path;
    # this only makes the cue-less fallback track the speaking pace by default.
    av = props.get("anim_seconds")
    anim = float(av) if av is not None else max(1.2, 0.7 * dur)
    reveal_frames = max(1, min(frames, int(round(anim * fps))))
    shots, copies, settle_i = [], [], None
    for i in range(frames):
        if _has_ambient:
            # backdrop spans the whole scene: true progress, every frame (no hold-copy -> no snap).
            # reveals then also spread across the scene in blind mode — fine for the sparse hero/hold
            # beats a living backdrop belongs on (the cued path keeps reveals precise + settled).
            p = 1.0 if frames <= 1 else i / (frames - 1)   # single-frame → settled, like the paced path
            shots.append((i, f"file://{src}?p={p:.4f}"))
            continue
        p = 1.0 if i >= reveal_frames - 1 else i / max(1, reveal_frames - 1)
        if p >= 1.0 and settle_i is not None:
            copies.append((i, settle_i)); continue
        shots.append((i, f"file://{src}?p={p:.4f}"))
        if p >= 1.0:
            settle_i = i
    return _capture_frames(shots, copies, workdir, index, W, H, meta, f"scene {index:02d}")
