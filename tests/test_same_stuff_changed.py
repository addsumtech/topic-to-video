"""SameStuffChanged — the register whose whole claim is that the material is CONSERVED.

Nothing new arrives and nothing vanishes; the same body is re-apportioned. That is the one sentence this
register exists to say, so it is the one property worth measuring on the real render rather than trusting to
the code. It was not true when the register was first written: each cell's `x` and its `w` were lerped
independently, and two independently lerped edges only meet at the endpoints. Mid-transition the cells
overlapped, so the DRAWN body was narrower than the body — measured on an eight-way split, 1301px of 1652,
21% of the material gone from the frame while the narration said none of it was. Both settled frames were
exact, which is why reading the code and checking the ends both missed it.

So this measures the drawn span at the MIDDLE of a re-forming, at the split that stresses it hardest.
"""
import json
import os
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _render(props, out, frame):
    pf = out + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(dict(props, dna="product"), fh, ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "SameStuffChanged", out,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    return r.returncode, (r.stderr or "") + (r.stdout or "")


def _drawn_span(png, y=520):
    """First and last column of a scanline that is not the frame's own ground."""
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image", reason="needs Pillow")
    a = np.asarray(Image.open(png).convert("L"), dtype=float)
    row = a[y]
    on = np.nonzero(np.abs(row - np.median(a)) > 12)[0]
    assert len(on), "the scanline crosses no body at all — the register drew nothing"
    return int(on.min()), int(on.max())


# One cell becoming EIGHT is the hardest case for the same reason a 2-way split is the easiest: the more
# unequal the two stages' cell counts, the further two independently-lerped edges drift apart.
_SPLIT_8 = {"stages": [{"label": "一整块", "cells": [{"name": "全部", "share": 1}]},
                       {"label": "分成八份",
                        "cells": [{"name": "第%d项" % i, "share": 1} for i in range(1, 9)]}]}


@needs_toolchain
@pytest.mark.parametrize("frame", [80, 110, 140])
def test_the_body_is_the_same_width_while_it_re_forms(tmp_path, frame):
    out = str(tmp_path / ("f%d.png" % frame))
    rc, err = _render(_SPLIT_8, out, frame)
    assert rc == 0, err[-400:]
    x0, x1 = _drawn_span(out)
    # the body zone the register lays out in: W*0.07 .. W*0.93 at 1920 wide
    want0, want1 = round(1920 * 0.07), round(1920 * 0.93)
    assert abs(x0 - want0) <= 3, "the body no longer starts at the left of its zone: %d vs %d" % (x0, want0)
    assert abs(x1 - want1) <= 3, (
        "the drawn body is %dpx wide where the material is %dpx — %.0f%% of it is off the frame while the "
        "register is claiming that none of it went anywhere. The cells are being positioned independently "
        "of their widths again; lay them out end to end from the lerped widths."
        % (x1 - x0 + 1, want1 - want0 + 1, 100.0 * (1 - (x1 - x0 + 1) / float(want1 - want0 + 1))))
