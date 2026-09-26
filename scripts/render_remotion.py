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
}
# `focus`, `through-dark` and `portal` are the DEPTH seams (Film.tsx). They belong here or a storyboard that
# asks for one is silently downgraded to a fade, which is the exact "built but unreachable" failure this
# file's `transition_in` docstring was written about — and it has already cost this repo two deliveries.
_KINETIC_TYPES = {"slide", "push", "lift", "wipe", "clock", "dissolve", "fadethrough", "drift", "blur",
                  "carry", "focus", "through-dark", "portal", "return"}


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
# shared with the html tier, where `dip` IS the default seam and `cut`/`none` mean "no seam at all". They
# resolve to no remotion mark, which is correct — but they are KNOWN, so `validate.py` must not report them
# as words this renderer cannot draw.
_UNMARKED_WORDS = {"cut", "none", "hard-cut", "dip", "fade"}


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


def _transition_in(slide, travel=None):
    """Map a storyboard scene's transition intent → the Film `transitionIn` mark (or None = the safe default fade).
    Only a MARKED (kinetic) seam returns a value; the shot-director budgets ~2-3 per film for chapter breaks.

    `travel` is this beat's (dx, dy) from `film_board.travels`, present only on a beat that declares a
    RETURN. It arrives as an argument rather than being derived here because the vector is a property of the
    whole board — where this beat sits and where the one it names sits — and a per-slide function cannot see
    that. One definition, in `film_board`, used by the planner, the validator and this emitter alike.
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
            return out
    style = (slide.get("transition_style") or "").strip().lower()
    return dict(_TRANSITION_STYLE[style]) if style in _TRANSITION_STYLE else None


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


def resolve_cue_props(props, out_dir, audio, narration, dur_s, fps):
    """A prop written `{"cue": "<words the narration says>"}` becomes the `t` at which the voice says them.

    WHY. A register that changes state at a fixed fraction of its clip changes it at a moment that has nothing
    to do with the sentence over it. Measured on a delivered film: CompanionCard turned its card grey at ~19.9s
    while the voice was still saying 「绿色的工作中」 (20.5-21.7s) — for a second the frame said 等待中 under a
    sentence saying 工作中. The timing belongs to the narration, and the narration's own word times are on disk
    (tts.py writes `audio/NN.words.json`), so the board names the WORDS and this puts the event on them. Without
    word times the position is estimated from the narration text, the same fallback the html tier's cues use.
    `{"cue": ..., "offset": seconds}` shifts it. An anchor the narration does not contain is an ERROR — landing
    it anywhere would be exactly the guess this exists to remove."""
    def is_cue(v):
        return isinstance(v, dict) and "cue" in v and set(v) <= {"cue", "offset"}
    if not any(is_cue(v) for v in (props or {}).values()):
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
    out = dict(props)
    for k, v in props.items():
        if not is_cue(v):
            continue
        phrase = str(v["cue"] or "").strip()
        if not phrase or _cues._anchor_pos(narration or "", phrase) < 0:
            raise SystemExit("[render_remotion] shot prop `%s` cues %r, which this beat's narration does not say "
                             "— name words the voice actually speaks" % (k, phrase))
        if words and _cues._find(words, phrase, 0) >= 0:
            sec = _cues.resolve_cues(words, [phrase])[0]
        else:
            sec = _cues.estimate_cues_from_text([phrase], narration or "", dur_s)[0]
        sec += float(v.get("offset") or 0.0)
        out[k] = t_at_seconds(sec, round(dur_s * fps), fps)
    return out


def film_shot_props(slide, out_dir, fps=30):
    """A beat's `shot_props` as the RENDERER passes them — cue props resolved to `t`. Every gate that renders a
    film's beat on its own (text_safe_qa, cjk_type_qa, shot_proof) goes through this, so a board that writes
    `{"cue": ...}` is checked with the value the film actually plays, not with an object no register reads.
    Before tts has run there is no duration; the cue is then placed by its position in the narration text."""
    props = dict(slide.get("shot_props") or {})
    narration = slide.get("narration") or slide.get("script") or ""
    dur = slide.get("duration")
    if dur:
        return resolve_cue_props(props, out_dir, slide.get("audio"), narration, float(dur), fps)
    return resolve_cue_props(props, out_dir, None, narration, 1.0, fps) if any(
        isinstance(v, dict) and "cue" in v for v in props.values()) else props


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
    starts, acc = [], 0                                # output-timeline start of each scene (each cut removes tr frames)
    for i, sc in enumerate(scenes):
        starts.append((acc - i * tr) / fps)
        acc += sc["durF"]
    # SRT must MIRROR THE BURN, not summarise it. It used to emit one scene-long cue carrying the whole
    # narration while Film.tsx burns one chunk PER SENTENCE, each timed by its share of the characters — so
    # the sidecar shipped cues up to 3x too long and mistimed against what a viewer actually saw. Reproduce
    # Film.tsx's splitCaption (including its decimal guard) and its length-weighted chunk timing here.
    half = tr // 2
    lines, n = [], 0
    for i, sc in enumerate(scenes):
        cap = sc.get("caption")
        if not cap:
            continue
        chunks = _split_caption(cap)
        if not chunks:
            continue
        a = (starts[i] * fps) + (half if i > 0 else 14)         # window in FRAMES on the output timeline
        b = (starts[i] * fps) + sc["durF"] - ((tr - half) if i + 1 < len(scenes) else 16)
        span = max(1.0, b - a)
        lens = [max(1, len(c)) for c in chunks]
        tot = float(sum(lens))
        cum = 0.0
        for c, L in zip(chunks, lens):
            f0 = a + span * (cum / tot)
            cum += L
            f1 = a + span * (cum / tot)
            n += 1
            lines.append("%d\n%s --> %s\n%s\n" % (n, _srt_ts(f0 / fps), _srt_ts(max(f0 / fps + 0.3, f1 / fps - 0.02)), c))
    with open(os.path.join(out_dir, "out.srt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    if shutil.which("ffmpeg") and os.path.exists(out_mp4):   # per-scene keyframes for the shot-critic
        kdir = os.path.join(out_dir, "_keyframes"); os.makedirs(kdir, exist_ok=True)
        src_path = os.path.join(kdir, _KEYFRAME_SOURCES)
        try:
            was = json.load(open(src_path, encoding="utf-8")) if segments else {}
        except (OSError, ValueError):
            was = {}
        now, kept = {}, 0

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


def build_scenes(slides, out_dir, valid, fps=30):
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
        props = s.get("shot_props") or {}
        if not isinstance(props, dict):
            raise RuntimeError("scene #%s `shot_props` must be an object." % idx)
        # A PhotoPlate frames the WHOLE photograph, so it needs the picture's proportions. Read from the
        # file here rather than asked of the author: measured, a portrait photograph in the register's
        # default landscape plate lost 67% of its height, and since `marks` are plate fractions the crop
        # also moved every mark off the thing it named.
        if shot == "PhotoPlate" and isinstance(props.get("src"), str) and not props.get("imageAspect"):
            try:
                from PIL import Image as _Im
                with _Im.open(os.path.join(out_dir, props["src"])) as _im:
                    if _im.height:
                        props = dict(props, imageAspect=round(_im.width / _im.height, 4))
            except Exception:
                pass                          # a missing or unreadable file is the renderer's problem, not ours
        # THE EAR'S TEXT AND THE EYE'S TEXT ARE NOT THE SAME TEXT. `narration` is written to be SPOKEN, so a
        # film spells an initialism out — "没有用 T T S", "S S H", "A G P L 三点零" — to stop edge-tts reading
        # it as a word. That is correct for the voice and wrong on the frame, and it shipped: an independent
        # reviewer found three burned captions carrying spelled-out forms, and on the closing beat the SAME
        # fact twice in one frame — the register's own note reading `AGPL-3.0` above a caption reading
        # `A G P L 三点零`. A slide may now carry an explicit `caption` for the eye; without one, a run of
        # spaced single capitals is rejoined, which is the safe half of the transform and needs no author.
        caption = (s.get("caption") or _caption_for_eye(s.get("narration") or s.get("script") or "")).strip()
        props = resolve_cue_props(props, out_dir, audio, s.get("narration") or s.get("script") or "", dur, fps)
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
        tin = _transition_in(s, _travels.get(i))   # a MARKED seam → Film's kinetic transition; else the safe fade
        if tin:
            scene["transitionIn"] = tin
        cam = _camera(s)          # a MOTIVATED per-beat move (push/pull); absent = hold
        if cam:
            scene["camera"] = cam
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
        scenes.append(scene)
    return scenes


def film_props(out_dir, data, sample=None, reduced_motion=False, vertical=False):
    """(props, slides): the Film's input props for this board, and the slides they were built from.

    The render and `remotion_segments.py --plan` both ask this one function, so a plan describes the board
    AS IT IS NOW. Reading the last render's props file instead would answer "which beats would a render
    redo?" with "none" right after an edit — the one moment anybody asks.
    """
    valid = _remotion_shot_ids()
    slides = data.get("slides", [])
    if sample is not None:
        slides = [s for s in slides if s.get("index") == sample]
        if not slides:
            raise RuntimeError("no scene with index %s to sample" % sample)
    fps = 30
    scenes = build_scenes(slides, out_dir, valid, fps)
    meta = data.get("meta") or {}
    reduced = bool(reduced_motion or meta.get("reduced_motion"))
    # ASPECT: --vertical or meta.aspect:"9:16" renders the Film Composition at 1080x1920 (Root.tsx calculateMetadata
    # reads this `aspect` prop). Any of 16:9 / 9:16 / 1:1 / 4:5 / 4:3; unknown falls back to 16:9.
    aspect = "9:16" if vertical else str(meta.get("aspect") or "16:9")
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
             "reducedMotion": reduced, "aspect": aspect,
             "captions": bool(meta.get("captions", True))}
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
    return props, slides


def _render_remotion(out_dir, data, sample=None, log="error", reduced_motion=False, vertical=False, whole=False):
    """Render via the bespoke-shot LIBRARY. Fails loud on a missing/unknown shot or missing audio."""
    if not shutil.which("npx"):
        raise RuntimeError("Node/npx not found — the Remotion tier needs Node.js.")
    if not os.path.isdir(os.path.join(_REMOTION2_DIR, "node_modules")):
        raise RuntimeError("remotion deps not installed — run `cd %s && npm install` once." % _REMOTION2_DIR)
    props, slides = film_props(out_dir, data, sample=sample, reduced_motion=reduced_motion, vertical=vertical)
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
    if segmented:
        try:
            done = _rs.render_film(out_dir, props, props_path, out_mp4, run_flags, _rs.pixel_flags(gl),
                                   labels=[sl.get("index", i + 1) for i, sl in enumerate(slides)])
            print("[render_remotion] %d beat(s): %d re-rendered, %d reused from %s/"
                  % (done["beats"], len(done["rendered"]), done["beats"] - len(done["rendered"]), _rs.CACHE_DIR))
            segments_used = done["segments"]
        except _rs.ModelMismatch as e:
            print("[render_remotion] the per-beat cache disagreed with the film (%s) — rendering it WHOLE "
                  "instead; nothing from the cache is used." % e)
            segmented = False
    if not segmented:
        cmd = ["npx", "remotion", "render", "src/index.ts", "Film", out_mp4,
               "--props=" + os.path.abspath(props_path), "--public-dir=" + os.path.abspath(out_dir)] + run_flags
        try:
            subprocess.run(cmd, cwd=_REMOTION2_DIR, check=True)
        except subprocess.CalledProcessError:
            print("[render_remotion] render failed with GL — retrying ONCE without --gl (software raster; slower).")
            subprocess.run([a for a in cmd if not a.startswith("--gl=")], cwd=_REMOTION2_DIR, check=True)
    if sample is None:                                 # delivery parity: srt + critic keyframes (full render only)
        try:
            _remotion_deliverables(out_dir, scenes, out_mp4, fps, segments=segments_used)
        except Exception as e:
            print("[render_remotion] deliverables (srt/keyframes) skipped: %s" % e)
        meta = data.get("meta") or {}
        if meta.get("sound_design"):                   # opt-in SFX(+BGM) bed, post-render
            try:
                import sfx
                tr = _REMOTION2_TR                      # feed durationInFrames = durF-TR so cue times land on the
                # carry transitionIn per scene so the SFX marks the SAME seams the eye does (fades stay quiet)
                sfx_scenes = [{"durationInFrames": max(1, sc["durF"] - tr), "transitionIn": sc.get("transitionIn")}
                              for sc in scenes]         # overlap-compressed timeline
                if sfx_scenes:                          # the closing sentence lands on the last beat's arrival
                    sfx_scenes[-1]["shots"] = [{"startFrame": 0}]
                sfx.mix(out_dir, out_mp4, sfx_scenes, meta, fps)   # whooshes + riser/impact/sparkle + meta.bgm
            except Exception as e:
                print("[render_remotion] sound_design skipped: %s" % e)
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
python3 scripts/critic_brief.py   %(out)s          # _critic_brief.md + _contact_sheet.png
python3 scripts/critic_ledger.py  %(out)s --emit-template
# dispatch agents/shot-critic.md as a SUBAGENT whose entire input is the path %(out)s —
#   no rationale, no summary of what you fixed, no steer about where to look
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
