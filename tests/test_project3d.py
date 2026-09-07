"""project3d — putting real type on a thing in 3D space.

The helper exists because the two obvious ways to label a WebGL object both fail on a Chinese film: a CJK
glyph baked onto a texture is mush at render scale AND dims when its object turns away from the key light,
and drei's <Html> is not a dependency. So the label stays DOM and this says where to put it.

These run the REAL module through node, not a grep of its source, and the central one checks the arithmetic
against three.js's own camera — because "my projection is correct" is exactly the claim that is worth
nothing unless something independent agrees with it.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")

_NEEDS_NODE = pytest.mark.skipif(
    not (shutil.which("npx") and shutil.which("node") and os.path.isdir(os.path.join(_REM, "node_modules"))),
    reason="needs the remotion toolchain")


def _run(body, extra_import=""):
    """Bundle `body` against the real project3d module and run it under node.

    The probe lives INSIDE the remotion directory, not in /tmp: esbuild resolves bare imports relative to the
    entry file, so a probe outside the project cannot find `three` and the comparison this file exists for
    would be skipped rather than run.
    """
    tmp = tempfile.mkdtemp(prefix="p3d_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        header = ("import * as P from %s;\n%s\nconst out: any = {};\n"
                  % (json.dumps(os.path.join(_REM, "src", "runtime", "project3d")), extra_import))
        open(entry, "w", encoding="utf-8").write(header + body + "\nconsole.log(JSON.stringify(out));\n")
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
def test_it_agrees_with_threes_own_camera():
    """THE ONE THAT MATTERS. A label sits on its object only if this arithmetic matches the arithmetic the
    renderer used, so the check is against three's PerspectiveCamera projecting the same points — not against
    numbers I worked out by hand, which would only prove I can reproduce my own mistake."""
    out = _run("""
      const W = 1920, H = 1080, FOV = 40;
      const cam: P.Vec3 = [1.2, 2.0, 5.0], aim: P.Vec3 = [0.1, 0.2, -0.3];
      const pts: P.Vec3[] = [[0,0,0], [1,0.5,-1], [-2,1.2,0.7], [0.3,-0.8,2.1], [2.5,2.5,-2.5]];

      const c = new THREE.PerspectiveCamera(FOV, W / H, 0.1, 100);
      c.position.set(cam[0], cam[1], cam[2]);
      c.up.set(0, 1, 0);
      c.lookAt(new THREE.Vector3(aim[0], aim[1], aim[2]));
      c.updateMatrixWorld(true);
      c.updateProjectionMatrix();

      out.pairs = pts.map((p) => {
        const mine = P.project(p, cam, aim, FOV, W, H);
        const v = new THREE.Vector3(p[0], p[1], p[2]).project(c);
        return {
          mine: mine ? [mine.x, mine.y] : null,
          three: [(v.x * 0.5 + 0.5) * W, (0.5 - v.y * 0.5) * H],
        };
      });
    """, extra_import="import * as THREE from 'three';")
    for i, pair in enumerate(out["pairs"]):
        assert pair["mine"] is not None, "point %d projected to null" % i
        mx, my = pair["mine"]
        tx, ty = pair["three"]
        assert abs(mx - tx) < 0.5 and abs(my - ty) < 0.5, \
            "point %d: mine=(%.2f, %.2f) three=(%.2f, %.2f)" % (i, mx, my, tx, ty)


@_NEEDS_NODE
def test_a_point_behind_the_lens_has_no_position():
    """It returns null rather than a clamped edge coordinate. A label for something behind you drawn at the
    frame edge is a confident lie about where the thing is; the caller has to decide not to draw it."""
    out = _run("""
      const W = 1920, H = 1080;
      out.behind = P.project([0, 0, 9], [0, 0, 5], [0, 0, 0], 40, W, H);
      out.front  = P.project([0, 0, 0], [0, 0, 5], [0, 0, 0], 40, W, H) !== null;
      out.onLens = P.project([0, 0, 5], [0, 0, 5], [0, 0, 0], 40, W, H);
    """)
    assert out["behind"] is None
    assert out["onLens"] is None, "a point AT the lens has no projection either"
    assert out["front"] is True


@_NEEDS_NODE
def test_a_top_down_camera_does_not_produce_nan_labels():
    """A shot that tilts to top-down is an ordinary move. Looking straight down, the forward vector is
    parallel to world up and the right-vector is undefined — without a nudged reference every label on that
    frame becomes NaN and silently disappears."""
    out = _run("""
      const W = 1920, H = 1080;
      const at = P.project([1, 0, 0], [0, 6, 0], [0, 0, 0], 40, W, H);
      out.ok = at !== null && isFinite(at.x) && isFinite(at.y);
      out.at = at ? [at.x, at.y] : null;
    """)
    assert out["ok"] is True, out


@_NEEDS_NODE
def test_the_frame_centre_is_where_the_camera_aims():
    """The simplest invariant, and the one that catches a sign flip: the aim point lands dead centre."""
    out = _run("""
      const W = 1600, H = 900;
      const at = P.project([0.4, 1.1, -2.0], [3, 2, 4], [0.4, 1.1, -2.0], 40, W, H);
      out.at = at ? [at.x, at.y, at.depth] : null;
    """)
    x, y, depth = out["at"]
    assert abs(x - 800) < 0.01 and abs(y - 450) < 0.01, out["at"]
    assert depth > 0


@_NEEDS_NODE
def test_depth_orders_things_front_to_back():
    """`depth` is what a caller uses to draw near labels over far ones, so it has to grow with distance."""
    out = _run("""
      const near = P.project([0, 0, 1], [0, 0, 5], [0, 0, 0], 40, 1920, 1080);
      const far  = P.project([0, 0, -3], [0, 0, 5], [0, 0, 0], 40, 1920, 1080);
      out.near = near ? near.depth : null;
      out.far = far ? far.depth : null;
    """)
    assert out["near"] < out["far"]


@_NEEDS_NODE
def test_yaw_point_matches_the_rotation_a_group_applies():
    """Labels track an object only if the shot's <group rotation={[0, yaw, 0]}> and the label's own maths are
    the same rotation. Checked against three's Object3D rather than restated here."""
    out = _run("""
      const yaw = 0.37;
      const p: P.Vec3 = [1.3, 0.5, -0.8];
      const mine = P.yawPoint(p, yaw);
      const g = new THREE.Object3D();
      g.rotation.set(0, yaw, 0);
      g.updateMatrixWorld(true);
      const v = new THREE.Vector3(p[0], p[1], p[2]).applyMatrix4(g.matrixWorld);
      out.mine = mine; out.three = [v.x, v.y, v.z];
    """, extra_import="import * as THREE from 'three';")
    for a, b in zip(out["mine"], out["three"]):
        assert abs(a - b) < 1e-6, (out["mine"], out["three"])


@_NEEDS_NODE
def test_on_ring_spaces_items_evenly_on_the_ground_plane():
    out = _run("""
      const n = 6, r = 2;
      const pts = Array.from({length: n}, (_, i) => P.onRing(i, n, r, 0.5));
      out.radii = pts.map((p) => Math.hypot(p[0], p[2]));
      out.heights = pts.map((p) => p[1]);
      out.gaps = pts.map((p, i) => {
        const q = pts[(i + 1) % n];
        return Math.hypot(p[0] - q[0], p[2] - q[2]);
      });
    """)
    assert all(abs(r - 2) < 1e-9 for r in out["radii"])
    assert all(abs(h - 0.5) < 1e-9 for h in out["heights"])
    assert max(out["gaps"]) - min(out["gaps"]) < 1e-9, "spacing must be even"
