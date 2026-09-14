"""The FOCUS RELAY seam — the only cut in this vocabulary that happens in DEPTH.

WHERE IT CAME FROM, and why it was worth borrowing rather than inventing. Measured against the
video-shotcraft library (218 shots, the same stack: Remotion 4 + React, CSS 3D on both sides), that library
reaches for `blur()` in 35% of its shots against this tier's 11%, and three of its six documented hand-off
recipes are built on DEPTH — through-dark flight, focus relay, portal wipe. This tier had none: every seam
it shipped (fade, dissolve, clock, wipe, carry) moves pixels in the PLANE or fades them, and a film whose
cuts are all planar reads as pages replacing pages.

The parameters are the borrowed part, from that library's case law: "前景 blur 0→8px 同时后景 8px→0，交叉
窗口 10–16f；两景错开 2–4f 起跑" — with the recorded failure "同帧起跑读作整屏糊掉". The STAGGER is the whole
trick, so it is what these tests pin.

TWO PATHS HAD TO BE OPENED AND BOTH WERE INITIALLY SHUT, which is why they are tested rather than assumed.
The seam rendered byte-identically to a fade until the luminance guard was told that a rack focus cannot
flash (it redistributes light rather than adding any); and `render_remotion._KINETIC_TYPES` did not list it,
so a storyboard asking for it was silently downgraded — the same "built but unreachable" failure that
`_transition_in`'s own docstring was written about.
"""
import os
import re

import pytest

import render_remotion as rr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(rr.__file__)))
FILM = open(os.path.join(ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()


def test_the_board_path_accepts_it():
    """Without this the seam exists and no storyboard can ask for it."""
    assert "focus" in rr._KINETIC_TYPES
    assert rr._transition_in({"transition_in": {"type": "focus"}}) == {"type": "focus"}


def test_the_luminance_guard_knows_it_cannot_flash():
    """The guard rewrites a marked seam to a plain fade across a dark/light boundary. Focus was in that net
    for its first three renders — which measured identical luminance, sharpness and motion to a fade, the
    signature of a change having no effect — because the property was asserted in the presentation's header
    and never told to the guard."""
    assert "CANNOT_FLASH" in FILM
    m = re.search(r"CANNOT_FLASH = new Set\(\[([^\]]*)\]\)", FILM)
    assert m and "'focus'" in m.group(1) and "'carry'" in m.group(1), m and m.group(1)


def test_the_two_beats_are_STAGGERED_not_simultaneous():
    """The recorded failure mode: start both at the same frame and the audience sees one blurred screen
    instead of a hand-off. The offset is what makes it read as a relay."""
    m = re.search(r"RELAY_OFFSET = ([\d.]+)", FILM)
    assert m, "the stagger constant is gone"
    off = float(m.group(1))
    assert 0.08 < off < 0.4, "the stagger is %s — outside the 2-4 frames of a 12-frame seam it was set for" % off
    body = FILM.split("const FocusRelayPresentation")[1].split("const focusRelay")[0]
    assert "RELAY_OFFSET, 1" in body and "1 - RELAY_OFFSET" in body, (
        "the entering and leaving beats no longer start at different points")


def test_the_focus_carries_the_cut_not_the_opacity():
    """A long opacity cross on top of a blur is an ordinary dissolve wearing a rack focus."""
    body = FILM.split("const FocusRelayPresentation")[1].split("const focusRelay")[0]
    m = re.search(r"const op = isEnter \? interpolate\(p, \[([\d.]+), ([\d.]+)\]", body)
    assert m, "the opacity ramp moved"
    start, end = float(m.group(1)), float(m.group(2))
    assert start >= 0.25 and (end - start) <= 0.45, (
        "the opacity cross starts at %.2f and spans %.2f — it has become the hand-off" % (start, end - start))


def test_the_planner_routes_a_CROSSING_payoff_to_it():
    """Before this, every seam that crossed a dark/light boundary collapsed to the same carry whatever it was
    claiming. A payoff says 'this became that', and focus is the crossing form that still says it.

    Checked by RUNNING the planner, not by grepping its source. The first version of this test asserted the
    exact ternary the routing was written as, so the day a third crossing route was added — a `new-topic`
    going to the through-dark flight — the assertion failed on a correct change and said nothing about
    whether the payoff still routes anywhere. A test that pins the spelling of a line pins the wrong thing."""
    import seam_plan as sp
    assert sp.CROSSING_PAYOFF_SEAM == {"type": "focus"}
    dark, light = _crossing_pair()
    if not (dark and light):
        pytest.skip("no dark/light pair in the library to build a crossing seam from")
    got = sp.plan(_board(light, dark, 15, "payoff")).get(15)
    assert got and got["type"] == "focus", "a crossing payoff no longer routes to the relay: %r" % (got,)


def test_it_is_registered_in_the_scene_type_and_the_switch():
    assert "| 'focus'" in FILM, "SceneSpec.transitionIn does not admit it"
    assert "case 'focus': return focusRelay();" in FILM


def _crossing_pair():
    """One dark register and one light one, taken from the library rather than named here."""
    import shot_director as sd
    dark = next((n for n in sd.PROVENANCE if sd.shot_luma(n) == "dark"), None)
    light = next((n for n in sd.PROVENANCE if sd.shot_luma(n) == "light"), None)
    return dark, light


def _board(base, other, at, relation):
    """A 30-beat film that is one luminance throughout except for beat `at`, which crosses."""
    slides = [{"shot": base, "relation": "continuation"} for _ in range(30)]
    slides[0]["relation"] = "open"
    slides[at] = {"shot": other, "relation": relation}
    return slides
