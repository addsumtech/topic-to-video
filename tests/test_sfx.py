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
    for name in ("click", "tick", "focus", "whoosh", "pop", "reveal", "riser", "impact", "sparkle"):
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
    names = [c[1] for c in cs]
    sentence = sum(names.count(n) for n in ("riser", "impact", "sparkle"))
    assert sentence == 3, "the closing sentence is never thinned by the cap"
    # the cap counts EVENTS: the three-part sentence is one landing and costs one slot
    assert len(cs) - sentence + 1 <= int(round((100.0 / 10.0) * 4)), \
        "must cap density (restraint: don't cue every beat)"


# ── the closing sentence: riser -> impact -> sparkle, pinned to the landing ─────────────────────────
def _film(n_scenes, last_dur=150):
    """The shape the real caller (render_remotion) sends: seams declared, the close's ONE shot at frame 0."""
    sc = [{"durationInFrames": 150, "transitionIn": None if i == 0 else {"type": "wipe"}} for i in range(n_scenes)]
    sc[-1]["durationInFrames"] = last_dur
    sc[-1]["shots"] = [{"startFrame": 0}]
    return sc


def test_closing_sentence_is_pinned_to_the_landing():
    cs = {n: t for t, n, g in sfx.plan_cues(_film(3), 30)}
    land = 2 * 150 / 30.0
    assert cs["impact"] == pytest.approx(land), "the impact IS the landing"
    assert cs["riser"] == pytest.approx(land - sfx.SENTENCE_RISER_LEAD / 30.0), "the build leads by 35f"
    assert cs["sparkle"] == pytest.approx(land + sfx.SENTENCE_SPARKLE_LAG / 30.0), "the glow follows by 25f"
    assert cs["riser"] < 2 * 150 / 30.0 < cs["impact"] + 1e-9, "the riser crosses the cut into the close"


def test_no_bell_closes_the_film():
    names = [c[1] for c in sfx.plan_cues(_film(3), 30)]
    assert "reveal" not in names, "a bell is a game sound (their case law) — the close lands on an impact"


def test_impact_on_the_seam_replaces_that_seam_whoosh():
    cs = sfx.plan_cues(_film(3), 30)
    seam2 = 2 * 150 / 30.0
    whooshes = [t for t, n, g in cs if n == "whoosh"]
    assert any(abs(t - (150 / 30.0 - 2 / 30.0)) < 1e-6 for t in whooshes), "the interior seam keeps its whoosh"
    assert not any(abs(t - (seam2 - 2 / 30.0)) < 1e-6 for t in whooshes), \
        "the seam the impact lands on is voiced by the riser, not a whoosh two frames before the hit"


def test_impact_is_the_loudest_cue():
    gains = {n: g for t, n, g in sfx.plan_cues(_film(3), 30)}
    assert gains["impact"] == max(gains.values()), "the impact is the film's loudness peak"


def test_sparkle_pulls_in_or_drops_when_the_film_ends_early(capsys):
    cs = {n: t for t, n, g in sfx.plan_cues(_film(3, last_dur=30), 30)}     # 1.0s of film after the landing
    assert "sparkle" in cs and cs["sparkle"] < cs["impact"] + sfx.SENTENCE_SPARKLE_LAG / 30.0 and \
        cs["sparkle"] <= 11.0 - sfx.SPARKLE_MIN_TAIL_S + 1e-9, "pulled in so it can ring"
    cs = {n: t for t, n, g in sfx.plan_cues(_film(3, last_dur=6), 30)}      # 0.2s: no room at all
    assert "sparkle" not in cs and "impact" in cs, "dropped, the sentence keeps its verb"
    assert "sparkle dropped" in capsys.readouterr().out, "and it says so"


def test_sentence_cues_are_deterministic():
    for n in ("riser", "impact", "sparkle"):
        assert np.array_equal(sfx.cue(n), sfx.cue(n))


def test_the_low_bus_carries_the_impact_body_and_stays_out_of_the_voice_band(tmp_path):
    """The SFX bus is highpassed at 800Hz; an impact's body is a 35-60Hz thump. Measured through the REAL graph:
    the two-band graph keeps the body and adds nothing to the 300Hz-3kHz voice band."""
    import subprocess, shutil
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("ffmpeg")
    d = str(tmp_path)
    total = 3.0
    sfx.build_sfx_track([(1.0, "impact", 0.95)], total, d + "/s.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x36:r=30", "-f", "lavfi",
                    "-i", "anullsrc=r=48000:cl=stereo", "-t", str(total), "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", d + "/base.mp4"], check=True)

    def run(graph, out):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", d + "/base.mp4", "-i", d + "/s.wav", "-filter_complex",
                        graph, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "pcm_s16le", out], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", out, "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le",
                        out + ".f32"], check=True)
        return np.fromfile(out + ".f32", dtype=np.float32)

    def band(x, lo, hi):
        X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / 48000.0)
        m = (f >= lo) & (f < hi)
        return float(np.sqrt(np.mean(np.abs(X[m]) ** 2)))

    # Measured BEFORE loudnorm: that stage is one global gain over the whole mix, so a louder impact (the
    # body is back) turns the entire film down a little and would read as the voice band "changing". The
    # split and its buses are the thing under test; loudnorm is the same stage in both graphs.
    import re
    strip = lambda g: re.sub(r",loudnorm=[^\[]*", "", g)
    one_band = "[1:a]highpass=f=800,volume=1.0[sfx];[0:a][sfx]amix=inputs=2:duration=first:normalize=0[a]"
    assert "loudnorm" not in strip(sfx.filtergraph(total, False)) and "asplit" in strip(sfx.filtergraph(total, False))
    a = run(one_band, d + "/one.mov")[48000:int(1.45 * 48000)]
    b = run(strip(sfx.filtergraph(total, False)), d + "/two.mov")[48000:int(1.45 * 48000)]
    assert band(b, 20, 110) > 20 * band(a, 20, 110), "the body survives the chain (it did not before)"
    assert abs(band(b, 300, 3000) - band(a, 300, 3000)) < 0.05 * band(a, 300, 3000), \
        "the low bus adds nothing to the voice band"


def test_a_scored_film_ships_a_no_bgm_twin(tmp_path):
    import subprocess, shutil
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("ffmpeg")
    d = str(tmp_path); mp4 = d + "/out.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x36:r=30", "-f", "lavfi",
                    "-i", "anullsrc=r=48000:cl=stereo", "-t", "4", "-c:v", "libx264", "-c:a", "aac", "-shortest",
                    mp4], check=True)
    scenes = [{"durationInFrames": 60, "transitionIn": None}, {"durationInFrames": 60, "transitionIn": {"type": "wipe"},
                                                                "shots": [{"startFrame": 0}]}]
    assert sfx.mix(d, mp4, scenes, {"sound_design": True, "bgm": "auto"}, 30)
    assert os.path.exists(d + "/out.nobgm.mp4"), "same cues, same frames, no music"


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
