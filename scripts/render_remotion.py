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
import argparse, json, os, shutil, subprocess, sys
import re
import storyboard as sb

_REMOTION2_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion")
_REMOTION2_TR = 12   # cross-dissolve length in Film.tsx (frames) — the output timeline is compressed by this per cut

# The MARKED-seam grammar (P2): a storyboard scene MARKS the transition INTO it. Only kinetic styles produce a
# mark — everything else (fade/dip/drift/blur/none/absent) is the luminance-safe default fade in Film.tsx, and a
# kinetic mark across a dark↔light gap is itself suppressed back to fade there (Film's pickPresentation). This
# maps the deck's `transition_style` vocabulary (shared with the local tier) onto the bespoke transition set;
# an explicit `transition_in:{type,direction}` on the scene wins outright (a direct remotion mark).
_TRANSITION_STYLE = {
    "slide": {"type": "slide", "direction": "from-right"}, "push": {"type": "slide", "direction": "from-right"},
    "lift": {"type": "slide", "direction": "from-bottom"}, "slide-up": {"type": "slide", "direction": "from-bottom"},
    "wipe": {"type": "wipe", "direction": "from-bottom"},
    "clock": {"type": "clock"}, "clockwipe": {"type": "clock"}, "clock-wipe": {"type": "clock"},
    "dissolve": {"type": "dissolve"},
    "carry": {"type": "carry"}, "collapse": {"type": "carry"}, "line": {"type": "carry"}, "match-cut": {"type": "carry"},
}
# `focus` is the depth seam (Film.tsx FocusRelayPresentation) — the rack-focus hand-off. It belongs here or
# a storyboard that asks for it is silently downgraded to a fade, which is the exact "built but unreachable"
# failure this file's `transition_in` docstring was written about.
_KINETIC_TYPES = {"slide", "wipe", "clock", "dissolve", "carry", "focus"}


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


def _transition_in(slide):
    """Map a storyboard scene's transition intent → the Film `transitionIn` mark (or None = the safe default fade).
    Only a MARKED (kinetic) seam returns a value; the shot-director budgets ~2-3 per film for chapter breaks."""
    ti = slide.get("transition_in")
    if isinstance(ti, dict) and ti.get("type") in _KINETIC_TYPES:          # explicit remotion mark wins
        out = {"type": ti["type"]}
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


def _remotion_deliverables(out_dir, scenes, out_mp4, fps):
    """Delivery parity with the html tier so the WORKFLOW's critic + A/V gate have material: write out.srt
    (from the overlap-compressed scene timeline) and _keyframes/scene_NN.png (one mid-scene frame per beat,
    extracted from out.mp4) for the shot-critic filmstrip + `check_av`."""
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
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % at, "-i", out_mp4,
                            "-frames:v", "1", os.path.join(kdir, "scene_%02d.png" % (i + 1))], check=False)
            # ALSO a MOTION frame, in _keyframes/motion/. The settled frame is the right one for every
            # frame-craft question — is anything colliding, off-frame, illegible — but it is the wrong one
            # for every MOTION question, because by definition nothing is moving in it. Reviewing motion
            # from settled frames is how a delivered film's reveal timing went unexamined for six rounds.
            # Cheap (one more ffmpeg seek per beat) and kept in a subdirectory so nothing that globs
            # scene_*.png picks it up by accident.
            mdir = os.path.join(kdir, "motion"); os.makedirs(mdir, exist_ok=True)
            mid = starts[i] + frame_at_t(durF, 0.42) / fps
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % mid, "-i", out_mp4,
                            "-frames:v", "1", os.path.join(mdir, "scene_%02d.png" % (i + 1))], check=False)
        print("[render_remotion] wrote out.srt + %d keyframes (_keyframes/) for the shot-critic + A/V gate." % len(scenes))


def build_scenes(slides, out_dir, valid, fps=30):
    """The storyboard -> Film SceneSpec[] translation, on its own so it can be TESTED without a render.

    It was inline in _render_remotion, which meant the only way to check that a storyboard field reaches
    the Film was to render a film. That is how `ground`/`key` came to be forwarded by nothing: the runtime
    could re-ground every register, and a delivered film could still only ever be one near-black, because
    the translation nobody could test had never learned the fields.
    """
    scenes = []
    for s in slides:
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
        caption = (s.get("narration") or s.get("script") or s.get("caption") or "").strip()
        scene = {"shot": shot, "props": props, "durF": int(round(dur * fps)),
                 "mp3": str(audio).replace(os.sep, "/"), "caption": caption}
        tin = _transition_in(s)   # a MARKED seam (chapter break) → Film's kinetic transition; else the safe fade
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


def _render_remotion(out_dir, data, sample=None, log="error", reduced_motion=False, vertical=False):
    """Render via the bespoke-shot LIBRARY. Fails loud on a missing/unknown shot or missing audio."""
    if not shutil.which("npx"):
        raise RuntimeError("Node/npx not found — the Remotion tier needs Node.js.")
    if not os.path.isdir(os.path.join(_REMOTION2_DIR, "node_modules")):
        raise RuntimeError("remotion deps not installed — run `cd %s && npm install` once." % _REMOTION2_DIR)
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
    props_path = os.path.join(out_dir, ".remotion-props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, allow_nan=False, ensure_ascii=False)
    out_name = "sample.mp4" if sample is not None else "out.mp4"
    out_mp4 = os.path.abspath(os.path.join(out_dir, out_name))
    gl = os.environ.get("REMOTION_GL") or ("angle" if sys.platform in ("darwin", "win32") else "swangle")
    cmd = ["npx", "remotion", "render", "src/index.ts", "Film", out_mp4,
           "--props=" + os.path.abspath(props_path), "--public-dir=" + os.path.abspath(out_dir),
           "--gl=" + gl, "--log=" + log,
           "--timeout=" + str(int(os.environ.get("REMOTION_TIMEOUT_MS", "120000") or "120000"))]
    # CONCURRENCY. Remotion opens one browser tab per worker and EACH loads the film's fonts; on a loaded
    # machine a starved tab can blow past its delayRender and kill a long render outright. REMOTION_CONCURRENCY
    # lets a caller trade wall-clock for that safety without editing this file.
    _conc = os.environ.get("REMOTION_CONCURRENCY")
    if _conc:
        cmd.append("--concurrency=" + str(int(_conc)))
    print("[render_remotion] %s: %d scene(s) -> %s"
          % ("sample" if sample is not None else "full", len(scenes), out_mp4))
    try:
        subprocess.run(cmd, cwd=_REMOTION2_DIR, check=True)
    except subprocess.CalledProcessError:
        if any(a.startswith("--gl=") for a in cmd):
            print("[render_remotion] render failed with GL — retrying ONCE without --gl (software raster; slower).")
            subprocess.run([a for a in cmd if not a.startswith("--gl=")], cwd=_REMOTION2_DIR, check=True)
        else:
            raise
    if sample is None:                                 # delivery parity: srt + critic keyframes (full render only)
        try:
            _remotion_deliverables(out_dir, scenes, out_mp4, fps)
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
    return out_mp4


def render(out_dir, vertical=False, reduced_motion=False, sample=None, log="error", no_plan=False):
    """Render the whole deck to out.mp4 (+ out.srt / _keyframes / optional SFX), or one scene (sample=N) to
    sample.mp4 for the sign-off checkpoint. Routes through the remotion bespoke-shot library. `reduced_motion`
    stills the #camera drift (accessibility); `vertical` (or meta.aspect) renders portrait 1080x1920 via the
    aspect-aware Composition; `no_plan` is accepted for CLI parity."""
    data = sb.load(os.path.join(out_dir, "storyboard.json"))
    _renderer = (data.get("meta") or {}).get("renderer")
    if _renderer == "remotion":
        return _render_remotion(out_dir, data, sample=sample, log=log, reduced_motion=reduced_motion, vertical=vertical)
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
    a = ap.parse_args()
    render(a.out_dir, vertical=a.vertical, reduced_motion=a.reduced_motion, sample=a.sample, log=a.log, no_plan=a.no_plan)


if __name__ == "__main__":
    main()
