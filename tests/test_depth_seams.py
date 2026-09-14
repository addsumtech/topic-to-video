"""The other two DEPTH seams — through-dark flight and portal wipe.

WHERE THEY CAME FROM, AND WHAT WAS ACTUALLY BORROWED. Measured against the video-shotcraft library, three of
its six documented hand-off recipes are built on depth — through-dark flight, focus relay, portal wipe — and
this tier had none. The focus relay was borrowed first, WITH its parameters, which the peer study had quoted
verbatim. For these two the study recorded only the NAMES, and the library is no longer on disk, so the
numbers here are derived rather than borrowed and the source comments say so. What is not derived is the
SHAPE of the argument: a seam is a claim about how two beats relate.

THE PROPERTY THAT SEPARATES THEM is luminance, and it is the reason one is exempt from the guard and the
other is not:

  through-dark  the two beats never carry light at the same time, so there is no instant where a bright
                frame is added to a dark one. Exempt, and more strongly than `carry` (whose bridge line IS
                the dip) or `focus` (which redistributes light without adding any).
  portal        both beats are on screen at once, one of them through a hole. A bright aperture opening on
                a dark field is exactly the brightness jump the guard exists to refuse. NOT exempt.

MEASURED ON A RENDERED THREE-BEAT FILM, because a seam that type-checks is not a seam that works. Across the
through-dark seam the frame's mean luminance ran 0.068 -> 0.016 -> 0.013 -> 0.010 (frame max 0.14: the
picture is black) -> 0.040 -> 0.070. A cross-fade between two dark beats holds near 0.07 the whole way, so
the dip is the flight and not a fade wearing its name.

AND THE FIRST PORTAL RUN VERIFIED THE GUARD, NOT THE SEAM. Beat 3 was an accent flood, so the seam crossed a
dark/light boundary and was correctly rewritten to a fade — the measured ramp was a fade's smooth monotone
0.079 -> 0.566. Re-run between two dark beats it renders as a portal: the incoming beat at the centre at
full size, the outgoing beat still visible in the corners and scaled past the lens.
"""
import os
import re

import render_remotion as rr
import seam_plan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(rr.__file__)))
FILM = open(os.path.join(ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()


def _body(name):
    return FILM.split("const %sPresentation" % name)[1].split("\nconst ", 1)[0]


# ── the board path: built but unreachable is the failure this repo has already paid for twice ──────────
def test_both_seams_can_be_ASKED_FOR_by_a_storyboard():
    """`seam_plan.py`'s own docstring records a delivered 35-beat film whose 34 seams were all the default
    cross-fade, because nothing in the authoring path ever wrote the field."""
    assert "through-dark" in rr._KINETIC_TYPES and "portal" in rr._KINETIC_TYPES
    assert rr._transition_in({"transition_in": {"type": "through-dark"}}) == {"type": "through-dark"}
    assert rr._transition_in({"transition_in": {"type": "portal"}}) == {"type": "portal"}


def test_the_style_aliases_reach_them_too():
    """An author writing `transition_style` rather than an explicit mark must land on the same seam."""
    for alias, want in (("through-dark", "through-dark"), ("flight", "through-dark"),
                        ("through-black", "through-dark"), ("portal", "portal"), ("aperture", "portal")):
        assert rr._transition_in({"transition_style": alias}) == {"type": want}, alias


def test_the_film_renders_both_rather_than_falling_through_to_a_fade():
    """A switch that does not name them returns `fade()` from its default arm — silently, and the film looks
    finished. This is the second half of the same unreachability failure."""
    sw = FILM.split("switch (t) {")[1].split("\n};")[0]
    assert "case 'through-dark': return throughDark();" in sw, sw[-400:]
    assert "case 'portal': return portal(W, H);" in sw, sw[-400:]


# ── the luminance guard: one is exempt, one must not be ───────────────────────────────────────────────
def test_the_flight_is_exempt_from_the_guard_and_the_portal_is_NOT():
    m = re.search(r"CANNOT_FLASH = new Set\(\[([^\]]*)\]\)", FILM)
    assert m, "the guard's exemption set is gone"
    inside = m.group(1)
    assert "'through-dark'" in inside, (
        "the flight is refused across the dark/light boundary it is the best seam for: %r" % inside)
    assert "'portal'" not in inside, (
        "a bright aperture opening on a dark field is the flash this guard exists to refuse: %r" % inside)
    # and the two that were already there stay there
    assert "'carry'" in inside and "'focus'" in inside, inside


def test_a_crossing_new_topic_routes_to_the_flight_instead_of_collapsing_to_the_carry():
    """Every crossing seam used to become the carry whatever it was claiming. A bridge line is a claim of
    CONTINUITY, which is the opposite of what a chapter break across a light boundary says."""
    assert seam_plan.CROSSING_NEW_TOPIC_SEAM == {"type": "through-dark"}
    assert seam_plan.CROSSING_PAYOFF_SEAM == {"type": "focus"}, "the payoff route moved"
    assert seam_plan.CROSSING_SEAM == {"type": "carry"}, "the fallback route moved"


# ── the two moves themselves ──────────────────────────────────────────────────────────────────────────
def test_the_flight_actually_goes_THROUGH_something():
    """Brightness is what makes it a flight through dark rather than two scales pointed at each other. A
    version that only moved the scale would leave the frame lit the whole way and read as a push."""
    body = _body("ThroughDark")
    assert "brightness(" in body, body
    assert re.search(r"FLIGHT_TOWARD\s*=\s*1\.[1-9]", FILM), "the arriving beat no longer starts out from the lens"
    assert re.search(r"FLIGHT_AWAY\s*=\s*0\.[5-9]", FILM), "the leaving beat no longer recedes"


def test_the_flight_ramps_OVERLAP_so_the_dark_is_passed_through_not_held():
    """With a gap the frame HOLDS on black, and a held black frame inside four tenths of a second is a
    dropout rather than a move. The crossover past 0.5 is what makes the two ramps overlap."""
    m = re.search(r"FLIGHT_CROSS = ([\d.]+)", FILM)
    assert m, "the crossover constant is gone"
    cross = float(m.group(1))
    assert 0.5 < cross < 0.62, "crossover %s — outside it the two ramps leave a gap or never darken" % cross


def test_the_portal_reveals_through_a_MASK_and_the_arriving_beat_never_fades():
    """An opacity ramp under an opening aperture is a dissolve with a shape on it."""
    body = _body("Portal")
    assert "maskImage" in body, body
    enter = body.split("if (!isEnter)")[1].split("}", 1)[1]
    assert "opacity" not in enter, "the arriving beat fades under its own aperture: %r" % enter[:400]


def test_the_portal_opens_on_the_CONTENT_ZONE_not_the_frame():
    """The strip below `contentBottom` belongs to the burned caption, so the frame's own centre sits low of
    everything a viewer is looking at — by 90px at 16:9 and 190px at 9:16."""
    body = _body("Portal")
    assert "CONTENT_TOP" in body and "contentBottom" in body, body[:400]
    assert "at 50% 50%" not in body, "the aperture went back to the frame centre"


def test_the_two_seams_are_not_the_same_move_with_two_names():
    """They are different claims: one leaves through darkness, the other goes through the frame. If they
    shared a body, one of the two names would be decoration."""
    assert _body("ThroughDark") != _body("Portal")
    assert "maskImage" not in _body("ThroughDark"), "the flight grew an aperture"
    assert "brightness(" not in _body("Portal"), "the portal grew a dip to black"
