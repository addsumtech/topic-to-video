"""A MacBook Air 13 (M5) for a device plate, built to remotion/src/runtime/deviceSpec.json models.macbook-air-13:
the PUBLISHED case 304.1 x 215.0 x 11.3 mm and display 2560 x 1664 at 224 ppi (apple.com/macbook-air/specs, retrieved
2026-10-30), the display's 2.5 mm top corners and notch (design values there), and body3d's deck layout (keyboard well,
key rows, trackpad, thumb scoop, hinge inset, 6 mm corners, 0.8 mm rim — the 14-inch Pro's measured deck scaled to the
Air, as that file says). NOT published, chosen and said: the base takes 7.7 of the 11.3 mm, the lid 3.6; the key height.

Real geometry, not slabs (the WorkBuddy spike, 2026-11-07: the user found the slab laptop "not like a real MacBook"):
a rounded body with a polished bevel (its own material), a recessed keyboard well whose floor is dark (the boolean
TRANSFERS the cutter's material — without it the floor was bright aluminium between the keys), every keycap standing
0.05 mm clear of that floor (coplanar faces leaked light in Cycles) with its legend, a glass trackpad in a dark seam,
the scoop, a dark hinge barrel, a lid whose chin sinks behind the deck, black glass with the display inset in it, the
notch and its lens. Brushed aluminium is a stretched-noise bump. No brand mark.

make(k, screen_png, W) -> k.lap = {root, base, keys, hinge, lid, screen, tex, uv_point(u, v), normal()}; `tex` is the
screen's image node (a device plate swaps its picture per frame); uv (0, 0) is the display's bottom-left. Units: W
scene units across the case's 304.1 mm."""
import math

import bmesh
import bpy
from mathutils import Vector

CASE_W, CASE_D, CASE_T = 304.1, 215.0, 11.3
LID_T = 3.6
BASE_T = CASE_T - LID_T
CORNER, RIM = 6.0, 0.8
DISP_W, DISP_H = 2560 / 224 * 25.4, 1664 / 224 * 25.4
BEZEL = (CASE_W - DISP_W) / 2
DISP_R = 2.5
WELL = (17.2, 275.7, 109.2)            # from the back edge: start, width, depth
PAD = (127.0, 131.7, 78.1, 4.0)        # width, start from the back edge, depth, corner
SCOOP = 52.2
HINGE_INSET = 36.0
KEY_GAP, KEY_R, KEY_H = 2.6, 0.9, 0.55
ROWS = [
    [1.5] + [1] * 12 + [1],
    [1] * 13 + [1.5],
    [1.5] + [1] * 12 + [1],
    [1.75] + [1] * 11 + [1.75],
    [2.25] + [1] * 10 + [2.25],
    [1, 1, 1, 1.25, 5, 1.25, 1, "L", "UD", "R"],
]
UNITS = 14.5


def _mat(name, rgb, rough, metal=0.0, coat=0.0, aniso=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if coat:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = 0.03
    if aniso and "Anisotropic" in p.inputs:
        p.inputs["Anisotropic"].default_value = aniso
    return m


def _brushed(m, strength=0.04):
    """Bead-blasted / brushed aluminium: a fine noise stretched along x, as a bump (the micro-texture the eye
    reads as metal rather than grey plastic)."""
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.4, 60.0, 60.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.02
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    # a faint roughness variation from the same streaks
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = p.inputs["Roughness"].default_value - 0.04
    mr.inputs["To Max"].default_value = p.inputs["Roughness"].default_value + 0.04
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], p.inputs["Roughness"])
    return m


def _srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def _rr(x0, y0, x1, y1, r_top, r_bot, seg=10):
    """A rounded rectangle's outline, counter-clockwise, y up; separate top and bottom corner radii."""
    pts = []
    corners = [((x1 - r_bot, y0 + r_bot), r_bot, -90), ((x1 - r_top, y1 - r_top), r_top, 0),
               ((x0 + r_top, y1 - r_top), r_top, 90), ((x0 + r_bot, y0 + r_bot), r_bot, 180)]
    for (cx, cy), r, a0 in corners:
        if r <= 1e-6:
            pts.append((cx, cy))
            continue
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _prism(bm, outline, z0, z1, mat_top=0, mat_side=0, mat_bot=0):
    """Extrude a 2D outline (x, y) between z0 and z1 into bm; returns the top face."""
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in outline]
    top = bm.faces.new(hi)
    top.material_index = mat_top
    bot = bm.faces.new(list(reversed(lo)))
    bot.material_index = mat_bot
    n = len(outline)
    for i in range(n):
        f = bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
        f.material_index = mat_side
    return top


def _obj(name, bm, mats, parent=None, smooth_angle=35, bevel=None, bevel_mat=-1):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    for m in mats:
        me.materials.append(m)
    if bevel:
        mod = ob.modifiers.new("edge", "BEVEL")
        mod.width, mod.segments, mod.limit_method = bevel, 4, "ANGLE"
        mod.angle_limit = math.radians(50)
        mod.harden_normals = True
        mod.material = bevel_mat
    for poly in me.polygons:
        poly.use_smooth = True
    if hasattr(me, "set_sharp_from_angle"):
        me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    if parent is not None:
        ob.parent = parent
    return ob


# the US layout's legends, row by row, in the order the keys are laid (runtime/laptop3d.tsx ROWS)
LEGENDS = [
    ["esc"] + ["F%d" % i for i in range(1, 13)] + [""],
    list("`1234567890-=") + ["delete"],
    ["tab"] + list("QWERTYUIOP[]") + ["\\"],
    ["caps lock"] + list("ASDFGHJKL;'") + ["return"],
    ["shift"] + list("ZXCVBNM,./") + ["shift"],
    ["fn", "control", "option", "command", "", "command", "option", "<", "^", "v", ">"],
]


def _legends(caps, z, root):
    """A legend on every key: a single character centred, a word small at the key's lower left (as Apple sets them),
    in one light-grey text mesh per key. Drawn as type because a MacBook's keys carry type; at film distance it is
    texture the eye uses to read the keyboard as real."""
    ink = _mat("legend", _srgb("#c9cbd0"), 0.5)
    flat = [lab for row in LEGENDS for lab in row]
    for (x0, y0, x1, y1, ri, i) in caps:
        lab = flat[i] if i < len(flat) else ""
        if not lab:
            continue
        cu = bpy.data.curves.new("leg%d" % i, "FONT")
        cu.body = lab
        word = len(lab) > 1 and not lab.startswith("F")
        cu.size = 2.0 if word else (2.4 if ri == 0 else 4.2)
        cu.align_x, cu.align_y = ("LEFT", "BOTTOM") if word else ("CENTER", "CENTER")
        ob = bpy.data.objects.new("leg%d" % i, cu)
        bpy.context.collection.objects.link(ob)
        ob.data.materials.append(ink)
        ob.parent = root
        ob.location = (x0 + 1.4, y0 + 1.3, z) if word else ((x0 + x1) / 2, (y0 + y1) / 2, z)


def make(k, screen_png, W=2.2):
    s = W / CASE_W
    alu = _brushed(_mat("alu", _srgb("#d9dadd"), 0.30, metal=1.0, aniso=0.25))
    edge = _mat("alu_edge", _srgb("#eceef0"), 0.12, metal=1.0)            # the polished chamfer
    well = _mat("well", _srgb("#26272b"), 0.55)
    keycap = _mat("keycap", _srgb("#151618"), 0.42, coat=0.15)
    pad = _mat("pad", _srgb("#cfd1d5"), 0.22, metal=0.85)
    seam = _mat("seam", _srgb("#3a3b3f"), 0.6)
    black = _mat("glass_black", _srgb("#030304"), 0.18, coat=0.35)
    hinge_m = _mat("hinge", _srgb("#1a1b1e"), 0.35, metal=0.6)
    lens = _mat("lens", _srgb("#101522"), 0.05, coat=1.0)

    root = bpy.data.objects.new("laptop", None)
    bpy.context.collection.objects.link(root)
    root.scale = (s, s, s)                         # everything below is in millimetres
    D2 = CASE_D / 2                                 # base: x right, y toward the back (+), z up; centred

    # ── the base: a rounded slab with a polished edge, the keyboard well cut into its top, the thumb scoop ──
    bm = bmesh.new()
    _prism(bm, _rr(-CASE_W / 2, -D2, CASE_W / 2, D2, CORNER, CORNER, 12), 0.0, BASE_T)
    base = _obj("lap_base", bm, [alu, edge], parent=root, bevel=RIM, bevel_mat=1)
    # the well: a rounded box cut 0.7 mm into the top, carrying its dark floor in
    wy1 = D2 - WELL[0]
    wy0 = wy1 - WELL[2]
    bm = bmesh.new()
    _prism(bm, _rr(-WELL[1] / 2, wy0, WELL[1] / 2, wy1, 3.2, 3.2, 8), BASE_T - 0.7, BASE_T + 2)
    cut = _obj("well_cut", bm, [well])
    cut.display_type = "WIRE"
    cut.hide_render = True
    b1 = base.modifiers.new("well", "BOOLEAN")
    b1.operation, b1.object, b1.solver = "DIFFERENCE", cut, "EXACT"
    b1.material_mode = "TRANSFER"                  # the well's floor and walls take the cutter's dark material
    # the thumb scoop: a flattened cylinder through the front edge's middle
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.0, depth=1.0)
    sc_ = bpy.context.object
    sc_.name = "scoop_cut"
    sc_.rotation_euler = (math.radians(90), 0, 0)
    sc_.scale = (SCOOP / 2, BASE_T * 0.45, 6.0)
    sc_.location = (0, -D2 - 1.0, BASE_T)
    sc_.hide_render = True
    sc_.display_type = "WIRE"
    sc_.parent = root
    b2 = base.modifiers.new("scoop", "BOOLEAN")
    b2.operation, b2.object, b2.solver = "DIFFERENCE", sc_, "EXACT"
    cut.parent = root

    # ── the keys: every keycap of the six rows, rounded, standing in the well ──
    bm = bmesh.new()
    unit, row_d = WELL[1] / UNITS, WELL[2] / len(ROWS)
    floor = BASE_T - 0.7
    caps = []
    for ri, row in enumerate(ROWS):
        x = -WELL[1] / 2
        y_top = wy1 - ri * row_d                     # rows run from the back (function row) to the front
        for kw in row:
            if kw in ("L", "R"):
                boxes = [(x, y_top - row_d / 2, x + unit, y_top - row_d)]
                x += unit
            elif kw == "UD":
                boxes = [(x, y_top, x + unit, y_top - row_d / 2), (x, y_top - row_d / 2, x + unit, y_top - row_d)]
                x += unit
            else:
                boxes = [(x, y_top, x + kw * unit, y_top - row_d)]
                x += kw * unit
            for (xa, ya, xb, yb) in boxes:
                g = KEY_GAP / 2
                _prism(bm, _rr(xa + g, yb + g, xb - g, ya - g, KEY_R, KEY_R, 4), floor + 0.05, floor + 0.7 + KEY_H)
                caps.append((xa + g, yb + g, xb - g, ya - g, ri, len(caps)))
    keys = _obj("lap_keys", bm, [keycap], parent=root, smooth_angle=40)
    _legends(caps, floor + 0.7 + KEY_H + 0.01, root)

    # ── the trackpad: glass flush with the deck, a dark seam around it ──
    py1 = D2 - PAD[1]
    py0 = py1 - PAD[2]
    bm = bmesh.new()
    _prism(bm, _rr(-PAD[0] / 2 - 0.35, py0 - 0.35, PAD[0] / 2 + 0.35, py1 + 0.35, PAD[3] + 0.35, PAD[3] + 0.35, 8),
           BASE_T - 0.2, BASE_T + 0.01)
    _obj("lap_seam", bm, [seam], parent=root)
    bm = bmesh.new()
    _prism(bm, _rr(-PAD[0] / 2, py0, PAD[0] / 2, py1, PAD[3], PAD[3], 8), BASE_T - 0.2, BASE_T + 0.02)
    _obj("lap_pad", bm, [pad], parent=root)

    # ── the hinge: a dark barrel along the back edge between its insets ──
    hw = CASE_W / 2 - HINGE_INSET
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1.0, depth=1.0)
    hb = bpy.context.object
    hb.name = "lap_hinge_barrel"
    hb.rotation_euler = (0, math.radians(90), 0)
    hb.scale = (LID_T * 0.62, LID_T * 0.62, 2 * hw)
    hb.location = (0, D2 - LID_T * 0.5, BASE_T + 0.2)
    hb.data.materials.append(hinge_m)
    hb.parent = root
    for poly in hb.data.polygons:
        poly.use_smooth = True

    # ── the lid: hinged at the back edge; its chin drops 8 mm behind the deck (laptop3d hinge.liftMm) ──
    hinge = bpy.data.objects.new("lap_hinge", None)
    bpy.context.collection.objects.link(hinge)
    hinge.parent = root
    hinge.location = (0, D2 - LID_T * 0.5, BASE_T + 0.2)
    # lid local: x right, z up the lid (0 at the hinge), y = thickness; its face (glass, display) faces -y
    L0, L1 = -8.0, CASE_D - 8.0
    bm = bmesh.new()
    outline = _rr(-CASE_W / 2, L0, CASE_W / 2, L1, CORNER, 1.5, 12)
    lo = [bm.verts.new((x, -LID_T / 2, z)) for x, z in outline]
    hi = [bm.verts.new((x, LID_T / 2, z)) for x, z in outline]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    n = len(outline)
    for i in range(n):
        bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    lid = _obj("lap_lid", bm, [alu, edge], parent=hinge, bevel=RIM * 0.75, bevel_mat=1)
    # the black glass over the face, inside an aluminium rim of RIM mm
    bm = bmesh.new()
    gl = _rr(-CASE_W / 2 + RIM, L0, CASE_W / 2 - RIM, L1 - RIM, CORNER - RIM, 0.0, 12)
    bm.faces.new([bm.verts.new((x, -LID_T / 2 - 0.05, z)) for x, z in reversed(gl)])
    _obj("lap_glass", bm, [black], parent=hinge)
    # the display: rounded top corners, inset by the bezel; UV (0,0) bottom-left of the panel
    top = L1 - BEZEL
    bot = top - DISP_H
    dx0, dx1 = -DISP_W / 2, DISP_W / 2
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    out = _rr(dx0, bot, dx1, top, DISP_R, 0.0, 8)
    f = bm.faces.new([bm.verts.new((x, -LID_T / 2 - 0.1, z)) for x, z in reversed(out)])
    for lp in f.loops:
        x, _y, z = lp.vert.co
        lp[uvl].uv = ((x - dx0) / DISP_W, (z - bot) / DISP_H)
    scr_m = bpy.data.materials.new("screen")
    scr_m.use_nodes = True
    nt = scr_m.node_tree
    p = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(screen_png)
    tex.extension = "EXTEND"
    p.inputs["Base Color"].default_value = (0, 0, 0, 1)      # a display only glows
    nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = 1.0
    p.inputs["Roughness"].default_value = 0.05
    p.inputs["Coat Weight"].default_value = 1.0
    p.inputs["Coat Roughness"].default_value = 0.03
    screen = _obj("lap_screen", bm, [scr_m], parent=hinge)
    # the notch: the camera housing in the top bezel, with its lens
    nw, nh = DISP_W * 0.07, DISP_H * 0.035
    bm = bmesh.new()
    nout = _rr(-nw / 2, top - nh, nw / 2, top + 0.01, 0.0, 1.6, 6)
    bm.faces.new([bm.verts.new((x, -LID_T / 2 - 0.15, z)) for x, z in reversed(nout)])
    _obj("lap_notch", bm, [black], parent=hinge)
    bm = bmesh.new()
    lens_c = (0.0, -LID_T / 2 - 0.2, top + BEZEL / 2)
    ring = [bm.verts.new((lens_c[0] + 0.9 * math.cos(2 * math.pi * i / 24), lens_c[1],
                          lens_c[2] + 0.9 * math.sin(2 * math.pi * i / 24))) for i in range(24)]
    bm.faces.new(list(reversed(ring)))
    _obj("lap_lens", bm, [lens], parent=hinge)

    def uv_point(u, v):
        return screen.matrix_world @ Vector((dx0 + u * DISP_W, -LID_T / 2 - 0.1, bot + v * DISP_H))

    def face_normal():
        return (hinge.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()

    k.lap = {"root": root, "base": base, "keys": keys, "hinge": hinge, "lid": lid, "screen": screen, "tex": tex,
             "uv_point": uv_point, "normal": face_normal}
    return root
