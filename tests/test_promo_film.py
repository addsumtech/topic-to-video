"""promo_film: the shot-table check refuses what would render wrong, and the sound is pinned to the table's actions."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import promo_film as pf  # noqa: E402


@pytest.fixture
def film(tmp_path):
    from PIL import Image
    Image.new("RGB", (800, 600), "white").save(tmp_path / "page.png")    # a 2x capture: CSS 400x300
    Image.new("RGB", (64, 64), "white").save(tmp_path / "other.png")
    (tmp_path / "mark.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
    return tmp_path


def page(**kw):
    s = {"kind": "page", "dur": 90, "src": "page.png", "w": 400, "h": 300,
         "keys": [{"f": 0, "cx": 200, "cy": 150, "zoom": 1.2}, {"f": 40, "cx": 260, "cy": 150, "zoom": 1.8}],
         "layers": [{"kind": "pop", "box": {"x": 10, "y": 10, "w": 100, "h": 40}, "at": 10}]}
    s.update(kw)
    return s


def test_a_clean_table_passes(film):
    spec = {"shots": [{"kind": "brand", "dur": 80, "mark": "mark.svg", "aspect": 1}, {"kind": "title", "dur": 56, "text": "One *idea.*"}, page()]}
    errs, adv = pf.check(spec, str(film))
    assert errs == [] and adv == []


@pytest.mark.parametrize("bad, words", [
    (page(src="missing.png"), "does not exist"),
    (page(w=800, h=600), "CSS size"),                                               # the 2x pixels taken as CSS px
    (page(keys=[{"f": 0, "cx": 200, "cy": 150, "zoom": 2.6}]), "density"),             # an upsampled texture
    (page(keys=[{"f": 30, "cx": 1, "cy": 1, "zoom": 1}, {"f": 10, "cx": 1, "cy": 1, "zoom": 1}]), "out of order"),
    (page(keys=[{"f": 0, "cx": 900, "cy": 150, "zoom": 1}]), "off the capture"),
    (page(layers=[{"kind": "lift", "box": {"x": 350, "y": 10, "w": 100, "h": 40}, "at": 5, "until": 30}]), "outside"),
    (page(layers=[{"kind": "pop", "box": {"x": 10, "y": 10, "w": 20, "h": 20}, "at": 4, "src": "other.png",
                   "srcBox": {"x": 25, "y": 25, "w": 20, "h": 20}}]), "srcBox"),      # crop past the OTHER capture's edge
])
def test_defects_stop_the_render_by_name(film, bad, words):
    errs, _ = pf.check({"shots": [bad]}, str(film))
    assert any(words in e for e in errs), errs


def test_low_contrast_accent_ink_is_refused(film):
    errs, _ = pf.check({"look": {"accentInk": "#16805f", "paper": "#f6f5f1"}, "shots": [page()]}, str(film))
    assert any("4.5:1" in e for e in errs)
    errs, _ = pf.check({"look": {"accentInk": "#137a5a", "paper": "#f6f5f1"}, "shots": [page()]}, str(film))
    assert errs == []


def test_shot_lengths_outside_the_band_are_advised_not_refused(film):
    errs, adv = pf.check({"shots": [{"kind": "title", "dur": 150, "text": "x"}, page(dur=20)]}, str(film))
    assert errs == [] and len(adv) == 2


def test_sound_is_pinned_to_the_table():
    spec = {"shots": [
        {"kind": "title", "dur": 50, "text": "x"},
        page(layers=[{"kind": "pop", "box": {}, "at": 10}, {"kind": "pop", "box": {}, "at": 11}, {"kind": "pop", "box": {}, "at": 16},
                     {"kind": "type", "box": {}, "at": 20, "text": "abcd", "cpf": 1},
                     {"kind": "cursor", "path": [{"f": 50, "x": 0, "y": 0}], "clicks": [60]}]),
        {"kind": "outro", "dur": 120, "pieces": [], "mark": "m.svg", "aspect": 1, "stampAt": 40}]}
    cues = pf.plan_sfx(spec)
    names = [c for _, c, _ in cues]
    # the camera travels 60 px and 0.6 zoom in 40 frames: one whoosh, at the move's middle
    assert (50 + 20, "whoosh") in [(f, c) for f, c, _ in cues]
    # pops one frame apart are ONE sound; 5 frames apart, two
    assert names.count("pop") == 2
    assert [f for f, c, _ in cues if c == "key"] == [50 + 20, 50 + 22]
    assert (50 + 62, "click") in [(f, c) for f, c, _ in cues]
    # the outro's sentence: riser into the stamp, impact on it, sparkle after
    o = 50 + 90 + 40
    assert [(f, c) for f, c, _ in cues if c in ("riser", "impact", "sparkle")] == [(o - 2, "riser"), (o + 3, "impact"), (o + 18, "sparkle")]
    assert cues == sorted(cues)
