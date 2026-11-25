#!/usr/bin/env python3
"""mix — voice, music and SFX into one master, the music set UNDER the voice by measurement, not by a guessed gain.

    python3 scripts/mix.py --voice audio/voice.wav [--music audio/score.wav] [--sfx audio/sfx.wav] --out audio/mix.wav
        [--under 20] [--lift 8] [--sfx-gain 0.8] [--lufs -14] [--tp -2] [--band-deep 9]
    python3 scripts/mix.py --music audio/score.wav [--sfx audio/sfx.wav] --out audio/mix.wav   # a film with NO voice
    python3 scripts/mix.py --check <film_dir>        # film_qc "mix": the shipped mix is this script's, as measured

While the voice speaks, the music sits `--under` dB below it (measured RMS over the speech, 20 by default: WCAG 1.4.7
asks background sound to be at least 20 dB under speech, and mixers use 18-24); between lines (a pause of 0.6 s or
more) it rises `--lift` dB, never above 6 dB under the voice. The ducking follows the voice track itself: down 0.12 s
before each line starts, back up over 0.5 s after it ends. SFX are high-passed at 160 Hz. The sum is mastered to
`--lufs` integrated with true peak at or under `--tp`. It prints the separation it reached (voice over music, per
half second of speech) and exits 1 when a tenth of the speech has less than `--under` - 3 dB: the music would
compete with the words. The same is held in the 1-4 kHz band where consonants live: while the voice speaks, the
music's 1-4 kHz band alone is lowered (up to `--band-deep` dB more) until it too sits `--under` dB under the voice's,
and a tenth of the speech under `--under` - 5 dB there is red. The master is a linear gain and a 4x-oversampled
true-peak limiter (not loudnorm, whose second pass falls back to dynamic gain when the target and true peak conflict). Beside the mix it writes <name>.mix.json (the measures and the mix's SHA-1), which
film_qc's "mix" check reads: a film with a music stem in audio/ must ship that very mix.

WHY. A launch film mixed its own score at a fixed gain under a sidechain compressor; measured, the music sat a median
5 dB under the voice (job-hunt film, 2026-11-19): loud enough to compete with every word. Studies of narrated
instruction find music costs recall when it competes with the narration (Moreno & Mayer 2000), and the mixing norm
is ~20 dB under speech.
MEASURED (2026-11-25, an EN and a ZH edge-tts voice over score.py, seed 7): broadband the music sat 20 dB under the
voice, in 1-4 kHz only 14.3 dB (p10); the band duck lifted it to 19.7 / 18.7 dB while the music overall fell 0.2 dB;
the old loudnorm second pass landed the ZH mix at -15.1 LUFS against -14, the gain + limiter at -14.2.
Exit 0 mixed, 1 the separation is short, 2 usage or an unreadable input.
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

SR = 48000
_USAGE = __doc__.strip().splitlines()[2].strip()


def load(path, n=None):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    if n is not None:
        x = np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]
    return x


def _rms_db(x, hop):
    m = x.mean(axis=1)
    k = len(m) // hop
    r = np.sqrt(np.mean(m[:k * hop].reshape(k, hop) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(r)


def speech_mask(voice, hop=2400, gap=0.6):
    """Per 50 ms frame: is the voice speaking (gaps under `gap` s count as speaking)?"""
    db = _rms_db(voice, hop)
    on = db > max(db.max() - 45, np.percentile(db, 95) - 30)
    fill = int(round(gap * SR / hop))
    idx = np.flatnonzero(on)
    for a, b in zip(idx[:-1], idx[1:]):
        if 1 < b - a <= fill:
            on[a:b] = True
    return on, db


def _smooth_db(db, mask, frames):
    """Power average of `db` over `frames` frames around each frame, counting only frames where mask is True."""
    p = np.where(mask, 10 ** (db / 10), 0.0)
    k = np.ones(frames)
    num, den = np.convolve(p, k, "same"), np.convolve(mask.astype(float), k, "same")
    return 10 * np.log10(np.maximum(num / np.maximum(den, 1e-9), 1e-12))


def gains(mask, vdb, mdb, under, lift, hop=2400, span=0.5):
    """Per frame, the music gain in dB: while the voice speaks, `under` dB below the voice of the last/next `span` s
    (it follows a quieter line and a louder bar of the score); between lines `lift` dB higher, never above 6 dB under
    the voice."""
    f = max(1, int(round(span * SR / hop)))
    vs, ms = _smooth_db(vdb, mask, f), _smooth_db(mdb, np.ones_like(mask), f)
    g_speech = vs - under - ms
    vmean = 10 * np.log10(np.mean(10 ** (vdb[mask] / 10)))
    g_gap = np.minimum(np.median(g_speech[mask]) + lift, vmean - 6 - ms)
    return np.where(mask, g_speech, g_gap)


def envelope(mask, g_db, hop=2400, n=None, pre=0.12, release=0.5):
    """Per-sample linear gain from per-frame dB targets: lower at once (and `pre` s before a line starts, so the music is
    down before the first word), higher only over `release` s."""
    tgt = g_db.copy()
    lead = int(round(pre * SR / hop))
    for i in np.flatnonzero(mask):
        tgt[max(0, i - lead):i] = np.minimum(tgt[max(0, i - lead):i], tgt[i])
    out = np.empty_like(tgt)
    a_up = 1 - np.exp(-hop / (release * SR))
    out[0] = tgt[0]
    for i in range(1, len(tgt)):
        out[i] = tgt[i] if tgt[i] < out[i - 1] else out[i - 1] + (tgt[i] - out[i - 1]) * a_up
    # between frames, interpolate (a stepped gain clicks)
    x = (np.arange(len(out)) + 0.5) * hop
    n = n or len(out) * hop
    return np.interp(np.arange(n), x, 10 ** (out / 20))


def separation(voice, music, mask, hop=2400, win=10):
    """Voice over music in dB, per window of `win` 50 ms frames where the voice is sounding (within 10 dB of its usual
    speech level; the breath between two words is not a place music competes with a word)."""
    vd, md = _rms_db(voice, hop), _rms_db(music, hop)
    k = min(len(vd), len(md), len(mask))
    level = np.median(vd[:k][mask[:k]])
    out = []
    for i in range(0, k - win, win):
        v = 10 * np.log10(np.mean(10 ** (vd[i:i + win] / 10)))
        if mask[i:i + win].mean() > 0.8 and v > level - 10:
            out.append(v - 10 * np.log10(np.mean(10 ** (md[i:i + win] / 10))))
    return np.array(out)


BAND = (1000, 4000)    # where consonants carry intelligibility: the music must be under the voice HERE too


def band(x, lo=BAND[0], hi=BAND[1]):
    """The 1-4 kHz band of x (zero phase, so x - band(x) + band(x) is x exactly)."""
    from scipy.signal import butter, sosfiltfilt
    return sosfiltfilt(butter(4, [lo, hi], btype="band", fs=SR, output="sos"), x, axis=0)


def band_duck(voice, bed, mask, under, deep, hop=2400, span=0.5):
    """The bed with its 1-4 kHz band lowered, while the voice speaks, until it sits `under` dB below the voice's own
    1-4 kHz band (at most `deep` dB more); the rest of the music is untouched."""
    vb, bb = band(voice), band(bed)
    k = min(len(mask), len(voice) // hop)
    f = max(1, int(round(span * SR / hop)))
    vs = _smooth_db(_rms_db(vb, hop)[:k], mask[:k], f)
    bs = _smooth_db(_rms_db(bb, hop)[:k], np.ones(k, bool), f)
    extra = np.where(mask[:k], np.clip((vs - under) - bs, -deep, 0.0), 0.0)
    return bed + (envelope(mask[:k], extra, n=len(bed))[:, None] - 1.0) * bb


def master(total, out_p, lufs, tp):
    """A linear gain to `lufs`, then a limiter at 4x oversampling (so it holds TRUE peak under `tp`); the limiter can
    take a little loudness, so the gain is corrected from the measured result (<= 3 rounds, to within 0.2 LU)."""
    tmp = out_p + ".sum.wav"
    _write(tmp, total)
    g = lufs - _ebu(tmp)[0]
    for _ in range(3):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                        "volume=%.3fdB,aresample=192000,alimiter=limit=%.5f:level=false:attack=1:release=50,aresample=%d"
                        % (g, 10 ** ((tp - 0.2) / 20), SR), "-ar", str(SR), out_p], check=True)
        got = _ebu(out_p)[0]
        if abs(got - lufs) <= 0.2:
            break
        g += lufs - got
    os.remove(tmp)


def _ebu(path):
    """(integrated LUFS, true peak dBTP, max short-term LUFS) of a file."""
    r = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    i = tpk = None
    st = []
    for line in r.splitlines():
        s = line.strip()
        if s.startswith("I:"):
            i = float(s.split()[1])
        elif s.startswith("Peak:"):
            tpk = float(s.split()[1])
        elif " S:" in line and " M:" in line:
            try:
                st.append(float(line.split(" S:")[1].split()[0]))
            except (ValueError, IndexError):
                pass
    if i is None:
        raise RuntimeError("mix: ffmpeg measured no loudness for %s" % path)
    return i, tpk, (max(st) if st else None)


def mix(voice_p, music_p, sfx_p, out_p, under=20.0, lift=8.0, sfx_gain=0.8, lufs=-14.0, tp=-2.0, band_deep=9.0):
    if not voice_p:                           # a music-led film (a short promo told in type): the music IS the track
        assert music_p, "mix: a film with no voice needs --music"
        total = load(music_p)
        n = len(total)
        report = {"under": under, "voice": False}
        music_p = None
    else:
        voice = load(voice_p)
        n = len(voice)
        mask, vdb = speech_mask(voice)
        total = voice.copy()
        report = {"under": under}
    if music_p:
        music = load(music_p, n)
        mdb = _rms_db(music, 2400)
        k = min(len(mask), len(mdb))
        g = gains(mask[:k], vdb[:k], mdb[:k], under, lift)
        bed = music * envelope(mask[:k], g, n=n)[:, None]
        if band_deep > 0:
            bed = band_duck(voice, bed, mask, under, band_deep)
        sep = separation(voice, bed, mask)
        bsep = separation(band(voice), band(bed), mask)
        report.update(separation_median=round(float(np.median(sep)), 1) if len(sep) else None,
                      separation_p10=round(float(np.percentile(sep, 10)), 1) if len(sep) else None,
                      music_gain_db=round(float(np.median(g[mask[:k]])), 1),
                      band_separation_median=round(float(np.median(bsep)), 1) if len(bsep) else None,
                      band_separation_p10=round(float(np.percentile(bsep, 10)), 1) if len(bsep) else None)
        total = total + bed
    if sfx_p:
        from scipy.signal import lfilter
        b, a = _hp(160)                       # on the SFX alone: in the master chain it would thin the voice too
        total = total + lfilter(b, a, load(sfx_p, n) * sfx_gain, axis=0)
    master(total, out_p, lufs, tp)
    report["lufs"], report["true_peak"], report["max_short_term"] = (round(v, 1) if v is not None else None
                                                                     for v in _ebu(out_p))
    return report


def _sha1(path):
    import hashlib
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def report_path(out):
    return os.path.splitext(out)[0] + ".mix.json"


MUSIC_STEMS = ("score", "music", "bgm", "bed")


def check(film_dir):
    """film_qc's "mix": a film with a music stem (audio/<score|music|bgm|bed>*) ships audio/mix.wav made by this
    script, unchanged since it was measured, with the music held under the voice. 0 OK or no music, 1 not."""
    a = os.path.join(film_dir, "audio")
    stems = [f for f in (os.listdir(a) if os.path.isdir(a) else []) if f.lower().startswith(MUSIC_STEMS) and f.lower().endswith((".wav", ".mp3", ".m4a", ".flac"))]
    if not stems:
        print("[mix] OK  no music stem in audio/ (nothing to judge)")
        return 0
    mixp = os.path.join(a, "mix.wav"); rp = report_path(mixp)
    if not os.path.isfile(rp):
        print("[mix] RED  audio/%s is music but audio/mix.wav was not made by scripts/mix.py (no %s): a hand-set mix sat the "
              "score 2 dB under the words" % (stems[0], os.path.basename(rp)))
        return 1
    rep = json.load(open(rp))
    if not os.path.isfile(mixp) or rep.get("sha1") != _sha1(mixp):
        print("[mix] RED  audio/mix.wav changed after scripts/mix.py measured it: mix again")
        return 1
    if rep.get("voice") is False:
        print("[mix] OK  a film with no voice: the music is the track, mastered to %s LUFS" % rep.get("lufs"))
        return 0
    if rep.get("separation_p10") is None or rep["separation_p10"] < rep.get("under", 20) - 3:
        print("[mix] RED  the music competes with the voice: separation p10 %s dB (needs >= %s)" % (rep.get("separation_p10"), rep.get("under", 20) - 3))
        return 1
    if rep.get("band_separation_p10") is not None and rep["band_separation_p10"] < rep.get("under", 20) - 5:
        print("[mix] RED  the music competes with the consonants: 1-4 kHz separation p10 %s dB (needs >= %s)"
              % (rep["band_separation_p10"], rep.get("under", 20) - 5))
        return 1
    print("[mix] OK  music %s dB under the voice (median), %s dB at the tenth percentile%s"
          % (rep["separation_median"], rep["separation_p10"], ", %s dB in 1-4 kHz" % rep["band_separation_p10"]
             if rep.get("band_separation_p10") is not None else ""))
    return 0


def _hp(f):
    from scipy.signal import butter
    return butter(2, f / (SR / 2), btype="high")


def _write(path, x):
    pcm = np.clip(x, -1, 1).astype(np.float32).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", path], input=pcm, check=True)


def main(argv):
    if argv[:1] == ["--check"]:
        if len(argv) != 2 or not os.path.isdir(argv[1]):
            print("usage: mix.py --check <film_dir>", file=sys.stderr)
            return 2
        return check(argv[1])
    _c.refuse_unknown(argv, valued=("voice", "music", "sfx", "out", "under", "lift", "sfx-gain", "lufs", "tp", "band-deep"),
                      usage=_USAGE)
    v, out = _c.argflag(argv, "voice"), _c.argflag(argv, "out")
    if not out or not (v or _c.argflag(argv, "music")):
        print(_USAGE, file=sys.stderr)
        return 2
    for p in (v, _c.argflag(argv, "music"), _c.argflag(argv, "sfx")):
        if p and not os.path.isfile(p):
            print("mix: no file %s" % p, file=sys.stderr)
            return 2
    under = float(_c.argflag(argv, "under", 20))
    rep = mix(v, _c.argflag(argv, "music"), _c.argflag(argv, "sfx"), out, under, float(_c.argflag(argv, "lift", 8)),
              float(_c.argflag(argv, "sfx-gain", 0.8)), float(_c.argflag(argv, "lufs", -14)), float(_c.argflag(argv, "tp", -2)),
              float(_c.argflag(argv, "band-deep", 9)))
    rep.update(music=_c.argflag(argv, "music"), sha1=_sha1(out))
    with open(report_path(out), "w") as f:      # what film_qc's "mix" check reads: this exact file, measured
        json.dump(rep, f, indent=1)
    print(json.dumps(rep))
    short = rep.get("separation_p10") is not None and rep["separation_p10"] < under - 3
    short_band = rep.get("band_separation_p10") is not None and rep["band_separation_p10"] < under - 5
    loud = rep.get("max_short_term") is not None and rep["max_short_term"] > float(_c.argflag(argv, "lufs", -14)) + 5
    if loud:      # EBU R128 s1 (short-form): max short-term loudness within programme + 5 LU
        print("[mix] NOTE max short-term %s LUFS is more than 5 LU over the programme: a hit or riser jumps out"
              % rep["max_short_term"])
    print("[mix] %s -> %s" % ("SHORT: the music competes with the voice" if short else
                              "SHORT: the music competes with the consonants (1-4 kHz)" if short_band else "OK", out))
    short = short or short_band
    return 1 if short else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
