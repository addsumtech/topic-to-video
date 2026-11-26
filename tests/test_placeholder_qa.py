"""placeholder_qa: a screen of empty bars or blocks reads as a screen with nothing on it (a Grok Bot promo, 2026-11-26)."""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "placeholder_qa.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402
import placeholder_qa as pq  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None

W, H = 1000, 700
PAGE = [0, 0, W, H, "#fff"]


def test_empty_text_line_bars_are_a_placeholder_and_the_same_bars_with_words_are_not():
    bars = [[40, 100 + 40 * i, 300 - 20 * i, 12, "#ddd"] for i in range(4)]
    assert len(pq.judge(W, H, [PAGE] + bars, [])[0]) == 4
    words = [[b[0] + 4, b[1] - 2, 100, 14] for b in bars]               # each pill carries its label
    assert pq.judge(W, H, [PAGE] + bars, words) == ([], [])


def test_two_bars_a_hairline_rule_and_an_invisible_shape_do_not_count():
    two = [[40, 100, 300, 12, "#ddd"], [40, 140, 200, 12, "#ddd"]]
    rules = [[0, 100 + 40 * i, W * 0.8, 1, "#eee"] for i in range(6)]   # dividers: thinner than any line of text
    white = [[40, 300 + 40 * i, 300, 12, "#fff"] for i in range(4)]     # the page's own colour on the page: not seen
    assert pq.judge(W, H, [PAGE] + two + rules + white, []) == ([], [])


def test_empty_blocks_of_one_colour_are_a_placeholder_but_a_bar_charts_bars_are_not():
    cal = [[100 + 150 * d, 120 + 60 * d, 130, 90, "rgba(21,132,255,0.22)"] for d in range(4)]
    assert len(pq.judge(W, H, [PAGE] + cal, [])[1]) == 4
    chart = [[100 + 90 * i, 600 - h, 60, h, "#d6d9de"] for i, h in enumerate((120, 200, 160, 260))]
    assert pq.judge(W, H, [PAGE] + chart, []) == ([], [])
    icons = [[100 + 40 * i, 100, 12, 10, "#5aa7f2"] for i in range(5)]   # icons: too small to hold a word
    assert pq.judge(W, H, [PAGE] + icons, []) == ([], [])


def test_a_container_is_not_judged_as_a_block():
    cards = [[20 + 330 * i, 20, 310, 660, "#f4f4f6"] for i in range(3)]  # three columns, each a big share of the screen
    assert pq.judge(W, H, [PAGE] + cards, [[40 + 330 * i, 40, 100, 14] for i in range(3)]) == ([], [])


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_on_a_page_a_canvas_of_bars_and_an_html_screen_of_empty_rows_are_red_the_real_ones_pass(tmp_path):
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), tmp_path / "stage3d.js")
    (tmp_path / "timeline.json").write_text('{"duration": 1.0}')
    (tmp_path / "film.html").write_text("""<!doctype html><html><body style="margin:0;background:#fff">
<canvas id="bars" width="600" height="400" style="position:absolute;left:0;top:0"></canvas>
<canvas id="words" width="600" height="400" style="position:absolute;left:620px;top:0"></canvas>
<canvas id="rows" width="390" height="300" style="position:absolute;left:0;top:420px"></canvas>
<canvas id="meant" width="600" height="400" data-placeholder-ok="a loading state the product really shows"
        style="position:absolute;left:620px;top:420px"></canvas>
<script src="stage3d.js"></script>
<script>
const pill = (g, x, y, w, h) => { g.beginPath(); g.roundRect(x, y, w, h, h / 2); g.fill(); };
for (const id of ['bars', 'words', 'meant']) { const g = document.getElementById(id).getContext('2d');
  g.fillStyle = '#fff'; g.fillRect(0, 0, 600, 400);
  for (let i = 0; i < 5; i++) { g.fillStyle = '#dcdde0'; g.save(); g.translate(30, 40 + i * 50);
    if (id === 'words') { g.fillStyle = '#333'; g.font = '16px sans-serif'; g.textBaseline = 'top'; g.fillText('Invoice from Acme ' + i, 0, 0); }
    else pill(g, 0, 0, 300 - i * 30, 14);
    g.restore(); } }
window.filmReady = Stage3D.screen(document.getElementById('rows'),
  '<div>' + [0, 1, 2, 3].map((i) => '<div style="height:12px;width:' + (200 - i * 20) + 'px;margin:20px;background:#ddd;border-radius:6px"></div>').join('') + '</div>',
  {size: [390, 300], name: 'empty-rows'}).then(() => 'ok');
window.seek = () => {};
</script></body></html>""")
    r = subprocess.run([sys.executable, SCRIPT, str(tmp_path), "--json"], capture_output=True, text=True, timeout=300)
    assert r.returncode == 1, r.stdout + r.stderr
    j = json.loads(r.stdout)
    assert sorted(j["placeholders"]) == ["#bars", "#rows"], j             # the canvas of words passes
    assert list(j["ok"]) == ["#meant"] and not j["ok_without_reason"], j


def test_one_size_repeated_many_times_is_a_pattern_not_a_placeholder():
    qr = [[40 + 30 * (i % 7), 40 + 30 * (i // 7), 24, 24, "#000"] for i in range(30)]   # a QR code's modules
    assert pq.judge(W, H, [PAGE] + qr, []) == ([], [])


def test_bands_across_the_whole_screen_are_highlights_not_lines_of_text():
    bands = [[0, 100 + 60 * i, W, 30, "rgba(255,54,163,0.3)"] for i in range(5)]
    assert pq.judge(W, H, [PAGE] + bands, []) == ([], [])


def test_a_qr_codes_finder_squares_and_touching_modules_are_a_drawing_not_empty_blocks():
    finders = []
    for x, y in ((40, 40), (500, 40), (40, 400)):
        finders += [[x, y, 210, 210, "#000"], [x + 30, y + 30, 150, 150, "#fff"], [x + 60, y + 60, 90, 90, "#000"]]
    modules = [[300 + 30 * i, 300, 30, 30, "#000"] for i in range(5)] + [[300, 330, 30, 30, "#000"]]
    assert pq.judge(W, H, [PAGE] + finders + modules, []) == ([], [])
