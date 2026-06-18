"""storyboard.json -> out.mp4 (+ out.srt). ffmpeg-direct, no moviepy.

Captions are burned in with PIL (a bundled font), composited as an overlay
*after* zoompan so they stay fixed while the slide gently zooms. This avoids
any dependency on an ffmpeg built with libass.
"""
import argparse, os, re, tempfile
from PIL import Image, ImageDraw, ImageFont
import _common
import storyboard as sb

BUNDLED_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "assets", "fonts", "DejaVuSans.ttf")

# The bundled Latin font (DejaVuSans) has no CJK glyphs, so Chinese/Japanese/Korean
# captions render as tofu boxes unless we swap to a system font that covers the script.
_HAN = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_KANA = "\u3040-\u30ff"
_HANGUL = "\uac00-\ud7a3\u1100-\u11ff"
_CJK_PUNCT = "\u3000-\u303f\uff00-\uffef"
_CJK = _HAN + _KANA + _HANGUL + _CJK_PUNCT
_CJK_RE = re.compile(f"[{_CJK}]")

# macOS system fonts with CJK coverage, keyed by detected script. First existing wins.
_FONT_CANDIDATES = {
    "ja": ["/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
           "/System/Library/Fonts/Hiragino Sans GB.ttc"],
    "ko": ["/System/Library/Fonts/AppleSDGothicNeo.ttc"],
    "zh": ["/System/Library/Fonts/PingFang.ttc",
           "/System/Library/Fonts/Hiragino Sans GB.ttc"],
}
_FONT_FALLBACKS = ["/System/Library/Fonts/PingFang.ttc",
                   "/System/Library/Fonts/Hiragino Sans GB.ttc",
                   "/System/Library/Fonts/AppleSDGothicNeo.ttc",
                   "/Library/Fonts/Arial Unicode.ttf"]

def _script_of(text, language="auto"):
    """Best-guess script of the caption text. Han is shared across zh/ja/ko, so the
    declared `language` breaks the tie when only Han chars are present."""
    if re.search(f"[{_KANA}]", text):
        return "ja"
    if re.search(f"[{_HANGUL}]", text):
        return "ko"
    if re.search(f"[{_HAN}{_CJK_PUNCT}]", text):
        lang = (language or "").lower()
        if lang.startswith("ja"):
            return "ja"
        if lang.startswith("ko"):
            return "ko"
        return "zh"
    return "latin"

def _font_path(meta, text):
    """Resolve the caption font: an explicit meta.font override, else a system CJK font
    when the text needs one, else the bundled Latin font."""
    explicit = (meta or {}).get("font")
    if explicit and os.path.exists(explicit):
        return explicit
    script = _script_of(text or "", (meta or {}).get("language", "auto"))
    if script != "latin":
        for p in _FONT_CANDIDATES.get(script, []) + _FONT_FALLBACKS:
            if os.path.exists(p):
                return p
    return BUNDLED_FONT

_FONT_CACHE = {}
def _load_font(size, path=None):
    path = path or BUNDLED_FONT
    key = (path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except Exception:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def _canvas(meta, vertical):
    if vertical:
        return 1080, 1920
    return meta.get("width", 1920), meta.get("height", 1080)

def _fit_frame(src, dst, W, H):
    """Scale-and-pad a slide image onto a WxH canvas (letterbox)."""
    im = Image.open(src).convert("RGB")
    im.thumbnail((W, H), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), (0, 0, 0))
    bg.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    bg.save(dst)

def _atoms(text):
    """Break text into wrap units: each CJK character is its own unit (CJK has no
    spaces, so a line may break between any two characters), while runs of non-CJK
    non-space characters stay together as Latin 'words'. Whitespace is dropped here and
    re-inserted on join only between two Latin words."""
    return re.findall(f"[{_CJK}]|[^{_CJK}\\s]+", text)

def _wrap(d, text, font, max_w):
    """Greedy wrap to a max pixel width. Latin words join with a space; CJK characters
    join tight and may break anywhere — so Chinese/Japanese/Korean captions wrap instead
    of overflowing as one un-splittable line (which `text.split()` alone produced)."""
    lines, cur = [], ""
    for a in _atoms(text):
        if not cur:
            trial = a
        elif _CJK_RE.match(a) or _CJK_RE.match(cur[-1]):
            trial = cur + a            # no space when either side is CJK
        else:
            trial = cur + " " + a      # space between two Latin words
        if not cur or d.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur); cur = a
    if cur:
        lines.append(cur)
    return lines

def _draw_caption(d, text, W, H, meta=None):
    """Burn a centered caption bar near the bottom (fixed, doesn't zoom)."""
    if not text:
        return
    font = _load_font(int(H * 0.045), _font_path(meta, text))
    margin = int(H * 0.06)
    pad = int(H * 0.012)
    lines = _wrap(d, text, font, int(W * 0.9))
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    block_h = line_h * len(lines) + pad * 2
    y0 = H - margin - block_h
    d.rectangle([0, y0, W, y0 + block_h], fill=(0, 0, 0, 140))
    y = y0 + pad
    for ln in lines:
        w = d.textlength(ln, font=font)
        d.text(((W - w) / 2, y), ln, font=font, fill=(255, 255, 255, 255))
        y += line_h

def _callout_layer(callouts, W, H, dst, meta=None):
    """Draw ONLY the callouts onto a transparent PNG (shown for the whole slide)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for co in callouts or []:
        x0, y0, x1, y1 = co["box"]
        box = [x0 * W, y0 * H, x1 * W, y1 * H]
        if co.get("style") == "highlight":
            d.rectangle(box, fill=(255, 230, 0, 60), outline=(255, 200, 0, 230), width=4)
        else:  # box / arrow target
            d.rectangle(box, outline=(255, 60, 60, 240), width=5)
        if co.get("label"):
            label_font = _load_font(int(H * 0.028), _font_path(meta, co["label"]))
            d.text((box[0] + 6, max(0, box[1] - 30)), co["label"],
                   font=label_font, fill=(255, 255, 255, 255))
    layer.save(dst)

def _caption_layer(text, W, H, dst, meta=None):
    """Draw ONLY one caption block onto a transparent PNG (shown for one time window)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _draw_caption(ImageDraw.Draw(layer), text, W, H, meta)
    layer.save(dst)

def _srt_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

# sentence / clause boundaries. CJK punctuation (。！？，、：) carries NO trailing space, so
# we break right after it. Latin punctuation (.!?,:) breaks only when followed by whitespace
# or end-of-text — otherwise a decimal like "1.77" or "$1.5M" would split mid-number, and a
# CJK-only "ender + whitespace" rule would leave a whole Chinese paragraph as one caption.
_CJK_ENDERS = "。！？…"
_LATIN_ENDERS = ".!?"
_CJK_CLAUSES = "，、：；"
_LATIN_CLAUSES = ",:;"

def _segment(text, cjk_marks, latin_marks):
    """Split into pieces ending at a boundary mark (kept attached). CJK marks break
    unconditionally; Latin marks break only before whitespace/EOL so numbers stay intact."""
    t = re.sub(rf"([{cjk_marks}])", "\\1\x00", text)
    t = re.sub(rf"([{latin_marks}])(\s+|$)", "\\1\x00\\2", t)
    return [p.strip() for p in t.split("\x00") if p.strip()]

def _split_caption_chunks(text, max_len=84):
    """Split narration into readable, subtitle-sized chunks: first on sentence enders,
    then break any over-long sentence on commas/colons so a chunk fits 1-2 lines.
    CJK uses a tighter char limit because each glyph is full-width — the Latin limit would
    still render as a wall of text on screen."""
    text = (text or "").strip()
    if not text:
        return []
    limit = 34 if _CJK_RE.search(text) else max_len
    chunks = []
    for s in _segment(text, _CJK_ENDERS, _LATIN_ENDERS):
        if len(s) <= limit:
            chunks.append(s); continue
        cur = ""
        for piece in _segment(s, _CJK_CLAUSES, _LATIN_CLAUSES):
            if cur and len(cur) + len(piece) > limit:
                chunks.append(cur); cur = piece
            elif cur:
                # join CJK tight (no space); Latin words keep a separating space
                cur = cur + piece if _CJK_RE.search(cur[-1]) else cur + " " + piece
            else:
                cur = piece
        if cur:
            chunks.append(cur)
    return chunks

def _captions_for(slide):
    """Timed caption segments that TRACK THE NARRATION as it's spoken. If the slide
    provides an explicit multi-segment `captions` track, honour it. Otherwise split the
    narration into subtitle chunks and time them across the slide's audio duration,
    weighted by length (longer sentences take proportionally longer to say) — an
    approximate but well-synced subtitle, far better than one static line per slide."""
    caps = slide.get("captions") or []
    if len(caps) >= 2:                       # author-provided timed track wins
        return caps
    dur = float(slide.get("duration") or 0)
    chunks = _split_caption_chunks(slide.get("narration") or (caps[0]["text"] if caps else ""))
    if not chunks or dur <= 0:
        return []
    weights = [max(1, len(c)) for c in chunks]
    total = sum(weights)
    segs, t = [], 0.0
    for c, w in zip(chunks, weights):
        seg = dur * (w / total)
        segs.append({"start": round(t, 3), "end": round(min(dur, t + seg), 3), "text": c})
        t += seg
    segs[-1]["end"] = round(dur, 3)
    return segs

def _write_srt(data, path):
    idx = 1; t0 = 0.0
    lines = []
    for s in data["slides"]:
        for c in _captions_for(s):
            lines.append(str(idx))
            lines.append(f"{_srt_time(t0 + c['start'])} --> {_srt_time(t0 + c['end'])}")
            lines.append(c["text"]); lines.append(""); idx += 1
        t0 += s["duration"]
    with open(path, "w") as f:
        f.write("\n".join(lines))

def _fingerprint(slide, meta, W, H, ss, burn, vertical):
    """A short hash of everything that affects a slide's rendered clip, so a re-render can
    skip slides that didn't change (the cache key). Includes the image/audio file
    mtime+size, so regenerating the deck or TTS invalidates the cached clip."""
    import hashlib, json
    def stat(rel):
        p = os.path.join(meta["_out"], rel or "")
        try:
            return [os.path.getmtime(p), os.path.getsize(p)]
        except OSError:
            return None
    payload = json.dumps({
        "s": {k: slide.get(k) for k in
              ("image", "audio", "duration", "motion", "narration", "captions", "callouts",
               "type", "props")},
        "r": [W, H, meta.get("fps", 30), ss, burn, vertical,
              meta.get("language", "auto"), meta.get("font")],
        "img": stat(slide.get("image")), "aud": stat(slide.get("audio")),
    }, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode()).hexdigest()[:16]

def _encode_frames_clip(pattern, audio_rel, dur, caption_segs, meta, W, H, out_clip, workdir):
    """Encode a per-frame PNG sequence + the scene's TTS audio (+ timed captions) into a
    clip using the SAME codec params as the slide path, so the '-c copy' concat still works."""
    fps = meta.get("fps", 30)
    parts = [f"[0:v]scale={W}:{H}[v0]"]               # frames are already WxH; scale = safety
    vlabel = "v0"; extra_inputs = []; n_in = 2        # 0=frames, 1=audio
    for k, seg in enumerate(caption_segs):
        if not (seg.get("text") or "").strip():
            continue
        cap_png = os.path.join(workdir, f"scap_{k:03d}.png")
        _caption_layer(seg["text"], W, H, cap_png, meta)
        extra_inputs += ["-i", cap_png]
        en = f"between(t,{seg['start']},{seg['end']})"
        parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0:enable='{en}'[v{n_in}]")
        vlabel = f"v{n_in}"; n_in += 1
    cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", pattern,
           "-i", os.path.join(meta["_out"], audio_rel)] + extra_inputs + [
        "-filter_complex", ";".join(parts), "-map", f"[{vlabel}]", "-map", "1:a",
        "-t", f"{dur}", "-r", str(fps), "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", out_clip]
    _common.run(cmd)
    return out_clip

def _render_scene(slide, meta, W, H, out_clip, burn_captions, workdir):
    import scenes
    fps = meta.get("fps", 30)
    dur = slide["duration"]
    frames = max(1, int(round(dur * fps)))
    renderer = getattr(scenes, "render_" + slide["type"])   # render_title / render_chart / render_timeline
    pattern = renderer(slide.get("props") or {}, meta, W, H, frames, workdir, slide["index"])
    segs = _captions_for(slide) if burn_captions else []
    return _encode_frames_clip(pattern, slide["audio"], dur, segs, meta, W, H, out_clip, workdir)

def _render_slide(slide, meta, W, H, out_clip, burn_captions, workdir):
    if slide.get("type", "slide") != "slide":
        return _render_scene(slide, meta, W, H, out_clip, burn_captions, workdir)
    i = slide["index"]
    frame = os.path.join(workdir, f"fit_{i:02d}.png")
    _fit_frame(os.path.join(meta["_out"], slide["image"]), frame, W, H)
    fps = meta.get("fps", 30)
    dur = slide["duration"]
    frames = max(1, int(round(dur * fps)))
    m = slide["motion"]
    fx, fy, z0 = m["from"]; tx, ty, z1 = m["to"]
    zexpr = f"{z0}+({z1}-{z0})*on/{frames}"
    # x/y are normalized pan anchors in 0..1 (0.5 = centered); map each to the crop
    # window's top-left so the chosen point stays put as we zoom in.
    xpan = f"{fx}+({tx}-{fx})*on/{frames}"
    ypan = f"{fy}+({ty}-{fy})*on/{frames}"
    # Anti-jitter: run zoompan in a SUPERSAMPLED space then scale back down. zoompan floors
    # its crop x/y to whole *input* pixels, so at native size every step is a full output
    # pixel = visible 'shivering'. Working at ss× makes each step 1/ss of an output pixel and
    # the final downscale anti-aliases it away. A `scale` filter MUST precede zoompan (a
    # looped image fed straight in makes zoompan mis-place/shrink the frame).
    ss = max(1, int(meta.get("motion_ss", 2)))    # 2 = smooth + practical; raise to 3 if needed
    bw, bh = W * ss, H * ss
    vf = (f"scale={bw}:{bh}:flags=lanczos,"
          f"zoompan=z='{zexpr}'"
          f":x='(iw-iw/zoom)*({xpan})':y='(ih-ih/zoom)*({ypan})'"
          f":d={frames}:s={bw}x{bh}:fps={fps},"
          f"scale={W}:{H}:flags=lanczos")

    # Overlays, in order: one static callout layer (whole slide) + one caption layer per
    # narration segment, each enabled only during its spoken window — so the subtitle
    # changes WITH the narration instead of showing one fixed line per slide.
    parts = [f"[0:v]{vf}[v0]"]
    vlabel = "v0"
    extra_inputs = []
    n_in = 2                                        # 0=frame(loop), 1=audio
    if slide.get("callouts"):
        co_png = os.path.join(workdir, f"co_{i:02d}.png")
        _callout_layer(slide.get("callouts"), W, H, co_png, meta)
        extra_inputs += ["-i", co_png]
        parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0[v{n_in}]"); vlabel = f"v{n_in}"; n_in += 1
    if burn_captions:
        for k, seg in enumerate(_captions_for(slide)):
            if not (seg.get("text") or "").strip():
                continue
            cap_png = os.path.join(workdir, f"cap_{i:02d}_{k:02d}.png")
            _caption_layer(seg["text"], W, H, cap_png, meta)
            extra_inputs += ["-i", cap_png]
            en = f"between(t,{seg['start']},{seg['end']})"
            parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0:enable='{en}'[v{n_in}]")
            vlabel = f"v{n_in}"; n_in += 1
    fcomplex = ";".join(parts)

    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", frame, "-i",
           os.path.join(meta["_out"], slide["audio"])] + extra_inputs + [
        "-filter_complex", fcomplex, "-map", f"[{vlabel}]", "-map", "1:a",
        "-t", f"{dur}", "-r", str(fps), "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", out_clip]
    _common.run(cmd)
    return out_clip

def render(out_dir, sample=None, vertical=False, only=None):
    data = sb.load(os.path.join(out_dir, "storyboard.json"))
    sb.validate(data)
    meta = data["meta"]; meta["_out"] = out_dir
    W, H = _canvas(meta, vertical)
    burn = bool(meta.get("captions", True))
    ss = max(1, int(meta.get("motion_ss", 2)))

    def _need_av(s):
        if not s.get("audio") or not s.get("duration"):
            raise sb.StoryboardError(f"slide {s['index']} missing audio/duration; run tts.py first")

    # SAMPLE: one slide, throwaway tempdir.
    if sample is not None:
        s = next(x for x in data["slides"] if x["index"] == sample)
        _need_av(s)
        with tempfile.TemporaryDirectory() as wd:
            clip = _render_slide(s, meta, W, H, os.path.join(wd, "s.mp4"), burn, wd)
            dst = os.path.join(out_dir, "sample.mp4")
            _common.run(["ffmpeg", "-y", "-i", clip, "-c", "copy", dst])
            return dst

    # FULL render with a per-slide CLIP CACHE: only slides whose fingerprint changed are
    # re-rendered; the rest are reused, so iterating on a few slides is fast. `--only N`
    # forces slide N to re-render regardless of cache.
    clipdir = os.path.join(out_dir, ".clips")
    os.makedirs(clipdir, exist_ok=True)
    clips, rendered = [], 0
    with tempfile.TemporaryDirectory() as wd:
        for s in data["slides"]:
            clip = os.path.join(clipdir, f"clip_{s['index']:02d}.mp4")
            keyf = clip + ".key"
            key = _fingerprint(s, meta, W, H, ss, burn, vertical)
            force = (only is not None and s["index"] == only)
            cached = (not force and os.path.exists(clip) and os.path.exists(keyf)
                      and open(keyf).read().strip() == key)
            if not cached:
                _need_av(s)
                _render_slide(s, meta, W, H, clip, burn, wd)
                with open(keyf, "w") as f:
                    f.write(key)
                rendered += 1
            clips.append(clip)
        listfile = os.path.join(wd, "list.txt")
        with open(listfile, "w") as f:
            for c in clips:
                f.write(f"file '{os.path.abspath(c)}'\n")
        dst = os.path.join(out_dir, "out.mp4")
        _common.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
                     "-c", "copy", dst])
        _write_srt(data, os.path.join(out_dir, "out.srt"))
        print(f"({rendered} slide(s) rendered, {len(clips) - rendered} reused from cache)")
        return dst

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--vertical", action="store_true")
    a = ap.parse_args()
    res = render(a.out_dir, sample=a.sample, vertical=a.vertical, only=a.only)
    print(f"Rendered -> {res}")

if __name__ == "__main__":
    main()
