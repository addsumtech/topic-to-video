"""An overlay caption reads on a busy photograph — no strip, no scrim, no white halo — and the gate measures it.

THE DEFECT (validation film 蜂巢, 1:1, 2026-10-31). render.py picked the caption's ink against ONE colour, the median
of the bottom 20% of the scene's first frame, and outlined it 2px in that same median. Over a bright amber bee close-up
it chose a dark ink with an amber hairline (measured on the delivered frames: 96% of the caption's edge under 3:1
against its ink); the author scrimmed the photos by hand. No gate looked at a caption's contrast.

THE FIX. render._caption_inks scores the deck's two inks by their 10th-percentile contrast against EVERY ground pixel
under the caption's lines over its window, and outlines the winner in the ground's own far tone (its darkest decile
under light ink) — the photo's shadow, never a bar. scripts/caption_contrast_qa.py measures the delivered pixels at the
places render.py records (.clips/clip_NN.mp4.captions.json): the share of the glyphs' edge zone under 3:1.

These tests run without a render: a busy synthetic ground (stripes of a bright amber and a near-black, like the cells
under the bees) and a flat one, the caption drawn by render.py's own _caption_layer, judged by the gate's own code.
"""
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
import render as rd  # noqa: E402
import caption_contrast_qa as cc  # noqa: E402

AMBER, DARK, CREAM = (236, 170, 60), (25, 18, 10), (240, 226, 196)
BROWN = (123, 91, 18)    # the median under the film's first caption: dark ink cleared 3:1 against it by 0.01


def _film(tmp_path, fg="#f0f3f8", on_accent="#111111", bg="#14100a"):
    (tmp_path / "theme.css").write_text(":root{--fg:%s;--on-accent:%s;--bg:%s}" % (fg, on_accent, bg), encoding="utf-8")
    return {"_out": str(tmp_path), "language": "zh", "captions": True}


def _busy(W, H, a=BROWN, b=AMBER, period=9, share=0.6):
    """Diagonal stripes, `share` of them colour a: every caption glyph crosses both — the bee close-up's make-up under
    its first caption (median a mid brown, bright amber through it)."""
    y, x = np.mgrid[0:H, 0:W]
    m = ((x + y) // period) % 10 < int(round(share * 10))
    out = np.empty((H, W, 3), np.uint8)
    out[m], out[~m] = a, b
    return Image.fromarray(out)


def _melt(ground, text, W, H, meta, inks):
    rec = {"text": text, "start": 0, "end": 1}
    lay = os.path.join(meta["_out"], "cap.png")
    # the old path's ground: the median of the frame's bottom 20% (render._sample_region_color)
    g = ground.convert("RGB")
    px = sorted(rd._pixels(g.crop((0, int(H * 0.8), W, H))), key=rd._rel_lum)
    rd._caption_layer(text, W, H, lay, meta, band_bg=px[len(px) // 2], inks=inks, record=rec)
    comp = ground.convert("RGB").copy()
    layer = Image.open(lay)
    comp.paste(layer, (0, 0), layer)
    # delivered pixels are ENCODED: a 4:2:0 lossy round trip, as the film's own frames are (the gate reads out.mp4)
    import io
    buf = io.BytesIO()
    comp.save(buf, "JPEG", quality=90)
    comp = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    core, edge = cc.caption_mask(rec, W, H)
    melt, _ink = cc.judge_frame(np.asarray(comp), core, edge)
    return melt, rec


@pytest.mark.parametrize("W, H, text", [
    (1080, 1080, "约三点八公斤蜂蜜，才换来四百五十克蜡。"),            # the film's own frame and line
    (1920, 1080, "It takes about 3.8 kg of honey to make 450 g of wax."),   # another aspect, another language
    (1080, 1920, "蜜蜂の巣はなぜ六角形なのか。"),                       # portrait, Japanese
])
def test_on_a_busy_ground_the_measured_inks_read_and_the_old_ones_melt(tmp_path, W, H, text, monkeypatch):
    meta = _film(tmp_path)
    ground = _busy(W, H)
    boxes = rd.caption_boxes(text, W, H, meta)
    inks = rd._caption_inks(rd._ground_pixels([ground], boxes), meta)
    new, rec = _melt(ground, text, W, H, meta, inks)
    with monkeypatch.context() as m:                         # the previous pick: one median colour, its 2px hairline
        m.setattr(rd, "caption_outline_px", lambda font: 2)
        old, _ = _melt(ground, text, W, H, meta, None)
    assert old > cc.ERROR_FRAC, "control: the old single-colour pick should melt on stripes (got %.2f)" % old
    assert new <= cc.WARN_FRAC, "the measured inks still melt: %.0f%% of the edge under 3:1 (%r)" % (new * 100, inks)
    # the outline is one of the GROUND's own colours — the one on the far side of the ink — never white, never a bar
    assert rec["outline"] is not None
    assert min(max(abs(a - b) for a, b in zip(rec["outline"], c)) for c in (BROWN, AMBER)) <= 12, rec["outline"]
    assert rd._wcag_contrast(rec["ink"], rec["outline"]) >= 4.5, (rec["ink"], rec["outline"])


def test_on_a_flat_ground_the_outline_is_the_ground_itself(tmp_path):
    meta = _film(tmp_path)
    ground = Image.new("RGB", (1080, 1080), (20, 16, 10))
    text = "面积相同，六边形周长最短。"
    inks = rd._caption_inks(rd._ground_pixels([ground], rd.caption_boxes(text, 1080, 1080, meta)), meta)
    assert inks["outline"] == (20, 16, 10) and inks["ink"] == (240, 243, 248)
    melt, _ = _melt(ground, text, 1080, 1080, meta, inks)
    assert melt == 0.0


def test_on_a_light_photo_the_ink_goes_dark_and_its_outline_light(tmp_path):
    meta = _film(tmp_path, fg="#111111", on_accent="#ffffff", bg="#f4f1ea")
    ground = _busy(1080, 1080, a=(200, 180, 140), b=CREAM, share=0.5)
    text = "边越短，越省蜡。"
    inks = rd._caption_inks(rd._ground_pixels([ground], rd.caption_boxes(text, 1080, 1080, meta)), meta)
    assert rd._rel_lum(inks["ink"]) < 0.2 and inks["outline"] == CREAM, inks


def test_the_render_records_what_it_drew(tmp_path):
    meta = _film(tmp_path)
    rec = {"text": "x", "start": 0.5, "end": 2.0}
    rd._caption_layer("能铺满平面的正多边形，只有三种。", 1080, 1080, str(tmp_path / "c.png"), meta, record=rec)
    assert rec["lines"] and len(rec["xy"]) == len(rec["lines"]) and rec["font"][1] > 20
    assert rec["outline_px"] >= 2 and len(rec["ink"]) == 3
    clip = str(tmp_path / "clip_01.mp4")
    rd._write_caption_manifest(clip, [rec])
    assert json.load(open(rd.caption_manifest_path(clip)))["captions"][0]["lines"] == rec["lines"]


def test_a_caption_that_is_not_there_is_not_judged():
    """A frame where the recorded caption is absent (a different chunk, a seam) is skipped, not scored as melted."""
    core = np.zeros((50, 50), bool); core[20:30, 10:40] = True
    edge = np.zeros((50, 50), bool); edge[17:20, 10:40] = True
    frame = np.asarray(_busy(50, 50, a=DARK, period=1, share=0.5))
    assert cc.judge_frame(frame, core, edge) == (None, None)


# ── the spoken word's highlight ──────────────────────────────────────────────────────────────────────────────
def _film_accent(tmp_path, accent="#f0a830", accent2="#d9534f"):
    (tmp_path / "theme.css").write_text(":root{--fg:#f0f3f8;--on-accent:#111111;--bg:#14100a;--accent:%s;--accent2:%s}"
                                        % (accent, accent2), encoding="utf-8")
    return {"_out": str(tmp_path), "language": "zh", "captions": True}


def test_the_highlight_is_scored_on_the_ground_and_never_falls_under_the_inks_floor(tmp_path):
    """The film's case: an amber accent over amber-and-brown honeycomb. The deck's accent sits under 3:1 against
    most of that ground (the old pick cleared it against ONE median); the measured highlight either clears the floor
    the base ink meets or IS the base ink."""
    meta = _film_accent(tmp_path)
    W = H = 1080
    text = "蜡来之不易。"
    px = rd._ground_pixels([_busy(W, H)], rd.caption_boxes(text, W, H, meta))
    inks = rd._caption_inks(px, meta)
    sample = sorted(rd._wcag_contrast((240, 168, 48), g) for g in px)
    assert sample[len(sample) // 10] < rd.CAPTION_MIN_CONTRAST, "control: the deck's amber should melt here"
    floor = min(rd.CAPTION_MIN_CONTRAST, inks["p10"])
    assert inks["hl_p10"] >= floor - 1e-9 or tuple(inks["hl"]) == tuple(inks["ink"]), inks


def test_on_a_clean_ground_the_highlight_is_the_decks_own_accent(tmp_path):
    meta = _film_accent(tmp_path)
    ground = Image.new("RGB", (1080, 1080), (20, 16, 10))
    inks = rd._caption_inks(rd._ground_pixels([ground], rd.caption_boxes("面积相同。", 1080, 1080, meta)), meta)
    assert inks["hl"] == (240, 168, 48), inks


def test_the_gate_judges_the_spoken_word_in_its_own_colour(tmp_path):
    meta = _film_accent(tmp_path)
    W = H = 1080
    text = "约三点八公斤蜂蜜，才换来四百五十克蜡。"
    ground = Image.new("RGB", (W, H), (20, 16, 10))
    inks = rd._caption_inks(rd._ground_pixels([ground], rd.caption_boxes(text, W, H, meta)), meta)
    rec = {"text": text, "start": 0, "end": 1}
    lay = str(tmp_path / "c.png")
    rd._caption_layer(text, W, H, lay, meta, band_bg=(20, 16, 10), hl_span=(6, 8), record=rec, inks=inks)
    assert rec.get("hl_runs") and "".join(r[2] for r in rec["hl_runs"]) == "蜂蜜", rec.get("hl_runs")
    comp = ground.copy()
    layer = Image.open(lay)
    comp.paste(layer, (0, 0), layer)
    core, edge = cc.caption_mask(rec, W, H, rec["hl_runs"])
    melt, ink = cc.judge_frame(np.asarray(comp), core, edge)
    assert max(abs(int(a) - b) for a, b in zip(ink, rec["hl"])) <= 3 and melt == 0.0, (ink, rec["hl"])
