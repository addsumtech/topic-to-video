"""DeviceDemo on real frames: the tap lands on its target, the caret stays at the typing head, a scroll ends
with no blank past the last row, and the push-in makes the target's text as tall as a caption.

Each of these is a defect the design mockups themselves shipped before they were caught by a screenshot —
so each is measured on the render, never inferred from the code."""
import json
import os
import shutil
import subprocess
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")
FONT = os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf")
from _caption_band import caption_band_px    # noqa: E402 — scripts/ is on the path from the line above
ACCENT_PRODUCT = None     # read from the rendered pixels, not restated


def _screenshot(path, h=2532, rows=12):
    im = Image.new("RGB", (1170, h), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 46)
    d.rounded_rectangle([60, 200, 1110, 320], radius=36, fill=(238, 241, 244))
    d.text((110, 232), "搜索反馈", fill=(140, 147, 160), font=f)
    for i in range(rows):
        y = 420 + i * 180
        d.text((90, y), "第%d条反馈" % (i + 1), fill=(20, 23, 28), font=f)
        d.line([(60, y + 120), (1110, y + 120)], fill=(222, 226, 232), width=3)
    im.save(path)
    return path


def _render(tmp_path, props, frame, name, aspect="16:9"):
    pf = tmp_path / (name + ".json")
    pf.write_text(json.dumps(dict(props, dna="product", aspect=aspect), ensure_ascii=False), encoding="utf-8")
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DeviceDemo", png, "--frame=%d" % frame,
                        "--gl=angle", "--log=error", "--props=" + str(pf), "--public-dir=" + str(tmp_path)],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
    return png


def _geom(W=1920, H=1080, kind="phone", look="flat"):
    import device_geometry as dg
    return dg.geometry(kind, look, W, H)["screen"]


def _accent_centroid(png):
    np = pytest.importorskip("numpy")
    a = np.asarray(Image.open(png).convert("RGB"), dtype=int)
    blue = (a[..., 2] > 150) & (a[..., 2] - a[..., 0] > 70) & (a[..., 2] - a[..., 1] > 30)
    ys, xs = np.nonzero(blue)
    return (float(xs.mean()), float(ys.mean())) if len(xs) > 40 else None


BASE = {"device": "phone", "look": "flat", "camera": "still"}


@needs_toolchain
def test_the_tap_lands_on_its_target(tmp_path):
    _screenshot(str(tmp_path / "ui.png"))
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"tap": [0.3, 0.2], "t0": 0.3, "ta": 0.4, "t1": 0.7}]
    png = _render(tmp_path, dict(BASE, steps=steps), 72, "tap")
    s = _geom()
    c = _accent_centroid(png)
    assert c is not None, "no tap ring was drawn"
    tx, ty = s["x"] + 0.3 * s["w"], s["y"] + 0.2 * s["h"]
    assert abs(c[0] - tx) < s["w"] * 0.06 and abs(c[1] - ty) < s["h"] * 0.03, (c, (tx, ty))


@needs_toolchain
def test_the_caret_sits_at_the_typing_head(tmp_path):
    np = pytest.importorskip("numpy")
    _screenshot(str(tmp_path / "ui.png"))
    field = {"box": [60 / 1170, 200 / 2532, 1110 / 1170, 320 / 2532], "bg": "#eef1f4", "ink": "#111111",
             "textFrac": 46 / 1170}
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"type": "上周的客户反馈", "into": [0.5, 0.1], "field": field, "t0": 0.25, "ta": 0.3, "t1": 0.7}]
    png = _render(tmp_path, dict(BASE, steps=steps), 100, "type")
    s = _geom()
    a = np.asarray(Image.open(png).convert("RGB"), dtype=int)
    y0, y1 = int(s["y"] + s["h"] * 200 / 2532), int(s["y"] + s["h"] * 320 / 2532)
    band = a[y0:y1, s["x"]:s["x"] + s["w"]]
    dark = (band.sum(axis=2) < 200).any(axis=0)
    blue = ((band[..., 2] > 150) & (band[..., 2] - band[..., 0] > 70)).any(axis=0)
    assert dark.any() and blue.any(), "no typed text or no caret in the field"
    text_right, caret_x = int(np.flatnonzero(dark).max()), int(np.flatnonzero(blue).mean())
    assert 0 <= caret_x - text_right <= max(8, s["w"] * 0.02), (text_right, caret_x)


@needs_toolchain
def test_long_typed_text_stays_inside_its_field(tmp_path):
    np = pytest.importorskip("numpy")
    _screenshot(str(tmp_path / "ui.png"))
    field = {"box": [60 / 1170, 200 / 2532, 1110 / 1170, 320 / 2532], "bg": "#eef1f4", "ink": "#111111",
             "textFrac": 46 / 1170}
    long = "上周所有产品线的客户反馈以及它们最常提到的问题"
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"type": long, "into": [0.5, 0.1], "field": field, "t0": 0.2, "ta": 0.25, "t1": 0.8}]
    png = _render(tmp_path, dict(BASE, steps=steps), 120, "long")      # mid-typing: the caret is solid
    s = _geom()
    a = np.asarray(Image.open(png).convert("RGB"), dtype=int)
    y0, y1 = int(s["y"] + s["h"] * 200 / 2532), int(s["y"] + s["h"] * 320 / 2532)
    band = a[y0:y1, :]
    blue = ((band[..., 2] > 150) & (band[..., 2] - band[..., 0] > 70)).any(axis=0)
    xs = np.flatnonzero(blue)
    right = s["x"] + s["w"] * 1110 / 1170
    assert len(xs) and xs.max() <= right, "the caret left the field (x=%d, field ends %d)" % (xs.max(), right)


@needs_toolchain
def test_a_scroll_ends_with_the_last_row_on_the_screen_and_no_blank(tmp_path):
    np = pytest.importorskip("numpy")
    long = _screenshot(str(tmp_path / "long.png"), h=6000, rows=30)
    im = Image.open(long).convert("RGB")      # a dark footer on the image's last 40 px: only a scroll that ends
    ImageDraw.Draw(im).rectangle([0, 5960, 1169, 5999], fill=(20, 23, 28))   # exactly at the end shows it
    im.save(long)                             # on the screen's last rows (short of it: hidden; past it: a gap)
    steps = [{"screen": {"image": "long.png"}, "imageW": 1170, "imageH": 6000, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"scroll": 1.0, "t0": 0.2, "ta": 0.3, "t1": 0.7}]
    png = _render(tmp_path, dict(BASE, steps=steps), 170, "scroll")
    s = _geom()
    a = np.asarray(Image.open(png).convert("L"), dtype=int)
    bottom = a[s["y"] + s["h"] - 8:s["y"] + s["h"] - 2, s["x"] + 40:s["x"] + s["w"] - 40]
    assert (bottom < 100).mean() > 0.9, "the image's last rows are not on the screen's bottom edge after the scroll"


@needs_toolchain
def test_the_push_in_makes_the_target_text_caption_tall(tmp_path):
    import screen_media as sm
    ui = _screenshot(str(tmp_path / "ui.png"))
    cap = sm.caption_ink_px("zh", 1920, 1080)
    y = (420 + 6 * 180 + 30) / 2532                     # a mid-screen row: the camera clamp does not move it
    ink = sm.text_band_px(ui, 0.3, y)                    # measured, exactly as prepare() measures it
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"tap": [0.3, y], "t0": 0.3, "ta": 0.45, "t1": 0.75, "focus": [0.3, y],
              "textFrac": ink / 1170, "captionPx": cap}]
    props = {"device": "phone", "look": "flat", "steps": steps}
    png = _render(tmp_path, props, 100, "zoom")
    # the camera centres the target in its VIEW — the zone above the caption band — not in the frame
    band = sm.text_band_px(png, 0.5, (1080 - caption_band_px(1920, 1080)) / 2.0 / 1080)
    assert band is not None and band >= cap * 0.85, (band, cap)


@needs_toolchain
def test_the_standalone_demo_renders_without_a_script(tmp_path):
    _render(tmp_path, {}, 90, "demo")


@needs_toolchain
def test_a_push_in_near_the_top_stays_on_the_device(tmp_path):
    """Pushing in on the search bar (the spec's own `into: [0.5, 0.11]`) with the camera clamped to the FRAME
    left a third of the frame as dark background above and beside the phone, the target off-centre. Clamped
    to the device, the view's top edge is the phone's own top."""
    import screen_media as sm
    np = pytest.importorskip("numpy")
    ui = _screenshot(str(tmp_path / "ui.png"))
    cap = sm.caption_ink_px("zh", 1920, 1080)
    y = 255 / 2532                                        # the search bar's placeholder line
    ink = sm.text_band_px(ui, 0.2, y)
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"tap": [0.2, y], "t0": 0.3, "ta": 0.45, "t1": 0.75, "focus": [0.2, y],
              "textFrac": ink / 1170, "captionPx": cap}]
    png = _render(tmp_path, {"device": "phone", "look": "flat", "steps": steps}, 100, "edge")
    a = np.asarray(Image.open(png).convert("L"), dtype=float)
    top = a[: int(a.shape[0] * 0.05), int(a.shape[1] * 0.35): int(a.shape[1] * 0.65)]
    assert top.mean() > 150, "the top of a push-in near the device's edge is background (mean %.0f)" % top.mean()


@needs_toolchain
def test_the_device_at_rest_draws_inside_its_body(tmp_path):
    """deviceGeometry fits the body to the content zone exactly — a phone's bottom IS contentBottom — and the
    realistic look drew its metal ring OUTSIDE the lid: for a phone or a tablet, whose face is its whole body,
    10 px into the caption band on every frame. At rest, no bright pixel of any device leaves its body."""
    np = pytest.importorskip("numpy")
    import device_geometry as dg
    for kind in ("phone", "tablet", "laptop", "monitor"):
        b = dg.geometry(kind, "real", 1920, 1080)["body"]
        png = _render(tmp_path, {"device": kind, "look": "real"}, 2, "rest_" + kind)
        a = np.asarray(Image.open(png).convert("L"), dtype=int)
        out = a > 40            # the ground peaks at 22; the ring's darker band is 89, so a cut at 90 missed it
        out[max(0, b["y"] - 2):b["y"] + b["h"] + 2, max(0, b["x"] - 2):b["x"] + b["w"] + 2] = False
        assert not out.any(), "%s: %d device pixels outside the body %r" % (kind, out.sum(), b)


@needs_toolchain
def test_a_push_in_near_a_lid_edge_stays_on_the_lid(tmp_path):
    """A laptop's body is as wide as its BASE, which overhangs the lid; a monitor's body runs down its stand.
    With the push-in clamped to the body, a target on a laptop screen's left edge showed 280 px of background
    beside the lid, and one on a monitor's bottom row showed the empty ground around the stand. The zoomed view
    stays on the face — the screen and its bezel."""
    np = pytest.importorskip("numpy")
    for kind, (iw, ih), focus, strip in (("laptop", (1920, 1200), [0.0286, 0.481], "left"),
                                         ("monitor", (1920, 1080), [0.5, 0.97], "bottom")):
        Image.new("RGB", (iw, ih), "white").save(str(tmp_path / (kind + ".png")))
        # a tiny text height forces the largest push-in (maxZoom), where the leak was widest
        steps = [{"screen": {"image": kind + ".png"}, "imageW": iw, "imageH": ih, "t0": 0.06, "ta": 0.06, "t1": 0.2},
                 {"tap": focus, "t0": 0.3, "ta": 0.45, "t1": 0.75, "focus": focus, "textFrac": 0.003,
                  "captionPx": 41.0}]
        png = _render(tmp_path, {"device": kind, "look": "flat", "steps": steps}, 100, "lid_" + kind)
        a = np.asarray(Image.open(png).convert("L"), dtype=float)
        H, W = a.shape
        cb = H - caption_band_px(W, H)                     # the view ends where the caption band begins
        band = a[:cb, : int(W * 0.03)] if strip == "left" else np.concatenate(
            [a[cb - int(H * 0.03):cb, : int(W * 0.25)], a[cb - int(H * 0.03):cb, int(W * 0.75):]], axis=1)
        assert band.mean() > 150, "%s: the %s edge of the push-in is background (mean %.0f)" % (kind, strip,
                                                                                               band.mean())


@needs_toolchain
def test_the_push_in_leaves_the_caption_band_to_the_ground(tmp_path):
    """The camera filled the FRAME, so a push-in laid the screen's rows under the burned caption: on a real film
    「先在上面的搜索框里输入上周的反馈。」 sat on 「第4条反馈」, and a caption word sat black on the black bezel. The
    camera fills the content zone (PointerTour's rule); below it the band stays the film's own ground."""
    import screen_media as sm
    np = pytest.importorskip("numpy")
    ui = _screenshot(str(tmp_path / "ui.png"))
    cap = sm.caption_ink_px("zh", 1920, 1080)
    y = 255 / 2532                                        # the search bar's placeholder line
    ink = sm.text_band_px(ui, 0.2, y)
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"tap": [0.2, y], "t0": 0.3, "ta": 0.45, "t1": 0.75, "focus": [0.2, y],
              "textFrac": ink / 1170, "captionPx": cap}]
    for kind in ("phone", "tablet"):                      # both push in here (a laptop's text is caption-tall already)
        png = _render(tmp_path, {"device": kind, "look": "flat", "steps": steps}, 100, "band_" + kind)
        a = np.asarray(Image.open(png).convert("L"), dtype=int)
        H, W = a.shape
        band = a[H - caption_band_px(W, H):, :]
        assert band.max() <= 40, "%s: the push-in reaches the caption band (brightest %d)" % (kind, band.max())


@needs_toolchain
def test_a_script_step_without_its_time_is_refused(tmp_path):
    """One step missing `t1` used to re-time the WHOLE script by an even spread, silently: the tap drew nothing
    at the words the narration names. A film's script is prepared on every step or it is refused."""
    _screenshot(str(tmp_path / "ui.png"))
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"tap": [0.3, 0.2], "t0": 0.3, "ta": 0.4}]
    pf = tmp_path / "bad.json"
    pf.write_text(json.dumps(dict(BASE, steps=steps, dna="product", aspect="16:9")), encoding="utf-8")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DeviceDemo", str(tmp_path / "bad.png"),
                        "--frame=72", "--gl=angle", "--log=error", "--props=" + str(pf),
                        "--public-dir=" + str(tmp_path)], cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode != 0 and "has no prepared time" in (r.stdout + r.stderr), (r.stdout + r.stderr)[-400:]

