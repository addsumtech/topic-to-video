"""The device-fidelity checks (scripts/device_fidelity_qa.py, scripts/device_models.py, runtime/textSafe `device`):
each with a fixture that fails and one that passes."""
import json
import os
import sys

import pytest
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)

import device_models as dm          # noqa: E402
import device_fidelity_qa as fq     # noqa: E402
import device_script as ds          # noqa: E402
import _tsprobe as tp               # noqa: E402

FPS = 30


def _img(path, w, h, mode="RGB", fill="white"):
    Image.new(mode, (w, h), fill).save(str(path))
    return os.path.basename(str(path))


# ── model inference ────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("size, model, how", [
    ((416, 496), "watch-s12-46", "native"),
    ((374, 446), "watch-s12-42", "native"),
    ((1206, 2622), "iphone-18-pro", "native"),
    ((1320, 2868), "iphone-18-pro-max", "native"),
    ((402, 874), "iphone-18-pro", "1/3"),
    ((1206, 6000), "iphone-18-pro", "long"),
    ((1640, 2360), "ipad-a16", "native"),
    ((2360, 1640), "ipad-a16", "native"),
    ((2560, 1664), "macbook-air-13", "native"),
    ((1512, 982), "macbook-pro-14", "1/2"),
])
def test_a_capture_names_the_model_it_was_taken_on(size, model, how):
    assert dm.candidates(*size)[0] == (model, how)


@pytest.mark.parametrize("size", [(1170, 2532), (1000, 716), (0, 10), (417, 496), (2622, 1206)])
def test_a_size_no_model_has_names_none(size):
    assert dm.candidates(*size) == []


def test_every_model_carries_its_source_and_date():
    for name, m in dm.models().items():
        assert m["source"].startswith("https://www.apple.com/"), name
        assert m["retrieved"] and m["published"]["px"] and m["published"]["ppi"] and m["published"]["caseMm"], name
        assert m.get("derived") or m.get("design"), name


def test_the_watch_capture_is_drawn_as_its_watch(tmp_path):
    """No `device`: the hero takes the capture's model and its kind — a 416x496 is a 46 mm watch, not a laptop."""
    n = _img(tmp_path / "w.png", 416, 496)
    out, warns = ds.prepare({"screen": {"image": n}}, shot="DeviceHero", out_dir=str(tmp_path), dur_frames=150,
                            fps=FPS, W=1920, H=1080, lang="en")
    assert out["device"] == "watch" and out["model"] == "watch-s12-46", out
    assert warns == [], warns


def test_an_unknown_size_is_drawn_generic_and_said(tmp_path):
    n = _img(tmp_path / "p.png", 1170, 2532)
    out, warns = ds.prepare({"device": "phone", "screen": {"image": n}}, shot="DeviceHero", out_dir=str(tmp_path),
                            dur_frames=150, fps=FPS, W=1920, H=1080, lang="en")
    assert "model" not in out
    assert any("1170x2532" in w and "generic phone" in w for w in warns), warns


def test_a_named_model_the_capture_contradicts_is_refused(tmp_path):
    n = _img(tmp_path / "p.png", 1320, 2868)                    # a Pro Max capture
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.prepare({"device": "phone", "model": "iphone-18-pro", "screen": {"image": n}}, shot="DeviceHero",
                   out_dir=str(tmp_path), dur_frames=150, fps=FPS, W=1920, H=1080, lang="en")
    assert "iPhone 18 Pro Max" in str(e.value)
    ok = _img(tmp_path / "q.png", 1206, 2622)
    out, _w = ds.prepare({"device": "phone", "model": "iphone-17", "screen": {"image": ok}}, shot="DeviceHero",
                         out_dir=str(tmp_path), dur_frames=150, fps=FPS, W=1920, H=1080, lang="en")
    assert out["model"] == "iphone-17"                          # same pixels as the 18 Pro: the author's choice


def test_a_model_of_another_kind_is_refused_by_name():
    probs = ds.check_shape({"device": "phone", "model": "watch-s12-46", "steps": [{"screen": {"image": "a.png"}}]})
    assert any("is a watch, not a phone" in p for p in probs), probs
    assert any("`model` is one of" in p for p in ds.check_shape({"model": "nokia", "steps": [{"screen": {"image": "a"}}]}))


def test_a_watch_has_no_keyboard():
    probs = ds.check_shape({"device": "watch", "steps": [{"screen": {"image": "a.png"}},
                                                         {"type": "ok", "into": [0.5, 0.5]}]})
    assert any("a watch has no keyboard" in p for p in probs), probs
    assert ds.check_shape({"device": "watch", "steps": [{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5]}]}) == []


# ── aspect: no stretch, no silent crop ─────────────────────────────────────────────────────────────────────────

def test_a_capture_a_little_off_the_screen_proportion_is_said_in_pixels():
    off = fq.aspect_findings({"w": 1170, "h": 2480}, "phone", None, "step 1")
    assert off and "empty below it" in off[0], off
    assert fq.aspect_findings({"w": 1206, "h": 2622}, "phone", "iphone-18-pro", "step 1") == []
    assert fq.aspect_findings({"w": 1206, "h": 6000}, "phone", "iphone-18-pro", "step 1") == []   # it scrolls
    cut = fq.aspect_findings({"w": 1170, "h": 2600}, "phone", None, "step 1")
    assert cut and "cuts" in cut[0], cut


def test_a_capture_wider_than_the_model_screen_is_refused_naming_its_device(tmp_path):
    n = _img(tmp_path / "w.png", 416, 496)
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.prepare({"device": "phone", "screen": {"image": n}}, shot="DeviceHero", out_dir=str(tmp_path),
                   dur_frames=150, fps=FPS, W=1920, H=1080, lang="en")
    assert 'use device "watch"' in str(e.value)


# ── resolution ────────────────────────────────────────────────────────────────────────────────────────────────

def test_a_capture_drawn_past_its_pixels_is_said_at_media_res_scales():
    import media_res_qa as mr
    p, w = fq.resolution_findings(600, 416, 1.0, "`screen`")
    assert p == [] and w and "media_res_qa blocks delivery" in w[0] and "1.44x" in w[0]
    p, w = fq.resolution_findings(416 * (mr.WARN_SCALE + mr.ERROR_SCALE) / 2, 416, 1.0, "`screen`")
    assert p == [] and w and "blocks" not in w[0]
    assert fq.resolution_findings(300, 416, 1.0, "`screen`") == ([], [])
    p, w = fq.resolution_findings(300, 416, 2.0, "step 2")             # a 2x push-in onto it
    assert w and "at the push-in" in w[0]


# ── concentric corners, even bezels ───────────────────────────────────────────────────────────────────────────

def test_corners_not_concentric_or_a_bezel_uneven_are_named():
    good = {"radius": 40, "outerRadius": 52, "bezels": {"l": 12, "r": 12, "t": 12, "b": 12}, "model": "x"}
    assert fq.concentric_findings(good, "watch") == []
    assert "not concentric" in fq.concentric_findings(dict(good, outerRadius=40), "watch")[0]
    uneven = dict(good, bezels={"l": 12, "r": 12, "t": 4, "b": 4})
    assert any("uneven" in m for m in fq.concentric_findings(uneven, "watch"))
    chin = dict(good, bezels={"l": 12, "r": 12, "t": 12, "b": 40})
    assert fq.concentric_findings(chin, "laptop") == []                 # a laptop's chin is its design


# ── a mockup is not drawn in a second device ──────────────────────────────────────────────────────────────────

def test_a_picture_that_is_already_a_mockup_is_said(tmp_path):
    im = Image.new("RGBA", (1000, 716), (0, 0, 0, 0))
    im.paste(Image.new("RGBA", (900, 640), (20, 20, 20, 255)), (50, 38))
    im.save(str(tmp_path / "mock.png"))
    assert "already a device mockup" in fq.mockup_warning(str(tmp_path / "mock.png"))
    watch = Image.new("RGBA", (416, 496), (20, 20, 20, 255))         # a watch capture: only its corners clear
    for x, y in ((0, 0), (415, 0), (0, 495), (415, 495)):
        watch.putpixel((x, y), (0, 0, 0, 0))
    watch.save(str(tmp_path / "watch.png"))
    assert fq.mockup_warning(str(tmp_path / "watch.png")) is None
    _img(tmp_path / "rgb.png", 1000, 716)
    assert fq.mockup_warning(str(tmp_path / "rgb.png")) is None


# ── a workshop shot that draws its own device ─────────────────────────────────────────────────────────────────

def _workshop(tmp_path, src):
    d = tmp_path / "workshop" / "shots"
    d.mkdir(parents=True)
    (d / "WsWatch.tsx").write_text(src, encoding="utf-8")
    _img(tmp_path / "watch-note.png", 416, 496)


def test_a_workshop_shot_drawing_a_known_capture_by_hand_is_warned(tmp_path):
    _workshop(tmp_path, "import React from 'react';\nimport {Img, staticFile} from 'remotion';\n"
                        "export const WsWatch = () => <Img src={staticFile('watch-note.png')} />;\n")
    w = fq.workshop_warning({"shot": "WsWatch", "shot_props": {}}, str(tmp_path))
    assert w and "Apple Watch Series 12, 46 mm" in w and "DeviceHero" in w, w


def test_a_workshop_shot_using_the_kit_is_not_warned(tmp_path):
    _workshop(tmp_path, "import React from 'react';\nimport {Device, deviceGeometry} from '@runtime/device';\n"
                        "const SRC = 'watch-note.png';\nexport const WsWatch = () => null;\n")
    assert fq.workshop_warning({"shot": "WsWatch", "shot_props": {}}, str(tmp_path)) is None
    # and a workshop shot showing a picture of no known device size says nothing
    (tmp_path / "workshop" / "shots" / "WsWatch.tsx").write_text(
        "export const WsWatch = () => <img src='chart.png' />;\n", encoding="utf-8")
    _img(tmp_path / "chart.png", 1200, 800)
    assert fq.workshop_warning({"shot": "WsWatch", "shot_props": {}}, str(tmp_path)) is None


def test_validate_prints_the_workshop_warning(tmp_path):
    _workshop(tmp_path, "export const WsWatch = () => <img src='watch-note.png' />;\n")
    board = {"meta": {"tier": "remotion"}, "slides": [{"shot": "WsWatch", "shot_props": {}, "narration": "x"}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board), encoding="utf-8")
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(_HERE), "scripts", "device_fidelity_qa.py"),
                        str(tmp_path)], capture_output=True, text=True)
    assert "WARN  beat 1" in r.stdout and "without the device kit" in r.stdout, r.stdout + r.stderr


# ── a label set on the device: the DOM, through text_safe_qa ──────────────────────────────────────────────────

@pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")
def test_a_label_on_the_watch_band_is_reported_and_one_beside_it_is_not(tmp_path):
    import text_safe_qa as g
    hit = g.audit_shot("DeviceLabelProbe", {"dna": "product"}, 30, str(tmp_path / "on.png"))
    on = [v for v in hit if v.get("device")]
    assert on and on[0]["text"] == "Apple Watch", hit
    assert "ON THE DEVICE" in g._describe(on[0])
    clean = g.audit_shot("DeviceLabelCleanProbe", {"dna": "product"}, 30, str(tmp_path / "off.png"))
    assert not [v for v in clean if v.get("device")], clean


def test_a_microphone_or_an_earphone_is_not_a_phone():
    # the ANC film, 2026-11-05: every shot that drew an earbud's microphone was refused as "a hand-drawn device
    # (its code names: microphone)" — 'phone' found inside 'microphone'
    import device_fidelity_qa as dq
    for ok in ("const microphone = 1;", "const innerMicrophone = 2;", "earphoneTip", "headphones", "drawMegaphone"):
        assert not dq._device_evidence(ok), ok
    for bad in ("const phone = 1;", "iPhoneFrame", "drawPhone()", "phoneBody", "laptopLid", "IPadScreen",
                "macBookHinge", "smartphone", "tabletEdge"):
        assert dq._device_evidence(bad), bad
