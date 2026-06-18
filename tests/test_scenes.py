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
