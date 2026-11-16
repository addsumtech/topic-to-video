"""beat_clock: one reader of where each beat is, on the film's own clock (audit 2026-11-15, step 6). Three copies
disagreed: two subtracted the Remotion seam on an HTML film (settled_frame --beat N landed 0.4 s early per cut)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import beat_clock as bc  # noqa: E402
import render_remotion as rr  # noqa: E402


def _board(renderer=None):
    meta = {"fps": 30}
    if renderer:
        meta["renderer"] = renderer
    return {"meta": meta, "slides": [{"index": i + 1, "duration": d} for i, d in enumerate((3.0, 4.0, 5.0))]}


def test_an_html_film_has_no_seam_between_its_clips():
    assert bc.board_spans(_board()) == [(0.0, 3.0), (3.0, 7.0), (7.0, 12.0)]


def test_a_remotion_film_mounts_each_beat_one_seam_early():
    seam = rr._REMOTION2_TR / 30.0
    sp = bc.board_spans(_board("remotion"))
    assert abs(sp[1][0] - (3.0 - seam)) < 1e-9 and abs(sp[2][0] - (7.0 - 2 * seam)) < 1e-9
    a, b = bc.clear(sp, 1)
    assert abs(a - 3.0) < 1e-9 and abs(b - sp[2][0]) < 1e-9          # after the seam in, before the seam out


def test_the_plan_is_read_while_it_describes_the_video(tmp_path):
    d = str(tmp_path)
    (tmp_path / "storyboard.json").write_text(json.dumps(_board()), encoding="utf-8")
    vid = tmp_path / "out.mp4"
    vid.write_bytes(b"x")
    plan = {"video": "out.mp4", "fps": 30, "segments": [{"start": 0, "end": 80}, {"start": 80, "end": 200},
                                                         {"start": 200, "end": 360}]}
    (tmp_path / "_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    assert bc.spans(d)[1] == (80 / 30, 200 / 30)
    # a video written after the plan is a later render it does not describe: the board's clock instead
    later = time.time() + 60
    os.utime(vid, (later, later))
    assert bc.spans(d) == [(0.0, 3.0), (3.0, 7.0), (7.0, 12.0)]
    # a plan for another video is not this one's
    os.utime(vid, None)
    os.utime(tmp_path / "_plan.json", None)
    assert bc.spans(d, video=str(tmp_path / "other.mp4")) == [(0.0, 3.0), (3.0, 7.0), (7.0, 12.0)]
