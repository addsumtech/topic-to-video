"""A RESIZED capture is drawn on the real model whose screen is its shape (scripts/device_fidelity_qa.py resolve).

Measured 2026-11-01 on a Grok Bot film: Apple's App Store iPad/iPhone screens, cropped out of their marketing
composites, are not any device's native pixels (1258x1676, 930x2020) — so they were drawn on the GENERIC tablet and
phone, whose guessed 11.5 mm corner rounded the status bar's time and battery off. They are exactly the shape of the
13-inch iPad Pro (3:4) and of the 6.9-inch iPhone: drawn on that model, the corners are the real ones.
"""
import device_fidelity_qa as fq
from PIL import Image


def _png(tmp_path, name, w, h):
    (tmp_path / "media").mkdir(exist_ok=True)
    Image.new("RGB", (w, h), (250, 250, 250)).save(tmp_path / "media" / name)
    return "media/" + name


def _props(src, device):
    return {"device": device, "screen": {"image": src}}


def test_a_resized_capture_takes_the_model_of_its_shape(tmp_path):
    out, probs, warns = fq.resolve(_props(_png(tmp_path, "pad.png", 1258, 1676), "tablet"), "DeviceHero", str(tmp_path))
    assert probs == [] and out["model"] == "ipad-pro-13", (out, warns)
    assert any("shape" in w for w in warns), warns
    out, probs, warns = fq.resolve(_props(_png(tmp_path, "ph.png", 930, 2020), "phone"), "DeviceHero", str(tmp_path))
    assert out["model"] in ("iphone-18-pro-max", "iphone-18-pro", "iphone-17"), out


def test_a_shape_no_model_has_stays_generic_and_a_native_capture_is_unchanged(tmp_path):
    out, _p, warns = fq.resolve(_props(_png(tmp_path, "sq.png", 1000, 1000), "tablet"), "DeviceHero", str(tmp_path))
    assert "model" not in out and any("generic" in w for w in warns), (out, warns)
    out, _p, warns = fq.resolve(_props(_png(tmp_path, "a16.png", 1640, 2360), "tablet"), "DeviceHero", str(tmp_path))
    assert out["model"] == "ipad-a16" and not any("shape" in w for w in warns)
