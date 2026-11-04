"""runtime/blenderPlate under a workshop shot, rendered by Remotion: the plate's alpha shows the shot's own ground,
and its anchors land where Blender projected them, at the film's own frame size."""
import json
import os
import shutil
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import blender_plate as bp  # noqa: E402
from test_blender_plate import GOOD, make_film  # noqa: E402

REMOTION_OK = os.path.isdir(os.path.join(ROOT, "remotion", "node_modules"))
needs_both = pytest.mark.skipif(bp.blender_bin() is None or not REMOTION_OK, reason="needs Blender and remotion/")
GROUND = (0x20, 0x40, 0x60)


def make_plate_film(tmp_path, monkeypatch, w, h, aspect=None):
    film = make_film(tmp_path, dict(GOOD, anchors=["top"], objects=["cube"]))
    shutil.copyfile(os.path.join(ROOT, "tests/fixtures/blender/cube_scene.py"), film + "/blender/s.py")
    shutil.copyfile(os.path.join(ROOT, "tests/fixtures/blender_film/PlateProbe.tsx"), film + "/workshop/shots/PlateProbe.tsx")
    if aspect:
        b = json.load(open(film + "/storyboard.json"))
        b["meta"]["aspect"] = aspect
        json.dump(b, open(film + "/storyboard.json", "w"), ensure_ascii=False)
    monkeypatch.setattr(bp, "_frame_facts", lambda out_dir, board, i: (4, 30, w, h))
    assert bp.build(film)[0]["state"] == "built"
    return film


def near(a, b, tol=24):
    return all(abs(x - y) <= tol for x, y in zip(a[:3], b[:3]))


def still(film, frame, props=None, aspect=None):
    import workshop
    return Image.open(workshop.still(film, "PlateProbe", props or {}, frame=frame, aspect=aspect)).convert("RGB")


def anchor(film, f):
    return json.load(open(os.path.join(bp.plate_dir(film, "sat"), "anchors.json")))["anchors"]["top"][f]


@needs_both
def test_plate_composites_over_the_ground(tmp_path, monkeypatch):
    film = make_plate_film(tmp_path, monkeypatch, 480, 270)
    im = still(film, 2)
    W, H = im.size
    assert near(im.getpixel((8, 8)), GROUND)                          # the plate's transparent corner shows the ground
    assert not near(im.getpixel((W // 2, H // 2)), GROUND)            # the cube is drawn over it
    x, y = anchor(film, 2)[:2]
    k = W / 480
    assert near(im.getpixel((round(x * k), round(y * k))), (255, 0, 255), tol=40)


@needs_both
def test_plate_scales_to_frame(tmp_path, monkeypatch):
    film = make_plate_film(tmp_path, monkeypatch, 270, 480, aspect="9:16")
    im = still(film, 1, aspect="9:16")
    W, H = im.size
    assert H > W
    x, y = anchor(film, 1)[:2]
    k = W / 270
    assert near(im.getpixel((round(x * k), round(y * k))), (255, 0, 255), tol=40)
