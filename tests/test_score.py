"""The generated score (scripts/score.py). The pipeline cannot hear, so these are LISTEN-PROXIES: each can say the
bed is wrong (off its grid, clipping, all sub-bass, a click for a crest, out of tune, the same every film), none can
say it is good. A human listens before delivery."""
import math

import numpy as np
import pytest

import beatgrid as bg
import score

TEMPOS = [(100.0, 0.0, 1), (112.5, 0.37, 2), (108.0, 0.11, 3)]   # two frame-locked, one not (108 is 16.67 frames)


@pytest.fixture(scope="module")
def beds():
    out = {}
    for bpm, off, seed in TEMPOS:
        g = bg.BeatGrid(bpm, off)
        out[bpm] = (g, score.render(g, 26.0, climax_s=g.t(g.nearest_beat(15.0)), seed=seed * 1009))
    return out


@pytest.mark.parametrize("bpm", [t[0] for t in TEMPOS])
def test_the_bed_is_on_its_own_grid(beds, bpm):
    """The QA mix() runs on every score: re-detect the beats and hold them to the grid (< 10 ms median)."""
    g, s = beds[bpm]
    out = bg.verify_bed(s["bed"] + s["pulse"], s["sr"], g, log=lambda m: None)
    assert out["median_ms"] < bg.BED_LIMIT_MS and abs(out["bpm_detected"] / bpm - 1) < 0.005, out


@pytest.mark.parametrize("bpm", [t[0] for t in TEMPOS])
def test_the_listen_proxy(beds, bpm):
    """Ranges are CHOICES (U), set from the measured beds, wide enough to hold a different seed and tight enough to
    catch the failures seen while building it: 60% of the energy under 100 Hz (a bed a phone plays as nothing), an
    18-19 dB crest from pluck transients (the loudness pass is linear and peak-capped), and sum clipping."""
    g, s = beds[bpm]
    x = s["bed"] + s["pulse"]
    p = score.listen_proxy(x, s["sr"])
    assert p["clipped"] == 0 and p["peak_dbfs"] <= -0.99, p
    assert 10.0 <= p["crest_db"] <= 18.0, p
    b = p["bands"]
    assert b["sub<100"] < 0.5, b                                   # not all kick and bass
    assert b["mid400-2k"] >= 0.1, b                                # the pluck and pad are there to be heard
    assert b["presence2k-6k"] + b["air6k-16k"] >= 0.04, b          # the shaker / hat exist
    assert b["ultra>16k"] < 0.01, b                                # nothing aliasing near Nyquist
    # the stems keep their balance: the pulse sits ~5 LU under the bed
    lb, lp = score.lufs(s["bed"]), score.lufs(s["pulse"])
    assert 3.0 <= lb - lp <= 7.0, (lb, lp)


def test_the_score_is_deterministic_and_varies_by_seed():
    g = bg.BeatGrid(105.88235294117646, 0.2)
    a = score.render(g, 12.0, seed=7)
    b = score.render(g, 12.0, seed=7)
    assert np.array_equal(a["bed"], b["bed"]) and np.array_equal(a["pulse"], b["pulse"])
    keys = {score.render(g, 4.0, seed=s)["info"]["key"] for s in (1, 22, 333, 4444, 55555, 666666)}
    assert len(keys) >= 3, keys
    assert score.render(g, 4.0, seed=1, key="Eb")["info"]["key"] == "Eb"
    assert score.render(g, 4.0, seed=1, key="c minor")["info"]["key"] == "Cm"


def test_one_chord_per_bar_from_a_known_progression():
    for seed in range(12):
        pc, mode, prog, _ = score.choose(seed * 97)
        assert prog in score.PROGRESSIONS[mode]
        tri = score._triad(pc, mode, prog[0])
        # a diatonic triad of the key: every note in the key's scale
        scale = score.MAJOR if mode == "major" else score.MINOR
        assert all(((n - pc) % 12) in scale for n in tri)


def test_the_pluck_is_in_tune():
    """An integer Karplus-Strong delay is up to 44 cents off over the pluck's range at 48 kHz (computed); the
    fractional loop measured 0.13 cents worst — held here to 4."""
    rng = np.random.default_rng(0)
    for f in (293.66, 440.0, 659.26, 880.0):
        x = score.pluck(f, rng, vel=0.8, dur=1.0)[: score.SR]
        spec = np.abs(np.fft.rfft(x * np.hanning(len(x)), 8 * len(x)))
        fr = np.fft.rfftfreq(8 * len(x), 1.0 / score.SR)
        band = (fr > f * 0.9) & (fr < f * 1.1)
        f0 = fr[band][np.argmax(spec[band])]
        assert abs(1200 * math.log2(f0 / f)) < 4.0, (f, f0)


def test_the_payoff_opens_the_peak_and_the_riser_ends_on_it():
    g = bg.BeatGrid(120.0, 0.0)
    climax = g.t(32)                                               # bar 8's downbeat
    arr = score.arrangement(g, 30.0, climax)
    assert arr["landing_beat"] == 32 and arr["energy"][8] == 3 and arr["energy"][7] < 3
    assert arr["energy"][max(arr["energy"])] == 0, "the film ends on its outro bar"
    on = score.render(g, 30.0, climax_s=climax, riser_into_climax=True, seed=5)
    off = score.render(g, 30.0, climax_s=climax, riser_into_climax=False, seed=5)
    sr_ = score.SR
    pre = slice(int((climax - 0.9) * sr_), int((climax - 0.05) * sr_))
    hi = lambda x: float(np.sqrt(np.mean(np.diff(x[pre]) ** 2)))   # noqa: E731 — a crude high-band level
    assert hi(on["pulse"]) > 3 * hi(off["pulse"]), "the riser fills the two beats before the landing"
    assert on["info"]["riser"] and not off["info"]["riser"]


def test_stems_have_the_films_length_at_48k():
    g = bg.BeatGrid(94.73684210526316, 0.5)
    s = score.render(g, 7.3, seed=2)
    assert s["sr"] == 48000 and len(s["bed"]) == len(s["pulse"]) == int(round(7.3 * 48000))
    with pytest.raises(ValueError):
        score.render(g, 7.3, sr=44100)
