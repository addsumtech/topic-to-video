"""Structural guard for the CSS-3D lens rig — the silent flattening footgun.

In Chrome/Remotion, any opacity<1 / filter / overflow!=visible / blend / mask on a `preserve-3d`
ANCESTOR forces transform-style back to flat and collapses ALL translateZ — a flat (not
per-frame-wrong) image that NO render test reports. So the rig node must stay clean; the scene fade,
the vignette and the DoF blur live on OTHER nodes. This test locks that invariant in place."""
import os
import re

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CAMERA = os.path.join(_SKILL, "remotion", "src", "Camera.tsx")


def test_preserve3d_world_carries_no_opacity_or_filter():
    src = open(_CAMERA, encoding="utf-8").read()
    m = re.search(r"const world:[^=]*=\s*\{(.*?)\n  \};", src, re.S)
    assert m, "could not find the 3D `world` style block in Camera.tsx"
    world = m.group(1)
    assert "preserve-3d" in world, "the world node must be the preserve-3d ancestor"
    assert "opacity" not in world, "opacity on the preserve-3d world silently FLATTENS all translateZ"
    assert "filter" not in world, "filter on the preserve-3d world silently FLATTENS all translateZ"


def test_perspective_container_carries_no_opacity_or_filter():
    src = open(_CAMERA, encoding="utf-8").read()
    # the AbsoluteFill that sets `perspective:` must not also set opacity/filter on the same element.
    m = re.search(r"perspective: `\$\{perspective[^}]*\}px`[^>]*?\}\}", src)
    assert m, "could not find the perspective container style"
    assert "opacity" not in m.group(0) and "filter" not in m.group(0)
