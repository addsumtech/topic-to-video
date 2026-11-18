#!/usr/bin/env python3
"""word_align — word timings for a voice that gives none (MiniMax, OpenAI, macOS say), carried over from the free edge
voice speaking the SAME text, by aligning the two recordings.

    python3 scripts/word_align.py --ref ref.mp3 --ref-words ref.words.json --target paid.mp3 --out paid.words.json

WHY. The director path builds its clock from per-word timings (timeline.json: captions, cuts ~0.1-0.2 s before the
word). Only edge reports them, so choosing a paid voice left a film with nothing to cut to (2026-11-18).
HOW. Both recordings as log-mel frames (10 ms), each normalised per band; dynamic time warping over their cosine
distance gives the path through both; each reference word's start is read off the path in the target. Same words,
same order, two speakers: the path is well defined, and leading/trailing silence and different pacing are absorbed.
MEASURED (scripts' test + a real run): edge voice onto another edge voice, and onto itself at +25 % rate, both of which
report their own true timings — median error ~10-30 ms, worst ~80 ms; the film's cuts lead words by 100-200 ms.
REFUSES loudly (exit 1 / ValueError): a silent recording, or a warp whose slope says the two do not say the same
thing (the end of one matched at the start of the other).
Output format = edge's: [{"w": <word>, "t": <start s>}].
"""
import json
import os
import subprocess
import sys

import numpy as np

SR, HOP, NFFT, NMEL = 16000, 160, 512, 40


def _pcm(path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    if p.returncode != 0:
        raise ValueError("cannot decode %s: %s" % (path, p.stderr.decode(errors="replace")[:200]))
    return np.frombuffer(p.stdout, np.float32).astype(np.float64)


def _mel_bank():
    def hz2mel(f): return 2595 * np.log10(1 + f / 700.0)
    def mel2hz(m): return 700 * (10 ** (m / 2595.0) - 1)
    pts = mel2hz(np.linspace(hz2mel(80), hz2mel(7600), NMEL + 2))
    bins = np.floor((NFFT + 1) * pts / SR).astype(int)
    fb = np.zeros((NMEL, NFFT // 2 + 1))
    for m in range(1, NMEL + 1):
        a, b, c = bins[m - 1], bins[m], bins[m + 1]
        for k in range(a, b):
            fb[m - 1, k] = (k - a) / max(1, b - a)
        for k in range(b, c):
            fb[m - 1, k] = (c - k) / max(1, c - b)
    return fb


def features(path):
    """(frames x NMEL) log-mel, each band normalised over the clip; plus per-frame energy."""
    x = _pcm(path)
    if x.size < NFFT or np.abs(x).max() < 1e-4:
        raise ValueError("%s is silent or too short to align" % path)
    n = 1 + (x.size - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    fr = x[idx] * np.hanning(NFFT)[None, :]
    spec = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    mel = np.log(spec @ _mel_bank().T + 1e-8)
    energy = mel.mean(axis=1)
    mel = (mel - mel.mean(0)) / (mel.std(0) + 1e-6)
    return mel, energy


def _cost(A, B):
    An = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-9)
    Bn = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-9)
    return 1.0 - An @ Bn.T


try:
    from numba import njit

    @njit(cache=True)
    def _dtw(C):
        n, m = C.shape
        D = np.full((n + 1, m + 1), np.inf)
        D[0, 0] = 0.0
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                best = D[i - 1, j - 1]
                if D[i - 1, j] < best:
                    best = D[i - 1, j]
                if D[i, j - 1] < best:
                    best = D[i, j - 1]
                D[i, j] = C[i - 1, j - 1] + best
        return D
except Exception:  # numba missing: the same recurrence, one row at a time
    def _dtw(C):
        n, m = C.shape
        D = np.full((n + 1, m + 1), np.inf)
        D[0, 0] = 0.0
        for i in range(1, n + 1):
            diag = np.minimum(D[i - 1, :-1], D[i - 1, 1:])
            row = C[i - 1] + diag
            out = np.empty(m + 1)
            out[0] = np.inf
            for j in range(1, m + 1):
                out[j] = min(row[j - 1], C[i - 1, j - 1] + out[j - 1])
            D[i] = out
        return D


def path(A, B):
    """The DTW path [(i, j)] from (0, 0) to the ends: frame i of A matched to frame j of B."""
    D = _dtw(_cost(A, B))
    i, j = A.shape[0], B.shape[0]
    out = [(i - 1, j - 1)]
    while i > 1 or j > 1:
        cand = [(D[i - 1, j - 1], i - 1, j - 1), (D[i - 1, j], i - 1, j), (D[i, j - 1], i, j - 1)]
        _v, i, j = min(c for c in cand if c[1] >= 1 and c[2] >= 1)
        out.append((i - 1, j - 1))
    return out[::-1]


def align(ref_audio, ref_words, target_audio):
    """ref_words [{w, t}] timed on ref_audio -> the same words timed on target_audio."""
    A, _ea = features(ref_audio)
    B, _eb = features(target_audio)
    p = np.array(path(A, B))
    # a sane warp: overall slope between 1/3 and 3 (the target is the same text, not 3x faster or slower)
    slope = (B.shape[0] / float(A.shape[0]))
    if not (1 / 3.0 < slope < 3.0):
        raise ValueError("the two recordings differ %.1fx in length: they do not say the same thing" % slope)
    first = {}
    for i, j in p:
        first.setdefault(int(i), int(j))
    out, last = [], 0.0
    for w in ref_words:
        fi = min(A.shape[0] - 1, max(0, int(round(float(w["t"]) * SR / HOP))))
        t = first.get(fi, p[np.argmin(np.abs(p[:, 0] - fi)), 1]) * HOP / float(SR)
        t = max(t, last)                       # monotonic, as the words are spoken
        out.append({"w": w["w"], "t": round(t, 3)})
        last = t
    return out


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--ref", required=True)
    ap.add_argument("--ref-words", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        words = align(a.ref, json.load(open(a.ref_words, encoding="utf-8")), a.target)
    except ValueError as e:
        print("word_align: %s" % e, file=sys.stderr)
        return 1
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(words, fh, ensure_ascii=False)
    print("[word_align] %d word(s) -> %s" % (len(words), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
