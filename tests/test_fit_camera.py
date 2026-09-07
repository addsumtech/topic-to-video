"""fitCamera — framing a 3D shot at an aspect it was not composed for.

These run the REAL module under node. The point of the helper is that it asks the projection instead of
trusting a formula, so every test here checks the PROJECTED result, not the number that came back.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")

_NEEDS_NODE = pytest.mark.skipif(
    not (shutil.which("npx") and shutil.which("node") and os.path.isdir(os.path.join(_REM, "node_modules"))),
    reason="needs the remotion toolchain")

_PRELUDE = """
const CUBE = P.boxCorners([0, 0, 0], [1.6, 0.4, 0.4]);
const AIM = [0, 0, 0];
const DIR = [0, 0.55, 1];
const FOV = 34;
const boxOf = (W, H, pad) => ({left: pad, right: W - pad, top: pad, bottom: H - pad});
const fitsIn = (pts, cam, aim, W, H, box) => {
  const b = P.screenBounds(pts, cam, aim, FOV, W, H);
  return !!b && b.x0 >= box.left - 0.01 && b.x1 <= box.right + 0.01
             && b.y0 >= box.top - 0.01 && b.y1 <= box.bottom + 0.01;
};
"""


def _run(body):
    tmp = tempfile.mkdtemp(prefix="fit_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        header = "import * as P from %s;\nconst out: any = {};\n" % json.dumps(
            os.path.join(_REM, "src", "runtime", "fitCamera"))
        open(entry, "w", encoding="utf-8").write(header + _PRELUDE + body + "\nconsole.log(JSON.stringify(out));\n")
        outf = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node",
                            "--outfile=" + outf, "--log-level=error"],
                           cwd=_REM, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", outf], cwd=_REM, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@_NEEDS_NODE
def test_it_actually_fits_at_every_aspect_including_the_narrow_ones():
    """THE ONE THAT MATTERS, and the one the closed-form version would have failed. A wide object framed for
    16:9 has to survive 4:3, 1:1, 4:5 and 9:16 — and 'fits' is checked by projecting the object at the camera
    that came back, never by re-running the arithmetic that chose it."""
    out = _run("""
      const ASPECTS = [[1920,1080], [1440,1080], [1080,1080], [1080,1350], [1080,1920]];
      out.rows = ASPECTS.map(([W, H]) => {
        const box = boxOf(W, H, 60);
        const d = P.fitDistance(CUBE, AIM, DIR, FOV, W, H, box, 4.2);
        const n = Math.hypot(DIR[0], DIR[1], DIR[2]);
        const cam = [AIM[0] + DIR[0] / n * d, AIM[1] + DIR[1] / n * d, AIM[2] + DIR[2] / n * d];
        return {W, H, d, fits: fitsIn(CUBE, cam, AIM, W, H, box)};
      });
    """)
    for r in out["rows"]:
        assert r["fits"], "%dx%d did not fit at the distance fitDistance returned (%.3f)" % (r["W"], r["H"], r["d"])
    wide = next(r for r in out["rows"] if r["W"] == 1920)
    narrow = next(r for r in out["rows"] if r["W"] == 1080 and r["H"] == 1920)
    assert narrow["d"] > wide["d"] * 1.2, (
        "a narrower frame must move the lens BACK; got %.2f vs %.2f" % (narrow["d"], wide["d"]))


@_NEEDS_NODE
def test_it_never_recrops_the_aspect_the_shot_was_composed_for():
    """`d0` is the composed framing. This exists to rescue the aspects that do not fit it — a version that
    also pulled IN when it could would silently redesign the shot that was actually art-directed."""
    out = _run("""
      const W = 1920, H = 1080;
      const roomy = boxOf(W, H, 20);
      out.same = P.fitDistance(CUBE, AIM, DIR, FOV, W, H, roomy, 12.0);   // 12 is far more than needed
    """)
    assert abs(out["same"] - 12.0) < 1e-9, "it moved the lens on an aspect that already fitted"


@_NEEDS_NODE
def test_a_lopsided_box_is_answered_by_MOVING_not_only_by_shrinking():
    """Reserve a copy block under the object and a pure pull-back replies by shrinking the object until it
    clears the copy — leaving all the spare room at the TOP of the frame and the object smaller than it needed
    to be. That is exactly the bug this rescued: PortRail's title was clamped up onto its own rail."""
    out = _run("""
      const W = 1920, H = 1080;
      const box = {left: 60, right: W - 60, top: 40, bottom: H - 380};   // a tall copy block at the bottom
      const only = P.fitDistance(CUBE, AIM, DIR, FOV, W, H, box, 4.2);
      const framed = P.frameCamera([{pts: CUBE, box}], AIM, DIR, FOV, W, H, 4.2);
      const n = Math.hypot(DIR[0], DIR[1], DIR[2]);
      const camOnly = [DIR[0]/n*only, DIR[1]/n*only, DIR[2]/n*only];
      out.onlyFits = fitsIn(CUBE, camOnly, AIM, W, H, box);
      out.framedFits = fitsIn(CUBE, framed.cam, framed.aim, W, H, box);
      out.onlyDist = only; out.framedDist = framed.dist;
      const b = P.screenBounds(CUBE, framed.cam, framed.aim, FOV, W, H);
      out.centreOffset = Math.abs((b.y0 + b.y1) / 2 - (box.top + box.bottom) / 2);
    """)
    assert out["onlyFits"] and out["framedFits"]
    assert out["framedDist"] < out["onlyDist"] * 0.95, (
        "panning should let the object stay LARGER than shrinking alone: %.2f vs %.2f"
        % (out["framedDist"], out["onlyDist"]))
    assert out["centreOffset"] < 2.0, "the object should end up centred in the box it is allowed"


@_NEEDS_NODE
def test_it_refuses_a_box_with_no_room_rather_than_returning_a_number():
    """A reservation that grew past the frame — a copy block taller than the content zone — is a real bug in
    the caller. Returning some distance for it would frame the shot around an impossible constraint and look
    merely odd; throwing names the reservation that ate the frame."""
    out = _run("""
      const W = 1920, H = 1080;
      const bad = [
        {name: 'inverted', box: {left: 60, right: W - 60, top: 700, bottom: 300}},
        {name: 'empty pts', box: {left: 60, right: W - 60, top: 40, bottom: H - 40}, pts: []},
      ];
      out.threw = bad.map((c) => {
        try { P.fitDistance(c.pts ?? CUBE, AIM, DIR, FOV, W, H, c.box, 4.2); return null; }
        catch (e: any) { return c.name; }
      });
      try { P.fitDistance(CUBE, AIM, [0, 0, 0], FOV, W, H, boxOf(W, H, 60), 4.2); out.zeroDir = null; }
      catch (e: any) { out.zeroDir = 'threw'; }
    """)
    assert out["threw"] == ["inverted", "empty pts"], out["threw"]
    assert out["zeroDir"] == "threw", "a lens sitting on its own target has no framing and must say so"


@_NEEDS_NODE
def test_screen_bounds_reports_nothing_rather_than_a_bounding_box_that_wraps_the_lens():
    """A point behind the camera has no screen position, so a bounding box containing one is a fiction — and
    a fit driven by it would happily 'fit' an object that is partly behind the viewer."""
    out = _run("""
      const behind = [[0, 0, 0], [0, 0, 20]];
      out.b = P.screenBounds(behind, [0, 0, 5], [0, 0, 0], FOV, 1920, 1080);
    """)
    assert out["b"] is None


@_NEEDS_NODE
def test_a_pose_that_lasts_a_moment_does_not_get_to_shrink_the_whole_shot():
    """The reason groups exist. PortRail's modules arrive from above; while one is travelling its label is not
    drawn, so it owes the label row nothing. Charged the settled pose's reservations, the travelling pose sized
    the entire composition — the row came out a third smaller for the whole shot to protect type that does not
    exist yet. Two claims, two boxes, and the frame is sized by what is actually on it."""
    out = _run("""
      const W = 1920, H = 1080;
      const settled = P.boxCorners([0, 0, 0], [1.6, 0.2, 0.4]);
      const lifted  = P.boxCorners([0, 1.1, 0], [1.6, 0.2, 0.4]);   // the same row, mid-flight
      const tight = {left: 60, right: W - 60, top: 300, bottom: H - 300};   // labels above, copy below
      const loose = {left: 20, right: W - 20, top: 60, bottom: H - 60};
      const both  = P.fitDistanceMulti([{pts: settled, box: tight}, {pts: lifted, box: loose}],
                                       AIM, DIR, FOV, W, H, 4.2);
      const naive = P.fitDistance(settled.concat(lifted), AIM, DIR, FOV, W, H, tight, 4.2);
      out.both = both; out.naive = naive;
      const n = Math.hypot(DIR[0], DIR[1], DIR[2]);
      const camBoth = [DIR[0]/n*both, DIR[1]/n*both, DIR[2]/n*both];
      out.settledFits = fitsIn(settled, camBoth, AIM, W, H, tight);
      out.liftedFits  = fitsIn(lifted,  camBoth, AIM, W, H, loose);
    """)
    assert out["settledFits"], "the settled pose must still clear every reservation"
    assert out["liftedFits"], "the travelling pose must still be on screen"
    assert out["both"] < out["naive"] * 0.9, (
        "grouping should buy back real size: %.2f vs %.2f" % (out["both"], out["naive"]))
