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
