"""A laptop is ONE 3D object (runtime/laptop3d.tsx): one camera for the deck, the hinge, the lid and the screen on it.

The defect it exists for: a film turned the kit's flat laptop picture in 3D — the lid's top edge slanted while the
base stayed a front-on horizontal sliver, two cameras on one object — and every gate was green."""
import json
import os
import re
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)

import _tsprobe as tp               # noqa: E402

needs_node = pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")
SPEC = json.load(open(os.path.join(tp.RUNTIME, "deviceSpec.json"), encoding="utf-8"))
ASPECTS = [(1920, 1080), (1080, 1920), (1080, 1080), (1080, 1350)]
CASES = [None, "macbook-pro-14", "macbook-air-13"]
IMPORTS = ("import {deviceGeometry} from %s; import {laptopCamera, laptopBounds, laptopScreenTransform} from %s;"
           % (tp.mod("device"), tp.mod("laptop3d")))


def _homography_apply(m3d, x, y):
    v = [float(n) for n in re.match(r"matrix3d\((.*)\)", m3d).group(1).split(",")]
    # CSS matrix3d is column-major: [a b 0 g, c d 0 h, 0 0 1 0, e f 0 1]
    a, b, g, c, d, h, e, f = v[0], v[1], v[3], v[4], v[5], v[7], v[12], v[13]
    w = g * x + h * y + v[15]
    return (a * x + c * y + e) / w, (b * x + d * y + f) / w


@needs_node
def test_at_rest_the_screen_is_exactly_the_geometry_rect_and_the_body_holds_the_whole_machine():
    """The gates judge deviceGeometry's rects: at rest the lid faces the camera square, so the projected screen IS
    g.screen (no transform at all), and the deck below it fits the body the geometry reserved — without reserving a
    band it never draws (laptopBase / laptopOverhang are this picture's extent)."""
    ts = tp.run_ts(IMPORTS, """
      for (const m of %s) for (const l of ['real', 'flat']) for (const [W, H] of %s) {
        const g = deviceGeometry('laptop', l as any, W, H, 'center', false, m);
        const c = laptopCamera(g);
        out[`${m}/${l}/${W}x${H}`] = {g, quad: c.screenQuad, t: laptopScreenTransform(g, c) ?? null, b: laptopBounds(c)};
      }""" % (json.dumps(CASES), json.dumps([list(a) for a in ASPECTS])))
    assert len(ts) == len(CASES) * 2 * len(ASPECTS)
    for key, r in ts.items():
        g, q, b = r["g"], r["quad"], r["b"]
        s = g["screen"]
        want = [(s["x"], s["y"]), (s["x"] + s["w"], s["y"]), (s["x"] + s["w"], s["y"] + s["h"]), (s["x"], s["y"] + s["h"])]
        for p, (x, y) in zip(q, want):
            assert abs(p["x"] - x) < 0.6 and abs(p["y"] - y) < 0.6, (key, q, want)
        assert r["t"] is None, (key, r["t"])
        body = g["body"]
        assert b["x"] >= body["x"] - 1 and b["x"] + b["w"] <= body["x"] + body["w"] + 1, (key, b, body)
        assert b["y"] >= body["y"] - 1 and b["y"] + b["h"] <= body["y"] + body["h"] + 1, (key, b, body)
        # ...and the reserved band is used: the deck's front reaches the body's bottom, its width the body's sides
        assert body["y"] + body["h"] - (b["y"] + b["h"]) < 0.012 * s["w"] + 2, (key, b, body)
        assert body["w"] - b["w"] < 0.012 * s["w"] + 2, (key, b, body)


@needs_node
def test_turning_the_laptop_turns_all_of_it_with_one_camera():
    """Turned, the deck's front edge and the lid's top edge slant the SAME way (the old picture slanted the lid
    over a level base), and the screen's DOM lands exactly on the lid's projected screen rectangle."""
    ts = tp.run_ts(IMPORTS, """
      const g = deviceGeometry('laptop', 'real', 1920, 1080, 'center', false, 'macbook-pro-14');
      for (const yaw of [-30, -12, 12, 30]) {
        const c = laptopCamera(g, {yaw, pitch: 15});
        const d = c.dims;
        const fl = c.project([-d.W / 2, 0, d.D]), fr = c.project([d.W / 2, 0, d.D]);
        const tl = c.project(c.lid(-d.face.w / 2, d.face.h)), tr = c.project(c.lid(d.face.w / 2, d.face.h));
        out[yaw] = {front: (fr.y - fl.y) / (fr.x - fl.x), top: (tr.y - tl.y) / (tr.x - tl.x), quad: c.screenQuad,
          t: laptopScreenTransform(g, c), s: g.screen};
      }""")
    for yaw, r in ts.items():
        assert abs(r["front"]) > 0.03 and abs(r["top"]) > 0.03, (yaw, r["front"], r["top"])
        assert (r["front"] > 0) == (r["top"] > 0), ("deck and lid slant opposite ways", yaw, r["front"], r["top"])
        s = r["s"]
        for (x, y), p in zip([(0, 0), (s["w"], 0), (s["w"], s["h"]), (0, s["h"])], r["quad"]):
            hx, hy = _homography_apply(r["t"], x, y)
            assert abs(hx + s["x"] - p["x"]) < 0.05 and abs(hy + s["y"] - p["y"]) < 0.05, (yaw, (hx, hy), p)


@needs_node
def test_a_pose_the_drawing_cannot_order_is_refused_by_name():
    ts = tp.run_ts(IMPORTS, """
      const g = deviceGeometry('laptop', 'real', 1920, 1080, 'center', false, 'macbook-pro-14');
      for (const [k, pose] of [['yaw', {yaw: 80}], ['pitch', {pitch: -5}], ['open', {open: 175}]] as any) {
        try { laptopCamera(g, pose); out[k] = 'drawn'; } catch (e) { out[k] = String((e as Error).message); }
      }""")
    assert all(v != "drawn" and "laptop3d" in v for v in ts.values()), ts


def test_every_laptop_model_records_its_deck_and_says_where_each_number_came_from():
    for name, m in SPEC["models"].items():
        if name.startswith("_") or m.get("kind") != "laptop":
            continue
        b = m.get("body3d")
        assert b, "%s has no body3d — the laptop object cannot be drawn" % name
        prov = b.get("_provenance") or {}
        assert prov.get("published") and (prov.get("derived") or prov.get("design")), name
        assert 0 < b["lidMm"] < m["published"]["caseMm"][2], name
        x, z, w, d = b["well"]
        W, D = m["published"]["caseMm"][:2]
        assert abs(2 * x + w - W) < 1.0 and z + d < D, (name, "the keyboard well is not centred inside the deck")
        tw, tz, td, _ = b["trackpad"]
        assert tw < W and tz > z + d and tz + td < D, (name, "the trackpad is not between the well and the front")
    l3 = SPEC["parts"]["laptop3d"]
    assert l3["_doc"].startswith("design")
