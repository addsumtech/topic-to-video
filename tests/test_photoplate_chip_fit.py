"""A numbered callout chip on PhotoPlate is as wide as what it holds, so a short label stays on one line.

THE DEFECT, ON A DELIVERED FRAME. A city film's chip read 「对岸：深圳」 with its last glyph alone on a second
line. The chip's width was a sum that under-counted its own contents: the number in front of the label (one or
two digits and two non-breaking spaces, set in the mono face) was budgeted as 1.6em when it is 1.8-2.4em; the
box's side padding (1.4 × the pad, each side) and its border were budgeted as one pad each; and the full-width
colon fell outside the CJK character class, so it was counted at the Latin advance while it renders a whole em
wide. A short Chinese label has too little slack to absorb any of that, so it broke a glyph off — 「关口」 under
mark 3 is a few pixels short as well. The wrap simulation sized the box's HEIGHT for the second line, which is
why no gate saw a clipped line: only cjk_type_qa's orphan check (a last line holding one character) named it.

Rendered, through the gate's own instrument, with the copy that failed: no chip may orphan a glyph.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)

import _tsprobe  # noqa: E402

needs_toolchain = pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")


@needs_toolchain
def test_a_short_numbered_chinese_chip_keeps_every_glyph_on_its_line(tmp_path):
    import cjk_type_qa as cq
    import register_energy as reg
    src = reg.ensure_fixture()
    assert src, "the stand-in photograph could not be drawn (PIL missing?)"
    props = {
        "src": src, "imageAspect": 1400 / 933,
        "title": "一线 · 深圳河", "caption": "从香港罗湖站隔着深圳河望向深圳",
        "credit": "Daniel Case · CC BY-SA 3.0 · Wikimedia Commons",
        "marks": [
            {"n": 2, "x": 0.72, "y": 0.34, "label": "对岸：深圳"},              # the delivered frame's chip
            {"n": 3, "x": 0.4, "y": 0.5, "label": "关口"},                      # pure Han, two glyphs
            {"n": 1, "x": 0.62, "y": 0.66, "label": "深圳河，香港与内地的界河"},  # a long one, which always fit
        ],
    }
    frame = int(cq.durations()["PhotoPlate"] * cq.PROBE_FRAC)     # the frame the gate itself judges
    hits = cq.audit("PhotoPlate", props, frame, str(tmp_path / "plate.png"))
    assert hits is not None, "PhotoPlate did not render the probe"
    orphans = [h for h in hits if h.get("kind") == "orphan"]
    assert not orphans, "a chip broke a glyph onto a line of its own: %s" % (
        "; ".join("%r" % (h.get("text") or h) for h in orphans))
