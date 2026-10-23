#!/usr/bin/env python3
"""The film's MUSICAL CLOCK: a beat grid, how to find one in an author's track, how to choose one for a generated
score, and how to move the cuts onto it without moving a single word.

  python3 scripts/beatgrid.py <out_dir>            # the film's grid (beats.json) and where every cut sits on it
  python3 scripts/beatgrid.py --detect <track>     # a track's tempo, phase and how sure the detector is

WHY THIS EXISTS. `meta.bgm: "auto"` was a drone with no tempo and no key, nothing in the pipeline read a tempo, and
nothing aligned a picture to music (references/motion-research.md §0). A cut that lands between two beats of the
film's own score reads as an edit that does not know there is music under it.

THREE TIERS, simulated over 400 films before any of this was written (motion-research §3):
  1. FIT the grid to the cuts — choose BPM and phase so the cuts already sit near beats (mean 146 -> 60 ms).
  2. SNAP the pads — stretch the silence at a scene's tail so its cut lands on the beat. tts.py only ever APPENDS
     silence after a clip, so moving a pad moves no word inside it and `audio/NN.words.json` stays valid. Bounded:
     a few frames of trim (never under the pause floor) to ~0.3 s added; a cut the window cannot reach is left
     where it is and SAID. A whole bar would cost ~0.7 s a scene — a film that stops to wait for the music.
  3. a tempo map (generated bed only) — NOT built; tiers 1+2 already land the cuts a frame from the beat.

THE TIMELINE IS Film.tsx's, mirrored: beat k starts `TR` frames before beat k-1 ends at a cut and on the frame after
it inside a stage run (`sceneStarts`). A cut's picture moment is its seam's MIDDLE frame — the fastest frame of the
transition, where `sfx.plan_cues` already lands a whoosh's peak; inside a stage run it is the beat's first frame.
A cut "on the beat" is that frame at or up to one frame BEFORE the beat: editors cut picture 1-2 frames early
(motion-research §3) and the ear forgives sound late far more than sound early (ITU-R BT.1359: +45 / -125 ms).
"""
import json
import math
import os
import re
import subprocess
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import numpy as np
except Exception:                                   # the grid model needs no numpy; detection and fitting do
    np = None

FILM_FPS = 30                   # the Film composition's rate (remotion/src/Root.tsx); render_remotion uses it as is
DETECT_BPM_RANGE = (70, 145)    # where detection looks (motion-research §3); a ×2/×½ answer outside it is folded in
SCORE_BPM_RANGE = (90, 125)     # (U) the generated score's tempo window — "no authoritative explainer range; 90-125"
MAX_ADD_S = 0.30                # (U) the most silence tier 2 may ADD to one scene's tail
MAX_TRIM_S = 0.10               # (U) the most it may take away, and never below the scene_pause floor (see snap_pads)
BED_LIMIT_MS = 10.0             # verify_bed: the generated bed's re-detected beats must sit this close to its grid
BEATS_FILE = "beats.json"
UNITS = ("beat", "half", "bar")


class BeatGrid:
    """A constant-tempo grid. `offset_s` is the time of beat 0 and beat 0 is a DOWNBEAT, so beat i is the downbeat
    of a bar exactly when i % beats_per_bar == 0; i may be negative (the pickup before the first full bar)."""

    def __init__(self, bpm, offset_s=0.0, beats_per_bar=4, fps=FILM_FPS, source="synth", info=None):
        bpm = float(bpm)
        if not (20.0 <= bpm <= 300.0) or math.isnan(bpm):
            raise ValueError("a beat grid needs a tempo in 20-300 BPM, got %r" % bpm)
        if int(beats_per_bar) < 1:
            raise ValueError("beats_per_bar must be >= 1, got %r" % beats_per_bar)
        if source not in ("synth", "detected", "author"):
            raise ValueError("source must be synth / detected / author, got %r" % source)
        self.bpm = bpm
        self.beats_per_bar = int(beats_per_bar)
        self.fps = int(fps)
        self.source = source
        self.info = dict(info or {})
        bar = self.period * self.beats_per_bar
        self.offset_s = float(offset_s) % bar          # one canonical phase: [0, bar)

    @property
    def period(self):
        return 60.0 / self.bpm

    @property
    def bar_s(self):
        return self.period * self.beats_per_bar

    def t(self, i):
        """The time of beat i, in seconds."""
        return self.offset_s + float(i) * self.period

    def index(self, t):
        """Where `t` falls on the grid, in beats (fractional)."""
        return (float(t) - self.offset_s) / self.period

    def frame(self, i):
        """The picture frame for beat i: the last frame AT OR BEFORE the beat — "cut on the beat, at most one frame
        early". (+1e-4 of a frame, 3 µs: a beat that is ON a frame must not floor to the frame before it through the
        float error of offset + i*period.)"""
        return int(math.floor(self.t(i) * self.fps + 1e-4))

    def nearest(self, t, unit="beat"):
        """The nearest grid line of `unit` (beat / half / bar) to `t`, in seconds."""
        if unit not in UNITS:
            raise ValueError("unit must be one of %s, got %r" % (UNITS, unit))
        step = {"beat": self.period, "half": self.period / 2.0, "bar": self.bar_s}[unit]
        return self.offset_s + round((float(t) - self.offset_s) / step) * step

    def nearest_beat(self, t):
        return int(round(self.index(t)))

    def is_downbeat(self, i):
        return int(i) % self.beats_per_bar == 0

    def beats(self, t0, t1):
        """Beat indices whose time lies in [t0, t1)."""
        a = int(math.ceil(self.index(t0) - 1e-9))
        b = int(math.ceil(self.index(t1) - 1e-9))
        return list(range(a, b))

    def frame_locked(self):
        """True when a beat is a whole number of frames (60*fps/n BPM): every beat then lands ON a frame."""
        n = 60.0 * self.fps / self.bpm
        return abs(n - round(n)) < 1e-6

    def to_dict(self):
        # full precision: rounded to 6 decimals, a frame-locked grid's 0.433333 put beat 7 a third of a microsecond
        # before its frame, and frame() floored it to the frame before — json round-trips a float exactly
        return {"bpm": self.bpm, "offset_s": self.offset_s, "beats_per_bar": self.beats_per_bar,
                "fps": self.fps, "source": self.source, "frame_locked": self.frame_locked()}

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            raise ValueError("a beat grid is an object, got %r" % type(d).__name__)
        return cls(d["bpm"], d.get("offset_s", 0.0), d.get("beats_per_bar", 4), d.get("fps", FILM_FPS),
                   d.get("source", "synth"))

    def __repr__(self):
        return "BeatGrid(%.3f BPM, offset %.3fs, %d/bar, %d fps, %s)" % (self.bpm, self.offset_s, self.beats_per_bar,
                                                                         self.fps, self.source)


def frame_locked_tempos(bpm_range, fps=FILM_FPS):
    """The tempos at which a beat is a whole number of frames, 60*fps/n, inside `bpm_range` (fastest first).
    At 30 fps in 90-125: 120, 112.5, 105.88, 100, 94.74, 90 (motion-research §3)."""
    lo, hi = float(bpm_range[0]), float(bpm_range[1])
    out = []
    for n in range(1, 10 * fps):
        b = 60.0 * fps / n
        if b < lo - 1e-9:
            break
        if b <= hi + 1e-9:
            out.append(b)
    return out


# ── the meta contract: what a board may ask for, checked in ONE place (validate.py and tts.py both call it) ──────
MUSIC_KEYS = ("bpm", "snap", "key", "seed")
_KEY_RE = re.compile(r"^\s*([A-Ga-g])([#b]?)\s*(m|min|minor|maj|major)?\s*$")


def parse_key(key):
    """'A', 'F#m', 'Bb major', 'c minor' -> (pitch class 0-11, 'major'|'minor'). Raises ValueError otherwise."""
    m = _KEY_RE.match(str(key or ""))
    if not m:
        raise ValueError("a key is a note name with an optional sharp/flat and mode (C, F#m, Bb major), got %r" % key)
    pc = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}[m.group(1).lower()]
    pc = (pc + {"#": 1, "b": -1, "": 0}[m.group(2)]) % 12
    mode = "minor" if (m.group(3) or "").lower() in ("m", "min", "minor") else "major"
    return pc, mode


def music_problems(meta):
    """(errors, warnings) for `meta.music` and the music request around it — the one definition validate.py and
    the tts stage share, so the board the validator passes is the board the snapper reads."""
    errors, warnings = [], []
    meta = meta if isinstance(meta, dict) else {}
    mu = meta.get("music")
    if mu is None:
        return errors, warnings
    if not isinstance(mu, dict):
        return ["meta.music must be an object {bpm?, snap?, key?, seed?}, got %r" % type(mu).__name__], warnings
    for k in mu:
        if k not in MUSIC_KEYS:
            errors.append("meta.music.%s is not a field this pipeline reads (it would be ignored in silence) — "
                          "the fields are %s" % (k, ", ".join(MUSIC_KEYS)))
    if "bpm" in mu:
        b = mu["bpm"]
        if isinstance(b, bool) or not isinstance(b, (int, float)) or not (60 <= float(b) <= 180):
            errors.append("meta.music.bpm must be a tempo in 60-180 BPM, got %r" % (b,))
        elif isinstance(meta.get("bgm"), str) and meta.get("bgm") not in ("", "auto") and not (
                DETECT_BPM_RANGE[0] <= float(b) <= DETECT_BPM_RANGE[1]):
            warnings.append("meta.music.bpm %s is outside the %d-%d BPM the detector confirms an author track in — "
                            "the track's phase cannot be found there, so the cuts will not be snapped to it"
                            % (b, DETECT_BPM_RANGE[0], DETECT_BPM_RANGE[1]))
    if "snap" in mu and mu["snap"] not in ("beat", "off"):
        errors.append("meta.music.snap must be \"beat\" (stretch pads so cuts land on beats) or \"off\", got %r"
                      % (mu["snap"],))
    if "key" in mu:
        try:
            parse_key(mu["key"])
        except ValueError as e:
            errors.append("meta.music.key: %s" % e)
    if "seed" in mu and (isinstance(mu["seed"], bool) or not isinstance(mu["seed"], int)):
        errors.append("meta.music.seed must be an integer, got %r" % (mu["seed"],))
    bgm = meta.get("bgm")
    if not music_requested(meta):
        why = ("meta.bgm is not set" if not bgm else "meta.sound_design is off (the score is part of the SFX bed)"
               if not meta.get("sound_design") else "the html tier has no music mix")
        warnings.append("meta.music is set but the film has no music: %s — the field does nothing" % why)
    elif isinstance(bgm, str) and bgm != "auto" and "key" in mu:
        warnings.append("meta.music.key only chooses the GENERATED score's key; an author track (meta.bgm=%r) keeps "
                        "its own" % bgm)
    return errors, warnings


def music_requested(meta):
    """Does this board ask for music the pipeline will actually MIX? Only the remotion tier mixes (render_remotion ->
    sfx.mix), only with meta.sound_design on (a stage's clicks alone never carry a score), and only with meta.bgm set
    to "auto" or a path. Anything else is a film without music and must behave exactly as it did before."""
    meta = meta if isinstance(meta, dict) else {}
    if str(meta.get("renderer", "")).lower() not in ("remotion", "remotion-bespoke"):
        return False
    bgm = meta.get("bgm")
    return bool(meta.get("sound_design")) and isinstance(bgm, str) and bool(bgm.strip())


def score_seed(meta):
    """meta.music.seed, else a stable hash of the title: every film its own key and progression, the same film the
    same music on every render. crc32, not hash() — str hash() is salted per process (sfx.cue says why)."""
    mu = (meta or {}).get("music") or {}
    if isinstance(mu, dict) and isinstance(mu.get("seed"), int) and not isinstance(mu.get("seed"), bool):
        return int(mu["seed"])
    return zlib.crc32(str((meta or {}).get("title") or "untitled").encode("utf-8")) % 1000003


# ── the timeline (Film.tsx sceneStarts) and where its picture changes ─────────────────────────────────────────────
def seam_frames():
    """SEAM_FRAMES, parsed from remotion/src/runtime/motion.ts — the one definition the Film, tts.py and this module
    read, so none of them can drift."""
    try:
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "runtime",
                                "motion.ts"), encoding="utf-8").read()
        m = re.search(r"export const SEAM_FRAMES\s*=\s*(\d+)", src)
        if m:
            return int(m.group(1))
    except OSError:
        pass
    return 12


def dur_frames(seconds, fps=FILM_FPS):
    """A beat's length in frames exactly as render_remotion computes it (`int(round(dur * fps))`)."""
    return max(1, int(round(float(seconds) * fps)))


def boundaries(durF, joined, tr, close_on_arrival=False):
    """[{'k', 'kind', 'start', 'frame'}] for each boundary between beat k-1 and beat k (k >= 1).

    `start` is where beat k mounts on the film's timeline; `frame` is where its picture CHANGES: a cut's seam
    middle (start + tr//2, the transition's fastest frame) or, inside a stage run, the beat's first frame.

    close_on_arrival: a SCORED film's last boundary is timed by its ARRIVAL, not its seam's middle. sfx.plan_cues
    lands the closing impact on the last beat's first frame (render_remotion puts the close's one shot at frame 0),
    and music only plays with that SFX bed on; timed by the seam's middle instead, the score's downbeat would land
    six frames (200 ms) after the impact — two hits where the film has one."""
    out, acc = [], 0
    starts = []
    for k, d in enumerate(durF):
        starts.append(acc)
        acc += int(d) - (tr if k + 1 < len(durF) and not joined[k + 1] else 0)
    for k in range(1, len(durF)):
        cut = not joined[k]
        arrival = close_on_arrival and k == len(durF) - 1
        out.append({"k": k, "kind": ("close" if arrival else "cut") if cut else "joined", "start": starts[k],
                    "frame": starts[k] + (tr // 2 if cut and not arrival else 0)})
    return out


def film_frames(durF, joined, tr):
    cuts = sum(1 for k in range(1, len(durF)) if not joined[k])
    return max(1, sum(int(d) for d in durF) - cuts * tr)


# ── tier 2 (and the cost tier 1 minimises): move each cut onto a beat, inside its window ──────────────────────────
def _plan(cut_frames, windows, grid):
    """Sequential snap over the BASE cut frames. windows[j] = (lo, hi) frames the pad before cut j may change by
    (lo <= 0 <= hi). Moving cut j moves every cut after it by the same amount, which is why this cannot be solved
    cut by cut against the base timeline. Each cut takes the beat whose frame is CLOSEST inside its window
    (ties: the later one — added silence is the safer direction). Returns [(delta, beat or None, err_s)]: err_s is
    the cut's distance to its nearest beat AFTER the plan (cut - beat; <= 0 and > -1 frame when snapped)."""
    fps = grid.fps
    shift, out = 0, []
    for c0, (lo, hi) in zip(cut_frames, windows):
        c = c0 + shift
        best = None
        i0 = int(math.floor(grid.index((c + lo) / float(fps)))) - 1
        i1 = int(math.ceil(grid.index((c + hi + 1) / float(fps)))) + 1
        for i in range(i0, i1 + 1):
            d = grid.frame(i) - c
            if lo <= d <= hi and (best is None or (abs(d), -d) < (abs(best[0]), -best[0])):
                best = (d, i)
        if best is not None:
            shift += best[0]
            c += best[0]
            out.append((best[0], best[1], c / float(fps) - grid.t(best[1])))
        else:
            i = grid.nearest_beat(c / float(fps))
            out.append((0, None, c / float(fps) - grid.t(i)))
    return out


def _cost(plan, windows, fps):
    """A plan's cost, in frames: a snapped cut costs the silence it moved; an unsnapped one costs more than any snap
    could (its window's reach, plus one) and then how far off the beat it stays — so a grid that snaps more cuts
    always wins, and among grids that snap none, the one nearest the cuts wins (tier 1 exactly)."""
    c = 0.0
    for (d, beat, err), (lo, hi) in zip(plan, windows):
        if beat is not None:
            c += abs(d)
        else:
            c += (max(hi, -lo) + 1) + abs(err) * fps
    return c


def fit_to_cuts(cut_times, bpm_range=SCORE_BPM_RANGE, fps=FILM_FPS, beats_per_bar=4, bpm=None, windows=None,
                climax=None, source="synth", frame_locked=True, phase_step_s=0.001):
    """TIER 1: the grid that puts these cuts nearest the beat. `cut_times` are the picture moments, in seconds.

    windows=None: minimise the mean |cut - nearest beat| (no cut moves). windows=[(lo_s, hi_s)] per cut: minimise
    what tier 2 would then have to do (snap_pads runs this same plan), so tempo and phase are chosen FOR the snap.
    Frame-locked tempos (60*fps/n) are preferred — searched alone unless `frame_locked=False` — because then
    every beat IS a frame and a snapped cut sits exactly on its beat rather than up to a frame before it.
    `bpm` pins the tempo (an author's stated or detected one) and searches the phase alone. `climax` (seconds, a
    cut time) picks which beat is the DOWNBEAT: the film's payoff lands on beat one of a bar.
    """
    if np is None:
        raise RuntimeError("fit_to_cuts needs numpy")
    cuts = [float(t) for t in cut_times]
    cf = [int(round(t * fps)) for t in cuts]
    if windows is None:
        wf = [(0, 0)] * len(cf)
    else:
        if len(windows) != len(cf):
            raise ValueError("one window per cut: %d cuts, %d windows" % (len(cf), len(windows)))
        wf = [(-int(math.floor(-lo * fps + 1e-6)) if lo < 0 else 0, int(math.floor(hi * fps + 1e-6)))
              for lo, hi in windows]
        wf = [(min(0, lo), max(0, hi)) for lo, hi in wf]
    if bpm is not None:
        tempos = [float(bpm)]
    elif frame_locked:
        tempos = frame_locked_tempos(bpm_range, fps)
        if not tempos:
            raise ValueError("no frame-locked tempo at %d fps inside %s BPM" % (fps, bpm_range))
    else:
        tempos = list(np.arange(float(bpm_range[0]), float(bpm_range[1]) + 1e-9, 0.25))
    best = None
    for b in tempos:
        per = 60.0 / b
        n = per * fps
        if abs(n - round(n)) < 1e-6:                      # frame-locked: only whole-frame phases are distinct
            phases = [k / float(fps) for k in range(int(round(n)))]
        else:
            phases = list(np.arange(0.0, per, phase_step_s))
        for ph in phases:
            g = BeatGrid(b, ph, beats_per_bar, fps, source)
            if not cuts:
                cost, plan = 0.0, []
            else:
                plan = _plan(cf, wf, g)
                cost = _cost(plan, wf, fps)
            # (U) a whisper of a prior toward ~108 BPM, only to break exact ties between equally good grids
            cost += 1e-3 * abs(math.log2(b / 108.0))
            if best is None or cost < best[0] - 1e-12:
                best = (cost, b, ph, plan)
    cost, b, ph, plan = best
    per = 60.0 / b
    # THE DOWNBEAT. Beat phase alone decides where the cuts land; which of those beats is "one" decides how they
    # FEEL. The payoff on beat one; without a declared payoff, the bar phase that puts the most cuts on beat one.
    # Beat indices in `plan` count on the PHASE grid (beat 0 at `ph`); on a grid whose beat 0 is p beats later,
    # phase-grid beat i is beat i - p.
    pg = BeatGrid(b, ph, beats_per_bar, fps, source)
    ic = None
    if climax is not None and cuts:
        j = min(range(len(cuts)), key=lambda q: abs(cuts[q] - float(climax)))
        if plan[j][1] is not None:
            ic = plan[j][1]                                  # the beat the climax's cut was moved onto
        else:
            moved = sum(d for d, _i, _e in plan[:j + 1]) / float(fps)
            ic = pg.nearest_beat(cuts[j] + moved)
    elif climax is not None:
        ic = pg.nearest_beat(float(climax))
    cand = []
    for p in range(beats_per_bar):
        if ic is not None:
            score = 1 if (ic - p) % beats_per_bar == 0 else 0
        else:
            score = sum(1 for (d, i, e) in plan if i is not None and (i - p) % beats_per_bar == 0)
        cand.append((score, -p, p))
    p = max(cand)[2]
    grid = BeatGrid(b, ph + p * per, beats_per_bar, fps, source)
    # re-run the plan on the final grid so beat indices (and downbeats) in the report are the grid's own
    plan = _plan(cf, wf, grid) if cuts else []
    errs = [abs(t - grid.t(grid.nearest_beat(t))) for t in cuts]
    grid.info = {"cost": round(cost, 4), "tempos_tried": len(tempos),
                 "mean_err_ms_unmoved": round(1000.0 * float(np.mean(errs)), 1) if errs else None,
                 "plan": plan}
    return grid


def pad_windows(durF, bnd, slack, tr, fps=FILM_FPS, max_add_s=MAX_ADD_S, max_trim_s=MAX_TRIM_S):
    """(lo, hi) FRAMES each boundary's pad may change by — the one definition tier 1 fits against and tier 2 snaps
    within. The pad that moves boundary k's cut is beat k-1's tail."""
    out = []
    for b in bnd:
        k = b["k"] - 1
        lo = -int(math.floor(min(max_trim_s, max(0.0, float(slack[k] or 0.0))) * fps + 1e-6))
        hi = int(math.floor(max(0.0, max_add_s) * fps + 1e-6))
        # a beat must keep more than its seam: Film.tsx mounts the next beat `tr` frames before this one ends
        lo = max(lo, -(int(durF[k]) - tr - 1)) if lo < 0 else 0
        out.append((min(0, lo), max(0, hi)))
    return out


def snap_pads(durations, joined, grid, tr=None, max_add_s=MAX_ADD_S, max_trim_s=MAX_TRIM_S, slack=None,
              close_on_arrival=False):
    """TIER 2: stretch (or, a little, trim) each scene's trailing pad so the cut after it lands on a beat.

    durations: per-beat seconds as the board holds them (after mastering and the open/close holds). joined: the
    stage-run flags (stage_runs.joined_flags). slack[k]: seconds of beat k's pad above the scene_pause FLOOR — the
    most it may ever be shortened (0 = never: an explicit audio_breath, an unmastered clip, a silent beat). Each
    pad may lose at most min(max_trim_s, slack) and gain at most max_add_s; a cut that cannot reach a beat inside
    that window stays where it is (its report says so and how far off it sits).

    Returns (new_durations, report). A changed beat's new duration is a WHOLE number of frames, so the board's
    3-decimal duration rounds back to exactly the frame count the plan used (render_remotion: int(round(d*fps))).
    """
    fps = grid.fps
    tr = seam_frames() if tr is None else int(tr)
    n = len(durations)
    if len(joined) != n:
        raise ValueError("one joined flag per beat: %d beats, %d flags" % (n, len(joined)))
    slack = [0.0] * n if slack is None else [max(0.0, float(s or 0.0)) for s in slack]
    durF = [dur_frames(d, fps) for d in durations]
    bnd = boundaries(durF, joined, tr, close_on_arrival)
    cut_frames = [b["frame"] for b in bnd]
    windows = pad_windows(durF, bnd, slack, tr, fps, max_add_s, max_trim_s)
    plan = _plan(cut_frames, windows, grid)
    new = list(durations)
    newF = list(durF)
    report = []
    for b, (d, beat, err), (lo, hi) in zip(bnd, plan, windows):
        k = b["k"] - 1
        before = b["frame"] / float(fps)
        i0 = grid.nearest_beat(before)
        row = {"boundary": b["k"], "kind": b["kind"], "t_before": round(before, 4),
               "err_before_ms": round(1000.0 * (before - grid.t(i0)), 1), "window_frames": [lo, hi]}
        if beat is not None and d != 0:
            newF[k] += d
            new[k] = newF[k] / float(fps)
        row.update({"snapped": beat is not None, "added_s": round(d / float(fps), 4),
                    "beat": beat, "downbeat": bool(beat is not None and grid.is_downbeat(beat)),
                    "err_after_ms": round(1000.0 * err, 1)})
        if beat is None:
            row["why"] = ("no beat inside the pad's window (%+d..%+d frames); left %.0f ms off the beat"
                          % (lo, hi, 1000.0 * err))
        report.append(row)
    # where each cut ACTUALLY sits now, measured on the new timeline (not trusted from the plan)
    after = boundaries(newF, joined, tr, close_on_arrival)
    for row, b in zip(report, after):
        t = b["frame"] / float(fps)
        row["t_after"] = round(t, 4)
        row["err_after_ms"] = round(1000.0 * (t - grid.t(grid.nearest_beat(t))), 1)
    return new, report


def summarise(report):
    """The numbers a person reads: how many cuts, how far off before and after, what it cost in silence."""
    if not report:
        return {"cuts": 0}
    eb = [abs(r["err_before_ms"]) for r in report]
    ea = [abs(r["err_after_ms"]) for r in report]
    add = [r["added_s"] for r in report]
    return {"cuts": len(report), "snapped": sum(1 for r in report if r["snapped"]),
            "unsnappable": [r["boundary"] for r in report if not r["snapped"]],
            "mean_abs_err_ms_before": round(sum(eb) / len(eb), 1),
            "mean_abs_err_ms_after": round(sum(ea) / len(ea), 1),
            "max_abs_err_ms_after": round(max(ea), 1),
            "added_total_s": round(sum(a for a in add if a > 0), 3),
            "trimmed_total_s": round(-sum(a for a in add if a < 0), 3),
            "max_added_s": round(max([0.0] + add), 3)}


# ── detection (Ellis 2007, numpy + scipy: librosa/aubio are not installed here) ───────────────────────────────────
SR_ENV = 8000          # Ellis: analyse at 8 kHz
WIN_MS, HOP_MS = 32, 4  # 32 ms window, 4 ms hop -> a 250 Hz onset envelope
# THE TIMESTAMP. A flux frame stamped at its window's START put every beat ~30 ms early on synthetic beds with a known
# grid (the research prototype); stamped at the window's END less one hop, the detected grid sits 2.3-3.2 ms early on
# the ten beds of tests/test_beatgrid.py (76-140 BPM) — inside one 4 ms hop.
STAMP_S = (WIN_MS - HOP_MS) / 1000.0


def _mel_fb(n_fft, sr, n_mels=40):
    mel = lambda f: 2595.0 * np.log10(1.0 + f / 700.0)                  # noqa: E731
    imel = lambda m: 700.0 * (10.0 ** (m / 2595.0) - 1.0)               # noqa: E731
    pts = imel(np.linspace(mel(0.0), mel(sr / 2.0), n_mels + 2))
    bins = np.fft.rfftfreq(n_fft, 1.0 / sr)
    fb = np.zeros((n_mels, len(bins)))
    for i in range(n_mels):
        lo, c, hi = pts[i], pts[i + 1], pts[i + 2]
        fb[i] = np.maximum(0.0, np.minimum((bins - lo) / (c - lo), (hi - bins) / (hi - c)))
    return fb


def _to_8k(x, sr):
    from scipy.signal import resample_poly
    g = math.gcd(int(sr), SR_ENV)
    return resample_poly(np.asarray(x, dtype=np.float64), SR_ENV // g, int(sr) // g)


def _frames(y, n_fft, hop):
    n_fr = 1 + (len(y) - n_fft) // hop
    if n_fr < 2:
        return None
    # a strided VIEW, windowed into the one copy: an int64 index matrix the size of the frames was a third of
    # detect()'s memory on a long track
    return np.lib.stride_tricks.sliding_window_view(y, n_fft)[::hop][:n_fr] * np.hanning(n_fft)


def onset_env(x, sr):
    """Ellis 2007 §3.1: mel-band log-power spectral flux, half-wave rectified, high-passed and smoothed.
    Returns (env, rate, t0): env[i] belongs to time t0 + i/rate."""
    from scipy.signal import lfilter
    y = _to_8k(x, sr)
    n_fft, hop = SR_ENV * WIN_MS // 1000, SR_ENV * HOP_MS // 1000
    F = _frames(y, n_fft, hop)
    if F is None:
        return None, None, None
    S = np.abs(np.fft.rfft(F, axis=1)) ** 2
    M = S @ _mel_fb(n_fft, SR_ENV).T
    dB = 10.0 * np.log10(np.maximum(M, 1e-10 * max(M.max(), 1e-30)))
    d = np.maximum(0.0, np.diff(dB, axis=0)).sum(axis=1)
    fr = SR_ENV / float(hop)
    a = math.exp(-2.0 * math.pi * 0.4 / fr)                               # ~0.4 Hz DC blocker
    d = lfilter([1.0, -1.0], [1.0, -a], d)
    g = np.exp(-0.5 * (np.arange(-15, 16) / 2.5) ** 2)                     # ~20 ms wide Gaussian
    d = np.convolve(d, g / g.sum(), mode="same")
    return d / (d.std() + 1e-9), fr, STAMP_S


def _tempo(env, fr, bpm_lo, bpm_hi, tau0=0.5, sigma_oct=0.9, max_lag_s=4.0):
    """Ellis §3.2: autocorrelation weighted by a log-Gaussian around 120 BPM, with the TPS2/TPS3 metrical sums, read
    only inside [bpm_lo, bpm_hi]. Returns (bpm, salience): salience is the chosen peak over the in-range median."""
    n = len(env)
    L = min(int(max_lag_s * fr), n - 2)
    f = np.fft.rfft(env, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:L]
    lags = np.arange(1, L) / fr
    tps = np.zeros(L)
    tps[1:] = np.exp(-0.5 * (np.log2(lags / tau0) / sigma_oct) ** 2) * ac[1:]
    t2, t3 = tps.copy(), tps.copy()
    for t in range(1, L):
        if 2 * t + 1 < L:
            t2[t] += 0.5 * tps[2 * t] + 0.25 * (tps[2 * t - 1] + tps[2 * t + 1])
        if 3 * t + 1 < L:
            t3[t] += 0.33 * (tps[3 * t] + tps[3 * t - 1] + tps[3 * t + 1])
    comb = np.maximum(t2, t3)
    bpm = 60.0 * fr / np.arange(1, L)
    ok = (bpm >= bpm_lo) & (bpm <= bpm_hi)
    if not ok.any():
        return None, 0.0
    c = np.where(ok, comb[1:], -np.inf)
    i = int(np.argmax(c)) + 1
    di = 0.0
    if 1 < i < L - 1:
        y0, y1, y2 = comb[i - 1], comb[i], comb[i + 1]
        den = y0 - 2.0 * y1 + y2
        di = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    inr = comb[1:][ok]
    sal = float(comb[i] / (np.median(np.abs(inr)) + 1e-9))
    return 60.0 * fr / (i + di), sal


def _beats_dp(env, fr, bpm, alpha=680.0):
    """Ellis Fig. 1: dynamic-programming beat search (tightness alpha 680). Returns frame indices."""
    p = int(round(fr * 60.0 / bpm))
    prange = np.arange(-2 * p, -int(round(p / 2.0)) + 1)
    tx = -alpha * np.abs(np.log(prange / -float(p))) ** 2
    n = len(env)
    cum = env.astype(np.float64).copy()
    back = -np.ones(n, dtype=int)
    for i in range(-prange[0], n):
        cand = tx + cum[i + prange]
        j = int(np.argmax(cand))
        cum[i] = cand[j] + env[i]
        back[i] = i + prange[j]
    tail = int(np.argmax(cum[max(0, n - 2 * p):])) + max(0, n - 2 * p)
    b = [tail]
    while back[b[-1]] > 0:
        b.append(back[b[-1]])
    return np.array(b[::-1])


def _lowband(x, sr):
    """Low-band (<200 Hz, the kick) energy at 4 ms, timestamped like the onset envelope."""
    y = _to_8k(x, sr)
    n_fft, hop = 256, 32
    F = _frames(y, n_fft, hop)
    S = np.abs(np.fft.rfft(F, axis=1)) ** 2
    k = int(200.0 / (SR_ENV / float(n_fft)))
    return S[:, 1:k + 1].sum(axis=1), SR_ENV / float(hop), (n_fft / 2.0) / SR_ENV


def _phase_fix(x, sr, beats):
    """The DP can lock on the OFF-beat: hats and plucks are as loud as the kick in dB flux. Compare the low band at
    the beats with the low band half a beat later and keep the heavier — the beat is where the kick and bass are
    (the research prototype's fix, kept as it was)."""
    e, fr, t0 = _lowband(x, sr)
    half = float(np.median(np.diff(beats))) / 2.0

    def at(ts):
        i = np.clip(np.round((np.asarray(ts) - t0) * fr).astype(int), 0, len(e) - 1)
        return float(np.mean([e[max(0, j - 3): j + 4].max() for j in i]))
    a, b = at(beats[:-1]), at(beats[:-1] + half)
    return (beats, a, b) if a >= b else (beats + half, a, b)


def _downbeat_phase(x, sr, beats, bpb):
    """Which of every `bpb` beats is beat one: the beat-synchronous LOW-BAND RISE (a bass note or a kick starting a
    bar). Of the four rules the research prototype tried it was the only one right on every synthetic bed (54/54:
    house, rock, syncopated, with rubato, shuffle and a lead-in); spectral flux alone failed rock and syncopation.
    10/10 on the beds of tests/test_beatgrid.py."""
    y = _to_8k(x, sr)
    n_fft, hop = 512, 128
    F = _frames(y, n_fft, hop)
    S = np.log1p(np.abs(np.fft.rfft(F, axis=1)))[:, : n_fft // 2]
    tf = (np.arange(len(S)) * hop + n_fft / 2.0) / SR_ENV
    low = []
    for t0, t1 in zip(beats[:-1], beats[1:]):
        m = (tf >= t0 - 0.02) & (tf < t1 - 0.02)
        low.append(S[m][:, :12].sum(axis=1).mean() if m.any() else 0.0)
    low = np.array(low)
    rise = np.concatenate([[0.0], np.maximum(0.0, np.diff(low))])
    if len(rise) < bpb or rise.std() < 1e-9:
        return 0, 0.0
    v = (rise - rise.mean()) / (rise.std() + 1e-9)
    sc = np.array([v[p::bpb].mean() for p in range(bpb)])
    return int(np.argmax(sc)), float(np.max(sc) - np.median(sc))


def load_audio(path, sr=44100, max_seconds=None):
    """A file's audio as mono float32 at `sr`, decoded by ffmpeg. (The mono fold reads peaks +3 dB high — irrelevant
    here: every measure in this module is relative.)"""
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr)]
    if max_seconds:
        cmd += ["-t", "%.3f" % float(max_seconds)]
    r = subprocess.run(cmd + ["-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64)


# CONFIDENCE. A track is only gridded when its beats are STEADY (one constant tempo fits them), PHASED (the onset
# envelope on the grid stands out of the other 15 phases of the same period) and STRONG (the onsets on the grid are
# well above the envelope's spread). Below any bar the answer is None and the reason is printed: snapping a film's
# cuts to a tempo the track does not have costs silence and buys nothing, so precision is worth more than recall.
# Calibrated (scratch, 2026-10-23) — synthetic drum beds 76-140 BPM and swing: beat level 3.45-4.9, phase z 8-27;
# white/brown noise, speech-like bursts and drones: level <= 1.00, z <= 6.1. 254 local Apple Loops whose tempo is
# unambiguous: the tempo is right on 198 (78%, mostly ×4/3 on swung loops otherwise — the research's figure); with
# these bars 139 right grids are kept and 9 wrong ones, so ~94% of the grids this returns are at the right tempo.
# A swung track read at 4/3 of its tempo is the residual risk: `meta.music.bpm` confines the search to ±3% of it.
MIN_STEADY_MS = 20.0      # median distance of the DP beats from the fitted constant-tempo line
MIN_PHASE_Z = 3.0         # robust (MAD) contrast of the beat phase against the period's other phases
MIN_BEAT_LEVEL = 2.5      # mean onset strength on the grid, in units of the envelope's standard deviation
MIN_SECONDS = 6.0


def detect(src, sr=None, bpm_range=DETECT_BPM_RANGE, beats_per_bar=4, fps=FILM_FPS, max_seconds=None, log=print):
    """A track's beat grid, or None — loudly explained — when the detector is not sure.

    `src` is a path or a mono array (then `sr` is required). Tempo by weighted autocorrelation limited to
    `bpm_range`, beats by Ellis's DP, the half-beat lock fixed on the low band, then ONE constant tempo fitted to the
    beats (an author track is assumed to be at one tempo; a DAW-made bed is). The returned grid's `info` carries the
    raw DP beats, the confidence numbers and the downbeat's strength."""
    if np is None:
        raise RuntimeError("detect needs numpy + scipy")
    if isinstance(src, str):
        sr = sr or 44100
        x = load_audio(src, sr, max_seconds)
        name = os.path.basename(src)
    else:
        if not sr:
            raise ValueError("detect(array) needs its sample rate")
        x = np.asarray(src, dtype=np.float64)
        if max_seconds:
            x = x[: int(max_seconds * sr)]
        name = "the bed"

    def no(why):
        log("[beatgrid] no beat grid for %s: %s" % (name, why))
        return None
    if len(x) < MIN_SECONDS * sr:
        return no("%.1fs of audio is too short to hold a tempo (needs %.0fs)" % (len(x) / float(sr), MIN_SECONDS))
    if float(np.max(np.abs(x))) < 1e-4:
        return no("it is silent")
    env, fr, t0 = onset_env(x, sr)
    if env is None:
        return no("too short to analyse")
    bpm0, sal = _tempo(env, fr, *bpm_range)
    if bpm0 is None:
        return no("no tempo inside %s BPM" % (bpm_range,))
    fbeats = _beats_dp(env, fr, bpm0)
    if len(fbeats) < 8:
        return no("the beat search found only %d beats" % len(fbeats))
    beats = t0 + fbeats / fr
    beats, low_on, low_off = _phase_fix(x, sr, beats)
    # ONE TEMPO: a least-squares line through the beats, indexed by whole periods so a skipped or doubled beat in the
    # DP's path does not bend it
    per0 = 60.0 / bpm0
    idx = np.round((beats - beats[0]) / per0)
    A = np.vstack([np.ones_like(idx), idx]).T
    (a, per), *_ = np.linalg.lstsq(A, beats, rcond=None)
    resid = beats - (a + per * idx)
    steady = float(np.median(np.abs(resid))) * 1000.0
    # PHASED: the onset envelope sampled on the fitted grid at 16 phases of one period — a beat track peaks at one
    # phase; a drone, noise or speech has no preferred phase
    span = (t0 + np.arange(len(env)) / fr)
    k = np.arange(int(math.floor((span[0] - a) / per)) + 1, int(math.floor((span[-1] - a) / per)))
    prof = []
    for q in range(16):
        ts = a + (k + q / 16.0) * per
        j = np.clip(np.round((ts - t0) * fr).astype(int), 0, len(env) - 1)
        prof.append(float(np.mean([env[max(0, i - 2): i + 3].max() for i in j])))
    prof = np.array(prof)
    # ROBUST contrast (median absolute deviation, not the standard deviation): over 16 phases a single clean peak
    # can score at most sqrt(15) ~ 3.9 standard deviations, so a std z-score put real drum beds at 3.1-3.9 and white
    # noise at 2.1 — no room for a threshold. Against the MAD, the other 15 phases are the scale and a beat stands
    # far out of them while noise does not (tests/test_beatgrid.py calibrates it).
    med = float(np.median(prof))
    mad = float(np.median(np.abs(prof - med))) * 1.4826
    z = float((prof[0] - med) / (mad + 0.02 * (abs(prof).max() + 1e-9) + 1e-9))
    bpm = 60.0 / per
    # how strong the onsets ON the grid are, in units of the envelope's own spread (it is normalised by its std)
    level = float(prof[0])
    info = {"bpm_raw": round(float(bpm0), 3), "tempo_salience": round(sal, 2), "steady_ms": round(steady, 1),
            "phase_z": round(z, 2), "beat_level": round(level, 2), "beats": [round(float(b), 4) for b in beats],
            "low_on_off": [round(low_on, 4), round(low_off, 4)]}
    if steady > MIN_STEADY_MS:
        return no("its beats do not keep one tempo (median %.0f ms off a steady %.1f BPM; limit %.0f ms) — "
                  "a tempo change, rubato, or no beat at all" % (steady, bpm, MIN_STEADY_MS))
    if z < MIN_PHASE_Z or level < MIN_BEAT_LEVEL:
        return no("no clear beat (phase contrast %.1f, needs %.1f; onset level %.2f, needs %.2f) — a pad, a drone "
                  "or speech has no pulse to cut to" % (z, MIN_PHASE_Z, level, MIN_BEAT_LEVEL))
    db, db_strength = _downbeat_phase(x, sr, beats, beats_per_bar)
    first_down = a + db * per
    info["downbeat_strength"] = round(db_strength, 2)
    return BeatGrid(bpm, first_down, beats_per_bar, fps, "detected", info)


def beat_errors(beats, grid):
    """Each detected beat's distance to the nearest grid beat, in ms (signed: detected - grid)."""
    b = np.asarray(beats, dtype=np.float64)
    i = np.round((b - grid.offset_s) / grid.period)
    return (b - (grid.offset_s + i * grid.period)) * 1000.0


class BedOffGrid(RuntimeError):
    """The generated bed's own beats are not where its grid says — a bug in the score, never a judgement call."""


def verify_bed(x, sr, grid, limit_ms=BED_LIMIT_MS, log=print):
    """Re-detect the beats of a RENDERED bed and hold them to its grid: median |error| under `limit_ms`, at the
    grid's own tempo. The score is synthesised ON the grid, so this measures the detector's own error: 0-5.3 ms on
    generated beds (48 beds, 8 seeds x 6 tempos: 4.3 ms worst median). Anything near the limit means the synthesis and
    the grid disagree, and that ships as music landing off every cut. Raises BedOffGrid; returns the numbers when it
    passes."""
    g = detect(x, sr=sr, bpm_range=(grid.bpm * 0.97, grid.bpm * 1.03), beats_per_bar=grid.beats_per_bar,
               fps=grid.fps, log=log)
    if g is None:
        raise BedOffGrid("the generated bed has no detectable beat at its own tempo (%.2f BPM)" % grid.bpm)
    e = beat_errors(g.info["beats"], grid)
    med = float(np.median(np.abs(e)))
    p95 = float(np.percentile(np.abs(e), 95))
    out = {"median_ms": round(med, 2), "p95_ms": round(p95, 2), "bias_ms": round(float(np.median(e)), 2),
           "beats": int(len(e)), "bpm_detected": round(g.bpm, 3)}
    if abs(g.bpm / grid.bpm - 1.0) > 0.01:
        raise BedOffGrid("the bed re-detects at %.2f BPM against its grid's %.2f" % (g.bpm, grid.bpm))
    if med >= limit_ms:
        raise BedOffGrid("the bed's beats sit a median %.1f ms off its grid (limit %.0f ms; p95 %.1f ms)"
                         % (med, limit_ms, p95))
    return out


# ── beats.json: written at the tts stage, read by the render ─────────────────────────────────────────────────────
def write(out_dir, doc):
    path = os.path.join(out_dir, BEATS_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    return path


def read(out_dir):
    path = os.path.join(out_dir, BEATS_FILE)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def climax_boundary(slides):
    """The boundary the music builds INTO: the last beat declaring `relation: payoff`, else the `close`, else None.
    The board's relations are the argument's shape (seam_plan.py); a payoff is where it lands."""
    rel = [str((s or {}).get("relation") or "").strip().lower() for s in slides]
    for want in ("payoff", "close"):
        ks = [k for k in range(1, len(rel)) if rel[k] == want]
        if ks:
            return ks[-1], want
    return None, None


def music_for_render(out_dir, slides, scenes, meta, tr=None, log=print):
    """What render_remotion hands sfx.mix: {'grid', 'climax_s', 'bgm_skip_s', 'stale'} — or None for a film without
    music (which then mixes exactly as it always has; a leftover beats.json from an earlier scored run is ignored).

    The grid is the one tts.py wrote, checked against the board it is about to score: when the beat lengths no
    longer match the ones it was snapped for (an edited board, a re-voiced beat), the cuts are not on that grid any
    more, and it is re-fitted to them as they are (tier 1) — and said."""
    if not music_requested(meta):
        return None
    tr = seam_frames() if tr is None else tr
    import stage_runs as _sr
    joined = _sr.joined_flags(scenes)
    durF = [int(sc["durF"]) for sc in scenes]
    bnd = boundaries(durF, joined, tr, close_on_arrival=True)
    cuts = [b["frame"] / float(FILM_FPS) for b in bnd]
    doc = read(out_dir)
    k, rel = climax_boundary(slides)
    climax_s = cuts[k - 1] if k else None
    if not doc or not doc.get("grid"):
        if meta.get("bgm") == "auto":
            log("[beatgrid] no beats.json grid — fitting the score to the cuts as they are (tier 1 only; tts.py snaps "
                "the pads when it runs with music on)")
            g = fit_to_cuts(cuts, climax=climax_s, bpm=_pinned_bpm(meta))
            return {"grid": g, "climax_s": climax_s, "bgm_skip_s": 0.0, "stale": True}
        return None
    grid = BeatGrid.from_dict(doc["grid"])
    skip = float(doc.get("bgm_skip_s") or 0.0)
    want = doc.get("durF")
    if want != durF:
        log("[beatgrid] WARNING: beats.json was snapped for other beat lengths (the board changed since tts.py) — "
            "the cuts are NOT on its grid; re-fitting the phase to the cuts as they are. Re-run tts.py to snap them.")
        if grid.source == "detected":
            # an author track keeps its tempo; only where it starts can move (a skip of less than one bar)
            g = fit_to_cuts(cuts, bpm=grid.bpm, climax=climax_s, source="detected", beats_per_bar=grid.beats_per_bar)
            skip = _skip_for(doc, g)
            grid = g
        else:
            grid = fit_to_cuts(cuts, climax=climax_s, bpm=grid.bpm if grid.source == "author" else None,
                               source=grid.source)
        return {"grid": grid, "climax_s": climax_s, "bgm_skip_s": skip, "stale": True}
    return {"grid": grid, "climax_s": doc.get("climax", {}).get("t") if doc.get("climax") else climax_s,
            "bgm_skip_s": skip, "stale": False}


def _pinned_bpm(meta):
    mu = (meta or {}).get("music") or {}
    b = mu.get("bpm") if isinstance(mu, dict) else None
    return float(b) if isinstance(b, (int, float)) and not isinstance(b, bool) else None


def _skip_for(doc, grid):
    """How much of an author track's head to skip so its detected downbeat lands on `grid`'s downbeat."""
    track = doc.get("track_grid") or {}
    t_down = float(track.get("offset_s", 0.0))
    return round((t_down - grid.offset_s) % grid.bar_s, 6)


def plan_film(slides, meta, bgm_path=None, slack=None, log=print):
    """THE TTS-STAGE STEP: choose the film's grid and snap its pads. Pure apart from detecting an author track.

    Returns a beats.json document whose 'durations' are the new per-beat seconds (the caller pads the clips), or
    None when no grid can be had (the reason printed). Never changes a duration by more than its window."""
    import stage_runs as _sr
    tr = seam_frames()
    fps = FILM_FPS
    durations = [float(s.get("duration") or 0.0) for s in slides]
    joined = _sr.joined_flags(slides)
    durF = [dur_frames(d, fps) for d in durations]
    bnd = boundaries(durF, joined, tr, close_on_arrival=True)
    cuts = [b["frame"] / float(fps) for b in bnd]
    mu = (meta or {}).get("music") or {}
    snap = (mu.get("snap") if isinstance(mu, dict) else None) or "beat"
    k, rel = climax_boundary(slides)
    climax_s = cuts[k - 1] if k else None
    slack = slack or [0.0] * len(slides)
    windows = [(lo / float(fps), hi / float(fps)) for lo, hi in pad_windows(durF, bnd, slack, tr, fps)]
    if snap == "off":
        windows = None
    pinned = _pinned_bpm(meta)
    track = None
    skip = 0.0
    if bgm_path:
        rng = DETECT_BPM_RANGE if pinned is None else (pinned * 0.97, pinned * 1.03)
        film_s = film_frames(durF, joined, tr) / float(fps)
        try:
            track = detect(bgm_path, bpm_range=rng, max_seconds=film_s + 8.0, log=log)
        except Exception as e:                       # noqa: BLE001 — an unreadable track is reported, not raised
            log("[beatgrid] could not read the author track %s (%s: %s)" % (bgm_path, type(e).__name__, e))
            track = None
        if track is None:
            log("[beatgrid] the author track has no grid this pipeline trusts — its cuts are NOT snapped and its "
                "whooshes stay on their seams; the music still plays, untouched (it is never time-stretched)")
            return None
        # AN AUTHOR TRACK IS NEVER TIME-STRETCHED: its tempo is fixed and only where it STARTS can move — the head
        # of the track is skipped by less than one bar, which slides its whole grid under the cuts
        grid = fit_to_cuts(cuts, bpm=track.bpm, windows=windows, climax=climax_s, source="detected",
                           beats_per_bar=track.beats_per_bar)
        skip = round((track.offset_s - grid.offset_s) % grid.bar_s, 6)
    else:
        grid = fit_to_cuts(cuts, windows=windows, climax=climax_s, bpm=pinned,
                           source="author" if pinned else "synth", frame_locked=pinned is None)
    if windows is None:
        new = list(durations)
        _, report = snap_pads(durations, joined, grid, tr=tr, max_add_s=0.0, max_trim_s=0.0, close_on_arrival=True)
        for r in report:
            if not r["snapped"]:
                r["why"] = "meta.music.snap is off: measured, not moved (%.0f ms off the beat)" % r["err_after_ms"]
    else:
        new, report = snap_pads(durations, joined, grid, tr=tr, slack=slack, close_on_arrival=True)
    newF = [dur_frames(d, fps) for d in new]
    doc = {"version": 1, "grid": grid.to_dict(), "snap": snap, "fps": fps, "seam_frames": tr,
           "bgm": bgm_path and os.path.basename(bgm_path) or "auto", "bgm_skip_s": skip,
           "track_grid": track.to_dict() if track else None,
           "track_confidence": {k2: track.info[k2] for k2 in ("steady_ms", "phase_z", "tempo_salience",
                                                               "downbeat_strength") if k2 in track.info}
           if track else None,
           "climax": {"boundary": k, "relation": rel,
                      "t": [r["t_after"] for r in report if r["boundary"] == k][0]} if k else None,
           "durations": [round(d, 6) for d in new], "durF": newF,
           "added_s": [round(a - b, 6) for a, b in zip(new, durations)],
           "cuts": report, "summary": summarise(report),
           "film_s": round(film_frames(newF, joined, tr) / float(fps), 4)}
    return doc


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip().split("\n\n")[0])
        return 0
    if argv[0] == "--detect":
        if len(argv) < 2:
            print("usage: beatgrid.py --detect <track>")
            return 2
        g = detect(argv[1])
        if g is None:
            return 1
        print(repr(g))
        print(json.dumps({k: v for k, v in g.info.items() if k != "beats"}, indent=1))
        return 0
    doc = read(argv[0])
    if not doc:
        print("[beatgrid] no %s in %s — tts.py writes it when the board asks for music "
              "(meta.sound_design + meta.bgm on the remotion tier)" % (BEATS_FILE, argv[0]))
        return 1
    g = BeatGrid.from_dict(doc["grid"])
    print(repr(g), "| snap:", doc.get("snap"), "| bgm:", doc.get("bgm"), "| skip %.3fs" % doc.get("bgm_skip_s", 0))
    for r in doc.get("cuts") or []:
        print("  boundary %2d %-6s %7.3fs -> %7.3fs  err %+6.1f -> %+6.1f ms  %s%s"
              % (r["boundary"], r["kind"], r["t_before"], r["t_after"], r["err_before_ms"], r["err_after_ms"],
                 ("+%.2fs" % r["added_s"]) if r["added_s"] > 0 else ("%.2fs" % r["added_s"]) if r["added_s"] else "",
                 "" if r["snapped"] else "  UNSNAPPED: " + r.get("why", "")))
    print(json.dumps(doc.get("summary"), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
