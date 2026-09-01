import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import contest_diversity as cd


def _frame(path, bg, ink, boxes):
    im = Image.new("RGB", (640, 360), bg)
    d = ImageDraw.Draw(im)
    for (x0, y0, x1, y1) in boxes:
        d.rectangle([x0, y0, x1, y1], fill=ink)
    im.save(path)


def test_identical_frames_flagged(tmp_path):
    a = str(tmp_path / "a.png"); b = str(tmp_path / "b.png")
    _frame(a, "#f4f2ed", "#222", [(60, 60, 400, 160)])
    _frame(b, "#f4f2ed", "#222", [(60, 60, 400, 160)])
    r = cd.check([a, b])
    assert r["flagged"] == [[a, b]]


def test_a_mode_flip_over_the_same_layout_is_still_one_idea(tmp_path):
    """This asserted the opposite, and the opposite is the defect.

    The old contract was "a mode flip alone is strong divergence", and its fixture put the SAME rectangle in
    the SAME place twice — one light, one dark — and required it to pass. A viewer shown three directions
    built that way said they could be one film: they differed in palette and in which registers were named,
    and not at all in how a frame was ORGANISED. Measured, two of them had their ink centroid at (0.48,0.72)
    and (0.45,0.71) with near-identical long-run ratios. A direction is a way of building a frame; a
    colourway is not a second direction, and neither is a mode flip over the same composition.
    """
    a = str(tmp_path / "a.png"); b = str(tmp_path / "b.png")
    _frame(a, "#f4f2ed", "#222", [(60, 60, 400, 160)])
    _frame(b, "#0e0f11", "#ffb454", [(60, 60, 400, 160)])   # same layout, dark+amber
    r = cd.check([a, b])
    assert r["flagged"], "the same composition in two colourways still reads as two directions"
    assert r["modes"][b] == "dark"


def test_a_mode_flip_with_a_different_composition_diverges(tmp_path):
    """And the intuition the old test was reaching for still holds — once the composition moves too."""
    a = str(tmp_path / "a.png"); b = str(tmp_path / "b.png")
    _frame(a, "#f4f2ed", "#222", [(60, 60, 400, 160)])                                # one top band
    _frame(b, "#0e0f11", "#ffb454", [(60, 200, 180, 330), (220, 200, 340, 330),
                                     (380, 200, 500, 330), (540, 200, 620, 330)])     # four low tiles
    r = cd.check([a, b])
    assert r["flagged"] == [], r["pairs"]


def test_different_silhouettes_diverge(tmp_path):
    a = str(tmp_path / "a.png"); b = str(tmp_path / "b.png")
    _frame(a, "#f4f2ed", "#e2231a", [(40, 40, 600, 120)])                      # top band
    _frame(b, "#f6f3ea", "#a4231b", [(40, 200, 200, 340), (420, 200, 600, 340)])  # two bottom blocks
    r = cd.check([a, b])
    assert r["flagged"] == []
