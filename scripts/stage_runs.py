"""STAGE RUNS — consecutive beats that are ONE continuous scene (SKILL.md, "Continuous stage").

A beat joins the beat before it when both name the same `stage.run`:

    {"shot": "CardStage", "stage": {"run": "deck"}, "shot_props": {…this beat's state…}}

Joined beats are rendered as one Sequence by remotion/src/Film.tsx: no seam between them, so the next beat starts on the
frame the last one ends (a seam overlaps them by SEAM_FRAMES instead), one stage component draws the whole run, and its
actors carry their state from beat to beat (remotion/src/runtime/stageRun.tsx). Every Python mirror of the film's timing
asks THIS module whether a boundary is a cut — the segment timeline, the subtitle file, the SFX cue map and the TTS tail
pad — because a mirror that still assumed a seam at every boundary would put each later caption and sound a little early.
"""
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
STAGE_DIR = os.path.join(_HERE, "..", "remotion", "src", "stage")


def run_id(item):
    """The stage run a slide or a Film scene belongs to, or None."""
    st = (item or {}).get("stage") if isinstance(item, dict) else None
    if isinstance(st, dict) and isinstance(st.get("run"), str) and st["run"].strip():
        return st["run"].strip()
    return None


def joined(prev, cur):
    """True when `cur` continues `prev`'s stage run — the boundary between them is not a cut."""
    r = run_id(cur)
    return bool(r) and prev is not None and run_id(prev) == r


def joined_flags(items):
    """[bool] per item: joined to the one before it (the first is never joined)."""
    return [i > 0 and joined(items[i - 1], items[i]) for i in range(len(items))]


def runs(items):
    """[(first, last, run_id)] for every stage run, indices inclusive (a run of one beat included)."""
    out, i = [], 0
    while i < len(items):
        r = run_id(items[i])
        if not r:
            i += 1
            continue
        j = i
        while j + 1 < len(items) and joined(items[j], items[j + 1]):
            j += 1
        out.append((i, j, r))
        i = j + 1
    return out


def stage_names():
    """The stage components the Film can draw a run with (remotion/src/stage/<Name>.tsx)."""
    try:
        return sorted(os.path.splitext(f)[0] for f in os.listdir(STAGE_DIR)
                      if f.endswith(".tsx") and re.match(r"^[A-Z]\w+\.tsx$", f))
    except OSError:
        return []


_EXIF_TURNED = (5, 6, 7, 8)   # EXIF orientations a browser draws a quarter turn from the stored pixels


def image_aspect(path):
    """width / height of an image AS A BROWSER DRAWS IT — <img> honours EXIF orientation, so a phone photo stored
    landscape and tagged "rotate 90" is a portrait face."""
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
        try:
            turned = im.getexif().get(0x0112) in _EXIF_TURNED
        except Exception:
            turned = False
    if turned:
        w, h = h, w
    if w <= 0 or h <= 0:
        raise ValueError("%s has no size (%dx%d)" % (path, w, h))
    return round(w / h, 4)


def stamp_faces(props, public_dir):
    """`props` with its face's shape added as `imageAspect` — a stage beat's `image` names a file the film serves,
    and the stage gives the card that file's shape, which a frame cannot measure before it draws the image. `props`
    comes back as it was when it names no image; a missing file is an error here rather than a blank card in the film."""
    if not isinstance(props, dict) or not isinstance(props.get("image"), str) or not props["image"].strip():
        return props
    path = os.path.join(public_dir, props["image"].lstrip("/"))
    if not os.path.isfile(path):
        raise FileNotFoundError("stage image %r is not a file in %s" % (props["image"], public_dir))
    return dict(props, imageAspect=image_aspect(path))    # a copy: the board's own shot_props are never written


def check(slides):
    """The problems that make a board's stage runs unrenderable or misleading — [] when there are none."""
    probs = []
    names = set(stage_names())
    seen = {}
    for first, last, r in runs(slides):
        if r in seen:
            probs.append("stage run %r appears twice (beats %d and %d) — a run is ONE stretch of consecutive beats; "
                         "name the second one differently" % (r, seen[r] + 1, first + 1))
        seen.setdefault(r, first)
        shots = {slides[k].get("shot") for k in range(first, last + 1)}
        if len(shots) != 1:
            probs.append("stage run %r (beats %d-%d) mixes shots %s — every beat of a run is drawn by ONE stage "
                         "component" % (r, first + 1, last + 1, sorted(map(str, shots))))
        shot = slides[first].get("shot")
        if shot not in names:
            probs.append("stage run %r (beats %d-%d) is drawn by %r, which is not a stage (remotion/src/stage/: %s)"
                         % (r, first + 1, last + 1, shot, ", ".join(sorted(names)) or "none"))
        for k in range(first + 1, last + 1):
            s = slides[k]
            if s.get("transition_in") not in (None, "", {}):
                probs.append("beat %d continues stage run %r, so it has no cut to transition through — drop its "
                             "transition_in" % (k + 1, r))
        for k in range(first + 1, last + 1):
            for f in ("ground", "key"):
                if slides[k].get(f) is not None:
                    probs.append("beat %d declares a `%s`, but it continues stage run %r, which is lit from its first beat "
                                 "— move the %s to beat %d" % (k + 1, f, r, f, first + 1))
        for k in range(first, last + 1):
            if slides[k].get("camera") not in (None, "", {}):
                probs.append("beat %d is on stage run %r, whose stage moves its own camera — drop its `camera` (put "
                             "the move in the beat's stage state)" % (k + 1, r))
    return probs
