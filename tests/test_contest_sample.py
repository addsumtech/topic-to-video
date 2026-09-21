"""A conceived direction must reach the screen as ITSELF.

`contest_sample.py --conceived` exists so an author can state a direction as FRAMES and have the user SEE
it. It put the direction's `dna` into the Film's `template` prop, and a conceived DNA is an OBJECT, which
`dnaFromTemplate()` cannot resolve — so every conceived direction rendered in the default look and the
contest asked a user to choose between three ballots none of which had been applied. Measured on a real
three-direction Chinese film: a direction declaring `bg: #F2EDE3` (paper, Y=0.850) came back near-black and
its props file carried no `dna` key at all. That is worse than having no contest, because the ballot looks
real.
"""
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), "scripts")


def _mod():
    spec = importlib.util.spec_from_file_location(
        "contest_sample", os.path.join(_SCRIPTS, "contest_sample.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _spec(**kw):
    d = {"key": "paper-dossier", "pitch": "卷宗", "shots": [["EdStat", {"figure": "1000 万"}],
                                                          ["EdCompare", {"kicker": "两种做法"}]]}
    d.update(kw)
    return d


def test_a_conceived_dna_reaches_the_film_as_a_dna_not_as_a_template_name():
    m = _mod()
    dna = {"id": "paper", "bg": "#F2EDE3", "fg": "#101A33", "accent": "#133C9A"}
    p = m.build_props_conceived(_spec(dna=dna), "介绍飞书")
    assert p.get("dna") == dna, (
        "the conceived look went to %r instead of the Film's `dna` prop, so it renders as the default"
        % sorted(p))
    assert "template" not in p, "a conceived DNA must not also claim a preset name: %r" % p.get("template")


def test_a_preset_NAME_still_goes_to_template():
    """The seed path is unchanged — a string names a preset, and `render_remotion.py` routes it the same way."""
    m = _mod()
    p = m.build_props_conceived(_spec(dna="editorial"), "介绍飞书")
    assert p.get("template") == "editorial", p
    assert "dna" not in p, p


def test_the_marked_seam_keeps_its_direction():
    """A film's seam is `{type, direction}`. Wrapping it as `{"type": <the whole object>}` makes the one
    marked cut in the sample anonymous, which is the same defect one layer down."""
    m = _mod()
    p = m.build_props_conceived(_spec(dna={"id": "x"}, seam={"type": "wipe", "direction": "from-top"}),
                                "介绍飞书")
    assert p["scenes"][1]["transitionIn"] == {"type": "wipe", "direction": "from-top"}, \
        p["scenes"][1]["transitionIn"]
    # ...and a bare string is still accepted, since that is how the seeds spell it
    q = m.build_props_conceived(_spec(dna={"id": "x"}, seam="clock"), "介绍飞书")
    assert q["scenes"][1]["transitionIn"] == {"type": "clock"}, q["scenes"][1]["transitionIn"]


def test_a_direction_with_no_frames_is_refused():
    """A direction that cannot be rendered is a pitch, and the contest exists so the user SEES it."""
    m = _mod()
    import pytest
    with pytest.raises(SystemExit):
        m.build_props_conceived(_spec(shots=[]), "介绍飞书")
