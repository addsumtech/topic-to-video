"""Subject craft (spec 2026-11-06 D1): what separates a crafted, lit subject from a line drawing, measured on the hero
beat's settled frame. The user found the GPS film "lacking beauty" and the HTTPS film's subjects were line drawings
in a dark frame; no gate could tell either from a lit object."""
import json
import os
import sys

import numpy as np
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import subject_craft_qa as sc  # noqa: E402

N = 240


def _disc_mask(r=80):
    yy, xx = np.mgrid[0:N, 0:N]
    return (xx - N / 2) ** 2 + (yy - N / 2) ** 2 <= r * r


def _flat_disc():
    img = np.full((N, N, 3), 0.10)
    img[_disc_mask()] = 0.25                                  # one mid-dark tone on a dark ground
    return img


def _lit_sphere():
    yy, xx = np.mgrid[0:N, 0:N]
    dx, dy = (xx - N / 2) / 80.0, (yy - N / 2) / 80.0
    rr = np.sqrt(dx ** 2 + dy ** 2)
    m = rr <= 1
    z = np.sqrt(np.clip(1 - rr ** 2, 0, 1))
    key = np.clip(-0.5 * dx - 0.5 * dy + 0.7 * z, 0, 1)      # soft key from the upper left
    spec = np.clip((key - 0.9) * 10, 0, 1)                    # a small highlight
    rim = np.clip((rr - 0.85) / 0.15, 0, 1) * 0.9             # rim light along the silhouette
    lum = np.clip(0.08 + 0.45 * key + spec * 0.4 + rim, 0, 1)
    img = np.full((N, N, 3), 0.10)
    for c in range(3):
        img[..., c][m] = lum[m]
    return img


def test_a_lit_sphere_beats_a_flat_disc_on_every_measure():
    lit = sc.measure(_lit_sphere(), _disc_mask())
    flat = sc.measure(_flat_disc(), _disc_mask())
    assert lit["lum_range"] > flat["lum_range"] + 0.3
    assert lit["rim_sep"] > flat["rim_sep"] + 0.2
    assert lit["highlight"] > flat["highlight"] + 0.2
    assert lit["detail"] > flat["detail"]
    assert flat["flat_share"] > 0.9 > lit["flat_share"]


def test_an_empty_mask_is_refused():
    import pytest
    with pytest.raises(ValueError):
        sc.measure(_flat_disc(), np.zeros((N, N), bool))


def test_mask_from_box_keeps_the_subject_not_the_ground():
    img = _flat_disc()
    m = sc.mask_from_box(img, (30, 30, 210, 210))         # the disc spans 40..200
    assert m.sum() > 0.9 * _disc_mask().sum() and not m[35, 35]


def _film(tmp_path, slides, meta=None):
    d = tmp_path / "f"
    (d / "_proof").mkdir(parents=True)
    (d / "storyboard.json").write_text(json.dumps({"meta": dict({"renderer": "remotion"}, **(meta or {})),
                                                   "slides": slides}))
    Image.fromarray((_lit_sphere() * 255).astype(np.uint8)).resize((480, 270)).save(d / "_proof" / "beat_01.png")
    return str(d)


def test_a_hero_with_no_subject_location_is_not_measured_and_fails(tmp_path, capsys):
    d = _film(tmp_path, [{"index": 1, "shot": "S"}], {"hero_moments": [1]})
    assert sc.main([d]) == 1
    assert "NOT MEASURED" in capsys.readouterr().out


def test_a_hero_located_by_its_sketch_is_measured(tmp_path, capsys):
    sk = {"hero": "ball", "layout": [{"name": "ball", "rect": [0.3, 0.1, 0.4, 0.8], "hero": True}]}
    d = _film(tmp_path, [{"index": 1, "shot": "S", "sketch": sk}], {"hero_moments": [1]})
    sc.main([d])
    out = capsys.readouterr().out
    assert "beat 1" in out and "lum_range" in out and "NOT MEASURED" not in out


def test_no_hero_moments_measures_nothing_and_says_so(tmp_path, capsys):
    d = _film(tmp_path, [{"index": 1, "shot": "S"}])
    assert sc.main([d]) == 0
    assert "no hero" in capsys.readouterr().out.lower()


def test_a_box_given_on_the_command_line_locates_an_old_films_subject(tmp_path, capsys):
    d = _film(tmp_path, [{"index": 1, "shot": "S"}])
    sc.main([d, "--beat", "1", "--box", "0.3,0.1,0.4,0.8"])
    assert "lum_range" in capsys.readouterr().out
