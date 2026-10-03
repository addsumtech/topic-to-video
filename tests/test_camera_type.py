"""Type must ride a moving camera as smoothly as the drawing it sits in.

THE DEFECT, MEASURED. A viewer reported 字体还是会有很轻微的抖动 on a delivered film's push beats. Chrome draws text
through Skia, and Skia snaps a glyph run's baseline to a whole device pixel whenever the text's matrix is
axis-aligned — which a scale plus a translate always is. So under a push every line of type advanced in 1px steps
while the rules and shapes around it glided. On the film's own push (a kicker and a plate number, ink centroid
against the camera's scale curve) the type's vertical residual was a ±0.5px sawtooth, RMS 0.27px with 1px jumps,
against 0.05px for the sheet border in the same layer. `runtime/depth.tsx` ("the baseline unlock") gives a moving
camera a skew too small to see and large enough to survive Skia's 1/1024 rounding, and the type then tracks the
drawing to the quarter pixel Skia positions glyphs at.

HOW IT IS MEASURED HERE. `CameraTypeProbe` (runtime/__probe_camera.tsx) draws one line of black type and one red
rule inside the real SceneCamera. The type's ink centroid is fitted, per axis, as an affine function of the
rule's: a camera that carries both together leaves only the quarter-pixel floor; a snapped baseline leaves the
sawtooth. Calibrated on this machine's renderer, frames 30-99 of the probe:

                     old camera (y RMS / largest step)    unlocked (y RMS / largest step)
    push             0.247 / 0.876 px                     0.011 / 0.044 px
    pull             0.248 / 0.891 px                     0.010 / 0.038 px
    pan              0.296 / 0.740 px                     0.010 / 0.049 px

x sits at the quarter-pixel floor both ways (0.035-0.071 px RMS, steps under 0.25px). The thresholds below sit
between the two columns with room on both sides.

The other two tests pin what the unlock must not cost: a skewed layer no longer covers the frame's top and bottom
edges at scale 1, so it carries its own overscan (without it, measured, the frame edge showed 239 levels of
whatever lay behind the shot); and a beat that holds must render exactly as it did, pixel for pixel.
"""
import glob
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
REMOTION = os.path.join(os.path.dirname(_HERE), "remotion")
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)
import _tsprobe  # noqa: E402
import remotion_segments  # noqa: E402  (the GL backend a film renders with, so the probe sees the same text path)

needs_toolchain = pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")

# The probe's own clock: DURATION 120, so useT carries the camera through its 0.28..0.88 window on frames ~35..95.
# Rendered from 20 to 110 so the frames where the layer is smallest — before a push starts, after a pull lands —
# are judged for an uncovered edge as well.
RENDERED = (20, 110)
MOVING = slice(30 - RENDERED[0], 100 - RENDERED[0])     # frames 30..99
Y_RMS_MAX, Y_STEP_MAX = 0.10, 0.40      # px: the snapped baseline measured 0.25-0.30 / 0.74-0.89
X_RMS_MAX, X_STEP_MAX = 0.15, 0.45      # px: the quarter-pixel floor measured 0.035-0.071 / under 0.25
MIN_TRAVEL_PX = 10                      # the probe's rule travels 16-35px; a camera that barely moves proves nothing


def _env():
    # a film's workshop is irrelevant to the probe, and a stale one would make the bundle refuse to build
    return {k: v for k, v in os.environ.items() if k != "SLIDES_WORKSHOP"}


def _run(cmd):
    r = subprocess.run(cmd, cwd=REMOTION, capture_output=True, text=True, env=_env())
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    out = tmp_path_factory.mktemp("camera_type") / "bundle"
    _run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + str(out), "--log=error"])
    return out


def _render(bundle, out, frames, props):
    """The probe's frames as lossless PNGs, in frame order, as float RGB arrays."""
    import numpy as np
    from PIL import Image
    out.mkdir(parents=True, exist_ok=True)
    pf = out.parent / (out.name + ".props.json")
    pf.write_text(json.dumps(props), encoding="utf-8")
    _run(["npx", "remotion", "render", str(bundle), "CameraTypeProbe", str(out), "--sequence",
          "--image-format=png", "--frames=" + frames, "--gl=" + remotion_segments.default_gl(), "--log=error",
          "--props=" + str(pf)])
    paths = sorted(glob.glob(str(out / "*.png")), key=lambda p: int(p.rsplit("-", 1)[1][:-4]))
    assert paths, "the probe rendered no frames into %s" % out
    return [np.asarray(Image.open(p).convert("RGB")).astype(np.float32) for p in paths]


def _tracks(frames):
    """Per frame: (type x, type y, rule x, rule y) ink centroids, told apart by colour (see the probe)."""
    import numpy as np

    def centroid(wt):
        cols, rows = wt.sum(axis=0, dtype=np.float64), wt.sum(axis=1, dtype=np.float64)
        m = cols.sum()
        assert m > 1e5, "the probe drew no type or no rule"
        return (np.arange(cols.size) * cols).sum() / m, (np.arange(rows.size) * rows).sum() / m
    rows = []
    for a in frames:
        red, green = a[..., 0], a[..., 1]
        # black type is the only ink with red missing; the red rule the only ink with red and no green
        rows.append(centroid(255.0 - red) + centroid(np.clip(red - green, 0, None)))
    return np.array(rows)


def _residual(tracks, axis):
    """(RMS, largest frame-to-frame step, the rule's travel) of the type against the rule, on one axis."""
    import numpy as np
    t, r = (tracks[:, 0], tracks[:, 2]) if axis == "x" else (tracks[:, 1], tracks[:, 3])
    A = np.vstack([np.ones_like(r), r]).T
    coef, *_ = np.linalg.lstsq(A, t, rcond=None)
    res = t - A @ coef
    return float(np.sqrt((res ** 2).mean())), float(np.abs(np.diff(res)).max()), float(r.max() - r.min())


@needs_toolchain
@pytest.mark.parametrize("name,props", [
    ("push", {"move": "push"}),
    ("pull", {"move": "pull"}),
    ("pan", {"move": "hold", "pan": [0.6, -0.8]}),
])
def test_type_rides_a_moving_camera_with_its_drawing(bundle, tmp_path, name, props):
    frames = _render(bundle, tmp_path / name, "%d-%d" % RENDERED, props)
    tracks = _tracks(frames[MOVING])
    y_rms, y_step, y_travel = _residual(tracks, "y")
    x_rms, x_step, x_travel = _residual(tracks, "x")
    assert y_travel >= MIN_TRAVEL_PX, "%s: the camera carried the rule only %.1fpx — nothing was measured" % (
        name, y_travel)
    assert y_rms < Y_RMS_MAX and y_step < Y_STEP_MAX, (
        "%s: the type trembles against its own rule vertically — residual RMS %.3fpx, a %.3fpx jump between two "
        "frames (a baseline snapped to whole pixels measures ~0.25 / ~0.9)" % (name, y_rms, y_step))
    assert x_rms < X_RMS_MAX and x_step < X_STEP_MAX, (
        "%s: the type trembles against its own rule horizontally — residual RMS %.3fpx, largest step %.3fpx"
        % (name, x_rms, x_step))
    # the whole beat, not only the window: the frames before the move starts carry the skew too
    _assert_frame_covered(frames, name)


def _assert_frame_covered(frames, name):
    import numpy as np
    worst = max(float((255.0 - np.concatenate([a[0, :, 2], a[-1, :, 2], a[:, 0, 2], a[:, -1, 2]])).max())
                for a in frames)
    assert worst <= 8, ("%s: the camera's layer uncovered the frame's edge (blue deficit %.0f on the border) — "
                        "the probe's yellow backing shows through where the shot should be" % (name, worst))


@needs_toolchain
def test_a_held_camera_draws_the_page_exactly_as_no_camera_does(bundle, tmp_path):
    """A beat that holds gets none of the unlock: its frames are what they were before the unlock existed."""
    import numpy as np
    held = _render(bundle, tmp_path / "hold", "50-50", {"move": "hold"})[0]
    bare = _render(bundle, tmp_path / "bare", "50-50", {"bare": True})[0]
    assert float(np.abs(held - bare).max()) == 0.0


@needs_toolchain
def test_the_unlock_overscan_covers_the_frame_at_every_aspect():
    """The skew tilts the layer's top and bottom edges by the skew times half the width; at scale 1 that uncovers
    two corners. The overscan must clear them by the margin at EVERY aspect the films render at, with the camera
    origin where SceneCamera puts it — and the skew must survive Skia's 1/1024 rounding for type down to half
    size, or the unlock silently does nothing (a 0.02° rotation measured exactly that)."""
    out = _tsprobe.run_ts(
        "import {baselineUnlockOverscan, BASELINE_UNLOCK_SKEW as K} from %s;\n"
        "import {CONTENT_TOP, contentBottom} from %s;" % (_tsprobe.mod("depth"), _tsprobe.mod("layout")),
        """
        out.rows = [];
        for (const [W, H] of [[1920, 1080], [1080, 1920], [1080, 1080], [1080, 1350], [1440, 1080], [3840, 2160]]) {
          const oy = (CONTENT_TOP + contentBottom(W, H)) / 2, ox = W / 2;
          const s = 1 + baselineUnlockOverscan(W, H, oy);
          // the layer's corners under translate(o) scale(s) skewY(K) translate(-o)
          const y = (px: number, py: number) => oy + s * ((py - oy) + K * (px - ox));
          const x = (px: number) => ox + s * (px - ox);
          out.rows.push({W, H, s, top: Math.max(y(0, 0), y(W, 0)), bottom: Math.min(y(0, H), y(W, H)),
                         left: x(0), right: x(W)});
        }
        out.halfSize = Math.round(0.5 * K * 1024);
        try { baselineUnlockOverscan(1920, 1080, 0.5); out.edge = 'no throw'; } catch (e) { out.edge = String(e); }
        """)
    for r in out["rows"]:
        where = "%dx%d" % (r["W"], r["H"])
        assert r["top"] <= -1 + 1e-6 and r["bottom"] >= r["H"] + 1 - 1e-6, (where, r)
        assert r["left"] <= 0 and r["right"] >= r["W"], (where, r)
        assert r["s"] < 1.01, "%s: the unlock costs a %.2f%% zoom — that is a move, not a margin" % (
            where, 100 * (r["s"] - 1))
    assert out["halfSize"] >= 1, "the skew rounds to zero for type at half size — Skia would snap it again"
    assert "frame's edge" in out["edge"], out["edge"]
