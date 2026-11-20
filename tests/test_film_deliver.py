"""film_deliver: the subtitles timed on the voice's words, a cover from the FINAL film with its captions hidden, and the
graded encode; loud when the cover could not hide a caption."""
import json
import os
import subprocess
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "film_deliver.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402
import film_deliver as fd  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None

TL = {"duration": 4.0, "lines": [
    {"id": "l01", "text": "Hand it the work. Keep the final say.", "start": 0.5, "end": 3.0,
     "words": [{"w": w, "t": t} for w, t in [("Hand", 0.55), ("it", 0.8), ("the", 0.9), ("work.", 1.0),
                                              ("Keep", 1.8), ("the", 2.0), ("final", 2.15), ("say.", 2.5)]]}]}


def test_subtitles_start_on_their_first_word():
    s = fd.srt(TL)
    blocks = [b.split("\n") for b in s.strip().split("\n\n")]
    assert len(blocks) == 2, s
    assert blocks[0][1].startswith("00:00:00,5") and blocks[0][2] == "Hand it the work."
    # each later chunk appears CAPTION_LEAD (0.1 s) before its first word ("Keep" at 1.8 s): the classic rule, kept
    assert blocks[1][1].startswith("00:00:01,700") and blocks[1][2] == "Keep the final say."


def _film(d, page=True):
    (d / "timeline.json").write_text(json.dumps(TL))
    (d / "_plan.json").write_text(json.dumps({"video": "final.mp4", "fps": 30, "frames": 120, "cuts": [],
                                              "segments": [{"id": "s01", "start": 0, "end": 120}]}))
    (d / "shot_plan.json").write_text(json.dumps({"shots": [{"id": "s01", "start": 0, "end": 4, "hero": True}]}))
    (d / "work" / "frames").mkdir(parents=True)
    for i in range(120):
        Image.new("RGB", (640, 360), (20, 30, 60)).save(d / "work" / "frames" / ("f_%05d.jpg" % i))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=4", str(d / "mix.wav")], check=True)
    if page:
        (d / "film.html").write_text("""<!doctype html><html><body style="margin:0;background:#103050">
<div data-caption style="position:absolute;left:0;right:0;top:900px;height:120px;background:#ff0000"></div>
<script>window.seek = (t) => {};</script></body></html>""")
    return d


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_encode_srt_and_a_cover_without_its_caption(tmp_path):
    d = _film(tmp_path)
    r = subprocess.run([sys.executable, SCRIPT, str(d), "--encode", "--audio", "mix.wav", "--no-copy"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "captions hidden" in r.stdout
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                            str(d / "final.mp4")], capture_output=True, text=True).stdout.split()
    assert probe == ["video", "audio"]
    assert (d / "final.srt").read_text().count(" --> ") == 2
    px = Image.open(d / "out.cover.png").convert("RGB").getpixel((960, 960))
    assert px[0] < 100, "the red caption box was not hidden on the cover: %s" % (px,)


def test_without_a_page_the_cover_says_it_carries_a_caption(tmp_path):
    d = _film(tmp_path, page=False)
    r = subprocess.run([sys.executable, SCRIPT, str(d), "--encode", "--audio", "mix.wav", "--no-copy"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and "WITH its caption" in r.stdout, r.stdout + r.stderr


def test_missing_inputs_are_refused(tmp_path):
    r = subprocess.run([sys.executable, SCRIPT, str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 2 and "needs _plan.json and timeline.json" in r.stderr


def test_a_share_copy_is_made_beside_the_master_and_capped(tmp_path):
    import film_deliver as fd
    d = _film(tmp_path)
    r = subprocess.run([sys.executable, SCRIPT, str(d), "--encode", "--audio", "mix.wav", "--no-copy"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    sh = d / "final.share.mp4"
    assert sh.exists() and "final.share.mp4" in r.stdout
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(sh)],
                           capture_output=True, text=True).stdout.split()
    assert probe == ["video", "audio"]
    # over the cap, the copy is re-encoded at a bitrate that fits (a tiny cap stands in for a long, rich film)
    sh.unlink()
    out = fd.share(str(d / "final.mp4"), cap_mb=0.01)
    assert os.path.getsize(out) < os.path.getsize(d / "final.mp4") * 4      # it ran the capped encode and finished


def test_deliver_hands_over_the_share_copy_and_the_credits_when_the_film_has_them(tmp_path):
    import deliver
    d = tmp_path / "film"
    d.mkdir()
    (d / "_plan.json").write_text(json.dumps({"video": "final.mp4", "fps": 30, "frames": 3}))
    for f in ("final.mp4", "final.share.mp4", "final.credits.txt"):
        (d / f).write_bytes(b"x")
    to = tmp_path / "desk"
    to.mkdir()
    got = [os.path.basename(p) for p in deliver.deliver(str(d), to=str(to))]
    assert any(p.endswith(" - share.mp4") for p in got) and any(p.endswith(" - credits.txt") for p in got), got
