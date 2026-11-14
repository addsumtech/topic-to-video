"""promo_capture: boxes found in a screenshot with no DOM, a logo cut to alpha, a local page captured with its boxes."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import promo_capture as pc  # noqa: E402


def _ui(path, cards, ground=(250, 250, 250), size=(1200, 800)):
    """A 2x 'app screenshot': flat ground, cards with a 1 px edge and a few lines of 'text' inside."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (size[0] * 2, size[1] * 2), ground)
    d = ImageDraw.Draw(im)
    for (x, y, w, h, fill) in cards:
        d.rounded_rectangle([x * 2, y * 2, (x + w) * 2, (y + h) * 2], radius=16, fill=fill, outline=(214, 214, 214), width=2)
        for k in range(2):
            d.rectangle([x * 2 + 24, y * 2 + 30 + k * 34, x * 2 + 24 + w, y * 2 + 46 + k * 34], fill=(40, 40, 40))
    im.save(path)


def test_boxes_are_found_where_the_cards_are(tmp_path):
    cards = [(40, 60, 300, 120, (255, 255, 255)), (380, 60, 300, 120, (255, 255, 255)), (40, 220, 640, 160, (240, 246, 255))]
    p = str(tmp_path / "ui.png")
    _ui(p, cards)
    lay = pc.find_boxes(p)
    found = [(e["x"], e["y"], e["w"], e["h"]) for e in lay["elements"]]
    for (x, y, w, h, _) in cards:
        assert any(abs(fx - x) <= 3 and abs(fy - y) <= 3 and abs(fw - w) <= 4 and abs(fh - h) <= 4 for fx, fy, fw, fh in found), (
            (x, y, w, h), found)
    assert lay["w"] == 1200 and lay["h"] == 800
    assert [e["id"] for e in lay["elements"]] == list(range(len(lay["elements"])))


def test_a_flat_page_has_no_boxes(tmp_path):
    p = str(tmp_path / "flat.png")
    _ui(p, [])
    assert pc.find_boxes(p)["elements"] == []


def test_a_mark_is_cut_to_alpha_without_a_halo(tmp_path):
    from PIL import Image, ImageDraw
    import numpy as np
    p = str(tmp_path / "page.png")
    big = Image.new("RGB", (1600, 800), (255, 255, 255))           # drawn 4x and sampled down: an anti-aliased edge
    ImageDraw.Draw(big).ellipse([240, 240, 560, 560], fill=(105, 101, 219))
    big.resize((400, 200), Image.LANCZOS).save(p)
    info = pc.cut_mark(p, (20, 20, 80, 60), str(tmp_path / "m.png"))
    m = np.asarray(Image.open(tmp_path / "m.png"))
    assert m.shape[2] == 4 and info["ground"] == "#ffffff"
    assert m[0, 0, 3] == 0                                    # the ground is gone
    c = m[(100 - 40), (100 - 40)]                             # the disc's middle (crop starts at 2x (40, 40))
    assert c[3] == 255 and abs(int(c[2]) - 219) <= 3          # ...a MID-TONE ink stays opaque at its own colour
    rim = m[:, :, 3][(m[:, :, 3] > 0) & (m[:, :, 3] < 255)]
    assert rim.size > 0                                       # the anti-aliased rim is partial, not cut hard
    edge_rgb = m[(m[:, :, 3] > 0) & (m[:, :, 3] < 128)][:, :3].astype(int)
    assert (abs(edge_rgb - [105, 101, 219]).max(1) <= 12).all()   # ...and keeps the ink's colour: no white halo
    with pytest.raises(SystemExit):
        pc.cut_mark(p, (150, 5, 40, 20), str(tmp_path / "none.png"))   # an empty box names itself


@pytest.mark.skipif(not pc.find_chrome(), reason="no Chrome")
def test_a_local_page_is_captured_with_its_boxes_and_own_words(tmp_path):
    html = tmp_path / "p.html"
    html.write_text("""<!doctype html><html><head><title>Demo Board</title><meta name="description" content="A board for testing.">
<style>body{margin:0;background:#fff;font:16px sans-serif}.card{position:absolute;border:1px solid #ddd;border-radius:10px;background:#f6f6f6}</style>
</head><body><button style="position:absolute;left:40px;top:30px;width:120px;height:40px">Share</button>
<div class="card" style="left:40px;top:120px;width:300px;height:160px">Card one</div>
<div class="card" style="left:380px;top:120px;width:300px;height:160px">Card two</div></body></html>""")
    lay = pc.capture_web(str(tmp_path), "file://" + str(html), "p", W=800, H=500, wait=0.2)
    assert lay["title"] == "Demo Board" and lay["description"] == "A board for testing."
    assert (lay["w"], lay["h"]) == (800, 500)
    from PIL import Image
    with Image.open(tmp_path / "caps" / "p.png") as im:
        assert im.size == (1600, 1000)                         # a 2x capture
    boxes = {(e["x"], e["y"], e["w"], e["h"]): e for e in lay["elements"]}
    assert (40, 30, 120, 40) in boxes and boxes[(40, 30, 120, 40)]["text"] == "Share"
    near = lambda b: any(abs(k[0] - b[0]) <= 2 and abs(k[1] - b[1]) <= 2 and abs(k[2] - b[2]) <= 2 and abs(k[3] - b[3]) <= 2 for k in boxes)
    assert near((40, 120, 300, 160)) and near((380, 120, 300, 160))     # border-box: a 1 px border is part of the card
    saved = json.load(open(tmp_path / "caps" / "p.layout.json"))
    assert saved["src"] == "caps/p.png" and saved["elements"] == lay["elements"]


@pytest.mark.parametrize("js", ["a=1 ;;; b=2", "a=1;;;b=2", "a=1\n;;;\nb=2", "a=1\n  ;;;  \nb=2\n;;;\n"])
def test_eval_steps_split_however_the_separator_is_written(js):
    # the docs wrote "js ;;; js" on one line and the split wanted "\n;;;\n": `;;;` is valid JS, so the steps ran
    # silently as ONE (no settle between them, only the last value returned)
    assert pc.split_steps(js) == ["a=1", "b=2"]


def test_hires_items_resolve_by_text_selector_box_or_id(capsys):
    els = [{"id": 0, "x": 0, "y": 0, "w": 800, "h": 400, "text": "Compress MozJPEG 862 kB", "tag": "div"},
           {"id": 1, "x": 600, "y": 300, "w": 120, "h": 30, "text": "862 kB", "tag": "span"}]
    css = lambda sel: {"x": 5, "y": 6, "w": 7, "h": 8} if sel == "#export" else None  # noqa: E731 (no page: text: uses the layout)
    out = pc._hires_boxes("text:862 KB;css:#export;10,20,30,40;0", els, css)
    assert out[0] == {"x": 600, "y": 300, "w": 120, "h": 30}          # the SMALLEST element holding the text
    assert out[1] == {"x": 5, "y": 6, "w": 7, "h": 8}
    assert out[2] == {"x": 10.0, "y": 20.0, "w": 30.0, "h": 40.0}
    assert out[3]["w"] == 800
    said = capsys.readouterr().out
    assert said.count("--hires") == 4 and "ids shift between captures" in said
    with pytest.raises(SystemExit):
        pc._hires_boxes("text:nowhere", els, css)
    with pytest.raises(SystemExit):
        pc._hires_boxes("css:#nope", els, css)


@pytest.mark.skipif(not pc.find_chrome(), reason="no Chrome")
def test_parts_are_captured_on_their_own_with_the_films_demo_text(tmp_path):
    html = tmp_path / "p.html"
    html.write_text("""<!doctype html><html><body style="margin:0;background:#eee;font:16px sans-serif">
<div id="card" style="position:absolute;left:60px;top:50px;width:300px;height:140px;border-radius:18px;background:#fff">
<input id="q" style="margin:20px;width:240px;font-size:18px"><div id="res">nothing yet</div></div></body></html>""")
    lay = pc.capture_web(str(tmp_path), "file://" + str(html), "p", W=600, H=400, wait=0.2,
                         js="__ttv.fill('#q', 'hello film') ;;; __ttv.text('#res', 'Result: 3 matches') ;;; document.querySelector('#q').value",
                         parts_spec="card=css:#card;result=text:Result: 3 matches")
    assert lay["eval"][-1] == "hello film"                                # the film's own demo state, in the page
    card, res = lay["parts"]["card"], lay["parts"]["result"]
    assert (card["w"], card["h"], card["radius"]) == (300, 140, 18) and card["bg"] == "rgb(255, 255, 255)"
    from PIL import Image
    with Image.open(tmp_path / card["src"]) as im:
        assert im.size == (1200, 560)                                     # 4x: staged large, still sharp
    assert res["h"] < 40 and (tmp_path / res["src"]).is_file()        # the result LINE, not the card holding it
