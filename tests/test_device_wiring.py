"""From the storyboard to what the registers draw: every text target becomes a point, every step a window,
every field a box, every recording a mapping — or the beat is refused with every reason at once."""
import json
import os
import shutil
import subprocess
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


def _recording(tmp_path, name, seconds, colour="white"):
    (tmp_path / "rec").mkdir(exist_ok=True)
    path = tmp_path / "rec" / name
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=%s:s=64x138:r=30:d=%d" % (colour, seconds),
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return "rec/" + name


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_every_recording_problem_is_reported_at_once(tmp_path):
    """The recording check raised on the FIRST offender, so a script with two over-fast recordings was fixed
    one error at a time — against prepare's own promise of every problem at once."""
    a, b = _recording(tmp_path, "a.mp4", 20), _recording(tmp_path, "b.mp4", 20)
    props = {"device": "phone", "steps": [{"screen": {"video": a, "from": 0, "to": 18}},
                                          {"screen": {"video": b, "from": 0, "to": 18}}]}
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920, H=1080,
                   lang="zh", recognizer=_fake_recognizer)
    assert "step 1 (screen)" in str(e.value) and "step 2 (screen)" in str(e.value), e.value.problems


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_a_mark_with_no_text_to_measure_is_counted_unmeasured(tmp_path):
    """A mark's push-in is measured on the recording's frame; a mark where nothing can be measured used to be
    left out of the count, so an unmeasured target read as a passing one."""
    v = _recording(tmp_path, "plain.mp4", 6)
    props = {"device": "phone", "steps": [{"screen": {"video": v, "from": 0, "to": 5}},
                                          {"mark": [0.5, 0.5], "video": 2.0}]}
    _out, warns = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920,
                             H=1080, lang="zh", recognizer=_fake_recognizer)
    assert any("measured 0 of 1" in w for w in warns), warns


def test_a_hero_is_checked_like_a_demo(tmp_path):
    img = _ui(tmp_path)
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.prepare({"device": "phone", "look": "bogus", "placement": "nowhere", "screen": {"image": img}},
                   shot="DeviceHero", out_dir=str(tmp_path), dur_frames=150, fps=FPS, W=1920, H=1080, lang="zh")
    assert "`look`" in str(e.value) and "`placement`" in str(e.value)
    for screen, needle in (({}, "exactly one of image / video"), (None, "needs `screen`"),
                           ({"page": "demo"}, "register's own preview")):
        props = {"device": "laptop"} if screen is None else {"device": "phone", "screen": screen}
        with pytest.raises(ds.DeviceScriptError) as e:     # a film's hero shows the product, never the skeleton
            ds.prepare(props, shot="DeviceHero", out_dir=str(tmp_path), dur_frames=150, fps=FPS, W=1920, H=1080,
                       lang="zh")
        assert needle in str(e.value), (screen, e.value.problems)


def test_a_text_target_is_measured_by_its_ink_not_its_recognition_box(tmp_path):
    """The push-in brings a target to the caption's INK height, but a text target took its height from the
    recognition BOX — Vision's line box, 1.1–1.6x the ink and not the same for two identical rows — so every text
    target was pushed in about a third too little (a real film's rows read 67–74% of its caption). The box now
    only bounds where the ink is measured."""
    import screen_media as sm
    img = _ui(tmp_path)
    tall_box = lambda path: [{"text": "反馈汇总", "box": [90 / 1170, 690 / 2532, 290 / 1170, 770 / 2532]}]
    props = {"device": "phone", "steps": [{"screen": {"image": img}}, {"tap": {"text": "反馈汇总"}, "at": 0.7}]}
    out, _ = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920, H=1080,
                        lang="zh", recognizer=tall_box)
    ink = sm.text_band_px(str(tmp_path / img), 190 / 1170, 725 / 2532)
    got = out["steps"][1]["textFrac"] * 1170
    assert ink and abs(got - ink) <= 1, "measured %.1f px for text whose ink is %.1f px (the box is 80 px)" % (got, ink)


def _ink_rows(path, x0, x1, y0, y1):
    """(top, bottom) source rows holding ink inside the given region — the truth the measure is checked against."""
    import numpy as np
    a = np.asarray(Image.open(path).convert("L"), dtype=float)[y0:y1, x0:x1]
    rows = np.flatnonzero((a < 200).any(axis=1))
    return y0 + int(rows[0]), y0 + int(rows[-1])


def test_a_box_cut_tighter_than_its_glyphs_still_measures_the_ink(tmp_path):
    """A recogniser whose box stops short of the descenders (here: the top 70% of the ink) must not shrink the
    push-in's measure: the ink is looked for past the box, and a line the wider look still isolates is exact."""
    img = _ui(tmp_path)
    top, bottom = _ink_rows(str(tmp_path / img), 90, 290, 650, 850)     # 「反馈汇总」, drawn at y 700
    ink = bottom - top + 1
    tight = lambda path: [{"text": "反馈汇总", "box": [90 / 1170, top / 2532, 290 / 1170, (top + 0.7 * ink) / 2532]}]
    props = {"device": "phone", "steps": [{"screen": {"image": img}}, {"tap": {"text": "反馈汇总"}, "at": 0.7}]}
    out, warns = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920,
                            H=1080, lang="zh", recognizer=tight)
    assert abs(out["steps"][1]["textFrac"] * 1170 - ink) <= 1, (out["steps"][1]["textFrac"] * 1170, ink)
    assert not any("told apart" in w for w in warns), warns


def test_a_line_that_runs_into_the_next_one_is_reported_not_guessed(tmp_path):
    """Two rows set closer than their own size touch, and their ink reads as one band 1.2x the line: that is not
    this line's height. It is reported by step, and the recognition box stands in for the height."""
    im = Image.new("RGB", (1170, 2532), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 46)
    d.text((90, 700), "反馈汇总", fill=(20, 23, 28), font=f)
    d.text((90, 740), "意见反馈", fill=(20, 23, 28), font=f)       # a 40 px pitch for 46 px type: the ink touches
    (tmp_path / "ui").mkdir(exist_ok=True)
    im.save(str(tmp_path / "ui" / "tight.png"))
    box = lambda path: [{"text": "反馈汇总", "box": [90 / 1170, 700 / 2532, 290 / 1170, 750 / 2532]}]
    props = {"device": "phone", "steps": [{"screen": {"image": "ui/tight.png"}}, {"tap": {"text": "反馈汇总"}, "at": 0.7}]}
    out, warns = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920,
                            H=1080, lang="zh", recognizer=box)
    assert any("step 2" in w and "told apart" in w for w in warns), warns
    assert abs(out["steps"][1]["textFrac"] * 1170 - 50) <= 1, out["steps"][1]["textFrac"] * 1170


def test_a_beat_is_checked_before_its_narration_exists(tmp_path):
    """Before tts.py the timing cannot be checked, but a misspelt look or a missing screenshot can — they used to
    wait, unreported, until the narration existed."""
    bad = {"shot": "DeviceDemo", "shot_props": {"device": "phone", "look": "glossy", "steps": [
        {"screen": {"image": "ui/none.png"}}, {"tap": [0.5, 0.5]}]}}
    errs, _ = ds.check_slide(bad, str(tmp_path), {})
    assert any("`look`" in e for e in errs) and any("ui/none.png" in e and "does not exist" in e for e in errs), errs
    hero = {"shot": "DeviceHero", "shot_props": {"screen": {"video": "rec/none.mp4"}}}
    errs, _ = ds.check_slide(hero, str(tmp_path), {})
    assert any("rec/none.mp4" in e and "does not exist" in e for e in errs), errs
    good = {"shot": "DeviceDemo", "shot_props": {"device": "phone", "steps": [{"screen": {"image": _ui(tmp_path)}},
                                                                           {"tap": [0.5, 0.5]}]}}
    assert ds.check_slide(good, str(tmp_path), {}) == ([], [])


def test_a_missing_field_is_named_at_the_point_the_author_wrote(tmp_path):
    """The refusal named the SCREENSHOT's fraction, which on a long screenshot is not the number in the script."""
    img = _ui(tmp_path, "long.png", h=4200)
    props = {"device": "phone", "steps": [{"screen": {"image": img}}, {"type": "上周", "into": [0.5, 0.04]}]}
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920, H=1080,
                   lang="zh", recognizer=_fake_recognizer)
    assert "at [0.50, 0.04] on the screen" in str(e.value) and "of the screenshot" in str(e.value), e.value.problems


def test_a_scripted_beat_is_not_called_rushed():
    """validate's natural-pace warning compares a beat with its register's standalone length; a DeviceDemo beat is
    paced by its script (every step scheduled into the beat, and refused when it does not fit), so the warning
    fired on every short line and said nothing true. An unscripted short beat is still warned."""
    import validate as v
    slides = [{"shot": "DeviceDemo", "duration": 2.5, "shot_props": {"steps": [{"screen": {"image": "a.png"}}]}},
              {"shot": "DeviceHero", "duration": 2.5, "shot_props": {}},
              {"shot": "InOrder", "duration": 2.0, "shot_props": {"steps": [{"label": "one"}, {"label": "two"}]}}]
    warnings = []
    v._shot_truncation({}, slides, [], warnings)
    assert not any("beat 1 " in w for w in warnings), warnings
    # another register that happens to take a `steps` list is still paced (the skip once silenced five of them)
    assert any("beat 2 " in w for w in warnings) and any("beat 3 " in w for w in warnings), warnings


def test_a_switch_default_is_a_choice_not_demo_furniture():
    """shot_proof warned "device is the register's DEMO DEFAULT 'phone'" on every phone DeviceDemo. A prop typed as
    a choice of literals is a setting the film makes; only copy can be leftover demo furniture."""
    import shot_proof as sp
    assert {"device", "look", "placement", "camera"} <= sp.switch_props("DeviceDemo"), sp.switch_props("DeviceDemo")
    assert {"device", "look", "placement"} <= sp.switch_props("DeviceHero")
    assert "kicker" not in sp.switch_props("DeviceDemo") and not sp.switch_props("CommandSummon")


def test_a_film_gate_draws_a_device_beat_as_the_film_does(tmp_path):
    """text_safe_qa, shot_proof and cjk_type_qa render a beat through film_shot_props; it never prepared a device
    script, so every device beat of a correct film "failed to render" (no prepared time) and no device film
    could pass delivery. The gates' props are the film's: every step timed, the screenshot sized."""
    import render_remotion as rr
    img = _ui(tmp_path)
    slide = {"shot": "DeviceDemo", "narration": "点开反馈汇总", "duration": 4.0,
             "shot_props": {"device": "phone", "steps": [{"screen": {"image": img}}, {"tap": [0.3, 0.28], "at": 0.6}]}}
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"language": "zh"}, "slides": [slide]},
                                                         ensure_ascii=False), encoding="utf-8")
    props = rr.film_shot_props(slide, str(tmp_path))
    assert all(k in st for st in props["steps"] for k in ("t0", "ta", "t1")), props["steps"]
    assert props["steps"][0]["imageW"] == 1170


def test_a_short_screenshot_has_nothing_to_scroll(tmp_path):
    img = _ui(tmp_path)                                      # exactly one phone screen tall
    props = {"device": "phone", "steps": [{"screen": {"image": img}}, {"scroll": 0.5}]}
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920, H=1080,
                   lang="zh", recognizer=_fake_recognizer)
    assert "nothing to scroll" in str(e.value), e.value.problems


def test_a_tablet_turns_to_a_landscape_screen(tmp_path):
    """Spec §1: a tablet is 3:4 portrait or 4:3 landscape. A 2732x2048 iPad capture was refused as "a capture of
    a different device"; the tablet now turns to the screen it shows."""
    Image.new("RGB", (2732, 2048), "white").save(str(tmp_path / "ipad.png"))
    out, _ = ds.prepare({"device": "tablet", "steps": [{"screen": {"image": "ipad.png"}}, {"tap": [0.5, 0.5]}]},
                        shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920, H=1080,
                        lang="zh", recognizer=_fake_recognizer)
    assert out["device"] == "tablet-landscape"
    img = _ui(tmp_path)                                      # a portrait capture keeps the portrait tablet
    out, _ = ds.prepare({"device": "tablet", "steps": [{"screen": {"image": img}}, {"tap": [0.5, 0.5]}]},
                        shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920, H=1080,
                        lang="zh", recognizer=_fake_recognizer)
    assert out.get("device", "tablet") == "tablet"


def test_a_capture_that_fits_another_device_says_which():
    import screen_media as sm
    with pytest.raises(ds.DeviceScriptError) as e:
        sm.fit_kind({"w": 1920, "h": 1080}, "laptop")
    assert 'use device "monitor"' in str(e.value), e.value.problems


def test_a_file_that_is_no_image_is_named_not_a_traceback(tmp_path):
    (tmp_path / "shot.png").write_bytes(b"this is not a picture")
    slide = {"shot": "DeviceDemo", "narration": "点开", "duration": 4.0,
             "shot_props": {"device": "phone", "steps": [{"screen": {"image": "shot.png"}}, {"tap": [0.3, 0.3]}]}}
    errs, _ = ds.check_slide(slide, str(tmp_path), {"language": "zh"})
    assert any("not an image this machine can read" in e for e in errs), errs


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_a_recording_holds_its_edges_instead_of_showing_black(tmp_path):
    """Outside its spans a recording draws black: through the beat's opening seam, and while the next screen
    pushes it out. Its first frame is held from the start, its last until it has gone."""
    v = _recording(tmp_path, "r.mp4", 6)
    img = _ui(tmp_path)
    props = {"device": "phone", "steps": [{"screen": {"video": v, "from": 0, "to": 4}},
                                          {"screen": {"image": img}, "via": "push"}]}
    out, _ = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920, H=1080,
                        lang="zh", recognizer=_fake_recognizer)
    import render_remotion as rr
    spans = out["steps"][0]["spans"]
    gone = rr.frame_at_t(180, out["steps"][1]["t1"])
    assert spans[0]["f0"] == 0 and spans[0]["v0"] == 0, spans
    assert spans[-1]["f1"] == pytest.approx(gone) and spans[-1]["v0"] == spans[-1]["v1"] == 4, spans


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_a_mark_at_the_recordings_last_moment_is_measured_not_a_crash(tmp_path):
    v = _recording(tmp_path, "end.mp4", 4)
    props = {"device": "phone", "steps": [{"screen": {"video": v, "from": 0, "to": 4}},
                                          {"mark": [0.5, 0.5], "video": 4.0}]}
    out, warns = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920,
                            H=1080, lang="zh", recognizer=_fake_recognizer)
    assert out["steps"][1]["t1"] > 0
    cut = [f for f in os.listdir(str(tmp_path / ".cache" / "device")) if f.startswith("end.mp4-")]
    assert cut, "no frame was cut at the recording's last moment, so the mark could never be measured"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_a_recording_stretched_into_slow_motion_is_said(tmp_path):
    v = _recording(tmp_path, "short.mp4", 2)
    _out, warns = ds.prepare({"device": "phone", "screen": {"video": v}}, shot="DeviceHero", out_dir=str(tmp_path),
                             dur_frames=180, fps=FPS, W=1920, H=1080, lang="zh")
    assert any("slow motion" in w for w in warns), warns


def test_a_label_on_a_button_is_measured_by_its_ink(tmp_path):
    """A button a little taller than its label: the wider of R22's two windows reached past the button onto the
    page, its own ground flipped to the page, the whole button read as ink, and the label fell back to its box
    with a warning that it "could not be told apart from the line next to it". Both windows now share a ground."""
    im = Image.new("RGB", (1170, 2532), "white")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([300, 1000, 870, 1070], radius=20, fill=(53, 99, 233))          # a 70 px button
    f = ImageFont.truetype(FONT, 40)
    d.text((585, 1035), "继续 Continue", fill="white", font=f, anchor="mm")
    (tmp_path / "ui").mkdir(exist_ok=True)
    im.save(str(tmp_path / "ui" / "btn.png"))
    import numpy as np
    a = np.asarray(Image.open(str(tmp_path / "ui" / "btn.png")).convert("L"), dtype=float)[1002:1068, 440:730]
    rows = np.flatnonzero((a > 200).any(axis=1))                  # the white label on the blue button
    top, bottom = 1002 + int(rows[0]), 1002 + int(rows[-1])
    ink = bottom - top + 1
    pad = 0.2 * ink                                          # a recogniser's line box: a little taller than the ink
    box = lambda path: [{"text": "继续 Continue", "box": [440 / 1170, (top - pad) / 2532, 730 / 1170,
                                                          (bottom + pad) / 2532]}]
    props = {"device": "phone", "steps": [{"screen": {"image": "ui/btn.png"}},
                                          {"tap": {"text": "继续 Continue"}, "at": 0.7}]}
    out, warns = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920,
                            H=1080, lang="zh", recognizer=box)
    assert not any("told apart" in w for w in warns), warns
    assert abs(out["steps"][1]["textFrac"] * 1170 - ink) <= 1, (out["steps"][1]["textFrac"] * 1170, ink)


def test_a_gate_meeting_a_refused_device_beat_names_it(tmp_path):
    import render_remotion as rr
    img = _ui(tmp_path)
    slide = {"shot": "DeviceDemo", "narration": "往下看", "duration": 4.0,
             "shot_props": {"device": "phone", "steps": [{"screen": {"image": img}}, {"scroll": 0.5}]}}
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {}, "slides": [slide]}, ensure_ascii=False),
                                              encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        rr.film_shot_props(slide, str(tmp_path))
    assert "nothing to scroll" in str(e.value) and "validate.py" in str(e.value), e.value

