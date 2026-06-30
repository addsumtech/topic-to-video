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

def test_find_chrome_honors_meta_path(tmp_path):
    fake = tmp_path / "MyChrome"; fake.write_text("")
    assert c.find_chrome({"chrome_path": str(fake)}) == str(fake)

def test_find_chrome_ignores_bad_meta_path():
    # a non-existent chrome_path must not be returned; falls through to real discovery (path or None)
    r = c.find_chrome({"chrome_path": "/nope/Chrome"})
    assert r is None or os.path.exists(r)
