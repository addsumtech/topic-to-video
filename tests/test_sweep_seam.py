"""SWEEP — the hidden cut: a panel passes the lens and the scene changes behind it (seams.tsx).

WHY. The peer library's transition-hidden-cut (an oversized card sweeps past the lens with heavy motion blur, the
background swapping scenes inside the fully covered frames) claims a relation this tier's 20 seam words could not:
CONTINUITY OF MOTION — the camera never stopped, the world went past it. What is held: the word resolves on the
board, the panel covers the WHOLE frame on the frame the picture changes, sfx times its whoosh there, and a rendered
seam really is covered at its middle and shows each beat on its own side.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import render_remotion as rr  # noqa: E402
import sfx  # noqa: E402
import _tsprobe as tp  # noqa: E402

_REM = os.path.join(_ROOT, "remotion")


def test_the_board_names_the_sweep_and_its_sound_lands_on_the_swap():
    assert rr.seam_type("sweep") == "sweep" and rr.seam_type("hidden-cut") == "sweep"
    assert rr.is_mark({"transition_in": {"type": "sweep"}})
    assert sfx.SEAM_PEAK["sweep"] == pytest.approx(0.5)
    assert sfx.SEAM_CUE["sweep"][0] == "whoosh"
    cues = sfx.plan_cues([{"durationInFrames": 120, "transitionIn": None},
                          {"durationInFrames": 120, "transitionIn": {"type": "sweep"}}], 30, seam_frames=12)
    wh = [c for c in cues if c[1] == "whoosh"]
    assert wh and abs(wh[0][0] - (4.0 + 6 / 30)) < 2 / 30 + 1e-6, cues        # the swap: seam start (4 s) + 6 frames


@pytest.mark.skipif(not tp.available(), reason="needs node + remotion/node_modules")
def test_the_panel_covers_the_whole_frame_on_the_frame_the_picture_changes():
    out = tp.run_ts("import {sweepCovers, CUT_AT} from %s;" % json.dumps(os.path.join(_REM, "src", "seams.tsx")),
                    "out.at = sweepCovers(CUT_AT); out.frames = Array.from({length: 13}, (_, i) => sweepCovers(i / 12));"
                    "out.start = sweepCovers(0); out.end = sweepCovers(1);")
    assert out["at"], "the swap must be under the panel"
    assert not out["start"] and not out["end"], "the panel enters and leaves: the seam's ends are the beats"
    assert sum(out["frames"]) >= 2, "covered for at least two of the twelve frames"


@pytest.mark.skipif(not (os.path.isdir(os.path.join(_REM, "node_modules")) and shutil.which("npx")),
                    reason="needs the remotion toolchain")
def test_a_rendered_sweep_is_covered_at_its_middle_and_never_brighter_than_both_beats(tmp_path):
    scenes = [{"shot": "EdStat", "props": {"value": "42", "label": "first"}, "durF": 60, "ground": "#101820"},
              {"shot": "EdStat", "props": {"value": "7", "label": "second"}, "durF": 60, "ground": "#2a3440",
               "transitionIn": {"type": "sweep"}}]
    props = tmp_path / "p.json"
    props.write_text(json.dumps({"scenes": scenes, "dna": "product", "captions": False, "camera": 0,
                                 "cameraBed": False}), encoding="utf-8")
    means, stds = {}, {}
    for f in (40, 54, 70):                       # beat 1, the seam's middle (48 + 6), beat 2
        png = tmp_path / ("f%d.png" % f)
        subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", str(png), "--frame=%d" % f,
                        "--props=%s" % props, "--gl=angle", "--log=error"], cwd=_REM, check=True)
        a = np.asarray(Image.open(png).convert("L"), dtype=float)
        means[f], stds[f] = a.mean(), a.std()
    assert stds[54] < 6, "mid-seam the frame is one panel, no beat showing through (std %.1f)" % stds[54]
    assert means[54] <= max(means[40], means[70]) + 12, "the panel is never a flash brighter than both beats"
