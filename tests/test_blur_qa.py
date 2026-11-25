"""blur_qa: a real picture held out of focus reads as a blurry original (the Airbnb film, 2026-11-25)."""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "blur_qa.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402
import blur_qa as bq  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None

PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c63f8cfc0f01f0005000201a5f2e6a90000000049454e44ae426082")


def test_runs_measure_how_long_each_picture_stays_blurred():
    s = [(0.0, [{"el": "#a", "blur": 3, "ok": None}]), (0.1, [{"el": "#a", "blur": 5, "ok": None}]),
         (0.2, []), (0.3, [{"el": "#a", "blur": 2, "ok": None}])]
    r = bq.runs(s)
    assert [(x["el"], x["from"], x["seconds"], x["max_blur"]) for x in r] == [("#a", 0.0, 0.2, 5), ("#a", 0.3, 0.1, 2)]


def test_a_short_whip_passes_a_held_blur_is_red_and_a_reason_declares_it():
    whip = {"el": "#w", "seconds": 0.4, "ok": None}
    held = {"el": "#h", "seconds": 1.2, "ok": None}
    meant = {"el": "#m", "seconds": 3.0, "ok": "a dream sequence: the memory is soft on purpose"}
    empty = {"el": "#e", "seconds": 3.0, "ok": " "}
    red, declared = bq.judge([whip, held, meant, empty])
    assert [r["el"] for r in red] == ["#h", "#e"] and [r["el"] for r in declared] == ["#m"]


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_on_a_page(tmp_path):
    (tmp_path / "p.png").write_bytes(PNG)
    (tmp_path / "timeline.json").write_text('{"duration": 2.0}')
    (tmp_path / "film.html").write_text("""<!doctype html><html><body style="margin:0;background:#fff">
<img id="held" src="p.png" style="position:absolute;left:0;top:0;width:300px;height:200px">
<div id="wrap" style="position:absolute;left:400px;top:0"><img id="whip" src="p.png" style="width:300px;height:200px"></div>
<div id="glow" style="position:absolute;left:0;top:300px;width:300px;height:100px;background:#f88;filter:blur(20px)"></div>
<script>window.seek = (t) => {
  document.getElementById('held').style.filter = t < 1.5 ? 'blur(4px)' : 'none';          // 1.5 s out of focus
  document.getElementById('wrap').style.filter = t > 1.0 && t < 1.3 ? 'blur(8px)' : 'none'; // a 0.3 s whip
};</script></body></html>""")
    r = subprocess.run([sys.executable, SCRIPT, str(tmp_path), "--json"], capture_output=True, text=True, timeout=300)
    assert r.returncode == 1, r.stdout + r.stderr
    j = json.loads(r.stdout)
    assert [x["el"] for x in j["red"]] == ["#held"], j      # the whip and the blurred glow (no picture) pass
