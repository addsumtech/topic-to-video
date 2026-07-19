"""Resolve per-point reveal cue times from TTS word timings. PURE (no I/O) so it unit-tests without
edge-tts. Each point's anchor phrase is matched against the spoken word stream left-to-right and
monotonically; unmatched anchors are interpolated between resolved neighbors. Result is always the
same length as `anchors` and monotonic non-decreasing."""
import re

EPS = 0.15  # seconds — minimum gap nudge when two anchors resolve to the same/earlier time

# CJK ranges (ideographs, kana, hangul, fullwidth) — such text has NO word gaps, so a word-boundary
# match would never fire between two CJK chars; those anchors match as plain substrings instead.
_CJK = re.compile("[\u3000-\u30ff\u3400-\u9fff\uac00-\ud7a3\uf900-\ufaff\uff00-\uffef]")   # incl. compat ideographs (matches render._HAN)

def _anchor_pos(narration, anchor, start=0):
    """Char offset of `anchor` in `narration` at/after `start`, else -1. CASE-INSENSITIVE, and for a
    Latin anchor it requires WHOLE-WORD boundaries (so "art" doesn't match inside "start", "AI" not
    inside "brain"). CJK anchors match as a plain substring (no word gaps). This mirrors resolve_cues'
    casefold/whole-token matching so the text estimate and validate agree with the edge word-resolver."""
    a = (anchor or "").strip()
    if not a:
        return -1
    if _CJK.search(a):
        m = re.compile(re.escape(a), re.IGNORECASE).search(narration, start)
    else:
        m = re.compile(r"\b" + re.escape(a) + r"\b", re.IGNORECASE).search(narration, start)
    return m.start() if m else -1

def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").casefold()).strip()

_STOP = {"a","an","the","and","or","of","to","in","on","for","with","your","you","this","that","from","is","are","it","its"}

def _find(words, phrase, start):
    """First index >= start whose word/cue text matches the anchor; -1 if none. LATIN: whole-token match
    on the first SIGNIFICANT token. CJK: substring-match the anchor against the JOINED word stream — CJK
    text has no word gaps, so a multi-char anchor (扩散模型 = edge words 扩散+模型) never equals a single
    word; `_norm` would strip every CJK char to '' and match nothing (reveals silently fell back to an
    even spread). This mirrors `_anchor_pos` so the edge word-resolver agrees with the text estimator."""
    a = (phrase or "").strip()
    if not a:
        return -1
    if _CJK.search(a):
        owner, chars = [], []
        for i in range(start, len(words)):
            for ch in str(words[i].get("w", "")):
                chars.append(ch); owner.append(i)
        s = "".join(chars).casefold()
        key = re.sub(r"\s+", "", a).casefold()          # CJK anchors carry no spaces
        pos = s.find(key)
        return owner[pos] if 0 <= pos < len(owner) else -1
    toks = _norm(a).split()
    if not toks:
        return -1
    key = next((t for t in toks if t not in _STOP), toks[0])
    for i in range(start, len(words)):
        wn = _norm(words[i].get("w", ""))
        if wn == key or key in wn.split():
            return i
    return -1

def resolve_cues(words, anchors):
    n = len(anchors)
    if n == 0:
        return []
    last = float(words[-1].get("t", n)) if words else float(n)
    raw = [None] * n
    cur = 0
    for i, a in enumerate(anchors):
        idx = _find(words, a, cur)
        if idx >= 0:
            raw[i] = float(words[idx].get("t", 0.0))
            cur = idx + 1
    known = [i for i in range(n) if raw[i] is not None]
    res = [0.0] * n
    if not known:                                   # nothing matched -> even spread over [0, last]
        span = last if last > 0 else float(n)
        res = [span * (i + 1) / (n + 1) for i in range(n)]
    else:
        for i in range(known[0]):                        # leading unknowns -> 0..first
            res[i] = round(raw[known[0]] * (i + 1) / (known[0] + 1), 3)
        res[known[0]] = raw[known[0]]
        for a, b in zip(known, known[1:]):               # interior gaps -> linear interpolate
            res[b] = raw[b]
            for m in range(a + 1, b):
                res[m] = round(raw[a] + (raw[b] - raw[a]) * (m - a) / (b - a), 3)
        for i in range(known[-1] + 1, n):                # trailing unknowns -> after last known
            res[i] = round(raw[known[-1]] + EPS * (i - known[-1]), 3)
    for i in range(1, n):                            # enforce monotonic non-decreasing
        if res[i] <= res[i - 1]:
            res[i] = round(res[i - 1] + EPS, 3)
    return [round(float(x), 3) for x in res]


def _fill(raw, n, dur):
    """Fill None entries in `raw` (known reveal times) by interpolating between neighbours, then
    enforce monotonic non-decreasing within [0, dur]. Shared by both cue resolvers."""
    known = [i for i in range(n) if raw[i] is not None]
    res = [0.0] * n
    if not known:
        return [round(dur * (i + 1) / (n + 1), 3) for i in range(n)]   # even spread
    for i in range(known[0]):                                          # leading unknowns
        res[i] = round(raw[known[0]] * (i + 1) / (known[0] + 1), 3)
    res[known[0]] = round(raw[known[0]], 3)
    for a, b in zip(known, known[1:]):                                 # interior gaps
        res[b] = round(raw[b], 3)
        for m in range(a + 1, b):
            res[m] = round(raw[a] + (raw[b] - raw[a]) * (m - a) / (b - a), 3)
    for i in range(known[-1] + 1, n):                                  # trailing unknowns
        res[i] = round(min(dur, raw[known[-1]] + EPS * (i - known[-1])), 3)
    for i in range(1, n):
        if res[i] <= res[i - 1]:
            res[i] = round(res[i - 1] + EPS, 3)
    return [round(float(x), 3) for x in res]


def estimate_cues_from_text(anchors, narration, duration):
    """Approximate reveal times WITHOUT per-word timings (e.g. MiniMax/say/openai voices): place each
    anchor at (its char offset in the narration / total length) * duration, assuming a ~uniform
    speaking rate. Far better than a blind linear stagger — reveals track the narration's own pacing.
    Monotonic left-to-right scan (an anchor found only earlier than the cursor is still accepted so a
    later point can't jump ahead of it); unmatched anchors interpolate. Pure; same length as anchors."""
    n = len(anchors)
    if n == 0:
        return []
    N = narration or ""
    dur = float(duration) if duration and duration > 0 else float(n)
    # SPEAKING-TIME weighted offsets: a CJK char takes ~3x a Latin char (~5 chars/s vs ~15), so a
    # uniform per-char position skews estimates by seconds in mixed-script narration.
    w = [3 if _CJK.match(ch) else 1 for ch in N]
    pref = [0]
    for x in w:
        pref.append(pref[-1] + x)
    L = pref[-1]
    raw = [None] * n
    cur = 0
    for i, a in enumerate(anchors):
        a = (a or "").strip()
        pos = _anchor_pos(N, a, cur)
        if pos < 0 and a:
            pos = _anchor_pos(N, a)                   # out of order — accept anywhere
        if pos >= 0:
            raw[i] = (pref[pos] / L) * dur if L else 0.0
            cur = max(cur, pos + len(a))
    return _fill(raw, n, dur)
