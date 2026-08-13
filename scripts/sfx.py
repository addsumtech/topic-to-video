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
    [(t_seconds, cue_name, gain)] aligned to beats: a whoosh at each scene transition (anticipatory, −2
    frames), a focus tick at each interior shot arrival, a pop at each element's enter, and a reveal bell
    at the LAST scene's final shot. Then applies restraint — caps density at ~4 cues / 10s, dropping the
    lowest-priority (ticks/pops) first so the film breathes."""
    cues = []                                       # (t, name, gain, priority) — lower priority dropped first
    t0 = 0.0
    n = len(scenes)
    for si, sc in enumerate(scenes):
        dur = float(sc.get("durationInFrames") or 0) / fps
        if si > 0:                                  # scene transition — whoosh, 2 frames early (anticipation)
            cues.append((max(0.0, t0 - 2.0 / fps), "whoosh", 0.5, 0))
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
    if not (cues and build_sfx_track(cues, dur, sfx_wav)):
        print("[sfx] no cues planned — video unchanged"); return False

    # optional BGM: an author track (meta.bgm=path) or a synthesized pad (meta.bgm='auto')
    bgm_wav = None
    bgm = meta.get("bgm")
    if bgm == "auto":
        bgm_wav = os.path.join(sdir, "_bgm.wav"); _write_wav(bgm_wav, synth_pad(dur))
    elif isinstance(bgm, str) and bgm and os.path.exists(os.path.join(out_dir, bgm)):
        bgm_wav = os.path.join(out_dir, bgm)

    inputs = ["-i", mp4, "-i", sfx_wav]
    fc = ["[1:a]highpass=f=%d,volume=1.0[sfx]" % _SFX_HP]
    mix_ins = "[0:a][sfx]"; n_in = 2
    if bgm_wav:
        inputs += ["-i", bgm_wav]
        fc.append("[2:a]lowpass=f=%d,afade=in:st=0:d=0.3,afade=out:st=%.2f:d=1.5,volume=%.2f[bgm]"
                   % (_BGM_LP, max(0.0, dur - 1.5), _BGM_VOL))
        mix_ins = "[0:a][bgm][sfx]"; n_in = 3
    fc.append("%samix=inputs=%d:duration=first:normalize=0,loudnorm=I=%.1f:TP=-1.5:LRA=11[a]"
              % (mix_ins, n_in, _TARGET_LUFS))
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
