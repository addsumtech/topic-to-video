"""caption_size_qa: a caption line's ink height in the bottom band, as a share of the frame; calibrated so a ~56 px
font at 1080p passes and the 38-44 px captions the skill's films used fail."""
import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import caption_size_qa as cq  # noqa: E402

FONT = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "DejaVuSans.ttf")


def _frame(size, text="Every point of the scene does this at once."):
    im = Image.new("L", (1920, 1080), 24)
    d = ImageDraw.Draw(im)
    d.text((960, 990), text, font=ImageFont.truetype(FONT, size), fill=235, anchor="mm")
    return np.asarray(im)


def test_line_height_tracks_the_font_size():
    small, big = cq.line_height(_frame(42)), cq.line_height(_frame(60))
    assert small < 0.046 * 1080 <= big


def test_no_caption_is_none():
    assert cq.line_height(np.full((1080, 1920), 24, np.uint8)) is None


@pytest.mark.parametrize("size,ok", [(42, False), (60, True)])
def test_judge_on_a_real_video(tmp_path, size, ok):
    png, mp4 = tmp_path / "f.png", tmp_path / "f.mp4"
    Image.fromarray(_frame(size)).save(png)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(png), "-t", "3", "-r", "30",
                    "-pix_fmt", "yuv420p", str(mp4)], check=True)
    r = cq.judge(str(mp4))
    assert r["judged"] and r["ok"] is ok
    assert cq.main([str(mp4)]) == (0 if ok else 1)


def test_a_film_without_captions_is_not_judged(tmp_path):
    mp4 = tmp_path / "blank.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x181818:s=1920x1080:r=30:d=3",
                    "-pix_fmt", "yuv420p", str(mp4)], check=True)
    assert cq.judge(str(mp4))["judged"] is False and cq.main([str(mp4)]) == 0
