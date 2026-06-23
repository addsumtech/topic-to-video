"""Resolve per-point reveal cue times from TTS word timings. PURE (no I/O) so it unit-tests without
edge-tts. Each point's anchor phrase is matched against the spoken word stream left-to-right and
monotonically; unmatched anchors are interpolated between resolved neighbors. Result is always the
same length as `anchors` and monotonic non-decreasing."""
import re

EPS = 0.15  # seconds — minimum gap nudge when two anchors resolve to the same/earlier time

def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").casefold()).strip()

def _find(words, phrase, start):
    """First index >= start whose (normalized) word/cue text contains the anchor's first token; -1 none."""
    toks = _norm(phrase).split()
    if not toks:
        return -1
    key = toks[0]
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
        return [round(last * (i + 1) / (n + 1), 3) for i in range(n)]
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
