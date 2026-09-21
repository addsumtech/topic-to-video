"""The ink gate's own calibration — on synthetic frames, where the right answer is known.

A gate that renders 340 frames is expensive to trust by re-running, and this one was wrong in four different
ways before it was right: it counted a white card's FILL on warm-white paper, then it dropped bold display
type as if it were a fill, then it read a wordmark on an accent tile against the paper two hundred pixels
away, then it flagged a panel's soft shadow. Each of those is a picture a reader has no trouble with, and a
gate that reports them is a gate that gets discounted — which this repository has already paid for.

So the instrument is held to cases built here, where what a reader would see is not in question:

  a mark that INVERTS with the ground (the register read the DNA)          must pass
  a mark that keeps its light ink when the ground turns light               must fail
  white type on an accent tile, tile and all                                must pass
  a panel's soft glow, which simply stops being visible on light paper      must pass
  one low-contrast hairline among readable words                            must pass

...and, because a SHARE cannot tell those apart from the real thing, the shape of what failed:

  the same count of failing marks, gathered into one lost line                one big hole
  the same count, spread as anti-aliased rims over many small marks           no hole worth reporting
  six glyph-shaped failures 4px apart                                         ONE hole, not six
"""
import importlib.util
import os

import numpy as np
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), "scripts")


def _gate():
    spec = importlib.util.spec_from_file_location("ink_contrast_qa",
                                                  os.path.join(_SCRIPTS, "ink_contrast_qa.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _frame(bg, w=480, h=270):
    return np.tile(np.array(bg, dtype=np.float32) / 255.0, (h, w, 1))


def _text(img, colour, x=40, y=40, rows=6, cols=200, stroke=6, gap=14):
    """Bands of `stroke` px — a stand-in for lines of type, which is what this gate judges."""
    for r in range(rows):
        top = y + r * (stroke + gap)
        img[top:top + stroke, x:x + cols] = np.array(colour, dtype=np.float32) / 255.0
    return img


def _measure(gate, dark, light):
    """Run the gate's own arithmetic over two in-memory frames."""
    dg = gate._y(np.median(dark.reshape(-1, 3), axis=0))
    dy = np.apply_along_axis(gate._y, 2, dark)
    ly = np.apply_along_axis(gate._y, 2, light)
    dark_local = gate._ground_behind(dy, radius=3)
    d_hi = np.maximum(dy, dark_local) + 0.05
    d_lo = np.minimum(dy, dark_local) + 0.05
    mask = (d_hi / d_lo) >= 4.5
    mask = (mask & np.roll(mask, 1, 0) & np.roll(mask, -1, 0)
            & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
    assert mask.sum() > 200, "the synthetic frame drew nothing this gate would judge"
    local = gate._ground_behind(ly, radius=3)
    hi = np.maximum(ly[mask], local[mask]) + 0.05
    lo = np.minimum(ly[mask], local[mask]) + 0.05
    ratios = hi / lo
    return {"share": float((ratios < gate.FAIL_RATIO).mean()), "median": float(np.median(ratios))}


def _flagged(gate, m):
    return m["median"] < gate.FAIL_RATIO or m["share"] >= gate.SHARE_FLOOR


def test_ink_that_inverts_with_the_ground_passes():
    g = _gate()
    dark = _text(_frame((11, 13, 18)), (242, 245, 250))
    light = _text(_frame((246, 243, 238)), (21, 24, 29))       # the register read the DNA
    m = _measure(g, dark, light)
    assert not _flagged(g, m), m
    assert m["median"] > 8, m


def test_ink_that_stays_light_on_a_light_ground_fails():
    g = _gate()
    dark = _text(_frame((11, 13, 18)), (242, 245, 250))
    light = _text(_frame((246, 243, 238)), (242, 245, 250))    # a literal near-white, whatever the film says
    m = _measure(g, dark, light)
    assert _flagged(g, m), m
    assert m["median"] < 1.5, m


def test_white_type_on_an_accent_tile_passes():
    """The mark is read against the TILE, not against the paper across the frame. Measured against the frame's
    median, `BentoReveal`'s wordmark scored 1.0:1 — white on blue, which is what `onAccent` is for."""
    g = _gate()
    dark, light = _frame((11, 13, 18)), _frame((246, 243, 238))
    for img, tile in ((dark, (36, 86, 194)), (light, (29, 99, 214))):
        img[30:200, 30:300] = np.array(tile, dtype=np.float32) / 255.0
        _text(img, (255, 255, 255), x=50, y=60, rows=4, cols=220)
    m = _measure(g, dark, light)
    assert not _flagged(g, m), m


def test_a_panels_soft_glow_is_not_a_mark():
    """A halo differs from the paper far away and barely from itself nearby; on light paper it simply stops
    showing, and no reader loses anything. It must not be measured as ink."""
    g = _gate()
    dark, light = _frame((11, 13, 18)), _frame((246, 243, 238))
    yy, xx = np.mgrid[0:270, 0:480]
    halo = np.exp(-(((yy - 135) / 60.0) ** 2 + ((xx - 240) / 90.0) ** 2))
    dark += (halo[..., None] * 0.55).astype(np.float32)
    light -= (halo[..., None] * 0.03).astype(np.float32)
    _text(dark, (242, 245, 250), y=110, rows=2)
    _text(light, (21, 24, 29), y=110, rows=2)                  # the type itself still inverts
    m = _measure(g, dark, light)
    assert not _flagged(g, m), m


def test_one_unreadable_hairline_among_readable_words_passes():
    """`BentoReveal` keeps a 1px tile border that is blue-on-white at 1.2:1 while every word on it reads at
    4.5:1 or better. The BULK is the headline; one hairline is not a finding."""
    g = _gate()
    dark = _text(_frame((11, 13, 18)), (242, 245, 250))
    light = _text(_frame((246, 243, 238)), (21, 24, 29))
    dark[250:256, 20:460] = np.array((90, 150, 240), dtype=np.float32) / 255.0
    light[250:256, 20:460] = np.array((236, 240, 248), dtype=np.float32) / 255.0
    m = _measure(g, dark, light)
    assert not _flagged(g, m), m
    assert m["share"] > 0, "the hairline should still be counted, just not decisive"


def _fail_map(shape=(540, 960)):
    return np.zeros(shape, dtype=bool)


def test_a_lost_block_of_ink_is_one_region_and_scattered_rims_are_not():
    """The number that tells `AnswerStream` from `StateSheet`, which share cannot.

    Both lost ~43% of their marks. In one, the right half of a three-line sentence turned white-on-white and
    the beat's words stopped existing; in the other, a dozen tiny mono captions kept a soft anti-aliased rim
    and a dozen card borders lost their edge, and a reader misses nothing. The difference is not how much
    failed but whether what failed was one PLACE.
    """
    g = _gate()
    block = _fail_map()
    block[100:140, 300:600] = True                        # a line of type gone: 300x40
    rims = _fail_map()
    for r in range(26):                                   # the SAME pixel count, spread as 1px rims
        for c in range(23):
            rims[80 + r * 12, 40 + c * 40: 40 + c * 40 + 20] = True
    assert abs(int(block.sum()) - int(rims.sum())) < 0.02 * int(block.sum())   # the same amount of ink
    assert g._largest_hole(block) > 8 * g._largest_hole(rims), \
        (g._largest_hole(block), g._largest_hole(rims))


def test_a_hole_is_measured_after_the_gaps_between_glyphs_are_closed():
    """Letters are separate shapes; a lost WORD is not six lost letters. The failing marks are closed before
    they are labelled, so a word reads as one region — otherwise the largest region a sentence can ever show
    is a single letter, and the measure says the same thing as the share again."""
    g = _gate()
    word = _fail_map()
    for k in range(6):                                    # six glyph-sized blobs, 4px apart
        word[300:340, 200 + k * 24: 200 + k * 24 + 20] = True
    one = _fail_map()
    one[300:340, 200:344] = True
    assert g._largest_hole(word) > 0.7 * g._largest_hole(one), (g._largest_hole(word), g._largest_hole(one))


def test_an_empty_failure_map_has_no_hole():
    """The register that passes cleanly must not divide by anything or index an empty count."""
    g = _gate()
    assert g._largest_hole(_fail_map()) == 0


def test_the_two_probe_dnas_differ_only_in_colour():
    """The measurement rests on one pixel being one mark in both renders. Any field that moves a glyph — a
    face, the radius — must be identical in the two probes, or the comparison is between two layouts."""
    g = _gate()
    for k in ("fontDisplay", "fontBody", "fontMono", "radius"):
        assert g.DARK[k] == g.LIGHT[k], k
    assert g._y((0.05, 0.05, 0.07)) < 0.02, "the dark probe is not dark"
    assert g._y((0.96, 0.95, 0.93)) > 0.85, "the light probe is not light"
