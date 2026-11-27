"""animatic: the boards cut to the real voice clock — own boards first, then the hero keyframes, else a grey card that
says BOARD MISSING; --page captures the film's own page; the voice is laid at the timeline's line starts."""
import json
import os
import subprocess
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "animatic.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402
import animatic  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None


def _film(d):
    (d / "voice").mkdir()
    for name, freq in (("l01", 440), ("l02", 660)):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=%d:d=1.0" % freq,
                        str(d / "voice" / ("%s.mp3" % name))], check=True)
    (d / "timeline.json").write_text(json.dumps({"fps": 30, "duration": 3.0, "lines": [
        {"id": "l01", "text": "The first line.", "start": 0.2, "end": 1.2, "clip": "voice/l01.mp3", "trim": [0, 1.0]},
        {"id": "l02", "text": "The second line.", "start": 1.8, "end": 2.8, "clip": "voice/l02.mp3", "trim": [0, 1.0]}]}))
    (d / "shot_plan.json").write_text(json.dumps({"shots": [
        {"id": "s01", "start": 0, "end": 1.0, "technique": "open"},
        {"id": "s02", "start": 1.0, "end": 2.0, "technique": "the hero", "hero": True},
        {"id": "s03", "start": 2.0, "end": 3.0, "technique": "close"}],
        "objects_note": "a test film of plain colour cards: no recurring object",
        "physics_note": "colour cards: no physical process shown"}))
    (d / "design" / "keyframes").mkdir(parents=True)
    Image.new("RGB", (1920, 1080), (200, 40, 40)).save(d / "design" / "keyframes" / "kf1.png")     # red: the hero
    (d / "design" / "boards").mkdir()
    Image.new("RGB", (1920, 1080), (40, 40, 200)).save(d / "design" / "boards" / "s01.png")       # blue: own board
    (d / "design" / "treatment.md").write_text("**s03 · 2.0-3.0 · close.** The lockup holds.\n")
    return d


def _frame(video, t):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True, check=True)
    import io
    return Image.open(io.BytesIO(p.stdout)).convert("RGB")


def test_boards_in_priority_order_and_the_missing_one_named(tmp_path):
    d = _film(tmp_path)
    r = subprocess.run([sys.executable, SCRIPT, str(d), "--width", "640"], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert "1 BOARD MISSING: s03" in r.stdout, r.stdout
    out = d / "design" / "animatic.mp4"
    assert _frame(out, 0.5).getpixel((320, 150))[2] > 150, "s01 shows its own board (blue)"
    assert _frame(out, 1.5).getpixel((320, 150))[0] > 150, "the hero shot shows the hero keyframe (red)"
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True).stdout.split()
    assert probe == ["video", "audio"], probe


def test_the_voice_sits_on_the_timeline(tmp_path):
    d = _film(tmp_path)
    va = animatic._voice(str(d), json.load(open(d / "timeline.json"))["lines"], 3.0, str(tmp_path / "v.wav"))
    import numpy as np
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", va, "-ac", "1", "-ar", "8000", "-f", "f32le", "-"], capture_output=True)
    x = np.abs(np.frombuffer(p.stdout, np.float32))
    loud = lambda a, b: x[int(a * 8000):int(b * 8000)].mean()   # noqa: E731
    assert loud(0.4, 1.0) > 0.03 and loud(1.3, 1.7) < 0.005 and loud(2.0, 2.6) > 0.03, "lines at 0.2 s and 1.8 s, silence between"


def test_treatment_paragraphs_are_read_per_shot(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("**s01 · 0-4 · open.** The window at night.\nMore of it.\n\n**s02 · 4-9.** Day.\n")
    t = animatic.treatment_lines(str(p))
    assert t["s01"].endswith("The window at night. More of it.") and t["s02"].endswith("Day.")


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_page_mode_captures_the_films_own_frames(tmp_path):
    d = _film(tmp_path)
    for p in (d / "design" / "boards").glob("*"):
        p.unlink()
    for p in (d / "design" / "keyframes").glob("*"):
        p.unlink()
    (d / "film.html").write_text("""<!doctype html><html><body style="margin:0"><canvas id="c" width="1920" height="1080"></canvas>
<script>const g = document.getElementById('c').getContext('2d');
window.seek = (t) => { g.fillStyle = t < 1 ? '#00ff00' : '#ffff00'; g.fillRect(0, 0, 1920, 1080); };</script></body></html>""")
    r = subprocess.run([sys.executable, SCRIPT, str(d), "--width", "640", "--page", "film.html"], capture_output=True,
                       text=True, timeout=300)
    assert r.returncode == 0 and "0 BOARD MISSING" in r.stdout, r.stdout + r.stderr
    a, b = _frame(d / "design" / "animatic.mp4", 0.5), _frame(d / "design" / "animatic.mp4", 2.5)
    assert a.getpixel((320, 150))[1] > 200 and a.getpixel((320, 150))[0] < 80, "s01 drawn by the page (green)"
    assert b.getpixel((320, 150))[0] > 200 and b.getpixel((320, 150))[1] > 200, "s03 drawn by the page (yellow)"


def test_missing_inputs_are_refused(tmp_path):
    r = subprocess.run([sys.executable, SCRIPT, str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 2 and "needs shot_plan.json and timeline.json" in r.stderr


def test_wrap_fits_the_width_in_both_scripts_and_never_starts_a_line_with_closing_punctuation():
    f = animatic._font(36)
    zh = animatic.wrap("所以中午，你不看太阳，随便看哪一块天，看到的都是被分子弹开的蓝光，它们从四面八方来到你的眼睛里。", f, 600)
    en = animatic.wrap("They message each other, and pass the work along. You are not the router anymore.", f, 600)
    for lines in (zh, en):
        assert len(lines) >= 2 and all(f.getlength(l) <= 600 + f.getlength("，") for l in lines), lines
    assert not any(l[0] in "，。、；：！？" for l in zh), zh
    assert "".join(zh) == "所以中午，你不看太阳，随便看哪一块天，看到的都是被分子弹开的蓝光，它们从四面八方来到你的眼睛里。"


@pytest.mark.skipif(not CHROME, reason="needs Chrome")
def test_page_mode_draws_the_caption_at_its_home_and_a_shot_covering_the_home_is_red(tmp_path):
    # Apollo 2026-11-26: the animatic showed the line only under the picture, and the shots were re-framed for the
    # captions after approval. Now the caption is ON the picture at its home, and a shot parked on it fails here.
    d = _film(tmp_path)
    for p in list((d / "design" / "boards").glob("*")) + list((d / "design" / "keyframes").glob("*")):
        p.unlink()
    (d / "film.html").write_text("""<!doctype html><html><body style="margin:0"><canvas id="c" width="1920" height="1080"></canvas>
<script>const g = document.getElementById('c').getContext('2d');
window.seek = (t) => { g.fillStyle = '#20242a'; g.fillRect(0, 0, 1920, 1080);
  if (t >= 1.8) { g.fillStyle = '#e8944e'; g.fillRect(700, 980, 520, 70); } };</script></body></html>""")
    r = subprocess.run([sys.executable, SCRIPT, str(d), "--width", "640", "--page", "film.html"], capture_output=True,
                       text=True, timeout=300)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "CAPTION HOME  s03" in r.stdout and "CAPTION HOME  s01" not in r.stdout, r.stdout
    im = _frame(d / "design" / "animatic.mp4", 0.6)               # "The first line." burned at the home
    band = [im.getpixel((x, round(360 * 1012 / 1080))) for x in range(200, 440)]
    assert max(sum(p) for p in band) > 600, "white caption ink at the home"



def test_the_objects_are_listed_with_their_reference_and_model_or_the_animatic_is_red(tmp_path):
    # Titanic 2026-11-27: the hero ship was a box-built stand-in from blocking to build; nobody set it beside the ship
    d = _film(tmp_path)
    plan = json.loads((d / "shot_plan.json").read_text())
    plan.pop("objects_note")
    (d / "shot_plan.json").write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, SCRIPT, str(d)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 1 and "lists no `objects`" in r.stdout, r.stdout + r.stderr
    Image.new("RGB", (1200, 800), (30, 30, 30)).save(d / "design" / "ref.jpg")
    plan["objects"] = [{"name": "the ship", "reference": "design/ref.jpg", "render": "design/model.png"}]
    (d / "shot_plan.json").write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, SCRIPT, str(d)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 1 and "no render file" in r.stdout, r.stdout
    Image.new("RGB", (1920, 1080), (200, 200, 200)).save(d / "design" / "model.png")
    r = subprocess.run([sys.executable, SCRIPT, str(d)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and "design/objects.jpg" in r.stdout, r.stdout + r.stderr
    sheet = Image.open(d / "design" / "objects.jpg")
    assert sheet.size == (1920, 588)
    assert sheet.getpixel((480, 300))[0] < 60 and sheet.getpixel((1440, 300))[0] > 150, "reference left, model right"


def test_the_physics_the_film_shows_is_written_down_or_the_animatic_is_red(tmp_path):
    # Titanic 2026-11-27: the sea sprayed OUT of the hull and a boiler room was half full where the inquiry says water
    # was only coming up from under its floor: nobody had written down how the flooding behaves
    d = _film(tmp_path)
    plan = json.loads((d / "shot_plan.json").read_text())
    plan.pop("physics_note")
    (d / "shot_plan.json").write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, SCRIPT, str(d)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 1 and "lists no `physics`" in r.stdout, r.stdout + r.stderr
    plan["physics"] = [{"phenomenon": "flooding", "behaviour": "the sea flows in; levels never exceed the sea",
                        "shots": ["s02", "s09"]}]
    (d / "shot_plan.json").write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, SCRIPT, str(d)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 1 and "no basis" in r.stdout and "not in the plan: s09" in r.stdout, r.stdout
    plan["physics"][0].update(basis="gradeff#rose steadily", shots=["s02"])
    (d / "shot_plan.json").write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, SCRIPT, str(d)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and "physics: flooding (s02)" in r.stdout, r.stdout + r.stderr
