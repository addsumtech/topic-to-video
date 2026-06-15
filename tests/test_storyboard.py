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
