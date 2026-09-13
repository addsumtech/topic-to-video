"""Pre-render correctness gate for storyboard.json. Runs in ~1s and catches the failures
that otherwise waste a full (minutes-long) render: a referenced image/audio/page/font that
doesn't exist on disk, a duplicate scene index, an html scene whose `file://` assets or
theme.css are missing, a caption that wraps into a wall of text, an over-zealous zoom, a
CJK language with no system font (tofu), or audio/duration not yet synthesised.

Mirrors check_av.py: a pure `evaluate(data, out_dir)` core, a thin `check(out_dir)` IO
wrapper, and a `main()` that prints a human summary (or --json) and exits non-zero on any
ERROR so the workflow can gate on it BEFORE render.py. ERRORS block; warnings don't.

Run it AFTER tts.py and BEFORE render.py (step 9). Use --pre-tts to validate earlier
(skips the audio/duration checks), e.g. right after authoring the storyboard.
"""
import argparse, json, math, os, re, sys
import unicodedata
from html.parser import HTMLParser


def _disp_width(s):
    """Display width of a string for FIXED-WIDTH box lints: a full/wide east-asian glyph (W/F) counts as 2,
    since it fills a fixed-px box twice as fast as a Latin 'i'. A codepoint count under-fires on CJK decks."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in str(s))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common
import storyboard as sb
import re
import render as rd                       # caption-fit + font helpers, reused verbatim
import cues as _cues                      # anchor matcher (timed-callout cues + reveal alignment)

# A zoom delta beyond this reads as a lurch, not a gentle Ken Burns (SKILL.md / motion-grammar).
MAX_ZOOM_DELTA = 0.20
# A static frame held longer than this drags even with motion (SKILL.md pacing guardrail).
PACE_CEILING_S = 8.0
# A caption that needs more than this many wrapped lines is a wall of text on screen.
MAX_CAPTION_LINES = 3
# A burned caption flashed for less than this reads faster than a viewer can follow.
# Netflix Timed Text Style Guide (published, primary) — the only source found that gives real numbers
# for CJK, and they are NOT a translation of the Latin ones: Simplified Chinese caps at 9 characters per
# second against English's 20, and 16 characters per line against 42. A Chinese caption therefore carries
# roughly 38% of the characters and 45% of the reading-speed budget of the English line it came from, so an
# English-density script translated 1:1 into the same box cannot be read.
MIN_CAPTION_SECONDS = 0.833        # 5/6 s absolute floor, any length, any language
MAX_CAPTION_SECONDS = 7.0          # ceiling — past this a caption reads as stuck
CPS_CJK, CPS_LATIN = 9.0, 20.0     # adult reading speed, characters per second
CJK_CHARS_PER_LINE = 16            # zh-Hans per-line ceiling
# A Latin caption line that ends on a lone short word ("…to the / future") reads as a typo.
DANGLING_WORD_MAX_CHARS = 8
# A single cue denser than this is a wall even when it wraps to <= MAX_CAPTION_LINES (line count
# alone misses a 2-line-but-packed CJK cue). CJK glyphs are full-width, so the ceiling is tighter.
MAX_CAPTION_CHARS_CJK = 36
MAX_CAPTION_CHARS_LATIN = 90
# A caption ending on a clause mark looks cut-off mid-thought at the line break.
TRAIL_CLAUSE_MARKS = "，、：；,;:"
# Reveal-vs-voice alignment: a point should appear ~when the narration speaks it. Flag a point whose
# reveal leads/lags the voice by more than this fraction of the scene AND at least this many seconds.
ALIGN_FRAC_TOL = 0.25
ALIGN_SECS_TOL = 1.2
# Cue-triggered animation truncated by the scene cut. Below this completion fraction the frozen
# last frame reads as visibly broken (a connector stopping in mid-air) -> ERROR; a marginal
# shortfall above it is cosmetic -> WARNING.
TRUNCATION_ERROR_FRAC = 0.90
# Layout-diversity gate: warn when one form family exceeds this share of the html scenes.
LAYOUT_FAMILY_MAX_SHARE = 0.45
# When a callout is this far (in normalized frame units) from where the camera settles, the
# motion isn't framing it — the highlight and the push disagree.
MOTION_ALIGN_TOL = 0.25

_FILE_REF_RE = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"')
# hardcoded-hex lint (KB "one primary + one accent; accent==meaning"): enforce the semantic-var
# contract deterministically. Scan ONLY color contexts — a style="…" value, an SVG fill/stroke/
# stop-color attr, or an inline <style> block — so a deck that legitimately DISPLAYS a hex string as
# content never false-positives. Match a CSS-legal color token only (3/6/8 hex digits, non-hex left
# boundary) so an SVG id ref like url(#face) / a 4-5 char #dead can't trip it.
_COLOR_CTX_RE = re.compile(
    r'style\s*=\s*"([^"]*)"|(?:fill|stroke|stop-color)\s*=\s*"([^"]*)"|<style[^>]*>(.*?)</style>',
    re.I | re.S)
_HEX_TOKEN_RE = re.compile(r'(?<![0-9a-fA-F#])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')

# --- HTML reveal / composition analysis (one-by-one reveals, arrows-with-blocks, freshness) ------
# A "reveal" is a CSS class that starts opacity:0 + paused (base.css); WHEN it fires is set by a
# data-cue-index (spoken order). One meaningful component = one cued reveal → components land one-by-one.
_REVEAL = {"reveal", "reveal-up", "reveal-up-sm", "reveal-pop", "reveal-wipe", "reveal-glow"}
_CHROME = {"kicker", "rule", "title", "sub"}          # the only elements allowed to be uncued on a cued page
# ...in the BUILT-IN vocabulary. A deck with its own register names its header chrome whatever the
# register calls it (.a-cap, .masthead, .plate-tag), and a class whitelist cannot know those — it
# once put a false "page sits BLANK" warning on all 41 pages of a deck whose every page opened with
# a static kicker. The question is not what the class is called; it is whether any TEXT is on screen
# at t=0. That is: an element with real text, no cue, and no entrance animation to wait for.
# NOTE an entrance class is deliberately NOT disqualifying. An UNCUED .reveal runs on the blind
# stagger, i.e. it fades in immediately and lands inside the renderer's head window — the page is not
# "blank while the opening plays". Only a CUED element waits for a phrase that may be spoken late,
# which is the failure this check exists to catch.


def _has_static_opening_text(html):
    """True when some element paints TEXT at t=0 — uncued, unanimated, non-empty.

    Only LEAF elements count. A wrapper like `<div class="stage">` inherits its children's text
    while carrying none of its own, so counting containers would call every cued page "not blank"
    and silence the check entirely.
    """
    body = html[html.find("<body"):] if "<body" in html else html
    # Match each OPENING tag and only the text directly after it, before any child tag. Pairing
    # tags with a regex cannot survive nesting — an outer <div class="stage"> swallows the kicker
    # inside it and the kicker is never examined — and direct text is exactly what "this element
    # paints" means anyway.
    for m in re.finditer(r'<(div|p|span|h[1-6])\b([^>]*)>([^<]*)', body, re.I):
        attrs, direct = m.group(2), m.group(3)
        if "data-cue-index" in attrs:
            continue
        if re.sub(r"&[a-z#0-9]+;|\s", "", direct):    # real glyphs, not an entity or whitespace
            return True
    return False
_CONN = {"arrow", "hs-connect", "connector"}          # connectors — reveal WITH their destination block
#   `.arrow`/`.hs-connect` are the archetype connectors; `.connector` is the GENERAL marker an author
#   puts on ANY directional element that borrows a cue slot (a bespoke SVG arc/chevron/link that reveals
#   WITH the line it belongs to, carrying no data-cue of its own) — so it's exempt from the duplicate/
#   uncued accounting exactly like the built-in connectors, and never left static (frame-0) on a cued page.
# Independently-meaningful facts = distinct LINE-ITEMS (row/tile/step/block/seg/hs-spoke) or a PRIMARY
# number (stat/num). Pure descriptors attached to a number or a row (.label/.note/.bar/.delta/.unit) are
# part of that ONE unit, NOT separate facts — so a "label: value" row or "5.6% ▲" counts as one point.
# (Only the OUTERMOST such node per branch is counted, so a tile wrapping a labeled row is one fact.)
_MEAN = {"stat", "num", "row", "tile", "step", "block", "seg", "hs-spoke", "tl-node"}
_VOID = {"img", "br", "hr", "input", "meta", "link", "source", "path", "circle", "rect", "line",
         "polyline", "polygon", "use", "stop", "ellipse"}
_BG_CLASSES = {"bg-soft", "bg-soft-tint", "bg-photo", "accent-fill", "bg-stars", "bg-glow", "bg-paper",
               "bg-motif", "bg-grid"}


class _DomNode:
    __slots__ = ("tag", "classes", "cue", "parent", "idx")
    def __init__(self, tag, classes, cue, parent, idx):
        self.tag, self.classes, self.cue, self.parent, self.idx = tag, classes, cue, parent, idx


class _DomParser(HTMLParser):
    """Minimal nesting parser: records each element's tag, class set, data-cue-index, and parent idx.
    handle_endtag pops DOWN TO the nearest open element of the matching tag (auto-closing any
    optional-close tags left open, e.g. an unclosed <p>/<li>), and ignores a stray end tag — so an
    unclosed <p> inside a flow step no longer re-parents the following .arrow off the flow. This keeps
    the CONNECTOR-ORDERING check (which appends an ERROR) reliable on imperfect-but-browser-valid HTML;
    the parser is still best-effort and returns [] on any exception."""
    def __init__(self):
        super().__init__()
        self.nodes, self.stack = [], []
    def _open(self, tag, attrs):
        d = dict(attrs)
        cue = d.get("data-cue-index")
        try:
            cue = int(cue) if cue is not None else None
        except (TypeError, ValueError):
            cue = None
        idx = len(self.nodes)
        self.nodes.append(_DomNode(tag, set((d.get("class") or "").split()), cue,
                                   self.stack[-1] if self.stack else None, idx))
        return idx
    def handle_starttag(self, tag, attrs):
        idx = self._open(tag, attrs)
        if tag not in _VOID:
            self.stack.append(idx)
    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs)                        # self-closing: opened + closed, never pushed
    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):  # pop to the matching open tag; stray end tag → no-op
            if self.nodes[self.stack[i]].tag == tag:
                del self.stack[i:]
                return


def _parse_dom(html):
    try:
        p = _DomParser(); p.feed(html); return p.nodes
    except Exception:
        return []


def _composition_sig(html):
    """Coarse composition signature for the diversity gate: the visual ENVELOPE (vertical anchor ×
    horizontal balance), whether the page opens with a kicker hat, whether it's a full-bleed hero,
    and whether it has ANY backdrop element (else a bare --bg 'flat' page)."""
    # match the WHOLE <div class="stage" …> open-tag so `style` is read regardless of attribute order
    # (a `<div style="…" class="stage">` previously missed the style → false CENTER-anchor warnings).
    sm = re.search(r'<[^>]*\bclass\s*=\s*"[^"]*\bstage\b[^"]*"[^>]*>', html)
    style = ""
    if sm:
        st = re.search(r'style\s*=\s*"([^"]*)"', sm.group(0))
        style = st.group(1) if st else ""
    # The ENVELOPE classes (base.css "VERTICAL composition") are the supported way to set the vertical
    # band; read them FIRST, since they are a declaration the author made on purpose. Inline
    # justify-content stays supported as the escape hatch.
    _cls_anchor = None
    for _c, _a in (("band-upper", "top"), ("band-lower", "bottom"),
                   ("anchor-top", "top"), ("anchor-bottom", "bottom"), ("bleed", "full")):
        if re.search(r'class\s*=\s*"[^"]*\bstage\b[^"]*\b' + _c + r'\b', html) \
                or re.search(r'class\s*=\s*"[^"]*\b' + _c + r'\b[^"]*\bstage\b', html):
            _cls_anchor = _a
            break
    # html-pages.md teaches overriding `.stage{…justify-content:…}` in a <style> block; reading only
    # the style= ATTRIBUTE made those pages silently vote "center" (the default) with full confidence.
    if not re.search(r'justify-content', style):
        _blk = re.search(r'<style[^>]*>(.*?)</style>', html, re.S)
        if _blk:
            _rule = re.search(r'\.stage[^{}]*\{[^{}]*justify-content\s*:\s*([\w-]+)', _blk.group(1))
            if _rule:
                style += f";justify-content:{_rule.group(1)}"
    jc = re.search(r'justify-content\s*:\s*([\w-]+)', style)
    jc_seen = bool(jc) or _cls_anchor is not None
    jc = jc.group(1) if jc else "center"
    anchor = _cls_anchor or ("top" if jc in ("flex-start", "start") else "bottom" if jc in ("flex-end", "end")
                             else "full" if jc.startswith("space") else "center")
    # off-center/thirds bands park the content in one horizontal third with a deliberate void — a
    # genuine left/right-weighted balance the composition gate should CREDIT (not a centered column).
    # `(?<![\w-])...(?![\w-])` are token boundaries so a hyphenated superstring (e.g. "grid-thirds") is
    # NOT mis-credited — only the exact frame-left/frame-right/thirds classes count.
    _off = r'(?<![\w-])(?:frame-left|frame-right|thirds)(?![\w-])'
    if re.search(r'class\s*=\s*"[^"]*\bstage\b[^"]*' + _off, html) \
            or re.search(r'class\s*=\s*"[^"]*' + _off + r'[^"]*\bstage\b', html):
        balance = "offset"
    # `.split` is a PAGE layout (motifs.css sizes it as its own 1920×1080 container) and `.grid-asym`
    # only rebalances the frame when it IS the stage's layout. Credited from anywhere in the source, a
    # single nested sub-panel on a dead-centred page counted as "breaks the centered column" — so
    # require them at page level: outside the stage subtree, or on the stage itself.
    elif _at_page_level(html, sm, "split"):
        balance = "split"
    elif _at_page_level(html, sm, "grid-asym"):
        balance = "asym"
    elif "text-align:center" in style.replace(" ", ""):
        balance = "centered"
    else:
        balance = "twocol"
    # STATICALLY MEASURABLE? anchor/balance above are read off the .stage's FLEX signature + a handful
    # of layout classes. A page that lays itself out with absolutely-positioned children has neither,
    # so those two fields are not observations — they are the defaults ("center"/"centered"). Reporting
    # them as findings produces a CONFIDENT FALSE READING (a deck measured 12-left/8-mid/7-right by DOM
    # was reported as "0% break the centered column"), which is worse than staying silent: it sends the
    # author chasing a non-problem and hides the real one. Detect the idiom and abstain — keyframe_qa
    # measures these pages properly from real element boxes.
    # Count absolute positioning INSIDE the stage subtree only — the backdrops/vignettes that every
    # page stacks behind .stage are absolute by design and must not make a normal flex page look
    # unmeasurable. And `jc_seen` must NOT rescue the verdict: flex properties do not lay out
    # absolutely-positioned children, so a page that declares justify-content AND positions its
    # content absolutely is exactly the confident-false-reading case, not an exemption from it.
    abs_kids = len(re.findall(r'position\s*:\s*absolute', html[(sm.start() if sm else 0):]))
    measurable = abs_kids < 5
    kicker_first = bool(re.search(r'class\s*=\s*"[^"]*\bstage\b[^"]*"[^>]*>\s*<[^>]*class\s*=\s*"[^"]*\bkicker\b', html))
    hero = bool(re.search(r'class\s*=\s*"[^"]*\bbg-photo\b', html))
    # an image-forward page (.media/.split panel or a full-bleed .bg-photo) is NOT a flat wall, even
    # with no .bg-soft — mirror the AI-look flat exemption so an image-rich deck isn't false-flagged.
    img_rich = bool(re.search(r'class\s*=\s*"[^"]*\b(?:media|split|bg-photo)\b', html))
    flat = not img_rich and not any(re.search(r'class\s*=\s*"[^"]*\b' + re.escape(c) + r'\b', html) for c in _BG_CLASSES)
    return {"anchor": anchor, "balance": balance, "kicker_first": kicker_first, "hero": hero, "flat": flat,
            "measurable": measurable}


def _at_page_level(html, stage_match, cls):
    """True when `cls` governs the PAGE's balance rather than sitting in a nested sub-panel: it is on
    the stage element itself, or it appears before the stage opens (i.e. it IS the page container)."""
    pat = r'class\s*=\s*"[^"]*\b' + re.escape(cls) + r'\b'
    if stage_match is not None and re.search(pat + r'[^"]*\bstage\b|\bstage\b[^"]*' + re.escape(cls),
                                             stage_match.group(0)):
        return True
    hit = re.search(pat, html)
    if not hit:
        return False
    return stage_match is None or hit.start() < stage_match.start()


def _exists(out_dir, rel):
    return bool(rel) and os.path.exists(os.path.join(out_dir, rel))


def _local_path_from_url(url):
    """Resolve a stylesheet/script/image URL from an html page to a local filesystem path,
    or None if it's a remote/data URI (which an html scene must not use). Strips the
    `?p=...&cues=...` query seek params and percent-decodes the path."""
    from urllib.parse import unquote, urlparse
    if url.startswith(("http://", "https://", "//")):
        return False                                   # NETWORK asset — not allowed (non-deterministic)
    if url.startswith("data:"):
        return None                                    # inline data: URI — offline + deterministic, allowed
    u = url.split("?", 1)[0]
    if u.startswith("file://"):
        return unquote(urlparse(u).path)
    return None                                        # relative/unknown — skip (can't resolve)


def _caption_lines(text, meta, W, H):
    """The lines this caption wraps to at the burned-in font/width (render.py's exact logic)."""
    from PIL import Image, ImageDraw
    if not (text or "").strip():
        return []
    font = rd._load_font(rd._caption_font_px(W, H, band=(meta or {}).get("caption_mode") == "band", meta=meta),
                         rd._font_path(meta, text))  # narrow-dim scaled + caption_scale/band-aware
    d = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    return rd._wrap(d, text, font, int(W * 0.9))


def _dangling_word(lines):
    """A Latin caption whose last wrapped line is a single short word (typographic widow)."""
    if len(lines) < 2:
        return None
    last = lines[-1].strip()
    if " " not in last and not rd._CJK_RE.search(last) and 0 < len(last) <= DANGLING_WORD_MAX_CHARS:
        return last
    return None


def _cjk_font_ok(meta):
    """For a CJK language, does a glyph-covering font resolve? If not, captions will tofu."""
    lang = (meta.get("language") or "").lower()
    probe = {"zh": "中", "ja": "あ", "ko": "가"}.get(lang[:2])
    if not probe:
        return True                                    # not a CJK language -> N/A
    return rd._font_path(meta, probe) != rd.BUNDLED_FONT


def _edge_tts_available():
    try:
        import edge_tts  # noqa: F401
        return True
    except Exception:
        return False


# A STATISTIC form on a slide — the shapes a fabricated "confident number" most often takes: a percent,
# an ×/x multiplier, currency, "percent"/"pct", "-fold", or a magnitude suffix (k/M/B/million/…). A plain
# bare count ("5 agents", "3 steps") is usually structural, so it's deliberately NOT matched (too noisy);
# these UNIT-BEARING forms are high-signal and rarely coincidental. Each alternative captures the numeric
# VALUE in its own group; _figure_traceability takes whichever group matched.
_STAT_RE = re.compile(
    r"(?<![\w.])(?:"
    r"(\d+(?:\.\d+)?)\s?[%×]"                                                   # 50%   3×
    r"|(\d+(?:\.\d+)?)\s?[xX](?![\w])"                                          # 3x    (not 'matrix')
    r"|[$€£¥]\s?(\d+(?:\.\d+)?)"                                                # $4.2
    r"|(\d+(?:\.\d+)?)\s?(?:percent|pct)\b"                                     # 50 percent
    r"|(\d+(?:\.\d+)?)-fold\b"                                                  # 2.3-fold
    r"|(\d+(?:\.\d+)?)\s?(?:k|K|M|B|bn|billion|million|trillion|thousand)\b"    # 4.2M  3 billion
    r")", re.I)


def _brief_numbers(out_dir):
    """Numeric tokens that appear in `brief.json`'s **evidence** (the CITED facts) — the set a slide
    statistic must trace to. None when there's no brief (skip; the content-critic owns faithfulness).
    Collecting from `evidence` (NOT the whole brief) is deliberate: a figure must come from a cited
    fact, not from a rhetorical framing that lives in the thesis / misconceptions / why_it_matters — an
    invented "43%" placed only in a punchy framing (not in cited evidence) must still be caught."""
    if not out_dir:
        return None            # `_check_remotion(out_dir=None)` is a documented call shape; joining None
                               # raised TypeError instead, so the whole remotion check died on it
    try:
        b = json.load(open(os.path.join(out_dir, "brief.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return set(re.findall(r"\d+(?:\.\d+)?", json.dumps(b.get("evidence") or [], ensure_ascii=False)))


def _visible_text(out_dir, rel):
    """Best-effort VISIBLE text of an html page — drop <style>/<script>/<svg> blocks (their CSS/SVG
    coordinates are not content), then strip tags (which also removes inline `style=` numbers). So a
    figure found here is a real on-screen claim, not a layout coordinate."""
    p = _local_path_from_url("file://" + os.path.abspath(os.path.join(out_dir, rel))) \
        if not str(rel).startswith("file://") else _local_path_from_url(rel)
    try:
        t = open(p or os.path.join(out_dir, rel), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""
    t = re.sub(r"<(style|script|svg)\b.*?</\1>", " ", t, flags=re.S | re.I)
    # drop UI-idiom chrome text (a zoom badge's "100%", window-chrome labels): a LEAF element marked
    # `data-ui` declares "this text is interface idiom, not a content claim" — excluded from the
    # figure-traceability scan so authors never mutate chrome text to dodge the lint (the failure mode:
    # "100%"→"1:1" satisfied the machine and confused every human; see html-pages.md Decodability rule).
    t = re.sub(r"<(\w+)\b[^>]*\bdata-ui\b[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def _figure_traceability(slides, out_dir, warnings):
    """Deterministic backstop for truthful content: every STATISTIC (%/× ) spoken or shown must trace to
    a number in `brief.json` (the sourced evidence). A stat whose value is absent from the brief is likely
    INVENTED — WARN (not ERROR: a figure can be legitimately DERIVED or phrased differently, and the
    content-critic is the semantic judge that FAILs a confirmed fabrication). No brief → skip."""
    nums = _brief_numbers(out_dir)
    if nums is None:
        return
    for s in slides:
        idx = s.get("index")
        texts = [s.get("narration") or ""]
        props = s.get("props") or {}
        # For a PROGRAMMATIC scene, props ARE the on-screen strings. For an `html` scene they are
        # authoring metadata (form notes, layout hints like "2×2", cue arrays) and the real screen
        # text is read from the page below — scanning both made a layout note read as a fabricated
        # statistic, which erodes the one gate that guards against invented numbers.
        if s.get("type") not in ("slide", "html"):
            texts.append(json.dumps(props, ensure_ascii=False))     # animated on-screen strings
        sp = s.get("shot_props")
        if sp:
            texts.append(json.dumps(sp, ensure_ascii=False))        # remotion: figures shown via shot_props
        if props.get("html"):
            texts.append(_visible_text(out_dir, props["html"]))     # html-page on-screen text
        seen = set()
        for txt in texts:
            for m in _STAT_RE.finditer(txt or ""):
                stat = m.group(0).strip()
                val = next((g for g in m.groups() if g is not None), None)   # numeric value across the alternation
                if val is None or val in nums or stat in seen:
                    continue
                seen.add(stat)
                warnings.append(f"scene {idx}: figure '{stat}' isn't in brief.json evidence — every statistic "
                                f"must trace to the source; cite it, reframe qualitatively, or (if it's derived "
                                f"or a hypothetical) confirm it — no invented numbers (see the faithfulness gate)")


_CINE_KINDS = {"fill", "grid", "floor", "hero", "panel", "image"}
_CINE_EASINGS = {"linear", "in", "out", "inout", "house"}  # `house` = the shared premium expo-out settle (default)
# A GENERATED (Codex/`atmosphere`) image can render texture/mood/material but NOT legible text, UI chrome,
# data marks, or logos — asking for them yields garbled glyphs (that content belongs on the code-drawn
# plane). Used to WARN on a gen backplane prompt that requests them. (The "AI = background, code = data"
# split, made mechanical for the cinematic depth-plane path.)
_GEN_PROMPT_FORBIDDEN = re.compile(
    r"\b(text|words?|letter|lettering|label|caption|title|headline|paragraph|typograph\w*|"
    r"UI|interface|screenshot|dashboard|chart|graph|plot|axis|legend|table|"
    r"logo|wordmark|brand\s?mark|number|digits?|percent|data)\b", re.I)
_SHOT_TYPES = {"ESTABLISH", "MEDIUM", "CLOSEUP", "OVER_SHOULDER", "REVEAL", "HERO"}
_ELEM_KINDS = {"panel", "image", "textblock", "callout", "grid", "floor", "hero", "fill", "card", "metaphor", "display", "terminal", "spotlight", "hud", "connector"}  # ElementKind (elements.tsx); card=Path-A html form, metaphor=materialized verb, display=giant kinetic type, terminal=streaming CLI, spotlight=travelling light-pool, hud=FUI reticle+readout, connector=draw-on line
_METAPHOR_CONCEPTS = {"widening-gap", "physical-fall", "filling-vessel", "diverging-pair", "converging-scatter"}
_METAPHOR_ARITY = {"widening-gap": 2, "physical-fall": 2, "filling-vessel": 1, "diverging-pair": 2}
# The per-beat DESIGN axis ((the removed legacy cinematic tier)). Chosen per cinematic scene; MUST vary across the
# film so every beat isn't the same glass panel reframed. Orthogonal to meta.style (the deck's one skin).
_ARCHETYPES = {"hero-on-void", "manifesto-monolith", "data-materializes", "metric-wall", "process-flow",
               "comparison-split", "system-map", "timeline-rail", "quadrant-position", "metaphor-mechanic",
               "device-focus", "world-immersion", "quote-testament", "exploded-assemble", "turntable-material"}
# signature beats that have a REAL renderer (a non-deliverable reserve archetype must not satisfy the gate).
# world-immersion = a native world the camera stands INSIDE (glyphrain/terminal/device) — a real native form.
_SIGNATURE_ARCHETYPES = {"metaphor-mechanic", "data-materializes", "manifesto-monolith", "world-immersion"}
_RESERVE_ARCHETYPES = {"exploded-assemble", "turntable-material"}  # named but no native renderer yet


def _archetype_of(s):
    return str(s.get("archetype") or (s.get("props") or {}).get("archetype") or "")


def _design_variety_lint(slides, errors, warnings):
    """DESIGN-VARIETY across the film (cinematic tier): the ARCHETYPE (each beat's bespoke design) must vary
    — not just the camera. The backstop for the design-sameness failure (every beat = one glass panel
    reframed): no archetype on >45% of beats, >=3 distinct, >=1 signature/metaphor beat, no back-to-back
    repeats. These BLOCK (errors) on a >=4-archetype film — a lazy same-look film must not render. CAVEAT
    kept honest: this reads the archetype STRING, not the rendered pixels, so 'labelled a different archetype
    but built the identical panel' still needs design-critic D12h; this gate catches the declared-sameness case."""
    arches = [_archetype_of(s) for s in slides if _archetype_of(s)]
    if len(arches) >= 4:
        top, n = max(((a, arches.count(a)) for a in set(arches)), key=lambda kv: kv[1])
        if n / len(arches) > 0.45:
            errors.append("design-variety: archetype '%s' is on %d/%d cinematic beats (>45%%) — vary the "
                          "per-beat DESIGN ((the removed legacy cinematic tier)); every beat the same look is the "
                          "design-sameness failure the tier exists to avoid" % (top, n, len(arches)))
        if len(set(arches)) < 3:
            errors.append("design-variety: only %d distinct archetype(s) across %d cinematic beats — a launch "
                          "film needs a fresh design idea per beat (>=3 distinct)" % (len(set(arches)), len(arches)))
        if not (_SIGNATURE_ARCHETYPES & set(arches)):
            errors.append("design-variety: no signature/metaphor beat (metaphor-mechanic / data-materializes / "
                          "manifesto-monolith) — add >=1 so the film has a memorable, topic-locked moment")
    for a, b in zip(slides, slides[1:]):
        aa, bb = _archetype_of(a), _archetype_of(b)
        if aa and aa == bb:
            errors.append("design-variety: scenes #%s and #%s share archetype '%s' back-to-back — consecutive "
                          "beats must reframe the DESIGN, not just the camera" % (a.get("index"), b.get("index"), aa))
_SHOT_MOTIONS = {"STATIC", "PUSH_IN", "PULL_OUT", "PAN_RIGHT", "PAN_LEFT", "TILT_UP", "TILT_DOWN",
                 "ORBIT_RIGHT", "ORBIT_LEFT", "RACK_FOCUS"}
# MIRROR render_remotion._MOTION_ALIASES so the bare survey names the docs teach (PAN/TILT/ORBIT/…) pass
# the gate and resolve to the same concrete direction the render uses.
_SHOT_MOTION_ALIASES = {"PAN": "PAN_RIGHT", "TILT": "TILT_UP", "ORBIT": "ORBIT_RIGHT",
                        "DOLLY": "PUSH_IN", "ZOOM": "PUSH_IN", "PUSH": "PUSH_IN", "PULL": "PULL_OUT"}


def _norm_motion(m):
    m = str(m).upper().replace("-", "_").replace(" ", "_")
    return _SHOT_MOTION_ALIASES.get(m, m)


# Per-kind SCREEN FOOTPRINT (half-width hw, top/bottom offset from the element's y), MIRRORING the fixed
# boxes in stage/elements.tsx (a `display` is a 1680-wide, 200px block centred on its position — NOT sized to
# its text). Used to catch two content elements placed so close they COLLIDE on the same depth plane — the
# "内容过近/重叠" defect that a positions-only board produces silently (validate passes, the render ships the
# overlap). Overlay kinds (hud/spotlight, screen-fixed) and backdrops (grid/floor/fill/image) are excluded:
# their overlap with world content is by design, not a bug.
_CINE_FOOTPRINT = {          # kind: (half_width, top_offset, bottom_offset)
    "display": (840, -180, 300), "hero": (840, -180, 300), "textblock": (400, -100, 220),
    "terminal": (430, -390, 390), "metaphor": (360, -260, 260), "callout": (260, -40, 80),
    "panel": (500, -300, 300), "card": (800, -450, 450),
}
_CINE_SAMEPLANE_DZ = 25      # |Δz| within this => same visual plane (real parallax across z is NOT a collision)


def _cine_crowding(elements, tag, warnings):
    """Warn when two content elements' fixed boxes overlap on the same depth plane (they visually collide)."""
    boxes = []
    for el in elements:
        if not isinstance(el, dict):
            continue
        fp = _CINE_FOOTPRINT.get(el.get("kind"))
        pos = el.get("position")
        if fp is None or not (isinstance(pos, list) and len(pos) == 3 and all(isinstance(v, (int, float)) for v in pos)):
            continue
        hw, t0, t1 = fp
        if el.get("kind") == "card" and isinstance(el.get("size"), list) and len(el["size"]) == 2:
            hw, t0, t1 = el["size"][0] / 2, -el["size"][1] / 2, el["size"][1] / 2   # a card is sized explicitly
        x, y, z = pos
        boxes.append((el.get("id"), z, x - hw, x + hw, y + t0, y + t1))
    for i in range(len(boxes)):
        idi, zi, x0i, x1i, y0i, y1i = boxes[i]
        for j in range(i + 1, len(boxes)):
            idj, zj, x0j, x1j, y0j, y1j = boxes[j]
            if abs(zi - zj) > _CINE_SAMEPLANE_DZ:
                continue                                     # different depth plane — parallax, not a collision
            ox = max(0, min(x1i, x1j) - max(x0i, x0j))
            oy = max(0, min(y1i, y1j) - max(y0i, y0j))
            if ox <= 0 or oy <= 0:
                continue
            area = ox * oy
            amin = min((x1i - x0i) * (y1i - y0i), (x1j - x0j) * (y1j - y0j)) or 1
            if area >= 0.25 * amin:                          # a meaningful overlap, not a hairline touch
                warnings.append(f"{tag}: elements {idi!r} and {idj!r} overlap on the same depth plane "
                                f"(~{100 * area / amin:.0f}% of the smaller box) — space them apart or stagger "
                                f"their z; two large boxes at the same [x,y] collide (see the crowding rule)")


_GEN_TEXT_FIELDS = ("title", "sub", "kicker", "text", "heroText")


def _gen_image_guards(el, z, parallax, focal_zs, label, tag, errors, warnings):
    """Guardrails for a GENERATED (`treatment:"atmosphere"`) image — SHARED by the flat depth-plane path
    (`layers`) and the shot-based path (`stage.elements`) so the discipline generalises across BOTH tiers,
    not just the one it was first written for. A gen image is a FAR BACKPLANE behind the code-drawn focal
    card: (1) it must sit BEHIND the focal/text plane, never foreground; (2) it carries NO text/data (gen
    glyphs garble — the code plane owns text); (3) it must not stand in for a REAL named subject (that's
    `documentary`, fetched + credited). `z`/`parallax` locate the plane (either may be None); `focal_zs`
    are the z of the text-bearing planes it must sit behind. No-op unless the plane is a gen image."""
    if el.get("kind") != "image" or str(el.get("treatment", "")).strip().lower() != "atmosphere":
        return
    # (1) PLACEMENT — behind the focal (text) plane, never foreground.
    if z is not None:
        if focal_zs and float(z) >= min(focal_zs):
            errors.append(f"{tag}: {label} is a GENERATED image at z={z} but sits at/in front of the text "
                          f"plane (z≥{min(focal_zs):g}) — a gen image is atmosphere; push it BEHIND the "
                          f"focal card (more-negative z)")
        elif not focal_zs and float(z) > 0:
            warnings.append(f"{tag}: {label} is a GENERATED image at z={z} (>0, foreground) — reserve the "
                            f"front for the code-drawn focal plane; push it back")
    elif isinstance(parallax, (int, float)) and float(parallax) >= 1.0:
        errors.append(f"{tag}: {label} is a GENERATED image at parallax {parallax} (≥1 = foreground) — a gen "
                      f"image is atmosphere; make it a background plane (parallax<1) behind the focal card")
    elif parallax is None:
        warnings.append(f"{tag}: {label} is a GENERATED image with no explicit depth (parallax/z) — place it "
                        f"as a background plane (parallax<1 or a deep -z) so it stays behind the focal card")
    # (2) NO TEXT/DATA — gen glyphs garble; the code plane owns text.
    if any(isinstance(el.get(f), str) and el.get(f).strip() for f in _GEN_TEXT_FIELDS):
        errors.append(f"{tag}: {label} is a GENERATED image carrying TEXT — gen imagery garbles type and "
                      f"can't hold a fact; keep title/kicker/sub/data on the code-drawn focal plane")
    # (3) real-named-subject smell — a specific real thing must be documentary, not fabricated.
    if (el.get("doc_query") or "").strip() or (el.get("credit") or "").strip():
        warnings.append(f"{tag}: {label} is treatment 'atmosphere' (generated) yet names a real subject "
                        f"(doc_query/credit) — a specific real thing must be 'documentary' (fetched + "
                        f"credited), never generated")
    # (4) prompt hygiene — a gen prompt asking for text/UI/data/logos renders garbled.
    _bad = _GEN_PROMPT_FORBIDDEN.search(el.get("image_prompt") or "")
    if _bad:
        warnings.append(f"{tag}: {label} gen image_prompt asks for '{_bad.group(0)}' — generated imagery "
                        f"can't render legible text/UI/data/logos; draw those in code and keep the prompt to "
                        f"texture/material/mood")


def _shot_stage_fields(stage, shots, tag, errors, warnings):
    """P2 SHOT-BASED pre-render gate: a scene-space SET (stage.elements placed once) + an ordered LIST
    of shots. Mirrors render_remotion._clean_stage/_clean_shots so the ~1s validate pass catches the
    faults that would otherwise only fail at render: an empty/malformed stage, a NaN position, a shot
    with an unknown type/motion, or a shot targeting an element id that isn't on the stage. Structural
    only — the framings themselves are judged from the rendered filmstrip (design-critic D12)."""
    ids = set()
    if not isinstance(stage, dict) or not isinstance(stage.get("elements"), list) or not stage["elements"]:
        errors.append(f"{tag}: shot-based `stage.elements` must be a non-empty list")
    else:
        for j, el in enumerate(stage["elements"]):
            if not isinstance(el, dict):
                errors.append(f"{tag}: stage element {j} must be an object"); continue
            eid = el.get("id")
            if not isinstance(eid, str) or not eid:
                errors.append(f"{tag}: stage element {j} needs a non-empty string `id`")
            elif eid in ids:
                errors.append(f"{tag}: duplicate stage element id {eid!r}")
            else:
                ids.add(eid)
            k = el.get("kind")
            if k is not None and k not in _ELEM_KINDS:
                warnings.append(f"{tag}: stage element {eid!r} kind '{k}' is unknown "
                                f"(known: {sorted(_ELEM_KINDS)}) — it will render as a default panel")
            if k == "metaphor":                              # mirror _clean_stage: concept + values arity
                cn = el.get("concept")
                if cn not in _METAPHOR_CONCEPTS:
                    errors.append(f"{tag}: stage element {eid!r} unknown metaphor concept {cn!r} "
                                  f"(known: {sorted(_METAPHOR_CONCEPTS)})")
                vs = el.get("values")
                if not (isinstance(vs, list) and vs):
                    errors.append(f"{tag}: stage element {eid!r} metaphor needs a non-empty `values` list")
                elif cn in _METAPHOR_ARITY and len(vs) != _METAPHOR_ARITY[cn]:
                    errors.append(f"{tag}: stage element {eid!r} concept {cn!r} needs {_METAPHOR_ARITY[cn]} values, got {len(vs)}")
                # SEMANTIC-DIRECTION checks (the verb encodes meaning in a visual property, so a value that
                # contradicts the verb renders a confidently-wrong beat that no structural check would catch):
                _vn = [v for v in (vs or []) if isinstance(v, (int, float))]
                if cn == "physical-fall" and len(_vn) == 2 and _vn[0] <= _vn[1]:
                    warnings.append(f"{tag}: element {eid!r} physical-fall needs values[0] > values[1] (a FALL); "
                                    f"{_vn} does not drop — the token freezes on the shelf and the label mis-signs")
                if cn == "filling-vessel" and len(_vn) >= 1 and _vn[0] == 1:
                    warnings.append(f"{tag}: element {eid!r} filling-vessel value 1 is read as the fraction 1.0 "
                                    f"(=100%); write 0.01 for 1% or 100 for 100% to disambiguate")
            if k == "display" and el.get("attitude") is not None and str(el["attitude"]) not in ("rise", "tracking-in", "blur-in"):
                warnings.append(f"{tag}: display element {eid!r} attitude {el['attitude']!r} unknown "
                                f"(rise|tracking-in|blur-in) — a typo silently renders as blur-in")
            if k == "terminal" and not (isinstance(el.get("lines"), list) and el.get("lines")):
                errors.append(f"{tag}: terminal element {eid!r} needs a non-empty `lines` list (the streaming log)")
            # NATIVE TEXT CLIPS/COLLIDES beyond its element's fixed footprint — a render shipped a quote
            # running off the right edge and two giant displays overlapping. A native `textblock` is a
            # FIXED 800px box that does not wrap-to-fit (long prose clips); a native `display` is 1680px at
            # 200px type (~14 chars/line — a 1-3 word monolith) and a long line wraps to 3+ lines where two
            # displays then collide. Multi-line prose / a headline+body belongs on a Path-A html card.
            if k == "textblock":
                for _ln in str(el.get("text") or "").split("\n"):
                    _w = _disp_width(_ln.strip())               # east-asian-width: a full-width CJK glyph = 2
                    if _w > 30:
                        warnings.append(f"{tag}: textblock {eid!r} has a ~{_w}-wide line — a native "
                                        f"textblock is a fixed 800px box that CLIPS beyond ~30 (a full-width CJK "
                                        f"glyph counts double); put multi-line prose on a Path-A html card")
                        break
            if k == "display":
                _dt = str(el.get("text") or el.get("heroText") or "")
                _w = _disp_width(_dt)
                if _w > 22:
                    warnings.append(f"{tag}: display {eid!r} text is ~{_w} wide — a native display wraps beyond "
                                    f"~14 at 200px (CJK counts double) and two wrapped displays collide; keep it "
                                    f"a 1-3 word monolith, or move a headline+body to a Path-A html card")
            pos = el.get("position")
            if not (isinstance(pos, list) and len(pos) == 3 and all(isinstance(v, (int, float)) for v in pos)):
                errors.append(f"{tag}: stage element {eid!r} `position` must be [x,y,z] numbers")
            elif any(isinstance(v, float) and not math.isfinite(v) for v in pos):
                errors.append(f"{tag}: stage element {eid!r} position has a NaN/Infinity — not renderable")
        # connector target-BY-ID: a `to` naming an element must name a STAGED one (mirror _clean_stage's
        # fail-loud so the dangling id is caught at the ~1s gate, not after a multi-minute render).
        for el in stage["elements"]:
            if isinstance(el, dict) and el.get("kind") == "connector" and isinstance(el.get("to"), str):
                if el["to"] not in ids:
                    errors.append(f"{tag}: connector {el.get('id')!r} `to` target id {el['to']!r} is not a staged element")
        _n_display = sum(1 for el in stage["elements"] if isinstance(el, dict) and el.get("kind") == "display")
        if _n_display >= 2:                                  # two 1680×200 monoliths each wrap and collide
            warnings.append(f"{tag}: {_n_display} native `display` monoliths in one scene — each is a large "
                            f"block that WRAPS at 200px, and two of them collide (a render overlapped a "
                            f"floor/ceiling pair); compose multiple big lines on ONE Path-A html card instead")
        _cine_crowding(stage["elements"], tag, warnings)     # two content boxes colliding on one depth plane

        # GENERATED-imagery guardrails on the shot-based tier — a `treatment:"atmosphere"` image ELEMENT is
        # the same atmosphere-only backplane as a `layers` gen plane, so it gets the SAME three bright lines
        # (backplane behind the focal card / no text-data / not a real-named-subject stand-in). Focal = any
        # element that carries text OR is a Path-A `card` (the code-drawn focal plane the gen image sits
        # behind). Without this, the director's PREFERRED cinematic path would generate but go unguarded.
        def _el_z(e):
            p = e.get("position")
            return float(p[2]) if isinstance(p, list) and len(p) == 3 and isinstance(p[2], (int, float)) else None
        _focal_zs = [_el_z(e) for e in stage["elements"]
                     if isinstance(e, dict) and _el_z(e) is not None
                     and (e.get("kind") == "card"
                          or any(isinstance(e.get(f), str) and e.get(f).strip() for f in _GEN_TEXT_FIELDS))]
        for el in stage["elements"]:
            if isinstance(el, dict):
                _gen_image_guards(el, _el_z(el), None, [z for z in _focal_zs if z is not None],
                                  f"stage element {el.get('id')!r}", tag, errors, warnings)
    if not isinstance(shots, list) or not shots:
        errors.append(f"{tag}: shot-based `shots` must be a non-empty list"); return
    for j, sh in enumerate(shots):
        if not isinstance(sh, dict):
            errors.append(f"{tag}: shot {j} must be an object"); continue
        st = str(sh.get("type", "MEDIUM")).upper()
        if st not in _SHOT_TYPES:
            errors.append(f"{tag}: shot {j} unknown type {st!r} (known: {sorted(_SHOT_TYPES)})")
        mo = _norm_motion(sh.get("motion", "STATIC"))
        if mo not in _SHOT_MOTIONS:
            errors.append(f"{tag}: shot {j} unknown motion {mo!r}")
        # MIRROR _clean_shots: energy + easing + targetPos are coerced/raised there, so catch them at the
        # ~1s gate instead of after a multi-minute render.
        en = sh.get("energy")
        if en is not None and str(en).lower() not in ("subtle", "balanced", "bold"):
            errors.append(f"{tag}: shot {j} energy {en!r} must be subtle|balanced|bold")
        ea = sh.get("easing")
        if ea is not None and str(ea) not in _CINE_EASINGS:
            warnings.append(f"{tag}: shot {j} easing {ea!r} unknown (known: {sorted(_CINE_EASINGS)}) — falls back to house")
        tp = sh.get("targetPos")
        if tp is not None and not (isinstance(tp, list) and len(tp) == 3 and all(isinstance(v, (int, float)) for v in tp)):
            errors.append(f"{tag}: shot {j} targetPos must be [x,y,z] numbers")
        tgt = sh.get("target")
        if tgt is not None and ids and str(tgt) not in ids:
            errors.append(f"{tag}: shot {j} target {tgt!r} is not a staged element id")
    # MOVE-DIVERSITY (P4, analog of contest_diversity): a (framing,motion) pair that recurs >=3 times reads
    # as a template, not a film — even padded with a token-different shot. Fire on the MOST-REPEATED pair,
    # not only the degenerate all-identical case (the old len(set)==1 missed [EST,EST,EST,HERO]).
    moves = [(str(sh.get("type", "MEDIUM")).upper(), _norm_motion(sh.get("motion", "STATIC")))
             for sh in shots if isinstance(sh, dict)]
    if moves:
        top, n = max(((m, moves.count(m)) for m in set(moves)), key=lambda kv: kv[1])
        if n >= 3:
            warnings.append(f"{tag}: {n} of {len(moves)} shots use the same framing+motion {top} — vary the "
                            f"shot type / motion / target so the camera reframes (D12g; >=3 identical shots "
                            f"is the cinematic form of a template)")
    # #6 MOTIVE: a big push (HERO/CLOSEUP) must answer a question — nudge for a one-line `motive`.
    if any(isinstance(sh, dict) and str(sh.get("type", "")).upper() in ("HERO", "CLOSEUP") and not sh.get("motive")
           for sh in shots):
        warnings.append(f"{tag}: a HERO/CLOSEUP shot has no `motive` — state in one line what question the push "
                        f"answers; a move without a motive reads as restless (the removed legacy cinematic tier)")
    # #6 FLAT ARC: the author pinned every shot to the SAME energy (a uniform push, not an arc).
    _ens = [str(sh.get("energy")).lower() for sh in shots if isinstance(sh, dict) and sh.get("energy")]
    if len(_ens) >= 4 and len(set(_ens)) == 1:
        warnings.append(f"{tag}: all {len(_ens)} shots share energy '{_ens[0]}' — build an ARC (calm open -> "
                        f"bold climax near ~80%% -> resolve), don't push uniformly (or drop `energy` to auto-derive)")


def _camera_lurch(track, axes, tag, gname, warnings):
    """Amplitude + in-and-out (oscillation) lint across a camera track's keyframes — the '忽远忽近' lurch the
    per-keyframe band checks MISS (a zoom 1.0->1.55->1.0 passes every band but swings out and back). Advisory,
    like shot_qa: ONE motivated push/tilt/orbit is fine; a BIG swing OR a move that RETURNS is what this flags.
    `axes` = list of (key, amp_warn, osc_warn, relative); relative -> thresholds are a fraction of the mean |v|."""
    kfs = [k for k in (track or []) if isinstance(k, dict)]
    if len(kfs) < 2:
        return
    for key, amp_thr, osc_thr, rel in axes:
        vals = [float(k[key]) for k in kfs if isinstance(k.get(key), (int, float))]
        if len(vals) < 2:
            continue
        amp = max(vals) - min(vals)
        backtrack = sum(abs(b - a) for a, b in zip(vals, vals[1:])) - abs(vals[-1] - vals[0])  # went out and returned
        base = max(1e-6, sum(abs(v) for v in vals) / len(vals)) if rel else 1.0
        amp_n, bt_n = (amp / base, backtrack / base) if rel else (amp, backtrack)
        if bt_n > osc_thr:
            warnings.append(f"{tag}: {gname} `{key}` moves in-and-out within one scene (out to {max(vals):g} and "
                            f"back, backtrack {backtrack:g}) — the '忽远忽近' lurch. A camera gesture should be SINGLE "
                            f"and motivated, not a swing that returns; HOLD or make it monotonic (SKILL camera grammar).")
        elif amp_n > amp_thr:
            warnings.append(f"{tag}: {gname} `{key}` swings {min(vals):g}->{max(vals):g} (delta {amp:g}) across one "
                            f"scene — a big camera move reads as a lurch, not a gentle push; keep one small motivated "
                            f"move over a held, frontal frame.")


def _cinematic_fields(s, meta, out_dir, tag, errors, warnings):
    """Validate the opt-in cinematic `camera` / `layers` on a scene (Remotion tier). NO-OP when both
    are absent, so non-cinematic decks are wholly unaffected. The camera MOVE itself is judged from the
    rendered filmstrip (`_keyframes/scene_NN.png`), never from the plan — this gate only catches the
    STRUCTURAL faults that would render a broken, blank, or lurching move: bad keyframe ordering,
    off-canvas targets, a push past the read-safe zoom, an unknown layer kind, a missing image plane."""
    cam = s.get("camera") or (s.get("props") or {}).get("camera")
    lens = s.get("lens") or (s.get("props") or {}).get("lens")
    layers = s.get("layers") or (s.get("props") or {}).get("layers")
    stage = s.get("stage") or (s.get("props") or {}).get("stage")
    shots = s.get("shots") or (s.get("props") or {}).get("shots")
    planes = s.get("planes") or (s.get("props") or {}).get("planes")
    camera3d = s.get("camera3d") or (s.get("props") or {}).get("camera3d")
    component = s.get("component") or (s.get("props") or {}).get("component")

    # THE TIER THESE FIELDS BELONG TO WAS REMOVED, AND THIS GATE WAS STILL CERTIFYING THEM. `render.py`
    # refuses a slide carrying `layers`/`lens` ("it renders on the cinematic tier"); `render_remotion.py`
    # answers `meta.renderer='remotion-legacy'` with "the legacy generic-scene Remotion tier has been
    # REMOVED in the phase-3 cutover ... an old-tier storyboard (planes/stage/atmosphere) must be
    # re-authored"; the live Film consumes `camera` only as {move, amount, pan}, never a keyframe list; and
    # this file's own scene-type check allows exactly ("slide", "html"). So a board carrying them renders on
    # NO tier — and two tests asserted such a scene passes with no errors AND no warnings, which is this
    # gate promising a render that cannot happen. Said here, the author learns at validate time instead of
    # at the end of a render.
    _removed = [k for k in ("lens", "layers", "camera3d", "perspective", "planes", "stage", "shots")
                if (s.get(k) or (s.get("props") or {}).get(k))]
    if _removed and not component:
        errors.append(
            f"{tag}: carries {_removed} — fields of the generic-scene tier REMOVED in the phase-3 cutover. "
            f"No renderer consumes them: render.py refuses the scene and render_remotion.py refuses the "
            f"board. Re-author the beat as `shot` + `shot_props` against remotion/LIBRARY.md")

    # TWO RENDER TIERS, NEVER MIXED: Scene.tsx dispatches a scene to EITHER ThreeScene (its `planes`, checked
    # FIRST) OR SceneStage (`stage`+`shots`) — never both, so a scene carrying BOTH silently DROPS all its
    # stage content (the plane tier wins). The docs say the tiers are mutually exclusive; catch the mistake
    # here (ERROR) instead of shipping a film missing half its authored forms.
    if isinstance(planes, list) and planes and stage and isinstance(stage.get("elements"), list) and stage["elements"]:
        errors.append(f"{tag}: carries BOTH `planes` and `stage` — a scene renders EITHER the plane tier "
                      f"(bars/particles/glyphrain/device/connector3d/…) OR the stage tier (display/metaphor/"
                      f"hud/connector/…), never both; the `stage` content would SILENTLY DROP. Split into two "
                      f"scenes or keep the beat on ONE tier.")
    if stage and shots:
        _shot_stage_fields(stage, shots, tag, errors, warnings)   # P2 shot-based pre-render gate
    # PATH A: any stage element / 3D plane with an `html` form page — the page MUST exist on disk (render
    # screenshots it into a plane texture). A missing page would silently render nothing, so fail loud here.
    pr = s.get("props") or {}
    _st = stage if isinstance(stage, dict) else None
    _cards = [e for e in ((_st.get("elements") if _st else None) or []) if isinstance(e, dict) and e.get("html")]
    _cards += [p for p in (s.get("planes") or pr.get("planes") or []) if isinstance(p, dict) and p.get("html")]
    for c in _cards:
        if not _exists(out_dir, str(c.get("html") or "")):
            errors.append(f"{tag}: Path-A html card page '{c.get('html')}' not found under {out_dir} — "
                          f"author the form page there (it is screenshotted onto the plane at render)")
    # DESIGN AXIS ((the removed legacy cinematic tier)): a shot-based / 3D cinematic beat must declare an
    # `archetype` so it gets a bespoke, topic-driven design (not the default glass panel). Absent -> warn
    # (nudge the director); set-but-unknown -> error.
    _arche = s.get("archetype") or pr.get("archetype")
    if (stage and shots) or (s.get("planes") or pr.get("planes")):
        if _arche is None:
            warnings.append(f"{tag}: no `archetype` — pick one from (the removed legacy cinematic tier) so the beat "
                            f"gets a bespoke design (cover-the-copy test), not the default glass panel")
        elif str(_arche) not in _ARCHETYPES:
            errors.append(f"{tag}: unknown archetype {_arche!r} (known: {sorted(_ARCHETYPES)})")
        elif str(_arche) in _RESERVE_ARCHETYPES:
            warnings.append(f"{tag}: archetype {_arche!r} has no native renderer yet — it renders as whatever "
                            f"stage elements you build; use a shipped archetype or build the set explicitly")
    # #6 COMFORT BUDGET: too many camera changes per second reads as vertigo (huashu: >=2.6s between moves).
    if stage and isinstance(shots, list) and len(shots) >= 3 and isinstance(s.get("duration"), (int, float)) and s["duration"]:
        avg = float(s["duration"]) / len(shots)
        if avg < 2.6:
            warnings.append(f"{tag}: {len(shots)} shots in {float(s['duration']):.1f}s (~{avg:.1f}s each) — the "
                            f"camera changes faster than ~2.6s (vertigo); merge or cut a shot (comfort budget)")
    # PLANE DATA (bars/stack) — runs for the shot-based / cinematic3d paradigm too (which returns before the
    # cam/lens NaN checks below): a NaN/Inf value blanks the WebGL render; a large `stack` count spawns one
    # cube per unit (hundreds of shadow-casters that stagger past the scene's end, never finishing) — the
    # renderer caps at 50, but steer big magnitudes to `bars` (stack is for SMALL countable accumulation).
    for j, p in enumerate((s.get("planes") or pr.get("planes") or [])):
        if not isinstance(p, dict) or p.get("kind") not in ("bars", "stack") or not isinstance(p.get("data"), list):
            continue
        nums = [v for v in p["data"] if isinstance(v, (int, float))]
        if any(isinstance(v, float) and not math.isfinite(v) for v in nums):
            errors.append(f"{tag}: plane {j} `data` has a NaN/Infinity value — it blanks the 3D render")
        # SIGNED DATA — the classic "every gate misses it" trap: Bars3D grows every bar UP from |value| and
        # Stack3D clamps a negative to 0 cubes, while the label keeps the sign — so a -30 renders as the
        # TALLEST bar tagged "-30", a decline reads as a record high. The 3D primitives are magnitude-only;
        # fail loud here (bipolar rendering isn't built) rather than ship a confidently-wrong chart.
        if any(v < 0 for v in nums):
            errors.append(f"{tag}: plane {j} `{p.get('kind')}` has a NEGATIVE value — 3D bars/stack render by "
                          f"MAGNITUDE (a -30 becomes the tallest bar, labelled '-30'); they cannot show signed "
                          f"data. Use positive magnitudes, or an html chart plane (Path A) for a signed series")
        if p.get("kind") == "stack" and nums:
            mx = max(abs(v) for v in nums)
            if mx > 40:
                warnings.append(f"{tag}: plane {j} is a `stack` with a column of {int(mx)} — it renders one "
                                f"cube per unit (render caps at 50, so it will UNDER-count); `stack` is for "
                                f"small countable accumulation — use `bars` for a magnitude like this")
        if p.get("kind") == "bars" and len(nums) > 12:
            warnings.append(f"{tag}: plane {j} is a `bars` chart with {len(nums)} columns — beyond ~12 the bars "
                            f"spill past the frame and each emits 2 rasterized label PNGs; aggregate to the top "
                            f"~8–10, or use an html chart plane (Path A) for a dense series")
    # born-in-3D forms (particles/surface): a NaN blanks the WebGL render; a huge particle count is capped by
    # the renderer (PARTICLE_MAX=160) so it silently UNDER-shows — steer the author to the cap early.
    for j, p in enumerate((s.get("planes") or pr.get("planes") or [])):
        if not isinstance(p, dict):
            continue
        if p.get("kind") == "particles" and p.get("count") is not None:
            c = p.get("count")
            if not isinstance(c, (int, float)) or (isinstance(c, float) and not math.isfinite(c)) or c <= 0:
                errors.append(f"{tag}: plane {j} particles `count` {c!r} must be a positive number")
            elif c > 160:
                warnings.append(f"{tag}: plane {j} particles count {int(c)} exceeds the render cap (160) — it "
                                f"will UNDER-show; keep it ≤160 (the field reads as 'many' well below that)")
        if p.get("kind") == "surface" and isinstance(p.get("data"), list):
            if any(isinstance(v, float) and not math.isfinite(v) for v in p["data"] if isinstance(v, (int, float))):
                errors.append(f"{tag}: plane {j} surface `data` has a NaN/Infinity value — it blanks the render")
    # BESPOKE hero beat: a `component` names a custom React/R3F file staged into the Remotion bundle. validate
    # can't judge the component's VISUAL interior (that's rendered-frame review, D12), but it CAN guard the
    # WIRING deterministically — an unsafe name / missing file / missing export would render an empty frame.
    if component is not None:
        name = str(component)
        cprops = s.get("componentProps") or s.get("component_props") or (s.get("props") or {}).get("componentProps")
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", name):
            errors.append(f"{tag}: component name {name!r} must be a bare identifier ([A-Za-z][A-Za-z0-9_]*) — "
                          f"it becomes a filename + a TS import; rename the component + its file")
        else:
            src = os.path.join(out_dir, "bespoke", name + ".tsx")
            if not os.path.isfile(src):
                errors.append(f"{tag}: component {name!r} is set but {os.path.join('bespoke', name + '.tsx')} is "
                              f"missing under {out_dir} — author it there (references/bespoke-components.md)")
            else:
                try:
                    with open(src, encoding="utf-8") as _f:
                        txt = _f.read()
                except OSError:
                    txt = ""
                # The registry imports `_Name.<Name> ?? _Name.default`, so the file MUST expose one of those.
                if txt and not re.search(r"export\s+(?:const|function|class)\s+" + re.escape(name) + r"\b", txt) \
                        and not re.search(r"export\s*\{[^}]*\b" + re.escape(name) + r"\b", txt) \
                        and "export default" not in txt:
                    errors.append(f"{tag}: {name}.tsx exports neither a named `{name}` nor a default — the registry "
                                  f"can't resolve it and the beat renders BLANK; add `export const {name} = ...`")
                if txt and re.search(r"<Captions\b|staticFile\([^)]*audio|<Audio\b", txt):
                    warnings.append(f"{tag}: {name}.tsx renders its own Captions/Audio — the Scene wrapper ALREADY "
                                    f"adds them (double captions/audio). The component should return only its visual body")
        if cprops is not None and not isinstance(cprops, dict):
            errors.append(f"{tag}: `componentProps` must be an object (author params passed to {name})")
        # A bespoke component renders the WHOLE beat and owns its OWN camera — it receives only
        # {theme, componentProps, reducedMotion, atmosphere, durationInFrames}. So pipeline render/camera fields
        # are DEAD here (a `camera3d` that never moves the view, `planes` that never draw); warn, don't silently drop.
        _dead = [k for k in ("planes", "camera3d", "stage", "shots", "layers", "lens", "camera", "perspective")
                 if s.get(k) or (s.get("props") or {}).get(k)]
        if _dead:
            warnings.append(f"{tag}: component {name!r} also carries {_dead} — those are IGNORED on a bespoke beat "
                            f"(the component renders the beat and owns its camera; it gets only theme/componentProps/"
                            f"reducedMotion/atmosphere/durationInFrames). Move that motion INTO the component or drop the fields")
    if not cam and not lens and not layers and not camera3d and not component:
        return
    fps = int((meta or {}).get("fps", 30) or 30)
    dur = s.get("duration")
    dframes = int(round(float(dur) * fps)) if isinstance(dur, (int, float)) and dur else None

    # Non-finite (NaN/Infinity) anywhere is an ERROR, not a range warning — it blanks the render and
    # writes invalid JSON. (json.load parses NaN/Infinity, so a hand-authored board can contain them.)
    def _nf(v):
        return isinstance(v, float) and not math.isfinite(v)
    for j, ly in enumerate(layers if isinstance(layers, list) else []):
        if isinstance(ly, dict):
            for key in ("z", "blur", "dim", "parallax", "x", "y", "revealAtFrame"):
                if _nf(ly.get(key)):
                    errors.append(f"{tag}: layer {j} {key} is NaN/Infinity — not a renderable value")
    for grp, gname in ((cam, "camera"), (lens, "lens")):
        for j, k in enumerate(grp if isinstance(grp, list) else []):
            if isinstance(k, dict):
                for key in ("atFrame", "x", "y", "zoom", "dolly", "pitch", "yaw", "roll", "focusZ"):
                    if _nf(k.get(key)):
                        errors.append(f"{tag}: {gname} keyframe {j} {key} is NaN/Infinity — not a renderable value")

    persp = s.get("perspective") or (s.get("props") or {}).get("perspective")
    if persp is not None and (not isinstance(persp, (int, float)) or _nf(persp) or not (600 <= float(persp) <= 3200)):
        warnings.append(f"{tag}: perspective {persp} outside 600–3200 — too small warps, too large flattens the 3D")

    if layers is not None:
        if not isinstance(layers, list) or not layers:
            errors.append(f"{tag}: `layers` must be a non-empty list of depth planes")
        else:
            for j, ly in enumerate(layers):
                if not isinstance(ly, dict):
                    errors.append(f"{tag}: layer {j} must be an object"); continue
                if ly.get("kind") not in _CINE_KINDS:
                    warnings.append(f"{tag}: layer {j} kind '{ly.get('kind')}' is not one of "
                                    f"{sorted(_CINE_KINDS)} — it renders blank")
                p = ly.get("parallax", 1.0)
                if not isinstance(p, (int, float)) or not (0.3 <= float(p) <= 2.0):
                    warnings.append(f"{tag}: layer {j} parallax {p} outside 0.3–2.0 — depth reads wrong "
                                    f"(background < 1, foreground > 1)")
                zz = ly.get("z")
                if zz is not None and (not isinstance(zz, (int, float)) or not (-4000 <= float(zz) <= 1500)):
                    warnings.append(f"{tag}: layer {j} z {zz} outside -4000..1500 px — a plane that far "
                                    f"is off-camera or through the lens")
                bl = ly.get("blur", 0)
                if not isinstance(bl, (int, float)) or not (0 <= float(bl) <= 40):
                    warnings.append(f"{tag}: layer {j} blur {bl} outside 0–40 px")
                dm = ly.get("dim", 0)
                if not isinstance(dm, (int, float)) or not (0 <= float(dm) <= 1):
                    warnings.append(f"{tag}: layer {j} dim {dm} outside 0–1")
                if ly.get("kind") == "image":
                    if not (ly.get("src") or "").strip() and (ly.get("image_prompt") or "").strip():
                        # authored a gen backplane but the asset isn't there yet — clearer than 'src not found'
                        errors.append(f"{tag}: layer {j} has image_prompt but no generated src — run "
                                      f"imagegen.py first (it fills each depth-plane's src)")
                    elif not _exists(out_dir, ly.get("src") or ""):
                        errors.append(f"{tag}: layer {j} image src '{ly.get('src')}' not found under {out_dir}")
                # TEXT belongs on the sharp focal plane. A dimmed/blurred background plane carrying a
                # title/sub/kicker muddles into competing noise (the audit's clearest authoring fix).
                has_text = any(isinstance(ly.get(k), str) and ly.get(k).strip()
                               for k in ("title", "sub", "kicker", "text", "heroText"))
                if has_text and ((isinstance(dm, (int, float)) and float(dm) >= 0.25)
                                 or (isinstance(bl, (int, float)) and float(bl) >= 4)):
                    warnings.append(f"{tag}: layer {j} puts TEXT on a backgrounded plane (dim/blur) — "
                                    f"competing text muddles into noise; reserve text for the sharp focal "
                                    f"plane and make far planes texture (grid/floor/hero)")

                # ── GENERATED-imagery guardrails (the Codex/`atmosphere` backplane) — shared helper so the
                # SAME three bright lines apply on the shot-based `stage.elements` path too (see below). ──
                _focal_zs = [float(t.get("z")) for t in layers
                             if isinstance(t, dict) and isinstance(t.get("z"), (int, float))
                             and any(isinstance(t.get(w), str) and t.get(w).strip() for w in _GEN_TEXT_FIELDS)]
                _z = float(zz) if isinstance(zz, (int, float)) else None
                _gen_image_guards(ly, _z, ly.get("parallax"), _focal_zs, f"layer {j}", tag, errors, warnings)

    if lens is not None:
        if not isinstance(lens, list) or not lens:
            errors.append(f"{tag}: `lens` must be a non-empty list of 3D keyframes")
        elif layers is None:
            errors.append(f"{tag}: `lens` needs `layers` to move over — add depth planes")
        else:
            prev = None
            for j, k in enumerate(lens):
                if not isinstance(k, dict):
                    errors.append(f"{tag}: lens keyframe {j} must be an object"); continue
                at = k.get("atFrame")
                if not isinstance(at, (int, float)):
                    errors.append(f"{tag}: lens keyframe {j} needs a numeric atFrame")
                else:
                    if at < 0:
                        errors.append(f"{tag}: lens keyframe {j} atFrame {at} < 0")
                    if prev is not None and at < prev:
                        errors.append(f"{tag}: lens keyframes must be non-decreasing in atFrame "
                                      f"(kf {j}={at} < kf {j - 1}={prev})")
                    if dframes is not None and at > dframes + 1:
                        warnings.append(f"{tag}: lens keyframe {j} atFrame {at} is past the scene end "
                                        f"({dframes}f) — it clamps")
                    prev = at
                # ESCAPE-HATCH clamp: the auto shot ladder is bounded by construction, but a HAND-AUTHORED
                # lens is not — so an EGREGIOUS zoom/keystone (fisheye-crop / edge-on read-card territory)
                # BLOCKS, while mild out-of-band stays advisory. Conservative bounds so a dramatic-but-fine
                # shot is never falsely blocked. (Audit P0: the highest-risk input had zero enforcement.)
                pitch = k.get("pitch", 0)
                if not isinstance(pitch, (int, float)):
                    errors.append(f"{tag}: lens keyframe {j} pitch must be a number")
                elif abs(float(pitch)) > 60:
                    errors.append(f"{tag}: lens keyframe {j} pitch {pitch}° is a SEVERE keystone — flat card "
                                  f"planes reveal edge-on; route a true top-down to the R3F tier")
                elif abs(float(pitch)) > 45:
                    warnings.append(f"{tag}: lens keyframe {j} pitch {pitch}° beyond ±45 — flat card planes "
                                    f"keystone and reveal as sheets; route a true top-down to the R3F tier")
                yaw = k.get("yaw", 0)
                if not isinstance(yaw, (int, float)):
                    errors.append(f"{tag}: lens keyframe {j} yaw must be a number")
                elif abs(float(yaw)) > 55:
                    errors.append(f"{tag}: lens keyframe {j} yaw {yaw}° loses the card's face entirely — keep "
                                  f"orbit-lite within ±35 (a true orbit belongs on the R3F tier)")
                elif abs(float(yaw)) > 35:
                    warnings.append(f"{tag}: lens keyframe {j} yaw {yaw}° beyond ±35 — card planes lose their "
                                    f"face; keep orbit-lite within ±20–35")
                zoomv = k.get("zoom", 1.0)
                if not isinstance(zoomv, (int, float)):
                    errors.append(f"{tag}: lens keyframe {j} zoom must be a number")
                elif float(zoomv) > 2.0 or float(zoomv) < 0.4:
                    errors.append(f"{tag}: lens keyframe {j} zoom {zoomv} is a SEVERE over/under-zoom — the "
                                  f"read-card fisheye-crops or vanishes; keep it in the readable band ~0.6–1.6")
                elif not (0.6 <= float(zoomv) <= 1.6):
                    warnings.append(f"{tag}: lens keyframe {j} zoom {zoomv} outside 0.6–1.6")
                e = k.get("easing", "inout")
                if e not in _CINE_EASINGS:
                    warnings.append(f"{tag}: lens keyframe {j} easing '{e}' unknown — use "
                                    f"{sorted(_CINE_EASINGS)} (the runtime falls back to inout)")

    if cam is not None:
        if not isinstance(cam, list) or not cam:
            errors.append(f"{tag}: `camera` must be a non-empty list of keyframes")
        else:
            prev = None
            for j, k in enumerate(cam):
                if not isinstance(k, dict):
                    errors.append(f"{tag}: camera keyframe {j} must be an object"); continue
                at = k.get("atFrame")
                if not isinstance(at, (int, float)):
                    errors.append(f"{tag}: camera keyframe {j} needs a numeric atFrame (integer frame index)")
                else:
                    if at < 0:
                        errors.append(f"{tag}: camera keyframe {j} atFrame {at} < 0")
                    if prev is not None and at < prev:
                        errors.append(f"{tag}: camera keyframes must be non-decreasing in atFrame "
                                      f"(kf {j}={at} < kf {j - 1}={prev})")
                    if dframes is not None and at > dframes + 1:
                        warnings.append(f"{tag}: camera keyframe {j} atFrame {at} is past the scene end "
                                        f"({dframes}f) — it clamps")
                    prev = at
                z = k.get("zoom", 1.0)
                if not isinstance(z, (int, float)):
                    errors.append(f"{tag}: camera keyframe {j} zoom must be a number")
                elif float(z) > 2.0 or float(z) < 0.4:
                    errors.append(f"{tag}: camera keyframe {j} zoom {z} is a SEVERE over/under-zoom — the "
                                  f"read-card crops or vanishes; keep it in the readable band ~0.6–1.6")
                elif not (0.6 <= float(z) <= 1.6):
                    warnings.append(f"{tag}: camera keyframe {j} zoom {z} outside 0.6–1.6 — a bigger push "
                                    f"lurches or breaks the 3-second read")
                for ax in ("x", "y"):
                    v = k.get(ax, 0.5)
                    if not isinstance(v, (int, float)) or not (-0.5 <= float(v) <= 1.5):
                        warnings.append(f"{tag}: camera keyframe {j} {ax}={v} is far off-canvas (keep ~0..1)")
                e = k.get("easing", "inout")
                if e not in _CINE_EASINGS:
                    warnings.append(f"{tag}: camera keyframe {j} easing '{e}' unknown — use "
                                    f"{sorted(_CINE_EASINGS)} (the runtime falls back to inout)")
            zs = [float(k.get("zoom", 1.0)) for k in cam
                  if isinstance(k, dict) and isinstance(k.get("zoom", 1.0), (int, float))]
            for a, b in zip(zs, zs[1:]):
                if abs(b - a) > 0.35:
                    warnings.append(f"{tag}: camera zoom jumps {a}->{b} (Δ{abs(b - a):.2f} > 0.35) in one "
                                    f"segment — reads as a lurch, not a filmic push")

    # AMPLITUDE + OSCILLATION lint — the '忽远忽近' lurch the per-keyframe bands miss, across ALL camera tiers.
    _camera_lurch(cam, [("zoom", 0.55, 0.28, False), ("x", 0.6, 0.35, False), ("y", 0.6, 0.35, False)], tag, "camera", warnings)
    _camera_lurch(lens, [("zoom", 0.55, 0.28, False), ("pitch", 38, 20, False), ("yaw", 46, 26, False)], tag, "lens", warnings)
    # camera3d (the R3F orbit/crane tier) was UNvalidated (the early return skipped it) — sanity-check it, then
    # lurch-lint yaw/radius/height (radius/height relative to their mean, since world units vary by scene).
    if camera3d is not None:
        if not isinstance(camera3d, list) or not camera3d:
            errors.append(f"{tag}: `camera3d` must be a non-empty list of orbit/crane keyframes")
        else:
            prev3 = None
            for j, k in enumerate(camera3d):
                if not isinstance(k, dict):
                    errors.append(f"{tag}: camera3d keyframe {j} must be an object"); continue
                at = k.get("at", k.get("atFrame"))
                if not isinstance(at, (int, float)):
                    warnings.append(f"{tag}: camera3d keyframe {j} needs a numeric `at` (0..1 fraction)")
                elif prev3 is not None and float(at) < float(prev3):
                    warnings.append(f"{tag}: camera3d keyframes should be non-decreasing in `at` (kf {j}={at} < {prev3})")
                else:
                    prev3 = at
                for key in ("yaw", "radius", "height"):
                    if _nf(k.get(key)):
                        errors.append(f"{tag}: camera3d keyframe {j} {key} is NaN/Infinity — not a renderable value")
            _camera_lurch(camera3d, [("yaw", 55, 28, False), ("radius", 0.55, 0.30, True), ("height", 0.6, 0.35, True)], tag, "camera3d", warnings)


def _check_shot_template(meta, errors, warnings):
    """The remotion analogue of the html register-contest gate (mirrors the `template_contest` checks): a whole-
    film `meta.shot_template` DIRECTION (one of the 6 seed keys OR a bespoke topic-conceived slug) with a
    `meta.shot_template_contest` that is a real divergence — >=2 candidates, the winner among them and == the
    chosen direction, a USER pick, and a WIDTH matching meta.audacity. A bold/experimental film with NO contest
    is an ERROR (the divergence isn't optional there); conservative may skip; balanced warns."""
    tmpl = meta.get("shot_template")
    aud = str(meta.get("audacity") or "balanced").lower()
    try:
        import shot_templates as _st
        keys = set(_st.TEMPLATES)
        want_w = _st.contest_width(aud)
    except Exception:
        keys, want_w = None, {"conservative": 0, "balanced": 3, "bold": 5, "experimental": 7}.get(aud, 3)
    if tmpl is not None and keys and tmpl not in keys:
        warnings.append("meta.shot_template %r is not one of the 6 SEED directions — assumed a bespoke topic-"
                        "conceived direction (fine); confirm it's intentional, not a typo of a seed key" % tmpl)
    tc = meta.get("shot_template_contest")
    if tc is None:
        if aud in ("bold", "experimental"):
            errors.append("meta.audacity=%r REQUIRES a `meta.shot_template_contest` (>=%d topic-conceived "
                          "directions, judged, user-picked) — the divergence+selection is not optional at this "
                          "audacity (mirror the html register-contest 3.55)" % (aud, want_w))
        elif tmpl is not None and aud != "conservative":
            warnings.append("meta.shot_template is set but no `meta.shot_template_contest` is recorded — the "
                            "user should PICK the direction from rendered contest stills; record "
                            "{candidates, winner, user_pick, width, audacity}")
        return
    if not isinstance(tc, dict):
        errors.append("meta.shot_template_contest must be an object {candidates, winner, user_pick}"); return
    cands = tc.get("candidates")
    if not isinstance(cands, list) or len(cands) < 2:
        errors.append("meta.shot_template_contest needs >=2 `candidates` — a contest is a divergence")
    elif want_w and len(cands) < want_w:
        warnings.append("meta.shot_template_contest offered %d candidate(s) but audacity=%r wants ~%d — widen "
                        "the divergence (conceive more bespoke directions)" % (len(cands), aud, want_w))
    win = tc.get("winner")
    if win is not None and isinstance(cands, list) and win not in cands:
        errors.append("meta.shot_template_contest.winner %r is not among its candidates %s" % (win, cands))
    if win is not None and tmpl is not None and win != tmpl:
        errors.append("meta.shot_template_contest.winner %r != meta.shot_template %r — the winner IS the "
                      "chosen direction" % (win, tmpl))
    if not tc.get("user_pick"):
        warnings.append("meta.shot_template_contest has no `user_pick:true` — record that the USER chose the "
                        "direction (the contest exists so a human picks, not the model)")


def _DNA_PRESETS_FOR_TEST():
    """The preset ids validate treats as 'themed'. Exposed so tests/test_remotion.py can assert this set
    still matches DNA_PRESETS in remotion/src/runtime/dna.tsx — the two copies drifting is a silent gate loss."""
    return {"terminal-technical", "terminal", "neutral", "editorial", "kinetic-editorial",
            "product", "product-demo", "apple", "blueprint",
            "cinematic-craft", "cinematic", "data-story", "data", "retro-playful", "retro"}


# Mirror of AtomForms in remotion/src/runtime/dna.tsx. tests/test_remotion.py asserts the two stay equal —
# drift means an authored DNA gets warned about a form the runtime actually supports, or a typo passes.
_ATOM_FORMS = {
    "bar": {"block", "solid", "ruled", "pixel", "dimension"},
    "figure": {"mono", "serif", "display", "segment"},
    "list": {"tree", "ruled", "bullet", "numbered"},
    "label": {"prompt", "kicker", "spec", "chip"},
    "divider": {"scanline", "hairline", "dimension", "dotted"},
    "marker": {"caret", "triangle", "crosshair", "arrow"},
}





def _ground_followers():
    """Registers a declared ground may be applied to, PARSED from GROUND_FOLLOWS_MEASURED in
    remotion/src/runtime/shotLuma.ts (the allow list runtime/light.tsx consults; 103 of 152 registers).

    The runtime already REFUSES a ground on a register that does not follow one — but it refuses mid-render,
    minutes in, which is exactly the cost measure_ground_reach.py's own docstring says this check exists to
    avoid. Same discipline as _ground_preset_names: parsed, and None when unreadable, so a validator reading
    the wrong file says nothing rather than refusing a legal beat.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "remotion", "src", "runtime", "shotLuma.ts")
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"GROUND_FOLLOWS_MEASURED[^=]*=\s*(?:new Set\()?\[(.*?)\]", src, re.S)
    if not m:
        return None
    names = set(re.findall(r"'([A-Za-z0-9_]+)'", m.group(1)))
    return names or None


def _ground_preset_names():
    """The named grounds, PARSED from remotion/src/runtime/light.tsx rather than restated here.

    This repo's caption band once existed as four disagreeing copies, and the scar is why. Returns None when
    the block cannot be found, and the caller then declines to judge a name rather than inventing a verdict
    from a stale list — a validator that refuses a legal ground because it is reading the wrong file is worse
    than one that says nothing.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "remotion", "src", "runtime", "light.tsx")
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"export const GROUND_PRESETS[^{]*\{(.*?)\n\};", src, re.S)
    if not m:
        return None
    names = set(re.findall(r"^\s{2}([A-Za-z][A-Za-z0-9_]*)\s*:", m.group(1), re.M))
    return names or None


def _ground_ref_error(ref, where, presets):
    """One GroundRef, judged. Returns an error string or None. Mirrors light.tsx resolveRef's vocabulary:
    an index into the film's grounds, a named preset, a #hex, or an inline {bg,...} spec."""
    if isinstance(ref, bool):
        return "%s must be an index, a named ground, a #hex or a {bg:...} spec — got a boolean" % where
    if isinstance(ref, int):
        return None if ref >= 0 else "%s is a negative ground index (%d)" % (where, ref)
    if isinstance(ref, float):
        return "%s is a ground INDEX, so it must be a whole number — got %r" % (where, ref)
    if isinstance(ref, str):
        if re.fullmatch(r"#[0-9a-fA-F]{3,8}", ref):
            return None
        if presets is None or ref in presets:
            return None
        return ("%s names the ground %r, which is not one of %s and is not a #hex. A typo here does not fail "
                "— it silently paints a different beat." % (where, ref, "/".join(sorted(presets))))
    if isinstance(ref, dict):
        if not str(ref.get("bg") or "").strip():
            return "%s is an inline ground with no `bg` — the one field a ground cannot derive" % where
        return None
    return "%s must be an index, a named ground, a #hex or a {bg:...} spec — got %s" % (where, type(ref).__name__)


def _beat_grounds(slides, errors, warnings):
    """`slide.ground` / `slide.key` — the per-beat exposure the delivery path now forwards.

    Both are COMMANDS that repaint the frame (runtime/light.tsx), which is what separates them from `bgLum`,
    a description the caption pick reads. The runtime throws on a malformed one, but a render is minutes away
    and a typo in `key` is the expensive kind: any value that is not the film's own key re-lights the beat, so
    `'ligth'` renders a film nobody asked for rather than failing. Catch it here, before the render.
    """
    presets = _ground_preset_names()
    followers = _ground_followers()
    seen_ground = 0
    for s in slides:
        beat = int(s.get("index", 0)) + 1
        k = s.get("key")
        if k is not None and k not in ("dark", "light"):
            errors.append("remotion: beat %d has key %r — the only exposures are 'dark' and 'light'. Any "
                          "other value is a typo that re-lights the beat instead of failing." % (beat, k))
        g = s.get("ground")
        if g is None:
            continue
        # A ground on a register that does not FOLLOW one is refused by the runtime — but mid-render, so the
        # author pays minutes to learn it. Caught here, it costs a second.
        shot = s.get("shot")
        if followers and shot and shot not in followers:
            errors.append(
                "remotion: beat %d declares a `ground` on %s, which does not follow one — under a declared "
                "ground its own content keeps its luminance, so the frame would be part the ground you asked "
                "for and part the register's own, and the burned caption would pick ink for the half that is "
                "not there. Move the ground to a neighbouring beat whose register follows (103 of the "
                "library do; the list is GROUND_FOLLOWS_MEASURED in remotion/src/runtime/shotLuma.ts), or "
                "make %s paint from the DNA tokens and re-measure with "
                "`python3 scripts/measure_ground_reach.py --emit`." % (beat, shot, shot))
        seen_ground += 1
        if isinstance(g, dict) and ("from" in g or "to" in g):
            for half in ("from", "to"):
                if half not in g:
                    errors.append("remotion: beat %d declares a ground RAMP with no `%s`" % (beat, half))
                    continue
                e = _ground_ref_error(g[half], "remotion: beat %d ground.%s" % (beat, half), presets)
                if e:
                    errors.append(e)
            at = g.get("at")
            if at is not None:
                ok = (isinstance(at, (list, tuple)) and len(at) == 2
                      and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in at)
                      and 0 <= at[0] < at[1] <= 1)
                if not ok:
                    errors.append("remotion: beat %d ground.at must be two rising fractions in 0..1, got %r "
                                  "— a malformed window used to poison every colour on the frame" % (beat, at))
        else:
            e = _ground_ref_error(g, "remotion: beat %d ground" % beat, presets)
            if e:
                errors.append(e)
    # A film that declares ONE ground has an exposure change, not an arc. film_energy_qa measures the arc as
    # the fraction of adjacent seconds whose light moves, precisely because a single bright passage scored
    # 0.910 on the old range measure while nothing in the film changed.
    if 0 < seen_ground < 3 and len(slides) >= 8:
        warnings.append("remotion: %d beat(s) of %d declare a `ground`. One bright passage is not a "
                        "luminance ARC — film_energy_qa measures how often the light moves, and a film that "
                        "re-grounds once will still read as unlit." % (seen_ground, len(slides)))
    elif seen_ground == 0 and len(slides) >= 8:
        # THE CASE THAT ACTUALLY SHIPS, and it used to pass in silence: the warning above began at `0 <`, so a
        # film that never re-grounds AT ALL — every beat on one flat ground from first frame to last — was the
        # one shape nothing mentioned. It is not a rare shape. Swept across the library, 142 of 152 registers
        # measure under the delivery gate's light floor (median luma_range 0.016 against a floor of 0.135 and
        # reference launch films at 0.27-0.90), because a register holds ONE ground by design: a film's light
        # comes from moving BETWEEN beats, and nothing was moving.
        #
        # A WARNING, not an error. Where the light goes is a directorial decision — the automatic arc was
        # built and deliberately withdrawn from the default path (light_plan.py --write refuses without
        # --accept-risk). This says the decision was never made, which is different from making it and
        # choosing to stay dark; a film that means to be monotone declares meta.energy_waiver with a reason.
        warnings.append(
            "remotion: no beat declares a `ground` — %d beats on ONE flat exposure, first frame to last. "
            "A register holds one ground by design; a FILM's light comes from moving between them, and "
            "film_energy_qa measures how often it moves. The vocabulary needs no setup: `ground: 0` is the "
            "film's own ground, `1` its opposite key (dark film -> a lit frame), `2`+ one chromatic ground "
            "per accent — or name one of %s. Put 3-6 beats somewhere else, on the beats where the ARGUMENT "
            "turns (a payoff, a section break, a before/after), and say so in shot_adaptation. If the film "
            "means to be monotone, declare meta.energy_waiver with a reason."
            % (len(slides), "/".join(sorted(presets)) if presets else "the named presets"))


def _idiom_world(meta, slides, errors, warnings):
    """A register speaks some world's vocabulary. The film must be in that world.

    Family says what a shot LOOKS like; provenance says WHOSE language it is. A `$ diff` gutter, a bento
    dashboard and a command palette are the vocabulary of developer tooling and SaaS — legible, well made,
    and wrong for a canal city, a piece of music or a court case. Nothing in the pipeline knew that, so a
    35-beat city documentary shipped 16 beats speaking product, every one of them passing its own gates.

    So: each register carries a provenance (shot_director.PROVENANCE); the film declares which worlds its
    subject belongs to (`meta.idiom_world`); a beat drawing from an undeclared world is an ERROR that names
    both sides. That converts "this design feels inappropriate" — a thing only a reviewer used to catch —
    into something the pipeline refuses.

    WHAT IT CANNOT DO, stated so nobody trusts it too far: it catches a whole vocabulary arriving from the
    wrong world. It does NOT catch one beat misusing an in-world idiom. An industrial conveyor belt is
    legitimate in a harbour film and still wrong for people cycling to a station; that is a per-beat meaning
    judgement and stays with the shot-critic.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import shot_director as _sd
        PROV, WORLDS = _sd.PROVENANCE, set(_sd.IDIOM_WORLDS)
    except Exception:
        return
    declared = meta.get("idiom_world")
    if not declared:
        used = sorted({PROV.get(s.get("shot")) for s in slides if PROV.get(s.get("shot"))})
        warnings.append(
            "remotion: no meta.idiom_world — the film never said which worlds its subject's visual language "
            "belongs to, so nothing checks whether its registers speak them. This film currently draws from: "
            "%s. Declare the ones that belong (agents/shot-director.md step 0.5)." % ", ".join(used))
        return
    if isinstance(declared, str):
        declared = [declared]
    bad = [w for w in declared if w not in WORLDS]
    if bad:
        errors.append("meta.idiom_world names unknown world(s) %s — known: %s"
                      % (", ".join(repr(b) for b in bad), ", ".join(sorted(WORLDS))))
        return
    ok = set(declared)
    off, untagged = [], []
    for s in slides:
        shot = s.get("shot")
        w = PROV.get(shot)
        if w is None:
            # A register with no provenance is SILENTLY EXEMPT from this gate — validate looks it up, gets
            # nothing and moves on. That is how the check would have decayed to nothing as the library grew,
            # so an untagged register is a finding about the LIBRARY, not a pass for the beat.
            if shot:
                untagged.append((int(s.get("index", 0)) + 1, shot))
        elif w not in ok:
            off.append((int(s.get("index", 0)) + 1, shot, w))
    for beat, shot in untagged[:6]:
        errors.append("remotion: beat %d uses %s, which carries no PROVENANCE in shot_director.py — an "
                      "untagged register is exempt from this gate by accident. Register it with "
                      "`register_shot.py %s <Family> --provenance <world>`." % (beat, shot, shot))
    for beat, shot, w in off[:10]:
        errors.append("remotion: beat %d uses %s, whose visual language comes from %r — a world this film "
                      "did not declare (%s). Either the beat wants a form from one of the film's own worlds, "
                      "or the world genuinely belongs to the subject and should be declared."
                      % (beat, shot, w, ", ".join(sorted(ok))))
    if len(off) > 10:
        errors.append("remotion: %d more beat(s) draw from undeclared worlds" % (len(off) - 10))

_KNOWN_DNA_IDS = {'terminal', 'product', 'apple', 'editorial', 'blueprint', 'data', 'retro'}


def _caption_legibility(meta, slides, errors, warnings, out_dir=None):
    """Would this film's captions be squeezed under the size a viewer can actually read?

    The renderer caps the caption's type at whatever fits the reserved band, which is a guarantee that it
    never overlaps the picture — but a guarantee that degrades SILENTLY. An unbroken 120-character sentence
    at 16:9 fits by shrinking to 22px, about 2% of frame height, which is present and illegible. So the
    arithmetic is repeated here, where the narration text and the aspect are both visible, and it is said
    out loud instead.
    """
    try:
        from _caption_band import caption_band_px, caption_size_px, _fracs, aspect_wh
    except Exception:
        return
    W, H = aspect_wh(meta.get("aspect"))
    band, ideal = caption_band_px(W, H), caption_size_px(W, H)
    f = _fracs()
    margin = int(round(min(W, H) * f["CAPTION_MARGIN_FRAC"]))
    measure = min(1600, W - 120)
    # DERIVED FROM THE AUTHORED SIZE, not restated. This was a hardcoded `0.042 * min(W, H)` — which is a
    # third file holding an opinion about caption type, and the moment layout.ts lowered its own fraction to
    # 0.042 the two numbers collided and this warned on every beat of a correctly-authored film. The check
    # is about SQUEEZING: the renderer shrinks a caption that will not otherwise fit its band, and past some
    # point the shrink makes it unreadable. So the floor is a fraction OF the authored size — a caption at
    # full size can never trip it, and one squeezed below 85% always does, whatever the film's type scale.
    floor = 0.85 * ideal
    worst = []
    for i, sl in enumerate(slides, 1):
        text = (sl.get("narration") or sl.get("caption") or "").strip()
        if not text:
            continue
        # the renderer splits on sentence ends and then on clause boundaries; the worst CHUNK is what sets
        # the size, so approximate that split rather than measuring the whole paragraph
        chunks = [c for c in re.split(r"(?<=[.!?。！？])\s+", text) if c.strip()] or [text]
        for c in chunks:
            cjk = len(re.findall(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", c)) * 2 >= len(c) and len(c) > 0
            lead = f["CAPTION_LEAD"] * (1.7 / 1.26 if cjk else 1.0)
            per = max(8, int(measure / (ideal * (1.0 if cjk else 0.52))))
            # a long chunk gets cut at a clause boundary first — only a clause-free run stays whole
            if len(c) > per * f["CAPTION_LINES"] and re.search(r"[,;，；、]", c):
                c = max(re.split(r"[,;，；、]", c), key=len)
            lines = max(1, -(-len(c) // per))
            fit = max(12, min(ideal, int((band - margin) / (lead * lines))))
            if fit < floor:
                worst.append((i, fit, lines))
                break
    if worst:
        i, fit, lines = min(worst, key=lambda x: x[1])
        warnings.append(
            "%d beat(s) carry a caption that will be squeezed to %dpx (%.1f%% of frame height) to fit the "
            "reserved band — present but not readable; worst is beat %d at %d lines. Shorten the line, or "
            "break it at a clause the renderer can cut on (a comma), or raise meta.aspect's room."
            % (len(worst), fit, fit / min(W, H) * 100, i, lines))


def _image_attribution(slides, out_dir, errors, warnings):
    """Every license-clean image must be credited to the person who actually made it.

    `imagefetch.py` writes a sidecar `<file>.json` with the real artist and licence, and nothing compared it
    against what the film puts on screen. Two defects on one board: a credit naming the wrong photographer
    entirely, and a two-image beat carrying ONE credit line — so the second image was uncredited and its
    licence misstated. The second had already shipped.

    This is an ERROR, not a warning. A CC-BY attribution is the condition the work is licensed under, and a
    wrong one is not a typo — it credits someone else's photograph to a stranger.
    """
    if not out_dir:
        return
    for i, sl in enumerate(slides, 1):
        props = sl.get("shot_props") or {}
        if not isinstance(props, dict):
            continue
        blob = json.dumps(props, ensure_ascii=False)
        credits = " ".join(str(v) for k, v in props.items()
                           if "credit" in str(k).lower() and isinstance(v, str))
        # ANY relative image path, not only `media/` and `assets/`. A film is free to organise its files, and
        # a beat whose photograph sits in `photos/` or `img/2024/` was invisible to this gate entirely —
        # the licence condition does not depend on the directory someone chose.
        for rel in sorted(set(re.findall(r'"((?!https?:)[^"\s]+\.(?:jpg|jpeg|png|webp|avif))"', blob, re.I))):
            side = os.path.join(out_dir, rel + ".json")
            if not os.path.exists(side):
                continue                       # a hand-supplied image has nothing to check against
            try:
                meta = json.load(open(side, encoding="utf-8"))
            except Exception:
                continue
            artist = str(meta.get("artist") or "").strip()
            lic = str(meta.get("license") or "").strip()
            # Match on NAME TOKENS, not the exact string. Commons writes an artist as 'Koning, J.P. de
            # (fotograaf)' while a credit line reads 'J.P. de Koning' — the same person, and an exact
            # substring test called it uncredited. A checker that fails on correct attributions gets
            # switched off, and then the wrong ones ship too.
            #
            # Tokens are CJK RUNS plus Latin words of two letters or more, because a first pass demanding
            # three letters raised a false ERROR on every two-character Chinese name and on short surnames
            # like Wu and Ng — refusing to ship a correctly credited photograph, which is worse than the
            # defect it was written to catch. A name that yields no tokens at all (initials only) is not
            # checkable and is left alone rather than failed.
            _ROLE = {"fotograaf", "photographer", "fotograf", "own", "work", "unknown", "anonymous", "user"}
            # THE NAME, NOT THE PAGE. Commons often stores the artist as a name followed by a paragraph of
            # boilerplate — "Donald Trung Quoc Don (Chữ Hán: 徵國單) - Wikimedia Commons - © CC BY-SA 4.0
            # International.(Want to use this image?)Original publication…". Requiring every substantial
            # token of THAT rejects a credit that names the author perfectly, which is the false positive
            # this gate must never produce: it blocks delivery on correct attribution. Cut at the first
            # boilerplate marker and check the name.
            name = re.split(r"\s[-–—]\s|©|\(Want\b|Original publication|\bWikimedia\b|[\r\n]", artist)[0]
            bare = re.sub(r"\([^)]*\)", " ", name)[:80]
            # CJK is read from the NAME including any parenthesised form (a Chinese name often sits
            # in brackets beside its romanisation), but only from the name, never the boilerplate.
            cjk = re.findall(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]+", name[:80])
            latin = [w for w in re.findall(r"[A-Za-zÀ-ÿ]{2,}", bare) if w.lower() not in _ROLE]
            # EVERY substantial token must be present, not half of them. A half-match passes the credit
            # 'Massimo Smith' for a photograph by Massimo Catarinella — the right first name and the wrong
            # photographer, which is precisely the defect this gate exists to catch, and a false NEGATIVE is
            # far worse here than the false positives fixed earlier: it ships the breach silently.
            # Particles and initials (de, van, der, J, P) are dropped from the requirement because Commons
            # and a credit line order them differently; if a name is nothing BUT particles, they are all
            # that is left to check and they are required.
            need = [w for w in latin if len(w) >= 3] or latin
            hit_cjk = all(w in credits for w in cjk)
            hit_lat = all(w.lower() in credits.lower() for w in need)
            named = bool(cjk or latin) and hit_cjk and hit_lat
            if artist and (cjk or latin) and not named:
                errors.append(
                    "beat %d shows %s but does not credit its author. The sidecar says %r; the beat's "
                    "credit reads %r. A CC licence requires the actual creator to be named."
                    % (i, rel, artist, credits[:90] or "(nothing)"))
            elif lic and lic.lower() not in credits.lower():
                warnings.append(
                    "beat %d credits %s to the right author but states no matching licence (sidecar says "
                    "%r)." % (i, rel, lic))


def _film_language(meta, slides, errors, warnings):
    """Is the film's own CUT vocabulary actually being used, or is every seam the anonymous default?

    The remotion tier ships five kinetic seams, a luminance guard that protects them, and a `carry`
    match-cut that reads as continuity rather than a swap. A delivered 35-beat film used none of them:
    all 34 cuts were the default cross-fade, because nothing in the authoring path ever wrote
    `transition_in` — the key was not in the storyboard at all. Everything worked; nothing was reached.

    That is the failure this warns about. It is a WARNING, not an error: a film whose argument really is
    one unbroken line is entitled to leave every cut invisible. But it must be a decision someone made,
    and `scripts/seam_plan.py` derives a defensible plan from the `relation` field the board already has.
    """
    n = len(slides)
    if n < 12:
        return                                  # too short for punctuation to mean anything
    # from beat 1: there is no seam before the first shot, so a mark there counts nothing and made the
    # message read "20 of 19 cuts are MARKED"
    marked = [i for i, s in enumerate(slides)
              if i > 0 and (s.get("transition_in") or s.get("transition_style"))]
    # `meta.design_dna` is EITHER an inline DNA object OR a preset NAME — both are documented, both are
    # accepted by coerceDna() on the TS side, and the string form is validated a few hundred lines below.
    # This check read it as a dict unconditionally and crashed the whole gate with an AttributeError the
    # first time a film declared its DNA the short way. A validator that dies on a legal board is worse
    # than the defect it was looking for: nothing downstream of it ran.
    dna_raw = meta.get("design_dna")
    dna = dna_raw if isinstance(dna_raw, dict) else {}
    native = (dna.get("seam") or {}).get("type")
    if isinstance(dna_raw, str) and dna_raw:
        # A preset carries its OWN native seam (terminal clears the screen, editorial lays a sheet down),
        # so the swamping check below cannot see it from here. Say so rather than reporting a clean run.
        warnings.append(
            "meta.design_dna is the preset %r, whose NATIVE seam this check cannot resolve — the "
            "\"declared seam swamps the marks\" test below is therefore only measuring the %d authored "
            "mark(s). Declare `seam` inline if you need that checked." % (dna_raw, len(marked)))
    if not marked:
        warnings.append(
            "%d beats and not one MARKED seam — every cut is the anonymous default. The tier implements "
            "clock/slide/wipe/dissolve and `carry` (a collapse-to-line match-cut that reads as continuity), "
            "and the board already says which beats are new-topic / payoff / close. Run "
            "`python3 scripts/seam_plan.py <out_dir>` to derive ~2-3 marked cuts from that, or set them by "
            "hand; leave it bare only if the film is deliberately one unbroken line." % n)
    elif len(marked) > max(4, n // 8):
        warnings.append(
            "%d of %d cuts are MARKED — a marked seam is punctuation and only reads as punctuation while it "
            "is rare. Budget ~2-3 per film and let the rest be the default cut." % (len(marked), n - 1))
    # A camera move the tier does not have is DROPPED by render_remotion — silently, so the author's
    # intent vanishes with no signal at all. Measured: `{"move":"orbit","amount":3}` produced not one word.
    cam_vocab = {"push", "pull", "hold"}
    bad_cam, wild_amt = [], []
    for i, sl in enumerate(slides, 1):
        c = sl.get("camera")
        if c is None:
            continue
        if not isinstance(c, dict) or str(c.get("move", "")).strip().lower() not in cam_vocab:
            bad_cam.append(i)
            continue
        try:
            a = float(c.get("amount")) if c.get("amount") is not None else None
        except (TypeError, ValueError):
            wild_amt.append(i)
            continue
        if a is not None and not (0 < a <= 0.2):
            wild_amt.append(i)
    if bad_cam:
        warnings.append(
            "beat(s) %s carry a `camera` the renderer will silently drop — the move must be one of %s. "
            "A dropped move looks exactly like a beat nobody wrote a camera for."
            % (", ".join(map(str, bad_cam[:8])), "/".join(sorted(cam_vocab))))
    if wild_amt:
        warnings.append(
            "beat(s) %s give `camera.amount` a value outside 0-0.2; SceneCamera clamps it to what the "
            "caption band can absorb, so the number on the page is not the move on the screen."
            % ", ".join(map(str, wild_amt[:8])))

    # THE TWO CAMERA LAYERS COMPETE FOR ONE BUDGET. The film-wide ambient drift and the per-beat move both
    # scale the picture toward the caption band, so `maxCameraPush` hands the beat only what the drift has
    # not spent. Measured at 16:9: drift 1.0 leaves 4.8%, drift 1.5 leaves 2.1% — under the 0.045 default —
    # and drift 2.0 leaves nothing at all, silently clamping every authored move to zero. An author who set
    # both would see no camera and no reason why.
    try:
        drift = float(meta.get("camera_drift") or 0)
    except (TypeError, ValueError):
        drift = 0.0
    moving = [i for i, sl in enumerate(slides, 1) if isinstance(sl.get("camera"), dict)
              and str(sl["camera"].get("move", "")).lower() in ("push", "pull")]
    if drift > 0 and moving:
        from _caption_band import aspect_wh as _awh, caption_band_px as _band, _fracs as _fr
        W, H = _awh(meta.get("aspect"))
        f = _fr()
        blockH = min(W, H) * (f["CAPTION_SIZE_FRAC"] * f["CAPTION_LEAD"]
                              * (f["CAPTION_LINES"] + (1 if W < 1400 else 0)) + f["CAPTION_MARGIN_FRAC"])
        headroom = (_band(W, H) - blockH) - (H / 2) * (drift * 0.045)
        zoneH = max(1, H - 176 - _band(W, H))
        cap = max(0.0, (headroom / (zoneH / 2)) * 0.75)
        if cap < 0.045:
            warnings.append(
                "meta.camera_drift %.2f leaves the per-beat camera only %.1f%% of push before it would "
                "reach the caption, so the %d authored move(s) are clamped%s. The two layers scale the same "
                "picture toward the same band — pick one: the ambient drift, or the motivated per-beat move."
                % (drift, cap * 100, len(moving), " to nothing" if cap <= 0.001 else ""))

    seam_vocab = {"wipe", "slide", "clock", "dissolve", "screen-clear", "fade"}
    if native and native not in seam_vocab:
        warnings.append(
            "meta.design_dna.seam.type '%s' is not one of %s — Film.tsx silently falls back to the preset "
            "switch, so the declared cut never happens and the film looks like it was ignored."
            % (native, "/".join(sorted(seam_vocab))))
    # A film with NO design_dna at all is a different (and separately reported) situation; calling it a
    # "bespoke direction named None" was a confusing message for a real state.
    # A DECLARED native seam applies to every UNMARKED cut, which is nearly all of them. On a film whose
    # shots share a ground it made 32 of 34 cuts kinetic, and the 2 deliberate chapter marks then read
    # exactly like the 32 that mean nothing — the film lost its punctuation to the thing meant to give it
    # a voice. So this is not something to nag an author into. A gentle cross-fade is the filmic default
    # and is a good answer; `seam` is for a world with a genuine native ACTION (a terminal clearing its
    # screen), and the warning now fires the other way.
    if native and native != 'fade' and len(marked) and (n - 1 - len(marked)) > 6 * len(marked):
        warnings.append(
            "meta.design_dna.seam makes all %d unmarked cuts kinetic while only %d are MARKED — a mark only "
            "reads as punctuation when the cuts around it do not. Either drop the native seam (a plain "
            "cross-fade is the correct default, not a missing decision) or accept that this film's cuts are "
            "a texture rather than a structure."
            % (max(0, n - 1 - len(marked)), len(marked)))



_FORM_TOKENS = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+")


def _catalogue_forms(names):
    """{declared form: the register whose name it already is} — the shopped half of a form vocabulary.

    Tokenised on case boundaries so `StrataColumn` reads as {strata, column}, and matched by prefix so a
    subject's "stratigraphic column" is recognised as the register's "strata column". A form counts as the
    catalogue's when at least two of its tokens match one register's, or when a single-word form is a
    single-word register outright.
    """
    shots = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "shots")
    if not os.path.isdir(shots):
        return {}
    reg = {}
    for f in os.listdir(shots):
        if f.endswith(".tsx"):
            reg[f[:-4]] = [t.lower() for t in _FORM_TOKENS.findall(f[:-4])]

    def pref(a, b):
        return a == b or (len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)))

    out = {}
    for form in names:
        ft = [t.lower() for t in _FORM_TOKENS.findall(str(form).replace("-", " "))]
        if not ft:
            continue
        best = None
        for rname, rt in reg.items():
            m = sum(1 for t in ft if any(pref(t, r) for r in rt))
            if m >= 2 or (len(ft) == 1 and m == 1 and len(rt) == 1):
                if best is None or m > best[1]:
                    best = (rname, m)
        if best:
            out[form] = best[0]
    return out


def _form_vocabulary(meta, slides, errors, warnings):
    """Every beat must name which of the SUBJECT'S OWN forms it realises.

    A design language has two layers. The direction contest conceives the ATMOSPHERE from the topic —
    palette, type, motion. The FORM VOCABULARY is the other one: what kind of object each frame IS. A
    dictionary entry, a stratigraphic column, a ledger, a departure board, a score, a docket, a patent plate.
    That layer used to arrive from the catalogue, which means whatever the catalogue is mostly made of
    became every film's vocabulary. A city documentary came out of an AI-product library speaking
    developer-tool: six terminal shots, a SaaS dashboard under a children's book character, a factory
    conveyor belt for people cycling to a station — 16 of 35 beats, every one passing its own gates.

    Prose in an agent file could not stop that; nothing checked it. This does. `meta.form_vocabulary` is the
    derivation, and each beat's `shot_fit.form` must name one entry of it, so a register cannot be assigned
    without saying which form OF THIS SUBJECT it is. Shopping the catalogue then fails at the gate rather
    than at the review.
    """
    vocab = meta.get("form_vocabulary")
    if not vocab:
        warnings.append(
            "remotion: no meta.form_vocabulary — the film never derived what KIND of object each frame "
            "should be from its own subject, so its forms came from whatever the catalogue happens to hold. "
            "See agents/shot-director.md step 0.5; name 6-10 forms the subject is actually recorded in.")
        return
    names = set()
    for i, f in enumerate(vocab if isinstance(vocab, list) else []):
        if isinstance(f, dict):
            n = str(f.get("form") or "").strip()
            if not n:
                errors.append("meta.form_vocabulary[%d] has no `form` name" % i)
            else:
                names.add(n)
            if not str(f.get("carries") or "").strip():
                warnings.append("meta.form_vocabulary[%d] (%s) does not say what argument it CARRIES — a "
                                "form without an argument shape is a picture style, not a vocabulary entry"
                                % (i, n or "?"))
        elif isinstance(f, str) and f.strip():
            names.add(f.strip())
    if len(names) < 4:
        warnings.append("meta.form_vocabulary names only %d form(s) — a subject worth a film is recorded in "
                        "more ways than that; a short list forces the catalogue back in" % len(names))

    # ── DID IT DERIVE, OR DID IT SHOP? ──────────────────────────────────────────────────────────────────
    # Everything above checks that the derivation was DECLARED. None of it checks that it was a derivation.
    # A film could name six forms that are simply the names of six existing registers, point every beat at
    # one of them, and pass — the catalogue supplying the vocabulary again, now with paperwork. The
    # shot-director's rule 2 ("at least half must be forms this library does NOT already have; if everything
    # you name is already a register, you shopped") was the one rule that distinguishes the two, and it was
    # the only one with nothing behind it.
    #
    # A register's FILE NAME is its form name (StrataColumn, MuseumLabel, DepartureBoard), so the overlap is
    # measurable. Warning, not error: a real subject can genuinely be recorded in a form the library already
    # holds, and a museum label is a museum label. So it names the evidence and lets a human overrule it.
    shopped = _catalogue_forms(names)
    if names and len(shopped) * 2 > len(names):
        warnings.append(
            "remotion: %d of %d forms in meta.form_vocabulary are names the library ALREADY has (%s) — that "
            "is a shopping list wearing a derivation's clothes. Re-read the comprehension brief and ask how "
            "this subject is recorded by the people whose subject it is; at least half the vocabulary should "
            "be forms this library has never held (agents/shot-director.md step 0.5, rule 2)."
            % (len(shopped), len(names),
               "; ".join("%s = %s" % (f, r) for f, r in sorted(shopped.items())[:6])))
    missing, unknown = [], []
    for s in slides:
        beat = int(s.get("index", 0)) + 1
        form = str(((s.get("shot_fit") or {}).get("form")) or "").strip()
        if not form:
            missing.append(beat)
        elif form not in names:
            unknown.append((beat, form))
    if missing:
        errors.append(
            "remotion: %d beat(s) name no `shot_fit.form` — a register was assigned without saying which of "
            "this subject's own forms it realises, which is how the catalogue supplies the vocabulary "
            "unnoticed (beats %s)" % (len(missing), ", ".join(str(b) for b in missing[:12])))
    for beat, form in unknown[:8]:
        errors.append("remotion: beat %d names form %r, which is not in meta.form_vocabulary — either add it "
                      "to the derivation or pick a form the film actually derived" % (beat, form))

def _shot_truncation(meta, slides, errors, warnings):
    """A shot whose clip is far shorter than its natural pace plays RUSHED.

    NOT truncation. `useT()` normalises over the REAL scene duration (Film.tsx supplies it through
    SceneDurationContext), so a shot always reaches its settled state whatever the clip length — a short
    clip just animates faster. A first version of this check treated `DURATION` as "frames the shot needs"
    and reported eight beats as cut off; they were not. `DURATION` is only the standalone-preview length.

    What IS real: a register authored to breathe over 5.6s and handed 3.5s plays its whole language 1.6x
    fast, then cuts. That reads as hurried rather than as a shot landing. It is a pacing signal, so it
    warns and never blocks — the answer is a longer line for that beat or a register with a calmer
    natural pace, and sometimes the compression is fine.
    """
    import glob as _glob
    shots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "shots")
    need = {}
    for f in _glob.glob(os.path.join(shots_dir, "*.tsx")):
        try:
            m = re.search(r"export const DURATION\s*=\s*(\d+)", open(f, encoding="utf-8").read())
        except OSError:
            continue
        if m:
            need[os.path.basename(f)[:-4]] = int(m.group(1))
    if not need:
        return
    fps = float(meta.get("fps", 30) or 30)
    seam = _seam_frames()
    for s in slides:
        shot = s.get("shot")
        n = need.get(shot)
        dur = s.get("duration")
        if not n or not isinstance(dur, (int, float)) or not dur:
            continue
        have = int(round(float(dur) * fps)) - seam
        ratio = n / max(1.0, float(have))
        if ratio < 1.35:                     # under a third faster than authored: not worth mentioning
            continue
        beat = int(s.get("index", 0)) + 1
        warnings.append(
            "remotion: beat %d (%s) plays %.1fx faster than the register's natural pace (clip %d frames vs an "
            "authored %d) — its whole design language happens in a rush and then cuts. Give the beat a longer "
            "line, or a register that settles more calmly." % (beat, shot, ratio, have, n))


def _seam_frames(default=12):
    """SEAM_FRAMES from runtime/motion.ts — the cross-dissolve the next scene overlaps onto this one."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "runtime", "motion.ts")
    try:
        m = re.search(r"export const SEAM_FRAMES\s*=\s*(\d+)", open(p, encoding="utf-8").read())
        return int(m.group(1)) if m else default
    except OSError:
        return default

def _demo_copy_library():
    """{register: {prop: the copy its default prints}} — PARSED from each register's signature.

    Parsed, not listed, for the reason the `NUM` map right below documents in its own comment: a restated
    list of registers went stale and two number-bearing registers sat exempt from the faithfulness check. The
    same list for copy would be 136 registers and 267 props, and wrong the day someone adds a register."""
    global _DEMO_COPY_CACHE
    if _DEMO_COPY_CACHE is None:
        try:
            import demo_copy_qa
            _DEMO_COPY_CACHE = demo_copy_qa.library()
        except Exception:
            _DEMO_COPY_CACHE = {}      # unavailable → skip rather than false-flag every beat
    return _DEMO_COPY_CACHE


_DEMO_COPY_CACHE = None


def _check_remotion(meta, slides, errors, warnings, out_dir=None):
    """Guardrails for the remotion bespoke-shot tier: a valid whole-film `shot_template` direction (+ its
    contest trace); every scene needs a valid `shot` id + object `shot_props`; a NUMBER-bearing register left on
    its illustrative demo default is flagged (a real film must pass a SOURCED figure); a register left as a raw
    TEXT-SWAP — empty `shot_props` or no recorded `shot_adaptation` — is flagged (keep the register's STYLE but
    redesign its modules/components + content to THIS topic, §B2); adjacent same-FAMILY scenes are flagged (vary
    the design language). Ids auto-derived from remotion/src/shots so this never drifts from the library.
    The adapt lint is a PROXY (a script sees empty props + a missing note, never whether the components were
    truly redesigned) — the SEMANTIC verdict is shot-critic S10 (the note vs the rendered pixels)."""
    _check_shot_template(meta, errors, warnings)
    # DESIGN DNA — the GLOBAL visual system every shot inherits (runtime/dna.tsx). A themed film should carry an
    # explicit meta.design_dna artifact (the reviewable "Design DNA", docx Artifact A) OR a shot_template that maps
    # to a built-in DNA preset; else every shot renders its OWN hardcoded identity and the film reads as "different
    # compositions, different templates" (no global visual system). Keep _DNA_PRESETS in sync with DNA_PRESETS in
    # remotion/src/runtime/dna.tsx.
    # Keep in sync with DNA_PRESETS in remotion/src/runtime/dna.tsx (a themed film = any of these OR an explicit
    # meta.design_dna). Missing an editorial/product/blueprint key here would let those themed films dodge the
    # themed-only lints (theme_cues coverage + un-migrated-register), so the whole preset set must be listed.
    _DNA_PRESETS = _DNA_PRESETS_FOR_TEST()
    # every token a component actually reads — a partial DNA no longer crashes (Film coerces it through
    # NEUTRAL_DNA) but it DOES silently borrow neutral values, so name what is missing.
    _DNA_KEYS = ("fontDisplay", "fontMono", "fontBody", "bg", "fg", "dim", "accent", "accent2",
                 "onAccent", "surface", "line", "decoration", "motion")
    # PACING. meta.scene_pause is the silence a viewer HEARS between two scenes; tts.py converts it into a
    # per-tier pad. It is unvalidated at your peril: a negative or tiny value silently reproduces the exact
    # defect it was introduced to fix — a delivered film measured 0.18s at every seam, SHORTER than its own
    # within-sentence comma pauses, which reads as the next scene cutting in before the sentence lands.
    _sp = meta.get("scene_pause")
    if _sp is not None:
        try:
            _spv = float(_sp)
        except (TypeError, ValueError):
            errors.append("meta.scene_pause must be a number of seconds, got %r" % (_sp,))
            _spv = None
        if _spv is not None:
            if _spv < 0:
                errors.append("meta.scene_pause is negative (%s) — it is a duration in seconds" % _spv)
            elif _spv < 0.3:
                warnings.append("meta.scene_pause %.2fs is shorter than a within-sentence comma pause — the "
                                "gap between two scenes will read as no gap at all. ~0.5-0.7s is a breath; "
                                "the default is %.2f." % (_spv, 0.55))
            elif _spv > 1.2:
                warnings.append("meta.scene_pause %.2fs is a long hold, not a breath — each scene will end on "
                                "a frozen silent frame that reads as the video hanging. Reading time belongs "
                                "in a slower meta.tts_speed." % _spv)
    # A film-energy WAIVER is legitimate, and it is also the one lever that turns film_energy_qa green
    # without changing a frame. Announce it at the FIRST gate, not only at the last: a waiver the author
    # wrote is a decision; a waiver that has quietly outlived the film it was written for is a hole.
    # A CJK CHARACTER THE BUNDLED FACES CANNOT DRAW IS A HOLE IN THE FRAME. The faces are subset to
    # GB2312 (every character normal Chinese prose uses), so a rare surname or a classical form renders as
    # a blank box beside correct type — which reads as a rendering bug and which no other gate looks at.
    # Asked of the font file, before the render, where it costs nothing.
    _txt = " ".join([str(meta.get("title") or "")] +
                    [str(sl.get("narration") or "") + " " + json.dumps(sl.get("shot_props") or {},
                                                                       ensure_ascii=False)
                     for sl in slides])
    try:
        import cjk_type_qa as _cq
        _uncov = _cq.subset_coverage(_txt)
    except Exception:                                    # noqa: BLE001 — a diagnostic never blocks
        _uncov = None
    if _uncov:
        errors.append("remotion: %d character(s) in this film's copy are outside the bundled CJK subset and "
                      "would render as an empty box: %s. The bundled faces cover GB2312 (all normal "
                      "Simplified Chinese) plus kana, punctuation and Latin — NOT Hangul, rare/classical "
                      "Han, or Japanese kanji outside GB2312. Replace the characters, or re-subset the "
                      "faces (assets/fonts/NOTO-SC-SUBSET-NOTE.txt says how)."
                      % (len(_uncov), " ".join("%s (U+%04X)" % (c, cp) for c, cp in _uncov[:12])))
    # ...AND A CJK FILM WHOSE FONT STACKS NAME NO BUNDLED FACE IS NOT USING THEM AT ALL. The subsets were
    # bundled for determinism — the same film renders the same on any machine — and a stack that lists only
    # system families (PingFang, YaHei, Songti) falls through to whatever the render box happens to have.
    # This is not hypothetical: the presets in runtime/dna.tsx were given the subsets and `dna_from_deck.py`
    # was not, so the ONE path a real Chinese film takes was the one path that never reached them.
    _dna_obj = meta.get("design_dna") if isinstance(meta.get("design_dna"), dict) else None
    if _txt.strip() and _dna_obj:
        try:
            import cjk_type_qa as _cq2
            _bundled = [f for f, has in (_cq2.bundled_cjk_coverage() or []) if has]
        except Exception:                                # noqa: BLE001 — a diagnostic never blocks
            _bundled = []
        _fams = {re.sub(r"-Subset$", "", os.path.splitext(os.path.basename(f))[0]).replace("-", " ")
                 for f in _bundled}
        _fams |= {"Noto Sans SC", "Noto Serif SC"}
        if _bundled and _cq2._HAS_CJK.search(_txt):
            _blind = [k for k in ("fontDisplay", "fontBody", "fontMono")
                      if isinstance(_dna_obj.get(k), str) and _dna_obj[k]
                      and not any('"%s"' % f in _dna_obj[k] for f in _fams)]
            if _blind:
                warnings.append(
                    "remotion: this film's copy is CJK and meta.design_dna names no BUNDLED CJK face in %s — "
                    "every Chinese glyph will be drawn by whatever font the render machine has installed, so "
                    "the film's typography is not reproducible and the Design DNA does nothing to it. Put "
                    "\"Noto Sans SC\" (or \"Noto Serif SC\" in a serif world) at the head of the CJK chain."
                    % ", ".join(_blind))
    _v = meta.get("voice")
    if isinstance(_v, str) and _v.strip().lower() in ("edge", "openai", "minimax"):
        errors.append("meta.voice=%r is a bare ENGINE name, and tts.py reads everything before the first ':' as "
                      "the engine — with no colon the whole string is a macOS `say` VOICE name, so the film "
                      "would be narrated by the offline robotic voice with no per-word timings. Write "
                      "\"%s:<voice-name>\" (e.g. \"edge:zh-CN-XiaoxiaoNeural\") or \"auto\"." % (_v, _v.strip().lower()))
    _ew = meta.get("energy_waiver")
    if _ew is not None:
        # The waiver is PER-AXIS, and this reads it through film_energy_qa's own parser rather than a second
        # copy — a copy here that still assumed a string rejected a legitimate object the day the gate began
        # accepting one.
        try:
            import film_energy_qa as _fe
            _axes, _blanket = _fe.parse_waiver(_ew)
            _known = set(_fe.AXES)
        except Exception:                                # noqa: BLE001
            _axes, _blanket, _known = ({}, _ew if isinstance(_ew, str) else "", set())
        if not _axes and not _blanket:
            errors.append("meta.energy_waiver must be a non-empty reason, or an object naming the axes it "
                          "waives (e.g. {\"density\": \"why\"}) — it switches a delivery floor off, so it has "
                          "to say why")
        elif _blanket:
            warnings.append("meta.energy_waiver is a plain STRING, so it waives EVERY film-energy floor "
                            "(motion, density, light, arc) — not only the one you reasoned about. Name the "
                            "axes instead to keep the rest gated: %r" % _blanket[:100])
        else:
            _bad = sorted(a for a in _axes if _known and a not in _known)
            if _bad:
                errors.append("meta.energy_waiver names axis/axes %s that no floor is called — expected any "
                              "of %s, so this waiver silently covers nothing" % (_bad, sorted(_known)))
            warnings.append("meta.energy_waiver ACCEPTS rather than meets: %s. Confirm each still describes "
                            "the current cut." % ", ".join(sorted(set(_axes) - set(_bad))))
    design_dna = meta.get("design_dna")
    # THE DECK IS THE BRAND. When the film was ingested from a pptx whose theme is NOT Office's default, its
    # colours and typefaces were chosen by someone — and a preset DNA (or none) paints over them with a
    # direction's generic identity. `dna_from_deck.py` reads that theme (and the rendered frames) into a
    # Design DNA; a hand-authored object is left alone, because authoring is a decision too.
    _src = str(meta.get("source") or "")
    if _src.lower().endswith(".pptx") and os.path.exists(_src) and not isinstance(design_dna, dict):
        try:
            import pptx_theme as _pt
            _t = _pt.read(_src)
        except Exception:                                        # noqa: BLE001 — a diagnostic never blocks
            _t = None
        if _t and not _t.get("default_theme"):
            warnings.append("remotion: the source deck carries its OWN theme (%r: accent %s, %s / %s) but the film "
                            "wears %s — run `python3 scripts/dna_from_deck.py <out_dir>` so the film carries the "
                            "deck's brand, then retune the object it writes if you must."
                            % (_t.get("scheme"), (_t.get("colors") or {}).get("accent1"),
                               ((_t.get("fonts") or {}).get("major") or {}).get("latin") or "?",
                               ((_t.get("fonts") or {}).get("minor") or {}).get("latin") or "?",
                               ("the preset %r" % design_dna) if design_dna else "no design_dna"))
    if isinstance(design_dna, str):
        # A STRING design_dna is a preset NAME. This used to reach coerceDna(), which spread the string's
        # character indices over NEUTRAL_DNA and returned the neutral palette — the whole film rendered in
        # the wrong design system, silently. The runtime now throws on an unknown name; catch it here, before
        # a render that costs minutes.
        if design_dna not in _DNA_PRESETS:
            errors.append("meta.design_dna \"%s\" is not a known preset — expected one of %s (or an inline "
                          "DNA object)." % (design_dna, sorted(_DNA_PRESETS)))
    elif design_dna is not None and not isinstance(design_dna, dict):
        errors.append("meta.design_dna must be a preset name or an object, got %s" % type(design_dna).__name__)
    if isinstance(design_dna, dict):
        _miss = [k for k in _DNA_KEYS if not design_dna.get(k)]
        if _miss:
            warnings.append(f"meta.design_dna is missing core key(s) {_miss} — a Design DNA needs at least "
                            f"{list(_DNA_KEYS)} so every shot can inherit its type + palette (runtime/dna.tsx).")
        atoms = design_dna.get("atoms")
        if atoms is None:
            warnings.append("meta.design_dna declares no `atoms` — every shot's Bar/Figure/List/Label/"
                            "Divider/Marker will render its NEUTRAL or `fallbackForm` (a migrated shot's "
                            "own pre-atoms look), never a form this DNA speaks. A migrated shot (e.g. "
                            "EdStat, TermCounter, TermBars) will keep its ORIGINAL form via fallbackForm "
                            "even while every other token follows this DNA — add an `atoms` block "
                            "(runtime/dna.tsx AtomForms) so the shots' content parts follow it too.")
        elif not isinstance(atoms, dict):
            warnings.append("meta.design_dna.atoms must be an object mapping an atom to a form "
                            "(e.g. {\"bar\": \"block\"}) — ignoring it; every atom will use its neutral form")
        elif isinstance(atoms, dict):
            for _k, _v in atoms.items():
                if _k not in _ATOM_FORMS:
                    warnings.append(f"meta.design_dna.atoms has unknown atom {_k!r} — known atoms are "
                                    f"{sorted(_ATOM_FORMS)}; it will be ignored")
                elif _v not in _ATOM_FORMS[_k]:
                    warnings.append(f"meta.design_dna.atoms.{_k} = {_v!r} is not a form this atom implements "
                                    f"({sorted(_ATOM_FORMS[_k])}) — it will render the neutral form instead")
    elif str(meta.get("shot_template") or "") not in _DNA_PRESETS:
        warnings.append("remotion: NO Design DNA — no meta.design_dna, and meta.shot_template maps to no known DNA "
                        "preset, so every shot renders its ORIGINAL hardcoded identity and the film reads as "
                        "'different compositions, different templates'. Author meta.design_dna (Design DNA artifact) "
                        "or pick a template with a preset (runtime/dna.tsx) so ONE visual system runs through every shot.")
    _themed = isinstance(design_dna, dict) or str(meta.get("shot_template") or "") in _DNA_PRESETS  # DNA-themed film
    shots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "shots")
    valid = {f[:-4] for f in os.listdir(shots_dir) if f.endswith(".tsx")} if os.path.isdir(shots_dir) else set()
    try:                          # which shots READ the Design DNA (self-updating grep of the source) — the rest
        import dna_audit as _da   # wear a hardcoded palette and won't unify on a THEMED film (lint below)
        _dna_aware = _da.dna_aware_shots()
    except Exception:
        _dna_aware = None         # audit unavailable → skip the migration lint rather than false-flag everything
    # Every register that puts a SOURCED FIGURE on screen. EdStat and TermCounter were missing, so two
    # registers that display a headline number were exempt from the demo-default faithfulness check.
    NUM = {"ChartLive": "endVal", "BeforeAfterSlider": "metric", "VelocitySnap": "metric",
           "OdometerRoll": "value", "GaugeCluster": "value", "ChartRace": "data",
           "EdStat": "value", "TermCounter": "value"}
    brief_nums = _brief_numbers(out_dir)     # figures a number-bearing shot must trace to (None = no brief)
    seq = []
    _fit_missing, _fit_verdicts = [], []     # the per-beat fit judgement (see the shot_fit block below)
    for s in slides:
        tag = "scene #%s" % s.get("index")
        shot = s.get("shot")
        if not shot:
            errors.append(f"{tag}: meta.renderer='remotion' but the scene has no `shot` (a register id) — run "
                          f"the shot-director step; valid ids are in remotion/LIBRARY.md")
            seq.append(None); continue
        if valid and shot not in valid:
            errors.append(f"{tag}: unknown shot {shot!r} — see remotion/LIBRARY.md for the valid ids")
            seq.append(None); continue
        sp = s.get("shot_props")
        if sp is not None and not isinstance(sp, dict):
            errors.append(f"{tag}: `shot_props` must be an object")
        if shot in NUM and (not isinstance(sp, dict) or NUM[shot] not in sp):
            warnings.append(f"{tag}: {shot} shows an ILLUSTRATIVE demo number by default — pass "
                            f"shot_props.{NUM[shot]} a SOURCED figure, or use a non-number register (no-fake-info)")
        elif shot in NUM and brief_nums is not None:
            # the value IS set — a bare counter (endVal:250) has no %/× unit so _figure_traceability can't see it;
            # check its digits trace to brief.json evidence (a fabricated on-screen figure, else silent on remotion)
            for n in re.findall(r"\d+(?:\.\d+)?", json.dumps(sp.get(NUM[shot]), ensure_ascii=False)):
                if n not in brief_nums:
                    warnings.append(f"{tag}: {shot} shows figure '{n}' (shot_props.{NUM[shot]}) not in brief.json "
                                    f"evidence — every on-screen number must trace to the source; cite it, reframe, "
                                    f"or use a non-number register (no invented figures)")
                    break
        # ADAPT-don't-text-swap (§B2): keep the register's STYLE, redesign its modules/components + content for
        # THIS topic. A script can't see a true redesign, but it CAN catch the crudest text-swap — empty props —
        # and a missing/stub adaptation note; the SEMANTIC verdict is shot-critic S10 (the note vs the pixels).
        props_empty = (not isinstance(sp, dict)) or (len(sp) == 0)
        adapt = s.get("shot_adaptation")
        adapt_ok = (isinstance(adapt, dict)
                    and isinstance(adapt.get("redesigned"), str) and adapt["redesigned"].strip()
                    and isinstance(adapt.get("topic_idea"), str) and adapt["topic_idea"].strip())
        # DEMO COPY that ships as content. Empty props are the crude case and were already caught; the
        # dangerous case is PARTIAL props, which read as authored. A delivered Chinese film about a real
        # product shipped BentoReveal with title/hero/heroKicker in its own words and no `items` — so six of
        # the frame's seven cells printed the register's English demo labels (Throughput / Coverage / Trend /
        # Signals / Team / Auto-sync) and every gate was green. That register's own source comments record the
        # same bug being fixed once before, for `heroKicker`; the fix turned the hardcoded word into a prop,
        # which moved the default one level down and left the hole exactly where it was.
        # An ERROR, not a warning: the empty plate says nothing, this says something FALSE.
        _props_empty = (not isinstance(sp, dict)) or (len(sp) == 0)
        if isinstance(sp, dict) and shot in _demo_copy_library():
            _left = [(p, c) for p, c in sorted(_demo_copy_library()[shot].items()) if p not in sp]
            if _left and _props_empty:
                # An empty-props beat already HAS a finding below (the mannequin warning), and it names the
                # right problem. Stacking a second, longer error on the same beat teaches the author nothing
                # — but the warning never said what would actually be READ off the frame, so say that.
                warnings.append(f"{tag}: {shot} with empty shot_props will PRINT its demo copy: "
                                + "; ".join(f"{p}={c}" for p, c in _left[:4])
                                + (" …" if len(_left) > 4 else ""))
                _left = []
            for prop, copy in _left:
                off = "[]" if copy.startswith("[") else '""'
                errors.append(f"{tag}: {shot} was given no `{prop}`, so the register's DEMO COPY prints on "
                              f"the delivered frame: {copy}. Write this beat's own copy, or set "
                              f"`shot_props.{prop}` to {off} to draw nothing there.")
        if props_empty:
            warnings.append(f"{tag}: {shot} carries EMPTY shot_props — a raw text-swap keeps the register's demo "
                            f"scaffolding (a mannequin), shipping a generic beat. Redesign its modules/components + "
                            f"content for THIS topic and record shot_adaptation (adapt-don't-text-swap §B2)")
        elif not adapt_ok:
            warnings.append(f"{tag}: {shot} has no recorded shot_adaptation {{kept, redesigned, topic_idea}} — every "
                            f"beat must KEEP the register's style but REDESIGN its modules/components + content for "
                            f"THIS topic; record what you kept vs rebuilt so shot-critic S10 can verify it (§B2)")
        elif _themed and not (isinstance(adapt.get("theme_cues"), (list, str)) and adapt.get("theme_cues")):
            warnings.append(f"{tag}: {shot} on a DNA-themed film records no shot_adaptation.theme_cues — name the "
                            f"2-3 concrete cues that tie THIS shot to the global visual system (Design DNA coverage "
                            f"check); shot-critic S11 verifies them against the rendered frame.")
        # FIT JUDGEMENT — the trigger for BUILDING a new register. The library can grow, and the authoring
        # reference has always said so; in practice it never did, because nothing ever ASKED whether a beat's
        # argument actually had a register. The director's own first rule was "match intent -> register", so
        # every beat got matched to the closest existing one whether or not that register's structure could
        # carry the claim. `shot_fit` makes the judgement explicit and reviewable:
        #   fit   — the register's own structure already carries this beat's argument shape
        #   adapt — the structure fits; its modules are redesigned for this content (§B2)
        #   build — no register's structure carries it, so a NEW one was authored (scripts/register_shot.py)
        fit = s.get("shot_fit")
        verdict = (fit or {}).get("verdict") if isinstance(fit, dict) else None
        if verdict is None:
            _fit_missing.append(s.get("index"))
        elif verdict not in ("fit", "adapt", "build", "unjudged"):
            warnings.append(f"{tag}: shot_fit.verdict {verdict!r} is not one of fit/adapt/build")
        else:
            _fit_verdicts.append(verdict)
            if verdict == "build":
                # NOTE ON WHAT THIS CAN AND CANNOT CHECK: a "build" claim is not independently verifiable
                # here — nothing in the board proves a register was authored for THIS film rather than
                # picked from the catalogue and relabelled. What is checkable is that the claim is
                # COHERENT (the named register really is registered everywhere) and that the register is
                # REUSABLE rather than welded to one topic, which `shot_proof.py` measures against the
                # film's own strings. Do not read a passing build claim as proof of anything more.
                try:
                    import register_shot as _rs
                    _miss = _rs.check(shot)
                except Exception:                       # noqa: BLE001 — never let the gate crash the run
                    _miss = []
                if _miss:
                    errors.append(f"{tag}: shot_fit says a NEW register was built for this beat, but {shot} is "
                                  f"not registered in {', '.join(_miss)} — run "
                                  f"`python3 scripts/register_shot.py {shot} <FamilyLetter> --use-when '…'`")
        # UN-MIGRATED REGISTER on a themed film: a shot that never reads useDNA renders its OWN hardcoded palette,
        # breaking the global visual system (the exact "different compositions, different templates" defect the DNA
        # layer exists to fix). WARN (not ERROR): the fix is to migrate the shot (read dna tokens — see §C2 / the
        # shadow trick) or pick a DNA-aware register. `python scripts/dna_audit.py` lists the full worklist.
        if _themed and _dna_aware is not None and shot not in _dna_aware:
            warnings.append(f"{tag}: {shot} is NOT Design-DNA-aware (never reads useDNA) — on this themed film it "
                            f"renders its own hardcoded palette instead of the global visual system. Migrate it to "
                            f"read the DNA tokens (§C2 / shadow trick) or pick a DNA-aware register "
                            f"(`python scripts/dna_audit.py` for the worklist).")
        seq.append(shot)
    # WHOLE-FILM fit judgement. Two failure directions, and the gate has to watch BOTH:
    #  * the judgement is never made — nothing records shot_fit, so "no register can draw this" can never
    #    surface and the film is assembled purely by catalogue lookup;
    #  * the judgement is made and is always "perfect" — every beat allegedly matched a register exactly,
    #    which for a topic-specific film is the signature of matching rather than judging.
    if _fit_missing:
        warnings.append("remotion: %d of %d beats record no `shot_fit` {verdict: fit|adapt|build, why} — that "
                        "judgement is the ONLY thing that can surface \"no register in the library carries this "
                        "beat's argument\". Without it a film is assembled by catalogue lookup, and the library "
                        "never grows (scenes %s)"
                        % (len(_fit_missing), len(slides),
                           ", ".join(str(x) for x in _fit_missing[:8]) + (" …" if len(_fit_missing) > 8 else "")))
    # THE BUILD SIGNAL, AT THE DECISION. Nine of the library's twenty-five families hold a single
    # register, so "vary the family" pushes every film toward the four big ones, and a beat whose argument
    # wants a thin family has nothing to choose between: its one member either carries the argument or it
    # does not. Leaning on a thin family AND building nothing is the shape of settling, and how hard that
    # lands is the risk budget the author already chose — audacity.
    try:
        import shot_director as _sdx
        import collections as _co
        _famsize = _co.Counter(_sdx.FAMILY.values())
        _thin_used = sorted({_sdx.FAMILY.get(x) for x in seq
                             if _sdx.FAMILY.get(x) and _famsize[_sdx.FAMILY[x]] <= 2})
        _reused = {x for x in seq if seq.count(x) > 1}
        _thin_and_reused = sorted({x for x in seq
                                   if x in _reused and _famsize.get(_sdx.FAMILY.get(x), 9) <= 2})
    except Exception:
        _thin_used, _thin_and_reused = [], []
    _built = [v for v in _fit_verdicts if v == "build"]
    _aud = str(meta.get("audacity") or "balanced").lower()
    if _thin_used and not _built and _aud != "conservative":
        _msg = ("remotion: this film leans on thin famil%s %s — %s only ONE register in the whole library — "
                "and built nothing. When a beat's argument wants a language the library holds one example "
                "of, there is nothing to choose between: either that register carries the argument or the "
                "answer was `scripts/register_shot.py`. Record a `shot_fit` verdict of 'build' for the "
                "beat(s) it applies to, or say in `why` what made the single member fit."
                % ("y" if len(_thin_used) == 1 else "ies", ", ".join(_thin_used),
                   "it holds" if len(_thin_used) == 1 else "each holds"))
        if _aud in ("bold", "experimental"):
            errors.append(_msg + " At audacity '%s' this is an ERROR: that setting is a request to push, "
                                 "and settling for the only stocked option is the opposite." % _aud)
        else:
            warnings.append(_msg)
    if _thin_and_reused:
        warnings.append("remotion: %s sit(s) in a one- or two-register family AND carr%s more than one beat "
                        "in this film — the strongest build case there is, because the second use had no "
                        "alternative to move to." % (", ".join(_thin_and_reused),
                                                     "y" if len(_thin_and_reused) > 1 else "ies"))
    _unjudged = [v for v in _fit_verdicts if v == "unjudged"]
    if _unjudged:
        warnings.append("remotion: %d of %d beats carry shot_fit 'unjudged' — assigned deterministically, "
                        "with nobody asking whether the register's structure carries the beat's argument. "
                        "That question is the only thing that can surface \"nothing in the library can draw "
                        "this\"." % (len(_unjudged), len(slides)))
    elif len(slides) >= 10 and _fit_verdicts and all(v == "fit" for v in _fit_verdicts):
        warnings.append("remotion: every one of %d beats records shot_fit 'fit' — no beat needed its modules "
                        "redesigned and none needed a new register. On a topic-specific film that is the "
                        "signature of matching the catalogue rather than judging it. Re-read the beats whose "
                        "register you picked for its shape rather than its meaning." % len(slides))
    try:                                                   # family-variety: no two ADJACENT beats one look
        import shot_director as _sd
        fams = [_sd.FAMILY.get(x) if x else None for x in seq]
        for a, b, fa, fb in zip(seq, seq[1:], fams, fams[1:]):
            if fa and fa == fb:
                warnings.append(f"remotion: adjacent scenes {a}/{b} share family {fa} — vary the design "
                                f"language so the film doesn't read as one look")
    except Exception:
        pass
    try:                                                   # marked-seam BUDGET: most seams ride the safe fade
        import render_remotion as _rr
        marked = sum(1 for s in slides[1:] if _rr._transition_in(s))   # scene 0 has no incoming seam
        seams = max(0, len(slides) - 1)
        budget = max(3, seams // 3)
        if marked > budget:
            warnings.append(f"remotion: {marked} of {seams} seams are MARKED with a kinetic transition (budget "
                            f"~{budget}) — most seams should ride the luminance-safe default fade; marking them "
                            f"all is as monotonous as marking none (shot-director Rule 5)")
    except Exception:
        pass
    try:                                                   # color-arc: a dark<->light STROBE across the film
        import shot_director as _sd2
        lums = [_sd2.shot_luma(x) for x in seq if x]
        flips = sum(1 for a, b in zip(lums, lums[1:]) if _sd2._hard_flip(a, b))
        span = max(1, len(lums) - 1)
        if len(lums) >= 6 and flips / span > 0.6:
            warnings.append(f"remotion: {flips} of {span} seams hard-FLIP luminance (dark<->light) — the film "
                            f"STROBES (each seam is smooth, but the whole-film brightness pulse reads restless); "
                            f"sequence a calmer luminance ARC (runs/gradients via shotLuma), reserving a hard "
                            f"flip for a deliberate jolt (shot-director color-arc)")
    except Exception:
        pass
    # PARITY — capabilities the HTML/local tier honors that the remotion tier silently DROPS (no gate saw these
    # because evaluate() returns right after this function for a remotion deck).
    brand = meta.get("brand")
    if isinstance(brand, dict) and brand.get("logo"):
        # the logo now renders as a persistent corner BUG (Film.tsx BrandMark); note the tier limitation.
        warnings.append("remotion: meta.brand renders as a persistent corner BUG only — the remotion tier has no "
                        "authored cover/endcard LOCKUP page (that's an html-tier concept). Confirm the corner mark "
                        "reads on your grounds (it prefers logo_dark).")
    if meta.get("reduced_motion"):
        warnings.append("remotion: meta.reduced_motion freezes the camera, atmosphere, AND the 122 useT-driven shots "
                        "at a settled frame — but the ~10 shots that read useCurrentFrame directly still animate, so "
                        "the variant is MOSTLY (not fully) reduced. Spot-check the film if strict reduced-motion is required.")
    if meta.get("sound_design"):
        bgm = meta.get("bgm")
        if out_dir and bgm and bgm != "auto" and not _exists(out_dir, bgm):
            warnings.append(f"remotion: sound_design is on but bgm '{bgm}' does not exist — it will be dropped "
                            f"silently; fix the path or use bgm:'auto'. AUDITION out.mp4 before delivery.")
        else:
            warnings.append("remotion: sound_design is on — the pipeline CANNOT hear the SFX/BGM mix; AUDITION "
                            "out.mp4 before delivery (a wrong or absent bed ships silently).")
    _asp = str(meta.get("aspect") or "16:9")
    # READ, not restated. "keep in sync with Root.tsx ASPECTS" was a comment, and a comment is not a
    # mechanism: this set and the renderer's table could drift in either direction — a ratio the renderer
    # supports refused here, or one it does not silently accepted and rendered 16:9.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import _caption_band as _cb
        _ASPECTS = set(_cb.aspect_table())
    except Exception:
        _ASPECTS = {"16:9", "9:16", "1:1", "4:5", "4:3"}
    if _asp not in _ASPECTS:
        errors.append(f"remotion: meta.aspect='{_asp}' is not supported {sorted(_ASPECTS)} — it would SILENTLY render "
                      f"16:9 (Root.tsx dims() fallback); fix the typo or add the ratio to Root.tsx ASPECTS.")
    elif _asp != "16:9":
        warnings.append(f"remotion: meta.aspect='{_asp}' (non-16:9) — most library shots are 16:9-tuned; still-render "
                        f"EACH chosen shot at this aspect and fix/swap any that don't reflow (multi-column must STACK, "
                        f"wide elements must not run off-frame) — references/remotion-shot-authoring.md §A.9.")
    # THE ENERGY SKELETON. The plan declares an `energy` per beat; the library sweep measures a motion per
    # register; nothing between the planner and the register picker used to read the first against the
    # second. Measured on a delivered film: the plan's climax sat on a register UNDER the delivery motion
    # floor and four HIGH beats on the library's stillest fifth (scripts/energy_skeleton.py has the table).
    # Warnings, not errors — a finding is a candidate, since a beat's real motion also depends on its props,
    # ground, camera and length — and each names in-band, unused alternatives.
    if slides and any(s.get("shot") for s in slides):
        try:
            import energy_skeleton as _es
            _fs, _cv, _why = _es.check_slides(slides, _es.load_plan(out_dir) if out_dir else None)
        except Exception as e:                                       # noqa: BLE001 — never let a diagnostic block
            _es, _fs, _cv, _why = None, [], None, "energy_skeleton failed: %s" % e
        if _why:
            warnings.append("remotion: energy skeleton NOT checked — %s" % _why)
        elif _fs:
            _hard = [f for f in _fs if f["kind"] in _es.HARD]
            for f in _hard[:6] + [f for f in _fs if f["kind"] not in _es.HARD]:
                warnings.append("remotion: energy skeleton — %s" % _es.describe(f))
            if len(_hard) > 6:
                warnings.append("remotion: energy skeleton — %d more beat(s) contradict their declared energy; "
                                "run python3 scripts/energy_skeleton.py <out_dir> for the full curve" % (len(_hard) - 6))


def evaluate(data, out_dir, pre_tts=False, vertical=False):
    """Pure check: returns {ok, errors, warnings, scenes, ...}. No render, no network.
    `vertical` mirrors render.py's --vertical flag; meta.aspect=="9:16" also forces it, so the
    caption-fit checks run on the SAME canvas render.py will use."""
    errors, warnings = [], []

    # 1. Structural contract (the same gate render.py runs, surfaced early with its message).
    #    Catch the broad failures too: a non-dict `meta`/`slides` makes sb.validate raise
    #    TypeError/AttributeError/KeyError rather than StoryboardError — a gate must report
    #    those cleanly, never crash with a traceback.
    if not isinstance(data, dict):
        return {"ok": False, "errors": ["storyboard.json is not a JSON object"], "warnings": warnings, "scenes": 0}
    try:
        sb.validate(data)
    except (sb.StoryboardError, TypeError, AttributeError, KeyError) as e:
        errors.append(f"structure: {e}")
        return {"ok": False, "errors": errors, "warnings": warnings, "scenes": 0}

    meta = data["meta"]
    slides = data["slides"]
    # MIXED-VOICE (both tiers): tts.py records `meta._tts_mixed_voice` when a cloud/edge engine fell back to `say`
    # on SOME scenes — a systemic failure that split the deck between two voices. It was written and read by
    # nothing; surface it so a half-say/half-cloud deck can't ship silently (SKILL.md's ⚠️ MIXED-VOICE guidance).
    _mv = meta.get("_tts_mixed_voice")
    if _mv:
        _n = len(_mv) if isinstance(_mv, (list, dict)) else _mv
        warnings.append(f"MIXED-VOICE run: {_n} scene(s) fell back to a different TTS engine (meta._tts_mixed_voice) — "
                        f"the deck is split between two voices; fix the engine and re-run tts.py, or set meta.voice to "
                        f"one engine (edge:*/say:*) so every scene matches. Do NOT ship a two-voice deck.")
    # REMOTION2 bespoke-shot tier — its own scene contract (shot id + props + family variety); the legacy
    # cinematic/HTML checks below don't apply to it, so guard and skip them.
    if (meta.get("renderer") or "") == "remotion":
        _check_remotion(meta, slides, errors, warnings, out_dir)
        _shot_truncation(meta, slides, errors, warnings)
        _form_vocabulary(meta, slides, errors, warnings)
        _idiom_world(meta, slides, errors, warnings)
        _beat_grounds(slides, errors, warnings)
        _film_language(meta, slides, errors, warnings)
        _image_attribution(slides, out_dir, errors, warnings)
        _caption_legibility(meta, slides, errors, warnings, out_dir)
        _figure_traceability(slides, out_dir, warnings)   # %/×/$ figures in shot_props text must trace to brief.json
        return {"ok": not errors, "errors": errors, "warnings": warnings, "scenes": len(slides)}
    # visual_style is the declared single source of truth — a typo/hallucinated key degrades silently to the
    # default look, so cross-check it against the catalog (theme.STYLE_PRESETS) independent of the plan file.
    _vs = str(meta.get("visual_style") or "").strip()   # str() guards a hand-edited non-string value (.strip crash)
    if _vs and _vs.lower() != "custom":
        try:
            import theme as _theme
            if not _theme._style_key(_vs):
                warnings.append(f"meta.visual_style '{_vs}' is not a known style — use a references/visual-styles.md key "
                                f"({', '.join(sorted(_theme.STYLE_PRESETS))}) or \"custom\"; an unknown key degrades to the flat default")
        except Exception:
            pass
    # CJK x style-register feasibility: the comic/mono display faces are Latin-only, so a zh/ja/ko deck
    # picking them renders headlines in plain system CJK sans — the style register silently vanishes.
    _lang2 = str(meta.get("language") or "").lower()[:2]
    if _vs and _lang2 in ("zh", "ja", "ko"):
        try:
            import theme as _theme2
            _kind = _theme2._STYLE_FONT_KIND.get(_theme2._style_key(_vs) or "", "")
            if _kind == "mono":
                warnings.append(f"meta.visual_style '{_vs}' uses a mono display face with NO CJK glyphs — "
                                "a CJK deck renders its headlines in plain system sans (the style register "
                                "won't read); pick a sans/serif style or accept the plain-type look knowingly")
            elif _kind == "comic":
                warnings.append(f"meta.visual_style '{_vs}': the comic face has no CJK glyphs — zh/ja/ko "
                                "headlines fall back to a HANDWRITING face on macOS (Hannotate/HanziPen, a "
                                "reasonable comic read) and plain sans elsewhere; check the sample")
        except Exception:
            pass
    # audacity dial — the register's RISK budget (a typo silently loses the intent). Never touches the floor.
    _aud = str(meta.get("audacity") or "").strip().lower()
    if _aud and _aud not in ("conservative", "balanced", "bold", "experimental"):
        warnings.append(f"meta.audacity '{meta.get('audacity')}' is not a known level — use "
                        "conservative | balanced (default) | bold | experimental; it scales how far the design_register pushes")
    # DIEGETIC BRIDGE — only 'type-enter' renders today (others are designed, not built). A documented-but-
    # unrendered gesture (or a typo) SILENTLY no-ops and swallows every bridge_label, so warn pre-render;
    # and a long bridge_label overflows the command bar, so cap it. (Audit P0/P2; mirrors render_remotion.)
    _br = str(meta.get("bridge") or "").strip().lower()
    if _br and _br not in ("none", "auto", "type-enter"):
        warnings.append(f"meta.bridge '{meta.get('bridge')}' is not a rendered gesture — only 'type-enter' "
                        "(and 'auto') render today; the seams will fall back to a plain cut (references/camera-and-bridges.md lists the designed menu)")
    if _br and _br not in ("none", ""):
        for s in data.get("slides", []):
            _lbl = str(s.get("bridge_label") or "")
            if len(_lbl) > 28:
                warnings.append(f"scene {s.get('index')}: bridge_label {_lbl!r} is ~{len(_lbl)} chars — keep a "
                                "diegetic command ≤~28 chars so it reads at the held framing and doesn't run off the bar")
    vertical = vertical or meta.get("aspect") == "9:16"
    W, H = rd._canvas(meta, vertical)
    voice = (meta.get("voice") or "auto")
    wants_edge = voice == "auto" or voice.startswith("edge")

    # 2. Duplicate indices break the per-clip cache + audio/words.json filenames.
    seen = {}
    for s in slides:
        i = s.get("index")
        if i in seen:
            errors.append(f"duplicate scene index {i}")
        seen[i] = True

    # 3. Global font + language sanity (once).
    if not os.path.exists(rd.BUNDLED_FONT):
        warnings.append(f"bundled caption font missing ({rd.BUNDLED_FONT}); render falls back to a default face")
    if not _cjk_font_ok(meta):
        warnings.append(f"language '{meta.get('language')}' is CJK but no system font covers it — captions will tofu; set meta.font")
    if wants_edge and not _edge_tts_available() and not pre_tts:
        warnings.append("meta.voice wants edge-tts but it isn't importable — tts.py falls back to 'say' (different voice/quality)")

    prev_types = []
    families = []                         # per-html-scene layout family, for the diversity gate
    comps = []                            # per-html-scene composition signature, for the composition gate
    ai_look = meta.get("image_source") == "openai"
    soft = list(meta.get("soft_textures") or [])
    for s in slides:
        i = s.get("index")
        t = s.get("type", "slide")
        tag = f"scene {i}"

        _cinematic_fields(s, data.get("meta") or {}, out_dir, tag, errors, warnings)

        # SHARED-ELEMENT match-cut spec (P3+): validate the anchor early (render's _clean_match is fail-loud,
        # but a ~1s catch is friendlier). from/to are [cx,cy,w,h] FRAME FRACTIONS (0..1); it needs a NEXT scene.
        mc = s.get("match_cut")
        if mc is not None:
            if not isinstance(mc, dict):
                errors.append(f"{tag}: match_cut must be an object")
            else:
                if str(mc.get("shape", "box")) not in ("box", "bar", "line", "dot"):
                    errors.append(f"{tag}: match_cut.shape {mc.get('shape')!r} must be box|bar|line|dot")
                for key in ("from", "to"):
                    v = mc.get(key)
                    if not (isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v)):
                        errors.append(f"{tag}: match_cut.{key} must be [cx,cy,w,h] frame fractions (0..1)")
                    elif any(not (-0.2 <= float(x) <= 1.2) for x in v):
                        warnings.append(f"{tag}: match_cut.{key} {v} looks like PIXELS — coords are FRAME "
                                        f"FRACTIONS (0..1); the anchor will sit off-frame")
                if slides and s is slides[-1]:
                    warnings.append(f"{tag}: match_cut is on the LAST scene — no next scene to match into, so it "
                                    f"never renders; put it on the scene that transitions INTO the shared element")

        # PATH-A deprecation (the cinematic tier is a DISTINCT native-3D style — not the HTML tier with a
        # camera bolted on). A hand-authored `html:"pages/..."` on a stage `card`/plane is SCREENSHOTTED onto
        # a plane the camera flies past = "build a 2D slide, then simulate 3D" — the thing the tier AVOIDS.
        # WARN so it stays a rare escape hatch: carry content with NATIVE forms (display/text/metaphor/bars/
        # device/glyphrain/…), or if the deck is really designed 2D slides, make it an HTML-tier deck (omit
        # meta.renderer:"remotion"). Targets an authored `html:` field. A template's generated `colorWorld`
        # backplane ALSO becomes an html card — but only at RENDER time (`_generate_color_worlds` injects
        # `html` into the props JSON), AFTER validate has read the authored storyboard.json where the card
        # still carries only `colorWorld`. So this pre-render gate never sees (never warns on) a colorWorld
        # backplane — do NOT move colour-world generation before validate, or this lint would false-fire on
        # the SUPPORTED template path.
        _st = s.get("stage") or (s.get("props") or {}).get("stage")
        _els = _st.get("elements") if isinstance(_st, dict) else []
        _patha = sum(1 for e in (_els or []) if isinstance(e, dict) and (e.get("html") or "").strip())
        _patha += sum(1 for p in (s.get("planes") or (s.get("props") or {}).get("planes") or [])
                      if isinstance(p, dict) and (p.get("html") or "").strip())
        if _patha:
            warnings.append(f"{tag}: uses {_patha} Path-A HTML-screenshot plane(s) (a 2D slide flown past the "
                            f"camera) — deprecated as the cinematic default; carry the content with NATIVE 3D "
                            f"forms (display/text/metaphor/bars/device/glyphrain/…), or if this is really a "
                            f"designed 2D-slide deck, drop meta.renderer:'remotion' and use the HTML tier")

        # --- referenced media exists on disk -------------------------------------------
        if t == "slide":
            if (s.get("image_prompt") or "").strip() and not s.get("image"):
                errors.append(f"{tag}: image_prompt set but no generated image — run imagegen.py first")
            elif s.get("image") and not _exists(out_dir, s["image"]):
                errors.append(f"{tag}: image '{s['image']}' not found under {out_dir}")
        elif t == "html":
            page = (s.get("props") or {}).get("html")
            if not _exists(out_dir, page):
                errors.append(f"{tag}: html page '{page}' not found under {out_dir}")
            else:
                _check_html_assets(out_dir, page, wants_edge, i, errors, warnings,
                                   (s.get("props") or {}).get("anim_seconds"), s.get("duration"),
                                   s.get("narration"), families,
                                   captions_on=bool((data.get("meta") or {}).get("captions", True)),
                                   ai_look=ai_look, soft_textures=soft, comps=comps, vertical=vertical)
        elif t in ("keypoints", "timeline", "chart", "compare", "title"):
            # Readability floor for the PROGRAMMATIC tier — keyframe_qa only overflow-checks html pages,
            # so nothing else guards these. The renderers now wrap/shrink-to-fit, but past a sane item
            # count the type drops below the squint test on a moving frame. Deterministic, warning-only.
            props = s.get("props") or {}
            # keypoints is already hard-capped 1-5 by the storyboard contract; guard the UNCAPPED types.
            _budget = {"timeline": ("events", 7), "chart": ("data", 8), "compare": ("parts", 6)}
            if t in _budget:
                key, ceil = _budget[t]
                nitems = len(props.get(key) or [])
                if nitems > ceil:
                    warnings.append(f"{tag}: {t} has {nitems} {key} (> {ceil}) — too many to read on a moving frame; "
                                    f"split the beat or promote the few that matter (the renderer shrinks to fit, but "
                                    f"past ~{ceil} the type drops below the squint test)")
            if t == "title" and rd._wlen(str(props.get("title") or "")) > 90:
                warnings.append(f"{tag}: title weighs {rd._wlen(str(props.get('title'))):.0f} width-units — a title should land in a "
                                f"glance; tighten it or move the detail to the subtitle (it now wraps, but a paragraph "
                                f"title isn't a title)")

        # --- audio / duration (skipped in --pre-tts mode) ------------------------------
        if not pre_tts:
            if not s.get("audio") or not s.get("duration"):
                errors.append(f"{tag}: no audio/duration — run tts.py before render")
            elif not _exists(out_dir, s["audio"]):
                errors.append(f"{tag}: audio '{s['audio']}' not found under {out_dir}")
            elif s["duration"] > PACE_CEILING_S:
                warnings.append(f"{tag}: holds {s['duration']:.1f}s (> {PACE_CEILING_S:.0f}s) — splitting into shorter beats reads less sluggish")

        # --- caption craft (no wall of text, no widow, readable on screen) -------------
        if meta.get("captions", True):
            caps = s.get("captions") or []
            texts = ([c.get("text", "") for c in caps] if len(caps) >= 2
                     else rd._split_caption_chunks(s.get("narration") or "", hard_wrap=False))
            for txt in texts:
                ct = (txt or "").strip()                  # NOT `t` — that is the scene type above
                lines = _caption_lines(ct, meta, W, H)
                if len(lines) > MAX_CAPTION_LINES:
                    warnings.append(f"{tag}: caption wraps to {len(lines)} lines (> {MAX_CAPTION_LINES}) — \"{ct[:40]}…\"; shorten or split")
                # density ceiling — catches a 2-line-but-packed cue the line count misses (e.g. a
                # CJK clause authored with ASCII commas that the segmenter couldn't break)
                # weighted density (render._wlen: CJK ~2.5, Latin 1) — the binary CJK/Latin flip
                # disagreed with the renderer's own budget on MIXED-script captions in both directions
                if rd._wlen(ct) > 84:
                    warnings.append(f"{tag}: caption weighs {rd._wlen(ct):.0f} width-units (> 84) — a wall of text on screen; split it on a comma/clause — \"{ct[:40]}…\"")
                if ct and ct[-1] in TRAIL_CLAUSE_MARKS:
                    warnings.append(f"{tag}: caption ends on a dangling \"{ct[-1]}\" — trim the trailing clause mark or merge with the next chunk")
                widow = _dangling_word(lines)
                if widow:
                    warnings.append(f"{tag}: caption ends on a lone word \"{widow}\" — rephrase so the last line isn't a widow")
            # minimum on-screen time (needs the timed segments, so only after tts)
            if not pre_tts and s.get("duration"):
                shown_floor = shown_cps = shown_ceil = False
                for seg in rd._captions_for(s):
                    ct2 = (seg.get("text") or "").strip()
                    if not ct2:
                        continue
                    dwell = seg["end"] - seg["start"]
                    if not shown_floor and dwell < MIN_CAPTION_SECONDS:
                        warnings.append(f"{tag}: a caption shows for {dwell:.2f}s (< {MIN_CAPTION_SECONDS}s, the published "
                                        f"absolute floor) — too fast to read; merge chunks or lengthen the line")
                        shown_floor = True
                    # READING SPEED, per script. A CJK line needs more than twice the seconds-per-character
                    # of a Latin one; the old width-only "wall of text" check could not see this at all.
                    cjk = sum(1 for c in ct2 if '\u3040' <= c <= '\u9fff' or '\uac00' <= c <= '\ud7af')
                    cps = CPS_CJK if cjk * 2 >= len(ct2) else CPS_LATIN
                    need = len(ct2) / cps
                    if not shown_cps and dwell + 1e-6 < need:
                        warnings.append(f"{tag}: a caption of {len(ct2)} chars shows for {dwell:.2f}s but needs "
                                        f"{need:.2f}s at {cps:.0f} chars/sec ({'CJK' if cps == CPS_CJK else 'Latin'}) — "
                                        f"shorten the line or slow meta.tts_speed")
                        shown_cps = True
                    if not shown_ceil and dwell > MAX_CAPTION_SECONDS:
                        warnings.append(f"{tag}: a caption holds {dwell:.1f}s (> {MAX_CAPTION_SECONDS:.0f}s) — split it; "
                                        f"a line held that long reads as stuck")
                        shown_ceil = True
                    if cps == CPS_CJK:
                        for ln in _caption_lines(ct2, meta, W, H):
                            if len(ln.strip()) > CJK_CHARS_PER_LINE:
                                warnings.append(f"{tag}: CJK caption line is {len(ln.strip())} chars "
                                                f"(> {CJK_CHARS_PER_LINE}) — \"{ln.strip()[:20]}…\"")
                                break
                    if shown_floor and shown_cps and shown_ceil:
                        break

        # --- narration AI-tells (humanizer-informed): reads as machine-generated even if grammatical ---
        seen_tells = set()
        for phrase, label in _narration_ai_tells(s.get("narration")):
            key = phrase.lower()
            if key in seen_tells:
                continue
            seen_tells.add(key)
            warnings.append(f"{tag}: narration AI-tell — \"{phrase}\" ({label}); say it the way a "
                            f"person would (references/narration-writing.md)")

        # --- motion sanity --------------------------------------------------------------
        m = s.get("motion") or {}
        reduced = bool((data.get("meta") or {}).get("reduced_motion"))
        try:
            dz = abs(m["to"][2] - m["from"][2])
            # under reduced motion the renderer forces to==from, so zoom warnings don't apply
            if dz > MAX_ZOOM_DELTA and not reduced:
                warnings.append(f"{tag}: zoom delta {dz:.2f} > {MAX_ZOOM_DELTA} — the zoom will lurch")
            if m["to"][2] > 1.25 and not reduced:
                warnings.append(f"{tag}: zoom ends at {m['to'][2]:.2f}× (> 1.25) — fine text softens at zoompan's scale limit")
            # motivated motion: a callout should be framed by where the camera settles — flag
            # whenever motion.to is far from the callout center (a static centered hold OR a
            # pan aimed somewhere else both leave the highlight unframed).
            co = s.get("callouts") or []
            if co and len(co[0].get("box", [])) == 4:
                bx = co[0]["box"]
                cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
                tx, ty = m["to"][0], m["to"][1]
                if abs(tx - cx) + abs(ty - cy) > MOTION_ALIGN_TOL:
                    warnings.append(f"{tag}: callout sits at ({cx:.2f},{cy:.2f}) but the camera settles at ({tx:.2f},{ty:.2f}) — move motion.to toward the callout so the push frames it (see references/motion-grammar.md)")
            # C3 — a TIMED callout (`cue`) must anchor to a phrase the narration actually says, and
            # shouldn't land so late there's no time to see it. `at` is an explicit fraction, no check.
            N = (s.get("narration") or "")
            for c in co:
                cue = c.get("cue")
                if not cue:
                    continue
                pos = _cues._anchor_pos(N, cue)
                if pos is None or pos < 0:      # cues._anchor_pos returns -1 for not-found
                    warnings.append(f'{tag}: callout cue "{cue}" is not in the narration — it can\'t be timed to the voice; use a spoken phrase or set an explicit `at` fraction')
                elif N and pos / max(1, len(N)) > 0.85:
                    warnings.append(f'{tag}: callout cue "{cue}" is spoken at ~{100*pos/len(N):.0f}% of the line — it appears too late to help; move the phrase earlier or set `at`')
        except (KeyError, IndexError, TypeError):
            pass

        # --- transition sanity (per-scene overrides; see motion-grammar "Transition rhythm") ----
        _raw_tr = s.get("transition")
        _flat_tr, _tr_sec = sb.normalize_transition(s)   # tolerate a legacy {in,out,seconds} object
        if _raw_tr is not None and _flat_tr is None:
            warnings.append(f"{tag}: unknown transition '{_raw_tr}' — use 'dip'/'in'/'out'/'none' (falls back to the meta default)")
        _ts = s.get("transition_style") or meta.get("transition_style")
        if _ts and _ts not in ("dip", "fadethrough", "drift", "push", "lift", "wipe", "blur"):
            warnings.append(f"{tag}: unknown transition_style '{_ts}' — use dip / fadethrough / drift / "
                            f"push / lift / wipe / blur (see motion-grammar 'Transition STYLE'); falls back to dip")
        elif _ts == "blur" and meta.get("renderer") == "remotion":
            # blur is a KNOWN seam key but the Remotion tier has no rack-defocus presentation yet — it renders
            # as a cross-dissolve (Video.tsx presentationFor default). Surface the approximation so a template
            # that leans on a "blur coda" doesn't silently ship a plain fade (legacy cinematic tier, removed).
            warnings.append(f"{tag}: transition_style 'blur' renders as a cross-dissolve on the Remotion tier "
                            f"(real rack-defocus is roadmap) — author a rack via a scene DoF beat if you need it")
        _tsec = s.get("transition_seconds")
        if isinstance(_tsec, (int, float)) and _tsec > 0.5:
            warnings.append(f"{tag}: transition_seconds {_tsec} > 0.5 — a seam past ~0.45s reads as a stall "
                            f"(norms: seam ≤0.35, payoff 0.3, closer ≤0.45)")
        ts = _tr_sec
        if ts is not None:
            try:
                if float(ts) > 0.5:
                    warnings.append(f"{tag}: transition_seconds {float(ts):.2f} > 0.5 — a long dip reads as sluggish; keep seams ≤0.35, closer ≤0.45")
            except (TypeError, ValueError):
                warnings.append(f"{tag}: transition_seconds '{ts}' is not a number")

        # --- content sanity -------------------------------------------------------------
        if not (s.get("narration") or "").strip():
            warnings.append(f"{tag}: empty narration — the scene plays silent")

        prev_types.append(t)

    # Anti-slop R8: no more than 2 consecutive scenes with the same visual type. SKIP the html
    # tier — every html scene's `type` is "html" regardless of its page layout, so the variety
    # the rule cares about (the on-page design) isn't visible from the storyboard; flagging it
    # would fire on every (recommended) all-html "designed deck". SKIP cinematic likewise — every
    # cinematic scene's type is "cinematic"/"cinematic3d" and its variety is the ARCHETYPE spread,
    # enforced by _design_variety_lint (>45% / <3 distinct / back-to-back); a type run-length warn
    # here fires on EVERY cinematic film (incl. the golden fixture) and is unactionable. Programmatic
    # types (title/chart/timeline/…) still checked.
    _variety_exempt = {"html", "cinematic", "cinematic3d"}
    run = 1
    for a, b in zip(prev_types, prev_types[1:]):
        run = run + 1 if a == b else 1
        if run == 3 and b not in _variety_exempt:
            warnings.append(f"3+ consecutive '{b}' scenes — vary the visual type (anti-slop)")

    # Layout-diversity gate (html tier): a deck dominated by one form family reads as auto-generated.
    # Warn (not error) — a genuinely same-shape run is allowed with the design plan's form-ledger reason,
    # which design-critic (D1) judges. Skip small decks where a majority is unavoidable.
    if len(families) >= 4:
        import collections
        fam, n = collections.Counter(families).most_common(1)[0]
        # require the dominant family to be BOTH a majority-ish share AND ≥3 scenes, so a tiny deck
        # (e.g. 2 of 4 the same) isn't falsely flagged as monotonous.
        if n >= 3 and n / len(families) > LAYOUT_FAMILY_MAX_SHARE:
            warnings.append(f"layout diversity: {n}/{len(families)} html scenes use the same form family "
                            f"('{fam}', {round(100*n/len(families))}%) — one form top-to-bottom reads as "
                            f"auto-generated; vary per content (form-selection in references/html-pages.md)")

    # Composition-diversity + background-flatness gate (html tier): distinct FORM families can STILL
    # all reduce to "top kicker over a vertically-centered stack on a flat ground" — the templated look.
    # Guard the composition ENVELOPE (vertical anchor × balance) and background variety, parallel to the
    # form-family gate. Warning-only (design-critic D6b judges intent); skip small decks (<4 html scenes).
    if len(comps) >= 4:
        n = len(comps)
        # Only pages whose layout this gate can actually READ may vote on anchor/balance. An
        # absolute-positioned deck is invisible to a flex/class signature, so counting its default
        # "center"/"centered" would manufacture a false verdict (see _composition_sig).
        meas = [c for c in comps if c.get("measurable", True)]
        if len(meas) < max(4, 0.5 * n):
            warnings.append(f"composition diversity: NOT statically measurable — {n - len(meas)}/{n} html pages lay "
                            f"themselves out with absolutely-positioned children, which carry no flex/class "
                            f"composition signature. This gate is abstaining rather than reporting a false 0%; read "
                            f"keyframe_qa's DOM-measured content band/centroid for these pages instead")
        else:
            m = len(meas)
            # a split/asym/offset page is left/right-weighted, not a center stack — don't count it toward center-anchor share
            center_share = sum(1 for c in meas if c["anchor"] == "center" and c["balance"] not in ("split", "asym", "offset")) / m
            offcenter = sum(1 for c in meas if c["balance"] in ("split", "asym", "offset") or c["anchor"] != "center") / m
            if center_share > 0.6:
                warnings.append(f"composition diversity: {round(100*center_share)}% of html pages are vertically "
                                f"CENTER-anchored — vary the vertical anchor (top/bottom/full-bleed), don't stack every beat mid-frame")
            if offcenter < 0.25:
                warnings.append(f"composition diversity: only {round(100*offcenter)}% of pages break the centered column — "
                                f"≥~1/3 should be off-center (.frame-left/.frame-right/.thirds/grid-asym/.split/top-anchored)")
        if all(c["kicker_first"] for c in comps):
            warnings.append("composition diversity: EVERY html page opens with a top .kicker hat — let ≥1 hero lead "
                            "with its number/image (no kicker) so the deck isn't one template")
        non_hero = [c for c in comps if not c["hero"]]
        if non_hero:
            nflat = sum(1 for c in non_hero if c["flat"])
            if nflat / len(non_hero) > 0.6:
                warnings.append(f"background flatness: {nflat}/{len(non_hero)} content pages have NO backdrop (bare "
                                f"--bg) — rotate ≥2 backdrops or alternate plain/tinted/soft/accent-fill; in the FREE/flat tier "
                                f"a faint on-topic .bg-motif (an SVG diagram derived from THIS deck's motif — a ghosted "
                                f"network/segbar/whisper of the beat's own chart) or a .bg-grid makes a page read not-flat AND on-topic")

    # Transition seam-pairing (motion-grammar "Transition rhythm"): a dip only reads as a dip when
    # BOTH sides of the cut fade — an in-edge without the predecessor's out-edge is a smash-to-bg
    # entrance; an out-edge into a hard-opening scene is a fade-down-then-pop. Both read as glitches.
    meta_t = (data.get("meta") or {}).get("transition", "dip")
    def _eff(s):
        t, _ = sb.normalize_transition(s)
        return t if t in ("dip", "in", "out", "none") else meta_t
    effs = [_eff(s) for s in slides]
    for k in range(1, len(effs)):
        a, b = effs[k - 1], effs[k]
        ta, tb = slides[k - 1].get("index", k), slides[k].get("index", k + 1)
        if b in ("in", "dip") and a not in ("out", "dip"):
            warnings.append(f"scene {tb} fades in from bg but scene {ta} ends hard — the seam reads as a "
                            f"smash-cut-to-blank; give scene {ta} transition 'out' (or 'dip')")
        elif a in ("out", "dip") and b not in ("in", "dip"):
            warnings.append(f"scene {ta} fades out to bg but scene {tb} opens hard — fade-down-then-pop; "
                            f"give scene {tb} transition 'in' (or make scene {ta} 'none'/'in')")
    if effs and meta_t != "none" and effs[-1] not in ("out", "dip"):
        warnings.append(f"final scene's transition '{effs[-1]}' has no out edge — the video ends on a hard "
                        f"frame; the closer should be 'dip' (its out edge IS the end fade)")

    # UNIFORM-SEAM smell: when NO scene sets its own transition, every cut falls through to the meta
    # default — so all N seams look identical. A viewer reads that as "the transition is always the
    # same" (they are right). The section rhythm — hard cut inside a section, a dip at 2-3 seams — is
    # exactly what the design-director plans per beat; a deck where none of it reached the storyboard
    # is one that forgot to wire it in. Only fires on a FADING default (a uniform HARD cut is the
    # invisible baseline, not a repeating effect) and on a deck long enough for the repetition to read.
    explicit = sum(1 for s in slides if sb.normalize_transition(s)[0] in ("dip", "in", "out", "none"))
    if explicit == 0 and meta_t != "none" and len(slides) >= 6:
        warnings.append(f"all {len(slides)} scenes use the meta default transition '{meta_t}' and not one "
                        f"sets its own — every cut is the identical seam, which reads as monotonous. "
                        f"Author the rhythm: mark 2-3 section seams (a `dip`) and set the rest to hard "
                        f"cuts (meta.transition:'none', or per-scene 'none'). The design plan's per-beat "
                        f"`transition` is what carries this — make sure it reached the storyboard.")

    # Transition-STYLE discipline (motion-grammar "the style is the deck's LOOK"): ONE style per deck,
    # chosen from the register's motion personality; a per-scene override marks at most one special
    # seam. 3+ distinct styles reads as a template sampler, not a register. And blur is a reflective
    # coda accent — once per deck, never the house style.
    meta_ts = meta.get("transition_style") or "dip"
    eff_ts = [(s.get("index", i + 1), s.get("transition_style") or meta_ts)
              for i, s in enumerate(slides) if _eff(s) != "none"]
    by_style = {}
    for _idx, _st in eff_ts:
        by_style.setdefault(_st, []).append(_idx)
    if len(by_style) > 2:
        pretty = ", ".join(f"{k} (scene {', '.join(map(str, v[:4]))})" for k, v in sorted(by_style.items()))
        warnings.append(f"deck mixes {len(by_style)} transition styles — {pretty}; the style is the "
                        f"deck's LOOK: pick ONE meta.transition_style, per-scene overrides mark at most "
                        f"one special seam (see motion-grammar 'Transition STYLE')")
    if meta_ts == "blur":
        warnings.append("meta.transition_style 'blur' rack-defocuses EVERY seam — blur is a once-per-deck "
                        "coda accent; set the house style to dip/fadethrough/drift/... and give only the "
                        "closer a per-scene transition_style 'blur'")
    elif len(by_style.get("blur", [])) > 1:
        warnings.append(f"blur transition on scenes {', '.join(map(str, by_style['blur']))} — blur reads "
                        f"as a reflective coda; use it at most ONCE (usually the closer)")

    # A cinematic scene (type 'cinematic', or any scene carrying top-level `layers`/`lens`) renders ONLY
    # on the Remotion tier. On the local path render.py does getattr(scenes,'render_cinematic') and
    # crashes with AttributeError — so it MUST declare meta.renderer=='remotion'. Caught here, unconditionally.
    def _cine_content(s):
        # Any cinematic content that the Remotion tier draws WITHOUT an image: a shot-based SET
        # (stage+shots), true-3D planes (P6), or legacy depth layers. Used to exempt these from the
        # "blank scene" trap and to route them to the remotion renderer.
        pr = s.get("props") or {}
        return ((s.get("stage") or pr.get("stage")) and (s.get("shots") or pr.get("shots"))) \
            or (s.get("planes") or pr.get("planes")) or (s.get("layers") or pr.get("layers")) \
            or (s.get("component") or pr.get("component"))   # BESPOKE beat draws its own content (no image needed)
    _design_variety_lint(slides, errors, warnings)

    cine = [s.get("index") for s in slides
            if s.get("type") in ("cinematic", "cinematic3d") or s.get("lens")
            or (s.get("props") or {}).get("lens") or _cine_content(s)]
    if cine and meta.get("renderer") != "remotion":
        errors.append("scene(s) %s use the cinematic tier (type 'cinematic' / `layers` / `lens`) but "
                      "meta.renderer is '%s' — set meta.renderer:'remotion' (the local renderer has no "
                      "cinematic path and would crash at render)"
                      % (", ".join("#%s" % i for i in cine), meta.get("renderer") or "local"))

    # Remotion cinematic tier renders IMAGE scenes only — a non-image scene would render BLANK and still
    # pass the A/V gate (a blank video's audio is in sync). Fail at THIS gate too, not just at render.
    if meta.get("renderer") == "remotion":
        blank = [(s.get("index"), s.get("type", "slide")) for s in slides
                 if not (s.get("image") or (s.get("props") or {}).get("image"))
                 and not _cine_content(s)   # stage+shots / planes / layers all render content without an image
                 and s.get("type", "slide") not in ("slide", "title")]
        if blank:
            errors.append("renderer=remotion (cinematic tier) renders IMAGE scenes only, but scene(s) "
                          + ", ".join("#%s(%s)" % (i, t) for i, t in blank)
                          + " carry non-image content (html/chart/…) that would render BLANK — use "
                            "renderer=local for an html/designed deck, or give them an `image`")

        # PARITY: the Remotion tier silently DROPS several local-tier looks. Warn so an authored look
        # isn't discarded without notice (parity with the brand-bug lint below).
        if meta.get("caption_mode") == "band":
            warnings.append("renderer=remotion ignores meta.caption_mode:'band' — captions render as a "
                            "bottom overlay (no dedicated strip); keep content clear of the lower ~15%")
        _ts = meta.get("transition_style")
        if _ts == "blur":
            warnings.append("renderer=remotion: transition_style:'blur' (rack-defocus) is not yet a Remotion "
                            "presentation — it renders as a cross-dissolve (fade). Use dip/push/lift/wipe for "
                            "an exact seam, or the blur coda on the local tier.")
        if meta.get("captions_karaoke") not in (None, "off", False):
            warnings.append("renderer=remotion has no karaoke caption highlight — captions render plain; "
                            "meta.captions_karaoke is ignored on this tier")
        _co = [s.get("index") for s in slides
               if (s.get("type") == "cinematic" or s.get("layers")) and s.get("callouts")]
        if _co:
            warnings.append("scene(s) %s carry `callouts` but the cinematic path does not render them — "
                            "put the highlight IN a layer, or move it to an image scene"
                            % ", ".join("#%s" % i for i in _co))
        # cinematic layers are authored in absolute px tuned for a 1920-wide landscape canvas; on a
        # 1080-wide 9:16 frame a full-width panel overflows and NO gate re-checks the pixels.
        if (vertical or meta.get("aspect") == "9:16") and any(
                s.get("type") in ("cinematic", "cinematic3d") or s.get("layers") for s in slides):
            warnings.append("cinematic scenes are landscape-tuned (stage/plane sizes + camera framing assume "
                            "1920-wide) — on a 9:16 frame panels/hero/display/3D planes can crop; verify the "
                            "render, or keep cinematic scenes to 16:9")
        # CJK on the cinematic tier is a PORTABILITY trap: the 4 bundled display faces are Latin-only, so 3D
        # text/label planes route to a HOST system CJK font (present on macOS, absent on a bare headless
        # Linux/Lambda box — the --gl=swangle target), and DOM stage text (panel/display/metaphor) resolves
        # only through the CSS system-font chain. A clean mac preview can ship boxes on CI. Warn loud here
        # (~1s) so it isn't discovered after a multi-minute render — the HTML tier has the real CJK fallbacks.
        if str(meta.get("language") or "").lower()[:2] in ("zh", "ja", "ko") and any(
                s.get("type") in ("cinematic", "cinematic3d") for s in slides):
            warnings.append("CJK deck on the cinematic tier: the bundled display faces are Latin-only, so 3D "
                            "text/label planes and DOM stage text depend on a HOST CJK font — a macOS preview "
                            "renders but a headless Linux/Lambda target can tofu. Use the HTML tier for a CJK "
                            "deck, or ensure the render host has a CJK font (Noto Sans CJK) installed")
        # CINEMATIC TEMPLATE (the whole-film LOOK): a cinematic film should DECLARE meta.cinematic_template — a
        # key from (the removed legacy cinematic tier) — so the design-director instantiates a bold, coherent,
        # GENERALISABLE look (accent -> per-beat colour worlds via cine_palette) instead of an ad-hoc concept.
        # Absent -> warn (nudge the director to run the template contest); set-but-unknown -> error.
        if cine:
            _tpl = meta.get("cinematic_template")
            # (legacy generic-scene tier, retained inert — the live Remotion tier is remotion/shot-director)
            _known = {"command-surface", "liquid-model", "molten-ledger", "aurora-bloom", "ignition-monument",
                      "doorway-gallery", "rakelight", "exploded-schematic", "defrag"}
            if _tpl is None:
                warnings.append("cinematic film has no `meta.cinematic_template` — pick one from "
                                "(the removed legacy cinematic tier) (design-director runs a template contest) so "
                                "the film gets a bold, coherent, generalisable look, not an ad-hoc concept")
            elif str(_tpl) not in _known:
                errors.append("unknown meta.cinematic_template %r (known: %s)" % (_tpl, sorted(_known)))
            elif not meta.get("accent"):
                # the colour-world generator (render_remotion._generate_color_worlds -> cine_palette) derives
                # every beat's palette from meta.accent; without it, `colorWorld` cards fall back to the theme
                # accent and the template's colour intent is lost.
                warnings.append("meta.cinematic_template %r is set but meta.accent is not — the colour-world "
                                "generator derives every beat's palette from the accent; set meta.accent (the "
                                "brand/topic hue) so the template re-colours to this topic" % _tpl)
            # TEMPLATE CONTEST trace (mirrors register_contest): the STEP-0 contest ("offer 2–4 → USER picks")
            # should leave a record, else a hardcoded single template passes green with no user involvement.
            # meta.template_contest = {candidates:[≥2 template keys], winner, user_pick}.
            if _tpl is not None and str(_tpl) in _known:
                _tc = meta.get("template_contest")
                _aud = str(meta.get("audacity") or "balanced").strip().lower()
                if not (isinstance(_tc, dict) and _tc):
                    # A contest is EXPECTED at every audacity except conservative (which deliberately SKIPS it —
                    # see the contest-width rule: conservative skips · balanced 3 · bold 5 · experimental 7). So a
                    # missing record ERRORs at balanced/bold/experimental (the default is balanced) and is only a
                    # warning at conservative — a hardcoded single template must not pass as "the user picked it".
                    if _aud != "conservative":
                        errors.append("cinematic film at audacity '%s' records no `meta.template_contest` — a "
                                      "single hardcoded template is not a contest; run STEP-0 (offer 2–4, user "
                                      "picks) and record {candidates:[>=2], winner, user_pick}" % _aud)
                    else:
                        warnings.append("cinematic film at audacity 'conservative' records no `meta.template_contest` "
                                        "— conservative may skip the contest, but recording {candidates, winner, "
                                        "user_pick} still documents the STEP-0 choice")
                else:
                    _cand = [str(c) for c in (_tc.get("candidates") or []) if isinstance(c, str)]
                    if len(_cand) < 2:
                        errors.append("meta.template_contest needs >=2 `candidates` — a contest is divergence")
                    _win = _tc.get("winner")
                    if _win is not None and str(_win) != str(_tpl):
                        errors.append("meta.template_contest.winner %r != meta.cinematic_template %r — the winner "
                                      "IS the chosen template" % (_win, _tpl))
                    if _win is not None and _cand and str(_win) not in _cand:
                        errors.append("meta.template_contest.winner %r is not among its candidates %s" % (_win, _cand))
                    # the AIM is ~3 distinct candidates (the user's "give me 3"); >=2 is the hard floor. And the
                    # pick is a HUMAN choice — record user_pick so a self-selection isn't passed off as a contest.
                    if 0 < len(_cand) < 3:
                        warnings.append("meta.template_contest offered only %d candidate(s) — aim for ~3 distinct "
                                        "templates so the user has a real choice (>=2 is the floor)" % len(_cand))
                    if _tc.get("user_pick") is not True:
                        warnings.append("meta.template_contest has no `user_pick:true` — record that the USER "
                                        "chose (a contest is a human pick, not a self-selection)")

            # ATMOSPHERE (the whole-film WORLD substrate — the removed legacy tier): meta.atmosphere binds the
            # render's material CLASS + post profile + style to the picked world (terminal/cartoon/app/…), so
            # the chosen world actually reaches the pixels. Unknown key -> ERROR (it silently no-ops to the
            # default look). The topic-routed contest (the removed atmosphere router) offers the best ~3 to pick from.
            _atmo_key = meta.get("atmosphere")
            if _atmo_key is not None:
                _known_atmo = set()   # (legacy generic-scene tier retired; the world catalogue no longer ships)
                if _known_atmo and str(_atmo_key).lower() not in _known_atmo:
                    errors.append("unknown meta.atmosphere %r (known: %s)" % (_atmo_key, sorted(_known_atmo)))
                # ATMOSPHERE CONTEST trace (mirror template_contest): record which WORLDS were offered so a
                # hardcoded world isn't passed off as a topic-routed pick. Absent -> warn; present -> validate.
                _ac = meta.get("atmosphere_contest")
                if not (isinstance(_ac, dict) and _ac):
                    warnings.append("meta.atmosphere is set but no `meta.atmosphere_contest` — record the STEP-0a "
                                    "contest {candidates:[>=2 keys from the removed atmosphere router], winner, user_pick} so a "
                                    "hardcoded world isn't passed off as a topic-routed pick")
                else:
                    _ac_cand = [str(c).lower() for c in (_ac.get("candidates") or []) if isinstance(c, str)]
                    if len(_ac_cand) < 2:
                        errors.append("meta.atmosphere_contest needs >=2 `candidates` — a contest is a choice")
                    elif len(_ac_cand) < 3:
                        warnings.append("meta.atmosphere_contest offered only 2 worlds — aim for ~3 (the removed atmosphere router "
                                        "returns 3 by default)")
                    _ac_win = _ac.get("winner")
                    if _ac_win is not None and str(_ac_win).lower() != str(_atmo_key).lower():
                        errors.append("meta.atmosphere_contest.winner %r != meta.atmosphere %r — the winner IS the "
                                      "chosen world" % (_ac_win, _atmo_key))
                    if _ac_win is not None and _ac_cand and str(_ac_win).lower() not in _ac_cand:
                        errors.append("meta.atmosphere_contest.winner %r is not among its candidates %s" % (_ac_win, _ac_cand))
                    if _known_atmo:
                        _bad_w = [c for c in _ac_cand if c not in _known_atmo]
                        if _bad_w:
                            errors.append("meta.atmosphere_contest has unknown candidate world(s): %s" % _bad_w)
                    if _ac.get("user_pick") is not True:
                        warnings.append("meta.atmosphere_contest has no `user_pick:true` — record that the USER chose the world")

    # meta.brand (user-supplied REAL assets — the mirror of the "never fabricate logos in generated
    # imagery" doctrine): render.py composites the corner bug from the raster file, and the cover/
    # endcard lockups must already be AUTHORED into the first/last pages — lint both before a full
    # render bakes a missing or broken mark into every frame.
    _brand_lints(meta, slides, out_dir, errors, warnings)

    # Form-fit + creativity presence — mechanical hooks for design-critic D1/D2c, read from the
    # persisted design_plan.json (semantic judgment stays with the critic; these just flag the highest-
    # signal mismatch + a missing creative field). No-op when the plan isn't persisted.
    _design_plan_lints(out_dir, warnings, meta)

    # Truthful-content backstop: flag any statistic spoken/shown that doesn't trace to brief.json evidence.
    _figure_traceability(slides, out_dir, warnings)

    return {"ok": not errors, "errors": errors, "warnings": warnings, "scenes": len(slides)}


_TREND_SHAPE = ("time", "trend", "over-time", "over time", "trajectory", "growth", "declin", "rise",
                "fell", "fall", "change over", "quarter", "year-over", "month")
_SHARE_SHAPE = ("share", "part-of-whole", "part of whole", "proportion", "percent of", "split of",
                "breakdown", "makeup", "composition of")
_CATALOG_FORM = ("grid", "cards", "scorecard", "dash", "keypoints", "blocks")


def _design_plan_lints(out_dir, warnings, meta=None):
    """When design_plan.json is persisted: WARN the two highest-signal content_shape↔form mismatches
    (a temporal shape rendered static; a share atomized into separate numbers) and a missing/decorative
    signature_concept / style_thesis — deterministic hooks feeding design-critic D1 + D2c."""
    path = os.path.join(out_dir, "design_plan.json")
    if not os.path.exists(path):
        return
    try:
        plan = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(plan, dict):          # a hand-edited plan that parses to a list/scalar — nothing to lint
        return
    raw = plan.get("beats") or plan.get("scenes") or []
    # beats may be a dict keyed by id ({"1": {...}}) or a list — normalize to a list of dicts
    beats = ([dict(v, index=k) for k, v in raw.items() if isinstance(v, dict)]
             if isinstance(raw, dict) else [b for b in raw if isinstance(b, dict)])

    def _form(b):
        vis = b.get("visual") or {}
        return str(b.get("form") or vis.get("form") or vis.get("type") or "").lower()

    for b in beats:
        shape = str(b.get("content_shape") or b.get("visual_intent") or "").lower()
        form = _form(b)
        if not shape or not form:
            continue
        temporal = any(k in shape for k in _TREND_SHAPE)
        charty = any(f in form for f in ("chart", "line", "timeline", "flow", "spark",
                                         "slope", "dumbbell", "waterfall", "bump"))
        catalogish = any(f in form for f in ("stat", "keypoint", "card", "scorecard", "tile"))
        if temporal and not charty and catalogish:
            warnings.append(f"form-fit: a beat's content_shape reads temporal/trend ('{shape[:34]}') but its form is "
                            f"'{form}' — a trend rendered static hides the trajectory; use a line/slope/waterfall or timeline (design-critic D1)")
        share = any(k in shape for k in _SHARE_SHAPE)
        sharey = any(f in form for f in ("segbar", "meter", "donut", "stack",
                                         "gauge", "waffle", "isotype", "bullet", "pictograph"))
        atomized = any(f in form for f in ("stat", "card", "tile", "scorecard"))
        if share and not sharey and atomized:
            warnings.append(f"form-fit: a beat's content_shape reads share/part-of-whole ('{shape[:34]}') but its form "
                            f"is '{form}' — separate numbers hide the whole; use .segbar/.meter or a single-proportion "
                            f".gauge/.waffle/.isotype (design-critic D1)")

    if beats and not plan.get("signature_concept"):
        warnings.append("creativity: design_plan has no signature_concept — name ONE inventive beat (an apt + "
                        "unexpected content→visual encoding), not just a varied catalog (design-critic D2c)")
    if beats and not plan.get("style_thesis"):
        warnings.append("creativity: design_plan has no style_thesis — the deck needs a distinctive aesthetic POV "
                        "that fits the subject (design-critic D2c)")
    if beats and not plan.get("visual_style"):
        warnings.append("style: design_plan has no visual_style — pick ONE named style from "
                        "references/visual-styles.md via the selection contest (or \"custom\"); it seeds theme.py "
                        "--style and imagegen's style_preamble so the deck reads as one coherent register (design-critic D2d)")
    sig = plan.get("signature_concept") or {}
    sig_beat = sig.get("beat") if isinstance(sig, dict) else None
    if sig_beat is not None:
        for b in beats:
            if str(b.get("index")) == str(sig_beat) or b.get("beat") == sig_beat:
                if any(f in _form(b) for f in _CATALOG_FORM):
                    warnings.append("creativity: the signature_concept beat's form looks like a catalog grid — a "
                                    "signature must be a bespoke encoding, not a reskinned card grid (design-critic D2c)")
                break

    # WHOLE-VIDEO register (the up-pushing 差异感 axis): a coherent named identity carried across the video,
    # committing MOTION personality — not a per-beat signature bolted onto a generic deck. Structural hooks
    # feeding design-critic D2e; the semantic "is it actually distinct / did the motion vary" is D2e's.
    reg = plan.get("design_register")
    if beats and not (isinstance(reg, dict) and reg):
        warnings.append("register: design_plan has no design_register — commit ONE whole-video expressive identity "
                        "(name + motion_personality + type_attitude + how_distinct + carried_by), not just a per-beat "
                        "signature; a coherent register carried across the video is its 差异感 (design-critic D2e)")
    elif beats:
        if not reg.get("name") or not reg.get("motion_personality"):
            warnings.append("register: design_register needs a NAMED identity AND a motion_personality — commit a "
                            "whole-video motion CHARACTER (not the uniform whisper-zoom), the video's biggest "
                            "distinctiveness lever (design-critic D2e)")
        cb = [str(x) for x in (reg.get("carried_by") or []) if not isinstance(x, (dict, list))]
        if len(cb) < 2:
            warnings.append("register: design_register.carried_by must name ≥2 beats the register spans (incl. the "
                            "opener AND the signature beat) — a register is a SPINE across the video, not a one-off "
                            "flourish (design-critic D2e)")
        elif sig_beat is not None and str(sig_beat) not in cb:
            warnings.append("register: design_register.carried_by omits the signature beat — the register should PEAK "
                            "at the signature, so that beat must be among the beats it spans (design-critic D2e)")

    # REGISTER CONTEST (the generative half): a single-shot register regresses to the safe mean, so at a
    # bold/experimental audacity the plan should record a real divergence+selection contest. Structural
    # hooks only — the judging itself is design-critic's "Register contest — judge mode".
    contest = plan.get("register_contest")
    aud = str((meta or {}).get("audacity") or "balanced").strip().lower()
    if beats and isinstance(reg, dict) and reg:
        if not (isinstance(contest, dict) and contest):
            if aud in ("bold", "experimental"):
                # (The remotion shot-template contest is a hard ERROR; this HTML lint stays a WARN because
                # _design_plan_lints is warnings-only and the design-critic judge-mode is the real contest gate.)
                warnings.append(f"register: audacity '{aud}' but design_plan records no register_contest — a "
                                "single-shot register regresses to the safe mean; run the divergence contest "
                                "(SKILL.md 'Register contest') and record {mode, candidates, winner, user_pick}")
        else:
            raw_c = contest.get("candidates")
            if isinstance(raw_c, dict):    # dict keyed by candidate key — normalize like `beats` above
                raw_c = [dict(v, key=k) for k, v in raw_c.items() if isinstance(v, dict)]
            cands = [c for c in raw_c if isinstance(c, dict)] if isinstance(raw_c, list) else []

            def _ckey(c):
                # NO truthiness fallback: a falsy-but-valid key (0, "") must not fall through to `name`
                k = c.get("key")
                return str(c.get("name") or "") if k is None else str(k)
            keys = [_ckey(c) for c in cands]
            if len(cands) < 2:
                warnings.append("register: register_contest has <2 candidates — a contest needs genuinely "
                                "divergent rivals, else it's a single-shot with extra steps")
            win = contest.get("winner")
            if win is None and cands:
                warnings.append("register: register_contest records candidates but no winner — the contest is "
                                "divergence + SELECTION; record the final pick as `winner` (`user_pick: true` "
                                "when the user made the pick)")
            elif win is not None and keys and str(win) not in keys:
                warnings.append("register: register_contest.winner is not among its candidates — record the FINAL "
                                "selected candidate's key (the user's pick is final when they made one)")
            elif win is not None:
                wname = next((str(c.get("name") or "") for c in cands if _ckey(c) == str(win)), "")
                if wname and str(reg.get("name") or "") and wname != str(reg.get("name")):
                    warnings.append("register: the committed design_register.name differs from the contest winner's "
                                    "name — the full plan must adopt the SELECTED register (or re-record the winner)")


_BRAND_PLACEMENTS = ("cover", "endcard", "bug")


def _brand_lints(meta, slides, out_dir, errors, warnings):
    """meta.brand lints. ERRORS for what render.py cannot do (no logo file, no raster for the bug);
    WARNINGS for what would render wrong (opaque JPEG, an off-contract bug config, a cover/endcard
    placement whose page never references the logo — the lockup planned but not authored). The
    slide-image tier gets no lockup check: master-slide logos arrive baked into the frames."""
    brand = meta.get("brand")
    if brand is None:
        return
    if not isinstance(brand, dict):
        errors.append(f"meta.brand {brand!r} is not an object — declare {{\"logo\": \"assets/brand/logo.png\", ...}}")
        return
    logo = brand.get("logo")
    dark = brand.get("logo_dark")
    if not logo:
        errors.append("meta.brand has no 'logo' — the one REQUIRED brand field; point it at the user's "
                      "real file (assets/brand/logo.png), never a generated one")
    elif not _exists(out_dir, logo):
        errors.append(f"meta.brand.logo '{logo}' not found under {out_dir} — copy the real asset in before render")
    if dark and not _exists(out_dir, dark):
        errors.append(f"meta.brand.logo_dark '{dark}' not found under {out_dir} — copy it in, or drop the key "
                      f"(render falls back to logo)")
    for k, p in (("logo", logo), ("logo_dark", dark)):
        if p and str(p).lower().endswith((".jpg", ".jpeg")):
            warnings.append(f"meta.brand.{k} '{p}' is a JPEG — no alpha channel, so it composites as a "
                            f"white box on any non-white ground; export a transparent png")
    pl = brand.get("placement")
    if pl is None:
        pl = ["cover", "endcard"]                     # the contract default when absent
    if not isinstance(pl, list) or any(v not in _BRAND_PLACEMENTS for v in pl):
        errors.append(f"meta.brand.placement {pl!r} — must be a list drawn from "
                      f"{' / '.join(_BRAND_PLACEMENTS)}; an unknown value would silently place nothing")
        pl = [v for v in pl if v in _BRAND_PLACEMENTS] if isinstance(pl, list) else []
    elif pl == []:
        warnings.append("meta.brand.placement is [] — the brand is declared but would never appear; "
                        "drop meta.brand or list cover/endcard/bug")
    if "bug" in pl:
        # the corner bug is PIL-composited by render.py, so it needs a RASTER — and render picks the
        # variant BY THEME GROUND (logo_dark on dark, logo on light), so EVERY declared variant must
        # be raster: an svg logo + raster logo_dark still fails on a light theme. Svg stays fine for
        # the html lockups.
        for _k, _p in (("logo", logo), ("logo_dark", dark)):
            if _p and str(_p).lower().endswith(".svg"):
                errors.append(f"meta.brand.{_k} '{_p}' is an .svg with 'bug' in placement — the render "
                              f"bug is raster-composited and picks its variant by theme ground; export "
                              f"a png (keep the svg for the html lockups)")
        # (the remotion tier NOW draws the logo as a persistent corner bug — Film.tsx BrandMark; the old
        # "remotion doesn't draw the bug" warning that lived here is removed, and it was dead code anyway since a
        # remotion deck returns from evaluate() before this HTML-path lint.)
        bug = brand.get("bug")
        if bug is not None and not isinstance(bug, dict):
            errors.append(f"meta.brand.bug {bug!r} is not an object — use "
                          f'{{"corner":"tr","opacity":0.5,"height_frac":0.045,"margin_frac":0.02}}')
        if isinstance(bug, dict):
            corner = bug.get("corner")
            if corner is not None and corner not in ("tl", "tr"):
                warnings.append(f"meta.brand.bug.corner '{corner}' — top corners only (the bottom is the "
                                f"caption zone); render clamps it to 'tr'")
            op = bug.get("opacity")
            if sb._is_num(op) and not (0.15 <= float(op) <= 0.9):
                warnings.append(f"meta.brand.bug.opacity {op} outside 0.15..0.9 — below it the mark is lint, "
                                f"above it it shouts over the content; keep ~0.5")
            hf = bug.get("height_frac")
            if sb._is_num(hf) and not (0.02 <= float(hf) <= 0.10):
                warnings.append(f"meta.brand.bug.height_frac {hf} outside 0.02..0.10 — a bug is a watermark, "
                                f"not a lockup; keep ~0.045")
            mf = bug.get("margin_frac")
            if sb._is_num(mf) and not (0.005 <= float(mf) <= 0.08):
                warnings.append(f"meta.brand.bug.margin_frac {mf} outside 0.005..0.08 — past it the 'top "
                                f"corner' mark drifts into the content (or clean off the canvas); keep ~0.02")
        # a banner wordmark drawn at bug height becomes a strip across the top — render clamps it to
        # ~35% of the frame width (aspect kept), so warn the author toward a squarer mark up front
        if logo and _exists(out_dir, logo) and not str(logo).lower().endswith(".svg"):
            try:
                from PIL import Image as _Im
                lw, lh = _Im.open(os.path.join(out_dir, str(logo))).size
                if lh and lw / lh > 8:
                    warnings.append(f"meta.brand.logo is {lw}×{lh} (~{lw / lh:.0f}:1) — at corner-bug height a "
                                    f"banner this wide hits render's ~35%-of-frame-width clamp; a squarer mark "
                                    f"(or a cropped monogram variant) reads better at watermark size")
            except Exception:
                pass
    # cover/endcard lockups are AUTHORED into the first/last html pages (render.py does NOT draw
    # them) — a placement whose page never references the logo filename ships an unbranded frame.
    names = {os.path.basename(str(p)) for p in (logo, dark) if p}
    has_html = any(isinstance(s, dict) and s.get("type") == "html" for s in slides)
    for place, scene in (("cover", slides[0] if slides else None),
                         ("endcard", slides[-1] if slides else None)):
        if place not in pl or not isinstance(scene, dict):
            continue
        if scene.get("type") != "html":
            # only meaningful on a deck that HAS designed pages — a pure slide-image deck can't author
            # a lockup anywhere (its master-slide logo arrives baked into the frames)
            if has_html:
                warnings.append(f"meta.brand: '{place}' in placement but the "
                                f"{'first' if place == 'cover' else 'last'} scene is type "
                                f"'{scene.get('type', 'slide')}' — a lockup can only be AUTHORED into an html "
                                f"page; make that beat an html scene or drop '{place}' from placement")
            continue
        page = (scene.get("props") or {}).get("html")
        if not page or not _exists(out_dir, page):
            continue                                  # a missing page is already an ERROR upstream
        try:
            html = open(os.path.join(out_dir, page), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        html = re.sub(r"<!--.*?-->", "", html, flags=re.S)   # a commented-out lockup is not a lockup
        if names and not any(n in html for n in names):
            warnings.append(f"meta.brand: '{place}' in placement but {page} never references "
                            f"'{sorted(names)[0]}' — the lockup is authored into the page, not drawn by "
                            f"render.py; add the <img> lockup (or drop '{place}' from placement)")


def _layout_family(html):
    """Classify an html page's dominant LAYOUT FAMILY (for the diversity gate). Priority-ordered so a
    specific archetype wins over the generic card/row grid it may also contain. Token-exact on class
    attributes (so 'block' != 'blockquote')."""
    classes = set()
    for m in re.findall(r'class="([^"]*)"', html):
        classes.update(m.split())
    def has(*cs):
        return any(c in classes for c in cs)
    if has("scorecard", "tile"):            return "scorecard"
    if has("flow"):                         return "flow"
    if has("timeline", "tl-node"):          return "timeline"
    if has("quadrant"):                     return "quadrant"
    if has("hubspoke", "hs-hub", "hs-spoke"): return "hubspoke"
    if has("iceberg"):                      return "iceberg"
    # research / technical forms — a distinct silhouette each; classify so the diversity gate doesn't
    # mis-lump an equation / code / results-table page into the generic "title" bucket.
    if has("eqn"):                          return "equation"
    if has("code"):                         return "code"
    if has("rtable"):                       return "table"
    if has("waterfall"):                    return "waterfall"
    if has("gauge", "waffle", "isotype", "bullet"): return "proportion"
    if has("rings", "venn"):                return "nested"
    if has("stepper"):                      return "stepper"
    if has("segbar", "meter"):              return "parts"
    if has("blocks", "block"):              return "blocks"
    if has("pullquote"):                    return "quote"
    if has("defocus"):                      return "compare"
    if has("stat"):                         return "stat"
    if has("card", "row", "dash"):          return "cards"
    return "title"

# High-precision AI-tell phrases in NARRATION (spoken == subtitle). Humanizer-informed
# (github.com/blader/humanizer): these read as machine-written even when grammatical. WARN only
# (a person rewrites them); the marketing-buzzword / filler bans live in narration-writing.md + critic R1a.
_AI_TELLS = [
    (r"\b(?:delve|tapestry|testament|underscor(?:e[sd]?|ing)|showcas(?:e[sd]?|ing)|realm|myriad|intricacies|pivotal)\b", "AI-vocabulary word"),
    (r"\b(?:at its core|the real question is|what really matters|when it comes to|needless to say)\b", "authority/aphorism trope"),
    (r"\b(?:not only|it['’]s not just|it is not just)\b", "negative parallelism"),
    (r"\b(?:let['’]s dive in|let['’]s explore|here['’]s the thing|the thing is)\b", "signposting opener"),
    (r"值得注意的是|值得一提的是|众所周知|综上所述|总而言之|不难看出", "套话 (throat-clearing)"),
    (r"深入探讨|深入了解|彰显|交织|织就", "AI 味词"),
    (r"不仅[^。！？!?]{0,18}(?:而且|还|也)|不仅仅是", "递进对偶 (not-only)"),
    (r"让我们(?:一起)?|在[^，。]{0,12}的今天", "signposting/throat-clearing"),
]
_AI_TELLS = [(re.compile(p, re.IGNORECASE), lbl) for p, lbl in _AI_TELLS]

def _narration_ai_tells(text):
    """Return [(matched_phrase, label)] of AI-tell phrases found in the narration (spoken subtitle)."""
    t = text or ""
    return [(m.group(0), lbl) for pat, lbl in _AI_TELLS for m in pat.finditer(t)]

def _ordered_anchors(html):
    """The page's data-cue anchor phrases, ordered by data-cue-index (attr order-independent)."""
    pts = re.findall(r'data-cue-index="(\d+)"[^>]*?data-cue="([^"]*)"', html)
    pts += [(i, a) for (a, i) in re.findall(r'data-cue="([^"]*)"[^>]*?data-cue-index="(\d+)"', html)]
    seen = {}
    for i, a in pts:
        seen.setdefault(int(i), a)
    return [seen[k] for k in sorted(seen)]

def _css_anim_durations():
    """{class_name: seconds} for every animation class in base.css/motifs.css.

    Delegates to `_common` so validate (does a cued animation FINISH before the scene cuts?) and
    scenes (how wide must the capture window be so it doesn't freeze mid-flight?) read ONE table.
    These two must agree on the same numbers or one gate passes exactly what the other renders
    wrong — which is why this is not a second copy of the parser."""
    return _common.css_anim_durations()


# seek.js drives these off scene PROGRESS (0->1 across the whole scene), not the reveal clock, so
# they can never be truncated by a late cue — mirror that exclusion here.
_AMBIENT_CLASSES = {"bg-live", "bg-drift"}

def _reveal_truncation(html, narration, duration, words_path, tag, errors, warnings):
    """A cue-triggered animation that cannot FINISH before the scene cuts.

    seek.js freezes each cued element at `cue_time`, then runs its animation for the element's own
    animation-duration. If cue + duration exceeds the scene, the render's last frame catches the
    animation mid-flight and hard-cuts — a connector that stops in mid-air, a bar that never reaches
    its value. keyframe_qa cannot see this: with no ?cues= it renders in blind-envelope mode where
    p=1.0 means "every animation has finished" by construction, so only this gate catches it."""
    anchors = _ordered_anchors(html)
    if not anchors or not (sb._is_num(duration) and float(duration) > 0):
        return
    dur = float(duration)
    times = None
    if os.path.exists(words_path):
        try:
            times = _cues.resolve_cues(json.load(open(words_path)), anchors)
        except Exception:
            times = None
    if times is None:
        times = _cues.estimate_cues_from_text(anchors, narration, dur)
    table = _css_anim_durations()
    for el in re.findall(r"<[^>]+>", html):
        mi = re.search(r'data-cue-index="(\d+)"', el)
        if not mi:
            continue
        ci = int(mi.group(1))
        if ci >= len(times) or times[ci] is None:
            continue
        mc = re.search(r'class="([^"]*)"', el)
        classes = set(re.findall(r"[\w-]+", mc.group(1))) if mc else set()
        if classes & _AMBIENT_CLASSES or "data-ambient" in el:
            continue
        mo = re.search(r"animation-duration\s*:\s*([\d.]*)s", el)   # inline override wins
        if mo and mo.group(1) not in ("", "."):
            adur = float(mo.group(1))
        else:
            hits = [table[c] for c in classes if c in table]
            if not hits:
                continue                                            # element carries no animation
            adur = max(hits)
        moff = re.search(r'data-cue-offset\s*=\s*["\']([-\d.]+)["\']', el)   # lead(-)/lag(+) vs the word
        cue = max(0.0, min(dur, float(times[ci]) + (float(moff.group(1)) if moff else 0.0)))
        done = (dur - cue) / adur if adur > 0 else 1.0
        if done >= 1.0:
            continue
        what = f'the "{(anchors[ci] or "")[:18]}" reveal'
        fix = (f"set an inline animation-duration of ~{max(0.2, (dur - cue) - 0.15):.2f}s on it, or "
               f"re-anchor it to an earlier phrase")
        msg = (f"{tag}: {what} starts at {cue:.2f}s and needs {adur:.2f}s, but the scene ends at "
               f"{dur:.2f}s — it is only ~{done*100:.0f}% complete when the render cuts; {fix}")
        (errors if done < TRUNCATION_ERROR_FRAC else warnings).append(msg)

def _reveal_alignment(html, narration, duration, anim_seconds, words_path, tag, warnings):
    """Flag points whose on-screen reveal leads/lags the voice. WHEN a point is SPOKEN is estimated
    from its data-cue anchor's position in the narration text; WHEN it is SHOWN comes from the reveal
    mechanism — the resolved word-cue time if edge `words.json` exists, else the paced even-stagger.
    A large, sustained gap is the "audio before/after the content block" defect."""
    anchors = _ordered_anchors(html)
    N = narration or ""
    L = len(N)
    if len(anchors) < 2 or not N.strip():
        return
    # spoken fraction per anchor — case-insensitive, whole-word (Latin) / substring (CJK) monotonic
    # scan via the SAME matcher render uses (cues._anchor_pos), so "spoken" can't skew vs "shown".
    spoken, cur = [], 0
    for a in anchors:
        a = (a or "").strip()
        pos = _cues._anchor_pos(N, a, cur)
        if pos < 0:
            anywhere = _cues._anchor_pos(N, a)
            if anywhere < 0:
                warnings.append(f"{tag}: data-cue anchor \"{a[:20]}\" is not in the narration — it can't "
                                f"resolve, so that point reveals at the wrong time; use a phrase the "
                                f"narration actually speaks")
                spoken.append(None); continue
            warnings.append(f"{tag}: data-cue anchor \"{a[:20]}\" is out of spoken order — reveals fire "
                            f"out of sequence; order the anchors as the narration says them")
            pos = anywhere
        spoken.append(pos / L if L else 0.0)
        cur = max(cur, pos + len(a))
    if not (sb._is_num(duration) and float(duration) > 0):
        return                                       # need real durations (post-tts) for the timing gap
    dur = float(duration); n = len(anchors)
    shown = None
    if os.path.exists(words_path):                   # cued (edge): reveal at the resolved spoken-word time
        try:
            words = json.load(open(words_path))
            shown = [min(1.0, t / dur) for t in _cues.resolve_cues(words, anchors)]
        except Exception:
            shown = None
    if shown is None:                                # no word-timings: render estimates from text position
        shown = [min(1.0, t / dur) for t in _cues.estimate_cues_from_text(anchors, narration, dur)]
    for i, (sp, sh) in enumerate(zip(spoken, shown)):
        if sp is None:
            continue
        gap = sh - sp        # shown fraction minus spoken fraction
        if abs(gap) >= ALIGN_FRAC_TOL and abs(gap) * dur >= ALIGN_SECS_TOL:
            # shown LATER than spoken -> content lags; shown EARLIER -> content leads (appears before the voice)
            when = "lags the voice (content appears late)" if gap > 0 else "leads the voice (content appears early)"
            warnings.append(f"{tag}: point {i+1} (\"{(anchors[i] or '')[:18]}\") is spoken at ~{sp*100:.0f}% "
                            f"of the scene but shown at ~{sh*100:.0f}% — the reveal {when} by ~{abs(gap)*dur:.1f}s; "
                            f"re-anchor the point (data-cue) or adjust anim_seconds / the narration")

def _check_html_assets(out_dir, page_rel, wants_edge, index, errors, warnings,
                       anim_seconds=None, duration=None, narration=None, families=None,
                       captions_on=True, ai_look=False, soft_textures=None, comps=None, vertical=False):
    """Verify an html scene's page links resolve locally (base/theme/motifs css, seek.js,
    images), that its audio-synced cues will fire, and that its reveals won't lead/lag the audio."""
    path = os.path.join(out_dir, page_rel)
    tag = f"scene {index}"
    try:
        html = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        errors.append(f"{tag}: cannot read html page '{page_rel}': {e}")
        return
    if families is not None:
        families.append(_layout_family(html))
    if comps is not None:
        comps.append(_composition_sig(html))
    for url in _FILE_REF_RE.findall(html):
        local = _local_path_from_url(url)
        if local is False:
            errors.append(f"{tag}: page links a remote/data asset '{url[:50]}' — html scenes must use local file:// assets only")
        elif local and not os.path.exists(local):
            errors.append(f"{tag}: page asset not found: {local}")
    if "theme.css" in html and not os.path.exists(os.path.join(out_dir, "theme.css")):
        errors.append(f"{tag}: page links theme.css but {out_dir}/theme.css is missing — run theme.py")
    hexes = []
    for m in _COLOR_CTX_RE.finditer(html):
        hexes += _HEX_TOKEN_RE.findall(m.group(1) or m.group(2) or m.group(3) or "")
    if hexes:
        uniq = sorted(set(h.lower() for h in hexes))
        warnings.append(f"{tag}: raw hex {uniq[:3]} in a style/SVG color — use semantic vars "
                        f"(var(--accent)/var(--surface)/…), not hardcoded colors (off-theme risk)")
    # .code / algorithm block legibility: a wall of code is unreadable on a moving frame. Warn past
    # ~9 lines or any line > ~52 chars (visible text only — strip the inline tag markup first). This is
    # the code cousin of the caption wall-of-text + chart item-budget gates. (design dict "Algorithm".)
    for cm in re.finditer(r'<div[^>]*class="[^"]*\bcode\b[^"]*"[^>]*>(.*?)</div>', html, re.S):
        lns = re.findall(r'<span[^>]*class="[^"]*\bln\b[^"]*"[^>]*>(.*?)</span>', cm.group(1), re.S)
        if not lns:
            continue
        texts = [re.sub(r"<[^>]+>", "", ln).replace("&nbsp;", " ").strip("\n") for ln in lns]
        if len(texts) > 9:
            warnings.append(f"{tag}: a .code block has {len(texts)} lines (> 9) — a code wall is unreadable "
                            f"on a moving frame; keep the key ~9 lines and elide the rest with a `# …` comment")
        longest = max((sum(2 if rd._CJK_RE.match(ch) else 1 for ch in t) for t in texts), default=0)   # CJK mono = 2 cols
        # the readable line width tracks the column: a 9:16 vertical column (1080px) fits far fewer
        # monospace chars than a 16:9 row, so tighten the budget when vertical.
        line_max = 40 if vertical else 58
        if longest > line_max:
            warnings.append(f"{tag}: a .code line is {longest} chars (> {line_max}"
                            f"{' for 9:16' if vertical else ''}) — too wide to read in a video; shorten "
                            f"identifiers, drop alignment padding, or wrap the logic (algorithm_build budget)")
    # dogfood: the bottom .chrome rail (base.css bottom:56px) sits inside the burned caption band
    # (bottom ~8% of the canvas) — with captions ON they collide (text under text). Caught by the
    # AV critic in practice; cheaper to catch here, pre-render.
    if captions_on and re.search(r'class="[^"]*\bchrome\b', html):
        warnings.append(f"{tag}: page has a bottom .chrome rail but captions are ON — it collides "
                        f"with the burned caption band; drop .chrome (or set meta.captions:false)")
    # Living backdrop: ONE moving thing per page, and full-bleed only. seek.js animates every ambient
    # element, so two of them fight; and a .bg-live/.bg-drift on a non-full-bleed element (a card, a
    # .split side image) both distracts AND, if nested in .stage/.split, misfires the keyframe_qa
    # overflow probe (which then blames text length). Both are cheap static catches.
    # Token-exact + quote-agnostic (mirrors scenes.py _has_ambient / seek.js's .matches()): split each
    # class attr into tokens so 'my-bg-live' doesn't false-match, and accept single OR double quotes.
    cls_lists = [a or b for a, b in re.findall(r'''class\s*=\s*(?:"([^"]*)"|'([^']*)')''', html)]
    amb_classes = [c for c in cls_lists if {"bg-live", "bg-drift"} & set(c.split())]
    n_ambient = len(amb_classes) + len(re.findall(r'\bdata-ambient(?![\w-])', html))
    if n_ambient > 1:
        warnings.append(f"{tag}: {n_ambient} living backdrops on one page — keep ONE moving thing per page "
                        f"(motion-grammar: 'a moving backdrop is the loudest thing on screen')")
    for cl in amb_classes:
        if not ({"bg-soft", "bg-photo"} & set(cl.split())):
            warnings.append(f"{tag}: .bg-live/.bg-drift on a non-full-bleed element (class=\"{cl[:40]}\") — "
                            f"apply a living backdrop only to a full-bleed .bg-soft/.bg-photo, not a card/side image")
            break
    # BACKDROP THAT RENDERS AS NOTHING. Two ways an authored backdrop silently contributes zero:
    #   (a) it is painted BEFORE an opaque full-bleed sibling (a .world/.near-black grade covering
    #       inset:0), so it is completely occluded — the page looks identical with the image removed;
    #   (b) it is declared as a raw inline `background-image` div instead of <img class="bg-soft">,
    #       which bypasses the opacity guidance AND the flatness gate, so the page still reads flat.
    # Both shipped together in a real deck: five paid generated images sat under an opaque gradient at
    # opacity .10 — the tier was billed and bought literally nothing, and every gate stayed silent.
    _OPAQUE_FULLBLEED = r'<div[^>]*class\s*=\s*"[^"]*\b(?:world|near-black)\b'
    _occluder = re.search(_OPAQUE_FULLBLEED, html)
    if _occluder:
        for m in re.finditer(r'<(?:img|div)[^>]*(?:class\s*=\s*"[^"]*\bbg-(?:soft|photo)\b|background-image\s*:\s*url)[^>]*>', html):
            if m.start() < _occluder.start():
                warnings.append(f"{tag}: a backdrop is painted BEFORE the opaque full-bleed "
                                f"\"{_occluder.group(0)[12:44].strip()}…\" layer — it is fully occluded and renders as "
                                f"NOTHING (the page is identical with the image deleted). Move it AFTER that layer "
                                f"(and before any .desk/foreground plane)")
                break
    # DUPLICATE style= ON ONE ELEMENT — silent data loss. HTML keeps the FIRST style attribute and
    # DISCARDS the second, so an element that already carried `style="left:…;top:…"` and then gained a
    # second `style="animation-duration:…"` silently loses its POSITION and collapses to the layout
    # default. Three labels stacked into one illegible pile that way, and no geometry gate could see it:
    # the pile is inside the canvas, not blank, not overflowing — it is simply unreadable. Merge them.
    for m in re.finditer(r'<[a-zA-Z][^>]*?\sstyle\s*=\s*"[^"]*"[^>]*?\sstyle\s*=\s*"[^"]*"[^>]*>', html):
        dup = re.sub(r'\s+', ' ', m.group(0))[:90]
        warnings.append(f"{tag}: element carries TWO style= attributes — HTML keeps the first and "
                        f"DROPS the second, so whichever declaration came later (often the position) is "
                        f"silently lost: {dup}… — merge them into one style attribute")
        break

    for m in re.finditer(r'<div[^>]*style\s*=\s*"[^"]*inset\s*:\s*0[^"]*background-image\s*:\s*url\([^)]*\)[^"]*"[^>]*>', html):
        # The mechanism (div+background-image vs <img>) is fine; what matters is that the element
        # DECLARES itself a backdrop with bg-soft/bg-photo. Undeclared, it is invisible to the
        # flatness gate and to the opacity cap — so it reads as a flat page carrying a hidden image.
        if re.search(r'class\s*=\s*"[^"]*\bbg-(?:soft|photo)\b', m.group(0)):
            continue
        warnings.append(f"{tag}: full-bleed backdrop is UNDECLARED — a raw inset:0 background-image div with no "
                        f"bg-soft/bg-photo class. Add the class (or use <img class=\"bg-soft\"> + .bg-soft-tint) so "
                        f"it obeys the opacity cap and REGISTERS with the flatness gate, which cannot see it today")
        break
    # AI look (image_source:openai): content pages must NOT be flat — each carries a reused low-opacity
    # TOPIC texture (.bg-soft + .bg-soft-tint) so the deck isn't a flat wall. Exempt the image-forward
    # opener/closer (.bg-photo) and any content page leading with a real .media/.split image panel
    # (already visually non-flat).
    if ai_look and not re.search(r'class\s*=\s*"[^"]*\bbg-photo\b', html) \
            and not re.search(r'class\s*=\s*"[^"]*\b(?:media|split)\b', html):
        has_soft = re.search(r'class\s*=\s*"[^"]*\bbg-soft\b', html)
        has_tint = re.search(r'class\s*=\s*"[^"]*\bbg-soft-tint\b', html)
        if not (has_soft or has_tint):
            warnings.append(f"{tag}: AI look (image_source:openai) but this content page is FLAT — add a reused "
                            f".bg-soft topic texture + .bg-soft-tint (the design-director rotates meta.soft_textures)")
        else:
            for op in re.findall(r'class\s*=\s*"[^"]*\bbg-soft\b[^"]*"[^>]*style\s*=\s*"[^"]*opacity:\s*([0-9.]+)', html):
                try:
                    if float(op) > 0.20:
                        warnings.append(f"{tag}: content .bg-soft opacity {op} > .20 — too loud behind text; cap ~.14")
                        break
                except ValueError:
                    pass
            if has_soft and not has_tint:
                warnings.append(f"{tag}: a .bg-soft with no following .bg-soft-tint — add the tint so text stays legible")
            if soft_textures:
                bases = {os.path.basename(t) for t in soft_textures}
                for src in re.findall(r'class\s*=\s*"[^"]*\bbg-soft\b[^"]*"[^>]*src\s*=\s*"([^"]+)"', html):
                    if os.path.basename(src) not in bases:
                        warnings.append(f"{tag}: .bg-soft src '{os.path.basename(src)}' is outside meta.soft_textures — "
                                        f"reuse the deck texture set (rotate meta.soft_textures), not a bespoke per-page image")
                        break
    # Audio-synced reveals: cued points need a data-cue anchor AND a words.json to resolve against.
    # (The anchor regex is an approximate within-tag co-occurrence count — warning-only, never fatal.)
    if "data-cue-index" in html:
        nodes = _parse_dom(html)
        # BACKDROP INERTNESS: a full-bleed backdrop (.bg-motif/.bg-soft/.bg-photo/…) must be INERT
        # atmosphere. If an author drops the beat's OWN cued chart/reveal SVG into a .bg-motif without
        # stripping markers, render_html scrapes those data-cue anchors — and since the backdrop is the
        # FIRST child of <body>, its anchor WINS the per-index dedup over the real content, poisoning
        # every reveal time. Flag any element UNDER a backdrop that still carries a cue or a .reveal*.
        _INERT_BG = {"bg-motif", "bg-grid", "bg-soft", "bg-photo", "bg-stars", "bg-glow", "bg-paper"}
        def _under_backdrop(i):
            hops = 0
            while i is not None and 0 <= i < len(nodes) and hops < 128:
                if nodes[i].classes & _INERT_BG:
                    return True
                i = nodes[i].parent; hops += 1
            return False
        live_bg = sum(1 for nd in nodes
                      if (nd.cue is not None or (nd.classes & _REVEAL))
                      and not (nd.classes & _INERT_BG) and _under_backdrop(nd.parent))
        if live_bg:
            warnings.append(f"{tag}: {live_bg} element(s) INSIDE a full-bleed backdrop carry a data-cue-index/"
                            f".reveal — a backdrop must be inert atmosphere; strip every data-cue*/id/.reveal* from "
                            f"any SVG copied into .bg-motif (else render_html scrapes its anchors and poisons reveal timing)")
        cued_all = re.findall(r'data-cue-index="(\d+)"', html)
        # Connectors (.arrow/.hs-connect) legitimately BORROW their destination block's cue-index and
        # carry no data-cue= of their own — subtract one occurrence per connector index so the
        # duplicate + missing-anchor accounting counts only real content points (not co-revealing arrows).
        conn_cues = [n.cue for n in nodes if (n.classes & _CONN) and n.cue is not None]
        cued = list(cued_all)
        for cc in conn_cues:
            if str(cc) in cued:
                cued.remove(str(cc))
        anchored = re.findall(r'data-cue-index="\d+"[^>]*data-cue="|data-cue="[^"]*"[^>]*data-cue-index="\d+"', html)
        if len(anchored) < len(cued):
            warnings.append(f"{tag}: {len(cued) - len(anchored)} cued point(s) missing a data-cue anchor — they fall back to the paced stagger")
        dupes = sorted({i for i in cued if cued.count(i) > 1}, key=int)
        if dupes:
            warnings.append(f"{tag}: duplicate data-cue-index {dupes} — two points share a reveal slot, so one "
                            f"reveals at the wrong time; number each point's data-cue-index uniquely in spoken order")
        # CUE-CONTIGUITY: indices should be 0..N-1 (a gap index resolves to sparse t=0, flashing in with
        # the header). Count all indices incl. connectors — a connector at the top index is legitimate.
        idxs = sorted({int(i) for i in cued_all})
        if idxs and idxs != list(range(idxs[-1] + 1)):
            missing = [k for k in range(idxs[-1] + 1) if k not in idxs]
            warnings.append(f"{tag}: data-cue-index not contiguous (missing {missing}) — number points 0..N-1 in "
                            f"spoken order; a gap index resolves to t=0 and flashes in with the header")
        # UNCUED-REVEAL: on a cued page a reveal element with NO data-cue-index keeps animation-delay:0
        # and flashes in at ~0.7s WITH the header, leading the voice. Only header chrome may be uncued.
        uncued = 0
        for tm in re.finditer(r'<[^>]+class\s*=\s*"([^"]*)"[^>]*>', html):
            toks = set(tm.group(1).split())
            if (_REVEAL & toks) and not (_CHROME & toks) and not (_CONN & toks) \
                    and "data-cue-index" not in tm.group(0):
                uncued += 1
        if uncued:
            warnings.append(f"{tag}: {uncued} reveal element(s) are uncued on a cued page — they fire at ~0.7s with "
                            f"the header (leading the voice); give each its own data-cue-index in spoken order")
        # FACTS-PER-CUE: a cued wrapper holding ≥2 independently-meaningful facts makes them land on ONE
        # cue (all-at-once). Count meaningful descendants grouped by their nearest cued ancestor.
        per_cue = {}
        for nd in nodes:
            if nd.cue is not None or not (nd.classes & _MEAN):
                continue
            p, anc, nested = nd.parent, None, False
            while p is not None and 0 <= p < len(nodes):
                if nodes[p].cue is not None:
                    if nodes[p].classes & _MEAN:    # the cued ancestor is ITSELF a line-item (.tile/.row/.stat)
                        nested = True               # → this descendant is PART of that one unit, not a 2nd fact
                    else:
                        anc = nodes[p].cue
                    break
                if nodes[p].classes & _MEAN:        # an outer line-item already owns this node — count only the outermost
                    nested = True; break
                p = nodes[p].parent
            if anc is not None and not nested:
                per_cue[anc] = per_cue.get(anc, 0) + 1
        for cidx in sorted(c for c, k in per_cue.items() if k >= 2):
            warnings.append(f"{tag}: cue {cidx} groups {per_cue[cidx]} independently-meaningful facts into ONE reveal "
                            f"step — split each into its own cued reveal child so they land one-by-one")
        # CONNECTOR ORDERING: an .arrow/.hs-connect must reveal WITH its destination block — never static
        # (paints from frame 0, before any block) and never at an index below its destination.
        for parent in nodes:
            if not (parent.classes & {"flow", "hubspoke"}):
                continue
            kids = [n for n in nodes if n.parent == parent.idx]
            cued_blocks = [k for k in kids if k.cue is not None and not (k.classes & _CONN)]
            if not cued_blocks:
                continue
            for k in kids:
                if not (k.classes & _CONN):
                    continue
                later = [b for b in cued_blocks if b.idx > k.idx]
                dest = later[0] if later else cued_blocks[-1]
                if k.cue is None and not (k.classes & _REVEAL):
                    errors.append(f"{tag}: a static '{'/'.join(sorted(k.classes & _CONN))}' connector sits among cued "
                                  f"blocks — it paints from frame 0, before the blocks; add reveal + "
                                  f'data-cue-index="{dest.cue}" so it reveals WITH its destination block')
                elif k.cue is not None and dest.cue is not None and k.cue < dest.cue:
                    warnings.append(f"{tag}: a connector reveals at cue {k.cue} but points to a block at cue {dest.cue} "
                                    f'— set data-cue-index="{dest.cue}" so it appears WITH the block, not before it')
        # OPENING GAP: header chrome (.kicker/.rule/.title/.sub) shows in the ~1.2s head window, so a page
        # with one is never blank at the start. But a NO-header hero/pullquote whose FIRST reveal is
        # anchored to a phrase spoken well into the narration sits BLANK while the voice speaks the
        # opening — reads as broken. Anchor the first reveal to an OPENING phrase (or add a kicker/title).
        header_early = _has_static_opening_text(html)
        if not header_early and (narration or "").strip():
            pairs = re.findall(r'data-cue-index="(\d+)"[^>]*?data-cue="([^"]*)"', html)
            pairs += [(i, a) for (a, i) in re.findall(r'data-cue="([^"]*)"[^>]*?data-cue-index="(\d+)"', html)]
            if pairs:
                first_idx = min(int(i) for i, _ in pairs)
                first_anchor = next((a for i, a in pairs if int(i) == first_idx and a.strip()), None)
                if first_anchor:
                    pos = _cues._anchor_pos(narration, first_anchor)
                    if pos is not None and pos >= 0:
                        frac = pos / max(1, len(narration))
                        if frac > 0.15:
                            warnings.append(f"{tag}: no early header AND the first reveal is anchored to a phrase "
                                            f"spoken at ~{round(100*frac)}% of the narration — the page sits BLANK "
                                            f"while the opening plays; anchor the FIRST reveal to an opening phrase "
                                            f"(or add an uncued .kicker/.title that shows immediately)")
        words = os.path.join(out_dir, "audio", f"{index:02d}.words.json")
        if wants_edge and not os.path.exists(words):
            warnings.append(f"{tag}: data-cue reveals present but audio/{index:02d}.words.json missing — reveals fall back to the paced stagger (run tts.py with edge-tts)")
        # per-point content↔voice alignment (leads/lags), for cued OR paced reveals
        _reveal_alignment(html, narration, duration, anim_seconds, words, tag, warnings)
        # a cued animation that cannot finish before the cut (keyframe_qa is structurally blind to it)
        _reveal_truncation(html, narration, duration, words, tag, errors, warnings)
    else:
        # No audio-synced cues: a multi-point page reveals via the paced stagger. If anim_seconds is
        # set SMALL relative to the scene, all the points appear long before the voice reaches them.
        # Flag it so the author adds data-cue (preferred) or lets anim_seconds spread (~0.7×duration).
        points = len(re.findall(r'reveal-up-sm', html)) + len(re.findall(r'card[^"]*reveal-up"', html))
        if points >= 3 and sb._is_num(anim_seconds) and sb._is_num(duration) and duration > 0 \
                and anim_seconds < 0.5 * duration:
            warnings.append(f"{tag}: {points} reveal points, no data-cue, anim_seconds={anim_seconds}s on a "
                            f"{duration:.0f}s scene — content appears well before the voice reaches it; add "
                            f"data-cue anchors (preferred, audio-synced) or raise anim_seconds toward ~{0.7*duration:.0f}s")


def check(out_dir, pre_tts=False, vertical=False):
    path = os.path.join(out_dir, "storyboard.json")
    if not os.path.exists(path):
        return {"ok": False, "errors": [f"no storyboard.json in {out_dir}"], "warnings": [], "scenes": 0}
    try:
        data = sb.load(path)
    except (json.JSONDecodeError, OSError) as e:
        return {"ok": False, "errors": [f"storyboard.json unreadable: {e}"], "warnings": [], "scenes": 0}
    if not isinstance(data, dict):                       # valid JSON but e.g. `null` / a list
        return {"ok": False, "errors": ["storyboard.json is not a JSON object"], "warnings": [], "scenes": 0}
    return evaluate(data, out_dir, pre_tts=pre_tts, vertical=vertical)


def main():
    ap = argparse.ArgumentParser(description="Pre-render gate for storyboard.json")
    ap.add_argument("out_dir")
    ap.add_argument("--pre-tts", action="store_true", help="skip audio/duration checks (validate before tts.py)")
    ap.add_argument("--vertical", action="store_true", help="check the 9:16 canvas (mirror render.py --vertical)")
    ap.add_argument("--json", action="store_true", help="emit the result dict as JSON")
    ap.add_argument("--strict", action="store_true",
                    help="treat DESIGN warnings as blocking. The gates enforce 'it will render'; "
                         "almost every judgement about how the video LOOKS is advisory, which is how "
                         "a deck once shipped 'all green' carrying 94 warnings. Opt-in so existing "
                         "decks keep their exit codes; reach for it on a deck you intend to be good.")
    a = ap.parse_args()
    r = check(a.out_dir, pre_tts=a.pre_tts, vertical=a.vertical)
    if a.strict and r["warnings"]:
        r = dict(r, ok=False)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"[validate] {'OK' if r['ok'] else 'FAIL'}  "
              f"{r['scenes']} scene(s), {len(r['errors'])} error(s), {len(r['warnings'])} warning(s)")
        for e in r["errors"]:
            print(f"  ERROR: {e}")
        for w in r["warnings"]:
            print(f"  {'ERROR' if a.strict else 'warn '}: {w}")
        if a.strict and r["warnings"]:
            print(f"[validate] --strict: {len(r['warnings'])} design warning(s) treated as blocking")
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
