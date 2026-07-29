"""P6 backstop — the TRUE-3D (WebGL / R3F) hero tier.

Locks the pipeline contract: a `cinematic3d` scene's `planes` + `camera3d` thread through build_props with
fail-loud coercion, the scene is renderable (not 'unsupported'), the render adds `--gl=angle` (without a
GL renderer headless Chrome has no WebGL -> black), and the TS wiring (ThreeScene exists + Scene dispatches
planes) can't silently regress. WebGL rendering itself is proven by a real render, not a unit test."""
import os
import pytest
import render_remotion as rr
import storyboard as sb

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _board(planes=None, camera3d="default"):
    d = sb.new_storyboard({"aspect": "16:9", "fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic3d", {}, narration="x")
    s["audio"] = "audio/01.mp3"; s["duration"] = 6.0
    s["planes"] = planes if planes is not None else [
        {"color": "#e3b23c", "position": [-2.6, 0, -1], "size": [3, 1.8]},
        {"color": "#5fb3c9", "position": [0.4, 0.2, 1], "rotation": [0, -0.3, 0], "size": [3, 1.8]}]
    if camera3d == "default":
        s["camera3d"] = [{"at": 0.0, "yaw": -0.9, "radius": 7, "height": 7},
                         {"at": 1.0, "yaw": 0.5, "radius": 7, "height": 2.6}]
    elif camera3d is not None:
        s["camera3d"] = camera3d
    d["slides"] = [s]
    return d


def test_planes_and_camera3d_thread(tmp_path):
    sc = rr.build_props(_board(), str(tmp_path))["scenes"][0]
    assert len(sc["planes"]) == 2 and sc["planes"][0]["color"] == "#e3b23c"
    assert [k["atFrame"] for k in sc["camera3d"]] == [0, 180]  # `at` fraction -> frame (6s @30)
    # 3D scene doesn't get the 2D cinematic paths
    assert sc["layers"] is None and sc["lens"] is None and sc["stage"] is None


def test_camera3d_defaults_when_absent(tmp_path):
    sc = rr.build_props(_board(camera3d=None), str(tmp_path))["scenes"][0]
    assert sc["camera3d"] and len(sc["camera3d"]) == 2  # a gentle default crane is synthesized


def test_3d_scene_is_renderable(tmp_path):
    assert rr.unsupported_scenes(_board()) == []  # planes make it renderable without an image


def test_nan_plane_position_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="not finite|position"):
        rr.build_props(_board(planes=[{"position": [0, float("nan"), 0]}]), str(tmp_path))


def test_empty_planes_scene_is_flagged_unsupported(tmp_path):
    """A cinematic3d scene with no real content (planes empty) has nothing to draw — it must be flagged
    (would render blank), not silently pass. (An empty list collapses to 'no planes' via _scene_planes.)"""
    d = _board(); d["slides"][0]["planes"] = []
    assert rr.unsupported_scenes(d) == [(1, "cinematic3d")]


def test_props_json_finite(tmp_path):
    import json
    json.dumps(rr.build_props(_board(), str(tmp_path)), allow_nan=False)


# ── TS wiring source-guards ──────────────────────────────────────────────────────────────────────────
def test_threescene_exists_and_uses_threecanvas():
    src = open(os.path.join(_SKILL, "remotion", "src", "three", "ThreeScene.tsx"), encoding="utf-8").read()
    assert "ThreeCanvas" in src and "@remotion/three" in src
    assert "camera.lookAt" in src, "the frame-driven camera must aim at the scene"


def test_scene_dispatches_planes_to_threescene():
    src = open(os.path.join(_SKILL, "remotion", "src", "Scene.tsx"), encoding="utf-8").read()
    assert "ThreeScene" in src and "scene.planes" in src


def test_render_adds_gl_angle_for_3d():
    src = open(os.path.join(_SKILL, "scripts", "render_remotion.py"), encoding="utf-8").read()
    assert "--gl=angle" in src and 'sc.get("planes")' in src, "3D scenes must trigger the WebGL renderer flag"


def test_three_deps_installed():
    """@remotion/three + r3f v8 + three must be present (the render depends on them)."""
    nm = os.path.join(_SKILL, "remotion", "node_modules")
    for p in ("@remotion/three", "@react-three/fiber", "three"):
        assert os.path.isdir(os.path.join(nm, *p.split("/"))), "missing dep %s" % p
