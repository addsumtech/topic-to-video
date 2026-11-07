"""Render one Blender plate, inside Blender. scripts/blender_plate.py runs this; nothing else should.

  Blender -b --factory-startup --python-exit-code 1 --python blender/runner.py -- \
      --scene S --out DIR --frames N --fps F --w W --h H --engine eevee|cycles --mode rgba|env \
      --cues JSON --anchors a,b --objects o,p [--still F] [--layout] [--no-reuse]

A scene script defines `build(k)` -> {"objects": {name: obj}, "anchors": {name: (obj, (x, y, z) local) | fn(k)}} and
`pose(k, t)` (t = seconds into the beat). The camera is made here, at the origin looking +Y (right = +X, up = +Z);
a scene moves it in `pose` if it wants. Per frame (1-based) this writes rgba/NNNN.png, ids/NNNN.png (half size),
and at the end anchors.json, camera.json and run.json. A frame whose two files already exist is not rendered again.

A frame that did not change is not rendered at all, and one where only some objects moved renders just their
rectangle (blender/kit/reuse.py: copy | patch | full, verified by whole renders): run.json `frames` says which, and
scripts/blender_plate.py assembles rgba/ and ids/ from full frames and patch/ + idpatch/. `--layout` renders no
picture, only the ID pass and the anchors — what plate_qa judges a layout on, for a fraction of the cost.
"""
import argparse
import importlib.util
import json
import math
import os
import sys
import time
import traceback

import bpy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from blender.kit import anchors as _anchors  # noqa: E402
from blender.kit import color as _color  # noqa: E402
from blender.kit import idpass as _idpass  # noqa: E402
from blender.kit import render as _render  # noqa: E402
from blender.kit import reuse as _reuse  # noqa: E402
from blender.kit import screenseq as _screenseq  # noqa: E402
from blender.kit import stage as _stage  # noqa: E402


class Kit:
    """What a scene script is handed."""

    def __init__(self, a, cam):
        self.scene = bpy.context.scene
        self.camera = cam
        self.cue = a.cues
        self.fps, self.frames, self.w, self.h = a.fps, a.frames, a.w, a.h
        self.duration = a.frames / a.fps
        self.mode, self.engine = a.mode, a.engine
        self.stage = _stage
        self.anchors = _anchors
        self.hexc = _color.hexc
        self.reuse = True          # a scene whose pose changes what kit/reuse.py cannot see (mesh vertices) sets False
        self.params = a.params     # slide.blender.params: the kit scene's own settings
        self.screen = _screenseq.frames_in(a.screen)   # a device's screen: the beat's own shot, one picture per frame


def _args(argv):
    ap = argparse.ArgumentParser(prog="runner.py")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, required=True)
    ap.add_argument("--fps", type=int, required=True)
    ap.add_argument("--w", type=int, required=True)
    ap.add_argument("--h", type=int, required=True)
    ap.add_argument("--engine", choices=("eevee", "cycles"), default="eevee")
    ap.add_argument("--mode", choices=("rgba", "env"), default="rgba")
    ap.add_argument("--cues", default="{}")
    ap.add_argument("--anchors", default="")
    ap.add_argument("--objects", default="")
    ap.add_argument("--still", type=int)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--layout", action="store_true", help="the ID pass and anchors only, no picture")
    ap.add_argument("--no-reuse", dest="reuse", action="store_false", help="render every frame whole")
    ap.add_argument("--screen", default="", help="a folder of pictures a device's screen plays, one per beat frame")
    ap.add_argument("--params", default="{}", help="slide.blender.params as JSON")
    a = ap.parse_args(argv)
    a.cues = json.loads(a.cues)
    a.params = json.loads(a.params)
    if a.screen and not _screenseq.frames_in(a.screen):
        raise SystemExit("--screen %s holds no pictures" % a.screen)
    a.anchors = [x for x in a.anchors.split(",") if x]
    a.objects = [x for x in a.objects.split(",") if x]
    if a.frames < 1 or a.fps < 1 or a.w < 2 or a.h < 2:
        raise SystemExit("frames/fps must be >= 1 and the frame at least 2x2")
    return a


def _load(path):
    # a scene imports helpers beside it (scripts/blender_plate.py keys every .py in that folder)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec = importlib.util.spec_from_file_location("plate_scene", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for fn in ("build", "pose"):
        if not callable(getattr(mod, fn, None)):
            raise SystemExit("%s defines no %s(k%s)" % (path, fn, ", t" if fn == "pose" else ""))
    return mod


def _done(p):
    return os.path.exists(p) and os.path.getsize(p) > 0


def main(argv):
    a = _args(argv)
    t0 = time.time()
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    sc.render.fps = a.fps
    sc.frame_start, sc.frame_end = 1, a.frames
    _render.configure(sc, a.engine, a.mode, a.w, a.h, samples=a.samples)
    cam_data = bpy.data.cameras.new("camera")
    cam = bpy.data.objects.new("camera", cam_data)
    sc.collection.objects.link(cam)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    bpy.context.view_layer.update()
    k = Kit(a, cam)
    mod = _load(a.scene)
    built = mod.build(k) or {}
    objects, anchors = built.get("objects") or {}, built.get("anchors") or {}
    missing = [n for n in a.objects if n not in objects] + [n for n in a.anchors if n not in anchors]
    if missing:
        raise SystemExit("the scene does not build %s (it builds objects %s, anchors %s)"
                         % (", ".join(missing), sorted(objects), sorted(anchors)))
    screen = built.get("screen")
    if k.screen and not screen:
        raise SystemExit("--screen was given and the scene builds no screen (return \"screen\": {node, corners})")
    mag = {"max": 0.0, "frame": None}

    def show_screen(f):
        """The beat frame's own picture on the device, and how far the lens stretches it."""
        if not screen:
            return
        node = screen["node"]
        path = k.screen[_screenseq.index(f, a.frames, len(k.screen))]
        old = node.image
        node.image = bpy.data.images.load(path, check_existing=True)
        if old is not None and old is not node.image and old.users == 0:
            bpy.data.images.remove(old)
        bpy.context.view_layer.update()
        px = node.image.size
        quad = [_anchors.project(sc, cam, p)[:2] for p in screen["corners"]()]
        m = _screenseq.magnification(quad, (px[0], px[1]))
        if m > mag["max"]:
            mag.update(max=round(m, 3), frame=f)

    os.makedirs(a.out, exist_ok=True)
    if a.still:
        sc.frame_set(a.still)
        mod.pose(k, (a.still - 1) / a.fps)
        show_screen(a.still)
        sc.render.filepath = os.path.join(a.out, "still_%04d.png" % a.still)
        bpy.ops.render.render(write_still=True)
        print("RUNNER-DONE " + json.dumps({"still": a.still, "seconds": round(time.time() - t0, 1)}))
        return
    colors = _idpass.palette(a.objects)
    if a.layout and not a.objects:
        raise SystemExit("--layout renders the ID pass only, and this plate names no objects")
    for d in ("rgba", "ids", "patch", "idpatch", "check"):
        os.makedirs(os.path.join(a.out, d), exist_ok=True)
    rec = {"w": a.w, "h": a.h, "fps": a.fps, "frames": a.frames, "anchors": {n: [] for n in a.anchors}}
    cams = []
    rendered = 0
    W, H = a.w, a.h
    beauty = not a.layout
    off = None if (a.reuse and k.reuse) else ("--no-reuse" if not a.reuse else "the scene set k.reuse = False")
    off = off or _reuse.blocked(sc)
    if screen and not off:
        off = "the screen plays a new picture every frame (a texture change kit/reuse.py cannot see)"
    kinds = {}                                   # frame -> {"kind": full|copy|patch, "rect": [...]}
    cur = {"rgba": None, "ids": None}            # the last frame as assembled (arrays), loaded only when reused from
    last_full = {"rgba": None, "ids": None}
    pending = []                                 # reused frames since the last verified one
    prev = None                                  # (shared signature, object signatures, object rects)
    need_check = True

    def path(d, f):
        return os.path.join(a.out, d, "%04d.png" % f)

    def render_beauty(dest, rect=None):
        _reuse.set_border(sc, rect)
        sc.render.filepath = dest
        bpy.ops.render.render(write_still=True)
        _reuse.set_border(sc, None)

    def render_ids(dest, rect=None):
        keep_colors = {o.name: tuple(o.color) for o in sc.objects}
        _idpass.assign({n: objects[n] for n in a.objects}, colors)
        _reuse.set_border(sc, rect)              # fractions of the frame: the same rectangle at half size
        _idpass.render(sc, dest)
        _reuse.set_border(sc, None)
        for o in sc.objects:
            o.color = keep_colors.get(o.name, o.color)

    def layers():
        return (["rgba"] if beauty else []) + (["ids"] if a.objects else [])

    def arr(layer):
        if cur[layer] is None:
            cur[layer] = _reuse.load(last_full[layer])
        return cur[layer]

    def full(f):
        nonlocal rendered
        if beauty and not _done(path("rgba", f)):
            render_beauty(path("rgba", f))
            rendered += 1
        if a.objects and not _done(path("ids", f)):
            render_ids(path("ids", f))
        for L in layers():
            last_full[L], cur[L] = path(L, f), None
        kinds[f] = {"kind": "full"}

    def pose_at(f):
        sc.frame_set(f)
        mod.pose(k, (f - 1) / a.fps)
        bpy.context.view_layer.update()
        show_screen(f)

    for f in range(1, a.frames + 1):
        pose_at(f)
        for n in a.anchors:
            if callable(anchors[n]):                  # computed on the picture this frame, already projected
                v = [float(x) for x in anchors[n](k)]
                if len(v) != 4:
                    raise SystemExit("anchor %r returned %r — a computed anchor returns [x, y, depth, visible]" % (n, v))
                rec["anchors"][n].append([round(v[0], 2), round(v[1], 2), round(v[2], 4), bool(v[3])])
                continue
            obj, local = anchors[n]
            rec["anchors"][n].append(_anchors.project(sc, cam, obj.matrix_world @ _anchors.Vector(local)))
        cams.append({"lens": cam.data.lens, "sensor": cam.data.sensor_width,
                     "matrix_world": [round(x, 6) for row in cam.matrix_world for x in row]})
        if off:
            full(f)
            continue
        shared, objs = _reuse.scene_sig(sc, cam)
        rects = {n: _reuse.screen_rect(sc, cam, [sc.objects[n]]) for n in objs if sc.objects[n].type != "LIGHT"}
        kind, rect, why = "full", None, "the first frame"
        if prev is not None and shared != prev[0]:
            parts = ("camera", "lights", "view", "node groups", "world")
            why = "changed: " + ", ".join([parts[j] for j in range(5) if shared[0][j] != prev[0][0][j]]
                                          + (["a light's placement"] if shared[1] != prev[0][1] else []))
        elif prev is not None and set(objs) != set(prev[1]):
            why = "objects were added or removed"
        if prev is not None and shared == prev[0] and set(objs) == set(prev[1]):
            moved = [n for n in objs if objs[n] != prev[1][n]]
            if not moved:
                kind = "copy"
            else:
                box = [0, 0, 0, 0]
                for n in moved:
                    box = _reuse.union(box, _reuse.union(rects.get(n, None), prev[2].get(n, None)))
                # the ID pass is cheap whole (Workbench, half size): only a PICTURE is worth patching — measured, a
                # layout pass of patched ID frames ran 42 s against 27 s whole
                rect = _reuse.patch_rect(box, W, H) if beauty else None
                kind = "patch" if rect else "full"
                why = None if rect else "moving: %s — over %d%% of the frame or behind the lens" % (
                    ", ".join(moved[:4]), round(_reuse.MAX_PATCH * 100))
        prev = (shared, objs, rects)
        if kind == "full":
            full(f)
            kinds[f]["why"] = why
            need_check = True
            continue
        if kind == "patch":
            if a.objects:                            # the ID pass whole, every patched frame
                if not _done(path("ids", f)):
                    render_ids(path("ids", f))
                last_full["ids"], cur["ids"] = path("ids", f), None
            if not _done(path("patch", f)):
                render_beauty(path("patch", f), rect)
                rendered += 1
            try:
                cur["rgba"] = _reuse.paste(arr("rgba"), _reuse.load(path("patch", f)), rect)
            except ValueError as e:                  # Blender cropped to another size: no patching on this machine
                off = "a patch came back the wrong size (%s)" % e
            if off:
                for g in pending:
                    pose_at(g)
                    full(g)
                pose_at(f)
                full(f)
                pending = []
                continue
        else:
            for L in layers():
                arr(L)
        kinds[f] = {"kind": kind, **({"rect": rect, "ids": "full"} if rect else {})}
        pending.append(f)
        if need_check or len(pending) >= _reuse.CHECK_EVERY or f == a.frames:
            bad = None
            for L in layers():
                chk = os.path.join(a.out, "check", "%s_%04d.png" % (L, f))
                (render_beauty if L == "rgba" else render_ids)(chk)
                why = _reuse.differs(_reuse.load(chk), arr(L))
                bad = bad or (why and "%s: %s" % (L, why))
                os.remove(chk)
            if bad:
                off = "frame %d reused differs from its whole render (%s)" % (f, bad)
                print("RUNNER-REUSE-OFF " + off)
                for g in pending:
                    pose_at(g)
                    for L in layers():
                        for d in (L, "patch" if L == "rgba" else "idpatch"):
                            if os.path.exists(path(d, g)):
                                os.remove(path(d, g))
                    full(g)
            pending, need_check = [], False
    json.dump(rec, open(os.path.join(a.out, "anchors.json"), "w"))
    json.dump({"frames": cams}, open(os.path.join(a.out, "camera.json"), "w"))
    tally = {kd: sum(1 for v in kinds.values() if v["kind"] == kd) for kd in ("full", "copy", "patch")}
    run = {"blender": bpy.app.version_string, "ids": colors, "rendered": rendered, "layout": bool(a.layout),
           "frames": [kinds[f] for f in range(1, a.frames + 1)], "reuse": tally, "reuse_off": off,
           "seconds": round(time.time() - t0, 1)}
    if screen:
        run["screen_mag"] = mag
    json.dump(run, open(os.path.join(a.out, "run.json"), "w"))
    print("RUNNER-DONE " + json.dumps(run))


if __name__ == "__main__":
    try:
        main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    except SystemExit as e:
        if e.code not in (0, None):
            print("RUNNER-ERROR %s" % e.code, file=sys.stderr)
        raise
    except Exception:  # noqa: BLE001 — every failure leaves Blender with a non-zero code and its traceback
        traceback.print_exc()
        sys.exit(1)
