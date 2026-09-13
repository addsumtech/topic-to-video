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


def _cjk_default():
    """The Han advance the fitters default to, READ from the source. It used to be the literal 1.05 in both
    places; when the source named it and gave callers a `cjk` option, a mirror holding its own copy of the
    number would have gone on agreeing with a value the source no longer used."""
    m = re.search(r"export const CJK_FIT_ADVANCE = ([\d.]+);", LAYOUT)
    assert m, "CJK_FIT_ADVANCE is gone from layout.ts — this mirror cannot follow it"
    return float(m.group(1))


def _fit(text, W, base, usable=0.9, adv=None, track=0.0, cjk=None):
    """The TS function, re-evaluated in Python from the same constants — the test fails if the source
    drifts from what these tests believe it does."""
    m = re.search(r"const \{usable = ([\d.]+), adv = ([\d.]+), track = 0, cjk = (\w+)\} = opts", LAYOUT)
    assert m, "fitTextPx's defaults moved — update the extraction"
    assert m.group(3) == "CJK_FIT_ADVANCE", (
        "fitTextPx's Han default is now %r — the mirror follows CJK_FIT_ADVANCE" % m.group(3))
    d_usable, d_adv = float(m.group(1)), float(m.group(2))
    usable = usable if usable != 0.9 else d_usable
    adv = adv if adv is not None else d_adv
    cjk = _cjk_default() if cjk is None else cjk
    w = sum((cjk if re.match(r"[⺀-鿿豈-﫿！-｠　-〿]", ch) else adv) + track
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


def test_a_monospace_caller_gets_the_two_cell_advance():
    """The advance is a property of the FACE. `monoFit()` is the pair a monospace caller hands the fitters,
    and its Han value must be TWO CELLS — not the proportional default this file's mirror uses. Carried as
    one number for both, TermGitLog ran a Chinese commit message 345px off the frame, TensionScale centred a
    note 68px too wide on BOTH sides, and BlueprintGrid clipped a spec by 288px."""
    m = re.search(r"export const monoFit = \(cell = ([\d.]+)\) => \(\{adv: cell, cjk: cell \* 2\}\)", LAYOUT)
    assert m, "monoFit is gone or no longer states the two-cell rule as `cell * 2`"
    cell = float(m.group(1))
    assert cell * 2 > _cjk_default(), (
        "a mono Han glyph (%.2f) measures no wider than the proportional default (%.2f)"
        % (cell * 2, _cjk_default()))
    assert _fit("一手掌握全部工作", 1080, 210, adv=cell, cjk=cell * 2) < _fit("一手掌握全部工作", 1080, 210)
