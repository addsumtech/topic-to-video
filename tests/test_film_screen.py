"""FilmScreen — a film or recording shown as itself. The board names only the files; the render reads each one's size
and length off the file (render_remotion.register_props), because a typed size is how a picture gets drawn past its
pixels, and a typed length is how a beat runs off the end of its clip."""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import render_remotion as rr  # noqa: E402

needs_ffmpeg = pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0,
                                  reason="needs ffmpeg")


def _clip(path, w=320, h=180, seconds=2):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=%dx%d:rate=30" % (w, h),
                    "-t", str(seconds), "-pix_fmt", "yuv420p", path], check=True)


def _jpg(path, w, h):
    from PIL import Image
    Image.new("RGB", (w, h), (40, 50, 60)).save(path)


@needs_ffmpeg
def test_the_clip_and_its_frames_are_measured_off_the_files(tmp_path):
    (tmp_path / "media").mkdir()
    _clip(str(tmp_path / "media" / "f.mp4"))
    for i, w in enumerate((384, 320)):
        _jpg(str(tmp_path / "media" / ("b%d.jpg" % i)), w, w * 9 // 16)
    out = rr.register_props("FilmScreen", {"video": "media/f.mp4", "from": 0.5,
                                           "run": ["media/b0.jpg", "media/b1.jpg"]}, str(tmp_path))
    assert out["video"]["src"] == "media/f.mp4" and (out["video"]["w"], out["video"]["h"]) == (320, 180)
    assert abs(out["video"]["seconds"] - 2.0) < 0.1
    assert out["run"] == {"frames": ["media/b0.jpg", "media/b1.jpg"], "w": 320}, "the narrowest frame bounds them all"
    assert out["from"] == 0.5


def test_a_missing_clip_stops_the_render_by_name(tmp_path):
    with pytest.raises(RuntimeError, match="media/none.mp4"):
        rr.register_props("FilmScreen", {"video": "media/none.mp4"}, str(tmp_path))


@needs_ffmpeg
def test_a_strip_is_not_taken_for_a_frame(tmp_path):
    """mri_html/_keyframes/scene_NN.png are 2800x315 strips of five phases: run as frames they were drawn 2.1x past
    their pixels. A run or reel frame must have a frame's shape."""
    (tmp_path / "media").mkdir()
    _jpg(str(tmp_path / "media" / "strip.jpg"), 2800, 315)
    _jpg(str(tmp_path / "media" / "ok.jpg"), 384, 216)
    with pytest.raises(RuntimeError, match="strip.jpg"):
        rr.register_props("FilmScreen", {"reel": ["media/ok.jpg", "media/strip.jpg"]}, str(tmp_path))
