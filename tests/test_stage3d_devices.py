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


def test_a_wide_card_with_small_corners_is_not_taken_for_a_square_backing(tmp_path):
    im = Image.new("RGBA", (2000, 340), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, 1999, 339), radius=32, fill=(30, 32, 32, 255))
    im.save(tmp_path / "term.png")
    res = _run(tmp_path, """
      const st = Stage3D.create({canvas: document.getElementById('c'), background: '#000000'}); st.studio();
      const T = Stage3D.THREE;
      st.card('term.png', {width: 3, depth: 0.05, y: 0.8, name: 'good'});
      const tex = await new Promise((r) => new T.TextureLoader().load('term.png', r)); const g = new T.Group(); g.name = 'bad';
      const back = new T.Mesh(new T.BoxGeometry(3, 3 * 340 / 2000, 0.006), new T.MeshStandardMaterial({color: '#888888'}));
      const face = new T.Mesh(new T.PlaneGeometry(3, 3 * 340 / 2000), new T.MeshStandardMaterial({map: tex, transparent: true}));
      face.position.z = 0.0035; g.add(back, face); g.position.set(0, 0.1, 0); st.scene.add(g);
      await st.ready(); st.render({pos: [0, 0.45, 4], look: [0, 0.45, 0], fov: 50});
      return st.contacts();""")
    kinds = [(c["kind"], c["a"]) for c in res]
    assert ("corners", "bad") in kinds, kinds
    assert not any(a == "good" for _, a in kinds), "a wide st.card with 16 px corners was flagged: %s" % kinds


def test_the_kit_caret_never_moves_its_line(tmp_path):
    res = _run(tmp_path, """
      const c = document.createElement('canvas'); c.width = 1600; c.height = 400;
      const css = '.d{font:24px/1.3 "PingFang SC",Helvetica;padding:20px} .t{font:30px/1.5 Menlo,"PingFang SC",monospace;padding:20px}';
      const lay = async (on, block) => { await Stage3D.screen(c, '<div class="d">定义事实准确性' + Stage3D.caret(on) + '、来源可靠性</div>'
        + '<div class="t">&gt; 帮我配置 job-hunt' + Stage3D.caret(on, {block: true}) + '</div>', {size: [800, 200], css, name: 'k' + on});
        const [r] = (await Stage3D.lintScreens()).filter((x) => x.screen === 'k' + on); return r ? r.lines : null; };
      const st = Stage3D.create({canvas: document.getElementById('c')}); st.studio(); const card = st.card(c, {width: 2, radius: 0}); await st.ready();
      st.render({pos: [0, 0, 3], look: [0, 0, 0], fov: 50});
      const on = await lay(true); card.userData.refresh(); st.render({pos: [0, 0, 3], look: [0, 0, 0], fov: 50}); const off = await lay(false);
      return {on, off};""")
    assert res["on"] and res["on"] == res["off"], res


def test_a_card_refuses_a_radius_that_disagrees_with_its_pictures_corners(tmp_path):
    im = Image.new("RGBA", (600, 120), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, 599, 119), radius=60, fill=(37, 41, 42, 255))   # a pill chip
    im.save(tmp_path / "pill.png")
    res = _run(tmp_path, """
      const st = Stage3D.create({canvas: document.getElementById('c')}); st.studio();
      st.card('pill.png', {width: 2, radius: 0.02, name: 'chip'}); let err = '';
      try { await st.ready(); } catch (e) { err = e.message; }
      const st2 = Stage3D.create({canvas: document.getElementById('c')}); st2.studio();
      const ok = st2.card('pill.png', {width: 2, radius: 0.2}); await st2.ready();
      return {err, r: ok.userData.radius};""")
    assert "disagrees with the picture" in res["err"] and "chip" in res["err"], res
    assert abs(res["r"] - 0.2) < 1e-3, "a radius that matches the picture (60 px of 600 on 2 units) is kept"


def test_ink_cut_away_by_a_clipping_box_is_not_an_overlap(tmp_path):
    res = _run(tmp_path, """
      const c = document.createElement('canvas'); c.width = 1080; c.height = 1280;
      const css = '.card{position:absolute;inset:0;background:#222} .hd{position:relative;z-index:1;height:100px;background:#333;color:#fff;font:30px Helvetica;padding:20px}'
        + ' .win{position:absolute;left:20px;right:20px;top:140px;bottom:0;overflow:hidden;background:#fff}'
        + ' .pg{position:absolute;left:0;top:-200px;font:24px/1.4 Helvetica;color:#111} .over{position:absolute;left:30px;top:40px;font:24px Helvetica;color:#f00}';
      await Stage3D.screen(c, '<div class="card"><div class="hd">Recruiter</div><div class="win" data-clip-ok><div class="pg">'
        + Array.from({length: 30}, (_, i) => '<div>Line ' + i + ' of the page</div>').join('') + '</div></div></div>', {size: [540, 640], css, name: 'crop'});
      const d = document.createElement('canvas'); d.width = 1080; d.height = 1280;
      await Stage3D.screen(d, '<div class="card"><div class="hd">Recruiter</div><div class="over">Overlapping words</div></div>', {size: [540, 640], css, name: 'bad'});
      const st = Stage3D.create({canvas: document.getElementById('c')}); st.studio();
      st.card(c, {width: 1, radius: 0, x: -0.7}); st.card(d, {width: 1, radius: 0, x: 0.7}); await st.ready();
      st.render({pos: [0, 0, 3], look: [0, 0, 0], fov: 50});
      return await Stage3D.lintScreens();""")
    by = {r["screen"]: r["issues"] for r in res}
    assert by["crop"] == [], "the page's lines cut away under the header are not ink: %s" % by["crop"]
    assert any(i["kind"] == "overlap" for i in by["bad"]), by["bad"]


def test_a_terminal_drawn_by_hand_is_told_from_a_captured_one(tmp_path):
    frame = {"t": 0, "cursor": [2, 1, 1], "rows": [[[" Claude Code v2.1", {"fg": "default", "bg": "default"}]],
                                                    [["❯ ", {"fg": "default", "bg": "default"}], ["hello", {"fg": "default", "bg": "default"}]]]}
    res = _run(tmp_path, """
      const frame = %s;
      const mk = () => { const c = document.createElement('canvas'); c.width = 800; c.height = 400; return c; };
      const css = '.tw{position:absolute;inset:0;background:#1b1d1d;font-family:Menlo,monospace;color:#eee;padding:20px}'
        + ' .web{font:20px Helvetica;padding:20px}';
      const a = mk(), b = document.createElement('canvas'), w = mk();
      await Stage3D.screen(a, '<div class="tw"><div class="wel">\\u273b Welcome to Claude Code!</div><div>&gt; hi</div></div>', {size: [400, 200], css, name: 'hand'});
      const t = Stage3D.terminal(frame, {px: 14, title: null}); b.width = t.size[0]; b.height = t.size[1];
      await Stage3D.screen(b, t.html, {size: t.size, css: t.css, name: 'captured'});
      await Stage3D.screen(w, '<div class="web">Works in Claude Code and Codex. Run ~ %% npx skills add it</div>', {size: [400, 200], css, name: 'web'});
      const st = Stage3D.create({canvas: document.getElementById('c')}); st.studio();
      [a, b, w].forEach((cv, i) => st.card(cv, {width: 0.8, x: -1 + i}));
      await st.ready(); st.render({pos: [0, 0, 3], look: [0, 0, 0], fov: 60});
      return await Stage3D.lintScreens();""" % json.dumps(frame))
    by = {r["screen"]: [i["kind"] for i in r["issues"]] for r in res}
    assert "imitated-terminal" in by.get("hand", []), by
    assert "imitated-terminal" not in by.get("captured", []) and "imitated-terminal" not in by.get("web", []), by


def test_a_terminals_block_characters_join_without_seams(tmp_path):
    # the Claude Code mascot is block characters; drawn cell by cell, then drawn into a sharper canvas (a non-whole
    # scale, as a film's screens are), two cells meeting inside a pixel each blended it with the ground and a dark line
    # ran between them (topic-to-video launch film, 2026-11-19)
    full = {"fg": "ffffff", "bg": "default"}
    frame = {"t": 0, "cursor": [0, 0, 0], "rows": [[["\u2588" * 12, full]], [["\u2588" * 12, full]], [["\u259b\u259c" * 6, full]]]}
    k = 2.37
    _run(tmp_path, """
      const t = Stage3D.terminal(%s, {px: 15, title: null, pad: 0, radius: 0, theme: {bg: '#000000'}});
      const c = document.getElementById('c'); c.width = Math.round(t.size[0] * %s); c.height = Math.round(t.size[1] * %s);
      await Stage3D.screen(c, t.html, {size: t.size, css: t.css + ' .tw{box-shadow:none}', name: 'blocks'});
      return t.size;""" % (json.dumps(frame), k, k), shot="s.png")
    im = Image.open(tmp_path / "s.png").convert("L")
    cw, rh = 15 * 0.6021 * k, 19 * k
    solid = [im.getpixel((x, y)) for y in range(2, int(2 * rh) - 2) for x in range(2, int(12 * cw) - 2)]
    assert min(solid) >= 235, "a seam between full blocks: darkest %d" % min(solid)
    top = [im.getpixel((x, y)) for y in range(int(2 * rh) + 2, int(2.5 * rh) - 2) for x in range(2, int(12 * cw) - 2)]
    assert min(top) >= 235, "a seam between quadrants: darkest %d" % min(top)


def test_a_terminals_cursor_is_found_before_its_block_art(tmp_path):
    # the launch film found its cursor as the terminal's first [data-overlap-ok]; when the mascot's drawing came first
    # it blinked the mascot black instead (2026-11-19). The cursor is named ([data-cursor]) and comes first.
    st = {"fg": "d77757", "bg": "default"}
    frame = {"t": 0, "cursor": [3, 1, 1], "rows": [[["▛█▜", st]], [["❯ ", {"fg": "default", "bg": "default"}]]]}
    res = _run(tmp_path, """
      const t = Stage3D.terminal(%s, {px: 15, title: null});
      const d = document.createElement('div'); d.innerHTML = t.html; document.body.appendChild(d);
      const first = d.querySelector('[data-overlap-ok]'), cur = d.querySelector('[data-cursor]'), art = d.querySelector('[data-term-art]');
      return {first: first === cur, art: !!art, curZ: +getComputedStyle(cur).zIndex, artZ: +getComputedStyle(art).zIndex};""" % json.dumps(frame))
    assert res == {"first": True, "art": True, "curZ": 1, "artZ": 0}, res
