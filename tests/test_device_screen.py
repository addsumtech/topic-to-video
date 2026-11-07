"""A device's screen plays the product's own interface, in Blender.

The WorkBuddy film's interface beats were the app rebuilt in DOM and tilted a few degrees — "2D mostly", in the user's
words (2026-11-07). The spike that answered it: the beat's own shot rendered frame by frame at the screen's pixels
(`holdFrames`: on the beat's clock), played as the texture of a MacBook built to its published dimensions, lit by a
real studio (an HDRI) on a seamless sweep, the camera pushing from the whole machine in to the part the voice is
about. `slide.blender.screen` names the shot; the plate build renders it first and keys the plate on it.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, _ROOT)

import blender_plate as bp                                         # noqa: E402
from test_blender_plate import make_film, _facts, _fake_runner      # noqa: E402

SCREEN = {"shot": "PlateProbe", "props": {"state": "plan"}, "px": [2560, 1664]}
DEVICE = {"id": "plan-3d", "scene": "kit:laptop_screen", "why": "device", "engine": "cycles", "screen": SCREEN}


def _spec(film):
    return bp.spec_of(json.load(open(film + "/storyboard.json"))["slides"][0], film)


def _film(tmp_path, blender):
    """make_film's one-beat film, its probe shot a real one (a shot declares its DURATION)."""
    film = make_film(tmp_path, blender)
    with open(os.path.join(film, "workshop", "shots", "PlateProbe.tsx"), "w") as fh:
        fh.write("export const DURATION = 60;\nexport const PlateProbe = () => null;\n")
    return film


# ── the board contract ────────────────────────────────────────────────────────────────────────────────────────
def test_a_device_plate_takes_a_kit_scene_and_a_screen(tmp_path):
    s = _spec(make_film(tmp_path, DEVICE))
    assert s["scene"] == "kit:laptop_screen" and s["why"] == "device"
    assert s["screen"] == {"shot": "PlateProbe", "props": {"state": "plan"}, "px": [2560, 1664]}
    assert s["params"] == {}


def test_a_device_needs_its_screen(tmp_path):
    with pytest.raises(bp.PlateError, match="needs a screen"):
        _spec(make_film(tmp_path, {k: v for k, v in DEVICE.items() if k != "screen"}))


@pytest.mark.parametrize("screen,word", [
    (dict(SCREEN, shot="NoSuchShot"), "shot"),
    (dict(SCREEN, px=[64, 40]), "px"),                      # too few pixels to be read on any screen
    (dict(SCREEN, px=[2560]), "px"),
    (dict(SCREEN, px=[20000, 9000]), "px"),
    (dict(SCREEN, props="state=plan"), "props"),
])
def test_a_bad_screen_is_refused_by_name(tmp_path, screen, word):
    with pytest.raises(bp.PlateError, match=word):
        _spec(make_film(tmp_path, dict(DEVICE, screen=screen)))


def test_a_library_register_can_be_the_screen(tmp_path):
    assert _spec(make_film(tmp_path, dict(DEVICE, screen=dict(SCREEN, shot="ChatThread"))))["screen"]["shot"] == "ChatThread"


def test_an_unknown_kit_scene_is_refused(tmp_path):
    with pytest.raises(bp.PlateError, match="kit scene 'kit:nope'"):
        _spec(make_film(tmp_path, dict(DEVICE, scene="kit:nope")))


def test_ui_without_a_device_is_still_not_a_plate(tmp_path):
    # a flat interface is never a Blender beat; the interface ON a real device is
    with pytest.raises(bp.PlateError, match="why"):
        _spec(make_film(tmp_path, dict(DEVICE, why="ui")))


# ── the key ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_key_moves_with_what_the_screen_shows(tmp_path, monkeypatch):
    film = make_film(tmp_path, DEVICE)
    monkeypatch.setattr(bp, "screen_code", lambda out_dir, screen: "code0")
    spec = _spec(film)
    base = dict(spec=spec, out_dir=film, frames=227, fps=30, w=1920, h=1080, cue_t={}, blender_version="5.2.4")
    keys = {bp.plate_key(**base)}
    keys.add(bp.plate_key(**dict(base, spec=dict(spec, screen=dict(SCREEN, props={"state": "files"})))))
    keys.add(bp.plate_key(**dict(base, spec=dict(spec, screen=dict(SCREEN, px=[2880, 1872])))))
    keys.add(bp.plate_key(**dict(base, spec=dict(spec, params={"end_d": 2.5}))))
    monkeypatch.setattr(bp, "screen_code", lambda out_dir, screen: "code1")       # the shot's code (or the library's) changed
    keys.add(bp.plate_key(**base))
    assert len(keys) == 5


def test_the_kit_s_lighting_is_in_every_key():
    assert any(p.endswith(".hdr") for p in bp.kit_files()), "the studio HDRI lights every device plate"


# ── the build renders the screen first ────────────────────────────────────────────────────────────────────────
def test_the_screen_is_rendered_at_its_pixels_on_the_beat_s_clock(tmp_path, monkeypatch):
    film = _film(tmp_path, DEVICE)
    cmd, kw, props = bp.screen_command(film, _spec(film), 227, str(tmp_path / "seq"))
    assert cmd[:4] == ["npx", "remotion", "render", "src/index.ts"] and cmd[4] == "PlateProbe"
    assert "--sequence" in cmd and "--image-format=png" in cmd
    assert "--width=2560" in cmd and "--height=1664" in cmd
    assert props["holdFrames"] == 227 and props["state"] == "plan"
    assert kw.get("env", {}).get("SLIDES_WORKSHOP", "").endswith("workshop")


def _fake_screen(calls):
    def render(out_dir, spec, frames, dest):
        calls.append(dest)
        os.makedirs(dest, exist_ok=True)
        for i in range(frames):
            Image.new("RGB", (8, 6), (255, 255, 255)).save(os.path.join(dest, "element-%03d.png" % i))
    return render


def test_the_runner_is_handed_the_screen_and_the_params(tmp_path, monkeypatch):
    film = _film(tmp_path, dict(DEVICE, params={"end_d": 2.5}))
    _facts(monkeypatch)
    calls, seen = [], {}
    monkeypatch.setattr(bp, "render_screen", _fake_screen(calls))
    fake = _fake_runner(objects=())

    def run(cmd, log):
        a = cmd[cmd.index("--") + 1:]
        seen.update({a[i]: a[i + 1] for i in range(len(a) - 1) if a[i] in ("--screen", "--params", "--scene")})
        return fake(cmd, log)
    monkeypatch.setattr(bp, "_run_blender", run)
    bp.build(film)
    assert len(calls) == 1 and len(os.listdir(seen["--screen"])) == 4
    assert json.loads(seen["--params"]) == {"end_d": 2.5}
    assert seen["--scene"].endswith(os.path.join("blender", "kit", "scenes", "laptop_screen.py"))
    bp.build(film)
    assert len(calls) == 1, "an unchanged screen was rendered again"


def test_a_screen_magnified_past_its_pixels_is_refused(tmp_path, monkeypatch):
    # never draw a raster past its own pixels (media_res_qa's 1.25x): the camera came so close that the interface's
    # texels were stretched — the screen is rendered again at more pixels, not shipped soft
    film = make_film(tmp_path, DEVICE)
    _facts(monkeypatch)
    monkeypatch.setattr(bp, "render_screen", _fake_screen([]))
    fake = _fake_runner(objects=())

    def run(cmd, log):
        rc = fake(cmd, log)
        out = cmd[cmd.index("--out") + 1]
        r = json.load(open(out + "/run.json"))
        r["screen_mag"] = {"max": 1.62, "frame": 3}
        json.dump(r, open(out + "/run.json", "w"))
        return rc
    monkeypatch.setattr(bp, "_run_blender", run)
    with pytest.raises(bp.PlateError, match="px"):
        bp.build(film)


# ── the screen's clock ────────────────────────────────────────────────────────────────────────────────────────
def test_the_screen_frame_follows_the_beat_frame():
    from blender.kit import screenseq
    assert [screenseq.index(f, 4, 4) for f in (1, 2, 3, 4)] == [0, 1, 2, 3]
    assert [screenseq.index(f, 227, 210) for f in (1, 227)] == [0, 209]       # a sequence of another length: by time
    assert screenseq.index(300, 227, 227) == 226                              # past the end: held on the last


def test_a_texel_ratio_is_the_screen_s_drawn_width_over_its_pixels():
    from blender.kit import screenseq
    assert screenseq.magnification([(0, 0), (1000, 0), (1000, 650), (0, 650)], (2560, 1664)) == pytest.approx(1000 / 2560)
    assert screenseq.magnification([(0, 0), (3000, 0), (3000, 1950), (0, 1950)], (2560, 1664)) == pytest.approx(3000 / 2560)


# ── a real build (Blender) ────────────────────────────────────────────────────────────────────────────────────
_BLENDER = None
try:
    _BLENDER = bp.require_blender({})
except Exception:                                   # noqa: BLE001
    pass


@pytest.mark.skipif(_BLENDER is None, reason="needs Blender 5")
def test_the_kit_scene_renders_a_laptop_whose_screen_plays_the_sequence(tmp_path):
    seq = tmp_path / "seq"
    seq.mkdir()
    for i, c in enumerate(((255, 0, 0), (0, 0, 255))):
        Image.new("RGB", (256, 166), c).save(seq / ("element-%03d.png" % i))
    out = tmp_path / "out"
    cmd = [_BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", bp.RUNNER, "--",
           "--scene", os.path.join(_ROOT, "blender", "kit", "scenes", "laptop_screen.py"), "--out", str(out),
           "--frames", "2", "--fps", "30", "--w", "160", "--h", "90", "--engine", "eevee", "--mode", "env",
           "--samples", "4", "--screen", str(seq), "--params", json.dumps({"start_d": 6.6, "end_d": 6.6})]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    a, b = (Image.open(out / "rgba" / ("%04d.png" % f)).convert("RGB") for f in (1, 2))
    reds = [sum(1 for p in im.getdata() if p[0] > 150 and p[2] < 90) for im in (a, b)]
    blues = [sum(1 for p in im.getdata() if p[2] > 150 and p[0] < 90) for im in (a, b)]
    assert reds[0] > 50 and blues[1] > 50 and reds[1] < reds[0] // 5, (reds, blues)   # frame 1 shows red, frame 2 blue
    run = json.load(open(out / "run.json"))
    assert 0 < run["screen_mag"]["max"] < 1.25
    assert run.get("reuse_off"), "a screen that changes every frame cannot reuse frames"


def test_the_screen_is_rendered_into_a_folder_whose_name_has_no_extension(tmp_path, monkeypatch):
    # Remotion reads `--sequence <out>` with an extension (`screen.part`) as a FILE and refuses the render: the first
    # real build (WorkBuddy beat 6, 2026-11-07) drew 0 of 227 pictures
    film = _film(tmp_path, DEVICE)
    seen = {}

    def run(cmd, capture_output=True, text=True, **kw):
        seen["out"] = cmd[5]
        os.makedirs(cmd[5], exist_ok=True)
        for i in range(3):
            Image.new("RGB", (8, 6)).save(os.path.join(cmd[5], "element-%03d.png" % i))
        return subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(bp.subprocess, "run", run)
    dest = str(tmp_path / "plate" / "screen")
    os.makedirs(os.path.dirname(dest))
    bp.render_screen(film, _spec(film), 3, dest)
    assert "." not in os.path.basename(seen["out"]), seen["out"]
    assert len(os.listdir(dest)) == 3
