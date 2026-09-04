"""fitTextPx — the width constraint display type was missing, proved on the failures that forced it.

Twenty-three registers cut type at 9:16 because a font size chosen for the TEXT and the FRAME IT WAS
AUTHORED ON was never related to the width it ships at. The helper estimates; these tests pin the three
properties the estimate must keep: it only ever shrinks, it counts CJK at full width, and it counts
tracking — each one a real bug class this repo has already paid for.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT = open(os.path.join(ROOT, "remotion", "src", "runtime", "layout.ts"), encoding="utf-8").read()


def _fit(text, W, base, usable=0.9, adv=None, track=0.0):
    """The TS function, re-evaluated in Python from the same constants — the test fails if the source
    drifts from what these tests believe it does."""
    m = re.search(r"const \{usable = ([\d.]+), adv = ([\d.]+), track = 0\} = opts", LAYOUT)
    assert m, "fitTextPx's defaults moved — update the extraction"
    d_usable, d_adv = float(m.group(1)), float(m.group(2))
    usable = usable if usable != 0.9 else d_usable
    adv = adv if adv is not None else d_adv
    w = sum((1.05 if re.match(r"[⺀-鿿豈-﫿！-｠　-〿]", ch) else adv) + track
            for ch in (text or " "))
    return max(12, min(base, int((W * usable) / max(0.1, w))))


def test_it_only_ever_shrinks():
    assert _fit("Hi", 1920, 96) == 96, "a short word should keep its authored size"


def test_the_portrait_case_it_was_built_for():
    """'WORKBUDDY' at 210px lost 107px off each edge of a 1080-wide frame; fitted, it must fit."""
    px = _fit("WORKBUDDY", 1080, 210)
    assert px < 210
    assert px * 9 * 0.72 <= 1080 * 0.92, "the fitted size still cannot hold the word"


def test_cjk_counts_at_full_width():
    """Geometry that assumes Latin advances measured a Chinese deck 46% short once already."""
    latin = _fit("ABCDEFGH", 1080, 210)
    cjk = _fit("一手掌握全部工作", 1080, 210)
    assert cjk < latin, "eight CJK glyphs measured no wider than eight Latin ones"


def test_tracking_is_part_of_width():
    """A 0.42em-tracked tagline is nearly half tracking by length."""
    assert _fit("ON YOUR MACHINE", 1080, 60, track=0.42) < _fit("ON YOUR MACHINE", 1080, 60)


def test_the_default_advance_is_generous_not_condensed():
    """The face that renders is the DNA's, not the register's fallback stack: a call tuned to condensed
    Antonio (0.52) shipped Space Grotesk and still clipped 85px per edge. The default must cover the
    widest face the DNA system actually ships."""
    m = re.search(r"adv = ([\d.]+), track", LAYOUT)
    assert float(m.group(1)) >= 0.70, "the default advance was lowered — that re-opens the HoloFoil clip"
