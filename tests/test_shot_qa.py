"""P5 backstop — the shot_qa scorer, on SYNTHETIC frames (no Node/ffmpeg needed).

The scorer's whole value is honesty: it must FLAG the unambiguous defects (a blank/flat frame; a declared
camera move that produced no motion) and PASS a clean cinematic frame — without false-failing good,
RESTRAINED motion or a captioned frame. These lock that behavior. (A prior version scored 'more motion =
better' and measured the burned caption's own edges — both caught by running it on a real render.)"""
import pytest

np = pytest.importorskip("numpy")
PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw  # noqa: E402
import shot_qa  # noqa: E402

W, H = 384, 216


def _panel(shift=0, scale=1.0):
    """A clean cinematic frame: dark bg + one bright focal panel (optionally shifted/scaled = motion)."""
    im = Image.new("RGB", (W, H), (14, 17, 22))
    d = ImageDraw.Draw(im)
    cw, ch = int(150 * scale), int(60 * scale)
    x0 = W // 2 - cw // 2 + shift
    y0 = H // 2 - ch // 2
    d.rectangle([x0, y0, x0 + cw, y0 + ch], fill=(30, 36, 46), outline=(230, 178, 60), width=3)
    d.text((x0 + 14, y0 + 10), "A team of agents", fill=(240, 244, 248))
    return im


def _blank():
    return Image.new("RGB", (W, H), (3, 3, 4))  # near-black


def _flat_noise():
    arr = (np.random.RandomState(0).rand(H, W, 3) * 90 + 60).astype("uint8")  # detail everywhere, no subject
    return Image.fromarray(arr, "RGB")


# ── PASS a clean, moving cinematic scene ─────────────────────────────────────────────────────────────
def test_clean_moving_scene_passes():
    frames = [_panel(shift=i * 6, scale=1 + i * 0.02) for i in range(5)]  # a gentle push/track
    r = shot_qa.score_scene(frames, declared_move=True, is_3d=True)
    assert not r["floors"], r["floors"]
    assert r["scores"]["composition"] >= 60
    assert r["metrics"]["motion_mean"] >= shot_qa._MOTION_DEAD


def test_restrained_motion_is_not_penalised():
    """A gentle, restrained move (≈ the real cinematic dolly's magnitude) must NOT fail, and must NOT be
    scored 'more is better' — restraint is the premium goal, not a defect."""
    frames = [_panel(shift=i * 3) for i in range(5)]  # restrained, but clearly above the dead floor
    r = shot_qa.score_scene(frames, declared_move=True, is_3d=True)
    assert r["metrics"]["motion_mean"] > shot_qa._MOTION_DEAD
    assert not any("no motion" in f for f in r["floors"])  # not flagged as an invisible move
    assert r["scores"]["motion"] is None  # motion is ABSTAINED, never a graded 'more is better' score


# ── FLOORS: the unambiguous defects ──────────────────────────────────────────────────────────────────
def test_blank_frame_floors():
    r = shot_qa.score_scene([_blank()] * 5, declared_move=False, is_3d=False)
    assert any("blank" in f for f in r["floors"])


def test_declared_move_with_no_motion_floors():
    frames = [_panel(shift=0)] * 5  # identical -> zero motion, but a move was declared
    r = shot_qa.score_scene(frames, declared_move=True, is_3d=True)
    assert any("no motion" in f for f in r["floors"])


def test_static_hold_with_no_motion_does_not_floor():
    frames = [_panel(shift=0)] * 5
    r = shot_qa.score_scene(frames, declared_move=False, is_3d=False)  # a legit still hold
    assert not any("no motion" in f for f in r["floors"])


def test_flat_frame_floors_on_focal_dominance():
    r = shot_qa.score_scene([_flat_noise()] * 5, declared_move=False, is_3d=False)
    assert any("focal dominance" in f for f in r["floors"])


def _murk():
    """A near-uniform very-dark focal region — content present nowhere (murky/illegible)."""
    import numpy as _np
    arr = (_np.ones((H, W, 3)) * 10 + _np.random.RandomState(1).rand(H, W, 3) * 6).astype("uint8")
    return Image.fromarray(arr, "RGB")


def test_legibility_floor_flags_dark_flat_focal():
    """The cinematic-tier WCAG analog: a dark + FLAT focal region (no readable content) floors."""
    r = shot_qa.score_scene([_murk()] * 5, declared_move=False, is_3d=False)
    assert any("murky" in f or "illegible" in f for f in r["floors"])


def test_legibility_floor_passes_dark_but_high_contrast():
    """A dark card with light text (dark MEAN but high CONTRAST) is legible — must NOT floor on legibility."""
    r = shot_qa.score_scene([_panel(shift=i * 4) for i in range(5)], declared_move=True, is_3d=True)
    assert not any("murky" in f or "illegible" in f for f in r["floors"])
    assert r["metrics"]["focal_contrast_std"] > 8


# ── abstention discipline ────────────────────────────────────────────────────────────────────────────
def test_typography_always_abstains():
    frames = [_panel(shift=i * 5) for i in range(5)]
    r = shot_qa.score_scene(frames, declared_move=True, is_3d=True)
    assert r["scores"]["typography"] is None  # can't measure legibility from a (potentially) captioned frame


def test_depth_abstains_when_not_3d():
    frames = [_panel(shift=i * 6) for i in range(5)]
    r = shot_qa.score_scene(frames, declared_move=True, is_3d=False)  # a flat message beat
    assert r["scores"]["depth"] is None


def test_no_numpy_abstains(monkeypatch):
    monkeypatch.setattr(shot_qa, "_np", lambda: None)
    r = shot_qa.score_scene([_panel()], declared_move=True, is_3d=True)
    assert r["abstained"] and not r["floors"]  # UNSCORED, never a false pass/fail
