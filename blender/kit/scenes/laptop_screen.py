"""KIT SCENE `kit:laptop_screen` — a MacBook Air on a studio sweep whose screen plays the beat's own interface, the
camera pushing from the whole machine in to the part the voice is about (references/blender-plates.md "Device screens").

`slide.blender.params` (all optional; distances in scene units, the laptop 2.2 wide):
  focus [x, y]       where the push ends, as fractions of the SCREEN from its top-left (default [0.5, 0.5])
  start_focus [x, y] where it starts, the same way; absent, the middle of the whole machine. A film whose earlier beat
                     already showed the laptop starts on its screen — and keeps the dark keyboard out of the caption
                     band (plate_qa judges it when the beat names `objects: ["keyboard"]`)
  start_d, end_d     the camera's distance at the start and the end of the move (6.6, 3.0)
  start_side, end_side   degrees the camera stands to the side of the screen's normal (24, 14)
  start_up, end_up   how far it looks down on it (0.32, 0.10)
  move [a, b]        the move's span as fractions of the beat, eased; still after (0.05, 0.70) — Workspace's own view move
  yaw, open          the laptop's turn on the desk and its lid's lean back, degrees (-16, 15)
  lens, fstop        50 mm; f/1.1 at this scale (the laptop is ~7x life size in scene units: a real f/8)
  ground             the sweep's colour, the ground the shot dissolves into ("#c8d0cd")
  hdri, softboxes    the studio's strength and the soft boxes' share (0.8, 0.35)
  samples            Cycles samples (24, with adaptive sampling and OIDN)

Builds objects {laptop, keyboard}, anchors {screen (its centre), focus (where the push ends)} and the screen for the runner to
play and measure. Measured on the WorkBuddy film's beat 6 (2026-11-07, Cycles, M4): 25 s a 1920x1080 frame."""
import math

from mathutils import Vector

from blender.kit import macbook, studio

DEFAULTS = {"focus": [0.5, 0.5], "start_focus": None, "start_d": 6.6, "end_d": 3.0, "start_side": 24.0, "end_side": 14.0,
            "start_up": 0.32, "end_up": 0.10, "move": [0.05, 0.70], "yaw": -16.0, "open": 15.0, "lens": 50.0,
            "fstop": 1.1, "ground": "#c8d0cd", "hdri": 0.8, "softboxes": 0.35, "samples": 24}


def _p(k):
    bad = sorted(set(k.params) - set(DEFAULTS))
    if bad:
        raise SystemExit("kit:laptop_screen has no param %s (it takes %s)" % (", ".join(bad), ", ".join(sorted(DEFAULTS))))
    return dict(DEFAULTS, **k.params)


def _side(vec, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return Vector((vec.x * c - vec.y * s, vec.x * s + vec.y * c, vec.z))


def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def build(k):
    import bpy
    p = k.p = _p(k)
    if not k.screen:
        raise SystemExit("kit:laptop_screen needs a screen (slide.blender.screen) — it is the picture the laptop shows")
    studio.world(strength=p["hdri"])
    floor = studio.sweep(ground=p["ground"])
    if k.mode == "rgba":
        # over the film's own ground: the sweep only catches the laptop's shadow (Cycles); EEVEE drops it
        if k.engine == "cycles":
            floor.is_shadow_catcher = True
        else:
            bpy.data.objects.remove(floor)
    macbook.make(k, k.screen[0])
    lap = k.lap
    lap["root"].rotation_euler = (0, 0, math.radians(p["yaw"]))
    lap["hinge"].rotation_euler = (math.radians(-p["open"]), 0, 0)
    bpy.context.view_layer.update()
    normal = lap["normal"]()
    fx, fy = p["focus"]
    k.focus_pt = lap["uv_point"](fx, 1 - fy)
    sf = p["start_focus"]
    k.whole_pt = lap["uv_point"](sf[0], 1 - sf[1]) if sf else \
        lap["root"].matrix_world @ Vector((0, -10, 100))                    # the middle of the machine (mm)
    k.dirs = ((_side(normal, p["start_side"]) + Vector((0, 0, p["start_up"]))).normalized(),
              (_side(normal, p["end_side"]) + Vector((0, 0, p["end_up"]))).normalized())
    cam = k.camera
    cam.data.lens = p["lens"]
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = p["fstop"]
    pose(k, 0.0)
    studio.softboxes(k.whole_pt, scale=p["softboxes"])
    studio.tune_cycles(p["samples"])
    corners = lambda: [lap["uv_point"](u, v) for u, v in ((0, 1), (1, 1), (1, 0), (0, 0))]   # TL TR BR BL
    # the keyboard is its own object: dark keys under the caption read black on black (WorkBuddy beat 6: 1.3 s under
    # 4.5:1 mid-push), and naming it lets plate_qa's layout pass keep it out of the caption band before a frame is lit
    return {"objects": {"laptop": lap["lid"], "keyboard": lap["keys"]},
            "anchors": {"screen": lambda kk: kk.anchors.project(kk.scene, kk.camera, lap["uv_point"](0.5, 0.5)),
                        "focus": lambda kk: kk.anchors.project(kk.scene, kk.camera, kk.focus_pt)},
            "screen": {"node": lap["tex"], "corners": corners}}


def pose(k, t):
    p = k.p
    a, b = p["move"]
    m = _ease((t / max(1e-6, k.duration) - a) / max(1e-6, b - a))
    tgt = k.whole_pt.lerp(k.focus_pt, m)
    d = p["start_d"] + (p["end_d"] - p["start_d"]) * m
    di = k.dirs[0].lerp(k.dirs[1], m).normalized()
    cam = k.camera
    cam.location = tgt + di * d
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.focus_distance = (tgt - cam.location).length
