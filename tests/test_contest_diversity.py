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


def test_mode_flip_always_diverges(tmp_path):
    a = str(tmp_path / "a.png"); b = str(tmp_path / "b.png")
    _frame(a, "#f4f2ed", "#222", [(60, 60, 400, 160)])
    _frame(b, "#0e0f11", "#ffb454", [(60, 60, 400, 160)])   # same layout, dark+amber
    r = cd.check([a, b])
    assert r["flagged"] == [] and r["modes"][b] == "dark"


def test_different_silhouettes_diverge(tmp_path):
    a = str(tmp_path / "a.png"); b = str(tmp_path / "b.png")
    _frame(a, "#f4f2ed", "#e2231a", [(40, 40, 600, 120)])                      # top band
    _frame(b, "#f6f3ea", "#a4231b", [(40, 200, 200, 340), (420, 200, 600, 340)])  # two bottom blocks
    r = cd.check([a, b])
    assert r["flagged"] == []
