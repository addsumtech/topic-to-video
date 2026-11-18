"""pan_speed_qa: a sustained camera move faster than the limit is a whip (it strobes at 30 fps); a slow pan and a cut
are not."""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "pan_speed_qa.py")


def _video(d, speed, n=40, cut=None):
    rng = np.random.default_rng(3)
    tex = rng.integers(0, 255, (1080 // 4, (1920 + speed * n) // 4 + 8), dtype=np.uint8)
    tex = np.kron(tex, np.ones((4, 4), dtype=np.uint8))                     # 4-px blocks: texture the tracker can see
    other = np.kron(rng.integers(0, 255, (270, 480), dtype=np.uint8), np.ones((4, 4), dtype=np.uint8))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "1920x1080",
                          "-r", "30", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p",
                          str(d / "final.mp4")], stdin=subprocess.PIPE)
    for i in range(n):
        f = other if (cut is not None and i >= cut) else tex[:, i * speed:i * speed + 1920]
        p.stdin.write(np.ascontiguousarray(f).tobytes())
    p.stdin.close()
    p.wait()
    (d / "_plan.json").write_text(json.dumps({"video": "final.mp4", "fps": 30, "frames": n, "cuts": [cut] if cut else []}))


def _run(d):
    r = subprocess.run([sys.executable, SCRIPT, str(d), "--json"], capture_output=True, text=True, timeout=300)
    return r.returncode, json.loads(r.stdout)


@pytest.mark.parametrize("speed,whip", [(80, True), (20, False)])
def test_a_fast_sustained_pan_is_a_whip_and_a_slow_one_is_not(tmp_path, speed, whip):
    _video(tmp_path, speed)
    code, j = _run(tmp_path)
    assert code == (1 if whip else 0), j
    assert abs(j["max_px"] - speed) < 6, j          # it measures the real speed, even past the tracker's tile size


def test_a_cut_is_not_a_pan(tmp_path):
    _video(tmp_path, 0, cut=20)
    code, j = _run(tmp_path)
    assert code == 0 and not j["whips"], j
