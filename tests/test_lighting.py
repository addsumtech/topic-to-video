"""Light to build with (spec 2026-11-06 D3). ANC's Blender plates measured almost no highlight (0.04-0.13) and a soft
edge against the ground (references/craft-bar.md); the craft bar's product light is a soft key, a fill, and a rim
light behind the subject tracing its silhouette. runtime/lighting.tsx gives built (SVG) shots the same three, and
blender/kit/stage.product_rig puts them in a plate with the rim linked to the subject only."""
import json
import os
import subprocess
import sys
import tempfile

import pytest

import _tsprobe as tp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import blender_plate as bp  # noqa: E402

needs_node = pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")
needs_blender = pytest.mark.skipif(bp.blender_bin() is None, reason="no Blender")
IMP = "import {rimGradient, keyFalloff, contactShadow} from %s;" % tp.mod("lighting.tsx")
BOX = "{x: 100, y: 100, w: 400, h: 300}"


@needs_node
def test_rim_is_brightest_at_the_chosen_edge_and_dark_inside():
    o = tp.run_ts(IMP, "out.l = rimGradient(%s, 'left', 1); out.r = rimGradient(%s, 'right', 0.5);" % (BOX, BOX))
    for g in (o["l"], o["r"]):
        offs = [s["offset"] for s in g["stops"]]
        assert offs == sorted(offs) and offs[0] == 0 and offs[-1] == 1
        assert g["stops"][0]["opacity"] > g["stops"][-1]["opacity"] == 0
    assert o["l"]["angle"] != o["r"]["angle"] and o["l"]["stops"][0]["opacity"] > o["r"]["stops"][0]["opacity"]


@needs_node
def test_key_falloff_centres_on_the_key_and_fades_out():
    o = tp.run_ts(IMP, "out.k = keyFalloff(%s, [0.25, 0.2]);" % BOX)["k"]
    assert abs(o["cx"] - 0.25) < 1e-9 and abs(o["cy"] - 0.2) < 1e-9
    assert o["stops"][0]["opacity"] > o["stops"][-1]["opacity"] == 0


@needs_node
def test_contact_shadow_sits_under_the_box_and_a_bad_box_is_refused():
    o = tp.run_ts(IMP, "out.s = contactShadow(%s, 400);" % BOX)["s"]
    assert abs(o["cx"] - 300) < 1e-9 and o["cy"] == 400 and o["rx"] > o["ry"] > 0 and 0 < o["opacity"] < 1
    with pytest.raises(AssertionError, match="lighting"):
        tp.run_ts(IMP, "out.s = contactShadow({x: 0, y: 0, w: -1, h: 10}, 10);")


_RIG = r"""
import bpy, json, sys
sys.path.insert(0, %r)
from kit import stage
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0)); cube = bpy.context.active_object
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -1)); floor = bpy.context.active_object
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.location = (0, -8, 1); bpy.context.scene.camera = cam
stage.face_toward(cam, "-Z", (0, 0, 0))
rig = stage.product_rig(cube, cam)
rim = rig["rim"]
coll = rim.light_linking.receiver_collection
out = {k: list(v.location) for k, v in rig.items()}
out["rim_receivers"] = sorted(o.name for o in coll.all_objects) if coll else None
out["types"] = {k: v.data.type for k, v in rig.items()}
e1 = {k: v.data.energy for k, v in rig.items()}
for o in list(bpy.data.objects):
    if o.name.startswith("rig_"): bpy.data.objects.remove(o)
rig4 = stage.product_rig(cube, cam, exposure=4.0)
out["ratio"] = {k: rig4[k].data.energy / e1[k] for k in e1}
print("RIG " + json.dumps(out))
"""


@needs_blender
def test_product_rig_rims_the_subject_only_from_behind():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(_RIG % os.path.join(ROOT, "blender"))
    r = subprocess.run([bp.blender_bin(), "-b", "--factory-startup", "--python-exit-code", "1", "--python", fh.name],
                       capture_output=True, text=True, timeout=300)
    os.unlink(fh.name)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    rig = json.loads(next(l for l in r.stdout.splitlines() if l.startswith("RIG "))[4:])
    assert rig["rim_receivers"] == ["Cube"]                       # the rim lights the subject, never the floor
    assert rig["rim"][1] > 0 > rig["key"][1]                       # rim behind the subject, key in front (camera at -y)
    assert rig["key"][0] * rig["fill"][0] < 0                      # key and fill on opposite sides
    assert set(rig["types"].values()) <= {"AREA", "SPOT", "POINT"}
    assert all(abs(r - 4.0) < 1e-6 for r in rig["ratio"].values())   # a dark subject gets more light, same balance
