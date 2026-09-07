"""pageCam2D — a lens over a page, and knowing where the page ended up.

The pure functions are checked here under node. The property that actually matters — that `pageToScreen`
agrees with the transform the browser applies — cannot be checked in node at all, and is checked by rendering
a register that places a cursor from `pageToScreen` onto a card drawn by the transform, then measuring
whether the two coincide. That pairing is exactly what went wrong in the WebGL registers, where two cameras
disagreed and every label landed on its neighbour.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(os.path.dirname(_HERE), "remotion")

_NEEDS_NODE = pytest.mark.skipif(
    not (shutil.which("npx") and shutil.which("node") and os.path.isdir(os.path.join(_REM, "node_modules"))),
    reason="needs the remotion toolchain")


def _run(body):
    tmp = tempfile.mkdtemp(prefix="pcam_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        head = "import * as P from %s;\nconst out: any = {};\n" % json.dumps(
            os.path.join(_REM, "src", "runtime", "pageCam2D"))
        open(entry, "w", encoding="utf-8").write(head + body + "\nconsole.log(JSON.stringify(out));\n")
        outf = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--outfile=" + outf,
                            "--log-level=error"], cwd=_REM, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", outf], cwd=_REM, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@_NEEDS_NODE
def test_the_point_the_camera_is_on_lands_dead_centre():
    """The simplest invariant, and the one a sign flip breaks: a key names the page point that should sit at
    the middle of the frame, so it had better sit there."""
    out = _run("""
      const W = 1920, H = 1080;
      out.rows = [{x: 0, y: 0, s: 1}, {x: 900, y: 640, s: 1.8}, {x: 120, y: 40, s: 0.4}].map((cam) => {
        const c = P.pageToScreen(cam as any, W, H, cam.x, cam.y);
        return [c.x, c.y];
      });
    """)
    for x, y in out["rows"]:
        assert abs(x - 960) < 1e-6 and abs(y - 540) < 1e-6, (x, y)


@_NEEDS_NODE
def test_scale_moves_things_away_from_the_centre_in_proportion():
    out = _run("""
      const W = 1920, H = 1080;
      const p = [700, 300];
      out.a = P.pageToScreen({x: 500, y: 200, s: 1}, W, H, p[0], p[1]);
      out.b = P.pageToScreen({x: 500, y: 200, s: 2}, W, H, p[0], p[1]);
    """)
    assert abs((out["b"]["x"] - 960) - 2 * (out["a"]["x"] - 960)) < 1e-6
    assert abs((out["b"]["y"] - 540) - 2 * (out["a"]["y"] - 540)) < 1e-6


@_NEEDS_NODE
def test_it_holds_before_the_first_stop_and_after_the_last():
    """A tour that eases out of nowhere before its first key reads as the shot starting late, and one that
    keeps drifting past its last key never lets the viewer finish reading the thing it flew to."""
    out = _run("""
      const keys = [{at: 0.2, x: 100, y: 50, s: 1}, {at: 0.8, x: 900, y: 400, s: 2}];
      out.before = P.camAt(keys, 0.0);
      out.first = P.camAt(keys, 0.2);
      out.mid = P.camAt(keys, 0.5);
      out.after = P.camAt(keys, 1.0);
    """)
    assert out["before"] == out["first"], "it must hold, not extrapolate, before the first key"
    assert out["after"]["x"] == 900 and out["after"]["s"] == 2
    assert 100 < out["mid"]["x"] < 900


@_NEEDS_NODE
def test_keys_out_of_order_are_a_route_not_an_error():
    """A tour is authored as a list of places; sorting it is the camera's job, not the author's. Read in the
    given order instead, an out-of-order table interpolates backwards through time and the lens jumps."""
    out = _run("""
      const a = P.camAt([{at: 0.8, x: 900, y: 400, s: 2}, {at: 0.2, x: 100, y: 50, s: 1}], 0.5);
      const b = P.camAt([{at: 0.2, x: 100, y: 50, s: 1}, {at: 0.8, x: 900, y: 400, s: 2}], 0.5);
      out.a = a; out.b = b;
    """)
    assert out["a"] == out["b"]


@_NEEDS_NODE
def test_a_camera_with_no_keys_and_a_page_with_no_size_both_say_so():
    out = _run("""
      try { P.camAt([], 0.5); out.noKeys = null; } catch (e: any) { out.noKeys = 'threw'; }
      out.fit = P.fitScale(1920, 1080, 3000, 1800, 1);
    """)
    assert out["noKeys"] == "threw"
    assert abs(out["fit"] - min(1920 / 3000, 1080 / 1800)) < 1e-9


@_NEEDS_NODE
def test_the_lens_stays_inside_the_page_when_it_can_and_centres_when_it_cannot():
    """A camera aimed at a corner card is aimed near the page's EDGE, and at close-up scale half the frame
    falls outside it — the toured screen appears to float with the backdrop showing beside it. And the same
    call has to do the opposite thing at the other end of the same move: at the overview the page is SMALLER
    than the frame and seeing it whole is the shot, so there is nothing to clamp to and it centres."""
    out = _run("""
      const W = 1920, H = 1080, pageW = 2688, pageH = 1734;
      const close = P.clampToPage({x: 400, y: 200, s: 1.2}, W, H, pageW, pageH);
      out.close = close;
      out.covers = (close.x - W / 2 / close.s >= -0.001) && (close.y - H / 2 / close.s >= -0.001)
                && (close.x + W / 2 / close.s <= pageW + 0.001)
                && (close.y + H / 2 / close.s <= pageH + 0.001);
      const wide = P.clampToPage({x: 400, y: 200, s: P.fitScale(W, H, pageW, pageH)}, W, H, pageW, pageH);
      out.wide = wide; out.centre = [pageW / 2, pageH / 2];
    """)
    assert out["covers"], "a clamped close-up must not show past the page edge: %s" % out["close"]
    assert abs(out["wide"]["x"] - out["centre"][0]) < 1e-6 and abs(out["wide"]["y"] - out["centre"][1]) < 1e-6, \
        "at a scale where the page cannot cover the frame it must centre, not clamp"
