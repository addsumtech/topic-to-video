"""The one camera move whose whole claim is that something does NOT change.

A dolly-zoom pins the subject's projected size while the background swells, and it means "this did not
change; what surrounds it did". Every other camera in this library says look closer or here is the whole of
it. The peer study named this as the unbuilt half of its depth gap and gave the figure it uses: subject
pinned, background 1 -> 2.25.

The claim is therefore MEASURABLE, and has to be measured on the rendered frame rather than argued from the
source: a subject that drifted two percent would be quietly making the opposite point while every gate in
this repo stayed green.
"""
import json
import os
import subprocess

import pytest

from test_camera_pan import run_probe

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


# ── the primitive ───────────────────────────────────────────────────────────────────────────────────────
def test_the_ground_swells_from_rest_to_the_peer_figure_and_back():
    out = run_probe("""
out.rest = C.dollyAt(0, 1080).ground;
out.mid = C.dollyAt(0.51, 1080).ground;
out.end = C.dollyAt(1, 1080).ground;
out.swell = C.DOLLY_SWELL;
out.outStart = C.dollyAt(0, 1080, {direction: 'out'}).ground;
out.outEnd = C.dollyAt(1, 1080, {direction: 'out'}).ground;
out.mono = [0, 0.2, 0.4, 0.6, 0.8, 1].map((t) => C.dollyAt(t, 1080).ground);
""")
    assert out["rest"] == pytest.approx(1.0), "the move starts somewhere other than rest: %r" % out["rest"]
    assert out["end"] == pytest.approx(out["swell"]), out
    assert 1.0 < out["mid"] < out["swell"], "the swell is not eased through the middle: %r" % out
    # `out` is the same move read backwards — an overwhelming room receding off a subject that never moved.
    assert out["outStart"] == pytest.approx(out["swell"]) and out["outEnd"] == pytest.approx(1.0), out
    # MONOTONE, for the reason panAt is: a background that grows and shrinks inside one beat is a wobble,
    # and `shake_qa` would be right to call it one.
    assert out["mono"] == sorted(out["mono"]), out["mono"]


def test_the_optical_anchor_rides_the_SWELL_and_not_the_clock():
    """Without the blur AND saturation anchors together, layered material reads as stickers flying rather
    than as depth — the peer case law this library already borrowed for `Plane`. A ground held at full swell
    must stay exactly as soft as it was when it arrived there, which is only true if the anchor reads `k`."""
    out = run_probe("""
const a = C.dollyAt(0, 1080), b = C.dollyAt(1, 1080);
out.restBlur = a.focus.blurPx; out.fullBlur = b.focus.blurPx;
out.restSat = a.focus.saturate; out.fullSat = b.focus.saturate;
out.heldOut = C.dollyAt(1, 1080, {direction: 'out'}).focus.blurPx;
out.startOut = C.dollyAt(0, 1080, {direction: 'out'}).focus.blurPx;
out.scale = b.focus.scale; out.opacity = b.focus.opacity;
""")
    assert out["restBlur"] == pytest.approx(0.0) and out["fullBlur"] > 1.5, out
    assert out["restSat"] == pytest.approx(1.0) and out["fullSat"] < 0.8, out
    # On the way out the clock runs forward while the swell runs back, so the anchor must follow the swell.
    assert out["startOut"] > 1.5 and out["heldOut"] == pytest.approx(0.0), out
    # The dolly owns the SCALE outright and nothing fades: a background that fades is a dissolve, not a lens.
    assert out["scale"] == pytest.approx(1.0) and out["opacity"] == pytest.approx(1.0), out


def test_a_move_that_cannot_move_is_refused_loudly():
    out = run_probe("""
try { C.dollyAt(0.5, 1080, {swell: 1}); out.flat = 'NO THROW'; } catch (e) { out.flat = String(e); }
try { C.dollyAt(0.5, 1080, {swell: 0.4}); out.shrink = 'NO THROW'; } catch (e) { out.shrink = String(e); }
try { C.dollyAt(0.5, 1080, {span: 0}); out.span = 'NO THROW'; } catch (e) { out.span = String(e); }
""")
    for key in ("flat", "shrink", "span"):
        assert "NO THROW" not in out[key], "dollyAt accepted a move that cannot move (%s)" % key


# ── the register, measured on the rendered frame ────────────────────────────────────────────────────────
def _still(props, out_png, frame):
    pf = out_png + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(dict(props, dna="product"), fh, ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DollyZoom", out_png,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stderr or "") + (r.stdout or "")
    return out_png


def _type_bbox(path):
    """The box the BRIGHT ink occupies. With no context labels and no reading line the only bright thing on
    the frame is the subject — the room is hairlines at a fraction of the ink's contrast."""
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(path).convert("L"), dtype=np.float32) / 255.0
    ground = float(np.median(a))
    hit = np.abs(a - ground) > 0.45
    assert hit.any(), "no bright ink on %s — the subject did not draw" % os.path.basename(path)
    ys, xs = np.nonzero(hit)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


@needs_toolchain
def test_the_subject_is_the_same_size_and_in_the_same_place_while_the_room_swells(tmp_path):
    """The argument in one measurement. The room is 2.25x larger at the end than at the start; if the
    subject's box moves at all, the shot is a zoom wearing a dolly-zoom's name."""
    props = {"subject": "One register", "context": [], "reading": ""}
    early = _type_bbox(_still(props, str(tmp_path / "early.png"), 12))
    late = _type_bbox(_still(props, str(tmp_path / "late.png"), 168))
    assert early == late, "the pinned subject moved between frames 12 and 168: %r -> %r" % (early, late)


@needs_toolchain
def test_the_room_ACTUALLY_swells_between_those_two_frames(tmp_path):
    """The other half, and the one a broken dolly passes silently: pinning the subject is trivial if nothing
    else moves. Rendered with context labels, the two frames must differ."""
    from PIL import Image
    import numpy as np
    props = {"subject": "One register", "context": ["a library", "a hundred more", "five aspects", "nine presets"],
             "reading": "the same one, in a bigger room"}
    a = np.asarray(Image.open(_still(props, str(tmp_path / "a.png"), 12)).convert("L"), dtype=np.float32)
    b = np.asarray(Image.open(_still(props, str(tmp_path / "b.png"), 168)).convert("L"), dtype=np.float32)
    moved = float(np.abs(a - b).mean()) / 255.0
    assert moved > 0.004, "the two frames are nearly identical (%.5f) — the room never swelled" % moved


@needs_toolchain
def test_a_subject_left_empty_is_refused_rather_than_drawn_as_an_empty_room(tmp_path):
    props = str(tmp_path / "empty.props.json")
    with open(props, "w", encoding="utf-8") as fh:
        json.dump({"dna": "product", "subject": "  "}, fh)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DollyZoom", str(tmp_path / "x.png"),
                        "--frame=120", "--gl=angle", "--log=error", "--props=" + props],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode != 0, "an empty subject rendered a room with nothing in it"
    assert "DollyZoom needs a `subject`" in (r.stderr or "") + (r.stdout or ""), (r.stderr or "")[-600:]


@needs_toolchain
def test_a_direction_that_is_neither_is_refused_rather_than_read_as_in(tmp_path):
    """The `= {}` default on a props object widens a literal union to `string`, so TypeScript cannot hold
    this prop to its own declared type. `in` and `out` are opposite arguments; a film that writes `inward`
    would otherwise get the opposite beat on a frame that looks perfectly finished."""
    props = str(tmp_path / "dir.props.json")
    with open(props, "w", encoding="utf-8") as fh:
        json.dump({"dna": "product", "subject": "One register", "direction": "inward"}, fh)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DollyZoom", str(tmp_path / "d.png"),
                        "--frame=120", "--gl=angle", "--log=error", "--props=" + props],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode != 0, "a direction that is neither 'in' nor 'out' was silently read as one of them"
    assert "direction must be" in (r.stderr or "") + (r.stdout or ""), (r.stderr or "")[-600:]
