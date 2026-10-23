"""The film's musical clock (scripts/beatgrid.py): the grid model, the Film.tsx timeline it mirrors, detection on beds
with a KNOWN grid (built here, independently of the score that is also tested against it), the tier-1 fit and the
tier-2 snap — the cut on the beat, at most one frame early, without moving a word."""
import json
import math
import os

import numpy as np
import pytest

import beatgrid as bg
import stage_runs as sr

SR = 44100


# ── a bed with a known grid, built independently of scripts/score.py ─────────────────────────────────────────────
def _bed(bpm, bars=10, pattern="house", shuffle=0.0, seed=0, lead=0.0):
    """Kick / snare / hat at a known tempo (the research prototype's beds). `shuffle` delays the off-beat hat by that
    fraction of half a beat: 1/3 is a triplet swing (the off-beat at 2/3 of the beat)."""
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bt = lead + np.arange(bars * 4) * beat
    x = np.zeros(int((bt[-1] + 3 * beat) * SR))

    def add(t, s, g=1.0):
        i = int(round(t * SR))
        e = min(len(x), i + len(s))
        if 0 <= i < len(x):
            x[i:e] += g * s[: e - i]
    tk = np.arange(int(0.35 * SR)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-tk / 0.03)) / SR) * np.exp(-tk / 0.12)
    th = np.arange(int(0.06 * SR)) / SR
    hat = np.diff(rng.standard_normal(len(th) + 1)) * np.exp(-th / 0.015)
    ts = np.arange(int(0.25 * SR)) / SR
    snare = (rng.standard_normal(len(ts)) * 0.6 + np.sin(2 * np.pi * 190 * ts)) * np.exp(-ts / 0.07)
    for i, t in enumerate(bt):
        pos = i % 4
        if pattern == "house" or pos in (0, 2):
            add(t, kick, 1.0 if pos == 0 else 0.8)
        if pattern == "rock" and pos in (1, 3):
            add(t, snare, 0.5)
        add(t + beat / 2 * (1 + shuffle), hat, 0.35)
    return x / np.abs(x).max(), bt


def _median_err_ms(found, truth_beats, grid):
    e = bg.beat_errors(truth_beats, grid)
    return float(np.median(np.abs(e)))


# ── the model ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_grid_model():
    g = bg.BeatGrid(120, 0.25)
    assert g.period == 0.5 and g.bar_s == 2.0
    assert g.t(0) == 0.25 and g.t(3) == 1.75 and g.t(-1) == -0.25
    assert g.nearest(1.6) == 1.75 and g.nearest(1.6, "half") == 1.5 and g.nearest(1.6, "bar") == 2.25
    assert g.is_downbeat(0) and g.is_downbeat(4) and not g.is_downbeat(2) and g.is_downbeat(-4)
    assert g.beats(0.0, 1.3) == [0, 1, 2] and g.beats(0.3, 1.25) == [1]
    assert g.frame_locked() and g.frame(1) == round(0.75 * 30)
    with pytest.raises(ValueError):
        g.nearest(1.0, "minute")
    back = bg.BeatGrid.from_dict(json.loads(json.dumps(g.to_dict())))
    assert (back.bpm, back.offset_s, back.beats_per_bar, back.source) == (120, 0.25, 4, "synth")
    with pytest.raises(ValueError):
        bg.BeatGrid(0)


def test_a_frame_is_the_last_one_at_or_before_its_beat():
    """"Cut on the beat minus at most one frame" (motion-research §3): for a beat between two frames, the frame
    before it — never the one after (picture early, sound late is the forgiving direction)."""
    g = bg.BeatGrid(108, 0.0)                                   # 0.5556 s a beat: not frame-locked at 30 fps
    assert not g.frame_locked()
    for i in range(40):
        f = g.frame(i)
        assert f / 30.0 <= g.t(i) + 1e-9 and g.t(i) - f / 30.0 < 1 / 30.0, (i, f, g.t(i))
    # an exact frame stays on itself through float error: 100 BPM is 18 frames a beat
    g2 = bg.BeatGrid(100, 0.0)
    assert [g2.frame(i) for i in range(5)] == [0, 18, 36, 54, 72]


def test_frame_locked_tempos_are_the_research_ones():
    t = bg.frame_locked_tempos((90, 125), 30)
    assert [round(x, 2) for x in t] == [120.0, 112.5, 105.88, 100.0, 94.74, 90.0]


def test_boundaries_mirror_the_films_own_timeline():
    """The cut model is Film.tsx's sceneStarts; remotion_segments.timeline is the Python mirror a test already holds to
    it. A drift here would snap every cut to a frame the film does not cut on."""
    import remotion_segments as rs
    scenes = [{"durF": 90}, {"durF": 120, "stage": {"run": "a"}}, {"durF": 80, "stage": {"run": "a"}},
              {"durF": 100}, {"durF": 75}]
    tr = bg.seam_frames()
    spans, total = rs.timeline(scenes, tr)
    b = bg.boundaries([s["durF"] for s in scenes], sr.joined_flags(scenes), tr)
    assert [x["start"] for x in b] == [a for a, _ in spans[1:]]
    assert [x["kind"] for x in b] == ["cut", "joined", "cut", "cut"]
    assert [x["frame"] - x["start"] for x in b] == [tr // 2, 0, tr // 2, tr // 2]
    assert bg.film_frames([s["durF"] for s in scenes], sr.joined_flags(scenes), tr) == total
    # a scored film's close is timed by its arrival — where sfx lands the closing impact
    c = bg.boundaries([s["durF"] for s in scenes], sr.joined_flags(scenes), tr, close_on_arrival=True)
    assert c[-1]["kind"] == "close" and c[-1]["frame"] == c[-1]["start"] and c[0]["frame"] == b[0]["frame"]


# ── detection ─────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("bpm", [76, 92, 108, 124, 140])
@pytest.mark.parametrize("pattern", ["house", "rock"])
def test_detect_finds_the_grid_of_a_known_bed(bpm, pattern):
    x, bt = _bed(bpm, pattern=pattern, lead=0.21)
    g = bg.detect(x, sr=SR, log=lambda m: None)
    assert g is not None, "a plain drum bed must be gridded"
    assert abs(g.bpm / bpm - 1) < 0.01, (g.bpm, bpm)
    err = bg.beat_errors(bt[4:-4], g)
    assert float(np.median(np.abs(err))) < 10.0, err
    # the timestamp correction (window end - hop): without it the beats came out ~30 ms early
    assert abs(float(np.median(err))) < 6.0, np.median(err)
    # beat one: the kick that starts each bar (house accents it; rock has kick on 1 and 3)
    assert (g.nearest_beat(bt[8]) % 4) == 0 or pattern == "rock", "the downbeat is the bar's first kick"


@pytest.mark.parametrize("bpm", [96, 120])
def test_detect_reads_a_swung_bed_at_its_own_tempo(bpm):
    """Triplet swing puts the off-beat hat at 2/3 of the beat — the case the research found real loops miss (as 4/3
    of the tempo). On a bed whose pulse is clear it must still be the beat, not the swing."""
    x, bt = _bed(bpm, bars=12, pattern="rock", shuffle=1 / 3.0, seed=4)
    g = bg.detect(x, sr=SR, log=lambda m: None)
    assert g is not None and abs(g.bpm / bpm - 1) < 0.01, g
    assert _median_err_ms(g.info["beats"], bt[4:-4], g) < 10.0


def test_a_bed_with_no_beat_has_no_grid():
    """Snapping cuts to a tempo the track does not have is worse than not snapping: noise, a drone and speech-like
    bursts are refused, and the refusal SAYS why."""
    t = np.arange(25 * SR) / SR
    rng = np.random.default_rng(1)
    drone = sum(np.sin(2 * np.pi * f * (1 + 0.0025 * np.sin(2 * np.pi * 0.05 * t)) * t) * 0.5 ** i
                for i, f in enumerate((110, 164.81, 220)))
    env = np.zeros(len(t))
    tt = 0.0
    while tt < 24.5:
        d = rng.uniform(0.08, 0.3)
        i, n = int(tt * SR), int(d * SR)
        env[i:i + n] = rng.uniform(0.3, 1.0) * np.hanning(n)
        tt += d + rng.uniform(0.02, 0.25) + (rng.uniform(0.3, 0.8) if rng.random() < 0.1 else 0.0)
    speech = env * np.convolve(rng.standard_normal(len(t)), np.ones(8) / 8, mode="same")
    for name, x in (("drone", drone), ("noise", rng.standard_normal(len(t))), ("speech", speech)):
        said = []
        assert bg.detect(x, sr=SR, log=said.append) is None, name
        assert said and "no beat grid" in said[0], (name, said)
    said = []
    assert bg.detect(np.zeros(3 * SR), sr=SR, log=said.append) is None and "too short" in said[0]


# ── tier 1 ────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_fit_recovers_a_grid_the_cuts_were_made_on():
    truth = bg.BeatGrid(112.5, 0.4)
    beats = [3, 11, 17, 26, 35, 41, 50, 58]
    cuts = [truth.frame(i) / 30.0 for i in beats]
    g = bg.fit_to_cuts(cuts)
    assert g.frame_locked() and abs(g.bpm - 112.5) < 1e-6
    assert g.info["mean_err_ms_unmoved"] == 0.0


def test_fit_prefers_frame_locked_tempos_and_honours_a_pinned_one():
    rng = np.random.default_rng(3)
    cuts = list(np.cumsum(rng.uniform(3.0, 8.0, 10)))
    assert bg.fit_to_cuts(cuts).frame_locked()
    g = bg.fit_to_cuts(cuts, bpm=97.0, source="author")
    assert g.bpm == 97.0 and g.source == "author"


def test_the_climax_lands_on_beat_one():
    rng = np.random.default_rng(5)
    cuts = list(np.cumsum(rng.uniform(3.0, 8.0, 9)))
    for c in (cuts[3], cuts[6]):
        g = bg.fit_to_cuts(cuts, climax=c)
        assert g.is_downbeat(g.nearest_beat(c)), (c, g)


# ── tier 2 ────────────────────────────────────────────────────────────────────────────────────────────────────────
def _board(n, seed, run_every=0):
    rng = np.random.default_rng(seed)
    durs = [round(float(x), 3) for x in rng.uniform(2.5, 8.0, n)]
    items = [{"stage": {"run": "r"}} if run_every and (k % run_every) else {} for k in range(n)]
    return durs, sr.joined_flags(items)


@pytest.mark.parametrize("seed", range(12))
def test_after_snapping_every_snapped_cut_is_on_its_beat_within_one_frame(seed):
    """THE CONTRACT: the cut's picture frame is at, or at most one frame before, its beat — measured on the NEW
    timeline from the new durations (not trusted from the plan). No pad grows by more than 0.3 s, none shrinks past
    its slack, and a cut that could not be reached is reported, not silently left off the beat."""
    durs, joined = _board(14, seed, run_every=3 if seed % 2 else 0)
    slack = [0.0 if k % 4 == 0 else 0.12 for k in range(len(durs))]
    tr = bg.seam_frames()
    durF = [bg.dur_frames(d) for d in durs]
    bnd = bg.boundaries(durF, joined, tr)
    windows = [(lo / 30.0, hi / 30.0) for lo, hi in bg.pad_windows(durF, bnd, slack, tr)]
    grid = bg.fit_to_cuts([b["frame"] / 30.0 for b in bnd], windows=windows)
    new, report = bg.snap_pads(durs, joined, grid, tr=tr, slack=slack)
    after = bg.boundaries([bg.dur_frames(round(d, 3)) for d in new], joined, tr)   # as the board will store them
    for row, b in zip(report, after):
        t = b["frame"] / 30.0
        i = grid.nearest_beat(t)
        if row["snapped"]:
            assert -1.0 / 30 < t - grid.t(i) <= 1e-9, (row, t, grid.t(i))
        else:
            assert "why" in row and "no beat inside" in row["why"]
    for k, (a, b) in enumerate(zip(durs, new)):
        assert b - a <= bg.MAX_ADD_S + 1 / 30.0 + 1e-9, (k, a, b)
        assert a - b <= min(bg.MAX_TRIM_S, slack[k]) + 1 / 30.0 + 1e-9, (k, a, b, slack[k])
        if b != a:
            assert abs(b * 30 - round(b * 30)) < 1e-6, "a snapped beat is a whole number of frames"
    s = bg.summarise(report)
    assert s["mean_abs_err_ms_after"] <= s["mean_abs_err_ms_before"]
    assert s["snapped"] >= 0.6 * s["cuts"], s


def test_snapping_never_shortens_a_pad_with_no_slack():
    durs, joined = _board(10, 7)
    g = bg.fit_to_cuts([b["frame"] / 30.0 for b in bg.boundaries([bg.dur_frames(d) for d in durs], joined, 12)])
    new, _ = bg.snap_pads(durs, joined, g, tr=12, slack=None)
    assert all(b >= a - 1 / 60.0 for a, b in zip(durs, new)), "the scene_pause floor: no slack, no trim"


def test_plan_film_writes_what_render_reads(tmp_path):
    slides = [{"index": k + 1, "duration": d, "relation": "payoff" if k == 4 else None}
              for k, d in enumerate([3.2, 4.41, 2.95, 5.12, 3.77, 4.05, 3.3])]
    meta = {"renderer": "remotion", "sound_design": True, "bgm": "auto", "title": "t"}
    doc = bg.plan_film(slides, meta, slack=[0.1] * 7)
    assert doc["grid"]["source"] == "synth" and doc["climax"]["boundary"] == 4
    g = bg.BeatGrid.from_dict(doc["grid"])
    assert g.is_downbeat(g.nearest_beat(doc["climax"]["t"])) or not doc["cuts"][3]["snapped"]
    bg.write(str(tmp_path), doc)
    scenes = [{"durF": f} for f in doc["durF"]]
    m = bg.music_for_render(str(tmp_path), slides, scenes, meta, log=lambda s: None)
    assert m["stale"] is False and abs(m["grid"].bpm - g.bpm) < 1e-9
    # the board changed after tts: the grid is re-fitted, and it says so
    said = []
    scenes[2]["durF"] += 7
    m2 = bg.music_for_render(str(tmp_path), slides, scenes, meta, log=said.append)
    assert m2["stale"] is True and said and "WARNING" in said[0]
    # a film without music ignores even a leftover beats.json
    assert bg.music_for_render(str(tmp_path), slides, scenes, dict(meta, bgm=None)) is None


def test_snap_off_measures_but_moves_nothing():
    slides = [{"index": k + 1, "duration": d} for k, d in enumerate([3.2, 4.41, 2.95, 5.12])]
    meta = {"renderer": "remotion", "sound_design": True, "bgm": "auto", "music": {"snap": "off"}}
    doc = bg.plan_film(slides, meta)
    assert doc["durations"] == [s["duration"] for s in slides] and all(a == 0 for a in doc["added_s"])


# ── the request and its fields ────────────────────────────────────────────────────────────────────────────────────
def test_music_is_requested_only_where_it_is_mixed():
    base = {"renderer": "remotion", "sound_design": True, "bgm": "auto"}
    assert bg.music_requested(base)
    assert not bg.music_requested(dict(base, renderer="html"))
    assert not bg.music_requested(dict(base, sound_design=False))
    assert not bg.music_requested(dict(base, bgm=None))
    assert not bg.music_requested(dict(base, bgm=""))


def test_music_fields_are_checked():
    ok = {"renderer": "remotion", "sound_design": True, "bgm": "auto",
          "music": {"bpm": 110, "snap": "beat", "key": "F#m", "seed": 3}}
    assert bg.music_problems(ok) == ([], [])
    bad = dict(ok, music={"bpm": 300, "snap": "bar", "key": "H", "seed": "x", "tempo": 1})
    errs, _ = bg.music_problems(bad)
    joined = " | ".join(errs)
    for word in ("bpm", "snap", "key", "seed", "tempo"):
        assert "meta.music." + word in joined, (word, errs)
    _, warns = bg.music_problems(dict(ok, bgm=None))
    assert warns and "does nothing" in warns[0]
    assert bg.music_problems({"music": [1]})[0]
    assert bg.parse_key("Bb major") == (10, "major") and bg.parse_key("c minor") == (0, "minor")


def test_verify_bed_fails_loudly_off_its_grid():
    """The QA on a rendered bed: on its grid it passes; held to a grid 30 ms away it raises, with the number."""
    import score
    g = bg.BeatGrid(112.5, 0.1)
    s = score.render(g, 20.0, seed=11)
    x = s["bed"] + s["pulse"]
    out = bg.verify_bed(x, score.SR, g, log=lambda m: None)
    assert out["median_ms"] < bg.BED_LIMIT_MS
    with pytest.raises(bg.BedOffGrid) as e:
        bg.verify_bed(x, score.SR, bg.BeatGrid(112.5, 0.13), log=lambda m: None)
    assert "ms off its grid" in str(e.value)
