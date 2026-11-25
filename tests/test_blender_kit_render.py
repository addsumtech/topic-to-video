"""The Blender kit's render settings and finishes from the 2026-11-25 scanner bench (references/3d-engines.md): Cycles
denoises on the GPU with the light tree on (25.6 -> 19.8 s a frame; 46.7 s without the tree); product_light takes the
view a product needs (AgX for white and glossy, Khronos PBR Neutral for a brand colour) and refuses another; micro()
varies a finish's roughness and refuses a material with nothing to vary."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from test_blender_runner import BLENDER, needs_blender  # noqa: E402

SCRIPT = r'''
import sys, bpy
sys.path.insert(0, %r)
from blender.kit import render, studio, materials as M
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene
try:
    render.configure(sc, "cycles", "rgb", 64, 64, samples=8)
    gpu = True
except RuntimeError:
    gpu = False        # no GPU on this machine: configure refuses, which is its own contract
if gpu:
    assert sc.cycles.denoising_use_gpu, "configure must denoise on the GPU"
    studio.tune_cycles(16)
    assert sc.cycles.denoising_use_gpu and sc.cycles.use_light_tree
bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.active_object
bpy.ops.object.camera_add(location=(0, -8, 2)); cam = bpy.context.active_object
studio.product_light([cube], cam, view="neutral")
assert sc.view_settings.view_transform == "Khronos PBR Neutral", sc.view_settings.view_transform
studio.product_light([cube], cam)
assert sc.view_settings.view_transform == "AgX"
try:
    studio.product_light([cube], cam, view="filmic"); raise SystemExit("an unknown view must be refused")
except ValueError:
    pass
m = M.finish("gloss_plastic", "#f2f2ef", "shell")
M.micro(m)
p = m.node_tree.nodes["Principled BSDF"]
assert p.inputs["Roughness"].is_linked and p.inputs["Coat Roughness"].is_linked
z = M.finish("satin_plastic", "#ffffff", "z"); z.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0
try:
    M.micro(z); raise SystemExit("a finish with no roughness to vary must be refused")
except ValueError:
    pass
print("KIT-OK")
''' % ROOT


@needs_blender
def test_kit_render_settings_views_and_micro_surface(tmp_path):
    f = tmp_path / "t.py"
    f.write_text(SCRIPT)
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", str(f)],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0 and "KIT-OK" in r.stdout, r.stdout[-2000:] + r.stderr[-2000:]
