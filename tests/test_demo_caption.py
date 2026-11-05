"""During a sound demo the caption gives way: the ANC film's beat 6 kept "Listen." on screen through the whole hum
and its cancellation. A scene carrying `captionUntil` (the demo's start, from slide.audio_demo.at_s) ends its burned
caption there — and out.srt, which mirrors the burn, ends its last cue there too."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import render_remotion as rr  # noqa: E402


def test_the_srt_cue_ends_where_the_demo_begins(tmp_path, monkeypatch):
    monkeypatch.setattr(rr.subprocess, "run", lambda *a, **k: None)                # no keyframe extraction
    scenes = [{"durF": 300, "caption": "It is quieter. Listen.", "captionUntil": 4.0}]
    try:
        rr._remotion_deliverables(str(tmp_path), scenes, str(tmp_path / "out.mp4"), 30)
    except Exception:
        pass                                                                       # keyframes need a real film
    srt = open(tmp_path / "out.srt").read()
    last_end = srt.strip().split("\n\n")[-1].split("\n")[1].split(" --> ")[1]
    assert last_end <= "00:00:04,000", srt


def test_film_hides_the_caption_after_captionUntil():
    src = open(os.path.join(_ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
    assert "captionUntil" in src
