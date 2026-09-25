"""The accessibility variant left the biggest motion in the film untouched.

Everything else in this tier honoured `reducedMotion`: `useT()` freezes every register's animation at
`REDUCED_MOTION_T`, the ambient camera is zeroed, the finish layer drops to 0.55. Then the film slid a WHOLE
FRAME across the screen at every marked seam — a push, a slide, a clock wipe, a portal — because
`pickPresentation` was never given the flag. Measured by rendering the same mid-seam frame both ways before
this was fixed: the boundary where the two beats met sat at column 889 against 899, and those ten pixels
were the ambient drift that was already being switched off. The seam itself was identical.

A cross-fade is the answer the html tier already gives for this ("HTML reveals become opacity-only
cross-fades"), it is what the luminance guard in the same function already falls back to, and it carries no
movement at all.

These tests measure the PICTURE rather than the flag, because the flag was being passed correctly to
everything except the one thing that mattered.
"""
import json
import os
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(os.path.dirname(_HERE), "remotion")

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

_PROBE = [
    {"shot": "TermTable", "durF": 60, "props": {"kicker": "ONE", "rows": [["a", "1"], ["b", "2"]]}},
    {"shot": "MadeOf", "durF": 60, "props": {"whole": "TWO"}},
    {"shot": "TermTable", "durF": 60, "props": {"kicker": "BACK", "rows": [["a", "1"], ["b", "2"]]}},
]


def _still(tmp_path, name, transition_in, reduced, frame=102):
    scenes = json.loads(json.dumps(_PROBE))
    if transition_in:
        scenes[2]["transitionIn"] = transition_in
    props = {"scenes": scenes, "dna": "product", "captions": False, "camera": 0}
    if reduced:
        props["reducedMotion"] = True
    pf = str(tmp_path / (name + ".json"))
    json.dump(props, open(pf, "w", encoding="utf-8"))
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png, "--frame=%d" % frame,
                        "--gl=angle", "--timeout=150000", "--scale=0.5", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-500:]
    return png


def _tile_edge(png):
    """(column, strength) of the strongest vertical edge — where two tiling beats meet, if they do."""
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image", reason="needs Pillow")
    import numpy as _np
    a = _np.asarray(Image.open(png).convert("L"), dtype=float)
    g = _np.abs(_np.diff(a.mean(axis=0)))
    return int(_np.argmax(g)), float(g.max())


@needs_toolchain
def test_a_marked_seam_stops_moving_under_reduced_motion(tmp_path):
    """A push tiles two full frames past each other, which shows up as one hard vertical edge travelling
    across the frame. Under reduced motion there must be no such edge, because there is no travel."""
    moving = _tile_edge(_still(tmp_path, "push_on", {"type": "push", "direction": "from-left"}, False))
    still_ = _tile_edge(_still(tmp_path, "push_reduced", {"type": "push", "direction": "from-left"}, True))
    assert moving[1] > 50, (
        "the control frame has no tile boundary, so this probe is not measuring a moving seam any more: %r"
        % (moving,))
    assert still_[1] < moving[1] * 0.8, (
        "under reduced motion the seam still draws a hard tile boundary (column %d, strength %.1f against "
        "the moving seam's %.1f) — a whole frame is sliding across the screen in the accessibility variant"
        % (still_[0], still_[1], moving[1]))


@needs_toolchain
def test_it_becomes_the_same_cross_fade_the_html_tier_promises(tmp_path):
    """The other side: the seam must not merely be DIFFERENT, it must be the plain opacity cross-fade. A
    reduced-motion variant that swapped one movement for another would pass the test above."""
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image", reason="needs Pillow")
    import numpy as _np
    reduced = _np.asarray(Image.open(
        _still(tmp_path, "r_push", {"type": "push", "direction": "from-left"}, True)).convert("L"), dtype=float)
    plain = _np.asarray(Image.open(
        _still(tmp_path, "r_fade", None, True)).convert("L"), dtype=float)
    diff = float(_np.abs(reduced - plain).mean())
    assert diff < 2.0, (
        "a marked seam under reduced motion does not render as the unmarked fade does (mean |difference| "
        "%.2f grey levels) — it is still drawing a seam of its own" % diff)
