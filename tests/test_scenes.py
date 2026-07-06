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

def test_keypoints_reveals_spread_across_scene_not_crammed(tmp_path):
    """Generality: points must reveal across the scene (track the voice), not cram into the first ~1s
    then hold — same as render_timeline/chart. At ~25% through a long scene the later points should
    not be on screen yet, so an early frame carries clearly less ink than the final frame."""
    def ink(png):
        im = Image.open(png).convert("RGB"); bg = (13, 17, 23)
        return sum(1 for px in im.getdata() if px != bg)
    props = {"title": "T", "points": [{"label": "Alpha"}, {"label": "Bravo"}, {"label": "Charlie"}]}
    pat = scenes.render_keypoints(props, META, 960, 540, 300, str(tmp_path), 1)
    early = ink(pat % 75)      # ~25% in — with spread, only the first point is appearing
    late = ink(pat % 299)      # end — all three points present
    assert early < 0.6 * late, f"keypoints not spread (early={early} vs late={late}); reveals look crammed"

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
    import _common
    monkeypatch.setattr(_common, "CHROME_CANDIDATES", [])
    monkeypatch.setattr(_common.shutil, "which", lambda n: None)
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
    assert "--user-data-dir" not in " ".join(cmd)   # explicit profile hangs vs a running Chrome
    assert cap["kw"].get("check") is True and cap["kw"].get("timeout") == 90

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
    meta = {"_out": str(out_dir), "fps": 30, "capture": "screenshot"}
    pat = scenes.render_html({"html": "pages/scene_03.html", "anim_seconds": 0.2},
                             meta, 1920, 1080, 12, str(tmp_path), 3)
    files = sorted(f for f in os.listdir(tmp_path) if f.endswith(".png"))
    assert len(files) == 12 and files[0] == "scene_03_0000.png" and "%04d" in pat
    # anim 0.2s * 30fps = 6 reveal frames -> 6 Chrome launches; the other 6 frames are copies.
    # Shots run in a thread pool, so completion order is nondeterministic — compare the SET of p's.
    assert len(calls) == 6
    assert sorted(c.split("?p=")[1] for c in calls) == ["0.0000","0.2000","0.4000","0.6000","0.8000","1.0000"]
    assert all(c.startswith("file://") and "scene_03.html" in c for c in calls)

def test_render_html_cued_path_captures_header_window(tmp_path, monkeypatch):
    """Regression: on a cued page the non-cued header chrome animates on time-based reveals, not
    cues. The cued capture path must shoot fresh frames across the initial HEAD_WINDOW — otherwise
    only p=0 (everything hidden) is captured and copied until the first cue, leaving the page blank."""
    import json
    out_dir = tmp_path / "proj"; (out_dir / "pages").mkdir(parents=True)
    (out_dir / "audio").mkdir(parents=True)
    # a cued page: a time-based header + one cued point whose anchor fires late (t=1.5s)
    (out_dir / "pages" / "scene_04.html").write_text(
        '<div class="title reveal-up">Header</div>'
        '<div class="row reveal-up" data-cue-index="0" data-cue="alpha">A</div>')
    json.dump([{"w": "alpha", "t": 1.5}], open(out_dir / "audio" / "04.words.json", "w"))
    calls = []
    monkeypatch.setattr(scenes, "_chrome_shot",
                        lambda url, out_png, W, H, meta: (calls.append(url), _tiny_png(out_png)))
    meta = {"_out": str(out_dir), "fps": 30, "capture": "screenshot"}
    # 60 frames @30fps -> dur=2.0s; cue at 1.5s. HEAD_WINDOW=1.2 -> t<=1.2 must be fresh shots.
    scenes.render_html({"html": "pages/scene_04.html"}, meta, 1920, 1080, 60, str(tmp_path), 4)
    assert calls, "cued path produced no Chrome shots"
    assert all("&cues=" in c for c in calls), "expected the cued render path (cues in URL)"
    # an early header-window frame (t=0.5s -> p=0.25) must be a FRESH shot, not a copy of p=0
    assert any("?p=0.2500" in c for c in calls), "header-entrance window was not captured (the bug)"
    # the window must cover the FULL header cadence: sub ends ~.95s (delay .25 + .7s reveal), so a
    # fresh shot near t=0.9s (p=0.45 @ dur=2.0) must exist — a too-small HEAD_WINDOW would miss it
    assert any("?p=0.4500" in c for c in calls), "HEAD_WINDOW too small to cover the header end (~.95s)"
    # and the late cue burst is still captured
    assert any("?p=0.7500" in c for c in calls), "cue burst near t=1.5s was not captured"

def test_render_html_single_frame_holds(tmp_path, monkeypatch):
    out_dir = tmp_path / "proj"; (out_dir / "pages").mkdir(parents=True)
    (out_dir / "pages" / "s.html").write_text("<html></html>")
    calls = []
    monkeypatch.setattr(scenes, "_chrome_shot",
                        lambda url, out_png, W, H, meta: (calls.append(url), _tiny_png(out_png)))
    pat = scenes.render_html({"html": "pages/s.html"}, {"_out": str(out_dir), "fps": 30, "capture": "screenshot"},
                             640, 360, 1, str(tmp_path), 1)
    assert os.path.exists(pat % 0) and len(calls) == 1 and calls[0].endswith("?p=1.0000")

def test_render_html_builds_absolute_file_url(tmp_path, monkeypatch):
    # Regression: a relative out_dir (e.g. render run with out_dir=".") must still yield an ABSOLUTE
    # file:// URL — CDP Page.navigate rejects "file://./pages/x.html" (ERR_INVALID_URL) and silently
    # renders a Chrome error page. abspath in render_html is the fix.
    (tmp_path / "proj" / "pages").mkdir(parents=True)
    (tmp_path / "proj" / "pages" / "s.html").write_text("<html></html>")
    monkeypatch.chdir(tmp_path / "proj")
    calls = []
    monkeypatch.setattr(scenes, "_chrome_shot",
                        lambda url, o, W, H, m: (calls.append(url), _tiny_png(o)))
    scenes.render_html({"html": "pages/s.html", "anim_seconds": 0.1},
                       {"_out": ".", "fps": 30, "capture": "screenshot"}, 640, 360, 3, str(tmp_path), 1)
    assert calls and all(c.startswith("file:///") for c in calls), calls[:1]
    assert all("file://." not in c and "/./" not in c for c in calls)


def test_capture_falls_back_to_screenshot_when_cdp_unavailable(tmp_path, monkeypatch):
    # If CDP can't run, render_html must transparently fall back to the --screenshot path.
    import _cdp
    out_dir = tmp_path / "proj"; (out_dir / "pages").mkdir(parents=True)
    (out_dir / "pages" / "s.html").write_text("<html></html>")
    monkeypatch.setattr(_cdp, "capture",
                        lambda *a, **k: (_ for _ in ()).throw(_cdp.CDPUnavailable("forced")))
    calls = []
    monkeypatch.setattr(scenes, "_chrome_shot",
                        lambda url, o, W, H, m: (calls.append(url), _tiny_png(o)))
    # NB: capture flag left at default ("cdp") so the CDP path is attempted, then fails over
    pat = scenes.render_html({"html": "pages/s.html", "anim_seconds": 0.1},
                             {"_out": str(out_dir), "fps": 30}, 640, 360, 6, str(tmp_path), 1)
    assert pat.endswith(".png") and calls, "fallback to --screenshot did not engage"


def _chrome_present():
    return scenes._chrome_bin({}) is not None


@pytest.mark.skipif(not _chrome_present(), reason="no Chrome for CDP integration test")
def test_cdp_capture_produces_real_jpeg_frames(tmp_path):
    # End-to-end: persistent-Chrome CDP path captures real (non-blank) JPEG frames + copies hold.
    import _cdp
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    css = os.path.join(skill, "assets", "html", "base.css")
    page = tmp_path / "p.html"
    page.write_text('<!doctype html><html><head><meta charset="utf-8">'
                    f'<link rel="stylesheet" href="file://{css}"></head>'
                    '<body><div class="stage"><h1 class="title">CDP 42</h1></div></body></html>')
    url = f"file://{page}?p=1"
    shots = [(0, url), (1, url)]
    copies = [(2, 0)]
    pat = _cdp.capture(shots, copies, str(tmp_path), 7, 960, 540, {}, "scene 07",
                       scenes._chrome_bin({}), 2, lambda *a: None)
    assert pat.endswith(".jpg")
    for i in (0, 1, 2):
        assert os.path.getsize(pat % i) > 3000, f"frame {i} looks blank"
    a = Image.open(pat % 0).convert("RGB")
    assert a.getextrema() != ((0, 0), (0, 0), (0, 0))   # non-blank render

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
def test_split_media_image_is_static(tmp_path):
    """A .split content-page side image must NOT zoom — a moving image next to revealing bullets is
    distracting (and steps with the cue capture). A .split page with no animated text renders
    IDENTICALLY at ?p=0 and ?p=1 (the image is frozen by `.split .media img{animation:none}`)."""
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    motifs = os.path.join(skill, "assets", "html", "motifs.css")
    js = os.path.join(skill, "assets", "html", "seek.js")
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
    scenes._chrome_shot(f"file://{page}?p=0", str(a), 1920, 1080, {})
    scenes._chrome_shot(f"file://{page}?p=1", str(b), 1920, 1080, {})
    assert Image.open(a).convert("RGB").tobytes() == Image.open(b).convert("RGB").tobytes()  # static, no zoom


@pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")
def test_kenburns_hero_backdrop_motion_captured(tmp_path):
    """Ken-Burns still animates on a full-bleed hero .bg-photo (NOT inside a .split): the frame
    differs at ?p=0 vs ?p=1, proving the hero backdrop motion path is intact."""
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    motifs = os.path.join(skill, "assets", "html", "motifs.css")
    js = os.path.join(skill, "assets", "html", "seek.js")
    img = tmp_path / "pic.png"
    pic = Image.new("RGB", (200, 200), (20, 60, 140))
    for x in range(200):
        for y in range(200):
            pic.putpixel((x, y), ((x * 5) % 256, (y * 7) % 256, 90))
    pic.save(img)
    page = tmp_path / "hero.html"
    page.write_text(
        '<!doctype html><html><head><meta charset="utf-8">'
        f'<link rel="stylesheet" href="file://{base}">'
        f'<link rel="stylesheet" href="file://{motifs}"></head>'
        f'<body><img class="bg-photo kenburns" src="file://{img}" alt="">'
        '<div class="stage"><h1 class="title">Hero</h1></div>'
        f'<script src="file://{js}"></script></body></html>')
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    scenes._chrome_shot(f"file://{page}?p=0", str(a), 1920, 1080, {})
    scenes._chrome_shot(f"file://{page}?p=1", str(b), 1920, 1080, {})
    assert Image.open(a).convert("RGB").tobytes() != Image.open(b).convert("RGB").tobytes()  # hero KB moves

def test_base_css_design_tokens_and_classes():
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    css = open(os.path.join(skill, "assets", "html", "base.css")).read()
    for tok in ("--ease-expo", "--ease-over", "--font-mono", "--shadow-primary",
                "--shadow-float", "--hairline", "--stagger"):
        assert tok in css, f"missing token {tok}"
    for cls in (".reveal-pop", ".reveal-up-sm", ".mono", ".card", ".dash", ".grid-asym", ".dash-col"):
        assert cls in css, f"missing class {cls}"
    # seek-safe: the new spring reveal must be paused
    i = css.index(".reveal-pop")
    assert "animation-play-state:paused" in css[i:i+240]
    assert "tabular-nums" in css            # data figures use tabular numerals

@pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")
def test_reveal_pop_motion_captured(tmp_path):
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    js = os.path.join(skill, "assets", "html", "seek.js")
    page = tmp_path / "pop.html"
    page.write_text('<!doctype html><html><head><meta charset="utf-8">'
                    f'<link rel="stylesheet" href="file://{base}"></head>'
                    '<body><div class="stage"><div class="stat reveal-pop">42</div></div>'
                    f'<script src="file://{js}"></script></body></html>')
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    scenes._chrome_shot(f"file://{page}?p=0", str(a), 960, 540, {})
    scenes._chrome_shot(f"file://{page}?p=1", str(b), 960, 540, {})
    from PIL import Image
    assert Image.open(a).convert("RGB").tobytes() != Image.open(b).convert("RGB").tobytes()

def test_motifs_focus_divider_and_kenburns_drift():
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    css = open(os.path.join(skill, "assets", "html", "motifs.css")).read()
    for cls in (".defocus", ".accent-fill", ".bg-paper"):
        assert cls in css, f"missing {cls}"
    # Ken-Burns now drifts diagonally, not scale-only
    i = css.index("@keyframes mt-kenburns")
    assert "translate(" in css[i:i+160]
    assert "#0d1117" not in css                      # scrim still theme-derived

def test_living_backdrop_classes_are_seekable():
    """The living-backdrop utilities exist, are paused (seek-frozen), and seek.js treats them as
    AMBIENT — progress-driven AND excluded from the reveal-stagger envelope."""
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    motifs = open(os.path.join(skill, "assets", "html", "motifs.css")).read()
    for rule, kf in ((".bg-live{", "@keyframes mt-bg-live"), (".bg-drift{", "@keyframes mt-bg-drift")):
        assert rule in motifs and kf in motifs, f"missing {rule}"
        i = motifs.index(rule)                                      # the RULE, not the doctrine comment
        assert "animation-play-state:paused" in motifs[i:i + 160]   # seek.js can freeze it
    js = open(os.path.join(skill, "assets", "html", "seek.js")).read()
    assert ".bg-live" in js and ".bg-drift" in js and "[data-ambient]" in js   # recognised as ambient
    assert "s.ambient ? m :" in js          # ambient EXCLUDED from the reveal-stagger envelope
    assert "-(p * s.dur)" in js             # ambient is PROGRESS-driven (0->1 over the scene)

def test_reduced_motion_disables_living_backdrop():
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    css = open(os.path.join(skill, "assets", "html", "reduced-motion.css")).read()
    assert ".bg-live" in css and ".bg-drift" in css   # living backdrops shown static under reduced motion
    assert "[data-ambient]" in css   # raw ambient escape hatch neutralized too (else it moves — vestibular leak)

def test_living_backdrop_coverage_never_exposes_edge():
    """A scaled full-bleed backdrop (object-fit:cover, CENTERED origin) must always cover the
    1920x1080 canvas: the scale margin must exceed the (scaled) translate at every p, or a hard --bg
    edge shows. Guards the motifs.css scale floors against being lowered below the translate."""
    import re
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    css = open(os.path.join(skill, "assets", "html", "motifs.css")).read()
    W, H = 1920, 1080
    def parse(kf):
        m = re.search(r'@keyframes ' + kf + r'\{(.*?)\}\}', css, re.S)
        assert m, f"keyframe {kf} not found"
        xforms = re.findall(r'transform:\s*([^}]+)', m.group(1))
        assert len(xforms) == 2, f"{kf}: expected from+to transforms"
        def vals(t):
            s = float(re.search(r'scale\(([0-9.]+)\)', t).group(1))
            tr = re.search(r'translate(?:X)?\(([^)]+)\)', t)
            tx = ty = 0.0
            if tr:
                parts = [x.strip().rstrip('%') for x in tr.group(1).split(',')]
                tx = float(parts[0]) / 100.0
                ty = float(parts[1]) / 100.0 if len(parts) > 1 else 0.0
            return s, tx, ty
        return vals(xforms[0]), vals(xforms[1])
    for kf in ("mt-bg-live", "mt-bg-drift"):
        (s0, x0, y0), (s1, x1, y1) = parse(kf)
        worst = 1e9
        for k in range(101):
            p = k / 100.0
            s = s0 + (s1 - s0) * p                      # linear proxy (endpoints dominate the min)
            tx = abs(x0 + (x1 - x0) * p); ty = abs(y0 + (y1 - y0) * p)
            mh = (s - 1) / 2 * W - s * tx * W           # margin each side, centered origin (conservative)
            mv = (s - 1) / 2 * H - s * ty * H
            worst = min(worst, mh, mv)
        assert worst >= 24, f"{kf}: min coverage margin {worst:.1f}px < 24px — a --bg edge can show"

@pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")
def test_living_backdrop_is_ambient_and_does_not_shift_reveals(tmp_path):
    """The determinism guarantee: an ambient backdrop (here a [data-ambient] box with a long 10s
    animation) is (a) CAPTURED — it moves between ?p=0 and ?p=1 — and (b) EXCLUDED from the reveal
    envelope, so a reveal is frozen IDENTICALLY whether or not the ambient element is present. If
    ambient were (wrongly) folded into `total`, its 10s duration would balloon the envelope and the
    reveal would jump to fully-revealed at p=0.5 — the top-region crops would then differ."""
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    motifs = os.path.join(skill, "assets", "html", "motifs.css")
    js = os.path.join(skill, "assets", "html", "seek.js")
    head = ('<!doctype html><html><head><meta charset="utf-8">'
            f'<link rel="stylesheet" href="file://{base}">'
            f'<link rel="stylesheet" href="file://{motifs}"></head>')
    # a delayed reveal box in the TOP-LEFT (its freeze position is what must not move)
    reveal = ('<div class="reveal-up" style="position:absolute;top:60px;left:60px;'
              'width:360px;height:180px;background:#12a150;animation-delay:.4s"></div>')
    # a full-duration AMBIENT box in the BOTTOM-LEFT (long 10s anim; the regression bait)
    ambient = ('<div data-ambient style="position:absolute;bottom:60px;left:60px;width:200px;'
               'height:200px;background:#d21f3c;animation:mt-float 10s ease forwards;'
               'animation-play-state:paused"></div>')
    tail = f'<script src="file://{js}"></script></body></html>'
    p_amb = tmp_path / "amb.html";  p_amb.write_text(head + "<body>" + reveal + ambient + tail)
    p_no = tmp_path / "noamb.html"; p_no.write_text(head + "<body>" + reveal + tail)

    def shot(page, p, name):
        out = tmp_path / name
        scenes._chrome_shot(f"file://{page}?p={p}", str(out), 1920, 1080, {})
        return Image.open(out).convert("RGB")

    amb_half = shot(p_amb, 0.5, "amb_half.png")
    no_half = shot(p_no, 0.5, "no_half.png")
    top = (0, 0, 600, 400)   # contains ONLY the reveal box (ambient box is at the bottom)
    assert amb_half.crop(top).tobytes() == no_half.crop(top).tobytes(), \
        "ambient backdrop shifted the reveal's freeze time — it must be excluded from the envelope"

    amb0 = shot(p_amb, 0, "amb0.png")
    amb1 = shot(p_amb, 1, "amb1.png")
    bot = (0, 800, 400, 1080)   # contains the ambient box
    assert amb0.crop(bot).tobytes() != amb1.crop(bot).tobytes(), \
        "ambient backdrop did not move between p=0 and p=1 — it is not progress-driven"

def test_render_html_cue_capture_passes_cues(tmp_path, monkeypatch):
    # a page with two cued points + a words.json -> render_html should resolve cues and pass ?cues= to chrome
    import json
    out = tmp_path; (out / "audio").mkdir(); (out / "pages").mkdir()
    (out / "audio" / "03.words.json").write_text(json.dumps(
        [{"w": "alpha", "t": 0.5}, {"w": "beta", "t": 3.0}]))
    (out / "pages" / "p.html").write_text('<div class="stage">'
        '<div class="row reveal-up-sm" data-cue-index="0" data-cue="alpha">A</div>'
        '<div class="row reveal-up-sm" data-cue-index="1" data-cue="beta">B</div></div>')
    seen = []
    monkeypatch.setattr(scenes, "_chrome_shot", lambda url, o, w, h, m: (seen.append(url),
                        __import__("pathlib").Path(o).write_bytes(b"\x89PNG\r\n")))
    meta = {"_out": str(out), "fps": 30, "capture": "screenshot"}
    scenes.render_html({"html": "pages/p.html", "anim_seconds": 1.0}, meta, 1920, 1080, 120, str(out / "wd"), 3)
    assert any("cues=" in u and "dur=" in u for u in seen), "cue params not passed"


def _cues_from_urls(urls):
    import re
    for u in urls:
        m = re.search(r"cues=([0-9.,]+)&dur=([0-9.]+)", u)
        if m:
            return [float(x) for x in m.group(1).split(",")], float(m.group(2))
    return None, None

def _stub_shot(scenes_mod, monkeypatch, seen):
    monkeypatch.setattr(scenes_mod, "_chrome_shot", lambda url, o, w, h, m: (seen.append(url),
                        __import__("pathlib").Path(o).write_bytes(b"\x89PNG\r\n")))

def test_render_html_cue_times_clamped_within_scene(tmp_path, monkeypatch):
    """A cue that would land past the scene end must be CLAMPED before the final frame, else the
    point stays hidden. 1 word (alpha) + 2 anchors -> beta is EPS-pushed; with the clamp all cues
    sit within the capture window (<= dur - margin)."""
    import json
    out = tmp_path; (out / "audio").mkdir(); (out / "pages").mkdir()
    (out / "audio" / "03.words.json").write_text(json.dumps([{"w": "alpha", "t": 0.5}]))
    (out / "pages" / "p.html").write_text('<div class="stage">'
        '<div class="row reveal-up-sm" data-cue-index="0" data-cue="alpha">A</div>'
        '<div class="row reveal-up-sm" data-cue-index="1" data-cue="beta">B</div></div>')
    seen = []; _stub_shot(scenes, monkeypatch, seen)
    # 30 frames @30fps -> dur=1.0, margin=dur-0.5=0.5
    scenes.render_html({"html": "pages/p.html"}, {"_out": str(out), "fps": 30, "capture": "screenshot"}, 1920, 1080, 30, str(out / "wd"), 3)
    cues, dur = _cues_from_urls(seen)
    assert cues is not None and dur == 1.0
    assert max(cues) <= dur - 0.4, f"a cue exceeded the capture window: {cues} (dur {dur})"

def test_render_html_cue_capture_copies_frames(tmp_path, monkeypatch):
    """The cue path must NOT screenshot every frame — it bursts around each cue and copies the rest."""
    import json
    out = tmp_path; (out / "audio").mkdir(); (out / "pages").mkdir()
    (out / "audio" / "03.words.json").write_text(json.dumps([{"w": "alpha", "t": 0.3}, {"w": "beta", "t": 1.0}]))
    (out / "pages" / "p.html").write_text('<div class="stage">'
        '<div class="row reveal-up-sm" data-cue-index="0" data-cue="alpha">A</div>'
        '<div class="row reveal-up-sm" data-cue-index="1" data-cue="beta">B</div></div>')
    seen = []; _stub_shot(scenes, monkeypatch, seen)
    frames = 90  # 3s @30fps
    scenes.render_html({"html": "pages/p.html"}, {"_out": str(out), "fps": 30, "capture": "screenshot"}, 1920, 1080, frames, str(out / "wd"), 3)
    n_png = len(list((out / "wd").glob("scene_03_*.png")))
    assert n_png == frames, "every frame index must produce a PNG (no %04d gap)"
    assert len(seen) < frames, f"cue capture should copy held frames, not shoot all ({len(seen)} of {frames})"

def _shot_progress(urls):
    import re
    return [float(re.search(r'[?&]p=([0-9.]+)', u).group(1)) for u in urls]

def test_render_html_ambient_page_shoots_every_frame_cued(tmp_path, monkeypatch):
    """A living backdrop moves CONTINUOUSLY, so the frame-copy hold optimization would freeze it then
    snap. When a page carries .bg-live/.bg-drift/[data-ambient], the cued path must shoot EVERY frame
    (no copies), each at true scene progress spanning 0->1."""
    import json
    out = tmp_path; (out / "audio").mkdir(); (out / "pages").mkdir()
    (out / "audio" / "03.words.json").write_text(json.dumps([{"w": "alpha", "t": 0.3}, {"w": "beta", "t": 1.0}]))
    (out / "pages" / "p.html").write_text(
        '<img class="bg-soft bg-live" src="x" alt="">'          # <-- the living backdrop
        '<div class="stage">'
        '<div class="row reveal-up-sm" data-cue-index="0" data-cue="alpha">A</div>'
        '<div class="row reveal-up-sm" data-cue-index="1" data-cue="beta">B</div></div>')
    seen = []; _stub_shot(scenes, monkeypatch, seen)
    frames = 90   # 3s @30fps
    scenes.render_html({"html": "pages/p.html"}, {"_out": str(out), "fps": 30, "capture": "screenshot"}, 1920, 1080, frames, str(out / "wd"), 3)
    assert len(seen) == frames, f"ambient page must shoot every frame, got {len(seen)}/{frames}"
    ps = _shot_progress(seen)
    assert min(ps) <= 0.01 and max(ps) >= 0.98, f"progress must span the scene: {min(ps):.3f}..{max(ps):.3f}"
    assert any("cues=" in u for u in seen), "cued reveals must still be decoupled via cue params"

def test_render_html_ambient_page_shoots_every_frame_paced(tmp_path, monkeypatch):
    """Cue-less (paced) ambient page: still every frame, progress driven across the WHOLE scene to
    p~1.0 (not the whole push crammed into anim_seconds then frozen)."""
    out = tmp_path; (out / "pages").mkdir()
    (out / "pages" / "p.html").write_text(
        '<img class="bg-photo bg-drift" src="x" alt="">'
        '<div class="stage"><h1 class="title reveal-up">Hero</h1></div>')
    seen = []; _stub_shot(scenes, monkeypatch, seen)
    frames = 60
    scenes.render_html({"html": "pages/p.html", "anim_seconds": 1.0},
                       {"_out": str(out), "fps": 30, "capture": "screenshot"}, 1920, 1080, frames, str(out / "wd"), 7)
    assert len(seen) == frames, f"paced ambient page must shoot every frame, got {len(seen)}/{frames}"
    ps = _shot_progress(seen)
    assert max(ps) >= 0.999, f"paced ambient progress must reach ~1.0 across the scene, got {max(ps):.3f}"

def test_ambient_detection_quote_agnostic_and_token_exact(tmp_path, monkeypatch):
    """_has_ambient must agree with seek.js's .matches(): SINGLE or double quotes, and EXACT class
    tokens. A single-quoted living backdrop must trigger every-frame capture; a look-alike token
    (my-bg-live) must NOT (else non-ambient pages needlessly shoot every frame / the freeze-snap guard
    misfires the other way)."""
    out = tmp_path; (out / "pages").mkdir()
    def shots_for(body):
        seen = []; _stub_shot(scenes, monkeypatch, seen)
        (out / "pages" / "p.html").write_text(body)
        scenes.render_html({"html": "pages/p.html", "anim_seconds": 1.0},
                           {"_out": str(out), "fps": 30, "capture": "screenshot"}, 1920, 1080, 60, str(out / "wd"), 7)
        return len(seen)
    # single-quoted ambient -> ambient -> every frame (60, no copies)
    assert shots_for("<img class='bg-photo bg-live' src='x'>"
                     "<div class='stage'><h1 class='title reveal-up'>H</h1></div>") == 60
    # look-alike token 'my-bg-live' is NOT the class 'bg-live' -> not ambient -> paced path copies (< 60)
    assert shots_for('<img class="bg-photo my-bg-live" src="x">'
                     '<div class="stage"><h1 class="title reveal-up">H</h1></div>') < 60

def test_render_html_noncontiguous_cue_index_sparse(tmp_path, monkeypatch):
    """data-cue-index 0 and 2 (gap at 1) -> the cues= param must be a sparse array of length 3 so
    seek.js indexes correctly (cues[2] = the 3rd element's time, not the 2nd)."""
    import json
    out = tmp_path; (out / "audio").mkdir(); (out / "pages").mkdir()
    (out / "audio" / "03.words.json").write_text(json.dumps([{"w": "alpha", "t": 0.3}, {"w": "beta", "t": 1.0}]))
    (out / "pages" / "p.html").write_text('<div class="stage">'
        '<div class="row reveal-up-sm" data-cue-index="0" data-cue="alpha">A</div>'
        '<div class="row reveal-up-sm" data-cue-index="2" data-cue="beta">B</div></div>')
    seen = []; _stub_shot(scenes, monkeypatch, seen)
    scenes.render_html({"html": "pages/p.html"}, {"_out": str(out), "fps": 30, "capture": "screenshot"}, 1920, 1080, 90, str(out / "wd"), 3)
    cues, _ = _cues_from_urls(seen)
    assert len(cues) == 3, f"sparse cue array must have 3 slots (indices 0,1,2): {cues}"
    assert cues[0] > 0 and cues[2] > 0  # the two real points resolved at their indices

def test_split_media_image_static_rule_present():
    """No-Chrome grep: the static-split rule must exist (deletion would otherwise pass CI)."""
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    css = open(os.path.join(skill, "assets", "html", "motifs.css")).read()
    i = css.find(".split .media img")
    assert i != -1 and "animation:none" in css[i:i + 60]

def test_render_html_no_words_uses_anim_path(tmp_path, monkeypatch):
    out = tmp_path; (out / "pages").mkdir()
    (out / "pages" / "p.html").write_text('<div class="stage"><div class="title reveal-up">X</div></div>')
    seen = []
    monkeypatch.setattr(scenes, "_chrome_shot", lambda url, o, w, h, m: (seen.append(url),
                        __import__("pathlib").Path(o).write_bytes(b"\x89PNG\r\n")))
    scenes.render_html({"html": "pages/p.html", "anim_seconds": 1.0}, {"_out": str(out), "fps": 30, "capture": "screenshot"},
                       1920, 1080, 60, str(out / "wd"), 5)
    assert seen and all("cues=" not in u for u in seen), "should use anim path (no cues)"

def test_render_html_cued_points_but_no_words_uses_anim(tmp_path, monkeypatch):
    out = tmp_path; (out / "pages").mkdir()
    (out / "pages" / "p.html").write_text('<div class="stage">'
        '<div class="row reveal-up-sm" data-cue-index="0" data-cue="alpha">A</div></div>')
    seen = []
    monkeypatch.setattr(scenes, "_chrome_shot", lambda url, o, w, h, m: (seen.append(url),
                        __import__("pathlib").Path(o).write_bytes(b"\x89PNG\r\n")))
    scenes.render_html({"html": "pages/p.html", "anim_seconds": 1.0}, {"_out": str(out), "fps": 30, "capture": "screenshot"},
                       1920, 1080, 60, str(out / "wd"), 7)   # no audio/07.words.json AND no meta._narration
    assert seen and all("cues=" not in u for u in seen), "no words.json + no narration -> anim path"

def test_render_html_text_cues_when_no_words_but_narration(tmp_path, monkeypatch):
    # NEW: no words.json, but the scene narration is available -> reveals are ESTIMATED from each
    # anchor's position in the narration text (text-cues), so the cued capture path runs (cues= in URL).
    out = tmp_path; (out / "pages").mkdir()
    (out / "pages" / "p.html").write_text('<div class="stage">'
        '<div class="row reveal-up-sm" data-cue-index="0" data-cue="alpha">A</div>'
        '<div class="row reveal-up-sm" data-cue-index="1" data-cue="beta">B</div></div>')
    seen = []
    monkeypatch.setattr(scenes, "_chrome_shot", lambda url, o, w, h, m: (seen.append(url),
                        __import__("pathlib").Path(o).write_bytes(b"\x89PNG\r\n")))
    meta = {"_out": str(out), "fps": 30, "capture": "screenshot",
            "_narration": "first we introduce alpha, then much later we get to beta near the end."}
    scenes.render_html({"html": "pages/p.html"}, meta, 1920, 1080, 60, str(out / "wd"), 8)
    assert seen and any("cues=" in u for u in seen), "no words.json + narration -> text-estimated cues"

@pytest.mark.skipif(not _chrome_present(), reason="no Chrome")
def test_seekjs_cue_override_gates_reveals(tmp_path):
    skill = os.path.dirname(os.path.dirname(os.path.abspath(scenes.__file__)))
    base = os.path.join(skill, "assets", "html", "base.css")
    js = os.path.join(skill, "assets", "html", "seek.js")
    page = tmp_path / "c.html"
    page.write_text('<!doctype html><html><head><meta charset="utf-8">'
                    f'<link rel="stylesheet" href="file://{base}"></head><body><div class="stage">'
                    '<div class="row reveal-up-sm" data-cue-index="0">A</div>'
                    '<div class="row reveal-up-sm" data-cue-index="1">B</div></div>'
                    f'<script src="file://{js}"></script></body></html>')
    early, late = tmp_path / "e.png", tmp_path / "l.png"
    # dur=4s, cues at 0.2 and 2.0; at p=0.1 (t=0.4s) only point 0 is in; at p=0.6 (t=2.4s) both are
    scenes._chrome_shot(f"file://{page}?cues=0.2,2.0&dur=4&p=0.1", str(early), 960, 540, {})
    scenes._chrome_shot(f"file://{page}?cues=0.2,2.0&dur=4&p=0.6", str(late), 960, 540, {})
    from PIL import Image
    assert Image.open(early).convert("RGB").tobytes() != Image.open(late).convert("RGB").tobytes()


# ── C1: one color world (theme.css palette reaches the programmatic tier) ─────────────
def test_scene_palette_dark_fallback():
    p = scenes._scene_palette({})                     # no _out -> original dark constants
    assert p["bg"] == "#0d1117" and p["fg"] == "#ffffff" and p["accent"] == "#4C9BE8"

def test_scene_palette_parses_theme_css_and_resolves_var(tmp_path):
    (tmp_path / "theme.css").write_text(
        ":root{--bg:#f5f3ee;--surface:#e8e6e1;--fg:#161412;--muted:#74726e;"
        "--accent:#0b6e99;--accent2:#c1472e;--rule:var(--accent2);}")
    scenes._PAL_CACHE.clear()
    p = scenes._scene_palette({"_out": str(tmp_path)})
    assert p["bg"] == "#f5f3ee" and p["fg"] == "#161412"
    assert p["accent"] == "#0b6e99" and p["rule"] == "#c1472e"   # var(--accent2) resolved

def test_title_uses_light_theme_bg(tmp_path):
    (tmp_path / "theme.css").write_text(":root{--bg:#f5f3ee;--fg:#161412;--accent:#0b6e99;}")
    scenes._PAL_CACHE.clear()
    pat = scenes.render_title({"title": "Light"}, {"fps": 30, "language": "en", "_out": str(tmp_path)},
                              640, 360, 3, str(tmp_path), 1)
    r, g, b = Image.open(pat % 2).convert("RGB").getpixel((5, 5))
    assert r > 220 and g > 210 and b > 200            # background is the light paper, not dark

# ── C7: climax counter holds the final value static (no overshoot) ───────────────────
def test_counter_climax_holds_final_static(tmp_path):
    props = {"kind": "counter", "climax": True, "data": [{"label": "x", "value": 100}]}
    pat = scenes.render_chart(props, META, 640, 360, 30, str(tmp_path), 1)
    assert _pix(pat % 25) == _pix(pat % 29)           # value landed before the end, then held static

def test_counter_nonclimax_still_counting_at_end(tmp_path):
    props = {"kind": "counter", "data": [{"label": "x", "value": 100}]}
    pat = scenes.render_chart(props, META, 640, 360, 30, str(tmp_path), 2)
    assert _pix(pat % 25) != _pix(pat % 29)           # no hold: still easing up to the final value

# ── C8: serif for editorial roles, sans for data ─────────────────────────────────────
def test_serif_path_latin_is_bundled_serif():
    p = scenes._serif_path({}, "Headline")
    assert p and p.endswith("DejaVuSerif.ttf") and os.path.exists(p)

def test_serif_and_sans_roles_differ():
    serif = scenes._font(META, "Title", 40, role="serif")
    sans = scenes._font(META, "Title", 40, role="sans")
    assert getattr(serif, "path", "").endswith("DejaVuSerif.ttf")
    assert getattr(sans, "path", "") != getattr(serif, "path", "")


# ── D: reduced-motion HTML injection + override css ──────────────────────────────────
def test_inject_reduced_motion_adds_link_last_in_head():
    html = '<html><head><link rel="stylesheet" href="base.css"></head><body>x</body></html>'
    out = scenes._inject_reduced_motion(html, "/abs/reduced-motion.css")
    assert out.index("base.css") < out.index("reduced-motion.css") < out.index("</head>")

def test_reduced_motion_css_neutralizes_all_transform_channels():
    assert os.path.exists(scenes._REDUCED_MOTION_CSS)
    css = open(scenes._REDUCED_MOTION_CSS).read()
    assert "animation-name: fade" in css and "transform: none" in css   # reveals -> opacity-only
    assert ".float" in css and "img.kenburns" in css and "animation: none" in css
    assert "stroke-dashoffset: 0" in css                                 # .draw shown, not hidden


def test_on_fill_argmax_black_on_light_white_on_dark():
    assert scenes._on_fill("#ffd166") == "#111111"               # bright yellow -> black text
    assert scenes._on_fill("#0d1117") == "#ffffff"               # near-black -> white text

def test_reduced_motion_title_has_no_rise(tmp_path):
    meta_rm = {"fps": 30, "language": "en", "reduced_motion": True}
    pat = scenes.render_title({"title": "Steady"}, meta_rm, 640, 360, 10, str(tmp_path), 1)
    early = Image.open(pat % 2).convert("L")
    final = Image.open(pat % 9).convert("L")
    bg = final.getpixel((3, 3))
    def bbox(im):
        from PIL import ImageChops
        return ImageChops.difference(im, Image.new("L", im.size, bg)).getbbox()
    assert bbox(early)[1] == bbox(final)[1]                      # same top y: fade only, no translate


def test_chart_bars_direct_labels_deterministic(tmp_path):
    props = {"kind": "bars", "unit": "%", "data": [{"label": "A", "value": 42}, {"label": "B", "value": 73}]}
    a = tmp_path / "a"; b = tmp_path / "b"; a.mkdir(); b.mkdir()
    pa = scenes.render_chart(props, META, 640, 360, 12, str(a), 1)
    pb = scenes.render_chart(props, META, 640, 360, 12, str(b), 1)
    assert all(_pix(pa % i) == _pix(pb % i) for i in range(12))   # labels stay pure/deterministic
    assert _pix(pa % 11) != _pix(pa % 9)                          # label alpha still ramping at the end
