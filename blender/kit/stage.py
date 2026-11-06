"""Composition in CAMERA space. Measured on the first plate (a GPS satellite, 2026-11-04): placing things in world
space by guess put the Earth off the frame and the satellite edge-on; placing them by where they should fall on the
picture — a screen fraction and a depth — got a composed frame. The camera's frame at a depth is Blender's own
`view_frame`, so lens, sensor fit and aspect are all honoured."""
import bpy
from mathutils import Vector


def frame_at(cam, depth):
    """The camera's four frame corners at `depth` along its view, in world space (top-right, bottom-right,
    bottom-left, top-left — Blender's order)."""
    sc = bpy.context.scene
    bpy.context.view_layer.update()           # a camera just made or moved has a stale matrix_world until this runs
    corners = cam.data.view_frame(scene=sc)
    scale = depth / -corners[0].z
    return [cam.matrix_world @ (c * scale) for c in corners]


def screen_point(cam, sx, sy, depth):
    """The world point that falls at screen fraction (sx, sy) — 0..1 from the TOP-LEFT — at `depth`."""
    tr, br, bl, tl = frame_at(cam, depth)
    top = tl.lerp(tr, sx)
    bottom = bl.lerp(br, sx)
    return top.lerp(bottom, sy)


def place(cam, obj, sx, sy, depth):
    """Put obj's origin where the picture wants it: screen fraction (sx, sy) from the top-left, `depth` away."""
    bpy.context.view_layer.update()
    obj.location = screen_point(cam, sx, sy, depth)


_AXES = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}


def face_toward(obj, local_axis, target, toward_lens=0.0, cam=None):
    """Turn obj so its `local_axis` ('-Z', 'Y', ...) points at `target`, bent toward the lens by `toward_lens`
    (0 = exactly at the target, 1 = at the camera). A satellite's antenna face points at the Earth but is
    bent toward the lens so the array SHOWS — what the viewer needs to see, not what the orbit dictates."""
    bpy.context.view_layer.update()
    want = (Vector(target) - obj.matrix_world.translation).normalized()
    if toward_lens:
        cam = cam or bpy.context.scene.camera
        to_cam = (cam.matrix_world.translation - obj.matrix_world.translation).normalized()
        want = want.lerp(to_cam, toward_lens).normalized()
    up = "Z" if local_axis.lstrip("-") != "Z" else "Y"
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = want.to_track_quat(local_axis, up)


def _bounds(obj):
    bpy.context.view_layer.update()
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return (lo + hi) / 2, max((hi - lo).length, 1e-3)


KEY_E, FILL_E, RIM_E = 3.0, 0.7, 12.0


def product_rig(subject, cam, key_az=35, rim_strength=1.0, exposure=1.0):
    """The craft bar's product light around `subject`, placed from the CAMERA (references/craft-bar.md): a soft key
    in front and to one side, a fill low on the other, and a rim BEHIND the subject that traces its silhouette. The rim
    is light-linked to the subject alone, so it never lifts the floor or the background — the reason product films
    use light linking at all. Sizes and energies scale with the subject. Returns {key, fill, rim} light objects.

    Measured why (2026-11-06): ANC's plates were soft matte objects with almost no highlight (0.04-0.13) and the
    subject_craft numbers of a flat pass.

    `exposure` scales every light alike, keeping the balance: the energies were tuned on a mid-grey sphere, and a
    near-black subject (a switch housing, albedo ~0.03) under the same light rendered as a silhouette with black sides —
    a photographer lights a dark product harder, not differently."""
    import math
    centre, size = _bounds(subject)
    to_cam = cam.matrix_world.translation - centre
    to_cam.z = 0
    f = to_cam.normalized() if to_cam.length > 1e-6 else Vector((0, -1, 0))
    up = Vector((0, 0, 1))
    right = f.cross(up).normalized()
    side = math.tan(math.radians(key_az))
    # irradiance at the subject (W/m^2 before Blender's own falloff): energy = this x distance^2, so the exposure
    # holds whatever the subject's size. KEY/FILL/RIM_E were tuned on a rendered grey sphere (2026-11-06): the first
    # fixed-watt rig blew the sphere out to flat white with no visible rim.
    spots = {"key": (2.2 * f + 2.2 * side * right + 1.5 * up, KEY_E, 1.4),
             "fill": (2.0 * f - 2.4 * right + 0.4 * up, FILL_E, 2.0),
             "rim": (-2.6 * f + 0.5 * right + 1.9 * up, RIM_E * rim_strength, 0.6)}
    rig = {}
    for name, (offset, watts, soft) in spots.items():
        data = bpy.data.lights.new("rig_" + name, "AREA")
        data.energy = exposure * watts * (size * offset.length) ** 2
        data.size = soft * size
        obj = bpy.data.objects.new("rig_" + name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = centre + size * offset
        face_toward(obj, "-Z", centre)
        rig[name] = obj
    receivers = bpy.data.collections.new("rig_rim_receivers")
    receivers.objects.link(subject)
    rig["rim"].light_linking.receiver_collection = receivers
    return rig
