"""Value-level source guard for the camera framing ladder (the over-zoom retune).

The auto shot ladder is bounded BY CONSTRUCTION — a compressed zoom band + frontal read shots + a clamped
move amplitude + a long flat default lens. That is what prevents 'opens tiny then pushes in until it
overflows / keystones'. Those numbers had NO other test (the render tests grep strings or assert tiling),
so a revert (HERO 1.06 -> 1.5, deleting the clamp, perspective 2000 -> 1300) would pass the whole suite.
This locks the band in place. (Audit: the retune's headline change was unprotected against its own regression.)"""
import os
import re

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_SKILL, "remotion", "src")


def _read(*p):
    return open(os.path.join(_SRC, *p), encoding="utf-8").read()


def test_framing_ladder_stays_in_one_legible_band():
    src = _read("stage", "shots.ts")
    zooms = [float(m) for m in re.findall(r"zoom:\s*([0-9.]+)", src)]   # per-shot zoom scalars in the ladder
    assert zooms, "no zoom values found in shots.ts"
    assert max(zooms) <= 1.15, "a shot zoom exceeds the compressed band (~<=1.15) — over-zoom regressed: %s" % zooms
    assert min(zooms) >= 0.9, "a shot opens too wide (<0.9) — tiny-then-huge regressed: %s" % zooms


def test_read_shots_are_frontal():
    src = _read("stage", "shots.ts")
    # the oblique REVEAL (pitch 10 / yaw -15 / zoom 1.8) was the main distortion culprit — stays recast frontal.
    assert "pitch: 10" not in src and "yaw: -15" not in src, "the oblique REVEAL keystone pose came back"
    assert "FRONTAL" in src, "the frontal-read discipline is gone from the shot ladder"


def test_move_amplitude_is_clamped():
    src = _read("stage", "motions.ts")
    assert "Math.min(1.6" in src, "the move-amplitude clamp is gone — a bold push can blow past the safe band"


def test_default_perspective_is_a_long_flat_lens():
    # >=2000 everywhere a perspective default is set; a short one (1300) fisheyes/keystones read planes.
    for f in (("stage", "SceneStage.tsx"), ("Scene.tsx",), ("Camera.tsx",)):
        src = _read(*f)
        assert "|| 2000" in src, "%s no longer defaults perspective to the 2000px long lens" % "/".join(f)
    # the two paths that were explicitly fixed must not still pin the old keystoning default.
    assert "|| 1300" not in _read("Scene.tsx"), "Scene.tsx still pins legacy perspective 1300"
    assert "|| 1300" not in _read("stage", "SceneStage.tsx"), "SceneStage.tsx still pins legacy perspective 1300"
