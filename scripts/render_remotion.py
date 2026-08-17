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
_KINETIC_TYPES = {"slide", "wipe", "clock", "dissolve", "carry"}


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
    lines, n = [], 0                                   # SRT: scene-level (the narration) over each scene's solo span
    for i, sc in enumerate(scenes):
        cap = sc.get("caption")
        if not cap:
            continue
        t0 = starts[i]
        t1 = starts[i + 1] if i + 1 < len(scenes) else t0 + sc["durF"] / fps
        n += 1
        lines.append("%d\n%s --> %s\n%s\n" % (n, _srt_ts(t0), _srt_ts(max(t0 + 0.4, t1 - 0.05)), cap))
    with open(os.path.join(out_dir, "out.srt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    if shutil.which("ffmpeg") and os.path.exists(out_mp4):   # per-scene keyframes for the shot-critic
        kdir = os.path.join(out_dir, "_keyframes"); os.makedirs(kdir, exist_ok=True)
        for i, sc in enumerate(scenes):
            mid = starts[i] + (sc["durF"] / fps) * 0.5
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % mid, "-i", out_mp4,
                            "-frames:v", "1", os.path.join(kdir, "scene_%02d.png" % (i + 1))], check=False)
        print("[render_remotion] wrote out.srt + %d keyframes (_keyframes/) for the shot-critic + A/V gate." % len(scenes))


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
    fps, scenes = 30, []
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
        caption = (s.get("narration") or s.get("script") or s.get("caption") or "").strip()
        scene = {"shot": shot, "props": props, "durF": int(round(dur * fps)),
                 "mp3": str(audio).replace(os.sep, "/"), "caption": caption}
        tin = _transition_in(s)   # a MARKED seam (chapter break) → Film's kinetic transition; else the safe fade
        if tin:
            scene["transitionIn"] = tin
        scenes.append(scene)
    meta = data.get("meta") or {}
    reduced = bool(reduced_motion or meta.get("reduced_motion"))
    # ASPECT: --vertical or meta.aspect:"9:16" renders the Film Composition at 1080x1920 (Root.tsx calculateMetadata
    # reads this `aspect` prop). Any of 16:9 / 9:16 / 1:1 / 4:5 / 4:3; unknown falls back to 16:9.
    aspect = "9:16" if vertical else str(meta.get("aspect") or "16:9")
    props = {"scenes": scenes, "camera": _camera_amp(meta), "reducedMotion": reduced, "aspect": aspect,
             "captions": bool(meta.get("captions", True))}
    theme = meta.get("theme")                 # the per-topic atmosphere WORLD (motif + palette) behind every shot
    if isinstance(theme, dict):
        props["theme"] = theme
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
                if sfx_scenes:                          # a closing reveal bell on the last beat
                    sfx_scenes[-1]["shots"] = [{"startFrame": 0}]
                sfx.mix(out_dir, out_mp4, sfx_scenes, meta, fps)   # transition whooshes + reveal + meta.bgm
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
