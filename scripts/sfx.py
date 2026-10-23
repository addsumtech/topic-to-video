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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common                                                   # noqa: E402
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
_SFX_LP = 110          # SFX LOW band (Hz) — an impact's body, kept under the voice's fundamentals
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
# gains for the sounds a board's own events ask for (plan_cues `events`)
EVENT_GAIN = {"click": 0.6}

def cue(name):
    if np is None:
        return None
    # zlib.crc32 (NOT Python's hash()) — str hash() is salted by PYTHONHASHSEED, so it varies every
    # process, making the noise cues (click/whoosh) synthesize a different waveform on each render. crc32
    # is stable, so a re-render is byte-reproducible (the frame-driven determinism law, in the audio bed).
    rng = np.random.default_rng(_SEED + (zlib.crc32(name.encode("utf-8")) % 9973))
    if name == "click":                            # a mouse button: the press, then its release
        # A MOUSE CLICK IS TWO KNOCKS, NOT A HISS. This was 60 ms of white noise — energy spread flat to 22 kHz, a
        # "tsss" a viewer heard as wrong on the first stage film ("鼠标点击的声音不是很好"). A switch is a press and a
        # release ~80 ms apart, each a sub-millisecond contact edge ringing the housing's few resonances for a few
        # milliseconds; the release is softer and a little higher. The resonances sit 1.6-4.7 kHz — inside the SFX
        # bus's high band (`_SFX_HP`) — and the faint body at 95 Hz inside its low band, so the filtergraph keeps
        # the whole sound rather than the part a 110-800 Hz body would lose.
        n = int(0.13 * SR); t = np.arange(n) / SR

        def knock(t0, pitch, gain):
            tt = np.maximum(0.0, t - t0)
            on = t >= t0
            ring = (1.00 * np.sin(2 * np.pi * 2900 * pitch * tt) * np.exp(-tt / 0.0028)
                    + 0.55 * np.sin(2 * np.pi * 4700 * pitch * tt) * np.exp(-tt / 0.0016)
                    + 0.40 * np.sin(2 * np.pi * 1650 * pitch * tt) * np.exp(-tt / 0.0045)
                    + 0.25 * np.sin(2 * np.pi * 95 * tt) * np.exp(-tt / 0.010))
            edge = np.convolve(rng.standard_normal(n) * np.exp(-tt / 0.0006), np.ones(4) / 4, mode="same")
            return np.where(on, (ring + 0.35 * edge) * gain, 0.0)

        return _norm(knock(0.0, 1.0, 1.0) + knock(0.082, 1.12, 0.45)) * 0.85
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
    # ── THE FILM VOCABULARY. Borrowed from a mature peer library's sound case law, where the first version
    # chose SFX by UI EVENT (click / drop / confirmation) and the user killed it in one listen: "太像游戏了" —
    # it sounded like a game. Film sound is chosen by PICTURE KIND, not event: whoosh (a move), impact (a
    # landing), riser (the build before it), sparkle (the afterglow). The three below complete that set; the
    # event cues above are kept so nothing already authored changes, but the planner no longer closes a film
    # on a bell.
    if name == "riser":                            # the build: bright noise climbing for ~1.2s into the hit
        n = int(1.2 * SR); t = np.arange(n) / SR
        climb = (t / 1.2) ** 1.6                                   # accelerating, like tension
        f = 300 + 2200 * climb; ph = 2 * np.pi * np.cumsum(f) / SR
        body = rng.standard_normal(n) + 0.35 * np.sin(ph)
        # ONE climb, not two: the first draft multiplied the body by `climb` and then enveloped it by `climb`
        # again, and measured through the real chain the first 0.4s of the build sat 54dB down — inaudible,
        # so the "1.2s riser" was a 0.5s swell. The envelope alone climbs; its floor is where the ear picks
        # the build up (-16dB under its end).
        return _norm(body * (0.15 + 0.85 * climb)) * 0.55
    if name == "impact":                           # the landing: a bright crack over a low body
        n = int(0.55 * SR); t = np.arange(n) / SR
        crack = rng.standard_normal(n) * _env(n, 0.001, 0.035)      # the transient — survives the SFX highpass
        f = 62.0 * np.exp(-t / 0.12) + 34.0                          # the body: a pitch-dropping thump
        ph = 2 * np.pi * np.cumsum(f) / SR
        body = np.sin(ph) * _env(n, 0.002, 0.22)                     # lives under 110Hz — the LOW bus carries it
        return _norm(0.55 * crack + 1.0 * body) * 0.95
    if name == "sparkle":                          # the afterglow: high partials shimmering out over ~1.4s
        n = int(1.4 * SR); t = np.arange(n) / SR
        parts = [4200.0, 5600.0, 7100.0, 8900.0]
        x = sum(np.sin(2 * np.pi * f * t + i) * (0.7 ** i) * (1 + 0.35 * np.sin(2 * np.pi * (5.5 + i) * t))
                for i, f in enumerate(parts))
        return _norm(x * np.exp(-t / 0.45) * _env(n, 0.01, 1.0)) * 0.42
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


# The closing sentence's shape, in FRAMES relative to the landing (their template: f945 → f980 → f1005).
SENTENCE_RISER_LEAD = 35
SENTENCE_SPARKLE_LAG = 25
SPARKLE_MIN_TAIL_S = 0.6     # the sparkle must have this much film left to ring into


# ── cue planning: pin cues to the video's BEATS (frame-exact), with restraint ─────────────────────────
def plan_cues(scenes, fps, events_only=False):
    """Given a scene list (each with durationInFrames; optional shots[].startFrame), return a cue list
    [(t_seconds, cue_name, gain)] aligned to beats: a whoosh at each MARKED scene transition (anticipatory,
    −2 frames; a plain cross-fade seam stays QUIET so the ear marks the same ~2-3 seams the eye does — the
    carry match-cut gets a softer swell), a focus tick at each interior shot arrival, a pop at each element's
    enter, and the CLOSING SENTENCE (riser → impact → sparkle) at the LAST scene's final shot. Then applies
    restraint — caps density at ~4 cues / 10s, dropping the lowest-priority (ticks/pops) first so the film
    breathes; the sentence is one landing and costs the cap ONE slot."""
    cues = []                                       # (t, name, gain, priority) — lower priority dropped first
    # AUTHORED EVENTS — a stage run's click lands on the word that names it (scenes[k]["events"], seconds into the
    # scene: scripts/stage_runs.py `sound_events`). They are the film's own actions, not decoration, so the density
    # cap never drops them; with `events_only` they are the whole track (a film without the SFX bed still clicks).
    authored = []
    t0 = 0.0
    n = len(scenes)
    land = None                                     # the closing landing, in seconds — set by the last scene
    for si, sc in enumerate(scenes):
        dur = float(sc.get("durationInFrames") or 0) / fps
        shots = sc.get("shots") or []
        seam_cue = None
        if si > 0:                                  # scene transition — sound only the MARKED seams
            tt = max(0.0, t0 - 2.0 / fps)           # 2 frames early (anticipation)
            if "transitionIn" in sc:                # the seam grammar is DECLARED (remotion tier)
                ti = sc.get("transitionIn")
                if ti and ti.get("type") == "carry":
                    seam_cue = (tt, "whoosh", 0.32, 1)      # a gentle match-cut swell (softer than a hard cut)
                elif ti:                            # slide / wipe / clock — a motion whoosh
                    seam_cue = (tt, "whoosh", 0.5, 0)
                # else: an unmarked FADE seam — no cue (the fade is visually gentle; restraint)
            else:                                   # grammar not declared (legacy caller) — unchanged behavior
                seam_cue = (tt, "whoosh", 0.5, 0)
        if si == n - 1 and shots:
            land = t0 + float(shots[-1].get("startFrame") or 0) / fps
            # The film's real caller lands the close on the last scene's ARRIVAL (its one shot starts at frame
            # 0), which puts the impact ON the seam. Then the riser IS that seam's sound — build across the cut,
            # land — and a whoosh two frames before an impact would be two sounds for one move. Dropped.
            if seam_cue is not None and abs(land - t0) <= 3.0 / fps:
                seam_cue = None
        if seam_cue is not None:
            cues.append(seam_cue)
        for k, sh in enumerate(shots):
            sf = float(sh.get("startFrame") or 0)
            if k > 0:                               # camera arrives on a new subject — focus
                cues.append((t0 + sf / fps, "focus", 0.42, 2))
        for ev in (sc.get("events") or []):
            if isinstance(ev, dict) and isinstance(ev.get("t"), (int, float)) and ev.get("name") in EVENT_GAIN:
                authored.append((t0 + float(ev["t"]), ev["name"], EVENT_GAIN[ev["name"]], -1))
        if events_only:
            t0 += dur
            continue
        for el in ((sc.get("stage") or {}).get("elements") or []):
            en = el.get("enterAtFrame")
            if isinstance(en, (int, float)) and en > 0 and el.get("kind") not in ("grid", "floor", "fill"):
                cues.append((t0 + float(en) / fps, "pop", 0.4, 3))
        t0 += dur
    total = t0 or 1.0
    sentence = []
    if events_only:
        return [(t, name, g) for (t, name, g, _p) in sorted(authored, key=lambda c: c[0])]
    if land is not None:
        # THE CLOSING SENTENCE — riser → impact → sparkle, the film's one big landing. The peer library's
        # template pins it at f945 → f980 → f1005 (a 35f build, a 25f afterglow) and records it as the one
        # passage never changed after the sound direction was set: build, land, glow, in that order, the
        # impact being the film's loudest SFX. It replaces the bell that used to sit here — a bell is the
        # pluck/bloop timbre class their case law calls a game sound. The riser starts BEFORE the landing even
        # when that is inside the previous scene: a build that crosses the cut is the point of a build. The
        # sparkle is the sentence's full stop and needs room to ring; a film that ends within its lag pulls it
        # in, and a film with no room at all drops it and says so — a sparkle cut off by the end is a glitch,
        # not a shorter sparkle.
        sentence.append((max(0.0, land - SENTENCE_RISER_LEAD / fps), "riser", 0.5, 0))
        sentence.append((land, "impact", 0.95, 0))
        sp = min(land + SENTENCE_SPARKLE_LAG / fps, total - SPARKLE_MIN_TAIL_S)
        if sp > land:
            # 0.30, not louder: measured on a real narrated film the sparkle's partials (4-9kHz) sat at the same
            # energy as the closing narration's sibilance band; the glow is under the voice, never beside it.
            sentence.append((sp, "sparkle", 0.30, 0))
        else:
            print("[sfx] closing sparkle dropped: the film ends %.2fs after its landing (needs %.1fs to ring)"
                  % (total - land, SPARKLE_MIN_TAIL_S))
    cap = max(2, int(round((total / 10.0) * 4)))    # <=4 cues per 10s (huashu density band)
    if sentence:
        cap = max(1, cap - 1)                       # the sentence is ONE landing — one slot, never three
    if len(cues) > cap:                             # restraint: drop lowest-priority (highest number) first
        cues.sort(key=lambda c: (c[3], c[0]))
        cues = cues[:cap]
    cues = sorted(cues + sentence + authored, key=lambda c: c[0])
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
    # TWO BANDS FROM ONE INPUT. The SFX bus has always been highpassed at 800Hz so it sits above the voice —
    # and an impact's body is a 35-60Hz thump, which that highpass deletes entirely: a landing would ship
    # as a click. It is split INSIDE the graph rather than fed as a second file so that the probe keeps
    # measuring exactly the chain the film renders through (a broadband click lands in both bands), and so
    # `amix` stays written once. The low band sits UNDER the voice (fundamentals from ~85Hz up, intelligibility
    # in 300Hz-4kHz), which is the same isolation argument as the high band from the other side.
    fc = ["[1:a]asplit[sh][sl]",
          "[sh]highpass=f=%d,volume=1.0[sfxhi]" % _SFX_HP,
          "[sl]lowpass=f=%d,volume=1.0[sfxlo]" % _SFX_LP]
    mix_ins, n_in = "[0:a][sfxhi][sfxlo]", 3
    if has_bgm:
        fc.append("[2:a]lowpass=f=%d,afade=in:st=0:d=0.3,afade=out:st=%.2f:d=1.5,volume=%.2f[bgm]"
                  % (_BGM_LP, max(0.0, dur - 1.5), _BGM_VOL))
        mix_ins, n_in = "[0:a][bgm][sfxhi][sfxlo]", 4
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
def mix(out_dir, mp4, scenes, meta, fps, events_only=False):
    """Post-render: overlay the SFX track (+ optional BGM) onto out.mp4's baked voiceover using huashu's
    frequency-isolation filtergraph, then mux back. Returns True if it re-wrote the video. Best-effort:
    no numpy / no ffmpeg / no cues -> leaves the video untouched."""
    if np is None or not shutil.which("ffmpeg"):
        print("[sfx] skipped (numpy/ffmpeg unavailable)"); return False
    dur = _probe_duration(mp4)
    if not dur:
        print("[sfx] skipped (could not probe video duration)"); return False
    cues = plan_cues(scenes, fps, events_only=events_only)
    sdir = os.path.join(out_dir, ".sfx"); os.makedirs(sdir, exist_ok=True)
    sfx_wav = os.path.join(sdir, "_sfx.wav")
    if not cues:
        print("[sfx] no cues planned — video unchanged"); return False

    # optional BGM: an author track (meta.bgm=path) or a synthesized pad (meta.bgm='auto')
    bgm_wav = None
    bgm = None if events_only else meta.get("bgm")   # the score belongs to the SFX bed, not to a stage's clicks
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
        if bgm_wav:
            # TWO DELIVERIES FROM ONE TIMELINE. A film with a BGM also ships a `.nobgm.mp4` twin — same cues,
            # same frames, no music — so the user can score it themselves without a re-render. Borrowed from
            # the peer library's delivery rule for scored films; the twin is a second pass through the same
            # graph with the BGM input absent, never a separate timeline.
            twin = os.path.splitext(mp4)[0] + ".nobgm.mp4"
            cmd2 = ["ffmpeg", "-y", "-v", "error", "-i", mp4, "-i", sfx_wav, "-filter_complex",
                    filtergraph(dur, False), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", twin]
            subprocess.run(cmd2, check=True)
            print("[sfx] no-BGM twin -> %s" % os.path.basename(twin))
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
        # `--fps 60` (no `=`) used to fall through to 30 in silence, and every number this prints is in
        # FRAMES — the offset would be reported against a frame length the run never used. Both spellings,
        # and an argument this tool does not know stops it. See scripts/_common.argflag.
        _common.refuse_unknown(sys.argv[1:], valued=("fps",), switches=("calibrate",),
                               usage="usage: sfx.py --calibrate [--fps=N | --fps N]")
        fps = int(_common.argflag(sys.argv[1:], "fps", 30))
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
    import stage_runs as _sr                   # no seam inside a stage run, so no overlap to remove there
    _sl = data.get("slides", [])
    _jn = _sr.joined_flags(_sl)
    scenes = [{"durationInFrames": max(1, int(round(float(s.get("duration") or 0) * fps))
                                   - (0 if k + 1 < len(_sl) and _jn[k + 1] else _TR))}
              for k, s in enumerate(_sl)]
    if scenes:
        scenes[-1]["shots"] = [{"startFrame": 0}]   # the closing sentence lands on the last beat's arrival
    cs = plan_cues(scenes, fps)
    print("planned %d cues:" % len(cs))
    for (t, name, g) in cs:
        print("  %6.2fs  %-7s  %.2f" % (t, name, g))
