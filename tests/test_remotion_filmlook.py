"""Film-look POST-stack backstops (#9): react-postprocessing EffectComposer (real optical DoF + selective
Bloom on the HDR-emissive result element + ACES tone) on the true-3D tier, verified from a render. Here we
lock the pinned v2 deps (v3 needs R3F v9/React 19 and crashes the reconciler), the composer wiring, the
'one owner' vignette rule, and the filmLook gating."""
import json
import os

import render_remotion as rr
import storyboard as sb

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


def _b3d(planes, meta_extra=None):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False, **(meta_extra or {})})
    s = sb.new_scene(1, "cinematic3d", {}, narration="x")
    s["audio"] = "a"
    s["duration"] = 4.0
    s["planes"] = planes
    d["slides"] = [s]
    return d


# ── pinned deps (the one real risk) ──────────────────────────────────────────────────────────────────
def test_postprocessing_pinned_to_the_v2_line():
    pkg = json.load(open(os.path.join(_SKILL, "remotion", "package.json")))
    deps = pkg.get("dependencies", {})
    assert deps.get("@react-three/postprocessing") == "2.19.1", "pin v2 (v3 hard-requires R3F v9 / React 19)"
    assert deps.get("postprocessing") == "6.37.8", "pin postprocessing (focusDistance semantics moved across 6.3x)"


def test_postprocessing_installed():
    nm = os.path.join(_SKILL, "remotion", "node_modules")
    assert os.path.isdir(os.path.join(nm, "@react-three", "postprocessing"))
    assert os.path.isdir(os.path.join(nm, "postprocessing"))


# ── composer wiring ──────────────────────────────────────────────────────────────────────────────────
def test_composer_wired_with_dof_bloom_aces():
    src = _src("remotion", "src", "three", "ThreeScene.tsx")
    for tok in ("EffectComposer", "DepthOfField", "Bloom", "ToneMapping", "SMAA"):
        assert tok in src, "composer must include %s" % tok
    assert "ACES_FILMIC" in src, "ACES tone map (matches R3F's default the composer bypasses)"
    assert 'attach="background"' in src, "opaque scene background (else the composer blackens the sky)"
    assert "HalfFloatType" in src, "HDR buffer so emissive>1 survives to selective Bloom"


def test_composer_is_gated_and_single_vignette():
    src = _src("remotion", "src", "three", "ThreeScene.tsx")
    assert "filmLook !== false" in src, "the composer is opt-in (gated by filmLook)"
    assert "<Vignette" not in src, "no composer vignette — Finish owns the vignette (one owner, no double)"


def test_selective_bloom_via_hdr_emissive():
    src = _src("remotion", "src", "three", "ThreeScene.tsx")
    assert "emissiveIntensity" in src and "toneMapped" in src, "the result bar glows via HDR emissive + toneMapped=false"


# ── filmLook threading ───────────────────────────────────────────────────────────────────────────────
def test_filmlook_defaults_on_for_3d(tmp_path):
    sc = rr.build_props(_b3d([{"kind": "bars", "position": [0, 0, 0], "data": [1, 2, 3]}]), str(tmp_path))["scenes"][0]
    assert sc["filmLook"] is True


def test_filmlook_meta_opt_out(tmp_path):
    sc = rr.build_props(_b3d([{"kind": "bars", "position": [0, 0, 0], "data": [1, 2]}], {"film_look": False}), str(tmp_path))["scenes"][0]
    assert sc["filmLook"] is False


def test_non_3d_scene_has_no_filmlook(tmp_path):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion"})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "a"
    s["duration"] = 3.0
    s["stage"] = {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0]}]}
    s["shots"] = [{"type": "HERO", "target": "a"}]
    d["slides"] = [s]
    assert rr.build_props(d, str(tmp_path))["scenes"][0]["filmLook"] is None
