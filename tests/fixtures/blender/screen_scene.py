"""A test scene that places by stage.screen_point straight away in build (no place() call first)."""
import bpy


def build(k):
    p = k.stage.screen_point(k.camera, 0.5, 0.5, 6.0)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=p)
    cube = bpy.context.object
    bpy.ops.object.light_add(type="SUN")
    return {"objects": {"cube": cube}, "anchors": {"c": (cube, (0, -0.5, 0))}}      # its face toward the lens


def pose(k, t):
    pass
