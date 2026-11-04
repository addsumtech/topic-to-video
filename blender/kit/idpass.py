"""The ID pass: each named object flat in its own colour, at half size, so the host can say where each object is on
every frame (scripts/blender_plate.py boxes_from_ids). EEVEE in Blender 5.2 offers no Object Index pass (its render
layer gives Image and Alpha only — probed 2026-11-04), so this is a Workbench render: flat light, object colour,
no anti-aliasing, the Standard view transform so a colour comes out as written. 0.72 s a frame at 960x540."""
import colorsys

import bpy

from . import render as _render


def palette(names):
    """{name: '#rrggbb'}: fully saturated, evenly spaced hues, assigned in sorted-name order (deterministic)."""
    names = sorted(names)
    out = {}
    for i, n in enumerate(names):
        r, g, b = colorsys.hsv_to_rgb(i / max(1, len(names)), 1.0, 1.0)
        out[n] = "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))
    return out


def _srgb(hexs):
    return tuple(int(hexs[i:i + 2], 16) / 255 for i in (1, 3, 5))


def assign(objects, colors):
    """Colour every object (and everything parented under it) with its ID; everything else black, so it still
    hides what it stands in front of but is never mistaken for a named object."""
    named = set()
    for name, obj in objects.items():
        c = _srgb(colors[name])
        for o in [obj, *obj.children_recursive]:
            o.color = (*c, 1.0)
            named.add(o.name)
    for o in bpy.context.scene.objects:
        if o.name not in named:
            o.color = (0.0, 0.0, 0.0, 1.0)


def render(sc, path):
    keep = _render.snapshot(sc)
    try:
        sc.render.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading
        sh.light = "FLAT"
        sh.color_type = "OBJECT"
        sc.display.render_aa = "OFF"
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
        sc.render.film_transparent = True
        sc.render.resolution_percentage = 50
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
    finally:
        _render.restore(sc, keep)
