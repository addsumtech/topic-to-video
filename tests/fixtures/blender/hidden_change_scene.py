"""A test scene whose pose changes what kit/reuse.py does not read — a mesh's vertices — so reuse must notice by its
verification render and turn itself off."""
import math

import bpy


def build(k):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cube = bpy.context.object
    k.stage.place(k.camera, cube, 0.5, 0.5, 6.0)
    k.v0 = [tuple(v.co) for v in cube.data.vertices]
    bpy.ops.object.light_add(type="SUN")
    bpy.context.object.rotation_euler = (math.radians(50), 0, math.radians(30))
    k.cube = cube
    return {"objects": {"cube": cube}, "anchors": {}}


def pose(k, t):
    s = 1.0 + 1.5 * t                            # the cube grows, by its vertices only
    for v, c in zip(k.cube.data.vertices, k.v0):
        v.co = (c[0] * s, c[1] * s, c[2] * s)
    k.cube.data.update()
