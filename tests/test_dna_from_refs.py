"""A film's palette READ from its style references (scripts/dna_from_refs.py), as dna_from_deck reads a deck's.

The cartoon acceptance film's palette was written by hand from looking at the references; reading it is repeatable
and says where each colour came from. Ground = the largest light (or dark) field, ink = the darkest (or lightest)
frequent colour, accents = the most saturated frequent colours of distinct hues.
"""
import json
import os

import numpy as np
import pytest
from PIL import Image, ImageDraw

import dna_from_refs as dfr


def _ref(path, ground=(250, 240, 220), blobs=((220, 50, 40), (40, 110, 210)), ink=(25, 20, 18)):
    img = Image.new("RGB", (400, 300), ground)
    d = ImageDraw.Draw(img)
    d.ellipse([40, 60, 180, 220], fill=blobs[0], outline=ink, width=6)
    d.rectangle([220, 80, 360, 230], fill=blobs[1], outline=ink, width=6)
    img.save(path)
    return str(path)


def _hue(hexc):
    import colorsys
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)


def test_a_light_set_reads_as_light_ground_dark_ink_two_accents(tmp_path):
    refs = [_ref(tmp_path / ("r%d.png" % k)) for k in range(3)]
    dna = dfr.derive(refs)
    import dna_from_deck  # noqa: F401 — same DNA shape
    assert _hue(dna["bg"])[2] > 0.9 and _hue(dna["fg"])[2] < 0.2
    hues = sorted(_hue(dna[k])[0] for k in ("accent", "accent2"))
    assert hues[0] < 0.08 or hues[0] > 0.92 or hues[1] > 0.9, hues            # a red
    assert any(0.5 < h < 0.7 for h in hues), hues                             # a blue
    assert dna["provenance"]["from"] == "style refs" and len(dna["provenance"]["colours"]) >= 4


def test_a_dark_set_reads_as_dark_ground_light_ink(tmp_path):
    refs = [_ref(tmp_path / ("d%d.png" % k), ground=(15, 18, 24), ink=(240, 236, 228)) for k in range(2)]
    dna = dfr.derive(refs)
    assert _hue(dna["bg"])[2] < 0.15 and _hue(dna["fg"])[2] > 0.85


def test_contrast_is_held(tmp_path):
    from_ = dfr.derive([_ref(tmp_path / "c.png", ground=(200, 200, 200), ink=(120, 120, 120))])
    import theme
    rgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    assert theme._contrast(rgb(from_["fg"]), rgb(from_["bg"])) >= 7.0       # ink pushed until it reads (theme.py's WCAG)


def test_it_writes_the_board_and_never_overwrites_an_authored_dna(tmp_path):
    (tmp_path / "style_refs").mkdir()
    _ref(tmp_path / "style_refs" / "a.png")
    board = {"meta": {"renderer": "remotion", "style": {"name": "x", "refs": [{"src": "style_refs/a.png", "from": "found"}]}},
             "slides": []}
    (tmp_path / "storyboard.json").write_text(json.dumps(board))
    assert dfr.main([str(tmp_path)]) == 0                                    # no DNA yet: the whole palette is read
    dna = json.load(open(tmp_path / "storyboard.json"))["meta"]["design_dna"]
    assert dna["provenance"]["from"] == "style refs"
    board["meta"]["design_dna"] = {"id": "mine", "bg": "#123456", "fg": "#fafafa", "accent": "#777777"}
    (tmp_path / "storyboard.json").write_text(json.dumps(board))
    assert dfr.main([str(tmp_path), "--ground"]) == 2                        # the ground is a design decision: refused
    assert json.load(open(tmp_path / "storyboard.json"))["meta"]["design_dna"]["accent"] == "#777777"
    assert dfr.main([str(tmp_path), "--ground", "--force"]) == 0


def test_with_a_dna_only_the_accents_are_read(tmp_path):
    """A reference's largest area is its own backdrop (a cel's painted sky), not the film's ground: read as the ground
    it turned a cartoon on cream into slate and white (the second acceptance film; the user found it worse). So a film
    that HAS a DNA keeps its ground and ink, and takes the references' accents."""
    (tmp_path / "style_refs").mkdir()
    _ref(tmp_path / "style_refs" / "a.png", ground=(60, 80, 95))
    board = {"meta": {"design_dna": {"id": "cream", "bg": "#fff4df", "fg": "#231a14", "accent": "#777777", "accent2": "#888888"},
                      "style": {"name": "x", "refs": [{"src": "style_refs/a.png", "from": "found"}]}}, "slides": []}
    (tmp_path / "storyboard.json").write_text(json.dumps(board))
    assert dfr.main([str(tmp_path)]) == 0
    dna = json.load(open(tmp_path / "storyboard.json"))["meta"]["design_dna"]
    assert (dna["id"], dna["bg"], dna["fg"]) == ("cream", "#fff4df", "#231a14")
    hues = sorted(_hue(dna[k])[0] for k in ("accent", "accent2"))
    assert any(h < 0.08 or h > 0.92 for h in hues) and any(0.5 < h < 0.7 for h in hues), (dna["accent"], dna["accent2"])
    assert dna["provenance"]["accents_from"] == "style refs"


def test_no_refs_is_refused(tmp_path):
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"style": {"name": "x", "refs": []}}, "slides": []}))
    assert dfr.main([str(tmp_path)]) == 2


def test_a_ref_that_shows_only_line_is_left_out_of_the_palette(tmp_path):
    """A reference can show HOW a line is drawn and nothing about colour (a white line drawing on black): read for the
    palette it outvoted two colour references and gave a cartoon on cream a black ground. `palette: false` keeps it out."""
    (tmp_path / "style_refs").mkdir()
    _ref(tmp_path / "style_refs" / "colour.png")
    _ref(tmp_path / "style_refs" / "line.png", ground=(0, 0, 0), blobs=((0, 0, 0), (0, 0, 0)), ink=(255, 255, 255))
    _ref(tmp_path / "style_refs" / "line2.png", ground=(0, 0, 0), blobs=((0, 0, 0), (0, 0, 0)), ink=(255, 255, 255))
    refs = [{"src": "style_refs/colour.png", "from": "found"},
            {"src": "style_refs/line.png", "from": "found", "palette": False},
            {"src": "style_refs/line2.png", "from": "found", "palette": False}]
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"style": {"name": "x", "refs": refs}}, "slides": []}))
    assert dfr.main([str(tmp_path)]) == 0
    dna = json.load(open(tmp_path / "storyboard.json"))["meta"]["design_dna"]
    assert _hue(dna["bg"])[2] > 0.9, dna["bg"]
    assert dna["provenance"]["refs"] == ["colour.png"]
