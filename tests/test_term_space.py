"""TermSpace — the last of the peer library's 3D line this tier had no answer to.

`basic-3d-scene` became SpatialSlides and `flying-words` became WordTunnel; `terminal-3d` had nothing. A 2x2
grid of terminals says "here are four things" and makes them peers on one plane; posing them in a room and
flying the camera to each says they COEXIST and you are moving among them.

TWO DEFECTS THE GATES COULD NOT SEE, both found by looking at the first render:

  * A console was drawn BLANK. The type was culled when its projected block left the safe box and the window
    was not, so a viewer saw an empty screen in the corner — a machine that had crashed rather than one the
    camera was passing. Surface and type share one `edgeFade` now.
  * The camera MISSED what it flew to. Backing off as `z: pose.z + d` steps along world z, which is no
    longer behind a lens that has just taken the screen's own rotation: measured 163px off centre on a 1920
    frame for a screen at ry 24deg. It backs off along its own forward axis now.

Neither is visible to `text_safe_qa` (nothing was cut off) or to `cjk_type_qa` (nothing was dropped at the
frame they sample). Both are pinned here.
"""
import json
import os
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
_SRC = os.path.join(_REM, "src", "shots", "TermSpace.tsx")

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")
SOURCE = open(_SRC, encoding="utf-8").read()


def _still(props, out_png, frame):
    pf = out_png + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(dict(props, dna="terminal"), fh, ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "TermSpace", out_png,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    return r


# ── the stage, not a private camera ───────────────────────────────────────────────────────────────────
def test_it_is_built_on_the_shared_stage_and_keeps_type_off_the_Z_plane():
    """`runtime/depth` measured what a 3D-composited layer does to type: 91 flat, 56 under Z. The stage
    carries SURFACES; every word is a flat 2D element placed by `projectPose`. A register that puts its own
    text inside a `Surface` would be soft and no gate would say so."""
    assert "from '../runtime/stage3d'" in SOURCE, "TermSpace no longer uses the shared stage"
    for needed in ("Stage3D", "Surface", "projectPose", "fitStage"):
        assert needed in SOURCE, "it stopped using %s" % needed
    for banned in ("perspective(", "translateZ(", "rotateY(", "rotateX("):
        assert banned not in SOURCE, (
            "TermSpace hand-rolls %s instead of posing on the stage — that is the second camera this "
            "runtime exists to prevent" % banned)
    surface = SOURCE.split("<Surface", 1)[1].split("</Surface>", 1)[0]
    assert "{s.name}" not in surface and "{s.status}" not in surface, (
        "a console's words were moved INSIDE the posed surface, where they are rasterized and upscaled")


def test_the_lens_backs_off_along_ITS_OWN_axis():
    """Written as `z: pose.z + d` the camera takes the screen's rotation and then steps back in a direction
    that is no longer behind it: 163px off centre at ry 24deg, which reads as the camera missing what it
    flew to. The forward axis in CSS's order is (sin ry cos rx, -sin rx, cos ry cos rx)."""
    tour = SOURCE.split("const tour: Pose", 1)[1].split("};", 1)[0]
    assert "Math.sin(ryR)" in tour and "Math.cos(rxR)" in tour, (
        "the dolly is back on world z: %r" % tour[:300])
    assert "Math.sin(rxR)" in tour, "the vertical component of the forward axis is gone"


def test_a_screen_and_its_words_leave_frame_TOGETHER():
    """Culling the type on its own leaves the window drawn: an empty console, which reads as a screen that
    failed rather than one the camera is passing."""
    assert "const edgeFade = (" in SOURCE, "the shared fade is gone"
    # TWO call sites, and they must be the two layers: the stage's surfaces and the flat type over them.
    assert SOURCE.count("edgeFade(") == 2, (
        "edgeFade is called %d time(s) — it exists to be applied to BOTH layers and only those"
        % SOURCE.count("edgeFade("))
    stage = SOURCE.split("<Stage3D", 1)[1].split("</Stage3D>", 1)[0]
    flat = SOURCE.split("</Stage3D>", 1)[1]
    assert "edgeFade(" in stage, "the SURFACE no longer fades — a screen can still go blank on frame"
    assert "edgeFade(" in flat, "the TYPE no longer fades with its screen"
    surface = SOURCE.split("<Surface", 1)[1].split("</Surface>", 1)[0]
    assert "opacity: sf" in surface, "the surface computes a fade and does not apply it"
    assert "* fade" in flat, "the type computes a fade and does not apply it"


def test_the_untyped_tail_stays_in_the_DOM():
    """The caret is what makes this a console, and a status that is trimmed as it types is a string the
    register has declined to draw for most of the shot. It is revealed, not trimmed: the whole line is in
    the DOM from frame one with the untyped tail transparent."""
    assert "s.status.slice(cut)" in SOURCE, "the untyped tail is gone — the gate now sees a short string"
    assert "opacity: 0}}>{s.status.slice(cut)}" in SOURCE.replace("\n", "").replace("  ", ""), (
        "the tail is drawn visibly or not at all")


# ── the artifact ──────────────────────────────────────────────────────────────────────────────────────
@needs_toolchain
def test_every_screen_is_READABLE_on_the_frame_the_gates_sample(tmp_path):
    """`cjk_type_qa` samples DURATION * 0.88, which lands in the close. WordTunnel shipped with its final
    phrase culled and every type gate reported 0 findings, because type that is never drawn is never cut
    off — so the close must hold every string this register was given."""
    from PIL import Image
    import numpy as np
    props = {"screens": [{"name": "ingest", "status": "reading the authorised directory"},
                         {"name": "plan", "status": "ordering the steps"},
                         {"name": "run", "status": "calling the tools"}]}
    png = str(tmp_path / "close.png")
    r = _still(props, png, 167)                                  # 190 * 0.88
    assert r.returncode == 0, (r.stderr or "")[-600:]
    a = np.asarray(Image.open(png).convert("L"), dtype=np.float32) / 255.0
    ground = float(np.median(a))
    ink = np.abs(a - ground) > 0.10
    # three screens, spread across the frame: ink must appear in at least three separate column bands
    cols = ink.sum(axis=0)
    bands = [cols[i:i + a.shape[1] // 6].sum() for i in range(0, a.shape[1], a.shape[1] // 6)]
    lit = sum(1 for b in bands if b > ink.sum() * 0.05)
    assert lit >= 3, "the close does not carry three separated screens — %r" % bands


@needs_toolchain
def test_an_empty_screens_list_is_refused_rather_than_drawn_as_an_empty_room(tmp_path):
    r = _still({"screens": []}, str(tmp_path / "x.png"), 120)
    assert r.returncode != 0, "an empty room rendered as a finished frame"
    assert "TermSpace needs at least one" in (r.stderr or "") + (r.stdout or ""), (r.stderr or "")[-500:]
