"""word_align: word starts carried from a timed reference onto an untimed recording of the same words, by aligning
the two; it refuses silence and two recordings that do not say the same thing."""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import word_align as wa  # noqa: E402

SR = 16000
# a "word" = a short chord with its own pitch pattern, so each one is distinguishable as speech sounds are
WORDS = [(220, 330), (440, 550), (300, 600), (500, 250), (350, 700), (260, 390), (620, 310), (410, 820)]


def _speak(path, durs, gaps, lead):
    """Write a clip: lead silence, then each word (duration d) followed by its gap. Returns the true word starts."""
    parts, t, starts = [np.zeros(int(lead * SR))], lead, []
    for (f1, f2), d, g in zip(WORDS, durs, gaps):
        n = int(d * SR)
        tt = np.arange(n) / SR
        sweep = np.sin(2 * np.pi * (f1 + (f2 - f1) * tt / d / 2) * tt) + 0.5 * np.sin(2 * np.pi * 2.01 * f1 * tt)
        parts.append(0.3 * sweep * np.hanning(n) ** 0.3)
        starts.append(t)
        t += d
        parts.append(np.zeros(int(g * SR)))
        t += g
    x = np.concatenate(parts).astype(np.float32)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", str(path)],
                   input=x.tobytes(), check=True)
    return starts


def test_word_starts_carry_over_to_a_differently_paced_recording(tmp_path):
    ref_starts = _speak(tmp_path / "ref.wav", [0.30] * 8, [0.08, 0.3, 0.08, 0.08, 0.4, 0.08, 0.08, 0.2], 0.10)
    # the "paid voice": slower words, other pauses, a longer lead-in
    tgt_starts = _speak(tmp_path / "tgt.wav", [0.42, 0.36, 0.40, 0.33, 0.45, 0.38, 0.40, 0.36],
                        [0.15, 0.12, 0.25, 0.05, 0.10, 0.3, 0.12, 0.2], 0.35)
    ref_words = [{"w": "w%d" % i, "t": t} for i, t in enumerate(ref_starts)]
    est = wa.align(str(tmp_path / "ref.wav"), ref_words, str(tmp_path / "tgt.wav"))
    err = np.abs(np.array([e["t"] for e in est]) - np.array(tgt_starts))
    assert [e["w"] for e in est] == [w["w"] for w in ref_words]
    assert all(b["t"] >= a["t"] for a, b in zip(est, est[1:])), "word starts must run forward"
    assert np.median(err) < 0.03 and err.max() < 0.08, err


def test_silence_and_unrelated_lengths_are_refused(tmp_path):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "1",
                    str(tmp_path / "silent.wav")], check=True)
    _speak(tmp_path / "ref.wav", [0.3] * 8, [0.08] * 8, 0.1)
    with pytest.raises(ValueError):
        wa.align(str(tmp_path / "ref.wav"), [{"w": "a", "t": 0.1}], str(tmp_path / "silent.wav"))
    _speak(tmp_path / "long.wav", [1.6] * 8, [0.5] * 8, 0.1)                 # 4x longer: not the same words
    with pytest.raises(ValueError):
        wa.align(str(tmp_path / "ref.wav"), [{"w": "a", "t": 0.1}], str(tmp_path / "long.wav"))
