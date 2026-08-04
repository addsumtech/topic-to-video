"""PER-BEAT grade (audit axis C): the finishing wash runs HOTTER on a climax, COOLER on a calm beat, and
gently breathes -- instead of the old GLOBAL, frame-invariant grade. Driven automatically from the beat's
ENERGY signal the director already authored (climax / bold / subtle / shot energies); a neutral beat with no
signal returns None so Finish renders the unchanged global grade (byte-identical, no regression)."""
import os

import render_remotion as rr

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src")


def _read(*p):
    return open(os.path.join(_SRC, *p), encoding="utf-8").read()


# ── _grade_heat signal ────────────────────────────────────────────────────────────────────────────────
def test_climax_is_hottest():
    assert rr._grade_heat({"props": {"climax": True}}) == 0.92
    assert rr._grade_heat({"climax": True}) == 0.92


def test_energy_tier_maps_to_heat():
    assert rr._grade_heat({"energy": "bold"}) == 0.78
    assert rr._grade_heat({"intensity": "subtle"}) == 0.30
    assert rr._grade_heat({"energy": "calm"}) == 0.26


def test_neutral_beat_is_none():
    # no energy signal -> None -> Finish renders the old global grade unchanged (no regression)
    assert rr._grade_heat({"type": "cinematic", "title": "x"}) is None
    assert rr._grade_heat({"energy": "balanced"}) is None


def test_shot_based_reads_the_hottest_shot():
    s = {"shots": [{"energy": "subtle"}, {"energy": "bold"}, {"energy": "balanced"}]}
    assert rr._grade_heat(s) == 0.78            # the scene grades to its hottest beat, tracking the arc
    assert rr._grade_heat({"shots": [{"energy": "balanced"}]}) is None   # all-neutral -> no signal


# ── Finish source-guard (the per-beat logic + the byte-identical default) ─────────────────────────────
def test_finish_is_per_beat_with_a_safe_default():
    src = _read("theme", "Finish.tsx")
    assert "energy?: number" in src and "dur?: number" in src, "Finish no longer takes per-beat energy/dur"
    assert "hasHeat" in src, "the per-beat heat branch is gone"
    # the DEFAULT (no energy) must be EXACTLY the old global look: grade opacity 1, no warm/cool, no swell.
    assert "hasHeat ? (0.72 + 0.56 * heat) * swell : 1" in src, "default grade opacity is no longer 1 (regression risk)"
    assert "warm" in src and "cool" in src, "the hot/cool per-beat casts are gone"


def test_renderers_thread_grade_heat_to_finish():
    for f in (("stage", "SceneStage.tsx"), ("Camera.tsx",), ("three", "ThreeScene.tsx")):
        assert "energy={gradeHeat ?? undefined} dur={dur}" in _read(*f), "%s does not pass per-beat grade to Finish" % "/".join(f)
    scene = _read("Scene.tsx")
    assert scene.count("gradeHeat={scene.gradeHeat}") >= 4, "not all 4 cinematic renderers receive gradeHeat"
