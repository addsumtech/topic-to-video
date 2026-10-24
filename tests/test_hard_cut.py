"""The HARD CUT — the seam word this tier did not have.

Every seam was at least a 12-frame cross-dissolve (or the DNA's native whip). Three benchmark films made with the
skill (2026-10-24) named that the strongest "this is slides" signal in them: a 1:1 type film cut on a 105.88 BPM grid
dissolved on every cut, and a 9:16 launch film cut ~14 times a minute, all soft, against the 27.8 measured on Apple's
launch film. `cut` changes the picture on ONE frame — the seam's middle frame, which is where beatgrid.py already
puts a cut's picture moment and the caption HUD already hands over — while the beats keep the seam's overlap, so the
narration breath is untouched.

Measured on a rendered dark -> light pair (DeviceDemo, product DNA, the second beat keyed light; frames 46-62 at half
scale): the cut held 17.4 through frame 53 and read 237.9 from frame 54 — one step, at seam start (48) + 6, inside
both beats' range and never back; mean |frame diff| 0.0 on every other frame. The plain fade over the same pair ramps
18.6 levels a frame from frame 49 to frame 60.
"""
import copy
import json
import os
import re
import shutil
import subprocess

import pytest

import beatgrid
import render_remotion as rr
import seam_plan as sp
import sfx

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
FILM = open(os.path.join(_REM, "src", "Film.tsx"), encoding="utf-8").read()
SEAMS = open(os.path.join(_REM, "src", "seams.tsx"), encoding="utf-8").read()
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")) or not shutil.which("npx"),
                                     reason="needs the remotion toolchain")


def _board(n=8, **meta):
    rel = ["new-topic", "continuation", "new-topic", "continuation", "continuation", "payoff", "continuation", "close"]
    en = ["medium", "medium", "high", "low", "medium", "peak", "high", "low"]
    slides = [{"shot": "MapPlate", "relation": rel[i % 8], "energy": en[i % 8], "duration": 3.0 + 0.1 * i}
              for i in range(n)]
    return {"meta": dict({"renderer": "remotion"}, **meta), "slides": slides}


# ── the word reaches the film ────────────────────────────────────────────────────────────────────────────────────
def test_cut_resolves_on_both_spellings_and_is_not_a_mark():
    assert rr.seam_type("cut") == "cut" and rr.seam_type("hard-cut") == "cut"
    assert rr._transition_in({"transition_in": {"type": "cut"}}) == {"type": "cut"}
    assert rr._transition_in({"transition_style": "hard-cut"}) == {"type": "cut"}
    # the planner's own tag never reaches the film
    assert rr._transition_in({"transition_in": {"type": "cut", "by": "seam_plan"}}) == {"type": "cut"}
    assert rr.is_hard_cut({"transition_in": {"type": "cut"}}) and not rr.is_mark({"transition_in": {"type": "cut"}})
    assert rr.is_mark({"transition_in": {"type": "punch"}}) and not rr.is_hard_cut({"transition_in": {"type": "punch"}})
    # `none` / `dip` / `fade` stay the known non-marks they were
    assert rr.seam_word_known("none") and rr.seam_type("none") is None


def test_the_picker_draws_it_and_the_guard_lets_it_cross():
    sw = FILM.split("switch (t) {")[1].split("\n};")[0]
    assert "case 'cut': return cut();" in sw
    m = re.search(r"CANNOT_FLASH = new Set\(\[([^\]]*)\]\)", FILM)
    assert m and "'cut'" in m.group(1)
    assert "cut" in sp.film_cannot_flash(), "the planner must mirror the guard"
    assert "export const CUT_AT = 0.5;" in SEAMS
    assert sfx.SEAM_PEAK["cut"] == 0.5, "sfx must read the cut's frame from seams.tsx"


def test_the_cut_switches_on_the_frame_beatgrid_calls_the_cut():
    """beatgrid's picture moment is `start + tr // 2`; the cut presentation switches at progress CUT_AT. With Remotion's
    linear timing a seam frame f has progress f / tr, so the switch frame is ceil(CUT_AT * tr) — the same frame."""
    tr = beatgrid.seam_frames()
    switch = min(f for f in range(tr) if f / tr >= 0.5 - 1e-9)
    assert switch == tr // 2
    bnd = beatgrid.boundaries([60, 60, 60], [False, False, False], tr)
    assert [b["frame"] - b["start"] for b in bnd] == [tr // 2, tr // 2]


# ── sound ────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_hard_cut_makes_no_cue_of_its_own():
    scenes = [{"durationInFrames": 90, "transitionIn": None},
              {"durationInFrames": 90, "transitionIn": {"type": "cut"}},
              {"durationInFrames": 90, "transitionIn": {"type": "slide"}}]
    cues = sfx.plan_cues(scenes, 30)
    wh = [c for c in cues if c[1] == "whoosh"]
    assert len(wh) == 1 and abs(wh[0][0] - (6.0 + 5 / 30)) < 1e-6, cues   # the slide's, not the cut's


def test_a_hard_cut_into_the_close_lands_the_impact_on_the_cut():
    scenes = [{"durationInFrames": 90, "transitionIn": None},
              {"durationInFrames": 90, "transitionIn": {"type": "cut"}, "shots": [{"startFrame": 0}]}]
    imp = [c for c in sfx.plan_cues(scenes, 30) if c[1] == "impact"]
    assert imp and abs(imp[0][0] - (3.0 + 6 / 30)) < 1e-6, imp
    scenes[1]["transitionIn"] = None
    imp = [c for c in sfx.plan_cues(scenes, 30) if c[1] == "impact"]
    assert imp and abs(imp[0][0] - 3.0) < 1e-6, "every other close is unchanged"


def test_a_scored_film_s_cuts_switch_on_the_beat():
    """tts.py snaps the pads so each cut's picture frame lands on a beat (or up to one frame before it); with the cut
    presentation the picture really switches on that frame — the close included, which a cut times by its cut."""
    b = _board(8, sound_design=True, bgm="auto")
    sp_marks = sp.plan(b["slides"])
    for i, m in sp_marks.items():
        b["slides"][i]["transition_in"] = {k: x for k, x in m.items() if k != "why"}
    _t, _b, cuts = sp.plan_cuts(b["slides"], b["meta"], sp_marks)
    for i in cuts:
        b["slides"][i]["transition_in"] = {"type": "cut", "by": "seam_plan"}
    b["slides"][-1]["transition_in"] = {"type": "cut"}           # the close too
    doc = beatgrid.plan_film(b["slides"], b["meta"], log=lambda m: None)
    grid = beatgrid.BeatGrid.from_dict(doc["grid"])
    tr = beatgrid.seam_frames()
    bnd = beatgrid.boundaries(doc["durF"], [False] * 8, tr, close_on_arrival=False)
    hard = [k for k in range(1, 8) if rr.is_hard_cut(b["slides"][k])]
    assert len(hard) >= 4, hard
    for bb in bnd:
        if bb["k"] not in hard:
            continue
        switch = bb["start"] + tr // 2                     # the frame CutPresentation switches on
        beat = grid.frame(grid.nearest_beat(switch / 30.0))
        row = [r for r in doc["cuts"] if r["boundary"] == bb["k"]][0]
        if row["snapped"]:
            assert 0 <= beat - switch <= 1, (bb, beat, row)


# ── the planner ──────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_tempo_comes_from_what_the_board_already_says():
    assert sp.film_tempo({"purpose": "launch"})[0] == "kinetic"
    assert sp.film_tempo({"purpose": "promo"})[0] == "kinetic"
    assert sp.film_tempo({"purpose": "teach", "intensity": "bold"})[0] == "kinetic"
    assert sp.film_tempo({"purpose": "teach", "renderer": "remotion", "sound_design": True, "bgm": "auto"})[0] == "scored"
    assert sp.film_tempo({"purpose": "teach"})[0] == "calm"
    assert sp.film_tempo({})[0] == "calm"
    assert sp.film_tempo({"purpose": "launch", "cuts": "calm"}) == ("calm", "meta.cuts")


def test_a_calm_explainer_keeps_its_dissolves_and_a_launch_film_cuts():
    calm = _board(8, purpose="teach")
    assert sp.plan_cuts(calm["slides"], calm["meta"])[2] == {}
    launch = _board(8, purpose="launch")
    marks = sp.plan(launch["slides"])
    tempo, _basis, cuts = sp.plan_cuts(launch["slides"], launch["meta"], marks)
    assert tempo == "kinetic"
    assert set(cuts) == set(range(1, 8)) - set(marks), (cuts, marks)


def test_a_scored_film_cuts_half_its_seams_and_never_into_a_low_beat_or_the_close():
    b = _board(8, purpose="teach", sound_design=True, bgm="auto")
    _t, _b, cuts = sp.plan_cuts(b["slides"], b["meta"], {})
    assert len(cuts) == 4, cuts                                   # ceil(0.5 * 7)
    for i in cuts:
        assert b["slides"][i]["energy"] != "low" and b["slides"][i]["relation"] != "close"


def test_the_planner_skips_what_it_must_not_cut():
    b = _board(8, purpose="launch")
    s = b["slides"]
    s[2]["transition_in"] = {"type": "wipe"}                    # authored
    s[3]["relation"] = "return"                                 # a return is the pan back across the board
    s[4]["match_cut"] = {"from": [0.5, 0.5, 0.2, 0.2], "to": [0.5, 0.5, 0.4, 0.4]}   # into beat 6 (index 5)
    s[6]["camera"] = {"move": "push", "handoff": True}         # the hand-off carries the cut into beat 8 (index 7)
    _t, _b, cuts = sp.plan_cuts(s, b["meta"], {})
    assert cuts and not ({2, 3, 5, 7} & set(cuts)), cuts
    s[1]["stage"] = {"run": "r"}; s[0]["stage"] = {"run": "r"}  # noqa: E702
    assert 1 not in sp.plan_cuts(s, b["meta"], {})[2]


def test_a_re_run_re_plans_its_own_cuts_and_keeps_the_authors(tmp_path):
    b = _board(8, purpose="launch")
    b["slides"][1]["transition_in"] = {"type": "cut"}           # an AUTHOR's cut (no `by`)
    out = str(tmp_path)
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w"))
    assert sp.main([out, "--dry-run"]) == 0
    assert json.load(open(os.path.join(out, "storyboard.json"))) == b, "a dry run writes nothing"
    assert sp.main([out]) == 0
    first = json.load(open(os.path.join(out, "storyboard.json")))
    planned = [i for i, x in enumerate(first["slides"]) if sp.is_planned_cut(x)]
    assert planned and first["slides"][1]["transition_in"] == {"type": "cut"}
    # the film changes tempo: the planner's cuts go, the author's stays
    first["meta"]["cuts"] = "calm"
    json.dump(first, open(os.path.join(out, "storyboard.json"), "w"))
    assert sp.main([out]) == 0
    second = json.load(open(os.path.join(out, "storyboard.json")))
    assert not [i for i, x in enumerate(second["slides"]) if sp.is_planned_cut(x)]
    assert second["slides"][1]["transition_in"] == {"type": "cut"}


def test_the_rate_is_measured_from_the_board():
    b = _board(8, purpose="launch")
    for i in (1, 3, 5):
        b["slides"][i]["transition_in"] = {"type": "cut"}
    b["slides"][7]["transition_in"] = {"type": "punch"}
    rep = sp.cut_report(b["slides"])
    film_s = sum(round(sl["duration"] * 30) for sl in b["slides"]) / 30.0 - 7 * 12 / 30.0
    assert rep["hard"] == 4 and rep["seams"] == 7 and rep["hard_beats"] == [2, 4, 6, 8]
    assert abs(rep["film_s"] - film_s) < 1e-3 and rep["per_min"] == round(240.0 / film_s, 1)
    del b["slides"][0]["duration"]
    assert sp.cut_report(b["slides"])["per_min"] is None, "no durations yet: no rate, not a wrong one"


# ── validate ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_cuts_spend_no_mark_budget_and_an_all_soft_launch_film_is_told():
    b = _board(14, purpose="launch")
    for i in range(1, 14):
        b["slides"][i]["transition_in"] = {"type": "cut"}
    assert all(not rr.is_mark(s) for s in b["slides"])
    assert sp.cut_shortfall(b["slides"], b["meta"]) is None
    soft = _board(14, purpose="launch")
    msg = sp.cut_shortfall(soft["slides"], soft["meta"])
    assert msg and "0 of 13 seams are hard cuts" in msg and "27.8" in msg, msg
    assert sp.cut_shortfall(_board(14, purpose="teach")["slides"], {"purpose": "teach"}) is None


# ── on the frame ─────────────────────────────────────────────────────────────────────────────────────────────────
@needs_toolchain
def test_rendered_the_picture_changes_on_one_frame_and_never_overshoots(tmp_path):
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    sc = [{"shot": "DeviceDemo", "durF": 60, "props": {"device": "phone"}},
          {"shot": "DeviceDemo", "durF": 60, "props": {"device": "phone", "placement": "left"}, "key": "light",
           "transitionIn": {"type": "cut"}}]
    pf = str(tmp_path / "p.json")
    json.dump({"scenes": sc, "dna": "product", "captions": False, "camera": 0, "cameraBed": False}, open(pf, "w"))
    seq = str(tmp_path / "seq")
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "Film", seq, "--sequence", "--image-format=png",
                        "--frames=52-55", "--gl=angle", "--scale=0.25", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    fr = {f: np.asarray(Image.open(os.path.join(seq, "element-%02d.png" % f)).convert("L"), dtype=float)
          for f in range(52, 56)}
    m = {f: a.mean() for f, a in fr.items()}
    assert abs(m[52] - m[53]) < 0.5 and abs(m[54] - m[55]) < 0.5, m          # nothing moves either side of it
    assert m[54] - m[53] > 150, m                                             # one step, dark -> light, on frame 54
    assert float(np.abs(fr[53] - fr[52]).mean()) < 0.5 and float(np.abs(fr[55] - fr[54]).mean()) < 0.5
