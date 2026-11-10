"""meta.signature_material — the one material a film makes its invisible subject visible through (advisory)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import validate as v                                                             # noqa: E402

SLIDES = [{"index": i} for i in range(1, 11)]


def test_a_long_film_without_one_is_asked_for_one():
    w = v._signature_material({}, SLIDES)
    assert len(w) == 1 and "signature material" in w[0]


def test_a_short_film_is_not_asked():
    assert v._signature_material({}, SLIDES[:5]) == []


def test_a_named_recurring_material_is_clean():
    sm = {"name": "refractive glass rings", "shows": "sound being cancelled", "beats": [2, 5, 9]}
    assert v._signature_material({"signature_material": sm}, SLIDES) == []


def test_a_material_seen_once_is_a_prop():
    sm = {"name": "cloth", "shows": "sound", "beats": [3]}
    assert any("fewer than two" in m for m in v._signature_material({"signature_material": sm}, SLIDES))


def test_malformed_and_off_board_entries_are_named():
    assert v._signature_material({"signature_material": "glass"}, SLIDES)
    sm = {"name": "cloth", "shows": "sound", "beats": [3, 40]}
    assert any("not on the board" in m for m in v._signature_material({"signature_material": sm}, SLIDES))
