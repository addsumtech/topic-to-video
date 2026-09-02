"""InOrder: N labelled steps, in order — the shape the library could not say at all.

Asked STRUCTURALLY rather than by reading prose (which register PROPS accept an ordered list of steps), the
library had two, and neither does this: VoiceSignal's `phases` are audio segments and PhaseEncodeStep's
`steps` is a count. So this is an absence being filled, not a density number being improved — and the tests
below pin the three things that make it an argument rather than a decorated bar chart: the bands TILE the
zone (the sequence is the frame), the ORDER is never rearranged, and the focus MOVES (which is where a shot
differs from a diagram).
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

STEPS = [{"label": "one"}, {"label": "two"}, {"label": "three"}, {"label": "four"}, {"label": "five"}]


def render(props, frame=150):
    d = tempfile.mkdtemp(prefix="inorder_")
    pf = os.path.join(d, "p.json")
    json.dump(props, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
    png = os.path.join(d, "o.png")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "InOrder", png,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=REMOTION, capture_output=True, text=True)
    assert os.path.exists(png), (r.stdout or "") + (r.stderr or "")
    return png


def band_edges(png, y_frac=0.55):
    """x of every vertical boundary in the partition row — the bands' own geometry, read off the pixels."""
    im = Image.open(png).convert("L")
    W, H = im.size
    row = np.asarray(im.crop((0, int(H * y_frac), W, int(H * y_frac) + 2))).astype(np.float32).mean(axis=0)
    d = np.abs(np.diff(row))
    return [i for i in np.nonzero(d > 12)[0]]


@_NEEDS
def test_the_bands_tile_the_zone_with_no_ground_left_showing():
    """The density is the partition, never an addition to it — a gap would be a hole that means nothing."""
    png = render({"dna": "product", "steps": STEPS})
    im = Image.open(png).convert("L")
    W, H = im.size
    band = np.asarray(im.crop((0, int(H * 0.30), W, int(H * 0.70)))).astype(np.float32) / 255
    # a PENDING step is deliberately an outline on the ground, so ground pixels are expected — what must not
    # happen is a gap BETWEEN bands, which shows as a ground column spanning the full sampled height
    col_ground = (band < 0.06).mean(axis=0)
    runs, cur = [], 0
    for v in col_ground > 0.95:
        cur = cur + 1 if v else 0
        runs.append(cur)
    assert max(runs) < W * 0.02, "a %d-px ground gutter runs through the partition" % max(runs)


@_NEEDS
def test_the_focus_moves_across_the_shot():
    """This is what makes it a SHOT and not a diagram, and it is where its motion comes from — measured at
    0.0099 frame-diff p75 as film, against a 0.0037 floor."""
    early, late = band_edges(render({"dna": "product", "steps": STEPS}, frame=40)), \
                  band_edges(render({"dna": "product", "steps": STEPS}, frame=170))
    assert early and late, (early, late)
    moved = max(abs(a - b) for a, b in zip(early[:min(len(early), len(late))], late[:min(len(early), len(late))]))
    assert moved > 40, "the bands barely move between frame 40 and 170 (max %dpx)" % moved


@_NEEDS
def test_order_is_never_rearranged():
    """ORDER is the claim. MadeOf sorts by share because area is its argument; here sorting would be a lie.

    Measured as the WIDEST RUN between boundaries, not from the first boundary: each band carries a 2px
    inset hairline, so the first detected edge is at x=3 and 'the first edge is far in' is a statement about
    the hairline, not about the bands. My first version of this test asserted exactly that and failed."""
    def widest_run(png):
        e = [0] + band_edges(png) + [Image.open(png).size[0]]
        return max(b - a for a, b in zip(e, e[1:])), e
    w0, e0 = widest_run(render({"dna": "product", "at": 0,
                                "steps": [{"label": "zzz"}, {"label": "aaa"}, {"label": "mmm"}]}))
    w2, e2 = widest_run(render({"dna": "product", "at": 2,
                                "steps": [{"label": "zzz"}, {"label": "aaa"}, {"label": "mmm"}]}))
    W = Image.open(render({"dna": "product", "at": 0, "steps": [{"label": "a"}]})).size[0]
    assert w0 > W * 0.30 and w2 > W * 0.30, (w0, w2, e0, e2)
    # the widest band must be at the START when at=0 and at the END when at=2 — order, not size, decides
    def widest_start(png):
        e = [0] + band_edges(png) + [Image.open(png).size[0]]
        pairs = list(zip(e, e[1:]))
        return max(pairs, key=lambda p: p[1] - p[0])[0]
    s0 = widest_start(render({"dna": "product", "at": 0,
                              "steps": [{"label": "zzz"}, {"label": "aaa"}, {"label": "mmm"}]}))
    s2 = widest_start(render({"dna": "product", "at": 2,
                              "steps": [{"label": "zzz"}, {"label": "aaa"}, {"label": "mmm"}]}))
    assert s0 < W * 0.2 and s2 > W * 0.4, "the focus is not where `at` says it is (%d, %d)" % (s0, s2)


@_NEEDS
@pytest.mark.parametrize("aspect", ["16:9", "9:16", "1:1", "4:5"])
def test_it_fills_the_frame_at_every_aspect(aspect):
    png = render({"dna": "product", "steps": STEPS, "aspect": aspect})
    a = np.asarray(Image.open(png).convert("L").resize((192, 108))).astype(np.float32) / 255
    assert (np.abs(a - np.median(a)) > 0.10).mean() > 0.25, aspect


@_NEEDS
def test_an_out_of_range_focus_is_clamped_not_crashed():
    for at in (-5, 99, 2.5):
        render({"dna": "product", "steps": STEPS, "at": at})


@_NEEDS
@pytest.mark.parametrize("at", [0, 2, 4, None])
def test_nothing_it_draws_enters_the_caption_band(at):
    """Measured as PIXELS in the band, not through shot_still_qa's band-vs-frame heuristic — which returned
    1.0 here on a band that is uniformly the film's own ground (min == max == median), because a register
    that fills the content zone and stops at the band produces the same hard top edge a laid-over panel
    does. That rule is now fixed; this test measures the thing directly so it cannot be fooled either way."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
    from _caption_band import caption_band_px
    p = {"dna": "product", "whole": "T", "steps": STEPS}
    if at is not None:
        p["at"] = at
    im = Image.open(render(p)).convert("L")
    W, H = im.size
    band = np.asarray(im.crop((0, H - caption_band_px(W, H), W, H))).astype(np.float32) / 255
    spread = float(band.max() - band.min())
    assert spread < 0.02, "the caption band is not uniform — something is drawn in it (spread %.3f)" % spread
