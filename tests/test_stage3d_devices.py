"""stage3d devices, cards, HTML screens and marks (assets/html/stage3d/devices.js, screens.js): a device refuses a
picture made for another screen (or letterboxes it whole on request); a card's rounded outline is its picture's, and a
hand-built rounded face on a square backing is caught; an app screen laid out as HTML is checked for overlapping ink
and cut-off text and gives its words; a mark follows a tilted object's projected outline."""
import json
import os
import shutil
import sys

import pytest
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402
import _filmpage as _fp  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None
pytestmark = pytest.mark.skipif(not CHROME, reason="Chrome not installed")


def _run(tmp_path, body, shot=None):
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), tmp_path)
    (tmp_path / "p.html").write_text("""<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#000">
<canvas id="c" width="960" height="540"></canvas><script src="stage3d.js"></script><script>
window.filmReady = (async () => { %s })().then((r) => { window.__res = r; return 'ok'; });
window.seek = () => {};
</script></body></html>""" % body)
    port, srv = _fp.serve(str(tmp_path))
    try:
        p = _fp.FilmPage(port, "p.html", 960, 540)
        try:
            res = p.ev("window.__res")
            if shot:
                p.shot(str(tmp_path / shot), "png")
            return res
        finally:
            p.close()
    finally:
        srv.shutdown()


def test_a_device_refuses_another_screens_picture_and_letterboxes_on_request(tmp_path):
    res = _run(tmp_path, """
      const st = Stage3D.create({canvas: document.getElementById('c')}); st.studio();
      const wide = document.createElement('canvas'); wide.width = 1600; wide.height = 1000;
      const g = wide.getContext('2d'); g.fillStyle = '#ff0000'; g.fillRect(0, 0, 1600, 1000);
      let err = ''; try { st.phone(wide); } catch (e) { err = e.message; }
      const ph = st.phone(wide, {fit: 'contain', width: 1.6}); ph.position.set(0, 1.6, 0);
      const fine = document.createElement('canvas'); fine.width = 1179; fine.height = 2556; st.phone(fine).visible = false;
      await st.ready(); ph.userData.refresh();
      st.render({pos: [0, 1.6, 4], look: [0, 1.6, 0], fov: 50});
      return {err, w: ph.userData.canvas.width, h: ph.userData.canvas.height};""", shot="s.png")
    assert "1179x2556" in res["err"] and "fit: 'contain'" in res["err"], res["err"]
    assert abs(res["w"] / res["h"] - 1179 / 2556) < 0.01
    im = Image.open(tmp_path / "s.png").convert("RGB")
    assert im.getpixel((480, 270))[0] > 180, "the letterboxed picture shows (red) in the middle of the phone"
    top = im.getpixel((480, 270 - 150))
    assert top[0] < 60, "above the wide picture the phone's display is black letterbox, not the picture stretched: %s" % (top,)


def test_a_card_takes_its_pictures_rounded_outline_and_a_square_backing_is_caught(tmp_path):
    im = Image.new("RGBA", (520, 150), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, 519, 149), radius=34, fill=(255, 255, 255, 255))
    im.save(tmp_path / "chip.png")
    res = _run(tmp_path, """
      const st = Stage3D.create({canvas: document.getElementById('c'), background: '#000000'}); st.studio();
      const T = Stage3D.THREE;
      const card = st.card('chip.png', {width: 2, y: 1, name: 'good'});
      // the hand-built way the Grok Bot chips were made: a square box behind a rounded face
      const tex = await new Promise((r) => new T.TextureLoader().load('chip.png', r)); const g = new T.Group(); g.name = 'bad';
      const back = new T.Mesh(new T.BoxGeometry(2, 2 * 150 / 520, 0.006), new T.MeshStandardMaterial({color: '#888888'}));
      const face = new T.Mesh(new T.PlaneGeometry(2, 2 * 150 / 520), new T.MeshStandardMaterial({map: tex, transparent: true}));
      face.position.z = 0.0035; g.add(back, face); g.position.set(0, -0.2, 0); st.scene.add(g);
      await st.ready(); st.render({pos: [0, 0.4, 4], look: [0, 0.4, 0], fov: 45});
      return {radius: card.userData.radius, contacts: st.contacts()};""")
    assert abs(res["radius"] - 34 * 2 / 520) < 0.012, res["radius"]
    kinds = [(c["kind"], c["a"]) for c in res["contacts"]]
    assert ("corners", "bad") in kinds, kinds
    assert not any(a == "good" for _, a in kinds), kinds


def test_an_html_screen_is_drawn_checked_and_read(tmp_path):
    res = _run(tmp_path, """
      const c = document.createElement('canvas'); c.width = 780; c.height = 1688;
      const st = Stage3D.create({canvas: document.getElementById('c')}); st.studio();
      const css = '.a{font:600 30px Helvetica;padding:20px} .bar{position:absolute;left:40px;top:120px;width:200px;height:60px;background:#f5b800}'
        + ' .leg{position:absolute;left:60px;top:130px;font:24px Helvetica} .cut{width:120px;overflow:hidden;white-space:nowrap;font:24px Helvetica}';
      await Stage3D.screen(c, '<div class="a">Q3 board deck</div><div class="bar"></div><div class="leg">Revenue</div>'
        + '<div class="cut">A label far too long to fit in its box</div>', {size: [390, 844], css, name: 'deck'});
      const ph = st.phone(c); ph.position.set(0, 1, 0); await st.ready(); ph.userData.refresh();
      st.render({pos: [0, 1, 3], look: [0, 1, 0], fov: 50});
      const px = c.getContext('2d').getImageData(60 * 2, 140 * 2, 1, 1).data;
      return {lint: await Stage3D.lintScreens(), drawn: Array.from(px)};""")
    assert res["drawn"][0] > 200 and res["drawn"][2] < 80, "the screen's markup was drawn onto the canvas: %s" % res["drawn"]
    [r] = res["lint"]
    kinds = {i["kind"] for i in r["issues"]}
    assert "overlap" in kinds and "clipped" in kinds, r["issues"]
    assert any(i["kind"] == "overlap" and "Revenue" in (i["a"] + i.get("b", "")) for i in r["issues"]), r["issues"]
    assert "Q3 board deck" in r["texts"] and "Revenue" in r["texts"]


def test_a_clean_screen_passes_and_a_hidden_one_is_not_judged(tmp_path):
    res = _run(tmp_path, """
      const st = Stage3D.create({canvas: document.getElementById('c')}); st.studio();
      const a = document.createElement('canvas'); a.width = 1179; a.height = 2556;
      const b = document.createElement('canvas'); b.width = 1179; b.height = 2556;
      const css = '.l{display:flex;flex-direction:column;gap:12px;padding:24px;font:22px Helvetica} .r{display:flex;gap:10px;align-items:center}'
        + ' .dot{width:30px;height:30px;border-radius:15px;background:#34c759}';
      await Stage3D.screen(a, '<div class="l"><div class="r"><div class="dot"></div><span>Memory</span></div><div class="r"><div class="dot"></div><span>Files</span></div></div>', {size: [393, 852], css, name: 'clean'});
      await Stage3D.screen(b, '<div style="position:absolute;top:10px">X</div><div style="position:absolute;top:10px">Y</div>', {size: [393, 852], name: 'hidden'});
      const pa = st.phone(a); pa.position.set(0, 1, 0); const pb = st.phone(b); pb.visible = false;
      await st.ready(); st.render({pos: [0, 1, 3], look: [0, 1, 0], fov: 50});
      return await Stage3D.lintScreens();""")
    assert [r["screen"] for r in res] == ["clean"], res
    assert res[0]["issues"] == [], res[0]["issues"]


def test_brackets_follow_a_tilted_object(tmp_path):
    res = _run(tmp_path, """
      const st = Stage3D.create({canvas: document.getElementById('c')}); st.studio();
      const c = document.createElement('canvas'); c.width = 400; c.height = 400;
      const card = st.card(c, {width: 1, radius: 0, y: 1, rotZ: 0.5}); await st.ready();
      st.render({pos: [0, 1, 3], look: [0, 1, 0], fov: 45});
      return st.quad(card);""")
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = res
    import math
    ang = math.degrees(math.atan2(-(y1 - y0), x1 - x0))
    assert 22 < ang < 35, "the quad's top edge is tilted with the card (rotZ 0.5 rad ~ 29 deg): %.1f" % ang
    assert abs(math.hypot(x1 - x0, y1 - y0) - math.hypot(x2 - x1, y2 - y1)) < 8, "a square card stays square on screen"


def test_a_character_and_a_kit_laptop_are_judged_together(tmp_path):
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((20, 20, 180, 180), fill=(0, 198, 106, 255))
    im.save(tmp_path / "bot.png")
    res = _run(tmp_path, """
      const st = Stage3D.create({canvas: document.getElementById('c')}); st.studio();
      const sc = document.createElement('canvas'); sc.width = 3024; sc.height = 1964; sc.getContext('2d').fillRect(0, 0, 3024, 1964);
      const lap = st.laptop(sc, {width: 3, name: 'mac'}); const top = lap.userData.baseTop;
      const on = st.inflate('bot.png', {width: 0.5, name: 'on', x: -0.8, y: top + 0.01});
      const sunk = st.inflate('bot.png', {width: 0.5, name: 'sunk', x: 0.8, y: -0.1});
      await st.ready(); st.render({pos: [0, 1.5, 4], look: [0, 0.3, 0], fov: 45});
      return st.contacts();""")
    pairs = {(c["kind"], frozenset((c["a"], c["b"]))) for c in res}
    assert ("penetrates", frozenset(("mac", "sunk"))) in pairs, res
    assert not any("on" in p for _, p in pairs), res
    assert not any(k == "corners" for k, _ in pairs), "the kit laptop's own layers are not a square backing: %s" % res
