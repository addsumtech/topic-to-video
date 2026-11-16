"""`settled_frame.py --beat` takes its fraction of the part of the beat NO SEAM TOUCHES.

90% of a 3.07 s beat is 0.3 s from its end — inside a 0.4 s dissolve. On the launch benchmark two "settled" frames
were mid-seam: a double exposure of beats 3 and 4, and beat 7 as a blank frame (checked against out.mp4)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import render_remotion as rr  # noqa: E402
import settled_frame as sf  # noqa: E402


def _board(tmp_path, durs):
    slides = [{"index": i + 1, "duration": d, "narration": "x"} for i, d in enumerate(durs)]
    # a REMOTION film (the launch benchmark's tier): its beats overlap by a seam. An HTML film's clips do not, and a
    # board that names no renderer is read on render.py's clock (scripts/beat_clock)
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"fps": 30, "renderer": "remotion"}, "slides": slides}))
    return str(tmp_path)


def test_the_settled_frame_of_a_short_beat_is_clear_of_both_seams(tmp_path):
    out = _board(tmp_path, [4.0, 3.07, 4.0])
    seam = rr._REMOTION2_TR / 30.0
    s, e = sf.beat_window(out, 2)
    a, b = sf.clear_window(out, 2)
    assert (round(a - s, 6), round(e - b, 6)) == (round(seam, 6), round(seam, 6))
    old, new = s + 0.9 * (e - s), a + 0.9 * (b - a)
    assert old > e - seam, "the fixture no longer shows the defect: 90%% of the beat was already clear"
    assert a < new < b
    # the first beat has no seam in; the last has none out
    a1, _b1 = sf.clear_window(out, 1)
    _a3, b3 = sf.clear_window(out, 3)
    assert a1 == sf.beat_window(out, 1)[0] and b3 == sf.beat_window(out, 3)[1]


def test_a_beat_shorter_than_its_seams_keeps_its_whole_window(tmp_path):
    seam = rr._REMOTION2_TR / 30.0
    out = _board(tmp_path, [4.0, seam * 1.5, 4.0])
    assert sf.clear_window(out, 2) == sf.beat_window(out, 2)


def test_an_html_film_beat_starts_where_its_clips_add_up(tmp_path):
    """The defect beat_clock fixed: the seam was subtracted on an HTML film too (0.4 s early per cut)."""
    slides = [{"index": i + 1, "duration": d, "narration": "x"} for i, d in enumerate([4.0, 3.07, 4.0])]
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"fps": 30}, "slides": slides}))
    assert sf.beat_window(str(tmp_path), 3) == (7.07, 11.07)
    assert sf.clear_window(str(tmp_path), 2) == sf.beat_window(str(tmp_path), 2)   # no seam to clear
