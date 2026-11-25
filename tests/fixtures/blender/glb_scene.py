"""A small scene for the --glb export test: a block standing on a plinth (contact to darken) with a fabric top whose
sheen weight must survive the export."""
import bpy


def build(k):
    from blender.kit import materials as M
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 4, 0.6))
    block = bpy.context.active_object
    block.scale = (0.6, 0.6, 0.6)
    M.apply([block], M.finish("satin_plastic", "#e8e8e6", "shell"))
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 4, 0.15))
    plinth = bpy.context.active_object
    plinth.scale = (1.6, 1.6, 0.3)
    M.apply([plinth], M.finish("soft_touch", "#3a3e44", "plinth"))   # sheen weight 0.25
    return {"objects": {"block": block, "plinth": plinth}}


def pose(k, t):
    pass
