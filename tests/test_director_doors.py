"""The director path reaches the classic capabilities through doors that need no storyboard: say.py (the voice layer),
imagegen --prompt (one image), sfx.py --cues (an SFX track), blender_clip --screen (a device's screen)."""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import blender_clip  # noqa: E402
import imagegen  # noqa: E402
import say  # noqa: E402
import tts  # noqa: E402


def test_say_routes_through_the_voice_layer(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(tts, "speak_retrying", lambda text, dest, meta, prov, name: calls.append((text, dest, meta, prov, name)))
    lex = tmp_path / "lex.json"
    lex.write_text(json.dumps({"重": "zhòng"}), encoding="utf-8")
    lines = tmp_path / "s.txt"
    lines.write_text("第一句\n\n第二句\n", encoding="utf-8")
    assert say.main(["--lines", str(lines), "--out-dir", str(tmp_path / "v"), "--voice", "edge:zh-CN-XiaoxiaoNeural",
                     "--speed", "1.08", "--lexicon", str(lex)]) == 0
    assert [c[0] for c in calls] == ["第一句", "第二句"]                       # blank lines skipped
    assert calls[1][1].endswith("l02.mp3")
    assert calls[0][3:] == ("edge", "zh-CN-XiaoxiaoNeural")
    assert calls[0][2] == {"tts_speed": 1.08, "tts_lexicon": {"重": "zhòng"}}


def test_imagegen_prompt_is_codex_first_with_the_faithfulness_tail(tmp_path, monkeypatch):
    seen = {}

    def fake_codex(prompt, out_path, size="1536x1024", quality="medium"):
        seen["prompt"] = prompt
        open(out_path, "wb").write(b"png")
    monkeypatch.setattr(imagegen, "_generate_codex", fake_codex)
    monkeypatch.setattr(imagegen, "generate", lambda *a, **k: pytest.fail("the paid API without a key"))
    out = tmp_path / "bg.png"
    imagegen.one("a misty valley at dawn", str(out))
    assert out.read_bytes() == b"png"
    assert seen["prompt"] != "a misty valley at dawn" and "a misty valley at dawn" in seen["prompt"]   # tail added


def test_sfx_cues_build_a_track_and_refuse_unknown_names(tmp_path):
    cues = tmp_path / "c.json"
    cues.write_text(json.dumps([{"t": 0.2, "cue": "pop", "gain": 0.6}, {"t": 0.8, "cue": "sparkle"}]))
    out = tmp_path / "sfx.wav"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sfx.py"), "--cues", str(cues), "--seconds", "2",
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0 and out.exists() and out.stat().st_size > 1000, r.stderr
    cues.write_text(json.dumps([{"t": 0.2, "cue": "kaboom"}]))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sfx.py"), "--cues", str(cues), "--seconds", "2",
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 2 and "kaboom" in r.stderr
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sfx.py"), "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "--cues" in r.stdout                       # it used to look for '--help/storyboard.json'


def test_blender_clip_passes_a_device_screen():
    cmd = blender_clip.command("/B", "s.py", "/out", 30, 30, 640, 360, "cycles", 24, True, "{}", screen="shots")
    assert cmd[cmd.index("--screen") + 1] == os.path.abspath("shots")
