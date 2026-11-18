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
