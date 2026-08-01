"""P2 visual-fix backstops (2026-08-02 audit): the film 'look' (Finish) + the true-3D grounding must not
regress. Each guards a fix verified from a real render (shadows/fog/bold text/roll-free billboard, and a
vignette that actually darkens the corners instead of falling entirely outside the frame)."""
import os
import re

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


def test_vignette_falloff_starts_inside_the_frame():
    src = _src("remotion", "src", "theme", "Finish.tsx")
    # the vignette's clear-centre (transparent) stop must be well inside the frame; the old 60% stop with
    # 135% radii put every visible corner below it, darkening ZERO pixels (a no-op).
    m = re.search(r"radial-gradient\(\d+% \d+% at [^,]+,\s*rgba\(0,0,0,0\)\s*(\d+)%", src)
    assert m, "vignette gradient (transparent -> black) not found"
    assert int(m.group(1)) <= 45, "vignette transparent stop must be inside the frame (<=45%), not a no-op"


def test_grain_has_a_floor():
    src = _src("remotion", "src", "theme", "Finish.tsx")
    assert "Math.max(0.03" in src, "grain needs a small video-tier floor so filmic styles aren't ungrained"


def test_three_scene_grounds_with_shadows_and_fog():
    src = _src("remotion", "src", "three", "ThreeScene.tsx")
    assert re.search(r"<ThreeCanvas\s+shadows", src), "canvas must enable shadow maps"
    assert "castShadow" in src and "receiveShadow" in src, "light casts + floor/bars receive/cast (grounded)"
    assert re.search(r"attach=(\"|')fog(\"|')", src), "fog must dissolve the hard floor edge into bg"


def test_billboard_is_roll_free_yaw_and_pitch():
    src = _src("remotion", "src", "three", "ThreeScene.tsx")
    assert "billboardEuler" in src and "'YXZ'" in src, \
        "billboard must face camera in yaw+pitch with a roll-free YXZ euler (not yaw-only, not XYZ)"


def test_rasterized_3d_text_is_bold():
    src = _src("scripts", "render_remotion.py")
    assert "set_variation_by_axes" in src, "3D text must rasterize at bold weight, not the VF light default"
