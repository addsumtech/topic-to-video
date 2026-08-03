"""P1 critical-fix backstops (2026-08-01 design audit). Each guards a fix proven from a real render:

1. Per-element DEPTH is not flattened — SceneStage must NOT place a filter/opacity/flat wrapper ABOVE an
   element's translate3d node (a flat ancestor collapses every translateZ to one plane → flat glass cards).
   The blur must be passed INTO Element and applied on an inner leaf. (This also closes finding #27: the
   old 3D-invariant test only read Camera.tsx and never guarded SceneStage — the file that had the bug.)
2. Shot framing holds the subject at a CONSTANT camera distance (dolly = -DIST - tz), so the
   establish→hero size ladder can't invert on a multi-depth stage (the earlier `tz - DIST` double-counted tz).
3. The cinematic type system forces LINING figures on every role (no old-style digits — a standing rule).
4. The pre-render gate ACCEPTS shot-based (stage+shots) and true-3D (planes / cinematic3d) boards — the
   whole P2+ paradigm used to fail validate.py because it still hard-required `layers`.
"""
import os
import re
import pytest
import storyboard as sb

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


# ── 1. per-element depth must not be flattened ───────────────────────────────────────────────────────
def test_scenestage_passes_blur_into_element_no_flat_wrapper():
    src = _src("remotion", "src", "stage", "SceneStage.tsx")
    assert re.search(r"<Element\b[^/>]*\bblur=\{", src), "blur must be passed INTO Element (applied on a leaf)"
    # NO <div style={{filter...}}> may sit directly above <Element> (that flat node collapses translateZ).
    assert not re.search(r"filter[^>]*>\s*<Element\b", src), "no filter/flat wrapper may wrap <Element>"


def test_element_blur_and_opacity_are_on_the_inner_leaf():
    src = _src("remotion", "src", "stage", "elements.tsx")
    assert "transformStyle: 'preserve-3d'" in src and "translate3d(" in src
    # opacity + rack-focus blur live on the inner leaf, never on the depth node. The leaf also carries the
    # entrance transform (materialize/aperture) — so match opacity:op … filter:leafFilter on that leaf, and
    # confirm the rack-focus blur is composed INTO leafFilter.
    assert re.search(r"opacity:\s*op,.*filter:\s*leafFilter", src), "opacity + filter(leafFilter) must be on the inner leaf"
    assert "blur(${blur}px)" in src, "rack-focus blur must be composed into the leaf filter"
    # the floor's rotateX must be composed onto the depth container (so it lays down in 3D), not a flat leaf.
    assert "isFloor ? ' rotateX(90deg)'" in src, "floor rotateX must be on the preserve-3d container"


# ── 2. constant-depth framing (no ladder inversion) ──────────────────────────────────────────────────
def test_shot_framing_holds_constant_subject_depth():
    src = _src("remotion", "src", "stage", "shots.ts")
    assert re.search(r"dolly = -\d+ - tz", src), "dolly must be -DIST - tz (subject at a constant depth)"
    assert not re.search(r"dolly = tz - \d", src), "the double-counting `dolly = tz - DIST` must be gone"


# ── 3. lining figures on every role ──────────────────────────────────────────────────────────────────
def test_typography_forces_lining_figures_on_all_roles():
    src = _src("remotion", "src", "theme", "typography.ts")
    assert "lining-nums" in src
    # a non-number role must no longer fall through to `undefined` (which let old-style figures render).
    assert not re.search(r"fontVariantNumeric:\s*role === 'number' \? '[^']*' : undefined", src), \
        "non-number roles must carry lining-nums, not undefined"


# ── 4. the pre-render gate accepts the shot-based + 3D paradigms ──────────────────────────────────────
def test_cinematic3d_is_a_valid_scene_type():
    assert "cinematic3d" in sb.VALID_SCENE_TYPES


def test_gate_accepts_shot_based_scene_without_layers():
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["stage"] = {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0], "title": "X"}]}
    s["shots"] = [{"type": "HERO", "target": "a"}]
    sb._validate_props(s)  # must NOT raise (previously demanded `layers`)


def test_gate_accepts_cinematic3d_planes():
    s = sb.new_scene(1, "cinematic3d", {}, narration="x")
    s["planes"] = [{"kind": "bars", "position": [0, 0, 0], "data": [1, 2, 3]}]
    sb._validate_props(s)


def test_gate_still_rejects_empty_cinematic():
    s = sb.new_scene(1, "cinematic", {}, narration="x")  # no stage/shots/planes/layers → nothing to draw
    with pytest.raises(sb.StoryboardError):
        sb._validate_props(s)


def test_gate_rejects_cinematic3d_without_planes():
    s = sb.new_scene(1, "cinematic3d", {}, narration="x")
    with pytest.raises(sb.StoryboardError):
        sb._validate_props(s)
