"""The 3D stage: does the arithmetic land where CSS actually draws?

This is the one failure a posed-card stage cannot ship with, and this repo has already paid for it once —
`runtime/aimCamera` records six PortRail labels sitting 215px off their own modules on a frame that read as
perfectly correct with the wrong words on it, because two cameras agreed until they quietly did not. The
maths tests below are cheap; the one that matters RENDERS the probe and measures the distance between a dot
CSS placed and a dot `projectPose` placed.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
REMOTION = os.path.join(os.path.dirname(_HERE), "remotion")
RUNTIME = os.path.join(REMOTION, "src", "runtime")


def run_probe(body):
    """Bundle `body` against the REAL stage3d.tsx and run it under node, returning its JSON."""
    if not shutil.which("npx") or not shutil.which("node"):
        pytest.skip("npx/node unavailable")
    if not os.path.isdir(os.path.join(REMOTION, "node_modules")):
        pytest.skip("remotion/node_modules not installed")
    tmp = tempfile.mkdtemp(prefix="stage3d_probe_")
    try:
        entry = os.path.join(tmp, "probe.tsx")
        header = ("import * as S from %s;\nconst out: any = {};\n"
                  % json.dumps(os.path.join(RUNTIME, "stage3d")))
        open(entry, "w", encoding="utf-8").write(header + body + "\nconsole.log(JSON.stringify(out));\n")
        out = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node",
                            "--external:react", "--external:remotion", "--outfile=" + out,
                            "--log-level=error"], cwd=REMOTION, capture_output=True, text=True)
        assert b.returncode == 0, "esbuild failed:\n" + b.stdout + b.stderr
        env = dict(os.environ, NODE_PATH=os.path.join(REMOTION, "node_modules"))
        r = subprocess.run(["node", out], cwd=REMOTION, capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_the_camera_is_the_inverse_of_a_pose():
    """`camera = stepTransform.inverse()` is the whole formula the stage rests on, so the inverse has to BE
    one: pose composed with its own inverse is the identity, on a pose with all three rotations, a
    translation and a scale at once. A transposed rotation passes an axis-aligned case and fails this."""
    r = run_probe("""
      const p = {x: 137, y: -88, z: 214, rx: 23, ry: -41, rz: 17, s: 1.7};
      const I = S.mul(S.inverseOf(p), S.matrixOf(p));
      out.roundTrip = I;
      out.worst = Math.max(...I.map((v: number, i: number) => Math.abs(v - S.identity()[i])));
    """)
    assert r["worst"] < 1e-9, "pose * inverse is not the identity (worst term %g)" % r["worst"]


def test_a_point_projects_where_the_perspective_divide_puts_it():
    """The projection is CSS's own: with `perspective: P` and the origin at the frame's centre, a point at
    eye-space z maps out by P/(P - z). Checked against hand-computed values rather than against itself."""
    r = run_probe("""
      const W = 1920, H = 1080, P = 1200;
      out.centre  = S.projectPose({}, {}, P, W, H);
      out.nearer  = S.projectPose({x: 100, z: 600}, {}, P, W, H);   // k = 1200/600 = 2
      out.further = S.projectPose({x: 100, z: -1200}, {}, P, W, H); // k = 1200/2400 = 0.5
      out.atEye   = S.projectPose({z: 1200}, {}, P, W, H);
      out.pastEye = S.projectPose({z: 1400}, {}, P, W, H);
    """)
    assert abs(r["centre"]["x"] - 960) < 1e-6 and abs(r["centre"]["y"] - 540) < 1e-6
    assert abs(r["centre"]["k"] - 1) < 1e-9
    assert abs(r["nearer"]["k"] - 2) < 1e-9, "k=%r" % r["nearer"]["k"]
    assert abs(r["nearer"]["x"] - (960 + 200)) < 1e-6
    assert abs(r["further"]["k"] - 0.5) < 1e-9
    assert abs(r["further"]["x"] - (960 + 50)) < 1e-6
    # AT the eye the divide is meaningless and PAST it the sign flips — a bare division hands back a mirrored
    # position one frame before a card crosses the lens, which draws as a card that jumps to the other side.
    assert r["atEye"]["behind"] and r["pastEye"]["behind"]


def test_fit_stage_backs_off_until_every_pose_is_inside_the_box():
    """The box is the shot's own — the caption band is not part of it — so "does it fit" and "does it land on
    the subtitle" are one question. `runtime/fitCamera` records why this bisects rather than solving in closed
    form: the half of an object nearer the lens projects larger than its centre depth predicts, so a formula
    under-reports the extent and came within 14px of failing at 4:3."""
    r = run_probe("""
      const W = 1080, H = 1080, P = 1242;
      const poses = [{x: -700, y: -520, z: 300}, {x: 760, y: 540, z: -200}, {x: 0, y: 0, z: 0}];
      const box = {left: 60, top: 176, right: W - 60, bottom: 823};
      const fit = S.fitStage(poses, {}, box, P, W, H);
      out.fits = fit.fits; out.z = fit.cam.z;
      out.at = poses.map((p: any) => S.projectPose(p, fit.cam, P, W, H));
      // and the camera it found is the NEAREST that fits: a hair closer must not
      const closer = {...fit.cam, z: (fit.cam.z ?? 0) - 40};
      out.closer = poses.map((p: any) => S.projectPose(p, closer, P, W, H));
    """)
    assert r["fits"], "no camera distance framed three poses inside the box"
    box = {"left": 60, "top": 176, "right": 1020, "bottom": 823}
    for q in r["at"]:
        assert not q["behind"]
        assert box["left"] <= q["x"] <= box["right"], q
        assert box["top"] <= q["y"] <= box["bottom"], q
    assert any(q["x"] < box["left"] or q["x"] > box["right"] or q["y"] < box["top"] or q["y"] > box["bottom"]
               for q in r["closer"]), "the fit is not tight — 40px closer still fits, so it over-pulled"


def test_face_shade_separates_a_face_turned_away_from_one_facing_the_key():
    """`cube-navigation`'s six faces are one rectangle each; what stops them reading as six flat panels is
    that each is shaded by its own normal. A shade function that returns nearly the same number for a face
    turned 90 degrees away is decoration."""
    r = run_probe("""
      out.front = S.faceShade({}, {});
      out.side  = S.faceShade({ry: 90}, {});
      out.back  = S.faceShade({ry: 180}, {});
      out.tilt  = S.faceShade({rx: 45}, {});
    """)
    assert r["front"] > 0.9, "a face square to the key is not lit: %r" % r["front"]
    assert r["side"] < r["front"] - 0.4, "a face edge-on is barely darker (%r vs %r)" % (r["side"], r["front"])
    assert r["back"] <= r["side"] + 1e-9, "a face turned away is not the darkest"
    assert r["front"] > r["tilt"] > r["side"], "the shade is not monotone through the tilt"


def _stage_report():
    """Render the probe with its reporter armed and return what the BROWSER measured for each marker."""
    if not shutil.which("npx"):
        pytest.skip("npx unavailable")
    tmp = tempfile.mkdtemp(prefix="stage3d_render_")
    try:
        png = os.path.join(tmp, "probe.png")
        props = os.path.join(tmp, "p.json")
        open(props, "w", encoding="utf-8").write(json.dumps({"report": True}))
        r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "StageProbe", png,
                            "--frame=10", "--gl=angle", "--log=error", "--props=" + props],
                           cwd=REMOTION, capture_output=True, text=True)
        blob = (r.stdout or "") + (r.stderr or "")
        assert "STAGE-PROBE " in blob, "the probe did not report:\n" + blob[-1200:]
        return json.JSONDecoder().raw_decode(blob.split("STAGE-PROBE ", 1)[1])[0]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_project_pose_lands_where_css_draws_it():
    """THE ONE THAT MATTERS. Everything above tests the arithmetic against itself; this asks the BROWSER
    where it drew each marker and compares. `runtime/aimCamera` records what the alternative costs: six
    labels 215px off their own modules, on a frame that read as correct.

    The poses are deliberately awkward — all three rotations at once, off-centre, at depth, under a camera
    that is itself rotated and dollied — because an axis-aligned probe is also passed by a transposed matrix.

    It reads `getBoundingClientRect` rather than the pixels, and that is a correction, not a convenience: a
    disc's centroid under perspective is not the projection of its centre, so the pixel version reported the
    CLEAN code 4.4px out on these poses and then, shrunk, caught a mutant by a dot that had gone MISSING
    rather than by a distance. The positive control below is the failure this file exists to prevent — the
    CSS given one perspective and the arithmetic another — and it moves the markers by hundreds of pixels.
    """
    rep = _stage_report()
    assert len(rep["rows"]) == 5, "the probe poses five markers, the browser reported %d" % len(rep["rows"])
    worst, where = 0.0, None
    for row in rep["rows"]:
        d = ((row["css"][0] - row["math"][0]) ** 2 + (row["css"][1] - row["math"][1]) ** 2) ** 0.5
        if d > worst:
            worst, where = d, row
    assert worst < 1.0, (
        "projectPose disagrees with CSS by %.2f px (marker %s: browser %s, arithmetic %s) — the drawn camera "
        "and the arithmetic one have come apart, which ships as a frame that looks right with every label in "
        "the wrong place" % (worst, where["i"], where["css"], where["math"]))


def test_fit_surfaces_frames_the_planes_themselves_not_spheres_around_them():
    """`fitStage` treats each pose as a point with a RADIUS, which for a wide tilted plane is a sphere far
    bigger than the plane: the camera backs off and the shot sits small in a mostly empty frame. That is
    exactly what the first render of `PlaneStack` did. `fitSurfaces` projects the four CORNERS instead, so
    the distance it finds is the one the drawn quad actually needs.

    Both must LAND — every corner inside the box — and the corner fit must not be the more distant of the
    two, or it is not solving a tighter problem."""
    r = run_probe("""
      const W = 1920, H = 1080, P = Math.round(Math.min(W, H) * S.PERSP_FRAC);
      const box = {left: 54, top: 176, right: W - 54, bottom: 890};
      const planes = [0, 1, 2].map((i) => ({
        pose: {x: 0, y: (i - 1) * 224, z: -(i - 1) * 54, rx: -48, ry: -8},
        w: 713, h: 281,
      }));
      const surf = S.fitSurfaces(planes, {}, box, P, W, H, {pad: 11});
      const sphere = S.fitStage(planes.map((p) => p.pose), {}, box, P, W, H,
        {radius: Math.hypot(713, 281) / 2});
      out.surf = surf; out.sphere = sphere;
      const corners: any[] = [];
      for (const {pose, w, h} of planes) {
        for (const [dx, dy] of [[-w / 2, -h / 2], [w / 2, -h / 2], [-w / 2, h / 2], [w / 2, h / 2]]) {
          corners.push(S.projectLocal(pose, surf.cam, P, W, H, dx, dy));
        }
      }
      out.corners = corners;
      out.box = box;
    """)
    assert r["surf"]["fits"] is True
    for q in r["corners"]:
        assert not q["behind"]
        assert r["box"]["left"] - 1 <= q["x"] <= r["box"]["right"] + 1, q
        assert r["box"]["top"] - 1 <= q["y"] <= r["box"]["bottom"] + 1, q
    # the sphere fit stands further back — the whole reason the corner fit exists
    assert r["surf"]["cam"]["z"] < r["sphere"]["cam"]["z"] * 0.95, (r["surf"]["cam"], r["sphere"]["cam"])


def test_fit_surfaces_centres_what_is_drawn_not_the_poses():
    """A yaw swings the far corners one way and perspective enlarges the near ones, so aiming at the
    centroid of the POSES leaves the ink off to one side with an empty margin opposite — which is how
    `PlaneStack` first read as a stack shoved to the right of an empty frame."""
    r = run_probe("""
      const W = 1920, H = 1080, P = Math.round(Math.min(W, H) * S.PERSP_FRAC);
      const box = {left: 54, top: 176, right: W - 54, bottom: 890};
      const planes = [0, 1, 2].map((i) => ({
        pose: {x: 0, y: (i - 1) * 224, z: -(i - 1) * 54, rx: -48, ry: -22},
        w: 713, h: 281,
      }));
      const fit = S.fitSurfaces(planes, {}, box, P, W, H);
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const {pose, w, h} of planes) {
        for (const [dx, dy] of [[-w / 2, -h / 2], [w / 2, -h / 2], [-w / 2, h / 2], [w / 2, h / 2]]) {
          const q = S.projectLocal(pose, fit.cam, P, W, H, dx, dy);
          x0 = Math.min(x0, q.x); x1 = Math.max(x1, q.x);
          y0 = Math.min(y0, q.y); y1 = Math.max(y1, q.y);
        }
      }
      out.ink = {x0, x1, y0, y1}; out.box = box;
    """)
    ink, box = r["ink"], r["box"]
    cx = (ink["x0"] + ink["x1"]) / 2, (box["left"] + box["right"]) / 2
    cy = (ink["y0"] + ink["y1"]) / 2, (box["top"] + box["bottom"]) / 2
    assert abs(cx[0] - cx[1]) <= 12, "the drawn stack is %.0fpx off the box's centre horizontally" % (cx[0] - cx[1])
    assert abs(cy[0] - cy[1]) <= 12, "the drawn stack is %.0fpx off the box's centre vertically" % (cy[0] - cy[1])
