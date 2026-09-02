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


def _board(tmp_path, shots):
    d = tmp_path / "film"
    d.mkdir()
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
    beats, unknown, _ink, _floor = da.advise(out)
    assert [b[1] for b in beats] == ["LastLeg"]
    assert unknown == ["NotARegisterAtAll"]
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
