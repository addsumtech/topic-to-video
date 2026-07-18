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
    def fake_edge(text, dest, voice, rate="+0%"):
        with open(dest, "wb") as f:
            f.write(b"\x00")
        made.append((dest, voice, rate))
    monkeypatch.setattr(tts, "_edge", fake_edge)
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.0)

    res = tts.synthesize(out)
    assert made, "edge synthesis was not called"
    assert made[0][1] == "en-US-AriaNeural"
    assert made[0][2] == "+0%"                       # default speed -> no rate change
    assert all(s["audio"].endswith(".mp3") for s in res["slides"])
    assert all(s["duration"] == 1.0 for s in res["slides"])

def test_edge_rate_maps_tts_speed():
    assert tts._edge_rate({}) == "+0%"               # natural default
    assert tts._edge_rate({"tts_speed": 1.25}) == "+25%"
    assert tts._edge_rate({"tts_speed": 0.9}) == "-10%"
    assert tts._edge_rate({"tts_speed": "bad"}) == "+0%"   # invalid -> natural

def test_synthesize_passes_edge_rate_from_meta(tmp_path, monkeypatch):
    out = _proj(tmp_path)
    data = sb.load(os.path.join(out, "storyboard.json"))
    data["meta"].update({"voice": "auto", "language": "en", "tts_speed": 1.25})
    sb.save(data, os.path.join(out, "storyboard.json"))
    monkeypatch.setattr(tts, "_have_edge", lambda: True)
    seen = []
    def fake_edge(text, dest, voice, rate="+0%"):
        open(dest, "wb").write(b"\x00"); seen.append(rate)
    monkeypatch.setattr(tts, "_edge", fake_edge)
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.0)
    tts.synthesize(out)
    assert seen and all(r == "+25%" for r in seen)   # meta.tts_speed reaches the edge voice

@pytest.mark.skipif(not _common.have_tool("say"), reason="macOS 'say' only")
def test_synthesize_writes_audio_and_durations(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: False)
    out = _proj(tmp_path)
    data = tts.synthesize(out)
    for s in data["slides"]:
        assert s["audio"] and os.path.exists(os.path.join(out, s["audio"]))
        assert s["duration"] and s["duration"] > 0.2

# --- audio master / dead-air trim ------------------------------------------------------------

def _tone_clip(path, tone_s, lead_s=0.0, tail_s=0.0):
    """A test speech-stand-in: lead_s silence + tone_s of 440Hz + tail_s silence, at 24k/mono."""
    af = "sine=frequency=440:duration=%s" % tone_s
    filt = []
    if lead_s:
        filt.append("adelay=%d" % int(lead_s * 1000))
    if tail_s:
        filt.append("apad=pad_dur=%s" % tail_s)
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", af]
    if filt:
        cmd += ["-af", ",".join(filt)]
    cmd += ["-ar", "24000", "-ac", "1", path]
    _common.run(cmd)

@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_master_trims_trailing_dead_air(tmp_path):
    p = str(tmp_path / "a.mp3")
    _tone_clip(p, tone_s=1.0, tail_s=1.2)          # 2.2s: 1s speech + 1.2s tail
    before = _common.audio_duration(p)
    tts._master(p, {})
    after = _common.audio_duration(p)
    assert before > 2.0                            # sanity: the tail was really there
    assert after < 1.6                             # tail trimmed to ~1s speech + 0.12 pad
    assert after > 0.8                             # but the speech itself is NOT eaten

@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_master_preserves_leading_silence(tmp_path):
    # LEADING/internal timing must NOT move — edge-tts words.json times are relative to the start.
    p = str(tmp_path / "b.mp3")
    _tone_clip(p, tone_s=1.0, lead_s=0.4)          # 1.4s: 0.4s lead + 1s speech, no tail
    tts._master(p, {})
    after = _common.audio_duration(p)
    assert after > 1.3                             # ~0.4 lead + 1.0 speech (+pad) kept; not trimmed to ~1.1

@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_master_opt_out_leaves_clip_untouched(tmp_path):
    p = str(tmp_path / "c.mp3")
    _tone_clip(p, tone_s=1.0, tail_s=1.2)
    before = _common.audio_duration(p)
    tts._master(p, {"audio_master": False})
    assert abs(_common.audio_duration(p) - before) < 0.05

# --- MiniMax ---------------------------------------------------------------------------------

def test_minimax_voice_catalog():
    assert tts.resolve_minimax_voice("zh", "female") == "Chinese (Mandarin)_IntellectualGirl"
    assert tts.resolve_minimax_voice("en", "male") == "English_Trustworth_Man"
    assert tts.resolve_minimax_voice("xx") == tts.MINIMAX_DEFAULT_VOICE   # unlisted lang -> fallback

def test_minimax_voice_candidates():
    fem = tts.minimax_voice_candidates("en", "female")
    assert len(fem) >= 3 and fem[0] == "English_Graceful_Lady"
    assert tts.minimax_voice_candidates("zh", "male")[0] == "Chinese (Mandarin)_Reliable_Executive"
    assert tts.minimax_voice_candidates("xx") == []                      # no curated candidates
    # the first candidate for a (lang,gender) must equal the catalog default the bare voice resolves to
    for lang in ("en", "zh"):
        for g in ("female", "male"):
            assert tts.minimax_voice_candidates(lang, g)[0] == tts.resolve_minimax_voice(lang, g)

def test_resolve_voice_minimax_expands_and_passes_through():
    # bare "minimax" -> concrete catalog voice for the language; explicit voice_id passes through
    assert tts._resolve_voice({"voice": "minimax", "language": "zh"}) == \
        "minimax:Chinese (Mandarin)_IntellectualGirl"
    assert tts._resolve_voice({"voice": "minimax:auto", "language": "en", "voice_gender": "male"}) == \
        "minimax:English_Trustworth_Man"
    assert tts._resolve_voice({"voice": "minimax:English_Graceful_Lady", "language": "en"}) == \
        "minimax:English_Graceful_Lady"

def test_minimax_builds_request_and_decodes_hex(tmp_path, monkeypatch):
    captured = {}
    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"data": {"audio": b"ID3hello".hex(), "status": 2},
                    "base_resp": {"status_code": 0, "status_msg": "success"}}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, body=json); return FakeResp()
    import sys, types
    fake_requests = types.SimpleNamespace(post=fake_post)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setenv("MINIMAX_API_KEY", "secret-key")
    out = tmp_path / "o.mp3"
    tts._minimax("你好世界", str(out), "Chinese (Mandarin)_IntellectualGirl",
                 {"language": "zh", "tts_model": "speech-02-hd"})
    assert out.read_bytes() == b"ID3hello"                              # hex decoded to real bytes
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["body"]["voice_setting"]["voice_id"] == "Chinese (Mandarin)_IntellectualGirl"
    assert captured["body"]["language_boost"] == "Chinese"
    assert captured["body"]["output_format"] == "hex" and captured["body"]["audio_setting"]["format"] == "mp3"

def test_minimax_no_key_raises(monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setattr(tts, "_read_key_file", lambda p: None)   # ignore any real ~/.minimax_key
    with pytest.raises(RuntimeError, match="MINIMAX_API_KEY"):
        tts._minimax("hi", "/tmp/x.mp3", "English_Graceful_Lady", {"language": "en"})

def _fake_requests(handler):
    import sys, types
    return types.SimpleNamespace(post=handler)

def test_minimax_auto_region_falls_back_and_caches(tmp_path, monkeypatch):
    # A mainland key is rejected by the international host (2049); the skill must transparently try
    # the mainland host, succeed, and CACHE it so later slides skip the wasted intl probe.
    calls = []
    class R:
        def __init__(self, p): self._p = p
        def raise_for_status(self): pass
        def json(self): return self._p
    def post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        if "api.minimax.io" in url:
            return R({"base_resp": {"status_code": 2049, "status_msg": "invalid api key"}})
        return R({"data": {"audio": b"CN".hex()}, "base_resp": {"status_code": 0, "status_msg": "success"}})
    import sys
    monkeypatch.setitem(sys.modules, "requests", _fake_requests(post))
    monkeypatch.setenv("MINIMAX_API_KEY", "cn-key")
    monkeypatch.setattr(tts, "_MINIMAX_BASE_BY_KEY", {})
    out = tmp_path / "o.mp3"
    tts._minimax("你好", str(out), "Chinese (Mandarin)_IntellectualGirl", {"language": "zh"})
    assert out.read_bytes() == b"CN"
    assert any("api.minimax.io" in u for u in calls) and any("api.minimax.chat" in u for u in calls)
    calls.clear()
    tts._minimax("再见", str(out), "Chinese (Mandarin)_IntellectualGirl", {"language": "zh"})
    assert calls[0].startswith("https://api.minimax.chat"), "working host should be cached + tried first"

def test_minimax_explicit_base_does_not_switch_region(tmp_path, monkeypatch):
    # An explicit meta.minimax_base must be honored exactly — no silent cross-region retry.
    calls = []
    class R:
        def raise_for_status(self): pass
        def json(self): return {"base_resp": {"status_code": 2049, "status_msg": "invalid api key"}}
    def post(url, headers=None, json=None, timeout=None):
        calls.append(url); return R()
    import sys
    monkeypatch.setitem(sys.modules, "requests", _fake_requests(post))
    monkeypatch.setenv("MINIMAX_API_KEY", "k")
    monkeypatch.setattr(tts, "_MINIMAX_BASE_BY_KEY", {})
    with pytest.raises(RuntimeError, match="2049"):
        tts._minimax("hi", str(tmp_path / "x.mp3"), "English_Graceful_Lady",
                     {"language": "en", "minimax_base": "https://api.minimax.io/v1/t2a_v2"})
    assert len(calls) == 1, "explicit base must not try the other region"

def test_minimax_error_status_raises(tmp_path, monkeypatch):
    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"base_resp": {"status_code": 1004, "status_msg": "auth failed"}}
    import sys, types
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(
        post=lambda *a, **k: FakeResp()))
    monkeypatch.setenv("MINIMAX_API_KEY", "k")
    with pytest.raises(RuntimeError, match="1004"):
        tts._minimax("hi", str(tmp_path / "x.mp3"), "English_Graceful_Lady", {"language": "en"})

def test_minimax_failure_falls_back_to_say(tmp_path, monkeypatch):
    out = _proj(tmp_path)
    data = sb.load(os.path.join(out, "storyboard.json"))
    data["meta"]["voice"] = "minimax:English_Graceful_Lady"; data["meta"]["language"] = "en"
    sb.save(data, os.path.join(out, "storyboard.json"))
    def boom(*a, **k): raise RuntimeError("no MINIMAX_API_KEY")
    said = []
    monkeypatch.setattr(tts, "_minimax", boom)
    monkeypatch.setattr(tts, "_say", lambda text, dest, voice, rate=175: (
        said.append(voice), open(dest, "wb").write(b"\x00")))
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.0)
    res = tts.synthesize(out)
    assert said, "minimax failure should fall back to say"
    assert all(s["audio"].endswith(".aiff") for s in res["slides"])

def test_minimax_removes_stale_words_json(tmp_path, monkeypatch):
    # switching from edge to minimax must drop leftover per-word timings (they'd mis-cue reveals)
    out = _proj(tmp_path)
    data = sb.load(os.path.join(out, "storyboard.json"))
    data["meta"]["voice"] = "minimax:English_Graceful_Lady"; data["meta"]["language"] = "en"
    sb.save(data, os.path.join(out, "storyboard.json"))
    os.makedirs(os.path.join(out, "audio"), exist_ok=True)
    stale = os.path.join(out, "audio", "01.words.json")
    open(stale, "w").write('[{"w":"x","t":0.1}]')
    monkeypatch.setattr(tts, "_minimax", lambda text, dest, voice, meta: open(dest, "wb").write(b"\x00"))
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.0)
    tts.synthesize(out)
    assert not os.path.exists(stale), "stale words.json should be removed for the minimax provider"


def test_empty_narration_uses_silence_not_say(tmp_path, monkeypatch):
    # a blank-narration beat (divider / pre-script ingest) must NOT crash and must NOT call say ' ' —
    # it gets a real short silent clip and a floored duration so the slide holds on screen.
    out = tmp_path / "proj"; os.makedirs(out, exist_ok=True)
    data = sb.new_storyboard()
    data["meta"]["voice"] = "say:Samantha"
    data["slides"] = [sb.new_slide(1, "frames/01.png", "Hello there."),
                      sb.new_slide(2, "frames/02.png", "")]   # slide 2 SILENT
    sb.save(data, os.path.join(out, "storyboard.json"))
    said, silenced = [], []
    monkeypatch.setattr(tts, "_say", lambda text, dest, voice, rate=175: (said.append(text), open(dest, "wb").write(b"\x00")))
    monkeypatch.setattr(tts, "_silence", lambda dest, seconds=1.2: (silenced.append(dest), open(dest, "wb").write(b"\x00")))
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.2)
    res = tts.synthesize(str(out))
    assert len(silenced) == 1 and silenced[0].endswith("02.aiff")     # silent clip for the blank slide
    assert " " not in said                                            # never synthesized a bare space
    assert res["slides"][1]["duration"] >= 1.0                        # floored so it holds
