"""Text targets: found, or refused with what WAS found. Never a guess."""
import os
import shutil
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import device_script as ds          # noqa: E402
import screen_text as st            # noqa: E402

LINES = [{"text": "反馈汇总", "box": [0.1, 0.30, 0.4, 0.33]},
         {"text": "按产品线分组", "box": [0.1, 0.40, 0.5, 0.43]},
         {"text": "设置", "box": [0.1, 0.80, 0.2, 0.83]},
         {"text": "设置", "box": [0.6, 0.80, 0.7, 0.83]}]


def test_a_whole_line_is_found_at_its_centre():
    r = st.find_text(LINES, "反馈汇总")
    assert r["x"] == pytest.approx(0.25) and r["y"] == pytest.approx(0.315)


def test_part_of_a_line_is_found_at_its_share_of_the_line():
    r = st.find_text(LINES, "产品线")
    assert 0.1 < r["box"][0] < r["box"][2] < 0.5 and r["box"][0] > 0.15


def test_text_that_is_not_there_lists_what_is():
    with pytest.raises(ds.DeviceScriptError) as e:
        st.find_text(LINES, "发票")
    assert "反馈汇总" in str(e.value) and "not found" in str(e.value)


def test_text_found_twice_needs_nth_and_nth_picks():
    with pytest.raises(ds.DeviceScriptError) as e:
        st.find_text(LINES, "设置")
    assert "2 places" in str(e.value)
    assert st.find_text(LINES, "设置", nth=2)["x"] == pytest.approx(0.65)


@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("swiftc"), reason="macOS Vision only")
def test_vision_finds_chinese_on_a_real_image(tmp_path):
    font = ImageFont.truetype(os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf"), 64)
    im = Image.new("RGB", (1170, 2532), "white")
    d = ImageDraw.Draw(im)
    d.text((100, 700), "反馈汇总", fill="black", font=font)
    d.text((100, 1200), "设置", fill="black", font=font)
    p = str(tmp_path / "s.png")
    im.save(p)
    r = st.find_text(st.recognize(p, cache_dir=str(tmp_path)), "反馈汇总")
    assert 0.05 < r["x"] < 0.4 and abs(r["y"] - (700 + 40) / 2532) < 0.02, r
