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


def test_plane_src_threads(tmp_path):
    """A plane's image `src` (textured onto a real 3D mesh) must thread through build_props."""
    sc = rr.build_props(_board(planes=[{"src": "assets/shot.png", "position": [0, 0, 0], "size": [5, 3.1]}]),
                        str(tmp_path))["scenes"][0]
    p = sc["planes"][0]
    assert p["src"] == "assets/shot.png" and p["size"] == [5.0, 3.1]


def test_bars_element_threads(tmp_path):
    """A `kind:'bars'` 3D element carries data (drives extruded bar heights) through build_props."""
    sc = rr.build_props(_board(planes=[{"kind": "bars", "position": [0, 0, 0], "data": [40, 65, 88],
                                         "labels": ["A", "B", "C"]}]), str(tmp_path))["scenes"][0]
    p = sc["planes"][0]
    assert p["kind"] == "bars" and p["data"] == [40.0, 65.0, 88.0] and p["labels"] == ["A", "B", "C"]


def test_bars_without_data_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="bars need a non-empty"):
        rr.build_props(_board(planes=[{"kind": "bars", "position": [0, 0, 0]}]), str(tmp_path))


def test_bad_plane_kind_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="kind must be"):
        rr.build_props(_board(planes=[{"kind": "pie", "position": [0, 0, 0]}]), str(tmp_path))


def test_bars3d_is_real_extruded_geometry():
    """Bars must be real 3D boxes that GROW by frame (born-in-3D data-viz), not a flat chart."""
    src = open(os.path.join(_SKILL, "remotion", "src", "three", "ThreeScene.tsx"), encoding="utf-8").read()
    assert "Bars3D" in src and "boxGeometry" in src, "bars are real extruded 3D boxes"
    assert "frame" in src and "EASE.out" in src, "bars grow from the floor, frame-driven + eased"


def test_text3d_rasterizes_to_a_textured_plane(tmp_path):
    """A `kind:'text'` 3D element is RASTERIZED (PIL) to a transparent PNG and becomes an alpha textured
    plane (billboarded) — troika/drei <Text> renders blank under Remotion, so we don't use it."""
    import os
    import theme as th
    th.write_theme_css({"bg": "#0e1116", "surface": "#141a24", "fg": "#f2f4f8", "muted": "#93a0b4",
                        "accent": "#e3b23c", "accent2": "#5fb3c9", "scrim": "rgba(14,17,22,.55)",
                        "on_accent": "#000", "on_accent2": "#000", "style": "editorial",
                        "style_vars": {"radius": "8px"}, "language": "en"}, str(tmp_path / "theme.css"))
    d = _board(planes=[{"kind": "text", "position": [0, 1.9, 0], "text": "Growth", "textColor": "#e3b23c"}])
    rr._rasterize_text3d(d, str(tmp_path))
    p = d["slides"][0]["planes"][0]
    assert p["kind"] == "plane" and p["alpha"] is True and p["billboard"] is True
    assert p["src"].startswith(".text3d") and os.path.isfile(tmp_path / p["src"])  # the PNG was written
    assert p["size"][0] > p["size"][1]  # "Growth" is wider than tall


def test_text3d_billboards_to_camera():
    """A billboard text plane must rotate to the current camera yaw (else it goes edge-on when orbited)."""
    src = open(os.path.join(_SKILL, "remotion", "src", "three", "ThreeScene.tsx"), encoding="utf-8").read()
    assert "camYaw" in src and "billboard" in src, "text planes billboard to face the camera"
    assert "transparent={!!alpha}" in src, "rasterized-text planes use a transparent material"


def test_texture_loads_at_dom_level_not_in_canvas():
    """Image textures MUST load in the DOM-level scene component (delayRender works there), not inside the
    R3F canvas children (a separate reconciler whose effects/delayRender aren't synced -> blank). And a
    screenshot renders UNLIT (meshBasicMaterial) so it shows at true pixel colours."""
    src = open(os.path.join(_SKILL, "remotion", "src", "three", "ThreeScene.tsx"), encoding="utf-8").read()
    assert "usePlaneTextures" in src and "delayRender" in src and "TextureLoader" in src
    assert "meshBasicMaterial" in src, "a UI screen must be unlit (true colours), not lit"
    assert "setCrossOrigin" in src, "WebGL needs a CORS-clean texture"


# ── TS wiring source-guards ──────────────────────────────────────────────────────────────────────────
def test_threescene_exists_and_uses_threecanvas():
    src = open(os.path.join(_SKILL, "remotion", "src", "three", "ThreeScene.tsx"), encoding="utf-8").read()
    assert "ThreeCanvas" in src and "@remotion/three" in src
    assert "camera.lookAt" in src, "the frame-driven camera must aim at the scene"


def test_scene_dispatches_planes_to_threescene():
    src = open(os.path.join(_SKILL, "remotion", "src", "Scene.tsx"), encoding="utf-8").read()
    assert "ThreeScene" in src and "scene.planes" in src


def test_render_adds_gl_flag_for_cinematic():
    src = open(os.path.join(_SKILL, "scripts", "render_remotion.py"), encoding="utf-8").read()
    # --gl is now added UNCONDITIONALLY for the cinematic tier (not only 3D `planes` scenes): TRUE-3D needs
    # WebGL, and the CSS-3D CinematicScene is ALSO GPU-bound — without a GL renderer it software-rasterises
    # and a peak-framing frame blows past the 30s/frame timeout (a whole scene once took >9min and FAILED).
    assert "--gl=" in src, "the cinematic tier must trigger the WebGL/ANGLE renderer flag"
    # backend is platform-branched: 'angle' on macOS/Windows, 'swangle' on GPU-less headless Linux/CI.
    assert '"angle"' in src and '"swangle"' in src, "GL backend must be platform-aware (angle / swangle)"
    # and a safety timeout so a slow frame degrades to 'slower', never a hard render failure.
    assert "--timeout=" in src, "raise the per-frame timeout for GPU-less peak-framing frames"


def test_three_deps_installed():
    """@remotion/three + r3f v8 + three must be present (the render depends on them)."""
    nm = os.path.join(_SKILL, "remotion", "node_modules")
    for p in ("@remotion/three", "@react-three/fiber", "three"):
        assert os.path.isdir(os.path.join(nm, *p.split("/"))), "missing dep %s" % p
