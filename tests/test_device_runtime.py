"""The device layer's pure functions, run in node against the real modules — and held to their Python twins."""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)

import _tsprobe as tp               # noqa: E402

needs_node = pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")
KINDS, LOOKS = ("phone", "tablet", "laptop", "monitor"), ("flat", "real", "screen")
ASPECTS = [(1920, 1080), (1080, 1920), (1080, 1080), (1080, 1350)]


@needs_node
def test_python_and_typescript_place_every_device_identically():
    import device_geometry as dg
    ts = tp.run_ts("import {deviceGeometry} from %s;" % tp.mod("device"), """
      for (const k of %s) for (const l of %s) for (const [W, H] of %s) for (const p of ['center', 'left'])
        out[`${k}/${l}/${W}x${H}/${p}`] = deviceGeometry(k as any, l as any, W, H, p as any, false);
    """ % (list(KINDS), list(LOOKS), [list(a) for a in ASPECTS]))
    for key, g in ts.items():
        k, l, wh, p = key.split("/")
        W, H = (int(v) for v in wh.split("x"))
        py = dg.geometry(k, l, W, H, p, False)
        assert {n: py[n] for n in ("body", "screen")} == {n: g[n] for n in ("body", "screen")}, key


@needs_node
def test_every_device_sits_inside_the_frame_and_above_the_caption_band():
    from _caption_band import caption_band_px
    ts = tp.run_ts("import {deviceGeometry} from %s;" % tp.mod("device"), """
      for (const k of %s) for (const l of %s) for (const [W, H] of %s)
        out[`${k}/${l}/${W}/${H}`] = deviceGeometry(k as any, l as any, W, H);
    """ % (list(KINDS), list(LOOKS), [list(a) for a in ASPECTS]))
    for key, g in ts.items():
        W, H = (int(v) for v in key.split("/")[2:])
        b, s = g["body"], g["screen"]
        assert b["x"] >= 0 and b["x"] + b["w"] <= W, key
        assert b["y"] >= 0 and b["y"] + b["h"] <= H - caption_band_px(W, H) + 1, key
        assert b["x"] <= s["x"] and s["x"] + s["w"] <= b["x"] + b["w"], key


@needs_node
def test_a_phone_fills_a_portrait_frame():
    from _caption_band import caption_band_px
    g = tp.run_ts("import {deviceGeometry} from %s;" % tp.mod("device"),
                  "out.g = deviceGeometry('phone', 'flat', 1080, 1920);")["g"]
    zone = 1920 - caption_band_px(1080, 1920) - round(1920 * 0.05)
    assert g["body"]["h"] >= 0.95 * zone, (g, zone)


@needs_node
def test_the_default_look_follows_the_ground():
    out = tp.run_ts("import {defaultLook} from %s;" % tp.mod("device"), """
      out.dark = defaultLook({bg: '#0b0d12'} as any); out.light = defaultLook({bg: '#f4f1ea'} as any);
      out.none = defaultLook(null);
    """)
    assert out == {"dark": "real", "light": "flat", "none": "flat"}