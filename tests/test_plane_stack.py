"""The layers a system is made of — measured on the rendered frame, because every claim here is visual.

`PlaneStack` says three things that a passing render does not prove: that the layer the film NAMED is the
one in focus (and no other), that a film which names none gets a stack with nothing picked, and that copy
too big for a plane is refused rather than run off the slab. The first two are read off the pixels; the
third is read off the exit code and the message.

The shot's history is why each of these is here. Its first version placed every word inside `Stage3D`, so
the camera transform was applied to the type a second time and every label landed in a huddle in the corner
while the planes sat in the middle. Its second fitted the camera to a SPHERE around each plane and sat small
in an empty frame. Its third ran a 30-glyph note clean off the right edge of every layer — with every word
still on screen, so the type gates saw nothing missing.
"""
import json
import os
import shutil
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(os.path.dirname(_HERE), "remotion")

needs_toolchain = pytest.mark.skipif(
    not shutil.which("npx") or not os.path.isdir(os.path.join(_REM, "node_modules")),
    reason="needs the remotion toolchain")

LAYERS = [
    {"label": "Coil", "note": "receives", "items": ["array"]},
    {"label": "Gradient", "note": "encodes place", "items": ["X", "Y"]},
    {"label": "Reconstruct", "note": "signal to picture", "items": ["k-space"]},
]


def _still(props, out_png, frame=142):
    pf = out_png + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(dict(props, dna="product"), fh, ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "PlaneStack", out_png,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    return r, out_png


def _rows(path, n=3):
    """The sharpness of each horizontal BAND of the frame, top to bottom — one band per layer.

    A blurred plane's edges are spread, so the band that holds the focal layer measures sharper than the
    others. Measured as the mean absolute horizontal gradient, which needs no knowledge of where anything is.
    """
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(path).convert("L"), dtype=np.float32) / 255.0
    top, bot = int(a.shape[0] * 0.16), int(a.shape[0] * 0.82)
    band = a[top:bot]
    out = []
    for i in range(n):
        s = band[int(band.shape[0] * i / n):int(band.shape[0] * (i + 1) / n)]
        out.append(float(np.abs(np.diff(s, axis=1)).mean()))
    return out


@needs_toolchain
def test_the_layer_the_film_names_is_the_one_in_focus(tmp_path):
    """Not the first, not the middle — the one named. A register that blurred by POSITION would pass every
    gate in this repo and quietly make a claim the film never made (case law E14)."""
    sharp = {}
    for focal in (0, 2):
        r, png = _still({"title": "A machine", "layers": LAYERS, "focal": focal},
                        str(tmp_path / ("f%d.png" % focal)))
        assert r.returncode == 0, (r.stderr or "")[-800:]
        sharp[focal] = _rows(png)
    # the named band is the sharpest of the three, and it moves when the film moves `focal`
    assert sharp[0].index(max(sharp[0])) == 0, sharp[0]
    assert sharp[2].index(max(sharp[2])) == 2, sharp[2]


@needs_toolchain
def test_a_film_that_names_no_layer_gets_a_stack_with_nothing_picked(tmp_path):
    """`focal` absent is a real answer, not a missing one: every layer is drawn alike. The spread of
    sharpness across the bands collapses compared with the same stack when one layer IS named."""
    r0, none_png = _still({"title": "A machine", "layers": LAYERS}, str(tmp_path / "none.png"))
    assert r0.returncode == 0, (r0.stderr or "")[-800:]
    r1, one_png = _still({"title": "A machine", "layers": LAYERS, "focal": 1}, str(tmp_path / "one.png"))
    assert r1.returncode == 0, (r1.stderr or "")[-800:]
    none, one = _rows(none_png), _rows(one_png)
    spread = lambda v: (max(v) - min(v)) / max(1e-9, max(v))
    assert spread(none) < spread(one) * 0.6, ("unnamed: %r  named: %r" % (none, one))


@needs_toolchain
@pytest.mark.parametrize("props,needle", [
    ({"layers": [{"label": "only"}]}, "draws 2-5 layers"),
    ({"layers": [{"label": "a"}, {"label": "b"}, {"label": "c"}, {"label": "d"},
                 {"label": "e"}, {"label": "f"}]}, "draws 2-5 layers"),
    ({"layers": [{"label": "a"}, {"label": "  "}]}, "has no `label`"),
    ({"layers": [{"label": "a"}, {"label": "b"}], "focal": 7}, "must be a layer index"),
    ({"layers": [{"label": "a", "items": ["1", "2", "3", "4", "5"]}, {"label": "b"}]}, "holds up to 4 items"),
    ({"layers": [{"label": "一个层的名字长到变成一整句话，这已经不是名字了" * 2}, {"label": "b"}]},
     "too long for a layer's label"),
])
def test_what_will_not_fit_is_refused_with_both_measurements(tmp_path, props, needle):
    r, _ = _still(props, str(tmp_path / "bad.png"))
    assert r.returncode != 0, "this should not have rendered: %r" % (props,)
    out = (r.stderr or "") + (r.stdout or "")
    assert needle in out, out[-700:]


@needs_toolchain
def test_the_type_is_not_composited_in_3d(tmp_path):
    """Type inside `Stage3D` is rasterized at layout size and upscaled — 91 glyph edge strength flat against
    56 under `perspective + translateZ`, measured by `runtime/depth`. Every word here belongs to a plane, so
    it is placed by `<OnSurface>`, which returns a screen-space 2D matrix and must sit OUTSIDE the stage.
    Inside it, the camera transform is applied twice: the first version of this shot drew every label in a
    huddle off the corner while the planes sat in the middle of the frame."""
    src = open(os.path.join(_REM, "src", "shots", "PlaneStack.tsx"), encoding="utf-8").read()
    stage = src[src.index("<Stage3D"):src.index("</Stage3D>")]
    assert "OnSurface" not in stage, "type is being drawn inside the 3D stage again"
    assert "OnSurface" in src, "the plane's own words are no longer placed on the plane"
    assert "fitSurfaces" in src, "the camera is no longer fitted to the planes themselves"
