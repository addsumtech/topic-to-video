#!/usr/bin/env python3
"""Python port of runtime/device.tsx deviceGeometry() — for the legibility and fidelity gates, which run before a
render.

tests/test_device_runtime.py holds this to the TypeScript for every kind x look x aspect x model: a second copy
of a rectangle is a second answer, so the copy is checked, not trusted."""
import math
import os
import re

import device_script as ds
from _caption_band import caption_band_px

_LAYOUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "runtime", "layout.ts")


def _content_top():
    m = re.search(r"export const TITLE_BAND\s*=\s*(\d+)", open(_LAYOUT, encoding="utf-8").read())
    if not m:
        raise RuntimeError("TITLE_BAND not found in runtime/layout.ts")
    return int(m.group(1))


def _r(x):
    """Math.round: halves go UP (Python's round() sends 0.5 to 0)."""
    return int(math.floor(x + 0.5))


def _base_kind(kind):
    return "tablet" if kind == "tablet-landscape" else kind


def models():
    return {k: v for k, v in ds.SPEC["models"].items() if not k.startswith("_")}


def proportions(kind, look, model=None):
    """runtime/device.tsx `proportions`: the screen's height and every bezel, overhang and extent in units of the
    screen's width. A model draws its published case around its own pixels (px / ppi); a kind draws its `like`
    model's proportions around the generic screen."""
    S = ds.SPEC
    M = models()
    if model is not None and model not in M:
        raise ValueError("device: no model %s — one of %s" % (model, ", ".join(M)))
    m = M.get(model) if model else None
    if m and m["kind"] != _base_kind(kind):
        raise ValueError("device: %s is a %s, not a %s" % (model, m["kind"], kind))
    if look not in ("flat", "real", "screen"):
        raise ValueError("device: no geometry for %s / %s" % (kind, look))
    if kind == "monitor":
        b = S["body"][look]["monitor"]
        rw, rh = S["screenRatio"]["monitor"]
        return dict(ratio=float(rh) / rw, bl=b["bezel"], bt=b["bezel"], bb=b["bezel"], inner=b["radius"],
                    ov=b["overhang"], above=0.0, below=0.0, base=b["base"], strip=b["strip"], island=False,
                    notch=False, smooth=False, topRoundOnly=False)
    like = m or M[S["kinds"][kind]["like"]]
    pw, ph = like["published"]["px"]
    cw, ch = like["published"]["caseMm"][:2]
    landscape = kind == "tablet-landscape"
    if landscape:
        pw, ph, cw, ch = ph, pw, ch, cw
    mm = 25.4 / like["published"]["ppi"]
    sW, sH = pw * mm, ph * mm
    if m:
        px = m["published"]["px"]
        ratio = float(px[0]) / px[1] if landscape else float(px[1]) / px[0]
    else:
        rw, rh = S["screenRatio"][kind]
        ratio = float(rh) / rw
    inner = like["displayRadiusMm"] / sW
    bk = _base_kind(kind)
    smooth = not like.get("circleDisplay")
    top_only = bool(like.get("topRoundOnly"))
    P = S["parts"]
    if look == "screen":
        strip = S["body"]["screen"]["laptop"]["strip"] if bk == "laptop" else 0.0
        return dict(ratio=ratio, bl=0.0, bt=0.0, bb=0.0, inner=inner, ov=0.0, above=0.0, below=0.0, base=0.0,
                    strip=strip, island=False, notch=False, smooth=smooth, topRoundOnly=top_only)
    bl = (cw - sW) / 2.0 / sW
    bt = bb = (ch - sH) / 2.0 / sW
    ov = above = below = base = 0.0
    if bk == "laptop":
        bt = bl * P["laptopTopBezelOfSide"]
        bb = (ch - sH) / sW - bt
        ov, base = P["laptopOverhang"], P["laptopBase"]
    elif bk == "watch":
        case_w, case_h = 1 + 2 * bl, ratio + 2 * bt
        ov = P["crown"]["out"] * case_w
        above = below = P["band"]["len"] * case_h
    else:
        ov = P["buttonOut"].get(bk, 0.0)
    notch = bk == "laptop" and bool(m.get("notch") if m else S["kinds"][kind].get("notch"))
    island = bk == "phone" and (bool(m.get("island")) if m else True)
    return dict(ratio=ratio, bl=bl, bt=bt, bb=bb, inner=inner, ov=ov, above=above, below=below, base=base,
                strip=0.0, island=island, notch=notch, smooth=smooth, topRoundOnly=top_only)


def geometry(kind, look, W, H, placement="center", kicker=False, model=None):
    S = ds.SPEC
    if kind not in S["screenRatio"] or look not in S["body"] or placement not in S["placementX"]:
        raise ValueError("device: no geometry for %s / %s / %s — kinds are %s, looks %s, placements %s"
                         % (kind, look, placement, ", ".join(S["screenRatio"]), ", ".join(S["body"]),
                            ", ".join(S["placementX"])))
    p = proportions(kind, look, model)
    top = _content_top() if kicker else _r(H * S["zoneTopFrac"])
    zone_h = max(1, (H - caption_band_px(W, H)) - top)
    zone_w = W * S["zoneWidthFill"]
    face_w = 1 + 2 * p["bl"]
    face_h = p["ratio"] * (1 + p["strip"]) + p["bt"] + p["bb"]
    bw = face_w + 2 * p["ov"]
    bh = face_h + p["above"] + p["below"] + p["base"]
    sw = min(zone_w / bw, zone_h / bh)
    sh = sw * p["ratio"]
    body_w, body_h = sw * bw, sw * bh
    margin = (W - zone_w) / 2.0
    body_x = min(max(W * S["placementX"][placement] - body_w / 2.0, margin), W - margin - body_w)
    body_y = top + (zone_h - body_h) / 2.0
    fx, fy = body_x + sw * p["ov"], body_y + sw * p["above"]
    sx = fx + sw * p["bl"]
    sy = fy + sw * p["bt"] + sh * p["strip"]

    def rect(x, y, w, h):
        return {"x": _r(x), "y": _r(y), "w": _r(w), "h": _r(h)}

    P = S["parts"]
    return {
        "body": rect(body_x, body_y, body_w, body_h),
        "face": rect(fx, fy, sw * face_w, sw * face_h),
        "screen": rect(sx, sy, sw, sh),
        "bezel": _r(sw * p["bl"]),
        "bezels": {"l": _r(sw * p["bl"]), "r": _r(sw * p["bl"]), "t": _r(sw * p["bt"]), "b": _r(sw * p["bb"])},
        "radius": _r(sw * p["inner"]),
        "outerRadius": _r(sw * p["inner"]) if look == "screen" else _r(sw * (p["inner"] + p["bl"])),
        "island": rect(sx + sw * (1 - P["island"]["w"]) / 2.0, sy + sw * P["island"]["top"], sw * P["island"]["w"],
                       sw * P["island"]["h"]) if p["island"] else None,
        "notch": rect(sx + sw * (1 - P["notch"]["w"]) / 2.0, sy, sw * P["notch"]["w"], sh * P["notch"]["h"])
        if p["notch"] else None,
        "model": model,
    }
