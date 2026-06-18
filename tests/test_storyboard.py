import json, pytest
import storyboard as sb

def _minimal():
    return {
        "meta": {"aspect": "16:9", "width": 1920, "height": 1080, "fps": 30,
                 "voice": "say:Samantha", "captions": True},
        "slides": [{"index": 1, "image": "frames/01.png", "narration": "Hello."}],
    }

def test_roundtrip(tmp_path):
    p = tmp_path / "s.json"
    sb.save(_minimal(), str(p))
    got = sb.load(str(p))
    assert got["slides"][0]["narration"] == "Hello."

def test_validate_accepts_minimal():
    sb.validate(_minimal())  # no raise

def test_validate_rejects_missing_image():
    bad = _minimal(); del bad["slides"][0]["image"]
    with pytest.raises(sb.StoryboardError):
        sb.validate(bad)

def test_validate_rejects_callout_out_of_range():
    bad = _minimal()
    bad["slides"][0]["callouts"] = [{"at": 1.0, "box": [0.4, 0.3, 1.4, 0.5], "style": "highlight"}]
    with pytest.raises(sb.StoryboardError):
        sb.validate(bad)

def test_new_slide_defaults():
    s = sb.new_slide(2, "frames/02.png")
    assert s["index"] == 2 and s["narration"] == "" and s["callouts"] == []

def test_default_voice_is_auto():
    assert sb.new_storyboard()["meta"]["voice"] == "auto"

def test_new_slide_defaults_type_slide():
    s = sb.new_slide(1, "frames/01.png")
    assert s["type"] == "slide" and s["props"] is None

def test_new_scene_roundtrip(tmp_path):
    sc = sb.new_scene(2, "title", {"title": "Hello"}, narration="Hi.")
    assert sc["type"] == "title" and sc["props"] == {"title": "Hello"} and sc["image"] is None
    p = tmp_path / "s.json"; sb.save({"meta": {}, "slides": [sc]}, str(p))
    assert sb.load(str(p))["slides"][0]["props"]["title"] == "Hello"

def _wrap(scene):
    return {"meta": {"aspect": "16:9"}, "slides": [scene]}

def test_validate_slide_still_requires_image():
    bad = _wrap({"index": 1, "type": "slide", "narration": "x"})  # no image
    with pytest.raises(sb.StoryboardError):
        sb.validate(bad)

def test_validate_unknown_type_rejected():
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap({"index": 1, "type": "hologram", "narration": "x", "props": {}}))

def test_validate_title_ok_and_requires_title_str():
    sb.validate(_wrap(sb.new_scene(1, "title", {"title": "T", "subtitle": "S"}, "n")))
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(sb.new_scene(1, "title", {"subtitle": "S"}, "n")))  # missing title

def test_validate_chart_numbers_only():
    ok = sb.new_scene(1, "chart", {"kind": "bars", "data": [{"label": "a", "value": 5}]}, "n")
    sb.validate(_wrap(ok))
    bad = sb.new_scene(1, "chart", {"kind": "bars", "data": [{"label": "a", "value": "five"}]}, "n")
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(bad))
    badkind = sb.new_scene(1, "chart", {"kind": "pie", "data": [{"label": "a", "value": 5}]}, "n")
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(badkind))

def test_validate_timeline_requires_events():
    sb.validate(_wrap(sb.new_scene(1, "timeline", {"events": [{"date": "2026", "label": "x"}]}, "n")))
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(sb.new_scene(1, "timeline", {"events": []}, "n")))
