"""jitter_html — the HTML tier's census for the pixel jitter gate (scripts/jitter_qa.py).

The unit tests pin the parts that need no browser: where a scene's frames start, which frames a seam owns, the Ken
Burns geometry (and that a reduced-motion film holds it still), the platform-safe mapping, and that a census of
another render is refused. The film tests render real HTML-tier films (scripts/render.py, under the render lock) at
16:9, 9:16 and 1:1, with Latin, CJK and dark type, and need GATE_RENDER=1."""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, _HERE)

import jitter_html as jh       # noqa: E402
import jitter_qa as jq         # noqa: E402
import _html_jitter_film as F  # noqa: E402

needs_render = pytest.mark.skipif(not os.environ.get("GATE_RENDER"), reason="renders films: set GATE_RENDER=1")


def test_scenes_that_do_not_add_up_to_the_video_are_another_render(tmp_path):
    slides = [{"index": 1, "duration": 3.0}, {"index": 2, "duration": 1.0}]
    assert jh.scene_frames(str(tmp_path), slides, 30, 120) == ([90, 30], "round(duration x fps)")
    with pytest.raises(RuntimeError, match="another render"):
        jh.scene_frames(str(tmp_path), slides, 30, 121)


def test_a_seam_owns_its_frames_and_a_cut_owns_none():
    meta = {"_out": _ROOT, "transition": "dip", "transition_seconds": 0.2}
    assert jh.edge_frames(meta, {"transition": "dip"}, 90, 30, 1920, 1080) == (7, 7)
    assert jh.edge_frames(meta, {"transition": "in"}, 90, 30, 1920, 1080) == (7, 0)
    assert jh.edge_frames(meta, {"transition": "none"}, 90, 30, 1920, 1080) == (0, 0)
    # a 1 s beat still has frames between its seams; a beat too short for its dip carries none (render._edge_filter)
    assert jh.edge_frames(meta, {"transition": "dip"}, 30, 30, 1920, 1080) == (7, 7)
    assert jh.edge_frames(meta, {"transition": "dip"}, 12, 30, 1920, 1080) == (0, 0)


def _kb(tmp_path, reduced, W=1920, H=1080):
    F.slide_image(str(tmp_path / "kb.png"), W, H)
    s = {"index": 1, "type": "slide", "image": "kb.png",
         "motion": {"type": "kenburns", "from": [0.3, 0.4, 1.0], "to": [0.6, 0.5, 1.12]}}
    return jh.kenburns_scene(str(tmp_path), {"reduced_motion": reduced}, s, 60, W, H)


def test_the_ken_burns_geometry_follows_the_move_and_a_reduced_motion_film_holds_still(tmp_path):
    moving = _kb(tmp_path, False)
    assert moving[0] and len(moving) == 60
    a, b = moving[0][0], moving[59][0]
    assert b["w"] == pytest.approx(a["w"] * (1 + 0.12 * 59 / 60), rel=1e-6), "the tile grows with the zoom"
    assert (a["x"], a["y"]) != (b["x"], b["y"])
    still = _kb(tmp_path, True)
    assert still[0][0] == still[59][0], "reduced motion: zoompan's move is held, so the truth is a still"


def test_ken_burns_tiles_are_found_in_a_portrait_frame(tmp_path):
    tiles = _kb(tmp_path, False, 1080, 1920)[0]
    assert tiles and all(0 <= t["x"] and t["x"] + t["w"] <= 1080 + 1 for t in tiles)


def test_a_platform_safe_frame_maps_the_page_into_its_scaled_frame():
    place = jh._mapper({"fw": 864, "fh": 1536, "x0": 108, "y0": 96}, 1080, 1920)
    assert place(0, 0, 1080, 1920) == (108, 96, 864, 1536)
    assert jh._mapper(None, 1080, 1920)(5, 6, 7, 8) == (5, 6, 7, 8)


def test_the_page_census_reports_each_lines_own_text_box():
    """The census JS reports the text's own box (tx/ty/tw/th) — a centred line in a full-width block would otherwise
    put the window on empty ground — and the glide judge's y is untouched."""
    import keyframe_qa as kq
    js = kq._GLIDE_JS_TMPL
    assert "rec.tx" in js and "selectNodeContents" in js and "y: Math.round(r.top" in js


# ── the films ───────────────────────────────────────────────────────────────────────────────────────────────────
def _verdict(out_dir):
    """(exit code, {scene index: worst level}, stdout) of jitter_qa on a rendered film."""
    r = subprocess.run([sys.executable, os.path.join(_ROOT, "scripts", "jitter_qa.py"), out_dir, "--json",
                        os.path.join(out_dir, "jitter.json")], capture_output=True, text=True, cwd=_ROOT)
    worst = {}
    if os.path.exists(os.path.join(out_dir, "jitter.json")):
        rank = {"error": 2, "warn": 1, "clean": 0}
        for ln in json.load(open(os.path.join(out_dir, "jitter.json")))["lines"]:
            sc = int(ln["key"][1:3])
            worst[sc] = max(worst.get(sc, "clean"), ln["level"], key=lambda v: rank[v])
    return r.returncode, worst, r.stdout


def _film(tmp_path, scenes, **kw):
    out = str(tmp_path / "film")
    F.build(out, scenes, **kw)
    F.render(out)
    return out


@needs_render
@pytest.mark.parametrize("kw", [{}, {"aspect": "9:16"}, {"W": 1080, "H": 1080}], ids=["16x9", "9x16", "1x1"])
def test_a_snapped_crawl_fails_a_gliding_one_passes_and_every_scene_is_judged(tmp_path, kw):
    out = _film(tmp_path, ["snapped", "smooth", "kenburns", "still", "title"], **kw)
    code, worst, stdout = _verdict(out)
    assert code == 1, stdout
    assert worst.get(1) == "error", (worst, stdout)
    assert worst.get(2) == "clean" and worst.get(4) == "clean", (worst, stdout)
    assert 3 in worst, "the Ken Burns slide is judged (its verdict is the zoompan's own: see the module docstring)"
    assert worst.get(5) == "clean" and "judged on its settled span" in stdout, (worst, stdout)
    assert "scope: MEASURED" in stdout


@needs_render
def test_cjk_and_dark_type_on_pages(tmp_path):
    out = _film(tmp_path, ["cjk-snapped", "cjk-smooth", "dark-snapped", "dark-smooth"])
    code, worst, stdout = _verdict(out)
    assert worst.get(1) == "error" and worst.get(2) == "clean", (worst, stdout)
    assert worst.get(3) == "error" and worst.get(4) in ("clean", "warn"), (worst, stdout)


@needs_render
def test_a_reduced_motion_film_with_captions_and_one_second_beats(tmp_path):
    """Reduced motion: the page crawls are held by reduced-motion.css, the Ken Burns by zoompan — nothing moves,
    nothing trembles; captions burn over the page and their zone is left out; 1 s beats keep frames between seams."""
    out = _film(tmp_path, ["snapped", "kenburns", "still"], seconds=1.0, reduced_motion=True, captions=True)
    code, worst, stdout = _verdict(out)
    assert code == 0, stdout
    assert all(v != "error" for v in worst.values()), (worst, stdout)


@needs_render
def test_a_video_of_another_render_is_unmeasured(tmp_path):
    out = _film(tmp_path, ["smooth", "still"])
    mp4 = os.path.join(out, "out.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-frames:v", "150", "-c:v", "libx264",
                    os.path.join(out, "cut.mp4")], check=True)
    os.replace(os.path.join(out, "cut.mp4"), mp4)
    code, _w, stdout = _verdict(out)
    assert code == 2 and "NOT MEASURED" in stdout, stdout
