"""The product studio (blender/kit/studio.product_light + materials) and the 2D finishes (runtime/solid.ts).

WHY: the 2026-11-11 craft-study surface measure — a product film's subject is a surface the light has modelled, ours
were clay models and flat fills. These pin what the fix promises: the studio puts a ramp AND a highlight on a glossy
subject that the old flat-world light did not; every finish builds in this Blender; the 2D finishes shade toward
the key, keep a flat interior's colour exactly, and refuse an unknown finish."""
import json
import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from test_blender_runner import BLENDER, needs_blender  # noqa: E402
import _tsprobe  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "blender")


def _still(tmp_path, params, w=240, h=135):
    out = tmp_path / ("run_" + "_".join("%s%s" % kv for kv in sorted(params.items())))
    cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", os.path.join(ROOT, "blender", "runner.py"),
           "--", "--scene", os.path.join(FIX, "studio_scene.py"), "--out", str(out), "--frames", "1", "--fps", "30",
           "--w", str(w), "--h", str(h), "--engine", "eevee", "--mode", "rgba", "--cues", "{}", "--anchors", "",
           "--objects", "ball", "--params", json.dumps(params)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    a = np.asarray(Image.open(out / "rgba" / "0001.png").convert("RGBA")).astype(float)
    on = a[..., 3] > 250
    lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[on]
    assert on.sum() > 500, "the ball should fill the middle of the frame"
    return lum


@needs_blender
def test_product_light_models_a_glossy_subject(tmp_path):
    lit = _still(tmp_path, {"lit": True})
    flat = _still(tmp_path, {"lit": False})
    rng = lambda v: float(np.percentile(v, 95) - np.percentile(v, 5))  # noqa: E731
    # a modelled surface: a wide ramp across the body and a near-white highlight (the strip lights' reflections)
    assert rng(lit) >= 60, rng(lit)
    assert np.percentile(lit, 99.5) >= 230, np.percentile(lit, 99.5)
    assert rng(lit) > rng(flat) + 10, (rng(lit), rng(flat))


@needs_blender
def test_a_metal_finish_renders_under_the_studio(tmp_path):
    lum = _still(tmp_path, {"lit": True, "finish": "anodized_alu"})
    assert float(np.percentile(lum, 95) - np.percentile(lum, 5)) >= 40


needs_ts = pytest.mark.skipif(not _tsprobe.available(), reason="no node/esbuild for the TS probe")


@needs_ts
def test_solid_form_shade_lights_the_key_side():
    out = _tsprobe.run_ts("import {formShade, lightDir, STUDIO_KEY, reflectionBands, chamferFilter, tube, FINISHES} from "
                          + _tsprobe.mod("solid.ts") + ";\nimport {lumValue} from " + _tsprobe.mod("shotLuma.ts") + ";", """
const box = {x: 100, y: 100, w: 400, h: 200};
const fs = formShade(box, '#7a8088', 'satin_plastic');
out.first = fs.stops[0].color; out.last = fs.stops[fs.stops.length - 1].color;
out.l0 = lumValue(fs.stops[0].color); out.l1 = lumValue(fs.stops[fs.stops.length - 1].color);
const d = lightDir(STUDIO_KEY);
out.d = d; out.p1 = [fs.x1, fs.y1]; out.p2 = [fs.x2, fs.y2];
out.metalStops = formShade(box, '#7a8088', 'anodized_alu').stops.length;
out.diffuseBands = reflectionBands(box, 'fabric').length;
out.glossBands = reflectionBands(box, 'gloss_plastic').length;
const ch: any = chamferFilter('c', 6, 'enamel');
const comp = ch.props.children.find((c: any) => c.props && c.props.operator === 'arithmetic');
out.k1 = comp.props.k1; out.k2 = comp.props.k2;
out.flat = Math.sin(STUDIO_KEY.elev * Math.PI / 180);
const t: any = tube('t', 'M0 0 L100 0', 10, '#b87333', 'copper');
out.tubeLayers = t.props.children.length;
out.n = FINISHES.length;
let thrown = 0;
for (const f of [() => formShade(box, '#fff', 'velvet'), () => tube('x', 'M0 0', 0, '#fff', 'copper'),
                 () => formShade({x: 0, y: 0, w: 0, h: 10}, '#fff', 'enamel')]) { try { f(); } catch (e) { thrown++; } }
out.thrown = thrown;
""")
    assert out["l0"] > out["l1"]                       # the lit end is lighter than the far end
    # the gradient starts on the key's side: from p1 to p2 runs along the light's travel
    v = (out["p2"][0] - out["p1"][0], out["p2"][1] - out["p1"][1])
    assert v[0] * out["d"]["x"] + v[1] * out["d"]["y"] > 0
    assert out["metalStops"] > 3                       # a metal mirrors the room: more than one ramp
    assert out["diffuseBands"] == 0 and out["glossBands"] == 2
    # the chamfer keeps a flat interior's colour exactly: k1 * flat + k2 == 1
    assert abs(out["k1"] * out["flat"] + out["k2"] - 1) < 1e-9
    assert out["tubeLayers"] == 5                      # outline, body, mid, lit side, specular (copper reflects)
    assert out["n"] >= 14 and out["thrown"] == 3


def test_surface_qa_tells_a_lit_surface_from_a_flat_fill():
    import surface_qa
    H, W = 270, 480
    yy, xx = np.mgrid[0:H, 0:W]
    ground = np.zeros((H, W, 3)) + 236.0
    flat = ground.copy()
    disc = (xx - 240) ** 2 + (yy - 110) ** 2 < 80 ** 2
    flat[disc] = (60, 90, 160)                                    # a vector fill
    lit = ground.copy()
    shade = np.clip(1.25 - ((xx - 200) ** 2 + (yy - 70) ** 2) ** 0.5 / 130.0, 0.15, 1.0)   # a key from the upper left
    for c, v in enumerate((60, 90, 160)):
        lit[..., c][disc] = (v * 0.4 + 150 * shade)[disc]
    assert surface_qa.frame_stats(flat)["modelled"] == 0
    assert surface_qa.frame_stats(flat)["flat_area"] > 0.05
    assert surface_qa.frame_stats(lit)["modelled"] > 0.05
    # thin hairlines on a ground are not a surface
    lines = ground.copy()
    lines[::12, :, :] = 40
    assert surface_qa.frame_stats(lines)["modelled"] == 0
    with pytest.raises(ValueError):
        surface_qa.frame_stats(np.zeros((5, 5, 3)))
