"""picture_glide_qa separates a glide from a whole-pixel staircase, and reads a promo film's page shots as its spans."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import picture_glide_qa as pg  # noqa: E402


def test_the_instrument_separates_a_glide_from_a_staircase(capsys):
    assert pg.calibrate() == 0, capsys.readouterr().out


def test_promo_spans_are_the_page_shots_inside_their_cuts(tmp_path):
    (tmp_path / "promo.json").write_text(json.dumps({"shots": [
        {"kind": "brand", "dur": 80}, {"kind": "page", "dur": 100}, {"kind": "title", "dur": 50}, {"kind": "page", "dur": 60}]}))
    assert pg.spans_of(str(tmp_path)) == [(2, 88, 172), (4, 238, 282)]
