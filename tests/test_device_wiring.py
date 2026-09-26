"""From the storyboard to what the registers draw: every text target becomes a point, every step a window,
every field a box, every recording a mapping — or the beat is refused with every reason at once."""
import json
import os
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import device_script as ds          # noqa: E402

FONT = os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf")
FPS = 30


def _ui(tmp_path, name="ui.png", h=2532):
    im = Image.new("RGB", (1170, h), "white")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([60, 200, 1110, 320], radius=36, fill=(238, 241, 244))
    d.text((110, 232), "搜索反馈", fill=(140, 147, 160), font=ImageFont.truetype(FONT, 46))
    d.text((90, 700), "反馈汇总", fill=(20, 23, 28), font=ImageFont.truetype(FONT, 46))
    (tmp_path / "ui").mkdir(exist_ok=True)
    im.save(str(tmp_path / "ui" / name))
    return "ui/" + name


def _fake_recognizer(path):
    return [{"text": "搜索反馈", "box": [110 / 1170, 232 / 2532, 300 / 1170, 280 / 2532]},
            {"text": "反馈汇总", "box": [90 / 1170, 700 / 2532, 290 / 1170, 750 / 2532]}]


def test_prepare_fills_everything_the_register_needs(tmp_path):
    img = _ui(tmp_path)
    props = {"device": "phone", "steps": [
        {"screen": {"image": img}}, {"type": "上周的反馈", "into": {"text": "搜索反馈"}},
        {"tap": {"text": "反馈汇总"}, "at": 0.7}]}
    out, warns = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS,
                            W=1920, H=1080, lang="zh", recognizer=_fake_recognizer)
    s0, s1, s2 = out["steps"]
    assert s0["imageW"] == 1170 and s0["imageH"] == 2532
    assert isinstance(s1["into"], list) and s1["field"]["bg"].startswith("#") and s1["field"]["ink"] == "#111111"
    assert isinstance(s2["tap"], list) and abs(s2["tap"][1] - 725 / 2532) < 0.01
    assert all(k in s2 for k in ("t0", "ta", "t1", "focus", "textFrac", "captionPx"))
    assert s2["ta"] == pytest.approx(0.7, abs=2e-3)


def test_every_problem_is_reported_at_once(tmp_path):
    props = {"device": "phone", "steps": [{"screen": {"image": "missing.png"}}, {"tap": {"text": "不在图里"}}]}
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920, H=1080,
                   lang="zh", recognizer=_fake_recognizer)
    assert "missing.png" in str(e.value)


def test_a_target_scrolled_out_of_view_is_refused(tmp_path):
    img = _ui(tmp_path, "long.png", h=6000)
    props = {"device": "phone", "steps": [{"screen": {"image": img}}, {"scroll": 1.0}, {"tap": [0.5, 0.1]},
                                          {"tap": {"text": "反馈汇总"}}]}
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=300, fps=FPS, W=1920, H=1080,
                   lang="zh", recognizer=_fake_recognizer)
    assert "scroll" in str(e.value) and "view" in str(e.value)


def test_validate_reports_a_device_beat_by_name(tmp_path):
    import validate as v
    img = _ui(tmp_path)
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "DeviceDemo", "narration": "先搜索。", "audio": "audio/01.mp3",
                         "duration": 1.0, "image": "ui/ui.png",
                         "shot_props": {"device": "phone", "steps": [{"screen": {"image": img}}] +
                                        [{"tap": [0.5, 0.5]}] * 6}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    assert any("scene #1" in e and "beat" in e for e in errs), errs


def test_a_film_in_auto_language_measures_captions_in_its_narrations_script():
    """meta.language defaults to "auto"; passed through as-is it read as not-Chinese, and a Chinese film's
    captions were measured with the Latin sample (43 px against 41 at 1920x1080) — ruling R12."""
    assert ds.film_language({"language": "auto"}, [{"narration": "先在上面搜索上周的反馈"}]) == "zh"
    assert ds.film_language({}, [{"narration": "Search last week's feedback"}]) == "en"
    assert ds.film_language({"language": "ja"}, [{"narration": "先在上面搜索"}]) == "ja"
