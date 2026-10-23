"""A seam's ground may only be painted while its leaving half is LEAVING.

`SeamGround` (Film.tsx) paints the film's ground under the leaving half of a seam that fades both halves (E15).
It was painted whenever the half was the EXITING one — and a TransitionSeries keeps every sequence inside its exit
presentation for the WHOLE of its length, at progress 0 until its seam begins. So a beat whose own exit was a whip,
a drift, a focus relay or a fadethrough carried an opaque full-frame ground under itself from its first frame, and
on that first frame it was still ARRIVING over the beat before: the ground covered that beat outright. Found by
looking at the seam probe: a paper-keyed beat cut to the next beat's near-black on the first frame of a plain
dissolve (frame mean 205 -> 9.7), on the base commit as much as after — the next beat's exit was the product DNA's
default whip. A product film's every unmarked seam is that whip, so every beat before one lost its last picture to
a flat ground on the first frame of the cut.
"""
import json
import os
import subprocess

import pytest

_REM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion")
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _mean(tmp_path, scenes, frame, name):
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    pf = str(tmp_path / (name + ".json"))
    json.dump({"scenes": scenes, "dna": "product", "captions": False, "camera": 0, "cameraBed": False},
              open(pf, "w", encoding="utf-8"))
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png, "--frame=%d" % frame, "--gl=angle",
                        "--timeout=150000", "--scale=0.25", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
    return float(np.asarray(Image.open(png).convert("L"), dtype=float).mean())


@needs_toolchain
@pytest.mark.parametrize("exit_seam", [None, {"type": "drift"}, {"type": "fadethrough"}])
def test_the_first_frame_of_a_cut_still_shows_the_beat_being_left(tmp_path, exit_seam):
    """A light beat, then a dark one entering by a plain dissolve whose OWN exit fades both halves (the product
    DNA's default whip when unmarked). The cut's first frame (progress 0) must still be the light beat."""
    scenes = [{"shot": "DeviceDemo", "durF": 60, "props": {"device": "phone"}, "key": "light"},
              {"shot": "DeviceDemo", "durF": 60, "props": {"device": "phone"}, "transitionIn": {"type": "dissolve"}},
              {"shot": "DeviceDemo", "durF": 60, "props": {"device": "phone"}}]
    if exit_seam:
        scenes[2]["transitionIn"] = exit_seam
    before = _mean(tmp_path, scenes, 47, "before")
    first = _mean(tmp_path, scenes, 48, "first")
    assert before > 150, "the probe's first beat is not light (%.1f) — it no longer tests anything" % before
    assert abs(first - before) < 2.0, (
        "the first frame of the cut dropped from %.1f to %.1f — the next beat's exit ground is covering the beat "
        "being left" % (before, first))
