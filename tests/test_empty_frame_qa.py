"""empty_frame_qa reports a blank HOLD (>= 1 s nearly empty above the caption band) and nothing that is merely sparse:
a solid fill, a light card on light paper, a lone hero object, and the closing fade are all left alone."""
import os
import subprocess
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import empty_frame_qa as eq  # noqa: E402
import film_qc  # noqa: E402

PAPER = (232, 230, 224)


def _frame(fill=PAPER):
    f = np.zeros((180, 320, 3), np.uint8)
    f[:] = fill
    return f


def test_blank_paper_is_empty():
    assert eq.occupancy(_frame()) < eq.FLOOR


def test_a_label_alone_is_still_empty():
    f = _frame()
    f[8:14, 12:60] = (30, 30, 30)              # a small step label in the corner
    assert eq.occupancy(f) < eq.FLOOR


def test_a_large_solid_fill_is_occupied():
    # the finder-pattern close-up the edge-only measure read as empty: big black squares have no inner edges
    f = _frame()
    f[20:130, 40:150] = (20, 20, 20)
    assert eq.occupancy(f) > 0.15


def test_a_light_card_on_light_paper_is_occupied():
    # white UI on near-white paper: the colour difference is under the threshold, the outline is not
    f = _frame()
    f[30:120, 60:240] = (250, 249, 246)
    f[30, 60:240] = f[119, 60:240] = (200, 200, 200)
    f[30:120, 60] = f[30:120, 239] = (200, 200, 200)
    assert eq.occupancy(f) > 0.15


def test_a_lone_hero_object_is_not_a_blank_hold():
    f = _frame()
    f[50:110, 130:190] = (40, 200, 140)        # a mascot / logo alone on the ground
    assert eq.occupancy(f) > eq.FLOOR


def test_caption_band_does_not_count():
    f = _frame()
    f[150:170, 60:260] = (20, 20, 20)          # a caption line only
    assert eq.occupancy(f) < eq.FLOOR


def test_stretches_need_the_minimum_length_and_skip_the_closing_grace():
    fps = eq.FPS
    full, low = 0.3, 0.0
    occ = [full] * 20 + [low] * (fps // 2) + [full] * 20 + [low] * (fps * 2) + [full] * 20 + [low] * (fps * 2)
    found = eq.stretches(occ, fps=fps)
    assert len(found) == 1                      # the half-second dip is a cut; the final 2 s is the closing fade
    a, b, m = found[0]
    assert b - a == pytest.approx(2.0) and m == 0.0


@pytest.fixture(scope="module")
def blank_hold_film(tmp_path_factory):
    d = tmp_path_factory.mktemp("film")
    v = str(d / "final.mp4")
    # 2 s with a card, 1.5 s of bare paper, 3 s with a card again
    box = "drawbox=x=500:y=250:w=900:h=500:color=0x205080:t=fill"
    vf = "color=c=0xE8E6E0:s=1920x1080:r=30:d=6.5,%s:enable='not(between(t,2,3.5))'" % box
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", vf, "-pix_fmt", "yuv420p", v], check=True)
    return d, v


def test_reports_the_blank_hold_in_a_real_video(blank_hold_film):
    _, v = blank_hold_film
    found, _ = eq.judge(v)
    assert len(found) == 1
    a, b, _m = found[0]
    assert abs(a - 2.0) <= 0.25 and abs(b - 3.5) <= 0.25
    assert eq.main([v]) == 1


def test_film_qc_refuses_a_dir_without_a_plan(tmp_path, capsys):
    assert film_qc.main([str(tmp_path)]) == 2
    assert "_plan.json" in capsys.readouterr().err


def test_film_qc_runs_every_check_on_the_plan_video(blank_hold_film):
    d, _ = blank_hold_film
    names = [n for n, _c in film_qc.checks(str(d), str(d / "final.mp4"), str(d / "_plan.json"))]
    assert names == ["flash", "rewind", "glide", "empty", "shake", "captions", "pan speed", "repetition", "banding", "mix"]
    glide = dict(film_qc.checks(str(d), str(d / "final.mp4"), str(d / "_plan.json")))["glide"]
    assert "--video=" + str(d / "final.mp4") in glide   # picture_glide_qa otherwise reads <dir>/out.mp4


def test_film_qc_adds_the_plan_and_seam_checks_with_a_shot_plan(tmp_path):
    names = [n for n, _c in film_qc.checks(str(tmp_path), str(tmp_path / "final.mp4"), str(tmp_path / "_plan.json"))]
    assert "shot plan" not in names and "seams" not in names
    (tmp_path / "shot_plan.json").write_text("{}")
    names = [n for n, _c in film_qc.checks(str(tmp_path), str(tmp_path / "final.mp4"), str(tmp_path / "_plan.json"))]
    assert names[-2:] == ["shot plan", "seams"]
