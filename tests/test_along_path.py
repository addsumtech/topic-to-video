"""A thing travelling down a curve has to agree with the curve about where it is.

Two registers placed a travelling object by re-deriving the geometry by hand, beside a `d` string that
already described it exactly. `MapRoutes` put its packet at `lerp(hub, pin, p)` minus a sine hump while the
route is a quadratic — measured against the route's own arc length the packet rode up to 140px off the line
it is supposed to be on, visibly floating in the dark beside it. `LightTrails` split a two-leg checkmark at
u=0.4 when the legs are 318 and 630 units, so the elbow is at 33.6% of the length and its head lagged the tip
of the stroke it leads by 61px.

Both are one mistake: a second model of a curve that already exists. The fix is to ask the path — and to ask
it by ARC LENGTH, which is what makes the answer agree with a stroke revealed by `pathLength={1}`.
"""
import json
import math
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
    tmp = tempfile.mkdtemp(prefix="alongp_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        open(entry, "w", encoding="utf-8").write(
            "import {pointAt, angleAt, pathLength, _internals} from %s;\nconst out: any = {};\n"
            % json.dumps(os.path.join(_REM, "src", "runtime", "alongPath"))
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
def test_equal_steps_cover_equal_distance():
    """THE ONE THAT MATTERS, and the property the hand-rolled versions did not have.

    Travel is by arc length, so equal steps in `u` are equal distances along the curve. The Bézier PARAMETER
    is not: it crawls where the curve bends and races where it straightens. Measured on one quadratic, the
    step lengths vary by 42% under the parameter and by 3.8% under arc length — and that residual is not
    error, it is CHORD versus ARC: consecutive samples are joined by a straight line that is shorter than the
    curve between them, by more where the curve bends. So the assertion is comparative, which is also the
    honest form of the claim: arc length must be an order flatter, not perfectly flat.

    The second path is two straight legs of very different length — no curvature, so chord IS arc, and there
    the parameterisation has nowhere to hide. That is the `LightTrails` shape, whose elbow sits at 33.6% of
    the length and was being sampled as if it were at 40%.
    """
    out = _run("""
      const curve = 'M0,0 Q200,-300 400,0';
      const bend  = 'M0,0 L100,0 L100,300';
      const spread = (f: (u: number) => {x: number; y: number}) => {
        const p: {x: number; y: number}[] = [];
        for (let i = 0; i <= 20; i++) p.push(f(i / 20));
        const s: number[] = [];
        for (let i = 1; i < p.length; i++) s.push(Math.hypot(p[i].x - p[i-1].x, p[i].y - p[i-1].y));
        const lo = Math.min(...s), hi = Math.max(...s);
        return (hi - lo) / hi;
      };
      // the same curve read the naive way, by Bezier parameter
      const byParam = (u: number) => {
        const m = 1 - u;
        return {x: m*m*0 + 2*m*u*200 + u*u*400, y: m*m*0 + 2*m*u*(-300) + u*u*0};
      };
      out.curveArc = spread((u) => pointAt(curve, u));
      out.curveParam = spread(byParam);
      out.bendArc = spread((u) => pointAt(bend, u));
    """)
    assert out["bendArc"] < 0.02, (
        "on straight legs, where chord IS arc, equal steps covered unequal distance (%.3f) — travel is not by "
        "arc length" % out["bendArc"])
    assert out["curveArc"] < 0.08, ("even allowing for chord-vs-arc the curve is uneven: %.3f" % out["curveArc"])
    assert out["curveParam"] > 5 * out["curveArc"], (
        "arc length is no flatter than the Bezier parameter (%.3f vs %.3f) — the thing being fixed is not "
        "being fixed" % (out["curveArc"], out["curveParam"]))


@_NEEDS_NODE
def test_the_ends_are_the_ends_and_nothing_escapes_them():
    """`seg()` overshoots and springs overshoot; a `u` outside 0..1 must land ON the path, not extrapolate off
    the end of it. NaN is the one that hides: it would reach the DOM as `cx="NaN"`, which the browser drops,
    parking the travelling object at the origin — the top-left corner of the frame."""
    out = _run("""
      const d = 'M10,10 L110,10 L110,110';
      out.start = pointAt(d, 0); out.end = pointAt(d, 1);
      // a negative length THROWS inside @remotion/paths, so an un-clamped undershoot takes the render down
      try { out.under = pointAt(d, -3); } catch (e) { out.under = {threw: String(e)}; }
      out.over = pointAt(d, 4); out.nan = pointAt(d, NaN);
    """)
    assert (round(out["start"]["x"]), round(out["start"]["y"])) == (10, 10)
    assert (round(out["end"]["x"]), round(out["end"]["y"])) == (110, 110)
    assert "threw" not in out["under"], (
        "an undershooting u reached @remotion/paths, which throws on a negative length and takes the whole "
        "render with it: %r" % out["under"])
    assert out["under"] == out["start"], "a negative u escaped the start of the path"
    assert out["over"] == out["end"], "a u past 1 escaped the end of the path"
    for k in ("x", "y"):
        assert out["nan"][k] == out["start"][k], (
            "NaN reached the caller as a coordinate; it would park the object at the frame's origin")


@_NEEDS_NODE
def test_the_angle_is_the_direction_of_travel_in_degrees():
    """Degrees because that is what `rotate()` takes — a caller converting from radians each time is a caller
    with a chance to convert wrong."""
    out = _run("""
      out.right = angleAt('M0,0 L100,0', 0.5);
      out.down = angleAt('M0,0 L0,100', 0.5);
      out.up = angleAt('M0,100 L0,0', 0.5);
      out.diag = angleAt('M0,0 L100,100', 0.5);
    """)
    assert abs(out["right"]) < 1e-6
    assert abs(out["down"] - 90) < 1e-6, out["down"]
    assert abs(abs(out["up"]) - 90) < 1e-6, out["up"]
    assert abs(out["diag"] - 45) < 1e-6, out["diag"]


@_NEEDS_NODE
def test_measuring_the_same_path_twice_costs_one_measurement_and_stays_right():
    """These run per travelling object per frame — six routes at 30fps is 180 parses a second of six strings
    that change only when the layout does. A cache that returned a stale length would be worse than no cache,
    so the key is the string itself: a path that genuinely changes shape is measured again."""
    out = _run("""
      const a = 'M0,0 L300,0';
      const b = 'M0,0 L900,0';
      out.a1 = pathLength(a); out.b = pathLength(b); out.a2 = pathLength(a);
      // past the eviction bound, and then the original again
      for (let i = 0; i < 700; i++) pathLength(`M0,0 L${i + 1},0`);
      out.a3 = pathLength(a);
      out.size = _internals.LENGTHS.size; out.max = _internals.MAX;
    """)
    assert abs(out["a1"] - 300) < 1e-6 and abs(out["b"] - 900) < 1e-6
    assert out["a2"] == out["a1"], "the same path measured twice gave two answers"
    assert abs(out["a3"] - 300) < 1e-6, "after eviction the path was re-measured wrongly"
    assert out["size"] <= out["max"], (
        "the memo has no ceiling — 700 distinct paths left %d entries in it, which on a register whose paths "
        "change every frame is a leak that grows for the length of the render" % out["size"])


def test_both_adopters_ask_the_path_instead_of_re_deriving_it():
    """The defect was never in the maths — each hand-rolled version was reasonable on its own. It was that a
    SECOND description of the curve existed at all, and drifted from the first."""
    mr = open(os.path.join(_REM, "src", "shots", "MapRoutes.tsx"), encoding="utf-8").read()
    code = "\n".join(l.split("//")[0] for l in mr.splitlines())
    assert "pointAt(d, pk)" in code, "MapRoutes no longer places its packet on its own route"
    assert "Math.sin(pk * Math.PI)" not in code, "the hand-rolled sine hump came back"
    lt = open(os.path.join(_REM, "src", "shots", "LightTrails.tsx"), encoding="utf-8").read()
    ltcode = "\n".join(l.split("//")[0] for l in lt.splitlines())
    assert "pointAt(checkD" in ltcode, "LightTrails' head is no longer read off the path it draws"
    assert "function checkPoint" not in ltcode, "the hand-split checkmark sampler came back"
