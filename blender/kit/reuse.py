"""NOT RENDERING WHAT DID NOT CHANGE. A plate's frames are rendered one by one, and most of a beat's picture often holds
still: the camera waits for its cue, or a camera and an Earth hold for 351 frames while a small satellite moves (the
first acceptance plates, 2026-11-04: 22 minutes of EEVEE for that one beat). So each frame is classified:

  copy   nothing the picture depends on changed since the last frame — the last frame IS this one;
  patch  only some objects moved, the camera, lights and world held — only the rectangle they cover (then and now,
         with a margin) is rendered, and pasted over the last frame;
  full   anything else.

What "the picture depends on" is read from the scene (signature below): every object's matrix, visibility and
modifier settings, every material's, world's and node group's node values, every light and camera setting. A pose
can change something it does not read (a mesh's vertices, an image file): so a copy and a patch are VERIFIED — the
first of each run, and every CHECK_EVERY after, is rendered whole as well and compared. A mismatch turns reuse off
for the rest of the plate and re-renders the frames since the last good check (never quietly wrong frames).
A scene opts out with `k.reuse = False`, and anything animated by Blender itself (keyframes, drivers, a Scene Time
node, an image sequence) turns reuse off from the start."""
import bpy
from bpy_extras.object_utils import world_to_camera_view

CHECK_EVERY = 24          # a reused frame is verified whole at least this often
MARGIN = 0.04             # of the frame's long side, round a patch (a moving object's soft edge, its near shadow)
MAX_PATCH = 0.6           # a patch over this share of the frame is rendered whole instead (no gain)
MEAN_TOL = 0.75 / 255     # verification: mean |difference| over the frame ...
PEAK_TOL = 24 / 255       # ... and the 99.9th percentile of it


def _r(v, n=6):
    try:
        return tuple(round(float(x), n) for x in v)
    except TypeError:
        return round(float(v), n) if isinstance(v, (int, float)) else str(v)


def _props(obj):
    out = []
    for p in obj.bl_rna.properties:
        if p.is_readonly or p.type not in ("FLOAT", "INT", "BOOLEAN", "ENUM"):
            continue
        try:
            out.append((p.identifier, _r(getattr(obj, p.identifier))))
        except (AttributeError, TypeError, ValueError):
            continue
    return tuple(out)


def _tree(nt):
    if nt is None:
        return ()
    out = []
    for n in nt.nodes:
        row = [n.name, n.bl_idname, _props(n)]
        for s in n.inputs:
            if hasattr(s, "default_value"):
                row.append(_r(s.default_value))
        if getattr(n, "color_ramp", None) is not None:
            row.append(tuple((_r(e.position), _r(e.color)) for e in n.color_ramp.elements))
        out.append(tuple(row))
    return tuple(out)


def blocked(sc):
    """Why nothing may be reused on this scene, or None: Blender animates something itself, frame by frame."""
    pools = (bpy.data.objects, bpy.data.materials, bpy.data.worlds, bpy.data.lights, bpy.data.cameras,
             bpy.data.node_groups, bpy.data.meshes, bpy.data.scenes, bpy.data.shape_keys)
    for pool in pools:
        for idb in pool:
            ad = getattr(idb, "animation_data", None)
            if ad and (ad.action or len(ad.drivers)):
                return "%s %r is animated by keyframes or drivers" % (type(idb).__name__, idb.name)
    trees = [m.node_tree for m in bpy.data.materials if m.node_tree] + [w.node_tree for w in bpy.data.worlds if w.node_tree] \
        + list(bpy.data.node_groups)
    for nt in trees:
        for n in nt.nodes:
            if n.bl_idname in ("GeometryNodeInputSceneTime",):
                return "node %r reads the scene's time" % n.name
            img = getattr(n, "image", None)
            if img is not None and img.source in ("SEQUENCE", "MOVIE"):
                return "image %r is a sequence or a movie" % img.name
    return None


def object_sig(o):
    mods = tuple((m.name, _props(m)) for m in o.modifiers)
    return (_r(tuple(x for row in o.matrix_world for x in row)), o.hide_render, o.visible_camera, o.visible_shadow,
            o.data.name if o.data else None, mods, _r(tuple(o.color)))


def scene_sig(sc, cam):
    """(the whole picture's settings except object placement, {object name: its own signature})."""
    world = sc.world
    lights = tuple((l.name, _props(l)) for l in bpy.data.lights)
    cams = (_r(tuple(x for row in cam.matrix_world for x in row)), _props(cam.data))
    mats = tuple((m.name, _tree(m.node_tree)) for m in bpy.data.materials)
    groups = tuple((g.name, _tree(g)) for g in bpy.data.node_groups)
    shared = (cams, lights, mats, groups, _tree(world.node_tree) if world else None)
    objs = {o.name: object_sig(o) for o in sc.objects if o.type != "CAMERA"}
    lamp_objs = tuple(sorted((n, s) for n, s in objs.items() if sc.objects[n].type == "LIGHT"))
    return (shared, lamp_objs), objs


def screen_rect(sc, cam, objs):
    """[x0, y0, x1, y1] in frame pixels (y down) covering every object in `objs` and its children, or None when one
    reaches behind the lens (its projection is unbounded)."""
    W = sc.render.resolution_x * sc.render.resolution_percentage // 100
    H = sc.render.resolution_y * sc.render.resolution_percentage // 100
    xs, ys = [], []
    for o in objs:
        for c in [o, *o.children_recursive]:
            if c.type == "EMPTY" or not c.bound_box:
                continue
            for corner in c.bound_box:
                v = world_to_camera_view(sc, cam, c.matrix_world @ __import__("mathutils").Vector(corner))
                if v.z <= 0:
                    return None
                xs.append(v.x * W)
                ys.append((1 - v.y) * H)
    if not xs:
        return [0, 0, 0, 0]
    return [min(xs), min(ys), max(xs), max(ys)]


def union(a, b):
    if a is None or b is None:
        return None
    if a[2] <= a[0] or a[3] <= a[1]:
        return b
    if b[2] <= b[0] or b[3] <= b[1]:
        return a
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def patch_rect(rect, W, H):
    """The rectangle actually rendered: `rect` grown by MARGIN, clamped, snapped OUT to even pixels (the ID pass is
    half size, so its patch lands on whole pixels too); None when it is over MAX_PATCH of the frame (render whole)."""
    if rect is None:
        return None
    m = MARGIN * max(W, H)
    x0, y0 = max(0, int(rect[0] - m)) // 2 * 2, max(0, int(rect[1] - m)) // 2 * 2
    x1, y1 = min(W, -(-int(rect[2] + m + 1) // 2) * 2), min(H, -(-int(rect[3] + m + 1) // 2) * 2)
    if x1 <= x0 or y1 <= y0:
        return [0, 0, 2, 2]
    if (x1 - x0) * (y1 - y0) > MAX_PATCH * W * H:
        return None
    return [x0, y0, x1, y1]


def set_border(sc, rect):
    """Render only `rect` (frame pixels, y down), cropped to it; None renders the whole frame."""
    r = sc.render
    if rect is None:
        r.use_border = False
        r.use_crop_to_border = False
        return
    W = r.resolution_x * r.resolution_percentage / 100
    H = r.resolution_y * r.resolution_percentage / 100
    r.use_border = True
    r.use_crop_to_border = True
    r.border_min_x, r.border_max_x = rect[0] / W, rect[2] / W
    r.border_min_y, r.border_max_y = 1 - rect[3] / H, 1 - rect[1] / H


def load(path):
    """An image file as an (h, w, 4) float array, as Blender reads it — both sides of a comparison read it alike."""
    import numpy as np
    im = bpy.data.images.load(path, check_existing=False)
    try:
        w, h = im.size
        a = np.empty(w * h * 4, dtype=np.float32)
        im.pixels.foreach_get(a)
        return a.reshape(h, w, 4)[::-1]          # Blender's rows run bottom-up
    finally:
        bpy.data.images.remove(im)


def paste(base, patch, rect):
    out = base.copy()
    x0, y0, x1, y1 = rect
    if patch.shape[0] != y1 - y0 or patch.shape[1] != x1 - x0:
        raise ValueError("patch is %dx%d, its rectangle %dx%d" % (patch.shape[1], patch.shape[0], x1 - x0, y1 - y0))
    out[y0:y1, x0:x1] = patch
    return out


def differs(a, b):
    """None when two renders of one frame agree, else how they differ."""
    import numpy as np
    if a.shape != b.shape:
        return "size %s vs %s" % (a.shape, b.shape)
    d = np.abs(a - b).max(axis=2)
    mean, peak = float(d.mean()), float(np.percentile(d, 99.9))
    if mean > MEAN_TOL or peak > PEAK_TOL:
        return "mean %.2f, 99.9th percentile %.1f levels" % (mean * 255, peak * 255)
    return None
