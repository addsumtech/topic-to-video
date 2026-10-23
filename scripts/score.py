#!/usr/bin/env python3
"""The GENERATED SCORE for `meta.bgm: "auto"`: music synthesised in numpy ON the film's beat grid, so the cuts the
tts stage snapped to that grid land on its beats by construction.

  python3 scripts/score.py --bpm 112.5 --seconds 30 [--seed N] [--key Am] [--climax 18.1] out.wav

WHY. The bed it replaces (`sfx.synth_pad`) was an A2+E3+A3 drone with a slow swell: no tempo, no key change, no
event — nothing a cut could land on, and nothing a viewer hears as music (references/motion-research.md §0).

WHAT IT IS (motion-research §3 — every voice there, nothing vendored, nothing downloaded):
  kick    a falling-pitch sine, 45 + 110·e^(-t/30ms) Hz, 120 ms decay, lightly saturated so a phone speaker that
          cannot play 50 Hz still hears its harmonics
  shaker  band-limited noise on eighths (sixteenths at the peak), a closed hat on the off-beats at the peak
  pluck   Karplus-Strong, an arpeggio of the bar's chord
  pad     detuned band-limited saws through a lowpass that opens across each phrase
  bass    the chord's root, rhythm by energy
  clap    on 2 and 4 at the peak only
  riser   noise through a band sweeping 150 Hz -> 10 kHz over the two beats into the payoff
One chord per bar from a four-chord progression (I-V-vi-IV and its relatives) in a key chosen from the seed; 4- or
8-bar sections whose energy rises into the film's payoff and settles after it; accents by VELOCITY (metre and phrase
position), never by random timing; the pad and bass pump against the kick times directly.

RETURNED AS STEMS: `bed` (pad, pluck, bass, clap — the part that ducks under the voice) and `pulse` (kick, shaker,
hat, riser — the quiet part that keeps time while the voice speaks; motion-research §3 "under a voice").

THE PIPELINE CANNOT HEAR. Every number below is a listen-PROXY (spectral balance, crest factor, peak, loudness
against the voice — tests/test_score.py); whether this is music a person accepts under a narrated promo is a
human's call, made by listening.
"""
import math
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                                    # noqa: E402
import beatgrid                                                       # noqa: E402

SR = 48000
MAJOR = (0, 2, 4, 5, 7, 9, 11)
MINOR = (0, 2, 3, 5, 7, 8, 10)
_DEG = {"i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6}
# Four-chord loops a listener already knows. I-V-vi-IV is the research pick; the rest are its rotations and the
# natural-minor loops built from the same diatonic triads, so every progression is in key by construction.
PROGRESSIONS = {
    "major": (("I", "V", "vi", "IV"), ("I", "vi", "IV", "V"), ("vi", "IV", "I", "V"), ("IV", "I", "V", "vi")),
    "minor": (("i", "VI", "III", "VII"), ("i", "iv", "VI", "VII"), ("i", "VI", "iv", "VII")),
}
# 8th-note arpeggio shapes over the chord's four pluck tones (0 = lowest); one per section, from the seed
PLUCK_SHAPES = ((0, 1, 2, 3, 2, 1, 2, 3), (0, 2, 1, 3, 0, 2, 1, 3), (0, 1, 3, 2, 1, 3, 2, 3), (0, 2, 3, 1, 2, 3, 1, 2))
# velocity by eighth position in the bar: the metre's own accents (1 > 3 > 2,4 > the off-beats)
PLUCK_VEL = (1.0, 0.58, 0.78, 0.6, 0.9, 0.58, 0.78, 0.64)
SHAKER_VEL8 = (0.55, 1.0, 0.5, 0.95, 0.55, 1.0, 0.5, 0.9)      # a shaker leans on the off-beat
SHAKER_VEL16 = (0.55, 0.35, 1.0, 0.4, 0.5, 0.35, 0.95, 0.4)
PHRASE_VEL = (1.0, 0.95, 0.98, 1.04)                            # bar 4 of a phrase leans into the next
# stem loudness BEFORE the mix's own gains (approximate BS.1770, ungated — see _lufs); choices, tuned by measuring the
# mixed result against the voice (sfx._SCORE_*_VOL and test_score), not taken from a source
BED_LUFS = -20.0
PULSE_LUFS = -25.0
PEAK_CEIL = 10 ** (-1.0 / 20.0)                                 # each stem peaks at or under -1 dBFS


def hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def choose(seed, key=None):
    """(tonic pitch class, mode, progression, pluck shapes order) — deterministic from the seed; `key` pins the key."""
    s = int(seed) & 0x7FFFFFFF
    if key:
        pc, mode = beatgrid.parse_key(key)
    else:
        # two films in three major: a narrated promo wants the lift more often than the shade
        mode = "minor" if (s // 7) % 3 == 0 else "major"
        pc = (s * 7) % 12                                       # walks the circle of fifths as the seed moves
    progs = PROGRESSIONS[mode]
    prog = progs[(s // 3) % len(progs)]
    return pc, mode, prog, (s // 11) % len(PLUCK_SHAPES)


def key_name(pc, mode):
    names = ("C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
    return names[pc] + ("m" if mode == "minor" else "")


def _triad(pc, mode, roman):
    scale = MAJOR if mode == "major" else MINOR
    d = _DEG[roman.lower()]
    return [pc + scale[(d + k) % 7] + 12 * ((d + k) // 7) for k in (0, 2, 4)]


def _voicings(triad, lo, hi):
    """Every placement of the triad's pitch classes (plus the root doubled) as 4 notes inside [lo, hi]."""
    pcs = [n % 12 for n in triad]
    out = []
    for inv in range(3):
        order = pcs[inv:] + pcs[:inv]
        for base in range(lo, hi):
            if base % 12 != order[0]:
                continue
            notes, cur = [], base
            for p in order + [order[0]]:
                while cur % 12 != p or (notes and cur <= notes[-1]):
                    cur += 1
                notes.append(cur)
            if notes[-1] <= hi:
                out.append(notes)
    return out


def _voice_lead(chords, lo, hi, start=60):
    """The pad's voicing per chord: the placement that moves least from the previous one (the first nearest `start`)."""
    out, prev = [], None
    for tri in chords:
        cands = _voicings(tri, lo, hi)
        if prev is None:
            v = min(cands, key=lambda c: abs(sum(c) / 4.0 - start))
        else:
            v = min(cands, key=lambda c: sum(abs(a - b) for a, b in zip(c, prev)))
        out.append(v)
        prev = v
    return out


# ── voices ────────────────────────────────────────────────────────────────────────────────────────────────────
def _env(n, attack, decay, sr=SR):
    t = np.arange(n) / sr
    return np.clip(t / max(1e-4, attack), 0.0, 1.0) * np.exp(-np.maximum(0.0, t - attack) / max(1e-4, decay))


def kick(sr=SR):
    n = int(0.42 * sr)
    t = np.arange(n) / sr
    f = 45.0 + 110.0 * np.exp(-t / 0.030)
    body = np.sin(2 * np.pi * np.cumsum(f) / sr) * _env(n, 0.001, 0.120, sr)
    # a phone speaker rolls off below ~150 Hz: tanh adds the harmonics that let the kick be HEARD there
    body = np.tanh(1.8 * body) / np.tanh(1.8)
    return body


def _biquad(kind, f0, q, sr=SR):
    """RBJ cookbook biquad (b, a)."""
    w = 2 * np.pi * min(f0, 0.45 * sr) / sr
    al = np.sin(w) / (2 * q)
    c = np.cos(w)
    if kind == "lp":
        b = [(1 - c) / 2, 1 - c, (1 - c) / 2]
    elif kind == "hp":
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
    elif kind == "bp":
        b = [al, 0.0, -al]
    else:
        raise ValueError(kind)
    a = [1 + al, -2 * c, 1 - al]
    return np.array(b) / a[0], np.array(a) / a[0]


def _filt(kind, x, f0, q=0.707, sr=SR):
    from scipy.signal import lfilter
    b, a = _biquad(kind, f0, q, sr)
    return lfilter(b, a, x)


def _sweep(kind, x, f_of_t, q, sr=SR, block=256, per_block=False):
    """A biquad whose centre moves: coefficients per `block` samples, state carried across blocks. `f_of_t` is the
    centre per SAMPLE, or with `per_block` one value per block (a long film's pad: four full-rate float64 arrays for
    one filter were most of a 5-minute score's 2.4 GB peak)."""
    from scipy.signal import lfilter
    y = np.empty_like(x)
    zi = np.zeros(2)
    for i in range(0, len(x), block):
        b, a = _biquad(kind, float(f_of_t[i // block] if per_block else f_of_t[i]), q, sr)
        y[i:i + block], zi = lfilter(b, a, x[i:i + block], zi=zi)
    return y


def noise_hit(rng, dur, hp, lp, attack, decay, sr=SR):
    n = int(dur * sr)
    x = rng.standard_normal(n)
    x = _filt("hp", x, hp, 0.707, sr)
    x = _filt("lp", x, lp, 0.707, sr)
    return x * _env(n, attack, decay, sr)


def clap(rng, sr=SR):
    n = int(0.22 * sr)
    t = np.arange(n) / sr
    x = _filt("bp", rng.standard_normal(n), 1150.0, 1.1, sr)
    env = np.zeros(n)
    for k, t0 in enumerate((0.0, 0.009, 0.019)):                # three hands, a few ms apart — what makes a clap
        tt = t - t0
        env += np.where(tt >= 0, np.exp(-np.maximum(tt, 0) / 0.006), 0.0) * (0.8 ** k)
    tail = np.where(t >= 0.019, np.exp(-np.maximum(t - 0.019, 0) / 0.075), 0.0) * 0.55
    return x * (env + tail)


def pluck(f, rng, vel=1.0, dur=1.1, decay_s=0.85, sr=SR):
    """Karplus-Strong: a period of filtered noise recirculating through a delay whose loop filter is a two-point
    average and a linear-interpolation fractional delay, so the note is IN TUNE: measured within 0.13 cents over the
    pluck's range (MIDI 62-88), where an integer delay would be up to 44 cents off at 48 kHz — audible against the
    pad. The loop gain sets a T60 of `decay_s`; the
    averaging takes the highs out faster, which is the pluck's natural darkening. Vectorised per period: every sample
    of one period depends only on the period before it."""
    period = sr / f
    N = int(math.floor(period - 0.5))                            # the averager adds half a sample of delay
    delta = period - 0.5 - N                                     # the interpolator supplies the rest, 0 <= delta < 1
    h = np.array([0.5 * (1 - delta), 0.5, 0.5 * delta])          # [1,1]/2 convolved with [1-delta, delta]
    g = 10.0 ** (-3.0 / (f * decay_s))
    n = int(dur * sr)
    y = np.zeros(n + N + 2)
    exc = rng.standard_normal(N)
    # velocity sets brightness as well as level: a soft pick is a darker one
    smooth = 0.55 - 0.35 * min(1.0, vel)
    for i in range(1, N):
        exc[i] = (1 - smooth) * exc[i] + smooth * exc[i - 1]
    exc -= exc.mean()
    y[2:2 + N] = exc
    m = 2 + N
    while m < len(y):
        e = min(len(y), m + N)
        k = np.arange(m, e)
        y[m:e] = g * (h[0] * y[k - N] + h[1] * y[k - N - 1] + h[2] * y[k - N - 2])
        m = e
    out = y[2:2 + n]
    fade = int(0.08 * sr)
    out[-fade:] *= np.linspace(1.0, 0.0, fade)
    # THE FIRST PERIOD IS RAW NOISE, and it was the bed's loudest sample: the pluck track measured a 26 dB crest and
    # pushed the bed into its peak ceiling. A 4 ms rise (still a pick, well under the ~10 ms the ear hears as a
    # bowed onset) takes the spike off without blunting the note.
    a = int(0.004 * sr)
    out[:a] *= np.linspace(0.0, 1.0, a) ** 0.7
    return out / (np.max(np.abs(out)) + 1e-12)


def _blep_saw(f, n, sr=SR, phase0=0.0):
    """A band-limited sawtooth (polyBLEP): a naive saw aliases a 300 Hz note's harmonics back into the audible band."""
    dt = f / sr
    ph = (phase0 + dt * np.arange(n)) % 1.0
    s = 2.0 * ph - 1.0
    a = ph < dt
    t = ph[a] / dt
    s[a] -= t + t - t * t - 1.0
    b = ph > 1.0 - dt
    t = (ph[b] - 1.0) / dt
    s[b] -= t * t + t + t + 1.0
    return s


def pad_chord(notes, n, sr=SR, attack=0.35, release=0.45, detune_cents=7.0, seed=0):
    """Four notes, each two saws detuned ±`detune_cents` (the beating IS the pad's motion), soft attack and release."""
    x = np.zeros(n)
    for k, m in enumerate(notes):
        for s in (-1.0, 1.0):
            f = hz(m) * 2.0 ** (s * detune_cents / 1200.0)
            x += _blep_saw(f, n, sr, phase0=((seed * 0.37 + k * 0.23 + (s + 1) * 0.31) % 1.0)) * (0.9 if k else 1.0)
    rel = int(release * sr)
    env = np.clip(np.arange(n) / (attack * sr), 0.0, 1.0)
    if rel < n:
        env[-rel:] *= np.linspace(1.0, 0.0, rel) ** 1.5
    return x * env / 8.0


def bass_note(m, dur, sr=SR):
    n = int(dur * sr)
    t = np.arange(n) / sr
    f = hz(m)
    x = np.sin(2 * np.pi * f * t) + 0.22 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
    env = np.clip(t / 0.008, 0, 1) * (0.72 + 0.28 * np.exp(-t / 0.09))
    r = min(n, int(0.06 * sr))
    env[-r:] *= np.linspace(1.0, 0.0, r)
    return np.tanh(1.3 * x * env) / np.tanh(1.3)


def riser(rng, dur, sr=SR):
    """Noise through a band climbing 150 Hz -> 10 kHz (motion-research §3), swelling to the landing. Cut, not faded,
    at the landing (a 12 ms ramp so the cut does not click): the downbeat is where it stops."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    fc = 150.0 * (10000.0 / 150.0) ** (t / dur)
    x = _sweep("bp", rng.standard_normal(n), fc, 1.6, sr)
    env = (t / dur) ** 2.2
    r = int(0.012 * sr)
    env[-r:] *= np.linspace(1.0, 0.0, r)
    return x * env


def _place(buf, t, s, gain, sr=SR):
    i = int(round(t * sr))
    if i >= len(buf) or i + len(s) <= 0:
        return
    a = max(0, -i)
    j = min(len(buf), i + len(s))
    buf[max(0, i):j] += s[a: a + (j - max(0, i))] * gain


def pump_env(n, kick_times, period, depth, sr=SR):
    """Sidechain pumping computed from the kick times themselves (not from a detector): the gain dips `depth` on
    each kick — a 4 ms lead-in so the dip itself does not click — and recovers over about half a beat."""
    g = np.ones(n, np.float32)
    tau = 0.2 * period
    L = int(0.6 * period * sr)
    lead = int(0.004 * sr)
    shape = np.concatenate([np.linspace(0.0, 1.0, lead, endpoint=False), np.exp(-np.arange(L) / (tau * sr))])
    for tk in kick_times:
        i = int(round(tk * sr)) - lead
        a = max(0, -i)
        j = min(n, i + len(shape))
        if j > max(0, i):
            seg = 1.0 - depth * shape[a: a + (j - max(0, i))]
            g[max(0, i):j] = np.minimum(g[max(0, i):j], seg)
    return g


def limit(x, ceiling, sr=SR, win_ms=8.0):
    """A look-ahead peak limiter: the gain that keeps every sample under `ceiling`, widened by a min-filter so it is
    already down when a peak arrives, then box-smoothed over the same window so it never steps (a stepped gain is
    a click). Acts only where a peak exceeds the ceiling; everywhere else the gain is exactly 1."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    w = max(3, int(win_ms * sr / 1000.0) | 1)
    env = np.abs(x)
    g = np.minimum(1.0, ceiling / np.maximum(env, 1e-12))
    g = minimum_filter1d(g, size=2 * w + 1, mode="nearest")
    g = uniform_filter1d(g, size=w, mode="nearest")
    return x * g


# CREST: the bed's plucks land on the kick's beats, and their summed transients measured an 18-19 dB crest on the
# rendered bed. Under a voice that matters beyond taste: the mix's loudness pass is LINEAR and capped by the true
# peak, so a music peak riding a voice peak lowers the whole film's gain (the same failure sfx gain-stages its SFX
# bus against). The bed is limited to this many dB over its own RMS — a choice; it trims only the attacks.
BED_CREST_DB = 14.0


# ── loudness (BS.1770 K-weighting at 48 kHz, ungated: a continuous bed has no silence to gate) ─────────────────────
_K1 = ([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585])
_K2 = ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])


def lufs(x, sr=SR, chunk=1 << 20):
    from scipy.signal import lfilter
    if sr != 48000:
        raise ValueError("the K-weighting coefficients here are the 48 kHz ones (BS.1770 table 1/2)")
    x = np.asarray(x)
    if not len(x):
        return -120.0
    # in chunks, the filter state carried: a whole 5-minute stem in float64, filtered twice, is three 115 MB copies
    z1, z2 = np.zeros(2), np.zeros(2)
    acc = 0.0
    for i in range(0, len(x), chunk):
        y, z1 = lfilter(*_K1, x[i:i + chunk].astype(np.float64), zi=z1)
        y, z2 = lfilter(*_K2, y, zi=z2)
        acc += float(np.dot(y, y))
    ms = acc / len(x)
    return -0.691 + 10.0 * math.log10(ms) if ms > 0 else -120.0


# ── the arrangement ─────────────────────────────────────────────────────────────────────────────────────────────
def arrangement(grid, seconds, climax_s=None, section_bars=None):
    """{bar: energy} and the landing beat: energy 1 (intro: pad, quarter plucks, soft shaker, a kick on one), 2
    (eighth plucks, kick on 1 and 3, bass), 3 (the peak: four on the floor, sixteenth shaker, hat, clap), 0 (outro).

    Sections are 8 bars on a film of 24 bars or more, else 4 (motion-research §3: changes on 4/8-bar boundaries), and
    they are COUNTED FROM THE LANDING, so the payoff opens a section. With no payoff declared the peak sits at the
    section boundary nearest 60% of the film (U)."""
    bpb = grid.beats_per_bar
    bar = grid.bar_s
    b0 = int(math.floor((0.0 - grid.offset_s) / bar))
    b1 = int(math.floor((seconds - grid.offset_s) / bar))
    nbars = b1 - b0 + 1
    L = section_bars or (8 if nbars >= 24 else 4)
    if climax_s is not None:
        land = grid.nearest_beat(climax_s)
        lbar = land // bpb
        virtual = False
    else:
        target = 0.6 * seconds
        lbar = int(round((target - grid.offset_s) / bar))
        lbar = b0 + int(round((lbar - b0) / float(L))) * L
        land = lbar * bpb
        virtual = True
    energy = {}
    first = (b0 - lbar) // L                                 # the film's first section, counted from the landing
    for b in range(b0, b1 + 1):
        s = (b - lbar) // L
        if s >= 0:
            e = 3 if s == 0 else 2                           # the payoff's section is the peak; after it, settled
        elif first <= -2:
            e = 1 if s == first else 2                       # the opening section is the intro, then the build
        else:
            e = 1 if b < b0 + 2 else 2                       # one section before the payoff: two light bars, then build
        energy[b] = e
    # the outro: the bar the film ends in, and the one before it when the end comes early in its bar
    energy[b1] = 0
    if (seconds - grid.t(b1 * bpb)) < 0.5 * bar and b1 - 1 in energy and b1 - 1 > lbar:
        energy[b1 - 1] = min(energy[b1 - 1], 1)
    return {"bars": (b0, b1), "section_bars": L, "landing_beat": land, "landing_bar": lbar, "virtual": virtual,
            "energy": energy}


def render(grid, seconds, climax_s=None, riser_into_climax=True, seed=0, key=None, sr=SR):
    """The score, as stems: {'bed': float32, 'pulse': float32, 'sr', 'info'}. Deterministic for (grid, seconds,
    climax_s, riser_into_climax, seed, key)."""
    if sr != SR:
        raise ValueError("the score renders at %d Hz (the delivery rate: no resampling between it and the AAC)" % SR)
    if seconds <= 0:
        raise ValueError("a score needs a positive length, got %r" % seconds)
    rng = np.random.default_rng(20261023 + (int(seed) & 0xFFFFFF))
    pc, mode, prog, shape0 = choose(seed, key)
    arr = arrangement(grid, seconds, climax_s)
    b0, b1 = arr["bars"]
    bpb, per, bar = grid.beats_per_bar, grid.period, grid.bar_s
    n = int(math.ceil((seconds + 0.25) * sr))
    # float32 tracks: measured, float64 ones put a 60 s score at a 0.7 GB peak and a 5-minute one at 2.4 GB
    tracks = {k: np.zeros(n, np.float32) for k in ("kick", "shaker", "hat", "clap", "pluck", "pad", "bass", "riser")}
    chords = [_triad(pc, mode, r) for r in prog]
    pad_v = _voice_lead(chords * 2, 50, 74)[len(chords):]          # settled voice leading around the loop
    land, lbar = arr["landing_beat"], arr["landing_bar"]
    kick_s = kick(sr)
    shakers = [noise_hit(rng, 0.09, 5200.0, 12000.0, 0.005, 0.034, sr) for _ in range(3)]
    hats = [noise_hit(rng, 0.06, 7500.0, 14000.0, 0.001, 0.020, sr) for _ in range(2)]
    claps = [clap(rng, sr) for _ in range(2)]
    pluck_cache = {}
    kicks = []

    def bar_chord(b):
        return (b - lbar) % len(chords)                          # the progression restarts at the landing
    # the break: the two beats before the landing drop the kick, bass and shaker; the riser fills them
    brk = {land - 2, land - 1} if not arr["virtual"] else set()
    for b in range(b0, b1 + 1):
        e = arr["energy"][b]
        tb = grid.t(b * bpb)
        ci = bar_chord(b)
        tri, pv = chords[ci], pad_v[ci]
        phrase = PHRASE_VEL[(b - lbar) % 4]
        sect_down = 1.12 if (b - lbar) % arr["section_bars"] == 0 else 1.0
        # PAD — one chord per bar, released into the next bar so the change is a crossfade, not a gap
        L = int((bar + 0.45) * sr)
        ch = pad_chord(pv, L, sr, attack=0.30 if e else 0.6, seed=b)
        _place(tracks["pad"], tb, ch, (0.55, 0.8, 1.0, 1.0)[e])
        # BASS — the root, two octaves down
        root = 36 + (tri[0] - 36) % 12
        if e >= 2:
            hits = ([(0, 1.5), (2, 0.9), (3.5, 0.45)] if e == 2 else
                    [(q / 2.0, 0.42) for q in range(2 * bpb)])
            for pos, d in hits:
                i_beat = b * bpb + int(math.floor(pos))
                if i_beat in brk:
                    continue
                vel = (1.0 if pos == 0 else 0.82 if pos == 2 else 0.7) * phrase
                _place(tracks["bass"], grid.t(b * bpb + pos), bass_note(root, d * per, sr), vel)
        # PLUCK — the arpeggio: quarter notes in the intro, eighths from energy 2
        tones = sorted(set([m for m in range(62, 82) if (m % 12) in [x % 12 for x in tri]]))[:4]
        shape = PLUCK_SHAPES[(shape0 + (b - lbar) // arr["section_bars"]) % len(PLUCK_SHAPES)]
        steps = range(0, 2 * bpb, 2) if e <= 1 else range(2 * bpb)
        for q in steps:
            if e == 0 and q > 0:
                break
            m = tones[shape[q % 8] % len(tones)]
            if e == 3 and q == 0:
                m += 12 if m + 12 <= 88 else 0                   # the peak's downbeat reaches up an octave
            vel = PLUCK_VEL[q % 8] * phrase * (sect_down if q == 0 else 1.0)
            key_ = (m, round(vel, 2))
            if key_ not in pluck_cache:
                pluck_cache[key_] = pluck(hz(m), rng, vel=vel, sr=sr)
            _place(tracks["pluck"], grid.t(b * bpb + q / 2.0), pluck_cache[key_], vel)
        # KICK
        pattern = {0: [], 1: [(0, 0.55)], 2: [(0, 0.95), (2, 0.8)], 3: [(0, 1.0), (1, 0.72), (2, 0.88), (3, 0.74)]}[e]
        for pos, vel in pattern:
            i_beat = b * bpb + pos
            if i_beat in brk:
                continue
            v = vel * phrase * (1.15 if i_beat == land else sect_down if pos == 0 else 1.0)
            t = grid.t(i_beat)
            if t >= 0:
                _place(tracks["kick"], t, kick_s, min(1.0, v))
                kicks.append(t)
        # SHAKER / HAT / CLAP
        if e >= 1:
            div, vels = (4, SHAKER_VEL16) if e == 3 else (2, SHAKER_VEL8)
            for q in range(div * bpb):
                i_beat = b * bpb + q // div
                if i_beat in brk:
                    continue
                v = vels[q % len(vels)] * (0.6 if e == 1 else 1.0) * phrase
                _place(tracks["shaker"], grid.t(b * bpb + q / float(div)), shakers[q % 3], v)
        if e == 3:
            for q in range(bpb):
                if b * bpb + q in brk:
                    continue
                _place(tracks["hat"], grid.t(b * bpb + q + 0.5), hats[q % 2], 0.9 if q % 2 else 0.75)
                if q in (1, 3):
                    _place(tracks["clap"], grid.t(b * bpb + q), claps[(q // 2) % 2], 0.95 if q == 3 else 0.85)
    if riser_into_climax and not arr["virtual"]:
        d = 2 * per
        _place(tracks["riser"], grid.t(land) - d, riser(rng, d, sr), 1.0)
    # PUMP — from the kick times, on the pad (deepest), bass and pluck (lightest)
    for name, depth in (("pad", 0.5), ("bass", 0.4), ("pluck", 0.18)):
        tracks[name] *= pump_env(n, kicks, per, depth, sr)
    # the pad's lowpass opens across each 4-bar phrase and with energy: "slow filter" (motion-research §3) — computed
    # once per filter block, which is all the filter reads
    blk = 256
    tb = np.arange(0, n, blk) / float(sr)
    ph = ((tb - grid.t(lbar * bpb)) / (4 * bar)) % 1.0
    eb = np.array([arr["energy"].get(int(math.floor((tt - grid.offset_s) / bar)), 1) for tt in tb])
    fc = np.array((520.0, 700.0, 1000.0, 1450.0))[eb] * (1.0 + 0.8 * (0.5 - 0.5 * np.cos(2 * np.pi * ph)))
    tracks["pad"] = _sweep("lp", tracks["pad"], fc, 0.9, sr, block=blk, per_block=True)
    # THE BALANCE, set by measuring each voice alone (scratch diag, 112.5 BPM, 32 s): at the first gains the kick and
    # bass came out 14-15 LU over the pluck and the hat and clap 30 LU under the kick — 58-61% of the energy below
    # 100 Hz, a bed a phone speaker would barely play. These weights put the pad and the pluck in front (the music;
    # pluck 2.7 LU under the pad), the bass 3.0 and the kick 4.0 LU under the pad, the shaker 10.9, clap 12.3 and hat
    # 15.9 under (choices, measured as LUFS over the whole bed; the riser plays for two beats, so over a 32 s bed its
    # level reads ~15 LU under its momentary one).
    mix = {"kick": 0.32, "shaker": 0.15, "hat": 0.29, "clap": 0.9, "pluck": 0.97, "pad": 0.5, "bass": 0.165,
           "riser": 0.22}
    bed = sum(tracks[k] * mix[k] for k in ("pad", "pluck", "bass", "clap"))
    rms = float(np.sqrt(np.mean(bed * bed))) if len(bed) else 0.0
    if rms > 0:
        bed = limit(bed, rms * 10.0 ** (BED_CREST_DB / 20.0), sr)
    pulse = sum(tracks[k] * mix[k] for k in ("kick", "shaker", "hat", "riser"))
    levels = {}
    for name, x, target in (("bed", bed, BED_LUFS), ("pulse", pulse, PULSE_LUFS)):
        lo = lufs(x, sr)
        gain = 10.0 ** ((target - lo) / 20.0) if lo > -100 else 1.0
        y = x * gain
        pk = float(np.max(np.abs(y))) if len(y) else 0.0
        if pk > PEAK_CEIL:
            y *= PEAK_CEIL / pk
        levels[name] = {"lufs": round(lufs(y, sr), 2), "peak_dbfs": round(20 * math.log10(max(1e-9, float(
            np.max(np.abs(y))))), 2)}
        if name == "bed":
            bed = y
        else:
            pulse = y
    # ONE CEILING FOR THE SUM: the stems are mixed apart (sfx ducks only the bed), but the bed alone and anything that
    # sums them must not clip either — both scaled together, so their balance holds
    both = float(np.max(np.abs(bed + pulse))) if len(bed) else 0.0
    if both > PEAK_CEIL:
        bed, pulse = bed * (PEAK_CEIL / both), pulse * (PEAK_CEIL / both)
        for name, y in (("bed", bed), ("pulse", pulse)):
            levels[name] = {"lufs": round(lufs(y, sr), 2),
                            "peak_dbfs": round(20 * math.log10(max(1e-9, float(np.max(np.abs(y))))), 2)}
        levels["sum_limited_db"] = round(20 * math.log10(PEAK_CEIL / both), 2)
    info = {"key": key_name(pc, mode), "mode": mode, "progression": list(prog), "bpm": round(grid.bpm, 4),
            "seed": int(seed), "landing_beat": land, "landing_t": round(grid.t(land), 4),
            "virtual_peak": arr["virtual"], "section_bars": arr["section_bars"],
            "energy": [arr["energy"][b] for b in range(b0, b1 + 1)], "first_bar": b0, "kicks": len(kicks),
            "riser": bool(riser_into_climax and not arr["virtual"]), "levels": levels}
    return {"bed": bed.astype(np.float32)[: int(round(seconds * sr))],
            "pulse": pulse.astype(np.float32)[: int(round(seconds * sr))], "sr": sr, "info": info}


def write_wav(path, x, sr=SR):
    a = np.clip(np.asarray(x, dtype=np.float64), -1.0, 1.0)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((a * 32767.0).astype("<i2").tobytes())


def listen_proxy(x, sr=SR):
    """The measurements that stand in for a listen (tests/test_score.py holds them to ranges): band energy shares,
    crest factor, peak, clipped samples, loudness. None of these says it sounds GOOD; each can say it sounds wrong."""
    x = np.asarray(x, dtype=np.float64)
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    tot = float(spec.sum()) or 1.0
    bands = {"sub<100": (0, 100), "low100-400": (100, 400), "mid400-2k": (400, 2000), "presence2k-6k": (2000, 6000),
             "air6k-16k": (6000, 16000), "ultra>16k": (16000, sr / 2)}
    share = {k: round(float(spec[(f >= a) & (f < b)].sum()) / tot, 4) for k, (a, b) in bands.items()}
    rms = float(np.sqrt(np.mean(x * x))) or 1e-12
    pk = float(np.max(np.abs(x)))
    return {"bands": share, "crest_db": round(20 * math.log10(pk / rms), 2), "peak_dbfs": round(20 * math.log10(
        max(pk, 1e-12)), 2), "clipped": int(np.sum(np.abs(x) >= 0.9999)), "lufs": round(lufs(x, sr), 2)}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="render the generated score alone (bed + pulse) to a WAV")
    ap.add_argument("out")
    ap.add_argument("--bpm", type=float, default=112.5)
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--key", default=None)
    ap.add_argument("--climax", type=float, default=None)
    ap.add_argument("--offset", type=float, default=0.0)
    a = ap.parse_args()
    g = beatgrid.BeatGrid(a.bpm, a.offset)
    s = render(g, a.seconds, climax_s=a.climax, seed=a.seed, key=a.key)
    write_wav(a.out, s["bed"] + s["pulse"])
    print(s["info"])
    print(listen_proxy(s["bed"] + s["pulse"]))
