#!/usr/bin/env python3
"""Is the device drawn as the real object, and the screenshot on it drawn as itself? — asked before a render.

WHY THIS EXISTS. A launch film's Apple Watch was a workshop shot drawn by hand, because the device layer had no
watch: the band a flat grey slab wider than the case and detached from it, the crown a grey block, the display
filling the case edge to edge with corners not concentric with it, a label set on the band, the slab skewed while
its text stayed level. The user saw it at once ("视频中的apple watch有些难看"). Every gate was green: none of them
knows what a watch is. These checks do, for the device kit (runtime/device.tsx) and for a beat that should have
used it:

  model       the screenshot's pixel size names the model it came from (scripts/device_models.py); the device is
              drawn as THAT model — a `model` the beat names that another capture size contradicts is an ERROR, an
              unknown size a WARN naming it (drawn on the generic kind)
  aspect      the screenshot's proportion is the screen's: past the tolerance it is refused (screen_media.fit_kind);
              inside it, a crop or a pad of more than ASPECT_NOTE is said, in pixels — never silent
  resolution  the screenshot's pixels are not drawn magnified: the same WARN/ERROR scales as media_res_qa.py, which
              measures the rendered film; this predicts it from the geometry and the push-in before a render
  concentric  the case's corner is the screen's corner plus the bezel, and the bezel is even side to side
  mockup      a picture that is ALREADY a device mockup (its frame drawn in, transparent around it) is not drawn in
              a second device
  workshop    a film's own shot that draws a capture of a known device size without the kit gets a WARN
              suggesting the kit
  dead screen (the RENDERED film, once object_closeups.py has run) a device whose screen shows nothing — flat, or
              only a wallpaper gradient: almost no luminance edges — on most of its sampled frames is a WARN: the
              screen says nothing; show the product's real UI or justify it

The sixth fidelity question — a film label or caption set ON the device — is asked of the DOM by
runtime/textSafe.tsx (`device` in a violation, reported by text_safe_qa.py), because only the layout engine knows
where the type landed.

    python3 scripts/device_fidelity_qa.py <out_dir>     # every beat's device findings, as validate prints them
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import device_script as ds          # noqa: E402
import device_models as dm          # noqa: E402

ASPECT_NOTE = 0.005        # a crop or pad of more than half a percent of the screen is said
CONCENTRIC_TOL_PX = 1.5    # rounding to whole pixels moves each radius by up to half a pixel
EVEN_TOL = 0.10            # bezels within 10% of each other (a laptop's chin excepted): the published 42 mm watch case gives 3.93 mm across and 3.63 down, 8%
MOCKUP_ALPHA = 16          # an edge pixel at or under this alpha is outside the picture
_IMG = re.compile(r"""["'`]([^"'`\s]+\.(?:png|jpe?g|webp))["'`]""", re.I)


def _scales():
    import media_res_qa as mr
    return mr.WARN_SCALE, mr.ERROR_SCALE


def first_source(props, shot):
    if shot == "DeviceHero":
        src = props.get("screen")
    else:
        src = next((st.get("screen") for st in props.get("steps") or []
                    if isinstance(st, dict) and isinstance(st.get("screen"), dict)), None)
    return src if isinstance(src, dict) else {}


def _facts(src, out_dir):
    import screen_media as sm
    try:
        if isinstance(src.get("image"), str) and os.path.isfile(os.path.join(out_dir, src["image"])):
            return sm.image_facts(os.path.join(out_dir, src["image"])), os.path.join(out_dir, src["image"])
        if isinstance(src.get("video"), str) and os.path.isfile(os.path.join(out_dir, src["video"])):
            return sm.video_facts(os.path.join(out_dir, src["video"])), None
    except ds.DeviceScriptError:
        pass                            # an unreadable file is named where it is checked, not here
    return None, None


def mockup_warning(path):
    """A sentence when the picture at `path` is already a device mockup — transparent at the middle of two or more
    of its edges, or around more than a tenth of it — else None. A screen capture is opaque to its edges (a
    watch's has transparent CORNERS: its display's own mask, which this does not count)."""
    if not path or not os.path.isfile(path):
        return None
    from PIL import Image
    import numpy as np
    with Image.open(path) as im:
        if "A" not in im.getbands():
            return None
        a = np.asarray(im.getchannel("A"))
    h, w = a.shape
    mids = [a[0, w // 2], a[h - 1, w // 2], a[h // 2, 0], a[h // 2, w - 1]]
    clear = sum(1 for v in mids if v <= MOCKUP_ALPHA)
    share = float((a <= MOCKUP_ALPHA).mean())
    if clear >= 2 or share > 0.10:
        return ("%s is already a device mockup — its own frame is drawn in the picture (transparent around it: %d of "
                "4 edge midpoints, %.0f%% of it) — a device drawn around it frames a frame; give the bare screen "
                "capture, or show the picture as an image, not on a device" % (os.path.basename(path), clear, share * 100))
    return None


def resolve(props, shot, out_dir):
    """(props with `device` and `model` settled, problems, warnings). The model a beat is drawn as is the one its
    first screen came from: named by `model`, or read off the capture's pixel size."""
    probs, warns = [], []
    src = first_source(props, shot)
    facts, path = _facts(src, out_dir)
    named = props.get("model")
    device = props.get("device")
    w = mockup_warning(path)
    if w:
        warns.append(w)
    if facts is None:
        return props, probs, warns
    cands = dm.candidates(facts["w"], facts["h"])
    size = "%dx%d" % (facts["w"], facts["h"])
    if named:
        if cands and named not in [c for c, _ in cands]:
            probs.append("`model` %s is drawn, but the %s screen is a %s capture — its screen is a different shape; "
                         "drop `model` (it is read from the capture) or give a %s capture"
                         % (named, size, dm.models()[cands[0][0]]["name"], dm.models()[named]["name"]))
        return props, probs, warns
    kind = ("tablet" if device == "tablet-landscape" else device) if device else None
    mine = [(c, how) for c, how in cands if kind is None or dm.models()[c]["kind"] == kind]
    if mine:
        model = mine[0][0]
        out = dict(props, model=model)
        if device is None:
            out["device"] = dm.kind_for(model, facts["w"], facts["h"])
        return out, probs, warns
    if cands:
        other = dm.models()[cands[0][0]]
        warns.append("the %s screen is a %s capture, shown on a %s — use device \"%s\" to draw it on its own device"
                     % (size, other["name"], device, other["kind"]))
        return props, probs, warns
    # A RESIZED capture (a marketing composite's crop, a 1x export at an odd scale) is no model's pixels, but it is
    # still some model's SHAPE. Drawn on the generic kind, its guessed corner cut the status bar off Apple's own iPad
    # screens (Grok Bot film); drawn on the model of its shape, the corners are the real ones.
    shaped = dm.by_shape(facts["w"], facts["h"], kind or ("phone" if shot == "DeviceDemo" else None))
    if shaped:
        model = shaped
        out = dict(props, model=model)
        if device is None:
            out["device"] = dm.kind_for(model, facts["w"], facts["h"])
        warns.append("the %s screen is no model's native pixels but the shape of the %s — drawn as that model (a "
                     "resized capture); name `model` to choose another" % (size, dm.models()[model]["name"]))
        return out, probs, warns
    if not w:
        warns.append("no device model has a %s screen — it is drawn on the generic %s, not a real model's proportions "
                     "(models: %s; a capture straight off the device is its native size)"
                     % (size, device or ("phone" if shot == "DeviceDemo" else "laptop"),
                        ", ".join("%s %dx%d" % (k, *m["published"]["px"]) for k, m in dm.models().items())))
    return props, probs, warns


def aspect_findings(facts, device, model, where, video=False):
    """The crop or pad a screenshot inside the tolerance still gets, said in screen pixels: an image is drawn at
    the screen's width (a shorter one leaves a strip, a taller one that does not scroll is cut), a recording
    covers the screen (cut on one axis)."""
    rw, rh = ds.screen_ratio(device, model)
    s = float(rw) / rh
    a = facts["w"] / float(facts["h"])
    tol = float(ds.SPEC["aspectTolerance"])
    if not video and a < s * (1 - tol):
        return []                                         # a long capture: it scrolls
    d = a / s - 1.0
    if abs(d) <= ASPECT_NOTE:
        return []
    if video:
        what = "cuts %.1f%% off its %s" % (abs(d) * 100, "sides" if d > 0 else "top and bottom")
    elif d > 0:
        what = "leaves %.1f%% of the screen's height empty below it" % (d / (1 + d) * 100)
    else:
        what = "cuts %.1f%% off its bottom" % (-d * 100)
    return ["%s: the %dx%d %s is not the %s screen's proportion (%d:%d) — drawn at the screen's width it %s; give a "
            "capture of that screen" % (where, facts["w"], facts["h"], "recording" if video else "screenshot",
                                        model or device, rw, rh, what)]


def resolution_findings(screen_w_px, image_w, zoom, where):
    """(problems, warnings): how far past its own pixels the screenshot is drawn — the screen's width in the frame,
    times the push-in, over the capture's width."""
    warn, err = _scales()
    if not image_w:
        return [], []
    s = screen_w_px * max(1.0, zoom) / float(image_w)
    msg = ("%s: the %d px-wide capture is drawn %.0f px wide%s — %.2fx its own pixels; give a sharper capture "
           "(native size, PNG) or let the device stand smaller" % (where, image_w, screen_w_px * max(1.0, zoom),
                                                                  " at the push-in" if zoom > 1 else "", s))
    # Said here, before a render, and BLOCKED where the film is measured: media_res_qa.py is the delivery gate at
    # these same scales, on every frame the film really draws (a seam or a camera this geometry does not know of).
    # Refused here it would also refuse the draft render the author needs to see it.
    if s > err:
        return [], [msg + " (past %.2fx: media_res_qa blocks delivery)" % err]
    if s > warn:
        return [], [msg]
    return [], []


# A device named as something the code DRAWS: an identifier (a component, a variable) naming a device — not a pictogram
# (`phoneGlyph`, `laptopIcon`) — or a comment naming a device AND one of its parts ("the phone's island", the Grok Bot
# phone's only trace). Part words alone are not evidence: a pressure gauge has a bezel, a door a hinge. Bare "pad" is
# padding.
_DEVICE_NOUN = r"(?:[Pp]hone|[Ll]aptop|[Tt]ablet|i[Pp]ad|IPad|[Mm]ac[Bb]ook|[Ss]martwatch)"
_DEVICE_IDENT = re.compile(r"[A-Za-z_$]*" + _DEVICE_NOUN + r"[A-Za-z0-9_$]*")
_PICTOGRAM = re.compile(r"(?:Glyph|Icon|Emoji|Pictogram)", re.I)
_DEVICE_NOUN_TEXT = re.compile(r"\b(i?phone|smartphone|i?pad|tablet|laptop|macbook|smartwatch)s?\b", re.I)
_DEVICE_PART_TEXT = re.compile(r"\b(dynamic island|island|notch|bezels?|hinge|home indicator|side buttons?|"
                               r"camera bump|keyboard deck|lid)\b", re.I)
_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def _device_evidence(src):
    """The words in a source that say it DRAWS a device: device identifiers in its code (not pictograms), and a
    comment that names a device together with one of its parts."""
    code = _COMMENT.sub(" ", "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("import ")))
    words = {m.group(0) for m in _DEVICE_IDENT.finditer(code) if not _PICTOGRAM.search(m.group(0))}
    for c in _COMMENT.findall(src):
        nouns, parts = _DEVICE_NOUN_TEXT.findall(c), _DEVICE_PART_TEXT.findall(c)
        if nouns and parts and not _PICTOGRAM.search(c):
            words.update(p.lower() for p in parts)
    return words


def hand_drawn_device(slide, out_dir, build_list=None):
    """An ERROR string when a beat's OWN shot draws a phone, tablet, laptop or watch by hand, else None.

    Measured on a Grok Bot film: a workshop phone drawn as a black rounded outline with an "island" — no buttons,
    wrong proportions — that `workshop_warning` could not see, because it showed no capture. A device the code NAMES is
    cleared by (1) the kit, imported at any depth (runtime/device), (2) a build-list fidelity record citing a real
    model's published numbers (deviceSpec.json `models`), or (3) a `@not-a-device: <why>` line in the source."""
    shot, sp = slide.get("shot"), slide.get("shot_props") or {}
    if not out_dir or not isinstance(shot, str) or shot in ("DeviceDemo", "DeviceHero"):
        return None
    import workshop as ws
    try:
        files = ws.beat_files(out_dir, shot, sp)
    except Exception:
        return None
    texts = []
    for f in files:
        try:
            texts.append(open(f, encoding="utf-8").read())
        except OSError:
            continue
    if not texts or any(re.search(r"runtime/device['\"]", t) for t in texts) or any("@not-a-device:" in t for t in texts):
        return None
    words = sorted(set().union(*(_device_evidence(t) for t in texts)))
    if not words:
        return None
    entry = next((e for e in build_list or [] if isinstance(e, dict) and e.get("id") == shot), None)
    record = json.dumps((entry or {}).get("fidelity") or {}, ensure_ascii=False)
    if any(m in record for m in dm.models()):
        return None
    return ("%s draws a device by hand (its code names: %s) — a hand-drawn phone/tablet/laptop gets its proportions, "
            "corners and parts wrong. Draw it with the kit (runtime/device `Device`, or DeviceHero / DeviceDemo); a "
            "built device's fidelity record must cite the real model it follows (deviceSpec.json models: %s); or say "
            "`// @not-a-device: <why>` in the source" % (shot, ", ".join(words), ", ".join(sorted(dm.models()))))


def concentric_findings(g, kind):
    """Problems with a device's corners and bezel: concentric (case corner = screen corner + bezel), even."""
    if g.get("outerRadius") is None or (g.get("bezels") or {}).get("l", 0) <= 0:
        return []
    out = []
    b = g["bezels"]
    if abs(g["outerRadius"] - (g["radius"] + b["l"])) > CONCENTRIC_TOL_PX:
        out.append("the %s's corners are not concentric: the case's %d px is not the screen's %d px plus the %d px "
                   "bezel" % (g.get("model") or kind, g["outerRadius"], g["radius"], b["l"]))
    pairs = [("left", b["l"], "right", b["r"])]
    if kind not in ("laptop", "monitor"):
        pairs += [("top", b["t"], "bottom", b["b"]), ("side", b["l"], "top", b["t"])]
    for na, va, nb, vb in pairs:
        if max(va, vb) > 0 and abs(va - vb) > max(1.0, EVEN_TOL * max(va, vb)):
            out.append("the %s's bezel is uneven: %s %d px against %s %d px"
                       % (g.get("model") or kind, na, va, nb, vb))
    return out


def workshop_warning(slide, out_dir):
    """A WARN when a beat's OWN shot (the film's workshop) draws a capture of a known device's size without the
    device kit — the hand-drawn watch this file opens with. Cheap: the beat's workshop sources and its props are
    read for image file names; none of the sources importing runtime/device, and one of the images being a known
    model's capture, is the finding."""
    shot, sp = slide.get("shot"), slide.get("shot_props") or {}
    if not out_dir or shot in ("DeviceDemo", "DeviceHero") or not isinstance(shot, str):
        return None
    import workshop as ws
    try:
        files = ws.beat_files(out_dir, shot, sp)
    except Exception:                                         # a broken workshop is workshop.check's to name
        return None
    if not files:
        return None
    texts = []
    for f in files:
        try:
            texts.append(open(f, encoding="utf-8").read())
        except OSError:
            continue
    if any(re.search(r"runtime/device['\"]", t) for t in texts):
        return None
    names = set()
    for t in texts + [json.dumps(sp, ensure_ascii=False)]:
        names.update(_IMG.findall(t))
    from PIL import Image
    for n in sorted(names):
        p = os.path.join(out_dir, n)
        if not os.path.isfile(p):
            continue
        try:
            with Image.open(p) as im:
                w, h = im.size
        except OSError:
            continue
        c = dm.candidates(w, h)
        if c:
            m = dm.models()[c[0][0]]
            return ("%s draws %s, a %s capture (%dx%d), in its own code without the device kit — a hand-drawn device "
                    "gets the band, the crown and the corners wrong; show it with DeviceHero / DeviceDemo "
                    "(device \"%s\", the model is read from the capture), or draw it with runtime/device's "
                    "deviceGeometry + Device inside the shot" % (shot, n, m["name"], w, h, m["kind"]))
    return None


# ── DEAD SCREEN — asked of the RENDERED film (object_closeups.py's census) ──
# A product film's MacBook stood beside the watch for its whole scene showing a dark wallpaper gradient: a screen
# that says nothing reads as a placeholder, and on a product film it is the product that is missing. A device's
# screen is judged by its EDGES: real UI (type, rows, icons, a chart) is full of sharp luminance steps; an empty
# screen, a flat colour or a wallpaper gradient has almost none, however bright or colourful it is.
DEAD_GRAD = 14           # a step of this much luminance (0-255) between neighbouring pixels is an edge
DEAD_EDGE = 0.006        # a screen with fewer than this share of its pixels on an edge shows nothing on that frame
DEAD_SHARE = 0.5         # ...on more than this share of its sampled frames is a dead screen
DEAD_INSET = 0.08        # the box's margin left out: a turned screen's bounding box takes in some bezel
DEAD_MIN_PX = 60         # a screen drawn smaller than this is not read
DEAD_SAMPLES = 12        # frames read per screen per beat


def edge_density(gray):
    """The share of a screen crop's pixels (a 2D uint8/float array) on a luminance edge stronger than DEAD_GRAD."""
    import numpy as np
    a = np.asarray(gray, dtype=float)
    h, w = a.shape
    iy, ix = int(h * DEAD_INSET), int(w * DEAD_INSET)
    a = a[iy:h - iy, ix:w - ix]
    if a.shape[0] < 3 or a.shape[1] < 3:
        return 0.0
    gx = np.abs(np.diff(a, axis=1))[:-1, :]
    gy = np.abs(np.diff(a, axis=0))[:, :-1]
    return float((np.maximum(gx, gy) > DEAD_GRAD).mean())


def dead_verdict(densities):
    """(dead, share) — the screen says nothing when more than DEAD_SHARE of its frames are under DEAD_EDGE."""
    if not densities:
        return False, 0.0
    share = sum(1 for d in densities if d < DEAD_EDGE) / float(len(densities))
    return share > DEAD_SHARE, share


def _read_frame_gray(video, frame, fps):
    import numpy as np
    import subprocess
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory(prefix="deadscr_") as tmp:
        p = os.path.join(tmp, "f.png")
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.4f" % ((frame + 0.5) / fps), "-i", video,
                            "-frames:v", "1", p], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isfile(p):
            return None
        with Image.open(p) as im:
            return np.asarray(im.convert("L"))


def dead_screens(out_dir, read=None):
    """WARN sentences, one per (beat, device screen) that shows nothing for most of its time on screen — read from
    object_closeups.py's record of every sampled screen box and the delivered out.mp4. [] when there is no record
    (object_closeups.py has not run: main() says so). `read(frame) -> 2D gray array` is for tests."""
    rp = os.path.join(out_dir, "_object_closeups.json")
    if not os.path.isfile(rp):
        return []
    rec = json.load(open(rp, encoding="utf-8"))
    fps = float(rec.get("fps") or 30)
    video = os.path.join(out_dir, "out.mp4")
    if read is None:
        cache = {}

        def read(f):
            if f not in cache:
                cache[f] = _read_frame_gray(video, f, fps)
            return cache[f]
    out = []
    for name, rows in sorted((rec.get("screens") or {}).items()):
        by_beat = {}
        for r in rows:
            f, x, y, w, h = r[:5]
            beat = r[5] if len(r) > 5 else None
            if w >= DEAD_MIN_PX and h >= DEAD_MIN_PX:
                by_beat.setdefault(beat, []).append((f, x, y, w, h))
        for beat, boxes in sorted(by_beat.items(), key=lambda kv: (kv[0] is None, kv[0])):
            step = max(1, len(boxes) // DEAD_SAMPLES)
            dens = []
            for f, x, y, w, h in boxes[::step][:DEAD_SAMPLES]:
                g = read(f)
                if g is None:
                    continue
                H, W = g.shape[:2]
                crop = g[max(0, y):min(H, y + h), max(0, x):min(W, x + w)]
                if crop.size:
                    dens.append(edge_density(crop))
            dead, share = dead_verdict(dens)
            if dead:
                out.append("%sthe %s screen says nothing on %d of %d sampled frames (edges on %.2f%% of it at the "
                           "median, under %.1f%%) — an empty, flat or wallpaper-only screen reads as a placeholder: "
                           "show the product's real UI on it, or justify an empty screen"
                           % ("beat %s: " % beat if beat is not None else "", name.split(":", 1)[-1],
                              round(share * len(dens)), len(dens), 100 * sorted(dens)[len(dens) // 2],
                              100 * DEAD_EDGE))
    return out


def main(argv):
    if len(argv) != 1:
        sys.exit("usage: device_fidelity_qa.py <out_dir> — every device beat's fidelity findings")
    out_dir = argv[0]
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta, slides = board.get("meta") or {}, board.get("slides") or []
    n_err = 0
    for i, s in enumerate(slides, 1):
        if s.get("shot") in ("DeviceDemo", "DeviceHero"):
            errs, warns = ds.check_slide(s, out_dir, meta, slides)
        else:
            w = workshop_warning(s, out_dir)
            errs, warns = [], [w] if w else []
        for e in errs:
            print("ERROR beat %d: %s" % (i, e))
        for w in warns:
            print("WARN  beat %d: %s" % (i, w))
        n_err += len(errs)
    # the rendered film's screens: a device that shows nothing (object_closeups.py keeps every screen's boxes)
    if os.path.isfile(os.path.join(out_dir, "_object_closeups.json")):
        for w in dead_screens(out_dir):
            print("WARN  " + w)
    elif any(s.get("shot") in ("DeviceDemo", "DeviceHero") for s in slides):
        print("note: the dead-screen check reads the rendered film — run scripts/object_closeups.py after the render")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
