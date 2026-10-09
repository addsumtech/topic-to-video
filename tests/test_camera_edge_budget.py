"""The push budget reserves the title band and the side margins, not only the caption band.

THE DEFECT, MEASURED. `maxCameraPush` derived the zoom from the room above the burned caption alone. On a plate
that fills the frame, the default push (3/4 of that cap, ~7.3% at 16:9) carried a kicker set 56px from the top to
~20px and labels set 100px in from the sides to ~37px. Nothing was cut, so text_safe passed; the type just sat on
the frame line, outside the EBU R95 action-safe border (3.5% per side).

`runtime/depth.tsx` now measures the visible type the camera carries on each frame and caps the move so type that
is inside the border at rest stays inside it (`edgeSafeExtra`). A beat whose type keeps clear of the edges keeps
the full caption-derived push — checked here on the rendered frame, not assumed.
"""
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
from test_camera_pan import run_probe  # noqa: E402  (bundles against the real depth.tsx)
import remotion_segments  # noqa: E402

needs_toolchain = pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")
SAFE = 0.035
SETTLED = 112          # the probe's 120-frame clock: the push has landed (cameraAt == 1 past t 0.88)


def test_clear_type_keeps_the_whole_push():
    out = run_probe("""
      const W = 1920, H = 1080;
      out.clear = C.edgeSafeExtra([{l: 700, t: 400, r: 1200, b: 460, w: 1}], W, H, W / 2, 528, 0.073);
      out.none = C.edgeSafeExtra([], W, H, W / 2, 528, 0.073);
    """)
    assert out["clear"] == pytest.approx(0.073) and out["none"] == pytest.approx(0.073)


def test_type_near_an_edge_caps_the_push_at_the_border():
    out = run_probe("""
      const W = 1920, H = 1080, oy = 528, ox = W / 2;
      const kicker = {l: 880, t: 56, r: 1040, b: 90, w: 1};
      const left = {l: 100, t: 480, r: 200, b: 520, w: 1};
      out.k = C.edgeSafeExtra([kicker], W, H, ox, oy, 0.073);
      out.l = C.edgeSafeExtra([left], W, H, ox, oy, 0.073);
      out.kTop = oy - (oy - 56) * (1 + out.k);
      out.lLeft = ox - (ox - 100) * (1 + out.l);
      out.inside = C.edgeSafeExtra([{l: 30, t: 480, r: 120, b: 520, w: 1}], W, H, ox, oy, 0.073);
      out.offFrame = C.edgeSafeExtra([{l: -40, t: 480, r: 60, b: 520, w: 1}], W, H, ox, oy, 0.073);
      out.faint = C.edgeSafeExtra([{...left, w: 0.5}], W, H, ox, oy, 0.073);
      // a pan toward the left spends the same border: the cap must be tighter than the zoom-only one
      out.panned = C.edgeSafeExtra([left], W, H, ox, oy, 0.073, 0, -0.8 * W / 2, 0);
    """)
    assert out["k"] < 0.073 and out["kTop"] == pytest.approx(1080 * SAFE, abs=0.01)
    assert out["l"] < 0.073 and out["lLeft"] == pytest.approx(1920 * SAFE, abs=0.01)
    assert out["inside"] == 0, "type already inside the border at rest must not be pushed further out"
    assert out["offFrame"] == pytest.approx(0.073), "type partly off the frame is text_safe's, not the camera's"
    assert out["l"] < out["faint"] <= 0.073, "a half-faded label pulls on the cap half as hard"
    assert out["panned"] < out["l"]


def _render(tmp_path, props, name):
    import numpy as np
    from PIL import Image
    env = {k: v for k, v in os.environ.items() if k != "SLIDES_WORKSHOP"}
    pf = tmp_path / (name + ".json")
    pf.write_text(json.dumps(props), encoding="utf-8")
    png = tmp_path / (name + ".png")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "EdgeBudgetProbe", str(png),
                        "--frame=%d" % SETTLED, "--gl=" + remotion_segments.default_gl(), "--log=error",
                        "--props=" + str(pf)], cwd=REMOTION, capture_output=True, text=True, env=env)
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    return np.asarray(Image.open(png).convert("RGB")).astype(np.int32)


def _ink(a):
    import numpy as np
    blk = (a[..., 0] < 90) & (a[..., 1] < 90) & (a[..., 2] < 90)
    ys, xs = np.nonzero(blk)
    red = (a[..., 0] > 200) & (a[..., 1] < 80) & (a[..., 2] < 80)
    ry, rx = np.nonzero(red)
    return ys.min(), xs.min(), xs.max(), (rx.mean(), ry.mean())


@needs_toolchain
def test_rendered_push_keeps_edge_type_inside_action_safe_and_clear_type_keeps_full_push(tmp_path):
    H, W = 1080, 1920
    top, left, right, _ = _ink(_render(tmp_path, {}, "edge"))
    assert top >= H * SAFE - 2, "kicker pushed to %dpx from the top (border %.0f)" % (top, H * SAFE)
    assert left >= W * SAFE - 2, "left label pushed to %dpx from the side (border %.0f)" % (left, W * SAFE)
    assert W - 1 - right >= W * SAFE - 2, "right label pushed to %dpx from the side" % (W - 1 - right)

    # the clear beat's applied scale, read off the red dot, equals the uncapped default push
    exp = _tsprobe.run_ts(
        "import {maxCameraPush, CONTENT_TOP, contentBottom} from %s;\n"
        "import {baselineUnlockOverscan} from %s;" % (_tsprobe.mod("layout"), _tsprobe.mod("glide")),
        "const W = 1920, H = 1080; const cap = maxCameraPush(W, H); const oy = (CONTENT_TOP + contentBottom(W, H)) / 2;"
        "const u = baselineUnlockOverscan(W, H, oy); const amp = Math.min(cap * 0.75, cap - u);"
        "out.s = 1 + amp + u; out.oy = oy;")
    _, _, _, (dx, dy) = _ink(_render(tmp_path, {"clear": True}, "clear"))
    rest_x, rest_y = round(W * 0.2) - 0.5, round(H * 0.25) - 0.5
    want_x = W / 2 + (rest_x - W / 2) * exp["s"]
    want_y = exp["oy"] + (rest_y - exp["oy"]) * exp["s"]
    assert abs(dx - want_x) < 1.5 and abs(dy - want_y) < 1.5, ((dx, dy), (want_x, want_y))
