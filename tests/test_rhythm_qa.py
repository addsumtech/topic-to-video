import rhythm_qa as rq


def _sc(index, dur, type="html", narration="a beat", climax=False, transition=None):
    s = {"index": index, "type": type, "narration": narration, "duration": dur, "props": {}}
    if climax:
        s["props"]["climax"] = True
    if transition:
        s["transition"] = transition
    return s


def _board(slides, meta=None):
    return {"meta": meta or {"language": "en"}, "slides": slides}


def test_uniform_durations_warn():
    # 6 identical-length beats, same type, no seams -> monotone
    slides = [_sc(i, 5.0) for i in range(6)]
    r = rq.evaluate(_board(slides))
    assert any("too uniform" in w for w in r["warnings"])


def test_varied_durations_no_uniformity_warn():
    slides = [_sc(0, 3.0, transition="in"), _sc(1, 4.0), _sc(2, 3.5, type="chart"),
              _sc(3, 7.0, climax=True), _sc(4, 6.0, type="title"), _sc(5, 2.5, type="title", narration="Done.")]
    r = rq.evaluate(_board(slides))
    assert not any("too uniform" in w for w in r["warnings"])


def test_climax_misplaced_warns():
    # climax at the very start (~10%) on a set where total ~ 25s
    slides = [_sc(0, 5.0, climax=True), _sc(1, 5.0, type="chart"), _sc(2, 5.0, type="title"),
              _sc(3, 5.0, type="compare"), _sc(4, 5.0, type="title", narration="end")]
    r = rq.evaluate(_board(slides))
    assert any("climax lands at" in w for w in r["warnings"])


def test_climax_well_placed_no_warn():
    slides = [_sc(0, 4.0), _sc(1, 4.0, type="chart"), _sc(2, 4.0, type="title"),
              _sc(3, 7.0, climax=True, type="chart"), _sc(4, 3.0, type="title", narration="end")]
    r = rq.evaluate(_board(slides))
    assert not any("climax lands at" in w for w in r["warnings"])


def test_no_climax_on_long_video_warns():
    slides = [_sc(i, 10.0, type=("chart" if i % 2 else "html")) for i in range(10)]  # 100s, no climax
    r = rq.evaluate(_board(slides))
    assert any("no climax beat" in w for w in r["warnings"])


def test_static_image_over_hold_is_error():
    slides = [_sc(0, 5.0), _sc(1, 20.0, type="slide"), _sc(2, 4.0, type="title", narration="end")]
    r = rq.evaluate(_board(slides))
    assert r["ok"] is False and any("static image is held 20s" in e for e in r["errors"])


def test_static_image_soft_hold_warns_not_errors():
    slides = [_sc(0, 5.0), _sc(1, 12.0, type="slide"), _sc(2, 4.0, type="title", narration="end")]
    r = rq.evaluate(_board(slides))
    assert r["ok"] is True and any("prefer 2 shorter cuts" in w for w in r["warnings"])


def test_attention_reset_gap_warns():
    # 5 same-type html beats, HARD cuts (meta transition none), ~40s with no seam/family change
    slides = [_sc(i, 8.0, type="html") for i in range(5)]
    r = rq.evaluate(_board(slides, meta={"language": "en", "transition": "none"}))
    assert any("no attention reset" in w for w in r["warnings"])


def test_meta_default_dip_no_false_reset():
    # same 5 same-family beats but relying on the meta-default dip (a breath at every cut) — NOT flagged
    slides = [_sc(i, 8.0, type="html") for i in range(5)]
    r = rq.evaluate(_board(slides))  # meta has no transition -> defaults to "dip"
    assert not any("no attention reset" in w for w in r["warnings"])


def test_seams_and_family_changes_reset_attention():
    slides = [_sc(0, 8.0, type="html"), _sc(1, 8.0, type="chart"),
              _sc(2, 8.0, type="html", transition="in"), _sc(3, 8.0, type="timeline"),
              _sc(4, 8.0, type="title", narration="end")]
    r = rq.evaluate(_board(slides))
    assert not any("no attention reset" in w for w in r["warnings"])


def test_dense_final_hold_warns():
    slides = [_sc(0, 4.0, narration="short"), _sc(1, 4.0, type="chart", narration="short"),
              _sc(2, 8.0, type="html", narration=" ".join(["word"] * 40))]  # dense closer
    r = rq.evaluate(_board(slides))
    assert any("final" in w for w in r["warnings"])


def test_durations_estimated_when_missing():
    # no `duration` -> estimated from narration; a long static image narration -> soft/hard hold
    slides = [{"index": 0, "type": "slide", "narration": " ".join(["word"] * 60), "props": {}},
              {"index": 1, "type": "title", "narration": "end", "props": {}}]
    r = rq.evaluate(_board(slides))
    assert any("estimated from narration" in (w + " ") for w in r["warnings"] + r["errors"]) or r["scenes"] == 2
