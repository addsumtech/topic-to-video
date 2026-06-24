import os, pytest
import tts, storyboard as sb, _common

def test_words_from_boundaries():
    chunks = [{"type": "audio", "data": b"x"},
              {"type": "WordBoundary", "text": "Dujiangyan", "offset": 20000000},
              {"type": "WordBoundary", "text": "Leshan", "offset": 60000000}]
    assert tts._words_from_boundaries(chunks) == [{"w": "Dujiangyan", "t": 2.0}, {"w": "Leshan", "t": 6.0}]

def test_words_from_boundaries_empty():
    assert tts._words_from_boundaries([{"type": "audio", "data": b"x"}]) == []

def test_synthesize_only_zero_targets_slide_0(tmp_path, monkeypatch):
    """--only 0 must synthesize ONLY slide 0 — the old `if only:` was falsy for 0 and synthesized all."""
    out = tmp_path / "proj"; os.makedirs(out, exist_ok=True)
    data = sb.new_storyboard()
    data["meta"]["voice"] = "say:Samantha"
    data["slides"] = [sb.new_slide(0, "frames/00.png", "zero"),
                      sb.new_slide(1, "frames/01.png", "one")]
    sb.save(data, os.path.join(out, "storyboard.json"))
    done = []
    def fake_say(text, dest, voice, rate=175):
        done.append(dest)
        with open(dest, "wb") as f:
            f.write(b"\x00")
    monkeypatch.setattr(tts, "_say", fake_say)
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.0)
    tts.synthesize(str(out), only=0)
    assert len(done) == 1 and done[0].endswith("00.aiff"), f"only slide 0 should synth, got {done}"

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

def test_edge_failure_falls_back_to_language_matched_say(tmp_path, monkeypatch):
    # When edge synthesis throws (e.g. endpoint reset), the synth-time fallback must use
    # the language-matched say voice — NOT hardcoded English Samantha — for a zh project.
    out = tmp_path / "proj"; os.makedirs(out, exist_ok=True)
    data = sb.new_storyboard()
    data["meta"]["voice"] = "edge:zh-CN-XiaoxiaoNeural"
    data["meta"]["language"] = "zh"
    data["slides"] = [sb.new_slide(1, "frames/01.png", "你好，这是测试。")]
    sb.save(data, os.path.join(out, "storyboard.json"))

    def boom(*a, **k):
        raise RuntimeError("edge endpoint reset")
    monkeypatch.setattr(tts, "_edge", boom)
    used = {}
    def fake_say(text, dest, voice, rate=175):
        used["voice"] = voice
        with open(dest, "wb") as f:
            f.write(b"\x00")
    monkeypatch.setattr(tts, "_say", fake_say)
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.0)

    tts.synthesize(str(out))
    assert used["voice"] == "Tingting"   # zh -> Tingting, not Samantha

def test_resolve_voice_auto_prefers_edge(monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: True)
    assert tts._resolve_voice({"voice": "auto", "language": "en"}) == "edge:en-US-AriaNeural"
    assert tts._resolve_voice({"voice": "auto", "language": "zh"}) == "edge:zh-CN-XiaoxiaoNeural"

def test_resolve_voice_auto_falls_back_to_say(monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: False)
    assert tts._resolve_voice({"voice": "auto", "language": "zh"}) == "say:Tingting"
    assert tts._resolve_voice({"voice": "auto", "language": "en"}) == "say:Samantha"

def test_resolve_voice_passthrough_explicit():
    assert tts._resolve_voice({"voice": "edge:en-GB-RyanNeural", "language": "en"}) == "edge:en-GB-RyanNeural"
    assert tts._resolve_voice({"voice": "openai:alloy", "language": "en"}) == "openai:alloy"
    assert tts._resolve_voice({"voice": "say:Alex", "language": "en"}) == "say:Alex"

def test_resolve_voice_auto_edge_unknown_language_falls_back_to_say(monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: True)
    # 'xx' is not in EDGE_VOICE_CATALOG -> resolve_edge_voice returns None -> must use say
    result = tts._resolve_voice({"voice": "auto", "language": "xx"})
    assert result.startswith("say:")

def test_synthesize_uses_edge_when_resolved(tmp_path, monkeypatch):
    out = _proj(tmp_path)
    data = sb.load(os.path.join(out, "storyboard.json"))
    data["meta"]["voice"] = "auto"; data["meta"]["language"] = "en"
    sb.save(data, os.path.join(out, "storyboard.json"))

    monkeypatch.setattr(tts, "_have_edge", lambda: True)
    made = []
    def fake_edge(text, dest, voice):
        with open(dest, "wb") as f:
            f.write(b"\x00")
        made.append((dest, voice))
    monkeypatch.setattr(tts, "_edge", fake_edge)
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.0)

    res = tts.synthesize(out)
    assert made, "edge synthesis was not called"
    assert made[0][1] == "en-US-AriaNeural"
    assert all(s["audio"].endswith(".mp3") for s in res["slides"])
    assert all(s["duration"] == 1.0 for s in res["slides"])

@pytest.mark.skipif(not _common.have_tool("say"), reason="macOS 'say' only")
def test_synthesize_writes_audio_and_durations(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: False)
    out = _proj(tmp_path)
    data = tts.synthesize(out)
    for s in data["slides"]:
        assert s["audio"] and os.path.exists(os.path.join(out, s["audio"]))
        assert s["duration"] and s["duration"] > 0.2
