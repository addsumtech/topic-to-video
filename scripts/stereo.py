"""stereo — the promo's sound placed in a stereo field, and the measurements that stand in for a listen.

The promo mix was MONO: every click, landing and whoosh in the middle of the picture, whatever the picture did. A
produced product film places a sound where its cause is (a click on the left of the frame is heard a little left), lets
air travel the way the picture travels, and gives the music and the big landing width. Three tools do it:

  pan(x, p)            constant-power pan, p in [-1 (left), 1 (right)] -> (n, 2)
  sweep(x, p0, p1)     a pan that travels across the sound's length (a whoosh following the move)
  widen(x, wet)        width from two decorrelated short rooms (no Haas delay: a delayed copy combs in mono)

and `measure(lr)` says what came out: the L/R correlation (1 = mono, ~0 = unrelated, < 0 = out of phase), the
loss when folded to mono (a phone speaker), and the balance. None of these says it sounds GOOD; each can say it is
broken (out of phase, lopsided, mono after all).
"""
import numpy as np


def _cp(p):
    p = np.clip(np.asarray(p, dtype=np.float64), -1.0, 1.0)
    a = (p + 1.0) * np.pi / 4.0
    return np.cos(a), np.sin(a)                    # constant power: L^2 + R^2 = 1 everywhere


def pan(x, p):
    gl, gr = _cp(p)
    x = np.asarray(x, dtype=np.float32)
    # normalised so a centred sound keeps its level in each channel (the mono mix's level)
    return np.stack([x * (gl * np.sqrt(2)), x * (gr * np.sqrt(2))], 1).astype(np.float32)


def sweep(x, p0, p1):
    x = np.asarray(x, dtype=np.float32)
    n = len(x)
    if n == 0:
        return np.zeros((0, 2), np.float32)
    # the travel happens where the sound has its energy: the pan follows the cumulative energy, not the clock, so a
    # whoosh that swells late still crosses the field while it is loud
    e = np.cumsum(x.astype(np.float64) ** 2)
    u = e / e[-1] if e[-1] > 0 else np.linspace(0, 1, n)
    gl, gr = _cp(p0 + (p1 - p0) * u)
    return np.stack([x * gl * np.sqrt(2), x * gr * np.sqrt(2)], 1).astype(np.float32)


_ROOMS = {}


def room(sr, seconds=0.42, seed=11):
    """Two decorrelated impulse responses: exponentially decaying noise (RT60 = `seconds`), darkened as it decays,
    each starting after its own few-ms pre-delay. Deterministic."""
    key = (sr, seconds, seed)
    if key not in _ROOMS:
        rng = np.random.default_rng(seed)
        n = int(seconds * sr)
        t = np.arange(n) / sr
        env = 10.0 ** (-3.0 * t / seconds)        # -60 dB at `seconds`
        irs = []
        for pre in (0.011, 0.017):
            x = rng.standard_normal(n) * env
            k = max(1, int(sr * 0.00025))
            x = np.convolve(x, np.ones(k) / k, mode="same")      # a little darker than white
            x = np.concatenate([np.zeros(int(pre * sr)), x])
            irs.append(x / np.sqrt(np.sum(x * x)))
        m = max(len(i) for i in irs)
        _ROOMS[key] = [np.pad(i, (0, m - len(i))) for i in irs]
    return _ROOMS[key]


def _fftconv(x, h):
    n = len(x) + len(h) - 1
    nf = 1 << int(np.ceil(np.log2(max(2, n))))
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(h, nf), nf)[: len(x)]


def widen(x, wet=0.35, sr=44100, seconds=0.42):
    """The dry sound in the middle, plus its own room heard differently in each ear. The room's level is `wet` of the
    dry's energy."""
    x = np.asarray(x, dtype=np.float64)
    if len(x) == 0:
        return np.zeros((0, 2), np.float32)
    il, ir = room(sr, seconds)
    pad = np.concatenate([x, np.zeros(len(il))])
    wl, wr = _fftconv(pad, il), _fftconv(pad, ir)
    dry = np.concatenate([x, np.zeros(len(il))])
    g = wet * np.sqrt(np.sum(dry * dry) / max(1e-12, (np.sum(wl * wl) + np.sum(wr * wr)) / 2))
    return np.stack([dry + g * wl, dry + g * wr], 1).astype(np.float32)


def place(x, how, sr=44100):
    """`how`: None / 0 (centre), a number (pan), (p0, p1) (a sweep), "wide" (the room), ("wide", p) (the room, leaning)."""
    if how is None:
        return pan(x, 0.0)
    if isinstance(how, (int, float)):
        return pan(x, float(how))
    if how == "wide":
        return widen(x, 0.45, sr)
    if isinstance(how, (tuple, list)) and len(how) == 2 and how[0] == "wide":
        w = widen(x, 0.45, sr)
        gl, gr = _cp(float(how[1]))
        return (w * np.array([gl * np.sqrt(2), gr * np.sqrt(2)])).astype(np.float32)
    if isinstance(how, (tuple, list)) and len(how) == 2:
        return sweep(x, float(how[0]), float(how[1]))
    raise ValueError("a placement is a pan, (p0, p1), 'wide' or ('wide', p): got %r" % (how,))


def measure(lr):
    """{'corr', 'mono_loss_db', 'balance_db'} over the frames where the sound is not silent."""
    lr = np.asarray(lr, dtype=np.float64)
    L, R = lr[:, 0], lr[:, 1]
    keep = (np.abs(L) + np.abs(R)) > 1e-4
    L, R = L[keep], R[keep]
    if len(L) < 16:
        return {"corr": 1.0, "mono_loss_db": 0.0, "balance_db": 0.0}
    el, er = float(np.sum(L * L)), float(np.sum(R * R))
    corr = float(np.sum(L * R) / np.sqrt(max(1e-18, el * er)))
    M = (L + R) / 2.0
    loss = 10 * np.log10(max(1e-18, float(np.sum(M * M))) / max(1e-18, (el + er) / 2.0))
    return {"corr": round(corr, 3), "mono_loss_db": round(float(-loss), 2), "balance_db": round(float(10 * np.log10(max(1e-18, el) / max(1e-18, er))), 2)}
