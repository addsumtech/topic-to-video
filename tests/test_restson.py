"""RestsOn: the last of the three explanatory shapes, and the hardest to give mass to.

MECHANISM is a RELATION, relations are conventionally drawn as boxes and arrows, and a line has no area —
which is why the five registers answering "why does this happen" measured a median of 2.4% ink. Here the
relation becomes LOAD: the phenomenon spans only as wide as the reason directly beneath it, each deeper
reason is broader, and the stack assembles from the root upward.

What these pin is the part that could quietly become a stacked bar chart: WIDTH must encode depth (or the
picture is a list that happens to be vertical), the build must run bottom-up (you cannot rest something on a
reason you have not given), and nothing may enter the caption band.
"""
import json
import os
import shutil
import subprocess
import tempfile

import numpy as np
import pytest
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
REMOTION = os.path.join(os.path.dirname(_HERE), "remotion")
_NEEDS = pytest.mark.skipif(
    shutil.which("npx") is None or not os.path.isdir(os.path.join(REMOTION, "node_modules")),
    reason="needs the remotion toolchain")

CAUSES = [{"label": "one"}, {"label": "two"}, {"label": "three"}]


def render(props, frame=160):
    d = tempfile.mkdtemp(prefix="restson_")
    pf = os.path.join(d, "p.json")
    json.dump(props, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
    png = os.path.join(d, "o.png")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "RestsOn", png,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=REMOTION, capture_output=True, text=True)
    assert os.path.exists(png), (r.stdout or "") + (r.stderr or "")
    return png


def block_width(png, y_frac):
    """Width of the drawn block on the row at y_frac, in pixels — read off the render."""
    im = Image.open(png).convert("L")
    W, H = im.size
    row = np.asarray(im.crop((0, int(H * y_frac), W, int(H * y_frac) + 2))).astype(np.float32).mean(axis=0)
    ground = float(np.median(np.concatenate([row[:20], row[-20:]])))
    on = np.abs(row - ground) > 0.06 * 255
    return int(on.sum())


@_NEEDS
def test_width_encodes_depth_so_it_is_not_a_list_that_happens_to_be_vertical():
    """A deeper reason is more foundational and is drawn broader. Without this the shot is InOrder rotated,
    and the two would be making the same claim about different things."""
    png = render({"dna": "product", "effect": "E", "causes": CAUSES})
    # sample inside the effect and inside each cause band: effShare 0.30, then three at 0.2333
    zone_top, zone_h = 176 / 1080, (1080 - 176 - 200) / 1080
    ys = [zone_top + zone_h * f for f in (0.15, 0.42, 0.65, 0.88)]
    widths = [block_width(png, y) for y in ys]
    assert all(b > a for a, b in zip(widths, widths[1:])), \
        "widths do not widen with depth: %r" % widths
    assert widths[-1] > widths[0] * 1.4, "the root is barely broader than the effect: %r" % widths


@_NEEDS
def test_it_builds_from_the_root_upward():
    """The explanatory order — and where the shot's motion comes from. Early in the shot the root is there
    and the effect is not."""
    zone_top, zone_h = 176 / 1080, (1080 - 176 - 200) / 1080
    early = render({"dna": "product", "effect": "E", "causes": CAUSES}, frame=30)
    top_w = block_width(early, zone_top + zone_h * 0.15)
    root_w = block_width(early, zone_top + zone_h * 0.88)
    assert root_w > top_w * 1.5, \
        "at frame 30 the effect is already as present as the root (%d vs %d) — it is not building upward" % (
            top_w, root_w)


@_NEEDS
def test_nothing_it_draws_enters_the_caption_band():
    """Measured as PIXELS in the band: a band with any spread has something drawn in it."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
    from _caption_band import caption_band_px
    for causes in (CAUSES, [], [{"label": "a"}] * 5):
        im = Image.open(render({"dna": "product", "effect": "E", "effectNote": "n",
                                "because": "because", "causes": causes})).convert("L")
        W, H = im.size
        band = np.asarray(im.crop((0, H - caption_band_px(W, H), W, H))).astype(np.float32) / 255
        assert float(band.max() - band.min()) < 0.02, "something is drawn in the caption band"


@_NEEDS
def test_the_joint_rides_the_seam_instead_of_printing_across_a_block():
    """The blocks tile with no gap, so a word placed 'above the seam' lands INSIDE the block above it —
    which is what the first version did, printing the joint across the effect's own bottom edge."""
    with_j = render({"dna": "product", "effect": "E", "because": "BECAUSE", "causes": CAUSES})
    without = render({"dna": "product", "effect": "E", "causes": CAUSES})
    a = np.asarray(Image.open(with_j).convert("L")).astype(np.int16)
    b = np.asarray(Image.open(without).convert("L")).astype(np.int16)
    H = a.shape[0]
    seam = int(176 + (1080 - 176 - 200) * 0.30)
    diff = np.abs(a - b) > 8
    # the joint's ink must live AT the seam, not spread up into the effect block
    assert diff[max(0, seam - 40):seam + 40].sum() > 0, "the joint drew nothing"
    assert diff[:max(0, seam - 60)].sum() == 0, "the joint printed inside the block above the seam"


@_NEEDS
@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1", "4:5"])
def test_it_fills_the_frame_at_every_aspect(aspect):
    png = render({"dna": "product", "effect": "E", "causes": CAUSES, "aspect": aspect})
    a = np.asarray(Image.open(png).convert("L").resize((192, 108))).astype(np.float32) / 255
    assert (np.abs(a - np.median(a)) > 0.10).mean() > 0.25, aspect


@_NEEDS
def test_no_causes_is_a_phenomenon_with_nothing_under_it_not_a_crash():
    render({"dna": "product", "effect": "E", "causes": []})
    render({"dna": "product"})
