import os
import pytest
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

def test_keypoints_cjk_labels_use_cjk_font_not_tofu(tmp_path):
    # Regression: point labels/subs must resolve their font from the ACTUAL (CJK) label text,
    # not a Latin stand-in — else CJK labels render as tofu boxes. Force the bundled Latin font
    # (which tofus CJK) and assert the normal zh render differs (it drew real glyphs).
    import render
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    props = {"points": [{"label": "政府客户", "sub": "军方"}]}
    pat_ok = scenes.render_keypoints(props, META_ZH, 640, 360, 1, str(a), 1)
    meta_latin = dict(META_ZH); meta_latin["font"] = render.BUNDLED_FONT
    pat_tofu = scenes.render_keypoints(props, meta_latin, 640, 360, 1, str(b), 1)
    assert _pix(pat_ok % 0) != _pix(pat_tofu % 0)          # CJK glyphs != tofu boxes

def test_compare_split_writes_frames_and_nonblank(tmp_path):
    props = {"title": "2025 年的 165 次发射", "kind": "split", "total": 165,
             "parts": [{"label": "自用 Starlink", "value": 123, "note": "不可争夺"},
                       {"label": "对外（可争夺）", "value": 42}], "accent": "#E8590C"}
    pat = scenes.render_compare(props, META_ZH, 1280, 720, 10, str(tmp_path), 6)
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".png")]) == 10
    last = Image.open(pat % 9).convert("RGB")
    assert last.size == (1280, 720)
    assert last.getextrema() != ((0, 0), (0, 0), (0, 0))

def test_compare_versus_writes_frames(tmp_path):
    props = {"kind": "versus", "parts": [{"label": "A", "value": 10}, {"label": "B", "value": 25}]}
    pat = scenes.render_compare(props, META, 1280, 720, 8, str(tmp_path), 2)
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".png")]) == 8
    assert Image.open(pat % 7).convert("RGB").getextrema() != ((0, 0), (0, 0), (0, 0))

def test_compare_deterministic(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    props = {"kind": "split", "parts": [{"label": "X", "value": 3}, {"label": "Y", "value": 7}]}
    pa = scenes.render_compare(props, META, 640, 360, 5, str(a), 1)
    pb = scenes.render_compare(props, META, 640, 360, 5, str(b), 1)
    assert all(_pix(pa % i) == _pix(pb % i) for i in range(5))

def test_chrome_bin_honors_meta_path(tmp_path):
    fake = tmp_path / "chrome"; fake.write_text("x")
    assert scenes._chrome_bin({"chrome_path": str(fake)}) == str(fake)

def test_chrome_bin_none_when_absent(monkeypatch):
    monkeypatch.setattr(scenes, "_CHROME_CANDIDATES", [])
    monkeypatch.setattr(scenes.shutil, "which", lambda n: None)
    assert scenes._chrome_bin({}) is None

def test_chrome_shot_builds_command(tmp_path, monkeypatch):
    fake = tmp_path / "chrome"; fake.write_text("x")
    cap = {}
    def fake_run(cmd, **kw):
        cap["cmd"] = cmd; cap["kw"] = kw
    monkeypatch.setattr(scenes.subprocess, "run", fake_run)
    scenes._chrome_shot("file:///p.html?p=0.5", str(tmp_path / "o.png"), 1920, 1080,
                        {"chrome_path": str(fake)})
    cmd = cap["cmd"]
    assert cmd[0] == str(fake)
    assert "--headless" in cmd and "--window-size=1920,1080" in cmd
    assert f"--screenshot={tmp_path / 'o.png'}" in cmd
    assert cmd[-1] == "file:///p.html?p=0.5"
    assert cap["kw"].get("check") is True and cap["kw"].get("timeout") == 60

def test_chrome_shot_no_chrome_raises(monkeypatch):
    monkeypatch.setattr(scenes, "_chrome_bin", lambda meta: None)
    with pytest.raises(RuntimeError):
        scenes._chrome_shot("file:///p.html", "/tmp/o.png", 1920, 1080, {})

def _tiny_png(path):
    Image.new("RGB", (4, 4), (10, 20, 30)).save(path)

def test_render_html_frames_launch_count_and_p_ramp(tmp_path, monkeypatch):
    out_dir = tmp_path / "proj"; (out_dir / "pages").mkdir(parents=True)
    (out_dir / "pages" / "scene_03.html").write_text("<html></html>")
    calls = []
    def fake_shot(url, out_png, W, H, meta):
        calls.append(url); _tiny_png(out_png)
    monkeypatch.setattr(scenes, "_chrome_shot", fake_shot)
    meta = {"_out": str(out_dir), "fps": 30}
    pat = scenes.render_html({"html": "pages/scene_03.html", "anim_seconds": 0.2},
                             meta, 1920, 1080, 12, str(tmp_path), 3)
    files = sorted(f for f in os.listdir(tmp_path) if f.endswith(".png"))
    assert len(files) == 12 and files[0] == "scene_03_0000.png" and "%04d" in pat
    # anim 0.2s * 30fps = 6 reveal frames -> 6 Chrome launches; the other 6 frames are copies
    assert len(calls) == 6
    assert [c.split("?p=")[1] for c in calls] == ["0.0000","0.2000","0.4000","0.6000","0.8000","1.0000"]
    assert calls[0].startswith("file://") and "scene_03.html" in calls[0]

def test_render_html_single_frame_holds(tmp_path, monkeypatch):
    out_dir = tmp_path / "proj"; (out_dir / "pages").mkdir(parents=True)
    (out_dir / "pages" / "s.html").write_text("<html></html>")
    calls = []
    monkeypatch.setattr(scenes, "_chrome_shot",
                        lambda url, out_png, W, H, meta: (calls.append(url), _tiny_png(out_png)))
    pat = scenes.render_html({"html": "pages/s.html"}, {"_out": str(out_dir), "fps": 30},
                             640, 360, 1, str(tmp_path), 1)
    assert os.path.exists(pat % 0) and len(calls) == 1 and calls[0].endswith("?p=1.0000")

def _chrome_present():
    return scenes._chrome_bin({}) is not None

def test_design_system_is_themeable():
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = open(os.path.join(skill, "assets", "html", "base.css")).read()
    motifs = open(os.path.join(skill, "assets", "html", "motifs.css")).read()
    # canonical semantic vars + back-compat aliases present in base.css :root
    for v in ("--bg", "--surface", "--fg", "--muted", "--accent", "--accent2", "--rule", "--scrim"):
        assert v in base, f"missing {v}"
    assert "--blue:var(--accent)" in base.replace(" ", "") or "--blue: var(--accent)" in base
    assert "--orange:var(--accent2)" in base.replace(" ", "") or "--orange: var(--accent2)" in base
    # motion + illustrated-page helpers live in motifs.css
    assert ".kenburns" in motifs and ".split" in motifs
    # the photo scrim now derives from the theme bg (no hardcoded #0d1117 in motifs scrim)
    assert "#0d1117" not in motifs

@pytest.mark.skipif(not _chrome_present(), reason="no Chrome")
def test_light_theme_renders_light(tmp_path):
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    theme_css = tmp_path / "theme.css"
    theme_css.write_text(":root{--bg:#f5f0e6;--surface:#fffdf8;--fg:#201a14;--muted:#6b5e4f;"
                         "--accent:#c0461f;--accent2:#2f7d4f;--rule:var(--accent2);--scrim:#f5f0e6;}")
    page = tmp_path / "p.html"
    page.write_text('<!doctype html><html><head><meta charset="utf-8">'
                    f'<link rel="stylesheet" href="file://{base}">'
                    f'<link rel="stylesheet" href="file://{theme_css}"></head>'
                    '<body><div class="stage"><h1 class="title">Hello</h1></div></body></html>')
    out = tmp_path / "o.png"
    scenes._chrome_shot(f"file://{page}", str(out), 480, 270, {})
    from PIL import Image
    px = Image.open(out).convert("RGB").getpixel((10, 10))
    assert sum(px) / 3 > 180, f"expected light bg, got {px}"   # theme.css overrode the dark default

@pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")
def test_base_css_page_renders_and_reveals(tmp_path):
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))   # skill root
    css = os.path.join(skill, "assets", "html", "base.css")
    js = os.path.join(skill, "assets", "html", "seek.js")
    assert os.path.exists(css) and os.path.exists(js)
    page = tmp_path / "p.html"
    page.write_text(
        '<!doctype html><html><head><meta charset="utf-8">'
        f'<link rel="stylesheet" href="file://{css}"></head>'
        '<body><div class="stage"><h1 class="title reveal-up">测试 42</h1></div>'
        f'<script src="file://{js}"></script></body></html>')
    a = tmp_path / "a.png"; b = tmp_path / "b.png"
    scenes._chrome_shot(f"file://{page}?p=0", str(a), 960, 540, {})
    scenes._chrome_shot(f"file://{page}?p=1", str(b), 960, 540, {})
    ia = Image.open(a).convert("RGB"); ib = Image.open(b).convert("RGB")
    assert ib.getextrema() != ((0, 0), (0, 0), (0, 0))     # settled page is non-blank
    assert ia.tobytes() != ib.tobytes()                    # reveal animated (hidden at p=0)

def test_motifs_css_exists():
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    assert os.path.exists(os.path.join(skill, "assets", "html", "motifs.css"))

@pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")
def test_motif_page_renders_nonblank(tmp_path):
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    motifs = os.path.join(skill, "assets", "html", "motifs.css")
    js = os.path.join(skill, "assets", "html", "seek.js")
    page = tmp_path / "m.html"
    page.write_text(
        '<!doctype html><html><head><meta charset="utf-8">'
        f'<link rel="stylesheet" href="file://{base}">'
        f'<link rel="stylesheet" href="file://{motifs}"></head>'
        '<body><div class="bg-stars"></div><div class="ghost">165</div>'
        '<div class="bg-glow blue" style="width:400px;height:400px;top:-80px;right:-80px"></div>'
        '<div class="stage"><h1 class="title reveal-up">测试 <span class="grad-text">42</span></h1></div>'
        f'<script src="file://{js}"></script></body></html>')
    out = tmp_path / "o.png"
    scenes._chrome_shot(f"file://{page}?p=1", str(out), 960, 540, {})
    assert Image.open(out).convert("RGB").getextrema() != ((0, 0), (0, 0), (0, 0))   # motifs render


@pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")
def test_kenburns_split_page_motion_captured(tmp_path):
    """Spec: a .split page with a .kenburns <img> must DIFFER at ?p=0 vs ?p=1 (the Ken-Burns
    transform progresses and seek.js freezes it per frame). Proves the illustrated-page motion path."""
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    motifs = os.path.join(skill, "assets", "html", "motifs.css")
    js = os.path.join(skill, "assets", "html", "seek.js")
    # a non-uniform local image so a scale/translate transform changes the captured pixels
    img = tmp_path / "pic.png"
    pic = Image.new("RGB", (200, 200), (20, 60, 140))
    for x in range(200):
        for y in range(200):
            pic.putpixel((x, y), ((x * 5) % 256, (y * 7) % 256, 90))
    pic.save(img)
    page = tmp_path / "split.html"
    page.write_text(
        '<!doctype html><html><head><meta charset="utf-8">'
        f'<link rel="stylesheet" href="file://{base}">'
        f'<link rel="stylesheet" href="file://{motifs}"></head>'
        '<body><div class="split"><div><h1 class="title">Point</h1></div>'
        f'<div class="media"><img class="kenburns" src="file://{img}" alt=""></div></div>'
        f'<script src="file://{js}"></script></body></html>')
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    # full 1920x1080 capture — the .split media panel (and its kenburns img) is in the RIGHT half
    scenes._chrome_shot(f"file://{page}?p=0", str(a), 1920, 1080, {})
    scenes._chrome_shot(f"file://{page}?p=1", str(b), 1920, 1080, {})
    assert Image.open(a).convert("RGB").tobytes() != Image.open(b).convert("RGB").tobytes()  # Ken-Burns moved
