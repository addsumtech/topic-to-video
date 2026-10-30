#!/usr/bin/env python3
"""The HTML tier's census for jitter_qa: where every line of type TRULY is on every frame of out.mp4.

    python3 scripts/jitter_qa.py <out_dir>        # an HTML-tier film is routed here by its tier (validate.film_tier)

WHY. jitter_qa judges type against its own geometry from the delivered pixels; on the remotion tier the geometry is
the Film composition's census. The HTML tier had nothing in that place: its glide audit (keyframe_qa) reads the DOM
and judges whether Chrome WILL snap a baseline — a rule — and nothing read the encoded film. Every way this tier
moves type that the rule does not model went unjudged: a page's own camera or Ken Burns, a reveal under a
transform the rule cannot decompose (matrix3d), the image slides' zoompan, the encode.

WHERE EACH SCENE'S GEOMETRY COMES FROM.
  html    the page itself, on the frames that SHIP: the same capture plan render_html captures on
          (scenes.html_capture_plan, cue mode included, held frames expanded to the capture they repeat) and the
          same in-page census keyframe_qa's glide audit runs (its _GLIDE_JS_TMPL), which reports each line's own TEXT
          box (its text ranges, every transform applied). A reduced-motion film is censused on the page with
          reduced-motion.css injected, as it is rendered.
  slide   an image with a Ken Burns move: the move is render._motion_exprs, applied by zoompan in a supersampled
          space, so the true place of any point of the fitted image on frame `on` is known exactly. The image has no
          DOM, so the census tracks its edge-dense tiles (jitter_qa.tiles_of) through that move.
  other   programmatic scenes (title, keypoints, timeline, chart, compare) are drawn by PIL at whole pixels from
          their own arithmetic and have no geometry to read. They SETTLE, though: after the last frame that differs
          from the scene's final interior frame, its edge-dense tiles are truly still, and are judged there (a pop,
          a shimmer). The reveal before that is NOT judged, and counted as such.

WHAT IS TAKEN OUT, AND COUNTED. Frames inside a scene-edge transition (render._edge_filter: the seam moves or fades
the whole page, which the page's census does not describe); lines under the burned overlay caption (a static
caption in the window would pin it); and the platform-safe portrait frame is not taken out but MAPPED — its page is
drawn scaled into a frame (render._platform_safe), and every box is carried into it.

THE FRAME COUNTS MUST AGREE. Each scene's frame count is read from its cached clip when the clips add up to
out.mp4, else round(duration x fps) as the render computes it; if the scenes do not add up to the video's own count
the census is of another render and nothing is measured (RuntimeError -> jitter_qa exit 2).
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

EDGE_PAD = 1          # frames beyond the transition's own length also left out (the fade's first/last step)


def video_frames(path):
    """The number of video frames in a file (packets, no decode)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return int((r.stdout or "").strip().splitlines()[0].strip().strip(","))
    except (ValueError, IndexError):
        raise RuntimeError("%s: ffprobe could not count its frames (%s)" % (path, (r.stderr or "").strip()[-200:]))


def scene_frames(out_dir, slides, fps, n_video):
    """[frames of each scene] that add up to the video. The cached clips are the render's own, when they add up."""
    clipdir = os.path.join(out_dir, ".clips")
    clips = [os.path.join(clipdir, "clip_%02d.mp4" % s["index"]) for s in slides]
    if all(os.path.isfile(c) for c in clips):
        counts = [video_frames(c) for c in clips]
        if sum(counts) == n_video:
            return counts, "the render's cached clips"
    counts = [max(1, int(round(float(s.get("duration") or 0) * fps))) for s in slides]
    if sum(counts) == n_video:
        return counts, "round(duration x fps)"
    raise RuntimeError("the video has %d frames and the board's scenes add up to %d (cached clips: %s) — the census "
                       "would be of another render; re-render, then measure" % (
                           n_video, sum(counts), "present" if all(os.path.isfile(c) for c in clips) else "absent"))


def edge_frames(meta, slide, nf, fps, W, H):
    """(lead, tail): how many frames at each end of a scene a seam transition owns (render._edge_filter)."""
    import render as R
    import storyboard as sb
    dur = nf / float(fps)
    parts, _lab = R._edge_filter(meta, dur, slide, "v", W, H)
    if not parts:
        return 0, 0
    t_, d = sb.normalize_transition(slide or {})
    t = t_ if t_ in ("dip", "in", "out", "none") else (meta or {}).get("transition", "dip")
    d = float(d if d is not None else (meta or {}).get("transition_seconds", 0.2))
    n = int(math.ceil(d * fps)) + EDGE_PAD
    return (n if t in ("dip", "in") else 0), (n if t in ("dip", "out") else 0)


def _mapper(safe, W, H):
    """Page px -> frame px: identity, or into the platform-safe portrait frame."""
    if not safe:
        return lambda x, y, w, h: (x, y, w, h)
    kx, ky = safe["fw"] / float(W), safe["fh"] / float(H)
    return lambda x, y, w, h: (safe["x0"] + x * kx, safe["y0"] + y * ky, w * kx, h * ky)


def _page_url(out_dir, meta, s, workdir):
    """file:// URL of the page AS RENDERED: reduced-motion.css injected on a reduced-motion film (scenes.render_html)."""
    from urllib.parse import quote
    import scenes
    src = os.path.abspath(os.path.join(out_dir, (s.get("props") or {})["html"]))
    if not os.path.isfile(src):
        raise RuntimeError("scene %s: its page %s does not exist" % (s.get("index"), src))
    if meta.get("reduced_motion"):
        html = open(src, encoding="utf-8", errors="replace").read()
        # beside the page, so its relative links resolve as they do for the original
        dst = os.path.join(os.path.dirname(src), ".jitter_rm_%02d.html" % s["index"])
        open(dst, "w", encoding="utf-8").write(scenes._inject_reduced_motion(html, scenes._REDUCED_MOTION_CSS))
        workdir.append(dst)
        src = dst
    return "file://" + quote(src)


def html_scene(chrome, out_dir, meta, s, nf, fps, url):
    """{frame in scene: [line]} — the page's census on the frames that ship."""
    import keyframe_qa as kq
    import scenes
    import sync_qa as _sq
    pmeta = dict(meta, _out=out_dir, _narration=_sq.narration_of(s), _slide=s)
    plan = scenes.html_capture_plan(s.get("props") or {}, pmeta, nf, s.get("index"))
    base = url + ("?p=0&cues=%s&dur=%.3f" % (plan["cue_param"], nf / float(fps)) if plan["cue_param"] is not None
                  else "?p=0")
    with tempfile.TemporaryDirectory() as tmp:
        chrome.shot(base, os.path.join(tmp, "p0.jpg"))
    frames = kq._glide_census(chrome, nf, plan)
    if len(frames) != nf:
        raise RuntimeError("scene %s: the page census covers %d of its %d frames" % (s.get("index"), len(frames), nf))
    return frames


def kenburns_scene(out_dir, meta, s, nf, W, H):
    """{frame in scene: [tile line]} — the image's edge-dense tiles carried through the zoompan move exactly as
    render._render_slide drives it (supersampled by meta.motion_ss, crop x/y = (iw - iw/zoom) * pan)."""
    import render as R
    import jitter_qa as jq
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        fit = os.path.join(tmp, "fit.png")
        R._fit_frame(os.path.join(out_dir, s["image"]), fit, W, H, s.get("fit", "contain"),
                     bg_rgb=R._theme_rgb(out_dir, "--bg", (13, 17, 23)))
        g = np.asarray(Image.open(fit).convert("L"), dtype=np.float32)
    # apart by more than two window margins: under a zoom every tile moves differently, and a window that reaches its
    # neighbour is skipped as crowded (600 of 1335 pairs on the first Ken Burns fixture)
    tiles = jq.tiles_of(g, gap=2 * jq.PAD + 4)
    m = s.get("motion") or {"from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.0]}
    ze, xe, ye = R._motion_exprs(m, nf, meta.get("reduced_motion"), amp=R._intensity_amp(meta, s))
    ss = max(1, int(meta.get("motion_ss", 2)))
    bw, bh = W * ss, H * ss
    out = {}
    for on in range(nf):
        env = {"on": float(on)}
        z, xp, yp = (float(eval(e, {"__builtins__": {}}, env)) for e in (ze, xe, ye))   # noqa: S307 — our own arithmetic
        cx, cy = (bw - bw / z) * xp, (bh - bh / z) * yp                                 # the crop's corner, ss px
        lines = []
        for n, (x0, y0, x1, y1) in enumerate(tiles):
            X, Y = (x0 * ss - cx) * z / ss, (y0 * ss - cy) * z / ss
            lines.append({"k": "/tile%d" % n, "t": "image tile %d" % n, "x": X, "y": Y, "w": (x1 - x0) * z,
                          "h": (y1 - y0) * z, "o": 1})
        out[on] = lines
    return out


# A frame is SETTLED when no region of it still differs from the scene's last interior frame: the 99.9th percentile
# of |difference| under SETTLED_P999 grey levels (a static picture through x264 decodes within 1-2). A whole-frame MEAN
# was the first criterion and let a title's subtitle, still fading in over a few hundred pixels, read as settled —
# its tile then "trembled" 0.28 px. A tile must also carry real type: band energy at least TILE_MIN_SHARE of the
# densest tile's (the twelfth-densest tile of a title card is mostly ground).
SETTLED_P999 = 4.0
TILE_MIN_SHARE = 0.25


def _frame_at(video, n):
    """Grey float32 frame `n` of a video (decoded as stored, -fps_mode passthrough)."""
    import jitter_qa as jq
    W, H, _f = jq.probe(video)
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-fps_mode", "passthrough", "-vf",
                        "select=eq(n\\,%d)" % n, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True)
    if len(r.stdout) < W * H:
        raise RuntimeError("%s: frame %d could not be decoded" % (video, n))
    return np.frombuffer(r.stdout[:W * H], np.uint8).reshape(H, W).astype(np.float32)


def settled_scenes(video, spans):
    """{scene pos: (first settled frame, tiles)} for programmatic scenes. A PIL scene (title, keypoints, timeline,
    chart, compare) has no geometry to read, but it SETTLES: after its reveals nothing on it should change. Its last
    interior frame gives the edge-dense tiles; walking back while each frame is within SETTLED_DIFF of it gives the
    span in which those tiles are TRULY still — so their pixels are judged (a pop, a shimmer) on that span, and only
    the reveal before it goes unjudged. `spans` = {pos: (first, last) interior frame, in film frames}."""
    import jitter_qa as jq
    if not spans:
        return {}
    last = {pos: _frame_at(video, b) for pos, (a, b) in spans.items()}
    first = {pos: b for pos, (a, b) in spans.items()}
    diffs = {pos: {} for pos in spans}
    for i, fr in jq.frames(video):
        for pos, (a, b) in spans.items():
            if a <= i <= b:
                diffs[pos][i] = float(np.percentile(np.abs(fr - last[pos]), 99.9))
    out = {}
    for pos, (a, b) in spans.items():
        f = b
        while f - 1 >= a and diffs[pos].get(f - 1, 1e9) < SETTLED_P999:
            f -= 1
        first[pos] = f
        tiles = jq.tiles_of(last[pos], gap=2 * jq.PAD + 4)
        band = np.abs(jq._band(last[pos]))
        energy = [float(band[y0:y1, x0:x1].mean()) for x0, y0, x1, y1 in tiles]
        top = max(energy) if energy else 0.0
        out[pos] = (f, [t for t, e in zip(tiles, energy) if top > 0 and e >= TILE_MIN_SHARE * top])
    return out


def film_census(out_dir, video):
    """({frame: {"lines": [...]}} over every frame of `video`, {reason: line-pairs not judged}, [scope sentences])."""
    import render as R
    import storyboard as sb
    from _caption_band import caption_band_px
    data = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = dict(data.get("meta") or {}, _out=out_dir)
    slides = data.get("slides") or []
    if not slides:
        raise RuntimeError("the board has no scenes")
    fps = meta.get("fps", 30)
    vertical = meta.get("aspect") == "9:16"
    W, H = R._canvas(meta, vertical)
    band = R._caption_band_px(meta, W, H)
    import jitter_qa as jq
    Wv, Hv, _f = jq.probe(video)
    if (Wv, Hv) != (W, H + band):
        raise RuntimeError("out.mp4 is %dx%d and this board renders %dx%d%s — not this board's render"
                           % (Wv, Hv, W, H, (" + a %d px caption band" % band) if band else ""))
    n_video = video_frames(video)
    counts, how = scene_frames(out_dir, slides, fps, n_video)
    safe = R._platform_safe(meta, W, H)
    place = _mapper(safe, W, H)
    # overlay captions burn into the bottom of the PAGE (or the safe frame's caption room); in band mode they sit in a
    # strip below H, where no page line can be
    cap_top = None
    if meta.get("captions", True) and not band:
        cap_top = (safe["cap_bottom"] - safe["cap_room"]) if safe else H - caption_band_px(W, H)
    census, skip, scope = {}, {}, []
    programmatic = {}
    judged_scenes, not_judged = [], []
    chrome, temp_pages = None, []

    def no(why, n=1):
        skip[why] = skip.get(why, 0) + n
    try:
        off = 0
        for pos, (s, nf) in enumerate(zip(slides, counts)):
            kind = s.get("type", "slide")
            lead, tail = edge_frames(meta, s, nf, fps, W, H)
            # a callout is a STATIC layer drawn over the moving picture (render._callout_layer, its label above the
            # box): its ink in a window would pin it, so a tile that reaches one is left out (in frame px)
            pins = []
            for co in s.get("callouts") or [] if kind == "slide" else []:
                bx = co.get("box") if isinstance(co, dict) else None
                if isinstance(bx, (list, tuple)) and len(bx) == 4:
                    px0, py0, pw, ph = place(bx[0] * W - 8, bx[1] * H - 0.04 * H, (bx[2] - bx[0]) * W + 16,
                                             (bx[3] - bx[1]) * H + 0.04 * H + 8)
                    pins.append((px0, py0, px0 + pw, py0 + ph))
            per = None
            if kind == "html":
                if chrome is None:
                    import keyframe_qa as kq
                    chrome = kq._open_cdp(meta, W, H)
                    if chrome is None:
                        raise RuntimeError("no CDP Chrome to read the pages' geometry")
                per = html_scene(chrome, out_dir, meta, s, nf, fps, _page_url(out_dir, meta, s, temp_pages))
            elif kind == "slide" and s.get("image"):
                per = kenburns_scene(out_dir, meta, s, nf, W, H)
            if per is not None:
                judged_scenes.append(s.get("index", pos + 1))
            elif nf - tail - lead < 2:
                not_judged.append("%02d %s" % (s.get("index", pos + 1), kind))
            for i in range(nf):
                f = off + i
                lines = []
                for ln in (per or {}).get(i, {}).get("lines", []) if kind == "html" else (per or {}).get(i, []):
                    if kind == "html":
                        if "tx" not in ln:
                            continue
                        x, y, w, h = place(ln["tx"], ln["ty"], ln["tw"], ln["th"])
                    else:
                        x, y, w, h = place(ln["x"], ln["y"], ln["w"], ln["h"])
                    if i < lead or i >= nf - tail:
                        if (i + 1) < nf:
                            no("inside a scene-edge transition (the seam moves or fades the whole page)")
                        continue
                    if pins and any(not (x + w < p0 or x > p2 or y + h < p1 or y > p3) for p0, p1, p2, p3 in pins):
                        if (i + 1) < nf:
                            no("under a callout drawn over the moving picture (a static layer would pin the window)")
                        continue
                    if cap_top is not None and y + h > cap_top:
                        if (i + 1) < nf:
                            no("under the burned overlay caption (static ink in the window would pin it)")
                        continue
                    if "s" in (ln.get("fl") or ""):
                        if (i + 1) < nf:
                            no("marked data-type-steps (the page says its stepping is intended)")
                        continue
                    rec = {"k": "s%02d%s" % (s.get("index", pos + 1), ln["k"]), "t": ln.get("t") or "",
                           "x": x, "y": y, "w": w, "h": h, "o": ln.get("o", 1), "b": pos}
                    for key in ("v", "fl", "g"):
                        if key in ln:
                            rec[key] = ln[key]
                    lines.append(rec)
                census[f] = {"lines": lines}
            if per is None and nf - tail - lead >= 2:
                programmatic[pos] = (off + lead, off + nf - tail - 1, kind, s.get("index", pos + 1))
            elif per is None:
                no("in a programmatic scene too short to settle between its seams (%s)" % kind, max(0, nf - 1))
            off += nf
    finally:
        if chrome is not None:
            chrome.close()
        for p in temp_pages:
            try:
                os.remove(p)
            except OSError:
                pass
    # THE PROGRAMMATIC SCENES, on their settled span (E18: a structure the census cannot read is handed to the pixels,
    # not skipped): their tiles are truly still there, so a pop or a shimmer is judged; the reveal before it is not
    settled = settled_scenes(video, {p: (a, b) for p, (a, b, _k, _i) in programmatic.items()})
    floor = cap_top if cap_top is not None else H          # below it: the burned caption (overlay, or its band)
    for pos, (a, b, kind, idx) in programmatic.items():
        f0, tiles = settled[pos]
        tiles = [t for t in tiles if t[3] <= floor]
        if a < f0:
            no("in the reveal of a programmatic scene (%s): drawn by PIL at whole pixels, no geometry to read" % kind,
               f0 - a)
        for f in range(f0, b + 1):
            census[f] = {"lines": [{"k": "s%02d/settled%d" % (idx, n), "t": "settled tile %d" % n,
                                    "x": float(t[0]), "y": float(t[1]), "w": float(t[2] - t[0]),
                                    "h": float(t[3] - t[1]), "o": 1, "b": pos} for n, t in enumerate(tiles)]}
        if b + 1 - f0 < 6:
            not_judged.append("%02d %s (settled for only %d frames)" % (idx, kind, b + 1 - f0))
        else:
            judged_scenes.append(idx)
            scope.append("scene %02d (%s, programmatic): judged on its settled span, frames %d-%d, as still tiles; "
                         "its reveal (%d frames) is not" % (idx, kind, f0, b, f0 - a))
    scope.append("geometry: %d scene(s) read (html pages from their own DOM on the capture plan; image slides from "
                 "their Ken Burns move), scene lengths from %s%s%s" % (
                     len(judged_scenes), how, "; platform-safe frame mapped" if safe else "",
                     "; reduced motion (pages censused with reduced-motion.css)" if meta.get("reduced_motion") else ""))
    if not_judged:
        scope.append("NOT judged — programmatic scene(s) %s: drawn by PIL at whole pixels, no geometry to read, and "
                     "no settled span long enough to judge" % ", ".join(not_judged))
    return census, skip, scope
