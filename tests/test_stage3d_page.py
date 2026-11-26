"""assets/html/stage3d.js renders a lit 3D stage with a real screen as a panel, from file://, in headless Chrome:
the canvas is not blank and the screen's own colours survive (it emits its picture). That the committed build matches its
source is checked in test_stage3d_finish_splat.py (both bundles, built from the stage's own toolchain)."""
import os
import shutil
import subprocess

import pytest
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


@pytest.mark.skipif(not os.path.exists(CHROME), reason="Chrome not installed")
def test_a_screen_renders_as_a_lit_panel(tmp_path):
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), tmp_path)
    Image.new("RGB", (800, 500), (255, 40, 40)).save(tmp_path / "screen.png")       # a pure red "screen"
    (tmp_path / "p.html").write_text("""<!doctype html><html><body style="margin:0;background:#000">
<canvas id="c" width="640" height="360"></canvas><script src="stage3d.js"></script><script>
const st = Stage3D.create({canvas: document.getElementById('c'), background: '#05060a'});
st.studio(); st.floor({}); st.panel('screen.png', {width: 4, x: 0, y: 1.6, rotY: -0.2});
st.ready().then(() => st.render({pos: [0, 1.8, 6], look: [0, 1.6, 0], fov: 40}));
</script></body></html>""")
    shot = tmp_path / "shot.png"
    subprocess.run([CHROME, "--headless=new", "--allow-file-access-from-files", "--hide-scrollbars",
                    "--window-size=640,360", "--virtual-time-budget=6000", "--screenshot=%s" % shot,
                    "file://%s" % (tmp_path / "p.html")], capture_output=True, timeout=120)
    im = Image.open(shot).convert("RGB")
    r, g, b = im.getpixel((320, 150))                          # the panel's centre
    assert r > 200 and g < 90 and b < 90, (r, g, b)            # the screen keeps its own red: it emits, unlit
    assert im.getpixel((5, 5))[0] < 40                         # the ground is the dark stage, not blank white


def _shoot(tmp_path, body, w=640, h=360):
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), tmp_path)
    (tmp_path / "p.html").write_text("""<!doctype html><html><body style="margin:0;background:#000">
<canvas id="c" width="%d" height="%d"></canvas><script src="stage3d.js"></script><script>
(async () => { %s })().then(() => document.title = 'ok', (e) => document.title = 'ERR ' + e.message);
</script></body></html>""" % (w, h, body))
    shot = tmp_path / "shot.png"
    r = subprocess.run([CHROME, "--headless=new", "--allow-file-access-from-files", "--hide-scrollbars",
                        "--window-size=%d,%d" % (w, h), "--virtual-time-budget=6000", "--dump-dom",
                        "file://%s" % (tmp_path / "p.html")], capture_output=True, timeout=120, text=True)
    subprocess.run([CHROME, "--headless=new", "--allow-file-access-from-files", "--hide-scrollbars",
                    "--window-size=%d,%d" % (w, h), "--virtual-time-budget=6000", "--screenshot=%s" % shot,
                    "file://%s" % (tmp_path / "p.html")], capture_output=True, timeout=120)
    return r.stdout, Image.open(shot).convert("RGB")


@pytest.mark.skipif(not os.path.exists(CHROME), reason="Chrome not installed")
def test_inflate_keeps_a_characters_shape_and_colours(tmp_path):
    # a green disc with one small blue dot (2% of it) on a transparent ground: the body is green, the dot stays blue
    from PIL import ImageDraw
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((20, 20, 180, 180), fill=(0, 198, 106, 255)); d.ellipse((90, 60, 110, 80), fill=(16, 132, 254, 255))
    im.save(tmp_path / "bot.png")
    dom, shot = _shoot(tmp_path, """const st = Stage3D.create({canvas: document.getElementById('c'), background: '#05060a',
      toneMapping: 'neutral'}); st.studio({env: 0.4}); const b = st.inflate('bot.png', {width: 2, x: 0, y: 0.2});
      await st.ready(); st.render({pos: [0, 1.2, 5], look: [0, 1.2, 0], fov: 40});""")
    assert "<title>ok</title>" in dom, dom[:300]
    px = [shot.getpixel((x, y)) for x in range(250, 390, 6) for y in range(140, 260, 6)]
    green = [p for p in px if p[1] > 120 and p[1] > p[0] + 50 and p[1] > p[2] + 30]
    blue = [p for p in px if p[2] > 150 and p[2] > p[0] + 80]
    assert len(green) > len(px) * 0.4, "the body lost its colour"
    assert blue, "the small blue part was snapped away"



@pytest.mark.skipif(not os.path.exists(CHROME), reason="Chrome not installed")
def test_inflate_rim_is_clean_when_turned(tmp_path):
    # the real case: a small character cut out of a WHITE screenshot (soft near-white fringe), turned so its rim faces the
    # camera. The rim must be body colour: no white fringe specks, no face texels stretched into streaks.
    import sys
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from cutout import cutout
    from PIL import ImageDraw
    big = Image.new("RGB", (440, 440), (255, 255, 255)); ImageDraw.Draw(big).ellipse((40, 40, 400, 400), fill=(220, 30, 50))
    cutout(big.resize((110, 110), Image.LANCZOS)).save(tmp_path / "bot.png")
    dom, shot = _shoot(tmp_path, """const st = Stage3D.create({canvas: document.getElementById('c'), background: '#05060a',
      toneMapping: 'neutral'}); st.studio({env: 0.2}); st.inflate('bot.png', {width: 2, y: 0.2, rotY: -1.1, clearcoat: 0, roughness: 1});
      await st.ready(); st.render({pos: [0, 1.2, 5], look: [0, 1.2, 0], fov: 40});""")
    assert "<title>ok</title>" in dom, dom[:300]
    import numpy as np
    a = np.asarray(shot).astype(float)
    m = (a[2:, :, 0] > 60) & (a[:-2, :, 0] > 60)                 # inside the red body, two px apart vertically
    d = np.abs(a[2:] - a[:-2]).sum(2)[m]
    assert m.sum() > 2000, "the body did not render"
    # smooth shading changes slowly (p99 ~25); streaks/specks jump (p99 78-103 before the rim fix, 2026-11-18)
    assert np.percentile(d, 99) < 50, "rim streaks: p99 vertical step %.0f" % np.percentile(d, 99)

@pytest.mark.skipif(not os.path.exists(CHROME), reason="Chrome not installed")
@pytest.mark.parametrize("case,expect", [("holes", "has transparent holes"), ("crescent", "not one star-shaped body")])
def test_inflate_refuses_what_it_would_draw_wrong(tmp_path, case, expect):
    from PIL import ImageDraw
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((20, 20, 180, 180), fill=(255, 90, 0, 255))
    if case == "holes":       # white eyes removed with the background colour: transparent holes inside the face
        d.rectangle((70, 70, 90, 120), fill=(0, 0, 0, 0)); d.rectangle((110, 70, 130, 120), fill=(0, 0, 0, 0))
    else:                     # a crescent: its horns lie outside any outline traced from the centre
        d.ellipse((70, 10, 200, 170), fill=(0, 0, 0, 0))
    im.save(tmp_path / "s.png")
    dom, _ = _shoot(tmp_path, """const st = Stage3D.create({canvas: document.getElementById('c')});
      st.inflate('s.png', {width: 1}); await st.ready();""")
    assert "ERR stage3d.inflate" in dom and expect in dom, dom[:400]


@pytest.mark.skipif(not os.path.exists(CHROME), reason="Chrome not installed")
def test_inflate_refuses_a_shape_that_touches_the_edge(tmp_path):
    Image.new("RGBA", (100, 100), (240, 240, 240, 255)).save(tmp_path / "tile.png")   # opaque: no outline to trace
    dom, _ = _shoot(tmp_path, """const st = Stage3D.create({canvas: document.getElementById('c')});
      st.inflate('tile.png', {width: 1}); await st.ready();""")
    assert "ERR stage3d.inflate" in dom and "touches the image edge" in dom, dom[:300]


@pytest.mark.skipif(not os.path.exists(CHROME), reason="Chrome not installed")
def test_carry_rides_on_the_posed_body(tmp_path):
    # a carried card must sit on the body's top as posed THIS frame: above it at rest, higher mid-hop, never inside it
    from PIL import ImageDraw
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0)); ImageDraw.Draw(im).ellipse((20, 20, 180, 180), fill=(0, 184, 160, 255))
    im.save(tmp_path / "bot.png")
    dom, _ = _shoot(tmp_path, """const st = Stage3D.create({canvas: document.getElementById('c')});
      let early = 'none'; const b0 = st.inflate('bot.png', {width: 1}); try { Stage3D.carry(new Stage3D.THREE.Object3D(), b0, {h: 0.5}); } catch (e) { early = 'threw'; }
      await st.ready(); const card = new Stage3D.THREE.Object3D(), body = b0.userData.body, out = [];
      for (const u of [0, 0.08, 0.5, 0.93]) { const h = Stage3D.hop(u, {height: 0.6}); body.position.y = h.y; body.scale.set(h.sx, h.sy, h.sx);
        const top = Stage3D.carry(card, b0, {h: 0.5, gap: 0.05}); out.push([top, card.position.y - 0.25].map((v) => v.toFixed(3)).join(':')); }
      document.body.setAttribute('data-res', early + ' ' + out.join(' '));""")
    import re
    m = re.search(r'data-res="(\S+) ([^"]*)"', dom)
    assert m, dom[:300]
    assert m.group(1) == "threw", "carry on a character that has not loaded must fail loudly"
    pairs = [tuple(map(float, p.split(":"))) for p in m.group(2).split()]
    for top, bottom in pairs:
        assert abs(bottom - (top + 0.05)) < 1e-3, "the card is not resting on the body's top: %s" % pairs
    rest, crouch, mid, land = [p[0] for p in pairs]
    assert mid > rest + 0.4 and crouch < rest and land < rest, "the top did not follow the hop and squash: %s" % pairs


@pytest.mark.skipif(not os.path.exists(CHROME), reason="Chrome not installed")
def test_depth_of_field_keeps_antialiasing_and_pixel_ratio_keeps_page_size(tmp_path):
    # the composer renders into its own target: without MSAA there, depth of field drops the antialiasing and every
    # silhouette stairs (binary edge pixels). pixelRatio 2 draws at twice the size but keeps the canvas W x H on the page.
    from PIL import ImageDraw
    import numpy as np
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0)); ImageDraw.Draw(im).ellipse((20, 20, 180, 180), fill=(255, 255, 255, 255))
    im.save(tmp_path / "disc.png")
    dom, shot = _shoot(tmp_path, """const c = document.getElementById('c');
      const st = Stage3D.create({canvas: c, background: '#000000', toneMapping: 'neutral', dof: {aperture: 0.00001, maxblur: 0.001}, pixelRatio: 2});
      st.studio({env: 1}); st.inflate('disc.png', {width: 2.4, y: -0.1, clearcoat: 0, roughness: 1}); await st.ready();
      st.render({pos: [0, 1.1, 5], look: [0, 1.1, 0], fov: 40, focus: 5});
      document.body.setAttribute('data-size', c.width + 'x' + c.height + ' ' + c.style.width + 'x' + c.style.height);""")
    import re
    m = re.search(r'data-size="([^"]*)"', dom)
    assert m and m.group(1) == "1280x720 640pxx360px", (m.group(1) if m else dom[:300])
    a = np.asarray(shot.convert("L")).astype(int)
    edge = (a > 25) & (a < 200)                                  # partly covered pixels along the silhouette
    inside = a >= 200
    assert inside.sum() > 2000, "the disc did not render"
    assert edge.sum() > 0.35 * np.sqrt(inside.sum()) * 3.5, "silhouette is stair-stepped (no antialiasing): %d edge px" % edge.sum()


@pytest.mark.skipif(not os.path.exists(CHROME), reason="Chrome not installed")
def test_eyes_are_separate_blink_and_look_together_on_the_face(tmp_path):
    # a character with two eye marks gets two raised eyes; a logo with five marks keeps its painted face (and says why)
    from PIL import ImageDraw
    im = Image.new("RGBA", (220, 220), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
    g.ellipse((10, 10, 210, 210), fill=(0, 184, 160, 255))
    for x in (120, 150):
        g.rounded_rectangle((x, 60, x + 14, 104), radius=7, fill=(255, 255, 255, 255))
    im.save(tmp_path / "bot.png")
    lg = Image.new("RGBA", (220, 220), (0, 0, 0, 0)); g = ImageDraw.Draw(lg)
    g.ellipse((10, 10, 210, 210), fill=(200, 30, 50, 255))
    for i in range(5):
        g.rectangle((40 + i * 30, 95, 56 + i * 30, 125), fill=(255, 255, 255, 255))
    lg.save(tmp_path / "logo.png")
    dom, _ = _shoot(tmp_path, """const st = Stage3D.create({canvas: document.getElementById('c')});
      const b = st.inflate('bot.png', {width: 1}), l = st.inflate('logo.png', {width: 1}), n = st.inflate('bot.png', {width: 1, eyes: false});
      await st.ready();
      const E = b.userData.eyes, sp0 = E[1].x0 - E[0].x0;
      Stage3D.blink(b, 1); const lid = E[0].lid.scale.y; Stage3D.blink(b, 0);
      Stage3D.look(b, 1, 0); const p0 = E[0].lid.parent.position, p1 = E[1].lid.parent.position;
      const res = {eyes: E.length, reason: b.userData.eyeReason, lid: +lid.toFixed(3), spacing: +((p1.x - p0.x) / sp0).toFixed(3),
        moved: +(p0.x - E[0].x0).toFixed(3), logo: (l.userData.eyes || []).length, logoReason: l.userData.eyeReason,
        off: (n.userData.eyes || []).length, offReason: n.userData.eyeReason};
      document.body.setAttribute('data-res', JSON.stringify(res));""")
    import json as _json, re as _re, html as _html
    m = _re.search(r'data-res="([^"]*)"', dom)
    assert m, dom[:300]
    r = _json.loads(_html.unescape(m.group(1)))
    assert r["eyes"] == 2 and r["reason"] is None, r
    assert r["lid"] < 0.15, "blink(1) shuts the eyes"
    assert abs(r["spacing"] - 1) < 0.02 and r["moved"] > 0, "a look moves both eyes together (spacing kept)"
    assert r["logo"] == 0 and "5 marks" in r["logoReason"], r
    assert r["off"] == 0 and r["offReason"] == "p.eyes is false", r
