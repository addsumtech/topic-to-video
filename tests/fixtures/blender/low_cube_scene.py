"""A test scene for blender/runner.py: one cube low in the frame, where the caption is, turning; an anchor on its top face and
one behind the camera (never visible)."""
import math

import bpy


def build(k):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cube = bpy.context.object
    k.stage.place(k.camera, cube, 0.5, 0.9, 3.0)
    m = bpy.data.materials.new("c")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = k.hexc("#d9a441")
    cube.data.materials.append(m)
    bpy.ops.object.light_add(type="SUN")
    bpy.context.object.rotation_euler = (math.radians(50), 0, math.radians(30))
    behind = bpy.data.objects.new("behind", None)
    bpy.context.scene.collection.objects.link(behind)
    behind.location = (0, -5, 0)                      # the camera looks +Y from the origin
    # a COMPUTED anchor: a point found per frame on the picture itself (a limb crossing, a contact point), already
    # projected — [x, y, depth, visible] in frame pixels
    corner = lambda kk: [kk.w * 0.25, kk.h * 0.75, 1.0, True]  # noqa: E731
    return {"objects": {"cube": cube},
            "anchors": {"top": (cube, (0, 0, 0.5)), "far": (behind, (0, 0, 0)), "corner": corner}}


def pose(k, t):
    bpy.data.objects["Cube"].rotation_euler = (0.4, 0.2, 0.6 * t)
