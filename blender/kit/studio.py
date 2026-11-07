"""A product studio for a device plate: a real studio photographed all round (an HDRI, Poly Haven CC0) as the light
and as what metal and glass mirror; a seamless sweep (a photographer's cyclorama: the floor curves up into the wall,
so there is no horizon line); a few soft boxes out of frame for the edges to catch.

Measured on the WorkBuddy spike (2026-11-07): three soft boxes alone left the aluminium clean but EMPTY — the user read
it as "not a real MacBook"; the HDRI is what the metal needed. A world of one flat colour drew a desk-to-wall horizon
line across the frame; the sweep removed it. Under AgX a screen's whites rendered grey: a device plate is viewed under
Standard (docskit.standard_view on the WorkBuddy film said the same of paper)."""
import math
import os

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
HDRI = os.path.join(HERE, "hdri", "studio_small_09_1k.hdr")


def _srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def world(strength=0.8, hdri=HDRI):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("studio")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    if not os.path.isfile(hdri):
        raise RuntimeError("the studio HDRI %s is missing — the kit ships it (blender/kit/hdri/)" % hdri)
    env = w.node_tree.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(hdri, check_existing=True)
    w.node_tree.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    sc.view_settings.view_transform = "Standard"
    try:
        sc.view_settings.look = "None"
    except TypeError:
        pass
    return w


def sweep(ground="#c8d0cd", depth=60.0, rise=8.0, wall=40.0, half_width=80.0):
    """The cyclorama: a floor running from the lens (`depth` units toward it) into a quarter-circle of radius `rise`
    that turns up into a wall. Its colour is the ground the shot dissolves into."""
    prof = [(-depth + i * (depth + 6) / 40, 0.0) for i in range(41)]
    prof += [(6 + rise * math.sin(math.radians(90 * i / 24)), rise * (1 - math.cos(math.radians(90 * i / 24))))
             for i in range(1, 25)]
    prof += [(6 + rise, rise + i * wall / 10) for i in range(1, 11)]
    bm = bmesh.new()
    rows = [[bm.verts.new((x, y, z)) for y, z in prof] for x in (-half_width, half_width)]
    for j in range(len(prof) - 1):
        bm.faces.new((rows[0][j], rows[1][j], rows[1][j + 1], rows[0][j + 1]))
    me = bpy.data.meshes.new("sweep")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("sweep", me)
    bpy.context.scene.collection.objects.link(ob)
    for poly in me.polygons:
        poly.use_smooth = True
    m = bpy.data.materials.new("sweep")
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*_srgb(ground), 1)
    p.inputs["Roughness"].default_value = 0.55
    me.materials.append(m)
    return ob


def softboxes(target, scale=0.35):
    """Three soft boxes the lens never sees, aimed at `target`: above, left and behind. `scale` sets their share of the
    light (the HDRI does most of it)."""
    out = []
    for name, loc, size, energy in (("box_top", (0, -1.5, 9), (10, 6), 220), ("box_left", (-7, -2, 3), (3, 6), 160),
                                    ("box_back", (2, 7, 4), (8, 3), 90)):
        loc = Vector(loc) + Vector(target) - Vector((0, 0, 0.8))
        bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
        bx = bpy.context.object
        bx.name = name
        bx.scale = (size[0], size[1], 1)
        bx.rotation_euler = (Vector(target) - loc).to_track_quat("Z", "Y").to_euler()
        em = bpy.data.materials.new(name)
        em.use_nodes = True
        nt = em.node_tree
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Strength"].default_value = scale * energy / (size[0] * size[1])
        nt.links.new(e.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])
        bx.data.materials.append(em)
        bx.visible_camera = False
        out.append(bx)
    return out


def tune_cycles(samples=24):
    """Cycles as the spike measured it (~25 s a 1920x1080 frame on an M4's GPU at 24 samples): adaptive sampling,
    OIDN, fewer bounces, no caustics, persistent data (only the camera and the screen's picture change)."""
    sc = bpy.context.scene
    if sc.render.engine != "CYCLES":
        return
    sc.cycles.samples = int(samples)
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.04
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces, sc.cycles.glossy_bounces, sc.cycles.diffuse_bounces = 6, 4, 3
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    sc.render.use_persistent_data = True
