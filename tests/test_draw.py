"""Drawing a stroke on, without knowing how long it is.

`stroke-dasharray` + `stroke-dashoffset` reveals a stroke from its start, and it needs the path's LENGTH.
Nine call sites in this library guessed that number, and the guess fails silently in one direction: drawn
length is `declared x p` capped at the real length, so declared too LARGE completes the stroke early and then
holds, and declared too SMALL means only part of the path is ever inked — a frame shipped with half a line.

`pathLength={1}` removes the number instead of correcting it: SVG scales the element's own length to 1 for
every dash calculation, so a dash of 1 is exactly the whole path. These tests pin the three properties as a
SET, because they are only meaningful together — a dash of 1 without the normalisation is a dash of one user
unit on a path of several hundred, which draws nothing at all.
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
    tmp = tempfile.mkdtemp(prefix="draw_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        open(entry, "w", encoding="utf-8").write(
            "import {drawOn, dashedStroke} from %s;\nconst out: any = {};\n"
            % json.dumps(os.path.join(_REM, "src", "runtime", "draw"))
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
def test_the_reveal_is_normalised_or_it_draws_nothing():
    """THE ONE THAT MATTERS. `pathLength` is not decoration beside the dash numbers — it is what gives them a
    scale. Drop it and a dasharray of 1 means one user unit: on a 300-unit route that is 0.3% of the stroke,
    so the register renders a dot and no line, at every value of p. The three travel together or not at all.
    """
    out = _run("out.rows = [0, 0.25, 0.5, 1].map((p) => drawOn(p));")
    for p, row in zip([0, 0.25, 0.5, 1], out["rows"]):
        assert row["pathLength"] == 1, (
            "drawOn no longer normalises the path; a dash of 1 is now one user unit and nothing draws: %r" % row)
        assert row["strokeDasharray"] == 1, ("the dash must span the whole normalised path", row)
        assert abs(row["strokeDashoffset"] - (1 - p)) < 1e-12, (p, row)


@_NEEDS_NODE
def test_the_ends_are_exact():
    """A reveal that starts at a sliver or ends a hair short is the defect this replaced, one order smaller."""
    out = _run("out.zero = drawOn(0); out.full = drawOn(1);")
    assert out["zero"]["strokeDashoffset"] == 1, "at p=0 some of the stroke is already inked"
    assert out["full"]["strokeDashoffset"] == 0, "at p=1 the stroke does not quite complete"


@_NEEDS_NODE
def test_a_progress_outside_the_range_cannot_invert_the_dash():
    """`seg()` and the springs both overshoot, and a negative dashoffset does not clamp — it slides the dash
    the other way, so an overshooting reveal would start ERASING from the far end. Clamped at the source."""
    out = _run("out.under = drawOn(-0.4); out.over = drawOn(1.6); out.nan = drawOn(NaN);")
    assert out["under"]["strokeDashoffset"] == 1, out["under"]
    assert out["over"]["strokeDashoffset"] == 0, out["over"]
    assert 0 <= out["nan"]["strokeDashoffset"] <= 1, ("NaN must not reach the DOM as a dashoffset", out["nan"])


@_NEEDS_NODE
def test_a_dashed_stroke_keeps_its_pattern_and_only_travels():
    """The other half of the primitive, and the reason it is separate. When the dash carries MEANING — a
    planned route, a boundary — the reveal cannot be spent on it. `dashedStroke` leaves `pathLength` unset so
    the pattern stays the size the design chose, and animates the offset, which slides the dashes rather than
    growing them."""
    out = _run("""
      out.a = dashedStroke(8, 6, 0);
      out.b = dashedStroke(8, 6, 1);
      out.keys = Object.keys(dashedStroke(8, 6, 0.5));
    """)
    assert out["a"]["strokeDasharray"] == "8 6" and out["b"]["strokeDasharray"] == "8 6"
    assert out["a"]["strokeDashoffset"] == 0
    assert out["b"]["strokeDashoffset"] == -14, "one full cycle of travel is dash+gap"
    assert "pathLength" not in out["keys"], (
        "normalising a MEANINGFUL dash pattern would resize it to the path — the pattern is content")
