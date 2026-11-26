"""The 3D stage on its own three (r180, assets/html/stage3d/package.json): the lens-and-finish pass (st.finish: bloom,
light shafts, a grade) and 3D scans as Gaussian splats (st.splat, through Spark in stage3d_splat.js).
WHY: Spark needs three r180+, and the stage bundled Remotion's r169. The upgrade was measured on 25 frames of seven real
films before it shipped (2026-11-26): two three changes moved old films (r175's ExtrudeGeometry put a different highlight
on a phone's band, 84/255; r178's blending equations moved an additive glow on a transparent stage, 6/255) and both are
pinned in the stage. The golden test here keeps that promise: a scene with those parts, rendered by the OLD r169 bundle,
is the reference the current bundle must reproduce. Bloom is a blur and the user forbids blur on real pictures and small
text: the finish must leave a screenshot's small text and a drawn display's labels exactly as they were, and glow only
around what emits. Every frame is a pure function of t, a splat's sort included (a page renders frames in any order)."""
import math
import os
import shutil
import struct
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402
import _filmpage as _fp  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None
needs_chrome = pytest.mark.skipif(not CHROME, reason="Chrome not installed")
HTML = os.path.join(ROOT, "assets", "html")
GOLDEN = os.path.join(ROOT, "tests", "fixtures", "stage3d", "r169_golden.png")
NM = os.path.join(HTML, "stage3d", "node_modules")


def _font(size):
    for f in ("/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def _assets(d):
    """A screenshot with small text, a flat character on a transparent ground, a small .splat (a ball on a disc)."""
    im = Image.new("RGB", (1280, 800), (250, 250, 252)); dr = ImageDraw.Draw(im)
    dr.text((60, 50), "Quarterly report", font=_font(40), fill=(20, 20, 30))
    for i in range(28):
        dr.text((60, 130 + i * 23), "Row %02d  revenue 1,234.%02d  margin 12.%d%%  small text must stay crisp" % (i, i, i % 10),
                font=_font(16), fill=(40, 40, 50))
    im.save(d / "screen.png")
    bot = Image.new("RGBA", (200, 200), (0, 0, 0, 0)); b = ImageDraw.Draw(bot)
    b.ellipse((20, 20, 180, 180), fill=(0, 184, 160, 255)); b.ellipse((70, 70, 90, 100), fill=(255, 255, 255, 255))
    b.ellipse((110, 70, 130, 100), fill=(255, 255, 255, 255)); bot.save(d / "bot.png")
    rows = []
    for i in range(6000):
        y = 1 - 2 * (i + 0.5) / 6000; r = math.sqrt(1 - y * y); a = i * math.pi * (3 - math.sqrt(5))
        x, z = math.cos(a) * r, math.sin(a) * r
        rows.append(((0.6 * x, 0.8 + 0.6 * y, 0.6 * z), (0.03,) * 3, (int(127 + 127 * x), int(127 + 127 * y), int(127 + 127 * z), 255)))
    for j in range(60):
        for k in range(120):
            rr, a, g = 0.05 + 1.6 * j / 60, 2 * math.pi * k / 120 + j * 0.1, 90 + (j * 7 + k * 13) % 60
            rows.append(((rr * math.cos(a), 0.0, rr * math.sin(a)), (0.04, 0.004, 0.04), (g, g, int(g * 0.8), 255)))
    with open(d / "ball.splat", "wb") as f:      # antimatter15 layout: pos f32x3, scale f32x3, rgba u8x4, quat u8x4 (w, x, y, z)
        for p, s, c in rows:
            f.write(struct.pack("<3f3f4B4B", *p, *s, *c, 255, 128, 128, 128))


def _page(d, script, W=640, H=360, bundle=None, splat=False):
    shutil.copy(bundle or os.path.join(HTML, "stage3d.js"), d / "stage3d.js")
    if splat:
        shutil.copy(os.path.join(HTML, "stage3d_splat.js"), d / "stage3d_splat.js")
    (d / "film.html").write_text("""<!doctype html><html><head><meta charset="utf-8"><meta name="film-size" content="%dx%d">
<style>html,body{margin:0;background:#2a3a55} canvas{position:absolute;left:0;top:0;width:%dpx;height:%dpx}</style></head>
<body><canvas id="c" width="%d" height="%d"></canvas><script src="stage3d.js"></script>%s<script>
const q = new URLSearchParams(location.search), T = Stage3D.THREE;
%s
</script></body></html>""" % (W, H, W, H, W, H, '<script src="stage3d_splat.js"></script>' if splat else "", script))


def _shoot(d, query, times, W=640, H=360):
    """[(t, HxWx3 float array)] for film.html?<query> at the given times, in that order, one page."""
    port, srv = _fp.serve(str(d))
    out = []
    try:
        p = _fp.FilmPage(port, "film.html?" + query, W, H)
        try:
            for i, t in enumerate(times):
                p.seek(t)
                f = d / ("shot_%s_%d.png" % (query.replace("=", "").replace("&", "_"), i))
                p.shot(str(f), "png")
                out.append(np.asarray(Image.open(f).convert("RGB")).astype(float))
        finally:
            p.close()
    finally:
        srv.shutdown()
    return out


def _lum(a):
    return a @ [0.2126, 0.7152, 0.0722]


def _edge(L):
    """Text crispness: the mean of the top 5 % luminance steps in a crop."""
    g = np.hypot(np.abs(np.diff(L, axis=1))[:-1, :], np.abs(np.diff(L, axis=0))[:, :-1]).ravel()
    return np.sort(g)[-max(1, len(g) // 20):].mean()


# a night console: a screenshot on a lit panel, a drawn EL display (digits brighter than white, small labels), a lamp
CONSOLE = """
const st = Stage3D.create({canvas: document.getElementById('c'), background: '#07080a', toneMapping: 'neutral', pixelRatio: 2,
                           passes: +(q.get('p') || 1)});
st.studio({key: 0.6, rim: 0.4, fill: 0.15, env: 0.15}); st.floor({color: '#0c0d10'});
st.panel('screen.png', {width: 3.2, x: -1.9, y: 1.2, rotY: 0.18});
const cv = document.createElement('canvas'); cv.width = 1024; cv.height = 512; const g = cv.getContext('2d');
const fontsOk = document.fonts.load('22px sans-serif');
const tx = new T.CanvasTexture(cv); tx.colorSpace = T.SRGBColorSpace;
const disp = new T.Mesh(new T.PlaneGeometry(2.4, 1.2), new T.MeshStandardMaterial({color: '#111', map: tx, emissiveMap: tx,
  emissive: '#ffffff', emissiveIntensity: 1.6, roughness: 0.5}));
disp.position.set(1.7, 1.2, 0); disp.rotation.y = -0.2; st.scene.add(disp);
const lamp = new T.Mesh(new T.SphereGeometry(0.12, 32, 16), new T.MeshBasicMaterial({color: new T.Color(6, 5, 3.5)}));
lamp.position.set(0.1, 2.7, -1.5); st.scene.add(lamp);
const FIN = {bloom: {bloom: {strength: 0.8}},
  all: {bloom: {strength: 0.8}, rays: {at: [0.1, 2.7, -1.5], strength: 0.6}, grade: {lift: [0.02, 0.01, 0], gain: [1.05, 1, 0.92], saturation: 0.9}},
  zero: {bloom: {strength: 0}, rays: {at: [0.1, 2.7, -1.5], strength: 0}}};
if (FIN[q.get('m')]) st.finish(FIN[q.get('m')]);
window.filmReady = (async () => { await fontsOk; g.fillStyle = '#050806'; g.fillRect(0, 0, 1024, 512); g.fillStyle = '#5dff8e';
  g.font = 'bold 190px sans-serif'; g.fillText('16:68', 90, 300); g.font = '22px sans-serif';
  for (let i = 0; i < 4; i++) g.fillText('PROG 63  VERB 16  NOUN 68  label ' + i, 90, 380 + i * 30);
  tx.needsUpdate = true; await st.ready(); return 'ok'; })();
window.seek = (t) => st.render({pos: [0.2 + 0.1 * t, 1.7, 6.2 - 0.2 * t], look: [0, 1.3, 0], fov: 40});
"""


@needs_chrome
def test_bloom_glows_around_what_emits_and_leaves_pictures_and_small_text_exactly_as_they_were(tmp_path):
    _assets(tmp_path); _page(tmp_path, CONSOLE)
    [off], [on], [zero] = (_shoot(tmp_path, "m=" + m, [0]) for m in ("off", "bloom", "zero"))
    lo, ln = _lum(off), _lum(on)
    # the glow: a ring around the lamp (it sits near x 330, y 83 in this framing) is lifted
    yy, xx = np.mgrid[0:360, 0:640]
    lamp = np.unravel_index(np.argmax(np.where(yy < 100, lo, 0)), lo.shape)
    ring = (np.hypot(yy - lamp[0], xx - lamp[1]) > 14) & (np.hypot(yy - lamp[0], xx - lamp[1]) < 40)
    assert (ln - lo)[ring].mean() > 4, "no glow around the lamp: %.2f" % (ln - lo)[ring].mean()
    # the screenshot's small text and the drawn display's labels: crisp and unchanged (crops of both, found by colour)
    for name, box in (("screenshot text", (55, 140, 160, 260)), ("display labels", (375, 203, 475, 230))):
        x0, y0, x1, y1 = box
        e0, e1 = _edge(lo[y0:y1, x0:x1]), _edge(ln[y0:y1, x0:x1])
        assert e0 > 30, "%s: the crop holds no text (edge %.1f); the framing moved" % (name, e0)
        assert abs(e1 / e0 - 1) < 0.01 and np.abs(ln - lo)[y0:y1, x0:x1].max() <= 2, \
            "%s softened under bloom: edge %.1f -> %.1f" % (name, e0, e1)
    # a finish at zero strength is the stage without one (all but 1-px edges between tone-mapped and unlit surfaces)
    d = np.abs(zero - off).max(2)
    assert d.mean() < 0.2 and (d > 8).mean() < 0.005, "finish at zero strength changed the frame: mean %.3f" % d.mean()


@needs_chrome
def test_the_finish_is_a_pure_function_of_t(tmp_path):
    # bloom, shafts and a grade on the accumulating renderer, frames in two orders in two pages: the same pixels
    _assets(tmp_path); _page(tmp_path, CONSOLE)
    a = _shoot(tmp_path, "m=all&p=8", [0, 1.5, 3])
    b = _shoot(tmp_path, "m=all&p=8", [3, 0, 1.5])
    for x, y in ((a[0], b[1]), (a[1], b[2]), (a[2], b[0])):
        assert np.abs(x - y).max() == 0
    assert np.abs(a[0] - a[2]).max() > 50, "the camera did not move: the test proves nothing"


@needs_chrome
def test_the_finish_refuses_what_it_cannot_do(tmp_path):
    _page(tmp_path, """const st = Stage3D.create({canvas: document.getElementById('c')}); const errs = [];
for (const f of [{blom: {}}, {bloom: {strenght: 1}}, {rays: {strength: 1}}]) { try { st.finish(f); errs.push('none'); } catch (e) { errs.push(e.message); } }
window.filmReady = Promise.resolve('ok'); window.__errs = errs; window.seek = (t) => st.render({});""")
    port, srv = _fp.serve(str(tmp_path))
    try:
        p = _fp.FilmPage(port, "film.html", 640, 360)
        try:
            errs = p.ev("window.__errs")
        finally:
            p.close()
    finally:
        srv.shutdown()
    assert "blom is not an option" in errs[0] and "strenght is not an option" in errs[1] and "rays need `at`" in errs[2], errs


SPLAT = """
const st = Stage3D.create({canvas: document.getElementById('c'), background: '#101214', toneMapping: 'neutral', passes: +(q.get('p') || 1)});
st.studio({env: 0.3});
st.splat('ball.splat');
const box = new T.Mesh(new T.BoxGeometry(0.5, 0.5, 0.5), new T.MeshStandardMaterial({color: '#c04020', roughness: 0.5}));
box.position.set(0.55, 0.6, 0.55); st.scene.add(box);
window.filmReady = st.ready().then(() => 'ok', (e) => 'ERR ' + e.message);
window.seek = (t) => st.render({pos: [3.2 * Math.sin(t * 0.6), 1.4, 3.2 * Math.cos(t * 0.6)], look: [0, 0.7, 0], fov: 40});
"""


@needs_chrome
def test_a_splat_scan_renders_among_meshes_and_each_frame_is_a_pure_function_of_t(tmp_path):
    _assets(tmp_path); _page(tmp_path, SPLAT, splat=True)
    a = _shoot(tmp_path, "p=1", [0, 1, 2.5])
    b = _shoot(tmp_path, "p=1", [2.5, 1, 0])           # another page, another order: the sort is for this camera only
    for x, y in ((a[0], b[2]), (a[1], b[1]), (a[2], b[0])):
        assert np.abs(x - y).max() == 0, "a splat frame depends on the frames before it"
    f = a[0]
    # the ball's own colours (a hue wheel) are there, and the box stands in front of it (depth both ways)
    sat = f.max(2) - f.min(2)
    assert (sat > 80).mean() > 0.03, "the splat ball did not render (no saturated pixels)"
    assert np.abs(a[0] - a[2]).max() > 50, "the camera did not move: the test proves nothing"
    box = a[2][190:250, 225:265]    # at t 2.5 the red box stands across the ball's left edge: it hides the ball there
    assert (box[..., 0] > box[..., 1] + 60).mean() > 0.95, "the box is not in front of the splat"


@needs_chrome
def test_a_splat_without_the_add_on_says_how_to_load_it(tmp_path):
    _page(tmp_path, """const st = Stage3D.create({canvas: document.getElementById('c')}); let err = 'none';
try { st.splat('x.spz'); } catch (e) { err = e.message; }
window.filmReady = Promise.resolve('ok'); window.__err = err; window.seek = (t) => st.render({});""")
    port, srv = _fp.serve(str(tmp_path))
    try:
        p = _fp.FilmPage(port, "film.html", 640, 360)
        try:
            err = p.ev("window.__err")
        finally:
            p.close()
    finally:
        srv.shutdown()
    assert "load stage3d_splat.js after stage3d.js" in err, err


# the parts that moved between r169 and r180, on one transparent stage over a coloured page: a phone (an extruded,
# bevelled slab: r175's ExtrudeGeometry), an additive glow (r178's blending), a screenshot panel, a character, a card
GOLDEN_SCENE = """
const st = Stage3D.create({canvas: document.getElementById('c'), transparent: true, toneMapping: 'neutral', pixelRatio: 1});
st.studio({env: 0.4}); st.floor({color: '#15181d'});
st.panel('screen.png', {width: 2.4, x: -1.7, y: 1.3, rotY: 0.35});
const ph = st.phone((() => { const c = document.createElement('canvas'); c.width = 1179; c.height = 2556; const g = c.getContext('2d');
  g.fillStyle = '#f4f4f6'; g.fillRect(0, 0, c.width, c.height); g.fillStyle = '#1a7f5a'; g.fillRect(90, 400, 1000, 300); return c; })(), {width: 0.9});
ph.position.set(0.15, 1.1, 0.4); ph.rotation.set(-0.25, -0.5, 0.1);
st.inflate('bot.png', {width: 0.8, x: 1.4, z: 0.6});
st.card('screen.png', {width: 1.1, x: 1.6, y: 1.9, z: -0.6, rotY: -0.3});
const glow = new T.Mesh(new T.CircleGeometry(0.9, 48), new T.MeshBasicMaterial({color: '#ffb547', transparent: true, opacity: 0.35,
  blending: T.AdditiveBlending, depthWrite: false}));
glow.position.set(0.2, 1.6, -0.8); st.scene.add(glow);
window.filmReady = st.ready().then(() => 'ok', (e) => 'ERR ' + e.message);
window.seek = (t) => st.render({pos: [0.4, 1.9, 5.2], look: [0, 1.2, 0], fov: 38});
"""


@needs_chrome
def test_a_film_made_on_r169_renders_the_same_on_the_new_three(tmp_path):
    """The golden frame was rendered by the r169 bundle (the one every film before 2026-11-26 shipped with). Regenerate it
    only from that bundle (`git show c168bd64:assets/html/stage3d.js > old.js`, then _assets + _page(..., bundle='old.js')
    + _shoot, saved as GOLDEN), never from the current one: that would make the test compare the stage with itself."""
    _assets(tmp_path); _page(tmp_path, GOLDEN_SCENE)
    [now] = _shoot(tmp_path, "", [0])
    gold = np.asarray(Image.open(GOLDEN).convert("RGB")).astype(float)
    d = np.abs(now - gold).max(2)
    assert d.max() <= 3 and d.mean() < 0.05, \
        "the stage renders an r169 film differently: max %d, mean %.3f, %.2f%% of pixels over 8" % (d.max(), d.mean(), 100 * (d > 8).mean())


@pytest.mark.skipif(not os.path.isdir(os.path.join(NM, "three")), reason="the stage's toolchain is not installed (cd assets/html/stage3d && npm ci)")
def test_the_committed_bundles_match_their_source(tmp_path):
    subprocess.run(["sh", os.path.join(ROOT, "scripts", "build_stage3d.sh"), str(tmp_path)], check=True, capture_output=True)
    for name in ("stage3d.js", "stage3d_splat.js"):
        assert (tmp_path / name).read_bytes() == open(os.path.join(HTML, name), "rb").read(), \
            "assets/html/%s is stale: run scripts/build_stage3d.sh" % name


def test_the_stage_pins_its_own_three_apart_from_remotions():
    import json
    pkg = json.load(open(os.path.join(HTML, "stage3d", "package.json")))["dependencies"]
    assert all(v[0].isdigit() for v in pkg.values()), "stage3d's toolchain must be pinned to exact versions: %s" % pkg
    assert int(pkg["three"].split(".")[1]) >= 180, "Spark needs three r180+"
    lock = json.load(open(os.path.join(HTML, "stage3d", "package-lock.json")))
    assert lock["packages"]["node_modules/three"]["version"] == pkg["three"]
