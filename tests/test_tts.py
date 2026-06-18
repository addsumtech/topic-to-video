import os, pytest
import tts, storyboard as sb, _common

def _proj(tmp_path):
    out = tmp_path / "proj"; os.makedirs(out, exist_ok=True)
    data = sb.new_storyboard()
    data["slides"] = [sb.new_slide(1, "frames/01.png", "Hello there."),
                      sb.new_slide(2, "frames/02.png", "Second slide narration.")]
    sb.save(data, os.path.join(out, "storyboard.json"))
    return str(out)

def test_edge_catalog_resolution():
    assert tts.resolve_edge_voice("en", "UK", "male") == "en-GB-RyanNeural"
    assert tts.resolve_edge_voice("zh", "Mainland", "female") == "zh-CN-XiaoxiaoNeural"
    assert tts.resolve_edge_voice("en") == "en-US-AriaNeural"      # default accent + gender
    assert tts.resolve_edge_voice("ja", gender="male") == "ja-JP-KeitaNeural"
    assert tts.resolve_edge_voice("EN-us", "uk") == "en-GB-SoniaNeural"  # case-insensitive
    assert tts.resolve_edge_voice("xx") is None                   # unknown language

@pytest.mark.skipif(not _common.have_tool("say"), reason="macOS 'say' only")
def test_synthesize_writes_audio_and_durations(tmp_path):
    out = _proj(tmp_path)
    data = tts.synthesize(out)
    for s in data["slides"]:
        assert s["audio"] and os.path.exists(os.path.join(out, s["audio"]))
        assert s["duration"] and s["duration"] > 0.2
