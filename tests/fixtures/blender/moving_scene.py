"""A test scene: a cube that starts mid-frame and leaves it to the right by the last frame. Anchors on its front face
(toward the lens) and its back face (hidden by the cube itself)."""
import bpy


def build(k):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cube = bpy.context.object
    cube.name = "mover"
    k.stage.place(k.camera, cube, 0.5, 0.5, 6.0)
    k.base = tuple(cube.location)
    bpy.ops.object.light_add(type="SUN")
    return {"objects": {"mover": cube}, "anchors": {"front": (cube, (0, -0.5, 0)), "back": (cube, (0, 0.5, 0))}}


def pose(k, t):
    u = t / max(1e-6, (k.frames - 1) / k.fps)
    x, y, z = k.base
    bpy.data.objects["mover"].location = (x + 9.0 * u, y, z)
