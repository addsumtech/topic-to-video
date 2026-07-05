"""storyboard.json -> out.mp4 (+ out.srt). ffmpeg-direct, no moviepy.

Captions are burned in with PIL (a bundled font), composited as an overlay
*after* zoompan so they stay fixed while the slide gently zooms. This avoids
any dependency on an ffmpeg built with libass.
"""
import argparse, json, os, re, tempfile, time
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

def _fit_frame(src, dst, W, H, fit="contain"):
    """Scale a slide image onto a WxH canvas. contain = letterbox (default); cover = scale to
    fill then center-crop (full-frame, for AI b-roll)."""
    im = Image.open(src).convert("RGB")
    if fit == "cover":
        scale = max(W / im.width, H / im.height)
        nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
        im = im.resize((nw, nh), Image.LANCZOS)
        left, top = (nw - W) // 2, (nh - H) // 2
        im.crop((left, top, left + W, top + H)).save(dst)
        return
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

KARAOKE_HL = (255, 209, 102, 255)   # warm gold — reads clearly on the dark caption bar

def _caption_font_px(W, H):
    """Caption size scales with the NARROW dimension, not height: H-relative sizing balloons to
    ~86px on a 9:16 canvas (double the landscape weight in half the width — 3-line wraps, widows,
    and the band eats the layout). min(W,H)*0.045 keeps the same visual weight in both aspects."""
    return int(min(W, H) * 0.045)

def _draw_caption(d, text, W, H, meta=None, hl_word=None):
    """Burn a centered caption bar near the bottom (fixed, doesn't zoom). If `hl_word` (a whitespace
    word index) is given, that word is drawn in the karaoke highlight colour (space-delimited text)."""
    if not text:
        return
    font = _load_font(_caption_font_px(W, H), _font_path(meta, text))
    margin = int(H * 0.06)
    pad = int(H * 0.012)
    lines = _wrap(d, text, font, int(W * 0.9))
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    block_h = line_h * len(lines) + pad * 2
    y0 = H - margin - block_h
    d.rectangle([0, y0, W, y0 + block_h], fill=(0, 0, 0, 140))
    y = y0 + pad
    if hl_word is None:
        for ln in lines:
            w = d.textlength(ln, font=font)
            d.text(((W - w) / 2, y), ln, font=font, fill=(255, 255, 255, 255))
            y += line_h
        return
    # word-aware: draw each wrapped line word-by-word, colouring the global hl_word index
    gi = 0
    space = d.textlength(" ", font=font)
    for ln in lines:
        words = ln.split(" ")
        lw = sum(d.textlength(w, font=font) for w in words) + space * (len(words) - 1)
        x = (W - lw) / 2
        for w in words:
            col = KARAOKE_HL if gi == hl_word else (255, 255, 255, 255)
            d.text((x, y), w, font=font, fill=col)
            x += d.textlength(w, font=font) + space
            gi += 1
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

def _caption_layer(text, W, H, dst, meta=None, hl_word=None):
    """Draw ONLY one caption block onto a transparent PNG (shown for one time window)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _draw_caption(ImageDraw.Draw(layer), text, W, H, meta, hl_word)
    layer.save(dst)

def _load_words(out_dir, index):
    """Per-word timings from edge-tts (audio/NN.words.json), or None."""
    try:
        return json.load(open(os.path.join(out_dir, "audio", f"{index:02d}.words.json")))
    except (OSError, ValueError, TypeError):
        return None

def _callout_time(slide, meta, co, dur, out_dir):
    """C3 — absolute appearance time (seconds) for a TIMED callout: an explicit `at` fraction
    (0..1) wins; else resolve its `cue` anchor phrase against the narration via edge word-timings
    (audio/NN.words.json) or, lacking those, the text-position estimate (same paths the HTML
    reveals use). Returns 0.0 for an untimed callout (shows for the whole slide, as before)."""
    if "at" in co:
        try:
            return max(0.0, min(float(dur), float(co["at"]) * float(dur)))
        except (TypeError, ValueError):
            return 0.0
    anchor = co.get("cue")
    if not anchor:
        return 0.0
    import cues as _cues
    words = _load_words(out_dir, slide.get("index") or 0)
    try:
        if words:
            times = _cues.resolve_cues(words, [anchor])
        else:
            times = _cues.estimate_cues_from_text([anchor], slide.get("narration") or "", float(dur))
        return max(0.0, min(float(dur), float(times[0]))) if times else 0.0
    except Exception:
        return 0.0

def _caption_karaoke_segs(slide, meta, out_dir):
    """Per-WORD caption overlays (active word highlighted), timed by the real edge-tts word times.
    Each caption CHUNK's on-screen window and its words come straight from words.json, so the
    highlight tracks the voice exactly. Returns None when karaoke can't apply (off / CJK / no
    words.json / empty) — the caller then uses the chunk-level captions."""
    if (meta or {}).get("captions_karaoke", "auto") in ("off", False):
        return None
    lang = ((meta or {}).get("language", "") or "").lower().split("-")[0]
    if lang in ("zh", "ja", "ko"):        # per-word highlight of gap-less CJK is awkward — chunk-level instead
        return None
    words = _load_words(out_dir, slide.get("index") or 0)
    dur = float(slide.get("duration") or 0)
    if not words or dur <= 0:
        return None
    chunks = _captions_for(slide)         # reuse the chunking (text/lines); re-time from real word starts
    chunk_words = [c["text"].split() for c in chunks]
    flat = [w for cw in chunk_words for w in cw]
    if not flat:
        return None
    import cues as _cues
    times = _cues.resolve_cues(words, flat)     # one monotonic time per display word
    if len(times) != len(flat):
        return None
    segs, gi, last = [], 0, len(flat) - 1
    for c, cw in zip(chunks, chunk_words):
        for j in range(len(cw)):
            start = times[gi]
            end = times[gi + 1] if gi < last else dur
            if end <= start:
                end = start + 0.08
            segs.append({"start": round(start, 3), "end": round(end, 3), "text": c["text"], "hl": j})
            gi += 1
    return segs or None

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
    unconditionally; Latin marks break before whitespace/EOL OR a following CJK glyph — so a
    comma/colon authored in ASCII *inside* Chinese text ("提取,公式") still splits, while a
    decimal like "1.77" or "1,000" (mark between digits) stays intact."""
    t = re.sub(rf"([{cjk_marks}])", "\\1\x00", text)
    t = re.sub(rf"([{latin_marks}])(?=\s|$|[{_CJK}])", "\\1\x00", t)
    return [p.strip() for p in t.split("\x00") if p.strip()]

# trailing clause punctuation looks cut-off at a caption line break — strip it from each chunk
_TRAIL_CLAUSE = "，、：；,;:　 "

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
                # join tight when either side is CJK (Chinese sets no space, even after an
                # ASCII comma); only two Latin pieces keep a separating space
                tight = _CJK_RE.search(cur[-1]) or _CJK_RE.search(piece[0])
                cur = cur + piece if tight else cur + " " + piece
            else:
                cur = piece
        if cur:
            chunks.append(cur)
    # a chunk ending on a clause mark (","/"、"/":") reads as cut-off at the line break — trim it
    return [c.rstrip(_TRAIL_CLAUSE) for c in chunks if c.rstrip(_TRAIL_CLAUSE)]

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
        # rel may be None (e.g. an html scene has no `image`). Must return None then — NOT stat
        # `os.path.join(out, "")` == the OUTPUT DIR, whose mtime changes on every render (new
        # logs/clips/srt). That made every image-less (html) scene's fingerprint unstable, so the
        # clip cache NEVER hit and every render re-did all html scenes. The guard is the fix.
        if not rel:
            return None
        p = os.path.join(meta["_out"], rel)
        try:
            return [os.path.getmtime(p), os.path.getsize(p)]
        except OSError:
            return None
    payload = json.dumps({
        "s": {k: slide.get(k) for k in
              ("image", "audio", "duration", "motion", "narration", "captions", "callouts",
               "type", "props", "fit", "transition", "transition_seconds")},
        "r": [W, H, meta.get("fps", 30), ss, burn, vertical,
              meta.get("language", "auto"), meta.get("font"),
              meta.get("transition", "dip"), meta.get("transition_seconds", 0.2),
              meta.get("captions_karaoke", "auto"), meta.get("reduced_motion", False), "x264crf18"],
        "img": stat(slide.get("image")), "aud": stat(slide.get("audio")),
        "html": stat((slide.get("props") or {}).get("html")),
        # re-theming (theme.py) busts ALL clips — html pages link theme.css AND the programmatic
        # renderers parse the same vars (one color world)
        "theme": stat("theme.css"),
        # per-word cue timings matter to html scenes AND any slide whose timed callout carries a
        # `cue` (resolved against words.json) — gate on that so a TTS re-run doesn't spuriously
        # bust every other static slide's cached clip
        "words": (stat(os.path.join("audio", f"{(slide.get('index') or 0):02d}.words.json"))
                  if (slide.get("type") == "html"
                      or any(c.get("cue") for c in slide.get("callouts") or [])) else None),
    }, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode()).hexdigest()[:16]

def _theme_bg(out_dir):
    """The deck's background colour (for transition dips) as ffmpeg 0xRRGGBB — from theme.css --bg,
    else the base dark default. A dip through the deck's OWN bg reads as the stage briefly clearing,
    seamless on any theme (fading to black would flash on a light deck)."""
    try:
        m = re.search(r"--bg\s*:\s*#([0-9a-fA-F]{3,6})", open(os.path.join(out_dir, "theme.css")).read())
        if m:
            h = m.group(1)
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            return "0x" + h.lower()
    except OSError:
        pass
    return "0x0d1117"

def _motion_exprs(m, frames, reduced_motion=False):
    """The zoompan z / x-pan / y-pan expressions for a slide's Ken Burns move. With reduced_motion,
    force to==from so every expression is constant (a static frame — no zoom/pan)."""
    fx, fy, z0 = m["from"]; tx, ty, z1 = m["to"]
    if reduced_motion:
        tx, ty, z1 = fx, fy, z0
    return (f"{z0}+({z1}-{z0})*on/{frames}",
            f"{fx}+({tx}-{fx})*on/{frames}",
            f"{fy}+({ty}-{fy})*on/{frames}")

def _fade_filter(meta, dur, slide=None):
    """A gentle dip-to-bg at both clip edges (video only — audio + duration untouched, so the
    per-clip cache, `-c copy` concat and A/V gate all still hold). '' when transitions are off or
    the clip is too short to dip. A SLIDE-level `transition` / `transition_seconds` overrides the
    meta default — that's how the section-aware rhythm is authored (hard cut inside a section,
    dip at a seam, a longer dip into the climax/closer; see motion-grammar.md "Transition rhythm").
    Values: 'dip' (both edges) | 'in' | 'out' (one edge) | 'none'; seconds default 0.2."""
    s = slide or {}
    t = s.get("transition")
    if t not in ("dip", "in", "out", "none"):    # unknown/absent -> the meta default (validate warns)
        t = (meta or {}).get("transition", "dip")
    if t == "none":
        return ""
    d = s.get("transition_seconds")
    d = float(d if d is not None else (meta or {}).get("transition_seconds", 0.2))
    if d <= 0 or dur <= 2.2 * d:
        return ""
    bg = _theme_bg(meta.get("_out", "."))
    parts = []
    if t in ("dip", "in"):      # "in": dip only on this clip's opening edge (seam-opener / climax)
        parts.append(f"fade=t=in:st=0:d={d}:c={bg}")
    if t in ("dip", "out"):     # "out": dip only on the closing edge (section-ender before a seam)
        parts.append(f"fade=t=out:st={dur - d:.3f}:d={d}:c={bg}")
    return ",".join(parts)

def _encode_frames_clip(pattern, audio_rel, dur, caption_segs, meta, W, H, out_clip, workdir, slide=None):
    """Encode a per-frame PNG sequence + the scene's TTS audio (+ timed captions) into a
    clip using the SAME codec params as the slide path, so the '-c copy' concat still works.
    Audio is pinned to a uniform rate (-ar 48000 -ac 1): scenes can come from different audio
    sources (edge .mp3 @24000 vs say .aiff @22050 in a partial-fallback run), and concatenating
    clips with mismatched sample rates via '-c copy' silently desyncs (the demuxer reinterprets
    all audio at the first clip's rate, inflating the audio stream) — normalizing here prevents it."""
    fps = meta.get("fps", 30)
    parts = [f"[0:v]scale={W}:{H}[v0]"]               # frames are already WxH; scale = safety
    vlabel = "v0"; extra_inputs = []; n_in = 2        # 0=frames, 1=audio
    for k, seg in enumerate(caption_segs):
        if not (seg.get("text") or "").strip():
            continue
        cap_png = os.path.join(workdir, f"scap_{k:03d}.png")
        _caption_layer(seg["text"], W, H, cap_png, meta, hl_word=seg.get("hl"))
        extra_inputs += ["-i", cap_png]
        en = f"between(t,{seg['start']},{seg['end']})"
        parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0:enable='{en}'[v{n_in}]")
        vlabel = f"v{n_in}"; n_in += 1
    fade = _fade_filter(meta, dur, slide)              # dip-to-bg transition at the clip edges
    if fade:
        parts.append(f"[{vlabel}]{fade}[vfade]"); vlabel = "vfade"
    cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", pattern,
           "-i", os.path.join(meta["_out"], audio_rel)] + extra_inputs + [
        "-filter_complex", ";".join(parts), "-map", f"[{vlabel}]", "-map", "1:a",
        "-t", f"{dur}", "-r", str(fps), "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-ar", "48000", "-ac", "1", "-shortest", out_clip]
    _common.run(cmd)
    return out_clip

def _render_scene(slide, meta, W, H, out_clip, burn_captions, workdir):
    import scenes
    fps = meta.get("fps", 30)
    dur = slide["duration"]
    frames = max(1, int(round(dur * fps)))
    renderer = getattr(scenes, "render_" + slide["type"])   # render_title / render_chart / render_timeline
    # expose this scene's narration so render_html can estimate reveal cues from text position when
    # there are no per-word timings (non-edge voices). Scenes render sequentially, so this is safe.
    meta["_narration"] = slide.get("narration") or ""
    pattern = renderer(slide.get("props") or {}, meta, W, H, frames, workdir, slide["index"])
    segs = ((_caption_karaoke_segs(slide, meta, meta["_out"]) or _captions_for(slide))
            if burn_captions else [])
    return _encode_frames_clip(pattern, slide["audio"], dur, segs, meta, W, H, out_clip, workdir, slide=slide)

def _render_slide(slide, meta, W, H, out_clip, burn_captions, workdir):
    if slide.get("type", "slide") != "slide":
        return _render_scene(slide, meta, W, H, out_clip, burn_captions, workdir)
    i = slide["index"]
    if (slide.get("image_prompt") or "").strip() and not slide.get("image"):
        raise sb.StoryboardError(f"slide {i}: image_prompt set but image not generated — run imagegen.py first")
    frame = os.path.join(workdir, f"fit_{i:02d}.png")
    _fit_frame(os.path.join(meta["_out"], slide["image"]), frame, W, H, slide.get("fit", "contain"))
    fps = meta.get("fps", 30)
    dur = slide["duration"]
    frames = max(1, int(round(dur * fps)))
    m = slide["motion"]
    # x/y are normalized pan anchors in 0..1 (0.5 = centered); map each to the crop
    # window's top-left so the chosen point stays put as we zoom in.
    zexpr, xpan, ypan = _motion_exprs(m, frames, meta.get("reduced_motion"))
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
        cos = slide["callouts"]
        # C3 — a callout with `cue`/`at` is TIMED: it appears when its region is spoken and holds
        # to the clip end (a vanishing highlight reads as a glitch). Untimed callouts stay on one
        # shared static layer (unchanged). The Ken Burns camera is NOT re-aimed mid-clip.
        static_cos = [c for c in cos if not c.get("cue") and "at" not in c]
        timed_cos = [c for c in cos if c.get("cue") or "at" in c]
        if static_cos:
            co_png = os.path.join(workdir, f"co_{i:02d}.png")
            _callout_layer(static_cos, W, H, co_png, meta)
            extra_inputs += ["-i", co_png]
            parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0[v{n_in}]"); vlabel = f"v{n_in}"; n_in += 1
        for j, co in enumerate(timed_cos):
            t0 = _callout_time(slide, meta, co, dur, meta["_out"])
            tco_png = os.path.join(workdir, f"tco_{i:02d}_{j:02d}.png")
            _callout_layer([co], W, H, tco_png, meta)
            extra_inputs += ["-i", tco_png]
            en = f"between(t,{t0:.3f},{dur})"
            parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0:enable='{en}'[v{n_in}]")
            vlabel = f"v{n_in}"; n_in += 1
    if burn_captions:
        segs = _caption_karaoke_segs(slide, meta, meta["_out"]) or _captions_for(slide)
        for k, seg in enumerate(segs):
            if not (seg.get("text") or "").strip():
                continue
            cap_png = os.path.join(workdir, f"cap_{i:02d}_{k:02d}.png")
            _caption_layer(seg["text"], W, H, cap_png, meta, hl_word=seg.get("hl"))
            extra_inputs += ["-i", cap_png]
            en = f"between(t,{seg['start']},{seg['end']})"
            parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0:enable='{en}'[v{n_in}]")
            vlabel = f"v{n_in}"; n_in += 1
    fade = _fade_filter(meta, dur, slide)              # dip-to-bg transition at the clip edges
    if fade:
        parts.append(f"[{vlabel}]{fade}[vfade]"); vlabel = "vfade"
    fcomplex = ";".join(parts)

    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", frame, "-i",
           os.path.join(meta["_out"], slide["audio"])] + extra_inputs + [
        "-filter_complex", fcomplex, "-map", f"[{vlabel}]", "-map", "1:a",
        "-t", f"{dur}", "-r", str(fps), "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-ar", "48000", "-ac", "1", "-shortest", out_clip]
    _common.run(cmd)
    return out_clip

def render(out_dir, sample=None, vertical=False, only=None, reduced_motion=False):
    data = sb.load(os.path.join(out_dir, "storyboard.json"))
    sb.validate(data)
    meta = data["meta"]; meta["_out"] = out_dir
    # D — reduced-motion tier (accessibility): CLI flag OR meta.reduced_motion. Kills zoom/pan on the
    # image tier and swaps HTML reveals to opacity-only fades; still deterministic + seekable.
    meta["reduced_motion"] = bool(reduced_motion or meta.get("reduced_motion"))
    # meta.aspect is authoritative; the --vertical flag also forces it (either makes it 9:16).
    vertical = vertical or meta.get("aspect") == "9:16"
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
    total_scenes = len(data["slides"])
    t_all = time.monotonic()
    with tempfile.TemporaryDirectory() as wd:
        for n, s in enumerate(data["slides"], 1):
            clip = os.path.join(clipdir, f"clip_{s['index']:02d}.mp4")
            keyf = clip + ".key"
            key = _fingerprint(s, meta, W, H, ss, burn, vertical)
            force = (only is not None and s["index"] == only)
            cached = (not force and os.path.exists(clip) and os.path.exists(keyf)
                      and open(keyf).read().strip() == key)
            if cached:
                print(f"[{n}/{total_scenes}] scene {s['index']:02d} ({s.get('type','slide')}) — cached", flush=True)
            else:
                _need_av(s)
                print(f"[{n}/{total_scenes}] scene {s['index']:02d} ({s.get('type','slide')}) — rendering…", flush=True)
                t0 = time.monotonic()
                _render_slide(s, meta, W, H, clip, burn, wd)
                with open(keyf, "w") as f:
                    f.write(key)
                rendered += 1
                print(f"[{n}/{total_scenes}] scene {s['index']:02d} ✓ {time.monotonic()-t0:.1f}s", flush=True)
            clips.append(clip)
        listfile = os.path.join(wd, "list.txt")
        with open(listfile, "w") as f:
            for c in clips:
                f.write(f"file '{os.path.abspath(c)}'\n")
        dst = os.path.join(out_dir, "out.mp4")
        _common.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
                     "-c", "copy", "-movflags", "+faststart", dst])
        _write_srt(data, os.path.join(out_dir, "out.srt"))
        print(f"({rendered} slide(s) rendered, {len(clips) - rendered} reused from cache; "
              f"{time.monotonic()-t_all:.1f}s total)")
        return dst

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--vertical", action="store_true")
    ap.add_argument("--reduced-motion", action="store_true",
                    help="accessibility: no zoom/pan + opacity-only reveals (still deterministic/seekable)")
    a = ap.parse_args()
    res = render(a.out_dir, sample=a.sample, vertical=a.vertical, only=a.only,
                 reduced_motion=a.reduced_motion)
    print(f"Rendered -> {res}")

if __name__ == "__main__":
    main()
