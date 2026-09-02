"""MadeOf: the register whose density IS its claim — so the claim had better be true.

WHY IT EXISTS. Measured across the library, the three shapes an explainer film is built from had no dense
register at all: process (12 registers, 0 over the density floor), mechanism (5, 0), and STRUCTURE — "what is
this made of" — which had 3 registers in total and 0 over the floor. Of the 32 registers that do clear the
floor, nine are described by MOOD ("calm premium ambient", "warm storybook") and get their pixels from a
field: they fill the frame precisely because they are not saying anything.

So the one thing that must be pinned here is that its pixels are the CONTENT. A region's area is its share,
which means an area that means nothing cannot be drawn — and it means the frame can LIE, in a way a mood
register never can. These tests read the rendered PNG and check the proportions it actually painted.
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


def render(props, frame=140):
    d = tempfile.mkdtemp(prefix="madeof_")
    pf = os.path.join(d, "p.json")
    json.dump(props, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
    png = os.path.join(d, "o.png")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "MadeOf", png,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=REMOTION, capture_output=True, text=True)
    assert os.path.exists(png), (r.stdout or "") + (r.stderr or "")
    return png


def cell_areas(png, top_frac=0.20, bottom_frac=0.80):
    """Area of each distinct fill in the partition band, as a fraction of the band.

    Sampled from a horizontal slice clear of the title and the caption band, and quantised so anti-aliased
    edges and the inset hairline do not become their own 'cells'."""
    im = Image.open(png).convert("RGB")
    W, H = im.size
    a = np.asarray(im.crop((0, int(H * top_frac), W, int(H * bottom_frac)))).astype(np.int16)
    q = (a // 24) * 24
    flat = q.reshape(-1, 3)
    keys, counts = np.unique(flat, axis=0, return_counts=True)
    tot = counts.sum()
    return sorted((c / tot for c in counts if c / tot > 0.02), reverse=True)


@_NEEDS
def test_the_areas_are_the_shares():
    """The frame must not lie: a region twice the size means twice the share, or the picture is a chart that
    disagrees with its own numbers."""
    shares = [50, 25, 15, 10]
    png = render({"dna": "product", "whole": "T",
                  "parts": [{"label": "a", "share": s} for s in shares]})
    got = cell_areas(png)[:len(shares)]
    assert len(got) == len(shares), "expected %d regions, segmented %d: %r" % (len(shares), len(got), got)
    want = [s / sum(shares) for s in shares]
    for w, g in zip(want, got):
        assert abs(w - g) < 0.06, "share %.2f painted as %.2f (all: %r)" % (w, g, got)


@_NEEDS
def test_the_partition_leaves_no_ground_showing():
    """Density here is a property of the claim, not an addition to it — which only holds if the parts TILE
    the zone. A gap would be decoration's opposite: a hole that means nothing."""
    png = render({"dna": "product", "parts": [{"label": "a", "share": 60}, {"label": "b", "share": 40}]})
    im = Image.open(png).convert("L")
    W, H = im.size
    band = np.asarray(im.crop((0, int(H * 0.25), W, int(H * 0.72)))).astype(np.float32) / 255
    # the film's ground is near-black; the partition is not. Nothing in the band may still be the ground.
    assert (band < 0.06).mean() < 0.02, "%.1f%% of the partition band is still bare ground" % (
        (band < 0.06).mean() * 100)


@_NEEDS
def test_a_part_with_no_share_is_dropped_not_drawn_at_zero():
    """A zero-area region is a label with nothing under it — it would read as a part that exists and is
    infinitesimal, which is a different claim from 'not a part'."""
    png = render({"dna": "product", "parts": [{"label": "a", "share": 60}, {"label": "gone", "share": 0},
                                              {"label": "b", "share": 40}]})
    got = cell_areas(png)
    assert len(got) == 2, "a zero share was drawn: %r" % (got,)


@_NEEDS
def test_nothing_it_draws_enters_the_caption_band():
    """The whole-level note was first placed under the partition, which is inside the band the burned
    subtitle owns — the exact collision that, on another register, turned two legible whites into mush the
    moment the ground changed."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
    import shot_still_qa as q
    png = render({"dna": "product", "whole": "T", "note": "a qualifier long enough to wrap onto two lines",
                  "parts": [{"label": "a", "share": 55}, {"label": "b", "share": 45}]})
    r = q.measure(png)
    assert r["caption"] <= q.CAPTION_FRAC_ERR, "it puts %.1f%% of content in the caption band" % (
        r["caption"] * 100)


@_NEEDS
@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1", "4:5"])
def test_it_fills_the_frame_at_every_aspect(aspect):
    """The 'small' half of this library's emptiness is composition inset into a corner — four of its sparsest
    registers occupy 9% to 19% of the frame. A partition that does not fill is not a partition."""
    png = render({"dna": "product", "aspect": aspect,
                  "parts": [{"label": "a", "share": 40}, {"label": "b", "share": 35}, {"label": "c", "share": 25}]})
    a = np.asarray(Image.open(png).convert("L").resize((192, 108))).astype(np.float32) / 255
    ink = np.abs(a - np.median(a)) > 0.10
    assert ink.mean() > 0.30, "%s: only %.1f%% ink" % (aspect, ink.mean() * 100)
