"""blender_plate.build end to end with real Blender and ffmpeg: a 4-frame plate of the cube fixture."""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import blender_plate as bp  # noqa: E402
from test_blender_plate import GOOD, make_film  # noqa: E402

needs_blender = pytest.mark.skipif(bp.blender_bin() is None, reason="no Blender for the plate build")


@needs_blender
def test_build_end_to_end(tmp_path, monkeypatch):
    film = make_film(tmp_path, dict(GOOD, anchors=["top"], objects=["cube"]))
    shutil.copyfile(os.path.join(ROOT, "tests/fixtures/blender/cube_scene.py"), film + "/blender/s.py")
    monkeypatch.setattr(bp, "_frame_facts", lambda out_dir, board, i: (4, 30, 160, 90))
    rep = bp.build(film)
    assert rep[0]["state"] == "built"
    pd = bp.plate_dir(film, "sat")
    probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", pd + "/plate.webm"],
                           capture_output=True, text=True).stdout.lower()
    assert "alpha_mode=1" in probe.replace("tag:", "") and "nb_read_frames=4" in probe
    boxes = json.load(open(pd + "/boxes.json"))["cube"]
    assert len(boxes) == 4 and all(b and b[0] < 80 < b[2] for b in boxes)       # the cube is mid-frame
    assert len(json.load(open(pd + "/anchors.json"))["anchors"]["top"]) == 4
    board = json.load(open(film + "/storyboard.json"))
    assert bp.plate_state(film, board, 0) == "fresh"
    assert not [d for d in os.listdir(pd) if d.startswith(".work-")]
