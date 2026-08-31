"""Sound-design backstops (#8): the two-track SFX(+BGM) layer. SFX are synthesized locally (deterministic
numpy — no API, no external assets); cues pin to beats with restraint; the mix uses huashu's frequency
isolation (SFX highpass 800 / BGM lowpass 4k / amix normalize=0) and is OPT-IN (meta.sound_design). The mix
itself is proven by a real render (peak -2.2dB, no clip); audio QUALITY must be auditioned by a human."""
import inspect
import os
import shutil
import wave

import numpy as np
import pytest
import sfx

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


def _scenes(n, dur_frames=150):
    return [{"durationInFrames": dur_frames,
             "shots": [{"startFrame": 0}, {"startFrame": 40}, {"startFrame": 90}],
             "stage": {"elements": [{"kind": "panel", "enterAtFrame": 40}]}} for _ in range(n)]


# ── synthesized cues (deterministic, in-range) ──────────────────────────────────────────────────────
def test_cues_synthesize_in_range():
    for name in ("click", "tick", "focus", "whoosh", "pop", "reveal"):
        c = sfx.cue(name)
        assert c is not None and len(c) > 0 and float(np.max(np.abs(c))) <= 1.0, "cue %s bad" % name


def test_cue_is_deterministic():
    assert np.array_equal(sfx.cue("whoosh"), sfx.cue("whoosh")), "synthesis must be deterministic (no RNG drift)"


def test_synth_pad_length_and_range():
    p = sfx.synth_pad(2)
    assert len(p) == 2 * sfx.SR and float(np.max(np.abs(p))) <= 1.0


# ── cue planning (beats + restraint) ────────────────────────────────────────────────────────────────
def test_plan_cues_marks_transitions_and_arrivals():
    names = [c[1] for c in sfx.plan_cues(_scenes(2), 30)]
    assert "whoosh" in names, "a scene transition gets a whoosh"
    assert "focus" in names, "an interior shot arrival gets a focus tick"


def test_plan_cues_respects_density_cap():
    cs = sfx.plan_cues(_scenes(20), 30)                 # 20 x 5s = 100s -> cap ~40
    assert len(cs) <= int(round((100.0 / 10.0) * 4)), "must cap density (restraint: don't cue every beat)"


def test_plan_cues_sorted_by_time():
    cs = sfx.plan_cues(_scenes(3), 30)
    assert cs == sorted(cs, key=lambda c: c[0]), "cues are time-ordered for placement"


def test_build_sfx_track_writes_wav(tmp_path):
    w = str(tmp_path / "s.wav")
    assert sfx.build_sfx_track([(0.5, "click", 0.5), (1.0, "reveal", 0.7)], 3.0, w)
    with wave.open(w) as f:
        assert f.getframerate() == sfx.SR and f.getnframes() > 0


# ── mix contract (frequency isolation + opt-in) ─────────────────────────────────────────────────────
def test_mix_uses_frequency_isolation_and_no_normalize():
    src = _src("scripts", "sfx.py")
    assert "_SFX_HP = 800" in src and "_BGM_LP = 4000" in src, "huashu freq bands"
    assert "highpass=f=%d" in src and "lowpass=f=%d" in src, "SFX highpassed, BGM lowpassed"
    assert "normalize=0" in src and "loudnorm=I=" in src, "amix normalize=0 (keep dynamics) + loudnorm"


def test_sound_design_is_opt_in():
    src = _src("scripts", "render_remotion.py")
    assert 'meta.get("sound_design")' in src and "sfx.mix" in src, "the mix runs only when meta.sound_design is set"


def test_the_audio_chain_does_not_move_a_cue_off_its_frame():
    """Cues are planned FRAME-exactly and then handed to an encoder nobody had ever measured.

    A seam whoosh is placed 2 frames early on purpose; a chain that holds sound back by a frame and a half
    silently turns that anticipation into a late hit, and the only audio gate in the pipeline (`check_av`)
    compares TOTAL STREAM DURATIONS with a 0.3s tolerance — nine frames at 30fps, and blind to where a cue
    sits relative to the cut it punctuates either way.

    The obvious fix was to copy the reference implementation's compensation constant (it measured its own
    encoder holding a click back 2032 samples, ~1.27 frames). Measured HERE the chain moves a sound by
    exactly zero: ffmpeg signals the AAC priming and the decoder skips it, and loudnorm adds no net delay.
    Subtracting a borrowed 1.27 frames would have INTRODUCED the error. So the number is measured, not
    assumed — and this is the gate that notices when it stops being zero.
    """
    if sfx.np is None or not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("needs numpy + ffmpeg + ffprobe to send a click through the real chain")
    for has_bgm in (False, True):
        off = sfx.measure_offset(30, has_bgm=has_bgm)
        assert off is not None, "the chain could not be measured (bgm=%s)" % has_bgm
        assert abs(off) * 30 < 0.5, (
            "the audio chain moves a cue by %+.3f frames (bgm=%s) — a cue planned to the frame does not "
            "land on it" % (off * 30, has_bgm))


def test_the_probe_measures_the_chain_the_film_actually_uses():
    """A probe with its own copy of the filtergraph certifies a chain nothing renders through.

    That is the same shape as every other duplicated definition this repo has paid for, and here it would be
    invisible: the probe would report a clean zero forever while `mix()` grew a filter that delays the sound.
    """
    src = inspect.getsource(sfx)
    assert src.count("amix=inputs=") == 1, "the mix graph is written more than once"
    assert "filtergraph(dur, bool(bgm_wav))" in src, "mix() no longer renders through the shared graph"
    assert "filtergraph(PROBE_SECONDS, has_bgm)" in src, "the probe no longer measures the shared graph"
    # and the offset must actually be SUBTRACTED, not merely printed
    assert "t - lat" in src, "the measured offset is reported but never applied to the cue times"
