"""GLB FOR THREE.JS — a Blender-built object exported for a film page's 3D stage (Stage3D.glb), optionally with its
ambient occlusion baked by Cycles into a second UV set (the hybrid: Blender's light, three.js's speed and page).

    glb.export(objs, "/film/models/scanner.glb", ao=2048)   # -> {"glb": path, "ao": ".../scanner_ao.png" | None}

WHY (measured on an MRI scanner rendered both ways, 2026-11-25, film_work/three_vs_blender):
- glTF's sheen has no weight. The exporter writes Principled "Sheen Tint" (white by default) as sheenColorFactor and
  drops "Sheen Weight", so a 0.25 sheen arrives in three.js as a full white one: a dark plinth and a slate fabric
  pad rendered light grey. Export folds the weight into the tint (and puts both back afterwards).
- The baked AO atlas gave the three.js render the contact darkening Cycles has (bore interior, base joints) for one
  ~100 s bake per model, not per frame. It darkens what the environment light reaches (three.js aoMap), so the page
  lights the model with an HDRI (Stage3D.hdri) for it to show.
The scene is left as it was: the bake works on a joined duplicate that is deleted afterwards.
"""
import os

import bpy

from . import render as _render


def _meshes(objs):
    out, seen = [], set()

    def walk(o):
        if o.name in seen:
            return
        seen.add(o.name)
        if o.type in ("MESH", "CURVE", "FONT", "SURFACE", "META") and not o.hide_render:
            out.append(o)
        for c in o.children:
            walk(c)
    for o in objs:
        walk(o)
    return out


def _fold_sheen(mats):
    undo = []
    for m in mats:
        if not (m and m.use_nodes):
            continue
        for p in m.node_tree.nodes:
            if p.type != "BSDF_PRINCIPLED":
                continue
            w = p.inputs["Sheen Weight"].default_value
            if 0 < w < 1:
                t = tuple(p.inputs["Sheen Tint"].default_value)
                undo.append((p, w, t))
                p.inputs["Sheen Tint"].default_value = (t[0] * w, t[1] * w, t[2] * w, t[3])
                p.inputs["Sheen Weight"].default_value = 1.0
    return undo


def export(objs, path, ao=0, ao_distance=0.6, ao_samples=128, ground=True):
    """Export the objects (and their children) to `path` (.glb), modifiers applied. `ao` > 0 bakes Cycles ambient
    occlusion at that resolution into a second UV set (TEXCOORD_1) and writes <path>_ao.png beside it; `ground` bakes it
    against a floor under the object's lowest point (contact darkening where it stands)."""
    if not path.endswith(".glb"):
        raise ValueError("glb.export: the path must end in .glb (%s)" % path)
    parts = _meshes(objs)
    if not parts:
        raise ValueError("glb.export: none of the objects is (or has) a renderable mesh")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    sc = bpy.context.scene
    view = bpy.context.view_layer
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    view.objects.active = parts[0]
    bpy.ops.object.duplicate()
    dups = list(bpy.context.selected_objects)
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.convert(target="MESH")            # bevels, booleans, text: real geometry
    view.objects.active = dups[0]
    if len(dups) > 1:
        bpy.ops.object.join()
    model = view.objects.active
    model.name = os.path.splitext(os.path.basename(path))[0]
    ao_path = None
    try:
        if ao:
            ao_path = os.path.splitext(path)[0] + "_ao.png"
            _bake_ao(sc, model, int(ao), ao_path, ao_distance, ao_samples, ground)
        undo = _fold_sheen(model.data.materials)
        try:
            bpy.ops.object.select_all(action="DESELECT")
            model.select_set(True)
            bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                                      export_lights=False, export_cameras=False)
        finally:
            for p, w, t in undo:
                p.inputs["Sheen Weight"].default_value = w
                p.inputs["Sheen Tint"].default_value = t
    finally:
        me = model.data
        bpy.data.objects.remove(model, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    return {"glb": path, "ao": ao_path}


def _bake_ao(sc, model, res, out, distance, samples, ground):
    layers = model.data.uv_layers
    if layers.new(name="ao") is None:
        raise RuntimeError("glb.export: the model already has the maximum number of UV sets; cannot add the AO atlas")
    # by index: a layer reference taken before new() dangles after it (the collection reallocates)
    layers.active_index = len(layers) - 1
    bpy.ops.object.select_all(action="DESELECT")
    model.select_set(True)
    bpy.context.view_layer.objects.active = model
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    model.data.uv_layers.active_index = 0   # the atlas is TEXCOORD_1; the model's own UVs stay TEXCOORD_0
    floor = None
    if ground:
        zmin = min((model.matrix_world @ v.co).z for v in model.data.vertices)
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, zmin))
        floor = bpy.context.active_object
    img = bpy.data.images.new(model.name + "_ao", res, res, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    added = []
    for m in model.data.materials:
        if not (m and m.use_nodes):
            continue
        n = m.node_tree.nodes.new("ShaderNodeTexImage")
        n.image = img
        m.node_tree.nodes.active = n
        added.append((m, n))
    if not added:
        raise RuntimeError("glb.export: the model has no node materials to bake its AO through")
    saved = _render.snapshot(sc)
    size = (sc.render.resolution_x, sc.render.resolution_y)
    cyc = (sc.cycles.samples, sc.cycles.device) if hasattr(sc, "cycles") else None
    world = sc.world
    try:
        _render.configure(sc, "cycles", "rgb", 64, 64, samples=samples)
        if sc.world is None:
            sc.world = bpy.data.worlds.new("ao_bake")
        dist = sc.world.light_settings.distance
        sc.world.light_settings.distance = distance
        bpy.ops.object.select_all(action="DESELECT")
        model.select_set(True)
        bpy.context.view_layer.objects.active = model
        bpy.ops.object.bake(type="AO", margin=16, uv_layer="ao")
        sc.world.light_settings.distance = dist
        img.filepath_raw = out
        img.file_format = "PNG"
        img.save()
    finally:
        _render.restore(sc, saved)
        sc.render.resolution_x, sc.render.resolution_y = size
        if cyc:
            sc.cycles.samples, sc.cycles.device = cyc
        sc.world = world
        for m, n in added:
            m.node_tree.nodes.remove(n)
        bpy.data.images.remove(img)
        if floor is not None:
            fm = floor.data
            bpy.data.objects.remove(floor, do_unlink=True)
            bpy.data.meshes.remove(fm)
