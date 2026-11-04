"""Render one Blender plate, inside Blender. scripts/blender_plate.py runs this; nothing else should.

  Blender -b --factory-startup --python-exit-code 1 --python blender/runner.py -- \
      --scene S --out DIR --frames N --fps F --w W --h H --engine eevee|cycles --mode rgba|env \
      --cues JSON --anchors a,b --objects o,p [--still F]

A scene script defines `build(k)` -> {"objects": {name: obj}, "anchors": {name: (obj, (x, y, z) local)}} and
`pose(k, t)` (t = seconds into the beat). The camera is made here, at the origin looking +Y (right = +X, up = +Z);
a scene moves it in `pose` if it wants. Per frame (1-based) this writes rgba/NNNN.png, ids/NNNN.png (half size),
and at the end anchors.json, camera.json and run.json. A frame whose two files already exist is not rendered again.
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
    a = ap.parse_args(argv)
    a.cues = json.loads(a.cues)
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
    _render.configure(sc, a.engine, a.mode, a.w, a.h)
    cam_data = bpy.data.cameras.new("camera")
    cam = bpy.data.objects.new("camera", cam_data)
    sc.collection.objects.link(cam)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    k = Kit(a, cam)
    mod = _load(a.scene)
    built = mod.build(k) or {}
    objects, anchors = built.get("objects") or {}, built.get("anchors") or {}
    missing = [n for n in a.objects if n not in objects] + [n for n in a.anchors if n not in anchors]
    if missing:
        raise SystemExit("the scene does not build %s (it builds objects %s, anchors %s)"
                         % (", ".join(missing), sorted(objects), sorted(anchors)))
    os.makedirs(a.out, exist_ok=True)
    if a.still:
        sc.frame_set(a.still)
        mod.pose(k, (a.still - 1) / a.fps)
        sc.render.filepath = os.path.join(a.out, "still_%04d.png" % a.still)
        bpy.ops.render.render(write_still=True)
        print("RUNNER-DONE " + json.dumps({"still": a.still, "seconds": round(time.time() - t0, 1)}))
        return
    colors = _idpass.palette(a.objects)
    for d in ("rgba", "ids"):
        os.makedirs(os.path.join(a.out, d), exist_ok=True)
    rec = {"w": a.w, "h": a.h, "fps": a.fps, "frames": a.frames, "anchors": {n: [] for n in a.anchors}}
    cams = []
    rendered = 0
    for f in range(1, a.frames + 1):
        sc.frame_set(f)
        mod.pose(k, (f - 1) / a.fps)
        bpy.context.view_layer.update()
        for n in a.anchors:
            obj, local = anchors[n]
            rec["anchors"][n].append(_anchors.project(sc, cam, obj.matrix_world @ _anchors.Vector(local)))
        cams.append({"lens": cam.data.lens, "sensor": cam.data.sensor_width,
                     "matrix_world": [round(x, 6) for row in cam.matrix_world for x in row]})
        rp = os.path.join(a.out, "rgba", "%04d.png" % f)
        ip = os.path.join(a.out, "ids", "%04d.png" % f)
        if not _done(rp):
            sc.render.filepath = rp
            bpy.ops.render.render(write_still=True)
            rendered += 1
        if a.objects and not _done(ip):
            keep_colors = {o.name: tuple(o.color) for o in sc.objects}
            _idpass.assign({n: objects[n] for n in a.objects}, colors)
            _idpass.render(sc, ip)
            for o in sc.objects:
                o.color = keep_colors.get(o.name, o.color)
    json.dump(rec, open(os.path.join(a.out, "anchors.json"), "w"))
    json.dump({"frames": cams}, open(os.path.join(a.out, "camera.json"), "w"))
    run = {"blender": bpy.app.version_string, "ids": colors, "rendered": rendered,
           "seconds": round(time.time() - t0, 1)}
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
