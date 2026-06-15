import os, json, pytest
import ingest, tts, render, storyboard as sb, _common

def _build(tmp_path, fixtures_dir):
    out = str(tmp_path / "proj")
    ingest.ingest(os.path.join(fixtures_dir, "deck.pdf"), out)
    data = sb.load(os.path.join(out, "storyboard.json"))
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
