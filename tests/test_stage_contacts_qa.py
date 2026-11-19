"""stage_contacts_qa: a card inside a character's body, or two cards in one plane overlapping, is a contact; a card
floating in front of a character, or objects parked out of view, are not."""
import json
import os
import shutil
import subprocess
import sys

import pytest
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "stage_contacts_qa.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None

PAGE = """<!doctype html><html><body style="margin:0;background:#000"><canvas id="c" width="960" height="540"></canvas>
<canvas id="card" width="300" height="140" style="display:none"></canvas>
<script src="stage3d.js"></script><script>
const card = document.getElementById('card'); card.getContext('2d').fillRect(0, 0, 300, 140);
const st = Stage3D.create({canvas: document.getElementById('c'), toneMapping: 'neutral'}); st.studio({});
const bot = st.inflate('bot.png', {width: 1.2, x: 0, y: 0, z: 0});
const p1 = st.panel(card, {width: 0.8, depth: 0.04, bezel: 0, name: 'card1'});
const p2 = st.panel(card, {width: 0.8, depth: 0.04, bezel: 0, name: 'card2'});
window.filmReady = st.ready().then(() => 'ok');
window.seek = (t) => { const pose = %(pose)s; pose(); st.render({pos: [0, 0.7, 5], look: [0, 0.6, 0], fov: 40}); };
</script></body></html>"""

POSES = {
    # the card's centre inside the Bot's body (a carried card sunk into its head)
    "sunk": "() => { p1.position.set(0, 0.6, 0); p2.position.set(0, -50, 0); }",
    # the card in front of the Bot, clear of its front dome
    "in_front": "() => { p1.position.set(0, 0.6, 0.9); p2.position.set(0, -50, 0); }",
    # two cards in one plane, overlapping (three action cards parked at one end point)
    "stacked": "() => { p1.position.set(1.5, 0.6, 0.5); p2.position.set(1.62, 0.66, 0.5); }",
    # both parked far out of view at the same spot: not a contact
    "parked": "() => { p1.position.set(0, -50, 0); p2.position.set(0, -50, 0); }",
}


def _film(tmp_path, pose):
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), tmp_path)
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0)); ImageDraw.Draw(im).ellipse((20, 20, 180, 180), fill=(0, 184, 160, 255))
    im.save(tmp_path / "bot.png")
    (tmp_path / "film.html").write_text(PAGE % {"pose": POSES[pose]})
    (tmp_path / "timeline.json").write_text('{"duration": 0.3}')
    return tmp_path


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
@pytest.mark.parametrize("pose,kind", [("sunk", "penetrates"), ("in_front", None), ("stacked", "stacked"), ("parked", None)])
def test_contacts_are_judged_on_exact_bodies_in_view(tmp_path, pose, kind):
    d = _film(tmp_path, pose)
    r = subprocess.run([sys.executable, SCRIPT, str(d), "--json"], capture_output=True, text=True, timeout=300)
    assert r.returncode in (0, 1), r.stdout + r.stderr
    found = json.loads(r.stdout)["contacts"]
    if kind is None:
        assert r.returncode == 0 and not found, found
    else:
        assert r.returncode == 1 and {c["kind"] for c in found} == {kind}, found


SCREEN_PAGE = """<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#000"><canvas id="c" width="960" height="540"></canvas>
<script src="stage3d.js"></script><script>
const st = Stage3D.create({canvas: document.getElementById('c'), toneMapping: 'neutral'}); st.studio({});
const cv = document.createElement('canvas'); cv.width = 1600; cv.height = 500;
// a CV row: one line, line-height 1, as the job-hunt CV set its rows
const css = '.d{font:22px/1 "PingFang SC",Helvetica;padding:30px;background:#fff;color:#111;height:100%%;box-sizing:border-box;white-space:nowrap}';
const caret = %(caret)s;
const html = (on) => '<div class="d">搭建问答质量评估流程，定义事实准确性' + caret(on) + '、来源可靠性与回答可读性标准；使用 Python 与 API 批量处理样本。</div>';
let card = null, shown = null;
window.filmReady = (async () => { await Stage3D.screen(cv, html(true), {size: [800, 250], css, name: 'doc'});
  card = st.card(cv, {width: 2.4, radius: 0, name: 'doc'}); await st.ready(); return 'ok'; })();
window.seek = async (t) => { const on = Math.floor(t * 4) %% 2 === 0;
  if (on !== shown) { shown = on; await Stage3D.screen(cv, html(on), {size: [800, 250], css, name: 'doc'}); card.userData.refresh(); }
  st.render({pos: [0, 0, 3], look: [0, 0, 0], fov: 50}); };
</script></body></html>"""

CARETS = {
    # the job-hunt film's caret: an inline box taller than the text, added only while it shows
    "joins_the_line": "(on) => on ? '<span style=\"display:inline-block;width:0;height:1.12em;border-left:2.4px solid #111;vertical-align:-0.18em\"></span>' : ''",
    "kit": "(on) => Stage3D.caret(on, {color: '#111'})",
}


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
@pytest.mark.parametrize("caret,jitters", [("joins_the_line", True), ("kit", False)])
def test_a_line_that_jumps_with_a_blinking_caret_is_jitter(tmp_path, caret, jitters):
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), tmp_path)
    (tmp_path / "film.html").write_text(SCREEN_PAGE % {"caret": CARETS[caret]})
    (tmp_path / "timeline.json").write_text('{"duration": 2.2}')
    r = subprocess.run([sys.executable, SCRIPT, str(tmp_path), "--json"], capture_output=True, text=True, timeout=300)
    assert r.returncode in (0, 1), r.stdout + r.stderr
    kinds = [c["kind"] for c in json.loads(r.stdout)["contacts"]]
    assert ("screen-jitter" in kinds) is jitters, r.stdout


def test_jitter_needs_returns_not_one_move():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import stage_contacts_qa as q
    k = ("doc", "DIV0/DIV2/")
    seq = lambda ys, words=None: [(i / 15, {k: (10.0, y, (words or (lambda i: "line"))(i))}) for i, y in enumerate(ys)]
    assert q.jitters(seq([0, 0, 3, 3, 0, 0, 3, 3, 0, 0]), 1 / 15), "back and forth twice is jitter"
    assert not q.jitters(seq([0, 0, 0, 31, 31, 31, 31]), 1 / 15), "a row pushed down once by an inserted line is not"
    assert not q.jitters(seq([0, 0, 31, 31, 0, 0]), 1 / 15), "pushed down and back once (a line shown, then removed) is not"
    assert not q.jitters(seq([0, 0.1, 0, 0.1, 0]), 1 / 15), "sub-quarter-pixel noise is not"
    typed = lambda i: "云原生：熟悉 Kubernetes"[:3 + i]
    assert q.jitters(seq([0, 2, 0, 2, 0, 2], typed), 1 / 15), "a line being typed that jumps with its caret is jitter"
    other = lambda i: "row A" if i % 2 == 0 else "row B"
    assert not q.jitters(seq([0, 2, 0, 2, 0, 2], other), 1 / 15), "two different lines taking turns in one place are not one line moving"


PAGE_LABEL = """<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#000"><canvas id="c" width="960" height="540"></canvas>
<div id="lab" %(attr)s style="position:absolute;left:40px;top:40px;font:22px/1 Helvetica;color:#fff;white-space:nowrap"></div>
<script src="stage3d.js"></script><script>
const st = Stage3D.create({canvas: document.getElementById('c')}); st.studio({});
window.filmReady = st.ready().then(() => 'ok');
window.seek = (t) => { const on = Math.floor(t * 4) %% 2 === 0;
  document.getElementById('lab').innerHTML = 'Facts traced' + (on ? '<span style="display:inline-block;width:0;height:1.3em;border-left:2px solid #fff;vertical-align:-0.25em"></span>' : '') + ' to your CV';
  st.render({pos: [0, 1, 4], look: [0, 1, 0], fov: 40}); };
</script></body></html>"""


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
@pytest.mark.parametrize("attr,jitters", [("", True), ("data-motion-ok", False)])
def test_a_page_label_that_jumps_with_its_caret_is_jitter(tmp_path, attr, jitters):
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), tmp_path)
    (tmp_path / "film.html").write_text(PAGE_LABEL % {"attr": attr})
    (tmp_path / "timeline.json").write_text('{"duration": 2.2}')
    r = subprocess.run([sys.executable, SCRIPT, str(tmp_path), "--json"], capture_output=True, text=True, timeout=300)
    assert r.returncode in (0, 1), r.stdout + r.stderr
    kinds = [c["kind"] for c in json.loads(r.stdout)["contacts"]]
    assert ("page-jitter" in kinds) is jitters, r.stdout
