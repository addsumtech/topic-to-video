"""A frame that flashes — one or two frames unlike both neighbours, which agree with each other (scripts/flash_qa.py).

Measured 2026-11-01 on a Grok Bot film: a 3D slab drawn as stacked translateZ layers ~2 px apart re-sorted for ONE
frame when its face's content changed, and an edge layer covered the face — near-black at 107.4 s and 109.1 s, grey
at 96.3 s. The user saw "black flashes"; all 16 delivery gates were green. A hard cut changes and stays changed, a fade
changes gradually: neither is a flash.
"""
import os
import shutil
import subprocess

import numpy as np
import pytest

import flash_qa

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def _video(path, frames):
    h, w = frames[0].shape
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "%dx%d" % (w, h),
                          "-r", "30", "-i", "-", "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(path)],
                         stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.astype(np.uint8).tobytes())
    p.stdin.close()
    assert p.wait() == 0


def _scene(level, n, w=160, h=96):
    g = np.tile(np.linspace(level - 30, level + 30, w), (h, 1))
    return [g.copy() for _ in range(n)]


@needs_ffmpeg
def test_a_one_or_two_frame_flash_is_found_and_cuts_and_fades_are_not(tmp_path):
    a, b = _scene(160, 1)[0], _scene(60, 1)[0]
    frames = [a] * 20 + [np.zeros_like(a)] + [a] * 20                     # 1-frame black flash at 20
    frames += [a] * 10 + [np.full_like(a, 200)] * 2 + [a] * 20             # 2-frame bright flash at 51
    frames += [b] * 30                                                     # a hard cut at 73: not a flash
    frames += [b * (1 - k / 15.0) + a * (k / 15.0) for k in range(16)] + [a] * 20   # a fade: not a flash
    v = tmp_path / "out.mp4"
    _video(v, frames)
    found = flash_qa.flashes(str(v))
    assert [(f["frame"], f["frames"]) for f in found] == [(20, 1), (51, 2)], found


@needs_ffmpeg
def test_a_clean_film_passes(tmp_path):
    frames = _scene(120, 30) + _scene(40, 30)
    v = tmp_path / "out.mp4"
    _video(v, frames)
    assert flash_qa.flashes(str(v)) == []
