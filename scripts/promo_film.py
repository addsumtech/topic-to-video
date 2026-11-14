#!/usr/bin/env python3
"""promo_film — a product promo film from a SHOT TABLE over real product captures (references/promo-film.md).

    python3 scripts/promo_film.py <film_dir> [--spec=promo.json] [--check] [--stills=120,400] [--no-sound]
                                  [--bgm=auto|none|<file>] [--out=out.mp4] [--sheet] [--remix]

  --check    the table only: errors stop it by name, advisories (caption on type, repeat structure, ...) are said
  --stills   frames rendered from one bundle into _stills/ (look at them full-size before a full render)
  --sheet    after the render: _sheet.jpg, one frame per shot at 90 %
  --remix    re-mix the sound over the picture already rendered (no picture render)

<film_dir> holds the captures and the spec; it is the render's public dir, so every `src` in the spec is a path
relative to it. Steps: CHECK the table (files, boxes inside their capture, zoom within the capture's density, keys
in order, shot lengths) — a defect stops here, by name; RENDER the picture (remotion composition `PromoFilm`); PIN
the sound to the same table (a cue per action: air through each carried cut, whoosh on a camera move, pop on an
element landing, keys under typing, click on a click, swell → impact as the closing lockup forms) unless the spec lists its own `sfx`
[{f, cue, gain}]; MIX (a generated score under the cues by default — a promo is scored; `--bgm=none` for SFX only,
`--bgm=<file>` for the user's own track) → <film_dir>/out.mp4, and the cue list
actually used → <film_dir>/promo_sfx.json.

WHY. The study (references/craft-standard.md, promo-film.md): the showcase product films are a different KIND of
film from a narrated explainer — the product as itself under a 2.5D camera, serif title cards as breaths, one look,
1.5-6 s shots, flash cuts, sound pinned to each action. This is that kind of film as data, so a director writes a
table and the layer does the craft the same way every time.
"""
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import argflag, refuse_unknown  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION = os.path.join(ROOT, "remotion")
FPS = 30
MAX_ZOOM = 2.0            # a 2x capture: past this the texture is upsampled (PageCam clamps and warns)
TITLE_BAND = (40, 80)     # a title card is a breath: long enough to read, short enough to stay one
SHOT_BAND = (36, 240)
SHOT_BAND_NOTE = "1.2-8 s; the reference films' product shots run 1.5-6 s"
ASPECTS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350), "4:3": (1440, 1080)}  # = remotion/src/Root.tsx ASPECTS


def key(f, cx, cy, zoom, page_w, page_h, aspect="16:9", **extra):
    """A straight-on camera key aimed at (cx, cy) whose view STAYS ON THE PAGE: the centre is moved in just enough that
    the frame does not show past the page's edge at this zoom (the rule `check` advises on). For `compose.py`:
    `pf.key(40, box_cx, box_cy, 1.6, L["w"], L["h"])`. A page smaller than the view at this zoom is centred on that
    axis. Extra fields (ease, rx, ...) pass through; a tilted key is an object shot and is not clamped."""
    fw, fh = ASPECTS.get(aspect, ASPECTS["16:9"])
    eff = zoom * fw / 1920.0
    vw, vh = fw / eff, fh / eff
    k = dict(f=int(f), cx=float(cx), cy=float(cy), zoom=float(zoom), **extra)
    if abs(extra.get("rx", 0)) + abs(extra.get("ry", 0)) + abs(extra.get("rz", 0)) >= 2:
        return k
    k["cx"] = page_w / 2.0 if vw >= page_w else min(max(cx, vw / 2.0), page_w - vw / 2.0)
    k["cy"] = page_h / 2.0 if vh >= page_h else min(max(cy, vh / 2.0), page_h - vh / 2.0)
    k["cx"], k["cy"] = round(k["cx"], 1), round(k["cy"], 1)
    return k


class SpecError(ValueError):
    pass


def _png_size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size


def _pose_at(keys, f):
    """(cx, cy, zoom, tilted) of a page shot's camera at frame f, keys interpolated straight (for WHERE things sit on
    the frame, within a few % of the eased path)."""
    ks = sorted(keys or [], key=lambda k: k["f"])
    if not ks:
        return None
    def at(k):
        return k["cx"], k["cy"], k.get("zoom", 1.0), abs(k.get("rx", 0)) + abs(k.get("ry", 0)) + abs(k.get("rz", 0)) >= 2
    if f <= ks[0]["f"]:
        return at(ks[0])
    for k0, k1 in zip(ks, ks[1:]):
        if f <= k1["f"]:
            u = (f - k0["f"]) / max(1e-9, k1["f"] - k0["f"])
            a, b = at(k0), at(k1)
            return tuple(a[i] + (b[i] - a[i]) * u for i in range(3)) + (a[3] or b[3],)
    return at(ks[-1])


def _text_w(text, px):
    return sum(px * (1.0 if ord(ch) > 0x2E7F else 0.52) for ch in text)


def _sub_box(text, W, H, top=False):
    """The voice's subtitle box on the frame (Shots.tsx Subtitles), from its CSS: centred, low (or high, `top`)."""
    s_ = min(W, H) / 1080.0
    tw, maxw = _text_w(text[:64], 34 * s_), 0.72 * W
    lines = max(1, int(-(-tw // maxw)))
    bw, bh = min(maxw, tw) + 44 * s_, lines * 34 * s_ * 1.3 + 20 * s_
    if top:
        y0 = H * (0.12 if H > W else 0.07)
        return (W / 2 - bw / 2, y0, W / 2 + bw / 2, y0 + bh)
    y1 = H - H * (0.16 if H > W else 0.07)
    return (W / 2 - bw / 2, y1 - bh, W / 2 + bw / 2, y1)


CAPTION_CORNERS = ("bl", "br", "tl", "tr")


def _cap_box(text, pos, W, H):
    """The caption strip's box on the frame (Cards.tsx CaptionStrip) in its corner: bl (default), br, tl, tr."""
    s_ = min(W, H) / 1080.0
    w = 18 * s_ + _text_w(text, 28 * s_) + 32 * s_
    h = max(34 * s_, 28 * s_ * 1.3 + 16 * s_)
    x0 = 64 * s_ if pos[1] == "l" else W - 64 * s_ - w
    if pos[0] == "b":
        y1 = H - (220 if H > W else 60) * s_
        return (x0, y1 - h, x0 + w, y1)
    y0 = (200 if H > W else 60) * s_
    return (x0, y0, x0 + w, y0 + h)


def _say_parts(say):
    import re as _re
    return [q.strip() for q in _re.split(SPLIT_RE, say) if q.strip()] or [say]


def _caption_boxes(sh, W, H):
    """[(frames to sample, (x0, y0, x1, y1), what, alt box or None)] — the caption strip and the voice's subtitle as the
    promo draws them (Cards.tsx CaptionStrip, Shots.tsx Subtitles), estimated from their CSS. A subtitle has an
    alternative: the top of the frame (place_subtitles moves it there when the bottom is the page's text)."""
    s_ = min(W, H) / 1080.0
    out = []
    d = int(sh.get("dur", 0))
    cap = sh.get("caption") or {}
    if cap.get("text"):
        at = int(cap.get("at", 8))
        span_ = int(cap.get("dur", max(20, d - at - 6)))
        out.append(((at + 10, at + span_ - 8), _cap_box(cap["text"], cap.get("pos", "bl"), W, H),
                    "the caption \"%s\"" % cap["text"][:40], None if cap.get("pos") else "caption"))
    say = str(sh.get("say") or "").strip()
    if say:
        longest = max(_say_parts(say), key=len)
        out.append(((15, max(15, d - 10)), _sub_box(longest, W, H), "the subtitle", _sub_box(longest, W, H, top=True)))
    return out


SUBJECT_WEIGHT = 8      # covering what the shot is ABOUT (its macro, ring, count, callout label) costs this much more than
                        # covering any other line of the page's text


def _callout_on_frame(sh, x, lx, ly, w, h, at, until, aspect):
    """Where Layers.tsx Callout really puts its label (page px): on the side it fits on the frame at the frames it
    lands (mirrored round its point if not), slid in if neither fits, then clamped top and bottom — the same rules,
    from the camera's keys. Returns (lx, ly, label to the right of lx)."""
    W, H = ASPECTS.get(aspect, ASPECTS["16:9"])
    keys = [_contained(sh, k, aspect) for k in sh.get("keys") or []]
    land, later = at + 16, min(until, at + 46)

    def scr(f, px, py):
        pose = _pose_at(keys, f)
        if not pose:
            return None
        cx, cy, z, _ = pose
        eff = z * W / 1920.0
        return W / 2 + (px - cx) * eff, H / 2 + (py - cy) * eff, eff

    def fits(lxx, side):
        for f in (land, later):
            p = scr(f, lxx, ly)
            if p is None:
                return True
            x0 = p[0] if side else p[0] - w * p[2]
            x1 = p[0] + w * p[2] if side else p[0]
            if not (x0 >= 24 and x1 <= W - 24):
                return False
        return True
    right = lx >= x
    if not fits(lx, right):
        mirror = x - (lx - x)
        if fits(mirror, not right):
            lx, right = mirror, not right
        else:
            p = scr(land, lx, ly)
            if p:
                over = (p[0] + w * p[2] - (W - 24)) if right else (24 - (p[0] - w * p[2]))
                if over > 0:
                    lx += (-1 if right else 1) * over / p[2]
    p = scr(land, lx, ly)
    if p:
        top, bot = p[1] - h * p[2] / 2, p[1] + h * p[2] / 2
        if top < 24:
            ly += (24 - top) / p[2]
        if bot > H - 24:
            ly -= (bot - (H - 24)) / p[2]
    return lx, ly, right


def _obstacles(film_dir, sh, aspect="16:9"):
    """[(box {x,y,w,h} in page px, weight, label, from frame, until frame)]: the page's own text (from the capture's
    layout) and the shot's SUBJECT — the boxes its acts are about and the labels its callouts and notes draw (sized
    as Layers.tsx sizes them, in page px: they scale with the camera)."""
    out = []
    if sh.get("kind") != "page" or not sh.get("src"):
        return out
    lp = os.path.join(film_dir, os.path.splitext(sh["src"])[0] + ".layout.json")
    try:
        for e in json.load(open(lp, encoding="utf-8")).get("elements") or []:
            # a LINE of text, not a container whose text is all its children's (a whole settings panel): which of its
            # lines sits under the band is unknown, and its area outweighed the hero number on the Squoosh film
            if str(e.get("text") or "").strip() and e.get("h", 0) <= 64:
                out.append((e, 1.0, e["text"][:30].replace("\n", " "), 0, 1e9))
    except (OSError, ValueError):
        pass
    em = lambda t: sum(1.0 if ord(ch) > 0x2E7F else 0.56 for ch in t)  # noqa: E731
    for l in sh.get("layers") or sh.get("acts") or []:
        k = l.get("kind")
        at, until = float(l.get("at", 0)), float(l.get("until", 1e9))
        # the acts that put TYPE or a mark on the page (a macro, a focus, a lift are areas — the close-up's whole
        # region — and covering part of an area is not covering a line of type)
        if k in ("ring", "count", "pop", "type", "write") and isinstance(l.get("box"), dict):
            out.append((l["box"], SUBJECT_WEIGHT, "its %s" % k, at, until))
        elif k in ("callout", "note") and l.get("text"):
            size = float(l.get("size", 30))
            txt, kick = str(l["text"]).replace("*", ""), str(l.get("kicker") or "")
            w = max(em(txt) * size, em(kick) * size * 0.42 * 1.25 if kick else 0) + 34
            h = size * 1.25 + (size * 0.42 + 4 if kick else 0) + 20
            lx, ly = float(l.get("lx", l.get("x", 0))), float(l.get("ly", l.get("y", 0)))
            lx, ly, right = _callout_on_frame(sh, float(l.get("x", lx)), lx, ly, w, h, at, until, aspect)
            x0 = lx if right else lx - w
            out.append(({"x": x0, "y": ly - h / 2, "w": w, "h": h}, SUBJECT_WEIGHT, "its %s %r" % (k, txt[:24]), at, until))
    return out


def _exact_frames(sh, f0, f1, aspect="16:9"):
    """The frames of [f0, f1] where the camera's pose is KNOWN exactly: its keys (the eased path passes through them)
    and the holds before the first and after the last. Between keys the path eases (landing curves), so a straight
    interpolation put the page where it never is — measured, it flagged a caption on a 9:16 film whose subject was
    half a frame away. A span that lies wholly inside a move is not judged."""
    ks = sorted(sh.get("keys") or [], key=lambda k: k["f"])
    if not ks:
        return []
    out = {k["f"] for k in ks if f0 <= k["f"] <= f1}
    def hold(a, b):                                       # every frame of a hold is exact: sampled every 8, so an
        a, b = max(f0, a), min(f1, b)                     # act that shows for a second inside it is seen
        return set(range(int(a), int(b) + 1, 8)) | {int(b)} if a <= b else set()
    if f1 >= ks[-1]["f"]:
        out |= hold(ks[-1]["f"], f1)
    if f0 <= ks[0]["f"]:
        out |= hold(f0, ks[0]["f"])
    for k0, k1 in zip(ks, ks[1:]):                       # a hold between two equal keys
        if all(abs(k0.get(q, 0) - k1.get(q, 0)) < 1e-6 for q in ("cx", "cy", "zoom", "rx", "ry", "rz")):
            out |= hold(k0["f"], k1["f"])
    return sorted(f for f in out if f0 <= f <= f1)


def _contained(sh, k, aspect):
    """A straight key as PageCam frames it: pulled in so the view stays on the page (containment, on by default)."""
    if sh.get("contain", True) is False or abs(k.get("rx", 0)) + abs(k.get("ry", 0)) + abs(k.get("rz", 0)) >= 2:
        return k
    w, h = sh.get("w"), sh.get("h")
    if not (w and h):
        return k
    return key(k["f"], k["cx"], k["cy"], k.get("zoom", 1.0), w, h, aspect)


def _band_score(sh, obs, box, frames, W, H):
    """(cost, [labels met on 2+ of the frames]) of type in `box` over the shot's frames: the overlapped area of each
    obstacle, in frame px, times its weight, averaged over the frames."""
    bx0, by0, bx1, by1 = box
    total, seen = 0.0, {}
    n = 0
    aspect = next((a for a, wh in ASPECTS.items() if wh == (W, H)), "16:9")
    keys = [_contained(sh, k, aspect) for k in sh.get("keys") or []]
    for f in frames:
        pose = _pose_at(keys, f)
        if not pose or pose[3]:
            continue
        n += 1
        cx, cy, z, _ = pose
        eff = z * W / 1920.0
        for (e, wt, lab, t0, t1) in obs:
            if not (t0 <= f <= t1):
                continue
            x0, y0 = W / 2 + (e["x"] - cx) * eff, H / 2 + (e["y"] - cy) * eff
            x1, y1 = x0 + e["w"] * eff, y0 + e["h"] * eff
            ix = min(x1, bx1 + 6) - max(x0, bx0 - 6)
            iy = min(y1, by1 + 6) - max(y0, by0 - 6)
            if ix > 0 and iy > 0 and x1 > 0 and x0 < W and y1 > 0 and y0 < H:
                total += ix * iy * wt
                seen[lab] = seen.get(lab, 0) + 1
    need = 2 if n >= 2 else 1
    return (total / max(1, n), [lab for lab, c in seen.items() if c >= need])


def _sub_choice(sh, obs, text, frames, W, H):
    """Where the voice's subtitle goes on this shot: low unless the low band covers type and the top covers clearly
    less (half the cost or under). Returns (pos, labels it still covers there)."""
    lo = _band_score(sh, obs, _sub_box(text, W, H), frames, W, H)
    if lo[0] <= 0 or not lo[1]:
        return "bottom", lo[1]
    hi = _band_score(sh, obs, _sub_box(text, W, H, top=True), frames, W, H)
    return ("top", hi[1]) if hi[0] <= lo[0] * 0.5 else ("bottom", lo[1])


def caption_overlaps(spec, film_dir):
    """Advise when a caption or the voice's subtitle lands on type: the page's OWN text (read from the capture's
    layout, placed by the camera at that frame) or the shot's subject and its callout labels. Two lines of type on
    each other read as neither (the Carbon run's caption sat in the page's footer links; the narrated Squoosh film's
    subtitle covered its hero "↓69 %"). A subtitle is judged where place_subtitles will put it. Straight-on keys only."""
    adv = []
    W, H = ASPECTS.get(spec.get("aspect", "16:9"), ASPECTS["16:9"])
    for i, sh in enumerate(spec.get("shots") or []):
        aspect = spec.get("aspect", "16:9")
        obs = _obstacles(film_dir, sh, aspect)
        if not obs:
            continue
        for (f0, f1), box, what, alt in _caption_boxes(sh, W, H):
            frames = _exact_frames(sh, f0, f1, aspect)
            if not frames:
                continue
            if alt is None:                                   # an authored corner: judged where it was put
                near = _band_score(sh, obs, box, frames, W, H)[1]
                where = "its corner (%s)" % (sh.get("caption") or {}).get("pos", "bl")
            elif alt == "caption":                            # no corner given: judged where place_captions puts it
                pos = _cap_choice(sh, obs, frames, W, H)
                near = _band_score(sh, obs, _cap_box(sh["caption"]["text"], pos, W, H), frames, W, H)[1]
                where = "the %s corner, where it goes (set caption.pos: bl, br, tl or tr)" % pos
            else:
                longest = max(_say_parts(str(sh.get("say"))), key=len)
                pos, near = _sub_choice(sh, obs, longest, frames, W, H)
                where = "the %s band, where it goes" % pos
            if near:
                adv.append("shot %d (page): %s covers %s in %s — aim the camera (the key's cy) so it sits clear, or move "
                           "the caption" % (i, what, ", ".join(repr(t) if not t.startswith("its ") else t for t in near[:3]), where))
    return adv


def _cap_choice(sh, obs, frames, W, H):
    """The caption's corner: bottom-left, unless it covers type there and another corner covers clearly less."""
    text = sh["caption"]["text"]
    base = _band_score(sh, obs, _cap_box(text, "bl", W, H), frames, W, H)
    if base[0] <= 0 or not base[1]:
        return "bl"
    best = min(CAPTION_CORNERS[1:], key=lambda c: _band_score(sh, obs, _cap_box(text, c, W, H), frames, W, H)[0])
    return best if _band_score(sh, obs, _cap_box(text, best, W, H), frames, W, H)[0] <= base[0] * 0.5 else "bl"


def place_captions(film_dir, spec):
    """A page shot's caption with no `pos` goes in the corner that does not cover type (bottom-left first): the
    Carbon run's caption sat in the page's footer links, and the advisory's "move the caption" had no field to do it."""
    out = json.loads(json.dumps(spec))
    W, H = ASPECTS.get(out.get("aspect", "16:9"), ASPECTS["16:9"])
    for sh in out.get("shots") or []:
        cap = sh.get("caption") or {}
        if sh.get("kind") != "page" or not cap.get("text") or cap.get("pos"):
            continue
        obs = _obstacles(film_dir, sh, out.get("aspect", "16:9"))
        at = int(cap.get("at", 8))
        span_ = int(cap.get("dur", max(20, int(sh["dur"]) - at - 6)))
        frames = _exact_frames(sh, at + 10, at + span_ - 8, out.get("aspect", "16:9"))
        if obs and frames:
            pos = _cap_choice(sh, obs, frames, W, H)
            if pos != "bl":
                cap["pos"] = pos
    return out


def place_subtitles(film_dir, spec):
    """Each subtitle sits LOW, unless on its shot the low band covers type — the page's own, or the shot's subject —
    and the top covers clearly less: then it is drawn at the top (`pos: "top"`). Measured on the narrated Squoosh
    film: the low subtitle covered the hero "↓69 %" and the photo sizes under the thumbnails."""
    out = json.loads(json.dumps(spec))
    W, H = ASPECTS.get(out.get("aspect", "16:9"), ASPECTS["16:9"])
    st, _ = starts(out)
    for sub in out.get("subtitles") or []:
        i = max([k for k, a in enumerate(st) if a <= sub["from"]] or [0])
        sh = out["shots"][i]
        obs = _obstacles(film_dir, sh, out.get("aspect", "16:9"))
        if not obs:
            continue
        f0, f1 = sub["from"] - st[i], min(int(sh["dur"]), sub["to"] - st[i])
        frames = _exact_frames(sh, max(0, f0 + 2), max(0, f1 - 2), out.get("aspect", "16:9"))
        if not frames:
            continue
        if _sub_choice(sh, obs, sub["text"], frames, W, H)[0] == "top":
            sub["pos"] = "top"
    return out


def check(spec, film_dir):
    """Errors (list) and advisories (list) for a promo table. Errors stop the render."""
    errs, adv = [], []
    if spec.get("aspect", "16:9") not in ASPECTS:
        errs.append("aspect %r is not one of %s" % (spec.get("aspect"), ", ".join(ASPECTS)))
    frame_w = ASPECTS.get(spec.get("aspect", "16:9"), ASPECTS["16:9"])[0]
    shots = spec.get("shots")
    if not isinstance(shots, list) or not shots:
        return ["spec has no shots"], adv
    sizes = {}

    def cap(src, where):
        p = os.path.join(film_dir, src)
        if not os.path.isfile(p):
            errs.append("%s: %s does not exist in the film dir" % (where, src))
            return None
        if src not in sizes and src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            sizes[src] = _png_size(p)
        return sizes.get(src)

    def inside(box, w, h, where):
        if not isinstance(box, dict):
            errs.append("%s: a box is {\"x\": .., \"y\": .., \"w\": .., \"h\": ..} in the capture's CSS px, not %r" % (where, box))
            return
        if not all(k in box for k in ("x", "y", "w", "h")):
            errs.append("%s: box needs x, y, w, h" % where)
            return
        if box["w"] <= 0 or box["h"] <= 0 or box["x"] < 0 or box["y"] < 0 or box["x"] + box["w"] > w + 1 or box["y"] + box["h"] > h + 1:
            errs.append("%s: box %s is outside its %dx%d capture" % (where, box, w, h))

    for i, s in enumerate(shots):
        where = "shot %d (%s)" % (i, s.get("kind"))         # numbered from 0, as the table, the glide report and the sheet
        d = s.get("dur")
        if not isinstance(d, (int, float)) or d <= 0:
            errs.append("%s: dur must be a positive number of frames" % where)
            continue
        k = s.get("kind")
        if k == "page" and s.get("recording"):
            rp = os.path.join(film_dir, s["recording"])
            if not os.path.isfile(rp):
                errs.append("%s: recording %s does not exist" % (where, s["recording"]))
            else:
                L = json.load(open(rp, encoding="utf-8"))
                if not os.path.isfile(os.path.join(film_dir, L.get("video", ""))):
                    errs.append("%s: the recording's video %s is missing" % (where, L.get("video")))
                # the recording plays at its own rate: its length in FILM frames is its frames x FPS / its fps
                rec_len = int(L.get("frames", 0) * FPS / float(L.get("fps", FPS) or FPS))
                if int(s.get("videoStart", 0)) + d > rec_len:
                    adv.append("%s: the recording lasts %d film frames (%d at %s fps); from videoStart %d the shot's %d frames "
                               "run past it (its last frame holds after)" % (where, rec_len, L.get("frames", 0), L.get("fps", FPS),
                                                                          int(s.get("videoStart", 0)), d))
                s = dict(s, src=L["src"], w=L["w"], h=L["h"])
        if k == "title":
            if not (TITLE_BAND[0] <= d <= TITLE_BAND[1]):
                adv.append("%s: a title card of %d frames (band %d-%d)" % (where, d, *TITLE_BAND))
            if not str(s.get("text", "")).strip():
                errs.append("%s: no text" % where)
        elif k == "page":
            sz = cap(s.get("src", ""), where)
            w, h = s.get("w"), s.get("h")
            if sz and (abs(sz[0] / 2 - w) > 2 or abs(sz[1] / 2 - h) > 2):
                errs.append("%s: w/h %sx%s is not the capture's CSS size %dx%d (a 2x capture is shown at half its pixels)" % (where, w, h, sz[0] // 2, sz[1] // 2))
            if not (SHOT_BAND[0] <= d <= SHOT_BAND[1]):
                adv.append("%s: %d frames (product shots run %d-%d)" % (where, d, *SHOT_BAND))
            keys = s.get("keys") or []
            if not keys:
                errs.append("%s: no camera keys" % where)
            last = -1
            mz = s.get("maxZoom", MAX_ZOOM)
            for kk in keys:
                if kk.get("f", -1) < last:
                    errs.append("%s: camera keys out of order at f=%s" % (where, kk.get("f")))
                last = kk.get("f", last)
                eff = kk.get("zoom", 1) * frame_w / 1920.0       # zoom is authored at a 1920-wide reference
                # past the page's density only onto a MACRO (a 4x capture of the element the close-up looks at)
                macro_ok = any(m.get("kind") == "macro" and eff <= float(m.get("scale", 4)) + 1e-6
                               and m["box"]["x"] <= kk.get("cx", -1) <= m["box"]["x"] + m["box"]["w"]
                               and m["box"]["y"] <= kk.get("cy", -1) <= m["box"]["y"] + m["box"]["h"]
                               for m in (s.get("layers") or s.get("acts") or []) if isinstance(m.get("box"), dict))
                if eff > mz + 1e-6 and not macro_ok:
                    errs.append("%s: key f=%s zoom %.2f is %.2f screen px per CSS px on this %dpx-wide frame, past the capture's density %.1f "
                                "(the texture would be upsampled; a close-up past it needs a `macro` act — a 4x capture of the element at (cx, cy))"
                                % (where, kk.get("f"), kk["zoom"], eff, frame_w, mz))
                frame_h = ASPECTS.get(spec.get("aspect", "16:9"), ASPECTS["16:9"])[1]
                tilt = abs(kk.get("rx", 0)) + abs(kk.get("ry", 0)) + abs(kk.get("rz", 0))
                if w and h and eff > 0 and tilt < 2 and s.get("contain", True) is not False:
                    vw, vh = frame_w / eff, frame_h / eff
                    if (vw < w and (kk.get("cx", 0) - vw / 2 < -1 or kk.get("cx", 0) + vw / 2 > w + 1)) or \
                       (vh < h and (kk.get("cy", 0) - vh / 2 < -1 or kk.get("cy", 0) + vh / 2 > h + 1)):
                        adv.append("%s: key f=%s frames past the page's edge — containment will pull the view in (aim the "
                                   "key inside, or set contain: false for a deliberate edge)" % (where, kk.get("f")))
                if w and h and not (0 <= kk.get("cx", 0) <= w and 0 <= kk.get("cy", 0) <= h):
                    errs.append("%s: key f=%s aims off the capture (%s, %s)" % (where, kk.get("f"), kk.get("cx"), kk.get("cy")))
            for j, l in enumerate(s.get("layers") or s.get("acts") or [], 1):
                lw = "%s layer %d (%s)" % (where, j, l.get("kind"))
                if l.get("kind") not in ("pop", "lift", "focus", "ring", "type", "cursor", "callout", "note", "macro", "deal", "write", "count"):
                    errs.append("%s: unknown layer kind" % lw)
                if l.get("kind") == "macro":
                    msz = cap(l.get("src", ""), lw)
                    b, sc = l.get("box") or {}, float(l.get("scale", 4))
                    if msz and isinstance(b, dict) and b and (abs(msz[0] - b.get("w", 0) * sc) > 3 or abs(msz[1] - b.get("h", 0) * sc) > 3):
                        errs.append("%s: %s is %dx%d px, not its box %sx%s at %gx — it would be stretched"
                                    % (lw, l.get("src"), msz[0], msz[1], b.get("w"), b.get("h"), sc))
                if l.get("kind") in ("pop", "lift", "focus", "ring", "type", "macro", "write", "count"):
                    inside(l.get("box", {}), w, h, lw)
                for bj, bb in enumerate(l.get("boxes") or []):
                    inside(bb, w, h, "%s box %d" % (lw, bj + 1))
                if l.get("kind") == "pop" and l.get("src") and l.get("src") != s.get("src") and isinstance(l.get("box"), dict) \
                        and isinstance(l.get("srcBox") or {}, dict):
                    osz = cap(l["src"], lw)
                    if osz:
                        sb = dict(l.get("srcBox") or l["box"])
                        sb["w"], sb["h"] = l["box"]["w"], l["box"]["h"]
                        inside(sb, osz[0] / 2, osz[1] / 2, lw + " srcBox")
                at = l.get("at", (l.get("path") or [{}])[0].get("f", 0))
                if isinstance(at, (int, float)) and at >= d:
                    adv.append("%s: starts at %s, after the shot ends (%d)" % (lw, at, d))
        elif k in ("brand", "outro"):
            cap(s.get("mark", ""), where)
            y = mark_luminance(os.path.join(film_dir, s.get("mark", ""))) if s.get("mark") else None
            if y is not None and y > 0.75 and _contrast(derive_look(spec.get("look"))["paper"], "#000000") >= 7:
                adv.append("%s: the mark is light (a white cut from a coloured header?) on this LIGHT film: it will "
                           "barely show — use `look.mode: dark`, or cut a dark version of the mark" % where)
            for j in s.get("recall") or []:
                if not (isinstance(j, int) and 0 <= j < len(shots) and shots[j].get("kind") == "page"):
                    errs.append("%s: recall %r is not the index of a page shot (0-based)" % (where, j))
            if k == "outro" and s.get("world") not in (None, "glow", "paper", "pastel"):
                errs.append("%s: world must be glow, paper or pastel (a staged outro: the film's objects gather round the mark)" % where)
            if k == "outro" and not s.get("world") and s.get("recall") != [] and not any(x.get("kind") == "page" for x in shots):
                errs.append("%s: the outro recalls the film's page shots and there are none (a staged film: `recall: []`)" % where)
        elif k == "statement":
            if not str(s.get("text", "")).strip():
                errs.append("%s: no text" % where)
            if s.get("ground") not in (None, "paper", "accent", "ink"):
                errs.append("%s: ground must be paper, accent or ink" % where)
        elif k in ("object", "wall"):
            fwh = ASPECTS.get(spec.get("aspect", "16:9"), ASPECTS["16:9"])
            things = s.get("items") if k == "object" else s.get("tiles")
            if not isinstance(things, list) or not things:
                errs.append("%s: needs %s (components: promo_capture --parts, or a recording cropped to one)" % (where, "items" if k == "object" else "tiles"))
                things = []
            if s.get("world") not in (None, "glow", "paper", "pastel"):
                errs.append("%s: world must be glow, paper or pastel" % where)
            lab = s.get("label")
            if lab is not None and not (isinstance(lab, dict) and str(lab.get("text") or "").strip()):
                errs.append("%s: a label needs its text (the claim; `\\n` between its two lines)" % where)
            items = [t for t in things if isinstance(t, dict)]
            # any item may carry the demonstration (Squoosh: the count runs on the bubble in front of the settings card)
            if k == "object" and lab is not None and items and not any(t.get("acts") or t.get("video") for t in items):
                adv.append("%s: the label claims a feature and its cards only sit there (no acts, no recording): the "
                           "claim is told, not shown. Act it out on the card — `focus` the part the claim names, `ring`/`lift` "
                           "its rows one by one, `count` its figure — or crop a recording of it (references/promo-film.md "
                           "§ Staging, 'Show the claim')" % where)
            if any(a.get("kind") == "lift" for t in items for a in (t.get("acts") or []) if isinstance(a, dict)):
                adv.append("%s: a `lift` on a staged card: its settle creeps under a pixel a frame on the tilted plane "
                           "(regex101, z 30: 11 %% shimmer, glide gate FAIL) — step a `ring` (or `focus`) instead" % where)
            for j, it in enumerate(t for t in things if isinstance(t, dict)):
                iw = "%s %s %d" % (where, "item" if k == "object" else "tile", j)
                if not (isinstance(it.get("w"), (int, float)) and isinstance(it.get("h"), (int, float)) and it["w"] > 0 and it["h"] > 0):
                    errs.append("%s: w and h (the component's CSS size, from its part) are needed" % iw)
                    continue
                # on screen: an object's width share of the frame; a tile's plane size (near tiles magnified ~1.3x)
                if k == "object":
                    shown = float(it.get("width", 0.5 if (lab and j == 0) else 0.6)) * fwh[0]
                else:
                    shown = float(s.get("tile", 560)) * (min(fwh) / 1080.0) * 1.3
                if it.get("video"):
                    if not os.path.isfile(os.path.join(film_dir, it["video"])):
                        errs.append("%s: video %s does not exist" % (iw, it["video"]))
                    cb = it.get("crop")
                    if not (isinstance(cb, dict) and all(q in cb for q in "xywh")):
                        errs.append("%s: a video item needs `crop` {x, y, w, h}: the component's box in the recording" % iw)
                    elif shown > cb["w"] * float(it.get("vscale", 2)) + 1:
                        vs = float(it.get("vscale", 2))
                        errs.append("%s: the recording is %gx: a %d px crop shown %d px wide is upsampled (crop at least %d px, "
                                    "record it with --scale=3 and set vscale, or show it smaller)" % (iw, vs, cb["w"], shown, int(shown / vs) + 1))
                else:
                    psz = cap(it.get("src", ""), iw)
                    if psz and shown > psz[0] + 1:
                        errs.append("%s: %s is %d px wide and would be shown %d px wide (upsampled, soft): capture it with "
                                    "--parts (4x), or show it smaller" % (iw, it.get("src"), psz[0], shown))
                    ink = ink_density(os.path.join(film_dir, it.get("src", ""))) if psz else None
                    if ink is not None and ink < INK_MIN:
                        adv.append("%s: %s is nearly blank (%.1f%% of it differs from its own ground; a component reads from "
                                   "%.0f%%): it shows as an empty card, so crop the part of the page where the content is"
                                   % (iw, it.get("src"), ink * 100, INK_MIN * 100))
        elif k in ("compare", "montage"):
            regions = [s.get("a"), s.get("b")] if k == "compare" else list(s.get("items") or [])
            if not regions or any(not isinstance(r, dict) for r in regions):
                errs.append("%s: needs %s" % (where, "a and b regions" if k == "compare" else "items (regions)"))
            fwh = ASPECTS.get(spec.get("aspect", "16:9"), ASPECTS["16:9"])
            fw, fh = (fwh[0] * 0.84, fwh[1] * 0.74) if k == "compare" else \
                ((fwh[0], fwh[1]) if s.get("full") else (fwh[0] * 0.8, fwh[1] * 0.74))   # = Shots.tsx Compare / Montage
            for j, r in enumerate(r for r in regions if isinstance(r, dict)):
                rsz = cap(r.get("src", ""), "%s region %d" % (where, j))
                if rsz:
                    inside(r.get("box", {}), rsz[0] / 2, rsz[1] / 2, "%s region %d" % (where, j))
                    b = r.get("box") if isinstance(r.get("box"), dict) else {}
                    if b.get("w", 0) > 0 and b.get("h", 0) > 0:
                        # a region is drawn to fit its frame box: past the capture's density it is upsampled (soft)
                        dens = rsz[0] / float(r.get("w") or rsz[0] / 2)        # the capture's px per CSS px (2, or 4)
                        kk = min(fw / b["w"], fh / b["h"])
                        if kk > dens + 1e-6:
                            errs.append("%s region %d: a %dx%d CSS px region is drawn at %.2f screen px per CSS px, past the "
                                        "capture's %gx (it would be upsampled): take a region at least %d px wide or %d tall"
                                        % (where, j, b["w"], b["h"], kk, dens, int(fw / dens) + 1, int(fh / dens) + 1))
        else:
            errs.append("%s: unknown kind" % where)
        if s.get("cut") not in (None, "carry", "flash", "hard", "through", "morph"):
            errs.append("%s: cut must be carry, flash, hard, through or morph" % where)
        if s.get("cut") == "morph" or (s.get("cut") is None and spec.get("cut") == "morph"):
            if i == 0 and s.get("cut") == "morph":
                errs.append("%s: a morph grows out of the shot before it, and the first shot has none" % where)
            mf = s.get("morphFrom")
            if mf is not None and not (isinstance(mf, dict) and all(isinstance(mf.get(q), (int, float)) for q in "xywh")
                                       and mf["x"] >= 0 and mf["y"] >= 0 and mf["w"] > 0 and mf["h"] > 0
                                       and mf["x"] + mf["w"] <= 1.001 and mf["y"] + mf["h"] <= 1.001):
                errs.append("%s: morphFrom is a box in FRACTIONS of the frame {x, y, w, h}, inside 0..1" % where)
        for j, l in enumerate(s.get("layers") or s.get("acts") or [], 1):
            if l.get("kind") == "count" and not isinstance(l.get("to"), (int, float)):
                errs.append("%s layer %d (count): `to` must be the number the figure lands on (the page's own)" % (where, j))
        if s.get("say") is not None and not str(s.get("say")).strip():
            errs.append("%s: an empty `say`" % where)
    if spec.get("cut") not in (None, "carry", "flash", "hard", "through", "morph"):
        errs.append("cut must be carry, flash, hard, through or morph")
    adv += skeleton_advice(spec, film_dir)
    try:
        adv += caption_overlaps(resolve_recordings(film_dir, spec) if errs == [] else spec, film_dir)
    except Exception as e:  # noqa: BLE001 — an advisory pass never breaks the check; said, not swallowed
        adv.append("the caption-overlap pass could not run: %s" % e)
    look = derive_look(spec.get("look"))
    for key in ("accent", "accentInk"):
        v = look.get(key)
        if v is not None and not (isinstance(v, str) and len(v) == 7 and v.startswith("#")):
            errs.append("look.%s must be #rrggbb" % key)
    if look.get("accentInk") and look.get("paper"):
        r = _contrast(look["accentInk"], look["paper"])
        if r < 4.5:
            errs.append("look.accentInk %s on paper %s is %.2f:1 (type needs 4.5:1)" % (look["accentInk"], look["paper"], r))
    return errs, adv


def _contrast(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _mix(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(pa, pb))


def derive_look(look):
    """The film's ONE look from as little as its accent: `{accent, mode: light|dark}`. Fields given are kept; the
    rest are derived — a near-neutral ground and paper tinted 3-5 % toward the accent, ink and muted ink, and
    `accentInk`, the accent walked toward the ink until it reads at 4.5:1 on the paper (type in the accent stays
    legible on any brand colour)."""
    look = dict(look or {})
    acc = look.get("accent", "#3a7bd5")
    dark = look.get("mode") == "dark" or (look.get("paper") and _contrast(look["paper"], "#000000") < 7)
    if dark:
        base = {"ground": _mix("#121215", acc, 0.06), "groundEdge": _mix("#2a2a30", acc, 0.1), "paper": _mix("#0d0d10", acc, 0.05),
                "ink": "#f3f2ee", "muted": "#9c9a94"}
    else:
        base = {"ground": _mix("#ecebe7", acc, 0.04), "groundEdge": _mix("#d8d6cf", acc, 0.06), "paper": _mix("#f6f5f2", acc, 0.03),
                "ink": "#151513", "muted": "#67655f"}
    for k, v in base.items():
        look.setdefault(k, v)
    look.setdefault("accent", acc)
    if "accentInk" not in look:
        ink = acc
        for i in range(41):
            ink = _mix(acc, look["ink"], i / 40)
            if _contrast(ink, look["paper"]) >= 4.6:
                break
        look["accentInk"] = ink
    look.pop("mode", None)
    return look


LEDGER = os.environ.get("TOPIC_TO_VIDEO_PROMO_LEDGER") or os.path.expanduser("~/.topic-to-video/promo_skeletons.json")


def skeleton(spec):
    """The film's STRUCTURE as a word: one letter per shot kind (+ narrated or not), cuts ignored. Two films with the
    same skeleton are the same film with different pictures — the template feel the user named on Squoosh vs WorkBuddy."""
    letter = {"brand": "B", "title": "C", "page": "P", "outro": "O", "statement": "S", "compare": "V", "montage": "M", "object": "X",
              "wall": "W"}
    return "".join(letter.get(sh.get("kind"), "?") for sh in spec.get("shots") or []) + ("+vo" if narrated(spec) else "")


def skeleton_advice(spec, film_dir):
    """Advise when this film's structure repeats another film's (ledger outside the repo, one row per film folder)."""
    import difflib
    me = skeleton(spec)
    try:
        led = json.load(open(LEDGER, encoding="utf-8"))
    except (OSError, ValueError):
        led = {}
    out = []
    for other, sk in led.items():
        if os.path.abspath(other) == os.path.abspath(film_dir):
            continue
        r = difflib.SequenceMatcher(None, me, sk).ratio()
        if r >= 0.8:
            out.append("structure %s repeats %s (%s, %.0f %% alike) — design this film's own arc (references/promo-film.md "
                       "§design): its hook, its proof, its payoff come from THIS product" % (me, os.path.basename(other.rstrip("/")), sk, r * 100))
    return out


def record_skeleton(spec, film_dir):
    try:
        led = json.load(open(LEDGER, encoding="utf-8"))
    except (OSError, ValueError):
        led = {}
    led[os.path.abspath(film_dir)] = skeleton(spec)
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(led, open(LEDGER, "w", encoding="utf-8"), indent=1)


def narrated(spec):
    """A film is narrated when it says so, or (no `narrate`) when any shot carries a line to `say`. Whether a film
    SHOULD speak is the director's call per film: a how-it-works story speaks, a mood or brand piece does not."""
    n = spec.get("narrate")
    return bool(n) if n is not None else any(str(sh.get("say") or "").strip() for sh in spec.get("shots") or [])


# where a voice line is cut into subtitle pieces: after a sentence end (a CJK one needs no space after it), or after a
# comma when a long clause follows
SPLIT_RE = r"(?<=[.!?])\s+|(?<=[。！？])\s*|(?<=[,;])\s+(?=\S{12,})|(?<=[，；])\s*(?=[^，；。！？]{12,})"
VO_LEAD, VO_TAIL = 0.3, 0.45      # s: a line starts a breath into its shot and ends a breath before the cut


def voice_pass(film_dir, spec):
    """Voice every `say` (edge-tts), lengthen each shot to hold its line, and time the subtitles from the voice's own
    word boundaries. Returns (resolved spec, [(start_s, mp3)]). Cached by text + voice."""
    import hashlib
    import math
    if not narrated(spec):
        return spec, []
    import tts
    voice = spec.get("voice") or "en-US-AndrewNeural"
    voice = voice.split(":", 1)[1] if voice.startswith("edge:") else voice
    rate = spec.get("voice_rate", "+0%")
    adir = os.path.join(film_dir, "audio")
    os.makedirs(adir, exist_ok=True)
    out = json.loads(json.dumps(spec))
    clips, subs, t = [], [], 0
    for i, sh in enumerate(out["shots"]):
        line = str(sh.get("say") or "").strip()
        d = int(round(sh["dur"]))
        if line:
            h = hashlib.sha1(("%s|%s|%s" % (voice, rate, line)).encode("utf-8")).hexdigest()[:12]
            mp3 = os.path.join(adir, "say_%02d_%s.mp3" % (i, h))
            off = os.path.join(adir, "say_%02d_%s.say.wav" % (i, h))
            if not os.path.isfile(mp3) and os.path.isfile(off):
                mp3 = off
            elif not os.path.isfile(mp3):
                try:
                    tts._edge(line, mp3, voice, rate)
                    if not (os.path.isfile(mp3) and os.path.getsize(mp3) > 0):
                        raise RuntimeError("edge-tts wrote nothing")
                except (Exception, SystemExit) as e:  # noqa: BLE001 — offline / blocked: the OFFLINE voice, said aloud
                    if os.path.isfile(mp3):
                        os.remove(mp3)
                    lang = (spec.get("language") or voice.split("-")[0] or "en").split("-")[0].lower()
                    sv = tts._resolve_say_voice("Samantha", lang)[0]          # (voice, note)
                    if not shutil.which("say"):
                        raise SystemExit("[promo_film] edge-tts failed (%s) and there is no offline `say` voice on this "
                                         "machine: the film cannot speak — set narrate: false, or run with network" % e)
                    print("[promo_film] edge-tts failed (%s): line %d voiced OFFLINE with macOS say (%s) — no word "
                          "timings, subtitles timed by length" % (str(e).splitlines()[0][:120] if str(e) else type(e).__name__, i, sv))
                    tts._say(line, off, sv)
                    mp3 = off
            secs = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3],
                                        capture_output=True, text=True).stdout.strip() or 0)
            need = int(math.ceil((VO_LEAD + secs + VO_TAIL) * FPS))
            if need > d:
                sh["dur"] = d = need
            st = t / FPS + VO_LEAD
            clips.append((st, mp3))
            # the frame already SAYS it (a statement or a card whose type is the line): the subtitle yields
            norm = lambda x: re.sub(r"[^\w]+", " ", str(x).replace("*", "")).strip().lower()
            if not (sh.get("kind") in ("statement", "title") and norm(sh.get("text", "")) == norm(line)):
                subs += _subtitle_chunks(line, os.path.splitext(mp3)[0] + ".words.json", st, secs)
        t += d
    out["subtitles"] = [{"from": int(round(a * FPS)), "to": int(round(b * FPS)), "text": x} for a, b, x in subs]
    return out, clips


def _subtitle_chunks(line, words_json, start_s, secs, max_chars=64):
    """The line in readable pieces (a sentence, or a clause when long), each shown from its first word to the next."""
    import re as _re
    parts = [p.strip() for p in _re.split(SPLIT_RE, line) if p.strip()]
    if not parts:
        return []
    try:
        words = json.load(open(words_json, encoding="utf-8"))
    except (OSError, ValueError):
        words = []
    out, wi = [], 0
    starts_ = []
    total = float(sum(len(p) for p in parts)) or 1.0
    for k, p in enumerate(parts):
        # no word times (a `say` voice): each piece starts at its share of the characters spoken before it
        starts_.append(words[wi]["t"] if wi < len(words) else sum(len(q) for q in parts[:k]) / total * secs)
        wi += len(p.split()) if words else 0
    for k, p in enumerate(parts):
        a = start_s + starts_[k]
        b = start_s + (starts_[k + 1] if k + 1 < len(parts) else secs) + (0.25 if k + 1 == len(parts) else 0)
        out.append((a, b, p))
    return out


def resolve_recordings(film_dir, spec):
    """A page shot naming `recording` (a promo_record layout) gets its poster, video and size from it, and — unless it
    draws its own cursor or says `cursor: false` — a cursor that does what the recording's hand did, on the same
    frames (headless Chrome records no pointer). `videoStart` picks where in the recording the shot begins."""
    out = json.loads(json.dumps(spec))
    for sh in out.get("shots") or []:
        rp = sh.get("recording")
        if sh.get("kind") != "page" or not rp:
            continue
        L = json.load(open(os.path.join(film_dir, rp), encoding="utf-8"))
        sh.setdefault("src", L["src"])
        sh["video"], sh["w"], sh["h"] = L["video"], L["w"], L["h"]
        v0 = int(sh.get("videoStart", 0))                  # in FILM frames, like everything in the table
        kf = FPS / float(L.get("fps", FPS) or FPS)         # a recording's event frames are at ITS rate
        acts = sh.setdefault("layers", sh.pop("acts", []) if "acts" in sh else [])
        # the recorded hand's events in FILM frames of this shot — the sound plan reads them (keys under typing, a
        # press and a release on a drag, air on a long scroll), whether or not a cursor is drawn
        evs, last_xy = [], (None, None)
        for e in L.get("events") or []:
            f = int(round(e["frame"] * kf)) - v0
            u = int(round(e.get("until", e["frame"]) * kf)) - v0
            if u < 0 or f > sh["dur"]:
                continue
            row = {"kind": e["kind"], "f": max(0, f), "until": min(int(sh["dur"]), max(f, u))}
            if "x" in e:
                last_xy = (e["x"], e["y"])
                row.update(x=e["x"], y=e["y"])
            if e["kind"] == "drag":
                row.update(x=e["from"][0], y=e["from"][1], x1=e["to"][0], y1=e["to"][1])
            if e["kind"] == "type":
                row.update(text=e.get("text", ""), x=last_xy[0], y=last_xy[1])
            if e["kind"] == "scroll":
                row.update(by=e.get("by", [0, 0]))
            evs.append(row)
        sh["recEvents"] = evs
        if sh.get("cursor", True) is not False and not any(a.get("kind") == "cursor" for a in acts):
            path, clicks = [], []
            for e in L.get("events") or []:
                f = int(round(e["frame"] * kf)) - v0
                if not (0 <= f <= sh["dur"]):
                    continue
                if e["kind"] in ("click", "hover"):
                    path.append({"f": max(0, f - 12), "x": e["x"] + 60, "y": e["y"] + 50, "ease": "swift"} if not path else
                                {"f": max(path[-1]["f"] + 1, f - 12), "x": e["x"], "y": e["y"], "ease": "swift"})
                    path.append({"f": max(path[-1]["f"] + 1, f), "x": e["x"], "y": e["y"], "ease": "swift"})
                    if e["kind"] == "click":
                        clicks.append(f)
                elif e["kind"] == "drag":
                    (x0, y0), (x1, y1) = e["from"], e["to"]
                    if not path:
                        path.append({"f": max(0, f - 12), "x": x0 + 60, "y": y0 + 50})
                    path.append({"f": max(path[-1]["f"] + 1, f), "x": x0, "y": y0, "ease": "swift"})
                    path.append({"f": max(path[-1]["f"] + 1, int(round(e["until"] * kf)) - v0), "x": x1, "y": y1, "ease": "smooth"})
            if path:
                acts.append({"kind": "cursor", "path": path, "clicks": clicks})
    return out


def starts(spec):
    t, out = 0, []
    for s in spec["shots"]:
        out.append(t)
        t += int(round(s["dur"]))
    return out, t


def _cam_at(keys, f):
    """The camera's (cx, zoom) at frame f of a page shot: the keys interpolated (the ease is the picture's business;
    for WHERE a sound sits the straight line between keys is within a few % of the frame)."""
    if not keys:
        return None
    ks = sorted(keys, key=lambda k: k["f"])
    if f <= ks[0]["f"]:
        return ks[0]["cx"], ks[0].get("zoom", 1.0)
    for k0, k1 in zip(ks, ks[1:]):
        if f <= k1["f"]:
            u = (f - k0["f"]) / max(1e-9, k1["f"] - k0["f"])
            return k0["cx"] + (k1["cx"] - k0["cx"]) * u, k0.get("zoom", 1.0) + (k1.get("zoom", 1.0) - k0.get("zoom", 1.0)) * u
    return ks[-1]["cx"], ks[-1].get("zoom", 1.0)


PAN_SPAN = 0.7          # the frame's edge is heard at 70 % toward that side: placed, never hard in one ear


def _pan_at(shot, f, x):
    """Where page x (CSS px) is on the frame at shot frame f, as a pan in [-PAN_SPAN, PAN_SPAN]. Zoom is authored at a
    1920-wide reference, so the frame share is the same at every aspect."""
    cam = _cam_at(shot.get("keys") or [], f)
    if cam is None or x is None:
        return 0.0
    cx, z = cam
    return max(-PAN_SPAN, min(PAN_SPAN, 2 * ((x - cx) * z / 1920.0) * PAN_SPAN))


def _box_x(l):
    b = l.get("box") or {}
    return b["x"] + b.get("w", 0) / 2 if "x" in b else None


def plan_sfx(spec, placed=False):
    """[(frame, cue, gain)] pinned to the table's actions. Restraint: a burst of pops is one sound per 3 frames,
    fading; a camera key only sounds when the camera really travels. `placed=True` adds each cue's place in the
    stereo field (stereo.place): a sound sits where its cause is on the frame, air travels the way the picture moves,
    the landing and the swell are wide."""
    cues = []
    st, _ = starts(spec)
    film_cut = spec.get("cut", "carry")
    for idx, (s, a) in enumerate(zip(spec["shots"], st)):
        k = s["kind"]
        if idx and (s.get("cut") or film_cut) in ("carry", "flash"):
            cues.append((a, "whoosh", 0.34, (-0.35, 0.35)))        # the cut carries a move: one air sound through it
        if k == "brand":
            cues += [(a + 14, "drop", 0.5, "wide"), (a + 22, "whoosh", 0.2, (0.3, -0.3))]
        elif k == "title":
            cues.append((a + 14, "select", 0.22, 0.0))              # the accent fill arrives
        elif k == "outro":
            sa = a + int(s.get("stampAt", 46))
            cues += [(a + 6, "swell", 0.4, "wide"), (sa + 10, "impact", 0.8, "wide")]
            if s.get("cta"):
                cues.append((sa + 46, "select", 0.3, 0.0))
        elif k == "object":
            lab = s.get("label")
            for j, it in enumerate(s.get("items") or []):
                at_ = int(it.get("at", 0))
                x = float(it.get("x", (0.68 if (lab or {}).get("side", "left") == "left" else 0.32) if (lab and j == 0) else 0.5))
                p_ = max(-PAN_SPAN, min(PAN_SPAN, (x - 0.5) * 2 * PAN_SPAN))
                if it.get("from", "tilt") in ("tilt", "rise"):
                    g = 1.0 if j == 0 else 0.5
                    cues.append((a + at_ + 6, "whoosh", 0.3 * g, (p_ * 0.4, p_)))         # it comes in toward its place
                    cues.append((a + at_ + 22, "drop", 0.34 * g, p_))                      # and lands there
                for l in it.get("acts") or []:
                    kind, la = l.get("kind"), int(l.get("at", 0))
                    if kind == "count":
                        cues += [(a + la + jj, "key", 0.12, p_) for jj in range(0, int(l.get("dur", 42)), 6)]
                    elif kind == "type":
                        n = len(l.get("text", ""))
                        cues += [(a + la + int(c / float(l.get("cpf", 0.5))), "key", 0.2, p_) for c in range(0, n, 2)]
                    elif kind in ("ring", "callout", "note"):
                        cues.append((a + la + 4, "select", 0.22, p_))
                    elif kind == "pop":
                        cues.append((a + la + 6, "drop", 0.26, p_))
            if lab:
                cues.append((a + int(lab.get("at", 4)) + 4, "select", 0.14, -PAN_SPAN * 0.6 if lab.get("side", "left") == "left" else PAN_SPAN * 0.6))
        elif k == "wall":
            cols = max(1, int(s.get("cols", 4)))
            cues.append((a + 10, "whoosh", 0.3, "wide"))
            for j in range(min(10, len(s.get("tiles") or []))):
                c = j % cols
                cues.append((a + int(16 + j * 1.6), "deal", max(0.1, 0.26 * (0.88 ** j)),
                             (c / max(1, cols - 1) - 0.5) * 1.2 * PAN_SPAN))
        elif k == "page":
            keys = s.get("keys") or []
            for k0, k1 in zip(keys, keys[1:]):
                travel = abs(k1["cx"] - k0["cx"]) + abs(k1["cy"] - k0["cy"]) + 400 * abs(k1.get("zoom", 1) - k0.get("zoom", 1)) \
                    + 6 * (abs(k1.get("rx", 0) - k0.get("rx", 0)) + abs(k1.get("ry", 0) - k0.get("ry", 0)))
                if travel > 120 and k1["f"] - k0["f"] <= 60:
                    # the page moves OPPOSITE to the camera: the air goes the way the picture goes, as far across as
                    # the move is sideways (a push in is heard in the middle, wide)
                    dx = (k1["cx"] - k0["cx"]) * k0.get("zoom", 1.0) / 1920.0
                    side = max(-1.0, min(1.0, -dx * 3)) * 0.5
                    how = (-side, side) if abs(side) > 0.08 else "wide"
                    cues.append((a + int((k0["f"] + k1["f"]) / 2), "whoosh", min(0.5, 0.22 + travel / 2000), how))
            cues += _recording_cues(s, a)
            last_pop, npop = -99, 0
            for l in s.get("layers") or s.get("acts") or []:
                kind = l.get("kind")
                if kind == "pop":
                    f = a + int(l["at"] + l.get("dur", 14) * 0.4)
                    if f - last_pop >= 3:
                        cues.append((f, "drop", max(0.12, 0.36 * (0.85 ** npop)), _pan_at(s, f - a, _box_x(l))))
                        last_pop, npop = f, npop + 1
                elif kind == "deal":
                    for bj, bb in enumerate(l.get("boxes") or []):
                        f = a + int(l["at"] + bj * l.get("every", 3) + l.get("dur", 18) * 0.8)
                        if f - last_pop >= 3:
                            cues.append((f, "deal", max(0.12, 0.3 * (0.88 ** bj)), _pan_at(s, f - a, bb.get("x", 0) + bb.get("w", 0) / 2)))
                            last_pop = f
                    cues.append((a + int(l["at"]) - 4, "whoosh", 0.3, "wide"))
                elif kind == "write":
                    n = max(1, round(l["box"]["h"] / l.get("lineH", 24)))
                    for li in range(0, n, 2):
                        f = a + int(l["at"] + li * l.get("every", 5))
                        cues.append((f, "key", 0.18, _pan_at(s, f - a, _box_x(l))))
                elif kind == "count":
                    for j in range(0, int(l.get("dur", 42)), 6):
                        cues.append((a + int(l["at"]) + j, "key", 0.12, _pan_at(s, int(l["at"]) + j, _box_x(l))))
                elif kind == "lift":
                    p_ = _pan_at(s, int(l["at"]) + 18, _box_x(l))
                    cues += [(a + int(l["at"]) + 6, "whoosh", 0.36, ("wide", p_)), (a + int(l["at"]) + 18, "glass", 0.22, p_),
                             (a + int(l["until"]) + 14, "drop", 0.35, _pan_at(s, int(l["until"]) + 14, _box_x(l)))]
                elif kind == "type":
                    cpf = float(l.get("cpf", 0.5))
                    n = len(l.get("text", ""))
                    for c in range(0, n, 2):
                        f = a + int(l["at"] + c / cpf)
                        cues.append((f, "key", 0.22, _pan_at(s, f - a, _box_x(l))))
                elif kind == "cursor":
                    path = sorted(l.get("path") or [], key=lambda q: q.get("f", 0))
                    for c in l.get("clicks") or []:
                        at_ = [q for q in path if q.get("f", 0) <= c]
                        cues.append((a + int(c) + 2, "click", 0.6, _pan_at(s, c, (at_[-1] if at_ else (path or [{}])[0]).get("x"))))
                elif kind == "ring":
                    cues.append((a + int(l["at"]) + 4, "select", 0.25, _pan_at(s, int(l["at"]) + 4, _box_x(l))))
                elif kind == "focus":
                    cues.append((a + int(l["at"]) + 6, "select", 0.18, _pan_at(s, int(l["at"]) + 6, _box_x(l))))
                elif kind in ("note", "callout"):
                    cues.append((a + int(l["at"]) + 4, "select", 0.24, _pan_at(s, int(l["at"]) + 4, l.get("x"))))
    cues.sort(key=lambda c: (c[0], c[1], c[2]))
    return cues if placed else [c[:3] for c in cues]


def _recording_cues(s, a):
    """The recorded hand, heard: keys under typing (one every 2 characters, as the `type` act), a press and a soft
    release on a drag, air on a long scroll, and a click on a click when no cursor act sounds it already."""
    out = []
    has_cursor = any(l.get("kind") == "cursor" for l in s.get("layers") or s.get("acts") or [])
    for e in s.get("recEvents") or []:
        f, u, k = int(e["f"]), int(e.get("until", e["f"])), e["kind"]
        if k == "type":
            n = len(e.get("text") or "")
            for c in range(0, n, 2):
                fc = f + int(round(c * (u - f) / max(1, n)))
                out.append((a + fc, "key", 0.2, _pan_at(s, fc, e.get("x"))))
        elif k == "drag":
            out.append((a + f, "click", 0.36, _pan_at(s, f, e.get("x"))))
            out.append((a + u, "key", 0.18, _pan_at(s, u, e.get("x1"))))
        elif k == "scroll" and abs((e.get("by") or [0, 0])[1]) + abs((e.get("by") or [0, 0])[0]) > 250:
            out.append((a + (f + u) // 2, "whoosh", 0.2, "wide"))
        elif k == "click" and not has_cursor:
            out.append((a + f + 2, "click", 0.6, _pan_at(s, f, e.get("x"))))
    return out


def mark_luminance(path):
    """The mean relative luminance (0..1) of a raster mark's OPAQUE pixels, or None (an SVG, no alpha, unreadable)."""
    try:
        from PIL import Image
        import numpy as np
        with Image.open(path) as im:
            if "A" not in im.getbands():
                return None
            a = np.asarray(im.convert("RGBA"), dtype=np.float64) / 255.0
    except Exception:  # noqa: BLE001 — an SVG or anything PIL cannot read keeps the default
        return None
    m = a[..., 3] > 0.5
    if m.sum() < 16:
        return None
    lin = np.where(a[..., :3] <= 0.04045, a[..., :3] / 12.92, ((a[..., :3] + 0.055) / 1.055) ** 2.4)
    y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    return float(y[m].mean())


INK_MIN = 0.04   # measured: real UI components 0.075 (a text table) .. 0.6; a mostly-blank card 0.016


def ink_density(path):
    """The share (0..1) of a component's pixels that differ from its own ground (its most common colour), or None
    when it cannot be read. A crop of the wrong part of a page — the empty bottom of an input — is near 0: on a wall or
    in the outro it reads as a blank card (the regex101 run's `tool_subst`, 1.6%)."""
    try:
        from PIL import Image
        import numpy as np
        with Image.open(path) as im:
            im = im.convert("RGBA")
            im.thumbnail((400, 400))
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            a = np.asarray(Image.alpha_composite(bg, im).convert("RGB"), dtype=np.int32)
    except Exception:  # noqa: BLE001 — unreadable: the size check names it
        return None
    if a.size == 0:
        return None
    q = (a // 16).reshape(-1, 3)
    mode = int(np.bincount(q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]).argmax())
    ground = np.array([mode // 256, (mode // 16) % 16, mode % 16]) * 16 + 8
    return float((np.abs(a - ground).max(-1) > 28).mean())


OUTRO_OBJECTS = 6


def resolve_outro_objects(film_dir, spec):
    """A staged outro's components, chosen once here (the composition used to pick them blind): the still parts of the
    film's object and wall shots, in film order, each once, leaving out a near-blank one (ink_density < INK_MIN), then
    up to six spread across the film. An authored `objects` list wins."""
    out = json.loads(json.dumps(spec))
    shots = out.get("shots") or []
    for sh in shots:
        if sh.get("kind") != "outro" or not sh.get("world") or "objects" in sh:
            continue
        seen, objs = set(), []
        for x in shots:
            for it in (x.get("items") if x.get("kind") == "object" else x.get("tiles") if x.get("kind") == "wall" else None) or []:
                src = it.get("src") if isinstance(it, dict) and not it.get("video") else None
                if not src or src in seen:
                    continue
                seen.add(src)
                ink = ink_density(os.path.join(film_dir, src))
                if ink is not None and ink < INK_MIN:
                    continue
                objs.append({"src": src, "w": it.get("w"), "h": it.get("h"), "radius": it.get("radius")})
        n = len(objs)
        sh["objects"] = objs if n <= OUTRO_OBJECTS else [objs[round(k * (n - 1) / (OUTRO_OBJECTS - 1))] for k in range(OUTRO_OBJECTS)]
    return out


def resolve_marks(film_dir, spec, look):
    """A brand/outro lockup sits on a light plate on a dark film, because a mark is usually drawn for light pages. A
    mark that is itself LIGHT (made for dark grounds) gets `plate: false` instead: on the plate it read weakly (the
    Carbon run: a yellow outline wordmark on near-white). An authored `plate` wins."""
    out = json.loads(json.dumps(spec))
    dark = _contrast(look["paper"], "#000000") < 7          # the paper is dark (the derive_look convention)
    for sh in out.get("shots") or []:
        if sh.get("kind") in ("brand", "outro") and "plate" not in sh and sh.get("mark") and dark:
            y = mark_luminance(os.path.join(film_dir, sh["mark"]))
            if y is not None and y > 0.35:
                sh["plate"] = False
    return out


def render_stills(film_dir, spec_path, frames, out_dir):
    """Every still of a `--stills` run from ONE bundle in ONE browser. Measured on the Carbon run: one `remotion still`
    per frame re-bundled the project each time, and 19 stills took ~5 min against ~2 min for the whole film's picture.
    The bundle is keyed on the film state (bundle_cache), so a stills run after a table edit reuses it too."""
    import shutil
    import tempfile
    import bundle_cache
    import remotion_segments as rs
    film_dir, spec_path = os.path.abspath(film_dir), os.path.abspath(spec_path)
    spec = json.load(open(spec_path, encoding="utf-8"))
    spec["look"] = derive_look(spec.get("look"))
    spec = resolve_marks(film_dir, spec, spec["look"])
    spec = resolve_outro_objects(film_dir, spec)
    spec = place_captions(film_dir, spec)
    pub = os.path.join(film_dir, "_promo_public")
    shutil.rmtree(pub, ignore_errors=True)
    rs.minimal_public(spec, film_dir, pub)           # the files the table names, linked: not old renders and stills
    serve = bundle_cache.bundle(pub)
    os.makedirs(out_dir, exist_ok=True)
    jobs = [{"tag": int(f), "id": "PromoFilm", "props": spec, "frame": int(f), "png": os.path.join(out_dir, "f%04d.png" % int(f))}
            for f in frames]
    tmp = tempfile.mkdtemp(prefix="promo_stills_")
    jp, op = os.path.join(tmp, "jobs.json"), os.path.join(tmp, "out.jsonl")
    json.dump(jobs, open(jp, "w"))
    r = subprocess.run(["node", os.path.join(ROOT, "scripts", "fidelity_stills.cjs"), REMOTION, serve, jp, op, "--gl=angle"],
                       capture_output=True, text=True)
    errs = []
    if os.path.isfile(op):
        for line in open(op, encoding="utf-8"):
            row = json.loads(line)
            if row.get("error"):
                errs.append("frame %s: %s" % (row["tag"], row["error"]))
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0 or errs:
        raise SystemExit("[promo_film] stills failed:\n  " + "\n  ".join(errs or [(r.stderr or r.stdout)[-2000:]]))
    return [j["png"] for j in jobs]


def render_picture(film_dir, spec_path, out, frames=None):
    # absolute paths: remotion runs from its own folder, so a relative film dir pointed it at nothing
    film_dir, spec_path, out = os.path.abspath(film_dir), os.path.abspath(spec_path), os.path.abspath(out)
    spec = json.load(open(spec_path, encoding="utf-8"))
    spec["look"] = derive_look(spec.get("look"))
    spec = resolve_marks(film_dir, spec, spec["look"])
    spec = resolve_outro_objects(film_dir, spec)
    spec = place_captions(film_dir, spec)
    props = os.path.join(film_dir, "_promo_props.json")          # the table as rendered: the derived look filled in
    json.dump(spec, open(props, "w"), indent=0)
    import shutil
    import remotion_segments as rs
    pub = os.path.join(film_dir, "_promo_public")
    shutil.rmtree(pub, ignore_errors=True)
    rs.minimal_public(spec, film_dir, pub)           # a bundle COPIES its public dir: not the film folder's old renders
    cmd = ["npx", "remotion", "render" if frames is None else "still", "src/index.ts", "PromoFilm", out,
           "--props=" + props, "--public-dir=" + pub]
    if frames is not None:
        cmd.append("--frame=%d" % frames)
    else:
        cmd += ["--codec=h264", "--crf=16", "--concurrency=6"]
    r = subprocess.run(cmd, cwd=REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("[promo_film] render failed:\n" + (r.stderr or r.stdout)[-3000:])


# RECORDED takes for the UI sounds (Kenney "Interface Sounds", CC0 — assets/sfx/kenney/LICENSE.txt); the noise-built
# cues (whoosh, swell, impact) stay synthesised. A synthesised bell or chime reads as a demo's beeps (HyperFrames'
# sound reference: "no synthesised tones, chimes, or dings"); a real click, drop or select reads as a product.
_KENNEY = os.path.join(ROOT, "assets", "sfx", "kenney")
BANK = {"click": ["click_005"], "key": ["click_002", "click_003"], "drop": ["drop_002", "drop_003"], "deal": ["drop_001"],
        "select": ["select_001", "select_002"], "glass": ["glass_002"]}


# a social film's loudness (-16..-14 LUFS), true peak under -1.5 dBTP: measured, the unnormalised mix sat at -24 LUFS
LOUD = "loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000,alimiter=limit=0.7:level=false"   # single-pass loudnorm and the AAC encode overshoot (-0.5/-0.6 dBTP measured); the limiter holds -3 dBFS


def _voice_track(clips, secs, out_wav):
    """Every line placed at its second on one mono 48 kHz track."""
    import numpy as np
    import wave
    sr = 48000
    buf = np.zeros(int((secs + 1) * sr), np.float32)
    for st, mp3 in clips:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp3, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
        i = int(st * sr)
        buf[i:i + len(a)] += a[: max(0, len(buf) - i)]
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype("<i2").tobytes())


def mix(film_dir, silent, cues, total_frames, out, bgm="auto", climax_s=None, vo_clips=()):
    import sfx
    secs = total_frames / FPS
    wav = os.path.join(film_dir, "_promo_sfx.wav")
    bank = sfx.load_bank({k: [os.path.join(_KENNEY, n + ".wav") for n in v] for k, v in BANK.items()})
    # STEREO: a cue sits where its cause is on the frame (plan_sfx(placed=True)); a cue with no place is centred
    if sfx.build_sfx_stereo([(c[0] / FPS,) + tuple(c[1:]) for c in cues], secs, wav, bank=bank) is False:
        raise SystemExit("[promo_film] numpy is needed to synthesise the sound")
    inputs = ["-i", silent, "-i", wav]
    if bgm == "auto":
        # a promo is SCORED (a film over ~15 s that tells something gets a bed): the generated score on a beat grid,
        # its riser and peak placed on the outro's stamp
        import beatgrid
        import score
        g = beatgrid.BeatGrid(112.5, 0.0)
        sc = score.render(g, secs + 1.0, climax_s=climax_s, seed=7)
        pad = os.path.join(film_dir, "_promo_bgm.wav")
        # the music is WIDE (the bed — pad, pluck, bass — in its own decorrelated room), the pulse in the middle
        import stereo
        import numpy as _np
        import wave as _wave
        bed = stereo.widen(sc["bed"], 0.5, score.SR, seconds=0.9)[: len(sc["bed"])]
        lr = bed + stereo.pan(sc["pulse"], 0.0)
        lr *= min(1.0, 0.98 / max(1e-9, float(_np.max(_np.abs(lr)))))
        with _wave.open(pad, "wb") as w:
            w.setnchannels(2), w.setsampwidth(2), w.setframerate(score.SR)
            w.writeframes((_np.clip(lr, -1, 1) * 32767).astype("<i2").tobytes())
        inputs += ["-i", pad]
    elif bgm and bgm != "none":
        inputs += ["-i", bgm]
    has_bed = len(inputs) == 6
    if vo_clips:
        # THE VOICE LEADS: the bed ducks under it (sidechain), the cues sit lower than in a music-only film
        vo = os.path.join(film_dir, "_promo_vo.wav")
        _voice_track(vo_clips, secs, vo)
        inputs += ["-i", vo]
        vi = 3 if has_bed else 2
        if has_bed:
            graph = ("[%d:a]aformat=channel_layouts=stereo,asplit=2[v][vk];[1:a]aformat=channel_layouts=stereo,highpass=f=120,volume=0.6[s];"
                     "[2:a]aformat=channel_layouts=stereo,volume=0.42,afade=t=in:d=0.4,afade=t=out:st=%.2f:d=2[b0];"
                     "[b0][vk]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=400[b];"
                     "[v][s][b]amix=inputs=3:normalize=0,%s[a]" % (vi, max(0, secs - 2), LOUD))
        else:
            graph = ("[%d:a]aformat=channel_layouts=stereo[v];[1:a]aformat=channel_layouts=stereo,highpass=f=120,volume=0.6[s];"
                     "[v][s]amix=inputs=2:normalize=0,%s[a]" % (vi, LOUD))
    elif has_bed:
        # the hits sit 3-6 dB over the bed; the bed fades in and closes on a 2 s fade under the end card
        graph = ("[1:a]aformat=channel_layouts=stereo,highpass=f=120,volume=1.0[s];[2:a]aformat=channel_layouts=stereo,volume=0.42,afade=t=in:d=0.4,"
                 "afade=t=out:st=%.2f:d=2[b];[s][b]amix=inputs=2:normalize=0,%s[a]" % (max(0, secs - 2), LOUD))
    else:
        graph = "[1:a]aformat=channel_layouts=stereo,highpass=f=120,%s[a]" % LOUD
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "0:v", "-map", "[a]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-t", "%.3f" % secs, out]
    subprocess.run(cmd, check=True)
    print("[promo_film] stereo: %s" % stereo_report(out))


def stereo_report(mp4):
    """The delivered mix's field, read back from the file: L/R correlation (1 = mono, < 0.2 = falls apart in mono,
    < 0 = out of phase), the loss folded to mono (a phone speaker), the balance. Said, and refused when broken."""
    import numpy as np
    import stereo
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-map", "0:a:0", "-ac", "2", "-ar", "24000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    lr = np.frombuffer(raw, np.int16).reshape(-1, 2).astype(np.float32) / 32768.0
    m = stereo.measure(lr)
    bad = m["corr"] < 0.2 or m["mono_loss_db"] > 3.0 or abs(m["balance_db"]) > 2.0
    txt = "corr %.2f, mono fold-down %.1f dB, balance %+.1f dB" % (m["corr"], m["mono_loss_db"], m["balance_db"])
    if bad:
        raise SystemExit("[promo_film] the stereo mix is broken (%s): out of phase, lopsided or lost in mono" % txt)
    return txt


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__.strip())
        return 0 if argv[:1] in (["--help"], ["-h"]) else 2
    refuse_unknown(argv[1:], valued=("spec", "stills", "bgm", "out"), switches=("check", "no-sound", "remix", "sheet"))
    film = os.path.abspath(argv[0])
    spec_path = os.path.join(film, argflag(argv, "spec", "promo.json"))
    spec = json.load(open(spec_path, encoding="utf-8"))
    errs, adv = check(spec, film)
    for a in adv:
        print("  ADVISORY  " + a)
    if errs:
        for e in errs:
            print("  ERROR     " + e)
        return 1
    _, total = starts(spec)
    print("[promo_film] %d shots, %d frames (%.1f s) · structure %s (other films' structures: %s)"
          % (len(spec["shots"]), total, total / FPS, skeleton(spec), LEDGER))
    if "--check" in argv:
        return 0
    stills = argflag(argv, "stills", None)
    if stills:
        # the stills see the film as it will render: recordings resolved (and the voice's lengths, if it speaks)
        spec_s = resolve_recordings(film, spec)
        spec_s, _vo = voice_pass(film, spec_s)
        spec_s = place_subtitles(film, spec_s)
        sp = os.path.join(film, "_promo_resolved_stills.json")
        json.dump(spec_s, open(sp, "w"), indent=0)
        for p in render_stills(film, sp, [int(x) for x in stills.split(",") if x.strip()], os.path.join(film, "_stills")):
            print("  still " + p)
        return 0
    out = os.path.join(film, argflag(argv, "out", "out.mp4"))
    # NARRATION FIRST: the voice decides how long a speaking shot lasts, so the table is resolved before the picture
    spec = resolve_recordings(film, spec)
    spec, vo_clips = voice_pass(film, spec)
    spec = place_subtitles(film, spec)
    if vo_clips:
        pass
    if vo_clips or any(sh.get("recording") for sh in spec.get("shots") or []):
        spec_path = os.path.join(film, "_promo_resolved_%s.json" % os.path.splitext(os.path.basename(out))[0])
        json.dump(spec, open(spec_path, "w"), indent=0)
        _, total = starts(spec)
        print("[promo_film] narrated: %d line(s), the film now %d frames (%.1f s)" % (len(vo_clips), total, total / FPS))
    record_skeleton(spec, film)
    # the picture, kept per output so two films in one folder (a 16:9 and a 9:16) never share it; `--remix` re-mixes the
    # sound over the picture already rendered
    silent = os.path.join(film, "_promo_silent_%s" % os.path.basename(out))
    if "--remix" in argv and os.path.isfile(silent):
        print("[promo_film] --remix: the picture is the one already rendered (%s)" % os.path.basename(silent))
    else:
        render_picture(film, spec_path, silent)
    if "--no-sound" in argv:
        os.replace(silent, out)
    else:
        cues = spec.get("sfx")
        cues = ([(int(c["f"]), c["cue"], float(c.get("gain", 0.4)), c.get("pan")) for c in cues] if cues
                else plan_sfx(spec, placed=True))
        rnd = lambda h: round(h, 3) if isinstance(h, float) else [rnd(q) for q in h] if isinstance(h, (list, tuple)) else h  # noqa: E731
        json.dump([{"f": c[0], "cue": c[1], "gain": round(c[2], 3), "pan": rnd(c[3])} for c in cues],
                  open(os.path.join(film, "promo_sfx.json"), "w"), indent=0)
        st, _ = starts(spec)
        outro = [(a, sh) for a, sh in zip(st, spec["shots"]) if sh.get("kind") == "outro"]
        climax = (outro[-1][0] + int(outro[-1][1].get("stampAt", 46))) / FPS if outro else None
        mix(film, silent, cues, total, out, argflag(argv, "bgm", "auto"), climax, vo_clips)
    print("[promo_film] wrote " + out)
    # THE PICTURE GLIDES, MEASURED: a page under a moving camera that steps instead (re-laid out per frame, a raster
    # re-chosen per render tab, a corner in the camera's path) is what a viewer sees as 抖动 — say so on every render
    if "--sheet" in argv:
        sheet(film, spec_path, out)
    rc = glide_check(film, spec_path, out)
    if rc == 1:
        print("[promo_film] the CAMERA steps or shimmers on a page shot (above) — fix it before delivery")
    return rc                                   # a film whose camera fails is written, and the run still says so


def sheet(film, spec_path, video, out_name="_sheet.jpg"):
    """One frame per shot at 90 % of it (the settled frame), labelled with its table index and kind — the contact
    sheet a review starts from."""
    from PIL import Image, ImageDraw
    spec = json.load(open(spec_path, encoding="utf-8"))
    st, _ = starts(spec)
    tiles = []
    for i, (a, sh) in enumerate(zip(st, spec["shots"])):
        f = a + int(round(sh["dur"] * 0.9))
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "select=eq(n\\,%d),scale=480:-2" % f, "-vsync", "0",
                            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
        import io
        im = Image.open(io.BytesIO(r.stdout)).convert("RGB") if r.stdout else Image.new("RGB", (480, 270), "black")
        tiles.append((i, sh.get("kind"), f, im))
    cols = 4
    tw, th = tiles[0][3].size
    out = Image.new("RGB", (cols * (tw + 8), ((len(tiles) + cols - 1) // cols) * (th + 22)), (16, 16, 16))
    d = ImageDraw.Draw(out)
    for k, (i, kind, f, im) in enumerate(tiles):
        x, y = (k % cols) * (tw + 8), (k // cols) * (th + 22)
        out.paste(im, (x, y))
        d.text((x + 4, y + th + 4), "%02d %s f%d" % (i, kind, f), fill=(220, 220, 220))
    p = os.path.join(film, out_name)
    out.save(p, quality=85)
    print("[promo_film] contact sheet " + p)
    return p


def glide_check(film, spec_path, video):
    """picture_glide_qa on every page shot; a shot that fails is re-judged on a CAMERA-ONLY proxy (its acts removed).
    A sparse page whose only texture is the elements popping in measures the acts' own motion — a pop's overshoot, a
    lift — not the camera (an Excalidraw sketch: 0.34 px with its acts, 0.10 camera-only; its slit-scan smooth). So the
    verdict is the camera's; the acts are named as what moved."""
    import tempfile
    import picture_glide_qa as pg
    spec = json.load(open(spec_path, encoding="utf-8"))
    W, H, _n, fps = pg._probe(video)
    bad = []
    for beat, a, b in pg.spans_of(film, spec_path):
        if b - a < 14:
            continue
        r = pg.judge_span(video, a, b, W, H, fps)
        if r is None or r.get("rms") is None:
            print("  shot %2d  not judged (%s)" % (beat - 1, "nothing moving" if r is None else "too little texture"))
            continue
        fails = r["rms"] > pg.FAIL_RMS or (r.get("shimmer") or 0) > pg.FAIL_SHIMMER
        line = "  shot %2d  %.3f px RMS · shimmer %s" % (beat - 1, r["rms"], "%.1f%%" % (r["shimmer"] * 100) if r.get("shimmer") is not None
                                                          else "n/a (no creep: the camera holds or moves fast, never crawls)")
        if not fails:
            print(line + "  ok")
            continue
        shot = dict(spec["shots"][beat - 1])
        if not (shot.get("layers") or shot.get("acts")):
            print(line + "   <- the CAMERA steps or shimmers")
            bad.append(beat - 1)
            continue
        # the camera-only proxy keeps the shot's MACROS: they are part of what the camera films (a push past the page's
        # 2x is onto them), and without them a macro close-up was re-judged as a push into a soft page
        keep = [l for l in (shot.get("layers") or shot.get("acts") or []) if l.get("kind") == "macro"]
        shot.pop("layers", None), shot.pop("acts", None), shot.pop("caption", None)
        shot["layers"] = keep
        proxy = dict(spec, shots=[shot])
        tmp = tempfile.mkdtemp(prefix="promo_cam_")
        pj = os.path.join(film, "_promo_cam_%d.json" % beat)
        json.dump(proxy, open(pj, "w"))
        mp4 = os.path.join(tmp, "cam.mp4")
        try:
            render_picture(film, pj, mp4)
            rc_ = pg.judge_span(mp4, 8, int(round(shot["dur"])) - 8, W, H, fps)
        finally:
            os.remove(pj)
        cam_bad = rc_ is not None and rc_.get("rms") is not None and (rc_["rms"] > pg.FAIL_RMS or (rc_.get("shimmer") or 0) > pg.FAIL_SHIMMER)
        if cam_bad:
            print(line + "   <- the CAMERA steps or shimmers (camera-only: %.3f px, shimmer %s)"
                  % (rc_["rms"], "%.1f%%" % (rc_["shimmer"] * 100) if rc_.get("shimmer") is not None else "n/a"))
            bad.append(beat - 1)
        else:
            print(line + "   camera-only %s — the camera glides; what moved is the shot's acts"
                  % ("%.3f px" % rc_["rms"] if rc_ and rc_.get("rms") is not None else "still"))
    print("[promo_film] glide (shots numbered as in the table, from 0): %s" % ("FAIL on shot(s) %s" % bad if bad else "OK — every page shot's camera glides"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
