"""Depth of field as a signal — how far a thing is from what the shot is about, said in optics.

This library had planes and no focus: things could sit at different depths and every one of them was
equally sharp, which is the one thing a real lens never does. In the reference library focus is not
decoration — it is how 18 of its recipes say what matters, and one of them puts it plainly: a flat
interface under a moving camera reads as a page scrolling, not as a surface being grazed, unless the far
part goes soft.
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
    tmp = tempfile.mkdtemp(prefix="foc_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        head = "import * as F from %s;\nconst out: any = {};\n" % json.dumps(
            os.path.join(_REM, "src", "runtime", "focus"))
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
def test_the_thing_in_focus_is_left_completely_alone():
    """Not `blur(0px) brightness(1)` — NOTHING. Any filter promotes the element to its own compositing layer,
    so the sharp subject gets resampled through a pipeline it does not need; on a text-bearing register that
    is the difference between crisp type and type that has been through a texture unit."""
    out = _run("""
      const f = F.focusAt(0, 1080);
      out.f = f; out.filter = F.focusFilter(f) ?? null;
    """)
    assert out["filter"] is None, "an in-focus element was given a filter: %r" % out["filter"]
    for k in ("opacity", "brightness", "scale"):
        assert abs(out["f"][k] - 1) < 1e-9, (k, out["f"])
    assert out["f"]["blurPx"] == 0


@_NEEDS_NODE
def test_everything_recedes_together_and_monotonically():
    """Distance dims, softens, darkens and shrinks at once. Moving one of them alone reads as an effect
    applied to an object rather than as the object being further away — and a non-monotonic curve means
    something briefly comes BACK into focus while travelling away, which reads as a flicker."""
    out = _run("""
      out.rows = [0, 0.25, 0.5, 0.75, 1].map((d) => F.focusAt(d, 1080));
    """)
    rows = out["rows"]
    for k, expect_down in (("opacity", True), ("brightness", True), ("scale", True), ("blurPx", False)):
        vals = [r[k] for r in rows]
        pairs = list(zip(vals, vals[1:]))
        assert all((a > b) if expect_down else (a < b) for a, b in pairs), (k, vals)


@_NEEDS_NODE
def test_the_blur_is_a_fraction_of_the_frame_not_a_literal():
    """The reference's 2.2px is on a 480-wide design stage — about 8px at 1920. Copied as a number it is a
    blur nobody can see, which is how a depth cue silently becomes no cue at all."""
    out = _run("""
      out.small = F.focusAt(1, 480).blurPx;
      out.large = F.focusAt(1, 1920).blurPx;
    """)
    assert out["large"] > out["small"] * 3.5, (out["small"], out["large"])


@_NEEDS_NODE
def test_a_shot_with_one_object_has_nothing_to_be_out_of_focus_against():
    """`focusDist` divides by the spread, and a single-item shot has a spread of zero. Returning NaN there
    would reach the filter as `blur(NaNpx)` and blank the element — a shot that vanishes for the one input
    it was not built around."""
    out = _run("""
      out.zeroSpread = F.focusDist(5, 0);
      out.normal = F.focusDist(60, 120);
      out.clamped = F.focusDist(400, 120);
      out.negative = F.focusDist(-60, 120);
    """)
    assert out["zeroSpread"] == 0
    assert abs(out["normal"] - 0.5) < 1e-9
    assert out["clamped"] == 1, "beyond the far plane must clamp, not keep blurring"
    assert abs(out["negative"] - 0.5) < 1e-9, "distance is unsigned — either side of focus recedes"


def test_the_carousel_uses_the_shared_lens_rather_than_its_own_numbers():
    """The reason this file exists as a runtime module and not as a snippet: SurfaceCarousel had four
    literals for the same idea, and the next register wanting a corridor would have written a fifth set."""
    src = open(os.path.join(_REM, "src", "shots", "SurfaceCarousel.tsx"), encoding="utf-8").read()
    assert "focusAt(" in src and "focusFilter(" in src, "the carousel no longer reads the shared lens"
    assert "blur(${" not in src, "a hand-rolled blur came back into the carousel"


def test_the_flyover_grazes_its_page_instead_of_scrolling_it():
    """The recipe that motivated this module: a flat interface under a moving camera reads as a page
    scrolling, not as a surface being examined, unless the part the lens is NOT on goes soft. So the page is
    drawn twice — sharp, and again blurred with a hole cut where the cursor is — and both copies must ride the
    SAME camera, or the soft layer slides against the sharp one and the whole frame reads as a printing
    misregistration.
    """
    src = open(os.path.join(_REM, "src", "shots", "PointerTour.tsx"), encoding="utf-8").read()
    assert "focusAt(" in src, "PointerTour has no depth of field — it is a pan over a flat page again"
    assert src.count("<PageCam2D") == 2, "the page is not drawn twice, so there is nothing to defocus"
    assert "maskImage" in src and "WebkitMaskImage" in src, (
        "the soft copy is not masked (and an unprefixed mask alone is not enough for the render browser)")
    # the mask must follow the CURSOR, not sit at a fixed point: the whole claim is that the thing being
    # pointed at is the thing in focus
    mask = src[src.index("const mask ="):src.index("const page =")]
    assert "target.x" in mask and "target.y" in mask, mask
    # and it must NOT be on during the opening overview, where the whole page IS the subject
    dof = src[src.index("const dof ="):src.index("const dofPx")]
    assert "OPEN" in dof, "the depth of field does not wait for the tour to start"
