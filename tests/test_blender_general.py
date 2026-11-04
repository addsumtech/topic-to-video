"""Blender plates on inputs the first plate was not built around: an opaque (env) plate, the Cycles engine, an
object that leaves the frame, a point the object itself hides, two plates on one board, Latin cues."""
import json
import os
import shutil
import subprocess
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import blender_plate as bp  # noqa: E402
from test_blender_plate import GOOD, _facts, _fake_runner, make_film  # noqa: E402
from test_blender_runner import BLENDER, needs_blender  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "blender")


def _run(tmp_path, scene, frames, w=160, h=90, engine="eevee", mode="rgba", anchors="", objects=""):
    out = tmp_path / "run"
    cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", os.path.join(ROOT, "blender", "runner.py"),
           "--", "--scene", os.path.join(FIX, scene), "--out", str(out), "--frames", str(frames), "--fps", "30",
           "--w", str(w), "--h", str(h), "--engine", engine, "--mode", mode, "--cues", "{}",
           "--anchors", anchors, "--objects", objects]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    meta = json.load(open(out / "run.json"))
    bp.assemble(str(out), meta["frames"], layout=meta["layout"])     # the runner leaves full frames + patches
    return out


@needs_blender
def test_env_mode_is_opaque(tmp_path):
    out = _run(tmp_path, "cube_scene.py", 1, mode="env", objects="cube")
    assert Image.open(out / "rgba/0001.png").getextrema()[3] == (255, 255)


@needs_blender
def test_cycles_renders_on_the_gpu(tmp_path):
    out = _run(tmp_path, "cube_scene.py", 1, w=64, h=36, engine="cycles", objects="cube")
    im = Image.open(out / "rgba/0001.png")
    assert im.size == (64, 36) and im.getpixel((32, 18))[3] == 255


@needs_blender
def test_an_object_leaving_the_frame(tmp_path):
    out = _run(tmp_path, "moving_scene.py", 4, anchors="front,back", objects="mover")
    a = json.load(open(out / "anchors.json"))["anchors"]
    assert a["front"][0][3] is True and a["front"][-1][3] is False       # in frame, then out of it
    assert a["back"][0][3] is False                                       # the cube hides its own back face
    run = json.load(open(out / "run.json"))
    boxes = bp.boxes_from_ids(str(out / "ids"), run["ids"], 4)
    assert boxes["mover"][0] is not None and boxes["mover"][-1] is None


def _two_beat_film(tmp_path):
    film = make_film(tmp_path, dict(GOOD, objects=["sat"]))
    b = json.load(open(film + "/storyboard.json"))
    two = dict(b["slides"][0], index=2, blender=dict(GOOD, id="earth", cues=["broadcasts"]))
    b["slides"].append(two)
    json.dump(b, open(film + "/storyboard.json", "w"), ensure_ascii=False)
    json.dump([{"w": "the", "t": 0.2}, {"w": "satellite", "t": 0.5}, {"w": "broadcasts,", "t": 1.25}],
              open(film + "/audio/02.words.json", "w"))
    return film


def test_two_plates_and_a_cue_edit_rebuild_only_one(tmp_path, monkeypatch):
    film = _two_beat_film(tmp_path)
    _facts(monkeypatch)
    calls = []
    fake = _fake_runner()
    monkeypatch.setattr(bp, "_run_blender", lambda cmd, log: (calls.append(cmd[cmd.index("--out") + 1]), fake(cmd, log))[1])
    assert [r["state"] for r in bp.build(film)] == ["built", "built"]
    assert bp.cue_times(film, 2, ["broadcasts"]) == {"broadcasts": 1.25}          # Latin token with its comma
    ts = open(film + "/workshop/assets/plates.ts", encoding="utf-8").read()
    assert '"sat":' in ts and '"earth":' in ts
    json.dump([{"w": "the", "t": 0.2}, {"w": "satellite", "t": 0.5}, {"w": "broadcasts", "t": 1.6}],
              open(film + "/audio/02.words.json", "w"))
    calls.clear()
    reps = {r["id"]: r["state"] for r in bp.build(film)}
    assert reps == {"sat": "fresh", "earth": "built"} and len(calls) == 1 and "/earth/" in calls[0]
    assert [r["id"] for r in bp.build(film, only="sat")] == ["sat"]


def test_env_plate_encodes_opaque(tmp_path, monkeypatch):
    film = make_film(tmp_path, dict(GOOD, mode="env"))
    _facts(monkeypatch)
    monkeypatch.setattr(bp, "_run_blender", _fake_runner(objects=()))
    assert bp.build(film)[0]["state"] == "built"
    pd = bp.plate_dir(film, "sat")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", pd + "/plate.webm"], capture_output=True, text=True).stdout
    assert "alpha_mode" not in probe.lower() and json.load(open(pd + "/plate.json"))["mode"] == "env"
    assert '"mode":"env"' in open(film + "/workshop/assets/plates.ts", encoding="utf-8").read()
