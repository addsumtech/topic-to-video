"""stereo: the promo's sounds are placed where their causes are on the frame, the field is mono-safe, and the mix
says what came out."""
import os
import sys
import wave

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
os.environ.setdefault("TOPIC_TO_VIDEO_PROMO_LEDGER", os.path.join(os.path.dirname(os.path.abspath(__file__)), "_promo_ledger_test.json"))
import stereo  # noqa: E402
import sfx  # noqa: E402
import promo_film as pf  # noqa: E402

X = (np.random.default_rng(0).standard_normal(22050) * np.exp(-np.arange(22050) / 4000)).astype(np.float32)


def test_a_centred_sound_keeps_the_mono_level_and_a_pan_leans_without_losing_power():
    c = stereo.pan(X, 0.0)
    assert np.allclose(c[:, 0], X, atol=1e-6) and np.allclose(c[:, 1], X, atol=1e-6)
    left = stereo.measure(stereo.pan(X, -0.7))
    assert left["balance_db"] > 6 and left["corr"] > 0.99
    e = lambda a: float(np.sum(a.astype(np.float64) ** 2))  # noqa: E731
    assert e(stereo.pan(X, -0.7)) == pytest.approx(e(stereo.pan(X, 0.0)), rel=1e-3)   # constant power


def test_a_sweep_travels_while_the_sound_is_loud():
    s = stereo.sweep(X, -0.6, 0.6)
    h = len(X) // 60                                      # X's first fifth of energy: the travel follows energy, not time
    first, last = stereo.measure(s[:h]), stereo.measure(s[-len(X) // 2:])
    assert first["balance_db"] > 2 and last["balance_db"] < -2


def test_wide_is_wide_and_mono_safe():
    w = stereo.measure(stereo.place(X, "wide"))
    assert 0.4 < w["corr"] < 0.95 and w["mono_loss_db"] < 1.5 and abs(w["balance_db"]) < 0.5


def test_an_unknown_placement_is_refused():
    with pytest.raises(ValueError):
        stereo.place(X, "everywhere")


def test_a_cue_is_heard_where_its_cause_is_on_the_frame():
    keys = [{"f": 0, "cx": 700, "cy": 450, "zoom": 1.0}]
    shot = {"kind": "page", "dur": 90, "src": "p.png", "w": 1400, "h": 900, "keys": keys,
            "layers": [{"kind": "cursor", "path": [{"f": 0, "x": 1300, "y": 400}, {"f": 20, "x": 120, "y": 400}], "clicks": [24]},
                       {"kind": "ring", "box": {"x": 1200, "y": 100, "w": 100, "h": 40}, "at": 40},
                       {"kind": "deal", "boxes": [{"x": 100 + 300 * i, "y": 300, "w": 200, "h": 100} for i in range(4)], "at": 50}]}
    cues = pf.plan_sfx({"shots": [shot]}, placed=True)
    by = {}
    for f, c, g, how in cues:
        by.setdefault(c, []).append(how)
    assert by["click"][0] < -0.3                         # the pointer clicked at x=120, the left of the frame
    assert by["select"][0] > 0.3                         # the ring is on the right
    deals = by["deal"]
    assert deals == sorted(deals) and deals[0] < 0 < deals[-1]     # dealt left to right, heard left to right
    assert all(abs(p) <= pf.PAN_SPAN for p in deals)     # placed, never hard in one ear
    # without placed=True the plan is the old three fields
    assert all(len(c) == 3 for c in pf.plan_sfx({"shots": [shot]}))


def test_air_goes_the_way_the_picture_goes():
    def move(dcx):
        return {"kind": "page", "dur": 60, "src": "p.png", "w": 3000, "h": 900,
                "keys": [{"f": 0, "cx": 1500, "cy": 450, "zoom": 1.2}, {"f": 30, "cx": 1500 + dcx, "cy": 450, "zoom": 1.2}]}
    right = [h for f, c, g, h in pf.plan_sfx({"shots": [move(800)]}, placed=True) if c == "whoosh"][0]
    left = [h for f, c, g, h in pf.plan_sfx({"shots": [move(-800)]}, placed=True) if c == "whoosh"][0]
    assert right[0] > 0 > right[1]                       # camera right -> the page slides left -> the air does
    assert left[0] < 0 < left[1]
    push = {"kind": "page", "dur": 60, "src": "p.png", "w": 3000, "h": 900,
            "keys": [{"f": 0, "cx": 1500, "cy": 450, "zoom": 1.0}, {"f": 30, "cx": 1500, "cy": 450, "zoom": 1.6}]}
    assert [h for f, c, g, h in pf.plan_sfx({"shots": [push]}, placed=True) if c == "whoosh"] == ["wide"]


def test_the_stereo_track_puts_each_cue_on_its_side(tmp_path):
    out = str(tmp_path / "s.wav")
    m = sfx.build_sfx_stereo([(0.3, "click", 0.6, -0.7), (1.3, "click", 0.6, 0.7)], 2.0, out)
    assert m and m["corr"] > 0.0
    with wave.open(out) as w:
        assert w.getnchannels() == 2
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float64)
    sr = sfx.SR
    first, second = a[: int(0.8 * sr)], a[int(0.8 * sr):]
    assert np.sum(first[:, 0] ** 2) > 4 * np.sum(first[:, 1] ** 2)
    assert np.sum(second[:, 1] ** 2) > 4 * np.sum(second[:, 0] ** 2)
    # a cue still PEAKS on its planned time, placed or not
    env = np.abs(first[:, 0])
    assert abs(np.argmax(env) / sr - 0.3) < 0.02
