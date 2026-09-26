"""Text targets: found, or refused with what WAS found. Never a guess."""
import json
import os
import threading
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


def test_nth_below_one_is_refused_not_wrapped():
    """`(nth or 1) - 1` read 0 as 1 and -1 as the last place — a silent wrong target."""
    for bad in (0, -1, 1.5, True):
        with pytest.raises(ds.DeviceScriptError) as e:
            st.find_text(LINES, "设置", nth=bad)
        assert "`nth`" in str(e.value)


def test_full_width_punctuation_matches_half_width():
    lines = [{"text": "设置：通知", "box": [0.1, 0.5, 0.5, 0.53]}, {"text": "ＡＩ 助手", "box": [0.1, 0.6, 0.4, 0.63]}]
    assert st.find_text(lines, "设置:")["y"] == pytest.approx(0.515)
    assert st.find_text(lines, "AI助手")["y"] == pytest.approx(0.615)


def test_a_lengthened_character_does_not_move_a_match():
    """NFKC turns ㎡ into m2: counted in folded characters, 说明 in 说明15㎡ ended at 2/6 of the line, not 2/5."""
    r = st.find_text([{"text": "说明15㎡", "box": [0.0, 0.0, 1.0, 0.1]}], "说明")
    assert r["box"][2] == pytest.approx(2 / 5)
    r = st.find_text([{"text": "面积15㎡说明", "box": [0.0, 0.0, 1.0, 0.1]}], "说明")
    assert r["box"][0] == pytest.approx(5 / 7) and r["box"][2] == pytest.approx(1.0)
    assert st.find_text([{"text": "面积15㎡说明", "box": [0.0, 0.0, 1.0, 0.1]}], "m2")["box"][0] == pytest.approx(4 / 7)


def test_racing_writers_each_land_a_whole_file(tmp_path):
    """A pid-only temp name let threads share one temp file: three of four raised, and the content was mixed."""
    target, errors = tmp_path / "out.json", []

    def worker(k):
        def write(tmp):
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"writer": k, "pad": "x" * 20000}))
        try:
            st._replace(str(target), write)
        except Exception as e:                                  # noqa: BLE001 — the test counts any failure
            errors.append(e)
    threads = [threading.Thread(target=worker, args=(k,)) for k in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    assert json.loads(target.read_text(encoding="utf-8"))["writer"] in range(8)
    assert [p.name for p in tmp_path.iterdir()] == ["out.json"]
    with pytest.raises(ds.DeviceScriptError) as e:
        st._replace(str(tmp_path / "missing" / "x.json"), lambda tmp: None)
    assert "cannot write" in str(e.value)


def test_a_missing_screenshot_and_a_torn_cache_entry(tmp_path, monkeypatch):
    with pytest.raises(ds.DeviceScriptError) as e:
        st.recognize(str(tmp_path / "nope.png"), cache_dir=str(tmp_path))
    assert "does not exist" in str(e.value)
    p = tmp_path / "s.png"
    Image.new("RGB", (40, 40), "white").save(p)
    monkeypatch.setattr(st, "available", lambda: "vision")
    monkeypatch.setattr(st, "_vision", lambda path: [{"text": "设置", "box": [0.1, 0.1, 0.2, 0.2]}])
    memo = tmp_path / "screen_text" / ("%s-vision.json" % st._sha(str(p)))
    memo.parent.mkdir()
    memo.write_text("{not json", encoding="utf-8")         # what an interrupted write leaves
    assert st.recognize(str(p), cache_dir=str(tmp_path))[0]["text"] == "设置"
    assert json.loads(memo.read_text(encoding="utf-8"))[0]["text"] == "设置"


def test_an_unrunnable_helper_is_rebuilt_once(tmp_path, monkeypatch):
    """A helper binary left torn by an interrupted build raised a raw `Exec format error`."""
    monkeypatch.setattr(st, "_BIN_DIR", str(tmp_path))
    exe = tmp_path / ("ocr_macos-" + st._sha(st._SWIFT)[:16])
    exe.write_bytes(b"\0" * 37)
    exe.chmod(0o755)

    def fake_compile(path):
        with open(path, "w") as fh:
            fh.write("#!/bin/sh\necho '[]'\n")
        os.chmod(path, 0o755)
    monkeypatch.setattr(st, "_compile", fake_compile)
    img = tmp_path / "s.png"
    Image.new("RGB", (40, 40), "white").save(img)
    assert st._vision(str(img)) == []


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
