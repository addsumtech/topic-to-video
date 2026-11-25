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
    assert names == ["flash", "rewind", "glide", "empty", "shake", "captions", "colour", "pan speed", "repetition", "banding", "mix"]
    glide = dict(film_qc.checks(str(d), str(d / "final.mp4"), str(d / "_plan.json")))["glide"]
    assert "--video=" + str(d / "final.mp4") in glide   # picture_glide_qa otherwise reads <dir>/out.mp4


def test_film_qc_adds_the_light_match_check_with_a_timeline(tmp_path):
    names = [n for n, _c in film_qc.checks(str(tmp_path), str(tmp_path / "final.mp4"), str(tmp_path / "_plan.json"))]
    assert "light" not in names
    (tmp_path / "timeline.json").write_text('{"seams": [], "lines": []}')
    names = [n for n, _c in film_qc.checks(str(tmp_path), str(tmp_path / "final.mp4"), str(tmp_path / "_plan.json"))]
    assert names[names.index("repetition") + 1] == "light"
    todo = [n for n, _c in film_qc.checks(str(tmp_path), "v.mp4", "p.json", (20, 50), page_dir=str(tmp_path))]
    assert "light" not in todo, "a stretch has no sequence context: judged on the whole film"


def test_film_qc_adds_the_plan_and_seam_checks_with_a_shot_plan(tmp_path):
    names = [n for n, _c in film_qc.checks(str(tmp_path), str(tmp_path / "final.mp4"), str(tmp_path / "_plan.json"))]
    assert "shot plan" not in names and "seams" not in names
    (tmp_path / "shot_plan.json").write_text("{}")
    names = [n for n, _c in film_qc.checks(str(tmp_path), str(tmp_path / "final.mp4"), str(tmp_path / "_plan.json"))]
    assert names[-2:] == ["shot plan", "seams"]


def _rendered_film(tmp_path, n=60):
    """A film whose frames are rendered (work/frames, film_frames.py's names) but not yet assembled: no final.mp4."""
    from PIL import Image
    fr = tmp_path / "work" / "frames"
    fr.mkdir(parents=True)
    for k in range(n):
        f = np.zeros((180, 320, 3), np.uint8)
        f[:] = (40, 60, 80)
        f[60:120, 20 + k:80 + k] = (230, 200, 120)          # a card travelling right, a pixel a frame
        Image.fromarray(f).save(fr / ("f_%05d.jpg" % k), quality=95)
    plan = {"video": "final.mp4", "fps": 30, "frames": n, "cuts": [30],
            "segments": [{"start": 0, "end": 30, "kind": "shot", "id": "a"}, {"start": 30, "end": n, "kind": "shot", "id": "b"}]}
    (tmp_path / "_plan.json").write_text(__import__("json").dumps(plan))
    (tmp_path / "shot_plan.json").write_text(__import__("json").dumps(
        {"shots": [{"id": "a", "start": 0.0, "end": 1.0, "seam_out": "match"}, {"id": "b", "start": 1.0, "end": 2.0}]}))
    return tmp_path


def test_film_qc_checks_one_builders_frames_before_the_film_exists(tmp_path):
    import json
    d = _rendered_film(tmp_path)
    assert film_qc.main([str(d), "--frames", "20-50", "--only", "flash,empty"]) == 0
    q = d / "work" / "qc_20-50"
    plan = json.loads((q / "_plan.json").read_text())
    assert plan["frames"] == 30 and plan["cuts"] == [10], plan
    assert [(g["id"], g["start"], g["end"]) for g in plan["segments"]] == [("a", 0, 10), ("b", 10, 30)]
    shots = json.loads((q / "shot_plan.json").read_text())["shots"]
    assert [(s["id"], round(s["start"], 3), round(s["end"], 3)) for s in shots] == [("a", 0.0, 0.333), ("b", 0.333, 1.0)]
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames", "-of", "csv=p=0", str(q / "final.mp4")], capture_output=True, text=True).stdout
    assert int(out) == 30, "the stretch is encoded, the frames A..B-1 only"
    assert not (d / "final.mp4").exists()


def test_film_qc_on_a_stretch_leaves_the_film_wide_checks_for_the_whole_film(tmp_path):
    d = _rendered_film(tmp_path)
    (d / "film.html").write_text("<script src='stage3d.js'></script>")
    todo = dict(film_qc.checks(str(d / "q"), "v.mp4", "p.json", (20, 50), page_dir=str(d)))
    assert not {"repetition", "mix", "shot plan"} & set(todo), todo
    for name in ("overlaps", "copy", "pictures", "contacts"):
        assert todo[name][-3:] == [str(d), "--frames", "20-50"], "page checks step through the stretch on the film's page"


def test_film_qc_refuses_a_stretch_it_cannot_judge(tmp_path, capsys):
    d = _rendered_film(tmp_path)
    with pytest.raises(SystemExit) as e:
        film_qc.main([str(d), "--frames", "40-20"])
    assert e.value.code == 2
    assert film_qc.main([str(d), "--frames", "20-90"]) == 2 and "past the film" in capsys.readouterr().err
    (d / "work" / "frames" / "f_00025.jpg").unlink()
    with pytest.raises(SystemExit) as e:
        film_qc.main([str(d), "--frames", "20-50"])
    assert e.value.code == 2 and "not rendered" in capsys.readouterr().err


def test_a_red_check_shows_every_finding_not_its_last_lines():
    # the MRI film's glide: beats 1, 5, 7, 8 and 13 stepped; the last 25 lines showed only 13
    out = "\n".join(["  beat %2d  frames 1-2  0.2 px RMS   <- STEPS" % k if k in (1, 5, 7, 8) else "  beat %2d  fine" % k
                     for k in range(1, 40)] + ["[picture_glide] FAIL — stepping: [1, 5, 7, 8]"])
    shown = film_qc._findings(out)
    assert sum("<- STEPS" in l for l in shown) == 4 and any("FAIL" in l for l in shown) and len(shown) < 10, shown


def test_film_qc_only_takes_a_hyphen_for_a_name_with_a_space(tmp_path, capsys):
    d = _rendered_film(tmp_path)
    assert film_qc.main([str(d), "--frames", "20-50", "--only", "pan-speed"]) in (0, 1)
    assert "no check named" not in capsys.readouterr().err
    assert film_qc.main([str(d), "--frames", "20-50", "--only", "pan-sped"]) == 2
