"""picture_legibility_qa: a picture on screen that shows almost nothing (a near-black block under its icon, the MRI
film's recap 2026-11-19) is reported, on the page and on a stage3d panel; a real picture, an intended blank, a dip to
black and a picture passing for a moment are not."""
import json
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common  # noqa: E402
import picture_legibility_qa as pl  # noqa: E402

needs_chrome = pytest.mark.skipif(not _common.find_chrome(), reason="Chrome not installed")

# a canvas filled with noise (a real picture) or one flat colour (a picture that shows nothing)
_DRAW = """
function paint(id, flat) { const c = document.getElementById(id), g = c.getContext('2d');
  if (flat) { g.fillStyle = flat; g.fillRect(0, 0, c.width, c.height); return; }
  for (let y = 0; y < c.height; y += 8) for (let x = 0; x < c.width; x += 8) {
    const v = Math.floor(Math.abs(Math.sin(x * 12.9898 + y * 78.233) * 43758.5453) % 1 * 255);
    g.fillStyle = 'rgb(' + v + ',' + v + ',' + v + ')'; g.fillRect(x, y, 8, 8); } }
"""


def _film(d, body, script, frames=60):
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), d)
    (d / "film.html").write_text("<!doctype html><html><head><meta charset='utf-8'></head>"
                                 "<body style='margin:0;width:1920px;height:1080px;background:#3a4250'>%s"
                                 "<script src='stage3d.js'></script><script>%s%s</script></body></html>" % (body, _DRAW, script))
    (d / "_plan.json").write_text(json.dumps({"video": "final.mp4", "fps": 30, "frames": frames}))


def _canvas(id_, x, extra=""):
    return "<canvas id='%s' width='400' height='300' style='position:absolute;left:%dpx;top:300px' %s></canvas>" % (id_, x, extra)


def test_the_measure_separates_a_flat_block_from_a_picture():
    from PIL import Image
    import numpy as np
    flat = Image.new("RGB", (400, 300), (12, 12, 14))
    rng = np.random.default_rng(1)
    pic = Image.fromarray((rng.random((300, 400, 3)) * 255).astype("uint8")).resize((400, 300))
    assert pl.unreadable(*pl.measure(flat, [0, 0, 400, 300]))
    assert not pl.unreadable(*pl.measure(pic, [0, 0, 400, 300]))


def test_two_samples_make_a_span_and_one_does_not():
    hits = [(120.47, "a", 2.9, 8.0), (120.97, "a", 2.9, 8.0), (130.0, "b", 1.0, 2.0)]
    assert [(n, round(s, 2), round(e, 2)) for n, s, e, _sd, _sp in pl.spans(hits, 0.5)] == [("a", 120.47, 121.47)]


@needs_chrome
def test_a_dark_block_among_real_pictures_is_reported(tmp_path, capsys):
    _film(tmp_path, _canvas("a", 100) + _canvas("b", 700) + _canvas("c", 1300),
          "paint('a'); paint('b'); paint('c', '#0b0c0e'); window.seek = () => {};")
    assert pl.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert out.count("UNREADABLE") == 1 and "'c' shows almost nothing" in out, out


@needs_chrome
def test_an_intended_blank_and_real_pictures_pass(tmp_path):
    _film(tmp_path, _canvas("a", 100) + _canvas("b", 700) + _canvas("c", 1300, "data-blank-ok"),
          "paint('a'); paint('b'); paint('c', '#0b0c0e'); window.seek = () => {};")
    assert pl.main([str(tmp_path)]) == 0


@needs_chrome
def test_a_dip_to_black_is_not_an_unreadable_picture(tmp_path):
    # the whole frame goes black (a seam): the picture is not being shown, empty_frame_qa judges the hold
    _film(tmp_path, _canvas("a", 700) + "<div style='position:absolute;inset:0;background:#000'></div>",
          "paint('a'); window.seek = () => {};")
    assert pl.main([str(tmp_path)]) == 0


@needs_chrome
def test_a_dark_stage_panel_is_reported(tmp_path, capsys):
    # a card in a stage3d scene whose picture is one flat dark colour, beside one that shows a real picture
    _film(tmp_path, "<canvas id='st' width='1920' height='1080' style='position:absolute;left:0;top:0'></canvas>"
                    + _canvas("pa", -2000) + _canvas("pb", -2000),
          """paint('pa'); paint('pb', '#08090a');
             window.filmReady = (async () => { const st = Stage3D.create({canvas: document.getElementById('st')}); st.studio();
               st.card(document.getElementById('pa'), {width: 1.6, x: -1.1, y: 0.2, name: 'lit'});
               st.card(document.getElementById('pb'), {width: 1.6, x: 1.1, y: 0.2, name: 'dark'});
               await st.ready(); window.seek = () => st.render({pos: [0, 0.2, 3.2], look: [0, 0.2, 0], fov: 50}); window.seek(0); return 'ok'; })();""")
    assert pl.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "stage panel dark" in out and "stage panel lit" not in out, out
