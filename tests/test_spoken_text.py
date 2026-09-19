"""The voice is sent the text it reads naturally; the frame keeps the text as written — `tts.spoken_text`.

Measured on edge-tts zh-CN-XiaoxiaoNeural: before an all-caps initialism (AI, TTS, API, SSH, CLI, GPU, MRI) in
a Chinese sentence the voice drags the preceding syllable and pauses (~0.23s + 0.10s vs 0.11s + 0.025s before
macOS or ChatGPT). Hyphenated (A-I, T-T-S) it reads straight through, and the listener picked that reading.
These pin the transform, its narrow scope, and that nothing it does reaches the caption or the word timings.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import tts  # noqa: E402

ZH = ({}, "edge", "zh-CN-XiaoxiaoNeural")


def test_short_initialisms_are_spelled_for_a_chinese_voice():
    said, back = tts.spoken_text("代码不需要 API 密钥，也没有用 TTS。你的 AI 任务", *ZH)
    assert said == "代码不需要 A-P-I 密钥，也没有用 T-T-S。你的 A-I 任务"
    assert back == {"A-P-I": "API", "T-T-S": "TTS", "A-I": "AI"}


def test_scope_is_narrow_on_purpose():
    """Four letters and up are where acronyms said as WORDS live; mixed case is a name; a word-acronym stays."""
    for keep in ("NASA 发射", "JSON 文件", "AGPL 3.0", "macOS 上", "iOS 里", "ChatGPT", "内存 RAM", "AIGC", "A-B 测试"):
        said, _ = tts.spoken_text(keep, *ZH)
        assert said == keep, (keep, said)


def test_only_where_it_was_measured():
    assert tts.spoken_text("AI 很好", {}, "edge", "en-US-AvaNeural")[0] == "AI 很好"
    assert tts.spoken_text("AI 很好", {}, "minimax", "female-shaonv")[0] == "AI 很好"
    assert tts.spoken_text("AI 很好", {"tts_spell_initialisms": False}, "edge", "zh-CN-XiaoxiaoNeural")[0] == "AI 很好"
    assert tts.spoken_text("AI is good", {"tts_spell_initialisms": True}, "edge", "en-US-AvaNeural")[0] == "A-I is good"


def test_an_authors_old_spelled_out_form_gets_the_same_reading():
    """Films used to write "T T S" / "A G P L" by hand to force the letters; that is no longer needed, and a
    leftover one is rejoined rather than read as four separate words."""
    assert tts.spoken_text("没有用 T T S", *ZH)[0] == "没有用 T-T-S"
    assert tts.spoken_text("采用 A G P L 协议", *ZH)[0] == "采用 AGPL 协议"


def test_the_lexicon_comes_first_and_maps_back():
    said, back = tts.spoken_text("AgentHalo 用 AI", {"tts_lexicon": {"AgentHalo": "Agent Halo"}}, "edge",
                                 "zh-CN-XiaoxiaoNeural")
    assert said == "Agent Halo 用 A-I" and back["Agent Halo"] == "AgentHalo"


def test_word_timings_come_back_in_the_written_spelling():
    """karaoke locates each timed word inside the CAPTION; a token spelled for the ear would never be found."""
    got = tts.written_words([{"w": "A-I", "t": 0.6}, {"w": "任务", "t": 1.0}, {"w": "T-T-S", "t": 2.0},
                             {"w": "Agent Halo", "t": 3.0}], {"Agent Halo": "AgentHalo"})
    assert [w["w"] for w in got] == ["AI", "任务", "TTS", "AgentHalo"]
    assert [w["t"] for w in got] == [0.6, 1.0, 2.0, 3.0]


def test_a_malformed_lexicon_fails_loudly():
    import pytest
    with pytest.raises(ValueError):
        tts.spoken_text("AI", {"tts_lexicon": ["AI", "A-I"]}, "edge", "zh-CN-XiaoxiaoNeural")


def test_synthesis_sends_the_spoken_form_and_keeps_the_narration(tmp_path, monkeypatch):
    """The wiring, not just the helper: what reaches the voice is the ear's text, `narration` is untouched."""
    import json
    sent = []

    def fake_edge(text, out_path, voice, rate="+0%"):
        sent.append(text)
        open(out_path, "wb").write(b"")
        json.dump([{"w": "A-I", "t": 0.1}], open(os.path.splitext(out_path)[0] + ".words.json", "w"))

    monkeypatch.setattr(tts, "_edge", fake_edge)
    monkeypatch.setattr(tts, "_master", lambda *a, **k: None)
    monkeypatch.setattr(tts, "_film_sentence_pause", lambda paths: None)
    monkeypatch.setattr(tts, "_film_lead_silence", lambda paths: 0.0)
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.0)
    d = {"meta": {"voice": "edge:zh-CN-XiaoxiaoNeural", "language": "zh"},
         "slides": [{"index": 1, "narration": "你的 AI 任务"}]}
    json.dump(d, open(tmp_path / "storyboard.json", "w"), ensure_ascii=False)
    tts.synthesize(str(tmp_path))
    assert sent == ["你的 A-I 任务"]
    out = json.load(open(tmp_path / "storyboard.json"))
    assert out["slides"][0]["narration"] == "你的 AI 任务"
    assert json.load(open(tmp_path / "audio" / "01.words.json"))[0]["w"] == "AI"
