#!/usr/bin/env python3
"""Python port of runtime/device.tsx deviceGeometry() — for the legibility gate, which runs before a render.

tests/test_device_runtime.py holds this to the TypeScript for every kind x look x aspect: a second copy of a
rectangle is a second answer, so the copy is checked, not trusted."""
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


def geometry(kind, look, W, H, placement="center", kicker=False):
    S = ds.SPEC
    if kind not in S["screenRatio"] or look not in S["body"] or kind not in S["body"][look] \
            or placement not in S["placementX"]:
        raise ValueError("device: no geometry for %s / %s / %s — kinds are %s, looks %s, placements %s"
                         % (kind, look, placement, ", ".join(S["screenRatio"]), ", ".join(S["body"]),
                            ", ".join(S["placementX"])))
    rw, rh = S["screenRatio"][kind]
    b = S["body"][look][kind]
    top = _content_top() if kicker else _r(H * S["zoneTopFrac"])
    zone_h = max(1, (H - caption_band_px(W, H)) - top)
    zone_w = W * S["zoneWidthFill"]
    sh_per_sw = float(rh) / rw
    bw = 1 + 2 * b["bezel"] + 2 * b["overhang"]
    bh = sh_per_sw * (1 + b["strip"]) + 2 * b["bezel"] + b["base"]
    sw = min(zone_w / bw, zone_h / bh)
    sh = sw * sh_per_sw
    body_w, body_h = sw * bw, sw * bh
    margin = (W - zone_w) / 2.0
    body_x = min(max(W * S["placementX"][placement] - body_w / 2.0, margin), W - margin - body_w)
    body_y = top + (zone_h - body_h) / 2.0
    sx = body_x + sw * (b["overhang"] + b["bezel"])
    sy = body_y + sw * b["bezel"] + sh * b["strip"]

    def rect(x, y, w, h):
        return {"x": _r(x), "y": _r(y), "w": _r(w), "h": _r(h)}

    return {"body": rect(body_x, body_y, body_w, body_h), "screen": rect(sx, sy, sw, sh)}
