"""A real photograph's own outlines, computed (scripts/photo_lines.py) — what PhotoToDiagram draws on over the photo.

WHY. The skill's evidence registers show a real photograph and point at it; nothing could carry the viewer from
"this is real" to "this is how it works" in one picture. The outlines here are the photograph's own edges — not a
drawing anyone made up — so the diagram the beat ends on is exactly the thing the photograph showed.
"""
import os
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import photo_lines as pl  # noqa: E402


def _square(tmp_path, name="sq.png", size=(400, 300)):
    im = Image.new("RGB", size, (30, 30, 30))
    ImageDraw.Draw(im).rectangle([100, 80, 300, 220], fill=(220, 220, 220))
    p = tmp_path / name
    im.save(p)
    return p


def test_the_lines_are_the_photographs_own_edges(tmp_path):
    src = _square(tmp_path)
    out = pl.lines(str(src), str(tmp_path / "sq.lines.png"))
    a = np.asarray(Image.open(out).convert("RGBA"))[:, :, 3].astype(float)
    assert a.shape == (300, 400), "the line layer has the photograph's own pixel size"
    on = a > 128
    edge = np.zeros_like(on)
    edge[76:85, 96:305] = edge[216:225, 96:305] = True
    edge[76:225, 96:105] = edge[76:225, 296:305] = True
    # the WHOLE outline is traced: every column of the top and bottom edges, every row of the sides, has ink in its band
    cover = [on[76:85, 105:296].any(0).mean(), on[216:225, 105:296].any(0).mean(),
             on[85:216, 96:105].any(1).mean(), on[85:216, 296:305].any(1).mean()]
    assert min(cover) > 0.95, cover
    assert on[~edge].mean() < 0.01, "nothing is drawn where the photograph has no edge"


def test_a_flat_photograph_has_no_lines_and_says_so(tmp_path):
    p = tmp_path / "flat.png"
    Image.new("RGB", (200, 200), (120, 120, 120)).save(p)
    with pytest.raises(RuntimeError, match="no outlines"):
        pl.lines(str(p), str(tmp_path / "flat.lines.png"))


def test_the_lines_are_cached_by_the_photographs_content(tmp_path):
    src = _square(tmp_path)
    dst = tmp_path / "sq.lines.png"
    pl.ensure(str(src), str(dst))
    m1 = os.path.getmtime(dst)
    pl.ensure(str(src), str(dst))
    assert os.path.getmtime(dst) == m1, "an unchanged photograph is not traced again"
    im = Image.open(src)
    ImageDraw.Draw(im).ellipse([20, 20, 80, 80], fill=(250, 250, 250))
    im.save(src)
    pl.ensure(str(src), str(dst))
    a = np.asarray(Image.open(dst).convert("RGBA"))[:, :, 3]
    assert a[18:83, 18:83].max() > 128, "a changed photograph is traced again"


def test_the_render_traces_a_diagram_beat_photograph_and_fills_its_size(tmp_path):
    import render_remotion as rr
    (tmp_path / "media").mkdir()
    _square(tmp_path / "media", "p.png")
    out = rr.photo_diagram_props({"src": "media/p.png", "marks": []}, str(tmp_path))
    assert out["lines"] == "media/p.lines.png" and (tmp_path / "media" / "p.lines.png").exists()
    assert out["imageW"] == 400 and out["imageAspect"] == pytest.approx(400 / 300, abs=1e-3)
    with pytest.raises(RuntimeError, match="does not exist"):
        rr.photo_diagram_props({"src": "media/missing.png"}, str(tmp_path))
