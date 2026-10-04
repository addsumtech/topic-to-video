"""KSpaceToPicture's own data is a Fourier pair, not a drawing.

With no `kspace` and no `frames` the register computes a modified Shepp–Logan phantom, its 2-D FFT, and the inverse
FFT of the rows written so far. These tests run that code in node (tests/_tsprobe.py) and hold it to numpy: the
phantom is the standard one, the k-space is its transform, every reconstruction is the inverse of exactly the rows
the reveal lights, the k-space is shown in the window a film's own data is written with (scripts/kspace_frames.py)
and every frame on one white point, and the pictures handed to <Img> decode to those bytes."""
import base64
import io
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
import _tsprobe as tp  # noqa: E402

SHOT = os.path.join(_ROOT, "remotion", "src", "shots", "KSpaceToPicture.tsx")
pytestmark = pytest.mark.skipif(not tp.available(), reason="node, npx or remotion/node_modules is missing")

N = 64          # a small matrix keeps the probe's JSON small; the arithmetic is the same at the default 256
M = 20          # rows written in the partial reconstructions below
FRAMES = 8      # frames in the small series; frame 3 holds round(N * 4 / 8) rows

# the modified Shepp–Logan table, restated independently of the TypeScript
ELLIPSES = [(1, .69, .92, 0, 0, 0), (-.8, .6624, .874, 0, -.0184, 0), (-.2, .11, .31, .22, 0, -18),
            (-.2, .16, .41, -.22, 0, 18), (.1, .21, .25, 0, .35, 0), (.1, .046, .046, 0, .1, 0),
            (.1, .046, .046, 0, -.1, 0), (.1, .046, .023, -.08, -.605, 0), (.1, .023, .023, 0, -.606, 0),
            (.1, .023, .046, .06, -.605, 0)]


def _phantom(n, ss=4):
    sub = (np.arange(n * ss) + 0.5) / ss                 # sample positions in pixel units, ss per pixel
    x = -1 + 2 * sub / n
    y = 1 - 2 * sub / n
    X, Y = np.meshgrid(x, y)
    img = np.zeros_like(X)
    for A, a, b, x0, y0, deg in ELLIPSES:
        r = np.deg2rad(deg)
        dx, dy = X - x0, Y - y0
        u, v = dx * np.cos(r) + dy * np.sin(r), dy * np.cos(r) - dx * np.sin(r)
        img += A * ((u / a) ** 2 + (v / b) ** 2 <= 1)
    return img.reshape(n, ss, n, ss).mean(axis=(1, 3))


@pytest.fixture(scope="module")
def computed():
    return tp.run_ts("import {phantomImage, fourierPair, phantomSeries, writtenRows, PHANTOM_ROWS} from %s;"
                     % json.dumps(SHOT), """
const n = %d, m = %d;
const img = phantomImage(n);
const {kspace, reconstruct} = fourierPair(img, n);
const mag = (r: {re: Float64Array; im: Float64Array}) => Array.from(r.re, (v, i) => Math.hypot(v, r.im[i]));
out.img = Array.from(img);
out.kspace = Array.from(kspace);
out.centre = mag(reconstruct(m, 'centre'));
out.top = mag(reconstruct(m, 'top'));
out.rowsCentre = writtenRows(m, n, 'centre');
out.rowsTop = writtenRows(m, n, 'top');
const s = phantomSeries('centre', n, %d);
out.kBytes = Array.from(s.kspace);
out.kUri = s.kspaceUri;
out.f3 = Array.from(s.frame(3));
out.f3Uri = s.frameUri(3);
const big = phantomImage(PHANTOM_ROWS);
out.bigN = PHANTOM_ROWS;
out.big = Array.from(big);
let refused = '';
try { fourierPair(new Float64Array(48 * 48), 48); } catch (e) { refused = String(e); }
out.refused = refused;
""" % (N, M, FRAMES))


def _arr(v, n):
    return np.array(v, dtype=np.float64).reshape(n, n)


def test_the_phantom_is_the_modified_shepp_logan_head(computed):
    n = computed["bigN"]
    big = _arr(computed["big"], n)
    assert np.allclose(big, _phantom(n), atol=1e-12)
    px = lambda x, y: big[int((1 - y) * n / 2), int((x + 1) * n / 2)]       # the pixel holding (x, y)
    assert px(0, 0) == pytest.approx(0.2)            # brain
    assert px(0, 0.902) == pytest.approx(1.0)        # skull, above the brain
    assert px(-0.22, 0) == pytest.approx(0.0, abs=1e-12) and px(0.22, 0) == pytest.approx(0.0, abs=1e-12)   # ventricles
    assert px(0, 0.35) == pytest.approx(0.3)         # the large bright ellipse
    assert px(-0.95, 0.95) == 0.0                    # outside the head


def test_the_k_space_is_the_fourier_transform_of_the_phantom(computed):
    img, K = _arr(computed["img"], N), _arr(computed["kspace"], N)
    want = np.abs(np.fft.fftshift(np.fft.fft2(img)))
    assert np.allclose(K, want, rtol=1e-9, atol=1e-9 * want.max())


@pytest.mark.parametrize("order,rows", [("centre", (N // 2 - M // 2, N // 2 + (M - 1) // 2)), ("top", (0, M - 1))])
def test_a_reconstruction_is_the_inverse_of_exactly_the_rows_the_reveal_lights(computed, order, rows):
    """The reveal lights rows c - floor(m/2) .. c + floor((m-1)/2) for a centre fill (c = n/2) and 0 .. m-1 for a top
    fill; the picture beside it must be computed from those rows and no others."""
    assert tuple(computed["rowsCentre" if order == "centre" else "rowsTop"]) == rows
    img = _arr(computed["img"], N)
    K = np.fft.fftshift(np.fft.fft2(img))
    mask = np.zeros((N, N))
    mask[rows[0]:rows[1] + 1, :] = 1
    want = np.abs(np.fft.ifft2(np.fft.ifftshift(K * mask)))
    got = _arr(computed[order], N)
    assert np.allclose(got, want, atol=1e-9)
    assert not np.allclose(got, img, atol=1e-3), "a partial fill should not already be the whole picture"


def test_the_full_inverse_check_refuses_a_matrix_it_cannot_transform(computed):
    assert "power of two" in computed["refused"], computed["refused"]


def test_the_display_bytes_follow_the_film_data_windows(computed):
    """The k-space as log magnitude above its median with its 99.95th percentile white, as a film's own k-space is
    written; every frame on ONE white point (half the skull's 1, so the tissue at 0.2-0.3 reads), so a frame's
    brightness says how much of the picture is there."""
    img = _arr(computed["img"], N)
    K = np.abs(np.fft.fftshift(np.fft.fft2(img)))
    mag = np.log1p(K)
    lo, hi = np.percentile(mag, 50), np.percentile(mag, 99.95)
    want_k = np.round(np.clip((mag - lo) / (hi - lo), 0, 1) * 255)
    assert np.abs(_arr(computed["kBytes"], N) - want_k).max() <= 1
    m = int(round(N * 4 / FRAMES))
    mask = np.zeros((N, N))
    mask[N // 2 - m // 2:N // 2 + (m - 1) // 2 + 1, :] = 1
    rec = np.abs(np.fft.ifft2(np.fft.ifftshift(np.fft.fftshift(np.fft.fft2(img)) * mask)))
    want_f = np.round(np.clip(rec / 0.5, 0, 1) * 255)
    assert np.abs(_arr(computed["f3"], N) - want_f).max() <= 1


@pytest.mark.parametrize("uri,data", [("kUri", "kBytes"), ("f3Uri", "f3")])
def test_the_pictures_handed_to_img_decode_to_the_computed_bytes(computed, uri, data):
    head = "data:image/bmp;base64,"
    assert computed[uri].startswith(head)
    im = Image.open(io.BytesIO(base64.b64decode(computed[uri][len(head):])))
    assert im.size == (N, N)
    got = np.asarray(im.convert("L"), dtype=np.float64)
    assert np.array_equal(got, _arr(computed[data], N)), "the picture is not the bytes it was made from, top row first"
