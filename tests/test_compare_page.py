"""compare_page: old and new beside each other per beat, from film folders or per-beat clips."""
import json
import os
import shutil
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import compare_page as cp  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


def _film(d, colours, frames=40):
    os.makedirs(d, exist_ok=True)
    parts, segs, a = [], [], 0
    for i, c in enumerate(colours):
        p = os.path.join(d, "p%d.mp4" % i)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=%s:s=320x180:r=30:d=%f" % (c, frames / 30.0),
                        "-pix_fmt", "yuv420p", p], check=True)
        parts.append(p)
        segs.append([a, a + frames - 1])
        a += frames
    lst = os.path.join(d, "l.txt")
    open(lst, "w").write("".join("file '%s'\n" % p for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(d, "out.mp4")], check=True)
    json.dump({"segments": segs}, open(os.path.join(d, ".render_record.json"), "w"))
    json.dump({"slides": [{"shot": "S%d" % i, "narration": "line %d" % i} for i in range(len(colours))]},
              open(os.path.join(d, "storyboard.json"), "w"))


def test_each_beat_shows_its_own_frames_from_each_side(tmp_path):
    _film(str(tmp_path / "old"), ["red", "blue", "green"])
    _film(str(tmp_path / "new"), ["white", "black", "yellow"])
    out = str(tmp_path / "cmp.html")
    rows = cp.build(out, str(tmp_path / "old"), str(tmp_path / "new"), beats=[2, 3])
    assert [r["beat"] for r in rows] == [2, 3]
    from PIL import Image
    img = lambda p: Image.open(os.path.join(str(tmp_path), p)).convert("RGB").getpixel((10, 10))
    old2, new2 = img(rows[0]["old"][1]), img(rows[0]["new"][1])
    assert old2[2] > 150 and old2[0] < 80, old2          # beat 2 of the old film is blue
    assert sum(new2) < 60, new2                          # beat 2 of the new film is black
    page = open(out, encoding="utf-8").read()
    assert 'name="b2"' in page and 'name="b3"' in page and "line 1" in page


def test_a_new_side_given_as_one_clip_per_beat(tmp_path):
    _film(str(tmp_path / "old"), ["red", "blue"])
    nd = tmp_path / "new"
    nd.mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=yellow:s=320x180:r=30:d=2", "-pix_fmt", "yuv420p",
                    str(nd / "_s2.mp4")], check=True)
    rows = cp.build(str(tmp_path / "c.html"), str(tmp_path / "old"), str(nd), beats=[1, 2], new_clip="_s{n}.mp4")
    by = {r["beat"]: r for r in rows}
    assert by[1]["new"] == [] and len(by[1]["old"]) == 3      # no clip for beat 1: said, not faked
    assert len(by[2]["new"]) == 3
