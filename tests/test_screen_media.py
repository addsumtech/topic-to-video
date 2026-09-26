"""A screenshot's facts are read from the file. Light AND dark screenshots, because every constant here is a
threshold that a dark UI turns upside down."""
import os
import subprocess
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import device_script as ds          # noqa: E402
import screen_media as sm           # noqa: E402

FONT = os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf")


def _shot(path, w=1170, h=2532, bg=(255, 255, 255), ink=(20, 23, 28), field=None, lines=(), border=None):
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    if field:
        (x0, y0, x1, y1), fcol = field
        d.rounded_rectangle([x0, y0, x1, y1], radius=int((y1 - y0) * 0.3), fill=fcol, outline=border,
                            width=1 if border else 0)
    for (x, y, text, px) in lines:
        d.text((x, y), text, fill=ink, font=ImageFont.truetype(FONT, px))
    im.save(path)
    return path


def test_an_android_screenshot_fits_a_phone(tmp_path):
    assert sm.fit_kind({"w": 1080, "h": 2400}, "phone") == "fit"          # 2.6% taller: inside the 4%


def test_a_long_screenshot_is_long_and_a_wide_one_is_refused():
    assert sm.fit_kind({"w": 1170, "h": 6000}, "phone") == "long"
    with pytest.raises(ds.DeviceScriptError) as e:
        sm.fit_kind({"w": 2560, "h": 1600}, "phone")
    assert "wider" in str(e.value)


def test_text_height_is_the_ink_band_under_the_point(tmp_path):
    p = _shot(str(tmp_path / "a.png"), lines=[(80, 600, "发票下载失败", 48), (80, 760, "搜索结果不准确", 48)])
    h = sm.text_band_px(p, 0.2, (600 + 30) / 2532)
    assert h is not None and 35 <= h <= 60, h


def test_dark_mode_text_and_field(tmp_path):
    p = _shot(str(tmp_path / "d.png"), bg=(12, 14, 20), ink=(236, 239, 244),
              field=((60, 300, 1110, 420), (38, 42, 52)), lines=[(110, 330, "搜索反馈", 44), (80, 700, "设置", 48)])
    assert sm.text_band_px(p, 0.1, (700 + 30) / 2532) is not None
    f = sm.field_at(p, 0.5, 360 / 2532)
    x0, y0, x1, y1 = f["box"]
    assert abs(x0 - 60 / 1170) < 0.03 and abs(x1 - 1110 / 1170) < 0.03, f
    assert abs(y0 - 300 / 2532) < 0.01 and abs(y1 - 420 / 2532) < 0.01, f
    assert f["ink"] == "#ffffff" and f["textPx"] is not None


def test_a_light_field_on_a_white_page(tmp_path):
    p = _shot(str(tmp_path / "l.png"), field=((60, 300, 1110, 420), (238, 241, 244)),
              lines=[(110, 330, "搜索反馈", 44)])
    f = sm.field_at(p, 0.5, 360 / 2532)
    assert abs(f["box"][0] - 60 / 1170) < 0.03 and abs(f["box"][2] - 1110 / 1170) < 0.03, f
    assert f["ink"] == "#111111"


def test_a_real_search_field_with_placeholder_text(tmp_path):
    """Ruling R1: a real placeholder fills ~47% of its field's height, so a column through a vertical stroke is
    only ~53% field colour. Growth at 0.6 stalled on the first stroke and returned a sliver."""
    p = _shot(str(tmp_path / "s.png"), ink=(142, 142, 147), field=((60, 300, 1110, 408), (238, 241, 244)),
              lines=[(140, 322, "搜索上周的客户反馈", 51)])
    for x in (0.8, 0.3):                                        # right of the placeholder, and ON it
        f = sm.field_at(p, x, 354 / 2532)
        x0, y0, x1, y1 = f["box"]
        assert abs(x0 - 60 / 1170) < 0.01 and abs(x1 - 1111 / 1170) < 0.01, (x, f)
        assert abs(y0 - 300 / 2532) < 0.005 and abs(y1 - 409 / 2532) < 0.005, (x, f)
        assert f["bg"] == "#eef1f4" and 40 <= f["textPx"] <= 55, (x, f)


def test_a_point_on_centred_placeholder_text_finds_the_field(tmp_path):
    """Ruling R6: a centred placeholder (WeChat's 搜索) sits exactly where `into: [0.5, y]` points. Seeded on the
    point, growth started on a glyph and returned a 1x1 box in the ink's colour."""
    p = _shot(str(tmp_path / "w.png"), bg=(237, 237, 237), ink=(178, 178, 178),
              field=((30, 250, 1140, 350), (255, 255, 255)), lines=[(535, 270, "搜索", 50)])
    f = sm.field_at(p, 0.5, 300 / 2532)
    x0, y0, x1, y1 = f["box"]
    assert abs(x0 - 30 / 1170) < 0.01 and abs(x1 - 1141 / 1170) < 0.01, f
    assert abs(y0 - 250 / 2532) < 0.005 and abs(y1 - 351 / 2532) < 0.005, f
    assert f["bg"] == "#ffffff" and f["ink"] == "#111111", f


def test_a_thin_field_is_not_mistaken_for_the_page(tmp_path):
    """A 60px field: a colour vote over a tall window sees more page than field and grows over the page."""
    p = _shot(str(tmp_path / "t.png"), ink=(60, 60, 67), field=((40, 500, 1130, 560), (242, 242, 247)),
              lines=[(555, 509, "搜索", 30)])
    f = sm.field_at(p, 0.5, 530 / 2532)
    assert abs(f["box"][1] - 500 / 2532) < 0.003 and abs(f["box"][3] - 561 / 2532) < 0.003, f
    assert f["bg"] == "#f2f2f7", f


def test_a_bordered_field_on_a_near_white_page(tmp_path):
    """A desktop field is often white on a near-white page (5/channel apart, inside FIELD_TOL) with a 1px border:
    the border is its edge. Pointed near its left end, where a fixed-width seed would reach past it."""
    p = _shot(str(tmp_path / "b.png"), w=2560, h=1600, bg=(250, 250, 252), ink=(120, 120, 130),
              field=((900, 120, 1660, 176), (255, 255, 255)), border=(200, 200, 204), lines=[(940, 130, "搜索", 26)])
    f = sm.field_at(p, 0.36, 148 / 1600)
    x0, y0, x1, y1 = f["box"]
    assert abs(x0 - 901 / 2560) < 0.003 and abs(x1 - 1660 / 2560) < 0.003, f
    assert abs(y0 - 121 / 1600) < 0.003 and abs(y1 - 176 / 1600) < 0.003, f


def test_no_field_under_the_point_is_an_error(tmp_path):
    p = _shot(str(tmp_path / "n.png"), field=((60, 300, 1110, 400), (238, 241, 244)), lines=[(100, 325, "搜索", 44)])
    with pytest.raises(ds.DeviceScriptError) as e:
        sm.field_at(p, 0.5, 0.6)                                # the page, far from the field
    assert "no text field under (0.50, 0.60)" in str(e.value)
    q = _shot(str(tmp_path / "e.png"), w=2560, h=1600, bg=(250, 250, 252), ink=(120, 120, 130),
              field=((900, 120, 1660, 176), (255, 255, 255)), lines=[(940, 130, "搜索", 26)])
    with pytest.raises(ds.DeviceScriptError) as e:
        sm.field_at(q, 0.36, 148 / 1600)                        # no border, and a fill 5/channel from the page
    assert "no visible edge" in str(e.value)
    r = _shot(str(tmp_path / "o.png"), ink=(20, 20, 20), field=((60, 300, 1110, 340), (238, 241, 244)),
              lines=[(62, 286, "搜索上周的客户反馈很长很长的文字", 44)])
    with pytest.raises(ds.DeviceScriptError):
        sm.field_at(r, 0.3, 320 / 2532)                         # text as tall as the region: no padding, no field


def test_caption_ink_is_measured_from_the_bundled_face():
    zh, en = sm.caption_ink_px("zh", 1920, 1080), sm.caption_ink_px("en", 1920, 1080)
    assert 25 < zh < 60 and 20 < en < 60, (zh, en)


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="needs ffmpeg")
def test_a_recording_is_probed_and_its_limits_checked(tmp_path):
    v = str(tmp_path / "r.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=390x844:rate=30",
                    "-t", "4", "-pix_fmt", "yuv420p", v], check=True)
    f = sm.video_facts(v)
    assert abs(f["duration"] - 4) < 0.1 and f["w"] == 390 and f["h"] == 844
    assert sm.check_video(f, "phone", 0, 3) == []
    assert any("longer than" in p for p in sm.check_video(f, "phone", 0, 9))
