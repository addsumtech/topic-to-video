"""WorksThrough — the register whose claim is that ONE path runs THROUGH the parts.

The path is the argument. If it breaks, the frame says the opposite of the beat: not "this travels through
here", but "here are some blocks". That is exactly what it drew when it was first written. Each bay held one
y for its whole width and the polygon put two vertices at the SAME x on every boundary, so a change of
direction was a vertical segment of zero width. The demo's gentle deflections left neighbouring bands
overlapping, so it read as a path and looked finished; fed +-0.9 on five parts it rendered as five
disconnected rectangles.

So this measures CONTINUITY on the real render, column by column: the band's vertical extent may move as
fast as it likes, but between two adjacent columns it must still overlap itself. A zero-width step fails
that at every boundary, and no amount of gentle test data hides it.
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

# Alternating hard deflections: the shape a film reaches for when a mechanism doubles back, and the one the
# first version could not draw. `carries` falls away too, so the band is also changing width as it turns.
_ZIGZAG = {"parts": [{"label": "第%d处" % i, "carries": 1 - 0.15 * i, "deflect": (-1) ** i * 0.9}
                     for i in range(1, 6)]}


def _render(props, out, frame=110):
    pf = out + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(dict(props, dna="product"), fh, ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "WorksThrough", out,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    return r.returncode, (r.stderr or "") + (r.stdout or "")


def band_columns(png):
    """Per column, the band's [top, bottom] — the brightest contiguous run, or None where there is none."""
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image", reason="needs Pillow")
    a = np.asarray(Image.open(png).convert("L"), dtype=float)
    # the band is the one bright thing in the section; the ground and its hatch sit near the frame median
    hot = a > (np.median(a) + 45)
    out = []
    for x in range(a.shape[1]):
        ys = np.nonzero(hot[:, x])[0]
        out.append((int(ys.min()), int(ys.max())) if len(ys) else None)
    return out


@needs_toolchain
def test_the_path_is_one_connected_band_however_hard_it_turns(tmp_path):
    out = str(tmp_path / "zig.png")
    rc, err = _render(_ZIGZAG, out)
    assert rc == 0, err[-400:]
    cols = band_columns(out)
    runs = [i for i, c in enumerate(cols) if c]
    assert len(runs) > 200, "almost no band was drawn — the probe is measuring the wrong thing"

    breaks = []
    for x in range(min(runs), max(runs)):
        a, b = cols[x], cols[x + 1]
        if not a or not b:
            continue                                   # the band has not reached here yet; not a break
        if min(a[1], b[1]) < max(a[0], b[0]):          # the two columns' extents do not touch
            breaks.append((x, a, b))
    assert not breaks, (
        "the band jumps between adjacent columns at %d place(s) — first at x=%d, %s then %s. The path is "
        "drawn in disconnected pieces, which argues the opposite of this register's claim. Ramp the centre "
        "line ACROSS each bay instead of holding one y per bay and stepping at the edge."
        % (len(breaks), breaks[0][0], breaks[0][1], breaks[0][2]))
