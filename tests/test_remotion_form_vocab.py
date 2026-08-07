"""Born-in-3D FORM VOCABULARY (audit top-3 #1): particles + surface, beyond bars/stack/plane.

The R3F tier shipped only 3 nouns (textured plane, bar boxes, cube stack) — the audit's biggest ceiling gap
for creative 3D. This adds two asset-free, deterministic, material-bound primitives the flat card rig cannot
make: `particles` (a field that assembles from scatter into a lattice) and `surface` (a parametric height
field / data landscape). These guard the renderer's acceptance + validate's early checks + the ThreeScene
wiring (source-guard, since no other test greps the R3F components)."""
import math
import os

import validate as v
import render_remotion as rr

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_SKILL, "remotion", "src")


def _three():
    return open(os.path.join(_SRC, "three", "ThreeScene.tsx"), encoding="utf-8").read()


# ── renderer accepts + coerces the new plane kinds ────────────────────────────────────────────────────
def test_clean_planes_accepts_particles_and_passes_count():
    out = rr._clean_planes([{"kind": "particles", "count": 90, "position": [0, 0, 0]}], "s1")
    assert out[0]["kind"] == "particles" and out[0]["count"] == 90


def test_clean_planes_accepts_surface_with_and_without_data():
    a = rr._clean_planes([{"kind": "surface", "position": [0, 0, 0]}], "s1")
    assert a[0]["kind"] == "surface"
    b = rr._clean_planes([{"kind": "surface", "data": [1, 4, 2, 8], "position": [0, 0, 0]}], "s1")
    assert b[0]["data"] == [1.0, 4.0, 2.0, 8.0]


def test_clean_planes_still_rejects_unknown_kind():
    import pytest
    with pytest.raises(RuntimeError):
        rr._clean_planes([{"kind": "bogus", "position": [0, 0, 0]}], "s1")


# ── validate early guards ─────────────────────────────────────────────────────────────────────────────
def _run(planes):
    errs, warns = [], []
    scene = {"type": "cinematic3d", "planes": planes,
             "camera3d": [{"at": 0.0, "yaw": 0, "radius": 8, "height": 4}]}
    v._cinematic_fields(scene, {"fps": 30}, "/tmp", "s1", errs, warns)
    return errs, warns


def test_particles_and_surface_scene_is_clean():
    errs, warns = _run([{"kind": "particles", "count": 120, "position": [0, 0, 0]},
                        {"kind": "surface", "data": [2, 5, 3, 9, 4], "position": [0, 0, 0]}])
    assert not errs, errs


def test_particles_over_cap_warns():
    _errs, warns = _run([{"kind": "particles", "count": 500, "position": [0, 0, 0]}])
    assert any("exceeds the render cap" in w for w in warns), warns


def test_surface_nan_data_errors():
    errs, _ = _run([{"kind": "surface", "data": [1.0, float("nan"), 3.0], "position": [0, 0, 0]}])
    assert any("NaN/Infinity" in e for e in errs), errs


# ── ThreeScene wiring (source-guard — the components + material binding + dispatch must stay) ──────────
def test_threescene_defines_and_dispatches_the_new_forms():
    src = _three()
    assert "Particles3D" in src and "Surface3D" in src, "the new 3D form components are gone"
    assert "kind === 'particles'" in src and "kind === 'surface'" in src, "dispatch for the new kinds is gone"
    # they must be MATERIAL-BOUND (inherit STYLE_TO_MATERIAL3D via mat3d) like bars/stack
    assert src.count("mat={mat3d}") >= 4, "a new form is not threaded the style material (mat={mat3d})"
    # deterministic: the particle scatter is a HASH of the index, never Math.random
    assert "_hash11" in src and "Math.random(" not in src, "particle placement must be a deterministic hash (no Math.random call)"


# ── TERMINAL glyph-rain (a born-in-3D world form) ─────────────────────────────────────────────────────
def test_clean_planes_accepts_glyphrain():
    out = rr._clean_planes([{"kind": "glyphrain", "count": 20, "position": [0, 0, 0]}], "s1")
    assert out[0]["kind"] == "glyphrain" and out[0]["count"] == 20


def test_glyphrain_wired_in_threescene_and_rasterizer():
    src = _three()
    assert "GlyphRain3D" in src and "kind === 'glyphrain'" in src, "glyph-rain component/dispatch is gone"
    assert "RepeatWrapping" in src and "offset.y" in src, "glyph-rain scroll (texture offset) is gone"
    rr_src = open(os.path.join(_SKILL, "scripts", "render_remotion.py"), encoding="utf-8").read()
    assert "glyphrain" in rr_src and "_glyphrain_png" in rr_src, "the glyph-strip rasterizer is gone"


def test_particle_cap_is_declared_in_source():
    src = _three()
    assert "PARTICLE_MAX = 160" in src, "the particle safety cap changed — keep validate's warn threshold in sync"
