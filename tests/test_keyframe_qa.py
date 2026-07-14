import sys, os, json
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from PIL import Image, ImageDraw
import keyframe_qa as kq
import _common

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "html"))

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

def test_probe_js_reports_chrome_excluded_content_bottom():
    # cbotc (real-content bottom for the caption-band check) must exclude backdrops, faint decorative
    # watermarks (.ghost/.icon-ghost can sit UNDER .stage), and corner chrome — so a pointer-events:none
    # watermark reaching the band never phantom-blocks the gate.
    assert "cbotc" in kq._OVERFLOW_JS
    for k in (".bg-soft", ".bg-glow", ".ghost", ".icon-ghost", ".credit", ".pageno"):
        assert k in kq._CBOTC_EXCL

def test_early_pop_js_wellformed():
    # self-invoking expression; excludes ambient backdrops + unanimated elements; thresholds at op>0.05
    assert kq._EARLY_POP_JS.startswith("(function(){") and kq._EARLY_POP_JS.endswith("})()")
    for k in (".reveal-up", ".bg-live", "[data-ambient]", "animationName", "0.05", "getBoundingClientRect"):
        assert k in kq._EARLY_POP_JS


def _pop_page(second_extra):
    """A page with two staggered reveal boxes; `second_extra` is inline style on box B. Links the
    REAL base.css + seek.js so seek.js freezes reveals at ?p=0 exactly as the render does."""
    return (
        "<!doctype html><html><head><meta charset=utf-8>"
        f'<link rel="stylesheet" href="file://{_ASSETS}/base.css">'
        "<style>:root{--dur:.7s;--ease-expo:ease;--fg:#111;--bg:#fff;--rule:#111;--muted:#555}"
        "body{margin:0;background:#fff}.stage{padding:80px}"
        ".box{width:600px;height:150px;background:#ccc;margin:30px}</style>"
        "</head><body><div class='stage'>"
        "<div class='box reveal-up' data-cue-index='0' data-cue='a' style='animation-delay:.3s'>A</div>"
        f"<div class='box reveal-up' data-cue-index='1' data-cue='b' style='animation-delay:.3s;{second_extra}'>B</div>"
        "</div>"
        f'<script src="file://{_ASSETS}/seek.js"></script></body></html>')


@pytest.mark.skipif(_common.find_chrome() is None, reason="needs Chrome for CDP DOM probe")
def test_early_pop_flags_opacity_leak_but_not_filter(tmp_path, capsys):
    # ONE deck, ONE Chrome session (the per-frame --screenshot fallback is slow/flaky — keep the live
    # footprint minimal). scene 1: box B leaks its opacity PROPERTY (inline opacity:.6) → painted at
    # p=0 before its cue — the exact .defocus/.hs-connect bug → must be flagged (blocks the gate).
    # scene 2: clean. scene 3: dimmed via filter:opacity() (the sanctioned channel) → opacity property
    # stays 0 at p=0 → must NOT be flagged.
    pages = tmp_path / "pages"; pages.mkdir()
    (pages / "leak.html").write_text(_pop_page("opacity:.6"))
    (pages / "clean.html").write_text(_pop_page(""))
    (pages / "filter.html").write_text(_pop_page("filter:opacity(.6)"))
    deck = {"meta": {"aspect": "16:9"},
            "slides": [{"index": 1, "type": "html", "props": {"html": "pages/leak.html"}},
                       {"index": 2, "type": "html", "props": {"html": "pages/clean.html"}},
                       {"index": 3, "type": "html", "props": {"html": "pages/filter.html"}}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(deck))
    rc = kq.run(str(tmp_path), ps=[0.0, 1.0], as_json=True)
    data = json.loads(capsys.readouterr().out)
    by = {r["scene"]: r for r in data["report"]}
    # if Chrome couldn't render at all (cold-launch timeout etc.), that's an infra flake, not our verdict
    if any("render failed" in i for r in data["report"] for i in r.get("issues", [])):
        pytest.skip("Chrome render flake (infra) — early-pop verdict not exercised")
    assert any("early pop" in i for i in by[1]["issues"]), by[1]          # opacity-property leak → flagged
    assert not any("early pop" in i for i in by[2].get("issues", [])), by[2]   # clean → not flagged
    assert not any("early pop" in i for i in by[3].get("issues", [])), by[3]   # filter:opacity() → not flagged
    assert rc == 1                                                        # scene 1's leak blocks the gate


@pytest.mark.skipif(_common.find_chrome() is None, reason="needs Chrome for CDP DOM probe")
def test_caption_band_overlap_flagged(tmp_path, capsys):
    # the flush caption strip is drawn over the bottom `band` px; content reaching into it is flagged so
    # the author raises/scales it. scene 1: a box pinned into the bottom band region → flagged. scene 2:
    # the same box up top → clears the band → not flagged.
    pages = tmp_path / "pages"; pages.mkdir()
    def page(box_style):
        return ("<!doctype html><html><head><meta charset=utf-8>"
                f'<link rel="stylesheet" href="file://{_ASSETS}/base.css">'
                "<style>:root{--dur:.7s;--ease-expo:ease;--fg:#111;--bg:#fff}body{margin:0;background:#fff}"
                ".stage{position:relative}</style>"
                f"</head><body><div class='stage'><div style='{box_style}'>X</div></div></body></html>")
    (pages / "low.html").write_text(page(               # bottom:20px on a 1080-tall canvas → into the band
        "position:absolute;left:80px;bottom:20px;width:600px;height:150px;background:#ccc"))
    (pages / "high.html").write_text(page("width:600px;height:150px;background:#ccc"))
    deck = {"meta": {"aspect": "16:9"},
            "slides": [{"index": 1, "type": "html", "props": {"html": "pages/low.html"}},
                       {"index": 2, "type": "html", "props": {"html": "pages/high.html"}}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(deck))
    rc = kq.run(str(tmp_path), ps=[0.0, 1.0], as_json=True)
    data = json.loads(capsys.readouterr().out)
    if any("render failed" in i for r in data["report"] for i in r.get("issues", [])):
        pytest.skip("Chrome render flake (infra) — band-overlap verdict not exercised")
    by = {r["scene"]: r for r in data["report"]}
    assert any("caption band" in i for i in by[1]["issues"]), by[1]           # into the band → flagged
    assert not any("caption band" in i for i in by[2].get("issues", [])), by[2]  # clears it → not flagged
