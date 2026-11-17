"""scripts/cutout.py cuts one shape out of a plain background by flood fill from the edge: white INSIDE the shape
(a Bot's eyes) stays, the background goes, and a shape cut off by the picture's edge is refused."""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import cutout  # noqa: E402

CLI = [sys.executable, os.path.join(ROOT, "scripts", "cutout.py")]


def _bot(w=240, h=200, at=(40, 30, 200, 170)):
    im = Image.new("RGB", (w, h), (252, 252, 252)); d = ImageDraw.Draw(im)
    d.ellipse(at, fill=(0, 198, 106))
    d.rectangle((95, 70, 110, 120), fill=(255, 255, 255)); d.rectangle((130, 70, 145, 120), fill=(255, 255, 255))
    return im


def test_white_eyes_inside_the_shape_stay_and_the_background_goes():
    out = cutout.cutout(_bot(), pad=6)
    a = out.getchannel("A")
    assert a.getpixel((0, 0)) == 0                                     # background gone
    # the eye (white, enclosed by the green body) is still opaque white
    ex, ey = 100 - 40 + 6, 95 - 30 + 6
    assert a.getpixel((ex, ey)) == 255 and out.getpixel((ex, ey))[:3] == (255, 255, 255)
    assert out.size == (160 + 1 + 12, 140 + 1 + 12)                    # trimmed to the shape + pad


def test_a_shape_cut_by_the_edge_is_refused(tmp_path):
    _bot(at=(-20, 30, 140, 170)).save(tmp_path / "cut.png")
    r = subprocess.run(CLI + [str(tmp_path / "cut.png"), str(tmp_path / "o.png")], capture_output=True, text=True)
    assert r.returncode == 1 and "touches the edge" in r.stderr
    assert not (tmp_path / "o.png").exists()


def test_box_and_usage(tmp_path):
    big = Image.new("RGB", (600, 400), (252, 252, 252)); big.paste(_bot(), (300, 100)); big.save(tmp_path / "b.png")
    r = subprocess.run(CLI + [str(tmp_path / "b.png"), str(tmp_path / "o.png"), "--box", "320,110,220,180"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert Image.open(tmp_path / "o.png").getchannel("A").getpixel((0, 0)) == 0
    assert subprocess.run(CLI + [str(tmp_path / "b.png")], capture_output=True).returncode == 2
    assert subprocess.run(CLI + [str(tmp_path / "b.png"), "o.png", "--box", "a,b"], capture_output=True).returncode == 2
    assert subprocess.run(CLI + [str(tmp_path / "b.png"), "o.png", "--nope"], capture_output=True).returncode == 2
