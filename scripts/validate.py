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
import argparse, json, os, re, sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storyboard as sb
import render as rd                       # caption-fit + font helpers, reused verbatim
import cues as _cues                      # anchor matcher (timed-callout cues + reveal alignment)

# A zoom delta beyond this reads as a lurch, not a gentle Ken Burns (SKILL.md / motion-grammar).
MAX_ZOOM_DELTA = 0.20
# A static frame held longer than this drags even with motion (SKILL.md pacing guardrail).
PACE_CEILING_S = 8.0
# A caption that needs more than this many wrapped lines is a wall of text on screen.
MAX_CAPTION_LINES = 3
# A burned caption flashed for less than this reads faster than a viewer can follow.
MIN_CAPTION_SECONDS = 0.7
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
_CONN = {"arrow", "hs-connect"}                       # connectors — reveal WITH their destination block
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
    jc = re.search(r'justify-content\s*:\s*([\w-]+)', style)
    jc = jc.group(1) if jc else "center"
    anchor = ("top" if jc in ("flex-start", "start") else "bottom" if jc in ("flex-end", "end")
              else "full" if jc.startswith("space") else "center")
    if re.search(r'class\s*=\s*"[^"]*\bsplit\b', html):
        balance = "split"
    elif re.search(r'class\s*=\s*"[^"]*\bgrid-asym\b', html):
        balance = "asym"
    elif "text-align:center" in style.replace(" ", ""):
        balance = "centered"
    else:
        balance = "twocol"
    kicker_first = bool(re.search(r'class\s*=\s*"[^"]*\bstage\b[^"]*"[^>]*>\s*<[^>]*class\s*=\s*"[^"]*\bkicker\b', html))
    hero = bool(re.search(r'class\s*=\s*"[^"]*\bbg-photo\b', html))
    # an image-forward page (.media/.split panel or a full-bleed .bg-photo) is NOT a flat wall, even
    # with no .bg-soft — mirror the AI-look flat exemption so an image-rich deck isn't false-flagged.
    img_rich = bool(re.search(r'class\s*=\s*"[^"]*\b(?:media|split|bg-photo)\b', html))
    flat = not img_rich and not any(re.search(r'class\s*=\s*"[^"]*\b' + re.escape(c) + r'\b', html) for c in _BG_CLASSES)
    return {"anchor": anchor, "balance": balance, "kicker_first": kicker_first, "hero": hero, "flat": flat}


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
    font = rd._load_font(rd._caption_font_px(W, H), rd._font_path(meta, text))  # narrow-dim scaled
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
                                   ai_look=ai_look, soft_textures=soft, comps=comps)
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
            if t == "title" and len(str(props.get("title") or "")) > 90:
                warnings.append(f"{tag}: title is {len(str(props.get('title')))} chars — a title should land in a "
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
                ceil = MAX_CAPTION_CHARS_CJK if rd._CJK_RE.search(ct) else MAX_CAPTION_CHARS_LATIN
                if len(ct) > ceil:
                    warnings.append(f"{tag}: caption is {len(ct)} chars (> {ceil}) — a wall of text on screen; split it on a comma/clause — \"{ct[:40]}…\"")
                if ct and ct[-1] in TRAIL_CLAUSE_MARKS:
                    warnings.append(f"{tag}: caption ends on a dangling \"{ct[-1]}\" — trim the trailing clause mark or merge with the next chunk")
                widow = _dangling_word(lines)
                if widow:
                    warnings.append(f"{tag}: caption ends on a lone word \"{widow}\" — rephrase so the last line isn't a widow")
            # minimum on-screen time (needs the timed segments, so only after tts)
            if not pre_tts and s.get("duration"):
                for seg in rd._captions_for(s):
                    if (seg.get("text") or "").strip() and (seg["end"] - seg["start"]) < MIN_CAPTION_SECONDS:
                        warnings.append(f"{tag}: a caption shows for {seg['end'] - seg['start']:.2f}s (< {MIN_CAPTION_SECONDS}s) — too fast to read; merge chunks or lengthen the line")
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
    # would fire on every (recommended) all-html "designed deck". Programmatic types still checked.
    run = 1
    for a, b in zip(prev_types, prev_types[1:]):
        run = run + 1 if a == b else 1
        if run == 3 and b != "html":
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
        # a split/asym page is two-column, not a center stack — don't count it toward center-anchor share
        center_share = sum(1 for c in comps if c["anchor"] == "center" and c["balance"] not in ("split", "asym")) / n
        offcenter = sum(1 for c in comps if c["balance"] in ("split", "asym") or c["anchor"] != "center") / n
        if center_share > 0.6:
            warnings.append(f"composition diversity: {round(100*center_share)}% of html pages are vertically "
                            f"CENTER-anchored — vary the vertical anchor (top/bottom/full-bleed), don't stack every beat mid-frame")
        if all(c["kicker_first"] for c in comps):
            warnings.append("composition diversity: EVERY html page opens with a top .kicker hat — let ≥1 hero lead "
                            "with its number/image (no kicker) so the deck isn't one template")
        if offcenter < 0.25:
            warnings.append(f"composition diversity: only {round(100*offcenter)}% of pages break the centered column — "
                            f"≥~1/3 should be off-center (grid-asym/.split/top-anchored)")
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

    # Remotion cinematic tier renders IMAGE scenes only — a non-image scene would render BLANK and still
    # pass the A/V gate (a blank video's audio is in sync). Fail at THIS gate too, not just at render.
    if meta.get("renderer") == "remotion":
        blank = [(s.get("index"), s.get("type", "slide")) for s in slides
                 if not (s.get("image") or (s.get("props") or {}).get("image"))
                 and s.get("type", "slide") not in ("slide", "title")]
        if blank:
            errors.append("renderer=remotion (cinematic tier) renders IMAGE scenes only, but scene(s) "
                          + ", ".join("#%s(%s)" % (i, t) for i, t in blank)
                          + " carry non-image content (html/chart/…) that would render BLANK — use "
                            "renderer=local for an html/designed deck, or give them an `image`")

    # Form-fit + creativity presence — mechanical hooks for design-critic D1/D2c, read from the
    # persisted design_plan.json (semantic judgment stays with the critic; these just flag the highest-
    # signal mismatch + a missing creative field). No-op when the plan isn't persisted.
    _design_plan_lints(out_dir, warnings)

    return {"ok": not errors, "errors": errors, "warnings": warnings, "scenes": len(slides)}


_TREND_SHAPE = ("time", "trend", "over-time", "over time", "trajectory", "growth", "declin", "rise",
                "fell", "fall", "change over", "quarter", "year-over", "month")
_SHARE_SHAPE = ("share", "part-of-whole", "part of whole", "proportion", "percent of", "split of",
                "breakdown", "makeup", "composition of")
_CATALOG_FORM = ("grid", "cards", "scorecard", "dash", "keypoints", "blocks")


def _design_plan_lints(out_dir, warnings):
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
    raw = plan.get("beats") or plan.get("scenes") or []
    # beats may be a dict keyed by id ({"1": {...}}) or a list — normalize to a list of dicts
    beats = ([dict(v, index=k) for k, v in raw.items() if isinstance(v, dict)]
             if isinstance(raw, dict) else [b for b in raw if isinstance(b, dict)])

    def _form(b):
        vis = b.get("visual") or {}
        return (b.get("form") or vis.get("form") or vis.get("type") or "").lower()

    for b in beats:
        shape = (b.get("content_shape") or b.get("visual_intent") or "").lower()
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
                        "--style and imagegen's style_preamble so the deck reads as one coherent register (design-critic D2c)")
    sig = plan.get("signature_concept") or {}
    sig_beat = sig.get("beat") if isinstance(sig, dict) else None
    if sig_beat is not None:
        for b in beats:
            if str(b.get("index")) == str(sig_beat) or b.get("beat") == sig_beat:
                if any(f in _form(b) for f in _CATALOG_FORM):
                    warnings.append("creativity: the signature_concept beat's form looks like a catalog grid — a "
                                    "signature must be a bespoke encoding, not a reskinned card grid (design-critic D2c)")
                break


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
                       captions_on=True, ai_look=False, soft_textures=None, comps=None):
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
        header_early = any((_CHROME & set(tm.group(1).split())) and "data-cue-index" not in tm.group(0)
                           for tm in re.finditer(r'<[^>]+class\s*=\s*"([^"]*)"[^>]*>', html))
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
    a = ap.parse_args()
    r = check(a.out_dir, pre_tts=a.pre_tts, vertical=a.vertical)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"[validate] {'OK' if r['ok'] else 'FAIL'}  "
              f"{r['scenes']} scene(s), {len(r['errors'])} error(s), {len(r['warnings'])} warning(s)")
        for e in r["errors"]:
            print(f"  ERROR: {e}")
        for w in r["warnings"]:
            print(f"  warn:  {w}")
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
