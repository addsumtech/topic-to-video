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


def resolve_steps(props, resolve, dur_s, beat_no):
    """A stage beat's `steps`, each with `t`: SECONDS into the beat at which it ARRIVES (runtime/stageRun.tsx). A step
    is timed by `at`: {"cue": "<words the narration says>"} (resolved on the voice's own word times by `resolve`,
    render_remotion.resolve_cue_props in seconds mode — the same ordered search a device script uses) or a 0..1
    fraction of the beat. Steps must come in time order; one that does not is an error, never a silent reorder."""
    steps = (props or {}).get("steps")
    if steps is None:
        return props
    probs = step_problems(steps)
    if probs:
        raise SystemExit("[render_remotion] beat %s: %s" % (beat_no, "; ".join(probs)))
    items = []
    for st in steps:
        st = dict(st)
        if _is_fraction(st.get("at")):
            st["t"] = round(float(st.pop("at")) * float(dur_s), 4)
        items.append(st)
    items = resolve({"steps": items})["steps"]
    out = []
    for st in items:
        st = dict(st)
        if "at" in st:                                  # resolved from a cue: seconds
            st["t"] = round(float(st.pop("at")), 4)
        out.append(st)
    ts = [st["t"] for st in out]
    if any(b < a for a, b in zip(ts, ts[1:])):
        raise SystemExit("[render_remotion] beat %s: its steps land at %s s — out of order. A step is a moment of the "
                         "narration; list them in the order the voice reaches them" % (beat_no, ts))
    return dict(props, steps=out)


def _is_fraction(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1


def _is_cue(v):
    return isinstance(v, dict) and isinstance(v.get("cue"), str) and v["cue"].strip() and set(v) <= {"cue", "offset"}


def step_problems(steps, narration=None):
    """What is wrong with a stage beat's `steps` list, as sentences ([] when nothing is)."""
    if not isinstance(steps, list):
        return ["`steps` must be a list of keyframes, each `{\"at\": {\"cue\": \"<words>\"} | 0..1, …what changes}`"]
    probs = []
    for j, st in enumerate(steps):
        if not isinstance(st, dict):
            probs.append("step %d is not an object" % (j + 1))
            continue
        at = st.get("at")
        if not (_is_cue(at) or _is_fraction(at)):
            probs.append("step %d needs `at`: {\"cue\": \"<words the narration says>\"} or a 0..1 fraction of the "
                         "beat (got %r)" % (j + 1, at))
        elif _is_cue(at) and narration is not None and _cue_pos(narration, at["cue"]) < 0:
            probs.append("step %d cues %r, which the beat's narration does not say" % (j + 1, at["cue"]))
        if len(set(st) - {"at", "move"}) == 0:
            probs.append("step %d changes nothing — say what it moves (cursor, marks, lift, camera, count, card…)"
                         % (j + 1))
        cur = st.get("cursor")
        if isinstance(cur, dict) and not all(isinstance(cur.get(k), (int, float)) and 0 <= cur[k] <= 1 for k in "uv"):
            probs.append("step %d's cursor needs `u` and `v`, a place on the face, 0..1" % (j + 1))
    return probs


def _cue_pos(narration, phrase):
    import cues as _cues
    return _cues._anchor_pos(narration or "", phrase.strip())


def sound_events(scenes):
    """[[{"t", "name"}…] per Film scene]: the sounds a stage run's own actions make — a click where a step's cursor
    clicks, at the step's resolved `t` (seconds into its scene). scripts/sfx.py plays them; the stage draws the click
    on the same frame (runtime/stageRun.tsx: a step ARRIVES at `t`)."""
    out = []
    for sc in scenes:
        evs = []
        if run_id(sc):
            for st in ((sc.get("props") or {}).get("steps") or []):
                cur = st.get("cursor") if isinstance(st, dict) else None
                if isinstance(cur, dict) and cur.get("click") and isinstance(st.get("t"), (int, float)):
                    evs.append({"t": float(st["t"]), "name": "click"})
        out.append(evs)
    return out


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
            sp = slides[k].get("shot_props") if isinstance(slides[k].get("shot_props"), dict) else \
                slides[k].get("props") if isinstance(slides[k].get("props"), dict) else {}
            if "steps" in sp:
                for pr in step_problems(sp["steps"], slides[k].get("narration") if "narration" in slides[k] else None):
                    probs.append("beat %d (stage run %r): %s" % (k + 1, r, pr))
        for k in range(first, last + 1):
            if slides[k].get("camera") not in (None, "", {}):
                probs.append("beat %d is on stage run %r, whose stage moves its own camera — drop its `camera` (put "
                             "the move in the beat's stage state)" % (k + 1, r))
    return probs
