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
import json
import math
import os
import re
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
_BGM_VOL = 0.30        # under a sidechain duck: ≥10 LU under the voice while it speaks (references/craft-research.md §3)
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
        # AIR MOVING PAST, NOT HISS. Flat noise under a swell has the same flat spectrum the old click had — a
        # "tsss". A whoosh is noise through a band that SWEEPS (here 300 Hz -> 5 kHz) as it swells and falls away
        # (references/craft-research.md §3); the swell peaks 60% in, and the mix lands that peak on the seam.
        n = int(0.50 * SR); t = np.arange(n) / SR
        fc = 300.0 * (5000.0 / 300.0) ** np.clip(t / 0.50, 0, 1)
        x = rng.standard_normal(n)
        out = np.empty(n, dtype=np.float64)
        low = band = 0.0
        q = 1.0 / 1.4
        for i in range(n):                          # a Chamberlin state-variable band-pass, its centre moving
            fk = 2.0 * np.sin(np.pi * fc[i] / SR)
            low += fk * band
            high = x[i] - low - q * band
            band += fk * high
            out[i] = band
        swell = np.where(t < 0.30, (t / 0.30) ** 1.5, np.exp(-(t - 0.30) / 0.07))
        return _norm(out * swell) * 0.5
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


# WHERE EACH ANCHORED SEAM IS FASTEST, as a share of the seam — READ from remotion/src/seams.tsx `SEAM_PEAK`, the one
# definition, so the sound cannot drift off the picture it marks: a punch's impact on its cut, a through-window's and
# a grow's whoosh on the frame that moves most, a container's soft swell where Material's curve is fastest.
_SEAMS_TSX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "seams.tsx")


def _seam_peaks():
    import re as _re
    src = open(_SEAMS_TSX, encoding="utf-8").read()
    m = _re.search(r"export const SEAM_PEAK = \{([^}]*)\}", src)
    if not m:
        raise RuntimeError("remotion/src/seams.tsx no longer exports SEAM_PEAK — sfx cannot place the anchored "
                           "seams' cues on their fastest frames")
    out = {}
    for key, num, den in _re.findall(r"'?([a-z-]+)'?\s*:\s*([0-9.]+)(?:\s*/\s*([0-9.]+))?", m.group(1)):
        out[key] = float(num) / (float(den) if den else 1.0)
    return out


SEAM_PEAK = _seam_peaks()
# the cue each anchored seam makes: (name, gain, priority). A punch is an IMPACT — the one hard landing, so it is
# never dropped by the density cap before a whoosh is. A container is the softest: the element never leaves the
# screen, and its sound is the carry's gentle swell, not a cut's.
SEAM_CUE = {"punch": ("impact", 0.62, 0), "through-window": ("whoosh", 0.5, 0), "grow": ("whoosh", 0.45, 0),
            "container": ("whoosh", 0.32, 1)}


# ── cue planning: pin cues to the video's BEATS (frame-exact), with restraint ─────────────────────────
def _on_the_beat(t_cue, t_cut, grid, fps):
    """A seam cue's peak, given a beat grid: still ON the cut — the cut's own frame or the one before it, the one-frame
    tolerance a seam cue always had (EBU R37: sound early by at most 40 ms) — but whichever of the two sits nearer a
    beat, so a whoosh does not flam a frame against the score's kick. Without a grid: `t_cue`, exactly as before."""
    if grid is None:
        return t_cue
    best = min((t_cut, t_cut - 1.0 / fps), key=lambda t: (abs(t - grid.t(grid.nearest_beat(t))), -t))
    return max(0.0, best)


def plan_cues(scenes, fps, events_only=False, seam_frames=12, grid=None):
    """Given a scene list (each with durationInFrames; optional shots[].startFrame), return a cue list
    [(t_seconds, cue_name, gain)] aligned to beats: a whoosh at each MARKED scene transition (anticipatory,
    −2 frames; a plain cross-fade seam stays QUIET so the ear marks the same ~2-3 seams the eye does — the
    carry match-cut gets a softer swell), a focus tick at each interior shot arrival, a pop at each element's
    enter, and the CLOSING SENTENCE (riser → impact → sparkle) at the LAST scene's final shot. Then applies
    restraint — caps density at ~4 cues / 10s, dropping the lowest-priority (ticks/pops) first so the film
    breathes; the sentence is one landing and costs the cap ONE slot.

    `grid` (scripts/beatgrid.BeatGrid, a scored film only): each marked seam's whoosh is quantised to the grid
    inside its one-frame tolerance (`_on_the_beat`). The tts stage has already snapped the cuts to the beat, so
    the peak lands on the cut AND the beat; an unsnapped cut keeps its whoosh on the cut."""
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
            # THE PEAK ON THE SEAM'S FASTEST FRAME, a frame early at most: every time here is where a cue's PEAK
            # lands (build_sfx_track aligns by it). "Two frames before the seam's first frame" put a whoosh's start
            # 67 ms early — past EBU R37's 40 ms — and its peak a fifth of a second later, after the motion's peak.
            tt = max(0.0, t0 + (seam_frames / 2.0 - 1.0) / fps)
            tt = _on_the_beat(tt, t0 + (seam_frames // 2) / float(fps), grid, fps)
            if "transitionIn" in sc:                # the seam grammar is DECLARED (remotion tier)
                ti = sc.get("transitionIn")
                if ti and ti.get("type") in SEAM_CUE:
                    # on the seam's OWN fastest frame (SEAM_PEAK) — a whoosh a frame early at most, as above; an
                    # impact ON its cut, because a transient heard before the picture it hits reads as a glitch
                    name, gain, prio = SEAM_CUE[ti["type"]]
                    at = SEAM_PEAK[ti["type"]] * seam_frames - (0.0 if name == "impact" else 1.0)
                    seam_cue = (t0 + max(0.0, at) / fps, name, gain, prio)
                elif ti and ti.get("type") == "cut":
                    # A HARD CUT MAKES NO SOUND OF ITS OWN. Nothing moves across it, so a whoosh would be the sound
                    # of a motion the picture does not make; on a scored film the music's beat — which beatgrid.py
                    # has snapped this cut onto — is its sound, and on an unscored one the cut is silent, as cuts are.
                    seam_cue = None
                elif ti and ti.get("type") == "carry":
                    seam_cue = (tt, "whoosh", 0.32, 1)      # a gentle match-cut swell (softer than a hard cut)
                elif ti:                            # slide / wipe / clock — a motion whoosh
                    seam_cue = (tt, "whoosh", 0.5, 0)
                # else: an unmarked FADE seam — no cue (the fade is visually gentle; restraint)
            else:                                   # grammar not declared (legacy caller) — unchanged behavior
                seam_cue = (tt, "whoosh", 0.5, 0)
        if si == n - 1 and shots:
            land = t0 + float(shots[-1].get("startFrame") or 0) / fps
            # A HARD CUT INTO THE CLOSE lands where its picture changes — the seam's middle frame (SEAM_PEAK.cut) —
            # not on the frame the beat mounts, six frames (200 ms) earlier, while the leaving beat is still the
            # whole picture: an impact heard before the cut it hits reads as a glitch. beatgrid.boundaries times the
            # same boundary by the same frame, so the score's downbeat and the impact stay one hit.
            if si > 0 and (sc.get("transitionIn") or {}).get("type") == "cut" and not shots[-1].get("startFrame"):
                land = t0 + SEAM_PEAK["cut"] * seam_frames / fps
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
        sentence.append((land, "riser", 0.5, 0))   # its peak — the top of the climb — on the landing
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


def _peak_seconds(c):
    """Where a cue's envelope peaks, in seconds — its 5 ms RMS maximum, so a riser's peak is the top of its climb and
    not whichever noise sample happens to be largest."""
    w = max(1, int(0.005 * SR))
    e = np.sqrt(np.convolve(np.asarray(c, dtype=np.float64) ** 2, np.ones(w) / w, mode="same"))
    return float(np.argmax(e)) / SR


def build_sfx_track(cues, total_seconds, out_wav, peak_cap=None):
    """Render the planned cues into ONE full-length SFX WAV (each cue placed at its sample offset), so the
    ffmpeg mix is a clean 2–3 input graph. Deterministic."""
    if np is None:
        return False
    buf = np.zeros(int((total_seconds + 1.0) * SR), dtype=np.float32)
    seen = {}
    for (t, name, g) in cues:
        c = cue(name)
        if c is None or not len(c):
            continue
        # A CUE REPEATED IS NOT THE SAME SOUND TWICE: the n-th click of a film is pitched and levelled a hair off the
        # first (deterministically), so a run of them does not machine-gun. The first of each is untouched.
        k = seen.get(name, 0)
        seen[name] = k + 1
        if k:
            r = 1.0 + 0.03 * np.sin(k * 2.3)
            c = np.interp(np.arange(0, len(c) - 1, r), np.arange(len(c)), c).astype(np.float32)
            g = float(g) * 10 ** (np.cos(k * 1.7) / 20.0)
        # `t` is where the cue's PEAK lands (its envelope's maximum), not where it starts: a whoosh swells for
        # 0.3 s, a riser climbs for 1.2 s — aligned by their starts, each one peaked after the moment it marks
        i = int(round((t - _peak_seconds(c)) * SR))
        a0 = max(0, -i)
        i = max(0, i)
        j = min(len(buf), i + len(c) - a0)
        buf[i:j] += c[a0: a0 + (j - i)] * float(g)
    if peak_cap is not None and float(np.max(np.abs(buf))) > peak_cap > 0:
        buf *= peak_cap / float(np.max(np.abs(buf)))   # gain-staged under the voice (see mix)
    buf = np.tanh(buf * 0.9)                         # soft-clip guard (never hard-clip the sum)
    _write_wav(out_wav, buf)
    return True


# ── the audio chain, and how far it actually MOVES a sound ────────────────────────────────────────────

OUT_RATE = 48000      # AAC delivery rate: loudnorm upsamples internally (the output came out 96 kHz) — resample back
TARGET_TP = -2.0       # true-peak ceiling BEFORE the AAC encode: a -1.5 request measured -1.3 dBTP after it
# the duck: music under the voice ≥10 LU while it speaks (Torcoli et al. 2019), 6 dB in a breath; measured with this
# pad level: 12.8 LU under speech, 6.8 in pauses (references/craft-research.md §3)
DUCK = {"threshold": 0.02, "ratio": 3, "attack": 15, "release": 450}
VOICE_FLOOR = 10 ** (-40 / 20.0)   # a voice track peaking under -40 dBFS is no voice to gain-stage the cues under


def _loudnorm(measured=None, print_json=False):
    ln = "loudnorm=I=%.1f:TP=%.1f:LRA=11" % (_TARGET_LUFS, TARGET_TP)
    if measured:
        ln += (":measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
               % (measured["input_i"], measured["input_tp"], measured["input_lra"], measured["input_thresh"],
                  measured["target_offset"]))
    if print_json:
        ln += ":print_format=json"
    return ln


# THE GENERATED SCORE IN THE MIX (scripts/score.py): two stems. The BED (pad, pluck, bass, clap) takes the old pad's
# place — lowpassed, faded and ducked under the voice exactly as it was. The PULSE (kick, shaker, hat, riser) is NOT
# ducked: a quiet kick and hat keep the time while the voice speaks (motion-research §3 "under a voice"), and it is
# lowpassed at 12 kHz rather than 4, because a shaker under 4 kHz is a thud. Levels set by measuring a copy of the
# slidemaker-promo film through this chain (`music_under_voice`): 15.5 LU under the voice while it speaks (≥10 wanted,
# craft-research §3) and 9.8 LU under its speaking level in the pauses; the old pad measured 21.9 / 11.9 there.
_SCORE_BED_VOL = 0.85
_SCORE_PULSE_VOL = 0.50
_PULSE_LP = 12000


def filtergraph(dur, has_bgm, measured=None, print_json=False, stems=False, bgm_skip=0.0, solo=None):
    """The one filtergraph. `mix()` renders through it and `measure_offset()` measures through it.

    Written twice, the probe would certify a chain the film does not use — which is the whole failure this
    module was audited for. A cue's time is computed frame-exactly and then handed to an encoder nobody had ever
    measured.

    `measured` is the first pass's loudness reading (`_measure_loudness`): the second pass then normalises LINEARLY
    to it. One dynamic pass landed a film 1.5-1.7 LU under its -14 target (the sum peaked over full scale before the
    limiter); `print_json` is that first pass.

    `stems` (the generated score): input 2 is the score's bed and input 3 its pulse. `bgm_skip` (an author track):
    seconds of the track's head skipped so its beat grid slides under the cuts — a shift, never a stretch. `solo`
    ("voice" / "music"): the same graph with the other inputs weighted to zero and no loudness pass, so the voice and
    the music can be measured apart exactly as they sit in the mix (`music_under_voice`). With none of the three the
    graph is the one this module always rendered, character for character.
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
        # THE MUSIC MAKES ROOM FOR THE VOICE. A static bed sat 4.2 LU under the voice (measured) where commentary
        # wants ≥10: the voice keys a compressor on the music. The key is padded to the film's length, or the music
        # falls silent where the voice ends.
        skip = ("atrim=start=%.6f,asetpts=PTS-STARTPTS," % bgm_skip) if bgm_skip and bgm_skip > 0 else ""
        fc += ["[0:a]asplit=2[vo][sc0]",
               "[sc0]apad=whole_dur=%.3f[sc]" % dur,
               "[2:a]%slowpass=f=%d,afade=in:st=0:d=0.3,afade=out:st=%.2f:d=1.5,volume=%.2f[bgm0]"
               % (skip, _BGM_LP, max(0.0, dur - 1.5), _SCORE_BED_VOL if stems else _BGM_VOL),
               "[bgm0][sc]sidechaincompress=threshold=%g:ratio=%g:attack=%g:release=%g:makeup=1[bgm]"
               % (DUCK["threshold"], DUCK["ratio"], DUCK["attack"], DUCK["release"])]
        mix_ins, n_in = "[vo][bgm][sfxhi][sfxlo]", 4
        if stems:
            fc.append("[3:a]lowpass=f=%d,afade=in:st=0:d=0.3,afade=out:st=%.2f:d=1.5,volume=%.2f[pulse]"
                      % (_PULSE_LP, max(0.0, dur - 1.5), _SCORE_PULSE_VOL))
            mix_ins, n_in = "[vo][bgm][pulse][sfxhi][sfxlo]", 5
    weights, tail = "", ",%s,aresample=%d" % (_loudnorm(measured, print_json), OUT_RATE)
    if solo:
        if solo not in ("voice", "music"):
            raise ValueError("solo is 'voice' or 'music', got %r" % (solo,))
        names = re.findall(r"\[(\w+)\]", mix_ins)
        music = ("bgm", "pulse")
        weights = ":weights=" + " ".join(("1" if (n in music) == (solo == "music") and n not in ("sfxhi", "sfxlo")
                                          else "0") for n in names)
        tail = ",aresample=%d" % OUT_RATE
    fc.append("%samix=inputs=%d:duration=first:normalize=0%s%s[a]" % (mix_ins, n_in, weights, tail))
    return ";".join(fc)


def _measure_loudness(inputs, dur, has_bgm, stems=False, bgm_skip=0.0):
    """The first pass: the chain's own loudness reading, or None (then the second pass is a dynamic one)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + inputs +
                       ["-filter_complex", filtergraph(dur, has_bgm, print_json=True, stems=stems, bgm_skip=bgm_skip),
                        "-map", "[a]", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr or "", re.S)
    try:
        j = json.loads(m.group(0)) if m else None
    except ValueError:
        j = None
    if not j or any(str(j.get(k, "")).lstrip("-").replace(".", "", 1).isdigit() is False
                    for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")):
        return None
    return {k: j[k] for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}


def _through_chain(inputs, dur, has_bgm, out, maps, stems=False, bgm_skip=0.0):
    """Render through the chain in two passes (measure, then normalise linearly to the measurement)."""
    meas = _measure_loudness(inputs, dur, has_bgm, stems, bgm_skip)
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", filtergraph(
        dur, has_bgm, meas, stems=stems, bgm_skip=bgm_skip)] + maps + ["-c:a", "aac", "-b:a", "192k", out], check=True)


def music_under_voice(inputs, dur, stems=False, bgm_skip=0.0, speech_lufs=-35.0):
    """How far the music sits under the voice IN THIS MIX, in LU, measured on the chain itself: the graph rendered
    twice with `solo` (the other inputs weighted to zero, ducking intact — the voice still keys it), each solo's
    momentary loudness (400 ms, every 100 ms) compared frame by frame. 'speech' frames are those where the voice solo
    is above `speech_lufs`; the rest are the pauses. Returns medians: 'speech_lu' = voice - music while it speaks
    (frame by frame), 'pause_lu' = the voice's speaking level - the music's level in the pauses (how far under the
    voice the music sits when it swells back), the three levels themselves, and the frame counts; or None when ffmpeg
    cannot measure it. Craft-research §3: ≥10 LU under commentary (Torcoli et al. 2019)."""
    def momentary(solo):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + inputs + [
            "-filter_complex", filtergraph(dur, True, stems=stems, bgm_skip=bgm_skip, solo=solo) + ";[a]ebur128=framelog=info[o]",
            "-map", "[o]", "-f", "null", "-"], capture_output=True, text=True)
        return [float(m) for m in re.findall(r"\bM:\s*(-?[\d.]+|-inf)", r.stderr or "") if m != "-inf"]
    try:
        v, m = momentary("voice"), momentary("music")
    except Exception:                                     # noqa: BLE001 — a measurement, never a reason to fail a mix
        return None
    n = min(len(v), len(m))
    if n < 10:
        return None
    v, m = v[:n], m[:n]
    med = lambda xs: round(sorted(xs)[len(xs) // 2], 1) if xs else None          # noqa: E731
    spk = [k for k in range(n) if v[k] > speech_lufs]
    pau = [k for k in range(n) if v[k] <= speech_lufs and m[k] > -70]
    v_sp, m_sp, m_pa = med([v[k] for k in spk]), med([m[k] for k in spk]), med([m[k] for k in pau])
    return {"speech_lu": med([v[k] - m[k] for k in spk]),
            "pause_lu": round(v_sp - m_pa, 1) if v_sp is not None and m_pa is not None else None,
            "voice_lufs": v_sp, "music_speech_lufs": m_sp, "music_pause_lufs": m_pa,
            "speech_frames": len(spk), "pause_frames": len(pau)}


def sfx_peak_cap(vo_peak):
    """The SFX bus's peak: 6 dB under the voice's own peak. A film with no voice to stage under (a music-only cut, a
    silent track: peak under -40 dBFS) or an unread one is not capped — capped to a silent voice, every cue was muted."""
    return vo_peak * 10 ** (-6 / 20.0) if vo_peak and vo_peak >= VOICE_FLOOR else None


def _audio_peak(mp4):
    """The largest sample magnitude of a file's audio, every channel as it is (a mono fold reads +3 dB high)."""
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vn", "-f", "f32le", "-"], capture_output=True,
                             check=True).stdout
        a = np.frombuffer(raw, dtype=np.float32)
        return float(np.max(np.abs(a))) if len(a) else None
    except Exception:
        return None


PROBE_AT = 2.0                  # where the probe click is placed, in seconds
PROBE_SECONDS = 5.0
MAX_SANE_SHIFT = 2.0            # frames — beyond this the measurement is not believed, and says so


def measure_offset(fps=30, has_bgm=False, workdir=None, stems=False, bgm_skip=0.0):
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
            if stems:
                ins += ["-i", os.path.join(tmp, "bgm.wav")]
        mixed = os.path.join(tmp, "mixed.mp4")
        _through_chain(ins, PROBE_SECONDS, has_bgm, mixed, ["-map", "0:v", "-map", "[a]", "-c:v", "copy"],
                       stems=stems and has_bgm, bgm_skip=bgm_skip if has_bgm else 0.0)
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
def _legacy_cut_times(scenes, fps, seam_frames=12):
    """Cut moments from an sfx scene list alone (durationInFrames on the overlap-compressed timeline): a seam's middle,
    and the last scene's arrival — beatgrid.boundaries' rule, for a caller that hands mix() no grid."""
    t0, out = 0.0, []
    for si, sc in enumerate(scenes):
        if si > 0:
            out.append(t0 + (0 if si == len(scenes) - 1 else (seam_frames // 2)) / float(fps))
        t0 += float(sc.get("durationInFrames") or 0) / fps
    return out


QA_MIN_SECONDS = 12.0    # the shortest render the bed's beat check runs on (a few bars at the slowest score tempo)


def _score_stems(sdir, dur, music, cues, meta, fps, lat):
    """Render the generated score on its grid, hold it to the grid (beatgrid.verify_bed), write its two stems.
    Returns (bed_wav, pulse_wav, info) or None — said aloud — when the score cannot be trusted."""
    import beatgrid
    import score
    grid = music["grid"]
    climax = music.get("climax_s")
    land = [t for (t, name, _g) in cues if name == "impact"]
    # the SFX closing sentence already builds into the close (riser -> impact): a score riser on the same landing
    # would be a second build on one hit, so the score only rises into a payoff that is NOT the close
    rise = climax is not None and not any(abs(climax - t) <= 2.0 / fps for t in land)
    mu = meta.get("music") if isinstance(meta.get("music"), dict) else {}
    st = score.render(grid, dur, climax_s=climax, riser_into_climax=rise, seed=beatgrid.score_seed(meta),
                      key=mu.get("key"))
    bed, pulse, sr = st["bed"], st["pulse"], st["sr"]
    qa_x = bed + pulse
    if dur < QA_MIN_SECONDS:
        # a tempo needs a few bars to be measured (beatgrid.MIN_SECONDS): a short film's score is checked on a longer
        # render of the SAME grid and synthesis — the beats are what is checked, and they do not depend on the length
        qa_st = score.render(grid, QA_MIN_SECONDS, climax_s=climax, riser_into_climax=rise,
                             seed=beatgrid.score_seed(meta), key=mu.get("key"))
        qa_x = qa_st["bed"] + qa_st["pulse"]
    try:
        qa = beatgrid.verify_bed(qa_x, sr, grid, log=lambda m: print("[sfx] " + m))
    except beatgrid.BedOffGrid as e:
        print("[sfx] ERROR: the generated score failed its own beat check — %s. The score is NOT mixed; the film "
              "falls back to the untimed pad. This is a bug in scripts/score.py, not in the board." % e)
        return None
    if lat:
        # the chain moved a click by `lat`: the bed is part of the picture's timing too, so it moves with the cues
        k = int(round(abs(lat) * sr))
        if lat > 0:
            bed, pulse = bed[k:], pulse[k:]
        else:
            bed = np.concatenate([np.zeros(k, np.float32), bed])
            pulse = np.concatenate([np.zeros(k, np.float32), pulse])
    bw, pw = os.path.join(sdir, "_bgm.wav"), os.path.join(sdir, "_pulse.wav")
    score.write_wav(bw, bed, sr)
    score.write_wav(pw, pulse, sr)
    inf = st["info"]
    print("[sfx] score: %s %s at %.2f BPM (%s), %s; beats re-detected %.1f ms (median) off the grid"
          % (inf["key"], "-".join(inf["progression"]), inf["bpm"], grid.source,
             ("rising into the payoff at %.2fs" % climax) if rise else
             ("landing with the close at %.2fs" % climax) if climax is not None else "peak at ~60%",
             qa["median_ms"]))
    return bw, pw, dict(inf, verify=qa)


def mix(out_dir, mp4, scenes, meta, fps, events_only=False, music=None):
    """Post-render: overlay the SFX track (+ optional BGM) onto out.mp4's baked voiceover using huashu's
    frequency-isolation filtergraph, then mux back. Returns True if it re-wrote the video. Best-effort:
    no numpy / no ffmpeg / no cues -> leaves the video untouched.

    `music` (beatgrid.music_for_render; a scored film only): {'grid', 'climax_s', 'bgm_skip_s'}. With it the whooshes
    quantise to the grid, `bgm: "auto"` is the GENERATED SCORE on that grid (scripts/score.py, two stems) instead of
    the pad, and an author track is started `bgm_skip_s` into itself so its beats sit under the cuts. Without it —
    every film that does not ask for music — the mix is the one this module always made."""
    if np is None or not shutil.which("ffmpeg"):
        print("[sfx] skipped (numpy/ffmpeg unavailable)"); return False
    dur = _probe_duration(mp4)
    if not dur:
        print("[sfx] skipped (could not probe video duration)"); return False
    bgm = None if events_only else meta.get("bgm")   # the score belongs to the SFX bed, not to a stage's clicks
    if bgm == "auto" and music is None and not events_only:
        # a caller that asked for the score but handed no grid (an older caller, a test): fit one to the cuts as they
        # are — tier 1 — rather than fall back to a bed with no tempo at all
        import beatgrid
        cuts = _legacy_cut_times(scenes, fps)
        music = {"grid": beatgrid.fit_to_cuts(cuts), "climax_s": cuts[-1] if cuts else None, "bgm_skip_s": 0.0}
        print("[sfx] no beat grid handed in — the score is fitted to the cuts as they are (%s)" % music["grid"])
    grid = (music or {}).get("grid") if not events_only else None
    cues = plan_cues(scenes, fps, events_only=events_only, grid=grid)
    sdir = os.path.join(out_dir, ".sfx"); os.makedirs(sdir, exist_ok=True)
    sfx_wav = os.path.join(sdir, "_sfx.wav")
    if not cues:
        print("[sfx] no cues planned — video unchanged"); return False

    # optional BGM: an author track (meta.bgm=path) or the generated score (meta.bgm='auto')
    bgm_wav = None
    pulse_wav = None
    skip = 0.0
    score_info = None
    if bgm == "auto":
        pass                                         # rendered below, once the chain's offset is known
    elif isinstance(bgm, str) and bgm and os.path.exists(os.path.join(out_dir, bgm)):
        bgm_wav = os.path.join(out_dir, bgm)
        skip = float((music or {}).get("bgm_skip_s") or 0.0)

    # SELF-CALIBRATING, never a borrowed constant. The chain is measured as it is about to be used, so a
    # different ffmpeg, a codec change or an added filter is corrected for instead of silently shifting every
    # cue. Measured 0.00 frames here; a measurement beyond MAX_SANE_SHIFT is not trusted and says so out loud
    # rather than dragging the cues somewhere arbitrary.
    stems = bgm == "auto" and grid is not None
    lat = measure_offset(fps, has_bgm=bool(bgm_wav) or bgm == "auto", stems=stems, bgm_skip=skip)
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
        if skip:
            skip = max(0.0, skip + lat)               # an author track's beats move with the picture's cues
    if bgm == "auto":
        made = _score_stems(sdir, dur, music, cues, meta, fps, lat) if stems else None
        if made:
            bgm_wav, pulse_wav, score_info = made
        else:
            stems = False
            bgm_wav = os.path.join(sdir, "_bgm.wav"); _write_wav(bgm_wav, synth_pad(dur))
    # GAIN-STAGED UNDER THE VOICE: the SFX bus peaks ≥6 dB under the voice's own peak. A riser and an impact at
    # -2.4 dBFS stacked on voice peaks put the sum over full scale before the limiter, and the film landed under its
    # loudness target (references/craft-research.md §3)
    if not build_sfx_track(cues, dur, sfx_wav, peak_cap=sfx_peak_cap(_audio_peak(mp4))):
        print("[sfx] could not build the cue track — video unchanged"); return False

    inputs = ["-i", mp4, "-i", sfx_wav] + (["-i", bgm_wav] if bgm_wav else []) + (["-i", pulse_wav] if stems else [])
    out2 = os.path.join(out_dir, "_snd.mp4")
    try:
        if score_info is not None:
            lu = music_under_voice(inputs, dur, stems=True)
            if lu:
                print("[sfx] music under the voice: %s LU while it speaks, %s LU in its pauses (craft-research §3: "
                      ">=10 under commentary)" % (lu["speech_lu"], lu["pause_lu"]))
                if lu["speech_lu"] is not None and lu["speech_lu"] < 10.0:
                    print("[sfx] WARNING: the score sits only %.1f LU under the voice while it speaks — it will "
                          "compete with the words; AUDITION it" % lu["speech_lu"])
        _through_chain(inputs, dur, bool(bgm_wav), out2, ["-map", "0:v", "-map", "[a]", "-c:v", "copy"],
                       stems=stems, bgm_skip=skip)
        if bgm_wav:
            # TWO DELIVERIES FROM ONE TIMELINE. A film with a BGM also ships a `.nobgm.mp4` twin — same cues,
            # same frames, no music — so the user can score it themselves without a re-render. Borrowed from
            # the peer library's delivery rule for scored films; the twin is a second pass through the same
            # graph with the BGM input absent, never a separate timeline.
            twin = os.path.splitext(mp4)[0] + ".nobgm.mp4"
            _through_chain(["-i", mp4, "-i", sfx_wav], dur, False, twin, ["-map", "0:v", "-map", "[a]", "-c:v", "copy"])
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
