"""validate prints at most a few warnings of one kind and counts the rest: the ANC film's runs carried a dozen
advisory lines, most of them repeats of one kind, and the ones worth acting on drowned among them."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import validate as v  # noqa: E402


def test_repeats_of_one_kind_are_counted_not_listed():
    ws = ["rhythm: beat %d is long" % i for i in (7, 12, 16, 19, 21)] + ["tier: purpose is teach"]
    lines = v._grouped_warnings(ws, keep=3)
    assert lines[:3] == ws[:3] and "tier: purpose is teach" in lines
    assert any("2 more" in l and "rhythm" in l for l in lines), lines
    assert len(lines) == 5


def test_scene_numbered_warnings_are_one_kind():
    ws = ["scene #%d: X has no recorded shot_adaptation" % i for i in range(1, 6)]
    lines = v._grouped_warnings(ws, keep=2)
    assert len(lines) == 3 and "3 more" in lines[-1]
