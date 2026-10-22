#!/usr/bin/env python3
"""Does this film USE the fact that it is a film? — a post-render gate on out.mp4.

    python3 scripts/film_energy_qa.py <out_dir>
    python3 scripts/film_energy_qa.py --reference <dir>   # re-measure the four films the floors come from

WHY THIS EXISTS. The remotion tier's whole claim over the html tier is TIME: motion, cutting, light that
changes. A delivered 30-beat film was described by its own author as something the html tier could have
produced, and the measurement agreed — so the claim was not being cashed, and nothing in the pipeline could
tell. Every other gate here asks whether a frame is correct. None asked whether the film moves.

THE FLOORS COME FROM REAL FILMS, not from taste. Four official product launch films were downloaded and
measured with the same instrument as the deck under test — greyscale at 12fps, 192x108:

    film                     frame-diff p75   median ink   luminance range   light STEPS
    Apple  iPhone 17 Pro           0.0357        24.3%          0.270            0.038
    OpenAI Codex Micro             0.0075        64.4%          0.330            0.060
    Figma  Config launches         0.0481        36.1%          0.903            0.425
    Anthropic Keep thinking        0.0381        42.1%          0.350            0.191
    -------------------------------------------------------------------------------------
    the film that prompted this    0.0023         4.3%          0.079            0.000

WHY THERE IS A FOURTH AXIS, added after the third was shown to be gameable. `luminance range` is p95 - p5
over the whole film, so it asks only whether the film CONTAINS a bright frame and a dark frame. It does not
ask whether light ever does anything. Measured: taking the 56s film above and appending FOUR SECONDS of a
flat white rectangle moves its range from 0.0972 to 0.9101 — clearing the floor by 6.7x and landing on
Figma's number — while every other frame is byte-identical. A blank rectangle is not a luminance arc.

`light steps` is the fraction of ADJACENT one-second windows whose mean luminance differs by >= 0.12. It asks
how often the light CHANGES, which is the property the range was standing in for. On the same three films:

    56s film as delivered      range 0.0972   steps 0.000
    + one 4s white block       range 0.9101   steps 0.017   <- range says excellent, steps says nothing moved
    bright beats DISTRIBUTED   range 0.9097   steps 0.133   <- the same range, and light that actually works

Two candidate statistics were tried and REJECTED on the same corpus rather than adopted on intuition: a
robust sigma (MAD x 1.4826) of the window means put our delivered film at 0.0398 against OpenAI's 0.0399 —
no separation at all — and the window IQR passed our film at half the lowest reference. Both are recorded
here so the next person does not re-derive them.

Three of those four are largely LIVE ACTION (Apple adds offline PBR renders), which a DOM compositor cannot
reach and should not chase. Figma's is the reachable one: entirely generative, no camera, and unambiguously
launch-grade. That it sits at the TOP of the motion and luminance columns is the useful part.

Each floor is HALF the lowest reference, deliberately lenient — this is a floor, not a target, and passing it
says only that the film is not a slideshow. The film above fails all three by 3.3x, 5.6x and 3.4x.

WHAT THE NUMBERS DO NOT SAY. Four films is a small corpus and three of them are a different production
category. Ink is measured against a per-frame median ground, so a full-bleed gradient reads as empty — which
is intended, a gradient is not content, but it means a deliberately atmospheric film will score low. A quiet
film can be right; `meta.energy_waiver` accepts one, and requires a written reason, because the discipline
this codebase runs on is that an accepted warning is a decision someone made rather than one that defaulted.

WHAT THIS GATE'S UNIVERSE IS, AND HOW IT SAYS SO. Every number above is a statistic over the frames ffmpeg
handed back, and that is NOT the same set as the film. `-v error` sends ffmpeg's own complaints to a stderr
this script used to discard, and its exit code was never read, so a PARTIAL decode came back as a shorter
film rather than as a failure. Measured, on a real 88.9s delivered film truncated to 40% of its bytes:
ffmpeg printed `partial file`, exited non-zero, and handed back 371 frames — this gate printed `31s`,
reported `OK  0 error(s)` and exited 0, having measured 35% of the film under a headline that read as the
film. The universe is therefore DERIVED from the container (`ffprobe` duration, never a constant), the
headline states coverage against it, and a short decode is an error `meta.energy_waiver` cannot touch: a
waiver is a judgement about a film someone watched, and this is a report that the film was never read.
"""
import glob
import json
import os
import subprocess
import sys

# Half the lowest of the four reference films, per the table above.
MOTION_P75_FLOOR = 0.0037     # lowest reference 0.0075 (OpenAI, a talking-head film — the quietest kind)
INK_FLOOR = 0.12              # lowest reference 0.243 (Apple: dark frames, one lit subject)
LUMA_RANGE_FLOOR = 0.135      # lowest reference 0.270 (Apple)
MIN_FRAMES = 8                # below this there are too few frame-diffs for a p75 to mean anything
# The light ARC. Floor is half the lowest reference (Apple 0.038) like the others; the delta is the size of a
# change worth calling one, and the window is a second because launch films cut every 0.75-3s.
LUMA_STEP_FLOOR = 0.019
LUMA_STEP_DELTA = 0.12
LUMA_WINDOW_SECONDS = 1
MIN_WINDOWS = 4               # under four seconds there is no arc to measure, and saying so beats guessing
# COVERAGE. The decode is allowed to land a little short of the container's duration — the sampler drops the
# fractional tail frame, and a container rounds — so a shortfall must clear BOTH of these to be a finding.
# They are deliberately loose: this exists to catch a decode that stopped, not to police rounding.
COVERAGE_MIN_GAP = 1.0        # seconds; under this, no arithmetic on a normal film can raise a finding
COVERAGE_TOLERANCE = 0.02     # …and at least this fraction of what the file claims

# The four films the floors are derived from, and the file each was measured from. A record nobody can
# regenerate is not a measurement, it is a memory — so `--reference <dir>` re-measures them and reports drift.
# The films are not in the repo (they are not ours to redistribute); the command names what to put in the
# directory, and says so plainly when a file is absent instead of quietly measuring three of four.
# The INK column is kept as a RECORD and is no longer compared: those numbers were measured under the old
# "share of pixels far from the frame's modal tone" definition, which `_drawn` replaced after it scored a
# film's emptiest frame as its second fullest. They cannot be re-derived without re-measuring these four
# films, which are not in the repo — so the density floor went with the old metric rather than being
# re-guessed from them, and `--reference` checks the three axes it can still honestly check.
REFERENCE = {                 # (motion_p75, [retired: ink_median], luma_range, luma_steps)
    "Apple iPhone 17 Pro": (0.0357, 0.243, 0.270, 0.038),
    "OpenAI Codex Micro": (0.0075, 0.644, 0.330, 0.060),
    "Figma Config": (0.0481, 0.361, 0.903, 0.425),
    "Anthropic Keep thinking": (0.0381, 0.421, 0.350, 0.191),
}
REFERENCE_FILES = {
    "Apple iPhone 17 Pro": "apple_hw",
    "OpenAI Codex Micro": "openai",
    "Figma Config": "figma",
    "Anthropic Keep thinking": "anthropic",
}
REFERENCE_COMPARED = (0, 2, 3)          # motion_p75, luma_range, luma_steps — ink is a record now
REFERENCE_DRIFT = 0.02        # re-encodes and re-downloads move these a little; a real drift moves them more


def verify_reference(directory):
    """Re-measure each reference film found in `directory` and report drift from the recorded table."""
    rows, missing = [], []
    for name, stem in sorted(REFERENCE_FILES.items()):
        hits = sorted(glob.glob(os.path.join(directory, stem + ".*")))
        if not hits:
            missing.append("%s (expected %s.* in %s)" % (name, stem, directory))
            continue
        m = measure(hits[0])
        if not isinstance(m, dict):
            missing.append("%s (%s could not be measured)" % (name, os.path.basename(hits[0])))
            continue
        got = (m["motion_p75"], m["ink_median"], m["luma_range"], m["luma_steps"] or 0.0)
        drift = max(abs(REFERENCE[name][i] - (got[i] or 0.0)) for i in REFERENCE_COMPARED)
        rows.append((name, REFERENCE[name], got, drift))
    return rows, missing


# WHAT "INK" MEANS, AND WHY IT WAS MEASURED BACKWARDS FOR A YEAR.
#
# It used to be `(|f - median(f)| > 0.10).mean()` — the share of pixels far from the frame's modal tone.
# That is a measure of how much of the frame is a FILLED FIELD, not of how much is DRAWN ON, and on a film
# whose language is hairlines and type the two come apart completely. Measured on a delivered 30-beat film,
# with the frames then opened and looked at:
#
#   beat 19 — five heavily blurred, information-free plates and one sharp card   OLD 22.5%  (2nd densest!)
#   beat  7 — two labels and four list rows, carried by two large colour fields  OLD 49.2%
#   beat 15 — a full stone slab with two lines of giant carved type              OLD  5.0%  (near the bottom)
#
# The gate's own sentence is "an empty frame with a caption on it is not sparse, it is unfinished" — and it
# was scoring the film's emptiest frame as its second fullest, because blurred grey plates deviate from
# cream. So the question it asks is now the one it meant: is there STRUCTURE here — edges, strokes, rules,
# type — or is this a coloured area? Local gradient answers that. Thin type scores; a flat block does not,
# except at its border; a blurred plate does not at all, which is exactly right.
#
#   the same three beats, re-measured                                            NEW 3.0% · 4.4% · 6.7%
#
# THE ABSOLUTE FLOOR IS RETIRED WITH THE OLD METRIC, NOT RE-GUESSED. The old 12% was "half of the sparsest
# reference, Apple's 24.3%" — a number derived from reference films measured under the OLD definition, so
# it does not carry over, and this repo has no corpus to re-derive one from. Inventing a replacement from
# the one film in front of me is the error recorded all over this codebase. The axis therefore REPORTS: the
# film's own distribution and the beats at the bottom of it, which is the question an author can act on
# ("which of my beats is least drawn on?") rather than one they can only waive.
_EDGE = 0.04          # a local step this size is a mark; below it is paper grain and gradient banding
# ...AND DENSITY IS MEASURED AT ITS OWN RESOLUTION, in a second decode. Structure is scale-dependent in a
# way a mean is not: at the 192px long side the other axes use, the film's confirmed-emptiest beat (five
# heavily blurred, information-free plates) ranked TWELFTH of thirty, because at that size a soft plate
# border still counts as an edge while 24px type does not resolve at all. At 384 it ranks second, at 640
# first; the confirmed-full and confirmed-densest beats rank 25-27th and 30th at every size, so the ranking
# is stable once the question can be resolved at all.
#
# The obvious move — raise `long_side` for everything — is the one that must not be made: MOTION is a
# frame-difference and IT MOVES WITH SCALE. Measured on the same film, p75 goes 0.00284 -> 0.00339 between
# 192 and 384 against a 0.0037 floor, i.e. from 23% under to 8% under with nothing about the film changed.
# That floor was calibrated against reference films decoded at 192, so a wider decode would silently
# recalibrate it. Two decodes, two questions, neither one quietly moving the other's bar.
DENSITY_LONG_SIDE = 384


def beat_spans(board, n, fps):
    """[(index, shot, f0, f1)] — each beat's sampled frames [f0, f1) ON THE FILM'S OWN CLOCK. A beat's position in
    out.mp4 is NOT the running sum of the board's durations: the renderer compresses every cut by its seam length,
    so summing durations drifts further out of place with every seam — eleven seconds of it by the end of a 30-beat
    film. The seam length is read from the renderer rather than restated here, so the two cannot disagree. The
    first and last sampled frame of each window are dropped (they straddle a cut); a beat shorter than two sampled
    frames is left out. Raises when the board cannot be read; callers keep their film-level numbers."""
    import render_remotion as _rr
    slides = board.get("slides") or []
    seam = _rr._REMOTION2_TR / float((board.get("meta") or {}).get("fps") or 30)
    import stage_runs as _sr
    joined = _sr.joined_flags(slides)                 # no seam inside a stage run (Film.tsx sceneStarts)
    out, t = [], 0.0
    for i, sl in enumerate(slides):
        a = t
        b = a + float(sl.get("duration") or 0)
        t = b - (seam if i + 1 < len(slides) and not joined[i + 1] else 0)
        f0, f1 = int(a * fps) + 1, min(n, int(b * fps) - 1)
        if f1 > f0:
            out.append((i + 1, sl.get("shot"), f0, f1))
    return out


def density(path, board=None, fps=12, long_side=None):
    """{median, beats:[{index, shot, drawn}]} — how much of each frame is DRAWN ON, at the resolution that
    question needs. Returns None when it cannot decode; the axis then reports that it did not run."""
    try:
        import numpy as np
    except ImportError:
        return None
    ls = long_side or DENSITY_LONG_SIDE
    size = probe_size(path)
    if not size:
        return None
    W0, H0 = size
    if W0 >= H0:
        w, h = ls, max(2, int(round(ls * H0 / W0)) // 2 * 2)
    else:
        h, w = ls, max(2, int(round(ls * W0 / H0)) // 2 * 2)
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf",
                           "fps=%d,scale=%d:%d" % (fps, w, h), "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                          capture_output=True)
    n = len(proc.stdout) // (w * h)
    if n < MIN_FRAMES:
        return None
    F = np.frombuffer(proc.stdout[:n * w * h], dtype=np.uint8).reshape(n, h, w).astype(np.float32) / 255.0
    out = {"median": float(np.median([_drawn(f) for f in F[::2]])), "beats": []}
    # PER-BEAT, ON THE FILM'S OWN CLOCK (beat_spans).
    if board:
        try:
            for idx, shot, f0, f1 in beat_spans(board, n, fps):
                out["beats"].append({"index": idx, "shot": shot,
                                     "drawn": float(np.mean([_drawn(f) for f in F[f0:f1]]))})
        except Exception:                          # noqa: BLE001 — the per-beat half never breaks the axis
            out["beats"] = []
    return out


def _drawn(f):
    """Share of the frame carrying local STRUCTURE — an edge, a stroke, a rule, a glyph.

    numpy is imported here rather than at module scope because this file's whole point is to be runnable
    where it is not installed: `measure` returns None instead of raising, and the caller says "needs
    ffmpeg + numpy" rather than dying on an import nobody asked for."""
    import numpy as np
    gy = np.abs(np.diff(f, axis=0))[:, :-1]
    gx = np.abs(np.diff(f, axis=1))[:-1, :]
    return float((np.maximum(gx, gy) > _EDGE).mean())


def probe_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        w, h = [int(x) for x in out.strip().rstrip(",").split(",")[:2]]
        return (w, h) if w > 0 and h > 0 else None
    except (ValueError, IndexError):
        return None


def probe_duration(path):
    """The seconds the FILE claims — this gate's universe, parsed from the container rather than assumed.

    Two entries because they disagree and either can be absent: a remuxed mp4 can carry a format duration
    with no stream one, and a raw stream the reverse. Whichever answers first and is positive wins; None
    means the file would not say, which is itself reportable — it is the difference between "I measured all
    of it" and "I have no idea how much of it I measured".
    """
    for select, entries in ((None, "format=duration"), ("v", "stream=duration")):
        args = ["ffprobe", "-v", "error"] + (["-select_streams", select] if select else [])
        args += ["-show_entries", entries, "-of", "csv=p=0", path]
        out = subprocess.run(args, capture_output=True, text=True).stdout
        for tok in out.replace(",", "\n").split():
            try:
                v = float(tok)
            except ValueError:
                continue
            if v > 0:
                return v
    return None


def measure(path, fps=12, long_side=192, board=None):
    """Greyscale frame-difference, ink coverage and luminance spread. Same instrument for every film.

    The sampling frame PRESERVES ASPECT. Forcing every film into 192x108 squashes a portrait one, and
    squashing blends neighbouring pixels, which lowers local contrast and so undercounts ink: measured on the
    same shot rendered three ways, the forced scale read 2.2 points low at 9:16 and 1.4 low at 1:1. Small, but
    systematically in the direction that makes a vertical film harder to pass than a landscape one — a bias
    with no defensible reason behind it.
    """
    try:
        import numpy as np
    except ImportError:
        return None
    size = probe_size(path)
    if not size:
        return None
    W0, H0 = size
    if W0 >= H0:
        w, h = long_side, max(2, int(round(long_side * H0 / W0)) // 2 * 2)
    else:
        h, w = long_side, max(2, int(round(long_side * W0 / H0)) // 2 * 2)
    # The return code and stderr are READ, not discarded. ffmpeg happily hands back the frames it managed
    # before giving up, so a truncated or damaged file used to arrive here as a shorter film.
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf",
                           "fps=%d,scale=%d:%d" % (fps, w, h), "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                          capture_output=True)
    raw = proc.stdout
    n = len(raw) // (w * h)
    if n < MIN_FRAMES:
        return n                                     # an INT, not None: the caller says which failure it was
    F = np.frombuffer(raw[:n * w * h], dtype=np.uint8).reshape(n, h, w).astype(np.float32) / 255.0
    D = np.abs(np.diff(F, axis=0))
    d = D.mean(axis=(1, 2))
    # FROZEN is not "under the floor". A small object moving — a needle, grains settling — changes a few hundred
    # pixels and stays far under a whole-frame mean; frozen means NO pixel changed by a mark's step (_EDGE) AND the
    # frame as a whole changed less than the floor (a fade moves every pixel a little and no pixel by a mark), so a
    # frozen difference is always also an under-floor one. And it is asked over a SECOND as well as a frame: a slow
    # drift — an idle clock, a low-contrast object creeping a pixel at a time — moves under a mark's step between two
    # sampled frames and well past it within a second, and frame-to-frame alone would call it frozen.
    moved = (D > _EDGE).any(axis=(1, 2)) | (d >= MOTION_P75_FLOOR)
    del D
    lag = max(1, int(round(fps * LUMA_WINDOW_SECONDS)))
    for i in range(len(moved)):
        if not moved[i] and i + 1 >= lag:
            moved[i] = bool((np.abs(F[i + 1] - F[i + 1 - lag]) > _EDGE).any())
    ink = []                                       # density has its own decode — see DENSITY_LONG_SIDE
    lum = F.mean(axis=(1, 2))
    k = max(1, int(round(fps * LUMA_WINDOW_SECONDS)))
    win = [float(lum[i:i + k].mean()) for i in range(0, len(lum) - k + 1, k)]
    # None, not 0.0, when the film is too short to have an arc: a zero here would read as "measured, and it
    # never moves", which is a different and much worse claim than "not long enough to ask".
    steps = (sum(1 for a, b in zip(win, win[1:]) if abs(b - a) >= LUMA_STEP_DELTA) / (len(win) - 1)
             if len(win) >= MIN_WINDOWS else None)
    err = (proc.stderr or b"").decode("utf-8", "replace").strip()
    # PER-BEAT, ON THE FILM'S OWN CLOCK. A beat's position in out.mp4 is NOT the running sum of the board's
    # durations: the renderer compresses every cut by its seam length, so summing durations drifts a beat
    # further out of place with every seam — by the end of a 30-beat film, eleven seconds of it. The seam
    # length is read from the renderer rather than restated, so the two cannot disagree.
    return {
        "beats": [],
        "motion_beats": motion_by_beat(d, moved, board, n, fps) if board else [],
        # the share of frame differences under the motion floor: p75 < floor exactly when this is over 0.75
        "motion_under_floor": float((d < MOTION_P75_FLOOR).mean()),
        "seconds": n / fps,
        "frames": n,
        "fps": fps,
        # The universe, and what the decode said about reaching it. None for `declared_seconds` is a real
        # answer ("the file would not say"), never a silent 0.
        "declared_seconds": probe_duration(path),
        "decode_rc": proc.returncode,
        "decode_stderr": err,
        "motion_p50": float(np.percentile(d, 50)),
        "motion_p75": float(np.percentile(d, 75)),
        "motion_p90": float(np.percentile(d, 90)),
        "ink_median": float(np.median(ink)) if len(ink) else None,
        "luma_range": float(np.percentile(lum, 95) - np.percentile(lum, 5)),
        "luma_steps": steps,
        "luma_windows": len(win),
    }


# WHERE THE FILM SITS UNDER THE FLOOR. The motion floor asks one question of the whole film — are more than three
# quarters of its frame differences under MOTION_P75_FLOOR? — and a film under it was told only its p75. Every diagram
# film this skill has delivered sits under it (p75 0.0005-0.0015, each one waived), and the waiver was the only lever
# the message offered, because it never said WHICH beats hold the film down. This splits the same count by beat, at
# the floor's own threshold, so nothing new is calibrated: the film's share under the floor is its beats' summed.
#
# UNDER THE FLOOR IS NOT FROZEN, and the split says both. Measured on three delivered films: a GradientRuler beat was
# under the floor for 94% of its frames and frozen for 0% (its ruler never stops moving — a few hundred pixels of a
# 20,736-pixel decode), while a NeuralField beat was under it for 96% and frozen for 74%. A reason like "the motion IS
# the mechanism" is about the first kind; only FROZEN seconds — no pixel changed by a mark's step — say that nothing
# on the frame moves. Reading the under-floor seconds as "still" would call the first beat inert.
def motion_by_beat(d, moved, board, n, fps):
    """[{index, shot, seconds, under_s, frozen_s, p75}] — each beat's sampled seconds, how many of them are under the
    motion floor, how many are FROZEN (no pixel changed), and the beat's own p75. [] when the board cannot be placed
    on the film."""
    try:
        import numpy as np
        rows = []
        for idx, shot, f0, f1 in beat_spans(board, n, fps):
            hi = max(f0, f1 - 1)                     # differences BETWEEN this beat's own frames
            seg, mv = d[f0:hi], moved[f0:hi]
            if len(seg) < 4:
                continue
            rows.append({"index": idx, "shot": shot, "seconds": len(seg) / float(fps),
                         "under_s": float((seg < MOTION_P75_FLOOR).sum()) / fps,
                         "frozen_s": float((~mv).sum()) / fps,
                         "p75": float(np.percentile(seg, 75))})
        return rows
    except Exception:                              # noqa: BLE001 — the per-beat half never breaks the axis
        return []


def under_floor_line(m):
    """One sentence naming the beats that hold the film under the motion floor, or "" when there is no per-beat
    split. The film clears the floor once AT MOST three quarters of its frame differences are under it, so the
    shortfall is the under-floor seconds above that share — counted over the whole film, seams included — and the
    beats are listed most-under first until they cover it (at least three, at most six)."""
    rows = sorted(m.get("motion_beats") or [], key=lambda r: (-r["under_s"], r["index"]))
    if not rows or m.get("motion_under_floor") is None:
        return ""
    fps = float(m.get("fps") or 12)
    diffs = max(0, int(m.get("frames", 0)) - 1)
    over = max(0.0, (m["motion_under_floor"] - 0.75) * diffs / fps)
    named, cover = [], 0.0
    for r in rows:
        if r["under_s"] <= 0 or (len(named) >= 3 and cover >= over):
            break
        named.append(r)
        cover += r["under_s"]
        if len(named) == 6:
            break
    if not named:
        return ""
    return (" By beat — seconds under the floor, and of those the FROZEN ones (no pixel changed; a small object "
            "moving is under the floor but not frozen): %s. About %.1fs under the floor would have to move more for "
            "the film to clear it — shorter holds, a register that keeps its object running (the stage registers' "
            "idle clock), or a beat split in two; or, if the stillness IS the design, say why per beat in the waiver."
            % ("; ".join("beat %d (%s) %.1f of %.1fs under, %.1fs frozen" % (
                r["index"], r["shot"] or "?", r["under_s"], r["seconds"], r["frozen_s"]) for r in named), over))


AXES = ("MOTION", "DENSITY", "LIGHT", "LIGHT ARC")


def coverage_line(m):
    """One phrase saying how much of the film these numbers describe. Always printed, never only on failure."""
    dec = m.get("declared_seconds")
    frames = "%d frames at %dfps" % (m.get("frames", 0), m.get("fps", 0))
    if not dec:
        return "%.1fs (%s) — the file declares no duration, so coverage is UNKNOWN" % (m["seconds"], frames)
    return "%.1fs of the %.1fs out.mp4 claims (%.0f%%, %s)" % (
        m["seconds"], dec, 100.0 * min(1.0, m["seconds"] / dec), frames)


def coverage_errors(m, name="out.mp4"):
    """The findings about what was NOT measured. Kept apart from the four axes on purpose: these are not
    judgements about a film, they are reports that part of it never reached the instrument, so
    `meta.energy_waiver` must not be able to absolve them."""
    out = []
    dec = m.get("declared_seconds")
    why = ""
    if m.get("decode_stderr"):
        why = " ffmpeg said: %s" % m["decode_stderr"].splitlines()[-1].strip()
    elif m.get("decode_rc"):
        why = " ffmpeg exited %d with nothing on stderr." % m["decode_rc"]
    if dec is None:
        out.append("COVERAGE: ffprobe could not read a duration from %s, so this run cannot say how much of "
                   "the film it measured — every number above describes the %.1fs it decoded and nothing "
                   "claims that is the whole film.%s" % (name, m["seconds"], why))
        return out
    short = dec - m["seconds"]
    if short > max(COVERAGE_MIN_GAP, COVERAGE_TOLERANCE * dec):
        out.append("COVERAGE: decoded %.1fs of the %.1fs %s claims — %.0f%% of the film never reached the "
                   "instrument, so every number above describes that %.0f%% and not this film. Re-render or "
                   "repair the file, then re-run.%s"
                   % (m["seconds"], dec, name, 100.0 * short / dec, 100.0 * m["seconds"] / dec,
                      why or " ffmpeg reported no error, which makes a damaged container the likely cause."))
    return out


def parse_waiver(raw):
    """({AXIS: reason}, blanket_reason) — the ONE reading of meta.energy_waiver.

    `validate.py` had its own copy that assumed a string, so the day this became per-axis a legitimate
    object-shaped waiver was rejected at the board while the gate accepted it. Two copies of one rule is how
    the caption band became four disagreeing numbers in this repo; there is one copy now and validate imports
    it.
    """
    if isinstance(raw, dict):
        return {str(k).strip().upper(): str(v).strip() for k, v in raw.items() if str(v).strip()}, ""
    if isinstance(raw, str):
        return {}, raw.strip()
    return {}, ""


def check(out_dir):
    mp4 = os.path.join(out_dir, "out.mp4")
    if not os.path.exists(mp4):
        return ["no out.mp4 — this gate reads the delivered film, so it runs after the render"], [], None
    meta, board = {}, None
    sb = os.path.join(out_dir, "storyboard.json")
    if os.path.exists(sb):
        try:
            board = json.load(open(sb, encoding="utf-8"))
            meta = board.get("meta") or {}
        except Exception:                                        # noqa: BLE001 - a broken board is another gate's job
            meta, board = {}, None
    m = measure(mp4, board=board)
    if isinstance(m, dict):
        _d = density(mp4, board=board)
        if _d:
            m["ink_median"], m["beats"] = _d["median"], _d["beats"]
    if isinstance(m, int):
        # Say WHICH failure this is. "needs ffmpeg + numpy" on a film that decoded perfectly well and is
        # simply half a second long sends the reader to install tools they already have.
        return ["%s decoded only %d sampled frame(s) — under %d, a p75 over three differences describes "
                "nothing. Measure a film, not a flash." % (os.path.basename(mp4), m, MIN_FRAMES)], [], None
    if m is None:
        return ["could not decode %s — check ffmpeg/ffprobe are installed and the file is a video" % mp4], [], None

    errs, warns = [], []
    # p75 rather than p90: measured across the corpus, p90's lowest reference sits close enough to a
    # slideshow that a half-floor would let one through. p75 separates them by 3.3x.
    # WHAT MOVES THIS NUMBER, AND WHAT DOES NOT — measured on one 161s film, so nobody repeats the trials:
    #   the camera BED (a slow lateral pan on every unauthored beat)   +0.0005   and it reads as drifting type
    #   SIX motivated camera pushes at the documented 0.045 amplitude   0.0000   exactly no change
    # A 4.5% scale over six seconds is far below this statistic's own threshold frame to frame, so camera
    # amplitude at any tasteful level cannot reach it. Only the CONTENT moving does. When a film is under
    # this floor the honest levers are livelier registers or a stated waiver — not a bigger camera.
    if m["motion_p75"] < MOTION_P75_FLOOR:
        errs.append("MOTION: frame-diff p75 is %.4f, under the %.4f floor (half the quietest reference "
                    "film's %.4f). Three quarters of this film's frames are within %.2f%% of the frame "
                    "before them — that is a slideshow, and the html tier renders slideshows for a "
                    "fraction of the cost. What this tier is FOR is time.%s"
                    % (m["motion_p75"], MOTION_P75_FLOOR, 0.0075, m["motion_p75"] * 100, under_floor_line(m)))
    # DENSITY REPORTS, IT DOES NOT GATE — see `_drawn` above for why the floor went with the old metric.
    # The useful question was never "is the median frame 12%"; it is "WHICH of my beats is least drawn on",
    # and that one is answerable without a reference corpus because a film is compared against itself. A
    # design language is the author's to choose; being the emptiest frame in your own film is a fact about
    # this film. `density_advice.py` still names the denser registers in the same family for the beats at
    # the bottom — the one substitution that does not change the film's visual language.
    if m.get("ink_median") is None:
        warns.append("DENSITY: not measured — the second decode (at %dpx, which is what resolves a drawn "
                     "frame from a blurred blank one) did not return enough frames." % DENSITY_LONG_SIDE)
    else:
        # REPORTED WHETHER OR NOT THERE IS A BOARD. The per-beat half needs storyboard.json to know where
        # the beats are; the film-level number does not, and a measurement that disappears because a file
        # is absent is the "measured 3 of 4 and said nothing" failure this file already refuses elsewhere.
        _b = sorted(m.get("beats") or [], key=lambda r: r["drawn"])
        if _b:
            _lo = _b[: max(1, len(_b) // 6)]
            _where = (" (range %.1f–%.1f%%). Least drawn on: %s. If one of those is a beat you meant to be "
                      "quiet, it is fine; if it is a beat you meant to carry an argument, it is not."
                      % (_b[0]["drawn"] * 100, _b[-1]["drawn"] * 100,
                         ", ".join("beat %d (%s, %.1f%%)" % (r["index"], r["shot"] or "?", r["drawn"] * 100)
                                   for r in _lo)))
        else:
            _where = (". Per-beat detail needs storyboard.json beside out.mp4 — without it this is the "
                      "film-level number only.")
        warns.append("DENSITY (measured, not gated): the film's frames carry %.1f%% structure at the "
                     "median%s `python3 scripts/density_advice.py <out_dir>` names denser registers in "
                     "the same family." % (m["ink_median"] * 100, _where))
    if m["luma_range"] < LUMA_RANGE_FLOOR:
        errs.append("LIGHT: luminance spans %.3f across the film, under the %.3f floor (half of Apple's "
                    "0.270; Figma's is 0.903). Nothing gets brighter or darker — the film has no light, "
                    "only a palette." % (m["luma_range"], LUMA_RANGE_FLOOR))
    if m["luma_steps"] is None:
        warns.append("LIGHT ARC: only %d one-second windows — too short to ask whether the light moves."
                     % m["luma_windows"])
    elif m["luma_steps"] < LUMA_STEP_FLOOR:
        errs.append("LIGHT ARC: only %.1f%% of adjacent seconds change exposure by %.2f, under the %.1f%% "
                    "floor (half of Apple's 3.8%%; Figma reaches 42.5%%). A wide luminance RANGE with no "
                    "steps is one bright passage in an otherwise unlit film — measured, appending four "
                    "seconds of a blank white rectangle to a film takes its range from 0.097 to 0.910 and "
                    "leaves this number at 0.017. Light has to work across the film, not once."
                    % (m["luma_steps"] * 100, LUMA_STEP_DELTA, LUMA_STEP_FLOOR * 100))

    # THE WAIVER IS PER-AXIS. It used to be one string that turned off all four floors at once, and that
    # shipped a real hole within a day of being used: a waiver written about DENSITY — with a reasoned
    # paragraph about a deck's warm-white design language — silently excused a MOTION failure that appeared
    # later, from an unrelated change. One stated reason must not absolve the axes nobody reasoned about.
    #
    # A plain string still waives everything (that is what existing boards mean by it) but now SAYS so, and
    # an object waives exactly the axes it names: {"density": "…"} leaves motion gated.
    per_axis, blanket = parse_waiver(meta.get("energy_waiver"))
    kept, waived = [], []
    for e in errs:
        axis = e.split(":", 1)[0].strip().upper()
        reason = per_axis.get(axis) or (blanket if blanket else "")
        if reason:
            waived.append("waived (%s) — %s" % (axis, e))
        else:
            kept.append(e)
    if waived:
        head = ("ACCEPTED by meta.energy_waiver: %s" % blanket) if blanket else \
            "ACCEPTED by meta.energy_waiver for %s" % ", ".join(sorted(per_axis))
        if blanket and kept:
            head += "  (a plain-string waiver covers EVERY axis — name the axes instead to keep the rest gated)"
        warns = [head] + waived + warns
    if kept:
        kept.append("If this film is deliberately quiet, say so in `meta.energy_waiver` with the reason — a "
                    "STRING waives every axis, an object like {\"density\": \"…\"} waives only what it names. "
                    "A waiver is a decision someone made; silence is one that defaulted.")
    # COVERAGE goes FIRST and never through the waiver loop above. A blanket string waiver turning off "I
    # only read a third of this file" is the exact shape of hole this gate was hardened against.
    return coverage_errors(m, os.path.basename(mp4)) + kept, warns, m


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: film_energy_qa.py <out_dir> | --reference <dir>")
        return 2
    if argv[0] == "--reference":
        if len(argv) < 2:
            print("[film_energy] --reference needs a directory holding %s"
                  % ", ".join(sorted(v + ".*" for v in REFERENCE_FILES.values())))
            return 2
        rows, missing = verify_reference(os.path.abspath(argv[1]))
        for name, rec, got, drift in rows:
            print("[film_energy] %-26s recorded %.4f/%.3f/%.3f/%.3f  measured %.4f/%.3f/%.3f/%.3f  drift %.4f%s"
                  % (name, rec[0], rec[1], rec[2], rec[3], got[0], got[1], got[2], got[3], drift,
                     "" if drift <= REFERENCE_DRIFT else "  ← the floors rest on this"))
        for m in missing:
            print("[film_energy] MISSING %s" % m)
        bad = [r for r in rows if r[3] > REFERENCE_DRIFT]
        print("[film_energy] %s  %d film(s) re-measured, %d drifted, %d missing"
              % ("FAIL" if (bad or missing) else "OK", len(rows), len(bad), len(missing)))
        return 1 if (bad or missing) else 0
    out_dir = os.path.abspath(argv[0])
    errs, warns, m = check(out_dir)
    if m:
        # COVERAGE BEFORE FINDINGS. The old first word was the measured length, which on a half-decoded file
        # read as the film's length; what a reader needs first is how much of the film these numbers are.
        print("[film_energy] measured %s" % coverage_line(m))
        # INK MAY BE ABSENT: density has its own decode, and when it fails the axis WARNs that it did not run —
        # this line used to multiply the None it left and crash the gate after it had said so
        print("              motion p50/p75/p90 %.4f/%.4f/%.4f  ink %s  light %.3f  arc %s (%d window(s))"
              % (m["motion_p50"], m["motion_p75"], m["motion_p90"],
                 "n/a" if m.get("ink_median") is None else "%.1f%%" % (m["ink_median"] * 100), m["luma_range"],
                 "n/a" if m["luma_steps"] is None else "%.1f%%" % (m["luma_steps"] * 100),
                 m["luma_windows"]))
        print("              reference floors: motion p75 >= %.4f · light >= %.3f · arc >= %.1f%% "
              "· density measured, not floored"
              % (MOTION_P75_FLOOR, LUMA_RANGE_FLOOR, LUMA_STEP_FLOOR * 100))
    for w in warns:
        print("[film_energy] WARN  %s" % w)
    for e in errs:
        print("[film_energy] ERROR %s" % e)
    print("[film_energy] %s  %d error(s), %d warning(s)"
          % ("FAIL" if errs else "OK", len(errs), len(warns)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
