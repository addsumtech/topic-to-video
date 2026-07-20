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

def test_probe_js_measures_mystery_furniture_and_nearmiss():
    # DECODABILITY: empty bordered leaf boxes with no text/role -> `mystery` (data-role is the opt-out);
    # ORDER: sibling edges off by 5-22px -> `nearmiss`. Both advisory signals must be in the probe.
    for k in ("mystery:", "nearmiss:", "data-role", "borderTopWidth", "children.length===0"):
        assert k in kq._OVERFLOW_JS, k
    # near-miss band is 5..22px and applies to sibling pairs, not nested boxes
    assert "ds[di]>=5&&ds[di]<=22" in kq._OVERFLOW_JS


def test_probe_js_measures_intra_box_clip_excluding_fills():
    # the probe must emit a `clip` signal, key it off scroll-vs-client height, and EXCLUDE fill/bar
    # components (a .meter legitimately clips its .fill) so only real text-clipping cards flag
    assert "clip:" in kq._OVERFLOW_JS and "scrollHeight" in kq._OVERFLOW_JS and "clientHeight" in kq._OVERFLOW_JS
    for c in (".meter", ".fill", ".bar", ".track", ".gauge"):
        assert c in kq._OVERFLOW_JS

# ---- _geometry_issues: the pure box-geometry classifier (overflow / intra-box clip / caption zone) ----
_CLEAN = {"worst": 0, "clip": 0, "cbot": 800, "ctop": 100, "cleft": 100, "cright": 1800}

def test_geometry_clean_page_has_no_issues():
    assert kq._geometry_issues(_CLEAN, {}, 1080) == []

def test_geometry_flags_canvas_overflow():
    out = kq._geometry_issues({**_CLEAN, "worst": 40}, {}, 1080)
    assert len(out) == 1 and "overflows the safe canvas" in out[0]

def test_geometry_flags_intra_box_clip():
    # the case the canvas check MISSES: box fits (worst 0) but its own text is sliced
    out = kq._geometry_issues({**_CLEAN, "clip": 104}, {}, 1080)
    assert len(out) == 1 and "CLIPPED inside a card/box" in out[0]

def test_geometry_clip_ignores_sub_threshold_jitter():
    assert kq._geometry_issues({**_CLEAN, "clip": 6}, {}, 1080) == []

def test_geometry_flags_caption_zone_occlusion():
    # content bottom at 1000 > 0.86*1080 (=928) => overlaps the burned overlay subtitle
    out = kq._geometry_issues({**_CLEAN, "cbot": 1000}, {}, 1080)
    assert len(out) == 1 and "caption zone" in out[0]

def test_geometry_caption_zone_exempt_in_band_mode():
    # band mode moves captions BELOW the content, so low content is fine
    assert kq._geometry_issues({**_CLEAN, "cbot": 1000}, {"caption_mode": "band"}, 1080) == []

def test_geometry_caption_zone_exempt_when_captions_off():
    assert kq._geometry_issues({**_CLEAN, "cbot": 1000}, {"captions": False}, 1080) == []

def test_geometry_caption_zone_scales_with_canvas_height():
    # a 9:16 canvas (H=1920) zone boundary is 0.86*1920=1651 — content at 1600 clears it
    assert kq._geometry_issues({**_CLEAN, "cbot": 1600}, {}, 1920) == []
    assert len(kq._geometry_issues({**_CLEAN, "cbot": 1700}, {}, 1920)) == 1

def test_geometry_no_caption_flag_without_a_content_box():
    # a full-bleed hero (no .stage content box) has nothing to occlude even if cbot is spurious
    empty = {"worst": 0, "clip": 0, "cbot": 1000, "ctop": 1e9, "cleft": 1e9, "cright": 0}
    assert kq._geometry_issues(empty, {}, 1080) == []


# ---- shipped frame (the render's REAL last frame) ------------------------------------------------
# The ?p= sheet renders BLIND (no ?cues=), and in that mode seek.js sets total = max(delay +
# animation-duration), so p=1.0 means "every animation has finished" BY CONSTRUCTION. An animation
# the scene cut off mid-flight is not representable there. The shipped shot re-renders in CUE mode.

_BODY = ('<div data-cue-index="0" data-cue="open">A</div>'
         '<div data-cue-index="1" data-cue="payoff">B</div>')

def _cued_scene(tmp_path, body=_BODY, narration="we open here and then the payoff", duration=6.0, index=1):
    os.makedirs(str(tmp_path / "pages"), exist_ok=True)
    (tmp_path / "pages" / "s.html").write_text(body)
    return {"index": index, "type": "html", "props": {"html": "pages/s.html"},
            "narration": narration, "duration": duration}

def test_shipped_url_carries_real_cues_and_duration(tmp_path):
    s = _cued_scene(tmp_path)
    u = kq._shipped_url(str(tmp_path), s, "file:///p.html")
    assert u.startswith("file:///p.html?p=1.0&cues=")
    assert "&dur=6.000" in u
    assert len(u.split("cues=")[1].split("&")[0].split(",")) == 2

def test_shipped_url_prefers_edge_word_timings(tmp_path):
    import json
    s = _cued_scene(tmp_path)
    os.makedirs(str(tmp_path / "audio"), exist_ok=True)
    json.dump([{"w": "open", "t": 0.5}, {"w": "payoff", "t": 4.25}],
              open(str(tmp_path / "audio" / "01.words.json"), "w"))
    u = kq._shipped_url(str(tmp_path), s, "file:///p.html")
    assert "cues=0.500,4.250" in u

def test_shipped_url_clamps_a_cue_to_the_render_margin(tmp_path):
    # render_html clamps every cue to dur-0.5 so it fires before the final frame; mirror it exactly
    import json
    s = _cued_scene(tmp_path)
    os.makedirs(str(tmp_path / "audio"), exist_ok=True)
    json.dump([{"w": "open", "t": 0.5}, {"w": "payoff", "t": 5.9}],
              open(str(tmp_path / "audio" / "01.words.json"), "w"))
    u = kq._shipped_url(str(tmp_path), s, "file:///p.html")
    assert "cues=0.500,5.500" in u

def test_shipped_url_none_when_scene_is_not_cued(tmp_path):
    s = _cued_scene(tmp_path, "<div>no cues here</div>")
    assert kq._shipped_url(str(tmp_path), s, "file:///p.html") is None

def test_shipped_url_none_before_tts(tmp_path):
    s = _cued_scene(tmp_path, _BODY, duration=None)
    assert kq._shipped_url(str(tmp_path), s, "file:///p.html") is None

def test_shipped_url_none_when_page_missing(tmp_path):
    s = {"index": 1, "type": "html", "props": {"html": "pages/gone.html"},
         "narration": "we open here and then the payoff", "duration": 6.0}
    assert kq._shipped_url(str(tmp_path), s, "file:///p.html") is None
