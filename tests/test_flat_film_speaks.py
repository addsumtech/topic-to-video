"""A film that never re-grounds must be TOLD so — the light axis's on-ramp.

THE MEASUREMENT THIS EXISTS FOR. 142 of 152 registers measure under the delivery gate's light floor
(median luma_range 0.016 against a floor of 0.135; the four reference launch films run 0.27-0.90). That is
not 142 broken registers: a register holds ONE ground by design, and a film's light comes from moving
BETWEEN beats. Nothing was moving, and nothing said so — the existing warning began at `0 < seen_ground`,
so the one shape that actually ships (zero grounds, one flat exposure, first frame to last) was the one
shape that passed in silence.

WHY A WARNING AND NOT AN ERROR. Where the light goes is a directorial decision, and the AUTOMATIC arc was
built and deliberately withdrawn from the default path (light_plan.py --write refuses without
--accept-risk). This does not make the decision; it says the decision was never made.

The vocabulary itself needed no building — `filmGrounds` derives one from any DNA (0 = the film's own
ground, 1 = its opposite key, 2+ = one chromatic ground per accent) and it was verified by rendering:
median frame luminance 0.04 / 0.04 / 0.91 / 0.38 / 0.33 across ground None/0/1/2/3, with every register
re-inking itself for each. It was simply never named anywhere an author reads.
"""
import os

import validate as v

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(v.__file__)))


def _warn(slides):
    errors, warnings = [], []
    v._beat_grounds(slides, errors, warnings)
    assert not errors, errors
    return [w for w in warnings if "ground" in w]


def test_a_film_that_never_re_grounds_is_told_so():
    hit = _warn([{"index": i} for i in range(20)])
    assert hit, "20 beats on one flat exposure produced no warning"
    assert "flat exposure" in hit[0]


def test_the_warning_hands_over_the_whole_vocabulary():
    """An author who hits this must not have to go looking: the derived indices, the named presets, how many
    beats, and where to put them are all decisions they have to make right now."""
    w = _warn([{"index": i} for i in range(20)])[0]
    for needed in ("ground: 0", "opposite key", "chromatic", "3-6 beats", "energy_waiver", "paper"):
        assert needed in w, "the flat-film warning never mentions %r" % needed


def test_one_bright_passage_is_still_not_an_arc():
    """The pre-existing rule, kept: re-grounding once changes the exposure without making the light move."""
    hit = _warn([{"index": i, **({"ground": 1} if i in (3, 9) else {})} for i in range(20)])
    assert hit and "not a" in hit[0] and "ARC" in hit[0]


def test_a_film_with_a_real_arc_is_left_alone():
    assert not _warn([{"index": i, **({"ground": 1} if i in (3, 9, 14, 18) else {})} for i in range(20)])


def test_a_short_film_is_left_alone():
    """Eight beats is where a luminance arc starts being a thing a viewer can perceive; below it the warning
    would be noise on every sample and test board."""
    assert not _warn([{"index": i} for i in range(5)])


def test_the_authoring_path_names_the_capability():
    """The whole finding was that this system was built, tested, gated — and unreachable, because the agent
    that writes every storyboard never said the word. A gate whose fix is undocumented just moves the
    silence one step later."""
    doc = open(os.path.join(ROOT, "agents", "shot-director.md"), encoding="utf-8").read()
    assert "scene.ground" in doc or "`ground`" in doc, "shot-director never mentions ground"
    for needed in ("ground: 0", "opposite key", "energy_waiver", "ARGUMENT turns"):
        assert needed in doc, "the shot-director's light rule never mentions %r" % needed


def test_a_ground_on_a_register_that_cannot_follow_one_is_caught_before_the_render():
    """The runtime already refuses it — mid-render, minutes in, which is the cost measure_ground_reach.py's
    own docstring says the pre-render check exists to avoid. Found by following the new authoring rule and
    watching the render throw on MorphForms.

    MORPHFORMS NO LONGER STANDS HERE. Its ground was a hardcoded near-black pool painted inside the film's
    own — repaired on 2026-09-20 with the ink sweep, and `measure_ground_reach.py` now measures it as
    FOLLOWING. `EmberFlame` is the example instead: a flame is emitted light, it measures as refusing, and
    the rule under test is unchanged."""
    errors, warnings = [], []
    v._beat_grounds([{"index": i, "shot": "EmberFlame", **({"ground": 1} if i == 2 else {})}
                     for i in range(10)], errors, warnings)
    assert errors and "does not follow one" in errors[0], errors
    assert "EmberFlame" in errors[0] and "shotLuma.ts" in errors[0]


def test_a_ground_on_a_following_register_passes():
    errors, warnings = [], []
    v._beat_grounds([{"index": i, "shot": "CardStack3D", **({"ground": 1} if i == 2 else {})}
                     for i in range(10)], errors, warnings)
    assert not errors, errors


def test_the_follower_list_is_parsed_not_restated():
    """103 names would be stale the day a register is added or re-measured."""
    import inspect
    src = inspect.getsource(v._ground_followers)
    assert "shotLuma.ts" in src and "GROUND_FOLLOWS_MEASURED" in src
    for name in ("CardStack3D", "EmberFlame"):
        assert name not in src, "_ground_followers hardcodes %s" % name
    got = v._ground_followers()
    assert got and len(got) > 50, "the follower list did not parse: %r" % (got,)
