"""mix.py: the music sits ~20 dB under the voice while it speaks, follows a swell in the score, rises between lines
(never above 6 dB under the voice), and the master lands near its loudness target."""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import mix  # noqa: E402

pytest.importorskip("scipy")


def _wav(path, x):
    mix._write(str(path), np.stack([x, x], axis=1))


def test_music_is_held_under_the_voice_and_rises_between_lines(tmp_path):
    sr, rng = mix.SR, np.random.default_rng(1)
    n = 12 * sr
    t = np.arange(n) / sr
    voice = np.zeros(n)
    lines = [(0.5, 3.0), (4.5, 7.0), (8.5, 11.0)]                      # three lines, 1.5 s pauses
    for a, b in lines:
        i, j = int(a * sr), int(b * sr)
        voice[i:j] = 0.1 * rng.standard_normal(j - i) * (0.6 + 0.4 * np.sin(2 * np.pi * 4 * t[i:j]) ** 2)
    music = 0.3 * np.sin(2 * np.pi * 220 * t) * np.where(t > 6, 2.0, 1.0)   # louder than the voice, and it swells
    _wav(tmp_path / "v.wav", voice)
    _wav(tmp_path / "m.wav", music)
    out = tmp_path / "mix.wav"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "mix.py"), "--voice", str(tmp_path / "v.wav"),
                        "--music", str(tmp_path / "m.wav"), "--out", str(out)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    rep = json.loads(r.stdout.splitlines()[0])
    assert rep["separation_p10"] >= 17 and rep["separation_median"] >= 19, rep
    assert abs(rep["lufs"] + 14) < 1.0 and rep["true_peak"] <= -2.0, rep
    # in the pause the music is up (louder than under the words), yet still at least 6 dB under the voice
    m = mix.load(str(out)).mean(axis=1)
    db = lambda a, b: 20 * np.log10(np.sqrt(np.mean(m[int(a * sr):int(b * sr)] ** 2)) + 1e-12)
    speaking = db(5.2, 6.8)                     # voice and music together while a line is spoken: mostly the voice
    pause = db(3.6, 4.2)                        # the music alone, between two lines
    assert pause < speaking - 6, (pause, speaking)
    mask, vdb = mix.speech_mask(mix.load(str(tmp_path / "v.wav")))
    g = mix.gains(mask, vdb, mix._rms_db(mix.load(str(tmp_path / "m.wav")), 2400), 20, 8)
    k = int(3.8 * sr / 2400)
    assert g[k] > np.median(g[mask]) + 3, "between lines the music comes up"


def test_a_short_separation_is_reported(tmp_path):
    sr = mix.SR
    t = np.arange(4 * sr) / sr
    _wav(tmp_path / "v.wav", 0.1 * np.random.default_rng(2).standard_normal(len(t)))
    _wav(tmp_path / "m.wav", 0.3 * np.sin(2 * np.pi * 220 * t))
    rep = mix.mix(str(tmp_path / "v.wav"), str(tmp_path / "m.wav"), None, str(tmp_path / "o.wav"), under=20)
    assert rep["separation_p10"] >= 17, rep
    sep = mix.separation(mix.load(str(tmp_path / "v.wav")), mix.load(str(tmp_path / "m.wav")), np.ones(len(t) // 2400, bool))
    assert np.median(sep) < 0, "unmixed, this music is louder than the voice: the measure says so"


def test_film_qc_mix_wants_the_measured_mix_when_there_is_music(tmp_path):
    sr = mix.SR
    t = np.arange(4 * sr) / sr
    a = tmp_path / "audio"; a.mkdir()
    run = lambda: subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "mix.py"), "--check", str(tmp_path)],
                                 capture_output=True, text=True, timeout=60)
    _wav(a / "voice.wav", 0.1 * np.random.default_rng(3).standard_normal(len(t)))
    r = run()
    assert r.returncode == 0 and "no music" in r.stdout, r.stdout          # a film without music: nothing to judge
    _wav(a / "score.wav", 0.3 * np.sin(2 * np.pi * 220 * t))
    _wav(a / "mix.wav", 0.1 * np.ones(len(t)))                              # a mix made by hand
    r = run()
    assert r.returncode == 1 and "not made by scripts/mix.py" in r.stdout, r.stdout
    m = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "mix.py"), "--voice", str(a / "voice.wav"),
                        "--music", str(a / "score.wav"), "--out", str(a / "mix.wav")], capture_output=True, text=True, timeout=120)
    assert m.returncode == 0, m.stdout + m.stderr
    r = run()
    assert r.returncode == 0 and "under the voice" in r.stdout, r.stdout
    with open(a / "mix.wav", "ab") as f:                                    # touched after it was measured
        f.write(b"\0\0\0\0")
    r = run()
    assert r.returncode == 1 and "changed after" in r.stdout, r.stdout


def _bandnoise(rng, n, lo, hi):
    from scipy.signal import butter, sosfiltfilt
    return sosfiltfilt(butter(4, [lo, hi], btype="band", fs=mix.SR, output="sos"), rng.standard_normal(n))


def test_the_music_is_held_under_the_voice_in_the_consonant_band_too(tmp_path):
    """A score loud in 1-4 kHz: broadband it sits under the voice, in the band it would not; the band duck lowers that
    band alone while the voice speaks (2026-11-25 bench: 14.3 -> 19.7 dB p10, the music overall -0.2 dB)."""
    sr, rng = mix.SR, np.random.default_rng(3)
    n = 10 * sr
    voice = np.zeros(n)
    for a, b in [(0.5, 4.0), (5.0, 9.0)]:
        i, j = int(a * sr), int(b * sr)
        voice[i:j] = 0.25 * _bandnoise(rng, j - i, 150, 600) + 0.03 * _bandnoise(rng, j - i, 1000, 4000)
    music = 0.2 * _bandnoise(rng, n, 60, 400) + 0.08 * _bandnoise(rng, n, 1000, 4000)
    _wav(tmp_path / "v.wav", voice); _wav(tmp_path / "m.wav", music)
    flat = mix.mix(str(tmp_path / "v.wav"), str(tmp_path / "m.wav"), None, str(tmp_path / "a.wav"), band_deep=0)
    duck = mix.mix(str(tmp_path / "v.wav"), str(tmp_path / "m.wav"), None, str(tmp_path / "b.wav"))
    assert flat["band_separation_p10"] < 15, flat
    assert duck["band_separation_p10"] >= 15, duck
    assert duck["band_separation_p10"] - flat["band_separation_p10"] >= 4, (flat, duck)
    # only the band moves: what the duck takes away has (almost) nothing below 500 Hz
    from scipy.signal import butter, sosfiltfilt
    v2, m2 = np.stack([voice, voice], 1), np.stack([music, music], 1)
    mask, _ = mix.speech_mask(v2)
    taken = m2 - mix.band_duck(v2, m2, mask, 20.0, 9.0)
    low = sosfiltfilt(butter(4, 500, btype="low", fs=sr, output="sos"), taken, axis=0)
    assert np.mean(taken ** 2) > 0 and np.mean(low ** 2) < 0.02 * np.mean(taken ** 2)


def test_the_master_lands_on_target_with_true_peak_held_on_a_peaky_mix(tmp_path):
    """loudnorm's linear second pass falls back to dynamic gain when the loudness target and the true-peak ceiling
    conflict (a ZH bench mix landed at -15.1 against -14); gain + an oversampled limiter lands on target."""
    sr, rng = mix.SR, np.random.default_rng(5)
    n = 8 * sr
    voice = 0.02 * rng.standard_normal(n)
    for k in range(1, 8):                                   # sharp hits near full scale over a quiet bed
        i = k * sr
        voice[i:i + 200] += 0.95 * np.hanning(200)
    _wav(tmp_path / "v.wav", voice)
    rep = mix.mix(str(tmp_path / "v.wav"), None, None, str(tmp_path / "o.wav"), lufs=-14.0, tp=-2.0)
    assert abs(rep["lufs"] + 14.0) <= 0.3, rep
    assert rep["true_peak"] <= -1.9, rep
