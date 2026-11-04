"""Every scene clip is a whole number of frames, video and audio cut to the same length, so the `-c copy` concat is
constant-frame-rate.

A scene's duration is its audio's (tts.py), almost never a multiple of 1/fps. Cut with `-t <dur> -shortest`, a clip's
video ended on the last whole frame while its audio ran to `dur`, and the concat started the next clip's video where the
audio ended: a QR-code film (2026-11-04) had 13 such gaps — out.mp4 averaged 29.94 fps, 5072 frames for 169.4 s, its
frame index 11 frames (0.37 s) behind its clock by the end. Every gate that reads frames by index (caption_contrast_qa,
jitter_qa) then judged the wrong frame: a karaoke word measured where the next chunk already stood, a moving line
against the geometry of a frame 0.3 s away."""
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
import render  # noqa: E402


def test_a_duration_becomes_whole_frames():
    assert render._frame_exact(6.586, 30) == (198, 6.6)
    assert render._frame_exact(4.0333, 30) == (121, 121 / 30)
    assert render._frame_exact(0.001, 30)[0] == 1


@pytest.mark.skipif(not render._common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_clips_cut_frame_exact_concat_without_gaps(tmp_path):
    fps, clips = 30, []
    for k, dur in enumerate((2.586, 1.7033, 2.0)):
        out = str(tmp_path / ("c%d.mp4" % k))
        n, secs = render._frame_exact(dur, fps)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:s=64x36:r=%d" % fps,
                        "-f", "lavfi", "-i", "sine=f=440:d=%s" % dur,
                        "-filter_complex", render._apad_graph("1:a", "a"), "-map", "0:v", "-map", "[a]",
                        ] + render._clip_cut(dur, fps) + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-ar", "48000", "-ac", "1", out], check=True)
        clips.append((out, n))
    lst = tmp_path / "list.txt"
    lst.write_text("".join("file '%s'\n" % c for c, _ in clips))
    film = str(tmp_path / "film.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    film], check=True)
    pts = [float(x.strip(",")) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "frame=pts_time", "-of", "csv=p=0", film], capture_output=True, text=True).stdout.split()]
    assert len(pts) == sum(n for _, n in clips)
    gaps = [b - a for a, b in zip(pts, pts[1:]) if abs(b - a - 1 / fps) > 0.002]
    assert not gaps, gaps
