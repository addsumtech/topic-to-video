"""A test scene for blender/kit/studio.product_light + materials: one white sphere in a manufactured finish, lit by
the product studio (params.lit = False lights it the old way: a flat-colour world and one soft key). Every finish is
built once so a renamed Principled input fails here, not in a film."""
import math

import bpy


def build(k):
    for kind in k.materials.FINISHES:
        k.materials.finish(kind, "#808080", name="probe_" + kind)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=64, ring_count=32)
    ball = bpy.context.object
    bpy.ops.object.shade_smooth()
    k.stage.place(k.camera, ball, 0.5, 0.5, 5.0)
    ball.data.materials.append(k.materials.finish(k.params.get("finish", "gloss_plastic"), "#f4f4f2", name="ball"))
    if k.params.get("lit", True):
        k.studio.product_light([ball], k.camera)
    else:
        w = bpy.data.worlds.new("flat")
        bpy.context.scene.world = w
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs["Color"].default_value = k.hexc("#f2f1ee")
        bpy.ops.object.light_add(type="AREA", location=(-3.5, -4.0, 4.0))
        bpy.context.object.data.energy = 900
        bpy.context.object.data.size = 4.0
    return {"objects": {"ball": ball}, "anchors": {}}


def pose(k, t):
    pass
