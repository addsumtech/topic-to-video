"""Type that SWAYS — rocks back and forth and never settles (scripts/text_safe_qa.py judge_sway, in the --glide gate).

Measured 2026-11-01 on a Grok Bot film: an idle "float" (an 18 px / 12 px sine on the draft card, ~3 s period) and a
"breathing" held camera read to the user as the frame SHAKING (左右上下晃动). shake_qa judges the whole frame's
high-frequency vibration over half-second windows and passed it; nothing judged a slow back-and-forth. The census
already holds every line's box on every frame: a line whose centre keeps swinging, swing after swing, is swaying. A
spring that settles, an entrance, a camera push and a pop scaled about its centre are not.
"""
import math

import text_safe_qa as tq


def _frames(track, key="/html0/body1/div0/span0", w=200, h=40, n=None):
    out = {}
    for f, (x, y) in enumerate(track):
        out[f] = {"lines": [{"k": key, "x": x - w / 2, "y": y - h / 2, "w": w, "h": h, "o": 1, "t": "Send", "fl": ""}]}
    return out


def test_an_idle_float_sways_and_a_settling_spring_does_not():
    float_ = [(960 + 12 * math.sin(2 * math.pi * f / 108), 540 + 18 * math.sin(2 * math.pi * f / 90)) for f in range(150)]
    found = tq.judge_sway(_frames(float_), short=1080)
    assert found and found[0]["swing"] >= 30, found
    spring = [(960, 540 + 40 * math.exp(-f / 6.0) * math.cos(f / 2.0)) for f in range(90)] + [(960, 540)] * 60
    assert tq.judge_sway(_frames(spring), short=1080) == []


def test_entrances_pushes_still_type_and_centred_pops_do_not_sway():
    entrance = [(960, 640 - 100 * min(1, f / 20.0)) for f in range(120)]
    push = [(960 + 0.4 * f, 540 + 0.25 * f) for f in range(150)]
    still = [(960, 540)] * 150
    for track in (entrance, push, still):
        assert tq.judge_sway(_frames(track), short=1080) == [], track[:3]
    # a pop scaled about its centre: the box grows and shrinks, its centre does not move
    pop = {}
    for f in range(120):
        s = 1 + 0.2 * math.sin(2 * math.pi * f / 40)
        pop[f] = {"lines": [{"k": "a", "x": 960 - 100 * s, "y": 540 - 20 * s, "w": 200 * s, "h": 40 * s, "o": 1,
                             "t": "Ultra", "fl": ""}]}
    assert tq.judge_sway(pop, short=1080) == []


def test_a_small_tremor_is_jitter_qa_s_and_a_faint_line_is_not_read():
    tiny = [(960, 540 + 1.5 * math.sin(2 * math.pi * f / 30)) for f in range(150)]
    assert tq.judge_sway(_frames(tiny), short=1080) == []
    faint = _frames([(960, 540 + 18 * math.sin(2 * math.pi * f / 90)) for f in range(150)])
    for v in faint.values():
        v["lines"][0]["o"] = 0.2
    assert tq.judge_sway(faint, short=1080) == []


def test_a_landed_line_that_drifts_away_and_turns_back_sways_even_inside_one_cycle():
    """The Grok Bot 'Send' (census of the old float): landed at frame 67, drifted 11 px right over a second and came
    back 13 px — less than one cycle of a 3 s float before the beat cut away. Two slow swings are enough; a spring's
    swings last a few frames, and a deliberate move across the frame is larger than any idle float."""
    xs = [1393.4, 1393.9, 1394.8, 1396.0, 1397.3, 1398.8, 1400.2, 1401.5, 1402.6, 1403.4, 1403.7, 1403.5, 1402.7,
          1401.4, 1399.5, 1397.2, 1395.2, 1393.3, 1391.3]
    track = []
    for i in range(len(xs) - 1):
        for s in range(3):
            track.append((xs[i] + (xs[i + 1] - xs[i]) * s / 3.0, 680))
    found = tq.judge_sway(_frames(track), short=1080)
    assert found and 10 <= found[0]["swing"] <= 14, found
    across = [(960 + 500 * math.sin(math.pi * min(1, f / 40.0)), 540) for f in range(80)]     # in and back out
    assert tq.judge_sway(_frames(across), short=1080) == []


def test_a_gesture_that_comes_to_rest_is_not_a_sway():
    """Corpus check (2026-11-01): a card that flies over on an arc, a card that tips forward and settles back, a word
    pasted down with a drop — each swings twice slowly and then RESTS. An idle float never rests until the cut."""
    tip = [(960, 540 + 27 * math.sin(math.pi * min(1, f / 40.0)) * (1 if f < 40 else 0)
            - (12 * math.sin(math.pi * min(1, (f - 40) / 30.0)) if 40 <= f < 70 else 0)) for f in range(130)]
    assert tq.judge_sway(_frames(tip), short=1080) == []
    arc = [(400 + 10 * f, 600 - 40 * math.sin(math.pi * min(1, f / 60.0))) for f in range(60)] + [(1000, 600)] * 40
    assert tq.judge_sway(_frames(arc), short=1080) == []


def test_the_html_census_shape_is_read_too():
    """keyframe_qa's census gives a line's text box as tx/ty/tw/th, not x/w/h: read either, or the HTML tier's sway
    check would skip every line and pass every page."""
    fr = {}
    for f in range(150):
        y = 540 + 18 * math.sin(2 * math.pi * f / 90)
        fr[f] = {"lines": [{"k": "p", "y": y - 20, "tx": 860, "ty": y - 20, "tw": 200, "th": 40, "o": 1, "t": "Send"}]}
    assert tq.judge_sway(fr, short=1080), "an HTML-shaped float was not read"
