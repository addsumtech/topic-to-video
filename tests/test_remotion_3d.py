"""Structural guard for the CSS-3D lens rig — the silent flattening footgun.

In Chrome/Remotion, any opacity<1 / filter / overflow!=visible / blend / mask on a `preserve-3d`
ANCESTOR forces transform-style back to flat and collapses ALL translateZ — a flat (not
per-frame-wrong) image that NO render test reports. So the rig node must stay clean; the scene fade,
the vignette and the DoF blur live on OTHER nodes. This test locks that invariant in place."""
import os
import re

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CAMERA = os.path.join(_SKILL, "remotion", "src", "Camera.tsx")
_SCENESTAGE = os.path.join(_SKILL, "remotion", "src", "stage", "SceneStage.tsx")


def _assert_world_clean(path, label):
    """The preserve-3d `world` rig node must carry NO opacity/filter — either silently flattens all depth."""
    src = open(path, encoding="utf-8").read()
    m = re.search(r"const world:[^=]*=\s*\{(.*?)\n  \};", src, re.S)
    assert m, "could not find the 3D `world` style block in %s" % label
    world = m.group(1)
    assert "preserve-3d" in world, "%s: the world node must be the preserve-3d ancestor" % label
    assert "opacity" not in world, "%s: opacity on the preserve-3d world silently FLATTENS all translateZ" % label
    assert "filter" not in world, "%s: filter on the preserve-3d world silently FLATTENS all translateZ" % label


def test_preserve3d_world_carries_no_opacity_or_filter():
    # Guard BOTH the legacy Camera.tsx AND SceneStage.tsx — the PRIMARY shot-based renderer, which was
    # previously unguarded though its comment claimed 'guarded by tests/test_remotion_3d.py'. (Audit P1.)
    _assert_world_clean(_CAMERA, "Camera.tsx")
    _assert_world_clean(_SCENESTAGE, "SceneStage.tsx")


def test_perspective_container_carries_no_opacity_or_filter():
    src = open(_CAMERA, encoding="utf-8").read()
    # the AbsoluteFill that sets `perspective:` must not also set opacity/filter on the same element.
    m = re.search(r"perspective: `\$\{perspective[^}]*\}px`[^>]*?\}\}", src)
    assert m, "could not find the perspective container style"
    assert "opacity" not in m.group(0) and "filter" not in m.group(0)
