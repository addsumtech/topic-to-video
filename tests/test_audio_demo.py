"""A film about a sound lets the viewer HEAR it (the ANC film had none): `slide.audio_demo` puts a clip after the
beat's voice and before the pause that ends it, at its own level; scripts/audio_demo.py synthesizes the cancellation
demo the scope draws — the noise, then the noise with its inverted copy a hair short and late."""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import _common  # noqa: E402
import audio_demo as ad  # noqa: E402
import tts  # noqa: E402


def _tone(path, seconds, hz=440, tail=0.0, rate=24000):
    t = np.arange(int(seconds * rate)) / rate
    x = (0.3 * np.sin(2 * np.pi * hz * t)).astype(np.float32)
    x = np.concatenate([x, np.zeros(int(tail * rate), np.float32)])
    raw = path + ".f32"
    x.tofile(raw)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", raw, path],
                   check=True)
    os.remove(raw)


def _rms(path, a, b, rate=24000):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ss", str(a), "-to", str(b), "-f", "f32le", "-ac", "1",
                          "-ar", str(rate), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.float32)
    return float(np.sqrt(np.mean(x * x))) if len(x) else 0.0


def test_the_cancellation_demo_is_the_noise_then_a_small_residual(tmp_path):
    out = str(tmp_path / "demo.wav")
    info = ad.synth_cancel(out, seconds=1.5, gap=0.3, gain=0.94, lag_ms=0.1)
    side = json.load(open(out + ".json"))
    assert side["kind"] == "synthesized" and side["switch_s"] == pytest.approx(1.8, abs=0.02)
    noise = _rms(out, 0.2, 1.3)
    residual = _rms(out, 2.0, 3.1)
    assert noise > 0.05 and residual < noise * 0.25, (noise, residual)     # quieter, never silent
    assert residual > noise * 0.02
    assert info["seconds"] == pytest.approx(3.3, abs=0.05)


def test_a_demo_is_put_after_the_voice_and_before_the_beats_pause(tmp_path):
    voice, demo = str(tmp_path / "v.wav"), str(tmp_path / "d.wav")
    _tone(voice, 1.0, tail=0.6)                               # 1 s of voice, then its 0.6 s pause
    _tone(demo, 2.0, hz=110)
    at = tts.append_demo(voice, demo, gap=0.25, gain_db=0.0)
    dur = _common.audio_duration(voice)
    assert at == pytest.approx(1.25, abs=0.06)                # the demo starts after the voice and the gap
    assert dur == pytest.approx(1.0 + 0.25 + 2.0 + 0.6, abs=0.08)   # ...and the beat still ends on its pause
    assert _rms(voice, at + 0.2, at + 1.8) > 0.05 and _rms(voice, dur - 0.5, dur - 0.05) < 0.01


def test_validate_refuses_a_demo_clip_that_is_missing_or_says_nothing_of_where_it_came_from(tmp_path):
    import validate as v
    (tmp_path / "audio_demo").mkdir()
    errs = v._audio_demo_problems([{"index": 6, "audio_demo": {"clip": "audio_demo/x.wav"}}], str(tmp_path))
    assert any("does not exist" in e for e in errs), errs
    (tmp_path / "audio_demo" / "x.wav").write_bytes(b"RIFF")
    errs = v._audio_demo_problems([{"index": 6, "audio_demo": {"clip": "audio_demo/x.wav"}}], str(tmp_path))
    assert any("sidecar" in e for e in errs), errs
    (tmp_path / "audio_demo" / "x.wav.json").write_text('{"kind": "synthesized"}')
    assert v._audio_demo_problems([{"index": 6, "audio_demo": {"clip": "audio_demo/x.wav"}}], str(tmp_path)) == []
