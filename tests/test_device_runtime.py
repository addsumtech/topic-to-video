"""The device layer's pure functions, run in node against the real modules — and held to their Python twins."""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)

import _tsprobe as tp               # noqa: E402

needs_node = pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")
KINDS, LOOKS = ("phone", "tablet", "tablet-landscape", "laptop", "monitor"), ("flat", "real", "screen")
ASPECTS = [(1920, 1080), (1080, 1920), (1080, 1080), (1080, 1350)]


@needs_node
def test_python_and_typescript_place_every_device_identically():
    import device_geometry as dg
    ts = tp.run_ts("import {deviceGeometry} from %s;" % tp.mod("device"), """
      for (const k of %s) for (const l of %s) for (const [W, H] of %s) for (const p of ['center', 'left', 'right'])
        for (const kick of [false, true])
          out[`${k}/${l}/${W}x${H}/${p}/${kick}`] = deviceGeometry(k as any, l as any, W, H, p as any, kick);
    """ % (list(KINDS), list(LOOKS), [list(a) for a in ASPECTS]))
    for key, g in ts.items():
        k, l, wh, p, kick = key.split("/")
        W, H = (int(v) for v in wh.split("x"))
        py = dg.geometry(k, l, W, H, p, kick == "true")
        assert {n: py[n] for n in ("body", "screen")} == {n: g[n] for n in ("body", "screen")}, key


@needs_node
def test_every_device_sits_inside_the_frame_and_above_the_caption_band():
    from _caption_band import caption_band_px
    ts = tp.run_ts("import {deviceGeometry} from %s;" % tp.mod("device"), """
      for (const k of %s) for (const l of %s) for (const [W, H] of %s) for (const p of ['center', 'left', 'right'])
        for (const kick of [false, true])
          out[`${k}/${l}/${W}/${H}/${p}/${kick}`] = deviceGeometry(k as any, l as any, W, H, p as any, kick);
    """ % (list(KINDS), list(LOOKS), [list(a) for a in ASPECTS]))
    for key, g in ts.items():
        W, H = (int(v) for v in key.split("/")[2:4])
        b, s = g["body"], g["screen"]
        assert b["x"] >= 0 and b["x"] + b["w"] <= W, key
        assert b["y"] >= 0 and b["y"] + b["h"] <= H - caption_band_px(W, H) + 1, key
        assert b["x"] <= s["x"] and s["x"] + s["w"] <= b["x"] + b["w"], key
        assert b["y"] <= s["y"] and s["y"] + s["h"] <= b["y"] + b["h"], key


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


@needs_node
def test_a_fling_ends_exactly_where_it_was_sent_and_overshoots_only_a_little():
    out = tp.run_ts("import {flingAt, scrollRangePx} from %s;" % tp.mod("screen"), """
      const us = Array.from({length: 101}, (_, i) => i / 100);
      out.v = us.map((u) => flingAt(u));
      out.range = scrollRangePx(1170, 6000, 390, 844);
      out.none = scrollRangePx(1170, 2532, 390, 844);
    """)
    v = out["v"]
    assert v[0] == 0 and abs(v[-1] - 1) < 1e-9
    assert max(v) <= 1.04 + 1e-9 and max(v) > 1.0
    assert all(b >= a - 1e-9 for a, b in zip(v[:72], v[1:73])), "the fling reverses before its peak"
    assert out["range"] == pytest.approx(6000 * 390 / 1170 - 844)
    assert out["none"] == 0


@needs_node
def test_a_screenshot_without_a_size_is_refused():
    """A zero width once scrolled 2.3 million pixels; NaN became a CSS height the browser silently drops."""
    out = tp.run_ts("import {scrollRangePx} from %s;" % tp.mod("screen"), """
      out.errors = [[0, 6000], [-1170, 6000], [NaN, 6000], [1170, 0], [Infinity, 6000]].map(([w, h]) => {
        try { scrollRangePx(w, h, 390, 844); return null; } catch (e) { return String((e as Error).message); }
      });
    """)
    assert all(e and "positive size" in e for e in out["errors"]), out["errors"]


_CHUNK_CASES = ["ab c", "上周的客户反馈", "上周 AI", "", "搜索：上周所有的客户反馈 invoice",
                chr(0xF900) + chr(0xF901), chr(0xE000) + chr(0xE001), chr(0xA000) + chr(0xA001), chr(0x4DC0)]   # R5: both edges, spelled with chr() so nothing can normalize them


@needs_node
def test_typing_chunks_are_the_same_on_both_sides():
    import device_script as ds
    out = tp.run_ts("import {typeChunks} from %s;" % tp.mod("gesture"),
                    "out.v = %s.map((s) => typeChunks(s));" % _CHUNK_CASES.__repr__().replace("'", '"'))
    assert out["v"] == [ds.type_chunks(s) for s in _CHUNK_CASES]


@needs_node
def test_every_chunk_is_typed_by_the_end_and_never_before_the_start():
    out = tp.run_ts("import {typeChunks, typedCount} from %s;" % tp.mod("gesture"), """
      const c = typeChunks('上周的客户反馈 invoice');
      const ts = Array.from({length: 51}, (_, i) => 0.3 + (i / 50) * 0.4);
      out.n = c.length; out.v = ts.map((t) => typedCount(t, 0.4, 0.6, c));
    """)
    v = out["v"]
    assert v[0] == 0 and v[-1] == out["n"] and all(b >= a for a, b in zip(v, v[1:]))


@needs_node
def test_the_caret_is_solid_while_typing_and_blinks_in_sixteen_frame_phases():
    out = tp.run_ts("import {caretOn} from %s;" % tp.mod("gesture"), """
      out.typing = [null, -3, 0].map((f) => caretOn(f as any, false));
      out.after = Array.from({length: 64}, (_, i) => caretOn(i + 1, false));
      out.reduced = caretOn(20, true);
    """)
    assert out["typing"] == [True, True, True] and out["reduced"] is True
    a = out["after"]
    flips = [i for i in range(1, len(a)) if a[i] != a[i - 1]]
    assert flips and all(b - a_ == 16 for a_, b in zip(flips, flips[1:])), flips


def test_an_unknown_device_is_named_not_a_key_error():
    import device_geometry as dg
    with pytest.raises(ValueError) as e:
        dg.geometry("watch", "flat", 1920, 1080)
    assert "no geometry for watch" in str(e.value) and "phone" in str(e.value)

