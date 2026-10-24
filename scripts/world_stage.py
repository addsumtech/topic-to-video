"""THE WORLD STAGE'S BOARD CHECK — what makes a WorldStage run unrenderable or wrong, said before anything renders.

A WorldStage run (remotion/src/stage/WorldStage.tsx, references/stage-runs.md "WorldStage") is one world a camera
travels through: `world.objects` places the film's objects in one space and every keyframe's `camera` frames one of
them. The stage throws on a world it cannot draw — a frame of nothing is a loud error, never an empty frame — but a
throw half way through a render is the expensive place to learn it. This module walks the run's keyframes exactly as
runtime/stageRun.tsx merges them (objects field by field, `null` removes) and names, per beat and step:

  * an object the camera frames, a label names or a nest is `in`, that is not in the world at that keyframe;
  * a nest that loops, a nested object no smaller than its parent (`span` outside 0..1), a top-level object with no
    `at: [x, y, z]` or no width;
  * an image object whose file the film does not serve, an object of a kind the stage does not draw, a type object
    with no words;
  * a camera move the stage does not draw, and a SCALE-ZOOM whose two framings are not on one nest chain — a zoom
    of ten is only a zoom when the next scale sits INSIDE the last (or the last inside the next, zooming out).

    check(slides, first, last, out_dir=None) -> [problem sentences]
    stamp(props, public_dir) -> props with every world image's `imageAspect` and `imageW` (a missing file raises)
"""
import os
import re

KINDS = ("image", "globe", "disc", "field", "stream", "stars", "band", "glow", "type", "frame", "volume")
# a `volume` object's forms (runtime/volumeCore.ts VOLUME_FORMS, read from there so the two cannot drift)
_VOLUME_CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "runtime",
                            "volumeCore.ts")


def volume_forms():
    src = open(_VOLUME_CORE, encoding="utf-8").read()
    m = re.search(r"export const VOLUME_FORMS = \[([^\]]*)\]", src)
    if not m:
        raise RuntimeError("runtime/volumeCore.ts no longer exports VOLUME_FORMS")
    return tuple(re.findall(r"'(\w+)'", m.group(1)))


def _max_intensity():
    src = open(_VOLUME_CORE, encoding="utf-8").read()
    m = re.search(r"export const VOLUME_MAX_INTENSITY = ([0-9.]+);", src)
    return float(m.group(1)) if m else 1.6
MOVES = ("dolly", "crane", "tilt", "orbit", "scale-zoom")


def merge(a, b):
    """runtime/stageRun.tsx mergeState: objects merge field by field, None removes a key, anything else replaces."""
    out = dict(a)
    for k, v in (b or {}).items():
        if v is None:
            out.pop(k, None)
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out


def _props(slide):
    sp = slide.get("shot_props") if isinstance(slide.get("shot_props"), dict) else slide.get("props")
    return sp if isinstance(sp, dict) else {}


def keyframes(slides, first, last):
    """[(where, own change, merged state)] for every keyframe of the run, in the order the stage applies them."""
    out, state = [], {}
    for k in range(first, last + 1):
        sp = _props(slides[k])
        own = {kk: v for kk, v in sp.items() if kk not in ("steps", "move")}
        state = merge(state, own)
        out.append(("beat %d" % (k + 1), own, state))
        for j, st in enumerate(sp.get("steps") or []):
            if not isinstance(st, dict):
                continue
            ch = {kk: v for kk, v in st.items() if kk not in ("at", "t", "move")}
            state = merge(state, ch)
            out.append(("beat %d step %d" % (k + 1, j + 1), ch, state))
    return out


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf"))


def _objects(state):
    w = state.get("world")
    o = w.get("objects") if isinstance(w, dict) else None
    return o if isinstance(o, dict) else {}


def layout_problems(objects, where):
    """What stops the world laying out (stage/worldCore.ts layoutWorld throws on each of these)."""
    probs = []
    for oid, o in objects.items():
        if not isinstance(o, dict):
            probs.append("%s: world object %r is not an object" % (where, oid))
            continue
        if re.fullmatch(r"\d+", str(oid)):
            probs.append("%s: world object id %r is a number — a browser reorders numeric keys, so the world's draw "
                         "order would not be the order written; name it" % (where, oid))
        kind = o.get("kind", "image")
        if kind not in KINDS:
            probs.append("%s: world object %r has kind %r — the stage draws %s" % (where, oid, kind, ", ".join(KINDS)))
        if kind == "volume":
            forms = volume_forms()
            if o.get("form") not in forms:
                probs.append("%s: volume object %r needs `form`: one of %s (got %r)" % (where, oid, ", ".join(forms),
                                                                                       o.get("form")))
            it = o.get("intensity")
            if it is not None and not (_num(it) and 0 < it <= _max_intensity()):
                probs.append("%s: volume object %r intensity must be in (0, %s] — past it the volume clips to a white "
                             "sheet" % (where, oid, _max_intensity()))
        if kind == "type" and not (isinstance(o.get("text"), str) and o["text"].strip()):
            probs.append("%s: type object %r has no `text`" % (where, oid))
        if kind == "image" and not (isinstance(o.get("image"), str) and o["image"].strip()):
            probs.append("%s: image object %r names no `image` file" % (where, oid))
        if isinstance(o.get("in"), str):
            if o["in"] not in objects:
                probs.append("%s: world object %r is nested `in` %r, which is not an object of the world" % (where, oid, o["in"]))
            sp = o.get("span")
            if not (_num(sp) and 0 < sp < 1):
                probs.append("%s: world object %r is nested in %r with span %r — a nested object is SMALLER than its parent "
                             "(span: its width as a share of the parent's, between 0 and 1)" % (where, oid, o["in"], sp))
        else:
            at = o.get("at")
            if not (isinstance(at, list) and len(at) == 3 and all(_num(x) for x in at)):
                probs.append("%s: world object %r needs `at`: [x, y, z] (world units: 1 = the frame's short side) or `in` a "
                             "parent — got %r" % (where, oid, at))
            if kind != "type" and not (_num(o.get("w")) and o["w"] > 0):
                probs.append("%s: world object %r needs a width `w` > 0, got %r" % (where, oid, o.get("w")))
    # a nest that loops never reaches a top-level object
    for oid in objects:
        seen, cur = [], oid
        while isinstance(objects.get(cur), dict) and isinstance(objects[cur].get("in"), str):
            if cur in seen:
                probs.append("%s: world object %r is nested inside itself (%s)" % (where, oid, " → ".join(seen + [cur])))
                break
            seen.append(cur)
            cur = objects[cur]["in"]
    return probs


def chain(objects, oid):
    """The object and every parent above it, nearest first."""
    out = []
    while isinstance(objects.get(oid), dict) and oid not in out:
        out.append(oid)
        oid = objects[oid].get("in")
        if not isinstance(oid, str):
            break
    return out


def check(slides, first, last, out_dir=None):
    """The problems of the WorldStage run slides[first..last] — [] when there are none. With `out_dir`, image files are
    checked against the folder the film serves."""
    probs = []
    prev_frame = None
    seen_err = set()
    for n, (where, own, state) in enumerate(keyframes(slides, first, last)):
        objects = _objects(state)
        if n == 0 and not objects:
            probs.append("%s: a WorldStage run's first beat declares the world — `world: {objects: {<id>: {...}}}`" % where)
        for pr in layout_problems(objects, where):
            key = pr.split(": ", 1)[1]
            if key not in seen_err:                      # one sentence per defect, not one per keyframe it survives
                seen_err.add(key)
                probs.append(pr)
        if out_dir:
            for oid, o in objects.items():
                img = o.get("image") if isinstance(o, dict) else None
                if isinstance(img, str) and img.strip() and not os.path.isfile(os.path.join(out_dir, img.lstrip("/"))):
                    key = "image:%s:%s" % (oid, img)
                    if key not in seen_err:
                        seen_err.add(key)
                        probs.append("%s: world object %r shows %r, which is not a file in %s" % (where, oid, img, out_dir))
        cam = state.get("camera")
        if not isinstance(cam, dict) or not isinstance(cam.get("frame"), str):
            if n == 0:
                probs.append("%s: the camera frames nothing — give the run's first beat `camera: {\"frame\": \"<object id>\"}`"
                             % where)
            continue
        fr = cam["frame"]
        if fr not in objects:
            probs.append("%s: the camera frames %r, which is not an object of the world there (objects: %s)"
                         % (where, fr, ", ".join(objects) or "none"))
        own_cam = own.get("camera") if isinstance(own.get("camera"), dict) else None
        move = (own_cam or {}).get("move", "dolly")
        if own_cam is not None and move not in MOVES:
            probs.append("%s: camera move %r is not one the stage draws (%s)" % (where, move, ", ".join(MOVES)))
        if move == "scale-zoom" and own_cam is not None and prev_frame and fr in objects:
            a, b = chain(objects, prev_frame), chain(objects, fr)
            if fr != prev_frame and prev_frame not in b and fr not in a:
                probs.append("%s: a scale-zoom from %r to %r — the two are not on one nest chain (%s; %s), so there is no "
                             "scale to zoom through. Nest the next scale `in` the last (`uv`, `span`), or dolly"
                             % (where, prev_frame, fr, " in ".join(a), " in ".join(b)))
        for key in ("yaw", "pitch"):
            if move == "scale-zoom" and own_cam is not None and key in own_cam:
                probs.append("%s: a scale-zoom keeps the lens's turn — drop its %s (turn the camera with an orbit or a "
                             "tilt before or after the zoom)" % (where, key))
        labels = state.get("labels")
        if labels is not None:
            if not isinstance(labels, list):
                probs.append("%s: `labels` must be a list of object ids" % where)
            else:
                for lid in labels:
                    if lid not in objects:
                        probs.append("%s: `labels` names %r, which is not an object of the world" % (where, lid))
                    elif not (isinstance(objects[lid], dict) and isinstance(objects[lid].get("label"), str)
                              and objects[lid]["label"].strip()):
                        probs.append("%s: `labels` shows %r, which has no `label` to show" % (where, lid))
        prev_frame = fr
    return probs


def stamp(props, public_dir):
    """`props` with every world image object's `imageAspect` (as a browser draws it) and `imageW` (its drawn width in
    px, which the stage lays the picture out at) — read from the file, which a frame cannot measure before it draws.
    A copy; a missing file raises here rather than leaving a blank in the film."""
    import stage_runs as _sr
    if not isinstance(props, dict):
        return props

    def world(d):
        w = d.get("world") if isinstance(d, dict) else None
        if not isinstance(w, dict) or not isinstance(w.get("objects"), dict):
            return d
        objs = {}
        for oid, o in w["objects"].items():
            if isinstance(o, dict) and isinstance(o.get("image"), str) and o["image"].strip():
                path = os.path.join(public_dir, o["image"].lstrip("/"))
                if not os.path.isfile(path):
                    raise FileNotFoundError("world object %r shows %r, which is not a file in %s" % (oid, o["image"], public_dir))
                a = _sr.image_aspect(path)
                from PIL import Image
                with Image.open(path) as im:
                    wpx = im.size[1] if _turned(im) else im.size[0]
                o = dict(o, imageW=int(wpx))
                o.setdefault("imageAspect", a)
            objs[oid] = o
        return dict(d, world=dict(w, objects=objs))

    out = world(props)
    if isinstance(out.get("steps"), list):
        out = dict(out, steps=[world(st) for st in out["steps"]])
    return out


def _turned(im):
    try:
        return im.getexif().get(0x0112) in (5, 6, 7, 8)
    except Exception:                                   # noqa: BLE001 — no EXIF is upright
        return False
