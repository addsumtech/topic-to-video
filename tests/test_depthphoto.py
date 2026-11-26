"""The 2.5D photo move: scripts/photo_depth.py (a depth map for one still) and assets/html/depthphoto.js (the photo
drawn as a displaced mesh, a pure function of t).
WHY: a documentary photo pushed in with its depth separating reads as filmed, but only within limits the user has
already paid for: no picture past its native pixels (a soft source, 2026-11), no blur, and no rubber-sheet smear at
a depth edge. These pin the depth file's form, the model's licence line and the loud failure when it cannot be
fetched, that two seeks to one t give the same pixels, that the move goes where the depth says, and that each guard
refuses what it promises to refuse."""
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402
import _filmpage as _fp  # noqa: E402
import photo_depth  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None
needs_chrome = pytest.mark.skipif(not CHROME, reason="Chrome not installed")
MODEL = os.path.join(os.environ.get("TTV_MODELS") or os.path.expanduser("~/.topic-to-video/models"),
                     "depth-anything-v2-small", "model.onnx")
needs_model = pytest.mark.skipif(not os.path.isfile(MODEL), reason="depth model not downloaded (photo_depth.py fetches it)")
SCRIPT = os.path.join(ROOT, "scripts", "photo_depth.py")


def test_work_size_brings_the_short_side_to_518_in_multiples_of_14():
    assert photo_depth.work_size(4132, 2784) == (770, 518)
    assert photo_depth.work_size(4000, 4000) == (518, 518)
    assert photo_depth.work_size(300, 200) == (518, 350)     # a small one: the side that changes least (the HF rule)


@needs_model
def test_depth_of_a_synthetic_scene_is_16_bit_full_range_and_near_is_bright(tmp_path):
    # a floor receding to a horizon, a wall above it, and a box standing on the floor in front
    h, w = 360, 540
    y = np.arange(h)[:, None].repeat(w, 1).astype(float)
    img = np.zeros((h, w, 3))
    img[:] = np.where(y < 150, 120, 60 + 150 * (y - 150) / (h - 150))[..., None]
    img[(np.arange(h) // 12 % 2)[:, None] == (np.arange(w) // 12 % 2)[None, :]] *= 0.8       # a checker on everything
    img[200:330, 220:330] = [200, 60, 40]
    src = tmp_path / "scene.png"
    Image.fromarray(img.clip(0, 255).astype("uint8")).save(src)
    r = subprocess.run([sys.executable, SCRIPT, str(src)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Apache-2.0" in r.stdout and "depth-anything-v2-small" in r.stdout
    d = Image.open(tmp_path / "scene.depth.png")
    assert d.mode in ("I;16", "I;16B", "I") and d.size == photo_depth.work_size(w, h)
    a = np.asarray(d).astype(float) / 65535
    assert a.min() == 0 and a.max() == 1
    sy, sx = a.shape[0] / h, a.shape[1] / w
    near_floor, wall = a[int(340 * sy):, :].mean(), a[: int(120 * sy), :].mean()
    assert near_floor > wall + 0.2, "the floor at the bottom should read nearer than the wall (%.2f vs %.2f)" % (near_floor, wall)


def test_an_unfetchable_model_exits_2_with_the_reason(tmp_path):
    env = dict(os.environ, TTV_MODELS=str(tmp_path / "models"), HTTPS_PROXY="http://127.0.0.1:9",
               https_proxy="http://127.0.0.1:9")
    Image.new("RGB", (64, 48), "grey").save(tmp_path / "a.jpg")
    r = subprocess.run([sys.executable, SCRIPT, str(tmp_path / "a.jpg")], capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "could not fetch the depth model" in r.stdout
    assert not os.listdir(tmp_path / "models" / "depth-anything-v2-small"), "a failed download must leave nothing behind"


# ── the page helper ──────────────────────────────────────────────────────────────────────────────────────────────
W, H = 480, 270


def _scene(tmp_path, pw=960, ph=540, flat=False):
    """A photo (a fine texture, or one flat grey) with a bright square in the middle; its depth: the square near
    (n = 1) on a far ground (n = 0)."""
    rng = np.random.default_rng(0)
    img = np.full((ph, pw, 3), 110, np.uint8) if flat else rng.integers(40, 200, (ph, pw, 3), dtype=np.uint8)
    img[ph * 3 // 8: ph * 5 // 8, pw * 3 // 8: pw * 5 // 8] = [250, 250, 250]
    Image.fromarray(img).save(tmp_path / "p.png")
    d = np.zeros((ph // 4, pw // 4), np.uint16)
    d[ph // 4 * 3 // 8: ph // 4 * 5 // 8, pw // 4 * 3 // 8: pw // 4 * 5 // 8] = 65535
    Image.fromarray(d).save(tmp_path / "p.depth.png")


def _page(tmp_path, move, shots=()):
    """Load a page with one photo and `move`; returns (window.__res, the frames at each t in `shots`)."""
    shutil.copy(os.path.join(ROOT, "assets", "html", "depthphoto.js"), tmp_path)
    (tmp_path / "p.html").write_text("""<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#000">
<canvas id="c"></canvas><script src="depthphoto.js"></script><script>
const dp = DepthPhoto.create({canvas: document.getElementById('c'), width: %d, height: %d});
let shot;
window.filmReady = dp.photo('p.png', 'p.depth.png', %s).then((s) => { shot = s; window.__res = s.report; return 'ok'; },
                                                             (e) => { window.__res = 'ERR ' + e.message; return 'ok'; });
window.seek = (t) => { if (shot) dp.draw(shot, t); };
</script></body></html>""" % (W, H, move))
    port, srv = _fp.serve(str(tmp_path))
    try:
        p = _fp.FilmPage(port, "p.html", W, H)
        try:
            out = []
            for i, t in enumerate(shots):
                p.seek(t)
                p.shot(str(tmp_path / ("f%d.png" % i)), "png")
                out.append(np.asarray(Image.open(tmp_path / ("f%d.png" % i)).convert("RGB")).astype(int))
            return p.ev("window.__res"), out
        finally:
            p.close()
    finally:
        srv.shutdown()


def _square_x(frame):
    """x of the white square's centre (its pure-white pixels)."""
    ys, xs = np.nonzero(frame.min(axis=2) > 240)
    return xs.mean()


@needs_chrome
def test_the_same_t_draws_the_same_pixels_and_the_near_square_moves_by_its_parallax(tmp_path):
    _scene(tmp_path)
    move = "{focus: 0, dolly: 0, from: {zoom: 1.04, x: 0}, to: {zoom: 1.04, x: -6}, start: 0, dur: 1}"
    res, (a, mid, b, a2) = _page(tmp_path, move, shots=(0.0, 0.5, 1.0, 0.0))
    assert isinstance(res, dict), res
    assert np.array_equal(a, a2), "a seek back to the same t must give the same pixels"
    assert not np.array_equal(a, mid)
    # focus 0: the far ground holds, the near square slides the full x (-6 px) by the end of the move
    assert abs((_square_x(b) - _square_x(a)) - (-6)) < 0.75, (_square_x(a), _square_x(b))
    assert abs(res["magnification"] - 0.5 * 1.04) < 1e-6


@needs_chrome
def test_a_move_past_the_photos_native_pixels_is_refused(tmp_path):
    _scene(tmp_path, pw=W, ph=H, flat=True)        # the photo is exactly the frame: any zoom draws past its pixels
    res, _ = _page(tmp_path, "{dolly: 0, from: {zoom: 1.0}, to: {zoom: 1.03}}")
    assert isinstance(res, str) and "native pixels" in res, res
    res, _ = _page(tmp_path, "{dolly: 0, from: {zoom: 1.0}, to: {zoom: 1.0}}")
    assert isinstance(res, dict) and res["magnification"] <= 1, res


@needs_chrome
def test_a_move_that_stretches_a_textured_depth_edge_is_refused_but_flat_ground_is_not(tmp_path):
    big = "{focus: 0, dolly: 0, from: {zoom: 1.1, x: 0}, to: {zoom: 1.1, x: -20}}"
    _scene(tmp_path)
    res, _ = _page(tmp_path, big)
    assert isinstance(res, str) and "stretches" in res, res
    res, _ = _page(tmp_path, "{focus: 0, dolly: 0, from: {zoom: 1.1, x: 0}, to: {zoom: 1.1, x: -5}}")
    assert isinstance(res, dict) and 4 < res["stretch"] <= 5.5, res
    flat = tmp_path / "flat"; flat.mkdir()
    _scene(flat, flat=True)                         # the same edge over flat grey: nothing to smear
    res, _ = _page(flat, big)
    assert isinstance(res, dict) and res["stretch"] == 0, res


@needs_chrome
def test_a_move_that_shows_the_photos_edge_is_refused(tmp_path):
    _scene(tmp_path, flat=True)
    res, _ = _page(tmp_path, "{focus: 1, dolly: 0, from: {zoom: 1.0, x: 0}, to: {zoom: 1.0, x: 30}}")
    assert isinstance(res, str) and "edge of" in res, res
