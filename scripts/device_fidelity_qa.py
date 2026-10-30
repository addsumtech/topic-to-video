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
    elif not w:
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
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
