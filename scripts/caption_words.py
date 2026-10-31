#!/usr/bin/env python3
"""Where a burned caption may break a line or a chunk — the HTML tier's half of remotion/src/captionBreak.ts.

    python3 scripts/caption_words.py "一九九九年，黑尔斯证明了它。约三点八公斤蜂蜜。"     # the allowed breaks, shown

WHY. The HTML tier wrapped a Chinese caption between ANY two characters (render.py `_atoms`: every CJK character its
own unit) and hard-split an over-long clause every N characters, so a validation film (蜂巢, 2026-10-31) burned
「正方 / 形」 and 「四百 / 五十」; the Remotion tier breaks at Intl.Segmenter's word boundaries, and ICU cuts numbers —
the same film's sister burned 「负 / 四」. Neither tier had a rule for a number, and the HTML tier had no gate at all.

ONE DEFINITION, BOTH TIERS.
  words    Intl.Segmenter (ICU) — the segmenter the Remotion tier already draws with — run in plain node (no
           packages) for every text at once. No node: every CJK character is its own word (the old behaviour), the
           number rule still holds, and the fallback is said out loud (`backend()`, and validate/render print it).
  numbers  remotion/src/captionGlue.json, the file captionBreak.ts reads: prefix + numerals (a joiner between two)
           + a unit (and a second after 多/余/来/几). Nothing inside such a span is a break. tests/test_caption_words.py holds the two
           implementations to the same spans on one corpus.
  kinsoku  never before closing punctuation, never after opening punctuation (captionBreak.ts CLOSE / OPEN).
"""
import json
import os
import re
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
GLUE_JSON = os.path.join(_HERE, "..", "remotion", "src", "captionGlue.json")
_G = json.load(open(GLUE_JSON, encoding="utf-8"))
NUMERALS = set(_G["numerals"])
JOINERS = set(_G["joiners"])
PREFIX = sorted(_G["prefix"], key=len, reverse=True)
UNITS_CJK = sorted(set(_G["units_cjk"]), key=len, reverse=True)
UNITS_LATIN = sorted(set(_G["units_latin"]), key=len, reverse=True)
APPROX = set(_G["approximators"])

# the same sets as captionBreak.ts — closing punctuation never starts a line, opening never ends one
CLOSE = set("、。，．,.：:；;？?！!）)]｝}」』】〕〉》〗〙〛’”…‥〜～ー々〻ゝゞヽヾぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ・%％")
OPEN = set("（([｛{「『【〔〈《〖〘〚‘“")
_CJK = re.compile(r"[㐀-鿿豈-﫿぀-ヿ가-힯]")


def is_cjk(c):
    return bool(c) and bool(_CJK.match(c))


def _word_char(c):
    return bool(c) and (c.isalnum() or c in "_'’")


def glue_spans(text):
    """[(a, b)] — the NUMBER spans of `text` (captionGlue.json): no break may fall at any k with a < k < b."""
    t, n, out, i = text or "", len(text or ""), [], 0
    while i < n:
        if t[i] not in NUMERALS:
            i += 1
            continue
        # a numeral run: numerals, a joiner allowed only BETWEEN two numerals (3.8, 28,800, 三点八, 1:30)
        a, j = i, i + 1
        while j < n:
            if t[j] in NUMERALS:
                j += 1
            elif t[j] in JOINERS and j + 1 < n and t[j + 1] in NUMERALS and t[j - 1] in NUMERALS:
                j += 2
            else:
                break
        # the prefix that binds to it (负四, 第三, 百分之九十, ±0.5, $3)
        for p in PREFIX:
            if t[max(0, a - len(p)):a] == p:
                a -= len(p)
                break
        # a unit (四百五十克, 十分钟, 一億二千万人, 3.8 kg, 95%), and a second after an approximator (三十多岁)
        b = j
        for k in range(2):
            sp = 1 if k == 0 and b < n and t[b] == " " else 0
            hit = next((u for u in UNITS_CJK if t.startswith(u, b + sp)), None) or \
                next((u for u in UNITS_LATIN if t.startswith(u, b + sp)
                      and not _word_char(t[b + sp + len(u): b + sp + len(u) + 1])), None)
            if not hit:
                break
            b += sp + len(hit)
            if hit not in APPROX:                    # a second unit only after 多/余/来/几 (三十多岁)
                break
        if b - a >= 2:
            out.append((a, b))
        i = max(j, i + 1)
    return out


# ── words: ICU in plain node, every text at once ─────────────────────────────────────────────────────────────
_NODE_JS = r"""
const texts = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const S = Intl.Segmenter ? new Intl.Segmenter('zh', {granularity: 'word'}) : null;
process.stdout.write(JSON.stringify(S ? texts.map((t) => [...S.segment(t)].map((s) => s.index)) : null));
"""
_CACHE = {}
_BACKEND = {"name": None, "why": None}


def backend():
    """('icu', None) when word boundaries come from Intl.Segmenter, else ('per-character', why) — the fallback."""
    if _BACKEND["name"] is None:
        _starts_icu(["一"])
    return _BACKEND["name"], _BACKEND["why"]


def _starts_icu(texts):
    todo = [t for t in dict.fromkeys(texts) if t not in _CACHE]
    if todo and _BACKEND["name"] != "per-character":
        node = shutil.which("node")
        res = None
        if node:
            try:
                r = subprocess.run([node, "-e", _NODE_JS], input=json.dumps(todo), capture_output=True, text=True,
                                   timeout=60)
                res = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
            except (OSError, ValueError, subprocess.TimeoutExpired):
                res = None
        if res is None:
            _BACKEND.update(name="per-character", why=("node is not installed" if not node else
                                                       "node has no Intl.Segmenter (ICU)"))
            sys.stderr.write("[caption_words] WARNING: no word segmenter (%s) — captions break between any two CJK "
                             "characters except inside a number; install Node.js (>= 16) for word boundaries\n"
                             % _BACKEND["why"])
        else:
            _BACKEND.update(name="icu", why=None)
            for t, s in zip(todo, res):
                _CACHE[t] = set(s)
    return [_CACHE.get(t) for t in texts]


def prime(texts):
    """Segment every text in ONE node call (render/validate call this with a film's captions before drawing)."""
    _starts_icu([t for t in texts if t])


_HAN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")


FRAGMENT_CAP = 6     # a joined word is at most this many characters: past it ICU's boundary stands


def _join_fragments(text, starts):
    """ICU's word starts with its OUT-OF-VOCABULARY fragments joined back. ICU spells a run it has no dictionary word
    for one character at a time — 黑|尔|斯 (a name), 走|时, 擒|纵|叉, 正|多边|形, 一|口气 — and a break after such a
    character is a break inside a word. So a one-character Han segment joins the Han segment AFTER it (正+多边,
    一+口气, 黑+尔+斯), and one at a phrase end — before punctuation, a space or the end — joins the Han word BEFORE it
    (多边+形，). Kana particles (の, は) and numbers (glue_spans owns those) are left alone, and no joined word
    grows past FRAGMENT_CAP characters. The
    cost: a break after a one-character word moves before it (平面 / 的正多边形 rather than 平面的 / 正多边形) — never
    into a word. scripts/caption_words.py and captionBreak.ts apply the same rule (tests/test_caption_words.py)."""
    cuts = sorted({0, len(text)} | {k for k in starts if 0 < k < len(text)})
    segs = list(zip(cuts, cuts[1:]))
    out = set(cuts[1:-1])
    num = set()                              # characters inside a number span: glue_spans owns those
    for a, b in glue_spans(text):
        num.update(range(a, b))
    u0 = 0                                   # where the current (joined) word starts
    for i in range(1, len(segs)):
        (pa, pb), (a, b) = segs[i - 1], segs[i]
        if b - u0 <= FRAGMENT_CAP and _HAN.match(text[a]) and _HAN.match(text[pb - 1]) and a not in num:
            single_prev = pb - pa == 1 and pb - 1 not in num
            phrase_end = b - a == 1 and (b == len(text) or not (_HAN.match(text[b]) or text[b].isalnum()))
            if single_prev or phrase_end:
                out.discard(a)
                continue
        u0 = a
    return out


def word_starts(text, joined=True):
    """The offsets at which a word starts (k > 0). `joined` (the BREAKER's reading) joins ICU's one-character
    fragments (_join_fragments); the GATE asks with joined=False — ICU's own words — so a break after a real
    one-character word (的 / 东西) is never called a split, while one inside 正方形 or 负四 always is."""
    s = _starts_icu([text])[0]
    if s is not None and joined:
        s = _join_fragments(text, s)
    if s is None:
        # every zh/ja character its own word; Korean keeps its spaces as its only word boundaries
        tight = lambda c: is_cjk(c) and not ("\uac00" <= c <= "\ud7af")   # noqa: E731
        return {i for i in range(1, len(text)) if tight(text[i]) or tight(text[i - 1])}
    return {k for k in s if k > 0}


def break_points(text):
    """The offsets k (0 < k < len) where a line may break so that text[k] starts the next line: a word start or the
    word after a space, never inside a number span, never in front of closing / after opening punctuation, never
    inside a run with no space and no CJK (a Latin word, a URL)."""
    t = text or ""
    starts = word_starts(t) | {i for i in range(1, len(t)) if t[i - 1].isspace() and not t[i].isspace()}
    inside = set()
    for a, b in glue_spans(t):
        inside.update(range(a + 1, b))
    out = []
    for k in sorted(starts):
        if k <= 0 or k >= len(t):
            continue
        c, p = t[k], t[k - 1]
        if c.isspace() or k in inside or c in CLOSE or p in OPEN:
            continue
        if not is_cjk(c) and not is_cjk(p) and not p.isspace():
            continue
        out.append(k)
    return out


def atoms(text):
    """`text` cut at its break points: the units a greedy wrap may put on one line (render.py `_wrap`)."""
    t = text or ""
    cuts = [0] + break_points(t) + [len(t)]
    return [t[a:b] for a, b in zip(cuts, cuts[1:]) if t[a:b]]


def _cut_fault(text, e, k):
    """Why a break whose line before ends at `e` and whose line after starts at `k` (in `text`) is wrong, or None."""
    if any(a < e and k < b for a, b in glue_spans(text)):     # the number span runs on across the break
        return "number"
    if e == k and _BACKEND["name"] == "icu" and k not in word_starts(text, joined=False):
        return "split"
    return None


def boundary_fault(left, right):
    """Why a break between `left` and `right` (two consecutive lines or chunks of one caption) is wrong, or None:
    'kinsoku' (closing punctuation starts the line), 'number' (inside a number span), 'split' (inside a word). The
    two are re-joined as a caption is written (captionBreak.ts lineFaults): a space between two Latin ends, none at a
    CJK one — when the source text is at hand, line_faults(lines, source) judges it there instead."""
    l, r = (left or "").rstrip(), (right or "").lstrip()
    if not l or not r:
        return None
    if r[0] in CLOSE:
        return "kinsoku"
    sep = "" if (is_cjk(l[-1]) or is_cjk(r[0])) else " "
    joined = l + sep + r
    word_starts(joined)                                       # ensure the backend is known
    return _cut_fault(joined, len(l), len(l) + len(sep))


def line_faults(lines, source=None):
    """[(line index, kind, text)] for a caption drawn in `lines`: a break inside a number or a word, a line that
    starts with closing punctuation, or a last line of one CJK glyph. With `source` (the text the lines were cut
    from) each break is judged where it really falls, so a space the caption had (约 460 ppi) is not re-joined away."""
    out = []
    ls = [x.strip() for x in lines if x is not None]
    for i in range(1, len(ls)):
        if ls[i] and ls[i][0] in CLOSE:
            out.append((i, "kinsoku", ls[i]))
    pos, at = [], 0
    if source is not None:
        for s in ls:
            k = source.find(s, at)
            if k < 0:
                pos = []
                break
            pos.append((k, k + len(s)))
            at = k + len(s)
    if pos:
        word_starts(source)
        for i in range(1, len(ls)):
            f = _cut_fault(source, pos[i - 1][1], pos[i][0])
            if f:
                out.append((i, f, ls[i]))
    else:
        for i in range(1, len(ls)):
            f = boundary_fault(ls[i - 1], ls[i])
            if f and f != "kinsoku":
                out.append((i, f, ls[i]))
    if len(ls) > 1:
        core = [c for c in ls[-1] if c not in CLOSE and c not in OPEN and not c.isspace()]
        if len(core) == 1 and is_cjk(core[0]):
            out.append((len(ls) - 1, "orphan", ls[-1]))
    return sorted(out)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if argv else 2
    for text in argv:
        prime([text])
        name, why = backend()
        print("[caption_words] %s (%s)" % (text, name + (": " + why if why else "")))
        print("  breaks: " + " | ".join(atoms(text)))
        print("  numbers: " + ", ".join(text[a:b] for a, b in glue_spans(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
