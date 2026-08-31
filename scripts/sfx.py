#!/usr/bin/env python3
"""OPTIONAL sound-design layer for the Remotion cinematic tier (#8) — the two-track SFX + BGM bed that
makes a launch film read as "a film," not "a deck with narration" (huashu audio-design law).

Iron rule (huashu): audio is TWO independent layers, frequency-isolated so they don't mask each other —
  SFX (beat layer): high-freq (highpass 800Hz), 0.2–2s, FRAME-ALIGNED to the video's beats, punch.
  BGM (atmosphere):  mid/low (lowpass 4kHz), continuous, −6..−8dB under, faded in/out.
Golden ratios (Anthropic-derived): amix normalize=0 (never flatten the dynamics); SFX peak 1.0, BGM ~0.45;
restraint — do NOT cue every beat (dropping 30–50% of cues reads more dramatic than a full one).

Everything here is FREE + LOCAL: SFX are SYNTHESIZED with numpy (no API spend, no external assets, no
fabricated sources); BGM is an author track (meta.bgm=<path>) or a subtle synthesized ambient pad
(meta.bgm='auto'). Opt-in via meta.sound_design — the mix is a post-render step on out.mp4's baked
voiceover. Cannot be auditioned by the pipeline; the operator should listen before delivery.
"""
import math
import os
import shutil
import tempfile
import struct
import subprocess
import sys
import wave
import zlib

try:
    import numpy as np
except Exception:                                  # numpy is required for synthesis; degrade to a no-op
    np = None

SR = 44100
_SEED = 20260802

# huashu golden ratios
_BGM_VOL = 0.45
_SFX_HP = 800          # SFX highpass (Hz) — push to the presence band
_BGM_LP = 4000         # BGM lowpass (Hz) — keep it under the SFX
_TARGET_LUFS = -14.0


def _env(n, attack, decay):
    t = np.arange(n) / SR
    a = np.clip(t / max(1e-4, attack), 0, 1)
    d = np.exp(-np.maximum(0, t - attack) / max(1e-4, decay))
    return (a * d).astype(np.float32)


def _norm(x):
    m = float(np.max(np.abs(x))) or 1.0
    return (x / m).astype(np.float32)


# ── the synthesized cue library (deterministic) ──────────────────────────────────────────────────────
# every cue is a short mono float array in [-1,1]; the ffmpeg highpass 800 shapes it into the SFX band.
def cue(name):
    if np is None:
        return None
    # zlib.crc32 (NOT Python's hash()) — str hash() is salted by PYTHONHASHSEED, so it varies every
    # process, making the noise cues (click/whoosh) synthesize a different waveform on each render. crc32
    # is stable, so a re-render is byte-reproducible (the frame-driven determinism law, in the audio bed).
    rng = np.random.default_rng(_SEED + (zlib.crc32(name.encode("utf-8")) % 9973))
    if name == "click":                            # a decision / selection tick
        n = int(0.06 * SR); return _norm(rng.standard_normal(n) * _env(n, 0.001, 0.02)) * 0.85
    if name == "tick":                             # a small focus/progress blip
        n = int(0.05 * SR); t = np.arange(n) / SR
        return _norm(np.sin(2 * np.pi * 3200 * t) * _env(n, 0.001, 0.014)) * 0.6
    if name == "focus":                            # the visual protagonist shifts (a soft blip)
        n = int(0.16 * SR); t = np.arange(n) / SR
        return _norm(np.sin(2 * np.pi * 1500 * t) * _env(n, 0.004, 0.06)) * 0.5
    if name == "whoosh":                           # a scene transition / camera move
        n = int(0.40 * SR); t = np.arange(n) / SR
        swell = np.sin(np.pi * np.clip(t / 0.40, 0, 1))
        return _norm(rng.standard_normal(n) * swell) * 0.5
    if name == "pop":                              # an element enters
        n = int(0.12 * SR); t = np.arange(n) / SR
        f = np.linspace(880, 320, n); ph = 2 * np.pi * np.cumsum(f) / SR
        return _norm(np.sin(ph) * _env(n, 0.002, 0.05)) * 0.6
    if name == "reveal":                           # the hero / brand landing (a soft bell)
        n = int(0.95 * SR); t = np.arange(n) / SR
        parts = [880.0, 1320.0, 1760.0, 2640.0]
        x = sum(np.sin(2 * np.pi * f * t) * (0.6 ** i) for i, f in enumerate(parts))
        return _norm(x * np.exp(-t / 0.36)) * 0.85
    n = int(0.05 * SR); return np.zeros(n, dtype=np.float32)


def synth_pad(seconds):
    """A subtle ambient BGM pad (a low sustained drone with slow movement) — atmosphere, not a melody.
    Deterministic; ffmpeg lowpasses it to <4kHz. Used when meta.bgm=='auto'."""
    if np is None:
        return None
    t = np.arange(int(max(1, seconds) * SR)) / SR
    base = [110.0, 164.81, 220.0]                  # A2 + E3 + A3 — an open fifth drone
    x = np.zeros_like(t)
    for i, f in enumerate(base):
        vib = 1 + 0.0025 * np.sin(2 * np.pi * (0.05 + 0.01 * i) * t)   # slow detune
        x = x + np.sin(2 * np.pi * f * vib * t) * (0.5 ** i)
    x = x * (0.82 + 0.18 * np.sin(2 * np.pi * 0.06 * t))               # slow swell
    return _norm(x) * 0.7


def _write_wav(path, arr):
    a = np.clip(arr, -1.0, 1.0)
    pcm = (a * 32767.0).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm)


# ── cue planning: pin cues to the video's BEATS (frame-exact), with restraint ─────────────────────────
def plan_cues(scenes, fps):
    """Given a scene list (each with durationInFrames; optional shots[].startFrame), return a cue list
    [(t_seconds, cue_name, gain)] aligned to beats: a whoosh at each MARKED scene transition (anticipatory,
    −2 frames; a plain cross-fade seam stays QUIET so the ear marks the same ~2-3 seams the eye does — the
    carry match-cut gets a softer swell), a focus tick at each interior shot arrival, a pop at each element's
    enter, and a reveal bell at the LAST scene's final shot. Then applies restraint — caps density at ~4 cues
    / 10s, dropping the lowest-priority (ticks/pops) first so the film breathes."""
    cues = []                                       # (t, name, gain, priority) — lower priority dropped first
    t0 = 0.0
    n = len(scenes)
    for si, sc in enumerate(scenes):
        dur = float(sc.get("durationInFrames") or 0) / fps
        if si > 0:                                  # scene transition — sound only the MARKED seams
            tt = max(0.0, t0 - 2.0 / fps)           # 2 frames early (anticipation)
            if "transitionIn" in sc:                # the seam grammar is DECLARED (remotion tier)
                ti = sc.get("transitionIn")
                if ti and ti.get("type") == "carry":
                    cues.append((tt, "whoosh", 0.32, 1))    # a gentle match-cut swell (softer than a hard cut)
                elif ti:                            # slide / wipe / clock — a motion whoosh
                    cues.append((tt, "whoosh", 0.5, 0))
                # else: an unmarked FADE seam — no cue (the fade is visually gentle; restraint)
            else:                                   # grammar not declared (legacy caller) — unchanged behavior
                cues.append((tt, "whoosh", 0.5, 0))
        shots = sc.get("shots") or []
        for k, sh in enumerate(shots):
            sf = float(sh.get("startFrame") or 0)
            if k > 0:                               # camera arrives on a new subject — focus
                cues.append((t0 + sf / fps, "focus", 0.42, 2))
        for el in ((sc.get("stage") or {}).get("elements") or []):
            en = el.get("enterAtFrame")
            if isinstance(en, (int, float)) and en > 0 and el.get("kind") not in ("grid", "floor", "fill"):
                cues.append((t0 + float(en) / fps, "pop", 0.4, 3))
        if si == n - 1 and shots:                   # the closing hero / reveal bell
            cues.append((t0 + float(shots[-1].get("startFrame") or 0) / fps, "reveal", 0.7, 1))
        t0 += dur
    total = t0 or 1.0
    cap = max(2, int(round((total / 10.0) * 4)))    # <=4 cues per 10s (huashu density band)
    if len(cues) > cap:                             # restraint: drop lowest-priority (highest number) first
        cues.sort(key=lambda c: (c[3], c[0]))
        cues = sorted(cues[:cap], key=lambda c: c[0])
    else:
        cues.sort(key=lambda c: c[0])
    return [(t, name, g) for (t, name, g, _p) in cues]


def build_sfx_track(cues, total_seconds, out_wav):
    """Render the planned cues into ONE full-length SFX WAV (each cue placed at its sample offset), so the
    ffmpeg mix is a clean 2–3 input graph. Deterministic."""
    if np is None:
        return False
    buf = np.zeros(int((total_seconds + 1.0) * SR), dtype=np.float32)
    for (t, name, g) in cues:
        c = cue(name)
        if c is None or not len(c):
            continue
        i = int(t * SR)
        j = min(len(buf), i + len(c))
        buf[i:j] += c[: j - i] * float(g)
    buf = np.tanh(buf * 0.9)                         # soft-clip guard (never hard-clip the sum)
    _write_wav(out_wav, buf)
    return True


# ── the audio chain, and how far it actually MOVES a sound ────────────────────────────────────────────

def filtergraph(dur, has_bgm):
    """The one filtergraph. `mix()` renders through it and `measure_offset()` measures through it.

    Written twice, the probe would certify a chain the film does not use — which is the whole failure this
    module was audited for. A cue's time is computed frame-exactly (a seam whoosh lands 2 frames early, on
    purpose) and then handed to an encoder nobody had ever measured.
    """
    fc = ["[1:a]highpass=f=%d,volume=1.0[sfx]" % _SFX_HP]
    mix_ins, n_in = "[0:a][sfx]", 2
    if has_bgm:
        fc.append("[2:a]lowpass=f=%d,afade=in:st=0:d=0.3,afade=out:st=%.2f:d=1.5,volume=%.2f[bgm]"
                  % (_BGM_LP, max(0.0, dur - 1.5), _BGM_VOL))
        mix_ins, n_in = "[0:a][bgm][sfx]", 3
    fc.append("%samix=inputs=%d:duration=first:normalize=0,loudnorm=I=%.1f:TP=-1.5:LRA=11[a]"
              % (mix_ins, n_in, _TARGET_LUFS))
    return ";".join(fc)


PROBE_AT = 2.0                  # where the probe click is placed, in seconds
PROBE_SECONDS = 5.0
MAX_SANE_SHIFT = 2.0            # frames — beyond this the measurement is not believed, and says so


def measure_offset(fps=30, has_bgm=False, workdir=None):
    """Send a click through the REAL chain and report how far it moved, in seconds. None if unmeasurable.

    WHY THIS IS MEASURED AND NOT ASSUMED. The obvious move was to copy a compensation constant: the
    reference implementation measured its own encoder holding a click back by 2032 samples (~1.27 frames at
    30fps) and subtracts that. Measured HERE — container start_time, two-input and three-input graphs,
    clicks at 0.5s / 2.0s / 4.2s — this chain moves a sound by exactly 0 samples: ffmpeg signals the AAC
    priming and the decoder skips it, and loudnorm in this configuration adds no net delay. Subtracting a
    borrowed 1.27 frames would have INTRODUCED the error it was meant to remove.
    """
    if np is None or not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return None
    tmp = workdir or tempfile.mkdtemp(prefix="sfx_cal_")
    try:
        n = int(PROBE_SECONDS * SR)
        click = np.zeros(n, dtype=np.float32); click[int(PROBE_AT * SR)] = 1.0
        _write_wav(os.path.join(tmp, "click.wav"), click)
        _write_wav(os.path.join(tmp, "silent.wav"), np.zeros(n, dtype=np.float32))
        base = os.path.join(tmp, "base.mp4")
        # The probe's base is built like a delivered film: H.264 video plus an already-baked AAC voice track,
        # because it is that SECOND encode of an existing audio stream the cue has to survive.
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                        "-i", "color=c=black:s=320x180:r=%d:d=%g" % (fps, PROBE_SECONDS),
                        "-i", os.path.join(tmp, "silent.wav"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", base], check=True)
        ins = ["-i", base, "-i", os.path.join(tmp, "click.wav")]
        if has_bgm:
            _write_wav(os.path.join(tmp, "bgm.wav"), np.zeros(n, dtype=np.float32))
            ins += ["-i", os.path.join(tmp, "bgm.wav")]
        mixed = os.path.join(tmp, "mixed.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error"] + ins +
                       ["-filter_complex", filtergraph(PROBE_SECONDS, has_bgm), "-map", "0:v", "-map", "[a]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", mixed], check=True)
        back = os.path.join(tmp, "back.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mixed, "-ac", "1", "-ar", str(SR),
                        "-f", "wav", back], check=True)
        with wave.open(back, "rb") as w:
            a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32)
        if not len(a) or float(np.max(np.abs(a))) <= 0:
            return None
        # The AUDIO's own timeline is only half the question. A container that starts the two streams at
        # different times shifts every cue against the picture without moving it inside its own track, so
        # the stream offset is added rather than assumed to be zero.
        return (int(np.argmax(np.abs(a))) / float(SR) - PROBE_AT) + _stream_skew(mixed)
    except Exception:
        return None
    finally:
        if workdir is None:
            shutil.rmtree(tmp, ignore_errors=True)


def _stream_skew(mp4):
    """audio start_time - video start_time, in seconds. A sound correct inside its own track still arrives
    late if the container starts that track late."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time",
                            "-of", "csv=p=0", mp4], capture_output=True, text=True, check=True)
        st = {}
        for line in r.stdout.strip().splitlines():
            kind, _, val = line.partition(",")
            try:
                st[kind.strip()] = float(val)
            except ValueError:
                pass
        return st.get("audio", 0.0) - st.get("video", 0.0)
    except Exception:
        return 0.0


# ── the mix: frequency-isolated two-track under the voiceover, muxed back into the video ──────────────
def mix(out_dir, mp4, scenes, meta, fps):
    """Post-render: overlay the SFX track (+ optional BGM) onto out.mp4's baked voiceover using huashu's
    frequency-isolation filtergraph, then mux back. Returns True if it re-wrote the video. Best-effort:
    no numpy / no ffmpeg / no cues -> leaves the video untouched."""
    if np is None or not shutil.which("ffmpeg"):
        print("[sfx] skipped (numpy/ffmpeg unavailable)"); return False
    dur = _probe_duration(mp4)
    if not dur:
        print("[sfx] skipped (could not probe video duration)"); return False
    cues = plan_cues(scenes, fps)
    sdir = os.path.join(out_dir, ".sfx"); os.makedirs(sdir, exist_ok=True)
    sfx_wav = os.path.join(sdir, "_sfx.wav")
    if not cues:
        print("[sfx] no cues planned — video unchanged"); return False

    # optional BGM: an author track (meta.bgm=path) or a synthesized pad (meta.bgm='auto')
    bgm_wav = None
    bgm = meta.get("bgm")
    if bgm == "auto":
        bgm_wav = os.path.join(sdir, "_bgm.wav"); _write_wav(bgm_wav, synth_pad(dur))
    elif isinstance(bgm, str) and bgm and os.path.exists(os.path.join(out_dir, bgm)):
        bgm_wav = os.path.join(out_dir, bgm)

    # SELF-CALIBRATING, never a borrowed constant. The chain is measured as it is about to be used, so a
    # different ffmpeg, a codec change or an added filter is corrected for instead of silently shifting every
    # cue. Measured 0.00 frames here; a measurement beyond MAX_SANE_SHIFT is not trusted and says so out loud
    # rather than dragging the cues somewhere arbitrary.
    lat = measure_offset(fps, has_bgm=bool(bgm_wav))
    if lat is None:
        print("[sfx] WARNING: could not measure the audio chain's offset — cues placed uncompensated")
        lat = 0.0
    elif abs(lat) * fps > MAX_SANE_SHIFT:
        print("[sfx] WARNING: measured offset %+.2f frames is beyond the sane range — NOT compensating; "
              "the mix is unchanged but the cue timing is suspect" % (lat * fps))
        lat = 0.0
    else:
        print("[sfx] audio chain offset %+.2f frames%s" % (lat * fps, " (compensated)" if lat else ""))
    if lat:
        cues = [(max(0.0, t - lat), name, g) for (t, name, g) in cues]
    if not build_sfx_track(cues, dur, sfx_wav):
        print("[sfx] could not build the cue track — video unchanged"); return False

    inputs = ["-i", mp4, "-i", sfx_wav] + (["-i", bgm_wav] if bgm_wav else [])
    fc = [filtergraph(dur, bool(bgm_wav))]
    out2 = os.path.join(out_dir, "_snd.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", ";".join(fc),
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out2]
    try:
        subprocess.run(cmd, check=True)
        shutil.move(out2, mp4)
        print("[sfx] mixed %d cue(s)%s -> %s" % (len(cues), " + BGM" if bgm_wav else "", os.path.basename(mp4)))
        return True
    except Exception as e:
        print("[sfx] mix failed (%s) — video unchanged" % e)
        try:
            os.path.exists(out2) and os.unlink(out2)
        except OSError:
            pass
        return False


def _probe_duration(mp4):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", mp4], capture_output=True, text=True, check=True)
        return float(r.stdout.strip())
    except Exception:
        return None


if __name__ == "__main__":                          # CLI: preview the cue plan for a deck (renderer-agnostic)
    import json
    if "--calibrate" in sys.argv[1:]:
        # `python3 scripts/sfx.py --calibrate` — send a click through the real chain and report where it
        # comes out. This is the one number nothing in this pipeline had ever measured: cues are planned to
        # the frame, and then handed to an encoder on trust.
        fps = 30
        for a in sys.argv[1:]:
            if a.startswith("--fps="):
                fps = int(a.split("=", 1)[1])
        bad = False
        for has_bgm in (False, True):
            off = measure_offset(fps, has_bgm=has_bgm)
            label = "SFX + BGM" if has_bgm else "SFX only "
            if off is None:
                print("[sfx] %s  UNMEASURABLE (needs numpy + ffmpeg + ffprobe)" % label); bad = True
            else:
                print("[sfx] %s  %+.4fs  = %+.3f frames @%dfps%s"
                      % (label, off, off * fps, fps, "" if abs(off) * fps < 0.5 else "   <-- OVER HALF A FRAME"))
                bad = bad or abs(off) * fps >= 0.5
        sys.exit(1 if bad else 0)
    out_dir = sys.argv[1]
    data = json.load(open(os.path.join(out_dir, "storyboard.json")))
    fps = int((data.get("meta") or {}).get("fps", 30))
    _TR = 12   # remotion cross-dissolve overlap (frames); the -TR keeps whooshes on the real transitions
    scenes = [{"durationInFrames": max(1, int(round(float(s.get("duration") or 0) * fps)) - _TR)}
              for s in data.get("slides", [])]
    if scenes:
        scenes[-1]["shots"] = [{"startFrame": 0}]   # closing reveal bell
    cs = plan_cues(scenes, fps)
    print("planned %d cues:" % len(cs))
    for (t, name, g) in cs:
        print("  %6.2fs  %-7s  %.2f" % (t, name, g))
