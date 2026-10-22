"""edge-tts leaf: a stalled stream is cut by a wall-clock deadline and retried; an empty or failing stream
never becomes a silent mp3. (An audition once sat 7 minutes on a socket that delivered nothing.)"""
import asyncio
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import tts  # noqa: E402


def _fake_edge(monkeypatch, plan):
    """`plan` is one entry per attempt: 'hang', 'empty' or 'ok'."""
    calls = {"n": 0}

    class Communicate:
        def __init__(self, *a, **k):
            self.kind = plan[min(calls["n"], len(plan) - 1)]
            calls["n"] += 1

        async def stream(self):
            if self.kind == "hang":
                await asyncio.sleep(60)
            if self.kind == "ok":
                yield {"type": "WordBoundary", "text": "hi", "offset": 0}
                yield {"type": "audio", "data": b"ID3fake"}

    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=Communicate))
    monkeypatch.setattr(tts, "_EDGE_DEADLINE_S", 0.2)
    monkeypatch.setattr(tts, "_EDGE_DEADLINE_PER_CHAR", 0.0)
    return calls


def test_a_stalled_stream_is_cut_and_retried(monkeypatch, tmp_path):
    calls = _fake_edge(monkeypatch, ["hang", "ok"])
    out = tmp_path / "01.mp3"
    tts._edge("hi", str(out), "en-US-AndrewNeural")
    assert calls["n"] == 2
    assert out.read_bytes() == b"ID3fake"
    assert (tmp_path / "01.words.json").exists()


def test_no_audio_after_every_attempt_fails_loudly(monkeypatch, tmp_path):
    calls = _fake_edge(monkeypatch, ["empty", "hang", "empty"])
    out = tmp_path / "02.mp3"
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        tts._edge("hi", str(out), "en-US-AndrewNeural")
    assert calls["n"] == 3
    assert not out.exists()
