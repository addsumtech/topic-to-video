import os, json, pytest
import ingest, tts, render, storyboard as sb, _common

def _build(tmp_path, fixtures_dir):
    out = str(tmp_path / "proj")
    ingest.ingest(os.path.join(fixtures_dir, "deck.pdf"), out)
    data = sb.load(os.path.join(out, "storyboard.json"))
    data["meta"]["voice"] = "say:Samantha"      # offline-deterministic; no edge/network in CI
    for s in data["slides"]:
        s["narration"] = f"This is slide {s['index']}."
    sb.save(data, os.path.join(out, "storyboard.json"))
    tts.synthesize(out)
    return out

@pytest.mark.skipif(not _common.have_tool("say"), reason="needs say+ffmpeg")
def test_sample_render(tmp_path, fixtures_dir):
    out = _build(tmp_path, fixtures_dir)
    mp4 = render.render(out, sample=1)
    assert os.path.exists(mp4)
    assert _common.audio_duration(mp4) > 0.3

@pytest.mark.skipif(not _common.have_tool("say"), reason="needs say+ffmpeg")
def test_full_render_emits_mp4_and_srt(tmp_path, fixtures_dir):
    out = _build(tmp_path, fixtures_dir)
    mp4 = render.render(out)
    assert os.path.exists(mp4)
    assert os.path.exists(os.path.join(out, "out.srt"))
    assert os.path.getsize(os.path.join(out, "out.srt")) > 0

def test_caption_overlay_draws_pixels(tmp_path):
    from PIL import Image
    p = str(tmp_path / "ov.png")
    render._caption_layer("Hello world, this is a burned-in caption.", 1920, 1080, p)
    im = Image.open(p).convert("RGBA")
    # The bottom band should contain opaque (drawn) pixels from the caption bar.
    bottom = im.crop((0, int(1080 * 0.8), 1920, 1080))
    assert bottom.getchannel("A").getextrema()[1] > 0

def test_band_karaoke_highlight_threads_band_bg(tmp_path, monkeypatch):
    # the spoken-word highlight must be picked against the ACTUAL band ground threaded from the call site
    # (band_bg), not blindly --accent — the reported accent-fill bug. Assert _draw_caption asks
    # _karaoke_hl_rgb with the band_bg it was given, and that the highlighted word draws distinct pixels.
    from PIL import Image
    seen = {}
    real = render._karaoke_hl_rgb
    monkeypatch.setattr(render, "_karaoke_hl_rgb",
                        lambda out, bg, base: seen.setdefault("bg", tuple(bg)) or real(out, bg, base))
    p = str(tmp_path / "band.png")
    terracotta = (181, 101, 47)
    render._caption_layer("alpha beta gamma", 1920, 1080, p, meta={"_out": str(tmp_path)},
                          hl_word=1, band=138, text_rgb=(22, 20, 18), band_bg=terracotta)
    assert seen.get("bg") == terracotta                       # the threaded ground reached the picker
    im = Image.open(p).convert("RGBA")
    assert im.size == (1920, 1080)                            # IN-canvas: the layer never grows the frame
    strip = im.crop((0, 1080 - 138, 1920, 1080))             # the in-canvas strip [H-band, H] carries the text
    assert strip.getchannel("A").getextrema()[1] > 0

def test_overlay_empty_when_nothing_to_draw(tmp_path):
    from PIL import Image
    p = str(tmp_path / "empty.png")
    render._caption_layer("", 1920, 1080, p)
    im = Image.open(p).convert("RGBA")
    assert im.getchannel("A").getextrema()[1] == 0

def test_script_detection():
    assert render._script_of("これはテストです") == "ja"      # kana -> Japanese
    assert render._script_of("이것은 시험입니다") == "ko"       # hangul -> Korean
    assert render._script_of("这是中文") == "zh"               # Han only -> Chinese
    assert render._script_of("这是中文", "ja") == "ja"         # Han + ja hint -> Japanese
    assert render._script_of("plain english") == "latin"

def test_cjk_caption_wraps_into_multiple_lines():
    # Chinese has no spaces, so the old word-wrap left it as one overflowing line.
    # The CJK-aware wrap must break a long run across multiple lines that each fit.
    from PIL import Image, ImageDraw
    d = ImageDraw.Draw(Image.new("RGB", (1920, 1080)))
    font = render._load_font(48, render._font_path({"language": "zh"}, "测"))
    long_zh = "这是一段很长的中文字幕用来测试自动换行是否会把它拆成多行" * 3
    lines = render._wrap(d, long_zh, font, int(1920 * 0.9))
    assert len(lines) >= 2
    assert all(d.textlength(ln, font=font) <= int(1920 * 0.9) for ln in lines)

def test_latin_wrap_unchanged():
    from PIL import Image, ImageDraw
    d = ImageDraw.Draw(Image.new("RGB", (1920, 1080)))
    font = render._load_font(48)
    lines = render._wrap(d, "the quick brown fox " * 8, font, int(1920 * 0.9))
    assert len(lines) >= 2
    # words stay intact (joined by single spaces, no mid-word breaks)
    assert all(" " in ln or ln == "the" for ln in lines)

def test_caption_chunks_cjk_splits_no_wall_of_text():
    # CJK punctuation (。，) has no trailing space; the splitter must still break it into
    # multiple short chunks instead of one screen-filling block.
    zh = ("再看最新进展，窗口正在收窄。SpaceX 已完成史上最大的 IPO，资本火力空前。"
          "Starship V3 已首飞，但尚未投运，计划下半年入轨。对手出现波动，窗口正在收窄。")
    chunks = render._split_caption_chunks(zh)
    assert len(chunks) >= 4
    assert all(len(c) <= 40 for c in chunks)   # no wall-of-text chunk

def test_caption_chunks_latin_unchanged():
    en = "Hello world. This is the first sentence. And here is a short second one."
    chunks = render._split_caption_chunks(en)
    assert len(chunks) >= 2
    assert chunks[0] == "Hello world."

def test_caption_chunks_cjk_with_ascii_punctuation_splits():
    # Chinese authored with ASCII commas/colons (no trailing space) is common — the splitter
    # must still break it on those marks, not leave one 50-char wall. Regression for the
    # "ASCII comma inside CJK never splits" bug.
    zh = "承载证据的图,都是真的:原图精准提取,公式是真 LaTeX 能改,概念在真实输入上现算,不是随手贴张糊图。"
    chunks = render._split_caption_chunks(zh)
    assert len(chunks) >= 2
    assert all(len(c) <= 36 for c in chunks)             # no wall-of-text chunk
    # no chunk ends on a dangling clause mark, and CJK joins stay tight (no space after a comma)
    assert all(c[-1] not in "，、：；,;:" for c in chunks)
    assert ", " not in "".join(chunks) and ": " not in "".join(chunks)

def test_caption_chunks_keeps_decimals_intact():
    # an ASCII period/comma between digits must NOT split (1.77, 1,000 stay whole)
    chunks = render._split_caption_chunks("缩放系数是 1.77 倍,采样 1,000 次,效果显著。")
    joined = "".join(chunks)
    assert "1.77" in joined and "1,000" in joined

def test_fit_frame_cover_fills_no_letterbox(tmp_path):
    from PIL import Image
    src = str(tmp_path / "s.png"); dst = str(tmp_path / "d.png")
    Image.new("RGB", (100, 100), (200, 80, 20)).save(src)   # square, non-black
    render._fit_frame(src, dst, 200, 100, fit="cover")       # target 2:1
    im = Image.open(dst).convert("RGB")
    assert im.size == (200, 100)
    # left & right edge columns are image content (no black letterbox bars)
    assert im.getpixel((0, 50)) != (0, 0, 0) and im.getpixel((199, 50)) != (0, 0, 0)

def test_fit_frame_contain_unchanged(tmp_path):
    from PIL import Image
    src = str(tmp_path / "s.png"); dst = str(tmp_path / "d.png")
    Image.new("RGB", (100, 100), (200, 80, 20)).save(src)
    render._fit_frame(src, dst, 200, 100)                    # default contain
    im = Image.open(dst).convert("RGB")
    assert im.size == (200, 100)
    assert im.getpixel((0, 50)) == (0, 0, 0)                 # letterbox bar present

def test_render_slide_ungenerated_ai_image_raises(tmp_path):
    s = sb.new_slide(1, None); s["image"] = None; s["image_prompt"] = "x"
    s["audio"] = "audio/01.aiff"; s["duration"] = 2.0
    meta = {"_out": str(tmp_path), "fps": 30}
    with pytest.raises(sb.StoryboardError):
        render._render_slide(s, meta, 1920, 1080, str(tmp_path / "c.mp4"), False, str(tmp_path))

def test_fingerprint_includes_type_and_props():
    meta = {"_out": "/tmp", "fps": 30}
    base = {"index": 1, "image": None, "audio": None, "duration": 3.0, "motion": {},
            "narration": "n", "captions": [], "callouts": [], "type": "title",
            "props": {"title": "A"}}
    fp = lambda s: render._fingerprint(s, meta, 1920, 1080, 2, True, False)
    a = fp(base)
    b = fp({**base, "props": {"title": "B"}})       # prop change -> different
    c = fp({**base, "type": "chart", "props": {"kind": "bars", "data": [{"label":"x","value":1}]}})
    assert a != b and a != c and a == fp(dict(base))  # stable for identical input

def test_fingerprint_includes_fit():
    meta = {"_out": "/tmp", "fps": 30}
    base = {"index": 1, "image": "frames/01.png", "audio": None, "duration": 3.0,
            "motion": {}, "narration": "n", "captions": [], "callouts": [],
            "type": "slide", "props": None, "fit": "contain"}
    fp = lambda s: render._fingerprint(s, meta, 1920, 1080, 2, True, False)
    assert fp(base) != fp({**base, "fit": "cover"})   # changing fit re-renders
    assert fp(base) == fp(dict(base))                 # stable otherwise

def test_fingerprint_includes_words_json(tmp_path):
    import render
    out = tmp_path; (out / "audio").mkdir()
    slide = {"index": 3, "type": "html", "props": {"html": "pages/p.html"}, "audio": "audio/03.mp3"}
    meta = {"_out": str(out)}
    a = render._fingerprint(slide, meta, 1920, 1080, 2, True, False)
    (out / "audio" / "03.words.json").write_text('[{"w":"x","t":0.1}]')   # add timings
    assert render._fingerprint(slide, meta, 1920, 1080, 2, True, False) != a   # cache busts

def test_fingerprint_busts_on_html_page_edit(tmp_path):
    pg = tmp_path / "pages"; pg.mkdir(); f = pg / "s.html"; f.write_text("a")
    meta = {"_out": str(tmp_path), "fps": 30}
    slide = {"index": 1, "type": "html", "props": {"html": "pages/s.html"},
             "image": None, "audio": None, "duration": 3.0, "motion": {}, "narration": "n",
             "captions": [], "callouts": [], "fit": "contain"}
    fp = lambda: render._fingerprint(slide, meta, 1920, 1080, 2, True, False)
    a = fp()
    f.write_text("a much longer page body that changes the file size")   # edit the page
    assert fp() != a                                                     # cache busts

def test_caption_karaoke_segs_word_windows(tmp_path):
    (tmp_path / "audio").mkdir()
    narr = "It turns your notes into slides."
    words = [{"w": "It", "t": 0.0}, {"w": "turns", "t": 0.4}, {"w": "your", "t": 0.8},
             {"w": "notes", "t": 1.2}, {"w": "into", "t": 1.6}, {"w": "slides", "t": 2.0}]
    import json as _j
    _j.dump(words, open(tmp_path / "audio" / "01.words.json", "w"))
    slide = {"index": 1, "narration": narr, "duration": 3.0, "type": "slide"}
    segs = render._caption_karaoke_segs(slide, {"language": "en"}, str(tmp_path))
    assert segs and len(segs) == 6                      # one overlay per word
    assert [s["hl"] for s in segs] == [0, 1, 2, 3, 4, 5]
    assert segs[0]["start"] == 0.0 and segs[-1]["end"] == 3.0   # last word runs to scene end
    assert all(segs[i]["start"] <= segs[i + 1]["start"] for i in range(5))
    assert all(s["text"] == narr for s in segs)

def test_karaoke_hl_contrast_and_distinct():
    # the highlight must NEVER vanish into the band ground and must differ from the neighbouring words
    T = (0xb5, 0x65, 0x2f)      # terracotta accent
    paper = (0xf5, 0xf2, 0xea); ink = (0x16, 0x14, 0x12); white = (255, 255, 255)
    for band_bg, base in [(T, ink), (T, white), (paper, ink), (ink, paper),
                          ((0x2f, 0x6d, 0x75), white)]:
        hl = render._karaoke_hl_rgb(".", band_bg, base)[:3]
        assert render._wcag_contrast(hl, band_bg) >= 3.0, (band_bg, base, hl)   # readable on the strip
        # distinct from neighbours: either a real luminance gap OR a clear channel-distance
        near = render._wcag_contrast(hl, base) >= 1.6 or sum(abs(a - b) for a, b in zip(hl, base)) >= 120
        assert near, (band_bg, base, hl)
    # the exact reported bug: an accent highlight on an accent-fill band must be REPLACED (not accent)
    assert render._karaoke_hl_rgb(".", T, ink)[:3] != T

def test_karaoke_hl_keeps_accent_on_paper():
    # on a normal light strip the on-brand accent highlight is preserved (no needless change)
    paper = (0xf5, 0xf2, 0xea); ink = (0x16, 0x14, 0x12)
    # with no theme.css, --accent falls back to the default terracotta-ish; assert it's chosen when it clears
    hl = render._karaoke_hl_rgb(".", paper, ink)[:3]
    assert render._wcag_contrast(hl, paper) >= 3.0

def test_ffhex_rgb_parses_ffmpeg_and_css_hex():
    assert render._ffhex_rgb("0xb5652f") == (181, 101, 47)
    assert render._ffhex_rgb("#f5f2ea") == (245, 242, 234)
    assert render._ffhex_rgb("garbage") == (244, 243, 238)   # safe fallback

def test_caption_karaoke_none_when_not_applicable(tmp_path):
    # CJK -> chunk-level (None)
    assert render._caption_karaoke_segs({"index": 1, "narration": "你好世界。", "duration": 3.0},
                                        {"language": "zh"}, str(tmp_path)) is None
    # no words.json -> None
    assert render._caption_karaoke_segs({"index": 2, "narration": "Hello there world.", "duration": 3.0},
                                        {"language": "en"}, str(tmp_path)) is None
    # explicit off -> None even with words.json
    (tmp_path / "audio").mkdir()
    import json as _j
    _j.dump([{"w": "Hello", "t": 0.1}], open(tmp_path / "audio" / "02.words.json", "w"))
    assert render._caption_karaoke_segs({"index": 2, "narration": "Hello world.", "duration": 3.0},
                                        {"language": "en", "captions_karaoke": "off"}, str(tmp_path)) is None

def test_theme_bg_parses_or_defaults(tmp_path):
    (tmp_path / "theme.css").write_text(":root{--bg:#f7f4ee;--fg:#111}")
    assert render._theme_bg(str(tmp_path)) == "0xf7f4ee"
    assert render._theme_bg(str(tmp_path / "nope")) == "0x0d1117"   # no theme.css -> dark default

def test_fade_filter_dip_default_and_off_and_tooshort():
    f = render._fade_filter({"_out": "/x"}, 10.0)                   # dip is the default
    assert "fade=t=in" in f and "fade=t=out" in f and "0x0d1117" in f
    assert render._fade_filter({"transition": "none"}, 10.0) == ""  # explicitly off
    assert render._fade_filter({"transition_seconds": 0.2}, 0.3) == ""  # clip too short to dip

def test_fingerprint_includes_transition():
    meta = {"_out": "/tmp", "fps": 30}
    base = {"index": 1, "image": "frames/01.png", "audio": None, "duration": 3.0, "motion": {},
            "narration": "n", "captions": [], "callouts": [], "type": "slide", "props": None, "fit": "contain"}
    fp = lambda m: render._fingerprint(base, m, 1920, 1080, 2, True, False)
    assert fp(meta) != fp({**meta, "transition": "none"})          # toggling transitions busts the cache


def test_fingerprint_stable_for_imageless_scene_when_outdir_changes(tmp_path):
    # Regression: an html scene has image=None. The fingerprint must NOT stat the output dir
    # (os.path.join(out, "")), whose mtime changes on every render — that defeated the clip cache
    # so all html scenes re-rendered every time. Writing a new file into out must NOT bust it.
    pg = tmp_path / "pages"; pg.mkdir(); (pg / "s.html").write_text("hi")
    meta = {"_out": str(tmp_path), "fps": 30}
    slide = {"index": 1, "type": "html", "props": {"html": "pages/s.html"}, "image": None,
             "audio": None, "duration": 3.0, "motion": {}, "narration": "n", "captions": [],
             "callouts": [], "fit": None}
    fp = lambda: render._fingerprint(slide, meta, 1920, 1080, 2, True, False)
    a = fp()
    (tmp_path / "out.srt").write_text("new log file in the out dir")   # bump out-dir mtime
    os.utime(str(tmp_path), None)
    assert fp() == a                                                   # cache still hits


@pytest.mark.skipif(not _common.have_tool("ffmpeg") or not _common.have_tool("say"),
                    reason="needs ffmpeg + say")
def test_title_scene_renders_and_concats_with_slide(tmp_path, fixtures_dir, monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: False)   # offline-deterministic audio
    out = str(tmp_path / "proj")
    ingest.ingest(os.path.join(fixtures_dir, "deck.pdf"), out)   # gives >=1 real slide
    data = sb.load(os.path.join(out, "storyboard.json"))
    data["meta"]["voice"] = "say:Samantha"
    slide1 = data["slides"][0]; slide1["narration"] = "This is the slide."
    title = sb.new_scene(99, "title", {"title": "Title Scene", "subtitle": "Sub"},
                         narration="Welcome to the talk.")
    data["slides"] = [title, slide1]
    sb.save(data, os.path.join(out, "storyboard.json"))
    tts.synthesize(out)                                     # sets audio+duration for both
    mp4 = render.render(out)
    assert os.path.exists(mp4)
    # both clips concatenated -> total duration ~= sum of scene durations
    total = sum(s["duration"] for s in sb.load(os.path.join(out, "storyboard.json"))["slides"])
    assert abs(_common.audio_duration(mp4) - total) < 0.6
    # the title clip exists and has an audio stream
    import json as _j
    clip = os.path.join(out, ".clips", "clip_99.mp4")
    streams = _j.loads(_common.run(["ffprobe","-v","error","-show_entries","stream=codec_type",
                                    "-of","json", clip]))["streams"]
    kinds = {s["codec_type"] for s in streams}
    assert "video" in kinds and "audio" in kinds


@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_mixed_samplerate_audio_stays_in_sync(tmp_path):
    """Regression: when scene audio comes from different sources (e.g. a partial edge-tts run —
    say .aiff @22050 for some scenes, edge .mp3 @24000 for others), the per-clip encodes must
    normalize the audio rate so the `-c copy` concat stays A/V-aligned. Before the fix the concat
    reinterpreted every clip's audio at the FIRST clip's sample rate, inflating the audio stream
    vs the video and drifting worse over time. Assert the final video/audio stream durations match."""
    import json as _j
    out = str(tmp_path)
    os.makedirs(os.path.join(out, "audio"), exist_ok=True)
    rates = [22050, 24000, 22050, 24000]                 # mixed, as a fallback TTS run produces
    slides = []
    for i, r in enumerate(rates, 1):
        af = f"audio/{i:02d}.wav"
        _common.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=4",
                     "-ar", str(r), "-ac", "1", os.path.join(out, af)])
        s = sb.new_scene(i, "title", {"title": f"Scene {i}", "subtitle": "x"}, narration="x")
        s["audio"] = af
        s["duration"] = 4.0
        slides.append(s)
    data = sb.new_storyboard({"voice": "say:Samantha", "captions": False})
    data["slides"] = slides
    sb.validate(data)
    sb.save(data, os.path.join(out, "storyboard.json"))
    mp4 = render.render(out)
    probe = lambda st: float(_common.run(["ffprobe", "-v", "error", "-select_streams", st,
        "-show_entries", "stream=duration", "-of", "default=nw=1:nk=1", mp4]).strip())
    vdur, adur = probe("v:0"), probe("a:0")
    assert abs(vdur - adur) < 0.3, f"A/V drift: video {vdur:.2f}s vs audio {adur:.2f}s"


# ── C3: timed callouts (appear when their region is spoken) ───────────────────────────
def test_callout_time_at_fraction():
    co = {"box": [0.1, 0.1, 0.3, 0.3], "at": 0.5}
    assert render._callout_time({"index": 1}, {}, co, 10.0, "/nonexistent") == 5.0

def test_callout_time_cue_estimated_from_text():
    slide = {"index": 1, "narration": "First the left side. Then the crucial region on the right."}
    co = {"box": [0.5, 0.1, 0.9, 0.5], "cue": "crucial region"}
    t = render._callout_time(slide, {}, co, 10.0, "/nonexistent")
    assert 3.0 < t < 10.0                              # lands in the latter part, when spoken

def test_callout_time_untimed_is_zero():
    slide = {"index": 1, "narration": "Anything at all."}
    assert render._callout_time(slide, {}, {"box": [0, 0, 1, 1]}, 10.0, "/nonexistent") == 0.0


# ── D: reduced-motion tier — static Ken Burns ────────────────────────────────────────
def test_motion_exprs_static_under_reduced_motion():
    m = {"from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]}
    z, x, y = render._motion_exprs(m, 100, reduced_motion=True)
    assert z == "1.0+(1.0-1.0)*on/100"                        # to==from -> constant zoom (no move)
    assert x == "0.5+(0.5-0.5)*on/100" and y == "0.5+(0.5-0.5)*on/100"

def test_motion_exprs_preserves_move_by_default():
    m = {"from": [0.5, 0.5, 1.0], "to": [0.4, 0.5, 1.12]}
    z, x, _ = render._motion_exprs(m, 100, reduced_motion=False)
    assert "1.12" in z and "0.4" in x                         # the real Ken Burns move is kept (amp=1.0)


def test_intensity_amp_dial():
    assert render._intensity_amp({}) == 1.0                                   # default balanced
    assert render._intensity_amp({"intensity": "subtle"}) < 1.0
    assert render._intensity_amp({"intensity": "bold"}) > 1.0
    assert render._intensity_amp({"intensity": "1.3"}) == 1.3                 # raw multiplier accepted
    assert render._intensity_amp({"intensity": "balanced"}, {"intensity": "bold"}) > 1.0  # per-scene overrides


def test_motion_exprs_amp_scales_move_but_keeps_start():
    # authored delta 0.10 leaves headroom under the 0.20 cap, so amp is visible un-clamped
    m = {"from": [0.5, 0.5, 1.0], "to": [0.4, 0.5, 1.10]}
    zb, xb, _ = render._motion_exprs(m, 100, amp=render._intensity_amp({"intensity": "bold"}))
    zs, xs, _ = render._motion_exprs(m, 100, amp=render._intensity_amp({"intensity": "subtle"}))
    assert "1.0+(" in zb and "1.0+(" in zs                                    # same start anchor
    import re
    bz = float(re.search(r"1\.0\+\(([\d.]+)-1\.0\)", zb).group(1))
    sz = float(re.search(r"1\.0\+\(([\d.]+)-1\.0\)", zs).group(1))
    assert bz > 1.10 > sz > 1.0                                               # bold amplifies, subtle damps
    # reduced motion still overrides everything to static regardless of amp
    zr, _, _ = render._motion_exprs(m, 100, reduced_motion=True, amp=2.0)
    assert zr == "1.0+(1.0-1.0)*on/100"

def test_motion_exprs_amp_clamped_to_caps():
    # authored move sits EXACTLY at the caps (delta 0.20, ends 1.20); a bold amp (×1.5) would push
    # the effective zoom to 1.30 (delta 0.30, abs 1.30) — the lurch/soft-text the validate gate forbids.
    m = {"from": [0.9, 0.5, 1.0], "to": [0.1, 0.5, 1.20]}
    z, x, y = render._motion_exprs(m, 100, amp=render._intensity_amp({"intensity": "bold"}))
    import re
    z1 = float(re.search(r"1\.0\+\(([\d.]+)-1\.0\)", z).group(1))
    assert z1 <= render._MAX_ZOOM_ABS + 1e-9                                  # abs zoom capped at 1.25
    assert (z1 - 1.0) <= render._MAX_ZOOM_DELTA + 1e-9                        # delta capped at 0.20
    # a huge raw multiplier can't pan the anchor off-canvas either
    _, x2, _ = render._motion_exprs(m, 100, amp=render._intensity_amp({"intensity": "9"}))
    tx = float(re.search(r"0\.9\+\(([-\d.]+)-0\.9\)", x2).group(1))
    assert 0.0 <= tx <= 1.0

def test_reduced_motion_in_fingerprint():
    slide = {"index": 1, "type": "html", "props": {"html": "pages/scene_01.html"}}
    base = {"_out": "/x"}
    a = render._fingerprint(slide, {**base}, 1920, 1080, 2, True, False)
    b = render._fingerprint(slide, {**base, "reduced_motion": True}, 1920, 1080, 2, True, False)
    assert a != b                                             # flag busts the clip cache


def test_fingerprint_words_gate_covers_cue_callouts(tmp_path):
    # a slide whose timed callout resolves against words.json must bust when words.json changes
    import os
    os.makedirs(tmp_path / "audio", exist_ok=True)
    slide = {"index": 1, "type": "slide", "image": None,
             "callouts": [{"box": [0, 0, 1, 1], "style": "highlight", "cue": "x"}]}
    meta = {"_out": str(tmp_path)}
    a = render._fingerprint(slide, meta, 1920, 1080, 2, True, False)
    (tmp_path / "audio" / "01.words.json").write_text("[]")
    b = render._fingerprint(slide, meta, 1920, 1080, 2, True, False)
    assert a != b                                                # words.json now in the key
    plain = {"index": 1, "type": "slide", "image": None, "callouts": []}
    c = render._fingerprint(plain, meta, 1920, 1080, 2, True, False)
    (tmp_path / "audio" / "01.words.json").write_text('[{"w":"x","t":0}]')
    d = render._fingerprint(plain, meta, 1920, 1080, 2, True, False)
    assert c == d                                                # cue-less slide: TTS re-run doesn't bust


# ── semantic per-scene transitions (relation → dip/in/out/none) ───────────────────────
def test_fade_filter_slide_overrides_meta():
    m = {"transition": "dip", "transition_seconds": 0.2, "_out": "/nonexistent"}
    assert render._fade_filter(m, 10.0, {"transition": "none"}) == ""
    both = render._fade_filter(m, 10.0, {})
    assert "t=in" in both and "t=out" in both                     # meta default: both edges
    fin = render._fade_filter(m, 10.0, {"transition": "in"})
    assert "t=in" in fin and "t=out" not in fin                   # seam-opener: in-edge only
    fout = render._fade_filter(m, 10.0, {"transition": "out"})
    assert "t=out" in fout and "t=in" not in fout                 # section-ender: out-edge only

def test_fade_filter_slide_seconds_override():
    m = {"transition": "dip", "transition_seconds": 0.2, "_out": "/nonexistent"}
    s = render._fade_filter(m, 10.0, {"transition": "in", "transition_seconds": 0.3})
    assert "d=0.3" in s                                           # payoff: longer breath

def test_fingerprint_includes_scene_transition():
    slide = {"index": 1, "type": "html", "props": {"html": "pages/scene_01.html"}}
    meta = {"_out": "/x"}
    a = render._fingerprint(slide, meta, 1920, 1080, 2, True, False)
    b = render._fingerprint({**slide, "transition": "none"}, meta, 1920, 1080, 2, True, False)
    c = render._fingerprint({**slide, "transition_seconds": 0.4}, meta, 1920, 1080, 2, True, False)
    assert a != b and a != c and b != c                           # per-scene fields bust the cache


def test_fade_filter_unknown_value_falls_back_to_meta():
    m = {"transition": "dip", "transition_seconds": 0.2, "_out": "/nonexistent"}
    s = render._fade_filter(m, 10.0, {"transition": "wipe"})     # unknown -> meta default (dip)
    assert "t=in" in s and "t=out" in s


def test_caption_font_scales_with_narrow_dimension():
    # same visual weight in both aspects: 48px on 1920x1080 AND on 1080x1920
    assert render._caption_font_px(1920, 1080) == 48
    assert render._caption_font_px(1080, 1920) == 48          # was 86 when H-relative (band ate the layout)


def test_caption_not_split_at_abbreviations():
    # "Dr."/"Mr."/"e.g."/"U.S." must not fragment into tiny captions; real sentence ends still split
    segs = render._segment("Dr. Smith and Mr. Jones ran the trial. It worked.",
                           render._CJK_ENDERS, render._LATIN_ENDERS)
    assert segs == ["Dr. Smith and Mr. Jones ran the trial.", "It worked."]
    # decimals / multipliers stay intact too
    segs2 = render._segment("It grew 3.2x, e.g. a lot. Then more.", render._CJK_ENDERS, render._LATIN_ENDERS)
    assert segs2 == ["It grew 3.2x, e.g. a lot.", "Then more."]


def test_legacy_object_transition_honored():
    # a design-plan {in,out,seconds} object must produce the SAME fade as the flat form, not silently
    # degrade to the meta default (which nullified the whole per-scene rhythm subsystem)
    meta = {"transition": "dip", "transition_seconds": 0.2, "_out": "."}
    obj = render._fade_filter(meta, 6.0, {"transition": {"in": "in", "out": "none"}, "transition_seconds": 0.4})
    flat = render._fade_filter(meta, 6.0, {"transition": "in", "transition_seconds": 0.4})
    assert obj == flat and "fade=t=in" in obj and "fade=t=out" not in obj


def test_long_clause_hard_wraps_no_wall_of_text():
    # a long sentence with NO comma/clause mark must break into <=limit chunks, not one 4-line wall
    long1 = ("The reconstruction pipeline transforms undersampled k-space measurements into a fully "
             "sampled clinically usable diagnostic magnetic resonance image without any artifacts")
    chunks = render._split_caption_chunks(long1)
    assert len(chunks) >= 2 and all(len(c) <= 84 for c in chunks)


def test_mixed_cjk_caption_not_tripled():
    # one CJK term in an English sentence must NOT collapse the whole line to the CJK-tight limit
    eng = "The k空间 measurements feed the reconstruction network and it outputs a clean image quickly"
    assert len(render._split_caption_chunks(eng)) <= 2

def test_single_edge_fade_renders_on_short_scene():
    # an 'in'/'out' seam only needs ~1*d headroom, not the dip's 2*d — so it isn't suppressed
    meta = {"transition": "dip", "transition_seconds": 0.3, "_out": "."}
    assert "fade=t=in" in render._fade_filter(meta, 1.0, {"transition": "in", "transition_seconds": 0.3})


# ── caption placement: overlay (default) vs a band BELOW the content (meta.caption_mode) ──────────────
def test_theme_var_hex_and_rgb(tmp_path):
    (tmp_path / "theme.css").write_text(":root{--bg:#f4f3ee;--fg:#161412;--accent:#e2231a}")
    assert render._theme_var_hex(str(tmp_path), "--bg", "x") == "f4f3ee"
    assert render._theme_var_hex(str(tmp_path), "--fg", "x") == "161412"
    assert render._theme_var_hex(str(tmp_path), "--nope", "fallback") == "fallback"
    assert render._theme_rgb(str(tmp_path), "--fg", (0, 0, 0)) == (0x16, 0x14, 0x12)
    assert render._theme_rgb(str(tmp_path), "--accent", (0, 0, 0)) == (0xe2, 0x23, 0x1a)
    assert render._theme_rgb(str(tmp_path / "none"), "--fg", (1, 2, 3)) == (1, 2, 3)   # no file -> default


def test_caption_band_px_modes_and_parity():
    # band (flush) is the DEFAULT now — unset OR explicit band reserves a non-zero, EVEN strip
    # (yuv420p needs H+band even) in BOTH aspects; only explicit overlay (or captions off) reserves none.
    for meta in ({}, {"caption_mode": "band"}):
        b16 = render._caption_band_px(meta, 1920, 1080)
        b916 = render._caption_band_px(meta, 1080, 1920)
        assert b16 > 0 and b16 % 2 == 0, meta
        assert b916 > 0 and b916 % 2 == 0, meta
    # explicit overlay (or captions off) keeps the classic dims — no band
    assert render._caption_band_px({"caption_mode": "overlay"}, 1920, 1080) == 0
    assert render._caption_band_px({"captions": False}, 1920, 1080) == 0


def test_caption_layer_band_is_in_canvas_bottom_strip(tmp_path):
    from PIL import Image
    (tmp_path / "theme.css").write_text(":root{--bg:#ffffff;--fg:#101010}")
    band = render._caption_band_px({"caption_mode": "band"}, 1920, 1080)
    p = str(tmp_path / "band.png")
    render._caption_layer("A caption sitting in the bottom strip.", 1920, 1080, p,
                          {"_out": str(tmp_path)}, band=band)
    im = Image.open(p).convert("RGBA")
    assert im.size == (1920, 1080)                              # IN-canvas: the frame does NOT grow
    content = im.crop((0, 0, 1920, 1080 - band))               # above the strip stays fully transparent
    strip = im.crop((0, 1080 - band, 1920, 1080))              # the caption text lands in the bottom strip
    assert content.getchannel("A").getextrema()[1] == 0        # NOTHING drawn over the content above
    assert strip.getchannel("A").getextrema()[1] > 0           # caption drawn in the in-canvas strip


def test_caption_overlay_default_unchanged(tmp_path):
    # regression guard: band=0 (default) still draws the classic scrim bar over the bottom of the content
    from PIL import Image
    p = str(tmp_path / "ov.png")
    render._caption_layer("Classic burned-in caption.", 1920, 1080, p, {}, band=0)
    im = Image.open(p).convert("RGBA")
    assert im.size == (1920, 1080)                              # no extra canvas in overlay mode
    assert im.crop((0, int(1080 * 0.8), 1920, 1080)).getchannel("A").getextrema()[1] > 0


def test_caption_band_fill_samples_scene_ground(tmp_path):
    # flush band continues THIS scene's own bottom colour: a red accent-fill frame -> red strip + light
    # text; an off-white frame -> off-white strip + ink text; contrast -> dark bar; no frame -> flat --bg.
    from PIL import Image
    (tmp_path / "theme.css").write_text(":root{--bg:#f4f3ee;--fg:#161412}")
    meta = {"_out": str(tmp_path)}
    red = str(tmp_path / "red.png"); Image.new("RGB", (200, 120), (0xe2, 0x23, 0x1a)).save(red)
    bg, text = render._caption_band_fill(meta, red)
    assert bg == "0xe2231a" and text == (0xf4, 0xf3, 0xee)      # strip matches red; text flips to light --bg
    ow = str(tmp_path / "ow.png"); Image.new("RGB", (200, 120), (0xf4, 0xf3, 0xee)).save(ow)
    bg2, text2 = render._caption_band_fill(meta, ow)
    assert bg2 == "0xf4f3ee" and text2 == (0x16, 0x14, 0x12)    # off-white strip + ink text
    assert render._caption_band_fill({**meta, "caption_band": "contrast"}, red)[0] == "0x161412"  # dark bar
    assert render._caption_band_fill(meta, None)[0] == "0xf4f3ee"                                  # flat fallback
    # a saturated MID-tone ground (teal accent-fill) stays legible (>=3:1) and never picks the worse colour
    teal = str(tmp_path / "teal.png"); Image.new("RGB", (80, 40), (42, 161, 152)).save(teal)
    _, tt = render._caption_band_fill(meta, teal)
    lt = render._rel_lum(teal_rgb := (42, 161, 152)); lx = render._rel_lum(tt)
    assert (max(lt, lx) + 0.05) / (min(lt, lx) + 0.05) >= 3.0
    # a pure-black contain-fit LETTERBOX bar must NOT become a black strip -> fall back to the --bg fill
    blk = str(tmp_path / "blk.png"); Image.new("RGB", (80, 40), (0, 0, 0)).save(blk)
    assert render._caption_band_fill(meta, blk)[0] == "0xf4f3ee"


def test_caption_band_bg_is_video_bg_margin_sampled_and_snapped(tmp_path):
    # the strip must be the SAME background as the video. (1) _snap_to_theme_bg pins a sampled ground to
    # the EXACT theme var (the video background) and keeps a far colour as-is. (2) the strip samples the
    # MARGINS, so centered content reaching the bottom can't tint it.
    from PIL import Image, ImageDraw
    (tmp_path / "theme.css").write_text(":root{--bg:#f5f1e8;--fg:#141414;--accent2:#0f766e}")
    out = str(tmp_path)
    assert render._snap_to_theme_bg((244, 240, 231), out) == (245, 241, 232)   # near --bg  -> exact --bg
    assert render._snap_to_theme_bg((16, 120, 116), out) == (15, 118, 110)     # near --accent2 -> exact
    assert render._snap_to_theme_bg((200, 10, 10), out) == (200, 10, 10)       # far -> kept as sampled
    W, H, band = 1080, 300, 164                                  # cream frame; a teal card fills the CENTRE
    im = Image.new("RGB", (W, H), (245, 241, 232))              # of the bottom band region, margins stay ground
    ImageDraw.Draw(im).rectangle([230, H - band - 8, W - 230, H], fill=(15, 118, 110))
    fp = str(tmp_path / "f.png"); im.save(fp)
    bg, _ = render._caption_band_fill({"_out": out}, fp, band)
    assert bg == "0xf5f1e8"                                      # sampled from margins (ground), NOT the card


def test_snap_to_theme_bg_keeps_ambiguous_blend_between_close_vars(tmp_path):
    # --bg and --surface only ~30 apart (the default dark theme): an EXACT bg/surface sample still
    # snaps (clear winner), but a sample blended toward the midpoint stays RAW rather than snapping to
    # the WRONG var — not snapping is always safe (the raw sample IS the ground). Guards cross-snap.
    (tmp_path / "theme.css").write_text(":root{--bg:#0d1117;--surface:#161b22;--fg:#e6edf3}")
    out = str(tmp_path)
    bgc, sur = (0x0d, 0x11, 0x17), (0x16, 0x1b, 0x22)
    assert render._snap_to_theme_bg(bgc, out) == bgc            # exact --bg  -> snaps to --bg
    assert render._snap_to_theme_bg(sur, out) == sur           # exact --surface -> snaps to --surface
    mid = tuple((bgc[k] + sur[k]) // 2 for k in range(3))       # ambiguous blend near the midpoint
    assert render._snap_to_theme_bg(mid, out) == mid           # kept RAW, NOT snapped to the wrong var
    near = (bgc[0] + 2, bgc[1] - 1, bgc[2] + 1)                 # clearly nearest --bg (noise) -> still snaps
    assert render._snap_to_theme_bg(near, out) == bgc


def test_fingerprint_includes_caption_placement():
    # caption_mode/band/scale change the CLIP HEIGHT -> must bust the cache or a partial re-render mixes
    # clip resolutions and the `-c copy` concat breaks.
    meta = {"_out": "/x", "fps": 30}
    base = {"index": 1, "type": "html", "props": {"html": "p.html"}, "image": None, "audio": None,
            "duration": 3.0, "motion": {}, "narration": "n", "captions": [], "callouts": [], "fit": None}
    fp = lambda m: render._fingerprint(base, m, 1920, 1080, 2, True, False)
    assert fp(meta) != fp({**meta, "caption_mode": "band"})
    assert fp({**meta, "caption_mode": "band"}) != fp({**meta, "caption_mode": "band", "caption_band": "contrast"})
    assert fp(meta) != fp({**meta, "caption_scale": 0.9})


def test_theme_rgb_ignores_invalid_hex(tmp_path):
    # a 4- or 5-digit CSS hex is invalid — must return the default, not crash or corrupt into a bad colour
    (tmp_path / "theme.css").write_text(":root{--bg:#abcd;--fg:#12345;--accent:#0e7c86}")
    assert render._theme_rgb(str(tmp_path), "--bg", (9, 9, 9)) == (9, 9, 9)
    assert render._theme_rgb(str(tmp_path), "--fg", (8, 8, 8)) == (8, 8, 8)
    assert render._theme_rgb(str(tmp_path), "--accent", (0, 0, 0)) == (0x0e, 0x7c, 0x86)   # valid 6-digit still parses
    assert render._theme_var_hex(str(tmp_path), "--bg", "ffffff") == "ffffff"              # ignored -> default


def test_caption_band_px_off_when_captions_disabled():
    # captions OFF must add NO strip even in band mode (else a captionless video gets a blank bar)
    assert render._caption_band_px({"caption_mode": "band", "captions": False}, 1920, 1080) == 0
    assert render._caption_band_px({"caption_mode": "band"}, 1920, 1080) > 0                # captions default-on


def test_caption_band_fill_contrast_floor(tmp_path):
    # a degenerate theme (both --fg and --bg mid-tone) + a mid-tone strip: neither theme colour clears the
    # ~3:1 AA-large floor, so the text must fall back to pure black/white to stay legible.
    from PIL import Image
    (tmp_path / "theme.css").write_text(":root{--bg:#808080;--fg:#8a8a8a}")
    p = str(tmp_path / "mid.png"); Image.new("RGB", (80, 40), (130, 130, 130)).save(p)
    _, text = render._caption_band_fill({"_out": str(tmp_path)}, p)
    assert text in ((0, 0, 0), (255, 255, 255))
    lum = render._rel_lum((130, 130, 130))
    tl = render._rel_lum(text)
    assert (max(tl, lum) + 0.05) / (min(tl, lum) + 0.05) >= 3.0                             # legible on the strip


@pytest.mark.skipif(not _common.have_tool("ffmpeg") or not _common.have_tool("say"),
                    reason="needs ffmpeg + say")
def test_caption_band_render_keeps_canvas_dims(tmp_path, monkeypatch):
    """End-to-end: a `caption_mode:band` deck renders the IN-canvas flush strip WITHOUT growing the frame
    (stays exactly W×H — a true 16:9 / 9:16), exercising BOTH encode paths — a `title` scene
    (_encode_frames_clip) AND an image `slide` (_render_slide) — so the drawbox strip fill is general
    across tiers and the clips still concat (uniform dims)."""
    from PIL import Image
    monkeypatch.setattr(tts, "_have_edge", lambda: False)      # offline-deterministic audio
    out = str(tmp_path / "proj"); os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    Image.new("RGB", (1920, 1080), (30, 30, 30)).save(os.path.join(out, "frames", "01.png"))
    (tmp_path / "proj" / "theme.css").write_text(":root{--bg:#ffffff;--fg:#111111}")
    title = sb.new_scene(99, "title", {"title": "Title", "subtitle": "Sub"}, narration="Welcome in.")
    img = sb.new_slide(1, "frames/01.png", narration="This is a content slide.")
    data = sb.new_storyboard({"voice": "say:Samantha", "caption_mode": "band"})
    data["slides"] = [title, img]
    sb.save(data, os.path.join(out, "storyboard.json"))
    tts.synthesize(out)
    mp4 = render.render(out)
    band = render._caption_band_px({"caption_mode": "band"}, 1920, 1080)
    probe = lambda st: _common.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", f"stream={st}", "-of", "default=nk=1:nw=1", mp4]).strip()
    assert band > 0                                            # band IS reserved (default flush mode)
    assert int(probe("width")) == 1920 and int(probe("height")) == 1080   # IN-canvas: NO growth
    assert _common.audio_duration(mp4) > 0.3                    # clips concatenated + play


@pytest.mark.skipif(not _common.have_tool("ffmpeg") or not _common.have_tool("say"),
                    reason="needs ffmpeg + say")
def test_caption_band_fill_color_not_range_shifted(tmp_path, monkeypatch):
    """Regression: the flush strip must be the EXACT sampled/snapped colour, NOT a range-shifted one.
    drawbox draws its fill in the frame's working space; on the yuv420p pipeline it range-converts the
    colour (full->limited: a light #f5f1e8 245,241,232 would land ~226,224,214) while the full-range
    CONTENT is untouched — so the strip would visibly differ from the scene ground. `format=rgb24`
    before drawbox keeps the fill exact. Render a solid light slide and assert the band matches it."""
    from PIL import Image
    monkeypatch.setattr(tts, "_have_edge", lambda: False)
    out = str(tmp_path / "proj"); os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    Image.new("RGB", (1920, 1080), (245, 241, 232)).save(os.path.join(out, "frames", "01.png"))
    (tmp_path / "proj" / "theme.css").write_text(":root{--bg:#f5f1e8;--fg:#161412}")
    img = sb.new_slide(1, "frames/01.png", narration="A light content slide for the band colour check.")
    data = sb.new_storyboard({"voice": "say:Samantha", "caption_mode": "band"})
    data["slides"] = [img]
    sb.save(data, os.path.join(out, "storyboard.json"))
    tts.synthesize(out)
    mp4 = render.render(out)
    band = render._caption_band_px({"caption_mode": "band"}, 1920, 1080)
    frame = str(tmp_path / "f.png")
    _common.run(["ffmpeg", "-v", "error", "-i", mp4, "-ss", "0.5", "-frames:v", "1", frame, "-y"])
    im = Image.open(frame).convert("RGB")
    # band FILL sampled at a text-free edge (bottom-left of the strip), NOT the centered caption text
    fill = sorted(im.crop((0, 1080 - band + 8, 40, 1078)).getdata())[(40 * (band - 10)) // 2]
    # exact colour (±8 for yuv rounding); a range-shifted strip (~226) would be >15 off and FAIL
    assert all(abs(fill[k] - g) <= 8 for k, g in enumerate((245, 241, 232))), f"band fill {fill} range-shifted"
