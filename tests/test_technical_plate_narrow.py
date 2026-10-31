"""TechnicalPlate on a frame narrower than its side-callout sheet needs (9:16, 4:5, 1:1, 4:3): a numbered drawing and
a parts key, the object as large as the frame allows.

The 2026-10-30 generality validation drew a film's object on TechnicalPlate at 9:16 at about a third of the frame's
width: the side-callout sheet is 0.52 W with two 0.17 W label columns, every size a fraction of W, so a 9:16 plate was a
561 px square floating in a 1270 px sheet with 15.7 px callouts. Measured on the GPS satellite art (gold body, blue
panels) at the settled frame: 49% of the width before, 80% after at 9:16; 46% -> 53% at 1:1 (the key goes beside the
drawing there, and the frame's height is what is left); 16:9 is the side-callout sheet, unchanged."""
import json
import os
import re
import shutil
import subprocess

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
SRC = open(os.path.join(_REM, "src", "shots", "TechnicalPlate.tsx"), encoding="utf-8").read()
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")) or not shutil.which("npx"),
                                     reason="needs the remotion toolchain")

ART = {"kicker": "PLATE", "object": "A GPS satellite", "plateNo": "FIG. 2", "art": {"id": "GpsSatellite"},
       "parts": [{"n": 1, "label": "solar wing", "x": 0.15, "y": 0.5, "side": "left"},
                 {"n": 2, "label": "antenna array", "x": 0.5, "y": 0.62, "side": "right"},
                 {"n": 3, "label": "bus", "x": 0.5, "y": 0.45, "side": "right"}],
       "note": "Twenty-four of these keep the clock."}


def test_the_narrow_layout_sizes_type_from_the_short_side():
    body = SRC.split("export const renderPlateKey")[1].split("\nexport const TechnicalPlate")[0]
    assert "const TU = short * 16 / 9;" in body, "type is a share of the short side, the 16:9 sizes at every aspect"
    assert not re.search(r"font: `[^`]*\bW \*", body), "a type size scaled by W is a third smaller at 9:16"
    assert re.search(r"font: `[^`]*\$\{KEY\}px", body), "the key's labels are set at KEY"
    assert "W < H * PLATE_SIDE_MIN_ASPECT" in SRC


def _art_width(png):
    from PIL import Image
    rgb = np.asarray(Image.open(png).convert("RGB")).astype(int)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    art = ((r > 120) & (g > 80) & (b < 90) & (r - b > 60)) | ((b > 90) & (b - r > 60) & (g < 110))
    cols = np.where(art.sum(0) >= 12)[0]           # real art, not the 1-2 px accent leaders crossing a column
    return (cols.max() - cols.min()) / rgb.shape[1]


@needs_toolchain
@pytest.mark.parametrize("aspect,floor", [("9:16", 0.70), ("1:1", 0.50)])
def test_the_object_uses_a_narrow_frame(tmp_path, aspect, floor):
    import render_remotion as rr
    frame = int(round(rr.frame_at_t(160, rr.SETTLED_T)))
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(dict(ART, dna="product", aspect=aspect)), encoding="utf-8")
    png = str(tmp_path / "s.png")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "TechnicalPlate", png, "--frame=%d" % frame,
                        "--gl=angle", "--log=error", "--props=" + str(pf)], cwd=_REM, capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
    assert _art_width(png) >= floor, _art_width(png)
