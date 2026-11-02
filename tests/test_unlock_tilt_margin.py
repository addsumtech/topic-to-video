"""The caption band reserves the baseline unlock's tilt, so nothing laid out against it can lean into the caption.

WHY. glide's unlock is a 1/1024 skewY held for a register's whole span. It tilts the element's BOX with its type:
the two ends of a box w px wide sit w/2048 px above and below where they were laid out (0.94 px for a full 1920
frame). A block laid flush on the band edge therefore leant a corner into the caption strip — RestsOn's own test
measured it, 0.08 of grey in a band that must be empty — once the unlock stopped switching off at rest (glide_lint,
2026-11-02). The reserve is made at the ONE place every register reads the band from, captionBand(), and the Python
gates read the same constant from layout.ts."""
import math
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)
import _caption_band as cb  # noqa: E402
import _tsprobe  # noqa: E402


@pytest.fixture(scope="module")
def ts():
    if not _tsprobe.available():
        pytest.skip("node/esbuild not available")
    return _tsprobe.run_ts(
        "import {captionBand, captionBandBare, UNLOCK_TILT_DIV} from %s;"
        "import {BASELINE_UNLOCK_SKEW} from %s;" % (_tsprobe.mod("layout.ts"), _tsprobe.mod("glide.ts")),
        "out.skew = BASELINE_UNLOCK_SKEW; out.div = UNLOCK_TILT_DIV;"
        "out.rows = [[1920,1080],[1080,1920],[1080,1080],[1080,1350],[1440,1080]].map(([W,H]) =>"
        " [W, H, captionBand(W,H), captionBandBare(W,H)]);")


def test_the_band_reserves_more_than_the_unlock_can_tilt(ts):
    assert ts["div"] == pytest.approx(2 / ts["skew"]), "UNLOCK_TILT_DIV must follow glide's BASELINE_UNLOCK_SKEW"
    for W, H, band, bare in ts["rows"]:
        tilt = ts["skew"] * W / 2                                # a full-width box's corner, either way
        assert band - bare >= tilt + 0.5, (W, H, band, bare, tilt)


def test_the_python_gates_measure_the_bare_strip_and_know_the_reserve(ts):
    """Gates measure intrusion against the caption's own strip; registers keep clear of the strip plus the tilt.
    Measuring against the reserve too would move the gate's edge WITH the content and leave no margin at all —
    which is what the first version of this fix did."""
    for W, H, band, bare in ts["rows"]:
        assert cb.caption_band_px(W, H) == bare, (W, H)
        assert cb.caption_reserve_px(W, H) == band, (W, H)
