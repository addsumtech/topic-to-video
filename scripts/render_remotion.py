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


def _scene_shot(s):
    """The shot specification for a scene (top-level or in props), or None."""
    return s.get("shot") or (s.get("props") or {}).get("shot")


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


def unsupported_scenes(data):
    """Scene indices whose visual would render BLANK on the cinematic tier (non-image html/chart/…).

    A scene carrying cinematic `layers` OR `stage`+`shot` (shot-based compositing) is renderable even
    with no `image`, so it is NOT unsupported — those paths draw the content."""
    bad = []
    for s in data.get("slides", []):
        t = s.get("type", "slide")
        # Shot-based or legacy layered scenes are OK (they render via SceneStage/CinematicScene)
        if _scene_stage(s) or _scene_layers(s):
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


def _copy_fonts(out_dir):
    """Copy bundled fonts from assets/fonts/*.ttf to out_dir/.fonts/ for @remotion/fonts staticFile() to load.
    Best-effort: silently no-ops if assets/fonts/ is missing (colour-only deck, no custom fonts)."""
    src_fonts = os.path.join(out_dir, "assets", "fonts")
    if not os.path.isdir(src_fonts):
        return
    dst_fonts = os.path.join(out_dir, ".fonts")
    os.makedirs(dst_fonts, exist_ok=True)
    for name in os.listdir(src_fonts):
        if name.lower().endswith(".ttf"):
            shutil.copy2(os.path.join(src_fonts, name), os.path.join(dst_fonts, name))


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
        shot = _scene_shot(s)
        layers = _scene_layers(s)
        camera = s.get("camera") or props.get("camera")
        lens = s.get("lens") or props.get("lens")           # 3D perspective path (dolly/pitch/yaw)
        perspective = _num(s.get("perspective") or props.get("perspective"), "scene %s perspective" % s.get("index"), None) \
            if (s.get("perspective") or props.get("perspective")) is not None else None

        # Shot-based scene: pass stage + shot through to SceneStage (validation in TypeScript)
        if stage and shot:
            if not isinstance(stage, dict):
                raise RuntimeError("cinematic scene %s: `stage` must be an object" % s.get("index"))
            if not isinstance(shot, dict):
                raise RuntimeError("cinematic scene %s: `shot` must be an object" % s.get("index"))
            # Validate stage.elements is a list
            elements = stage.get("elements")
            if not isinstance(elements, list):
                raise RuntimeError("cinematic scene %s: `stage.elements` must be a list" % s.get("index"))
            # Coerce shot.duration (required)
            if shot.get("duration") is None:
                shot = dict(shot)
                shot["duration"] = frames
            else:
                shot = dict(shot)
                shot["duration"] = int(round(_num(shot["duration"], "scene %s shot.duration" % s.get("index"))))

        # Legacy layered scenes: fail-loud coercion — no NaN/string reaches Remotion
        if layers is not None:
            layers = _clean_layers(layers, "scene %s" % s.get("index"))
        if layers and not camera and not lens and not (stage and shot):  # flat layered scene gets default push-in
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
            "stage": stage if (stage and shot) else None,    # shot-based (P2+): scene-space staging
            "shot": shot if (stage and shot) else None,      # shot specification (type, motion, target)
            "camera": camera,                        # cinematic FLAT: eased virtual-camera keyframes (or None)
            "lens": lens,                            # cinematic 3D: dolly/pitch/yaw keyframes (or None)
            "perspective": float(perspective) if perspective else None,
            "layers": layers,                        # cinematic: depth planes (or None)
            "reducedMotion": reduced,                # freeze the camera + show reveals instantly
        })
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
    print("[render_remotion] %s: %d scene(s), %dx%d @%dfps -> %s"
          % ("sample" if sample is not None else "full", len(props["scenes"]),
             props["width"], props["height"], props["fps"], out_mp4))
    subprocess.run(cmd, cwd=_REMOTION_DIR, check=True)
    try:
        os.unlink(props_path)                         # transient — don't leave it in the out_dir
    except OSError:
        pass

    _write_filmstrips(out_dir, data, out_mp4)         # the D12 evidence the design-critic judges from
    if sample is None:                                # out.srt for parity with the local renderer
        rd._write_srt(data, os.path.join(out_dir, "out.srt"))
        print("[render_remotion] done -> %s (+ out.srt)" % out_mp4)
    else:
        print("[render_remotion] sample done -> %s" % out_mp4)
    return out_mp4


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
        is_cine = s.get("type") == "cinematic" or _scene_layers(s)
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
