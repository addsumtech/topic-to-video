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
    spec = {"shots": [{"kind": "brand", "dur": 80, "mark": "mark.svg", "aspect": 1}, {"kind": "title", "dur": 56, "text": "One *idea.*"}, page(),
                      {"kind": "outro", "dur": 120, "mark": "mark.svg", "aspect": 1, "recall": [2]}]}
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
    (page(layers=[{"kind": "sparkles", "at": 3}]), "unknown layer"),
    (page(cut="wipe"), "cut must be"),
])

def test_defects_stop_the_render_by_name(film, bad, words):
    errs, _ = pf.check({"shots": [bad]}, str(film))
    assert any(words in e for e in errs), errs


def test_outro_recalls_page_shots_only(film):
    errs, _ = pf.check({"shots": [{"kind": "title", "dur": 56, "text": "x"},
                                  {"kind": "outro", "dur": 120, "mark": "mark.svg", "aspect": 1, "recall": [0]}]}, str(film))
    assert any("recall" in e for e in errs) and any("there are none" in e for e in errs)


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
        {"kind": "outro", "dur": 120, "mark": "m.svg", "aspect": 1, "stampAt": 40}]}
    cues = pf.plan_sfx(spec)
    names = [c for _, c, _ in cues]
    # every carried cut is one air sound ON the cut; the camera travels 60 px and 0.6 zoom in 40 frames: one whoosh
    # at the move's middle
    assert (50, "whoosh") in [(f, c) for f, c, _ in cues] and (50 + 90, "whoosh") in [(f, c) for f, c, _ in cues]
    assert (50 + 20, "whoosh") in [(f, c) for f, c, _ in cues]
    # pops one frame apart are ONE sound; 5 frames apart, two
    assert names.count("drop") == 2
    assert [f for f, c, _ in cues if c == "key"] == [50 + 20, 50 + 22]
    assert (50 + 62, "click") in [(f, c) for f, c, _ in cues]
    # the close: light swells under the recalled wall and the impact lands as the lockup forms — no synthesised bell
    o = 50 + 90
    assert [(f, c) for f, c, _ in cues if c in ("swell", "impact")] == [(o + 6, "swell"), (o + 40 + 10, "impact")]
    assert not {"reveal", "chime", "sparkle", "tick", "pop"} & set(names), "a synthesised tone in the promo's sound"
    assert all(c in pf.BANK or c in ("whoosh", "swell", "impact") for c in names), names
    # a film cut hard has no air on its cuts
    hard = pf.plan_sfx(dict(spec, cut="hard"))
    assert (50, "whoosh") not in [(f, c) for f, c, _ in hard]
    assert cues == sorted(cues)


@pytest.mark.parametrize("accent", ["#ffd400", "#57bf9c", "#6965db", "#e8452c", "#111111", "#ffffff"])
@pytest.mark.parametrize("mode", ["light", "dark"])
def test_a_look_derived_from_any_accent_keeps_its_type_legible(accent, mode):
    look = pf.derive_look({"accent": accent, "mode": mode})
    assert pf._contrast(look["accentInk"], look["paper"]) >= 4.5
    assert pf._contrast(look["ink"], look["paper"]) >= 7
    assert look["accent"] == accent and "mode" not in look
    assert (pf._contrast(look["paper"], "#000000") < 7) == (mode == "dark")


def test_given_look_fields_win(film):
    look = pf.derive_look({"accent": "#57bf9c", "paper": "#f6f5f1", "accentInk": "#137a5a"})
    assert look["paper"] == "#f6f5f1" and look["accentInk"] == "#137a5a"


def test_aspect_table_matches_the_compositions():
    import re
    root = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "Root.tsx"), encoding="utf-8").read()
    ts = dict((k, (int(a), int(b))) for k, a, b in re.findall(r"'(\d+:\d+)': \[(\d+), (\d+)\]", root.split("const ASPECTS")[1].split("};")[0]))
    assert ts == pf.ASPECTS


def test_zoom_cap_is_on_effective_density(film):
    # zoom 3 on a 1920 reference is 1.69 px/CSS px on a 1080-wide 9:16 frame: inside a 2x capture's density
    tall = {"aspect": "9:16", "shots": [page(keys=[{"f": 0, "cx": 200, "cy": 150, "zoom": 3.0}])]}
    assert pf.check(tall, str(film))[0] == []
    wide = {"shots": [page(keys=[{"f": 0, "cx": 200, "cy": 150, "zoom": 3.0}])]}
    assert any("density" in e for e in pf.check(wide, str(film))[0])


def test_the_page_camera_keeps_its_stillness_rules():
    """The four things that made a page step or shimmer (picture_glide_qa measures the result; these pin the causes):
    laid out once and moved by one transform, the raster pinned across render tabs, creeping segments collapsed into
    holds, landings with linear deceleration."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src", "promo", "PageCam.tsx"),
               encoding="utf-8").read()
    assert "willChange: 'transform'" in src
    assert "zoom: raster" in src and "scale3d(${s}, ${s}, 1)" in src
    assert "const CREEP = 8;" in src and "if (peak < CREEP)" in src
    assert "Math.cos(Math.PI * Math.pow(" in src          # the sine-bump landing
    assert "Math.exp(-(rx * rx + ry * ry + rz * rz) / 18)" in src   # containment smooth in the tilt


def test_a_close_up_past_the_density_needs_a_macro_under_it(film):
    from PIL import Image
    Image.new("RGB", (400, 160), "white").save(film / "hi.png")          # a 4x capture of a 100x40 element
    deep = [{"f": 0, "cx": 200, "cy": 150, "zoom": 1.2}, {"f": 40, "cx": 60, "cy": 30, "zoom": 3.6}]
    errs, _ = pf.check({"shots": [page(keys=deep, layers=[])]}, str(film))
    assert any("macro" in e for e in errs), errs
    macro = {"kind": "macro", "box": {"x": 10, "y": 10, "w": 100, "h": 40}, "src": "hi.png", "scale": 4}
    errs, _ = pf.check({"shots": [page(keys=deep, layers=[macro])]}, str(film))
    assert errs == [], errs
    off = [{"f": 0, "cx": 200, "cy": 150, "zoom": 3.6}]                  # pushed past 2x somewhere the macro is NOT
    assert any("macro" in e for e in pf.check({"shots": [page(keys=off, layers=[macro])]}, str(film))[0])
    wrong = dict(macro, box={"x": 10, "y": 10, "w": 120, "h": 40})        # a capture that is not its box at 4x
    assert any("stretched" in e for e in pf.check({"shots": [page(layers=[wrong])]}, str(film))[0])


def test_every_recorded_take_exists_and_is_licensed():
    import wave
    for name, takes in pf.BANK.items():
        for t in takes:
            p = os.path.join(pf._KENNEY, t + ".wav")
            with wave.open(p, "rb") as w:
                assert w.getnframes() > 0, p
    lic = open(os.path.join(pf._KENNEY, "LICENSE.txt"), encoding="utf-8").read()
    assert "CC0" in lic
