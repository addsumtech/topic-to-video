import os, subprocess, pytest
import _common as c

def test_run_returns_stdout():
    assert c.run(["echo", "hi"]).strip() == "hi"

def test_run_raises_on_failure():
    with pytest.raises(subprocess.CalledProcessError):
        c.run(["false"])

def test_audio_duration_of_generated_clip(tmp_path):
    wav = tmp_path / "a.aiff"
    c.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
           "-t", "1.0", str(wav)])
    d = c.audio_duration(str(wav))
    assert 0.9 <= d <= 1.1

def test_have_tool():
    assert c.have_tool("ffmpeg") is True
    assert c.have_tool("definitely-not-a-tool-xyz") is False
