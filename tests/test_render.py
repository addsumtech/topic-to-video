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
