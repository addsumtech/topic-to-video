"""light_match_qa: a straight cut inside one sequence that flips the light warm <-> cool is flagged (advisory);
the same flip at a seam, a change of brightness, or a frame with nothing neutral is not."""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import light_match_qa as lm  # noqa: E402

WARM, COOL, PLAIN = (200, 192, 175), (170, 176, 190), (128, 128, 128)   # b* about +7 and -6, as measured in real films


def _frame(rgb, h=90, w=160):
    return np.full((h, w, 3), rgb, np.uint8)


def test_the_key_reads_warm_cool_and_nothing():
    assert lm.key(_frame(WARM)) > lm.KEY_T and lm.key(_frame(COOL)) < -lm.KEY_T
    assert abs(lm.key(_frame(PLAIN))) < 1
    assert lm.key(_frame((230, 30, 40))) is None            # a saturated red has no neutral pixel to read the light by


def test_the_caption_band_does_not_count():
    f = _frame(COOL)
    f[int(f.shape[0] * lm.CAPTION):] = WARM                 # a warm caption strip under a cool picture
    assert lm.key(f) < -lm.KEY_T


def test_a_flip_inside_a_sequence_is_flagged_and_at_a_seam_it_is_not():
    shots = [(0, 2, 5.0), (2, 4, -4.0), (4, 6, -3.0)]
    assert [round(f["key_to"]) for f in lm.flips(shots, [])] == [-4]
    assert lm.flips(shots, [2.0]) == []                      # the world changes at the seam: a new light is allowed


def test_one_side_of_neutral_and_unreadable_shots_are_not_flips():
    assert lm.flips([(0, 2, 9.8), (2, 4, 0.8)], []) == []    # warmer and less warm: one key
    assert lm.flips([(0, 2, 1.5), (2, 4, -1.5)], []) == []   # both inside the dead band
    assert lm.flips([(0, 2, 6.0), (2, 4, None)], []) == []


def _film(d, b_rgb, seams):
    out = d / "final.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x%02x%02x%02x:s=320x180:r=30:d=2" % WARM,
                    "-f", "lavfi", "-i", "color=c=0x%02x%02x%02x:s=320x180:r=30:d=2" % b_rgb,
                    "-filter_complex", "[0][1]concat=n=2:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p", str(out)], check=True)
    (d / "_plan.json").write_text(json.dumps({"video": "final.mp4", "fps": 30, "cuts": [60]}))
    (d / "timeline.json").write_text(json.dumps({"duration": 4.0, "seams": seams, "lines": []}))


def test_on_a_rendered_film(tmp_path, capsys):
    _film(tmp_path, COOL, [])
    assert lm.main([str(tmp_path)]) == 0                    # advisory: never red
    assert "flips warm to cool" in capsys.readouterr().out
    _film(tmp_path, COOL, [{"t": 2.0, "from": "a", "to": "b"}])
    lm.main([str(tmp_path)])
    assert "0 warm/cool flip" in capsys.readouterr().out
    _film(tmp_path, (215, 208, 190), [])                     # brighter, same warm key: not a flip
    lm.main([str(tmp_path)])
    assert "0 warm/cool flip" in capsys.readouterr().out


def test_missing_inputs_are_a_usage_error(tmp_path):
    assert lm.main([str(tmp_path)]) == 2
    _film(tmp_path, COOL, ["soon"])
    assert lm.main([str(tmp_path)]) == 2                    # a seam it cannot read is said, never guessed
