#!/usr/bin/env python3
"""Optional CINEMATIC render tier — renders storyboard.json via Remotion instead of the local
ffmpeg+Chrome path. Opt-in (meta.renderer == "remotion"); the local renderer stays the free default.

This tier is built for STORY / cinematic decks: per scene it shows the scene's full-bleed IMAGE with a
gentle Ken Burns push, plays the synthesized narration, and overlays subtitles + an optional
lower-third title/kicker — the same storyboard.json contract, a different renderer. It does NOT
reproduce the HTML slide archetypes (kicker/cards/charts); an html-page deck should stay on the local
renderer. Scenes with no image render as a title/caption over the theme background.

Pipeline: storyboard.json (+ theme.css + synthesized audio/images) -> build_props() -> a props JSON ->
`remotion render` (the darwin/linux native compositor) -> out.mp4 (+ out.srt for parity).

Requires the Node toolchain + an installed remotion/ project (run `npm install` in <skill>/remotion once);
doctor.py reports whether it's available. Falls back with a clear error if not — never silently.

Usage:  python scripts/render_remotion.py <out_dir> [--vertical]
"""
import argparse, json, math, os, re, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storyboard as sb
import render as rd                      # reuse _canvas + _captions_for + _write_srt (one caption world)

_REMOTION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion")
_THEME_FALLBACK = {"bg": "#0d1117", "fg": "#f0f3f8", "muted": "#94989e", "accent": "#5fb3c4", "accent2": "#e0894a"}
# Extended design tokens the CINEMATIC tier also reads from theme.css (surface/scrim/on-accent colours,
# the type faces, style, radius, grain, tracking). theme.py ALREADY emits every one of these; only this
# consumer widens (the HTML tier reads the same vars — one design world). Every key is ADDITIVE with a
# fallback equal to today's implicit look, so a themeless / colour-only board renders unchanged and the
# golden legacy-props test stays green. Keys are camelCase; the CSS var is "--"+kebab (see _css_var).
_TOKEN_FALLBACK = {
    "surface": "#161b22", "scrim": "rgba(13,17,23,.55)", "onAccent": "#ffffff", "onAccent2": "#ffffff",
    "fontDisplay": '"Space Grotesk","Helvetica Neue",Arial,sans-serif',
    "fontBody": '"Space Grotesk","Helvetica Neue",Arial,sans-serif',
    "fontNumber": '"Space Grotesk","Helvetica Neue",Arial,sans-serif',
    "fontKind": "sans", "style": "", "radius": "14px",
    "grainAmount": "0", "trackScale": "1", "lhDisplay": "1.08"}
_DEFAULT_MOTION = {"from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]}   # matches storyboard.new_slide
# scene types the cinematic tier can render: an image (full-bleed) or a plain title/text card. The
# rest (html/chart/timeline/keypoints/compare) carry their visual in a page/props, NOT an image, so
# rendering them here would silently BLANK the content — those must fail loud (see unsupported_scenes).
_IMAGE_OK_TYPES = {"slide", "title"}


def _scene_layers(s):
    """The cinematic depth planes for a scene (top-level or in props), or None."""
    return s.get("layers") or (s.get("props") or {}).get("layers")


def _scene_stage(s):
    """The shot-based stage data for a scene (top-level or in props), or None."""
    return s.get("stage") or (s.get("props") or {}).get("stage")


def _scene_shots(s):
    """The ordered SHOT list for a scene (top-level or in props), or None. Accepts `shots` (a list, the
    paradigm) OR a legacy singular `shot` object, which is wrapped into a one-shot list for compat."""
    sh = s.get("shots") or (s.get("props") or {}).get("shots")
    if sh is not None:
        return sh
    one = s.get("shot") or (s.get("props") or {}).get("shot")
    return [one] if isinstance(one, dict) else None


def _scene_planes(s):
    """The TRUE-3D (P6) content planes for a scene (top-level or in props), or None."""
    return s.get("planes") or (s.get("props") or {}).get("planes")


def _num(v, ctx, default=0.0):
    """Coerce v to a FINITE float, raising a clear error naming ctx on NaN/Inf/non-numeric. Fail loud
    beats a silent-garbage render: a NaN reaches Remotion and blanks the frame; a string plane field
    would otherwise render at 0 with no error."""
    if v is None:
        return default
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise RuntimeError("cinematic %s: expected a number, got %r" % (ctx, v))
    if not math.isfinite(f):
        raise RuntimeError("cinematic %s: %r is not finite (NaN/Infinity)" % (ctx, v))
    return f


_LAYER_NUMS = ("z", "blur", "dim", "parallax", "x", "y", "revealAtFrame")


def _clean_layers(layers, tag):
    """Validate + coerce a layer stack. Every numeric field goes through _num (fail-loud); strings
    (kind/content) pass through. Raises on a non-list stack or a non-dict layer — never emits a shape
    that would crash Camera.tsx's .map."""
    if not isinstance(layers, list):
        raise RuntimeError("cinematic %s: `layers` must be a list, got %s" % (tag, type(layers).__name__))
    out = []
    for j, ly in enumerate(layers):
        if not isinstance(ly, dict):
            raise RuntimeError("cinematic %s layer %d: must be an object, got %s" % (tag, j, type(ly).__name__))
        c = dict(ly)
        for key in _LAYER_NUMS:
            if ly.get(key) is not None:
                c[key] = _num(ly[key], "%s layer %d.%s" % (tag, j, key))
        out.append(c)
    return out


# ── SHOT-BASED staging (P2): a scene is a SET (elements placed once in a 3D world) + an ordered LIST of
# SHOTS the camera moves between over that set. This is the shot paradigm — NOT one-move-per-scene. ──
_SHOT_TYPES = {"ESTABLISH", "MEDIUM", "CLOSEUP", "OVER_SHOULDER", "REVEAL", "HERO"}
_MOTIONS = {"STATIC", "PUSH_IN", "PULL_OUT", "PAN_RIGHT", "PAN_LEFT", "TILT_UP", "TILT_DOWN",
            "ORBIT_RIGHT", "ORBIT_LEFT", "RACK_FOCUS"}
_EASINGS = {"linear", "in", "out", "inout"}
# element content fields passed through verbatim (strings) — geometry (position) is coerced numeric.
_ELEM_STR = ("kind", "title", "kicker", "sub", "text", "heroText", "src", "label", "align", "level", "fit")


def _clean_stage(stage, tag):
    """Validate + coerce a scene's stage (the SET). Elements are a non-empty list; each needs a unique
    string `id`, a `kind`, and a finite [x,y,z] `position`. Content strings pass through; geometry is
    fail-loud numeric. Raises on any malformed shape so nothing garbage reaches SceneStage."""
    if not isinstance(stage, dict):
        raise RuntimeError("cinematic %s: `stage` must be an object, got %s" % (tag, type(stage).__name__))
    elems = stage.get("elements")
    if not isinstance(elems, list) or not elems:
        raise RuntimeError("cinematic %s: `stage.elements` must be a non-empty list" % tag)
    seen, out = set(), []
    for j, el in enumerate(elems):
        if not isinstance(el, dict):
            raise RuntimeError("cinematic %s element %d: must be an object" % (tag, j))
        eid = el.get("id")
        if not isinstance(eid, str) or not eid:
            raise RuntimeError("cinematic %s element %d: needs a non-empty string `id`" % (tag, j))
        if eid in seen:
            raise RuntimeError("cinematic %s: duplicate element id %r" % (tag, eid))
        seen.add(eid)
        pos = el.get("position")
        if not (isinstance(pos, list) and len(pos) == 3):
            raise RuntimeError("cinematic %s element %r: `position` must be [x,y,z]" % (tag, eid))
        c = {"id": eid, "position": [_num(pos[k], "%s element %r position[%d]" % (tag, eid, k)) for k in range(3)]}
        for key in _ELEM_STR:
            if el.get(key) is not None:
                c[key] = str(el[key])
        if el.get("enterAtFrame") is not None:
            c["enterAtFrame"] = int(round(_num(el["enterAtFrame"], "%s element %r enterAtFrame" % (tag, eid))))
        out.append(c)
    persp = stage.get("perspective")
    cleaned = {"elements": out}
    if persp is not None:
        cleaned["perspective"] = _num(persp, "%s stage.perspective" % tag)
    return cleaned


def _clean_shots(shots, frames, fps, elem_ids, tag):
    """Validate + coerce the ordered SHOT list and assign each shot an integer frame window that sums
    EXACTLY to the scene's `frames` (so audio/caption sync is never broken by authored shot durations).
    Each shot: a framing `type`, a `target` element (or targetPos/manual lens), a `motion` pattern, an
    `easing`, and a `carry` continuity flag. Raises on a bad shape or a target that isn't a staged id."""
    if not isinstance(shots, list) or not shots:
        raise RuntimeError("cinematic %s: `shots` must be a non-empty list" % tag)
    cleaned, raws = [], []
    for j, sh in enumerate(shots):
        if not isinstance(sh, dict):
            raise RuntimeError("cinematic %s shot %d: must be an object" % (tag, j))
        st = str(sh.get("type", "MEDIUM")).upper()
        if st not in _SHOT_TYPES:
            raise RuntimeError("cinematic %s shot %d: unknown type %r (known: %s)" % (tag, j, st, sorted(_SHOT_TYPES)))
        c = {"type": st, "motion": str(sh.get("motion", "STATIC")).upper().replace("-", "_").replace(" ", "_"),
             "easing": str(sh.get("easing", "inout")), "carry": bool(sh.get("carry"))}
        if c["motion"] not in _MOTIONS:
            raise RuntimeError("cinematic %s shot %d: unknown motion %r" % (tag, j, c["motion"]))
        en = str(sh.get("energy", "balanced")).lower()
        if en not in ("subtle", "balanced", "bold"):
            raise RuntimeError("cinematic %s shot %d: energy must be subtle|balanced|bold, got %r" % (tag, j, en))
        c["energy"] = en
        tgt = sh.get("target")
        if tgt is not None:
            if str(tgt) not in elem_ids:
                raise RuntimeError("cinematic %s shot %d: target %r is not a staged element id" % (tag, j, tgt))
            c["target"] = str(tgt)
        if sh.get("targetPos") is not None:
            tp = sh["targetPos"]
            if not (isinstance(tp, list) and len(tp) == 3):
                raise RuntimeError("cinematic %s shot %d: `targetPos` must be [x,y,z]" % (tag, j))
            c["targetPos"] = [_num(tp[k], "%s shot %d targetPos[%d]" % (tag, j, k)) for k in range(3)]
        if sh.get("lens") is not None:                       # manual keyframe override (advanced)
            if not isinstance(sh["lens"], list):
                raise RuntimeError("cinematic %s shot %d: `lens` must be a list" % (tag, j))
            c["lens"] = [{"atFrame": int(round(_num(k.get("atFrame", 0), "%s shot %d lens.atFrame" % (tag, j)))),
                          "dolly": _num(k.get("dolly", 0.0), "%s shot %d lens.dolly" % (tag, j)),
                          "pitch": _num(k.get("pitch", 0.0), "%s shot %d lens.pitch" % (tag, j)),
                          "yaw": _num(k.get("yaw", 0.0), "%s shot %d lens.yaw" % (tag, j)),
                          "roll": _num(k.get("roll", 0.0), "%s shot %d lens.roll" % (tag, j)),
                          "zoom": _num(k.get("zoom", 1.0), "%s shot %d lens.zoom" % (tag, j), 1.0),
                          "easing": str(k.get("easing", "inout")),
                          **({"focusZ": _num(k["focusZ"], "%s shot %d lens.focusZ" % (tag, j))} if k.get("focusZ") is not None else {})}
                         for k in sh["lens"] if isinstance(k, dict)]
        d = sh.get("duration")
        raws.append(max(1, int(round(_num(d, "%s shot %d duration" % (tag, j)) * fps))) if d is not None else None)
        cleaned.append(c)
    # Assign frame windows that sum EXACTLY to the scene's frames (protects A/V sync).
    n_none = raws.count(None)
    if n_none:
        fixed = sum(r for r in raws if r is not None)
        each = max(1, (frames - fixed) // n_none)
        raws = [each if r is None else r for r in raws]
    tot = sum(raws) or 1
    scaled = [max(1, int(round(r * frames / tot))) for r in raws]
    scaled[-1] = max(1, scaled[-1] + (frames - sum(scaled)))   # absorb rounding drift in the last shot
    acc = 0
    for c, dv in zip(cleaned, scaled):
        c["startFrame"], c["durationFrames"] = acc, dv
        acc += dv
    return cleaned


# ── TRUE-3D hero tier (P6): WebGL planes + an orbit/crane camera (ThreeScene / @remotion/three). ──
def _clean_planes(planes, tag):
    """Validate + coerce the 3D content planes. Each needs a finite [x,y,z] `position`; `rotation` (3),
    `size` (2) and `color` are optional. Fail-loud so no NaN/garbage reaches the WebGL scene."""
    if not isinstance(planes, list) or not planes:
        raise RuntimeError("cinematic3d %s: `planes` must be a non-empty list" % tag)
    out = []
    for j, p in enumerate(planes):
        if not isinstance(p, dict):
            raise RuntimeError("cinematic3d %s plane %d: must be an object" % (tag, j))
        pos = p.get("position")
        if not (isinstance(pos, list) and len(pos) == 3):
            raise RuntimeError("cinematic3d %s plane %d: `position` must be [x,y,z]" % (tag, j))
        c = {"position": [_num(pos[k], "%s plane %d position[%d]" % (tag, j, k)) for k in range(3)]}
        if p.get("rotation") is not None:
            r = p["rotation"]
            if not (isinstance(r, list) and len(r) == 3):
                raise RuntimeError("cinematic3d %s plane %d: `rotation` must be [x,y,z]" % (tag, j))
            c["rotation"] = [_num(r[k], "%s plane %d rotation[%d]" % (tag, j, k)) for k in range(3)]
        if p.get("size") is not None:
            sz = p["size"]
            if not (isinstance(sz, list) and len(sz) == 2):
                raise RuntimeError("cinematic3d %s plane %d: `size` must be [w,h]" % (tag, j))
            c["size"] = [_num(sz[k], "%s plane %d size[%d]" % (tag, j, k)) for k in range(2)]
        if p.get("color") is not None:
            c["color"] = str(p["color"])
        out.append(c)
    return out


def _clean_camera3d(cam, frames, tag):
    """Coerce the orbit/crane camera keyframes. `at` is a 0..1 fraction of the scene -> atFrame. Each
    keyframe: yaw (radians), pitch, radius, height, easing. A missing camera -> a gentle default crane."""
    if cam is None:
        return [{"atFrame": 0, "yaw": -0.6, "pitch": 0.0, "radius": 7.0, "height": 6.0, "easing": "inout"},
                {"atFrame": frames, "yaw": 0.4, "pitch": 0.0, "radius": 7.0, "height": 2.6, "easing": "inout"}]
    if not isinstance(cam, list) or not cam:
        raise RuntimeError("cinematic3d %s: `camera3d` must be a non-empty list" % tag)
    out = []
    for j, k in enumerate(cam):
        if not isinstance(k, dict):
            raise RuntimeError("cinematic3d %s camera3d %d: must be an object" % (tag, j))
        at = k.get("atFrame")
        if at is None:
            at = int(round(_num(k.get("at", 0.0), "%s camera3d %d at" % (tag, j)) * frames))
        out.append({"atFrame": int(at),
                    "yaw": _num(k.get("yaw", 0.0), "%s camera3d %d yaw" % (tag, j)),
                    "pitch": _num(k.get("pitch", 0.0), "%s camera3d %d pitch" % (tag, j)),
                    "radius": _num(k.get("radius", 7.0), "%s camera3d %d radius" % (tag, j), 7.0),
                    "height": _num(k.get("height", 4.0), "%s camera3d %d height" % (tag, j), 4.0),
                    "easing": str(k.get("easing", "inout"))})
    return out


def unsupported_scenes(data):
    """Scene indices whose visual would render BLANK on the cinematic tier (non-image html/chart/…).

    A scene carrying cinematic `layers` OR a `stage`+`shots` set (shot-based compositing) is renderable
    even with no `image`, so it is NOT unsupported — those paths draw the content."""
    bad = []
    for s in data.get("slides", []):
        t = s.get("type", "slide")
        # Shot-based (stage+shots), true-3D (planes), or legacy layered scenes are OK (they draw content)
        if (_scene_stage(s) and _scene_shots(s)) or _scene_planes(s) or _scene_layers(s):
            continue
        image = s.get("image") or (s.get("props") or {}).get("image")
        if not image and not _scene_layers(s) and t not in _IMAGE_OK_TYPES:
            bad.append((s.get("index"), t))
    return bad


def _css_var(key):
    """camelCase token key -> the CSS custom-property name theme.py emits ('onAccent' -> '--on-accent')."""
    return "--" + re.sub(r"([A-Z])", r"-\1", key).lower()


def _theme(out_dir):
    """Parse the deck's design tokens from theme.css — one design world with the HTML/local tier.
    Returns the 5 base colours (golden-locked) PLUS the extended cinematic tokens (surface/scrim/
    on-accent, the type faces, style, radius, grain, tracking). Each value is captured up to its `;`
    (so a font STACK with commas survives), and every key falls back to today's implicit default when
    the var is absent (a colour-only or themeless board). theme.py is unchanged; only this reader widens."""
    t = dict(_THEME_FALLBACK); t.update(_TOKEN_FALLBACK)
    path = os.path.join(out_dir, "theme.css")
    try:
        css = open(path, encoding="utf-8").read()
    except OSError:
        return t
    for key in t:
        m = re.search(r"%s\s*:\s*([^;]+?)\s*;" % re.escape(_css_var(key)), css)
        if m:
            t[key] = m.group(1).strip()
    return t


_SKILL_FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")


def _copy_fonts(out_dir):
    """Copy the bundled variable fonts from the SKILL's assets/fonts/*.ttf into out_dir/.fonts/ so
    @remotion/fonts `loadFont(staticFile('.fonts/<file>'))` can load the same faces the HTML tier uses
    (one type world). Source is the skill dir — NOT out_dir/assets (an out_dir has no assets/fonts; the
    HTML tier links its CSS by absolute file:// path). Returns the sorted list of copied basenames.
    Best-effort: no-ops if the skill's fonts dir is somehow missing."""
    if not os.path.isdir(_SKILL_FONTS):
        return []
    dst_fonts = os.path.join(out_dir, ".fonts")
    os.makedirs(dst_fonts, exist_ok=True)
    copied = []
    for name in sorted(os.listdir(_SKILL_FONTS)):
        if name.lower().endswith(".ttf"):
            shutil.copy2(os.path.join(_SKILL_FONTS, name), os.path.join(dst_fonts, name))
            copied.append(name)
    return copied


def _edges(slide, meta, fps):
    """Scene-edge dip in FRAMES from the storyboard's semantic transition (mirrors the local
    renderer): dip=both edges, in=lead, out=trail, none=hard cut. transition_seconds sets the length."""
    tr = slide.get("transition", meta.get("transition", "dip"))
    secs = slide.get("transition_seconds", meta.get("transition_seconds", 0.2))
    try:
        f = max(0, int(round(float(secs) * fps)))
    except (TypeError, ValueError):
        f = 0
    fi = f if tr in ("dip", "in") else 0
    fo = f if tr in ("dip", "out") else 0
    return fi, fo


# The deck's seam LOOK (meta.transition_style) -> a @remotion/transitions presentation KEY. The TS side
# (Video.tsx) maps the key to the actual presentation, so the vocabulary lives in one place. A per-scene
# `transition_style` overrides the deck default for that seam.
_TRANSITION_STYLE = {
    "dip": "fade", "fadethrough": "fade", "none": "fade",   # cross-dissolve (the smooth default)
    "push": "slide", "drift": "slide", "lift": "slide-up",   # directional page moves
    "wipe": "wipe", "blur": "blur",                          # sheet wipe / rack-defocus coda
}


def _transitions(scenes, meta, fps):
    """CROSS-SCENE transitions (P3): turn each seam that the storyboard marks (a scene's out-edge OR the
    next scene's in-edge) into a real cross-scene transition the TS TransitionSeries renders, instead of
    two within-clip dips-to-bg. Sets `transitionToNext` on each scene (or None) and ZEROES the two
    within-clip fades at a transitioned seam so the seam isn't faded twice.

    A/V SAFETY: the transition OVERLAPS the two scenes, so it must ride the trailing-breath SILENCE
    (tts pads meta.audio_breath, default 0.42s) — the overlap is CLAMPED to <= the breath so a
    transition can never eat live narration or desync the audio. The very first scene's opening fade and
    the very last scene's closing fade are NOT seams and are preserved."""
    style_default = str(meta.get("transition_style") or meta.get("transition") or "dip")
    # The overlap must ride the trailing-breath SILENCE. That silence only exists if mastering ran
    # (it pads meta.audio_breath). If mastering is OFF, assume NO breath and clamp the overlap to ~1
    # frame (a cut, not a cross-fade) so a transition can never eat live narration.
    breath = 0.0 if meta.get("audio_master") is False else float(meta.get("audio_breath", 0.42) or 0.42)
    cap = max(1, int(round(breath * fps)))                  # overlap ceiling = the breath (A/V safety)
    for i in range(len(scenes)):
        scenes[i]["transitionToNext"] = None
    for i in range(len(scenes) - 1):
        a, b = scenes[i], scenes[i + 1]
        seam = max(int(a.get("fadeOutFrames") or 0), int(b.get("fadeInFrames") or 0))
        if seam <= 0:                                        # a hard cut — no transition
            continue
        style = str(a.get("transitionStyle") or style_default)
        a["transitionToNext"] = {"style": _TRANSITION_STYLE.get(style, "fade"),
                                 "durationInFrames": min(seam, cap)}
        a["fadeOutFrames"] = 0                               # TransitionSeries now owns this seam
        b["fadeInFrames"] = 0
    return scenes


def build_props(data, out_dir, vertical=False, reduced_motion=False):
    """Pure storyboard -> Remotion input-props dict (no Node, no IO beyond reading durations).
    Paths stay RELATIVE to out_dir; render() passes --public-dir=out_dir so staticFile() resolves them.
    Threads the same per-scene fields the local renderer honours: motion (Ken Burns from/to), fit
    (contain/cover), captions, transitions — plus a canvas-derived caption font size."""
    meta = data.get("meta") or {}
    vertical = vertical or meta.get("aspect") == "9:16"
    W, H = rd._canvas(meta, vertical)
    fps = int(meta.get("fps", 30))
    reduced = bool(reduced_motion or meta.get("reduced_motion"))
    captions_on = meta.get("captions", True)
    scenes = []
    for s in data.get("slides", []):
        dur = float(s.get("duration") or 0)
        frames = max(1, int(round(dur * fps)))
        props = s.get("props") or {}
        image = s.get("image") or props.get("image")
        caps = []
        if captions_on:
            for seg in rd._captions_for(s):
                txt = (seg.get("text") or "").strip()
                if txt:
                    caps.append({"text": txt,
                                 "from": int(round(float(seg["start"]) * fps)),
                                 "to": int(round(float(seg["end"]) * fps))})
        fi, fo = _edges(s, meta, fps)
        # CINEMATIC (opt-in, additive, backward-compatible): virtual-camera over staged elements or layers.
        # P2+ SHOT-BASED: `stage` + `shot` → SceneStage (new paradigm, highest priority).
        # LEGACY: `lens` → CinematicScene3D (3D perspective); `layers` → CinematicScene (flat parallax).
        # Absent -> scene renders on existing image/Ken-Burns path unchanged.
        stage = _scene_stage(s)
        shots = _scene_shots(s)
        planes = _scene_planes(s)                           # P6 TRUE-3D (WebGL) content planes
        layers = _scene_layers(s)
        camera = s.get("camera") or props.get("camera")
        lens = s.get("lens") or props.get("lens")           # 3D perspective path (dolly/pitch/yaw)
        perspective = _num(s.get("perspective") or props.get("perspective"), "scene %s perspective" % s.get("index"), None) \
            if (s.get("perspective") or props.get("perspective")) is not None else None

        # TRUE-3D scene (P6): WebGL planes + an orbit/crane camera. Highest-priority cinematic path.
        three_d = bool(planes)
        if three_d:
            planes = _clean_planes(planes, "scene %s" % s.get("index"))
            camera3d = _clean_camera3d(s.get("camera3d") or props.get("camera3d"), frames, "scene %s" % s.get("index"))
        else:
            camera3d = None

        # Shot-based scene (P2): a SET (stage) + an ordered LIST of shots. Fail-loud coercion here,
        # camera timeline computed in SceneStage from the shots + element positions.
        shot_based = bool(stage and shots)
        if shot_based:
            stage = _clean_stage(stage, "scene %s" % s.get("index"))
            elem_ids = {e["id"] for e in stage["elements"]}
            shots = _clean_shots(shots, frames, fps, elem_ids, "scene %s" % s.get("index"))
            # KINETIC TYPE (P4): reveal each element's text as the camera FIRST frames it (the start of the
            # shot that targets it), unless the element sets an explicit enterAtFrame. So text animates in
            # on arrival — not while it's a speck in the wide establish.
            first_target = {}
            for sh in shots:
                t = sh.get("target")
                if t and t not in first_target:
                    first_target[t] = sh["startFrame"]
            for el in stage["elements"]:
                if el.get("enterAtFrame") is None and el["id"] in first_target:
                    el["enterAtFrame"] = first_target[el["id"]]

        # Legacy layered scenes: fail-loud coercion — no NaN/string reaches Remotion
        if layers is not None:
            layers = _clean_layers(layers, "scene %s" % s.get("index"))
        if layers and not camera and not lens and not shot_based:  # flat layered scene gets default push-in
            camera = [{"atFrame": 0, "x": 0.5, "y": 0.5, "zoom": 1.0, "easing": "inout"},
                      {"atFrame": frames, "x": 0.5, "y": 0.5, "zoom": 1.08, "easing": "inout"}]
        if camera is not None:
            if not isinstance(camera, list):
                raise RuntimeError("cinematic scene %s: `camera` must be a list" % s.get("index"))
            camera = [{"atFrame": int(round(_num(k.get("atFrame", 0), "scene %s camera.atFrame" % s.get("index")))),
                       "x": _num(k.get("x", 0.5), "scene %s camera.x" % s.get("index"), 0.5),
                       "y": _num(k.get("y", 0.5), "scene %s camera.y" % s.get("index"), 0.5),
                       "zoom": _num(k.get("zoom", 1.0), "scene %s camera.zoom" % s.get("index"), 1.0),
                       "easing": str(k.get("easing", "inout"))}
                      for k in camera if isinstance(k, dict)]
        if lens is not None:
            if not isinstance(lens, list):
                raise RuntimeError("cinematic scene %s: `lens` must be a list" % s.get("index"))
            lens = [{"atFrame": int(round(_num(k.get("atFrame", 0), "scene %s lens.atFrame" % s.get("index")))),
                     "dolly": _num(k.get("dolly", 0.0), "scene %s lens.dolly" % s.get("index")),
                     "pitch": _num(k.get("pitch", 0.0), "scene %s lens.pitch" % s.get("index")),
                     "yaw": _num(k.get("yaw", 0.0), "scene %s lens.yaw" % s.get("index")),
                     "roll": _num(k.get("roll", 0.0), "scene %s lens.roll" % s.get("index")),
                     "zoom": _num(k.get("zoom", 1.0), "scene %s lens.zoom" % s.get("index"), 1.0),
                     "easing": str(k.get("easing", "inout")),
                     **({"focusZ": _num(k["focusZ"], "scene %s lens.focusZ" % s.get("index"))} if k.get("focusZ") is not None else {})}
                    for k in lens if isinstance(k, dict)]
        mot = s.get("motion") or _DEFAULT_MOTION
        callouts = []                               # timed/static highlight overlays (parity with the local tier)
        for co in (s.get("callouts") or []):
            box = co.get("box")
            if not (isinstance(box, list) and len(box) == 4):
                continue
            t = rd._callout_time(s, meta, co, dur, out_dir)   # 0.0 = untimed (whole scene)
            callouts.append({"box": box, "style": co.get("style", "box"),
                             "label": co.get("label"), "fromFrame": int(round(t * fps))})
        scenes.append({
            "index": s.get("index"),
            "durationInFrames": frames,
            "image": image or None,
            "audio": s.get("audio") or None,
            "captions": caps,
            "kenburns": bool(image) and not reduced,
            "motion": {"from": list(mot.get("from", _DEFAULT_MOTION["from"])),
                       "to": list(mot.get("to", _DEFAULT_MOTION["to"]))},
            "fit": s.get("fit", "contain"),         # local default; cinematic scenes set fit:"cover"
            "callouts": callouts,
            "title": props.get("title"),
            "kicker": props.get("kicker"),
            "fadeInFrames": fi,
            "fadeOutFrames": fo,
            "stage": stage if shot_based else None,          # shot-based (P2): the SET (elements placed once)
            "shots": shots if shot_based else None,           # the ordered SHOT list (framings over the set)
            "planes": planes if three_d else None,            # P6 TRUE-3D: WebGL content planes
            "camera3d": camera3d if three_d else None,        # P6 orbit/crane camera keyframes
            "camera": camera,                        # cinematic FLAT: eased virtual-camera keyframes (or None)
            "lens": lens,                            # cinematic 3D: dolly/pitch/yaw keyframes (or None)
            "perspective": float(perspective) if perspective else None,
            "layers": layers,                        # cinematic: depth planes (or None)
            "reducedMotion": reduced,                # freeze the camera + show reveals instantly
            "transitionStyle": s.get("transition_style"),  # per-scene seam-look override (else meta default)
        })
    _transitions(scenes, meta, fps)                  # derive cross-scene transitions + de-double the seam fades
    return {"width": W, "height": H, "fps": fps, "captionFontPx": rd._caption_font_px(W, H, meta=meta),
            "theme": _theme(out_dir), "scenes": scenes}


def available():
    """True if the Node toolchain + an installed remotion/ project are present."""
    return bool(shutil.which("npx")) and os.path.isdir(os.path.join(_REMOTION_DIR, "node_modules"))


def render(out_dir, vertical=False, reduced_motion=False, sample=None, log="error"):
    """Render the whole deck to out.mp4 (+ out.srt), or a single scene (sample=N) to sample.mp4 for the
    step-8 sign-off checkpoint. Fails loudly on non-image scenes (which would render blank)."""
    if not shutil.which("npx"):
        raise RuntimeError("Node/npx not found — the Remotion tier needs Node.js. Install Node, then "
                           "`cd %s && npm install`, or use the local renderer (meta.renderer=local)." % _REMOTION_DIR)
    if not os.path.isdir(os.path.join(_REMOTION_DIR, "node_modules")):
        raise RuntimeError("remotion/ deps not installed — run `cd %s && npm install` once." % _REMOTION_DIR)

    path = os.path.join(out_dir, "storyboard.json")
    data = sb.load(path)
    if sample is not None:                            # single-scene preview for the step-8 checkpoint
        data = {"meta": data.get("meta", {}), "slides": [s for s in data.get("slides", []) if s.get("index") == sample]}
        if not data["slides"]:
            raise RuntimeError("no scene with index %s to sample" % sample)
    missing = [s.get("index") for s in data.get("slides", []) if not s.get("audio") or not s.get("duration")]
    if missing:
        raise RuntimeError("scene(s) %s have no audio/duration — run tts.py before rendering" % missing)
    bad = unsupported_scenes(data)
    if bad:                                           # the biggest trap: non-image scenes render BLANK
        raise RuntimeError(
            "the remotion cinematic tier renders IMAGE scenes only, but scene(s) %s carry non-image "
            "content (html/chart/timeline/…) that would render BLANK. Use the local renderer "
            "(meta.renderer=local) for an html/designed deck, or give those scenes an `image`."
            % ", ".join("#%s(%s)" % (i, t) for i, t in bad))

    # Copy bundled fonts to out_dir/.fonts/ for @remotion/fonts to load
    _copy_fonts(out_dir)

    props = build_props(data, out_dir, vertical, reduced_motion)
    props_path = os.path.join(out_dir, ".remotion-props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, allow_nan=False)   # bare NaN/Infinity is invalid JSON — Remotion rejects it cryptically
    out_name = "sample.mp4" if sample is not None else "out.mp4"
    out_mp4 = os.path.abspath(os.path.join(out_dir, out_name))

    cmd = ["npx", "remotion", "render", "src/index.ts", "Main", out_mp4,
           "--props=" + os.path.abspath(props_path),
           "--public-dir=" + os.path.abspath(out_dir),
           "--log=" + log]
    if any(sc.get("planes") for sc in props["scenes"]):   # P6 TRUE-3D scenes need a WebGL renderer
        cmd.append("--gl=angle")                          # else headless Chrome has no WebGL -> black frames
    print("[render_remotion] %s: %d scene(s), %dx%d @%dfps -> %s"
          % ("sample" if sample is not None else "full", len(props["scenes"]),
             props["width"], props["height"], props["fps"], out_mp4))
    subprocess.run(cmd, cwd=_REMOTION_DIR, check=True)
    try:
        os.unlink(props_path)                         # transient — don't leave it in the out_dir
    except OSError:
        pass

    _write_filmstrips(out_dir, data, out_mp4)         # the D12 evidence the design-critic judges from
    _run_shot_qa(out_dir, out_mp4)                     # P5: score the rendered frames -> shot_qa.json (advisory print)
    if sample is None:                                # out.srt — overlap-aware (cross-scene transitions)
        _write_srt_overlapped(data, out_dir, os.path.join(out_dir, "out.srt"))
        print("[render_remotion] done -> %s (+ out.srt)" % out_mp4)
    else:
        print("[render_remotion] sample done -> %s" % out_mp4)
    return out_mp4


def _run_shot_qa(out_dir, mp4):
    """Score the rendered cinematic frames (P5). Best-effort + non-fatal here: it always writes
    shot_qa.json and prints a summary so the design-critic (D12) and the operator see it; the actual
    BLOCK-below-threshold decision is the CLI (`python scripts/shot_qa.py <out> --threshold N`) run as a
    pre-full-render gate on the sample, so a scoring hiccup never crashes a finished render."""
    try:
        import shot_qa
        rep = shot_qa.evaluate(out_dir, mp4=mp4)
        if rep.get("abstained"):
            print("[shot_qa] UNSCORED (%s) — shot_qa.json written" % rep.get("reason", ""))
            return
        bad = [sc for sc in rep["scenes"] if not sc["passed"]]
        print("[shot_qa] %d/%d cinematic scenes pass (threshold %d)%s"
              % (len(rep["scenes"]) - len(bad), len(rep["scenes"]), rep["threshold"],
                 "" if not bad else "  — REVIEW: " + ", ".join("#%s %s" % (b["index"], b["floors"] or b["composite"]) for b in bad)))
    except Exception as e:
        print("[shot_qa] skipped (%s)" % e)


def _write_srt_overlapped(data, out_dir, path):
    """SRT for the Remotion tier that accounts for CROSS-SCENE transition OVERLAPS: when scene i+1 is
    transitioned into scene i, it starts `overlap` frames early, so every later scene's captions shift
    earlier by the cumulative overlap. The shared rd._write_srt sums durations sequentially (correct for
    the local tier, which has no overlap) — this variant subtracts overlaps so the burned/scene-local
    captions and the external .srt agree. Burned captions are already scene-local (they track their scene
    automatically); this only fixes the standalone .srt file."""
    meta = data.get("meta") or {}
    fps = int(meta.get("fps", 30) or 30)
    props = build_props(data, out_dir)               # reuse the exact overlaps the render used
    over = {sc["index"]: (sc.get("transitionToNext") or {}).get("durationInFrames", 0) for sc in props["scenes"]}
    lines, idx, t0, cum_overlap = [], 1, 0.0, 0.0
    for s in data.get("slides", []):
        start = t0 - cum_overlap
        for c in rd._captions_for(s):
            lines += [str(idx), "%s --> %s" % (rd._srt_time(start + c["start"]), rd._srt_time(start + c["end"])),
                      c["text"], ""]
            idx += 1
        t0 += float(s.get("duration") or 0)
        cum_overlap += float(over.get(s.get("index"), 0)) / fps
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_filmstrips(out_dir, data, mp4):
    """Per CINEMATIC scene, slice ~5 frames across its time span from the rendered mp4 and montage to
    <out_dir>/_keyframes/scene_NN.png — the rendered-pixel evidence the design-critic's D12 (and the shot
    cards' Checklists) judge the camera move from. Motion is un-judgeable from the plan, so this artifact
    is what makes the loop real. Best-effort: needs ffmpeg + PIL; silently no-ops if either is missing.
    `data` must match `mp4` (for --sample it is the single sampled scene, so the timeline starts at 0)."""
    try:
        from PIL import Image
    except Exception:
        return
    if not shutil.which("ffmpeg") or not os.path.exists(mp4):
        return
    kf = os.path.join(out_dir, "_keyframes")
    os.makedirs(kf, exist_ok=True)
    t0 = 0.0
    for s in data.get("slides", []):
        dur = float(s.get("duration") or 0)
        is_cine = s.get("type") == "cinematic" or _scene_layers(s) or _scene_planes(s) or (_scene_stage(s) and _scene_shots(s))
        if is_cine and dur > 0.2:
            n = 5
            tiles = []
            for i in range(n):
                t = t0 + dur * (0.06 + 0.9 * i / (n - 1))
                fp = os.path.join(kf, ".t.png")
                subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", mp4,
                                "-frames:v", "1", "-y", fp], check=False)
                if os.path.exists(fp):
                    tiles.append(Image.open(fp).copy())
            if tiles:
                w, h = tiles[0].size
                sc = 0.32
                tw, th = int(w * sc), int(h * sc)
                strip = Image.new("RGB", (tw * len(tiles), th))
                for i, im in enumerate(tiles):
                    strip.paste(im.resize((tw, th)), (i * tw, 0))
                strip.save(os.path.join(kf, "scene_%02d.png" % s.get("index")))
        t0 += dur
    try:
        os.unlink(os.path.join(kf, ".t.png"))         # drop the transient single-frame scratch
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(description="Render storyboard.json via the Remotion cinematic tier")
    ap.add_argument("out_dir")
    ap.add_argument("--vertical", action="store_true")
    ap.add_argument("--sample", type=int, default=None, help="render only scene N -> sample.mp4 (step-8 sign-off)")
    ap.add_argument("--reduced-motion", action="store_true")
    ap.add_argument("--log", default="error")
    a = ap.parse_args()
    render(a.out_dir, vertical=a.vertical, reduced_motion=a.reduced_motion, sample=a.sample, log=a.log)


if __name__ == "__main__":
    main()
