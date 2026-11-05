"""A test scene where a small cube stands still in front of a still backdrop and only its MATERIAL changes: that is
the cube changing, so kit/reuse.py renders its rectangle, not the frame."""
import math

import bpy


def build(k):
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    back = bpy.context.object
    back.name = "back"
    k.stage.place(k.camera, back, 0.5, 0.5, 12.0)
    back.rotation_euler = (math.radians(90), 0, 0)
    back.scale = (30, 30, 1)
    m = bpy.data.materials.new("b")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = k.hexc("#3060a0")
    back.data.materials.append(m)
    bpy.ops.mesh.primitive_cube_add(size=0.4)
    cube = bpy.context.object
    cube.name = "mover"
    k.stage.place(k.camera, cube, 0.3, 0.5, 6.0)
    k.base = tuple(cube.location)
    cm = bpy.data.materials.new("fading")
    cm.use_nodes = True
    cube.data.materials.append(cm)
    bpy.ops.object.light_add(type="SUN")
    bpy.context.object.rotation_euler = (math.radians(20), 0, math.radians(10))
    return {"objects": {"mover": cube}, "anchors": {"c": (cube, (0, 0, 0))}}


def pose(k, t):
    p = bpy.data.objects["mover"].active_material.node_tree.nodes["Principled BSDF"]
    v = min(1.0, 0.2 + 3.0 * t)
    p.inputs["Base Color"].default_value = (v, 0.3, 0.1, 1.0)
