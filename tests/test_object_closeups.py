"""The film's object close-up sheet (scripts/object_closeups.py) and the dead-screen warning it feeds
(device_fidelity_qa.dead_screens). Pure parts, on hand-made censuses and pictures — no render."""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import object_closeups as oc        # noqa: E402
import device_fidelity_qa as dq     # noqa: E402
import critic_brief as cb           # noqa: E402

W, H = 1920, 1080


def _beat(f):
    return 0 if f < 100 else 1


def test_each_object_is_taken_at_the_frame_where_it_is_largest_in_each_beat():
    frames = {
        0: {"o": [["device:macbook-pro-14", 100, 100, 300, 200, 1.0], ["bots", 0, 0, 50, 50, 1.0]]},
        30: {"o": [["device:macbook-pro-14", 90, 90, 600, 400, 1.0]]},
        60: {"o": [["device:macbook-pro-14", 0, 0, 900, 700, 0.3]]},          # bigger, but fading: not looked at
        120: {"o": [["device:macbook-pro-14", 10, 10, 200, 100, 1.0]]},       # another beat: its own close-up
    }
    best = oc.pick(frames, _beat, W, H)
    assert best[(0, "device:macbook-pro-14")]["frame"] == 30
    assert best[(0, "device:macbook-pro-14")]["seen"] == 2
    assert best[(1, "device:macbook-pro-14")]["frame"] == 120
    assert best[(0, "bots")]["frame"] == 0


def test_a_still_object_is_taken_settled_and_a_seam_does_not_list_it_twice():
    rows = {f: {"o": [["device:watch", 100, 100, 400, 800, 1.0]]} for f in range(0, 90, 3)}
    rows.update({f: {"o": [["device:watch", 100, 100, 400, 800, 1.0]]} for f in (102, 105)})   # carried by a seam
    best = oc.pick(rows, _beat, W, H)
    assert best[(0, "device:watch")]["frame"] == 45                                           # the middle, not frame 0
    assert (1, "device:watch") not in best


def test_a_box_is_clipped_to_the_frame_and_a_tiny_or_offscreen_one_is_not_looked_at():
    frames = {0: {"o": [["plane", -100, -50, 300, 200, 1.0], ["dot", 10, 10, 12, 12, 1.0],
                        ["gone", W + 10, 0, 300, 300, 1.0]]}}
    best = oc.pick(frames, _beat, W, H)
    assert best[(0, "plane")]["box"] == [0, 0, 200, 150]
    assert (0, "dot") not in best and (0, "gone") not in best


def test_tiles_are_packed_at_their_own_size_never_scaled():
    pos, (sw, sh) = oc.pack([(1000, 300), (1000, 300), (3000, 500), (200, 100)], max_w=2400, gap=10)
    assert pos[0] == (10, 10) and pos[1] == (1020, 10)
    assert pos[2] == (10, 320)                     # too wide for any row: a row of its own, at full size
    assert pos[3][1] == 830 and sw >= 3020


def test_the_sheet_shows_the_delivered_pixels_at_100_percent(tmp_path):
    rng = np.random.default_rng(7)
    px = rng.integers(0, 255, (H, W, 3), dtype=np.uint8)
    fp = tmp_path / "f.png"
    Image.fromarray(px).save(fp)
    item = {"name": "device:macbook-pro-14", "beat": 7, "label": "device · beat 7", "frame": 5,
            "box": [400, 300, 320, 180]}
    out = tmp_path / "sheet.png"
    oc.build_sheet([item], {5: str(fp)}, str(out))
    sheet = np.asarray(Image.open(out).convert("RGB"))
    x0, y0, x1, y1 = oc.crop_box(item["box"], W, H)
    crop = px[y0:y1, x0:x1]
    ox, oy = oc.pack([(crop.shape[1], crop.shape[0] + oc.LABEL_H)])[0][0]
    got = sheet[oy + oc.LABEL_H:oy + oc.LABEL_H + crop.shape[0], ox:ox + crop.shape[1]]
    assert got.shape == crop.shape and np.array_equal(got, crop)


def _film(tmp_path, objects):
    d = tmp_path / "film"
    d.mkdir()
    (d / "out.mp4").write_bytes(b"not really a film, but its bytes are what the record pins")
    rec = {"film": oc.film_sha(str(d / "out.mp4")), "fps": 30, "objects": objects, "screens": {}}
    (d / oc.RECORD).write_text(json.dumps(rec), encoding="utf-8")
    Image.new("RGB", (40, 40)).save(d / oc.SHEET)
    return d


def test_the_brief_says_a_missing_or_stale_sheet_and_lists_every_object_of_a_current_one(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert oc.status(str(empty)) == "missing"
    assert "MISSING" in cb.closeup_lines(str(empty))[0]
    objs = [{"name": "device:macbook-pro-14", "beat": 7, "shot": "WristRelay", "t": 30.5, "box": [1, 2, 600, 400]},
            {"name": "paper plane", "beat": 8, "shot": "PaperPlane", "t": 35.0, "box": [1, 2, 90, 90]}]
    d = _film(tmp_path, objs)
    assert oc.status(str(d)) == "ok"
    lines = cb.closeup_lines(str(d))
    assert "EVERY object" in lines[0]
    assert any("device:macbook-pro-14" in ln for ln in lines) and any("paper plane" in ln for ln in lines)
    (d / "out.mp4").write_bytes(b"a re-render")
    assert oc.status(str(d)) == "stale"
    assert "STALE" in cb.closeup_lines(str(d))[0]


def _ui_crop():
    im = Image.new("L", (420, 280), 30)
    dr = ImageDraw.Draw(im)
    font = ImageFont.load_default()
    for i in range(9):
        dr.text((20, 18 + i * 28), "Codex  有新回复  42 tests · 回到会话 %d" % i, fill=235, font=font)
    dr.rectangle((300, 230, 400, 260), fill=150)
    return np.asarray(im)


def test_a_flat_or_wallpaper_screen_says_nothing_and_real_ui_does():
    flat = np.full((280, 420), 18, dtype=np.uint8)
    yy, xx = np.mgrid[0:280, 0:420]
    wall = (60 + 120 * (xx / 420.0) * 0.7 + 50 * (yy / 280.0)).astype(np.uint8)    # a smooth wallpaper gradient
    assert dq.edge_density(flat) < dq.DEAD_EDGE
    assert dq.edge_density(wall) < dq.DEAD_EDGE
    assert dq.edge_density(_ui_crop()) > dq.DEAD_EDGE * 3
    assert dq.dead_verdict([0.0, 0.001, 0.02])[0] is True
    assert dq.dead_verdict([0.0, 0.02, 0.03])[0] is False


def test_dead_screens_warns_for_the_screen_that_shows_nothing_and_not_for_the_one_with_ui(tmp_path):
    d = tmp_path / "film"
    d.mkdir()
    frame = np.full((H, W), 20, dtype=np.uint8)
    yy, xx = np.mgrid[0:300, 0:500]
    frame[100:400, 100:600] = (40 + 0.2 * xx + 0.1 * yy).astype(np.uint8)              # the Mac: a wallpaper only
    ui = np.asarray(Image.fromarray(_ui_crop()).resize((500, 300)))
    frame[500:800, 1000:1500] = ui                                                        # the phone: its real UI
    rows_mac = [[f, 100, 100, 500, 300, 7] for f in range(0, 60, 3)]
    rows_phone = [[f, 1000, 500, 500, 300, 6] for f in range(0, 60, 3)]
    rec = {"fps": 30, "screens": {"screen:macbook-pro-14": rows_mac, "screen:iphone-18-pro": rows_phone}}
    (d / "_object_closeups.json").write_text(json.dumps(rec), encoding="utf-8")
    warns = dq.dead_screens(str(d), read=lambda f: frame)
    assert len(warns) == 1, warns
    assert "beat 7" in warns[0] and "macbook-pro-14" in warns[0] and "real UI" in warns[0]


def test_no_record_no_dead_screen_claim(tmp_path):
    assert dq.dead_screens(str(tmp_path)) == []
