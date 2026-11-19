#!/usr/bin/env python3
"""mix — voice, music and SFX into one master, the music set UNDER the voice by measurement, not by a guessed gain.

    python3 scripts/mix.py --voice audio/voice.wav [--music audio/score.wav] [--sfx audio/sfx.wav] --out audio/mix.wav
        [--under 20] [--lift 8] [--sfx-gain 0.8] [--lufs -14] [--tp -2]
    python3 scripts/mix.py --check <film_dir>        # film_qc "mix": the shipped mix is this script's, as measured

While the voice speaks, the music sits `--under` dB below it (measured RMS over the speech, 20 by default: WCAG 1.4.7
asks background sound to be at least 20 dB under speech, and mixers use 18-24); between lines (a pause of 0.6 s or
more) it rises `--lift` dB, never above 6 dB under the voice. The ducking follows the voice track itself: down 0.12 s
before each line starts, back up over 0.5 s after it ends. SFX are high-passed at 160 Hz. The sum is mastered to
`--lufs` integrated with true peak at or under `--tp`. It prints the separation it reached (voice over music, per
half second of speech) and exits 1 when a tenth of the speech has less than `--under` - 3 dB: the music would
compete with the words. Beside the mix it writes <name>.mix.json (the measures and the mix's SHA-1), which
film_qc's "mix" check reads: a film with a music stem in audio/ must ship that very mix.

WHY. A launch film mixed its own score at a fixed gain under a sidechain compressor; measured, the music sat a median
5 dB under the voice (job-hunt film, 2026-11-19): loud enough to compete with every word. Studies of narrated
instruction find music costs recall when it competes with the narration (Moreno & Mayer 2000), and the mixing norm
is ~20 dB under speech.
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


def mix(voice_p, music_p, sfx_p, out_p, under=20.0, lift=8.0, sfx_gain=0.8, lufs=-14.0, tp=-2.0):
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
        sep = separation(voice, bed, mask)
        report.update(separation_median=round(float(np.median(sep)), 1) if len(sep) else None,
                      separation_p10=round(float(np.percentile(sep, 10)), 1) if len(sep) else None,
                      music_gain_db=round(float(np.median(g[mask[:k]])), 1))
        total = total + bed
    if sfx_p:
        from scipy.signal import lfilter
        b, a = _hp(160)                       # on the SFX alone: in the master chain it would thin the voice too
        total = total + lfilter(b, a, load(sfx_p, n) * sfx_gain, axis=0)
    tmp = out_p + ".sum.wav"
    _write(tmp, total)
    # two passes: measure, then a linear gain to the target (one pass guesses its gain as it goes and lands off target)
    ln = "loudnorm=I=%g:TP=%g:LRA=20" % (lufs, tp - 0.5)
    m = subprocess.run(["ffmpeg", "-nostats", "-i", tmp, "-af", ln + ":print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    second = (ln + ":linear=true:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s"
              % (j["input_i"], j["input_tp"], j["input_lra"], j["input_thresh"], j["target_offset"]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    second + ",alimiter=limit=%.4f:level=false:attack=2:release=60" % 10 ** ((tp - 0.3) / 20), "-ar", str(SR), out_p], check=True)
    os.remove(tmp)
    r = subprocess.run(["ffmpeg", "-nostats", "-i", out_p, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    for line in r.splitlines():
        s = line.strip()
        if s.startswith("I:"):
            report["lufs"] = float(s.split()[1])
        if s.startswith("Peak:"):
            report["true_peak"] = float(s.split()[1])
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
    if rep.get("separation_p10") is None or rep["separation_p10"] < rep.get("under", 20) - 3:
        print("[mix] RED  the music competes with the voice: separation p10 %s dB (needs >= %s)" % (rep.get("separation_p10"), rep.get("under", 20) - 3))
        return 1
    print("[mix] OK  music %s dB under the voice (median), %s dB at the tenth percentile" % (rep["separation_median"], rep["separation_p10"]))
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
    _c.refuse_unknown(argv, valued=("voice", "music", "sfx", "out", "under", "lift", "sfx-gain", "lufs", "tp"), usage=_USAGE)
    v, out = _c.argflag(argv, "voice"), _c.argflag(argv, "out")
    if not v or not out:
        print(_USAGE, file=sys.stderr)
        return 2
    for p in (v, _c.argflag(argv, "music"), _c.argflag(argv, "sfx")):
        if p and not os.path.isfile(p):
            print("mix: no file %s" % p, file=sys.stderr)
            return 2
    under = float(_c.argflag(argv, "under", 20))
    rep = mix(v, _c.argflag(argv, "music"), _c.argflag(argv, "sfx"), out, under, float(_c.argflag(argv, "lift", 8)),
              float(_c.argflag(argv, "sfx-gain", 0.8)), float(_c.argflag(argv, "lufs", -14)), float(_c.argflag(argv, "tp", -2)))
    rep.update(music=_c.argflag(argv, "music"), sha1=_sha1(out))
    with open(report_path(out), "w") as f:      # what film_qc's "mix" check reads: this exact file, measured
        json.dump(rep, f, indent=1)
    print(json.dumps(rep))
    short = rep.get("separation_p10") is not None and rep["separation_p10"] < under - 3
    print("[mix] %s -> %s" % ("SHORT: the music competes with the voice" if short else "OK", out))
    return 1 if short else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
