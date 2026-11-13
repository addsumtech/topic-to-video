"""A register that declares CLOCK = 'own' is never clock-warped: the warp is piecewise linear, so on a continuous
camera every knot is a corner (a ProductPage beat's page dropped from 3.9 to 0.4 px a frame at one)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import sync_qa as sq  # noqa: E402


def test_declared_own_clock_is_exempt():
    for shot in ("ProductPage", "ChapterCard"):
        why = sq.register_exempt(shot)
        assert why and "CLOCK = 'own'" in why, (shot, why)


def test_an_ordinary_register_is_still_warpable():
    assert sq.register_exempt("HeadlineReveal") is None
