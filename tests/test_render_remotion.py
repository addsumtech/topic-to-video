import os
import pytest
import render_remotion as rr
import storyboard as sb


def _board(**meta):
    m = {"language": "en", "aspect": "16:9", "captions": True, "fps": 30, "renderer": "remotion"}
    m.update(meta)
    data = sb.new_storyboard(m)
    s = sb.new_scene(1, "title", {"kicker": "K", "title": "T"}, narration="Alpha beta gamma delta.")
    s["image"] = ".assets/x.png"; s["audio"] = "audio/01.mp3"; s["duration"] = 4.0
    s["transition"] = "dip"; s["transition_seconds"] = 0.2
    data["slides"] = [s]
    return data


def test_build_props_image_scene(tmp_path):
    p = rr.build_props(_board(), str(tmp_path))
    assert (p["width"], p["height"], p["fps"]) == (1920, 1080, 30)
    sc = p["scenes"][0]
    assert sc["durationInFrames"] == 120                 # 4.0s * 30fps
    assert sc["image"] == ".assets/x.png" and sc["audio"] == "audio/01.mp3"
    assert sc["kenburns"] is True and sc["title"] == "T" and sc["kicker"] == "K"
    assert sc["fadeInFrames"] == 6 and sc["fadeOutFrames"] == 6    # dip 0.2s * 30
    assert sc["captions"] and sc["captions"][0]["from"] == 0 and sc["captions"][-1]["to"] <= 120


def test_build_props_reduced_motion_no_kenburns(tmp_path):
    assert rr.build_props(_board(reduced_motion=True), str(tmp_path))["scenes"][0]["kenburns"] is False


def test_build_props_reduced_motion_param(tmp_path):
    # the CLI-style reduced_motion arg (not just meta) disables Ken Burns
    assert rr.build_props(_board(), str(tmp_path), reduced_motion=True)["scenes"][0]["kenburns"] is False


def test_build_props_threads_motion_fit_and_fontsize(tmp_path):
    d = _board()
    d["slides"][0]["motion"] = {"from": [0.3, 0.4, 1.0], "to": [0.6, 0.5, 1.2]}
    d["slides"][0]["fit"] = "cover"
    p = rr.build_props(d, str(tmp_path))
    sc = p["scenes"][0]
    assert sc["motion"] == {"from": [0.3, 0.4, 1.0], "to": [0.6, 0.5, 1.2]}   # honours slide.motion
    assert sc["fit"] == "cover"
    assert p["captionFontPx"] == int(min(1920, 1080) * 0.040)                 # canvas-derived (== 43)


def test_build_props_default_motion_and_fit(tmp_path):
    sc = rr.build_props(_board(), str(tmp_path))["scenes"][0]
    assert sc["motion"] == {"from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]}  # storyboard default
    assert sc["fit"] == "contain"                                            # local default


def test_build_props_threads_callouts(tmp_path):
    d = _board()
    d["slides"][0]["callouts"] = [{"box": [0.1, 0.2, 0.5, 0.6], "style": "highlight", "label": "here", "at": 0.5}]
    co = rr.build_props(d, str(tmp_path))["scenes"][0]["callouts"]
    assert len(co) == 1
    assert co[0]["box"] == [0.1, 0.2, 0.5, 0.6] and co[0]["style"] == "highlight" and co[0]["label"] == "here"
    assert co[0]["fromFrame"] == int(round(0.5 * 4.0 * 30))   # at=0.5 * dur 4.0s * 30fps = 60


def test_unsupported_scenes_flags_html_not_image(tmp_path):
    d = sb.new_storyboard({"renderer": "remotion"})
    s1 = sb.new_scene(1, "html", {"html": "pages/x.html"}, narration="a"); s1["duration"] = 3; s1["audio"] = "audio/01.mp3"
    s2 = sb.new_scene(2, "slide", {}, narration="b"); s2["image"] = ".assets/i.png"; s2["duration"] = 3; s2["audio"] = "audio/02.mp3"
    s3 = sb.new_scene(3, "title", {"title": "T"}, narration="c"); s3["duration"] = 3; s3["audio"] = "audio/03.mp3"
    d["slides"] = [s1, s2, s3]
    assert rr.unsupported_scenes(d) == [(1, "html")]   # html blanks; image slide + title card are fine


def test_build_props_captions_off(tmp_path):
    assert rr.build_props(_board(captions=False), str(tmp_path))["scenes"][0]["captions"] == []


def test_build_props_vertical(tmp_path):
    p = rr.build_props(_board(aspect="9:16"), str(tmp_path))
    assert (p["width"], p["height"]) == (1080, 1920)


def test_build_props_scene_without_image_is_card(tmp_path):
    d = _board()
    d["slides"][0]["image"] = None
    sc = rr.build_props(d, str(tmp_path))["scenes"][0]
    assert sc["image"] is None and sc["kenburns"] is False   # no image => no Ken Burns, renders as title/caption card


def test_edges_semantics():
    meta = {"fps": 30}
    assert rr._edges({"transition": "dip", "transition_seconds": 0.2}, meta, 30) == (6, 6)
    assert rr._edges({"transition": "in", "transition_seconds": 0.3}, meta, 30) == (9, 0)
    assert rr._edges({"transition": "out", "transition_seconds": 0.3}, meta, 30) == (0, 9)
    assert rr._edges({"transition": "none"}, meta, 30) == (0, 0)


def test_theme_parses_vars(tmp_path):
    open(os.path.join(str(tmp_path), "theme.css"), "w").write(":root{--bg:#111111;--accent:#5fb3c4;}")
    t = rr._theme(str(tmp_path))
    assert t["bg"] == "#111111" and t["accent"] == "#5fb3c4" and t["fg"]   # fg falls back to default


def test_theme_fallback_no_file(tmp_path):
    assert rr._theme(str(tmp_path))["bg"] == "#0d1117"


def test_validate_flags_remotion_nonimage_scene(tmp_path):
    import os
    import validate
    os.makedirs(os.path.join(str(tmp_path), "pages"), exist_ok=True)
    os.makedirs(os.path.join(str(tmp_path), "audio"), exist_ok=True)
    open(os.path.join(str(tmp_path), "pages", "x.html"), "w").write("<div class='stage'>x</div>")
    open(os.path.join(str(tmp_path), "audio", "01.mp3"), "wb").write(b"\x00")
    d = sb.new_storyboard({"renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "html", {"html": "pages/x.html"}, narration="a"); s["duration"] = 3.0; s["audio"] = "audio/01.mp3"
    d["slides"] = [s]
    sb.save(d, os.path.join(str(tmp_path), "storyboard.json"))
    r = validate.evaluate(d, str(tmp_path))
    assert not r["ok"] and any("renderer=remotion" in e and "BLANK" in e for e in r["errors"])


def test_renderer_meta_validation():
    ok = sb.new_storyboard({"renderer": "remotion"})
    ok["slides"] = [sb.new_scene(1, "title", {"title": "x"}, narration="x")]
    sb.validate(ok)                                          # valid renderer -> no raise
    bad = sb.new_storyboard({"renderer": "nope"})
    bad["slides"] = [sb.new_scene(1, "title", {"title": "x"}, narration="x")]
    with pytest.raises(sb.StoryboardError):
        sb.validate(bad)


# ── cinematic tier: additive camera + 2.5D layers (Phase 0 spine) ─────────────────────────────────
def _cine_board(**meta):
    m = {"aspect": "16:9", "fps": 30, "renderer": "remotion"}
    m.update(meta)
    data = sb.new_storyboard(m)
    s = sb.new_scene(1, "cinematic", {}, narration="Alpha beta gamma.")
    s["audio"] = "audio/01.mp3"; s["duration"] = 6.0
    s["layers"] = [{"kind": "grid", "parallax": 0.82}, {"kind": "panel", "parallax": 1.28, "title": "T"}]
    s["camera"] = [{"atFrame": 0, "x": 0.5, "y": 0.5, "zoom": 1.0, "easing": "inout"},
                   {"atFrame": 180, "x": 0.44, "y": 0.54, "zoom": 1.12, "easing": "inout"}]
    data["slides"] = [s]
    return data


def test_build_props_threads_camera_and_layers(tmp_path):
    sc = rr.build_props(_cine_board(), str(tmp_path))["scenes"][0]
    assert sc["layers"] and len(sc["layers"]) == 2
    assert sc["camera"] and sc["camera"][0]["atFrame"] == 0
    assert sc["camera"][-1]["zoom"] == 1.12 and sc["camera"][-1]["easing"] == "inout"
    assert sc["reducedMotion"] is False


def test_layered_scene_synthesizes_default_camera(tmp_path):
    d = _cine_board(); d["slides"][0].pop("camera", None)
    sc = rr.build_props(d, str(tmp_path))["scenes"][0]
    # a layered scene with no camera gets a gentle default eased push-in (so `layers` alone is cinematic)
    assert sc["camera"] and len(sc["camera"]) == 2 and sc["camera"][-1]["zoom"] > 1.0


def test_layered_scene_is_not_unsupported(tmp_path):
    d = _cine_board(); d["slides"][0].pop("image", None)
    assert rr.unsupported_scenes(d) == []                 # layers make it renderable without an image


def test_non_image_non_layer_scene_is_unsupported():
    d = _cine_board(); s = d["slides"][0]
    s.pop("layers", None); s.pop("camera", None); s.pop("image", None); s["type"] = "chart"
    assert any(i == 1 for i, _ in rr.unsupported_scenes(d))


def test_reduced_motion_flag_threads_to_cinematic_scene(tmp_path):
    sc = rr.build_props(_cine_board(), str(tmp_path), reduced_motion=True)["scenes"][0]
    assert sc["reducedMotion"] is True


# ── cinematic 3D LENS tier (perspective + dolly/pitch/yaw over translateZ planes) ─────────────────
def _lens_board(**meta):
    m = {"aspect": "16:9", "fps": 30, "renderer": "remotion"}
    m.update(meta)
    data = sb.new_storyboard(m)
    s = sb.new_scene(1, "cinematic", {}, narration="Depth.")
    s["audio"] = "audio/01.mp3"; s["duration"] = 6.0; s["perspective"] = 1250
    s["layers"] = [{"kind": "grid", "z": -1200, "blur": 8}, {"kind": "panel", "z": 120, "title": "T"}]
    s["lens"] = [{"atFrame": 0, "dolly": -500, "pitch": 30, "yaw": 10, "easing": "inout"},
                 {"atFrame": 180, "dolly": 200, "pitch": 4, "yaw": -2, "easing": "inout"}]
    data["slides"] = [s]
    return data


def test_build_props_threads_lens_and_perspective(tmp_path):
    sc = rr.build_props(_lens_board(), str(tmp_path))["scenes"][0]
    assert sc["lens"] and sc["lens"][0]["dolly"] == -500 and sc["lens"][-1]["pitch"] == 4
    assert sc["perspective"] == 1250 and sc["layers"][0]["z"] == -1200
    assert sc["camera"] is None                          # a lens scene is NOT also given a flat camera


def test_lens_scene_not_unsupported(tmp_path):
    d = _lens_board(); d["slides"][0].pop("image", None)
    assert rr.unsupported_scenes(d) == []                 # layers make it renderable
