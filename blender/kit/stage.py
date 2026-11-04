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
