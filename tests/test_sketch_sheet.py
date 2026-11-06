"""The sketch sheet (spec 2026-11-06 B2/B3): every beat's `slide.sketch` drawn as a greybox tile — PIL only, seconds —
and measured BEFORE any shot is built. A finding here costs a sentence to fix; the same finding after a build cost
the ANC film a re-render."""
import json
import os
import sys

from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import sketch_sheet as ss  # noqa: E402


def _sk(hero=(0.30, 0.20, 0.40, 0.50), other=(0.74, 0.30, 0.18, 0.10), metaphor="a tiny spring-loaded gate"):
    return {"metaphor": metaphor, "hero": "switch", "camera": "hold", "environment": "desk",
            "layout": [{"name": "switch", "rect": list(hero), "hero": True},
                       {"name": "label", "rect": list(other)}]}


def _slides(sketches):
    return [{"index": i + 1, "shot": "S", "sketch": s} for i, s in enumerate(sketches)]


def _varied(n):
    return _slides([_sk(hero=(0.05 + 0.1 * (i % 4), 0.15, 0.4, 0.5)) for i in range(n)])


def test_a_varied_sketched_film_has_no_findings():
    assert ss.findings(_varied(4), 1920, 1080) == []


def test_a_hero_too_small_to_lead_is_named():
    s = _varied(3)
    s[1]["sketch"]["layout"][0]["rect"] = [0.4, 0.3, 0.1, 0.1]               # 1 % of the frame
    f = ss.findings(s, 1920, 1080)
    assert any("beat 2" in x and "hero" in x for x in f), f


def test_a_sparse_film_is_named_at_its_median():
    tiny = [_sk(hero=(0.1 * i, 0.1, 0.1, 0.1), other=(0.8, 0.1, 0.05, 0.05)) for i in range(4)]
    f = ss.findings(_slides(tiny), 1920, 1080)
    assert any("SPARSE" in x for x in f), f


def test_the_same_layout_three_beats_running_is_named():
    f = ss.findings(_slides([_sk(), _sk(), _sk(), _sk(hero=(0.05, 0.1, 0.5, 0.6))]), 1920, 1080)
    assert any("same layout" in x and "1-3" in x for x in f), f


def test_a_rect_in_the_caption_band_is_named_with_the_aspects_own_band():
    # 0.84 of 1080 = 907 px: under the 16:9 band (1080-200 = 880) — and the 9:16 band is 257 px of 1920
    s = _varied(3)
    s[0]["sketch"]["layout"][1]["rect"] = [0.7, 0.80, 0.2, 0.05]
    assert any("beat 1" in x and "caption band" in x for x in ss.findings(s, 1920, 1080))
    s[0]["sketch"]["layout"][1]["rect"] = [0.7, 0.85, 0.2, 0.01]            # 1632..1651 of 1920: under 1663
    assert not any("caption band" in x for x in ss.findings(s, 1080, 1920))
    s[0]["sketch"]["layout"][1]["rect"] = [0.7, 0.87, 0.2, 0.02]            # 1670.. : inside the 257 px band
    assert any("caption band" in x for x in ss.findings(s, 1080, 1920))


def test_an_unsketched_beat_is_named_not_skipped():
    s = _varied(3)
    del s[2]["sketch"]
    assert any("beat 3" in x and "no sketch" in x for x in ss.findings(s, 1920, 1080))


def test_tile_draws_the_hero_darker_than_the_ground_and_marks_the_caption_band():
    im = ss.tile(_slides([_sk()])[0], 1920, 1080, tile_w=480)
    w, h = im.size
    assert (w, h) == (480, 270)
    hero_px = im.getpixel((int(0.5 * w), int(0.45 * h)))
    ground_px = im.getpixel((int(0.05 * w), int(0.05 * h)))
    band_px = im.getpixel((int(0.05 * w), h - 3))
    assert sum(hero_px) < sum(ground_px) and band_px != ground_px


def test_the_through_object_ribbon_joins_its_beats(tmp_path):
    board = {"meta": {"renderer": "remotion", "through_object": {"name": "cap", "beats": [1, 2]}},
             "slides": _varied(2)}
    (tmp_path / "storyboard.json").write_text(json.dumps(board))
    out = ss.build(str(tmp_path), desktop=False)
    sheet = Image.open(out).convert("RGB")
    assert sheet.getpixel(ss.ribbon_probe(0, th=270)) == ss.RIBBON


def test_cli_writes_the_sheet_and_exits_1_on_findings(tmp_path):
    board = {"meta": {"renderer": "remotion"}, "slides": _slides([_sk(), _sk(), _sk()])}
    (tmp_path / "storyboard.json").write_text(json.dumps(board))
    assert ss.main([str(tmp_path), "--no-desktop"]) == 1
    assert os.path.exists(tmp_path / "_sketch_review.png")


def test_chinese_metaphor_is_drawn_with_a_cjk_face(tmp_path):
    board = {"meta": {"renderer": "remotion"}, "slides": _slides([_sk(metaphor="轴体是一扇带弹簧的小门")] + _varied(2)[1:])}
    (tmp_path / "storyboard.json").write_text(json.dumps(board))
    assert ss.main([str(tmp_path), "--no-desktop"]) == 0
