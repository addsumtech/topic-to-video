"""film_frames: renders every frame (never skips a stale one), and its probe catches a page-dependent frame."""
import os
import subprocess
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "film_frames.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:  # no Chrome on this machine
    CHROME = None

PAGE = """<!doctype html><html><body style="margin:0;background:#000"><canvas id="c" width="1920" height="1080"></canvas>
<script>
const g = document.getElementById('c').getContext('2d');
window.filmReady = Promise.resolve(%(ready)s);
window.seek = (t) => { g.fillStyle = '#102030'; g.fillRect(0, 0, 1920, 1080);
  g.fillStyle = %(fill)s; g.fillRect(200 + t * 600, 300, 400, 300); };
</script></body></html>"""


def _film(tmp_path, fill="'#ff8800'", ready="'ok'", seconds=0.2):
    (tmp_path / "film.html").write_text(PAGE % {"fill": fill, "ready": ready})
    (tmp_path / "timeline.json").write_text('{"duration": %s}' % seconds)
    return tmp_path


def _run(d, *extra):
    return subprocess.run([sys.executable, SCRIPT, str(d), "--workers", "2", *extra], capture_output=True, text=True,
                          timeout=300)


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_renders_every_frame_and_replaces_a_stale_one(tmp_path):
    d = _film(tmp_path)
    out = d / "work" / "frames"
    out.mkdir(parents=True)
    (out / "f_00002.jpg").write_bytes(b"stale")                   # a leftover from an earlier render
    r = _run(d, "--probe", "2")
    assert r.returncode == 0, r.stdout + r.stderr
    files = sorted(p.name for p in out.glob("f_*.jpg"))
    assert files == ["f_%05d.jpg" % i for i in range(6)], files
    im = Image.open(out / "f_00002.jpg").convert("RGB")          # replaced by a real render, not skipped
    assert im.size == (1920, 1080)
    x = int(200 + 2 / 30 * 600) + 200
    assert im.getpixel((x, 450))[0] > 200, "frame 2 is not the frame-2 picture"
    assert "probe OK" in r.stdout


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_probe_fails_a_frame_that_depends_on_the_page(tmp_path):
    # Math.random: each page draws a different colour at the same t (what a font loaded late does to canvas text)
    d = _film(tmp_path, fill="'hsl(' + Math.floor(Math.random() * 360) + ',90%,50%)'")
    r = _run(d, "--probe", "2")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PAGE-DEPENDENT" in r.stdout
    assert list((d / "work" / "frames" / "_probe").glob("a_*.png")), "the differing pictures are kept to compare"


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_a_failed_film_ready_stops_loudly(tmp_path):
    d = _film(tmp_path, ready="'ERR the cast did not load'")
    r = _run(d, "--probe", "0")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "filmReady failed" in r.stderr and "cast did not load" in r.stderr


def test_usage_errors(tmp_path):
    r = subprocess.run([sys.executable, SCRIPT, str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 2 and "no page" in r.stderr
    (tmp_path / "film.html").write_text("<html></html>")
    r = subprocess.run([sys.executable, SCRIPT, str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 2 and "no frame count" in r.stderr


FONT_PAGE = """<!doctype html><html><head><style>@font-face { font-family: "TestF"; src: url(f.ttf); }</style></head>
<body style="margin:0"><canvas id="c" width="1920" height="1080"></canvas><script>
const c = document.getElementById('c'), g = c.getContext('2d');
const label = () => { g.fillStyle = '#fff'; g.font = '700 70px TestF, sans-serif'; g.fillText('Pipeline \\u2192 drafts', 60, 100); };
%(early)s
window.filmReady = (async () => { await document.fonts.load('700 70px TestF'); %(late)s return 'ok'; })();
window.seek = (t) => {};
</script></body></html>"""


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
@pytest.mark.parametrize("when,ok", [("early", False), ("late", True)])
def test_canvas_text_drawn_before_its_font_loaded_is_refused(tmp_path, when, ok):
    # the Grok Bot arrow: text drawn at script load took the web font in one render page and a fallback in another
    import shutil
    shutil.copy(os.path.join(ROOT, "assets", "fonts", "DejaVuSans.ttf"), tmp_path / "f.ttf")
    (tmp_path / "film.html").write_text(FONT_PAGE % {"early": "label();" if when == "early" else "",
                                                       "late": "label();" if when == "late" else ""})
    (tmp_path / "timeline.json").write_text('{"duration": 0.1}')
    r = _run(tmp_path, "--probe", "0")
    if ok:
        assert r.returncode == 0, r.stdout + r.stderr
    else:
        assert r.returncode == 2 and "before its font loaded" in r.stderr and "Pipeline" in r.stderr, r.stdout + r.stderr
