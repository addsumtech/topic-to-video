"""Cinematography backstops (#9 grade + #7 light): a per-register colour GRADE (Finish, one distinct split
per style — not the old fold-to-4) and a frame-driven LIGHT RIG in the true-3D tier (a travelling key/rim/
specular that sweeps + ramps out of a per-register mood floor). Both verified from renders; here we lock the
plumbing + the determinism + the lining-safe wiring so they can't silently regress."""
import os
import re

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_STYLES = ["cinematic", "noir", "editorial", "artdeco", "watercolor", "cyberpunk", "vaporwave", "terminal",
           "blueprint", "brutalism", "swiss", "bauhaus", "memphis", "risograph", "manga", "cartographic",
           "glassmorphism", "claymorphism"]


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


# ── per-register grade (Finish.tsx) ──────────────────────────────────────────────────────────────────
def test_grade_has_a_distinct_entry_per_style():
    src = _src("remotion", "src", "theme", "Finish.tsx")
    assert "STYLE_TO_GRADE" in src and "GRADE_FAMILIES" not in src, "the 4-family fold is replaced by a per-style table"
    for s in _STYLES:
        assert re.search(r"\b" + s + r":\s*'linear-gradient", src), "style %r must have its own grade" % s
    assert "STYLE_TO_GRADE[theme.style]" in src and "FALLBACK_GRADE" in src, "keyed on theme.style with a fallback"


# ── frame-driven light rig (ThreeScene.tsx) ──────────────────────────────────────────────────────────
def test_light_rig_is_frame_driven_and_sweeps():
    src = _src("remotion", "src", "three", "ThreeScene.tsx")
    assert "LightRig" in src and "STYLE_TO_MOOD" in src, "a per-register frame-driven light rig"
    assert "swing" in src, "the key/specular sweep is a function of the frame (L->R)"
    assert "revealEnvelope" in src and "reveal3d" in src, "a dark->lit reveal envelope + the opt-in overlay"


def test_light_rig_replaced_the_static_lights():
    src = _src("remotion", "src", "three", "ThreeScene.tsx")
    assert "position={[5, 9, 4]}" not in src, "the 3 static lights must be gone (replaced by LightRig)"
    assert "<LightRig" in src, "LightRig is wired into the canvas"


def test_light_rig_is_deterministic():
    src = _src("remotion", "src", "three", "ThreeScene.tsx")
    assert "Math.random" not in src and "Date.now(" not in src, "the rig must be a pure function of the frame"


def test_mood_floor_opens_dim_not_black():
    # every mood opens dim-but-visible (floor > 0) so a mid-film beat isn't full-black; the full black->lit
    # reveal is the opt-in reveal3d overlay.
    src = _src("remotion", "src", "three", "ThreeScene.tsx")
    floors = [float(m) for m in re.findall(r"floor:\s*([0-9.]+)", src)]
    assert floors and all(f > 0 for f in floors), "no mood may open at a 0 light floor (renders black + abstains)"
