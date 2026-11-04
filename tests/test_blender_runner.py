"""blender/runner.py — the Blender side of a plate, run by real Blender: per frame an RGBA render, a flat ID pass at
half size, the named anchors projected to pixels, and the camera. Skipped where Blender is not installed."""
import json
import os
import subprocess
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import blender_plate as bp  # noqa: E402

BLENDER = bp.blender_bin()
needs_blender = pytest.mark.skipif(BLENDER is None, reason="no Blender for the plate runner")
SCENE = os.path.join(ROOT, "tests", "fixtures", "blender", "cube_scene.py")


def run_fixture(tmp_path, frames=3, w=160, h=90, anchors="top,far", objects="cube", extra=(), check=True):
    out = tmp_path / "run"
    cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python",
           os.path.join(ROOT, "blender", "runner.py"), "--", "--scene", SCENE, "--out", str(out),
           "--frames", str(frames), "--fps", "30", "--w", str(w), "--h", str(h), "--engine", "eevee",
           "--mode", "rgba", "--cues", "{}", "--anchors", anchors, "--objects", objects, *extra]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if check:
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return out if check else r


@needs_blender
def test_runner_writes_the_contract(tmp_path):
    out = run_fixture(tmp_path)
    assert sorted(os.listdir(out / "rgba")) == ["0001.png", "0002.png", "0003.png"]
    im = Image.open(out / "rgba/0002.png")
    assert im.mode == "RGBA" and im.size == (160, 90)
    assert im.getextrema()[3][0] == 0                                 # transparent somewhere
    assert im.getpixel((80, 45))[3] == 255                            # the cube in the middle is opaque
    ids = Image.open(out / "ids/0002.png").convert("RGB")
    assert ids.size == (80, 45)
    run = json.load(open(out / "run.json"))
    want = tuple(int(run["ids"]["cube"][i:i + 2], 16) for i in (1, 3, 5))
    assert all(abs(a - b) <= 8 for a, b in zip(ids.getpixel((40, 22)), want))
    a = json.load(open(out / "anchors.json"))
    assert (a["w"], a["h"], a["fps"], a["frames"]) == (160, 90, 30, 3)
    top = a["anchors"]["top"][0]
    assert len(a["anchors"]["top"]) == 3 and top[3] is True and 40 < top[0] < 120 and 0 < top[1] < 45
    cam = json.load(open(out / "camera.json"))
    assert len(cam["frames"]) == 3 and len(cam["frames"][0]["matrix_world"]) == 16


@needs_blender
def test_offscreen_anchor_is_not_visible(tmp_path):
    out = run_fixture(tmp_path, frames=1)
    assert json.load(open(out / "anchors.json"))["anchors"]["far"][0][3] is False


@needs_blender
def test_portrait_frame_size(tmp_path):
    out = run_fixture(tmp_path, frames=1, w=90, h=160)
    assert Image.open(out / "rgba/0001.png").size == (90, 160)
    assert Image.open(out / "ids/0001.png").size == (45, 80)


@needs_blender
def test_resume_skips_done_frames(tmp_path):
    out = run_fixture(tmp_path, frames=2)
    before = {f: os.path.getmtime(out / "rgba" / f) for f in ("0001.png", "0002.png")}
    run_fixture(tmp_path, frames=3)
    assert {f: os.path.getmtime(out / "rgba" / f) for f in before} == before
    assert (out / "rgba/0003.png").exists()


@needs_blender
def test_unknown_anchor_fails_loudly(tmp_path):
    r = run_fixture(tmp_path, frames=1, anchors="top,nosuch", check=False)
    assert r.returncode != 0 and "nosuch" in (r.stdout + r.stderr)


@needs_blender
def test_still_writes_one_frame_only(tmp_path):
    out = run_fixture(tmp_path, frames=3, extra=("--still", "2"))
    assert os.path.exists(out / "still_0002.png") and not os.path.exists(out / "rgba")


@needs_blender
def test_a_scene_imports_its_sibling_helper(tmp_path):
    d = tmp_path / "scenes"
    d.mkdir()
    (d / "helper.py").write_text("SIZE = 0.8\n")
    (d / "uses_helper.py").write_text(open(SCENE).read().replace(
        "import bpy\n", "import bpy\n\nimport helper\n").replace("primitive_cube_add(size=1.0)", "primitive_cube_add(size=helper.SIZE)"))
    out = tmp_path / "run"
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python",
                        os.path.join(ROOT, "blender", "runner.py"), "--", "--scene", str(d / "uses_helper.py"), "--out", str(out),
                        "--frames", "1", "--fps", "30", "--w", "64", "--h", "36", "--anchors", "top", "--objects", "cube"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]


@needs_blender
def test_a_computed_anchor_is_taken_as_projected(tmp_path):
    out = run_fixture(tmp_path, frames=2, anchors="top,corner")
    assert json.load(open(out / "anchors.json"))["anchors"]["corner"] == [[40.0, 67.5, 1.0, True]] * 2
