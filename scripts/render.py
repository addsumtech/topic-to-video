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

def _wlen(s):
    """On-screen width in char-units for caption budgets. A CJK glyph is ~2.5 Latin chars wide (matching
    the skill's old 34-CJK vs 84-Latin ceilings at one budget of 84), so ONE CJK term in an English
    sentence no longer collapses the whole line to the CJK-tight limit (the old binary flip)."""
    return sum(2.5 if _CJK_RE.match(c) else 1 for c in (s or ""))

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

def _caption_font_px(W, H, band=False, meta=None):
    """Caption size scales with the NARROW dimension, not height: H-relative sizing balloons to
    ~86px on a 9:16 canvas (double the landscape weight in half the width — 3-line wraps, widows,
    and the band eats the layout). min(W,H)*0.045 keeps the same visual weight in both aspects.
    The below-content BAND uses a slightly smaller face (~0.85×) — it has its own strip, so it needn't
    shout over content; `meta.caption_scale` tunes either mode (e.g. 0.9 to shrink further)."""
    scale = (0.85 if band else 1.0) * float((meta or {}).get("caption_scale", 1.0) or 1.0)
    return max(12, int(min(W, H) * 0.045 * scale))

def _draw_caption(d, text, W, H, meta=None, hl_word=None, band=0, text_rgb=None, band_bg=None):
    """Burn a centered caption. `band==0` (default 'overlay'): NO background bar — the text sits at the very
    BOTTOM of the W×H content in the deck's `--fg` ink with a subtle opposite-luminance OUTLINE, so it reads
    over any ground (empty frame, a tint, a photo) on any theme + aspect without a heavy/ugly strip; the
    karaoke word is contrast-picked vs the frame's own `--bg`. `band>0` ('band' mode): the text is drawn centered in a dedicated
    strip BELOW the content — the region [H, H+band] on a W×(H+band) layer — so it never overlaps the
    slide (the strip's solid background is added by the render's `pad` filter; here we draw only the text
    in the deck's --bg colour over it). If `hl_word` is given, that word takes the karaoke colour —
    contrast-picked against `band_bg` (the strip ground) so it never vanishes into an accent-fill band."""
    if not text:
        return
    font = _load_font(_caption_font_px(W, H, band=bool(band), meta=meta), _font_path(meta, text))
    pad = int(H * 0.012)
    lines = _wrap(d, text, font, int(W * 0.9))
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    block_h = line_h * len(lines) + pad * 2
    if band:                                    # caption strip below the content — text only, centered in the band
        out = (meta or {}).get("_out", ".")
        # text = the per-scene sampled colour (contrasts THIS scene's strip) else the flat fallback
        base = (tuple(text_rgb) if text_rgb else _caption_band_colors(meta)[1]) + (255,)
        # the spoken word's highlight: contrast-picked against the strip GROUND (so it never blends into
        # an accent-fill band) AND kept distinct from the neighbouring words — not a blind --accent.
        bbg = tuple(band_bg) if band_bg else _ffhex_rgb(_caption_band_colors(meta)[0])
        hl_col = _karaoke_hl_rgb(out, bbg, base[:3])
        y0 = H + max(pad, (band - block_h) // 2)
        halo = None                             # the band has its own solid strip — no per-glyph outline needed
    else:                                       # overlay — NO background bar (a flat bar reads heavy/ugly, and a
        out = (meta or {}).get("_out", ".")     # theme strip still shows as a block). Draw the caption at the very
        fg = _theme_rgb(out, "--fg", (17, 17, 17))      # BOTTOM in the theme ink with a subtle contrast OUTLINE so it
        bg = _theme_rgb(out, "--bg", (244, 243, 238))   # stays legible over ANY ground (empty frame / tint / photo),
        base = tuple(fg) + (255,)               # on any theme + aspect — no bar.
        hl_col = _karaoke_hl_rgb(out, bg, base[:3])     # spoken word contrasts the frame's OWN ground
        halo = (245, 244, 240, 200) if _rel_lum(fg) < 0.45 else (12, 12, 12, 210)   # opposite-luminance outline
        y0 = H - int(H * 0.02) - block_h        # flush to the very bottom edge
    y = y0 + pad
    def _put(xy, s, fill):                      # a caption line/word, with a thin outline when there's no bar
        if halo:
            ox, oy = xy
            for dx, dy in ((-2, -2), (-2, 2), (2, -2), (2, 2), (-2, 0), (2, 0), (0, -2), (0, 2)):
                d.text((ox + dx, oy + dy), s, font=font, fill=halo)
        d.text(xy, s, font=font, fill=fill)
    if hl_word is None:
        for ln in lines:
            w = d.textlength(ln, font=font)
            _put(((W - w) / 2, y), ln, base)
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
            col = hl_col if gi == hl_word else base
            _put((x, y), w, col)
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

def _caption_layer(text, W, H, dst, meta=None, hl_word=None, band=0, text_rgb=None, band_bg=None):
    """Draw ONLY one caption block onto a transparent PNG (shown for one time window). In band mode the
    layer is W×(H+band) so the caption text lands in the strip below the content; `text_rgb` overrides
    the text colour (the per-scene sampled colour that contrasts a flush strip); `band_bg` is that strip's
    ground rgb, used to contrast-pick the karaoke highlight so it never vanishes into the band."""
    layer = Image.new("RGBA", (W, H + band), (0, 0, 0, 0))
    _draw_caption(ImageDraw.Draw(layer), text, W, H, meta, hl_word, band=band, text_rgb=text_rgb, band_bg=band_bg)
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
# abbreviations whose trailing '.' must NOT end a caption ("Dr. Smith" is one phrase, not two captions).
_ABBR = (r"Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St|Mt|vs|etc|al|Inc|Ltd|Co|Corp|Dept|No|Fig|Eq|Ref|Vol|Ch|approx|"
         r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|e\.g|i\.e|a\.m|p\.m|U\.S|U\.K|Ph\.D")

def _segment(text, cjk_marks, latin_marks):
    """Split into pieces ending at a boundary mark (kept attached). CJK marks break
    unconditionally; Latin marks break before whitespace/EOL OR a following CJK glyph — so a
    comma/colon authored in ASCII *inside* Chinese text ("提取,公式") still splits, while a
    decimal like "1.77" or "1,000" (mark between digits) stays intact. Abbreviation/initial periods
    ("Dr.", "e.g.", "U.S.", "J. Smith") are protected so they don't fragment into tiny captions."""
    t = re.sub(rf"([{cjk_marks}])", "\\1\x00", text)
    if "." in latin_marks:                       # protect abbrev/initial periods (\x02), restore after
        t = re.sub(rf"\b(?:{_ABBR})\.", lambda m: m.group(0)[:-1] + "\x02", t)
        t = re.sub(r"\b([A-Z])\.(?=\s*[A-Z])", lambda m: m.group(1) + "\x02", t)   # initials: J. Smith / U.S.A.
    t = re.sub(rf"([{latin_marks}])(?=\s|$|[{_CJK}])", "\\1\x00", t)
    t = t.replace("\x02", ".")
    return [p.strip() for p in t.split("\x00") if p.strip()]

# trailing clause punctuation looks cut-off at a caption line break — strip it from each chunk
_TRAIL_CLAUSE = "，、：；,;:　 "

def _hardwrap(s, limit):
    """Break an over-limit clause that has NO comma/clause mark to split on into <=limit pieces — at word
    boundaries (Latin) or char boundaries (CJK) — so a long no-punctuation sentence doesn't render as a
    4+-line wall of text over the lower third."""
    s = s.strip()
    if _wlen(s) <= limit:
        return [s] if s else []
    if _CJK_RE.search(s) and " " not in s:        # CJK run, no spaces — break on chars (weighted ~2.5)
        step = max(1, int(limit / 2.5))
        return [s[i:i + step] for i in range(0, len(s), step)]
    out, cur = [], ""
    for w in s.split():
        if cur and _wlen(cur) + 1 + _wlen(w) > limit:
            out.append(cur); cur = w
        else:
            cur = w if not cur else cur + " " + w
    if cur:
        out.append(cur)
    return out

def _split_caption_chunks(text, max_len=84, hard_wrap=True):
    """Split narration into readable, subtitle-sized chunks: first on sentence enders,
    then break any over-long sentence on commas/colons so a chunk fits 1-2 lines.
    A WEIGHTED budget (CJK glyph ~2, Latin ~1) fits both scripts — so a mostly-English line with one CJK
    term isn't chopped to the CJK-tight limit (the old binary flip tripled the cuts on bilingual decks)."""
    text = (text or "").strip()
    if not text:
        return []
    limit = max_len
    chunks = []
    for s in _segment(text, _CJK_ENDERS, _LATIN_ENDERS):
        if _wlen(s) <= limit:
            chunks.append(s); continue
        cur = ""
        for piece in _segment(s, _CJK_CLAUSES, _LATIN_CLAUSES):
            if cur and _wlen(cur) + _wlen(piece) > limit:
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
    # a chunk ending on a clause mark reads as cut-off at the line break — trim it.
    trimmed = [c.rstrip(_TRAIL_CLAUSE) for c in chunks if c.rstrip(_TRAIL_CLAUSE)]
    if not hard_wrap:                             # validate wants the PRE-wrap chunks so it can still
        return trimmed                            # warn "wall of text — split the beat" (author guidance)
    # HARD-WRAP any clause still over the limit (a long sentence with no comma to break on) so the render
    # doesn't put a 4+-line wall on screen even if the author ignores validate's warning.
    out = []
    for c in trimmed:
        out.extend(_hardwrap(c, limit))
    return out

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
               "type", "props", "fit", "transition", "transition_seconds", "intensity")},
        "r": [W, H, meta.get("fps", 30), ss, burn, vertical,
              meta.get("language", "auto"), meta.get("font"),
              meta.get("transition", "dip"), meta.get("transition_seconds", 0.2),
              meta.get("captions_karaoke", "auto"), meta.get("reduced_motion", False),
              # caption placement changes the CLIP HEIGHT (band -> H+band) and colours — must bust the
              # cache, else a partial re-render (--only / one edited scene) mixes clip heights and the
              # `-c copy` concat breaks.
              meta.get("caption_mode"), meta.get("caption_band"), meta.get("caption_scale"),
              meta.get("intensity"), "x264crf18"],
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

def _theme_var_hex(out_dir, var, default):
    """A theme.css colour var (e.g. '--bg', '--fg') as a 6-hex string ('rrggbb'), else `default`. Only
    valid 3- or 6-digit CSS hex matches (a 4/5-digit value is ignored, not truncated into a bad colour)."""
    try:
        m = re.search(re.escape(var) + r"\s*:\s*#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F])",
                      open(os.path.join(out_dir, "theme.css")).read())
        if m:
            h = m.group(1)
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            return h.lower()
    except OSError:
        pass
    return default

def _theme_bg(out_dir):
    """The deck's background colour (for transition dips) as ffmpeg 0xRRGGBB — from theme.css --bg,
    else the base dark default. A dip through the deck's OWN bg reads as the stage briefly clearing,
    seamless on any theme (fading to black would flash on a light deck)."""
    return "0x" + _theme_var_hex(out_dir, "--bg", "0d1117")

def _theme_rgb(out_dir, var, default_rgb):
    """A theme.css colour var as an (r,g,b) tuple for PIL, else `default_rgb`."""
    h = _theme_var_hex(out_dir, var, None)
    try:
        if h and len(h) == 6:
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        pass
    return default_rgb

def _caption_band_px(meta, W, H):
    """Height of the below-content caption strip when `meta.caption_mode == 'band'` (else 0). Sized for
    up to two caption lines + generous vertical padding; kept EVEN so H+band stays yuv420p-legal. In band
    mode the caption sits OUTSIDE the content frame (a dedicated strip below), so it never overlaps the
    slide — the output canvas becomes W×(H+band). Default ('overlay') keeps the classic burned-in bar."""
    if (meta or {}).get("caption_mode") != "band" or not (meta or {}).get("captions", True):
        return 0                                  # no strip in overlay mode OR when captions are off
    fp = _caption_font_px(W, H, band=True, meta=meta)
    band = int(fp * 2 * 1.30) + int(H * 0.030)   # up to 2 caption lines + tight vertical padding
    return band + (band & 1)

def _caption_band_colors(meta):
    """(strip_bg as ffmpeg 0xRRGGBB, text as an (r,g,b) tuple) — the flat fallback for the below-content
    caption band when there's no scene frame to sample. Default 'flush' = the deck's --bg + --fg (ink)
    text; `meta.caption_band == 'contrast'` = the dark --fg subtitle bar + --bg text. ≥7:1 either way."""
    out = (meta or {}).get("_out", ".")
    if (meta or {}).get("caption_band") == "contrast":
        return "0x" + _theme_var_hex(out, "--fg", "111111"), _theme_rgb(out, "--bg", (255, 255, 255))
    return "0x" + _theme_var_hex(out, "--bg", "f4f3ee"), _theme_rgb(out, "--fg", (17, 17, 17))

def _rel_lum(rgb):
    """WCAG relative luminance of an (r,g,b) 0..255 colour."""
    def _lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

def _sample_strip_color(frame_path):
    """Median colour of a content frame's bottom edge — so the flush caption strip is a SEAMLESS
    continuation of THIS scene's own ground (off-white, a tint, a red accent-fill, a photo), not a flat
    deck --bg. Median (not mean) shrugs off a stray glyph in the bottom row. None if the frame is unreadable."""
    try:
        im = Image.open(frame_path).convert("RGB")
        row = im.crop((0, max(0, im.height - 6), im.width, im.height))
        px = sorted(row.getdata(), key=_rel_lum)
        return px[len(px) // 2]
    except Exception:
        return None

def _caption_band_fill(meta, content_frame=None):
    """(strip bg 0xRRGGBB, text rgb) for band mode. 'contrast' or no frame -> the flat fallback above.
    Default 'flush' SAMPLES this scene's bottom-edge colour (content_frame) so the strip continues the
    slide exactly; the text is whichever of --fg/--bg contrasts that sampled ground better."""
    if (meta or {}).get("caption_band") == "contrast" or not content_frame:
        return _caption_band_colors(meta)
    rgb = _sample_strip_color(content_frame)
    if rgb is None or max(rgb) < 8:                  # unreadable, OR a pure-black contain-fit LETTERBOX
        return _caption_band_colors(meta)            # bar (no real theme/scene ground is near-pure-black)
    out = (meta or {}).get("_out", ".")
    fg = _theme_rgb(out, "--fg", (17, 17, 17)); bg = _theme_rgb(out, "--bg", (244, 243, 238))
    lum = _rel_lum(rgb)

    def _ratio(txt):
        a, b = sorted((_rel_lum(txt), lum))
        return (b + 0.05) / (a + 0.05)
    text = fg if _ratio(fg) >= _ratio(bg) else bg    # the theme colour that contrasts the strip better
    if _ratio(text) < 3.0:                           # AA-large floor: a saturated mid-tone strip could
        text = max((0, 0, 0), (255, 255, 255), key=_ratio)   # starve both -> pure b/w by MAX contrast
    return "0x%02x%02x%02x" % tuple(rgb), text

def _ffhex_rgb(s):
    """'0xRRGGBB' (or '#RRGGBB') -> (r,g,b). Used to turn the band strip colour back into rgb."""
    s = str(s).lstrip("#")
    if s[:2].lower() == "0x":
        s = s[2:]
    try:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return (244, 243, 238)

def _wcag_contrast(a, b):
    la, lb = sorted((_rel_lum(a), _rel_lum(b)))
    return (lb + 0.05) / (la + 0.05)

def _karaoke_hl_rgb(out, band_bg, base):
    """The karaoke highlight colour for the SPOKEN word in the caption band. Must (1) clear a readable
    contrast against the band BACKGROUND — so on an accent-fill strip the emphasised word never vanishes
    into a same-colour ground (the bug: --accent highlight on an --accent band) — AND (2) stay visually
    DISTINCT from the neighbouring (base) words, so the emphasis still reads. Prefers the deck --accent
    (keeps the on-brand look on a paper strip), then --accent2, then a warm gold, then a max-contrast b/w.
    `band_bg`/`base` are rgb tuples."""
    def rgb_dist(a, b):
        return sum(abs(x - y) for x, y in zip(a, b))
    def distinct(c):                                  # different enough from the neighbouring words
        return _wcag_contrast(c, base) >= 1.6 or rgb_dist(c, base) >= 120
    cands = [_theme_rgb(out, "--accent", (181, 101, 47)),
             _theme_rgb(out, "--accent2", (47, 109, 117)),
             tuple(KARAOKE_HL[:3])]
    for c in cands:
        if _wcag_contrast(c, band_bg) >= 3.0 and distinct(c):    # readable on the strip AND not a neighbour twin
            return tuple(c) + (255,)
    # nothing preferred clears both — prefer the black/white that BOTH contrasts the strip strongly AND
    # stays distinct from the neighbouring words (on an accent-fill band this gives a crisp high-contrast
    # spoken word); only if neither b/w is distinct (base already is b/w) fall to the accent that pops most.
    bw_ok = [c for c in ((0, 0, 0), (255, 255, 255)) if distinct(c)]
    if bw_ok:
        return max(bw_ok, key=lambda c: _wcag_contrast(c, band_bg)) + (255,)
    return tuple(max(cands, key=lambda c: _wcag_contrast(c, band_bg))) + (255,)

# The lurch / soft-text ceilings the validate gate enforces on the AUTHORED move. Kept here (not
# imported from validate — validate imports render, not the reverse) so the intensity dial can't push
# the EFFECTIVE move past them. Keep in sync with validate.MAX_ZOOM_DELTA / its 1.25 check.
_MAX_ZOOM_DELTA = 0.20   # a bigger zoom delta reads as a lurch, not a Ken Burns
_MAX_ZOOM_ABS = 1.25     # fine text softens past zoompan's scale limit

# Visual-ENERGY amplitude dial (baoyu "mood"/comic "tone"): scales the Ken Burns MOVE so a bold beat
# pushes harder + a subtle one drifts. meta.intensity sets the deck default; a per-scene slide.intensity
# (which the design-director maps from the beat's `energy`) overrides. balanced==1.0 leaves motion unchanged.
_INTENSITY = {"subtle": 0.6, "balanced": 1.0, "bold": 1.5}
def _intensity_amp(meta, slide=None):
    key = (slide or {}).get("intensity") or (meta or {}).get("intensity") or "balanced"
    try:
        return max(0.0, float(key))                  # a raw multiplier is allowed too
    except (TypeError, ValueError):
        return _INTENSITY.get(str(key).lower(), 1.0)

def _motion_exprs(m, frames, reduced_motion=False, amp=1.0):
    """The zoompan z / x-pan / y-pan expressions for a slide's Ken Burns move. With reduced_motion,
    force to==from so every expression is constant (a static frame — no zoom/pan). `amp` scales the MOVE
    (zoom-delta + pan) around the start point by the visual-energy dial (bold pushes more, subtle less)."""
    fx, fy, z0 = m["from"]; tx, ty, z1 = m["to"]
    if reduced_motion:
        tx, ty, z1 = fx, fy, z0
    elif amp != 1.0:                                  # scale the move around the start anchor
        z1 = z0 + (z1 - z0) * amp
        tx = fx + (tx - fx) * amp
        ty = fy + (ty - fy) * amp
        # intensity is a gentle DIAL, not a bypass of the caps validate enforces on the authored move:
        # clamp the amplified result so a bold beat (or a raw multiplier) can't exceed a 0.20 zoom-delta,
        # a 1.25 absolute zoom, or pan the anchor off-canvas — the exact lurch/soft-text this dial invites.
        dz = max(-_MAX_ZOOM_DELTA, min(_MAX_ZOOM_DELTA, z1 - z0))
        z1 = min(_MAX_ZOOM_ABS, max(1.0, z0 + dz))
        tx = min(1.0, max(0.0, tx))
        ty = min(1.0, max(0.0, ty))
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
    t, d = sb.normalize_transition(s)            # accepts the flat form AND a legacy {in,out,seconds} object
    if t not in ("dip", "in", "out", "none"):    # unknown/absent -> the meta default (validate warns)
        t = (meta or {}).get("transition", "dip")
    if t == "none":
        return ""
    d = float(d if d is not None else (meta or {}).get("transition_seconds", 0.2))
    # a DIP occupies both edges (~2*d), a single 'in'/'out' fade only one — don't suppress a legit
    # single-edge seam on a short scene by holding it to the dip headroom.
    need = 2.2 * d if t == "dip" else 1.1 * d
    if d <= 0 or dur <= need:
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
    band = _caption_band_px(meta, W, H)                # >0 -> captions in a strip BELOW the content
    parts = [f"[0:v]scale={W}:{H}[v0]"]               # frames are already WxH; scale = safety
    vlabel = "v0"; extra_inputs = []; n_in = 2        # 0=frames, 1=audio
    fade = _fade_filter(meta, dur, slide)              # dip-to-bg transition at the clip edges

    band_text = None; band_bg = None                   # per-scene sampled caption text colour + strip ground
    def _add_caption_overlays():
        nonlocal vlabel, n_in
        for k, seg in enumerate(caption_segs):
            if not (seg.get("text") or "").strip():
                continue
            cap_png = os.path.join(workdir, f"scap_{k:03d}.png")
            _caption_layer(seg["text"], W, H, cap_png, meta, hl_word=seg.get("hl"), band=band, text_rgb=band_text, band_bg=band_bg)
            extra_inputs.append("-i"); extra_inputs.append(cap_png)
            en = f"between(t,{seg['start']},{seg['end']})"
            parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0:enable='{en}'[v{n_in}]")
            vlabel = f"v{n_in}"; n_in += 1

    if band:                                           # fade the content, add the strip, then the caption text
        if fade:
            parts.append(f"[{vlabel}]{fade}[vf]"); vlabel = "vf"
        bg, band_text = _caption_band_fill(meta, pattern % 0)   # strip continues THIS scene's own ground
        band_bg = _ffhex_rgb(bg)                        # the strip ground, for the highlight-contrast pick
        parts.append(f"[{vlabel}]pad={W}:{H + band}:0:0:color={bg}[vpad]"); vlabel = "vpad"
        _add_caption_overlays()
    else:                                              # classic burn-in bar, then fade the whole frame
        _add_caption_overlays()
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
    zexpr, xpan, ypan = _motion_exprs(m, frames, meta.get("reduced_motion"), amp=_intensity_amp(meta, slide))
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
    band = _caption_band_px(meta, W, H)                # >0 -> captions in a strip BELOW the content
    segs = (_caption_karaoke_segs(slide, meta, meta["_out"]) or _captions_for(slide)) if burn_captions else []
    fade = _fade_filter(meta, dur, slide)              # dip-to-bg transition at the clip edges

    band_text = None; band_bg = None                   # per-scene sampled caption text colour + strip ground
    def _cap_overlays():
        nonlocal vlabel, n_in
        for k, seg in enumerate(segs):
            if not (seg.get("text") or "").strip():
                continue
            cap_png = os.path.join(workdir, f"cap_{i:02d}_{k:02d}.png")
            _caption_layer(seg["text"], W, H, cap_png, meta, hl_word=seg.get("hl"), band=band, text_rgb=band_text, band_bg=band_bg)
            extra_inputs.append("-i"); extra_inputs.append(cap_png)
            en = f"between(t,{seg['start']},{seg['end']})"
            parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0:enable='{en}'[v{n_in}]")
            vlabel = f"v{n_in}"; n_in += 1

    if band:                                           # fade content, add the strip, then the caption text
        if fade:
            parts.append(f"[{vlabel}]{fade}[vf]"); vlabel = "vf"
        bg, band_text = _caption_band_fill(meta, frame)    # strip continues THIS scene's own ground
        band_bg = _ffhex_rgb(bg)                        # the strip ground, for the highlight-contrast pick
        parts.append(f"[{vlabel}]pad={W}:{H + band}:0:0:color={bg}[vpad]"); vlabel = "vpad"
        _cap_overlays()
    else:                                              # classic burn-in bar, then fade the whole frame
        _cap_overlays()
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
    ap.add_argument("--renderer", choices=["local", "remotion"], default=None,
                    help="override meta.renderer; 'remotion' = the optional cinematic tier (image scenes)")
    a = ap.parse_args()
    # Renderer dispatch: the optional Remotion cinematic tier renders the whole storyboard at once.
    meta = (sb.load(os.path.join(a.out_dir, "storyboard.json")).get("meta") or {})
    if (a.renderer or meta.get("renderer", "local")) == "remotion":
        if a.only:
            print("[render] note: the remotion tier has no --only; rendering the whole deck.")
        import render_remotion
        print(f"Rendered -> {render_remotion.render(a.out_dir, vertical=a.vertical, reduced_motion=a.reduced_motion, sample=a.sample)}")
        return
    res = render(a.out_dir, sample=a.sample, vertical=a.vertical, only=a.only,
                 reduced_motion=a.reduced_motion)
    print(f"Rendered -> {res}")

if __name__ == "__main__":
    main()
