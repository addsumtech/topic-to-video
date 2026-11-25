"""Delivered video is limited-range BT.709, converted and tagged all four ways (_common.BT709_VF), and check_av's
colour check refuses anything else. WHY (bench 2026-11-25): from Chrome's full-range BT.601 JPEGs, `-pix_fmt yuv420p`
shipped yuvj420p/pc/bt470bg with no primaries or transfer — a player that assumes BT.709 for HD showed green dE 11.8
off; converted and tagged, dE 0.7."""
import os
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common  # noqa: E402
import check_av  # noqa: E402
import film_deliver  # noqa: E402

GREEN = (29, 185, 84)


def _frames(d, n=6):
    os.makedirs(d, exist_ok=True)
    for f in range(n):
        Image.new("RGB", (320, 180), GREEN).save(os.path.join(d, "f_%05d.jpg" % f), quality=95)


def _as_bt709_player(mp4):
    """The middle pixel decoded the way a player that assumes limited-range BT.709 does."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-frames:v", "1", "-vf",
                          "setparams=colorspace=bt709:range=tv,scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(180, 320, 3)[90, 160].astype(int)


def test_film_deliver_writes_tagged_bt709_that_a_709_player_shows_right(tmp_path):
    _frames(tmp_path / "f")
    out = str(tmp_path / "final.mp4")
    film_deliver.encode(str(tmp_path), str(tmp_path / "f"), None, out, 0)
    assert check_av.colour_tags(out) == _common.BT709_TAGS
    assert check_av.colour_issue(out) is None
    assert np.abs(_as_bt709_player(out) - np.array(GREEN)).max() <= 4
    sh = film_deliver.share(out)
    assert check_av.colour_tags(sh) == _common.BT709_TAGS


def test_the_colour_check_refuses_an_untagged_full_range_file(tmp_path):
    _frames(tmp_path / "f")
    old = str(tmp_path / "old.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", str(tmp_path / "f" / "f_%05d.jpg"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", old], check=True)
    assert check_av.colour_issue(old) is not None
    assert np.abs(_as_bt709_player(old) - np.array(GREEN)).max() > 8      # the shift the check is there for
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "check_av.py"), "--colour", old], capture_output=True, text=True)
    assert r.returncode == 1 and "RED" in r.stdout
