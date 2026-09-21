"""The density advisory must DIRECT the work, never do it — and never advise from an opinion.

Four candidate shared levers for the density axis were built and measured and all four failed (they are
listed in density_advice.py's own docstring, so nobody re-tries them). What generalises is not a mechanism
but direction: every design family holds both starved and dense registers, so a starved beat usually has a
denser neighbour on the same shelf.

The two things pinned here are the two ways this could quietly become useless: advising from something other
than measured pixels, and letting an unmeasured register read as a fine one.
"""
import json
import os

import pytest

import density_advice as da
import film_energy_qa as fe
import shot_director as sd


def _board(tmp_path, shots, name="film"):
    d = tmp_path / name
    d.mkdir(parents=True)
    (d / "storyboard.json").write_text(json.dumps(
        {"slides": [{"index": i, "shot": s} for i, s in enumerate(shots)]}), encoding="utf-8")
    return str(d)


def test_the_floor_is_the_delivery_gate_s_floor_not_a_second_copy():
    """A private copy would keep advising against the old number after the gate moved — the way this repo's
    caption band became four disagreeing definitions."""
    import inspect
    src = inspect.getsource(da)
    assert "fe.INK_FLOOR" in src and "0.12" not in src.split('"""')[2], (
        "density_advice carries its own ink floor instead of reading film_energy_qa's")


def test_it_advises_from_the_measured_sweep_and_says_so_when_there_is_none(tmp_path, monkeypatch):
    monkeypatch.setattr(da, "MANIFEST", str(tmp_path / "absent.json"))
    with pytest.raises(RuntimeError, match="register_energy"):
        da.measured()


def test_an_unmeasured_register_is_named_not_counted_as_fine(tmp_path):
    """Absence from the sweep reading as a pass is the failure this repo keeps finding."""
    out = _board(tmp_path, ["LastLeg", "NotARegisterAtAll"])
    beats, unknown, _ink, _floor, skipped, universe = da.advise(out)
    assert universe == 2, "M is the board's own length, not a count of what survived the loop"
    assert [b[1] for b in beats] == ["LastLeg"]
    assert unknown == ["NotARegisterAtAll"]
    # …and it leaves the measurement THROUGH the same list every other skip does, carrying its beat number
    # and a reason, so the coverage line and the exit code cannot disagree with the advice.
    assert [(b, s) for b, s, _ in skipped] == [(2, "NotARegisterAtAll")]
    assert "register_energy.py" in skipped[0][2]
    assert da.main([out]) == 1, "an unmeasured register must make the run non-zero"


def test_every_alternative_is_in_the_same_family_and_over_the_floor():
    """A cross-family swap is a different film, and an alternative under the floor is not an alternative."""
    ink = da.measured()
    floor = fe.INK_FLOOR
    checked = 0
    for shot, v in ink.items():
        if v >= floor or shot not in sd.FAMILY:
            continue
        for alt_v, alt in da.alternatives(shot, ink, floor):
            assert sd.FAMILY[alt] == sd.FAMILY[shot], "%s is not in %s's family" % (alt, shot)
            assert alt_v >= floor, "%s is offered as an alternative at %.3f" % (alt, alt_v)
            assert alt != shot
            checked += 1
    assert checked > 20, "only %d alternatives were checked — the sweep or the family map looks empty" % checked


def test_alternatives_are_offered_densest_first():
    ink = da.measured()
    for shot in list(ink)[:40]:
        alts = da.alternatives(shot, ink, fe.INK_FLOOR)
        assert alts == sorted(alts, reverse=True), (shot, alts)


def test_a_register_with_no_dense_neighbour_is_told_so_rather_than_left_silent(tmp_path, capsys):
    ink = da.measured()
    lonely = [s for s in ink if ink[s] < fe.INK_FLOOR and not da.alternatives(s, ink, fe.INK_FLOOR)]
    if not lonely:
        pytest.skip("every starved register currently has a denser neighbour")
    da.main([_board(tmp_path, [lonely[0]])])
    assert "needs its own composition" in capsys.readouterr().out


def test_the_advisory_refuses_to_be_read_as_an_instruction(tmp_path, capsys):
    """Swapping to whatever measures densest is how a film ends up carrying ink no viewer can decode. The
    output has to say so, every time it names a candidate."""
    ink = da.measured()
    starved = [s for s in ink if ink[s] < fe.INK_FLOOR and da.alternatives(s, ink, fe.INK_FLOOR)]
    da.main([_board(tmp_path, [starved[0]])])
    out = capsys.readouterr().out
    assert "CANDIDATES, not instructions" in out and "encodes the" in out


# ── COVERAGE: the headline must say what it did NOT measure, and derive M from the board ──────────────
#
# `[density] 6 beat(s)` was the count that SURVIVED the loop: a beat with no register `continue`d into
# silence, appearing in no list, no count and no line, so an eight-beat film reported six and the number
# read as the film. These pin the derivation and the naming; `_mutant` then breaks the gate on purpose.

def _mutant(old, new):
    """density_advice with ONE source edit, exec'd into a fresh namespace. Never writes to the repo."""
    import types
    src = open(da.__file__, encoding="utf-8").read()
    assert old in src, "the mutation target has drifted out of the source: %r" % old
    mod = types.ModuleType("density_advice_mutant")
    mod.__file__ = da.__file__
    exec(compile(src.replace(old, new, 1), da.__file__, "exec"), mod.__dict__)
    return mod


def _mixed_board(tmp_path, name="film"):
    """Eight entries: six measurable, one with no register, one that is not a beat object at all."""
    d = tmp_path / name
    d.mkdir()
    shots = ["LastLeg", "TermSpace", None, "TermLog", "NotARegisterAtAll", "TaskFold", "SplitFlap"]
    slides = [{"index": i, "shot": s} for i, s in enumerate(shots)] + ["a stray string"]
    (d / "storyboard.json").write_text(json.dumps({"slides": slides}), encoding="utf-8")
    return str(d)


@pytest.mark.parametrize("n", [1, 4, 9])
def test_the_coverage_line_derives_its_universe_from_the_board(tmp_path, capsys, n):
    """M is parsed from `slides`, never restated. A constant would keep printing the same M for any film."""
    da.main([_board(tmp_path, ["LastLeg"] * n, name="film%d" % n)])
    assert "measured %d of %d" % (n, n) in capsys.readouterr().out


def test_a_beat_that_leaves_the_measurement_is_counted_and_named(tmp_path, capsys):
    out = _mixed_board(tmp_path)
    rc = da.main([out])
    text = capsys.readouterr().out
    assert "measured 5 of 8" in text and "3 NOT measured" in text, text
    # NAMED, with a beat number and a reason a reader can act on — not "skipped".
    assert "beat   3" in text and "shot-director" in text, text
    assert "beat   5" in text and "NotARegisterAtAll" in text and "register_energy.py" in text, text
    assert "beat   8" in text and "not a beat object" in text, text
    assert rc == 1, "a run that could not measure part of its universe must not exit 0"


def test_the_mutation_that_drops_a_beat_is_caught(tmp_path, capsys):
    """THE MUTATION. Put the silent `continue` back for an unassigned beat: the gate still measures the
    same five, still prints a coverage line, and the line now lies about M. A coverage test that stays
    green here would be worse than no test."""
    mod = _mutant('            skipped.append((_pos, None, "no register assigned yet — run the shot-director,'
                  ' then re-run this"))\n            continue',
                  "            continue")
    with pytest.raises(RuntimeError, match="recorded no reason"):
        mod.main([_mixed_board(tmp_path, "mutant")])
    # It was NOT always this loud. The first version of the fix derived M from `len(beats) + len(skipped)`,
    # and this same mutant printed a confident "measured 5 of 7" — the universe shrank in step with the
    # beat it had just lost, so the coverage line read 100% while a beat had vanished. That is why M is
    # parsed from the board and why the invariant above refuses rather than rounds.
    assert "measured 5 of 7" not in capsys.readouterr().out
