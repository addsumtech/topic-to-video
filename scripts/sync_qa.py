#!/usr/bin/env python3
"""Does each piece of on-screen TEXT appear when the narration SAYS it? — measured, both tiers.

    python3 scripts/sync_qa.py <out_dir>             # the audit, on whichever tier the board renders with
    python3 scripts/sync_qa.py <out_dir> --json=PATH # remotion: every measured element, for a before/after diff

The tiers run it from their own gates: `text_safe_qa.py <out_dir> --sync` (remotion) and `keyframe_qa.py`
(html). This file is the shared half — how text is matched to the voice, how a lag is judged, and how the
remotion tier turns the measurement into a beat's time warp (`derive_warp`).

WHAT IS MEASURED. For every visible element of on-screen text in a beat:
  * APPEAR — the first frame it is readable: its composed opacity at least APPEAR_OPACITY, at least half of
    its box visible (inside the frame and every clipping ancestor), and its text already holding the words
    the narration says (a typewriter has not "appeared" while it is still on its first letters).
  * SPOKEN — when the narration first says it, from the per-word times tts.py writes (`audio/NN.words.json`).
    Text is matched as a run of UNITS: a CJK run of two or more characters, a Latin word (stop words alone
    never match), or a number. The longest run the element shares with the narration wins; its first unit's
    time is the spoken time. Text the narration never says (a kicker, an axis tick, a unit label) is skipped.
  * LAG = appear - spoken. Late past LAG_WARN is a WARN, past LAG_ERROR an ERROR. Early only matters as a
    spoiler: more than EARLY_WARN seconds before the voice gets there, and only as a WARN — a title that sits
    on screen while the sentence works up to it is a composition choice, not a defect.

WHY THE DOM. Both tiers already walk every frame of every beat for the type-glide census
(runtime/textSafe.tsx `auditGlide`, keyframe_qa's census JS), recording each visible line's text and composed
opacity. This reads the same records, so there is no second renderer and nothing to calibrate against pixels.
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ── thresholds (calibrated on the seven films the audit was built on — see tests/test_sync_qa.py) ──────────
APPEAR_OPACITY = 0.5      # composed opacity at which a line counts as readable
APPEAR_VISIBLE = 0.5      # share of its box that must be on screen
LAG_WARN = 0.6            # s late: the voice has named it and the eye is still waiting
LAG_ERROR = 1.5           # s late: a whole clause has gone by with nothing to look at
EARLY_WARN = 3.0          # s early: it gives away what the sentence is about to say
MIN_COVERAGE = 0.15       # share of an element's text a match must carry...
MIN_RUN_SCORE = 6         # ...unless it is this long on its own (3 words / 6 CJK characters)

_CJK = "぀-ヿ㐀-鿿가-힣豈-﫿"
_CJK_RE = re.compile("[%s]" % _CJK)
# a number (with its decimals / thousands / a percent), or a run of letters (CJK split per character below)
_UNIT_RE = re.compile(r"(\d+(?:[.,:]\d+)*%?)|([^\W\d_]+(?:['’][^\W\d_]+)*)", re.U)
# Characters that carry grammar, not content: a CJK run made only of these ("一个", "的是") is not a mention.
_CJK_STOP = set("的了是在和与及也都就把被这那个们之其以而或为对上下中不有我你他她它吗呢吧啊着过得地很更最还又再能会要将从到向给让使用")
_LATIN_STOP = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "for", "with", "by", "as", "from", "into",
    "is", "are", "was", "were", "be", "been", "being", "it", "its", "this", "that", "these", "those", "there",
    "here", "we", "you", "your", "our", "they", "their", "he", "she", "his", "her", "not", "no", "but", "so",
    "if", "then", "than", "can", "will", "has", "have", "had", "do", "does", "did", "how", "what", "when",
    "why", "which", "who", "all", "any", "each", "more", "most", "just", "also", "very", "up", "out", "about",
}


def _stem(w):
    """Light English folding so a label and the sentence meet on the same word: `signals`/`signal`,
    `decays`/`decay`, `frequencies`/`frequency`. Never applied to short words, where it would merge `is`/`i`."""
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


# CHINESE NUMERALS ARE NUMBERS. A frame writes 「约 962 平方公里」 and the narration says 九百六十二平方公里 —
# written for the ear, as tts needs it. Both sides are read through units(), so both meet on `962`.
_CN_DIG = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_MUL = {"十": 10, "百": 100, "千": 1000, "万": 10 ** 4, "亿": 10 ** 8}


def _cn_int(s):
    if len(s) > 1 and all(c in _CN_DIG for c in s):          # 二〇一八 — read digit by digit
        return int("".join(str(_CN_DIG[c]) for c in s))
    total, section, num = 0, 0, 0
    for c in s:
        if c in _CN_DIG:
            num = _CN_DIG[c]
        else:
            m = _CN_MUL[c]
            if m >= 10 ** 4:
                total += (section + num) * m
                section = 0
            else:
                section += (num if num else 1) * m
            num = 0
    return total + section + num


def _cn_numeral_at(run, i):
    """(normalised number, end index) for a Chinese numeral starting at run[i], or None. A lone 一/两/零 is a
    word ("一枚", "两边"), never a number, and 点 is a decimal point only between two numerals."""
    j = i
    while j < len(run) and (run[j] in _CN_DIG or run[j] in _CN_MUL):
        j += 1
    if j == i:
        return None
    whole = run[i:j]
    decimal = j + 1 < len(run) and run[j] == "点" and run[j + 1] in _CN_DIG
    if len(whole) == 1 and whole in "一两零〇" and not decimal:
        return None
    if whole[0] in _CN_MUL and whole[0] != "十":       # 万一 / 千万: a word, and 十 is the only bare multiplier
        return None
    try:
        val = str(_cn_int(whole))
    except (KeyError, ValueError):
        return None
    if decimal:
        k = j + 1
        while k < len(run) and run[k] in _CN_DIG:
            k += 1
        val += "." + "".join(str(_CN_DIG[c]) for c in run[j + 1:k])
        j = k
    return val, j


def units(text):
    """[(kind, norm, a, b)] — the matchable units of `text` with their character range. kind: 'c' a CJK
    character, 'w' a Latin word (casefolded, stemmed), 'n' a number (thousands separators dropped; Chinese
    numerals read as their value)."""
    out = []
    for m in _UNIT_RE.finditer(text or ""):
        if m.group(1):
            out.append(("n", m.group(1).replace(",", ""), m.start(), m.end()))
            continue
        run, base = m.group(2), m.start()
        i = 0
        while i < len(run):
            if _CJK_RE.match(run[i]):
                num = _cn_numeral_at(run, i)
                if num is not None:
                    out.append(("n", num[0], base + i, base + num[1]))
                    i = num[1]
                    continue
                out.append(("c", run[i], base + i, base + i + 1))
                i += 1
                continue
            j = i
            while j < len(run) and not _CJK_RE.match(run[j]):
                j += 1
            w = run[i:j].casefold().replace("’", "'")
            if w.endswith("'s"):
                w = w[:-2]
            out.append(("w", _stem(w), base + i, base + j))
            i = j
    return out


def _run_ok(run):
    """Is this run of matched units a MENTION? A number of two or more digits (a lone digit only beside
    another matched unit — 「3」 alone is said everywhere); a Latin content word; or a CJK run carrying two
    content characters (「的粉」 is one word of content and a particle, and matched every 「磨好的粉」)."""
    nums = [u[1] for u in run if u[0] == "n"]
    if any(len(re.sub(r"\D", "", x)) >= 2 for x in nums) or (nums and len(run) >= 2):
        return True
    if any(u[0] == "w" and u[1] not in _LATIN_STOP and len(u[1]) >= 2 for u in run):
        return True
    return sum(1 for u in run if u[0] == "c" and u[1] not in _CJK_STOP) >= 2


def _score(run):
    return sum(1 if u[0] == "c" else 2 for u in run)


CONTEXT_UNITS = 10        # spoken units either side of a mention in which the element's other words count
CONTEXT_WEIGHT = 0.5      # ...at half the weight of the run itself


def _content(u):
    return (u[0] == "n" or (u[0] == "w" and u[1] not in _LATIN_STOP)
            or (u[0] == "c" and u[1] not in _CJK_STOP))


def best_match(text_units, spoken_units):
    """(start index into spoken, length, start index into text) of the best mention, or None.

    Every run of units the element shares with the narration that is a MENTION (`_run_ok`) is a candidate,
    scored by its own length (a word or a number weighs two CJK characters) plus half of whatever ELSE of the
    element the narration says within CONTEXT_UNITS of it. The context is what tells two mentions apart:
    「2018 · 二线关撤销」 shares 二线关 with a sentence at 3.7s and with the one at 9s that also says 2018 and
    撤 — the second is the one this label is about. A tie goes to the mention the voice reaches first."""
    n, m = len(text_units), len(spoken_units)
    if not n or not m:
        return None
    runs = []                                            # (run score, spoken start, length, text start)
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        ti = text_units[i - 1]
        for j in range(1, m + 1):
            sj = spoken_units[j - 1]
            if ti[0] == sj[0] and ti[1] == sj[1]:
                cur[j] = prev[j - 1] + 1
                k = cur[j]
                run = text_units[i - k:i]                # the whole run ending here
                if _run_ok(run):
                    runs.append((_score(run), j - k, k, i - k))
        prev = cur
    if not runs:
        return None
    best, best_key = None, None
    for sc, j0, k, i0 in runs:
        lo, hi = max(0, j0 - CONTEXT_UNITS), min(m, j0 + k + CONTEXT_UNITS)
        near = {(u[0], u[1]) for u in spoken_units[lo:hi]}
        extra = {(u[0], u[1]) for x, u in enumerate(text_units)
                 if not (i0 <= x < i0 + k) and _content(u) and (u[0], u[1]) in near}
        bonus = sum(1 if kind == "c" else 2 for kind, _v in extra)
        key = (sc + CONTEXT_WEIGHT * bonus, sc, -j0)
        if best_key is None or key > best_key:
            best, best_key = (j0, k, i0), key
    return best


# ── the voice, as timed units ───────────────────────────────────────────────────────────────────────────────
_CHAR_CAP = 0.35   # s: one character never takes longer than this — a pause before the next word is silence


def _char_times(text, spans, duration):
    """Seconds at which each character of `text` is reached, from `cues.word_spans` ranges."""
    times = [None] * len(text)
    for k, sp in enumerate(spans):
        a, b, t = sp["a"], sp["b"], float(sp["t"])
        nxt = float(spans[k + 1]["t"]) if k + 1 < len(spans) else (duration or t + 0.3 * (b - a))
        per = min(_CHAR_CAP, max(0.0, nxt - t) / max(1, b - a))
        for c in range(a, min(b, len(text))):
            times[c] = t + per * (c - a)
    known = [i for i, x in enumerate(times) if x is not None]
    if not known:
        return None
    for i in range(len(times)):                          # characters between spans: the next span's start
        if times[i] is None:
            nxt = next((times[j] for j in known if j > i), None)
            prv = next((times[j] for j in reversed(known) if j < i), None)
            times[i] = nxt if nxt is not None else prv
    return times


def spoken_units(narration, words, duration=None):
    """[(kind, norm, a, b, t)] for the beat's narration — every unit with the second the voice reaches it,
    and the source of those times: 'words' (edge-tts per-word boundaries) or 'text' (position in the
    narration, the fallback the html tier's cues use for voices that report no word times).

    The narration is the text, located against the word stream with `cues.word_spans`: edge-tts NORMALISES what
    it speaks ("1.5" -> 一点五), so its own tokens can miss a number the board wrote in digits, while the
    narration still holds it and the spans around it still say when."""
    import cues as _cues
    text = narration or ""
    times, source = None, None
    if words and text.strip():
        spans = _cues.word_spans(words, text)
        if spans:
            times, source = _char_times(text, spans, duration), "words"
    if times is None and words:
        # the board's narration and the voice's words disagree too much to align: use the words themselves
        text = "".join(str(w.get("w") or "") + ("" if _CJK_RE.search(str(w.get("w") or "")) else " ")
                       for w in words)
        times, pos = [], 0
        for k, w in enumerate(words):
            tok = str(w.get("w") or "") + ("" if _CJK_RE.search(str(w.get("w") or "")) else " ")
            t = float(w.get("t") or 0)
            nxt = float(words[k + 1].get("t") or t) if k + 1 < len(words) else t + 0.3 * len(tok)
            per = min(_CHAR_CAP, max(0.0, nxt - t) / max(1, len(tok)))
            times.extend(t + per * c for c in range(len(tok)))
            pos += len(tok)
        source = "words"
    if times is None:
        if not text.strip() or not duration:
            return [], None
        w = [3 if _CJK_RE.match(ch) else 1 for ch in text]
        total, acc, times = float(sum(w)) or 1.0, 0.0, []
        for x in w:
            times.append(acc / total * float(duration))
            acc += x
        source = "text"
    out = [(k, nrm, a, b, times[min(a, len(times) - 1)]) for k, nrm, a, b in units(text)]
    return out, source


# ── appearance: census frames -> elements ───────────────────────────────────────────────────────────────────
def _contains(text_units, run):
    """Does `text_units` hold `run` (a list of (kind, norm)) contiguously?"""
    L = len(run)
    for i in range(len(text_units) - L + 1):
        if all(text_units[i + k][0] == run[k][0] and text_units[i + k][1] == run[k][1] for k in range(L)):
            return True
    return False


def _readable(line):
    return (float(line.get("o", 1)) >= APPEAR_OPACITY and float(line.get("v", 1)) >= APPEAR_VISIBLE)


def match_spoken(text, spoken):
    """(run, spoken second, what was said) for the narration's mention of `text`, or None when the voice never
    says it. The ONE definition of "the voice says this text": the sync audit judges a DOM element with it and
    `item_cues` pins a prop's item with it, so the two cannot disagree about which word an item belongs to."""
    tu = units(text)
    hit = best_match(tu, spoken)
    if hit is None:
        return None
    s0, L, t0 = hit
    # A LONG LINE THAT SHARES ONE TERM WITH THE VOICE IS NOT THE VOICE SAYING IT. A credit — 「原图：… CC
    # BY-SA 4.0 · Wikimedia Commons；k 空间…由该图傅里叶变换计算」 — names a term the narration says
    # minutes of sentence later; its "lag" would be noise. The match must carry MIN_COVERAGE of the
    # element's own text, unless it is a long run on its own (MIN_RUN_SCORE).
    if _score(tu[t0:t0 + L]) < MIN_RUN_SCORE and _score(tu[t0:t0 + L]) < MIN_COVERAGE * _score(tu):
        return None
    return ([(u[0], u[1]) for u in tu[t0:t0 + L]], float(spoken[s0][4]), "".join(_said(spoken[s0:s0 + L])))


def measure_beat(samples, spoken):
    """Every on-screen text element of one beat with its appear and spoken times.

    `samples` is [(t_seconds, [census line, ...]), ...] in time order — the beat's frames on ITS OWN clock
    (t = 0 where its narration starts). `spoken` is spoken_units(). Returns a list of
    {"text", "said", "spoken", "appear", "lag", "key"} sorted by appear time, one per distinct text (an
    element drawn twice — a title and its echo — appears when the first of them does).

    AN ELEMENT IS ITS TEXT, NOT ITS DOM SLOT. The census keys a line by its DOM path, and a path is a sibling
    index: when a register mounts or unmounts an element, the same path names a different line. Tracking by
    path and keeping each path's longest-shown text lost 「2018 · 二线关撤销」 for four seconds — its path showed
    another label first — and reported it 4 s late. So a distinct text is the element, wherever it is drawn;
    within one path a text that is a PREFIX of a longer one is that line still typing, and belongs to it."""
    first = {}                                           # (key, text) -> first readable t
    keys_of = {}                                         # text -> keys it was drawn under
    for t, lines in samples:
        for ln in lines:
            txt = str(ln.get("t") or "").strip()
            if not txt:
                continue
            k = ln.get("k")
            keys_of.setdefault(txt, set()).add(k)
            if _readable(ln) and (k, txt) not in first:
                first[(k, txt)] = t
    by_key = {}
    for (k, txt) in first:
        by_key.setdefault(k, set()).add(txt)
    # canonical text of each (key, text): the longest text the same key shows that starts with it
    canon = {}
    for k, texts in by_key.items():
        for txt in texts:
            longer = [o for o in texts if o != txt and o.startswith(txt.rstrip("…"))]
            canon[(k, txt)] = max(longer, key=len) if longer else txt
    elements = {}
    for (k, txt), c in canon.items():
        elements.setdefault(c, []).append((k, txt))
    out = []
    for text, states in elements.items():
        m = match_spoken(text, spoken)
        if m is None:
            continue
        run, spoken_t, said = m
        # readable AND already holding the words: a typing line has not appeared while it is on its first letters
        times = [(first[st], st[0]) for st in states
                 if _contains([(u[0], u[1]) for u in units(st[1])], run)]
        if not times:
            continue
        appear, key = min(times)
        out.append({"text": text, "said": said, "spoken": round(spoken_t, 3),
                    "appear": round(appear, 3), "lag": round(appear - spoken_t, 3), "key": key})
    return sorted(out, key=lambda r: (r["appear"], r["text"]))


def _said(us):
    out, prev = [], None
    for u in us:
        if prev is not None and (u[0] != "c" or prev[0] != "c"):
            out.append(" ")
        out.append(u[1])
        prev = u
    return out


def level(rec):
    lag = rec["lag"]
    if lag > LAG_ERROR:
        return "error"
    if lag > LAG_WARN:
        return "warn"
    if lag < -EARLY_WARN:
        return "early"
    return "ok"


def describe(rec):
    lag = rec["lag"]
    when = ("%.1fs AFTER the voice says it" % lag) if lag >= 0 else ("%.1fs BEFORE the voice says it" % -lag)
    return "%r appears at %.2fs, %s (%r at %.2fs)" % (
        rec["text"][:40], rec["appear"], when, rec["said"], rec["spoken"])


def summarize(beats):
    """{"elements", "late_warn", "late_error", "early", "worst_lag", "mean_abs_lag"} over
    {beat_label: [records]} — the numbers a before/after comparison reads."""
    allr = [r for rs in beats.values() for r in rs]
    lv = [level(r) for r in allr]
    return {"elements": len(allr), "late_warn": lv.count("warn"), "late_error": lv.count("error"),
            "early": lv.count("early"),
            "worst_lag": round(max((r["lag"] for r in allr), default=0.0), 2),
            "mean_abs_lag": round(sum(abs(r["lag"]) for r in allr) / len(allr), 3) if allr else 0.0}


def words_for(out_dir, slide):
    """The beat's per-word times, or [] — `audio/NN.words.json` beside its mp3 (tts.py)."""
    audio = slide.get("audio")
    cands = []
    if audio:
        cands.append(os.path.splitext(os.path.join(out_dir, audio))[0] + ".words.json")
    idx = slide.get("index")
    if isinstance(idx, int):
        cands.append(os.path.join(out_dir, "audio", "%02d.words.json" % idx))
    for wj in cands:
        if os.path.exists(wj):
            try:
                return json.load(open(wj, encoding="utf-8")) or []
            except (OSError, ValueError):
                return []
    return []


def narration_of(slide):
    return slide.get("narration") or slide.get("script") or ""


# ── the remotion tier's time warp ───────────────────────────────────────────────────────────────────────────
# A register's entrances are timed as fractions of its beat — `seg(t, 0.62, 0.78)` — whatever the sentence
# says, and 172 of 194 registers expose no timing prop. So the BEAT'S CLOCK is warped instead: Film.tsx hands
# the register `warp(frame)` rather than `frame`, a monotone piecewise-linear map whose knots put the frame at
# which the register shows a text element onto the frame at which the voice names it. The register file is
# never touched. The knots are derived from the census of the UN-warped film (`derive_warp`).
SLOPE_MIN = 0.4           # register frames per film frame: never slower than this...
SLOPE_MAX = 2.5           # ...nor faster. A warp that would need more is satisfied partly, never absurdly.
LEAD_S = 0.1              # s: an element should reach readable a breath BEFORE the word, not after it
DEADBAND_S = 0.25         # s: lateness inside this costs nothing
OPENING_S = 1.5           # s past the entry hold: what is readable by then IS the beat's opening composition
EARLY_SOFT_S = 1.0        # s early before it costs anything at all (a label settling just ahead of its word)
EARLY_SOFT_COST = 0.25    # per second early past EARLY_SOFT_S...
EARLY_HARD_COST = 0.5     # ...and per second past EARLY_WARN, where it becomes a spoiler (late costs more)
STRAIN_COST = 0.15        # per second of film played at e (2.7x) off the register's own speed: keeps warps gentle
MAX_ANCHORS = 12          # candidate anchors searched exhaustively (2^12 subsets — milliseconds)


def _pad(dur_frames, seam):
    """runtime/motion `useT`'s held edge: the register is still for this many frames at each end."""
    return min(seam, (max(1, int(dur_frames)) - 1) // 3)


def _place(anchors, first, last, lo, hi, opening=None):
    """Knots through `anchors` [(register frame, film frame wanted)] sorted by register frame, each film frame
    moved into what the slope allows from the previous knot AND still lets the exit hold be reached; None
    when the anchors cannot be ordered. With `opening`, the clock is the identity up to that frame."""
    knots = [[float(first), float(first)]]
    if opening is not None and first < opening < last:
        knots.append([float(opening), float(opening)])
    for g, f in anchors:
        pf, pg = knots[-1]
        dg = g - pg
        if dg <= 0:
            return None
        f_lo = max(pf + dg / hi, last - (last - g) / lo)
        f_hi = min(pf + dg / lo, last - (last - g) / hi)
        if f_lo > f_hi:
            return None
        knots.append([min(max(f, f_lo), f_hi), float(g)])
    knots.append([float(last), float(last)])
    return knots


def warp_cost(records, knots, fps):
    """What a warp leaves wrong, in seconds: lateness past DEADBAND_S, earliness past EARLY_SOFT_S (light) and
    past EARLY_WARN (heavy), plus STRAIN_COST per second of film played off the register's own speed (|ln
    slope| x duration). Every measured element counts, moved or not — a warp that fixes one label by dragging
    three others off their words is worse, and this is what says so."""
    import math
    c = 0.0
    for r in records:
        a = moved_appear(r, knots, fps)
        lag = a - r["spoken"]
        c += max(0.0, lag - DEADBAND_S) + max(0.0, lag - LAG_ERROR)          # late; twice over past ERROR
        c += EARLY_SOFT_COST * max(0.0, -lag - EARLY_SOFT_S) + EARLY_HARD_COST * max(0.0, -lag - EARLY_WARN)
    for (f0, g0), (f1, g1) in zip(knots or [], (knots or [])[1:]):
        c += STRAIN_COST * abs(math.log((g1 - g0) / (f1 - f0))) * (f1 - f0) / fps
    return c


PIN_SLACK = 1.0          # s: an item reading within this of its cue (or after it) is ON its cue, not on the clock


def pinned(r):
    """Does this record read where its per-element cue put it (runtime/cue.ts)? Such an item is converted through
    the warp at render time, so it stays on its word whatever the warp does: it is no anchor and it never moves."""
    return r.get("cap") is not None and r["appear"] >= float(r["cap"]) - PIN_SLACK


def moved_appear(r, knots, fps):
    """Where a measured element reads once `knots` warp its register's clock (seconds). An element on its cue
    stays; one still on the register's own clock moves with the warp — but never later than its cue, which is
    the most a cued item can ever be (`start` only ever pulls earlier)."""
    if pinned(r):
        return r["appear"]
    a = unwarp_frame(r["appear"] * fps, knots) / fps if knots else r["appear"]
    return min(a, float(r["cap"])) if r.get("cap") is not None else a


def derive_warp(records, dur_frames, fps, seam, slope=(SLOPE_MIN, SLOPE_MAX)):
    """(knots, notes) for one beat from its UN-warped measurement, or ([], notes) for the identity.

    knots are [[film_frame, register_frame], ...], strictly increasing in both, from the end of the entry hold
    to the start of the exit hold — the seams are never warped, so a beat opens and closes on exactly the frames
    it did. Between knots the map is linear and every segment's slope lies in `slope`.

    HOW. The opening — the entry hold plus OPENING_S — is never warped: what is readable by then is the beat's
    composition, and stretching it to delay a title is slow motion, not sync. Every element that becomes
    readable after it offers one anchor: its register frame onto (spoken - LEAD_S).
    Elements readable on the same frame offer one, onto the earliest of their words. Every subset of anchors
    that is increasing in both clocks is placed (`_place`, moving each anchor only as far as the slope allows)
    and scored by `warp_cost` over ALL the beat's elements; the cheapest wins, and the identity wins unless
    something is cheaper. So inconsistent anchors drop out, an anchor the slope can only half-reach is kept
    only if half is worth it, and no anchor is honoured at the price of pulling others off their words."""
    lo, hi = slope
    D = max(1, int(dur_frames))
    pad = _pad(D, seam)
    first, last = pad, D - 1 - pad
    if last - first < 4:
        return [], ["beat too short to warp"]
    open_f = first + OPENING_S * fps
    groups = {}
    for r in records:
        rf = r["appear"] * fps
        if rf <= open_f + 1 or rf >= last - 1 or pinned(r):
            continue
        key = int(round(rf))
        tgt = (r["spoken"] - LEAD_S) * fps
        groups[key] = tgt if key not in groups else min(groups[key], tgt)
    cands = sorted((float(g), float(min(max(f, open_f + 1), last - 1))) for g, f in groups.items())
    if len(cands) > MAX_ANCHORS:                         # the ones that are furthest off their words
        cands = sorted(sorted(cands, key=lambda a: -abs(a[1] - a[0]))[:MAX_ANCHORS])
    base = warp_cost(records, [], fps)
    best, best_cost = [], base
    n = len(cands)
    for mask in range(1, 1 << n):
        sub = [cands[i] for i in range(n) if mask >> i & 1]
        if any(b[1] <= a[1] for a, b in zip(sub, sub[1:])):
            continue                                      # not increasing in both clocks
        knots = _place(sub, first, last, lo, hi, opening=open_f)
        if knots is None:
            continue
        c = warp_cost(records, knots, fps)
        if c < best_cost - 1e-9 or (abs(c - best_cost) < 1e-9 and best and len(knots) < len(best)):
            best, best_cost = knots, c
    notes = []
    if not best or all(abs(f - g) < 0.5 for f, g in best):
        return [], notes
    for r in records:
        a = moved_appear(r, best, fps)
        if abs(a - r["appear"]) >= 0.2:
            notes.append("%r %.2fs -> %.2fs (said at %.2fs)" % (r["text"][:24], r["appear"], a, r["spoken"]))
    notes.append("cost %.2f -> %.2f" % (base, best_cost))
    return [[round(f, 3), round(g, 3)] for f, g in best], notes


def warp_frame(f, knots):
    """The register frame Film.tsx hands a beat at film frame `f` — the same piecewise-linear map as
    runtime `warpFrame`, written here for the tests and for predicting where an element will land."""
    if not knots or f <= knots[0][0] or f >= knots[-1][0]:
        return float(f)
    for (f0, g0), (f1, g1) in zip(knots, knots[1:]):
        if f0 <= f <= f1:
            return g0 + (g1 - g0) * (f - f0) / (f1 - f0)
    return float(f)


def unwarp_frame(g, knots):
    """The film frame at which the register reaches its own frame `g` — the inverse of warp_frame."""
    if not knots or g <= knots[0][1] or g >= knots[-1][1]:
        return float(g)
    for (f0, g0), (f1, g1) in zip(knots, knots[1:]):
        if g0 <= g <= g1:
            return f0 + (f1 - f0) * (g - g0) / (g1 - g0)
    return float(g)


def check_knots(knots, dur_frames, slope=(SLOPE_MIN, SLOPE_MAX)):
    """Problems with an AUTHORED warp (storyboard `sync.anchors`), [] when it is sound."""
    lo, hi = slope
    probs = []
    if not knots:
        return probs
    for (f0, g0), (f1, g1) in zip(knots, knots[1:]):
        if f1 <= f0 or g1 <= g0:
            probs.append("anchors must increase in both clocks (%s -> %s)" % ([f0, g0], [f1, g1]))
            continue
        s = (g1 - g0) / (f1 - f0)
        if not (lo - 1e-6 <= s <= hi + 1e-6):
            probs.append("segment %s -> %s plays the register at %.2fx, outside %.1f-%.1fx"
                         % ([f0, g0], [f1, g1], s, lo, hi))
    if knots[0][0] < 0 or knots[-1][0] > dur_frames - 1:
        probs.append("anchors run outside the beat (0..%d frames)" % (dur_frames - 1))
    return probs


# registers that already run on the voice or on a recording: warping their clock would take them OFF it
_SYNC_EXEMPT_IMPORTS = ("runtime/voice", "runtime/screen")


_SRC = os.path.join(os.path.dirname(HERE), "remotion", "src")
# any import specifier: `from '...'`, `import('...')`, a bare `import '...'` — relative, or a workshop alias
_ANY_IMPORT = re.compile(r"""(?:\bfrom\s+|\bimport\s*\(\s*|^\s*import\s+)['"]([^'"]+)['"]""", re.M)
_ALIASES = {"@runtime/": os.path.join(_SRC, "runtime"), "@shots/": os.path.join(_SRC, "shots")}


def _walk_deps(path, seen):
    path = os.path.realpath(path)
    if path in seen or not os.path.isfile(path):
        return
    seen.add(path)
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        return
    for spec in _ANY_IMPORT.findall(src):
        if spec.startswith("."):
            base = os.path.join(os.path.dirname(path), spec)
        else:
            pre = next((p for p in _ALIASES if spec.startswith(p)), None)
            if pre is None:
                continue                                   # a package ('react', 'remotion')
            base = os.path.join(_ALIASES[pre], spec[len(pre):])
        for ext in (".tsx", ".ts", "/index.tsx", "/index.ts", ""):
            if os.path.isfile(base + ext):
                _walk_deps(base + ext, seen)
                break


def _register_deps(shot, out_dir=None):
    """Every module the register's file reaches (the film's workshop copy first, then the library's), as
    '/'-paths; [] when there is no such register. A WORKSHOP register imports the runtime through its aliases
    (`@runtime/voice`, `@shots/X`), which a relative-only walk never followed — so a film's own register drawing
    from the voice was warped off it, and one adopting runtime/cue was never given its cues."""
    roots = [os.path.join(_SRC, "shots", shot + ".tsx")]
    if out_dir:
        import workshop as _ws
        roots.insert(0, os.path.join(_ws.workshop_dir(out_dir), "shots", shot + ".tsx"))
    for root in roots:
        if os.path.exists(root):
            seen = set()
            _walk_deps(root, seen)
            return sorted(d.replace(os.sep, "/") for d in seen)
    return []


def _reaches(deps, mod):
    return any(d.endswith(mod + ".tsx") or d.endswith(mod + ".ts") for d in deps)


def register_exempt(shot, out_dir=None):
    """Why this register's clock must not be warped, or None. A register that reads the narration's own
    audio (runtime/voice) is synced by construction; one that plays a screen recording (runtime/screen) is
    timed by the recording. Read from the register's imports, so a new one is covered the day it is written."""
    deps = _register_deps(shot, out_dir)
    for mod in _SYNC_EXEMPT_IMPORTS:
        if _reaches(deps, mod):
            return "it draws from %s (already on the voice / a recording)" % mod
    return None


# ── per-element cues (runtime/cue.ts) ───────────────────────────────────────────────────────────────────────
# The warp is ONE monotone clock per beat, so it cannot reorder: an item the voice names first and the register
# shows last stays late. A register that imports runtime/cue reads, per item, the film second at which the voice
# names it and starts that item's entrance early enough to read on its word (never later than its own timing).
# These are those seconds — computed from the beat's props and its voice, no census needed.
CUE_MODULE = "runtime/cue"
CUE_TEXT_FIELDS = ("text", "label", "title", "name", "caption")


def register_takes_cues(shot, out_dir=None):
    """Does this register read per-element cues? (It imports runtime/cue — read from its imports, like the
    exemption, so a register adopts the hook by importing it and nothing else has to be told.)"""
    return _reaches(_register_deps(shot, out_dir), CUE_MODULE)


def item_texts(props):
    """[(path, text)] — every text item of a beat's props a register may cue: a string prop (`caption`), a
    list of strings (`questions.1`), or a list of objects carrying their words in one of CUE_TEXT_FIELDS
    (`labels.0` -> labels[0].text). runtime/cue.ts keys an item by the same path."""
    out = []
    for k, v in (props or {}).items():
        if isinstance(v, str):
            out.append((k, v))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                if isinstance(x, str):
                    out.append(("%s.%d" % (k, i), x))
                elif isinstance(x, dict):
                    f = next((f for f in CUE_TEXT_FIELDS if isinstance(x.get(f), str)), None)
                    if f:
                        out.append(("%s.%d" % (k, i), x[f]))
    return [(k, t) for k, t in out if t.strip()]


def item_cues(props, spoken):
    """{path: film second by which the item should READ} for every item the voice names — LEAD_S before its
    first word, the same target the warp aims an entrance at. An item the voice never says gets no cue."""
    out = {}
    for key, text in item_texts(props):
        m = match_spoken(text, spoken)
        if m is not None:
            out[key] = round(max(0.0, m[1] - LEAD_S), 3)
    return out


def attach_cues(out_dir, data, props, slides):
    """Give each scene whose register reads cues its `cues` (in place). Not on a beat whose board says
    `sync: "off"` or gives its own `sync.anchors` — the author has taken the clock — and not on a register that
    does not import runtime/cue, whose props then stay exactly what they were. Returns [cues or None] per scene."""
    meta = (data or {}).get("meta") or {}
    got = []
    for sc, sl in zip(props["scenes"], slides):
        sc.pop("cues", None)
        setting = _sync_setting(meta, sl)
        cues = None
        if setting is None and register_takes_cues(sc["shot"], out_dir):
            spoken, _src = spoken_units(narration_of(sl), words_for(out_dir, sl), sl.get("duration"))
            cues = item_cues(sc.get("props") or {}, spoken) or None
        if cues:
            sc["cues"] = cues
        got.append(cues)
    return got


def cap_records(records, scene):
    """The beat's measured records, each carrying `cap` — its item's cue — when the scene cues the item that
    drew it. A census line is matched to an item by its text: equal, or one holding the other (a wrapped
    item is measured line by line)."""
    cues = (scene or {}).get("cues") or {}
    if not cues:
        return records
    items = [(re.sub(r"\s+", "", t), cues[k]) for k, t in item_texts(scene.get("props") or {}) if k in cues]
    out = []
    for r in records:
        rt = re.sub(r"\s+", "", r["text"])
        caps = [c for it, c in items if len(min(it, rt, key=len)) >= 2 and (it in rt or rt in it)]
        out.append(dict(r, cap=min(caps)) if caps else r)
    return out


def has_cue_props(props):
    """A beat whose board already times its register by `{"cue": ...}` props is synced by its author."""
    def is_cue(v):
        return isinstance(v, dict) and "cue" in v
    for v in (props or {}).values():
        if is_cue(v) or (isinstance(v, list) and any(isinstance(x, dict) and is_cue(x.get("at")) for x in v)):
            return True
    return False


def warp_key(scene, film_props_rest, words, code):
    """What a beat's derived warp depends on: the beat as the Film receives it (less its warp), the film-level
    props, the voice's word times and the renderer's code. Any change re-derives it."""
    sc = {k: v for k, v in scene.items() if k != "warp"}      # the warp is the OUTPUT: never part of its own key
    # ...and THIS FILE is part of it: a change to how text is matched or a warp is chosen re-derives every beat,
    # instead of leaving warps a previous rule chose looking fresh.
    with open(os.path.abspath(__file__), "rb") as fh:
        rules = hashlib.sha256(fh.read()).hexdigest()
    blob = json.dumps({"scene": sc, "film": film_props_rest, "words": words, "code": code, "rules": rules},
                      sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


SIDECAR = "sync_warp.json"
FPS = 30


def _sync_setting(meta, slide):
    """'off', an authored anchor list, or None (derive) — meta.sync / slide.sync. Anything else is refused."""
    for where, v in (("slide #%s" % slide.get("index"), slide.get("sync")), ("meta", (meta or {}).get("sync"))):
        if v is None or v == "auto":
            continue
        if v in ("off", False):
            return "off"
        if where != "meta" and isinstance(v, dict) and isinstance(v.get("anchors"), list):
            return v["anchors"]
        raise RuntimeError("%s `sync` must be \"off\", \"auto\" or {\"anchors\": [[voice_s, register_s], ...]} "
                           "(meta: \"off\"/\"auto\" only), not %r" % (where, v))
    return None


def authored_warp(anchors, dur_frames, seam, fps=FPS):
    """Knots for a storyboard's `sync.anchors` — [[voice second, register second], ...]: at the moment the voice
    reaches `voice second` the register should be at its own `register second`. The held edges are added, and
    the result must pass check_knots: an authored warp outside the slope limits is refused, never clamped."""
    D = max(1, int(dur_frames))
    pad = _pad(D, seam)
    try:
        mid = sorted([float(a) * fps, float(b) * fps] for a, b in anchors)
    except (TypeError, ValueError):
        raise RuntimeError("sync.anchors must be [[voice_s, register_s], ...] numbers, not %r" % (anchors,))
    knots = [[float(pad), float(pad)]] + mid + [[float(D - 1 - pad), float(D - 1 - pad)]]
    probs = check_knots(knots, D)
    if probs:
        raise RuntimeError("sync.anchors: " + "; ".join(probs))
    return [[round(f, 3), round(g, 3)] for f, g in knots]


def _film_rest(props):
    return {k: v for k, v in props.items() if k not in ("scenes", "typeGlide", "textSafe")}


def _load_sidecar(out_dir):
    try:
        with open(os.path.join(out_dir, SIDECAR), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) and isinstance(data.get("beats"), dict) else {"beats": {}}
    except (OSError, ValueError):
        return {"beats": {}}


def plan_warps(out_dir, data, props, slides):
    """[(status, warp, why)] per scene. status: 'off' | 'authored' | 'exempt' | 'derived' | 'identity' |
    'needed' (eligible, but no fresh derivation on disk). Pure apart from reading the sidecar and hashing the
    renderer's code (only when a sidecar exists to compare with)."""
    import remotion_segments as _rs
    meta = (data or {}).get("meta") or {}
    seam = _rs.seam_frames()
    side = _load_sidecar(out_dir)
    code = None
    out = []
    for k, (sc, sl) in enumerate(zip(props["scenes"], slides)):
        setting = _sync_setting(meta, sl)
        if setting == "off":
            out.append(("off", None, "sync: off on the board"))
            continue
        if isinstance(setting, list):
            out.append(("authored", authored_warp(setting, sc["durF"], seam), "sync.anchors on the board"))
            continue
        why = register_exempt(sc["shot"], out_dir) or (
            "its board times it by {\"cue\": ...} props" if has_cue_props(sl.get("shot_props")) else None)
        if why:
            out.append(("exempt", None, why))
            continue
        entry = side["beats"].get(str(sl.get("index", k + 1)))
        if entry:
            if code is None:
                code = _rs.code_hash(out_dir)
            key = warp_key(sc, _film_rest(props), words_for(out_dir, sl), code)
            if entry.get("key") == key:
                w = entry.get("warp") or None
                out.append(("derived" if w else "identity", w, "; ".join(entry.get("notes") or [])))
                continue
        out.append(("needed", None, "no derivation for this beat as it is now"))
    return out


def attach_warps(out_dir, data, props, slides):
    """Give each scene the warp plan_warps finds for it (in place on a copy of the scene list); returns the plan."""
    plan = plan_warps(out_dir, data, props, slides)
    scenes = []
    for sc, (_st, w, _why) in zip(props["scenes"], plan):
        sc = {k: v for k, v in sc.items() if k != "warp"}
        if w:
            sc["warp"] = w
        scenes.append(sc)
    props["scenes"] = scenes
    return plan


def derive_warps(out_dir, data, props, slides, log=print):
    """Measure the film on its registers' own clocks, derive every eligible beat's warp, write the sidecar and
    attach the result. Returns the plan after attaching. One census of the film (~30 s for a minute of film)."""
    import remotion_segments as _rs
    import text_safe_qa as _tsq
    plan = plan_warps(out_dir, data, props, slides)
    if not any(st == "needed" for st, _w, _why in plan):
        return attach_warps(out_dir, data, props, slides)
    raw = dict(props, scenes=[{k: v for k, v in sc.items() if k != "warp"} for sc in props["scenes"]])
    try:
        rep = _tsq.scan_film_sync(out_dir, raw=True, props=raw, slides=slides)
        why = "; ".join(rep["unmeasured"])
    except Exception as e:                      # noqa: BLE001 — a measurement that failed must not stop the render
        rep, why = None, "%s: %s" % (type(e).__name__, str(e).splitlines()[0][:200] if str(e) else "")
    if why:
        # LOUD, and not fatal: the film renders on its registers' own clocks and `text_safe_qa --sync` reports
        # whatever is then late — a warp that could not be measured is never guessed
        log("[sync] the census could not measure the film (%s) — rendering on the registers' own clocks" % why)
        return attach_warps(out_dir, data, props, slides)
    seam = _rs.seam_frames()
    code = _rs.code_hash(out_dir)
    side = _load_sidecar(out_dir)
    for k, ((st, _w, _why), sc, sl) in enumerate(zip(plan, raw["scenes"], slides)):
        if st != "needed":
            continue
        recs = cap_records(rep["by_k"][k], sc)
        warp, notes = derive_warp(recs, sc["durF"], FPS, seam)
        side["beats"][str(sl.get("index", k + 1))] = {
            "key": warp_key(sc, _film_rest(props), words_for(out_dir, sl), code), "warp": warp, "notes": notes,
            "measured": [{x: r[x] for x in ("text", "said", "spoken", "appear", "lag")} for r in recs]}
    side["version"] = 1
    with open(os.path.join(out_dir, SIDECAR), "w", encoding="utf-8") as fh:
        json.dump(side, fh, ensure_ascii=False, indent=1)
    plan = attach_warps(out_dir, data, props, slides)
    for (st, w, why), sl in zip(plan, slides):
        if st == "derived":
            moved = max(abs(f - g) for f, g in w) / FPS
            log("[sync] scene %s: register clock warped onto its voice (%d anchor(s), moves up to %.1fs)%s"
                % (sl.get("index"), sum(1 for f, g in w if abs(f - g) >= 0.5), moved, (" — " + why) if why else ""))
        elif st in ("exempt", "off"):
            log("[sync] scene %s: not warped — %s" % (sl.get("index"), why))
    return plan


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__.strip().splitlines()[2].strip())
        return 2
    out_dir = os.path.abspath(argv[0])
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    renderer = str((board.get("meta") or {}).get("renderer", "")).lower()
    rest = argv[1:]
    if renderer.startswith("remotion"):
        import text_safe_qa as _tsq
        return _tsq.main([out_dir, "--sync"] + rest)
    import keyframe_qa as _kq                 # the html tier runs the audit inside its keyframe sweep
    return _kq.run(out_dir, as_json="--json" in rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
