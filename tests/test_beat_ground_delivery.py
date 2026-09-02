"""The authoring path must be able to NAME the per-beat ground, or the runtime that paints it is unreachable.

runtime/light.tsx can re-ground every register and Film.tsx provides the DNA inside each Sequence — and a
delivered film could still only ever be one near-black, because `scripts/render_remotion.py` assembled each
scene field by field and had never learned `ground`/`key`. A capability the authoring path cannot name is
indistinguishable from a capability that was never built; it is the same shape as an opt-in gate that never
fires, which this repo has shipped before.

These tests are behavioural on both halves: the translation is exercised directly (which is why
`build_scenes` was lifted out of the renderer), and the validator is exercised on the malformed inputs that
would otherwise reach a render minutes later.
"""
import os
import sys

import pytest

import render_remotion as rr
import validate as v

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _beats(*extra):
    out = []
    for i, e in enumerate(extra):
        s = {"index": i, "shot": "LastLeg", "duration": 5.0, "audio": "audio/%02d.mp3" % i,
             "narration": "beat %d" % i}
        s.update(e)
        out.append(s)
    return out


def test_a_declared_ground_reaches_the_film():
    scenes = rr.build_scenes(_beats({"ground": "paper"}, {"key": "light"},
                                    {"ground": {"from": "#05060a", "to": "paper"}}),
                             "/tmp", {"LastLeg"})
    assert scenes[0]["ground"] == "paper"
    assert scenes[1]["key"] == "light"
    assert scenes[2]["ground"] == {"from": "#05060a", "to": "paper"}


def test_a_beat_that_declares_nothing_gains_nothing():
    """The backward-compat contract at its source: no field appears that the author did not write."""
    scenes = rr.build_scenes(_beats({}, {"ground": None, "key": None}), "/tmp", {"LastLeg"})
    for sc in scenes:
        assert "ground" not in sc and "key" not in sc, sc


def test_the_named_grounds_are_read_from_the_runtime_not_restated():
    """A private copy of the names would keep validating against them after light.tsx moved on — the way this
    repo's caption band became four disagreeing definitions."""
    names = v._ground_preset_names()
    assert names, "GROUND_PRESETS could not be parsed from remotion/src/runtime/light.tsx"
    src = open(os.path.join(_ROOT, "remotion", "src", "runtime", "light.tsx"), encoding="utf-8").read()
    for n in names:
        assert ("\n  %s:" % n) in src, "%r is not declared in light.tsx" % n


@pytest.mark.parametrize("beat,fragment", [
    ({"key": "ligth"}, "only exposures"),
    ({"key": "Light"}, "only exposures"),
    ({"ground": "papper"}, "not one of"),
    ({"ground": -1}, "negative ground index"),
    ({"ground": 1.5}, "whole number"),
    ({"ground": True}, "boolean"),
    ({"ground": {"fg": "#fff"}}, "no `bg`"),
    ({"ground": {"from": "#000"}}, "no `to`"),
    ({"ground": {"from": "#000", "to": "paper", "at": [0.8, 0.2]}}, "rising fractions"),
    ({"ground": {"from": "#000", "to": "paper", "at": "0.2"}}, "rising fractions"),
    ({"ground": {"from": "#000", "to": "paper", "at": [0.2]}}, "rising fractions"),
])
def test_a_malformed_ground_is_refused_before_the_render(beat, fragment):
    """A typo in `key` is the expensive kind: any value that is not the film's own key RE-LIGHTS the beat, so
    it renders a film nobody asked for instead of failing. Minutes of render later."""
    errs, warns = [], []
    b = dict(beat); b["index"] = 0
    v._beat_grounds([b], errs, warns)
    assert any(fragment in e for e in errs), (beat, errs)


@pytest.mark.parametrize("beat", [
    {"key": "dark"}, {"key": "light"}, {"ground": 0}, {"ground": 3}, {"ground": "paper"},
    {"ground": "#f4f0e6"}, {"ground": "#fff"}, {"ground": {"bg": "#101418"}},
    {"ground": {"from": 0, "to": "gallery", "at": [0.1, 0.9]}},
])
def test_a_legal_ground_is_left_alone(beat):
    errs, warns = [], []
    b = dict(beat); b["index"] = 0
    v._beat_grounds([b], errs, warns)
    assert not errs, (beat, errs)


def test_one_re_grounded_beat_is_reported_as_not_an_arc():
    """A single bright passage scored 0.910 on the old luminance RANGE while nothing in the film changed.
    An author who re-grounds once should hear it here, not from the delivery gate."""
    errs, warns = [], []
    beats = [{"index": i} for i in range(12)]
    beats[3]["ground"] = "gallery"
    v._beat_grounds(beats, errs, warns)
    assert not errs
    assert any("not a luminance ARC" in w for w in warns), warns
