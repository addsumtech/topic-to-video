"""A test scene that never moves: every frame after the first is the first again (kit/reuse.py `copy`)."""
import math

import bpy


def build(k):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cube = bpy.context.object
    k.stage.place(k.camera, cube, 0.5, 0.5, 6.0)
    cube.rotation_euler = (0.4, 0.2, 0.6)
    bpy.ops.object.light_add(type="SUN")
    bpy.context.object.rotation_euler = (math.radians(50), 0, math.radians(30))
    return {"objects": {"cube": cube}, "anchors": {"top": (cube, (0, 0, 0.5))}}


def pose(k, t):
    pass
