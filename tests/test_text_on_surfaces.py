"""A word ON a face takes that face's plane; only a word IN the space is a billboard.

THE CLASS, NOT THE INSTANCE. A viewer of a delivered film said the first beat's console windows tilt with
the room while the words on them stay upright — "not aligned like the terminal window is". That was
TermSpace. It was fixed, and the user then asked for the problem to be solved at its root. The root was not
TermSpace: `runtime/stage3d` itself documented "every label is an ordinary 2D DOM element positioned over
them by `projectPose`", and `projectPose` projects a surface's ORIGIN to a point with one uniform scale —
right for a billboard, wrong for a word on a face, which can then move and grow but never turn.

An audit then rendered every 3D register at a frame where its surfaces are tilted and classified each:

    words ON a face, drawn upright      TermSpace (reported), SpatialSlides (found by the audit — each card's
                                        own rules tilt and its title does not)
    words IN the space, correctly level PortRail (labels above modules), MaterialHero (labels beside a
                                        ring), WordTunnel (the phrase IS the object)
    words inside the 3D layer, aligned  CardFlip3D, CubeRotate, CardStack3D, GlowPick
    no words                            FractureIn

The fix lives in the runtime: `<OnSurface>` is the one way to put type on a surface, and a register that
means a billboard says so with `// @billboard: <why>`. This file asserts that rule over every register that
builds on the stage, so the THIRD register does not ship the same way — and proves the check bites on a
source that breaks it, because a rule shown only to pass on today's library has not been shown to do
anything.
"""
import glob
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SHOTS = os.path.join(_ROOT, "remotion", "src", "shots")
_STAGE = os.path.join(_ROOT, "remotion", "src", "runtime", "stage3d.tsx")


def violations(src):
    """[reason] for a register source that breaks the rule; [] when it holds or does not apply."""
    if "from '../runtime/stage3d'" not in src:
        return []
    # SAME LINE ONLY. `\s*` after the colon also matches the newline, so an EMPTY `// @billboard:` took the
    # next line's `import` as its reason and silenced the check — caught by the test below on its first run.
    billboard = re.search(r"//[ \t]*@billboard:[ \t]*\S", src) is not None
    out = []
    draws_surface = "<Surface" in src
    if draws_surface and "<OnSurface" not in src and not billboard:
        out.append("draws <Surface> but places no type with <OnSurface> and declares no @billboard")
    # the anti-pattern itself: a text block positioned at a projected CENTRE, which cannot turn
    if draws_surface and re.search(r"left:\s*q\.x\s*-\s*w\s*/\s*2", src) and not billboard:
        out.append("positions type at the projected centre (`left: q.x - w / 2`) — it cannot take the plane")
    if not draws_surface and "projectPose" in src and not billboard:
        out.append("places words with projectPose and no surface, but does not declare them @billboard")
    return out


def test_every_register_on_the_stage_follows_the_rule():
    names = sorted(glob.glob(os.path.join(_SHOTS, "*.tsx")))
    assert len(names) > 140, "the shots folder moved — this would pass on nothing"
    on_stage, bad = [], {}
    for f in names:
        src = open(f, encoding="utf-8").read()
        if "from '../runtime/stage3d'" in src:
            on_stage.append(os.path.basename(f)[:-4])
        v = violations(src)
        if v:
            bad[os.path.basename(f)[:-4]] = v
    assert on_stage, "no register imports runtime/stage3d — the check is scanning the wrong thing"
    assert not bad, "registers drawing type on the stage the wrong way: %r" % (bad,)


def test_the_check_bites_on_the_exact_pattern_that_shipped():
    """The pre-fix TermSpace/SpatialSlides shape, reduced to what matters. If this passes, the library test
    above is not testing anything."""
    shipped = (
        "import {Stage3D, Surface, projectPose} from '../runtime/stage3d';\n"
        "<Surface pose={p} w={1} h={1} />\n"
        "const q = projectPose(p, cam, P, W, H);\n"
        "<div style={{position: 'absolute', left: q.x - w / 2, top: q.y}}>{label}</div>\n")
    v = violations(shipped)
    assert v, "the pattern that drew text upright over tilted glass passes the check"
    assert any("OnSurface" in r for r in v) and any("projected centre" in r for r in v), v


def test_the_check_bites_on_an_undeclared_billboard():
    """A billboard is legitimate, but it has to be CHOSEN — an unmarked one is indistinguishable from a
    forgotten OnSurface."""
    undeclared = ("import {projectPose} from '../runtime/stage3d';\n"
                  "const q = projectPose(p, cam, P, W, H);\n")
    assert violations(undeclared), "a projectPose-placed word with no @billboard declaration passed"
    declared = "// @billboard: the phrase is the object\n" + undeclared
    assert not violations(declared), "a DECLARED billboard was refused — the rule has no legitimate exit"


def test_a_billboard_declaration_must_give_a_reason():
    """`// @billboard:` with nothing after it is a way to switch the check off without a decision."""
    empty = ("// @billboard:\n"
             "import {projectPose} from '../runtime/stage3d';\nconst q = projectPose(p, cam, P, W, H);\n")
    assert violations(empty), "an empty @billboard declaration silenced the check"


def test_on_surface_is_the_one_implementation():
    """Two registers each hand-rolling the matrix is how they drift. The transform is built in one place."""
    stage = open(_STAGE, encoding="utf-8").read()
    assert "export const OnSurface" in stage and "export const planeAffine" in stage
    for f in glob.glob(os.path.join(_SHOTS, "*.tsx")):
        src = open(f, encoding="utf-8").read()
        assert "`matrix(${aff.m11}" not in src, (
            "%s hand-rolls the plane matrix instead of using <OnSurface>" % os.path.basename(f))


def test_the_runtime_no_longer_states_the_rule_that_caused_it():
    """The header said "every label is an ordinary 2D DOM element positioned over them by `projectPose`", and
    two registers built exactly that. A rule documented wrong gets implemented wrong."""
    stage = open(_STAGE, encoding="utf-8").read()
    assert "positioned over them by `projectPose`" not in stage, (
        "stage3d's header is back to telling registers to place every word by projectPose")
    assert "2D DOES NOT MEAN UPRIGHT" in stage
