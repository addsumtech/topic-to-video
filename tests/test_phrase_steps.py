"""Phrase steps — the camera leans in on the voice's next clause once a beat has settled (scripts/phrase_steps.py).

WHY. craft_qa measured our films holding a frame still for 5.0 s (median longest still) against 2.5 s for 28 published
launch films; 89 beats across 22 films held past 3 s, spread over 30+ registers, starting about a third of the way into
the beat and lasting about half of it: the register reveals, then waits for the narration to finish. 80 of the 89 had
no camera. A continuous drift was tried before and rejected by a viewer ("the type slides sideways all film"), so the
remedy is an EVENT: a short eased push that lands on a clause the voice starts, then rests.
"""
import pytest

import phrase_steps as ps


def _spans(text, times):
    """capWords-like spans: one per non-space token in `text` (CJK per character), at the given times."""
    out, i = [], 0
    toks = [c for c in text if not c.isspace() and c not in "，。、；：！？,.;:!?"]
    assert len(toks) == len(times)
    for c, t in zip(toks, times):
        a = text.index(c, i)
        out.append({"t": t, "a": a, "b": a + 1})
        i = a + 1
    return out


def test_steps_land_on_clause_starts_after_the_beat_settles():
    text = "甲乙丙丁，戊己庚辛，壬癸子丑，寅卯辰巳。"
    times = [0.3 * k for k in range(16)]                             # 0.3 s a character, 16 spoken characters
    spans = _spans(text, times)
    steps = ps.phrase_steps(spans, text, duration=7.0)
    clause_starts = [times[k] for k in (4, 8, 12)]                  # 戊, 壬, 寅
    voiced = [s for s in steps if s <= times[-1]]                   # after the last word the tail rule applies
    assert voiced and all(any(abs(s - c) < 1e-6 for c in clause_starts) for s in voiced), (steps, clause_starts)
    assert all(s - prev >= ps.MIN_GAP - 1e-6 for prev, s in zip(steps, steps[1:]))
    assert steps[0] >= 7.0 * ps.SETTLE_FRAC - 1e-6


def test_no_two_steps_closer_than_the_minimum_gap_and_none_at_the_cut():
    text = "a, b, c, d, e, f, g, h, i, j, k, l."
    words = [w.strip(",.") for w in text.split()]
    spans, i = [], 0
    for k, w in enumerate(words):
        a = text.index(w, i)
        spans.append({"t": 0.5 * k, "a": a, "b": a + len(w)})
        i = a + len(w)
    steps = ps.phrase_steps(spans, text, duration=7.0)
    gaps = [b - a for a, b in zip(steps, steps[1:])]
    assert all(g >= ps.MIN_GAP - 1e-6 for g in gaps), gaps
    assert all(s <= 7.0 - ps.END_GUARD + 1e-6 for s in steps), steps


def test_a_long_clause_still_gets_a_step_on_a_word():
    text = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen"
    words = text.split()
    spans, i = [], 0
    for k, w in enumerate(words):
        a = text.index(w, i)
        spans.append({"t": 0.45 * k, "a": a, "b": a + len(w)})
        i = a + len(w)
    steps = ps.phrase_steps(spans, text, duration=7.5)
    onsets = [s["t"] for s in spans]
    voiced = [s for s in steps if s <= onsets[-1]]
    assert voiced and all(any(abs(s - o) < 1e-6 for o in onsets) for s in voiced), steps


def test_a_short_beat_gets_none():
    text = "短句，说完。"
    spans = _spans(text, [0.2 * k for k in range(4)])
    assert ps.phrase_steps(spans, text, duration=2.8) == []


def test_no_word_times_still_spaces_steps_evenly_inside_the_hold():
    steps = ps.phrase_steps([], "", duration=9.0)
    assert steps, steps
    gaps = [b - a for a, b in zip(steps, steps[1:])]
    assert all(ps.MIN_GAP - 1e-6 <= g <= ps.MAX_GAP + 1e-6 for g in gaps), gaps
    assert steps[-1] <= 9.0 - ps.END_GUARD + 1e-6


def test_a_cued_reveal_does_not_hold_the_steps_back():
    """Measured on a delivered film (espresso, TechnicalPlate): its three callouts were cued at 4.2, 7.4 and 9.2 s and
    are ~20 px labels — waiting for them put the first step at 12.1 s of a 13.9 s beat, and the frame held 8.9 s. A
    step on the clause that names a part lands WITH that part's reveal, which is the stronger event of the two."""
    text = "甲乙丙丁，戊己庚辛，壬癸子丑，寅卯辰巳。"
    spans = _spans(text, [0.3 * k for k in range(16)])
    steps = ps.phrase_steps(spans, text, duration=7.0)
    assert steps[0] < 7.0 * ps.SETTLE_FRAC + ps.MAX_GAP


@pytest.mark.parametrize("why,kw", [
    ("an authored hold, pan or hand-off", {"authored_camera": True}),
    ("a register that keeps moving", {"register_p75": 0.02}),
    ("opted out", {"enabled": False}),
])
def test_who_gets_none(why, kw):
    text = "甲乙丙丁，戊己庚辛，壬癸子丑，寅卯辰巳。"
    spans = _spans(text, [0.3 * k for k in range(16)])
    assert ps.phrase_steps(spans, text, duration=7.0, **kw) == [], why


def test_the_result_is_deterministic_and_sorted():
    text = "甲乙丙丁，戊己庚辛，壬癸子丑，寅卯辰巳。"
    spans = _spans(text, [0.3 * k for k in range(16)])
    a = ps.phrase_steps(spans, text, duration=7.0)
    assert a == ps.phrase_steps(spans, text, duration=7.0) == sorted(a)


def _board_dir(tmp_path, slides_extra=None, meta_extra=None):
    import json
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg needed for the audio stub")
    (tmp_path / "audio").mkdir()
    cap = "甲乙丙丁，戊己庚辛，壬癸子丑，寅卯辰巳。"
    slides = []
    for i, shot in enumerate(["TermTable", "TermTable", "TermTable", "TermTable"]):
        a = tmp_path / "audio" / ("%02d.wav" % (i + 1))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "12",
                        str(a)], check=True)
        words = [{"w": c, "t": round(0.3 * k, 3)} for k, c in
                 enumerate(c for c in cap if c not in "，。")]
        (tmp_path / "audio" / ("%02d.words.json" % (i + 1))).write_text(json.dumps(words, ensure_ascii=False))
        sl = {"index": i + 1, "shot": shot, "duration": 12.0, "narration": cap, "caption": cap,
              "audio": "audio/%02d.wav" % (i + 1), "shot_props": {"rows": [["a", "1"]]}}
        sl.update((slides_extra or {}).get(i + 1, {}))
        slides.append(sl)
    meta = {"renderer": "remotion", "aspect": "16:9"}
    meta.update(meta_extra or {})
    board = {"meta": meta, "slides": slides}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False))
    return board


def test_the_render_props_carry_phrase_steps_where_they_belong(tmp_path):
    import render_remotion as rr
    board = _board_dir(tmp_path, slides_extra={1: {"camera": {"move": "push"}}, 2: {"camera": {"move": "hold"}},
                                               3: {"camera": {"move": "push"}, "phrase_camera": False},
                                               4: {"camera": {"move": "push", "pan": [0.5, 0]}}})
    props, _ = rr.film_props(str(tmp_path), board)
    sc = props["scenes"]
    assert sc[0].get("phrase"), sc[0].keys()                     # an authored push on a settled beat: steps
    assert "phrase" not in sc[1]                                  # an authored hold is a decision
    assert "phrase" not in sc[2]                                  # switched off on the beat
    assert "phrase" not in sc[3]                                  # a pan is a travel, not a lean


def test_a_beat_nobody_gave_a_camera_gets_no_steps(tmp_path):
    """Built and measured as a scale and as a travel: type trembled on registers that had been still (gps 6 failing
    lines -> 17, up to 0.47 px). A camera the author did not ask for is not added."""
    import render_remotion as rr
    props, _ = rr.film_props(str(tmp_path), _board_dir(tmp_path))
    assert not any("phrase" in s for s in props["scenes"])


def test_an_authored_push_or_pull_is_delivered_in_steps(tmp_path):
    """A push spread evenly over a 15-19 s beat moved under what a viewer sees: espresso's push and pull beats held
    still 9.8 s and 8.2 s. The authored direction and amount stay; the move arrives clause by clause."""
    import render_remotion as rr
    board = _board_dir(tmp_path, slides_extra={1: {"camera": {"move": "push"}}, 2: {"camera": {"move": "pull"}}})
    props, _ = rr.film_props(str(tmp_path), board)
    sc = props["scenes"]
    assert sc[0].get("phrase") and sc[0]["camera"]["move"] == "push"
    assert sc[1].get("phrase") and sc[1]["camera"]["move"] == "pull"


def test_a_moving_register_gets_none(tmp_path, monkeypatch):
    import render_remotion as rr
    board = _board_dir(tmp_path, slides_extra={k: {"camera": {"move": "push"}} for k in (1, 2, 3, 4)})
    monkeypatch.setattr(rr, "_register_p75", lambda shot: 0.02)
    props, _ = rr.film_props(str(tmp_path), board)
    assert not any("phrase" in s for s in props["scenes"])


def test_film_wide_off_and_reduced_motion_get_none(tmp_path):
    import render_remotion as rr
    board = _board_dir(tmp_path, slides_extra={k: {"camera": {"move": "push"}} for k in (1, 2, 3, 4)},
                       meta_extra={"phrase_camera": False})
    props, _ = rr.film_props(str(tmp_path), board)
    assert not any("phrase" in s for s in props["scenes"])
    board["meta"]["phrase_camera"] = True
    props, _ = rr.film_props(str(tmp_path), board, reduced_motion=True)
    assert not any("phrase" in s for s in props["scenes"])
    props, _ = rr.film_props(str(tmp_path), board)
    assert all(s.get("phrase") for s in props["scenes"])


def test_the_runtime_step_curve_rests_between_steps_and_never_passes_its_total():
    import _tsprobe
    if not _tsprobe.available():
        pytest.skip("node/esbuild not available")
    out = _tsprobe.run_ts("import {phraseExtra, PHRASE_STEP_S} from %s;" % _tsprobe.mod("phrase.ts"),
                          "const fps = 30, steps = [2.0, 4.5], total = 0.04;"
                          "out.step = PHRASE_STEP_S;"
                          "out.v = Array.from({length: 240}, (_, f) => phraseExtra(f, fps, steps, total));")
    v, step = out["v"], out["step"]
    assert all(x == 0 for x in v[:60])                                  # nothing before the first step
    assert all(b >= a - 1e-12 for a, b in zip(v, v[1:]))                # it only ever leans in
    rest1 = v[int((2.0 + step) * 30) + 1: int(4.5 * 30)]
    assert rest1 and max(rest1) - min(rest1) < 1e-9 and abs(rest1[0] - 0.02) < 1e-9   # half the total, then rests
    assert abs(v[-1] - 0.04) < 1e-9 and max(v) <= 0.04 + 1e-12
    moving = [b - a for a, b in zip(v[60:60 + int(step * 30) + 1], v[61:61 + int(step * 30) + 1])]
    assert max(moving) > 0                                                # a real move inside the step


def test_a_short_authored_move_is_left_as_its_creep(tmp_path):
    """Measured: authored push/pull beats of 5.5-8.5 s (gps, a watch film) never held past 2.5 s — the creep is visible
    there — while beats of 15.2 and 18.8 s held 8.2 and 9.8 s. Stepped, a short one only got faster: gps's
    ListeningPhone type went from 0.16 to 0.28 px of tremble. Steps start at LONG_BEAT."""
    import render_remotion as rr
    board = _board_dir(tmp_path, slides_extra={1: {"camera": {"move": "push"}, "duration": 8.5},
                                               2: {"camera": {"move": "push"}, "duration": rr.LONG_BEAT}})
    props, _ = rr.film_props(str(tmp_path), board)
    assert "phrase" not in props["scenes"][0]
    assert props["scenes"][1].get("phrase")
