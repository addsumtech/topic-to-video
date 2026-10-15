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


def _pixels(im):
    """Every pixel of `im` as a list. Pillow 12 deprecates getdata() (gone in 14); get_flattened_data()
    is its replacement, with getdata() kept only for an older Pillow."""
    flat = getattr(im, "get_flattened_data", None)
    return list(flat() if flat else im.getdata())

def _speak_wlen(s):
    """SPEAKING-TIME weight of a string: a CJK char ~3x a Latin char (~5 chars/s vs ~15 chars/s).
    Used to TIME caption chunks in mixed-script text — raw len() starves the CJK side (a 20-char zh
    clause needs ~4s but weighed like 20 Latin chars), and a binary CJK/Latin flip breaks the mix."""
    return sum(3 if _CJK_RE.match(c) else 1 for c in (s or ""))

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

# caption face follows the deck's TYPE: --font-kind (theme.css) -> the same bundled style face the
# pages/programmatic tiers use, so the burned caption reads as the deck's own voice, not a third font.
# (Latin scripts only — CJK captions keep the system CJK face, which IS the deck's CJK body fallback.)
_STYLE_CAP_FACE = {"comic": "Bangers-Regular.ttf", "serif": "PlayfairDisplay-VF.ttf",
                   "sans": "SpaceGrotesk-VF.ttf", "mono": "JetBrainsMono-VF.ttf"}

def _style_caption_font(out_dir):
    """The deck's body face for captions, from theme.css --font-kind; None when absent/missing."""
    try:
        css = open(os.path.join(out_dir or ".", "theme.css"), encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"--font-kind:\s*(\w+)", css)
    if not m:
        return None
    p = os.path.join(os.path.dirname(BUNDLED_FONT), _STYLE_CAP_FACE.get(m.group(1), ""))
    return p if os.path.basename(p) and os.path.exists(p) else None

def _font_path(meta, text):
    """Resolve the caption font: an explicit meta.font override, else a system CJK font
    when the text needs one, else the deck's own body face (--font-kind), else the bundled Latin font."""
    explicit = (meta or {}).get("font")
    if explicit and os.path.exists(explicit):
        return explicit
    script = _script_of(text or "", (meta or {}).get("language", "auto"))
    if script != "latin":
        for p in _FONT_CANDIDATES.get(script, []) + _FONT_FALLBACKS:
            if os.path.exists(p):
                return p
        return BUNDLED_FONT
    return _style_caption_font((meta or {}).get("_out")) or BUNDLED_FONT

_FONT_CACHE = {}
def _load_font(size, path=None):
    path = path or BUNDLED_FONT
    key = (path, size)
    if key not in _FONT_CACHE:
        try:
            f = ImageFont.truetype(path, size)
            try:
                f.set_variation_by_axes([400])   # VF faces: pin Regular (SpaceGrotesk-VF defaults to 300/Light,
            except Exception:                    # which burned lighter than the deck body); static faces raise -> no-op
                pass
            _FONT_CACHE[key] = f
        except Exception:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def _canvas(meta, vertical):
    if vertical:
        return 1080, 1920
    return meta.get("width", 1920), meta.get("height", 1080)

def _fit_frame(src, dst, W, H, fit="contain", bg_rgb=(0, 0, 0)):
    """Scale a slide image onto a WxH canvas. contain = letterbox (default); cover = scale to
    fill then center-crop (full-frame, for AI b-roll). The letterbox is filled with `bg_rgb` — pass
    the deck's --bg so a bar-free caption in the letterbox keeps its ≥7:1 --fg contrast (a pure-black
    letterbox made a light-theme caption invisible) and the scene-edge dip matches the bands."""
    im = Image.open(src).convert("RGB")
    if fit == "cover":
        scale = max(W / im.width, H / im.height)
        nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
        im = im.resize((nw, nh), Image.LANCZOS)
        left, top = (nw - W) // 2, (nh - H) // 2
        im.crop((left, top, left + W, top + H)).save(dst)
        return
    im.thumbnail((W, H), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), tuple(bg_rgb))
    bg.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    bg.save(dst)

# Hangul is EXCLUDED from the break-anywhere class: Korean orthography REQUIRES inter-word spaces,
# so hangul runs wrap like Latin words (the old tight-join silently deleted the spaces).
_CJK_TIGHT = _HAN + _KANA + _CJK_PUNCT
_CJK_TIGHT_RE = re.compile(f"[{_CJK_TIGHT}]")

def _atoms(text):
    """Break text into wrap units: each zh/ja CJK character is its own unit (no spaces — a line may
    break between any two), while runs of other non-space characters (Latin words AND Korean hangul
    words) stay together and re-join with a space."""
    return re.findall(f"[{_CJK_TIGHT}]|[^{_CJK_TIGHT}\\s]+", text)

def _wrap(d, text, font, max_w):
    """Greedy wrap to a max pixel width. Latin words join with a space; CJK characters
    join tight and may break anywhere — so Chinese/Japanese/Korean captions wrap instead
    of overflowing as one un-splittable line (which `text.split()` alone produced)."""
    KINSOKU = "，。、：；！？…）』」》%"      # closers/clause marks never START a wrapped line
    lines, cur = [], ""
    for a in _atoms(text):
        if not cur:
            trial = a
        elif _CJK_TIGHT_RE.match(a) or _CJK_TIGHT_RE.match(cur[-1]):
            trial = cur + a            # no space when either side is zh/ja CJK
        else:
            trial = cur + " " + a      # space between Latin/hangul words
        if not cur or d.textlength(trial, font=font) <= max_w or a in KINSOKU:
            cur = trial                # kinsoku: a lone closer rides the line even slightly over budget
        else:
            lines.append(cur); cur = a
    if cur:
        lines.append(cur)
    return lines

KARAOKE_HL = (255, 209, 102, 255)   # warm gold — reads clearly on the dark caption bar

def _caption_font_px(W, H, band=False, meta=None):
    """Caption size scales with the NARROW dimension, not height: H-relative sizing balloons to
    ~86px on a 9:16 canvas (double the landscape weight in half the width — 3-line wraps, widows,
    and the band eats the layout). min(W,H)*0.040 keeps the same visual weight in both aspects.
    The below-content BAND uses a slightly smaller face (~0.85×) — it has its own strip, so it needn't
    shout over content; `meta.caption_scale` tunes either mode (e.g. 0.9 to shrink further).
    Base factor 0.040 (was 0.045): captions are a reading aid, not a headline — they should sit quietly
    under the content (user feedback: the burned caption competed with the page's own type)."""
    scale = (0.85 if band else 1.0) * float((meta or {}).get("caption_scale", 1.0) or 1.0)
    return max(12, int(min(W, H) * 0.040 * scale))

def _draw_caption(d, text, W, H, meta=None, hl_word=None, band=0, text_rgb=None, band_bg=None,
                  hl_span=None):
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
    if band:
        while block_h > band and getattr(font, "size", 0) > 16:   # authored 3+-line band captions: shrink to
            font = _load_font(max(16, int(font.size * 0.87)), _font_path(meta, text))   # fit the strip instead of
            lines = _wrap(d, text, font, int(W * 0.9))                                  # silently clipping lines
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
    else:                                       # overlay — NO background bar. Draw the caption at the very BOTTOM in
        out = (meta or {}).get("_out", ".")     # an ink that CONTRASTS the REAL ground (sampled into band_bg by the
        fg = _theme_rgb(out, "--fg", (17, 17, 17))      # caller), with a subtle opposite-luminance OUTLINE — legible
        bg = _theme_rgb(out, "--bg", (244, 243, 238))   # over any ground (empty frame / tint / photo / letterbox).
        ground = tuple(band_bg) if band_bg is not None else bg   # the pixels actually under the caption
        # Ink = the FRAME'S OWN content colour, so the subtitle reads as PART of the frame (not an independent
        # max-contrast pick that clashes — a dark caption under white-on-coral content). The deck uses --fg on
        # light/neutral grounds and --on-accent on saturated/colored/dark fills (a full accent-fill flood); pick
        # by the sampled ground's luminance. Fall back to pure b/w ONLY if the chosen deck ink would starve
        # (< AA-large 3:1) on an unusual mid-tone ground.
        on_acc = _theme_rgb(out, "--on-accent", (255, 255, 255))
        cand = fg if _rel_lum(ground) >= 0.5 else on_acc
        base = (tuple(cand) if _wcag_contrast(cand, ground) >= 3.0
                else max((17, 17, 17), (245, 244, 240), key=lambda c: _wcag_contrast(c, ground))) + (255,)
        hl_col = _karaoke_hl_rgb(out, ground, base[:3])          # spoken word contrasts the SAME real ground
        # Outline = the FRAME'S OWN ground colour (NOT a white/black opposite-luminance halo, which read as an
        # ugly solid "white background" behind the caption on a light frame). The subtitle sits directly on the
        # frame's own content background: this outline is that SAME colour, so it's invisible on the clean
        # caption zone and only a subtle hair where the ground varies — never a bar, never white. Authors keep
        # content clear of the bottom ~15% (keyframe_qa gates it) so the zone is the frame's own clean ground.
        halo = tuple(ground[:3]) + (235,)
        y0 = H - int(H * 0.02) - block_h        # flush to the very bottom edge
    y = y0 + pad
    def _put(xy, s, fill):                      # a caption line/word, with a thin outline when there's no bar
        if halo:
            ox, oy = xy
            for dx, dy in ((-2, -2), (-2, 2), (2, -2), (2, 2), (-2, 0), (2, 0), (0, -2), (0, 2)):
                d.text((ox + dx, oy + dy), s, font=font, fill=halo)
        d.text(xy, s, font=font, fill=fill)
    if hl_span is not None:
        # CJK karaoke: highlight a CHAR RANGE [a,b) of the ORIGINAL text. Wrapping may normalize
        # whitespace, so align wrapped-line chars to original indices by walking both streams over
        # their non-space chars; each line then draws as runs (base / highlight / base).
        a, b = hl_span
        oi = 0
        for ln in lines:
            runs, cur, cur_hl = [], "", None
            for chx in ln:
                if chx.isspace():
                    hl = cur_hl if cur_hl is not None else False   # spaces inherit the current run
                else:
                    while oi < len(text) and text[oi].isspace():
                        oi += 1
                    hl = a <= oi < b
                    oi += 1
                if cur_hl is None or hl == cur_hl:
                    cur += chx; cur_hl = hl
                else:
                    runs.append((cur, cur_hl)); cur, cur_hl = chx, hl
            if cur:
                runs.append((cur, cur_hl))
            x = (W - d.textlength(ln, font=font)) / 2
            for s, hlf in runs:
                _put((x, y), s, hl_col if hlf else base)
                x += d.textlength(s, font=font)
            y += line_h
        return
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

def _caption_layer(text, W, H, dst, meta=None, hl_word=None, band=0, text_rgb=None, band_bg=None,
                   hl_span=None):
    """Draw ONLY one caption block onto a transparent PNG (shown for one time window). In band mode the
    layer is W×(H+band) so the caption text lands in the strip below the content; `text_rgb` overrides
    the text colour (the per-scene sampled colour that contrasts a flush strip); `band_bg` is that strip's
    ground rgb, used to contrast-pick the karaoke highlight so it never vanishes into the band."""
    layer = Image.new("RGBA", (W, H + band), (0, 0, 0, 0))
    _draw_caption(ImageDraw.Draw(layer), text, W, H, meta, hl_word, band=band, text_rgb=text_rgb,
                  band_bg=band_bg, hl_span=hl_span)
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
    words = _load_words(out_dir, slide.get("index") or 0)
    dur = float(slide.get("duration") or 0)
    if not words or dur <= 0:
        return None
    if lang in ("zh", "ja", "ko"):
        # CJK has no spaces, so the space-split word path can't apply — but edge-tts DOES emit per-token
        # word boundaries for CJK. Match each token as a SUBSTRING of the caption chunks, sequentially
        # (tokens arrive in spoken order = display order), and highlight its CHAR RANGE (`hl_span`)
        # instead of a space-word index — so 中文 captions get the same word-level karaoke as English.
        return _cjk_karaoke_segs(words, _captions_for(slide), dur)
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

def _cjk_karaoke_segs(words, chunks, dur):
    """CJK karaoke: sequentially locate each edge-tts token as a substring of the caption chunks and
    emit one seg per token — {start, end, text (the chunk), hl_span: [a, b) char range}. Tokens and
    chunks are both in spoken order, so matching walks both left-to-right; a token absent from the
    current chunk's remainder moves to the next chunk when it appears later, else is skipped (edge
    normalizes some tokens — numbers, Latin runs). Too few matches → None (chunk-level fallback)."""
    toks = [(str(w.get("w") or "").strip(), float(w.get("t") or 0)) for w in words]
    toks = [(w, t) for w, t in toks if w]
    if not toks or not chunks:
        return None
    matches, wi = [], 0                     # [chunk_idx, a, b, start]
    for ci, c in enumerate(chunks):
        txt = c["text"]
        pos = 0
        slack = 4                            # chars the next match may sit past the cursor (punctuation);
        while wi < len(toks):                # grows after a skipped (normalized) token so we can resume
            tok, t0 = toks[wi]
            f = txt.find(tok, pos)
            near = f >= 0 and (f - pos) <= slack
            if not near:
                # no PLAUSIBLE match at the cursor. A far-forward hit is likely a DUPLICATE of a later
                # occurrence (edge normalized this token — e.g. spoke '1.5' as 一点五) — binding it
                # would flash the highlight early and starve the tokens in between. Advance to a later
                # chunk only with CORROBORATION (this token AND the next appear there in order);
                # otherwise skip just this token and widen the slack to step past its unmatched text.
                moved = False
                for cj in range(ci + 1, len(chunks)):
                    g = chunks[cj]["text"].find(tok)
                    if g >= 0:
                        nxt = toks[wi + 1][0] if wi + 1 < len(toks) else None
                        if (nxt is None or chunks[cj]["text"].find(nxt, g + len(tok)) >= 0
                                or any(nxt in chunks[ck]["text"] for ck in range(cj + 1, len(chunks)))):
                            moved = True
                        break
                if moved:
                    break
                wi += 1
                slack += 6
                continue
            matches.append([ci, f, f + len(tok), t0])
            pos = f + len(tok)
            slack = 4
            wi += 1
    if len(matches) < max(3, len(toks) // 2):
        return None                          # matching too weak — safer to fall back to chunk captions
    segs = []
    for i, (ci, a, b, t0) in enumerate(matches):
        end = matches[i + 1][3] if i + 1 < len(matches) else dur
        if end <= t0:
            end = t0 + 0.08
        segs.append({"start": round(t0, 3), "end": round(end, 3),
                     "text": chunks[ci]["text"], "hl_span": [a, b]})
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
    A WEIGHTED budget (CJK glyph ~2.5, Latin ~1) fits both scripts — so a mostly-English line with one CJK
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
    weights = [max(1, _speak_wlen(c)) for c in chunks]   # speaking-time, not raw chars (mixed-script)
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

def _tail_led(slide, meta):
    """The cue indices scenes.clamp_cues_to_end leads on this page (a cache salt; [] for anything else)."""
    if slide.get("type") != "html" or not (slide.get("props") or {}).get("html") or not slide.get("duration"):
        return []
    try:
        import scenes as _scenes
        fps = meta.get("fps", 30)
        m = dict(meta, _narration=slide.get("narration") or "", _slide=slide)
        return _scenes.html_capture_plan(slide.get("props") or {}, m, max(1, int(round(slide["duration"] * fps))),
                                         slide.get("index"))["tail_led"]
    except Exception:
        return []


def _has_long_cued_anim(slide, meta):
    """True when this scene is a CUED html page carrying an animation longer than the old flat 0.8s
    capture burst — i.e. exactly the pages whose rendered pixels changed when the burst became
    per-cue. Used as a surgical cache salt so the fix reaches existing decks without invalidating
    every cached clip in every out_dir."""
    if slide.get("type") != "html":
        return False
    rel = (slide.get("props") or {}).get("html")
    if not rel:
        return False
    try:
        html = open(os.path.join(meta["_out"], rel), encoding="utf-8", errors="replace").read()
    except OSError:
        return False
    if "data-cue-index" not in html:
        return False
    table = _common.css_anim_durations()
    for tag in re.findall(r"<[^>]+>", html):
        if "data-cue-index" not in tag:
            continue
        secs = _common.element_anim_seconds(tag, table)
        if secs and secs > 0.8:
            return True
    return False


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
    fp = {
        "s": {k: slide.get(k) for k in
              ("image", "audio", "duration", "motion", "narration", "captions", "callouts",
               "type", "props", "fit", "transition", "transition_seconds", "transition_style", "intensity")},
        "r": [W, H, meta.get("fps", 30), ss, burn, vertical,
              meta.get("language", "auto"), meta.get("font"),
              meta.get("transition", "dip"), meta.get("transition_seconds", 0.2),
              meta.get("transition_style", "dip"),
              meta.get("captions_karaoke", "auto"), meta.get("reduced_motion", False),
              # caption placement changes the CLIP HEIGHT (band -> H+band) and colours — must bust the
              # cache, else a partial re-render (--only / one edited scene) mixes clip heights and the
              # `-c copy` concat breaks.
              meta.get("caption_mode"), meta.get("caption_band"), meta.get("caption_scale"),
              meta.get("intensity"), "x264crf18"],
        # filter-impl version for the blur edge only: v1's chained alpha-fades cancelled to invisible
        # (fixed to one layer per edge) — bust just those clips, not every cached clip everywhere
        "edge": ("blur2" if (slide.get("transition_style") or meta.get("transition_style")) == "blur"
                 else None),
        # capture-window version — cued HTML pages carrying a LONG animation only. render_html's
        # burst was a flat 0.8s, which stopped capturing a 1.4s `.draw` at 57% of its timeline and
        # then held that frame for the rest of the scene (the connector never reached its endpoint).
        # The window is now sized per cue. A clip cached before that fix still contains the frozen
        # render, and nothing else in this fingerprint would notice — so salt exactly the pages whose
        # pixels change, and leave every ordinary .7s-reveal page byte-identical and still cached.
        "cap": ("burst2" if _has_long_cued_anim(slide, meta) else None),
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
        # brand is part of the look (always in the key); the logo BYTES matter only where render
        # DRAWS them — the corner bug — so a logo touch must not bust clips for lockup-only decks
        # (cover/endcard lockups live in the authored pages, fingerprinted via "html").
        "brand": meta.get("brand"),
        "logo": stat(_bug_logo_rel(meta)) if _bug_placed(meta) else None,
        # whether THIS scene carries the bug depends on its edge position (first/last skip under
        # cover/endcard) — appending or dropping an edge scene flips a former edge scene's bug
        # without changing anything else about it, so the verdict itself must key the cache.
        # "v2" = sizing impl (min(W,H) + 35%-W banner clamp): busts only bug-bearing clips
        "bughere": ("v2" if _bug_wanted(meta, slide) else False) if meta.get("brand") else None,
    }
    # a cue LED so its reveal finishes before the out-transition (scenes.clamp_cues_to_end). Added ONLY when
    # it applies: a key present on every clip (even as null) would change every fingerprint and re-render
    # every cached clip of every deck for a fix that moves a few pages.
    if _tail_led(slide, meta):
        fp["tail"] = "led1"
    payload = json.dumps(fp, sort_keys=True, default=str)
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
        px = sorted(_pixels(row), key=_rel_lum)
        return px[len(px) // 2]
    except Exception:
        return None

def _sample_region_color(frame_path, top_frac=0.80):
    """Median colour of a content frame's BOTTOM region (where the bar-free OVERLAY caption sits) — so
    the caption can contrast-pick its ink + outline + karaoke against the REAL ground (a photo, a tint,
    a --bg letterbox) instead of assuming the flat theme bg. Median shrugs off local detail. None if
    unreadable (the caller then falls back to the theme --fg/--bg)."""
    try:
        im = Image.open(frame_path).convert("RGB")
        y = max(0, min(im.height - 1, int(im.height * top_frac)))
        px = sorted(_pixels(im.crop((0, y, im.width, im.height))), key=_rel_lum)
        return px[len(px) // 2]
    except Exception:
        return None

def _caption_band_fill(meta, content_frame=None):
    """(strip bg 0xRRGGBB, text rgb) for band mode. 'contrast' or no frame -> the flat fallback above.
    Default 'flush' SAMPLES this scene's bottom-edge colour (content_frame) so the strip continues the
    slide exactly; the text is the frame's OWN ink for that ground (--fg on a light strip, --on-accent
    on a dark/saturated one), with an AA-large contrast floor behind it."""
    if (meta or {}).get("caption_band") == "contrast" or not content_frame:
        return _caption_band_colors(meta)
    rgb = _sample_strip_color(content_frame)
    if rgb is None or max(rgb) < 8:                  # unreadable, OR a pure-black contain-fit LETTERBOX
        return _caption_band_colors(meta)            # bar (no real theme/scene ground is near-pure-black)
    out = (meta or {}).get("_out", ".")
    fg = _theme_rgb(out, "--fg", (17, 17, 17)); on_acc = _theme_rgb(out, "--on-accent", (255, 255, 255))
    lum = _rel_lum(rgb)

    def _ratio(txt):
        a, b = sorted((_rel_lum(txt), lum))
        return (b + 0.05) / (a + 0.05)
    # text = the FRAME'S OWN content ink (so the caption matches the frame, not an independent contrast pick):
    # --fg on a light/neutral strip, --on-accent on a saturated/colored/dark one (a red accent-fill strip).
    text = fg if lum >= 0.5 else on_acc
    if _ratio(text) < 3.0:                            # AA-large floor: an unusual mid-tone strip could starve
        text = max((0, 0, 0), (255, 255, 255), key=_ratio)   # the deck ink -> pure b/w by MAX contrast
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

def _edge_filter(meta, dur, slide, vlabel, W, H):
    """Scene-edge transition as FILTERGRAPH PARTS: (parts, new_vlabel). The seam is TWO SELF-CONTAINED
    halves meeting at the byte-identical theme-bg frame (so the -c copy concat + per-clip cache hold —
    the same construction as an NLE's Dip-to-Color). Edges come from the semantic `transition` field
    (dip=both, in/out=one, none); the LOOK comes from `transition_style` (slide overrides meta):

      dip         fade to/from the theme bg (the quiet workhorse; default)
      fadethrough dip with studio timing — exit FAST (~half d, capped 0.15s), entrance takes the full d;
                  emphasis lands on the NEW content (Material fade-through's 30/70 choreography)
      drift       dip + a whisper of direction: ~24px positional drift while fully fading — the page
                  "breathes away"; direction without the push's loudness
      push        the page slides out LEFT over bg, next slides in from the RIGHT (lateral sequence)
      lift        vertical page-turn: out UP, in from BELOW (reading-flow progression)
      wipe        a theme-bg sheet sweeps L->R: exit covers the still page, entrance uncovers the next —
                  directional replacement without spatial travel (graphic/editorial)
      blur        rack-defocus: the frame softens (gblur copy alpha-fades in) as it dips to bg; entrance
                  refocuses — attention-shift / reflective coda (use at most once, e.g. the closer)

    All motion is smoothstep-eased, rides the audio-breath tail, and never touches audio/duration.
    See references/motion-grammar.md "Transition STYLE" for semantics + the one-style-per-deck rule."""
    st_, d = sb.normalize_transition(slide or {})
    t = st_ if st_ in ("dip", "in", "out", "none") else (meta or {}).get("transition", "dip")
    if t == "none":
        return [], vlabel
    d = float(d if d is not None else (meta or {}).get("transition_seconds", 0.2))
    style = (slide or {}).get("transition_style") or (meta or {}).get("transition_style") or "dip"
    if style not in ("dip", "fadethrough", "drift", "push", "lift", "wipe", "blur"):
        style = "dip"
    need = 2.2 * d if t == "dip" else 1.1 * d
    if d <= 0 or dur <= need:
        return [], vlabel
    fps = (meta or {}).get("fps", 30) or 30
    bg = _theme_bg(meta.get("_out", "."))
    T0 = dur - d
    has_in, has_out = t in ("dip", "in"), t in ("dip", "out")

    def _sm(expr_p):                                   # smoothstep of a 0..1 progress expression
        return f"pow(min({expr_p},1),2)*(3-2*min({expr_p},1))"
    sm_in, sm_out = _sm(f"t/{d}"), _sm(f"(t-{T0:.3f})/{d}")

    if style in ("dip", "fadethrough"):
        d_out = min(0.15, d * 0.5) if style == "fadethrough" else d   # exit fast, enter slow (30/70)
        fades = []
        if has_in:
            fades.append(f"fade=t=in:st=0:d={d}:c={bg}")
        if has_out:
            fades.append(f"fade=t=out:st={dur - d_out:.3f}:d={d_out}:c={bg}")
        return ([f"[{vlabel}]{','.join(fades)}[vedge]"], "vedge") if fades else ([], vlabel)

    if style == "blur":
        # progressive defocus riding the dip: a gblur copy alpha-fades over the sharp frame while the
        # composite fades to bg (exit); the entrance refocuses (alpha fades the blur away) while fading up.
        # ONE alpha-fade window per gblur layer — chained fades MULTIPLY (t=in zeroes everything before
        # its st, t=out everything after st+d), so a both-edges seam needs an independent layer per edge
        # (verified empirically: fade=t=in:alpha=1 holds the layer transparent before st; fade=t=out
        # :alpha=1 holds it transparent after st+d; two fades on one layer cancel to invisible).
        labels = ["shp"] + (["bi"] if has_in else []) + (["bo"] if has_out else [])
        parts = [f"[{vlabel}]split={len(labels)}" + "".join(f"[{l}]" for l in labels)]
        base = "shp"
        if has_in:   # entrance refocuses: blur opaque at t=0, alpha-fades away over 0.7d
            parts.append(f"[bi]gblur=sigma=14,format=yuva420p,fade=t=out:st=0:d={0.7 * d:.3f}:alpha=1[blin]")
            parts.append(f"[{base}][blin]overlay[vbi]")
            base = "vbi"
        if has_out:  # exit defocuses: blur transparent until T0, alpha-fades in over 0.7d
            parts.append(f"[bo]gblur=sigma=14,format=yuva420p,fade=t=in:st={T0:.3f}:d={0.7 * d:.3f}:alpha=1[blout]")
            parts.append(f"[{base}][blout]overlay[vbo]")
            base = "vbo"
        fades = []
        if has_in:
            fades.append(f"fade=t=in:st=0:d={0.6 * d:.3f}:c={bg}")
        if has_out:
            fades.append(f"fade=t=out:st={dur - 0.6 * d:.3f}:d={0.6 * d:.3f}:c={bg}")
        parts.append(f"[{base}]{','.join(fades)},format=yuv420p[vedge]")
        return parts, "vedge"

    if style == "drift":
        px = max(16, min(int(W * 0.015), 32))                          # a breath, not a slide
        terms = []
        if has_in:
            terms.append(f"if(lte(t,{d}),{px}*(1-({sm_in})),0)")
        if has_out:
            terms.append(f"if(gte(t,{T0:.3f}),-{px}*({sm_out}),0)")
        fades = []
        if has_in:
            fades.append(f"fade=t=in:st=0:d={d}:c={bg}")
        if has_out:
            fades.append(f"fade=t=out:st={dur - d:.3f}:d={d}:c={bg}")
        return ([f"color=c={bg}:s={W}x{H}:r={fps}:d={dur:.3f}[ebg]",
                 f"[{vlabel}]{','.join(fades)}[vfd]",
                 f"[ebg][vfd]overlay=eval=frame:x='{'+'.join(terms)}':y=0:shortest=1[vedge]"], "vedge")

    if style == "wipe":
        # a bg sheet passes L->R through the seam: exit covers (sheet x: -W -> 0), entrance uncovers
        # (sheet x: 0 -> +W). The PAGE is the main input, so the clip's own fps/duration are preserved.
        terms = []
        if has_out:
            terms.append(f"if(gte(t,{T0:.3f}),-{W}+{W}*({sm_out}),-{W})")
        if has_in:
            terms.append(f"if(lte(t,{d}),{W}*({sm_in}),{W})" if not has_out else "0")
        if has_in and has_out:   # both edges: one sheet enters, then a second leaves — use two overlays
            return ([f"color=c={bg}:s={W}x{H}:r={fps}:d={dur:.3f}[sh1]",
                     f"color=c={bg}:s={W}x{H}:r={fps}:d={dur:.3f}[sh2]",
                     f"[{vlabel}][sh1]overlay=eval=frame:y=0:x='if(lte(t,{d}),{W}*({sm_in}),{W})'[vw1]",
                     f"[vw1][sh2]overlay=eval=frame:y=0:x='if(gte(t,{T0:.3f}),-{W}+{W}*({sm_out}),-{W})'[vedge]"],
                    "vedge")
        expr = terms[0]
        return ([f"color=c={bg}:s={W}x{H}:r={fps}:d={dur:.3f}[sheet]",
                 f"[{vlabel}][sheet]overlay=eval=frame:y=0:x='{expr}'[vedge]"], "vedge")

    # push / lift — the page itself travels over the bg
    span = W if style == "push" else H
    terms = []
    if has_in:
        terms.append(f"if(lte(t,{d}),{span}*(1-({sm_in})),0)")
    if has_out:
        terms.append(f"if(gte(t,{T0:.3f}),-{span}*({sm_out}),0)")
    expr = "+".join(terms)
    xe, ye = (expr, "0") if style == "push" else ("0", expr)
    return ([f"color=c={bg}:s={W}x{H}:r={fps}:d={dur:.3f}[ebg]",
             f"[ebg][{vlabel}]overlay=eval=frame:x='{xe}':y='{ye}':shortest=1[vedge]"], "vedge")


# ── brand bug: a render-level persistent corner mark (meta.brand, placement "bug") ─────────────
def _brand_dict(meta):
    """meta.brand as a dict, {} for anything malformed — validate ERRORs a non-dict brand, but render
    must degrade (skip the bug), never crash, when run without the gate."""
    b = (meta or {}).get("brand")
    return b if isinstance(b, dict) else {}

def _bug_placement(meta):
    """The effective placement list (contract default when absent; malformed -> default, a string
    'bug' must not sneak past via substring containment)."""
    pl = _brand_dict(meta).get("placement")
    return pl if isinstance(pl, list) else ["cover", "endcard"]

def _bug_placed(meta):
    """True when the deck asks for the corner bug at all — the fingerprint's logo-stat gate."""
    return "bug" in _bug_placement(meta) and bool(_brand_dict(meta).get("logo"))

def _bug_wanted(meta, slide):
    """True when the corner bug belongs on THIS scene. Skips the first scene under 'cover' and the
    last under 'endcard' — those frames carry an AUTHORED lockup, and bug + lockup is a double-brand."""
    if not _bug_placed(meta):
        return False
    placement = _bug_placement(meta)
    idx = (slide or {}).get("index")
    first, last = (meta or {}).get("_first_index"), (meta or {}).get("_last_index")
    if "cover" in placement and first is not None and idx == first:
        return False
    if "endcard" in placement and last is not None and idx == last:
        return False
    return True

def _bug_logo_rel(meta):
    """The logo variant the bug draws: logo_dark on a dark ground (the SAME theme bg the seam dips
    through, rel-luminance < 0.5), else logo. Shared with _fingerprint so the statted file is the drawn one."""
    brand = _brand_dict(meta)
    dark = brand.get("logo_dark")
    if dark and _rel_lum(_ffhex_rgb(_theme_bg((meta or {}).get("_out", ".")))) < 0.5:
        return dark
    return brand.get("logo")

def _brand_bug_png(meta, W, H, dst):
    """The corner bug as a W×H transparent layer (same shape as the callout/caption layers), or None
    when the logo is missing/unreadable — a broken brand asset warns and skips, never kills a render.
    Aspect preserved (scaled by height only), never recolored, no effects; opacity rides the alpha.
    Top corners only — the bottom is the caption zone; an unknown corner value means tr."""
    cfg = _brand_dict(meta).get("bug")
    cfg = cfg if isinstance(cfg, dict) else {}         # validate ERRORs a non-dict; render degrades
    rel = _bug_logo_rel(meta)
    # the whole composition is guarded, not just the open — a garbage height_frac/opacity only WARNS
    # at the gate (numbers-only lint), and a warning must never become a render crash here
    try:
        logo = Image.open(os.path.join((meta or {}).get("_out", "."), rel)).convert("RGBA")
        if logo.getchannel("A").getextrema()[1] == 0:
            print(f"[render] warning: brand bug skipped — logo is fully transparent: {rel}")
            return None
        # size by the NARROW dimension (the caption-font lesson: a fraction of H balloons ~3× relative
        # to frame width on 9:16) and clamp a banner wordmark to ~35% of W — wider is a strip, not a
        # watermark, and PIL would silently paste it off-canvas; aspect survives via the h rescale
        margin = int(float(cfg.get("margin_frac", 0.02)) * W)
        h = max(1, int(float(cfg.get("height_frac", 0.045)) * min(W, H)))
        w = max(1, round(logo.width * h / logo.height))
        wmax = max(1, min(int(0.35 * W), W - 2 * margin))
        if w > wmax:
            w = wmax
            h = max(1, round(logo.height * w / logo.width))
        logo = logo.resize((w, h), Image.LANCZOS)
        op = max(0.0, min(1.0, float(cfg.get("opacity", 0.5))))
        if op < 1.0:
            logo.putalpha(logo.getchannel("A").point(lambda a: int(a * op)))
        x = margin if cfg.get("corner") == "tl" else W - w - margin
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.paste(logo, (x, margin)) # verbatim copy (no mask): the ground is fully transparent, and a
        layer.save(dst)                # masked paste would re-blend the logo's own alpha against it (op²)
        return dst
    except Exception as e:
        print(f"[render] warning: brand bug skipped — logo unusable: {rel} ({e})")
        return None


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

    if _bug_wanted(meta, slide):                      # before _edge_filter (both branches) — the bug rides the seam
        bug_png = os.path.join(workdir, f"sbug_{(slide or {}).get('index', 0):02d}.png")
        if _brand_bug_png(meta, W, H, bug_png):       # None = unreadable logo (warned) — render on without it
            extra_inputs += ["-i", bug_png]
            parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0[v{n_in}]"); vlabel = f"v{n_in}"; n_in += 1

    band_text = None; band_bg = None                   # per-scene sampled caption text colour + strip ground
    def _add_caption_overlays():
        nonlocal vlabel, n_in
        for k, seg in enumerate(caption_segs):
            if not (seg.get("text") or "").strip():
                continue
            # index-scoped like every other per-scene artifact in the shared workdir (sbug_/cap_/
            # scene_ frames) — the sequential loop makes a bare k safe today, a parallel one wouldn't
            cap_png = os.path.join(workdir, f"scap_{(slide or {}).get('index', 0):02d}_{k:03d}.png")
            _caption_layer(seg["text"], W, H, cap_png, meta, hl_word=seg.get("hl"), band=band, text_rgb=band_text, band_bg=band_bg, hl_span=seg.get("hl_span"))
            extra_inputs.append("-i"); extra_inputs.append(cap_png)
            en = f"between(t,{seg['start']},{seg['end']})"
            parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0:enable='{en}'[v{n_in}]")
            vlabel = f"v{n_in}"; n_in += 1

    if band:                                           # edge-treat the content, add the strip, then the captions
        ep, vlabel = _edge_filter(meta, dur, slide, vlabel, W, H)
        parts.extend(ep)
        bg, band_text = _caption_band_fill(meta, pattern % 0)   # strip continues THIS scene's own ground
        band_bg = _ffhex_rgb(bg)                        # the strip ground, for the highlight-contrast pick
        parts.append(f"[{vlabel}]pad={W}:{H + band}:0:0:color={bg}[vpad]"); vlabel = "vpad"
        _add_caption_overlays()
    else:                                              # overlay (no bar): sample the ground UNDER the caption so its
        band_bg = _sample_region_color(pattern % 0)    # ink/outline/karaoke adapt to a photo/tint/letterbox
        _add_caption_overlays()
        ep, vlabel = _edge_filter(meta, dur, slide, vlabel, W, H)
        parts.extend(ep)
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
    if slide["type"] == "cinematic" or slide.get("layers") or slide.get("lens"):
        raise RuntimeError("scene %s is a cinematic scene (type 'cinematic' / layers / lens) — it renders "
                           "on the Remotion tier only. Set meta.renderer:'remotion' (validate.py flags this "
                           "before render)." % slide.get("index"))
    if not hasattr(scenes, "render_" + slide["type"]):
        raise RuntimeError("scene %s: no renderer for type '%s' (known: title/slide/html/chart/timeline/"
                           "keypoints/compare)" % (slide.get("index"), slide["type"]))
    renderer = getattr(scenes, "render_" + slide["type"])   # render_title / render_chart / render_timeline
    # expose this scene's narration so render_html can estimate reveal cues from text position when
    # there are no per-word timings (non-edge voices). Scenes render sequentially, so this is safe.
    meta["_narration"] = slide.get("narration") or ""
    meta["_slide"] = slide          # its out-transition decides how late a cued reveal may start (scenes.py)
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
    _fit_frame(os.path.join(meta["_out"], slide["image"]), frame, W, H, slide.get("fit", "contain"),
               bg_rgb=_theme_rgb(meta.get("_out", "."), "--bg", (13, 17, 23)))
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
    # Brand bug — an ffmpeg overlay input (like callouts), NOT a paste into the source frame: the
    # frame rides zoompan, so a baked-in bug would zoom/pan with the Ken Burns move. Composited here,
    # BEFORE _edge_filter in both caption modes, so the bug dips/travels with the seam.
    if _bug_wanted(meta, slide):
        bug_png = os.path.join(workdir, f"bug_{i:02d}.png")
        if _brand_bug_png(meta, W, H, bug_png):        # None = unreadable logo (warned) — render on without it
            extra_inputs += ["-i", bug_png]
            parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0[v{n_in}]"); vlabel = f"v{n_in}"; n_in += 1
    band = _caption_band_px(meta, W, H)                # >0 -> captions in a strip BELOW the content
    segs = (_caption_karaoke_segs(slide, meta, meta["_out"]) or _captions_for(slide)) if burn_captions else []

    band_text = None; band_bg = None                   # per-scene sampled caption text colour + strip ground
    def _cap_overlays():
        nonlocal vlabel, n_in
        for k, seg in enumerate(segs):
            if not (seg.get("text") or "").strip():
                continue
            cap_png = os.path.join(workdir, f"cap_{i:02d}_{k:02d}.png")
            _caption_layer(seg["text"], W, H, cap_png, meta, hl_word=seg.get("hl"), band=band, text_rgb=band_text, band_bg=band_bg, hl_span=seg.get("hl_span"))
            extra_inputs.append("-i"); extra_inputs.append(cap_png)
            en = f"between(t,{seg['start']},{seg['end']})"
            parts.append(f"[{vlabel}][{n_in}:v]overlay=0:0:enable='{en}'[v{n_in}]")
            vlabel = f"v{n_in}"; n_in += 1

    if band:                                           # edge-treat content, add the strip, then the captions
        ep, vlabel = _edge_filter(meta, dur, slide, vlabel, W, H)
        parts.extend(ep)
        bg, band_text = _caption_band_fill(meta, frame)    # strip continues THIS scene's own ground
        band_bg = _ffhex_rgb(bg)                        # the strip ground, for the highlight-contrast pick
        parts.append(f"[{vlabel}]pad={W}:{H + band}:0:0:color={bg}[vpad]"); vlabel = "vpad"
        _cap_overlays()
    else:                                              # overlay (no bar): sample the ground UNDER the caption so its
        band_bg = _sample_region_color(frame)          # ink/outline/karaoke adapt to a photo/tint/--bg letterbox
        _cap_overlays()
        ep, vlabel = _edge_filter(meta, dur, slide, vlabel, W, H)
        parts.extend(ep)
    fcomplex = ";".join(parts)

    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", frame, "-i",
           os.path.join(meta["_out"], slide["audio"])] + extra_inputs + [
        "-filter_complex", fcomplex, "-map", f"[{vlabel}]", "-map", "1:a",
        "-t", f"{dur}", "-r", str(fps), "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-ar", "48000", "-ac", "1", "-shortest", out_clip]
    _common.run(cmd)
    return out_clip

def render(out_dir, sample=None, vertical=False, only=None, reduced_motion=False, preview=False):
    data = sb.load(os.path.join(out_dir, "storyboard.json"))
    sb.validate(data)
    meta = data["meta"]; meta["_out"] = out_dir
    # PREVIEW tier — cheap design iteration (~1.4-2x wall-clock; 2.5x fewer captures): 12fps captures + lighter JPEG, its OWN clip
    # cache (.clips_preview) and preview.mp4 output, so it never pollutes the full-quality cache or
    # out.mp4. Temporally IDENTICAL to the full render (fps only changes sampling density — captions,
    # cues and word-sync are all time-based), just choppier. The full render stays the delivery path.
    if preview:
        meta = dict(meta, fps=12, jpeg_quality=70)
        meta["_out"] = out_dir
    # D — reduced-motion tier (accessibility): CLI flag OR meta.reduced_motion. Kills zoom/pan on the
    # image tier and swaps HTML reveals to opacity-only fades; still deterministic + seekable.
    meta["reduced_motion"] = bool(reduced_motion or meta.get("reduced_motion"))
    # meta.aspect is authoritative; the --vertical flag also forces it (either makes it 9:16).
    vertical = vertical or meta.get("aspect") == "9:16"
    W, H = _canvas(meta, vertical)
    burn = bool(meta.get("captions", True))
    ss = max(1, int(meta.get("motion_ss", 2)))
    # first/last scene indices for the brand bug's skip rule (bug + authored cover/endcard lockup
    # on one frame is a double-brand) — also honoured by a --sample of an edge scene
    if data["slides"]:
        meta["_first_index"] = data["slides"][0]["index"]
        meta["_last_index"] = data["slides"][-1]["index"]

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
    clipdir = os.path.join(out_dir, ".clips_preview" if preview else ".clips")
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
        dst = os.path.join(out_dir, "preview.mp4" if preview else "out.mp4")
        _common.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
                     "-c", "copy", "-movflags", "+faststart", dst])
        if not preview:                       # srt belongs to the delivery artifact only
            _write_srt(data, os.path.join(out_dir, "out.srt"))
        print(f"({rendered} slide(s) rendered, {len(clips) - rendered} reused from cache; "
              f"{time.monotonic()-t_all:.1f}s total)")
        if not preview:
            _not_delivered(out_dir, data)
        return dst


# THE RENDER DOES NOT END ON A GREEN LIGHT — on this tier either. render_remotion.py leaves NOT_DELIVERED.md beside
# out.mp4 with the steps that remain, and critic_ledger.py --final is the only thing that removes (or rewrites) it;
# promote.py refuses a film that still has it. This tier wrote nothing, so an HTML film read as delivered the moment
# out.mp4 existed, and its components could be promoted from a film no critic had seen. Only the FULL render writes
# it: the step-8 `--sample` (sample.mp4) and `--preview` (preview.mp4) return before this, and neither writes nor
# removes the marker, because neither is the film a review covers. Only an HTML film (validate.is_html_film): the
# 原样配音 / programmatic-only tier has no ledger to clear it, and a marker nothing can remove is a lie by `ls`.
_NOT_DELIVERED = "NOT_DELIVERED.md"

_HTML_NEXT_STEPS = '''# RENDERED, not DELIVERED

`out.mp4` existing is not the same claim as this film being deliverable. The machine gates measure whether a page
is blank, overflows, lands with its word and plays in sync. NONE of them can ask whether a page MEANS what its beat
means, whether its numbers trace to the source, or whether the burned captions read.

That half is the rendered review's — `agents/design-critic.md` ("Rendered review — the delivery ledger", the
H-dimensions), with `agents/critic-av.md`'s lens — and it has to be a reviewer who does not know what you meant to
draw: the maker holds the intent, and the intent is what makes a wrong page look right.

Run these in order. The last one deletes this file when the review passes:

```sh
python3 scripts/check_av.py       %(out)s          # must exit 0 first
python3 scripts/critic_brief.py   %(out)s          # keyframes + _frames/ + _contact_sheet.png + _critic_brief.md
python3 scripts/critic_ledger.py  %(out)s --emit-template
# dispatch agents/design-critic.md (its delivery section) as a SUBAGENT whose entire input is the path %(out)s —
#   no rationale, no summary of what you fixed, no steer about where to look (critic-av beside it on standard+)
# after applying fixes and re-rendering: python3 scripts/critic_brief.py %(out)s AGAIN (a new render id + history)
python3 scripts/critic_ledger.py  %(out)s --final
#   exit 0 means the LEDGER is well formed — NOT that the film may ship. The verdict is what
#   ships it: --final prints `the FILM is not delivered` on a REVISE and still exits 0.
```
'''


def _not_delivered(out_dir, data):
    """Leave the remaining work IN the deliverable, not only in the log (an HTML film's full render only)."""
    import validate as _v
    if not _v.is_html_film(data.get("meta") or {}, data.get("slides") or []):
        return
    try:
        with open(os.path.join(out_dir, _NOT_DELIVERED), "w", encoding="utf-8") as fh:
            fh.write(_HTML_NEXT_STEPS % {"out": out_dir})
    except OSError as e:
        print("[render] could not write %s (%s) — the review below is still owed" % (_NOT_DELIVERED, e))
    print("[render] RENDERED, not DELIVERED — wrote %s with the remaining steps." % _NOT_DELIVERED)
    print("[render] next: python3 scripts/critic_brief.py %s, then agents/design-critic.md's delivery review "
          "(input = the out_dir path, nothing else), then python3 scripts/critic_ledger.py %s --final — read its "
          "VERDICT line: a REVISE exits 0 too and the film is NOT delivered" % (out_dir, out_dir))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--vertical", action="store_true")
    ap.add_argument("--reduced-motion", action="store_true",
                    help="accessibility: no zoom/pan + opacity-only reveals (still deterministic/seekable)")
    ap.add_argument("--renderer", choices=["local", "remotion", "remotion-legacy"], default=None,
                    help="override meta.renderer; 'remotion' = the bespoke-shot cinematic tier (recommended); "
                         "'remotion'/'remotion-legacy' = the deprecated generic-scene tier")
    ap.add_argument("--preview", action="store_true",
                    help="cheap iteration render: 12fps, own cache (.clips_preview), writes preview.mp4 — never touches out.mp4/.clips")
    a = ap.parse_args()
    # Renderer dispatch: any Remotion tier (bespoke remotion OR the legacy generic-scene remotion) renders the
    # whole storyboard at once via render_remotion, which internally picks the tier from meta.renderer.
    meta = (sb.load(os.path.join(a.out_dir, "storyboard.json")).get("meta") or {})
    if (a.renderer or meta.get("renderer", "local")) in ("remotion", "remotion-legacy"):
        if a.only:
            print("[render] note: the remotion tier has no --only; rendering the whole deck.")
        import render_remotion
        print(f"Rendered -> {render_remotion.render(a.out_dir, vertical=a.vertical, reduced_motion=a.reduced_motion, sample=a.sample)}")
        return
    res = render(a.out_dir, sample=a.sample, vertical=a.vertical, only=a.only,
                 reduced_motion=a.reduced_motion, preview=a.preview)
    print(f"Rendered -> {res}")

if __name__ == "__main__":
    main()
