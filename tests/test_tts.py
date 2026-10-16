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
    assert len(done) == 1 and done[0].endswith("00.wav"), f"only slide 0 should synth, got {done}"

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
    # READ from the catalogue, not restated. Pinning the literal name made three tests fail the moment a
    # default was replaced for a measured reason — they check the RESOLUTION CHAIN (default accent, default
    # gender), and the name is the catalogue's business. Which voice is allowed to be the default is a
    # separate question, checked by its own test against the F0 measurements.
    _EN = tts.EDGE_VOICE_CATALOG["en"]["US"]["female"]
    assert tts.resolve_edge_voice("en") == _EN                     # default accent + gender
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

class NoAudioReceived(Exception):
    """Named like edge_tts.exceptions.NoAudioReceived — the classifier reads the type's name."""


def test_a_transient_edge_failure_is_retried_before_the_film_changes_voice(tmp_path, monkeypatch):
    """Measured: 8 of 40 lines failed once with "No audio was received" and fell back to `say` — a mixed-voice
    film — though every one spoke within three attempts. A transient failure is retried; a 403 is not."""
    out = tmp_path / "proj"; os.makedirs(out, exist_ok=True)
    data = sb.new_storyboard()
    data["meta"]["voice"] = "edge:en-US-EmmaNeural"
    data["meta"]["language"] = "en"
    data["slides"] = [sb.new_slide(1, "frames/01.png", "Hello there.")]
    sb.save(data, os.path.join(out, "storyboard.json"))
    calls = []

    def flaky(text, dest, voice, rate="+0%"):
        calls.append(1)
        if len(calls) < 3:
            raise NoAudioReceived("No audio was received.")
        with open(dest, "wb") as f:
            f.write(b"\x00")
    monkeypatch.setattr(tts, "_edge", flaky)
    monkeypatch.setattr(tts, "EDGE_BACKOFF", (0.0, 0.0))
    said = []
    monkeypatch.setattr(tts, "_say", lambda *a, **k: said.append(a))
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.0)
    monkeypatch.setattr(tts, "_master", lambda *a, **k: None, raising=False)
    tts.synthesize(str(out))
    assert len(calls) == 3 and not said, (calls, said)

    calls.clear()
    def forbidden(*a, **k):
        calls.append(1)
        raise RuntimeError("Invalid response status 403")
    monkeypatch.setattr(tts, "_edge", forbidden)
    with pytest.raises(RuntimeError):
        tts.speak_retrying("x", str(out / "a.mp3"), data["meta"], "edge", "en-US-EmmaNeural", sleep=lambda s: None)
    assert len(calls) == 1, "a 403 names its own cause and must not be retried"


def test_resolve_voice_auto_prefers_edge(monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: True)
    assert tts._resolve_voice({"voice": "auto", "language": "en"}) == (
        "edge:" + tts.EDGE_VOICE_CATALOG["en"]["US"]["female"])
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
    assert made[0][1] == tts.EDGE_VOICE_CATALOG["en"]["US"]["female"]
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
    assert all(s["audio"].endswith(".wav") for s in res["slides"])

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
    assert len(silenced) == 1 and silenced[0].endswith("02.wav")     # silent clip for the blank slide
    assert " " not in said                                            # never synthesized a bare space
    assert res["slides"][1]["duration"] >= 1.0                        # floored so it holds


@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_master_breath_is_tunable(tmp_path):
    # the re-padded tail IS the between-scene breath: default ~0.42s, meta.audio_breath overrides
    a = str(tmp_path / "a.mp3"); b = str(tmp_path / "b.mp3")
    _tone_clip(a, tone_s=1.0, tail_s=1.5); _tone_clip(b, tone_s=1.0, tail_s=1.5)
    tts._master(a, {})                                   # default breath 0.42
    tts._master(b, {"audio_breath": 0.9})
    da, db = _common.audio_duration(a), _common.audio_duration(b)
    assert 1.25 <= da <= 1.65                            # ~1.0 speech + 0.42 breath
    assert db - da > 0.3                                 # bigger breath -> audibly longer tail


def test_scene_pause_is_what_the_viewer_hears_on_both_tiers():
    # MEASURED REGRESSION on a delivered 37-beat remotion film: the tail pad and the cross-dissolve were
    # both ~0.4s, and the dissolve overlaps the AUDIO, so every one of the 36 seams carried 0.15-0.24s of
    # silence (mean 0.18) while the narration's own within-sentence comma pauses ran to 0.55s. The pause
    # between two scenes was shorter than the pause between two clauses. `scene_pause` is now the AUDIBLE
    # gap and each tier converts it to a pad; the two tiers must agree.
    import os
    import re as _re
    import tts
    # The truth about the dissolve is motion.ts, parsed HERE independently. Measuring the pad against
    # tts._seam_seconds() would be self-referential: stubbing that function to 0 keeps the arithmetic
    # consistent while the real film regresses to a 0.02s seam. (That mutation passed the first draft
    # of this test.)
    _mt = open(os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "runtime", "motion.ts"),
               encoding="utf-8").read()
    SEAM = int(_re.search(r"export const SEAM_FRAMES\s*=\s*(\d+)", _mt).group(1))

    def _eats(meta):
        return SEAM / float(meta.get("fps", 30)) if meta["renderer"] == "remotion" else 0.0

    for pause in (0.35, 0.55, 0.9):
        rem = {"renderer": "remotion", "fps": 30, "scene_pause": pause}
        htm = {"renderer": "html", "fps": 30, "scene_pause": pause}
        # ONE definition, called — not re-derived here. Both of these lines used to restate the formula
        # and both went stale the moment the room tail was added to the chain.
        audible_rem = tts.audible_pause(rem)
        audible_htm = tts.audible_pause(htm)
        assert abs(audible_rem - pause) < 1e-6, (pause, audible_rem)
        assert abs(audible_htm - pause) < 1e-6, (pause, audible_htm)
        assert abs(audible_rem - audible_htm) < 1e-6, "the two tiers no longer sound the same"
    # the remotion pad MUST exceed the dissolve, or the pause collapses to nothing
    rem = {"renderer": "remotion", "fps": 30}
    assert tts._tail_pad(rem) > _eats(rem) + 0.2, "default pad does not clear the dissolve"
    # the seam length is READ from motion.ts, never duplicated — 24fps must halve it, not keep 0.40s
    assert abs(tts._seam_seconds({"renderer": "remotion", "fps": 60})
               - tts._seam_seconds({"renderer": "remotion", "fps": 30}) / 2) < 1e-6
    # an explicit audio_breath stays the RAW pad (boards that set it meant the pad, not the pause)
    assert abs(tts._tail_pad({"renderer": "remotion", "fps": 30, "audio_breath": 0.42}) - 0.42) < 1e-6
    # the between-scene pause must be at least as long as a within-sentence pause, or it reads backwards
    assert tts.SCENE_PAUSE_DEFAULT >= 0.5


def test_a_clip_ends_in_a_decay_not_a_cliff():
    """Reported as "every frame's last sentence sounds stopped rather than finished".

    Mastering trimmed the trailing silence at -45dB — which removes the whole natural decay of the last
    syllable — and then spliced ABSOLUTE silence onto the cut. Measured on three delivered clips, the
    envelope fell 64, 88 and 67 dB inside one 20ms window; at 5ms the worst single step was 42 dB, from
    -12 (clearly audible) straight to -49. A voice does not stop like that, and the ear hears the cut.

    This runs the real mastering chain over a synthetic clip that ends abruptly and measures the shape.
    """
    import array
    import inspect
    import math
    import re
    import subprocess
    import tempfile
    import tts
    if not _common.have_tool("ffmpeg"):
        import pytest
        pytest.skip("ffmpeg not available")
    d = tempfile.mkdtemp()
    clip = os.path.join(d, "c.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "sine=frequency=300:duration=1.2:sample_rate=48000", clip], check=True)
    tts._master(clip, {"renderer": "remotion", "fps": 30})

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", clip, "-ac", "1", "-ar", "48000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = array.array("h")
    x.frombytes(raw)
    win = int(0.005 * 48000)
    env = []
    for i in range(0, len(x) - win, win):
        pk = max((abs(v) for v in x[i:i + win]), default=0)
        env.append(20 * math.log10(pk / 32768.0) if pk else -99.0)
    assert env, "the mastered clip decoded to nothing"
    audible = [i for i, v in enumerate(env) if v > -60]
    assert audible, "no audible content survived mastering"
    last = max(audible)
    tail = env[max(0, last - 11):last + 2]
    worst = max(tail[i] - tail[i + 1] for i in range(len(tail) - 1))
    assert worst < 25, ("the tail falls %.0f dB in one 5ms step — that is a cut, not a decay: %s"
                        % (worst, [round(v) for v in tail]))
    # and the decay must actually reach inaudibility before the clip is cut
    assert min(tail) < -40, "the clip is still audible where it ends: %s" % [round(v) for v in tail]

    # THE TRIM THRESHOLD is load-bearing too, but only on a signal that HAS a decay tail — a pure tone
    # has nothing between -58 and -45 to preserve, so the synthetic clip above cannot see it. On one that
    # decays, trimming at -45 throws away 105ms of real tail that -58 keeps.
    dec = os.path.join(d, "decay.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "sine=frequency=300:duration=1.5:sample_rate=48000",
                    "-af", "afade=t=out:st=0.6:d=0.9:curve=exp", dec], check=True)
    # ISOLATE THE TRIM. This used to run the whole master chain and measure what survived — which
    # measures the FADE as much as the threshold, because the fade attenuates the last fifth of a second
    # by design. Lengthening the die-away from 0.10s to 0.18s (a real repair, made because the endings
    # were heard as stopping dead) dropped this number 0.895 -> 0.845 and turned the test red for doing
    # its job. A test whose assertion names one thing and whose measurement includes another will fail on
    # the next correct change too. So the trim runs here WITHOUT the fade, with the threshold read out of
    # tts.py so the two cannot drift.
    m = re.search(r"start_threshold=(-?\d+)dB", inspect.getsource(tts._master))
    assert m, "the trim threshold is no longer written as start_threshold=<n>dB in tts._master"
    trim_only = ("loudnorm=I=-14:TP=-1.5:LRA=11,areverse,"
                 "silenceremove=start_periods=1:start_duration=0.06:"
                 "start_threshold=%sdB:detection=peak,areverse" % m.group(1))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", dec, "-af", trim_only,
                    "-map_metadata", "-1", dec + ".trim.wav"], check=True)
    raw2 = subprocess.run(["ffmpeg", "-v", "error", "-i", dec + ".trim.wav", "-ac", "1", "-ar", "48000",
                           "-f", "s16le", "-"], capture_output=True).stdout
    y = array.array("h")
    y.frombytes(raw2)
    env2 = []
    for i in range(0, len(y) - win, win):
        pk = max((abs(v) for v in y[i:i + win]), default=0)
        env2.append(20 * math.log10(pk / 32768.0) if pk else -99.0)
    kept = max(i for i, v in enumerate(env2) if v > -60) * 0.005
    # Measured through the TRIM ALONE (loudnorm shifts the levels, so these are not raw-signal numbers,
    # and they are not the whole-chain numbers either — isolating the fade moved every one of them):
    #   -45dB keeps 0.860s of this fixture   -58dB keeps 0.975s   -70/-85/-99dB all keep 1.060s
    # The bar was 0.92, calibrated when -58 was shipped — which let a regression from -85 back to -58 pass.
    # Measured on real speech, that regression deletes the decay the source actually has (edge zh 55ms -> 5,
    # edge en 130 -> 10, say zh 35 -> 0) and ends the clip at -22dB instead of -75. The bar sits above
    # -58's 0.975 now, so only a threshold low enough to keep a real tail passes.
    assert kept > 1.02, ("only %.3fs of a decaying signal survived the trim — the threshold is cutting "
                         "into the natural tail (-58dB keeps 0.975s here, -85dB keeps 1.060s)" % kept)


# F0 standard deviation in semitones, measured over voiced frames on ONE identical sentence per voice
# (zh and en each got their own). A flat contour is where machine-ness lives, so this is the axis the
# default was chosen on. Not a quality score: it measures whether a voice is FLAT, and cannot tell natural
# from theatrical — which is why the shortlist went to a listener before anything shipped.
_VOICE_F0_SD = {
    "zh-CN-YunjianNeural": 6.93, "zh-CN-YunyangNeural": 6.88, "zh-CN-YunxiNeural": 4.61,
    "zh-CN-XiaoxiaoNeural": 4.05, "zh-CN-XiaoyiNeural": 3.62,
    "en-US-EmmaNeural": 4.89, "en-US-AndrewNeural": 4.77, "en-US-GuyNeural": 4.06,
    "en-US-MichelleNeural": 3.74, "en-US-AvaNeural": 3.49, "en-US-AriaNeural": 3.38,
    "en-US-JennyNeural": 2.82, "en-US-BrianNeural": 2.54,
}


def test_the_default_edge_voice_is_not_one_of_the_flat_ones():
    """The en/zh defaults were the oldest generation in the catalogue and nobody had gone back.

    Microsoft's list splits into News/Novel announcers (Aria, Guy, Yunxi — what this table was built from)
    and a Conversation/Copilot set written for dialogue (Ava, Emma, Andrew, Brian). Read aloud, the
    announcers are the ones that sound read. Measured on one identical sentence per language, the shipped
    defaults sat well down the pitch-movement ranking: Aria 3.38 against Emma's 4.89, Guy 4.06 against
    Andrew's 4.77, Yunxi 4.61 against Yunyang's 6.88.

    This pins the EVIDENCE rather than the name — a different voice may well be better, and should be able
    to ship without editing a test, but not one already measured flatter than what it replaces. The
    generation label is deliberately not the rule either: Brian is a Copilot voice and measured flattest of
    all thirteen, so "newer" would have been the wrong criterion.
    """
    import tts
    # what each slot shipped BEFORE this change — the floor a replacement may not fall under. Deliberately
    # not "must be the highest measured": Yunjian scores 6.93, above the chosen Yunyang's 6.88, and was
    # rejected anyway because Passion/Sports energy is not naturalness. A floor blocks the regression this
    # test exists for without pretending the metric can rank the top of the field.
    # The floor is the value a replacement must BEAT, not the value it replaced — set to the old
    # measurement it must clear. Written as ">= the old value" the first time, reverting to the old voice
    # passed by construction: a floor a candidate satisfies by BEING the thing you moved away from is not
    # a floor. The one unchanged slot keeps its own number.
    was = {("en", "female"): 3.5,    # must beat en-US-AriaNeural's 3.38
           ("en", "male"): 4.2,      # must beat en-US-GuyNeural's 4.06
           ("zh", "female"): 4.05,   # zh-CN-XiaoxiaoNeural — unchanged, and the best of a thin field
           ("zh", "male"): 4.8}      # must beat zh-CN-YunxiNeural's 4.61
    for lang, accent in (("en", "US"), ("zh", "Mainland")):
        for gender in ("female", "male"):
            v = tts.EDGE_VOICE_CATALOG[lang][accent][gender]
            sd = _VOICE_F0_SD.get(v)
            assert sd is not None, (
                "%s/%s default is %s, which has never been measured — synthesise one sentence with it and "
                "add its F0 sd here before shipping it as a default" % (lang, gender, v))
            assert sd >= was[(lang, gender)], (
                "%s/%s ships %s at F0 sd %.2f, below the %.2f the previous default measured — that is a "
                "regression toward the announcer voices this table was moved off" % (lang, gender, v, sd, was[(lang, gender)]))


def test_the_ending_has_a_room_to_decay_into():
    """The fix that actually worked, and the one nothing was guarding.

    TTS is anechoic. A person finishing a sentence in a room is followed by 150-250ms of reflections dying
    away, and that decay is most of what an ending sounds like. Measured on a delivered film, the time from
    -20 dB to -55 dB at the end of a trimmed edge-tts clip was ZERO milliseconds — the last syllable stops
    at full level. That is why no fade length worked: short and the ending is a wall (reported as 戛然而止),
    long and it lands on the last character instead (reported as 每句话的最后一个字有问题). The knob had no
    good setting because the material it needed did not exist.

    Synthesised early reflections give it that material. Measured after the change: 140ms of decay on the
    delivered clips, and the film's total silence fell from 28% to 14% because the tail now occupies what
    used to be dead air. Removing the room passes every other test in this file, which is why this one
    exists.
    """
    import array
    import math
    import re
    import subprocess
    import tempfile
    import tts
    if not _common.have_tool("ffmpeg"):
        import pytest
        pytest.skip("ffmpeg not available")
    d = tempfile.mkdtemp()
    clip = os.path.join(d, "abrupt.wav")
    # a tone that stops dead at full level: exactly what a trimmed TTS clip does
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "sine=frequency=300:duration=1.0:sample_rate=48000", clip], check=True)
    tts._master(clip, {"renderer": "remotion", "fps": 30})
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", clip, "-ac", "1", "-ar", "48000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = array.array("h"); x.frombytes(raw)
    end = max((i for i in range(len(x)) if abs(x[i]) > 2), default=len(x) - 1) + 1
    win = int(0.005 * 48000)
    prof = []
    for j in range(80, 0, -1):
        i = end - j * win
        seg = x[max(0, i):i + win]
        pk = max((abs(v) for v in seg), default=0)
        prof.append(20 * math.log10(pk / 32768.0) if pk else -99.0)
    loud = max((i for i, v in enumerate(prof) if v > -20), default=0)
    quiet = max((i for i, v in enumerate(prof) if v > -55), default=len(prof) - 1)
    decay_ms = (quiet - loud) * 5
    # BOTH TIERS, and that is a property of the code rather than a coincidence worth relying on. The room
    # lives in _master, which every tier's clips pass through, and the html tier was never exempt — its
    # clips stop just as dead; the seam there is simply longer, which masks it rather than fixing it. A
    # renderer branch inside _master would silently take the room away from one tier, so the absence of one
    # is asserted here alongside the behaviour it produces.
    import inspect
    master_src = re.sub(r"#[^\n]*", "", inspect.getsource(tts._master))
    assert "renderer" not in master_src, (
        "_master branches on the renderer — the ending treatment must be identical on both tiers, or one "
        "of them quietly keeps the defect")
    assert tts._seam_seconds({"renderer": "html", "fps": 30}) == 0.0, "the html tier is no longer seamless"

    assert decay_ms >= 60, (
        "the ending decays from -20 dB to -55 dB in %d ms — an anechoic clip stops dead at full level and "
        "no fade length can fix that; the room tail is what gives the ending somewhere to go" % decay_ms)


def test_the_fade_does_not_eat_the_last_syllable():
    """The other half of the same knob, and the two pull against each other.

    A clip's final syllable runs right up to where the trim cuts — measured across a delivered film, 28 of
    30 clips end above -50 dB, so the trim cuts the syllable rather than finding a decay to keep. That means
    the tail fade lands ON the last character. Widened to 0.18s to cure endings heard as stopping dead, it
    attenuated the syllable's body by 78 dB: a median 52% of the final syllable sat inside the fade and on
    four clips the whole of it did. The viewer's next report was 每句话的最后一个字有问题.

    Measured on 12 delivered clips, as attenuation applied 60ms from the end, where the character still is:
        0.06 exp —   0.0 dB   (and the clip still finishes at -77 dB: inaudible, no splice step)
        0.08 exp — -21.3 dB
        0.18 exp — -78.1 dB   (the character is gone)

    THIS IS A SOURCE-LEVEL GUARD, AND DELIBERATELY SO. Three behavioural versions were written first and all
    three measured something other than the fade: one anchored the mastered clip on its last non-zero
    sample, which the fade itself moves, so every duration read identically; one compared mastered against
    original and measured loudnorm's ~8 dB gain; one used a tail-vs-body ratio inside the file, which
    discriminated in a standalone probe and then did not under pytest, because the synthetic tone's detected
    end shifts by 28ms with the fade and carries the measuring point out of it. A test that cannot be shown
    to fail on the defect is not evidence, and shipping one that merely looks behavioural is worse than
    stating plainly what this checks. The numbers above come from real clips; the behavioural half of this
    knob is pinned by its sibling above, which fails if the ending stops being inaudible.
    """
    import inspect
    import re as _re
    import tts
    m = _re.search(r"afade=t=in:st=0:d=([\d.]+):curve=(\w+)", inspect.getsource(tts._master))
    assert m, "the tail fade is no longer written as afade=t=in:st=0:d=<n>:curve=<c> in tts._master"
    d, curve = float(m.group(1)), m.group(2)
    assert d <= 0.08, (
        "the tail fade is %.2fs — past 0.08 it reaches into the final syllable (measured: -21 dB at 0.08, "
        "-78 dB at 0.18), and the last character of every sentence goes with it" % d)
    assert d >= 0.03, (
        "the tail fade is %.2fs — too short to carry the ending to inaudibility; its sibling test measures "
        "that directly" % d)
    assert curve == "exp", (
        "curve=%s: only the exponential reaches true silence inside a window this short — tri and qsin "
        "finish at -52/-48 dB, which leaves a step at the splice" % curve)


def _paused_clip(path, gap, lead=0.8, tail=0.8):
    """A speech stand-in with ONE internal pause of `gap` seconds — a two-sentence beat."""
    dur = lead + gap + tail
    _common.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=%s" % dur,
                 "-af", "volume=enable='between(t,%s,%s)':volume=0" % (lead, lead + gap),
                 "-ar", "24000", "-ac", "1", path])


@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_the_scene_pause_is_measured_against_the_films_own_full_stop(tmp_path):
    """Reported as "每个 frame 的最后一句都有种被立即停止的感觉" AFTER the fixed pause landed.

    Measured on that delivered film: a within-beat sentence break ran 0.57s and the seam between two
    BEATS ran 0.72s — 27% longer for a change of picture, argument and register. A fixed number cannot
    be right here, because how long a full stop lasts is a property of the voice, the language and the
    rate, none of which the skill picks. So the pause is derived from what this film's own narration
    does at a full stop.
    """
    gap = 0.50
    clips = []
    for i, g in enumerate((0.20, 0.20, gap, gap)):        # half the beats are one sentence (comma-only)
        p = str(tmp_path / ("c%d.mp3" % i))
        _paused_clip(p, g)
        clips.append(p)
    ref = tts._film_sentence_pause(clips)
    # the FULL STOP, not the comma and not the mean of the two populations
    assert abs(ref - gap) < 0.08, (ref, gap)

    meta = {"renderer": "html", "fps": 30}
    audible = tts.audible_pause(meta, ref=ref)
    assert audible > gap + 0.3, "a scene break no longer clears a sentence break: %.2f" % audible

    # THE BREATH IS LOAD-BEARING: at 0 the seam collapses back onto the floor and this film would
    # sound exactly like the one that was reported.
    keep = tts.SENTENCE_PAUSE_BREATH
    try:
        tts.SENTENCE_PAUSE_BREATH = 0.0
        assert tts.audible_pause(meta, ref=ref) < 1.6 * gap
    finally:
        tts.SENTENCE_PAUSE_BREATH = keep

    # AND IT IS AN INCREMENT, NOT A MULTIPLE. A multiple compounds whatever the base is: tuned to 1.7 on a
    # voice whose full stop runs 0.57s (-> 0.97s), it asks a 0.90s-stop voice for 1.53s, which reads as the
    # film stopping. The gap between a generous voice and a terse one must stay roughly one breath, not
    # scale with the voice.
    terse, generous = tts.audible_pause(meta, ref=0.57), tts.audible_pause(meta, ref=0.90)
    assert abs((generous - terse) - 0.33) < 0.02, (terse, generous)

    # THE FLOOR IS LOAD-BEARING: a film of single unbroken clauses measures nothing, and must still
    # get its scene pause rather than none.
    flat = str(tmp_path / "flat.mp3")
    _tone_clip(flat, tone_s=1.4)
    assert tts._film_sentence_pause([flat]) is None
    assert abs(tts.audible_pause(meta, ref=None) - tts.SCENE_PAUSE_DEFAULT) < 1e-6

    # AND IT IS A PAUSE, NOT A HOLD: one dramatic 3s silence must not freeze every scene of the film.
    assert tts.audible_pause(meta, ref=3.0) <= tts.MAX_SCENE_PAUSE + 1e-6


@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_every_seam_in_a_film_gets_the_same_pause(tmp_path, monkeypatch):
    """Derived per clip, a two-sentence beat would get a 0.97s seam and a one-sentence beat 0.55s —
    the rhythm would change for a reason no viewer can perceive. The reference is film-wide."""
    import json as _json
    out = _proj(tmp_path)
    board = _json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8"))
    board["meta"]["renderer"] = "html"
    # THE FILM'S OPENING AND CLOSING HOLDS ARE NOT SEAMS: they are silence before the first word and after the
    # last. This fixture is two beats long, so every beat is an end beat and the holds would be counted as
    # seam length — the measure would read "the seam changed length" on a film whose seams are identical.
    # They are switched off here and measured by tests/test_open_close_hold.py instead.
    board["meta"]["open_hold"] = 0
    board["meta"]["close_hold"] = 0
    _json.dump(board, open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8"))
    made = {}                                              # ONE beat has a full stop inside; the rest do not

    def fake_say(text, dest, voice):
        gap = 0.55 if not made else 0.15
        _paused_clip(dest, gap)
        made[os.path.splitext(os.path.basename(dest))[0]] = gap

    monkeypatch.setattr(tts, "_have_edge", lambda: False)
    monkeypatch.setattr(tts, "_say", fake_say)
    data = tts.synthesize(out)
    speech = 0.8 + 0.8                                     # _paused_clip's two tones; the gap sits between
    # A SEAM IS BETWEEN TWO BEATS. The film's OPENING and CLOSING holds (tts.OPEN_HOLD_S / CLOSE_HOLD_S) are
    # silence before the first word and after the last, not seams — measured across all eight beats they made
    # this read as "the seam changed length", which is the one thing it must not say when the seams are equal.
    tails = [s["duration"] - speech - made["%02d" % s["index"]]
             for s in data["slides"] if "%02d" % s["index"] in made]
    assert len(tails) >= 2, made
    assert max(tails) - min(tails) < 0.06, ("the seam changed length between beats", tails)
    assert min(tails) > 0.55 + 0.3 - 0.12, ("the film-wide full stop was not used", tails)


_REMOTION_FFPROBE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion",
                                 "node_modules", "@remotion", "compositor-darwin-arm64", "ffprobe")


def _remotion_reads(path):
    """What Remotion's OWN bundled ffprobe says about `path` — the reader that refused `say`'s AIFF at render
    time while the system ffprobe read it fine."""
    import subprocess
    r = subprocess.run([_REMOTION_FFPROBE, "-v", "error", "-select_streams", "a:0", "-show_entries",
                        "stream=codec_name,duration", "-of", "csv=p=0", os.path.abspath(path)], capture_output=True, text=True,
                       cwd=os.path.dirname(_REMOTION_FFPROBE))     # its dylibs sit beside it, as Remotion runs it
    return r.returncode == 0 and bool(r.stdout.strip()), (r.stdout + r.stderr).strip()


@pytest.mark.skipif(not (_common.have_tool("say") and _common.have_tool("ffmpeg") and os.path.isfile(_REMOTION_FFPROBE)),
                    reason="needs macOS say, ffmpeg and remotion's bundled ffprobe")
def test_a_say_voice_writes_audio_the_remotion_tier_can_read(tmp_path):
    """A `say:` voice used to ship `.aiff`, which Remotion's bundled ffprobe refuses ("Invalid data found when
    processing input") — the cinematic tier failed at render time. Synthesis now rewraps it as PCM WAV, and a
    board voiced before that still renders: render_remotion rewraps a legacy AIFF losslessly first."""
    import render_remotion
    out = tmp_path / "proj"; os.makedirs(out, exist_ok=True)
    data = sb.new_storyboard()
    data["meta"]["voice"] = "say:Samantha"; data["meta"]["language"] = "en"
    data["slides"] = [sb.new_slide(1, "frames/01.png", "Offline voices render in the cinematic tier.")]
    sb.save(data, os.path.join(out, "storyboard.json"))
    res = tts.synthesize(str(out))
    s = res["slides"][0]
    assert s["audio"].endswith(".wav"), s["audio"]
    ok, why = _remotion_reads(os.path.join(out, s["audio"]))
    assert ok, why
    assert abs(_common.audio_duration(os.path.join(out, s["audio"])) - s["duration"]) < 1e-3

    legacy = os.path.join(out, "audio", "legacy.aiff")
    tts._common.run(["say", "-v", "Samantha", "-o", legacy, "A board voiced before the change."])
    assert not _remotion_reads(legacy)[0], "the reader no longer refuses AIFF: this test has lost its subject"
    rel = render_remotion._readable_audio(str(out), "audio/legacy.aiff")
    assert rel == "audio/legacy.wav"
    ok, why = _remotion_reads(os.path.join(out, rel))
    assert ok, why
    # lossless rewrap: the board's measured duration still holds to the sample
    assert abs(_common.audio_duration(os.path.join(out, rel)) - _common.audio_duration(legacy)) < 1e-4
