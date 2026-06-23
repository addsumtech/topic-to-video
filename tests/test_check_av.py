import os, subprocess, pytest
import check_av
import _common

def test_evaluate_aligned_ok():
    r = check_av.evaluate(10.0, 10.05, [48000, 48000], 5, 3)
    assert r["ok"] is True and r["uniform_rates"] is True and r["issues"] == []

def test_evaluate_drift_fails():
    r = check_av.evaluate(10.0, 12.6, [48000], 5, 3)
    assert r["ok"] is False and r["drift"] == 2.6
    assert any("drift" in i for i in r["issues"])

def test_evaluate_nonuniform_rates_fails():
    r = check_av.evaluate(10.0, 10.0, [22050, 24000], 5, 3)
    assert r["ok"] is False and r["uniform_rates"] is False
    assert any("sample rate" in i for i in r["issues"])

def test_evaluate_missing_stream_fails():
    r = check_av.evaluate(10.0, 0.0, [48000], 5, 3)
    assert r["ok"] is False

def test_evaluate_no_clips_is_uniform():
    r = check_av.evaluate(10.0, 10.1, [], 5, 3)
    assert r["ok"] is True and r["uniform_rates"] is True   # no clips -> uniformity skipped

def test_evaluate_cue_mismatch_is_warning_not_failure():
    r = check_av.evaluate(10.0, 10.0, [48000], 0, 3)
    assert r["ok"] is True and any("caption" in w for w in r["warnings"])

@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_check_integration_aligned_then_drift(tmp_path):
    out = str(tmp_path)
    aligned = os.path.join(out, "out.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=30",
                    "-f", "lavfi", "-i", "sine=duration=3", "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", aligned], capture_output=True)
    r = check_av.check(out)
    assert r["ok"] is True and r["drift"] < 0.3
    # now a mismatched render: 5s video, 3s audio (no -shortest)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=30",
                    "-f", "lavfi", "-i", "sine=duration=3", "-c:v", "libx264", "-c:a", "aac",
                    aligned], capture_output=True)
    r2 = check_av.check(out)
    assert r2["ok"] is False and r2["drift"] > 1.5
