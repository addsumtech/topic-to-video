"""PRODUCT MATERIALS — the finishes the craft study saw on real products, as Principled BSDF presets.

WHY. The 2026-11-11 surface measure (references/craft-study.md, P8) put a number on what everyone sees between a B&O
frame and ours: in their films 54-92 % of frames show a large surface the light has MODELLED (a continuous ramp of
>= 25 luma across a region); in ours 10-29 %. A plate's parts carried roughness and coat values, but the ANC earbud
still rendered as a clay model: one flat grey per part. Two things were missing. The finish: each product surface is a
specific manufactured finish (Strebel's "design guide" names a material, a thickness, a finish and a process for every
part — so a film's object should too). And what the finish reflects: a glossy surface is only as interesting as the
studio it mirrors (see `studio.product_light`).

Each preset is a manufactured finish with the values that make it read as that finish under a studio light. `finish`
returns a material; `apply` sets it on objects. Colours are the THING's colours (sRGB hex), never the film's palette.

    m = materials.finish("gloss_plastic", "#f6f6f4", name="shell")
"""
import bpy

# name: the Principled inputs that distinguish it (the rest stay at Blender's defaults). Values chosen per finish:
#   gloss_plastic  injection-moulded, polished tool: low roughness under a clear coat (AirPods, TE keys' tops)
#   satin_plastic  bead-blasted tool: a broad soft sheen (most housings, Nothing's back)
#   soft_touch     rubberised paint: almost no specular, a velvet edge (remote controls, grips)
#   silicone       ear tips, seals: soft, a little subsurface glow at thin edges
#   anodized_alu   bead-blasted then anodised: a satin metal, faintly brushed (MacBook, Beolab, OP-1 field)
#   brushed_steel  long grain highlights across the brush direction
#   polished_metal chrome, stainless trims: a mirror, all of its look is what it reflects
#   copper         refrigerant tube, voice coils: warm metal, mid roughness
#   enamel         painted sheet steel (white goods): a glossy paint over a flat panel
#   pcb            solder mask over a green board: glossy, a little coat
#   ceramic        black chip packages, white ceramics: dense, low-sheen
#   glass          cover glass, lenses, clear polycarbonate (Dyson's bin)
#   fabric         speaker cloth (B&O): matte with sheen at grazing angles
#   wood           oiled oak (B&O lamellas): matte, warm
FINISHES = {
    "gloss_plastic": dict(rough=0.14, coat=1.0, coat_rough=0.04, sss=0.04),
    "satin_plastic": dict(rough=0.38, coat=0.0),
    "soft_touch": dict(rough=0.72, spec=0.25, sheen=0.25),
    "silicone": dict(rough=0.42, sss=0.35, spec=0.35),
    "anodized_alu": dict(rough=0.3, metal=1.0, aniso=0.35),
    "brushed_steel": dict(rough=0.22, metal=1.0, aniso=0.75),
    "polished_metal": dict(rough=0.06, metal=1.0),
    "copper": dict(rough=0.22, metal=1.0, aniso=0.2),
    "enamel": dict(rough=0.2, coat=0.7, coat_rough=0.06),
    "pcb": dict(rough=0.3, coat=0.5, coat_rough=0.1),
    "ceramic": dict(rough=0.32, spec=0.5),
    "glass": dict(rough=0.02, transmission=1.0, ior=1.47),
    "fabric": dict(rough=0.9, spec=0.15, sheen=0.6),
    "wood": dict(rough=0.55, spec=0.35),
}


def _lin(hexc):
    h = hexc.lstrip("#")
    if len(h) != 6:
        raise ValueError("materials: colour must be #rrggbb, got %r" % hexc)
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)


def _set(p, names, v):
    """Set the first Principled input that exists under one of `names` (input names moved between Blender 3, 4, 5)."""
    for n in names:
        if n in p.inputs:
            p.inputs[n].default_value = v
            return True
    return False


def finish(kind, colour, name=None, emit=None):
    """A material of the manufactured finish `kind` in `colour` (#rrggbb). `emit` = (#rrggbb, strength) for a part
    that glows (an LED, a lit screen). Raises on an unknown finish: a guessed finish is a wrong object."""
    if kind not in FINISHES:
        raise ValueError("materials: unknown finish %r — one of %s" % (kind, ", ".join(sorted(FINISHES))))
    f = FINISHES[kind]
    m = bpy.data.materials.new(name or kind)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = _lin(colour)
    p.inputs["Roughness"].default_value = f["rough"]
    p.inputs["Metallic"].default_value = f.get("metal", 0.0)
    _set(p, ("Specular IOR Level", "Specular"), f.get("spec", 0.5))
    _set(p, ("Coat Weight", "Clearcoat"), f.get("coat", 0.0))
    _set(p, ("Coat Roughness", "Clearcoat Roughness"), f.get("coat_rough", 0.03))
    _set(p, ("Subsurface Weight", "Subsurface"), f.get("sss", 0.0))
    if f.get("sss"):
        _set(p, ("Subsurface Radius",), (0.6, 0.35, 0.25))
        _set(p, ("Subsurface Scale",), 0.05)
    _set(p, ("Anisotropic",), f.get("aniso", 0.0))
    _set(p, ("Sheen Weight", "Sheen"), f.get("sheen", 0.0))
    _set(p, ("Transmission Weight", "Transmission"), f.get("transmission", 0.0))
    if "ior" in f:
        _set(p, ("IOR",), f["ior"])
    if emit:
        _set(p, ("Emission Color", "Emission"), _lin(emit[0]))
        _set(p, ("Emission Strength",), float(emit[1]))
    return m


def apply(objs, m):
    """Give every object in `objs` the material `m` (replacing what it had)."""
    for ob in objs:
        if ob.type != "MESH":
            continue
        ob.data.materials.clear()
        ob.data.materials.append(m)


def chamfer(ob, width, segments=3):
    """A small bevel on every hard edge so the edge catches a highlight (the craft study: OP-XY's keys, MacBook's lid
    edge). `width` in the object's units; harden normals keep the faces flat between the rounded edges."""
    if width <= 0:
        raise ValueError("materials.chamfer: width must be > 0")
    bev = ob.modifiers.new("chamfer", "BEVEL")
    bev.width = width
    bev.segments = segments
    bev.limit_method = "ANGLE"
    if hasattr(bev, "harden_normals"):
        bev.harden_normals = True
    return bev
