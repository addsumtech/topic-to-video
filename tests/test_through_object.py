"""One continuous world (spec 2026-11-05 C2): a film names its through-object — the thing the camera keeps returning
to (the ANC film's earbud, drawn six different ways in six shots) — and the beats that live on it are JOINED: one
continuous stage (`stage.run`), a `container` seam carrying the object across the cut, or the same shot. validate
names each adjacent pair on the object that redraws it from scratch (advisory)."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import validate as v  # noqa: E402


def _slides(n):
    return [{"index": i + 1, "shot": "S%d" % (i + 1)} for i in range(n)]


def test_beats_on_the_through_object_that_redraw_it_are_named():
    slides = _slides(5)
    w = v._through_object({"through_object": {"name": "earbud", "beats": [2, 3, 4]}}, slides)
    assert len(w) == 1 and "2→3" in w[0] and "3→4" in w[0] and "earbud" in w[0]


def test_a_joined_pair_is_not_named():
    slides = _slides(5)
    slides[2]["transition_in"] = {"type": "container", "carry": "earbud"}             # 2→3 carried
    slides[3]["shot"] = slides[2]["shot"]                                             # 3→4 the same shot
    assert v._through_object({"through_object": {"name": "earbud", "beats": [2, 3, 4]}}, slides) == []
    slides = _slides(5)
    for i in (1, 2, 3):
        slides[i]["stage"] = {"run": "bud"}                                           # one continuous stage
    assert v._through_object({"through_object": {"name": "earbud", "beats": [2, 3, 4]}}, slides) == []


def test_no_through_object_says_nothing_and_a_malformed_one_is_named():
    assert v._through_object({}, _slides(3)) == []
    assert any("through_object" in m for m in v._through_object({"through_object": {"beats": "2,3"}}, _slides(3)))


# ── spec 2026-11-06 C1: the object is HANDED ON, and an unjoined pair is an error ───────────────────────────────────
def _pose(x, y, s=1.0, r=0.0):
    return {"x": x, "y": y, "scale": s, "rot": r}


def _tracked(n, poses):
    slides = _slides(n)
    for i, (pin, pout) in poses.items():
        slides[i - 1]["track"] = {"object": "cap", "in": pin, "out": pout}
    return slides


def test_matching_poses_hand_the_object_on():
    slides = _tracked(3, {1: (_pose(.2, .5), _pose(.4, .5)), 2: (_pose(.4, .5), _pose(.6, .4)),
                          3: (_pose(.6, .4), _pose(.6, .4))})
    assert v._through_object({"through_object": {"name": "cap", "beats": [1, 2, 3]}}, slides) == []


def test_a_pose_that_jumps_at_the_cut_is_named_with_both_values():
    slides = _tracked(2, {1: (_pose(.2, .5), _pose(.4, .5)), 2: (_pose(.7, .5), _pose(.7, .5))})
    w = v._through_object({"through_object": {"name": "cap", "beats": [1, 2]}}, slides)
    assert len(w) == 1 and "1→2" in w[0] and "0.4" in w[0] and "0.7" in w[0]


def test_pairs_follow_the_declared_order_and_a_beat_not_on_the_board_is_named():
    w = v._through_object({"through_object": {"name": "cap", "beats": [4, 2, 9]}}, _slides(5))
    assert any("4→2" in m for m in w) and any("9" in m and "not on the board" in m for m in w)


def test_a_waived_pair_is_not_named_but_a_reasonless_waiver_is():
    meta = {"through_object": {"name": "cap", "beats": [1, 2, 3], "waive": [{"pair": "1→2", "reason": "a new scene"}]}}
    w = v._through_object(meta, _slides(3))
    assert len(w) == 1 and "2→3" in w[0] and "1→2" not in w[0]
    meta["through_object"]["waive"] = [{"pair": "1→2", "reason": " "}]
    assert any("reason" in m for m in v._through_object(meta, _slides(3)))


def test_validate_errors_on_an_unjoined_pair():
    board = {"meta": {"renderer": "remotion", "through_object": {"name": "cap", "beats": [1, 2]}},
             "slides": [{"index": i, "shot": "S%d" % i, "narration": "x", "duration": 4.0, "audio": "a.mp3"}
                        for i in (1, 2)]}
    r = v.evaluate(board, "/tmp")
    assert any("THROUGH-OBJECT" in e for e in r["errors"]) and not any("THROUGH-OBJECT" in w for w in r["warnings"])


def test_the_renderer_hands_the_track_to_the_shot():
    sys.path.insert(0, os.path.join(_ROOT, "scripts"))
    import render_remotion as rr
    s = {"track": {"object": "cap", "in": _pose(.2, .5), "out": _pose(.4, .5)}}
    assert rr.with_track({"a": 1}, s) == {"a": 1, "track": s["track"]}
    assert rr.with_track({"a": 1}, {}) == {"a": 1}
