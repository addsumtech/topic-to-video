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
    ({"steps": [{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5], "colour": "red"}]}, "has no key `colour`"),
    ({"device": "watch", "steps": [{"screen": {"image": "a.png"}}]}, "`device`"),
    ({"steps": [{"screen": {"image": "a.png", "video": "b.mp4"}}]}, "exactly one of image / video / page"),
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
    into [U+8C48-U+FAFF] and silently swallow the Private Use Area, Yi and more. Pin both sides of the edge."""
    assert ds.type_chunks("豈更") == ["豈更"]      # compatibility ideographs ARE CJK: one word
    assert ds.type_chunks("") == ["", ""]  # the Private Use Area is not: two keys
    assert ds.type_chunks("ꀀꀁ") == ["ꀀ", "ꀁ"]  # nor is Yi
    assert ds.gesture_seconds({"type": "", "into": [0.5, 0.5]}) == ds.SPEC["minSeconds"]["typeLatinKey"]
