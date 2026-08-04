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
_EASINGS = {"linear", "in", "out", "inout", "house"}  # `house` = the shared premium expo-out settle (camera.ts)
# The docs (shot-vocabulary, design-director) teach the bare survey moves PAN/TILT/ORBIT (and DOLLY/ZOOM);
# resolve them to a concrete default direction so authoring a documented name never fails the gate. validate
# mirrors this map so the ~1s pass and the render agree.
_MOTION_ALIASES = {"PAN": "PAN_RIGHT", "TILT": "TILT_UP", "ORBIT": "ORBIT_RIGHT",
                   "DOLLY": "PUSH_IN", "ZOOM": "PUSH_IN", "PUSH": "PUSH_IN", "PULL": "PULL_OUT"}
# element content fields passed through verbatim (strings) — geometry (position) is coerced numeric.
_ELEM_STR = ("kind", "title", "kicker", "sub", "text", "heroText", "src", "html", "label", "align", "level",
             "fit", "frame", "frameLabel", "concept", "unit", "attitude", "termTitle", "enterMotion",
             "hue", "hudLabel", "hudStatus", "strokeColor")  # `html` = a Path-A form page (to
#            `src` at render); `concept` = a materialized-metaphor verb; frame = device/browser chrome
_METAPHOR = {"widening-gap", "physical-fall", "filling-vessel", "diverging-pair", "converging-scatter"}
# how many `values` each concept needs (None = any non-empty list)
_ARITY = {"widening-gap": 2, "physical-fall": 2, "filling-vessel": 1, "diverging-pair": 2, "converging-scatter": None}


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
        for _fk in ("enterAtFrame", "collapseAtFrame", "sweepSpan", "lockAtFrame", "drawAtFrame"):
            if el.get(_fk) is not None:
                c[_fk] = int(round(_num(el[_fk], "%s element %r %s" % (tag, eid, _fk))))
        if el.get("sweep") is not None:                      # spotlight sweep: a 2-number [a,b] tuple
            tv = el["sweep"]
            if not (isinstance(tv, list) and len(tv) == 2):
                raise RuntimeError("cinematic %s element %r: `sweep` must be [a,b]" % (tag, eid))
            c["sweep"] = [_num(tv[k], "%s element %r sweep[%d]" % (tag, eid, k)) for k in range(2)]
        if el.get("to") is not None:                         # connector end: a [dx,dy] offset OR a target id
            tv = el["to"]
            if isinstance(tv, str):                          # target-by-id: resolved to the delta after the loop
                c["to"] = tv                                 # (defer — the target's position may come later)
            elif isinstance(tv, list) and len(tv) == 2:
                c["to"] = [_num(tv[k], "%s element %r to[%d]" % (tag, eid, k)) for k in range(2)]
            else:
                raise RuntimeError("cinematic %s element %r: `to` must be [dx,dy] or a target element id"
                                   % (tag, eid))
        if el.get("arrow") is not None:
            c["arrow"] = bool(el["arrow"])
        if el.get("size") is not None:                       # image [w,h] px in stage space (fail-loud numeric)
            sz = el["size"]
            if not (isinstance(sz, list) and len(sz) == 2):
                raise RuntimeError("cinematic %s element %r: `size` must be [w,h]" % (tag, eid))
            c["size"] = [_num(sz[k], "%s element %r size[%d]" % (tag, eid, k)) for k in range(2)]
        if c.get("kind") == "terminal":                      # streaming CLI: a non-empty list of log lines
            ln = el.get("lines")
            if not (isinstance(ln, list) and ln):
                raise RuntimeError("cinematic %s element %r: terminal needs a non-empty `lines` list" % (tag, eid))
            c["lines"] = [str(x) for x in ln]
            if el.get("lineDelay") is not None:
                c["lineDelay"] = max(1, int(round(_num(el["lineDelay"], "%s element %r lineDelay" % (tag, eid)))))
        if c.get("kind") == "metaphor":                      # materialized-metaphor verb: validate + coerce data
            cn = c.get("concept")
            if cn not in _METAPHOR:
                raise RuntimeError("cinematic %s element %r: unknown metaphor concept %r (known: %s)"
                                   % (tag, eid, cn, sorted(_METAPHOR)))
            vs = el.get("values")
            if not (isinstance(vs, list) and vs):
                raise RuntimeError("cinematic %s element %r: metaphor needs a non-empty `values` list" % (tag, eid))
            c["values"] = [_num(v, "%s element %r values[%d]" % (tag, eid, k)) for k, v in enumerate(vs)]
            need = _ARITY[cn]
            if need is not None and len(c["values"]) != need:
                raise RuntimeError("cinematic %s element %r: concept %r needs exactly %d values, got %d"
                                   % (tag, eid, cn, need, len(c["values"])))
            if el.get("valueLabels") is not None:
                c["valueLabels"] = [str(x) for x in el["valueLabels"]]
            for k in ("atFrame", "verbSpan"):
                if el.get(k) is not None:
                    c[k] = int(round(_num(el[k], "%s element %r %s" % (tag, eid, k))))
            if c.get("verbSpan") is not None:                # floor at 1 frame: span 0 -> u=(f-fire)/0=NaN at
                c["verbSpan"] = max(1, c["verbSpan"])        # frame==fire (prints 'NaN'); negative freezes the verb
        out.append(c)
    # Resolve connector target-BY-ID: a `to` given as an element id becomes the [dx,dy] delta from the
    # connector's position to the target's (same y-down px space the SVG draws in — translate3d maps
    # position[1] straight to CSS translateY, so no sign flip). Deferred to here because a connector may
    # point at an element declared LATER in the list. Fail-loud on a dangling id (a mistyped target that
    # silently drew a stub line would look like a real diagram — exactly the mystery-furniture failure).
    _by_id = {c["id"]: c["position"] for c in out}
    for c in out:
        if isinstance(c.get("to"), str):
            tgt = _by_id.get(c["to"])
            if tgt is None:
                raise RuntimeError("cinematic %s connector %r: `to` target id %r is not a staged element"
                                   % (tag, c["id"], c["to"]))
            c["to"] = [tgt[0] - c["position"][0], tgt[1] - c["position"][1]]
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
    author_energy = any(isinstance(sh, dict) and sh.get("energy") is not None for sh in shots)
    cleaned, raws = [], []
    for j, sh in enumerate(shots):
        if not isinstance(sh, dict):
            raise RuntimeError("cinematic %s shot %d: must be an object" % (tag, j))
        st = str(sh.get("type", "MEDIUM")).upper()
        if st not in _SHOT_TYPES:
            raise RuntimeError("cinematic %s shot %d: unknown type %r (known: %s)" % (tag, j, st, sorted(_SHOT_TYPES)))
        mot = str(sh.get("motion", "STATIC")).upper().replace("-", "_").replace(" ", "_")
        mot = _MOTION_ALIASES.get(mot, mot)              # accept the bare documented names (PAN/TILT/ORBIT/…)
        eas = str(sh.get("easing", "house"))             # default to the shared HOUSE_EASE settle (#10) — NOT
        #                                                  'inout', which was shadowing camera.ts's `|| 'house'`.
        if eas not in _EASINGS:                          # validate easing too (the lens/camera paths already do)
            raise RuntimeError("cinematic %s shot %d: unknown easing %r (known: %s)" % (tag, j, eas, sorted(_EASINGS)))
        c = {"type": st, "motion": mot, "easing": eas, "carry": bool(sh.get("carry"))}
        if c["motion"] not in _MOTIONS:
            raise RuntimeError("cinematic %s shot %d: unknown motion %r" % (tag, j, c["motion"]))
        en = str(sh.get("energy", "balanced")).lower()
        if en not in ("subtle", "balanced", "bold"):
            raise RuntimeError("cinematic %s shot %d: energy must be subtle|balanced|bold, got %r" % (tag, j, en))
        c["energy"] = en
        if sh.get("motive"):                             # the shot's one-line reason to exist (#6 discipline)
            c["motive"] = str(sh["motive"])
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
    # ENERGY ARC (#6): if the author tuned NO shot's energy, DERIVE an arc instead of a uniform push —
    # calm open (the establish/first beat drifts), the climax near ~80% pushes hardest, the rest settle.
    # A hand-set energy on any shot means the author owns the arc, so leave all of them alone.
    if not author_energy and len(cleaned) >= 2:
        climax = max(0, int(round(len(cleaned) * 0.8)) - 1)
        for i, c in enumerate(cleaned):
            if i == 0 or c["type"] == "ESTABLISH":
                c["energy"] = "subtle"
            elif c["type"] == "HERO" or i == climax:
                c["energy"] = "bold"
            else:
                c["energy"] = "balanced"
    # Every shot needs at least 1 frame, so N shots cannot fit in fewer than N frames — otherwise the
    # windows sum past `frames` and trailing shots get a startFrame beyond the scene end (they never render).
    # Fail loud rather than silently drop the tail.
    if frames < len(cleaned):
        raise RuntimeError("cinematic %s: %d shots but only %d frame(s) (%.2fs) — each shot needs >=1 frame; "
                           "lengthen the scene or cut shots" % (tag, len(cleaned), frames, frames / max(1, fps)))
    # Assign frame windows that sum EXACTLY to the scene's frames (protects A/V sync). Un-authored windows
    # are weighted by energy so a bold climax gets MORE screen time and a subtle drift less (an energy arc
    # in TIME, not just amplitude) — authored `duration`s are honoured exactly.
    _W = {"subtle": 0.82, "balanced": 1.0, "bold": 1.35}
    n_none = raws.count(None)
    if n_none:
        fixed = sum(r for r in raws if r is not None)
        free = max(n_none, frames - fixed)
        wsum = sum(_W[cleaned[i]["energy"]] for i in range(len(raws)) if raws[i] is None) or 1
        raws = [max(1, int(round(free * _W[cleaned[i]["energy"]] / wsum))) if r is None else r
                for i, r in enumerate(raws)]
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
        if p.get("src") is not None:                         # image texture on a real 3D mesh
            c["src"] = str(p["src"])
        if p.get("html") is not None:                        # Path-A form page (screenshotted to src pre-render)
            c["html"] = str(p["html"])
        if p.get("alpha") is not None:                       # texture has transparency (rasterized text)
            c["alpha"] = bool(p["alpha"])
        if p.get("billboard") is not None:                   # face the camera (rasterized text default)
            c["billboard"] = bool(p["billboard"])
        kind = str(p.get("kind", "plane"))                   # 3D element: plane|bars|stack|text|particles|surface
        if kind not in ("plane", "bars", "stack", "text", "particles", "surface"):
            raise RuntimeError("cinematic3d %s plane %d: kind must be plane|bars|stack|text|particles|surface, "
                               "got %r" % (tag, j, kind))
        c["kind"] = kind
        if kind in ("bars", "stack"):                        # data-driven 3D: bar heights / cube-stack counts
            data = p.get("data")
            if not (isinstance(data, list) and data):
                raise RuntimeError("cinematic3d %s plane %d: %s need a non-empty `data` list" % (tag, j, kind))
            c["data"] = [_num(v, "%s plane %d data[%d]" % (tag, j, k)) for k, v in enumerate(data)]
            if p.get("labels") is not None:
                c["labels"] = [str(x) for x in p["labels"]]
        if kind == "particles" and p.get("count") is not None:   # how many points assemble (ThreeScene caps it)
            c["count"] = int(_num(p["count"], "%s plane %d count" % (tag, j)))
        if kind == "surface" and p.get("data") is not None:      # optional height ridge profile (else sum-of-sines)
            data = p.get("data")
            if not isinstance(data, list):
                raise RuntimeError("cinematic3d %s plane %d: surface `data` must be a list" % (tag, j))
            c["data"] = [_num(v, "%s plane %d data[%d]" % (tag, j, k)) for k, v in enumerate(data)]
        if kind == "text":                                   # real 3D text -> rasterized to a billboard plane
                                                             # (_rasterize_text3d); NOT drei/troika <Text>, which
                                                             # renders BLANK under Remotion (async glyph SDF).
            if not p.get("text"):
                raise RuntimeError("cinematic3d %s plane %d: text element needs a `text` string" % (tag, j))
            c["text"] = str(p["text"])
            if p.get("textColor") is not None:
                c["textColor"] = str(p["textColor"])
            if p.get("textSize") is not None:
                c["textSize"] = _num(p["textSize"], "%s plane %d textSize" % (tag, j))
        out.append(c)
    return out


def _clean_camera3d(cam, frames, tag):
    """Coerce the orbit/crane camera keyframes. `at` is a 0..1 fraction of the scene -> atFrame. Each
    keyframe: yaw (radians), radius, height, easing (tilt comes from height+radius; there is no `pitch`,
    which would no-op). A missing camera -> a gentle default crane."""
    if cam is None:
        return [{"atFrame": 0, "yaw": -0.6, "radius": 7.0, "height": 6.0, "easing": "inout"},
                {"atFrame": frames, "yaw": 0.4, "radius": 7.0, "height": 2.6, "easing": "inout"}]
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


_FONT_KIND_FILE = {"sans": "SpaceGrotesk-VF.ttf", "serif": "PlayfairDisplay-VF.ttf",
                   "mono": "JetBrainsMono-VF.ttf", "comic": "Bangers-Regular.ttf"}

# The 4 bundled display faces are LATIN-ONLY (verified: zero CJK/Kana/Hangul codepoints). So a Chinese/
# Japanese/Korean deck's 3D text (kind:"text" planes, bar/stack labels) would rasterize as .notdef TOFU
# boxes — silently, in a multi-minute render. The HTML tier already leans on a system CJK face; mirror that
# here: when a label carries non-Latin (>=U+2E80: CJK radicals, Kana, Hangul, CJK Unified) glyphs, fall back
# to the first system CJK font we can find (macOS + Linux/CI paths), else warn LOUD (never ship tofu quietly).
_CJK_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc", "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "C:/Windows/Fonts/msyh.ttc",
]
_CJK_FONT_CACHE = []   # [resolved_path_or_None]; a single filesystem probe per render


def _needs_nonlatin(txt):
    return any(ord(c) >= 0x2E80 for c in str(txt))


def _resolve_cjk_font():
    """First existing system CJK font path (cached), or None. None → the caller warns and renders tofu
    rather than crashing the whole render mid-way."""
    if not _CJK_FONT_CACHE:
        _CJK_FONT_CACHE.append(next((p for p in _CJK_FONT_CANDIDATES if os.path.isfile(p)), None))
    return _CJK_FONT_CACHE[0]


# Extruded-bar layout constants — MUST match three/ThreeScene.tsx Bars3D (bw/gap/maxH + floor base y) so
# rasterized value/category labels land exactly over their bars.
_BAR_BW, _BAR_GAP, _BAR_MAXH, _BAR_BASE_Y = 0.62, 0.42, 2.6, -1.3
# accreting cube-stack layout — MUST byte-match three/ThreeScene.tsx STACK_U/STACK_GAP/STACK_BASE_Y.
_STACK_U, _STACK_GAP, _STACK_BASE_Y = 0.5, 0.5, -1.3


def _fmt_bar_value(v):
    """Format a bar's numeric value for its on-top label: integers as-is, else one decimal, thousands
    grouped (a lining-figures display face renders the digits). Large magnitudes (>=1e6) abbreviate to
    M/B/T so the rasterized PNG can't grow enormous / run off the frame (matches elements.tsx abbrevNum)."""
    f = float(v)
    a = abs(f)
    for lim, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= lim:
            return ("{:.1f}".format(f / lim).rstrip("0").rstrip(".")) + suf
    return ("{:,}".format(int(round(f))) if abs(f - round(f)) < 0.05 else "{:,.1f}".format(f))


def _rasterize_text3d(data, out_dir):
    """Turn each cinematic3d `kind:'text'` element into a textured plane, AND emit value/category label
    planes for `kind:'bars'`. PIL renders each string to a TRANSPARENT PNG (the deck's bundled display face
    + colour); the element/label becomes a `plane` with `src`+`alpha:true`, billboarded to face the camera,
    sized from the text aspect. Why not drei/troika <Text>: it renders BLANK under Remotion (async glyph SDF
    inside the R3F canvas). This reuses the proven DOM-level texture path. Best-effort: no PIL -> text
    elements are dropped (never a blank card) and bars simply carry no labels."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        for s in data.get("slides", []):
            pls = _scene_planes(s)
            if isinstance(pls, list):
                s["planes"] = [p for p in pls if not (isinstance(p, dict) and p.get("kind") == "text")]
        return
    tk = _theme(out_dir)
    font_path = os.path.join(_SKILL_FONTS, _FONT_KIND_FILE.get(tk.get("fontKind", "sans"), "SpaceGrotesk-VF.ttf"))
    kf = os.path.join(out_dir, ".text3d")
    _warned = []                                     # warn ONCE per render if a CJK label falls back to tofu

    def _text_png(txt, color_rgb, rel_name, px=220):
        """Render txt to a transparent PNG under .text3d/; return (relpath, aspect w/h)."""
        os.makedirs(kf, exist_ok=True)
        fp = font_path
        if _needs_nonlatin(txt):                     # bundled faces are Latin-only → route CJK to a system face
            cjk = _resolve_cjk_font()
            if cjk:
                fp = cjk
            elif not _warned:
                print("[text3d] label %r has non-Latin glyphs but the bundled faces are Latin-only and no "
                      "system CJK font was found — it will render as boxes. Use the HTML tier for a CJK "
                      "deck, or install Noto Sans CJK." % str(txt)[:24])
                _warned.append(True)
        try:
            font = ImageFont.truetype(fp, px)
            try:                                     # match the 2D display titles' weight (~700-800): the VF
                font.set_variation_by_axes([700])    # default instance is LIGHT (Space Grotesk 300), which
            except Exception:                        # rasterizes thin/anemic beside a bold 2D title; a .ttc
                pass                                 # CJK face / non-VF (Bangers) keeps its single weight.
        except Exception:
            font = ImageFont.load_default()
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        l, t, r, b = tmp.textbbox((0, 0), txt, font=font)
        tw, th = max(1, r - l), max(1, b - t)
        pad = int(px * 0.18)
        img = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((pad - l, pad - t), txt, font=font, fill=tuple(color_rgb) + (255,))
        rel = os.path.join(".text3d", rel_name)
        img.save(os.path.join(out_dir, rel))
        return rel, img.width / img.height

    def _bar_label_planes(p, sidx):
        """Value labels above each bar (accent on the final/result bar) + optional category labels
        (`labels`) at the base — the numbers that make an extruded bar chart READ as data-viz."""
        vals = [abs(_num(v, "bars data")) for v in p["data"]]
        n = len(vals)
        if not n:
            return []
        mx = max(vals + [1e-6])
        total = n * _BAR_BW + (n - 1) * _BAR_GAP
        gx, gy, gz = (list(p.get("position") or [0, 0, 0]) + [0, 0, 0])[:3]
        labels = p.get("labels") or []
        accent = _hex_rgb(tk.get("accent", "#e3b23c"))
        fg = _hex_rgb(tk.get("fg", "#f0f3f8"))
        muted = _hex_rgb(tk.get("muted", "#93a0b4"))
        out = []
        for i, v in enumerate(vals):
            bar_x = -total / 2 + _BAR_BW / 2 + i * (_BAR_BW + _BAR_GAP)
            top_y = _BAR_BASE_Y + (v / mx) * _BAR_MAXH
            val_h = 0.32                                     # world height of the value label
            rel, asp = _text_png(_fmt_bar_value(p["data"][i]), accent if i == n - 1 else fg,
                                  "s%s_bar%d_val.png" % (sidx, i), px=170)
            out.append({"kind": "plane", "src": rel, "alpha": True, "billboard": True,
                        "position": [gx + bar_x, gy + top_y + 0.30, gz], "size": [val_h * asp, val_h]})
            if i < len(labels) and str(labels[i]).strip():   # category tag on the floor, IN FRONT of the bar
                cat_h = 0.26
                rel2, asp2 = _text_png(str(labels[i]), muted, "s%s_bar%d_cat.png" % (sidx, i), px=150)
                out.append({"kind": "plane", "src": rel2, "alpha": True, "billboard": True,
                            "position": [gx + bar_x, gy + _BAR_BASE_Y + 0.06, gz + 0.9], "size": [cat_h * asp2, cat_h]})
        return out

    def _stack_label_planes(p, sidx):
        """A per-column TOTAL label above each cube stack (the count = the accumulation) + optional category
        labels at the base — matches ThreeScene Stack3D's layout so the totals sit ON their stacks."""
        vals = [abs(_num(v, "stack data")) for v in p["data"]]
        n = len(vals)
        if not n:
            return []
        total = n * _STACK_U + (n - 1) * _STACK_GAP
        gx, gy, gz = (list(p.get("position") or [0, 0, 0]) + [0, 0, 0])[:3]
        labels = p.get("labels") or []
        accent = _hex_rgb(tk.get("accent", "#e3b23c"))
        fg = _hex_rgb(tk.get("fg", "#f0f3f8"))
        muted = _hex_rgb(tk.get("muted", "#93a0b4"))
        out = []
        for i, v in enumerate(vals):
            cnt = int(round(v))
            col_x = -total / 2 + _STACK_U / 2 + i * (_STACK_U + _STACK_GAP)
            top_y = _STACK_BASE_Y + cnt * _STACK_U
            val_h = 0.30
            rel, asp = _text_png(str(cnt), accent if i == n - 1 else fg, "s%s_stk%d_val.png" % (sidx, i), px=160)
            out.append({"kind": "plane", "src": rel, "alpha": True, "billboard": True,
                        "position": [gx + col_x, gy + top_y + 0.28, gz], "size": [val_h * asp, val_h]})
            if i < len(labels) and str(labels[i]).strip():
                cat_h = 0.24
                rel2, asp2 = _text_png(str(labels[i]), muted, "s%s_stk%d_cat.png" % (sidx, i), px=140)
                out.append({"kind": "plane", "src": rel2, "alpha": True, "billboard": True,
                            "position": [gx + col_x, gy + _STACK_BASE_Y - 0.30, gz + 0.9], "size": [cat_h * asp2, cat_h]})
        return out

    for s in data.get("slides", []):
        pls = _scene_planes(s)
        if not isinstance(pls, list):
            continue
        extra = []
        for i, p in enumerate(pls):
            if not isinstance(p, dict):
                continue
            if p.get("kind") == "text" and p.get("text"):
                world_h = float(p.get("textSize") or 0.6)    # world-unit height of the text
                col = _hex_rgb(p.get("textColor") or tk.get("fg", "#f0f3f8"))
                rel, aspect = _text_png(str(p["text"]), col, "s%s_p%d.png" % (s.get("index"), i))
                # billboard by default (face the camera) unless the author pinned a rotation.
                bill = p.get("rotation") is None
                pls[i] = {"kind": "plane", "src": rel, "alpha": True, "billboard": bill, "position": p["position"],
                          "size": [world_h * aspect, world_h], **({"rotation": p["rotation"]} if p.get("rotation") else {})}
            elif p.get("kind") == "bars" and isinstance(p.get("data"), list) and p["data"]:
                extra.extend(_bar_label_planes(p, s.get("index")))
            elif p.get("kind") == "stack" and isinstance(p.get("data"), list) and p["data"]:
                extra.extend(_stack_label_planes(p, s.get("index")))
        s["planes"] = list(pls) + extra


def _html_card_jobs(data):
    """Collect (html_page_rel, element_dict) for every cinematic element/plane that carries an `html` form
    page and has no `src` yet — across shot-based stage elements AND true-3D planes."""
    jobs = []
    for s in data.get("slides", []):
        stage = _scene_stage(s)
        if isinstance(stage, dict):
            for el in stage.get("elements") or []:
                if isinstance(el, dict) and el.get("html") and not el.get("src"):
                    jobs.append((str(el["html"]), el))
        for p in (_scene_planes(s) or []):
            if isinstance(p, dict) and p.get("html") and not p.get("src"):
                jobs.append((str(p["html"]), p))
    return jobs


def _generate_color_worlds(data, out_dir):
    """WIRE the generalisation engine (cine_palette) INTO the render pipeline — the audit's #1 fix. When
    `meta.cinematic_template` + `meta.accent` are set, any cinematic `card` element carrying a `colorWorld`
    content spec ({title,kicker,grad,sub}) gets its aurora backplane page GENERATED from the accent + the
    template (a deterministic per-beat transform), written under pages/, and set as the element's `html` — so
    _render_html_cards then screenshots it like any Path-A card. Colour worlds become a PRODUCT of the render,
    not a hand-run script. No-ops without a template/accent or without any colorWorld element (fully additive)."""
    meta = data.get("meta") or {}
    tpl = meta.get("cinematic_template")
    if not tpl:
        return
    try:
        import cine_palette as _cinep
    except Exception as e:
        print("[color-worlds] cine_palette unavailable (%s) — skipped" % e)
        return
    accent = meta.get("accent") or _theme(out_dir).get("accent") or "#7c5cff"
    cine = [s for s in data.get("slides", []) if _scene_stage(s) or _scene_planes(s)]
    if not cine:
        return
    pals = _cinep.derive(accent, str(tpl), len(cine))
    skill = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pages_dir = os.path.join(out_dir, "pages")
    made = 0
    for i, s in enumerate(cine):
        stage = _scene_stage(s)
        for el in ((stage or {}).get("elements") or []) if isinstance(stage, dict) else []:
            cw = el.get("colorWorld")
            if not isinstance(cw, dict) or el.get("html") or el.get("src"):
                continue
            os.makedirs(pages_dir, exist_ok=True)
            html = _cinep.aurora_page(pals[i], skill, out_dir, title=str(cw.get("title", "")),
                                      kicker=str(cw.get("kicker", "")), grad_words=str(cw.get("grad", "")),
                                      sub=str(cw.get("sub", "")))
            rel = os.path.join("pages", "_cw_%s.html" % re.sub(r"[^A-Za-z0-9_]+", "", str(el.get("id") or i)))
            with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as f:
                f.write(html)
            el["html"] = rel                              # now a Path-A card -> screenshotted below
            made += 1
    if made:
        print("[color-worlds] generated %d colour-world page(s) from template=%s accent=%s" % (made, tpl, accent))


def _render_html_cards(data, out_dir, scale=2):
    """PATH A — the bridge that lets a cinematic shot's content be ANY of the HTML tier's bespoke forms
    (flow / timeline / quadrant / metric-wall / comparison / …), NOT the one generic glass panel. A stage
    element or 3D plane carries `html: "pages/<name>.html"` (an author-written form page, the SAME kind the
    HTML tier renders). We screenshot that page through the SAME headless-Chrome path the HTML tier uses
    (snapshot/_cdp), at `scale`x device-pixels so it stays razor-sharp when the camera pushes in, then set
    the element's `src` to the PNG — and the existing image-plane / textured-3D-plane rendering flies the
    camera over it. RESILIENCE (html cards ARE the cinematic content, not decoration): a missing page or a
    per-card screenshot HICCUP prints a warning and SKIPS that one element (the other cards still render); but
    if Chrome can't start at all, or EVERY card fails, that would ship a content-BLANK film, so it raises —
    fail loud, never silently blank. A single bad card must not crash the render; a total content loss must
    not pass as green."""
    jobs = _html_card_jobs(data)
    if not jobs:
        return
    try:
        import _cdp
        import scenes
        import snapshot
        from urllib.parse import quote
    except Exception as e:
        print("[path-a] toolchain unavailable (%s) — html cards not rendered" % e)
        return
    meta = data.get("meta") or {}
    vertical = meta.get("aspect") == "9:16"
    W, H = rd._canvas(meta, vertical)
    cards_dir = os.path.join(out_dir, ".cards")
    os.makedirs(cards_dir, exist_ok=True)
    try:
        chrome = _cdp.Chrome(scenes._chrome_bin(meta), W, H, device_scale=scale)
    except Exception as e:
        # Chrome can't start but the deck NEEDS html cards for its content — this is fatal, not best-effort.
        raise RuntimeError("[path-a] Chrome unavailable (%s) — %d html card(s) are the cinematic content and "
                           "cannot be rendered. Install Google Chrome or set meta.chrome_path." % (e, len(jobs)))
    ok = 0
    try:
        for i, (html_rel, el) in enumerate(jobs):
            page = os.path.abspath(os.path.join(out_dir, html_rel))
            if not os.path.exists(page):
                print("[path-a] page not found: %s — element skipped" % html_rel)
                continue
            rel = os.path.join(".cards", "card_%02d.png" % i)
            try:
                chrome.shot("file://" + quote(page) + "?p=1.0", os.path.join(out_dir, rel))
            except Exception as e:
                print("[path-a] screenshot FAILED for %s (%s) — element skipped" % (html_rel, e))
                continue
            try:
                snapshot._ensure_png(os.path.join(out_dir, rel))   # CDP returns JPEG bytes -> real PNG
            except Exception:
                pass
            el["src"] = rel
            if "kind" in el and el.get("kind") == "card":          # stage `card` alias -> the image renderer
                el["kind"] = "image"
            elif _is_stage_el(el):
                el.setdefault("kind", "image")
            ok += 1
    finally:
        chrome.close()
    print("[path-a] rendered %d/%d html card(s) at %dx -> .cards/" % (ok, len(jobs), scale))
    if jobs and ok == 0:
        # every card failed -> the film would render content-blank. Fail loud rather than ship empty scenes.
        raise RuntimeError("[path-a] ALL %d html card(s) failed to screenshot — no cinematic content would "
                           "render. Check Chrome/CDP and the page files." % len(jobs))


def _is_stage_el(el):
    """True for a shot-based stage element (has a string `id`); a 3D plane has no id."""
    return isinstance(el.get("id"), str)


def _hex_rgb(h):
    h = str(h).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (240, 243, 248)


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
_MATCH_SHAPES = ("box", "bar", "line", "dot")


def _clean_match(m, tag):
    """Coerce a SHARED-ELEMENT match-cut spec (P3+). `from`/`to` are [cx,cy,w,h] as FRACTIONS of the frame
    (0..1): from==to is a pure HOLD match-cut (the anchor stays put while the scenes change), from!=to a
    MORPH (it travels/scales A->B). Fail loud on a malformed spec — a NaN would blank the anchor."""
    if not isinstance(m, dict):
        raise RuntimeError("cinematic %s: match_cut must be an object" % tag)

    def _box(key):
        v = m.get(key)
        if not (isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v)):
            raise RuntimeError("cinematic %s: match_cut.%s must be [cx,cy,w,h] fractions 0..1" % (tag, key))
        return [_num(x, "%s match_cut.%s[%d]" % (tag, key, k)) for k, x in enumerate(v)]

    shape = str(m.get("shape", "box"))
    if shape not in _MATCH_SHAPES:
        raise RuntimeError("cinematic %s: match_cut.shape %r must be one of %s" % (tag, shape, "|".join(_MATCH_SHAPES)))
    out = {"shape": shape, "from": _box("from"), "to": _box("to")}
    if m.get("color"):
        out["color"] = str(m["color"])
    return out


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
    # The breath silence only exists if tts MASTERING actually padded it — which needs ffmpeg. On a
    # Node-present/ffmpeg-absent host mastering is silently skipped (audio_master left unset), so there is
    # NO trailing silence and an overlap would eat live narration. Treat 'no ffmpeg' like audio_master:False.
    breath = 0.0 if (meta.get("audio_master") is False or not shutil.which("ffmpeg")) \
        else float(meta.get("audio_breath", 0.42) or 0.42)
    cap = max(1, int(round(breath * fps)))                  # overlap ceiling = the breath (A/V safety)
    for i in range(len(scenes)):
        scenes[i]["transitionToNext"] = None
    for i in range(len(scenes) - 1):
        a, b = scenes[i], scenes[i + 1]
        seam = max(int(a.get("fadeOutFrames") or 0), int(b.get("fadeInFrames") or 0))
        # a match-cut REQUIRES an overlap to carry the anchor — force a breath-length seam even on a hard cut.
        match = _clean_match(a["match_cut"], "scene %s" % a.get("index")) if a.get("match_cut") else None
        if seam <= 0 and not match:                          # a hard cut — no transition
            continue
        style = str(a.get("transitionStyle") or style_default)
        a["transitionToNext"] = {"style": _TRANSITION_STYLE.get(style, "fade"),
                                 "durationInFrames": min(seam if seam > 0 else cap, cap)}
        if match:                                            # the seam carries a shared-element anchor
            a["transitionToNext"]["match"] = match
        a["fadeOutFrames"] = 0                               # TransitionSeries now owns this seam
        b["fadeInFrames"] = 0
    return scenes


def build_props(data, out_dir, vertical=False, reduced_motion=False):
    """Pure storyboard -> Remotion input-props dict (no Node, no IO beyond reading durations).
    Paths stay RELATIVE to out_dir; render() passes --public-dir=out_dir so staticFile() resolves them.
    Threads the same per-scene fields the local renderer honours: motion (Ken Burns from/to), fit
    (contain/cover), captions, transitions — plus a canvas-derived caption font size."""
    meta = data.get("meta") or {}
    # motion_personality (#10): one dial that scales EVERY move's amplitude, so the whole film shares one
    # motion physics (a calm product film drifts; an energetic launch pushes). The cinematic tier used to
    # drop this field; now it flows into the shared camera ease/amplitude. Default balanced (1.0).
    _MOTION_AMP = {"calm": 0.72, "precise": 0.8, "weighty": 0.9, "balanced": 1.0, "smooth": 1.0,
                   "editorial": 1.0, "bold": 1.35, "energetic": 1.4}
    motion_amp = _MOTION_AMP.get(str(meta.get("motion_personality", "balanced")).lower(), 1.0)
    vertical = vertical or meta.get("aspect") == "9:16"
    W, H = rd._canvas(meta, vertical)
    fps = int(meta.get("fps", 30))
    reduced = bool(reduced_motion or meta.get("reduced_motion"))
    captions_on = meta.get("captions", True)
    # DIEGETIC BRIDGE selector: ONE advance-gesture per film, from meta.bridge ('auto' → derived from the
    # deck's aesthetic so a terminal/mono deck types-and-Enters). Only scenes that carry a `bridge_label`
    # (the command/phrase) get the gesture on their TAIL — minor beats stay plain cuts; reduced-motion drops
    # all gestures. The full gesture menu + per-aesthetic mapping is in references/camera-and-bridges.md.
    _tok = _theme(out_dir)
    _IMPLEMENTED_BRIDGES = {"none", "type-enter"}   # gestures BridgeOverlay actually renders (others are designed)
    _bridge_gesture = str(meta.get("bridge") or "none").lower()
    if _bridge_gesture == "auto":
        _mono = (_tok.get("fontKind") == "mono") or (str(_tok.get("style", "")).lower() == "terminal")
        _bridge_gesture = "type-enter" if _mono else "none"   # type-enter is the natively-rendered gesture today
    if _bridge_gesture not in _IMPLEMENTED_BRIDGES:
        # a documented-but-not-yet-rendered gesture (cursor-click / page-turn / …) or a typo would SILENTLY
        # no-op (BridgeOverlay returns null) and swallow every bridge_label. Fail LOUD to a plain cut instead —
        # mirror how shot type/motion/easing are validated (references/camera-and-bridges.md lists the menu).
        print("[render_remotion] meta.bridge=%r is not a rendered gesture (implemented: %s) — the seams will use "
              "a plain cut. Use 'type-enter' or 'auto', or leave it unset." % (_bridge_gesture, sorted(_IMPLEMENTED_BRIDGES)))
        _bridge_gesture = "none"
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
        bridge = None
        if not reduced and _bridge_gesture not in ("none", "") and s.get("bridge_label"):
            bridge = {"gesture": _bridge_gesture, "label": str(s.get("bridge_label"))}
            if s.get("bridge_at_frame") is not None:
                bridge["atFrame"] = int(round(_num(s["bridge_at_frame"], "scene %s bridge_at_frame" % s.get("index"))))
        # DoF must be ON for a rack-focus / REVEAL soft-arrival to SHOW: SceneStage applies the focus blur only
        # when dof is enabled, but RACK_FOCUS + the REVEAL recast do their whole job through focusZ — so without
        # dof they render as a crisp static hold (a silent no-op). Auto-enable it for those shots. (Audit P1.)
        _dof = bool(s.get("dof"))
        if shot_based and not _dof:
            for _sh in (shots or []):
                if str(_sh.get("motion", "")).upper() == "RACK_FOCUS" or str(_sh.get("type", "")).upper() == "REVEAL":
                    _dof = True
                    break
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
            "motionAmp": motion_amp if shot_based else None,  # motion_personality amplitude (#10)
            "dof": _dof if shot_based else None,  # rack-focus DoF (opt-in, or auto-on for RACK_FOCUS/REVEAL)
            "planes": planes if three_d else None,            # P6 TRUE-3D: WebGL content planes
            "camera3d": camera3d if three_d else None,        # P6 orbit/crane camera keyframes
            "filmLook": (s.get("film_look") if s.get("film_look") is not None else meta.get("film_look", True)) if three_d else None,
            "reveal3d": bool(s.get("reveal3d")) if three_d else None,   # opt-in dark->lit hero reveal (3D)
            "camera": camera,                        # cinematic FLAT: eased virtual-camera keyframes (or None)
            "lens": lens,                            # cinematic 3D: dolly/pitch/yaw keyframes (or None)
            "perspective": float(perspective) if perspective else None,
            "layers": layers,                        # cinematic: depth planes (or None)
            "reducedMotion": reduced,                # freeze the camera + show reveals instantly
            "transitionStyle": s.get("transition_style"),  # per-scene seam-look override (else meta default)
            "match_cut": s.get("match_cut"),         # shared-element match-cut INTO the next scene (P3+); _transitions
            #                                          coerces it onto transitionToNext.match (dropped from props after)
            "bridge": bridge,                        # diegetic advance gesture on this scene's tail (or None)
        })
    _transitions(scenes, meta, fps)                  # derive cross-scene transitions + de-double the seam fades
    return {"width": W, "height": H, "fps": fps, "captionFontPx": rd._caption_font_px(W, H, meta=meta),
            "theme": _theme(out_dir), "scenes": scenes,
            "heroMark": meta.get("hero_mark") or None}   # continuity spine (#11): a persistent brand lockup


def available():
    """True if the Node toolchain + an installed remotion/ project are present."""
    return bool(shutil.which("npx")) and os.path.isdir(os.path.join(_REMOTION_DIR, "node_modules"))


def render(out_dir, vertical=False, reduced_motion=False, sample=None, log="error", no_plan=False):
    """Render the whole deck to out.mp4 (+ out.srt), or a single scene (sample=N) to sample.mp4 for the
    step-8 sign-off checkpoint. Fails loudly on non-image scenes (which would render blank)."""
    path = os.path.join(out_dir, "storyboard.json")
    data = sb.load(path)
    # PLAN-TRACE (agent-workflow enforcement): a cinematic film must have been PLANNED by the pipeline. Require
    # content_plan.json (the content-planner's output) in out_dir so a hand-authored storyboard can't silently
    # SKIP the workflow — making "bypassable" into "walk the workflow, or opt out on purpose". Checked BEFORE the
    # toolchain probe so a workflow violation fails fast (and is testable without Node). Escape with --no-plan /
    # meta.no_plan for a deliberate hand-authored film.
    # Match the project's ACTUAL cinematic definition (not just type=='cinematic') so a cinematic3d deck or a
    # shot/layer/lens-based deck typed 'slide' can't bypass the content_plan.json enforcement. (Audit P2.)
    _cine_deck = any(s.get("type") in ("cinematic", "cinematic3d") or _scene_planes(s) or _scene_layers(s)
                     or (_scene_stage(s) and _scene_shots(s)) or s.get("lens") or s.get("camera")
                     for s in data.get("slides", []))
    _no_plan = no_plan or bool((data.get("meta") or {}).get("no_plan"))
    if _cine_deck and not _no_plan and not os.path.isfile(os.path.join(out_dir, "content_plan.json")):
        raise RuntimeError(
            "cinematic render has no content_plan.json — the agent workflow (content-planner -> design-director "
            "-> scriptwriter -> design-critic, see SKILL.md) must run before a cinematic render, so the film is "
            "actually PLANNED and DESIGNED, not hand-improvised. Hand-authoring on purpose? pass --no-plan (CLI) "
            "or set meta.no_plan:true.")

    if not shutil.which("npx"):
        raise RuntimeError("Node/npx not found — the Remotion tier needs Node.js. Install Node, then "
                           "`cd %s && npm install`, or use the local renderer (meta.renderer=local)." % _REMOTION_DIR)
    if not os.path.isdir(os.path.join(_REMOTION_DIR, "node_modules")):
        raise RuntimeError("remotion/ deps not installed — run `cd %s && npm install` once." % _REMOTION_DIR)

    if sample is not None:                            # single-scene preview for the step-8 checkpoint
        data = {"meta": data.get("meta", {}), "slides": [s for s in data.get("slides", []) if s.get("index") == sample]}
        if not data["slides"]:
            raise RuntimeError("no scene with index %s to sample" % sample)
    missing = [s.get("index") for s in data.get("slides", []) if not s.get("audio") or not s.get("duration")]
    if missing:
        raise RuntimeError("scene(s) %s have no audio/duration — run tts.py before rendering" % missing)

    # Copy bundled fonts to out_dir/.fonts/ for @remotion/fonts to load
    _copy_fonts(out_dir)
    _generate_color_worlds(data, out_dir)  # WIRE cine_palette: template+accent -> GENERATED colour-world pages
    _render_html_cards(data, out_dir)  # PATH A: `html` form pages -> screenshot -> textured plane `src`
    _rasterize_text3d(data, out_dir)   # 3D text -> transparent PNG textured planes (troika renders blank)

    # The blank-scene gate runs AFTER the pre-passes so it sees the FINAL planes: e.g. no PIL drops every
    # kind:'text' plane, leaving a scene content-blank — catch it here rather than render an empty frame.
    bad = unsupported_scenes(data)
    if bad:                                           # the biggest trap: non-image scenes render BLANK
        raise RuntimeError(
            "the remotion cinematic tier renders IMAGE scenes only, but scene(s) %s carry non-image "
            "content (html/chart/timeline/…) that would render BLANK. Use the local renderer "
            "(meta.renderer=local) for an html/designed deck, or give those scenes an `image`."
            % ", ".join("#%s(%s)" % (i, t) for i, t in bad))

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
    # GPU-backed rasterisation (ANGLE) — needed by the whole CINEMATIC tier, not only TRUE-3D `planes`:
    # TRUE-3D needs WebGL (else black frames), and the CSS-3D CinematicScene/SceneStage (a virtual camera over
    # depth planes + large card/text planes) is ALSO GPU-bound — software-rasterised it blows past the 30s/frame
    # timeout (a scene once took >9min and FAILED; ANGLE cut it to ~30s). But a PURE-IMAGE (Ken-Burns) deck does
    # NOT need GL, so only add it when a scene actually uses a GPU path — this keeps image-only decks portable
    # on GL-less hosts (adding --gl there regressed them). Backend: 'angle' on macOS/Windows; 'swangle'
    # (SwiftShader) on GPU-less headless Linux/CI/Lambda; override via REMOTION_GL.
    needs_gl = any(sc.get("planes") or sc.get("stage") or sc.get("layers") or sc.get("lens") or sc.get("camera")
                   for sc in props["scenes"])
    if needs_gl:
        gl = os.environ.get("REMOTION_GL") or ("angle" if sys.platform in ("darwin", "win32") else "swangle")
        cmd.append("--gl=" + gl)
        # raise the per-frame timeout so a slow GPU-less peak-framing frame degrades to 'slower', not a failure.
        cmd.append("--timeout=" + str(int(os.environ.get("REMOTION_TIMEOUT_MS", "120000") or "120000")))
    print("[render_remotion] %s: %d scene(s), %dx%d @%dfps -> %s"
          % ("sample" if sample is not None else "full", len(props["scenes"]),
             props["width"], props["height"], props["fps"], out_mp4))
    try:
        subprocess.run(cmd, cwd=_REMOTION_DIR, check=True)
    except subprocess.CalledProcessError:
        # a GL-init failure on a GPU-less/GL-restricted host is the likeliest cause of a render that would
        # otherwise work — retry ONCE without --gl (software raster: slower, but portable). If it fails again,
        # re-raise with a hint. Only fires when --gl was actually added (a GL-needing deck on an odd host).
        if any(a.startswith("--gl=") for a in cmd):
            print("[render_remotion] render failed with GL — retrying ONCE without --gl (software raster; slower). "
                  "If this recurs, set REMOTION_GL to a working backend (e.g. 'swangle' on headless Linux).")
            subprocess.run([a for a in cmd if not a.startswith("--gl=")], cwd=_REMOTION_DIR, check=True)
        else:
            raise
    try:
        os.unlink(props_path)                         # transient — don't leave it in the out_dir
    except OSError:
        pass

    _write_filmstrips(out_dir, data, out_mp4)         # the D12 evidence the design-critic judges from
    _run_shot_qa(out_dir, out_mp4)                     # P5: score the rendered frames -> shot_qa.json (advisory print)
    if sample is None:                                # out.srt — overlap-aware (cross-scene transitions)
        _write_srt_overlapped(data, out_dir, os.path.join(out_dir, "out.srt"))
        meta = data.get("meta") or {}
        if meta.get("sound_design"):                  # OPT-IN two-track SFX(+BGM) mix (#8), post-render
            try:
                import sfx
                sfx.mix(out_dir, out_mp4, props["scenes"], meta, int(meta.get("fps", 30)))
            except Exception as e:
                print("[sfx] skipped (%s)" % e)
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
        scored = [sc for sc in rep["scenes"] if not sc.get("abstained")]
        unscored = [sc for sc in rep["scenes"] if sc.get("abstained")]
        bad = [sc for sc in scored if not sc["passed"]]
        msg = "[shot_qa] %d/%d scored cinematic scenes pass (threshold %d)" % (
            len(scored) - len(bad), len(scored), rep["threshold"])
        if bad:
            msg += "  — REVIEW: " + ", ".join("#%s %s" % (b["index"], b["floors"] or b["composite"]) for b in bad)
        if unscored:
            msg += "  — UNSCORED (unmeasurable): " + ", ".join("#%s" % u["index"] for u in unscored)
        print(msg)
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
    # Cross-scene transitions OVERLAP the two scenes, so every later scene starts `overlap` frames EARLY —
    # the mp4 timeline is shorter than the naive Σduration. Subtract the cumulative overlap from the seek
    # time (mirroring _write_srt_overlapped) so each scene's filmstrip slices its OWN frames, not the next
    # scene's. (Audit P1: without this the D12 evidence drifts past scene boundaries on a multi-seam film.)
    fps = int((data.get("meta") or {}).get("fps", 30) or 30)
    try:
        over = {sc["index"]: (sc.get("transitionToNext") or {}).get("durationInFrames", 0)
                for sc in build_props(data, out_dir)["scenes"]}
    except Exception:
        over = {}
    t0 = 0.0
    cum_overlap = 0.0
    for s in data.get("slides", []):
        dur = float(s.get("duration") or 0)
        is_cine = s.get("type") == "cinematic" or _scene_layers(s) or _scene_planes(s) or (_scene_stage(s) and _scene_shots(s))
        if is_cine and dur > 0.2:
            n = 5
            tiles = []
            for i in range(n):
                t = (t0 - cum_overlap) + dur * (0.06 + 0.9 * i / (n - 1))
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
        cum_overlap += float(over.get(s.get("index"), 0)) / fps
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
    ap.add_argument("--no-plan", action="store_true",
                    help="allow a hand-authored cinematic render with no content_plan.json (skip the agent-workflow trace)")
    a = ap.parse_args()
    render(a.out_dir, vertical=a.vertical, reduced_motion=a.reduced_motion, sample=a.sample, log=a.log, no_plan=a.no_plan)


if __name__ == "__main__":
    main()
