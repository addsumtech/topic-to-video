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
