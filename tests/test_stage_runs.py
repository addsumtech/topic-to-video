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


def test_a_stage_face_carries_the_shape_a_browser_draws(tmp_path):
    """`imageAspect` is the image as <img> draws it: EXIF orientation 6 turns a stored-landscape photo portrait. The
    board's own props are never written, and a missing face is an error rather than a blank card."""
    import pytest
    from PIL import Image
    Image.new("RGB", (400, 300)).save(tmp_path / "wide.png")
    im = Image.new("RGB", (400, 300))
    exif = im.getexif()
    exif[0x0112] = 6
    im.save(tmp_path / "turned.jpg", exif=exif)
    board_props = {"image": "wide.png", "title": "t"}
    out = sr.stamp_faces(board_props, str(tmp_path))
    assert out["imageAspect"] == round(400 / 300, 4) and "imageAspect" not in board_props
    assert sr.stamp_faces({"image": "turned.jpg"}, str(tmp_path))["imageAspect"] == 0.75
    assert sr.stamp_faces({"title": "no face"}, str(tmp_path)) == {"title": "no face"}
    with pytest.raises(FileNotFoundError):
        sr.stamp_faces({"image": "missing.png"}, str(tmp_path))


def test_steps_resolve_to_seconds_in_order_and_refuse_what_cannot_play():
    """`at` 0..1 is a share of the beat; a cue goes through the renderer's ordered search (here a stand-in that answers
    seconds); steps out of time order, or that name nothing to change, are errors."""
    import pytest
    said = {"文本框": 0.4, "点开": 2.4}

    def resolve(pr):
        return {"steps": [dict(st, at=said[st["at"]["cue"]]) if isinstance(st.get("at"), dict) else st
                          for st in pr["steps"]]}

    props = {"title": "t", "steps": [{"at": {"cue": "文本框"}, "lift": [{"rect": [0, 0, 1, 1]}]},
                                     {"at": 0.5, "marks": []}, {"at": {"cue": "点开"}, "cursor": {"u": 0.2, "v": 0.4}}]}
    out = sr.resolve_steps(props, resolve, 4.0, 3)
    assert [st["t"] for st in out["steps"]] == [0.4, 2.0, 2.4] and all("at" not in st for st in out["steps"])
    assert props["steps"][1]["at"] == 0.5, "the board's own steps are never written"
    with pytest.raises(SystemExit, match="out of order"):
        sr.resolve_steps({"steps": [{"at": 0.9, "marks": []}, {"at": {"cue": "文本框"}, "marks": []}]}, resolve, 4.0, 3)
    with pytest.raises(SystemExit, match="changes nothing"):
        sr.resolve_steps({"steps": [{"at": 0.2}]}, resolve, 4.0, 3)
    narr = "每个文本框，点开就能改"
    assert sr.step_problems([{"at": {"cue": "点开"}, "cursor": {"u": 0.1, "v": 0.9, "click": True}}], narr) == []
    probs = sr.step_problems([{"at": {"cue": "拖动"}, "cursor": {"u": 1.4, "v": 0.2}}, {"at": 3, "count": {"value": 1}}], narr)
    assert any("does not say" in p for p in probs) and any("0..1" in p for p in probs) and any("got 3" in p for p in probs)
    board = [_s("CardStage", "deck", narration=narr, shot_props={"steps": [{"cursor": {"u": 0.1, "v": 0.1}}]}),
             _s("CardStage", "deck")]
    assert any("needs `at`" in p for p in sr.check(board))


def test_a_stage_click_is_a_sound_on_its_word_and_survives_the_density_cap():
    import sfx
    scenes = [{"shot": "CinematicTitle", "props": {}},
              {"shot": "CardStage", "stage": {"run": "r"}, "props": {"steps": [
                  {"t": 1.25, "cursor": {"u": 0.2, "v": 0.3, "click": True}}, {"t": 2.0, "cursor": {"u": 0.5, "v": 0.5}}]}}]
    events = sr.sound_events(scenes)
    assert events == [[], [{"t": 1.25, "name": "click"}]]
    fps = 30
    sfx_scenes = [{"durationInFrames": 90, "transitionIn": None, "events": events[0]},
                  {"durationInFrames": 120, "transitionIn": {"type": "wipe"}, "events": events[1]}]
    assert sfx.plan_cues(sfx_scenes, fps, events_only=True) == [(3.0 + 1.25, "click", sfx.EVENT_GAIN["click"])]
    full = sfx.plan_cues([dict(sc, shots=[{"startFrame": 0}]) if i == 1 else sc for i, sc in enumerate(sfx_scenes)], fps)
    assert any(name == "click" and abs(t - 4.25) < 1e-9 for t, name, _g in full), full


def test_the_gates_take_the_frames_the_stage_holds_and_the_middles_of_its_moves():
    """stage_frames mirrors runtime/stageRun.tsx buildKeys frame for frame. Worked by hand: a cut into the run at
    frame 88; its first beat arrives at once; step 1 (t=0.4 s) arrives on frame 12 of the run and may only start
    when the beat did (a 12-frame move, not 14); step 2 (t=2 s, move 1 s) runs 30-60; the joined beat morphs 120-144;
    the film's closing veil keeps the last held frame 16 frames off the end."""
    import stage_frames as sf
    scenes = [{"durF": 100},
              {"durF": 120, "stage": {"run": "r"}, "props": {"steps": [{"t": 0.4}, {"t": 2.0, "move": 1.0}]}},
              {"durF": 90, "stage": {"run": "r"}, "props": {}}]
    keys = sf.keyframes(scenes, 1, 2, 30)
    assert [(k["from"], k["to"]) for k in keys] == [(0, 0), (0, 12), (30, 60), (120, 144)]
    got = sf.sample_frames(scenes, 12, 30)
    assert got == {1: {"held": [88, 117, 207], "moving": [94, 133]}, 2: {"held": [281], "moving": [220]}}
    import pytest
    with pytest.raises(ValueError):
        sf.keyframes([{"durF": 90, "stage": {"run": "r"}, "props": {"steps": [{"cursor": {}}]}}], 0, 0, 30)


def test_the_board_gates_see_a_stage_for_what_it_is():
    import dna_audit
    import energy_skeleton
    import beat_key
    import validate
    assert "CardStage" in dna_audit.dna_aware_shots(), "it reads useDNA on its first line"
    assert "film_energy_qa" in energy_skeleton.unmeasured_reason("CardStage", {})
    assert beat_key.shot_file(None, "CardStage").endswith(os.path.join("stage", "CardStage.tsx"))
    slides = [_s("CinematicTitle", index=1),
              _s("CardStage", "a", index=2, shot_props={"image": "card.png"}), _s("CardStage", "a", index=3),
              _s("CardStage", "b", index=4, shot_props={"page": {"title": "t"}, "steps": [{"at": 0.5, "marks": []}]}),
              _s("CardStage", "c", index=5, shot_props={"page": {"title": "t"}, "title": "only a title"})]
    routes = {n: r for n, r, _why in validate.design_routes({}, slides, None)}
    assert routes[2] == routes[3] == "exempt" and routes[4] == "adapted" and routes[5] == "as-is"
