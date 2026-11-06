"""Sketch before build (spec 2026-11-06 B). On the ANC film every composition problem — titles at the top, labels in
the caption band, no light arc — was found by gates AFTER the shots were built. Kurzgesagt settles each scene's
visual metaphor in a sketching phase before illustration; here each remotion beat carries `slide.sketch` (metaphor,
the one hero, a rough layout) that the user approves as a greybox sheet before a line of TSX is written."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import validate as v  # noqa: E402


def _sk(**kw):
    s = {"metaphor": "the switch is a tiny spring-loaded gate", "hero": "switch",
         "layout": [{"name": "switch", "rect": [0.3, 0.2, 0.4, 0.5], "hero": True},
                    {"name": "label", "rect": [0.72, 0.3, 0.2, 0.08]}],
         "camera": "macro", "environment": "a desk under a lamp"}
    s.update(kw)
    return s


def _slides(n, sketch=True):
    return [dict({"index": i + 1, "shot": "S%d" % (i + 1)}, **({"sketch": _sk()} if sketch else {}))
            for i in range(n)]


def _run(meta, slides, tier="remotion"):
    return v._sketch_problems(dict({"renderer": "remotion"}, **meta), slides, tier)


def test_sketched_board_is_clean():
    assert _run({"hero_moments": [2]}, _slides(4)) == ([], [])


def test_built_remotion_beat_without_sketch_is_an_error():
    slides = _slides(3)
    del slides[1]["sketch"]
    errs, _w = _run({}, slides)
    assert len(errs) == 1 and "beat 2" in errs[0] and "sketch" in errs[0]


def test_a_board_with_no_sketch_at_all_gets_one_error_not_one_per_beat():
    errs, _w = _run({}, _slides(12, sketch=False))
    assert len(errs) == 1 and "12" in errs[0]


def test_keep_design_beat_is_exempt():
    slides = _slides(3)
    del slides[0]["sketch"]
    assert _run({}, slides, )[0]
    errs, warns = v._sketch_problems({"renderer": "remotion"}, slides, "remotion", kept={1})
    assert errs == [] and any("beat(s) 1" in w for w in warns)        # exempt, and said so


def test_layout_needs_exactly_one_hero_and_2_to_6_rects():
    two_heroes = _slides(1)
    two_heroes[0]["sketch"]["layout"][1]["hero"] = True
    assert any("one hero" in e for e in _run({}, two_heroes)[0])
    one_rect = _slides(1)
    one_rect[0]["sketch"]["layout"] = one_rect[0]["sketch"]["layout"][:1]
    assert any("2-6" in e for e in _run({}, one_rect)[0])
    seven = _slides(1)
    seven[0]["sketch"]["layout"] = [{"name": "r%d" % i, "rect": [0, 0, 0.1, 0.1], "hero": i == 0} for i in range(7)]
    assert any("2-6" in e for e in _run({}, seven)[0])


def test_rect_outside_0_1_is_named_with_the_beat():
    s = _slides(2)
    s[1]["sketch"]["layout"][1]["rect"] = [0.9, 0.3, 0.3, 0.1]               # runs off the right edge
    errs = _run({}, s)[0]
    assert any("beat 2" in e and "label" in e for e in errs)


def test_empty_metaphor_or_hero_is_an_error():
    s = _slides(1)
    s[0]["sketch"]["metaphor"] = " "
    assert any("metaphor" in e for e in _run({}, s)[0])


def test_eight_beat_film_without_hero_moments_warns_and_a_seven_beat_one_does_not():
    assert any("hero_moments" in w for w in _run({}, _slides(8))[1])
    assert not any("hero_moments" in w for w in _run({}, _slides(7))[1])


def test_hero_moments_must_name_1_to_3_beats_on_the_board():
    assert any("hero_moments" in e for e in _run({"hero_moments": [1, 2, 3, 4]}, _slides(8))[0])
    assert any("hero_moments" in e and "9" in e for e in _run({"hero_moments": [9]}, _slides(8))[0])


def test_html_tier_and_slide_type_boards_get_no_sketch_rule():
    assert _run({}, _slides(9, sketch=False), tier="html") == ([], [])
    assert _run({}, _slides(9, sketch=False), tier=None) == ([], [])
    slides = [{"index": 1, "type": "slide"}, {"index": 2, "shot": "S2", "sketch": _sk()}]
    assert _run({}, slides) == ([], [])


# ── review C1: a design-first film made before the sketch rule ─────────────────────────────────────────────────────
import json  # noqa: E402


def _old_film(tmp_path, n=3):
    slides = [{"index": i + 1, "shot": "S%d" % (i + 1), "shot_fit": {"ideal": "the frame %d" % i}} for i in range(n)]
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"renderer": "remotion"}, "slides": slides}))
    return str(tmp_path), slides


def test_a_design_first_film_without_sketches_can_be_kept_by_the_user(tmp_path):
    d, slides = _old_film(tmp_path)
    assert v._sketch_problems({"renderer": "remotion"}, slides, "remotion")[0]       # the rule still fires
    ok, msg = v.keep_sketches(d, "保持原样，只改字幕")
    assert ok, msg
    b = json.loads((tmp_path / "storyboard.json").read_text())
    assert v.sketch_keep(b["meta"], b["slides"]) == {1, 2, 3}
    errs, warns = v._sketch_problems(b["meta"], b["slides"], "remotion", kept=v.sketch_keep(b["meta"], b["slides"]))
    assert errs == [] and any("kept" in w for w in warns)


def test_a_kept_beat_whose_shot_changed_must_be_sketched_and_a_non_answer_is_refused(tmp_path):
    d, _ = _old_film(tmp_path)
    assert not v.keep_sketches(d, "auto")[0]
    assert v.keep_sketches(d, "保持原样")[0]
    b = json.loads((tmp_path / "storyboard.json").read_text())
    b["slides"][1]["shot"] = "NewShot"
    assert v.sketch_keep(b["meta"], b["slides"]) == {1, 3}


def test_validate_on_a_kept_old_film_has_no_sketch_error(tmp_path):
    d, _ = _old_film(tmp_path)
    v.keep_sketches(d, "保持原样")
    b = json.loads((tmp_path / "storyboard.json").read_text())
    for s in b["slides"]:
        s.update({"narration": "x", "duration": 4.0, "audio": "a.mp3"})
    assert not [e for e in v.evaluate(b, d)["errors"] if e.startswith("sketch:")]
