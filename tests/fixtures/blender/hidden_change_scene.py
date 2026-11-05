"""A test scene whose pose changes what kit/reuse.py does not read — the pixels of an image the cube is painted
with — so reuse must notice by its verification render and turn itself off."""
import math

import bpy


def build(k):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cube = bpy.context.object
    k.stage.place(k.camera, cube, 0.5, 0.5, 6.0)
    img = bpy.data.images.new("paint", 8, 8)
    m = bpy.data.materials.new("painted")
    m.use_nodes = True
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    m.node_tree.links.new(tex.outputs["Color"], m.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    cube.data.materials.append(m)
    bpy.ops.object.light_add(type="SUN")
    bpy.context.object.rotation_euler = (math.radians(50), 0, math.radians(30))
    k.img = img
    return {"objects": {"cube": cube}, "anchors": {}}


def pose(k, t):
    v = min(1.0, 0.1 + 2.5 * t)                  # the paint brightens, by the image's pixels only
    k.img.pixels[:] = [v, v * 0.6, 0.2, 1.0] * 64
    k.img.update()
