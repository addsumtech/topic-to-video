"""scripts/kspace_frames.py writes a real image's k-space and its partial reconstructions as KSpaceToPicture takes
them: a Fourier pair, filled in the order the register's reveal lights, each picture carrying the source's
attribution. The input here is drawn by the test, never a film's own image."""
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import kspace_frames as kf  # noqa: E402

ROWS, FRAMES = 32, 4


def _image(tmp_path, size=(120, 90)):
    im = Image.new("L", size, 0)
    d = ImageDraw.Draw(im)
    d.ellipse([20, 10, 100, 80], fill=200)
    d.rectangle([50, 30, 70, 60], fill=60)
    p = tmp_path / "slice.png"
    im.save(str(p))
    (tmp_path / "slice.png.json").write_text(json.dumps({"license": "CC0", "author": "the test"}), encoding="utf-8")
    return str(p)


def _png(path):
    return np.asarray(Image.open(path), dtype=np.float64)


def test_the_fill_order_is_the_reveals_order():
    """KSpaceToPicture lights rows c - floor(m/2) .. c + floor((m-1)/2) (c = n/2) for a centre fill and 0 .. m-1 for
    a top fill; the frames must be computed from those same rows."""
    seq = kf.fill_order(8, "centre")
    assert seq == [4, 3, 5, 2, 6, 1, 7, 0]
    for m in range(1, 9):
        assert sorted(seq[:m]) == list(range(4 - m // 2, 4 + (m - 1) // 2 + 1))
    assert kf.fill_order(8, "top") == list(range(8))


def test_the_frames_are_the_inverse_of_the_rows_written_and_the_last_is_the_image(tmp_path):
    out = tmp_path / "film"
    props = kf.write(str(out), _image(tmp_path), rows=ROWS, frames=FRAMES, display=ROWS)
    assert props["rows"] == ROWS and props["order"] == "centre" and len(props["srcFrames"]) == FRAMES
    a = np.asarray(kf.square_gray(str(tmp_path / "slice.png"), ROWS), dtype=np.float64)
    F = np.fft.fftshift(np.fft.fft2(a))
    hi = np.percentile(np.abs(np.fft.ifft2(np.fft.ifftshift(F))), 99.7)
    c = ROWS // 2
    for k, fn in enumerate(props["srcFrames"], 1):
        m = int(round(ROWS * k / FRAMES))
        mask = np.zeros_like(F)
        mask[c - m // 2:c + (m - 1) // 2 + 1, :] = 1
        want = np.round(np.clip(np.abs(np.fft.ifft2(np.fft.ifftshift(F * mask))) / hi, 0, 1) * 255)
        assert np.array_equal(_png(str(out / fn)), want), fn
    last = _png(str(out / props["srcFrames"][-1]))
    assert np.abs(last - np.round(np.clip(a / hi, 0, 1) * 255)).max() <= 1, "the last frame is not the whole image"
    mag = np.log1p(np.abs(F))
    lo, top = np.percentile(mag, 50), np.percentile(mag, 99.95)
    assert np.array_equal(_png(str(out / props["srcKspace"])), np.round(np.clip((mag - lo) / (top - lo), 0, 1) * 255))


def test_every_derived_picture_carries_the_sources_attribution(tmp_path):
    out = tmp_path / "film"
    props = kf.write(str(out), _image(tmp_path), rows=ROWS, frames=FRAMES, display=64)
    for fn in [props["srcKspace"]] + props["srcFrames"]:
        side = json.loads((out / (fn + ".json")).read_text(encoding="utf-8"))
        assert side["license"] == "CC0" and side["author"] == "the test" and side["derivation"], side
    rec = json.loads((out / "media" / "kspace.json").read_text(encoding="utf-8"))
    assert rec["frames"] == props["srcFrames"] and rec["rows_written"] == [8, 16, 24, 32]
    assert Image.open(str(out / props["srcKspace"])).size == (64, 64)


def test_a_wide_image_is_padded_to_a_square_not_stretched(tmp_path):
    sq = np.asarray(kf.square_gray(_image(tmp_path, size=(120, 90)), 120))
    assert sq.shape == (120, 120)
    assert not sq[:15].any() and not sq[-15:].any(), "the padding above and below the picture is not black"
    assert sq[15 + 45, 60] > 0, "the picture is not centred in its square"


@pytest.mark.parametrize("kw,why", [({"frames": kf.MAX_FRAMES + 1}, "--frames"), ({"rows": 4}, "--rows"),
                                    ({"display": 16}, "--display"), ({"order": "spiral"}, "--order")])
def test_what_the_register_cannot_take_is_refused(tmp_path, kw, why):
    with pytest.raises(ValueError) as e:
        kf.write(str(tmp_path / "film"), _image(tmp_path), **dict({"rows": ROWS, "frames": FRAMES, "display": ROWS}, **kw))
    assert why in str(e.value)


def test_a_blank_image_is_refused(tmp_path):
    p = tmp_path / "blank.png"
    Image.new("L", (40, 40), 0).save(str(p))
    with pytest.raises(ValueError) as e:
        kf.write(str(tmp_path / "film"), str(p), rows=ROWS, frames=FRAMES, display=ROWS)
    assert "blank" in str(e.value)
