"""Not rendering what did not change (blender/kit/reuse.py), the layout pass, and a key that ignores comments: what
made two short acceptance films cost 135 GPU minutes (2026-11-04). Real Blender; skipped where it is not installed."""
import json
import os
import subprocess
import sys

import pytest
from PIL import Image, ImageChops, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import blender_plate as bp  # noqa: E402

BLENDER = bp.blender_bin()
needs_blender = pytest.mark.skipif(BLENDER is None, reason="no Blender for the plate runner")
FIX = os.path.join(ROOT, "tests", "fixtures", "blender")


def run(tmp_path, scene, name, frames=6, objects="cube", anchors="", extra=()):
    out = tmp_path / name
    cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python",
           os.path.join(ROOT, "blender", "runner.py"), "--", "--scene", os.path.join(FIX, scene), "--out", str(out),
           "--frames", str(frames), "--fps", "30", "--w", "320", "--h", "180", "--engine", "eevee",
           "--mode", "rgba", "--cues", "{}", "--anchors", anchors, "--objects", objects, *extra]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    meta = json.load(open(out / "run.json"))
    bp.assemble(str(out), meta["frames"], layout=meta["layout"])
    return out, meta


def mean_diff(a, b):
    with Image.open(a) as x, Image.open(b) as y:
        return max(ImageStat.Stat(ImageChops.difference(x.convert("RGBA"), y.convert("RGBA"))).mean)


@needs_blender
def test_a_still_scene_is_rendered_once_and_copied(tmp_path):
    out, meta = run(tmp_path, "still_scene.py", "reuse", anchors="top")
    assert meta["reuse"] == {"full": 1, "copy": 5, "patch": 0} and meta["reuse_off"] is None, meta
    whole, _ = run(tmp_path, "still_scene.py", "whole", anchors="top", extra=("--no-reuse",))
    for f in (2, 6):
        assert mean_diff(out / ("rgba/%04d.png" % f), whole / ("rgba/%04d.png" % f)) < 0.5
        assert mean_diff(out / ("ids/%04d.png" % f), whole / ("ids/%04d.png" % f)) < 0.5


@needs_blender
def test_only_the_moving_objects_rectangle_is_rendered(tmp_path):
    out, meta = run(tmp_path, "patch_scene.py", "reuse", objects="mover", anchors="c")
    assert meta["reuse"]["patch"] >= 4 and meta["reuse_off"] is None, meta
    rect = next(fm["rect"] for fm in meta["frames"] if fm["kind"] == "patch")
    assert (rect[2] - rect[0]) * (rect[3] - rect[1]) < 0.5 * 320 * 180          # a part of the frame, not all of it
    whole, _ = run(tmp_path, "patch_scene.py", "whole", objects="mover", anchors="c", extra=("--no-reuse",))
    for f in range(2, 7):
        assert mean_diff(out / ("rgba/%04d.png" % f), whole / ("rgba/%04d.png" % f)) < 1.0, f
        assert mean_diff(out / ("ids/%04d.png" % f), whole / ("ids/%04d.png" % f)) < 0.5, f
    a = json.load(open(out / "anchors.json"))["anchors"]["c"]
    assert a == json.load(open(whole / "anchors.json"))["anchors"]["c"]


@needs_blender
def test_a_fading_material_is_its_object_changing(tmp_path):
    out, meta = run(tmp_path, "fade_scene.py", "fade", objects="mover", anchors="c")
    assert meta["reuse"]["patch"] >= 4 and meta["reuse_off"] is None, meta
    whole, _ = run(tmp_path, "fade_scene.py", "whole", objects="mover", anchors="c", extra=("--no-reuse",))
    for f in range(2, 7):
        assert mean_diff(out / ("rgba/%04d.png" % f), whole / ("rgba/%04d.png" % f)) < 1.0, f


@needs_blender
def test_a_change_reuse_cannot_see_turns_it_off_loudly(tmp_path):
    # the pose repaints the cube's IMAGE — no matrix, node value or vertex moves — so the first copy's verification
    # render differs, reuse goes off, and every frame is rendered whole (never a quietly frozen paint)
    out, meta = run(tmp_path, "hidden_change_scene.py", "hidden")
    assert meta["reuse_off"] and "differs" in meta["reuse_off"], meta
    assert meta["reuse"] == {"full": 6, "copy": 0, "patch": 0}, meta
    whole, _ = run(tmp_path, "hidden_change_scene.py", "whole", extra=("--no-reuse",))
    for f in range(1, 7):
        assert mean_diff(out / ("rgba/%04d.png" % f), whole / ("rgba/%04d.png" % f)) < 0.5, f


@needs_blender
def test_layout_pass_renders_no_picture(tmp_path):
    out, meta = run(tmp_path, "patch_scene.py", "layout", objects="mover", anchors="c", extra=("--layout",))
    assert meta["rendered"] == 0 and meta["layout"] is True
    # not even an upscaled copy of the ID pass: 351 of those and their VP9 encode were 48 s of an 84 s layout pass
    assert not os.path.isdir(out / "rgba") or not os.listdir(out / "rgba")
    with Image.open(out / "ids/0003.png") as ids:
        assert ids.size == (160, 90)


def test_key_ignores_comments_and_docstrings(tmp_path):
    a, b, c = tmp_path / "a.py", tmp_path / "b.py", tmp_path / "c.py"
    a.write_text('"""Doc."""\nimport bpy\n\n\ndef f(k):\n    """What f does."""\n    return k * 2\n')
    b.write_text('"""Another doc."""\n# a comment\nimport bpy\n\ndef f(k):   # here too\n    return k * 2\n')
    c.write_text('import bpy\n\n\ndef f(k):\n    return k * 3\n')
    assert bp._code_sha(str(a)) == bp._code_sha(str(b))
    assert bp._code_sha(str(a)) != bp._code_sha(str(c))


def test_layout_plates_are_refused_for_delivery(tmp_path, monkeypatch):
    from test_blender_plate import GOOD, make_film, _facts, _fake_runner
    film = make_film(tmp_path, dict(GOOD, objects=["sat"]))
    _facts(monkeypatch, frames=4, w=64, h=36)
    seen = []
    fake = _fake_runner()
    monkeypatch.setattr(bp, "_run_blender", lambda cmd, log: (seen.append(cmd), fake(cmd, log))[1])
    rep = bp.build(film, layout=True)[0]
    assert rep["state"] == "built" and "--layout" in seen[0]
    spec = bp.spec_of(json.load(open(film + "/storyboard.json"))["slides"][0], film)
    assert rep["estimate"] == round(bp.estimate_seconds(spec, 4, layout=True), 1)
    errs, _ = bp.validate_blender(json.load(open(film + "/storyboard.json")), film)
    assert any("LAYOUT" in e for e in errs), errs


def test_a_layout_plate_is_encoded_from_its_id_pass_at_the_plate_size(tmp_path):
    work = tmp_path / "work"
    (work / "ids").mkdir(parents=True)
    for i in (1, 2, 3):
        im = Image.new("RGBA", (32, 18), (0, 0, 0, 0))
        im.paste((255, 0, 0, 255), (4 * i, 4, 4 * i + 8, 12))
        im.save(work / "ids" / ("%04d.png" % i))
    dest = str(tmp_path / "plate.webm")
    bp._encode(str(work), dest, 30, "rgba", layout=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", dest], capture_output=True, text=True).stdout
    assert "width=64" in probe and "height=36" in probe and "alpha_mode=1" in probe.lower().replace("tag:", ""), probe
