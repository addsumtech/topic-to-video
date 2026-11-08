"""An object the voice names is shown as that object.

The WorkBuddy film (2026-11-08): beat 2 said "A report. A spreadsheet. A deck." over three identical blank cards, and
beat 8 named the list again as "a spreadsheet, a report, a dashboard" — the user: 最开始的三个空白，但是你说的是report，
sheet，deck，没有相应显示内容，而且后面有一个frame也又提到了这三个. The decodability rule was prose; the beat's own
ideal ("three blank files, waiting") contradicted its voice and nothing checked either. Now: the lists a voice names
are found (named_lists), a list named twice must agree, and the rendered beat must show each item — its name or the
evidence the beat declares, read off the picture with the caption band left out (named_objects_qa).
"""
import json
import os
import subprocess
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import named_lists as nl            # noqa: E402
import named_objects_qa as nq       # noqa: E402


# ── the lists a voice names ──────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text,items", [
    ("A report. A spreadsheet. A deck. Every week, the same pile of work, waiting to be made.",
     ["report", "spreadsheet", "deck"]),
    ("And it hands back results you can use: a spreadsheet, a report, a dashboard — ready to go.",
     ["spreadsheet", "report", "dashboard"]),
    ("Pick a template, a colour and a font.", ["template", "colour", "font"]),
    ("It reads a PDF, an Excel file, or a folder of notes.", ["pdf", "excel file", "folder of notes"]),
    ("它能做报告、表格和演示文稿。", ["报告", "表格", "演示文稿"]),
])
def test_a_list_the_voice_names_is_found(text, items):
    found = nl.lists_in(text)
    assert [it["key"] for it in found[0]] == items, found


@pytest.mark.parametrize("text", [
    "WorkBuddy breaks the task down, plans the steps, and carries them out — on its own, like a colleague.",
    "Fast, cheap and good.",                                  # adjectives, no articles: not objects
    "A report and a deck.",                                   # two is not a list
    "Describe what you need in a single sentence. That's the whole brief.",
])
def test_a_sentence_that_names_no_list_is_left_alone(text):
    assert nl.lists_in(text) == []


def _board(*narrations, shows=None):
    slides = [{"index": i + 1, "narration": n, "shot": "X"} for i, n in enumerate(narrations)]
    for i, sh in (shows or {}).items():
        slides[i - 1]["shot_fit"] = {"shows": sh}
    return {"meta": {"renderer": "remotion"}, "slides": slides}


def test_a_list_named_twice_must_agree():
    b = _board("A report. A spreadsheet. A deck.", "Then nothing.",
               "And it hands back a spreadsheet, a report, a dashboard.")
    w = nl.lint(b)
    assert any("beat 2" not in x and "beat 1" in x and "beat 3" in x and "deck" in x and "dashboard" in x for x in w), w


def test_the_same_list_named_twice_is_fine():
    b = _board("A report. A spreadsheet. A dashboard.", "And it hands back a spreadsheet, a report, a dashboard.",
               shows={1: {"report": ["report"], "spreadsheet": ["xlsx"], "dashboard": ["dashboard"]},
                      2: {"report": ["report"], "spreadsheet": ["xlsx"], "dashboard": ["dashboard"]}})
    assert nl.lint(b) == []


def test_a_named_list_with_no_word_on_how_it_is_shown_is_warned():
    w = nl.lint(_board("A report. A spreadsheet. A deck."))
    assert any("shot_fit.shows" in x and "report" in x for x in w), w


def test_shows_must_cover_every_item_and_take_known_forms():
    b = _board("A report. A spreadsheet. A deck.", shows={1: {"report": ["report"], "deck": {"by": "nothing"}}})
    w = nl.lint(b)
    assert any("spreadsheet" in x for x in w) and any("deck" in x and "by" in x for x in w), w


# ── the picture shows each item ──────────────────────────────────────────────────────────────────────────────────
def _film(tmp_path, narration, shows=None, frames=60):
    d = tmp_path / "film"
    d.mkdir()
    slide = {"index": 1, "narration": narration, "shot": "X", "duration": frames / 30}
    if shows:
        slide["shot_fit"] = {"shows": shows}
    (d / "storyboard.json").write_text(json.dumps({"meta": {"renderer": "remotion"}, "slides": [slide]}))
    (d / ".render_record.json").write_text(json.dumps({"mode": "segments", "out": "out.mp4", "gl": "angle",
                                                        "segments": [[0, frames - 1, "k"]]}))
    (d / "out.mp4").write_bytes(b"\0")
    return str(d)


def _fake_reads(monkeypatch, lines):
    """OCR stand-in: every sampled frame reads `lines` [(text, box 0..1)]."""
    monkeypatch.setattr(nq, "frame_png", lambda video, f, dest: dest)
    monkeypatch.setattr(nq, "video_size", lambda video: (1920, 1080))
    monkeypatch.setattr(nq, "read", lambda png: [{"text": t, "box": list(b)} for t, b in lines])


def test_three_blank_cards_do_not_show_a_report_a_spreadsheet_and_a_deck(tmp_path, monkeypatch):
    d = _film(tmp_path, "A report. A spreadsheet. A deck.")
    _fake_reads(monkeypatch, [])
    res = nq.judge(d)
    assert res["errors"] and all(w in res["errors"][0] for w in ("report", "spreadsheet", "deck"))


def test_named_items_found_on_the_picture_pass(tmp_path, monkeypatch):
    d = _film(tmp_path, "A spreadsheet, a report, a dashboard.",
              shows={"spreadsheet": ["xlsx", "spreadsheet"], "report": ["report"], "dashboard": ["dashboard"]})
    _fake_reads(monkeypatch, [("coffee-market-data.xlsx", (0.1, 0.5, 0.3, 0.53)),
                              ("Coffee Shop Market Report", (0.4, 0.2, 0.6, 0.24)),
                              ("Coffee Market Dashboard", (0.7, 0.2, 0.9, 0.24))])
    res = nq.judge(d)
    assert res["errors"] == [] and res["warnings"] == [], res


def test_a_name_only_in_the_caption_band_does_not_count(tmp_path, monkeypatch):
    # the caption says the word by construction: only the picture above it can show the object
    d = _film(tmp_path, "A report. A spreadsheet. A deck.")
    _fake_reads(monkeypatch, [("A report. A spreadsheet. A deck.", (0.2, 0.90, 0.8, 0.95))])
    assert nq.judge(d)["errors"]


def test_an_item_shown_by_picture_alone_is_left_to_the_critic(tmp_path, monkeypatch):
    d = _film(tmp_path, "A cat, a dog and a bird.",
              shows={"cat": {"by": "picture", "how": "a drawn cat"}, "dog": {"by": "picture", "how": "a drawn dog"},
                     "bird": {"by": "picture", "how": "a drawn bird"}})
    _fake_reads(monkeypatch, [])
    res = nq.judge(d)
    assert res["errors"] == [] and any("picture" in s for s in res["scope"])


def test_a_named_item_too_small_to_read_is_warned(tmp_path, monkeypatch):
    d = _film(tmp_path, "A spreadsheet, a report, a dashboard.")
    tiny = 8 / 1080                                                   # 8 px tall on a 1080 frame
    _fake_reads(monkeypatch, [("spreadsheet", (0.1, 0.3, 0.2, 0.3 + tiny)), ("report", (0.4, 0.3, 0.5, 0.3 + tiny)),
                              ("dashboard", (0.7, 0.3, 0.8, 0.3 + tiny))])
    res = nq.judge(d)
    assert res["errors"] == [] and res["warnings"] and "px" in res["warnings"][0]


def test_no_render_record_is_not_measured(tmp_path, monkeypatch):
    d = _film(tmp_path, "A report. A spreadsheet. A deck.")
    os.remove(os.path.join(d, ".render_record.json"))
    with pytest.raises(nq.NotMeasured):
        nq.judge(d)


def test_the_gate_is_in_the_fast_delivery_tier():
    import deliver_check as dc
    assert "named_objects_qa" in dc.gates_for({"renderer": "remotion"}, "fast")


# ── a real picture, read by the real OCR ─────────────────────────────────────────────────────────────────────────
import screen_text  # noqa: E402


@pytest.mark.skipif(screen_text.available() is None, reason="needs text recognition")
def test_a_real_frame_is_read(tmp_path):
    d = tmp_path / "film"
    (d / "frames").mkdir(parents=True)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 54)
    except OSError:
        font = ImageFont.load_default()
    for i in range(30):
        im = Image.new("RGB", (1920, 1080), (240, 240, 240))
        dr = ImageDraw.Draw(im)
        dr.text((200, 300), "Weekly Report", fill=(20, 20, 20), font=font)
        dr.text((800, 300), "sales.xlsx", fill=(20, 20, 20), font=font)        # no dashboard drawn
        dr.text((500, 960), "A report, a spreadsheet, a dashboard.", fill=(20, 20, 20), font=font)   # the caption
        im.save(d / "frames" / ("%03d.png" % i))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", str(d / "frames" / "%03d.png"),
                    "-pix_fmt", "yuv420p", str(d / "out.mp4")], check=True)
    slide = {"index": 1, "narration": "A report, a spreadsheet, a dashboard.", "shot": "X", "duration": 1.0,
             "shot_fit": {"shows": {"report": ["report"], "spreadsheet": ["xlsx"], "dashboard": ["dashboard"]}}}
    (d / "storyboard.json").write_text(json.dumps({"meta": {"renderer": "remotion"}, "slides": [slide]}))
    (d / ".render_record.json").write_text(json.dumps({"mode": "segments", "out": "out.mp4", "gl": "angle",
                                                        "segments": [[0, 29, "k"]]}))
    res = nq.judge(str(d))
    assert len(res["errors"]) == 1 and "dashboard" in res["errors"][0] and "report" not in res["errors"][0].split(":")[-1]


# ── validate carries both ────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("renderer", ["remotion", "local"])
def test_validate_warns_of_a_named_list_on_both_tiers(renderer):
    import validate as v
    slide = {"index": 1, "narration": "A report. A spreadsheet. A deck.", "duration": 5.0, "audio": "audio/01.mp3"}
    slide.update({"shot": "KnowledgeGraph", "shot_props": {}} if renderer == "remotion" else {"image": "frames/01.png"})
    r = v.evaluate({"meta": {"renderer": renderer}, "slides": [slide]}, "/tmp")
    assert any(w.startswith("named list") for w in r["warnings"]), r["warnings"]


# ── one device, one model ────────────────────────────────────────────────────────────────────────────────────────
def test_one_device_drawn_by_two_models_is_an_error(tmp_path):
    import blender_plate as bp
    board = {"meta": {"build_list": [
        {"id": "LaptopPlate", "kind": "shot", "fidelity": {"subject": "a MacBook Air 13 — macbook-air-13"}},
        {"id": "DevicePlate", "kind": "shot", "fidelity": {"subject": "the kit model of macbook-air-13"}}]},
        "slides": [{"index": 4, "shot": "LaptopPlate", "blender": {"id": "laptop", "scene": "blender/laptop.py"}},
                   {"index": 6, "shot": "DevicePlate", "blender": {"id": "plan-3d", "scene": "kit:laptop_screen"}}]}
    errs = bp.device_model_lints(board)
    assert errs and "macbook-air-13" in errs[0] and "blender/laptop.py" in errs[0] and "kit:laptop_screen" in errs[0]


def test_one_device_drawn_by_one_model_twice_is_fine():
    import blender_plate as bp
    board = {"meta": {"build_list": []},
             "slides": [{"index": 4, "shot": "DevicePlate", "blender": {"id": "a", "scene": "kit:laptop_screen"}},
                        {"index": 6, "shot": "DevicePlate", "blender": {"id": "b", "scene": "kit:laptop_screen"}}]}
    assert bp.device_model_lints(board) == []
