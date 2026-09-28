"""A device's screen can show something the FILM drew — an interface that does not exist yet, a scene — through
the object slot. Its taps land on coordinates; what needs a screenshot (a text target, typing, scrolling) is
refused by name, because there is no screenshot to find text in or to scroll."""
import os
import sys

import numpy as np
import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import device_script as ds  # noqa: E402
import workshop as ws  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

PHONE_UI = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {provenance: 'product-ui'};
export const %(name)s: React.FC<ObjectProps> = ({w, h}) => (
  <div style={{width: w, height: h, background: '#ff00ff'}} />
);
"""
SCREEN = {"object": {"id": "WsPhoneUi"}}


def test_an_object_screen_is_a_screen():
    props = {"device": "phone", "steps": [{"screen": SCREEN}, {"tap": [0.5, 0.5]},
                                          {"drag": {"from": [0.2, 0.8], "to": [0.2, 0.3]}}]}
    assert ds.check_shape(props) == []
    assert ds._hero_screen_problems({"screen": SCREEN}) == []


@pytest.mark.parametrize("steps,expect", [
    ([{"screen": {"object": "WsPhoneUi"}}], "a screen's object is {\"id\""),
    ([{"screen": SCREEN}, {"type": "你好", "into": [0.5, 0.2]}], "animate the typing inside the object"),
    ([{"screen": SCREEN}, {"scroll": 0.5}], "animate the scroll inside the object"),
    ([{"screen": SCREEN}, {"tap": {"text": "发送"}}], "on a film-drawn screen, target [x, y]"),
    ([{"screen": {"image": "a.png", "object": {"id": "WsPhoneUi"}}}], "exactly one of image / video / object / page"),
])
def test_what_an_object_screen_cannot_do_is_refused_by_name(steps, expect):
    probs = ds.check_shape({"device": "phone", "steps": steps})
    assert any(expect in p for p in probs), probs


def test_a_hero_object_screen_is_refused_when_malformed_and_passes_through_prepare(tmp_path):
    assert ds._hero_screen_problems({"screen": {"object": {"props": {}}}})
    out, warns = ds.prepare({"device": "laptop", "screen": {"object": {"id": "WsPhoneUi", "props": {"tone": 1}}}},
                            shot="DeviceHero", out_dir=str(tmp_path), dur_frames=150, fps=30, W=1920, H=1080,
                            lang="zh")
    assert out["screen"] == {"object": {"id": "WsPhoneUi", "props": {"tone": 1}}} and warns == []


def test_a_demo_object_screen_is_scheduled_and_the_camera_holds(tmp_path):
    props = {"device": "phone", "steps": [{"screen": SCREEN}, {"tap": [0.5, 0.5], "at": 0.5}]}
    out, _w = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=30, W=1920, H=1080,
                         lang="zh")
    assert all({"t0", "ta", "t1"} <= set(st) for st in out["steps"])
    assert "focus" not in out["steps"][1]              # nothing to measure a push-in against


def test_validate_names_an_unknown_object_on_a_device_screen(tmp_path):
    import validate as v
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "DeviceHero", "narration": "这就是它。", "audio": "audio/01.mp3",
                         "duration": 3.0, "shot_props": {"device": "laptop", "screen": {"object": {"id": "NoSuchUi"}}}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    assert any("names object 'NoSuchUi'" in e for e in errs), errs


@needs_toolchain
def test_a_film_drawn_screen_shows_on_the_phone_and_on_the_laptop(tmp_path):
    out = tmp_path / "film"
    d = out / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "WsPhoneUi.tsx").write_text(PHONE_UI % {"name": "WsPhoneUi"}, encoding="utf-8")
    ws.write_index(str(out))
    env = _env(ws.workshop_dir(str(out)))
    demo, _w = ds.prepare({"device": "phone", "steps": [{"screen": SCREEN}, {"tap": [0.5, 0.5]}]}, shot="DeviceDemo",
                          out_dir=str(out), dur_frames=180, fps=30, W=1920, H=1080, lang="zh")
    for comp, props, frame in (("DeviceDemo", demo, 150),
                               ("DeviceHero", {"device": "laptop", "screen": SCREEN}, 130)):
        png = tmp_path / (comp + ".png")
        r = _still(comp, png, dict(props, dna="product"), env, frame=frame)
        assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
        a = np.asarray(Image.open(str(png)).convert("RGB")).astype(int)
        magenta = int(((a[..., 0] > 200) & (a[..., 1] < 60) & (a[..., 2] > 200)).sum())
        assert magenta > a.shape[0] * a.shape[1] * 0.03, (comp, magenta)
