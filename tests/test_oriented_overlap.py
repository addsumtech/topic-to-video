"""The type-overlap detector measured tilted text with an instrument that has no idea text can tilt.

`Range.getClientRects()` and `getBoundingClientRect()` are AXIS-ALIGNED. For sloping type the box they
return is larger than the glyphs on the side the text slopes toward, so the detector both OVER-reports (two
lines with clear air between them read as colliding) and, by the same mechanism, can UNDER-report — a real
collision between two tilted lines can be missed because neither box grew toward the other. `CardStack3D`
paid the first: a label at 46px/1 whose three lines are visibly separate was reported as a 64px collision,
and the whole 64px was the tilt.

The fix reconstructs the shape instead of trusting the box. `offsetWidth`/`offsetHeight` are LAYOUT numbers
that transforms do not touch, and an affine image of a rectangle is a parallelogram, which is centrally
symmetric — so its axis-aligned bounding box is centred on exactly the same point. Centre plus the two edge
vectors is the whole shape, with no matrix-to-viewport walk and no reliance on `transform-origin`.

(`Element.getBoxQuads()` would answer this directly. It is undefined in the Chrome this renderer ships —
149, headless shell — which was asked rather than assumed before any of this was written.)

These run in node against the real module: the maths is pure, so it needs no browser.
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
    tmp = tempfile.mkdtemp(prefix="obox_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        open(entry, "w", encoding="utf-8").write(
            "import {selfMatrix, quadOf, quadOverlap} from %s;\nconst out: any = {};\n"
            % json.dumps(os.path.join(_REM, "src", "runtime", "textSafe"))
            + "const D = (d: number) => d * Math.PI / 180;\n"
            + body + "\nconsole.log(JSON.stringify(out));\n")
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
def test_it_reads_a_transform_it_can_invert_and_declines_one_it_cannot():
    """Null is the load-bearing answer: everything downstream reconstructs a shape from this, and for a
    `matrix3d` under a perspective ancestor the projection is not an affine image of the box at all."""
    out = _run("""
      const cs = (t: string, rot?: string) => ({transform: t, rotate: rot} as any);
      out.none = selfMatrix(cs('none'));
      out.rot20 = selfMatrix(cs('matrix(0.9397, 0.342, -0.342, 0.9397, 10, 20)'));
      out.skew = selfMatrix(cs('matrix(1, 0, 0.4, 1, 0, 0)'));
      out.scale = selfMatrix(cs('matrix(2, 0, 0, 3, 0, 0)'));
      out.threeD = selfMatrix(cs('matrix3d(1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1)'));
      out.longhand = selfMatrix(cs('none', '90deg'));
    """)
    assert out["none"] == [1, 0, 0, 1], out["none"]
    assert out["threeD"] is None, "a 3D matrix is being inverted as though it were flat"
    assert out["skew"] is not None and abs(out["skew"][2] - 0.4) < 1e-6, (
        "a SKEW is refused — but a skew is still an affine, and refusing it throws away the case this was "
        "written for: %r" % (out["skew"],))
    assert out["scale"] is not None and out["scale"][0] == 2 and out["scale"][3] == 3, out["scale"]
    assert abs(out["rot20"][1] - 0.342) < 1e-3, out["rot20"]
    assert abs(out["longhand"][1] - 1) < 1e-6, ("the `rotate` longhand is ignored: %r" % (out["longhand"],))


@_NEEDS_NODE
def test_the_shape_is_recovered_from_the_layout_size_not_from_the_box():
    """A 200x50 element tilted 20 degrees has an axis-aligned box of 205.9 x 115.4. The shape is still
    200x50, and that is what must come back."""
    out = _run("""
      const el: any = {offsetWidth: 200, offsetHeight: 50};
      const t = D(20), c = Math.cos(t), s = Math.sin(t);
      const W = 200 * Math.abs(c) + 50 * Math.abs(s), H = 200 * Math.abs(s) + 50 * Math.abs(c);
      const q = quadOf(el, {left: -W / 2, top: -H / 2, width: W, height: H}, [c, s, -s, c])!;
      const side = (i: number, j: number) => Math.hypot(q[j][0] - q[i][0], q[j][1] - q[i][1]);
      out.long = +side(0, 1).toFixed(3);
      out.short = +side(1, 2).toFixed(3);
      out.aabb = [+W.toFixed(1), +H.toFixed(1)];
      out.svg = quadOf({offsetWidth: 0, offsetHeight: 0} as any, {left: 0, top: 0, width: 9, height: 9}, [1, 0, 0, 1]);
    """)
    assert abs(out["long"] - 200) < 0.01 and abs(out["short"] - 50) < 0.01, (
        "the recovered shape is %sx%s, not the 200x50 that was laid out (its box is %s)"
        % (out["long"], out["short"], out["aabb"]))
    assert out["svg"] is None, "an element with no layout size must decline, not return a degenerate quad"


@_NEEDS_NODE
def test_two_tilted_lines_with_air_between_them_do_not_collide():
    """THE CASE THIS EXISTS FOR — TermSpace's «交付可验收的成果» x «自动归档», reported at 9:16, 1:1 and 4:5
    and clean on the frame. Both numbers are asserted, because the point is not that the new one is small
    but that the old one was large enough to cross a 22% threshold."""
    out = _run("""
      const t = D(14), w = 420, h = 34, gap = 44;
      const c = Math.cos(t), s = Math.sin(t);
      const el: any = {offsetWidth: w, offsetHeight: h};
      const W = w * Math.abs(c) + h * Math.abs(s), H = w * Math.abs(s) + h * Math.abs(c);
      const at = (cx: number, cy: number) =>
        quadOf(el, {left: cx - W / 2, top: cy - H / 2, width: W, height: H}, [c, s, -s, c])!;
      const A = at(0, 0), B = at(-Math.sin(t) * gap, Math.cos(t) * gap);
      out.trueOverlap = +quadOverlap(A, B).area.toFixed(2);
      // what the axis-aligned test said about the same pair
      const ow = Math.min(W / 2, -Math.sin(t) * gap + W / 2) - Math.max(-W / 2, -Math.sin(t) * gap - W / 2);
      const oh = Math.min(H / 2, Math.cos(t) * gap + H / 2) - Math.max(-H / 2, Math.cos(t) * gap - H / 2);
      out.boxFrac = +((Math.max(0, ow) * Math.max(0, oh)) / (W * H)).toFixed(3);
    """)
    assert out["trueOverlap"] == 0, (
        "two lines with 44px of clear air between them still collide: %r" % out["trueOverlap"])
    assert out["boxFrac"] > 0.22, (
        "the axis-aligned box fraction is %.3f, under the 0.22 threshold — this probe no longer reproduces "
        "the false positive it exists to pin" % out["boxFrac"])


@_NEEDS_NODE
def test_two_tilted_lines_that_really_cross_still_collide():
    """The other direction, and the dangerous one. A detector that answers 0 for everything tilted would
    pass the test above and quietly stop finding real collisions in 34 registers."""
    out = _run("""
      const el: any = {offsetWidth: 300, offsetHeight: 60};
      const q = (t: number, cx: number, cy: number) => {
        const c = Math.cos(t), s = Math.sin(t);
        const W = 300 * Math.abs(c) + 60 * Math.abs(s), H = 300 * Math.abs(s) + 60 * Math.abs(c);
        return quadOf(el, {left: cx - W / 2, top: cy - H / 2, width: W, height: H}, [c, s, -s, c])!;
      };
      out.crossed = +quadOverlap(q(D(20), 0, 0), q(D(-20), 0, 0)).area.toFixed(1);
      out.stacked = +quadOverlap(q(D(20), 0, 0), q(D(20), 0, 10)).area.toFixed(1);
      out.apart = +quadOverlap(q(D(20), 0, 0), q(D(20), 2000, 2000)).area.toFixed(1);
      out.depth = +quadOverlap(q(D(20), 0, 0), q(D(20), 0, 10)).depth.toFixed(1);
    """)
    assert out["crossed"] > 1000, "two lines crossing at 40 degrees to each other report %r" % out["crossed"]
    assert out["stacked"] > 1000, "two parallel lines 10px apart on a 60px line height report %r" % out["stacked"]
    assert out["apart"] == 0, "two lines 2000px apart report an overlap: %r" % out["apart"]
    assert out["depth"] > 0, "a real collision reports zero penetration depth"
