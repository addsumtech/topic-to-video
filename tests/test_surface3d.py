"""runtime/surface3d — one lens, surfaces posed under it, their content as their children (a Grok Bot film).

The projection is the one CSS applies (a point on a turned surface lands where the browser draws it); a turned surface
converges toward its vanishing point; and thickness is never stacked translateZ layers, which re-sorted over the face
for a frame (near-black flashes, 2026-11-01)."""
import os
import re

import pytest

import _tsprobe as tp

needs_node = pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")
SRC = os.path.join(tp.RUNTIME, "surface3d.tsx")


@needs_node
def test_an_unturned_surface_projects_where_it_is_and_a_turned_one_converges():
    out = tp.run_ts("import {project, toWorld} from %s;" % tp.mod("surface3d.tsx"), """
      const cam = {P: 1200, vx: 960, vy: 540};
      const flat = {cx: 960, cy: 540, w: 400, h: 300, rx: 0, ry: 0};
      out.flatTL = project(cam, flat, 0, 0); out.flatBR = project(cam, flat, 400, 300);
      const turned = {cx: 960, cy: 540, w: 400, h: 300, rx: 0, ry: 0.5};
      const l = [project(cam, turned, 0, 0), project(cam, turned, 0, 300)];
      const r = [project(cam, turned, 400, 0), project(cam, turned, 400, 300)];
      out.left = l[1].y - l[0].y; out.right = r[1].y - r[0].y;
    """)
    assert out["flatTL"] == {"x": 760, "y": 390} and out["flatBR"] == {"x": 1160, "y": 690}
    assert abs(out["left"] - out["right"]) > 10, out          # one side nearer, taller: it converges


def test_thickness_is_never_stacked_translateZ_layers():
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", open(SRC, encoding="utf-8").read(), flags=re.S)
    assert "translateZ(" not in code and "preserve-3d" not in code.replace("preserve ? 'preserve-3d'", ""), \
        "stacked depth layers re-sort over the face for a frame — paint thickness in the face's plane"
