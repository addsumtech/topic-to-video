import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from PIL import Image, ImageDraw
import keyframe_qa as kq

def test_is_blank_uniform_true():
    assert kq._is_blank(Image.new("RGB", (200, 120), "#f5f3ee")) is True

def test_is_blank_with_content_false():
    im = Image.new("RGB", (200, 120), "#f5f3ee")
    ImageDraw.Draw(im).text((20, 40), "Content here", fill="#101010")
    assert kq._is_blank(im) is False

def test_sheet_montages_all_frames(tmp_path):
    imgs = [Image.new("RGB", (192, 108), c) for c in ("#111", "#222", "#333")]
    out = str(tmp_path / "sheet.png")
    kq._sheet(imgs, out, cols=3, tw=100, th=56)
    assert os.path.exists(out) and Image.open(out).size == (300, 56)

def test_probe_js_is_wellformed():
    # a single self-invoking expression returning JSON with all three signals
    assert kq._OVERFLOW_JS.startswith("(function(){") and kq._OVERFLOW_JS.endswith("})()")
    for k in ("getBoundingClientRect", "textlen", "worst", "centered", "getComputedStyle", "closest"):
        assert k in kq._OVERFLOW_JS

def test_center_exclude_covers_display_and_diagram_classes():
    for c in (".title", ".pullquote", ".kicker", ".stat", ".flow", ".hubspoke",
              ".timeline", ".quadrant", ".scorecard", ".tile", ".block"):
        assert c in kq._CENTER_EXCL

def test_probe_js_reports_fill_bbox_and_bleed():
    # the 9:16 fill-exemption 'bleed' flag must cover BOTH full-bleed backdrops (.bg-photo AND .bg-soft)
    for k in ("ctop", "cbot", "bleed", ".bg-photo", ".bg-soft"):
        assert k in kq._OVERFLOW_JS
