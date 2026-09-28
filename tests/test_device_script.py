"""The step script of a device beat: its shape, how long each step needs, and when each one happens.

A schedule that silently squeezes steps into a beat too short for them draws a tap before the finger could
have arrived and a word the voice has not reached. So every refusal here must say, in SECONDS, what is
missing — an author fixes a script from the message, not from the code.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import device_script as ds          # noqa: E402

FPS = 30


def _steps(*kinds):
    table = {"screen": {"screen": {"image": "ui/a.png"}}, "tap": {"tap": [0.5, 0.4]},
             "type": {"type": "abc", "into": [0.5, 0.1]}, "scroll": {"scroll": 0.5}}
    return [dict(table[k]) for k in kinds]


def test_latin_types_a_key_at_a_time_and_cjk_a_two_glyph_word():
    assert ds.type_chunks("ab c") == ["a", "b", " ", "c"]
    assert ds.type_chunks("上周的客户反馈") == ["上周", "的客", "户反", "馈"]
    assert ds.type_chunks("上周 AI") == ["上周", " ", "A", "I"]
    assert ds.type_chunks(["上周", "的", "客户"]) == ["上周", "的", "客户"]


def test_each_kind_needs_its_own_time():
    assert ds.gesture_seconds({"tap": [0.5, 0.5]}) == pytest.approx(0.6)
    assert ds.gesture_seconds({"type": "abc", "into": [0.5, 0.1]}) == pytest.approx(0.45)
    assert ds.gesture_seconds({"type": ["上周", "反馈"], "into": [0.5, 0.1]}) == pytest.approx(0.70)
    assert ds.needs_lead({"tap": [0.5, 0.5]}) and not ds.needs_lead({"screen": {"image": "x.png"}})


@pytest.mark.parametrize("props,needle", [
    ({"steps": [{"tap": [0.5, 0.5]}]}, "step 1 must be a `screen`"),
    ({"steps": [{"screen": {"image": "a.png"}, "tap": [0.5, 0.5]}]}, "exactly one of"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"tap": [1.2, 0.5]}]}, "in 0..1"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"mark": [0.5, 0.5]}]}, "`mark` is for recordings"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"scroll": 0}]}, "`scroll` is a fraction"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"type": "abc"}]}, "needs `into`"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"tap": {"text": "设置", "nth": 0}}]}, "`nth` counts from 1"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"tap": {"text": "设置", "nth": True}}]}, "`nth` counts from 1"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"tap": [True, 0.5]}]}, "in 0..1"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5], "colour": "red"}]}, "has no key `colour`"),
    ({"device": "watch", "steps": [{"screen": {"image": "a.png"}}]}, "`device`"),
    ({"steps": [{"screen": {"image": "a.png", "video": "b.mp4"}}]}, "exactly one of image / video / object / page"),
])
def test_a_malformed_script_is_refused_with_its_reason(props, needle):
    probs = ds.check_shape(props)
    assert any(needle in p for p in probs), probs


def test_a_well_formed_script_has_no_problems():
    props = {"device": "phone", "look": "real", "steps": [
        {"screen": {"image": "ui/a.png"}}, {"type": "abc", "into": [0.5, 0.1]},
        {"tap": {"text": "反馈汇总"}}, {"screen": {"image": "ui/b.png"}, "via": "push"}, {"scroll": 0.6}]}
    assert ds.check_shape(props) == []


def test_unanchored_steps_are_spread_in_order_inside_the_beat():
    out = ds.schedule(_steps("screen", "tap", "type", "tap"), 180, FPS)
    t0s = [s["t0"] for s in out]
    assert t0s == sorted(t0s)
    assert all(s["t0"] <= s["ta"] <= s["t1"] for s in out)
    assert out[0]["t0"] == pytest.approx(0.06, abs=1e-3)           # the device arrives when the shot does
    assert out[-1]["t1"] <= 1.0


def test_an_anchored_step_acts_exactly_on_its_cue():
    steps = _steps("screen", "tap", "tap")
    steps[2]["at"] = 0.7
    out = ds.schedule(steps, 180, FPS)
    assert out[2]["ta"] == pytest.approx(0.7, abs=2e-3)
    assert out[1]["t1"] <= out[2]["t0"] + 1e-6                        # the earlier step finishes first


def test_a_short_beat_says_how_much_time_is_missing():
    # 12 taps cannot fit a 2-second beat: 12 x (0.35 lead + 0.6) = 11.4 s
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.schedule(_steps("screen", *["tap"] * 12), 60, FPS)
    msg = str(e.value)
    assert "needs" in msg and " s" in msg and "beat" in msg, msg


def test_an_anchor_that_arrives_before_the_steps_before_it_can_finish_is_an_error():
    steps = _steps("screen", "tap", "tap", "tap")
    steps[3]["at"] = 0.12                                               # too early for two taps before it
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.schedule(steps, 180, FPS)
    assert "step 4" in str(e.value) and "cue" in str(e.value)


def test_cjk_detection_covers_only_the_named_blocks():
    """U+F900 is a compatibility ideograph whose NFC form is U+8C48: a range typed as the glyph can be normalized
    into [U+8C48-U+FAFF] and silently swallow the Private Use Area, Yi and more. Both edges are pinned with chr()
    because a glyph written into this file is normalized the same way (it happened once already)."""
    compat = chr(0xF900) + chr(0xF901)
    assert ds.type_chunks(compat) == [compat]                                          # compatibility ideographs ARE CJK
    assert ds.type_chunks(chr(0xE000) + chr(0xE001)) == [chr(0xE000), chr(0xE001)]    # the Private Use Area is not
    assert ds.type_chunks(chr(0xF8FF) + chr(0xF8FF)) == [chr(0xF8FF), chr(0xF8FF)]    # up to its last codepoint
    assert ds.type_chunks(chr(0xA000) + chr(0xA001)) == [chr(0xA000), chr(0xA001)]    # nor is Yi
    assert ds.gesture_seconds({"type": chr(0xE000), "into": [0.5, 0.5]}) == ds.SPEC["minSeconds"]["typeLatinKey"]


def test_a_typed_list_holds_strings():
    """runtime/gesture.tsx stringifies a list's chunks the JavaScript way (true, null) and this module the Python
    way (True, None): a list of anything but strings is refused, so the two can never disagree."""
    probs = ds.check_shape({"steps": [{"screen": {"image": "a.png"}}, {"type": ["上周", 3, None], "into": [0.5, 0.1]}]})
    assert any("chunks as strings" in p for p in probs), probs
    assert not ds.check_shape({"steps": [{"screen": {"image": "a.png"}}, {"type": ["上周", "的"], "into": [0.5, 0.1]}]})


@pytest.mark.parametrize("steps, needle", [
    ([{"screen": {"page": "demo"}}], "register's own preview"),
    ([{"screen": {"image": 5}}], "file path"),
    ([{"screen": {"video": "r.mp4", "to": 3}}, {"tap": [0.5, 0.5]}], "the screen is a recording"),
    ([{"screen": {"video": "r.mp4", "to": 3}}, {"type": "hi", "into": [0.5, 0.2]}], "the screen is a recording"),
    ([{"screen": {"video": "r.mp4", "to": 3}}, {"drag": {"from": [0.2, 0.2], "to": [0.8, 0.8]}}],
     "the screen is a recording"),
    ([{"screen": {"video": "r.mp4", "to": 3}}, {"scroll": 0.5}], "the screen is a recording"),
    ([{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5], "at": 2.5}], "fraction of the beat from 0 to 1"),
])
def test_what_a_film_cannot_show_is_refused(steps, needle):
    """A demo page in a film is the placeholder the layer exists to replace; a finger over a recording performs
    an action the video does not show; a number `at` of 2.5 was meant as seconds and was clamped to the end."""
    probs = ds.check_shape({"steps": steps})
    assert any(needle in p for p in probs), probs


def test_the_opening_screen_takes_no_time():
    """The first screen is on the device when the beat opens; charged a screen change, it pushed every action
    to 1.25 s into its line and refused ordinary narration ("Scroll down the inbox…")."""
    steps = [{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5]}]
    (a0, b0, c0), (t0, ta, t1) = ds.schedule_seconds(steps, [None, 0.8], 0.4, 5.0)
    assert a0 == b0 == c0 and ta == pytest.approx(0.8)       # the 0.4 s entry + the 0.35 s camera lead fit


def test_a_cue_at_the_very_start_is_named_as_early():
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.schedule_seconds([{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5]}], [None, 0.4], 0.4, 5.0)
    assert "said as the beat opens" in str(e.value) and "0.35 s" in str(e.value), e.value.problems

