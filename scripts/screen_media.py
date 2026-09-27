#!/usr/bin/env python3
"""What a screenshot or a recording IS — read from the file, never declared.

The device layer (docs/superpowers/specs/2026-09-26-device-layer-design.md) puts a user's own screenshots and
recordings inside a drawn device. Everything it needs to know about them is measured here: a screenshot's
size and whether it is a long one, a recording's length and frame rate, how tall the text is at a point (the
legibility push-in), what a text field under a point looks like (so typing can paint over its placeholder),
and how tall the film's own caption glyphs are (the height a target's text must reach).
"""
import json
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import device_script as ds
from _caption_band import caption_size_px

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONTS = {"zh": os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf"),
          "latin": os.path.join(_ROOT, "assets", "fonts", "Inter-VF.ttf")}
_SAMPLE = {"zh": "字幕", "latin": "Caption"}
INK_DELTA = 40        # grey levels from the local background that count as glyph ink
FIELD_TOL = 8         # per-channel tolerance that still counts as the field's own background
FIELD_MAX_H = 0.25    # a region taller than this share of the screen is not a single-line field
FIELD_TEXT_MAX = 0.85 # ink taller than this share of the region: no padding, so no field (an icon may reach ~0.8)


def image_facts(path):
    """A screenshot's size. A file this machine cannot read as an image (HEIC, a corrupt download) is an error
    naming it — it used to end validate with a raw traceback."""
    try:
        with Image.open(path) as im:
            return {"w": int(im.width), "h": int(im.height)}
    except (OSError, ValueError) as e:              # PIL.UnidentifiedImageError is an OSError
        raise ds.DeviceScriptError(["%s is not an image this machine can read (save it as PNG or JPEG): %s"
                                    % (os.path.basename(path), str(e)[:120])])


def _screen_aspect(device):
    ratio = ds.SPEC["screenRatio"].get(device)
    if not ratio:
        raise ds.DeviceScriptError(["unknown device %r — one of %s" % (device, ", ".join(sorted(ds.SPEC["screenRatio"])))])
    rw, rh = ratio
    return float(rw) / float(rh)


def fit_kind(facts, device):
    """"fit" (within the tolerance of the screen's proportion), "long" (taller: it scrolls), or an error."""
    if facts["w"] <= 0 or facts["h"] <= 0:
        raise ds.DeviceScriptError(["a %dx%d screenshot has no picture" % (facts["w"], facts["h"])])
    a, s, tol = facts["w"] / float(facts["h"]), _screen_aspect(device), float(ds.SPEC["aspectTolerance"])
    if a > s * (1 + tol):
        fits = [k for k in ds.SPEC["screenRatio"] if abs(a / _screen_aspect(k) - 1) <= tol]
        hint = ("its proportion is a %s's screen — use device \"%s\"" % (fits[0], fits[0]) if fits else
                "crop it to the %s screen's proportion, or show it on a device whose screen it fits" % device)
        raise ds.DeviceScriptError(["a %dx%d screenshot is wider than a %s screen allows (%.3f against %.3f) — %s"
                                    % (facts["w"], facts["h"], device, a, s, hint)])
    return "long" if a < s * (1 - tol) else "fit"


def video_facts(path):
    """A recording's duration, frame rate and size, from ffprobe. A file without a video stream, or whose frame
    rate or duration ffprobe cannot state, is an error naming the file — never a default standing in for a
    measurement."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,avg_frame_rate:format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise ds.DeviceScriptError(["cannot read the recording %s: %s" % (path, r.stderr.strip()[-200:])])
    d = json.loads(r.stdout or "{}")
    st = (d.get("streams") or [None])[0]
    if not st or not st.get("width") or not st.get("height"):
        raise ds.DeviceScriptError(["the recording %s has no video stream" % path])
    fps = None
    for key in ("r_frame_rate", "avg_frame_rate"):
        num, _, den = str(st.get(key) or "").partition("/")
        try:
            v = float(num) / float(den or 1)
        except (ValueError, ZeroDivisionError):
            continue
        if v > 0:
            fps = v
            break
    if fps is None:
        raise ds.DeviceScriptError(["the recording %s has no frame rate ffprobe can state (r_frame_rate %r)"
                                    % (path, st.get("r_frame_rate"))])
    try:
        dur = float(d.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        dur = 0.0
    if dur <= 0:
        raise ds.DeviceScriptError(["the recording %s has no duration ffprobe can state" % path])
    return {"duration": dur, "fps": fps, "w": int(st["width"]), "h": int(st["height"])}


def check_video(facts, device, frm, to):
    probs = []
    a, s, tol = facts["w"] / float(max(1, facts["h"])), _screen_aspect(device), float(ds.SPEC["aspectTolerance"])
    if abs(a - s) > s * tol:
        probs.append("a %dx%d recording does not have a %s screen's proportion (%.3f against %.3f)"
                     % (facts["w"], facts["h"], device, a, s))
    if to > facts["duration"] + 1e-3:
        probs.append("`to` %.2f s is longer than the recording (%.2f s)" % (to, facts["duration"]))
    if frm < 0 or frm >= to:
        probs.append("`from` %.2f s must be >= 0 and before `to` %.2f s" % (frm, to))
    return probs


def _lum(path):
    return np.asarray(Image.open(path).convert("L"), dtype=float)


def _runs(rows):
    if not len(rows):
        return []
    out, start, prev = [], rows[0], rows[0]
    for r in rows[1:]:
        if r - prev > 2:
            out.append((start, prev))
            start = r
        prev = r
    out.append((start, prev))
    return out


def text_band_px(path, x, y, box=None, bg=None):
    """Height in SOURCE pixels of the line of text at image fractions (x, y): the contiguous band of rows
    holding glyph ink near that point, in a window around it (or inside `box`, image fractions).

    Every row holding ink belongs to the band: a line's words differ in reach (one has only x-height letters,
    the next an ascender and a descender) and the line is all of them together. So an icon beside the text
    that stands taller than it is measured with it (a Material search field's leading magnifier makes 16sp
    text read about a fifth taller). Telling an icon from a short word by shape was tried and rejected: a
    compactness + height + gap rule dropped a real word in 64 of 450 test lines ("lb", "A", "kl" look like
    icons), and a line that loses a word is worse than one that gains an icon. `bg` holds the ground at a value
    measured elsewhere (window_ground) instead of this window's median."""
    a = _lum(path)
    H, W = a.shape
    cx, cy = int(round(x * (W - 1))), int(round(y * (H - 1)))
    if box:
        x0, y0, x1, y1 = int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)
    else:
        x0, x1 = max(0, cx - int(W * 0.12)), min(W, cx + int(W * 0.12) + 1)
        y0, y1 = max(0, cy - int(H * 0.15)), min(H, cy + int(H * 0.15) + 1)
    win = a[y0:y1, x0:x1]
    if win.size == 0:
        return None
    bg = float(np.median(win)) if bg is None else float(bg)
    runs = [r for r in _runs(np.flatnonzero((np.abs(win - bg) > INK_DELTA).any(axis=1))) if r[1] - r[0] >= 2]
    if not runs:
        return None
    ty = cy - y0
    best = min(runs, key=lambda r: 0 if r[0] <= ty <= r[1] else min(abs(ty - r[0]), abs(ty - r[1])))
    return float(best[1] - best[0] + 1)


def window_ground(path, box):
    """The median luminance inside `box` (image fractions) — the ground text_band_px measures ink against."""
    a = _lum(path)
    H, W = a.shape
    win = a[int(box[1] * H):int(box[3] * H), int(box[0] * W):int(box[2] * W)]
    return float(np.median(win)) if win.size else None


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(round(c)) for c in rgb[:3])


def _run(row, c):
    """The run of True through column c of a boolean row (inclusive bounds), or None when row[c] is False."""
    if not row[c]:
        return None
    off = np.flatnonzero(~row)
    left, right = off[off < c], off[off > c]
    return (int(left[-1]) + 1 if len(left) else 0), (int(right[0]) - 1 if len(right) else len(row) - 1)


def _region_box(same, sx, sy, max_h):
    """Bounding box (inclusive) of the 4-connected region of `same` holding (sx, sy), filled a row-run at a time;
    None as soon as the region is taller than max_h rows."""
    H, W = same.shape
    seen = np.zeros_like(same)
    x0 = x1 = sx
    y0 = y1 = sy
    stack = [(sy, sx)]
    while stack:
        y, x = stack.pop()
        if seen[y, x]:
            continue
        run = _run(same[y] & ~seen[y], x)
        if run is None:
            continue
        a, b = run
        seen[y, a:b + 1] = True
        x0, x1, y0, y1 = min(x0, a), max(x1, b), min(y0, y), max(y1, y)
        if y1 - y0 + 1 > max_h:
            return None
        for ny in (y - 1, y + 1):
            if 0 <= ny < H:
                open_ = np.flatnonzero(same[ny, a:b + 1] & ~seen[ny, a:b + 1])
                if len(open_):
                    starts = open_[np.r_[True, np.diff(open_) > 1]]
                    stack.extend((ny, a + int(s)) for s in starts)
    return x0, y0, x1, y1


def field_at(path, x, y):
    """The text field under image fractions (x, y): its box, its background, the ink that reads on it, and the
    height of any text already in it. Raises DeviceScriptError when no single-line field is there.

    The field's colour is the commonest exact colour on the point's own rows: a point ON placeholder glyphs (a
    centred 搜索) still sees mostly field there, and a thin field never lets the page around it outvote it. The
    seed is the nearest pixel above or below the point that sits in a stretch of that colour no gap between
    glyphs spans (the padding over or under the placeholder line), so it is never a glyph or the hole inside
    one. The field is the connected region of its colour holding the seed: glyphs are holes in it, and any closed
    edge stops it (a 1px border on a page the same colour as the fill, whose rounded corners a row-or-column
    growth rule leaks through)."""
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=float)
    H, W, _ = rgb.shape
    cx, cy = int(round(x * (W - 1))), int(round(y * (H - 1)))
    where = "(%.2f, %.2f) of the screenshot" % (x, y)
    kb = max(8, int(W * 0.05))
    band = rgb[max(0, cy - 2):cy + 3, max(0, cx - kb):cx + kb + 1].reshape(-1, 3).astype(int)
    colours, counts = np.unique(band, axis=0, return_counts=True)
    bg = colours[counts.argmax()].astype(float)
    same = (np.abs(rgb - bg) <= FIELD_TOL).all(axis=2)
    need, reach = max(24, int(W * 0.05)), max(3, int(H * 0.03))
    seed = next((r for d in range(reach + 1) for r in ((cy,) if d == 0 else (cy - d, cy + d))
                 if 0 <= r < H and (_run(same[r], cx) or (0, -1))[1] - (_run(same[r], cx) or (0, -1))[0] + 1 >= need),
                None)
    if seed is None:
        raise ds.DeviceScriptError(["no text field under %s: no stretch of one colour runs through the point "
                                    "within %d px of it — aim `into` at the field itself" % (where, reach)])
    found = _region_box(same, cx, seed, int(FIELD_MAX_H * H))
    if found is None:
        raise ds.DeviceScriptError(["no text field under %s: its colour runs over %d%% of the screen's height, so "
                                    "the field has no visible edge (a border, or a fill more than %d/channel from "
                                    "the page)" % (where, round(100 * FIELD_MAX_H), FIELD_TOL)])
    x0, y0, x1, y1 = found
    box = [x0 / float(W), y0 / float(H), (x1 + 1) / float(W), (y1 + 1) / float(H)]
    text_px = text_band_px(path, x, y, box=box)
    if text_px is not None and text_px > FIELD_TEXT_MAX * (y1 + 1 - y0):
        raise ds.DeviceScriptError(["no text field under %s: the text there fills %d%% of the region's height, and "
                                    "a field has room above and below its line"
                                    % (where, round(100.0 * text_px / (y1 + 1 - y0)))])
    lum = 0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2]
    return {"box": box, "bg": _hex(bg), "ink": "#111111" if lum > 140 else "#ffffff", "textPx": text_px}


def caption_ink_px(lang, W, H):
    """The ink height of the film's caption glyphs at this frame size — the height a target's text must reach.
    Measured from the bundled body face at the caption's nominal size (layout.ts CAPTION_SIZE_FRAC). Film.tsx
    sets a long caption smaller to fit its band (`fitSize`), so this is the upper bound: the legibility push-in
    errs toward more legible, never less."""
    key = "zh" if str(lang or "").lower().startswith(("zh", "ja")) else "latin"
    size = caption_size_px(W, H)
    font = ImageFont.truetype(_FONTS[key], size)
    im = Image.new("L", (size * 8, size * 3), 0)
    ImageDraw.Draw(im).text((size // 2, size // 2), _SAMPLE[key], fill=255, font=font)
    rows = np.flatnonzero(np.asarray(im).max(axis=1) > 64)
    if not len(rows):
        raise RuntimeError("the caption sample %r drew no ink in %s — the bundled face lacks it"
                           % (_SAMPLE[key], _FONTS[key]))
    return float(rows[-1] - rows[0] + 1)
