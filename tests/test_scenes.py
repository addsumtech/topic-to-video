import os
from PIL import Image
import scenes

META = {"fps": 30, "language": "en"}
META_ZH = {"fps": 30, "language": "zh"}

def _pix(p):  # pixel bytes (metadata-independent determinism check)
    return Image.open(p).convert("RGB").tobytes()

def test_ease_clamped_monotonic():
    assert scenes._ease(-1) == 0.0 and scenes._ease(2) == 1.0
    assert scenes._ease(0.0) == 0.0 and scenes._ease(1.0) == 1.0
    assert scenes._ease(0.25) < scenes._ease(0.75)

def test_title_writes_exact_frames_and_nonblank(tmp_path):
    pat = scenes.render_title({"title": "Hello World", "subtitle": "A test"},
                              META, 1920, 1080, 12, str(tmp_path), 3)
    files = sorted(f for f in os.listdir(tmp_path) if f.endswith(".png"))
    assert len(files) == 12
    assert files[0] == "scene_03_0000.png"            # index-namespaced
    last = Image.open(pat % 11).convert("RGB")
    assert last.size == (1920, 1080)
    assert last.getextrema() != ((0,0),(0,0),(0,0))   # not all-black: text drawn
    assert "%04d" in pat

def test_title_deterministic(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    pa = scenes.render_title({"title": "Repeat"}, META, 640, 360, 6, str(a), 1)
    pb = scenes.render_title({"title": "Repeat"}, META, 640, 360, 6, str(b), 1)
    assert all(_pix(pa % i) == _pix(pb % i) for i in range(6))

def test_title_cjk_renders_glyphs(tmp_path):
    pat = scenes.render_title({"title": "进入商业航天发射市场"}, META_ZH, 1280, 720, 4, str(tmp_path), 1)
    last = Image.open(pat % 3).convert("RGB")
    assert last.getextrema() != ((0,0),(0,0),(0,0))   # CJK glyphs drawn (no blank/tofu-only)

def test_title_single_frame_is_settled_nonblank(tmp_path):
    pat = scenes.render_title({"title": "Still"}, META, 640, 360, 1, str(tmp_path), 5)
    from PIL import Image
    assert Image.open(pat % 0).convert("RGB").getextrema() != ((0,0),(0,0),(0,0))

def test_hex_rgb_shorthand():
    assert scenes._hex_rgb("#F0F") == (255, 0, 255)
    assert scenes._hex_rgb("#E8590C") == (232, 89, 12)

def test_chart_values_never_overshoot_and_settle():
    vals = [61, 165, 90]
    assert scenes._chart_values(vals, 0.0) == [0, 0, 0]
    mid = scenes._chart_values(vals, 0.5)
    assert all(0 <= m <= v for m, v in zip(mid, vals))     # never past target
    assert scenes._chart_values(vals, 1.0) == [61, 165, 90]  # settles exactly on data

def test_chart_writes_frames_and_final_nonblank(tmp_path):
    props = {"kind": "bars", "title": "Launches", "unit": "x",
             "data": [{"label": "2022", "value": 61}, {"label": "2025", "value": 165}]}
    pat = scenes.render_chart(props, META, 1280, 720, 10, str(tmp_path), 4)
    from PIL import Image
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".png")]) == 10
    assert Image.open(pat % 9).convert("RGB").getextrema() != ((0,0),(0,0),(0,0))

def test_chart_deterministic(tmp_path):
    props = {"kind": "bars", "data": [{"label": "a", "value": 3}, {"label": "b", "value": 7}]}
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    pa = scenes.render_chart(props, META, 640, 360, 5, str(a), 1)
    pb = scenes.render_chart(props, META, 640, 360, 5, str(b), 1)
    assert all(_pix(pa % i) == _pix(pb % i) for i in range(5))

def test_visible_count_grows_with_progress():
    assert scenes._visible_count(4, 0.0) >= 0
    assert scenes._visible_count(4, 1.0) == 4
    assert scenes._visible_count(4, 0.5) <= 4
    assert scenes._visible_count(4, 0.0) <= scenes._visible_count(4, 0.6) <= scenes._visible_count(4, 1.0)

def test_timeline_writes_frames_and_final_nonblank(tmp_path):
    props = {"title": "Milestones", "events": [
        {"date": "2026-01", "label": "Kickoff"}, {"date": "2026-06", "label": "MVP"},
        {"date": "2026-12", "label": "Ship"}]}
    pat = scenes.render_timeline(props, META, 1280, 720, 9, str(tmp_path), 7)
    from PIL import Image
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".png")]) == 9
    assert Image.open(pat % 8).convert("RGB").getextrema() != ((0,0),(0,0),(0,0))

def test_keypoints_writes_exact_frames_and_nonblank(tmp_path):
    props = {"title": "市场可争夺的部分",
             "points": [{"label": "对外发射 ≈ 42 次", "sub": "可被争夺"},
                        {"label": "且多为政府 / 国安订单"}], "accent": "#4C9BE8"}
    pat = scenes.render_keypoints(props, META_ZH, 1280, 720, 12, str(tmp_path), 4)
    files = sorted(f for f in os.listdir(tmp_path) if f.endswith(".png"))
    assert len(files) == 12 and files[0] == "scene_04_0000.png"
    last = Image.open(pat % 11).convert("RGB")
    assert last.size == (1280, 720)
    assert last.getextrema() != ((0, 0), (0, 0), (0, 0))   # text drawn
    assert "%04d" in pat

def test_keypoints_deterministic(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    props = {"points": [{"label": "One"}, {"label": "Two"}, {"label": "Three"}]}
    pa = scenes.render_keypoints(props, META, 640, 360, 6, str(a), 1)
    pb = scenes.render_keypoints(props, META, 640, 360, 6, str(b), 1)
    assert all(_pix(pa % i) == _pix(pb % i) for i in range(6))

def test_keypoints_single_point_and_single_frame(tmp_path):
    pat = scenes.render_keypoints({"points": [{"label": "Solo"}]}, META, 640, 360, 1, str(tmp_path), 2)
    last = Image.open(pat % 0).convert("RGB")
    assert last.getextrema() != ((0, 0), (0, 0), (0, 0))    # settled, non-blank
