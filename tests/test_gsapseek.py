"""assets/html/gsapseek.js + the vendored GSAP (assets/html/gsap/): GSAP on a film page whose every frame is a pure
function of t. The vendored files are the pinned 3.15.1 builds and load as classic scripts from file://; a frame is the
same whatever was seeked before it (2.0 -> 5.0 -> 2.0, any order, and after real time passes: GSAP's ticker never
moves anything); text is split only after its fonts loaded, and lands where the unsplit text's kerning put it; a tween
left outside the film timeline is refused; a letter moving slowly glides instead of stepping a pixel at a time (the
baseline unlock on the split element), measured against the same move with the unlock taken off."""
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:  # no Chrome on this machine
    CHROME = None
needs_chrome = pytest.mark.skipif(not CHROME, reason="Chrome not installed")
GSAP = os.path.join(ROOT, "assets", "html", "gsap")
FILES = ["gsap.min.js", "SplitText.min.js", "DrawSVGPlugin.min.js", "MorphSVGPlugin.min.js"]
SCRIPTS = "".join('<script src="gsap/%s"></script>' % f for f in FILES) + '<script src="gsapseek.js"></script>'


def test_the_vendored_files_are_the_pinned_builds_with_their_licence():
    lic = open(os.path.join(GSAP, "LICENSE.md"), encoding="utf-8").read()
    assert "Standard \"No Charge\" GSAP License" in lic and "gsap@3.15.1" in lic
    for f in FILES:
        b = open(os.path.join(GSAP, f), "rb").read()
        assert hashlib.sha256(b).hexdigest() in lic, "%s differs from the pinned build (LICENSE.md)" % f
        head = b[:400].decode("utf-8")
        assert "3.15.1" in head and "gsap.com/standard-license" in head, "%s lost its banner" % f
    assert sorted(os.listdir(GSAP)) == sorted(FILES + ["LICENSE.md"])


def _page(d, body, script, css=""):
    shutil.copytree(GSAP, d / "gsap", dirs_exist_ok=True)
    shutil.copy(os.path.join(ROOT, "assets", "html", "gsapseek.js"), d)
    shutil.copy(os.path.join(ROOT, "assets", "fonts", "IBMPlexSans-VF.ttf"), d / "plex.ttf")
    (d / "film.html").write_text("""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face { font-family: "Plex"; src: url(plex.ttf); font-weight: 100 700; }
html, body { margin: 0; background: #0b0c0d; color: #f1efe9; }
#line { position: absolute; left: 0; right: 0; top: 700px; text-align: center; white-space: nowrap; font: 600 120px/1.15 Plex; }
#code { position: absolute; left: 0; right: 0; top: 100px; text-align: center; font: 600 260px/260px Plex; }
%s</style></head><body>%s%s<script>
window.filmReady = (async () => { try { %s } catch (e) { document.title = 'ERR ' + e.message; throw e; } return 'ok'; })();
</script></body></html>""" % (css, body, SCRIPTS, script))
    (d / "_plan.json").write_text(json.dumps({"video": "final.mp4", "fps": 30, "frames": 240}))
    return d


def _dom(d):
    r = subprocess.run([CHROME, "--headless=new", "--allow-file-access-from-files", "--window-size=1920,1080",
                        "--virtual-time-budget=5000", "--dump-dom", "file://%s" % (d / "film.html")],
                       capture_output=True, text=True, timeout=120)
    t = r.stdout[r.stdout.index("<title>") + 7:r.stdout.index("</title>")].replace("&quot;", '"').replace("&amp;", "&")
    return t


@needs_chrome
def test_the_vendored_scripts_load_as_classic_scripts_from_file_url(tmp_path):
    _page(tmp_path, "<title>-</title>", """
await GsapSeek.ready();
document.title = JSON.stringify({v: gsap.version, split: typeof SplitText, draw: typeof DrawSVGPlugin,
  morph: typeof MorphSVGPlugin, reg: ['drawSVG', 'morphSVG'].every((p) => !!gsap.plugins[p]),
  film: typeof GsapSeek.film(), proto: location.protocol});""")
    got = json.loads(_dom(tmp_path))
    assert got == {"v": "3.15.1", "split": "function", "draw": "object", "morph": "object", "reg": True,
                   "film": "object", "proto": "file:"}, got


@needs_chrome
def test_splitting_waits_for_the_fonts_and_lands_in_the_kerned_layout(tmp_path):
    # a second face no element uses at load: document.fonts.ready alone leaves it 'unloaded'
    css = '@font-face { font-family: "Later"; src: url(plex.ttf); }'
    _page(tmp_path, '<title>-</title><div id="line">AVATAR Type, yet</div>', """
let early = '', film0 = ''; try { GsapSeek.assemble(gsap.timeline({paused: true}), '#line', {at: 0}); } catch (e) { early = e.message; }
try { GsapSeek.film(); } catch (e) { film0 = e.message; }
const el = document.getElementById('line'), r = document.createRange(), want = [];
await GsapSeek.ready();
const later = [...document.fonts].find((f) => f.family === 'Later').status;
el.style.fontVariantLigatures = 'none';
const tn = el.firstChild; for (let i = 0; i < tn.length; i++) if (tn.data[i] !== ' ') { r.setStart(tn, i); r.setEnd(tn, i + 1); want.push(r.getBoundingClientRect().left); }
const film = GsapSeek.film(), split = GsapSeek.assemble(film, el, {at: 1});
GsapSeek.seek(film, 9);
const got = split.chars.map((c) => c.getBoundingClientRect().left);
const tr = split.chars[0].style.transform;
document.title = JSON.stringify({early, film0, later, n: [want.length, got.length],
  err: Math.max(...got.map((x, i) => Math.abs(x - want[i]))), moved: split.chars.filter((c) => c.style.left).length, tr});""",
          css=css)
    got = json.loads(_dom(tmp_path))
    assert "before GsapSeek.ready()" in got["early"] and "after `await GsapSeek.ready()`" in got["film0"], got
    assert got["later"] == "loaded", got
    assert got["n"][0] == got["n"][1] == 14, got
    assert got["moved"] >= 2, "AVATAR / Type have kerning pairs: the split must restore them"
    assert got["err"] < 0.02, got                          # the settled line IS the typeset line
    assert got["tr"].replace(" ", "") == "skew(0deg,0.05595deg)", got["tr"]   # the unlock stays on each letter at rest


@needs_chrome
def test_a_font_that_fails_and_a_tween_outside_the_film_are_refused(tmp_path):
    css = '@font-face { font-family: "Gone"; src: url(missing.ttf); }'
    _page(tmp_path, "<title>-</title>", """
let font = ''; await GsapSeek.ready().catch((e) => { font = e.message; });
document.title = JSON.stringify({font});""", css=css)
    assert "Gone" in json.loads(_dom(tmp_path))["font"]
    d2 = tmp_path / "b"
    d2.mkdir()
    _page(d2, '<title>-</title><div id="box"></div>', """
await GsapSeek.ready(); const film = GsapSeek.film();
gsap.to('#box', {x: 100, duration: 1});
let err = ''; try { GsapSeek.seek(film, 0.5); } catch (e) { err = e.message; }
document.title = JSON.stringify({err});""")
    assert "outside the film timeline" in json.loads(_dom(d2))["err"] and "#box" in json.loads(_dom(d2))["err"]


ALL_MOVES = """
await GsapSeek.ready(); const film = GsapSeek.film();
GsapSeek.roll(film, '#code', {at: 0.3, value: '1202'});
GsapSeek.trace(film, '#s rect', {at: 1.5});
film.fromTo('#s rect', {attr: {'fill-opacity': 0}}, {attr: {'fill-opacity': 1}, duration: 0.1, stagger: 0.1, immediateRender: true}, 2.6);
GsapSeek.reshape(film, '#m', '#tick', {at: 2.0});
GsapSeek.assemble(film, '#line', {at: 3.5});
window.seek = (t) => GsapSeek.seek(film, t);"""
ALL_BODY = """<div id="code">1202</div><div id="line">all eight were full</div>
<svg width="1920" height="1080" style="position:absolute;left:0;top:0">
<g id="s"><rect x="560" y="420" width="120" height="120" rx="12" fill="#ff9f1a" stroke="#f1efe9" stroke-width="5"/>
<rect x="720" y="420" width="120" height="120" rx="12" fill="#ff9f1a" stroke="#f1efe9" stroke-width="5"/></g>
<path id="m" d="M1400 540 L1460 420 L1520 540 Z" fill="#ff9f1a"/>
<path id="tick" d="M1390 480 L1440 530 L1530 430 L1540 440 L1440 545 L1380 490 Z" fill="none" visibility="hidden"/></svg>"""


def _shots(d, order):
    import _filmpage as fp
    port, srv = fp.serve(str(d))
    out = {}
    try:
        p = fp.FilmPage(port, "film.html")
        try:
            for i, t in enumerate(order):
                path = d / ("s_%d.png" % i)
                p.seek(t)
                p.shot(str(path), "png")
                out.setdefault(t, []).append(np.asarray(Image.open(path).convert("RGB")).astype(int))
        finally:
            p.close()
    finally:
        srv.shutdown()
    return out


@needs_chrome
def test_every_frame_is_a_function_of_t_in_any_order(tmp_path):
    _page(tmp_path, ALL_BODY, ALL_MOVES)
    times = [0.0, 0.6, 1.0, 1.8, 2.2, 2.75, 3.7, 4.0, 4.6, 8.0]
    seq = _shots(tmp_path, [2.0, 5.0, 2.0] + times)
    a, b = seq[2.0]
    assert np.array_equal(a, b), "seek 2.0 -> 5.0 -> 2.0 drew a different 2.0"
    shuffled = times[:]
    random.Random(7).shuffle(shuffled)      # its first seek (4.6) is past the first letters' landing: the case where
    sh = _shots(tmp_path, shuffled)         # an unlock on the PARENT drew 3.7 a quarter pixel off (see gsapseek.js)
    back = _shots(tmp_path, times[::-1])    # and a page that starts at the end and runs backwards
    bad = [t for t in times if not (np.array_equal(seq[t][0], sh[t][0]) and np.array_equal(seq[t][0], back[t][0]))]
    assert not bad, "frames at t=%s depend on the order of seeks" % bad
    # every move really moved: frames differ across the film, and the settled end is not the start
    assert not np.array_equal(seq[0.0][0], seq[8.0][0]) and not np.array_equal(seq[2.2][0], seq[4.0][0])


@needs_chrome
def test_nothing_moves_on_its_own_between_seeks(tmp_path):
    _page(tmp_path, ALL_BODY, ALL_MOVES + "\nwindow.idle = (ms) => new Promise((r) => setTimeout(r, ms));")
    import _filmpage as fp
    port, srv = fp.serve(str(tmp_path))
    try:
        p = fp.FilmPage(port, "film.html")
        try:
            p.seek(0.5)          # mid-roll and before every other move: anything ticking would change this frame
            p.shot(str(tmp_path / "a.png"), "png")
            p.ev("window.idle(1200)", True)
            p.ev("new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))", True)
            p.shot(str(tmp_path / "b.png"), "png")
        finally:
            p.close()
    finally:
        srv.shutdown()
    a, b = (np.asarray(Image.open(tmp_path / n).convert("RGB")) for n in ("a.png", "b.png"))
    assert np.array_equal(a, b), "the picture changed with no seek: GSAP's ticker moved something"


GLIDE = """
await GsapSeek.ready(); const film = GsapSeek.film();
let c0;
if (%s) {           // the control: the same letters, the same move, by GSAP without the unlock
  const sp = SplitText.create('#line', {type: 'chars'}); c0 = sp.chars[0];
  film.fromTo(sp.chars, {yPercent: -30}, {yPercent: 0, duration: 3, ease: 'none', immediateRender: true}, 0);
} else c0 = GsapSeek.assemble(film, '#line', {at: 0, rise: -30, tilt: 0, dur: 3, ease: 'none', each: 0}).chars[0];
window.c0 = c0;
window.seek = (t) => { GsapSeek.seek(film, t); window.trueY = c0.getBoundingClientRect().top; };"""


def _glide_residual(d):
    """RMS (px) of the first letter's ink centroid against its true (DOM) place, over 60 slow frames."""
    import _filmpage as fp
    port, srv = fp.serve(str(d))
    ys, truth = [], []
    try:
        p = fp.FilmPage(port, "film.html")
        try:
            for f in range(15, 75):              # ~0.46 px a frame: where a snapped baseline steps
                p.seek(f / 30)
                truth.append(p.ev("window.trueY"))
                p.shot(str(d / "g.png"), "png")
                im = np.asarray(Image.open(d / "g.png").convert("L")).astype(float)
                box = im[600:900, 0:1920]
                x0 = int(p.ev("window.c0.getBoundingClientRect().left"))
                box = box[:, max(0, x0 - 10):x0 + 90]
                w = np.clip(box - 30, 0, None)
                ys.append(float((w.sum(1) * np.arange(w.shape[0])).sum() / w.sum()))
        finally:
            p.close()
    finally:
        srv.shutdown()
    ys, truth = np.array(ys), np.array(truth)
    A = np.vstack([truth, np.ones_like(truth)]).T
    k, c = np.linalg.lstsq(A, ys, rcond=None)[0]
    return float(np.sqrt(np.mean((ys - (k * truth + c)) ** 2)))


@needs_chrome
def test_a_slow_letter_glides_with_the_unlock_and_steps_without_it(tmp_path):
    body = '<div id="line">Hold the line</div>'
    (tmp_path / "on").mkdir()
    (tmp_path / "off").mkdir()
    on = _glide_residual(_page(tmp_path / "on", body, GLIDE % "false"))
    off = _glide_residual(_page(tmp_path / "off", body, GLIDE % "true"))
    # a whole-pixel staircase is ~0.29 px RMS (1/sqrt(12)); Skia's quarter-pixel positioning floor is ~0.07
    assert off > 0.2, "the control did not step (%.3f px): the measurement is blind" % off
    assert on < 0.11, "a split letter steps under the unlock: %.3f px RMS (control %.3f)" % (on, off)
