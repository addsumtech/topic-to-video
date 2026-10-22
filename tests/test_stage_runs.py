"""Continuous stage runs: which boundaries are cuts, where every beat starts, and what a board may not ask of a run."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import stage_runs as sr  # noqa: E402
import remotion_segments as rs  # noqa: E402


def _s(shot, run=None, **kw):
    d = {"shot": shot}
    if run:
        d["stage"] = {"run": run}
    d.update(kw)
    return d


def test_joined_only_inside_one_named_run():
    board = [_s("CinematicTitle"), _s("CardStage", "deck"), _s("CardStage", "deck"), _s("CardStage", "other"),
             _s("CinematicTitle")]
    assert sr.joined_flags(board) == [False, False, True, False, False]
    assert sr.runs(board) == [(1, 2, "deck"), (3, 3, "other")]
    assert sr.run_id({"stage": {"run": "  "}}) is None and sr.run_id({"stage": "deck"}) is None


def test_the_timeline_has_no_seam_inside_a_run_and_matches_the_old_one_without_runs():
    plain = [{"durF": 100}, {"durF": 90}, {"durF": 80}]
    ranges, total = rs.timeline(plain, 12)
    assert ranges == [(0, 87), (88, 165), (166, 245)] and total == 246   # unchanged: a seam at every cut
    run = [{"durF": 100}, {"durF": 90, "stage": {"run": "r"}}, {"durF": 80, "stage": {"run": "r"}}]
    ranges, total = rs.timeline(run, 12)
    # beat 2 mounts 12 frames before beat 1 ends (a cut); beat 3 starts on the frame after beat 2 ends (joined)
    assert ranges == [(0, 87), (88, 177), (178, 257)] and total == 258


def test_a_runs_segments_key_on_the_whole_run(tmp_path):
    sc = [{"shot": "CinematicTitle", "durF": 60}, {"shot": "CardStage", "durF": 60, "stage": {"run": "r"}, "props": {"a": 1}},
          {"shot": "CardStage", "durF": 60, "stage": {"run": "r"}, "props": {"a": 2}}]
    k1 = [s["key"] for s in rs.plan({"scenes": sc}, str(tmp_path), [], tr=12, code="c")[0]]
    sc2 = [dict(x) for x in sc]
    sc2[2] = dict(sc2[2], props={"a": 3})                      # edit the run's LAST beat
    k2 = [s["key"] for s in rs.plan({"scenes": sc2}, str(tmp_path), [], tr=12, code="c")[0]]
    assert k1[0] == k2[0], "the beat before the run is not on it"
    assert k1[1] != k2[1], "beat 2 of the run draws a move toward beat 3's state, so it must re-render"
    assert k1[2] != k2[2]


def test_what_a_run_may_not_ask():
    names = sr.stage_names()
    assert "CardStage" in names
    ok = [_s("CinematicTitle"), _s("CardStage", "deck", ground="paper"), _s("CardStage", "deck")]
    assert sr.check(ok) == []
    cases = {
        "mixes shots": [_s("CardStage", "deck"), _s("CinematicTitle", "deck")],
        "not a stage": [_s("CinematicTitle", "deck"), _s("CinematicTitle", "deck")],
        "appears twice": [_s("CardStage", "deck"), _s("CinematicTitle"), _s("CardStage", "deck")],
        "transition_in": [_s("CardStage", "deck"), _s("CardStage", "deck", transition_in={"type": "wipe"})],
        "camera": [_s("CardStage", "deck", camera={"move": "push"}), _s("CardStage", "deck")],
        "lit from its first beat": [_s("CardStage", "deck"), _s("CardStage", "deck", key="dark")],
    }
    for words, board in cases.items():
        probs = sr.check(board)
        assert any(words in p for p in probs), (words, probs)


def test_seam_plan_and_pace_see_no_cut_inside_a_run():
    import pace
    board = {"meta": {"renderer": "remotion", "language": "en"}, "slides": [
        {"narration": "One.", "duration": 2.0}, {"narration": "Two.", "duration": 2.0, "stage": {"run": "r"}},
        {"narration": "Three.", "duration": 2.0, "stage": {"run": "r"}}]}
    f = pace.film(board)
    one_seam = pace._seam_seconds(board["meta"], "remotion")
    assert abs(f["seams"] - one_seam) < 1e-9, f["seams"]          # one cut (1->2), none inside the run (2->3)


def test_a_runs_last_beat_re_renders_when_the_runs_face_is_remade(tmp_path):
    """The card's face is named by the run's FIRST beat only; the run's third beat draws it but its `prev` (beat 2)
    never names it, so the file's content must reach that beat's key through the run."""
    card = tmp_path / "card.png"
    card.write_bytes(b"one")
    sc = [{"shot": "CinematicTitle", "durF": 60},
          {"shot": "CardStage", "durF": 60, "stage": {"run": "r"}, "props": {"image": "card.png"}},
          {"shot": "CardStage", "durF": 60, "stage": {"run": "r"}, "props": {"title": "b"}},
          {"shot": "CardStage", "durF": 60, "stage": {"run": "r"}, "props": {"title": "c"}}]
    k1 = [s["key"] for s in rs.plan({"scenes": sc}, str(tmp_path), [], tr=12, code="c")[0]]
    card.write_bytes(b"two, a different size")
    k2 = [s["key"] for s in rs.plan({"scenes": sc}, str(tmp_path), [], tr=12, code="c")[0]]
    assert k1[0] == k2[0]
    assert all(x != y for x, y in zip(k1[1:], k2[1:])), "every beat of the run draws the card"
