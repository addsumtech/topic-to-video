#!/usr/bin/env python3
"""Render storyboard.json through the REMOTION2 bespoke-shot LIBRARY — the skill's Remotion cinematic tier.

Each storyboard scene names a `shot` (a register id from remotion/LIBRARY.md, chosen by the shot-director
agent) + optional topic `shot_props`; this sequences the chosen shots through the data-driven `Film`
composition (cross-dissolve transitions + scene-relative captions + per-scene edge-tts narration served from
out_dir via `--public-dir`), then writes delivery parity — `out.srt` + `_keyframes/scene_NN.png` (the
shot-critic filmstrip + the `check_av` A/V gate) + an optional `meta.sound_design` SFX/BGM bed.

The html/local tier (`render.py`) is a completely separate module and is byte-untouched by this one. The legacy
generic-scene Remotion machinery (atmospheres/templates/planes/ThreeScene) was REMOVED in the phase-3 cutover.
Requires the Node toolchain + `cd remotion && npm install` once (doctor.py reports availability).
"""
import argparse, json, os, shutil, subprocess
import re
import storyboard as sb

_REMOTION2_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion")
# `_REMOTION2_TR` (the cross-dissolve length the output timeline is compressed by per cut) is defined below,
# from runtime/motion.ts's SEAM_FRAMES — it used to be a literal 12 here, restated in three modules.

# The MARKED-seam grammar (P2): a storyboard scene MARKS the transition INTO it. Only kinetic styles produce a
# mark — everything else (fade/dip/drift/blur/none/absent) is the luminance-safe default fade in Film.tsx, and a
# kinetic mark across a dark↔light gap is itself suppressed back to fade there (Film's pickPresentation). This
# maps the deck's `transition_style` vocabulary (shared with the local tier) onto the bespoke transition set;
# an explicit `transition_in:{type,direction}` on the scene wins outright (a direct remotion mark).
_TRANSITION_STYLE = {
    # `push` and `lift` are the film words for the two directions of Remotion's slide. They are spelled here
    # AND in `_KINETIC_TYPES` below, because a relation the html tier can name and this one cannot is a hole:
    # `transition_in: {"type": "push"}` used to miss the kinetic set and come out as an anonymous fade.
    "slide": {"type": "slide", "direction": "from-right"}, "push": {"type": "push"},
    "lift": {"type": "lift"}, "slide-up": {"type": "lift"},
    "wipe": {"type": "wipe", "direction": "from-bottom"},
    # the three relations this tier could not claim until the seams below were built (Film.tsx)
    "fadethrough": {"type": "fadethrough"}, "fade-through": {"type": "fadethrough"},
    "drift": {"type": "drift"},
    "blur": {"type": "blur"}, "rack": {"type": "blur"}, "defocus": {"type": "blur"},
    "clock": {"type": "clock"}, "clockwipe": {"type": "clock"}, "clock-wipe": {"type": "clock"},
    "dissolve": {"type": "dissolve"},
    "carry": {"type": "carry"}, "collapse": {"type": "carry"}, "line": {"type": "carry"}, "match-cut": {"type": "carry"},
    # the other two DEPTH seams. Named by what they DO, with the aliases an author is likely to reach for.
    "through-dark": {"type": "through-dark"}, "flight": {"type": "through-dark"},
    "through-black": {"type": "through-dark"},
    "portal": {"type": "portal"}, "aperture": {"type": "portal"},
    # the four that take hold of ONE thing on the frame, or land one beat (remotion/src/seams.tsx). A style word
    # names no anchor, so `container`/`grow`/`through-window` spelled here still need `transition_in.carry` —
    # validate.py refuses them without one rather than letting them become a fade.
    "container": {"type": "container"}, "container-transform": {"type": "container"},
    "shared-element": {"type": "container"},
    "grow": {"type": "grow"}, "expand": {"type": "grow"},
    "through-window": {"type": "through-window"}, "zoom-through": {"type": "through-window"},
    "punch": {"type": "punch"}, "push-cut": {"type": "punch"}, "pushcut": {"type": "punch"},
    # THE HARD CUT (remotion/src/seams.tsx `cut`): the picture changes on the seam's middle frame and the audio keeps
    # the seam's overlap. `cut` was an html word only ("no seam at all") and resolved to the default cross-fade here,
    # because this tier had no picture for it — so a board that asked for a hard cut got a dissolve.
    "cut": {"type": "cut"}, "hard-cut": {"type": "cut"},
    # the HIDDEN cut: a panel passes the lens and the beat changes behind it — continuity of motion (seams.tsx sweep)
    "sweep": {"type": "sweep"}, "hidden-cut": {"type": "sweep"},
}
# `focus`, `through-dark` and `portal` are the DEPTH seams (Film.tsx). They belong here or a storyboard that
# asks for one is silently downgraded to a fade, which is the exact "built but unreachable" failure this
# file's `transition_in` docstring was written about — and it has already cost this repo two deliveries.
_KINETIC_TYPES = {"slide", "push", "lift", "wipe", "clock", "dissolve", "fadethrough", "drift", "blur",
                  "carry", "focus", "through-dark", "portal", "return",
                  "container", "grow", "through-window", "punch", "cut", "sweep"}
# THE CUTS THAT ARE NOT MARKS. A marked seam is punctuation and is budgeted (2-3 a film); a hard cut is the absence
# of a transition — the film's default grammar on a film whose energy asks for it (seam_plan.py) — and must not
# spend that budget or set off the "too many marks" warnings.
HARD_CUT_TYPES = {"cut"}
# The seams that take hold of a marked element (runtime/carry `data-carry`) and need to be told which one.
ANCHORED_TYPES = {"container", "grow", "through-window"}
# A match_cut's shapes, in the order the corner rounds (Film.tsx containerSpec).
MATCH_SHAPES = ("box", "bar", "line", "dot")


def match_cut_seam(prev_slide):
    """The OUTGOING beat's `match_cut` as the container seam it now is, or None.

    `match_cut: {shape, from: [cx,cy,w,h], to: [cx,cy,w,h]}` was validated and documented for years and drawn by
    nothing — a dead spec. It is the container seam by declared rects: the region `from` on the leaving beat is
    carried to the region `to` on the arriving one (remotion/src/seams.tsx). Shape sets the corner."""
    mc = (prev_slide or {}).get("match_cut")
    if not isinstance(mc, dict):
        return None
    fr, to = mc.get("from"), mc.get("to")
    ok = lambda v: isinstance(v, (list, tuple)) and len(v) == 4 and all(  # noqa: E731
        isinstance(x, (int, float)) and not isinstance(x, bool) for x in v)
    if not (ok(fr) and ok(to)):
        return None
    out = {"type": "container", "from": [float(x) for x in fr], "to": [float(x) for x in to]}
    shape = str(mc.get("shape", "box"))
    if shape in MATCH_SHAPES:
        out["shape"] = shape
    return out


# The runtime's own settled point, parsed from motion.ts so the two cannot drift: a keyframe must be the
# frame `useT()` calls "reveal complete, exit not begun", or every visual review reads an unfinished shot.
def _motion_const(name):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "runtime", "motion.ts")
    m = re.search(r"\b%s\s*=\s*([0-9.]+)" % name, open(p, encoding="utf-8").read())
    if not m:
        raise RuntimeError("%s not found in %s — the keyframe frame is derived from it" % (name, p))
    return float(m.group(1))


def _settled_t():
    return _motion_const("REDUCED_MOTION_T")


SETTLED_T = _settled_t()
SEAM_FRAMES = int(_motion_const("SEAM_FRAMES"))
ENTRY_T = _motion_const("ENTRY_T")
_REMOTION2_TR = SEAM_FRAMES        # film_energy_qa and settled_frame read it under this name


def frame_at_t(durF, t):
    """The frame at which `useT()` returns `t`. One inversion, used by everything that needs a moment."""
    durF = max(1, int(durF))
    pad = min(SEAM_FRAMES, (durF - 1) // 3)
    span = max(1, durF - 1 - 2 * pad)
    u = (float(t) - ENTRY_T) / max(1e-6, 1 - ENTRY_T)
    return pad + max(0.0, min(1.0, u)) * span


def settled_frame(durF):
    """The frame at which `useT()` returns SETTLED_T — inverted from useT, not re-derived beside it.

    This used to be `pad + SETTLED_T * (durF - 2*pad)`, which mirrored an earlier useT and then quietly
    stopped mirroring it twice over: useT's span is `dur - 1 - 2*pad`, and it now maps its progress through
    ENTRY_T (a shot is HELD at its composed skeleton rather than at nothing while the dissolve runs). The
    keyframe was landing at t=0.875 on a normal beat and t=0.984 on a short one — past the settled state and
    into the exit, on the very frame every visual gate and the shot-critic read. Two places computing the
    same quantity is the failure this codebase keeps paying for; there is one now, and it is an inversion of
    the definition rather than a copy of it.
    """
    return frame_at_t(durF, SETTLED_T)


_SPACED_CAPS = re.compile(r"\b(?:[A-Z] ){1,7}[A-Z]\b")


def _caption_for_eye(text):
    """The narration as it should be READ — the spoken spelling-out rejoined.

    Only the unambiguous half is done automatically: a run of two or more single capitals separated by one
    space each is an initialism a film spelled out for the voice (`T T S` -> `TTS`). Anything else a film
    spells for the ear — a number read as words, a deliberate pause — needs the slide's own `caption`,
    because guessing at those would edit the film's copy rather than restore it.
    """
    t = str(text or "")
    return _SPACED_CAPS.sub(lambda m: m.group(0).replace(" ", ""), t)


# WORDS THAT NAME A DELIBERATE NON-MARK, and the html tier's spelling of the default. `transition_style` is
# shared with the html tier, where `dip` IS the default seam and `none` means "no seam at all". They resolve to no
# remotion mark, which is correct — but they are KNOWN, so `validate.py` must not report them as words this renderer
# cannot draw. (`cut` and `hard-cut` were here too, and drew the default cross-fade: the tier had no hard cut. They
# resolve to the `cut` seam now.)
_UNMARKED_WORDS = {"none", "dip", "fade"}


def seam_word_known(word):
    """True when this word means something here — a mark, or a deliberate absence of one."""
    w = (word or "").strip().lower()
    return bool(w) and (w in _UNMARKED_WORDS or seam_type(w) is not None)


def seam_type(word):
    """The film word for a seam → the Film.tsx `transitionIn.type`, or None when this is not a seam word.

    One resolver for both spellings (`transition_in.type` and `transition_style`) and for every alias, so a
    word that works in one place cannot be silently ignored in the other."""
    w = (word or "").strip().lower()
    if w in _KINETIC_TYPES:
        return w
    mapped = _TRANSITION_STYLE.get(w)
    return mapped["type"] if mapped else None


def is_mark(slide):
    """Does this beat's incoming seam spend the MARKED-seam budget? Any resolved seam except a hard cut."""
    ti = _transition_in(slide)
    return bool(ti) and ti.get("type") not in HARD_CUT_TYPES


def is_hard_cut(slide):
    """Is this beat's incoming seam the plain hard cut (`cut`)?"""
    ti = _transition_in(slide)
    return bool(ti) and ti.get("type") in HARD_CUT_TYPES


def _transition_in(slide, travel=None, prev=None):
    """Map a storyboard scene's transition intent → the Film `transitionIn` mark (or None = the safe default fade).
    Only a MARKED (kinetic) seam returns a value; the shot-director budgets ~2-3 per film for chapter breaks.

    `travel` is this beat's (dx, dy) from `film_board.travels`, present only on a beat that declares a
    RETURN. It arrives as an argument rather than being derived here because the vector is a property of the
    whole board — where this beat sits and where the one it names sits — and a per-slide function cannot see
    that. One definition, in `film_board`, used by the planner, the validator and this emitter alike.

    `prev` is the beat before, for its `match_cut` (the container by declared rects, `match_cut_seam`); a seam this
    beat names itself wins over it, and validate.py refuses a board where the two disagree.
    """
    if travel is not None:
        dx, dy = travel
        return {"type": "return", "dx": round(float(dx), 5), "dy": round(float(dy), 5)}
    ti = slide.get("transition_in")
    if isinstance(ti, dict) and ti.get("type"):                            # explicit remotion mark wins
        # ALIASES RESOLVE ON BOTH SPELLINGS. They resolved only for `transition_style`, so a board that wrote
        # `transition_in: {"type": "rack"}` — a word this file itself offers one line above — missed the
        # kinetic set and was answered with an anonymous fade. `seam_type` is the single resolver, and
        # `validate.py` refuses a word it cannot resolve rather than letting the seam go quiet.
        t = seam_type(ti["type"])
        if t:
            out = {"type": t}
            if ti.get("direction"):
                out["direction"] = ti["direction"]
            # the anchored seams carry WHICH element they hold (validate.py checks it against the registers)
            if t in ANCHORED_TYPES:
                for k in ("carry", "from", "to", "shape"):
                    if ti.get(k) is not None:
                        out[k] = ti[k]
            return out
    style = (slide.get("transition_style") or "").strip().lower()
    if style in _TRANSITION_STYLE:
        out = dict(_TRANSITION_STYLE[style])
        if out["type"] in ANCHORED_TYPES and isinstance(ti, dict) and ti.get("carry") is not None:
            out["carry"] = ti["carry"]
        return out
    return match_cut_seam(prev)


_CAMERA_MOVES = ("push", "pull", "hold")


def _camera(slide):
    """Map a storyboard scene's MOTIVATED camera move → the Film `camera` mark (or None = hold).

    Written inline in the scene loop first, where it referenced a variable that does not exist in that
    scope; nothing executed it until a full film render, and the gates meanwhile reported green against the
    previous out.mp4. Extracted so it can be called — and tested — on its own.
    """
    cam = (slide or {}).get("camera")
    if not isinstance(cam, dict):
        return None
    move = str(cam.get("move", "")).strip().lower()
    if move not in _CAMERA_MOVES:
        return None
    out = {"move": move}
    try:
        if cam.get("amount") is not None:
            out["amount"] = float(cam["amount"])
    except (TypeError, ValueError):
        pass                                          # a bad amount falls back to the default, never crashes
    # A lateral TRAVEL, in fractions of the overscan the push already buys (runtime/depth.tsx SceneCamera).
    # Measured: a scale-only camera stamped on every beat of a 30-beat film moved its frame-diff p75 from
    # 0.0022 to 0.0029, still under the floor, against 0.0112 for the same film under a constant-velocity
    # pan. A malformed pan is dropped here and REFUSED by the runtime, so it cannot become a silent hold.
    pan = cam.get("pan")
    if isinstance(pan, (list, tuple)) and len(pan) == 2:
        try:
            out["pan"] = [float(pan[0]), float(pan[1])]
        except (TypeError, ValueError):
            pass
    # THE HAND-OFF: the move runs into its cut and the next beat inherits its velocity (Film.tsx HandoffCamera).
    # Only `true` reaches the film — a truthy string is not an instruction to move two beats.
    if cam.get("handoff") is True:
        out["handoff"] = True
    return out


# The #camera whole-film DRIFT amplitude. DEFAULT OFF (0 = still): every bespoke shot already animates itself
# (pure fn of useT), so a global breathing zoom+float ON TOP reads as a constant per-frame SHAKE — a repeated
# complaint. The drift is now OPT-IN via meta.camera_drift (a tier name OR a raw multiplier); absent = still.
# motion_personality no longer auto-enables it (it belongs to the html/image tier's per-shot Ken Burns, not here).
_MOTION_PERSONALITY = {"still": 0.0, "calm": 0.5, "gentle": 0.65, "balanced": 1.0, "lively": 1.3, "energetic": 1.6}


def _camera_amp(meta):
    cd = (meta or {}).get("camera_drift")
    if isinstance(cd, bool):
        return 1.0 if cd else 0.0
    if isinstance(cd, (int, float)):
        return max(0.0, float(cd))
    if cd is None:
        return 0.0                                   # still by default — no whole-film drift
    return _MOTION_PERSONALITY.get(str(cd).strip().lower(), 0.0)


def available():
    """True if the Node toolchain + the installed remotion/ project are present."""
    return bool(shutil.which("npx")) and os.path.isdir(os.path.join(_REMOTION2_DIR, "node_modules"))


def _remotion_shot_ids():
    """The valid shot ids = the component files in remotion/src/shots (auto-syncs with the library)."""
    d = os.path.join(_REMOTION2_DIR, "src", "shots")
    return {f[:-4] for f in os.listdir(d) if f.endswith(".tsx")} if os.path.isdir(d) else set()



_DEC = "\x00"


def t_at_seconds(sec, dur_frames, fps):
    """The register's `t` (runtime/motion `useT`) at `sec` seconds into its beat — the same held-edge mapping:
    the beat is held still for SEAM_FRAMES at each edge and `t` rests at ENTRY_T through the entry hold."""
    seam, entry = SEAM_FRAMES, ENTRY_T
    dur = max(1, int(dur_frames))
    pad = min(seam, (dur - 1) // 3)
    span = max(1, dur - 1 - 2 * pad)
    p = min(1.0, max(0.0, (float(sec) * fps - pad) / span))
    return round(entry + (1 - entry) * p, 4)


def _stage_run_id(slide):
    import stage_runs as _sr
    return _sr.run_id(slide)


def register_props(shot, props, out_dir, map_props=None):
    """A beat's props as its REGISTER needs them, from what only the film and its files know — the ONE preparation both
    the film (build_scenes) and every gate that renders a beat alone (film_shot_props) apply. They were prepared in
    two places and drifted three ways (tests/test_prop_parity.py). Cue times and device scripts are resolved after
    this, by both callers, from the beat's audio.
      * LivingMap: the board's {map, add, focus} -> the whole map and what is on screen at the beat's two ends
        (`map_props`, from expand_living_maps over the whole board);
      * PhotoPlate: the photograph's proportions — the plate frames the WHOLE photograph (a portrait photo in the
        default landscape plate lost 67% of its height, and every mark moved off what it named);
      * PhotoToDiagram: its traced outlines and pixel width (photo_diagram_props)."""
    if map_props is not None:
        props = map_props
    if shot == "PhotoPlate" and isinstance(props.get("src"), str) and not props.get("imageAspect"):
        try:
            from PIL import Image as _Im
            with _Im.open(os.path.join(out_dir, props["src"])) as _im:
                if _im.height:
                    props = dict(props, imageAspect=round(_im.width / _im.height, 4))
        except Exception:
            pass                          # a missing or unreadable file is the renderer's problem, not ours
    if shot == "PhotoToDiagram" and isinstance(props.get("src"), str):
        props = photo_diagram_props(props, out_dir)
    if shot == "FilmScreen":
        props = film_screen_props(props, out_dir)
    return props


def with_track(props, slide):
    """The beat's `slide.track` (the through-object's in/out pose, runtime/track.ts) handed to its shot as the `track`
    prop. On the board it sits beside shot_props, not in them, so validate can hold one beat's out to the next one's in
    without reading every register's props."""
    tr = (slide or {}).get("track")
    return dict(props, track=tr) if isinstance(tr, dict) else props


def film_screen_props(props, out_dir):
    """A FilmScreen beat's files -> what the register needs to draw them at their own pixels: the clip's size and length
    (ffprobe), and its run/reel frames' width (the narrowest bounds them all). The board names only the files; a typed
    size is how a picture gets drawn past its pixels. A missing file, or a "frame" that is not one (a 2800x315 strip of
    phases was drawn 2.1x past its pixels on the promo film), stops the render by name."""
    import subprocess
    out = dict(props)
    v = out.get("video")
    if isinstance(v, str):
        v = {"src": v}
    if isinstance(v, dict) and v.get("src") and not all(v.get(k) for k in ("w", "h", "seconds")):
        path = os.path.join(out_dir, v["src"])
        if not os.path.isfile(path):
            raise RuntimeError("FilmScreen: %s does not exist in the film's folder" % v["src"])
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height:format=duration", "-of", "json", path], capture_output=True, text=True)
        try:
            j = json.loads(r.stdout)
            st = j["streams"][0]
            v = dict(v, w=int(st["width"]), h=int(st["height"]), seconds=round(float(j["format"]["duration"]), 3))
        except (ValueError, KeyError, IndexError, TypeError):
            raise RuntimeError("FilmScreen: %s is not a video ffprobe can read" % v["src"])
    if v is not None:
        out["video"] = v
    from PIL import Image as _Im
    for key in ("run", "reel"):
        f = out.get(key)
        if isinstance(f, list):
            f = {"frames": f}
        if not isinstance(f, dict) or not f.get("frames") or f.get("w"):
            continue
        widths = []
        for src in f["frames"]:
            path = os.path.join(out_dir, src)
            if not os.path.isfile(path):
                raise RuntimeError("FilmScreen: %s frame %s does not exist in the film's folder" % (key, src))
            with _Im.open(path) as im:
                if not 0.4 <= im.width / im.height <= 2.5:
                    raise RuntimeError("FilmScreen: %s frame %s is %dx%d — not a frame (a strip or a sheet?); give one "
                                       "settled frame per beat" % (key, src, im.width, im.height))
                widths.append(im.width)
        out[key] = dict(f, w=min(widths))
    return out


def photo_diagram_props(props, out_dir):
    """A PhotoToDiagram beat's photograph -> its traced outlines (scripts/photo_lines.py, cached by content) and its own
    proportions and pixel width, so the register can draw its lines and never draw the plate past the photograph's
    pixels. A photograph with no outlines to trace stops the render with photo_lines' own reason."""
    import photo_lines as _pl
    src = os.path.join(out_dir, props["src"])
    if not os.path.exists(src):
        raise RuntimeError("PhotoToDiagram: %s does not exist — fetch the photograph first (scripts/imagefetch.py)" % props["src"])
    out = dict(props)
    if not out.get("lines"):
        rel = os.path.splitext(props["src"])[0] + ".lines.png"
        _pl.ensure(src, os.path.join(out_dir, rel))
        out["lines"] = rel.replace(os.sep, "/")
    from PIL import Image as _Im
    with _Im.open(src) as _im:
        out.setdefault("imageAspect", round(_im.width / _im.height, 4))
        out.setdefault("imageW", _im.width)
    return out


def _map_of(slide):
    sp = slide.get("shot_props") or {}
    return sp.get("map") if slide.get("shot") == "LivingMap" else None


def living_map_continues(slides, i):
    """Beat i carries on the map of beat i-1 — the same picture across the cut, so the cut is between two identical
    frames (render_remotion makes it a hard cut)."""
    return i > 0 and _map_of(slides[i]) is not None and _map_of(slides[i]) == _map_of(slides[i - 1])


def expand_living_maps(slides, meta):
    """ONE structure for the whole film (LivingMap): `meta.maps[id] = {nodes, edges}` is named once; each beat names
    `{map, add, focus}`. This hands each beat the whole map plus what is on screen when it starts (`before`, the
    camera's `focusFrom`) and when it ends (`after`, `focusTo`) — beat i's start is beat i-1's end, so the picture
    carries on across the cut. A beat with no `focus` frames everything shown so far. An id the map does not hold,
    or a map the film does not name, is refused. Returns one props dict per slide (None for other beats)."""
    maps = (meta or {}).get("maps") or {}
    shown, last_focus, out = {}, {}, []
    for i, s in enumerate(slides):
        mid = _map_of(s)
        if mid is None:
            out.append(None)
            continue
        m = maps.get(mid)
        if not isinstance(m, dict) or not m.get("nodes"):
            raise RuntimeError("scene #%d: LivingMap names map %r, which meta.maps does not define (nodes + edges)" % (i + 1, mid))
        ids = [str(n.get("id")) for n in m["nodes"]]
        sp = dict(s.get("shot_props") or {})
        for k in ("add", "focus"):
            bad = [x for x in (sp.get(k) or []) if str(x) not in ids]
            if bad:
                raise RuntimeError("scene #%d: LivingMap `%s` names %s, not in map %r (%s)" % (i + 1, k, bad, mid, ", ".join(ids)))
        before = list(shown.get(mid, []))
        after = before + [str(x) for x in (sp.get("add") or []) if str(x) not in before]
        if not after:
            raise RuntimeError("scene #%d: LivingMap shows nothing — `add` the first nodes of map %r" % (i + 1, mid))
        to = [str(x) for x in sp.get("focus")] if sp.get("focus") else after
        # the camera starts where the last beat left it — unless another beat came between, when nothing on screen is
        # there to move from (what an earlier stretch built is still drawn, from the first frame)
        frm = last_focus.get(mid) if living_map_continues(slides, i) else to
        props = {k: v for k, v in sp.items() if k not in ("map", "add", "focus")}
        props.update({"nodes": m["nodes"], "edges": m.get("edges") or [], "before": before, "after": after,
                      "focusFrom": frm, "focusTo": to})
        out.append(props)
        shown[mid], last_focus[mid] = after, to
    return out


_TIME_KEYS = {"hits", "hold", "freeze", "sakuga"}


def resolve_time(spec, out_dir, audio, narration, dur_s, fps, where):
    """`slide.time` -> the beat's time grammar in SECONDS (runtime/timeGrammar.ts reads it; Film.tsx checks its bounds).

    A time is a number of seconds inside the beat or `{"cue": "<words the voice says>", "offset"?: s}`, resolved
    from the beat's own word times like any cued prop — so a hit lands on the word that names the impact. An unknown
    key is refused: a misspelt `hitz` would otherwise draw a beat with no hit and no complaint."""
    if not isinstance(spec, dict) or not set(spec) <= _TIME_KEYS:
        raise RuntimeError("scene %s: `time` takes %s, got %r" % (where, ", ".join(sorted(_TIME_KEYS)), spec))

    def sec(v, what):
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        if isinstance(v, dict) and "cue" in v:
            return float(resolve_cue_props({"x": v}, out_dir, audio, narration, dur_s, fps, seconds=True)["x"])
        raise RuntimeError("scene %s: time %s must be seconds or {\"cue\": ...}, got %r" % (where, what, v))

    out = {}
    if "hits" in spec:
        out["hits"] = [sec(h, "hits[%d]" % k) for k, h in enumerate(spec["hits"] or [])]
    if "hold" in spec:
        out["hold"] = spec["hold"]
    if "freeze" in spec:
        fz = spec["freeze"] or {}
        out["freeze"] = {"at": sec(fz.get("at"), "freeze.at"), "hold": float(fz.get("hold") or 0)}
    if "sakuga" in spec:
        sk = spec["sakuga"] or {}
        out["sakuga"] = {"until": sec(sk.get("until"), "sakuga.until"), "every": sk.get("every", 2)}
    return out


def resolve_cue_props(props, out_dir, audio, narration, dur_s, fps, seconds=False):
    """A prop written `{"cue": "<words the narration says>"}` becomes the `t` at which the voice says them.

    WHY. A register that changes state at a fixed fraction of its clip changes it at a moment that has nothing
    to do with the sentence over it. Measured on a delivered film: CompanionCard turned its card grey at ~19.9s
    while the voice was still saying 「绿色的工作中」 (20.5-21.7s) — for a second the frame said 等待中 under a
    sentence saying 工作中. The timing belongs to the narration, and the narration's own word times are on disk
    (tts.py writes `audio/NN.words.json`), so the board names the WORDS and this puts the event on them. Without
    word times the position is estimated from the narration text, the same fallback the html tier's cues use.
    `{"cue": ..., "offset": seconds}` shifts it. An anchor the narration does not contain is an ERROR — landing
    it anywhere would be exactly the guess this exists to remove.

    LISTS OF TIMED ITEMS resolve IN ORDER. A prop that is a list of objects carrying `at: {"cue": ...}` — a
    device script's steps, a chat thread's messages — is ONE ordered search: each cue is looked for after the
    previous one's match, so a phrase the narration says twice lands on two successive items, and a cue the
    narration reaches only BEFORE the previous item's is an error rather than a silent swap.

    `seconds=True` writes SECONDS into the beat instead of a register `t` — a stage run's steps, whose beat has no
    seam pad and no warp (scripts/stage_runs.py `resolve_steps`)."""
    def is_cue(v):
        return isinstance(v, dict) and "cue" in v and set(v) <= {"cue", "offset"}

    def timed_list(v):
        return isinstance(v, list) and any(isinstance(x, dict) and is_cue(x.get("at")) for x in v)

    if not any(is_cue(v) or timed_list(v) for v in (props or {}).values()):
        return props
    import cues as _cues
    words = []
    if audio:
        wj = os.path.splitext(os.path.join(out_dir, audio))[0] + ".words.json"
        if os.path.exists(wj):
            try:
                words = json.load(open(wj, encoding="utf-8"))
            except (OSError, ValueError):
                words = []
    dur_frames = round(dur_s * fps)
    out = dict(props)
    for k, v in props.items():
        if is_cue(v):
            phrase = str(v["cue"] or "").strip()
            if not phrase or _cues._anchor_pos(narration or "", phrase) < 0:
                raise SystemExit("[render_remotion] shot prop `%s` cues %r, which this beat's narration does not say "
                                 "— name words the voice actually speaks" % (k, phrase))
            if words and _cues._find(words, phrase, 0) >= 0:
                sec = _cues.resolve_cues(words, [phrase])[0]
            else:
                sec = _cues.estimate_cues_from_text([phrase], narration or "", dur_s)[0]
            sec += float(v.get("offset") or 0.0)
            out[k] = round(sec, 4) if seconds else t_at_seconds(sec, dur_frames, fps)
        elif timed_list(v):
            items = [dict(x) if isinstance(x, dict) else x for x in v]
            idx = [i for i, x in enumerate(items) if isinstance(x, dict) and is_cue(x.get("at"))]
            phrases, pos = [], 0
            for i in idx:
                phrase = str(items[i]["at"].get("cue") or "").strip()
                if not phrase or _cues._anchor_pos(narration or "", phrase) < 0:
                    raise SystemExit("[render_remotion] shot prop `%s[%d].at` cues %r, which this beat's narration "
                                     "does not say — name words the voice actually speaks" % (k, i, phrase))
                p = _cues._anchor_pos(narration or "", phrase, pos)
                if p < 0:
                    raise SystemExit("[render_remotion] shot prop `%s[%d].at` cues %r, but the narration says it only "
                                     "BEFORE the previous item's cue — the items would play out of order. Reorder "
                                     "them, or cue a phrase said later" % (k, i, phrase))
                pos = p + len(phrase)
                phrases.append(phrase)
            if words and all(_cues._find(words, p, 0) >= 0 for p in phrases):
                secs = _cues.resolve_cues(words, phrases)
            else:
                secs = _cues.estimate_cues_from_text(phrases, narration or "", dur_s)
            for i, sec in zip(idx, secs):
                sec += float(items[i]["at"].get("offset") or 0.0)
                items[i]["at"] = round(sec, 4) if seconds else t_at_seconds(sec, dur_frames, fps)
            out[k] = items
    return out


def _readable_audio(out_dir, rel):
    """`rel`, or a WAV beside it when it is an AIFF. Remotion's bundled ffprobe refuses the AIFF macOS `say`
    writes ("Invalid data found when processing input"), so a board voiced before tts.py wrote WAV — or an
    AIFF dropped in by hand — would fail mid-render. The rewrap is lossless PCM at the same rate, so the
    board's measured duration still holds; it is redone whenever the AIFF is newer."""
    if not str(rel).lower().endswith((".aiff", ".aif")):
        return rel
    src = os.path.join(out_dir, rel)
    wav_rel = os.path.splitext(str(rel))[0] + ".wav"
    dest = os.path.join(out_dir, wav_rel)
    if os.path.isfile(src) and (not os.path.isfile(dest) or os.path.getmtime(dest) < os.path.getmtime(src)):
        import tts as _tts
        _tts.aiff_to_wav(src, dest)
    return wav_rel


def film_shot_props(slide, out_dir, fps=30):
    """A beat's `shot_props` as the RENDERER passes them — cue props resolved to `t`. Every gate that renders a
    film's beat on its own (text_safe_qa, cjk_type_qa, shot_proof) goes through this, so a board that writes
    `{"cue": ...}` is checked with the value the film actually plays, not with an object no register reads.
    Before tts has run there is no duration; the cue is then placed by its position in the narration text."""
    props = dict(slide.get("shot_props") or {})
    narration = slide.get("narration") or slide.get("script") or ""
    dur = slide.get("duration")
    # the SAME preparation build_scenes makes (register_props): a gate rendering the beat alone without it measured a
    # LivingMap's demo map, failed a PhotoToDiagram and measured a PhotoPlate crop the film never draws
    props = register_props(slide.get("shot"), props, out_dir,
                           _board_map_props(slide, out_dir) if slide.get("shot") == "LivingMap" else None)
    props = with_track(props, slide)
    if dur:
        props = resolve_cue_props(props, out_dir, slide.get("audio"), narration, float(dur), fps)
        if slide.get("shot") in ("DeviceDemo", "DeviceHero"):
            props = _prepared_device_props(slide, props, out_dir, float(dur), fps)
        return props
    return resolve_cue_props(props, out_dir, None, narration, 1.0, fps) if any(
        isinstance(v, dict) and "cue" in v for v in props.values()) else props


def _board_map_props(slide, out_dir):
    """This LivingMap beat's props as build_scenes expands them, read against the film's own board (storyboard.json);
    None when the board cannot be read or does not hold this beat."""
    try:
        with open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8") as fh:
            board = json.load(fh)
    except (OSError, ValueError):
        return None
    slides = board.get("slides") or []
    pos = next((i for i, x in enumerate(slides) if x is slide or (slide.get("index") is not None
                                                                   and x.get("index") == slide.get("index"))), None)
    if pos is None:
        return None
    return expand_living_maps(slides, board.get("meta") or {})[pos]


def _prepared_device_props(slide, props, out_dir, dur, fps):
    """A device beat as the film draws it. build_scenes prepares its script (device_script.prepare) against the
    film's frame and language; a gate that renders the beat on its own must do the same, or the register refuses
    the unprepared script and the gate reports a render failure on a correct film — which is what text_safe_qa,
    shot_proof and cjk_type_qa did to every device beat. The frame and the language come from the board."""
    import device_script as _ds
    from _caption_band import aspect_table
    board = {}
    try:
        with open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8") as fh:
            board = json.load(fh)
    except (OSError, ValueError):
        pass
    meta = board.get("meta") or {}
    W, H = aspect_table().get(str(meta.get("aspect") or "16:9"), (1920, 1080))
    try:
        out, _warns = _ds.prepare(props, shot=slide.get("shot"), out_dir=out_dir, dur_frames=int(round(dur * fps)),
                                  fps=fps, W=W, H=H, lang=_ds.film_language(meta, board.get("slides") or [slide]))
    except _ds.DeviceScriptError as e:          # a board validate refuses: named, not a traceback
        raise SystemExit("device beat (%s, %r): %s — validate.py names every problem before a render"
                         % (slide.get("shot"), (slide.get("narration") or "")[:40], "; ".join(e.problems)))
    return out


def _caption_word_spans(out_dir, audio, caption):
    """[{t, a, b}] for this beat's caption, or [] when there is no word timing to be had.

    Empty is a real answer and the caller must treat it as one: `say`/MiniMax emit no boundaries at all, and
    a beat whose caption was rewritten after the synth will not match. Both cases fall back to the estimated
    chunk timing that was there before, which is worse and still works — the failure this must never make is
    inventing times, because a caption confidently lit on the wrong word is harder to spot than one that
    simply drifts.
    """
    if not caption:
        return []
    wp = os.path.splitext(os.path.join(out_dir, str(audio)))[0] + ".words.json"
    try:
        with open(wp, encoding="utf-8") as fh:
            words = json.load(fh)
    except (OSError, ValueError):
        return []
    try:
        import cues as _cues
        return _cues.word_spans(words, caption)
    except Exception:
        return []


def _split_caption(text):
    """Mirror of Film.tsx splitCaption — same chunks, so the sidecar .srt matches the burn.

    Includes the decimal guard: a `.` between two digits is not a sentence end, or a line quoting
    "19.3 到 28.9%" breaks into "19." / "3 到 28." / "9%。"."""
    guarded = re.sub(r"(\d)\.(\d)", lambda m: m.group(1) + _DEC + m.group(2), text or "")
    raw = re.findall(r"[^.!?。！？—]+[.!?。！？]?(?:\s*—)?", guarded)
    chunks = [c.strip().replace(_DEC, ".") for c in raw]
    chunks = [c for c in chunks if c]
    cjk = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
    merged = []
    for c in chunks:                                   # merge short LATIN neighbours, as the JS does
        if merged and not cjk.search(c) and not cjk.search(merged[-1]) and (len(merged[-1]) < 22 or len(c) < 22):
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged

_CJK_CUE = re.compile(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]")


def _srt_ts(t):
    ms = int(round(max(0.0, t) * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


_KEYFRAME_SOURCES = ".segment_sources.json"


def _remotion_deliverables(out_dir, scenes, out_mp4, fps, segments=None):
    """Delivery parity with the html tier so the WORKFLOW's critic + A/V gate have material: write out.srt
    (from the overlap-compressed scene timeline) and _keyframes/scene_NN.png (one mid-scene frame per beat,
    extracted from out.mp4) for the shot-critic filmstrip + `check_av`.

    `segments` ([(a, b, key)] from a per-beat render) lets an unchanged keyframe be KEPT: a frame of the
    joined film is a bit-exact copy of its segment's frame, and a segment file is named by its content key,
    so a keyframe taken at frame f of the segment with key K is the same picture as long as both match.
    Measured on the 37-beat film, re-extracting all 74 keyframes was 42 of the 83 seconds a two-beat edit
    took. The lookup is BY FRAME, not by beat: a beat shorter than ~37 frames can settle inside the next
    beat's seam, which is the next segment. A whole render (segments=None) re-extracts everything and drops
    the record, because its frames are not the segments' bits."""
    tr = _REMOTION2_TR
    import stage_runs as _sr
    joined = _sr.joined_flags(scenes)                  # inside a stage run there is no seam (Film.tsx sceneStarts)
    starts, acc = [], 0                                # output-timeline start of each scene (each CUT removes tr frames)
    for i, sc in enumerate(scenes):
        starts.append(acc / fps)
        acc += sc["durF"] - (tr if i + 1 < len(scenes) and not joined[i + 1] else 0)
    # SRT must MIRROR THE BURN, not summarise it. It used to emit one scene-long cue carrying the whole
    # narration while Film.tsx burns one chunk PER SENTENCE, each timed by its share of the characters — so
    # the sidecar shipped cues up to 3x too long and mistimed against what a viewer actually saw. Reproduce
    # Film.tsx's splitCaption (including its decimal guard) and its length-weighted chunk timing here.
    half = tr // 2
    lines, n = [], 0
    # A CJK CUE IS BROKEN AT WORD BOUNDARIES (scripts/caption_breaks_qa.srt_lines: the film's own captionBreak.ts in
    # node, 16 glyphs a line, balanced, kinsoku) — a player wraps Chinese between any two characters, which is how the
    # burned caption came to read 「交回成 / 片」. Without node the cues stay one line each, as before.
    _all = [c for sc in scenes if sc.get("caption") for c in _split_caption(sc["caption"])]
    try:
        import caption_breaks_qa as _cbq
        _broken = _cbq.srt_lines(_all) if any(_CJK_CUE.search(c) for c in _all) else None
    except Exception as e:                                  # noqa: BLE001 — a sidecar is never worth a failed render
        print("[render_remotion] out.srt: CJK cues left unbroken (%s)" % e)
        _broken = None
    _lines_of = dict(zip(_all, _broken)) if _broken else {}
    for i, sc in enumerate(scenes):
        cap = sc.get("caption")
        if not cap:
            continue
        chunks = _split_caption(cap)
        if not chunks:
            continue
        a = (starts[i] * fps) + ((0 if joined[i] else half) if i > 0 else 14)   # window in FRAMES on the output timeline
        b = (starts[i] * fps) + sc["durF"] - (((1 if joined[i + 1] else tr - half)) if i + 1 < len(scenes) else 16)
        if sc.get("captionUntil") is not None:          # a sound demo follows the voice: the caption gives way to it
            b = min(b, starts[i] * fps + float(sc["captionUntil"]) * fps)
        span = max(1.0, b - a)
        lens = [max(1, len(c)) for c in chunks]
        tot = float(sum(lens))
        cum = 0.0
        for c, L in zip(chunks, lens):
            f0 = a + span * (cum / tot)
            cum += L
            f1 = a + span * (cum / tot)
            n += 1
            text = "\n".join(_lines_of.get(c) or [c])
            lines.append("%d\n%s --> %s\n%s\n" % (n, _srt_ts(f0 / fps), _srt_ts(max(f0 / fps + 0.3, f1 / fps - 0.02)), text))
    with open(os.path.join(out_dir, "out.srt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    if shutil.which("ffmpeg") and os.path.exists(out_mp4):   # per-scene keyframes for the shot-critic
        kdir = os.path.join(out_dir, "_keyframes"); os.makedirs(kdir, exist_ok=True)
        src_path = os.path.join(kdir, _KEYFRAME_SOURCES)
        try:
            was = json.load(open(src_path, encoding="utf-8")) if segments else {}
        except (OSError, ValueError):
            was = {}
        # A KEPT KEYFRAME IS ONLY AS GOOD AS THE FILM IT WAS TAKEN FROM. A keyframe used to be kept on (frame, segment
        # key) alone — and a benchmark film's second render joined a segment on the wrong time base into a 352 s video
        # stream; the keyframes taken from it were then kept across the repaired render, and the keyframe gate, the
        # contact sheet and the review all judged 8 frames that were not the film. The record now carries the joined
        # film's own timing; a film that differs re-extracts every keyframe.
        import remotion_segments as _rs
        try:
            vf, vd, _tb = _rs.video_timing(out_mp4)
            film_sig = [vf, round(vd, 3)]
        except Exception:                                  # noqa: BLE001 — unreadable: keep nothing
            film_sig = None
        if not film_sig or was.get("__film__") != film_sig:
            was = {}
        now, kept = ({"__film__": film_sig} if film_sig else {}), 0

        def key_at(f):
            return next((k for a, b, k in segments if a <= f <= b), None) if segments else None

        def grab(at_s, dest):
            nonlocal kept
            f = int(round(at_s * fps))
            name = os.path.relpath(dest, kdir)
            k = key_at(f)
            if k and was.get(name) == [f, k] and os.path.exists(dest):
                kept += 1
            else:
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % at_s, "-i", out_mp4,
                                "-frames:v", "1", dest], check=False)
            if k:
                now[name] = [f, k]
        # THE SETTLED FRAME, not the midpoint. A keyframe used to be taken at t=0.5 of the beat — but a
        # register reveals its content over roughly the first half of its animated span, so half the
        # keyframes showed a shot that had not finished drawing. Everything downstream reads these: the
        # shot-critic, keyframe_qa, and a human eyeballing the contact sheet. Measured consequence: a
        # delivered film's thesis beat was reviewed as "sliced mid-glyph" when the settled frame is clean,
        # and several real collisions went unseen because the colliding element had not appeared yet.
        #
        # `useT()` holds the shot still for `pad` frames at each edge and animates 0→1 between them, and
        # the library already names 0.86 as "reveal complete, exit not begun" (motion.ts REDUCED_MOTION_T).
        # Mirrored here so the keyframe IS the frame the runtime calls settled.
        for i, sc in enumerate(scenes):
            durF = max(1, int(sc["durF"]))
            pad = min(SEAM_FRAMES, (durF - 1) // 3)
            at = starts[i] + settled_frame(durF) / fps
            grab(at, os.path.join(kdir, "scene_%02d.png" % (i + 1)))
            # ALSO a MOTION frame, in _keyframes/motion/. The settled frame is the right one for every
            # frame-craft question — is anything colliding, off-frame, illegible — but it is the wrong one
            # for every MOTION question, because by definition nothing is moving in it. Reviewing motion
            # from settled frames is how a delivered film's reveal timing went unexamined for six rounds.
            # Cheap (one more ffmpeg seek per beat) and kept in a subdirectory so nothing that globs
            # scene_*.png picks it up by accident.
            mdir = os.path.join(kdir, "motion"); os.makedirs(mdir, exist_ok=True)
            mid = starts[i] + frame_at_t(durF, 0.42) / fps
            grab(mid, os.path.join(mdir, "scene_%02d.png" % (i + 1)))
        if segments:
            with open(src_path, "w", encoding="utf-8") as fh:
                json.dump(now, fh)
        elif os.path.exists(src_path):
            os.remove(src_path)
        print("[render_remotion] wrote out.srt + %d keyframes (_keyframes/) for the shot-critic + A/V gate%s."
              % (len(scenes), " — %d unchanged kept from their segments" % kept if kept else ""))


def build_scenes(slides, out_dir, valid, fps=30, frame=(1920, 1080), lang="zh", meta=None):
    """The storyboard -> Film SceneSpec[] translation, on its own so it can be TESTED without a render.

    It was inline in _render_remotion, which meant the only way to check that a storyboard field reaches
    the Film was to render a film. That is how `ground`/`key` came to be forwarded by nothing: the runtime
    could re-ground every register, and a delivered film could still only ever be one near-black, because
    the translation nobody could test had never learned the fields.
    """
    scenes = []
    # THE BOARD, ONCE PER FILM. A return's travel is a property of where two beats sit relative to each
    # other, so it cannot be derived inside a per-slide function; `film_board` owns the geometry and every
    # caller — the validator, this emitter, a human reading the plan — asks the same module for it.
    try:
        import film_board as _fb
        _travels = _fb.travels(slides)
    except Exception:                          # noqa: BLE001 — a board with no returns must still render
        _travels = {}
    # ONE STRUCTURE ACROSS BEATS (LivingMap): each beat's map props are the whole map and what is on screen at its two ends
    _maps = expand_living_maps(slides, meta)
    for i, s in enumerate(slides):
        idx, shot = s.get("index"), s.get("shot")
        if not shot:
            raise RuntimeError("scene #%s has no `shot` (a remotion register id) — run the shot-director "
                               "step; valid ids are in remotion/LIBRARY.md." % idx)
        if valid and shot not in valid:
            raise RuntimeError("scene #%s names unknown shot %r — see remotion/LIBRARY.md." % (idx, shot))
        dur, audio = s.get("duration"), s.get("audio")
        if not dur or not audio:
            raise RuntimeError("scene #%s has no audio/duration — run tts.py before rendering." % idx)
        audio = _readable_audio(out_dir, audio)
        props = s.get("shot_props") or {}
        if not isinstance(props, dict):
            raise RuntimeError("scene #%s `shot_props` must be an object." % idx)
        props = register_props(shot, props, out_dir, _maps[i])
        props = with_track(props, s)
        # THE EAR'S TEXT AND THE EYE'S TEXT ARE NOT THE SAME TEXT. `narration` is written to be SPOKEN, so a
        # film spells an initialism out — "没有用 T T S", "S S H", "A G P L 三点零" — to stop edge-tts reading
        # it as a word. That is correct for the voice and wrong on the frame, and it shipped: an independent
        # reviewer found three burned captions carrying spelled-out forms, and on the closing beat the SAME
        # fact twice in one frame — the register's own note reading `AGPL-3.0` above a caption reading
        # `A G P L 三点零`. A slide may now carry an explicit `caption` for the eye; without one, a run of
        # spaced single capitals is rejoined, which is the safe half of the transform and needs no author.
        caption = (s.get("caption") or _caption_for_eye(s.get("narration") or s.get("script") or "")).strip()
        if _stage_run_id(s):
            import stage_runs as _sr
            props = _sr.resolve_steps(props, lambda pr: resolve_cue_props(
                pr, out_dir, audio, s.get("narration") or s.get("script") or "", dur, fps, seconds=True), dur, idx)
        props = resolve_cue_props(props, out_dir, audio, s.get("narration") or s.get("script") or "", dur, fps)
        if shot in ("DeviceDemo", "DeviceHero"):
            import device_script as _ds
            try:
                props, _warns = _ds.prepare(props, shot=shot, out_dir=out_dir, dur_frames=int(round(dur * fps)),
                                            fps=fps, W=frame[0], H=frame[1], lang=lang)
            except _ds.DeviceScriptError as e:
                raise RuntimeError("scene #%s (%s): %s" % (idx, shot, "; ".join(e.problems)))
            for w in _warns:
                print("[render_remotion] scene #%s: %s" % (idx, w))
        scene = {"shot": shot, "props": props, "durF": int(round(dur * fps)),
                 "mp3": str(audio).replace(os.sep, "/"), "caption": caption}
        # THE VOICE'S OWN WORD TIMES, WHICH THIS TIER HAS NEVER SEEN. `tts.py` has written
        # `audio/NN.words.json` since edge-tts was adopted, and only the html renderer ever read it: the
        # remotion caption advances its chunks by CHARACTER PROPORTION of the beat, which is a guess that a
        # short clause and a long one are spoken at the same rate. They are not, and the caption drifts off
        # the voice inside a single beat. Located as character ranges (cues.word_spans) so the timing
        # survives whatever the renderer chunks the caption into.
        spans = _caption_word_spans(out_dir, audio, caption)
        if spans:
            scene["capWords"] = spans
        # A SOUND DEMO (slide.audio_demo) plays after the voice: the caption gives way to it at the demo's start, or
        # the beat's last line ("Listen.") sits on screen through the whole sound
        demo = s.get("audio_demo")
        if isinstance(demo, dict) and isinstance(demo.get("at_s"), (int, float)):
            scene["captionUntil"] = float(demo["at_s"])
        # a MARKED seam → Film's kinetic transition; else the safe fade. The beat before is passed for its match_cut.
        tin = _transition_in(s, _travels.get(i), slides[i - 1] if i > 0 else None)
        if tin:
            scene["transitionIn"] = tin
        elif living_map_continues(slides, i):
            # the map carries on: this beat's first frame IS the last one's, so the cut between them is invisible —
            # a dissolve would cross-fade a picture with itself while the camera starts to move
            scene["transitionIn"] = {"type": "cut"}
        # THE BEAT'S TIME GRAMMAR (runtime/timeGrammar): hit-stops, a freeze to look, held drawings into ones — named by
        # the words, resolved to seconds here; Film.tsx refuses a hold or a time it cannot mean.
        if s.get("time"):
            scene["time"] = resolve_time(s["time"], out_dir, audio, s.get("narration") or s.get("script") or "", dur, fps,
                                         "#%s (%s)" % (idx, shot))
        cam = _camera(s)          # a MOTIVATED per-beat move (push/pull); absent = hold
        if cam:
            scene["camera"] = cam
        # A HELD OBJECT'S IDLE CLOCK is on unless the beat says `"object_idle": false` (runtime/objectSlot). A value
        # that is not a boolean is refused: `"false"` is truthy, and would leave on what its author turned off.
        if "object_idle" in s:
            if not isinstance(s["object_idle"], bool):
                raise RuntimeError("scene #%s (%s): object_idle must be true or false, got %r"
                                   % (idx, shot, s["object_idle"]))
            if s["object_idle"] is False:
                scene["objectIdle"] = False
        chrome = s.get("chrome")   # DNA terminal chrome (command-path + status) framing this beat; remotion-only
        if isinstance(chrome, dict):
            scene["chrome"] = chrome
        # THE BEAT'S GROUND. Without these two lines the whole per-beat light system is unreachable from a
        # storyboard: runtime/light.tsx can re-ground every register, Film.tsx provides the DNA inside each
        # Sequence, and a delivered film could still only ever be one near-black. A capability the authoring
        # path cannot name is indistinguishable from a capability that was never built — the same shape as an
        # opt-in gate that never fires. `ground` names WHICH ground (an index into the film's grounds, a named
        # preset, a #hex, an inline spec, or a {from,to} ramp); `key` names the EXPOSURE when the beat does
        # not name a specific one. `bgLum` stays what it always was, a DESCRIPTION for the caption pick.
        for _f in ("ground", "key"):
            if s.get(_f) is not None:
                scene[_f] = s[_f]
        # THE PLACE the beat happens in (runtime/world.tsx, places.json), named from its subject. A place stands on its
        # own ground (space is dark), so it declares that ground unless the beat names one itself.
        if s.get("world"):
            scene["world"] = s["world"]
            pg = place_ground(s["world"])
            if pg and s.get("ground") is None:
                scene["ground"] = pg
        # THE BEAT'S OPTIC (runtime/optics.tsx): `slide.optic`, or `shot_props.optic` lifted out of the props (a register
        # never reads it as a prop). validate.py refuses a board where the two disagree; Film refuses an unknown one.
        _optic = s.get("optic")
        if isinstance(scene.get("props"), dict) and "optic" in scene["props"]:
            _po = scene["props"].get("optic")
            scene["props"] = {k: v for k, v in scene["props"].items() if k != "optic"}
            if _optic is not None and _optic != _po:
                raise RuntimeError("scene #%s (%s): optic %r and shot_props.optic %r disagree — one beat, one optic"
                                   % (idx, shot, _optic, _po))
            _optic = _po if _optic is None else _optic
        if _optic is not None:
            scene["optic"] = _optic
        # A CONTINUOUS STAGE RUN (scripts/stage_runs.py): consecutive beats naming one run render as one scene
        import stage_runs as _sr
        if _sr.run_id(s):
            scene["stage"] = {"run": _sr.run_id(s)}
            scene["props"] = _sr.stamp_faces(scene.get("props"), out_dir)
        scenes.append(scene)
    import stage_runs as _sr
    probs = _sr.check(slides)
    if probs:
        raise RuntimeError("the board's stage runs cannot render: " + "; ".join(probs))
    _sr.mark_backdrops(scenes)
    return scenes


def cut_carry_on(meta):
    """Whether a film's hard cuts carry the motion through (runtime/cutCarry): `meta.cut_carry` when the board says, else
    on for a film that cuts hard by tempo (seam_plan.film_tempo kinetic or scored) and off for a calm one, whose cuts
    are rare and whose dissolves already move."""
    m = meta if isinstance(meta, dict) else {}
    if isinstance(m.get("cut_carry"), bool):
        return m["cut_carry"]
    import seam_plan as _sp
    return _sp.film_tempo(m)[0] in ("kinetic", "scored")


def safe_zone(meta, aspect):
    """The platform-safe profile a film renders with: "social" for a full-screen vertical (9:16) film unless
    `meta.safe_zone` is "none", else None. A landscape, square or 4:5 film has no platform UI over it where the
    profile says (runtime/safeZone.ts SAFE_MIN_TALL)."""
    want = (meta or {}).get("safe_zone", "social")
    if want in (None, "", "none", False):
        return None
    if want != "social":
        raise SystemExit("[render_remotion] meta.safe_zone must be \"social\" or \"none\", got %r" % (want,))
    from _caption_band import aspect_table
    import text_safe_qa as _tq
    w, h = aspect_table().get(str(aspect), (1920, 1080))
    return "social" if _tq.safe_applies(w, h) else None


def film_props(out_dir, data, sample=None, reduced_motion=False, vertical=False):
    """(props, slides): the Film's input props for this board, and the slides they were built from.

    The render and `remotion_segments.py --plan` both ask this one function, so a plan describes the board
    AS IT IS NOW. Reading the last render's props file instead would answer "which beats would a render
    redo?" with "none" right after an edit — the one moment anybody asks.
    """
    import workshop as _ws
    # A FILM'S OWN SHOTS ARE SHOTS. The library's ids are the component files in remotion/src/shots; a film's
    # workshop (scripts/workshop.py) adds its own, which exist only in a render scoped to this film.
    import stage_runs as _sr
    valid = set(_remotion_shot_ids()) | _ws.shot_names(out_dir) | set(_sr.stage_names())
    slides = data.get("slides", [])
    if sample is not None:
        slides = [s for s in slides if s.get("index") == sample]
        if not slides:
            raise RuntimeError("no scene with index %s to sample" % sample)
    fps = 30
    from _caption_band import aspect_table
    _aspect = "9:16" if vertical else str((data.get("meta") or {}).get("aspect") or "16:9")
    _frame = aspect_table().get(_aspect, (1920, 1080))
    import device_script as _dsl
    scenes = build_scenes(slides, out_dir, valid, fps, frame=_frame, lang=_dsl.film_language(data.get("meta"), slides),
                          meta=data.get("meta"))
    meta = data.get("meta") or {}
    reduced = bool(reduced_motion or meta.get("reduced_motion"))
    # ASPECT: --vertical or meta.aspect:"9:16" renders the Film Composition at 1080x1920 (Root.tsx calculateMetadata
    # reads this `aspect` prop). Any of 16:9 / 9:16 / 1:1 / 4:5 / 4:3; unknown falls back to 16:9.
    aspect = _aspect                    # computed once, above, for the device beats' frame size as well
    props = {"scenes": scenes, "camera": _camera_amp(meta),
             # the camera BED (Film-side default Ken Burns on unauthored beats, themed films only) is ON
             # unless the board switches it off — `meta.camera_bed: false` is the film-wide opt-out
             # OPT-IN, not opt-out. The bed was introduced to lift film_energy's motion p75 from 0.0035 to
             # 0.0042, and it did — by putting a slow lateral pan on EVERY beat that had no authored camera
             # (21 of 25 on the film that exposed this). Watched rather than measured, that reads as the type
             # sliding sideways for the whole film. The viewer who said so was right and the number was not
             # wrong, it was answering a different question: "does the film move" is not "does the film look
             # like it is drifting". A default that has to be switched off after you notice it is a default
             # set backwards, so it is now `meta.camera_bed: true` for a film that genuinely wants the floor.
             "cameraBed": meta.get("camera_bed") is True,
             # THE CUT CARRY (runtime/cutCarry): a kinetic or scored film's hard cuts carry one move through the cut
             # frame instead of joining two still ones; `meta.cut_carry` true/false says so outright
             "cutCarry": cut_carry_on(meta),
             # Han/Latin spacing on the beats (Film.tsx `autospace`); `meta.cjk_autospace: false` leaves it out
             "autospace": meta.get("cjk_autospace") is not False,
             "reducedMotion": reduced, "aspect": aspect,
             "captions": bool(meta.get("captions", True)),
             # THE DELIVERY DITHER (runtime/dither.tsx): the dark grounds measured CAMBI 12-22 — rings a viewer sees
             # — without it, 0.0 with it; `meta.dither: false` turns it off
             "dither": meta.get("dither") is not False}
    # THE PLATFORM'S OWN UI: a portrait film is posted where a description, an author line and a button column sit
    # over its bottom and right edges — its caption and labels are kept clear of them (runtime/safeZone.ts). The
    # default for a portrait film; `meta.safe_zone: "none"` for a portrait film shown somewhere without that UI.
    zone = safe_zone(meta, aspect)
    if zone:
        props["safe"] = zone
        # the margin is the beat's GROUND (Film.tsx SafeEcho): its measured ground token, and over it the register's own
        # root ground drawn a second time with everything on it hidden. That second rendering of every register is a
        # cost; `meta.safe_echo: false` keeps the token alone (never content either way)
        if meta.get("safe_echo") is False:
            props["safeEcho"] = False
    if isinstance(meta.get("brand"), dict) and meta["brand"].get("logo"):
        props["brand"] = meta["brand"]     # served from out_dir via --public-dir; drawn as a persistent corner bug
    theme = meta.get("theme")                 # the per-topic atmosphere WORLD (motif + palette) behind every shot
    if isinstance(theme, dict):
        props["theme"] = theme
    # DESIGN DNA — the GLOBAL visual system every shot inherits (runtime/dna.ts). Prefer the EXPLICIT authored
    # artifact meta.design_dna (a token object); else pass the template id so Film expands a preset via
    # dnaFromTemplate (a terminal-technical deck with no authored DNA still gets TERMINAL_DNA). Absent both ->
    # Film provides null and every shot renders its original hardcoded look (backward-compatible).
    design_dna = meta.get("design_dna")
    if isinstance(design_dna, dict):
        props["dna"] = design_dna
    elif isinstance(design_dna, str) and design_dna.strip():
        # A STRING design_dna is a preset NAME. It used to be dropped here — neither dna nor template
        # reached the renderer, so a board that named a preset rendered completely UNTHEMED while
        # validate.py cheerfully blessed the name. Film's coerceDna resolves a name and throws on one it
        # does not know, so passing it through is both correct and loud.
        props["dna"] = design_dna.strip()
    elif meta.get("shot_template"):
        props["template"] = str(meta["shot_template"])
    # THE CJK DISPLAY VOICE (runtime/cjkVoice.ts): the titles' face on a Chinese film; 'noto' keeps the stack as it is
    if meta.get("cjk_display") and meta.get("cjk_display") != "noto":
        props["cjkDisplay"] = meta["cjk_display"]
    # THE DRAWING STYLE (runtime/style.tsx): passed as written — the renderer fills defaults from the same axis table
    # (runtime/styleAxes.json) that scripts/style_spec.py validated it against. Absent: nothing mounts.
    if isinstance(meta.get("style"), dict):
        props["style"] = meta["style"]
        tex = style_texture_props(meta, out_dir)
        if tex:
            props["styleTexture"] = tex
    # EACH BEAT'S CLOCK, ON ITS VOICE (scripts/sync_qa.py, Film.tsx `BeatClock`): the warp derived for the beat
    # AS IT IS NOW, or the board's own `sync.anchors`; nothing for a beat that has neither, so every reader of
    # these props — the render, the segment plan, the gates — sees the film that will actually play.
    import sync_qa as _sq
    # ...and each ITEM on its word where the warp cannot reach (it cannot reorder): per-element cues for a register
    # that reads them (runtime/cue.ts). Attached first, because a beat's warp is derived for the beat AS CUED.
    _sq.attach_cues(out_dir, data, props, slides)
    _sq.attach_warps(out_dir, data, props, slides)
    attach_phrases(props, slides, meta, fps)
    return props, slides


_ENERGY = None


def places():
    """{place: {ground, for}} — remotion/src/runtime/places.json, the table runtime/world.tsx draws from."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "runtime", "places.json")
    with open(p, encoding="utf-8") as fh:
        return {k: v for k, v in json.load(fh).items() if not k.startswith("_")}


def place_ground(place):
    return (places().get(place) or {}).get("ground")
# An authored move is stepped only on a beat this long. Measured: authored push/pull beats of 5.5-8.5 s never held past
# 2.5 s (the creep is visible there); beats of 15.2 and 18.8 s held 8.2 and 9.8 s. Stepped, a short beat's move only got
# faster, and gps's ListeningPhone type trembled more for it (0.16 -> 0.28 px).
LONG_BEAT = 10.0


def _register_p75(shot):
    """The register's measured motion p75 (remotion/register_energy.json), or None when it was never measured."""
    global _ENERGY
    if _ENERGY is None:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion",
                                   "register_energy.json"), encoding="utf-8") as fh:
                _ENERGY = json.load(fh).get("registers") or {}
        except (OSError, ValueError):
            _ENERGY = {}
    row = _ENERGY.get(shot) or {}
    return row.get("motion_p75")


def attach_phrases(props, slides, meta, fps):
    """The beat's EVENTS on the voice's clauses. Measured before this: our films' longest still hold was 5.0 s (median
    of 22) against 2.5 s on 28 published launch films, and the largest element held 48% of the layout against 63%.
      * a LISTED beat (scripts/focus_plan.py, runtime/focusLead.tsx): the item the voice names leads, its peers recede.
      * an AUTHORED push or pull (scripts/phrase_steps.py, Film.tsx PhraseCamera): the move arrives clause by clause.
    A stage run, reduced motion and `phrase_camera: false` (film or beat) get neither; an authored hold, pan or hand-off
    and a register that keeps moving on its own get no steps — and a beat with neither draws exactly what it drew."""
    import focus_plan as _fp
    import phrase_steps as _ps
    film_on = meta.get("phrase_camera") is not False and not props.get("reducedMotion")
    for sc, sl in zip(props["scenes"], slides):
        sc.pop("phrase", None)
        sc.pop("focus", None)
        sc.pop("focusItems", None)
        cam = sc.get("camera") or {}
        fixed = bool(cam) and (cam.get("move") not in ("push", "pull") or cam.get("pan") or cam.get("handoff"))
        if not film_on or sc.get("stage") or sl.get("phrase_camera") is False:
            continue
        # A LISTED BEAT'S EVENT IS ITS LEAD CHANGING HANDS (scripts/focus_plan.py, runtime/focusLead.tsx): the item the
        # voice names leads and its peers recede. Nothing moves, so no type is re-positioned — camera steps on
        # TechnicalPlate made its callout digits tremble 0.19-0.22 px (jitter_qa ERROR), as a scale and as a travel.
        focus = _fp.focus_plan(sc.get("props") or {}, sc.get("capWords") or [], sc.get("caption") or "",
                               sc["durF"] / float(fps), shot=sc.get("shot"))
        if focus:
            sc["focus"] = focus
            sc["focusItems"] = _fp.focus_items(sc.get("props") or {}, focus, shot=sc.get("shot"))
        # Camera steps only for an AUTHORED push or pull (Film.tsx PhraseCamera says why the rest were withdrawn), and
        # only on a beat long enough that its creep is invisible (LONG_BEAT).
        if not cam or fixed or sc["durF"] / float(fps) < LONG_BEAT:
            continue
        steps = _ps.phrase_steps(sc.get("capWords") or [], sc.get("caption") or "", sc["durF"] / float(fps),
                                 register_p75=_register_p75(sc["shot"]), enabled=sl.get("phrase_camera") is not False)
        if steps:
            sc["phrase"] = steps


def style_texture_props(meta, out_dir):
    """{"light", "dark"} — the GENERATED medium's tiles (scripts/imagegen.texture), served from the film's public dir;
    None when the spec does not ask for one or it was never made (the engine then draws the procedural medium)."""
    spec = meta.get("style") if isinstance(meta.get("style"), dict) else None
    surf = (spec or {}).get("surface") or {}
    if surf.get("source") != "generated" or (surf.get("kind") or "none") == "none":
        return None
    rel = {k: "style/surface-%s-%s.png" % (surf["kind"], k) for k in ("light", "dark")}
    return rel if all(os.path.isfile(os.path.join(out_dir, p)) for p in rel.values()) else None


def style_refusal(data, sample=None):
    """Why the FULL render of a styled film must not start, or None. The user approves a style on its sample before
    the film is rendered (scripts/style_sample.py); a spec changed after that approval is stale. A `--sample` render
    is always allowed — it is how a sample is made."""
    meta = data.get("meta") or {}
    spec = meta.get("style")
    if sample is not None or not isinstance(spec, dict):
        return None
    import style_spec as _ss
    so = meta.get("style_signoff")
    if not (isinstance(so, dict) and so.get("user_ok") is True):
        return ("this film has a drawing style and no sign-off: build the sample (scripts/style_sample.py <out_dir>), "
                "show it to the user, and record their yes (--signoff) before the full render")
    if so.get("spec_sha256") != _ss.spec_sha256(spec):
        return ("the style sign-off is stale: meta.style changed after the user approved its sample — build a new "
                "sample and show it")
    return None


def _render_remotion(out_dir, data, sample=None, log="error", reduced_motion=False, vertical=False, whole=False):
    """Render via the bespoke-shot LIBRARY. Fails loud on a missing/unknown shot or missing audio."""
    why = style_refusal(data, sample)
    if why:
        raise RuntimeError(why)
    if not shutil.which("npx"):
        raise RuntimeError("Node/npx not found — the Remotion tier needs Node.js.")
    if not os.path.isdir(os.path.join(_REMOTION2_DIR, "node_modules")):
        raise RuntimeError("remotion deps not installed — run `cd %s && npm install` once." % _REMOTION2_DIR)
    # TYPESET MATHS first: every `tex` the storyboard names becomes glyph outlines in <out_dir>/_math, which every
    # render below (the sync census included) reads through the film's public dir. A TeX error stops here, by name.
    import mathtex as _mt
    _mrep = _mt.ensure(out_dir, data)
    if _mrep.get("written"):
        print("[render_remotion] typeset %d equation(s) into %s/" % (len(_mrep["written"]), _mt.MATH_DIR))
    props, slides = film_props(out_dir, data, sample=sample, reduced_motion=reduced_motion, vertical=vertical)
    # A beat whose warp is missing or stale is measured now — one census of the film on its registers' own
    # clocks — so a re-render after any edit lands each entrance on its word without a separate step.
    # REMOTION_SYNC=0 renders on the registers' own clocks (the warps already on disk are still used).
    if os.environ.get("REMOTION_SYNC", "1") != "0":
        import sync_qa as _sq
        _sq.derive_warps(out_dir, data, props, slides, log=print)
    scenes, meta, fps = props["scenes"], data.get("meta") or {}, 30
    props_path = os.path.join(out_dir, ".remotion-props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, allow_nan=False, ensure_ascii=False)
    out_name = "sample.mp4" if sample is not None else "out.mp4"
    out_mp4 = os.path.abspath(os.path.join(out_dir, out_name))
    import remotion_segments as _rs
    gl = _rs.default_gl()
    run_flags = ["--gl=" + gl, "--log=" + log,
                 "--timeout=" + str(int(os.environ.get("REMOTION_TIMEOUT_MS", "120000") or "120000"))]
    # CONCURRENCY. Remotion opens one browser tab per worker and EACH loads the film's fonts; on a loaded
    # machine a starved tab can blow past its delayRender and kill a long render outright. REMOTION_CONCURRENCY
    # lets a caller trade wall-clock for that safety without editing this file.
    _conc = os.environ.get("REMOTION_CONCURRENCY")
    if _conc:
        run_flags.append("--concurrency=" + str(int(_conc)))
    print("[render_remotion] %s: %d scene(s) -> %s"
          % ("sample" if sample is not None else "full", len(scenes), out_mp4))
    # ONE BEAT AT A TIME (remotion_segments.py): each beat's share of the timeline is rendered from these same
    # props with --frames and kept under a key of everything its frames depend on, so an edit re-renders the
    # beats it touched. `whole` / `meta.segment_cache: false` / REMOTION_SEGMENTS=0 render the film in one
    # pass, the way it always was. A disagreement between the segment model and the film is never shipped:
    # it is reported, and the film is rendered whole instead.
    segmented = (sample is None and not whole and meta.get("segment_cache", True) is not False
                 and os.environ.get("REMOTION_SEGMENTS", "1") != "0")
    segments_used = None
    # THE RENDER RECORD (remotion_segments.RECORD): which GL backend drew this film. A film is drawn on ONE
    # backend — the per-beat path re-renders the whole film on the fallback when a beat fails on the first, and a
    # whole render is one process — and the record says which, so a later comparison of two renders of "the same"
    # film can tell a real change from a backend change (up to 10/255 on a gradient, measured).
    record = {"out": os.path.basename(out_mp4), "gl": gl, "mode": None}
    if segmented:
        try:
            done = _rs.render_film(out_dir, props, props_path, out_mp4, run_flags, _rs.pixel_flags(gl),
                                   labels=[sl.get("index", i + 1) for i, sl in enumerate(slides)])
            print("[render_remotion] %d beat(s): %d re-rendered, %d reused from %s/"
                  % (done["beats"], len(done["rendered"]), done["beats"] - len(done["rendered"]), _rs.CACHE_DIR))
            segments_used = done["segments"]
            record.update(mode="segments", gl=done.get("gl") or gl, frames=done["frames"],
                          segments=[[a, b, k] for a, b, k in done["segments"]])
            for f in ("gl_fallback_from", "gl_reason"):
                if done.get(f):
                    record[f] = done[f]
        except _rs.ModelMismatch as e:
            print("[render_remotion] the per-beat cache disagreed with the film (%s) — rendering it WHOLE "
                  "instead; nothing from the cache is used." % e)
            segmented = False
    if not segmented:
        import workshop as _ws
        wk = _ws.run_kwargs(out_dir)            # the film's workshop, or no extra environment when it has none
        cmd = ["npx", "remotion", "render", "src/index.ts", "Film", out_mp4,
               "--props=" + os.path.abspath(props_path), "--public-dir=" + os.path.abspath(out_dir)] + run_flags
        record["mode"] = "whole"
        try:
            subprocess.run(cmd, cwd=_REMOTION2_DIR, check=True, **wk)
        except subprocess.CalledProcessError as e:
            # NEVER "without --gl": that hands the backend to whatever Chrome picks and records nothing. One process
            # draws every frame, so a re-render on the NAMED fallback is still one backend for the whole film.
            fb = _rs.fallback_gl(gl)
            if fb is None:
                raise
            print("[render_remotion] render failed on --gl=%s — re-rendering the whole film on --gl=%s "
                  "(software ANGLE; slower)." % (gl, fb))
            subprocess.run(_rs.with_gl(cmd, fb), cwd=_REMOTION2_DIR, check=True, **wk)
            record.update(gl=fb, gl_fallback_from=gl, gl_reason="whole render failed on --gl=%s: %s" % (gl, e))
    if sample is None:
        _rs.write_record(out_dir, record)
        if record.get("gl_fallback_from"):
            print("[render_remotion] NOTE: this film was drawn on --gl=%s, not --gl=%s (%s) — recorded in %s"
                  % (record["gl"], record["gl_fallback_from"], record["gl_reason"], _rs.RECORD))
    if sample is None:                                 # delivery parity: srt + critic keyframes (full render only)
        try:
            _remotion_deliverables(out_dir, scenes, out_mp4, fps, segments=segments_used)
        except Exception as e:
            print("[render_remotion] deliverables (srt/keyframes) skipped: %s" % e)
        meta = data.get("meta") or {}
        import stage_runs as _sr
        _events = _sr.sound_events(scenes)          # a stage's clicks, on the words that name them
        _clicks = any(_events) and meta.get("stage_sounds", True) is not False
        # THE PICTURE'S OWN SOUNDS (scripts/shot_sounds.py): each register's declared SOUNDS on the frames its picture
        # makes them, and the board's `slide.sounds` on their words. They ride with the SFX bed (`sound_design`), or
        # alone with `meta.shot_sounds: true`; a board's `sounds: "none"` silences the beat under the whole bed.
        import shot_sounds as _ss
        _shot_on = bool(meta.get("sound_design")) or meta.get("shot_sounds") is True
        _own, _silent = [[] for _ in scenes], [False] * len(scenes)
        if _shot_on:
            for k, sc in enumerate(scenes):
                try:
                    _own[k] = _ss.scene_events(sc, fps, out_dir)
                    _b = _ss.board_events(slides[k] if k < len(slides) else {}, out_dir, fps)
                except (_ss.SoundDeclError, SystemExit) as e:
                    print("[render_remotion] WARNING: beat %d's own sounds cannot be placed (%s) — the beat plays "
                          "without them; validate.py names the same defect" % (k + 1, e))
                    continue
                if _b == "none":
                    _silent[k] = True
                else:
                    _own[k] = _own[k] + _b
        if meta.get("sound_design") or _clicks or any(_own):     # opt-in SFX(+BGM) bed, post-render — or a stage's
            # clicks / the shots' own sounds alone
            try:
                import sfx
                tr = _REMOTION2_TR                      # feed durationInFrames = durF-TR so cue times land on the
                # carry transitionIn per scene so the SFX marks the SAME seams the eye does (fades stay quiet)
                _jn = _sr.joined_flags(scenes)          # no seam inside a stage run
                sfx_scenes = [{"durationInFrames": max(1, sc["durF"] - (0 if k + 1 < len(scenes) and _jn[k + 1]
                                                                         else tr)),
                               "transitionIn": sc.get("transitionIn"),
                               "events": (_events[k] if _clicks else []) + _own[k],
                               "silent": _silent[k]}
                              for k, sc in enumerate(scenes)]   # overlap-compressed timeline
                if sfx_scenes:                          # the closing sentence lands on the last beat's arrival
                    sfx_scenes[-1]["shots"] = [{"startFrame": 0}]
                # THE FILM'S BEAT GRID (beats.json, written by tts.py when the board asks for music): the score is
                # generated on it and the whooshes quantise to it. None for a film without music — the mix below is
                # then exactly the one it always was.
                music = None
                if meta.get("sound_design"):
                    import beatgrid
                    music = beatgrid.music_for_render(out_dir, slides, scenes, meta,
                                                      log=lambda m: print("[render_remotion] " + m))
                sfx.mix(out_dir, out_mp4, sfx_scenes, meta, fps,     # whooshes + riser/impact/sparkle + meta.bgm
                        events_only=not meta.get("sound_design"), music=music)
            except Exception as e:
                print("[render_remotion] sound_design skipped: %s" % e)
        # a portrait film posted to a platform also needs its feed card (scripts/cover.py): best-effort, said aloud
        if (props.get("safe") or "") == "social":
            try:
                import cover as _cover
                print("[render_remotion] cover -> %s" % os.path.basename(_cover.cover(out_dir)))
            except (SystemExit, Exception) as e:          # noqa: BLE001 — a film without a cover still renders
                print("[render_remotion] no cover: %s" % e)
        _not_delivered(out_dir)
    return out_mp4


# THE RENDERER MUST NOT END ON A GREEN LIGHT. This one used to finish with "wrote out.srt + N keyframes
# (…) for the shot-critic", which MENTIONS the critic and names no command — and the step it points at
# lives eleven hundred lines into SKILL.md. Every film this session shipped without a critic pass for
# exactly that reason: a success line was the last thing anyone read.
#
# This repo already filed the rule, in another skill and in the same words: a gate that passes must SAY THE
# NEXT COMMAND, or a weaker agent stops at the first green light. So the render now ends on the remaining
# work, and it also LEAVES THAT WORK IN THE DIRECTORY: `NOT_DELIVERED.md` sits beside out.mp4 carrying the
# exact commands, and `critic_ledger.py --final` deletes it when the review it demands actually passes. A
# checklist that is printed can be scrolled past; a file in the deliverable cannot, and any later step can
# ask "is this film delivered?" by asking whether that file is gone.
_NOT_DELIVERED = "NOT_DELIVERED.md"

_NEXT_STEPS = '''# RENDERED, not DELIVERED

`out.mp4` existing is not the same claim as this film being deliverable. Every machine gate here measures
TYPE — is it cut off (`text_safe_qa`), was it drawn at all (`cjk_type_qa`), does the film move
(`film_energy_qa`). NONE of them can ask whether a picture MEANS what its beat means.

That half is the shot-critic's, and it has to be a reviewer who does not know what you meant to draw: the
maker holds the intent, and the intent is what makes a wrong frame look right.

Run these in order. The last one deletes this file when it passes:

```sh
python3 scripts/critic_ledger.py  %(out)s --preselect      # the depth to pre-select; then ask the review-depth question
python3 scripts/critic_brief.py   %(out)s          # _critic_brief.md + _contact_sheet.png
python3 scripts/critic_ledger.py  %(out)s --emit-template
# dispatch agents/shot-critic.md as a SUBAGENT whose entire input is the path %(out)s —
#   no rationale, no summary of what you fixed, no steer about where to look
# after applying fixes and re-rendering: python3 scripts/critic_brief.py %(out)s AGAIN (a new sheet + history),
#   and ask the review-depth question first if meta.review is not recorded (SKILL.md 9d) — --final refuses both
python3 scripts/critic_ledger.py  %(out)s --final
#   exit 0 means the LEDGER is well formed — NOT that the film may ship. The verdict is what
#   ships it: --final prints `the FILM is not delivered` on a REVISE and still exits 0, because
#   the exit code gates the REVIEW's form. Read the verdict line, not the exit code.
```

`--final` refuses three things: a ledger with MISSING ROWS (a dimension nobody looked at is a missing row,
not an absence of complaint), a BARE verdict (every pass/fail must cite a keyframe that exists), and a
ledger written by the film's own maker.
'''


def _not_delivered(out_dir):
    """Leave the remaining work IN the deliverable, not only in the log."""
    try:
        with open(os.path.join(out_dir, _NOT_DELIVERED), "w", encoding="utf-8") as fh:
            fh.write(_NEXT_STEPS % {"out": out_dir})
    except OSError:
        pass
    print("[render_remotion] RENDERED, not DELIVERED — wrote %s with the remaining steps." % _NOT_DELIVERED)
    print("[render_remotion] next: python3 scripts/critic_brief.py %s" % out_dir)
    print("[render_remotion]  then: dispatch agents/shot-critic.md (input = the out_dir path, nothing else)")
    print("[render_remotion]  then: python3 scripts/critic_ledger.py %s --final" % out_dir)
    print("[render_remotion]        read its VERDICT line — exit 0 only means the ledger is well "
          "formed; a REVISE verdict exits 0 too and the film is NOT delivered")



def render(out_dir, vertical=False, reduced_motion=False, sample=None, log="error", no_plan=False, whole=False):
    """Render the whole deck to out.mp4 (+ out.srt / _keyframes / optional SFX), or one scene (sample=N) to
    sample.mp4 for the sign-off checkpoint. Routes through the remotion bespoke-shot library. `reduced_motion`
    stills the #camera drift (accessibility); `vertical` (or meta.aspect) renders portrait 1080x1920 via the
    aspect-aware Composition; `no_plan` is accepted for CLI parity."""
    data = sb.load(os.path.join(out_dir, "storyboard.json"))
    _renderer = (data.get("meta") or {}).get("renderer")
    if _renderer == "remotion":
        return _render_remotion(out_dir, data, sample=sample, log=log, reduced_motion=reduced_motion, vertical=vertical,
                                whole=whole)
    if _renderer == "remotion-legacy":
        raise RuntimeError(
            "the legacy generic-scene Remotion tier has been REMOVED in the phase-3 cutover — set "
            "meta.renderer='remotion' (the bespoke-shot LIBRARY, remotion/LIBRARY.md) and run the "
            "shot-director step. An old-tier storyboard (planes/stage/atmosphere) must be re-authored.")
    raise RuntimeError("render_remotion handles only the Remotion tier (meta.renderer='remotion'); got %r "
                       "— use render.py for the html/local tier." % _renderer)


def main():
    import sys
    # line by line even into a file or a pipe: a render watched through its log must show where it is (the anc film's
    # log stayed EMPTY for minutes, block-buffered, while beats rendered)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Render storyboard.json via the remotion bespoke-shot tier")
    ap.add_argument("out_dir")
    ap.add_argument("--vertical", action="store_true")
    ap.add_argument("--sample", type=int, default=None, help="render only scene N -> sample.mp4 (sign-off)")
    ap.add_argument("--reduced-motion", action="store_true")
    ap.add_argument("--log", default="error")
    ap.add_argument("--no-plan", action="store_true", help="(accepted for CLI parity; no-op on this tier)")
    ap.add_argument("--whole", action="store_true",
                    help="render the film in ONE pass instead of per beat (no segment cache is read or written)")
    a = ap.parse_args()
    render(a.out_dir, vertical=a.vertical, reduced_motion=a.reduced_motion, sample=a.sample, log=a.log, no_plan=a.no_plan,
           whole=a.whole)


if __name__ == "__main__":
    main()
