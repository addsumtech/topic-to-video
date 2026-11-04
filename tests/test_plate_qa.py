"""scripts/plate_qa.py — type must not sit on a Blender plate's object. The Film is rendered with the plate-clear
census armed (runtime/plateClear.tsx): per sampled frame, every line of the shot's own type against every plate
object's box on that frame. The first plate (a GPS satellite, 2026-11-04) put its wing tip under the label 我在哪,
and no gate could see it: the wing is pixels of a video, not DOM."""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import blender_plate as bp  # noqa: E402
import plate_qa  # noqa: E402
from test_blender_plate import GOOD, make_film  # noqa: E402


def test_judge_needs_two_frames():
    fr = {3: {"hits": [["我在哪", "sat", 400, 1000]], "texts": 1, "objects": 1}}
    assert plate_qa.judge(fr, lambda f: 0, [1])["errors"] == []
    fr[6] = {"hits": [["我在哪", "sat", 500, 1000]], "texts": 1, "objects": 1}
    errs = plate_qa.judge(fr, lambda f: 0, [1])["errors"]
    assert len(errs) == 1 and "我在哪" in errs[0] and "sat" in errs[0] and "50%" in errs[0]


def test_judge_warn_band():
    fr = {f: {"hits": [["note", "earth", 80, 1000]], "texts": 1, "objects": 1} for f in (0, 3)}
    r = plate_qa.judge(fr, lambda f: 0, [1])
    assert r["errors"] == [] and len(r["warns"]) == 1


def test_judge_ignores_a_graze():
    fr = {f: {"hits": [["note", "earth", 20, 1000]], "texts": 1, "objects": 1} for f in (0, 3)}
    assert plate_qa.judge(fr, lambda f: 0, [1]) == {"errors": [], "warns": []}


def test_verdicts():
    base = {"errors": [], "warns": [], "unmeasured": [], "objects": 3}
    assert plate_qa.verdict(dict(base, errors=["x"])) == ("FAIL", 1)
    assert plate_qa.verdict(dict(base, unmeasured=["lost frames"])) == ("UNMEASURED", 2)
    assert plate_qa.verdict(dict(base, objects=0)) == ("NOTHING TO JUDGE", 0)
    assert plate_qa.verdict(base) == ("ok", 0)


def test_gate_listed_only_with_blender_beats(tmp_path):
    import critic_ledger
    with_b = make_film(tmp_path / "a", GOOD)
    without = make_film(tmp_path / "b")
    names = lambda d: [g[1] for g in critic_ledger.delivery_gates(d)]  # noqa: E731
    assert "plate_qa.py" in names(with_b) and "plate_qa.py" not in names(without)


REMOTION_OK = os.path.isdir(os.path.join(ROOT, "remotion", "node_modules"))
needs_both = pytest.mark.skipif(bp.blender_bin() is None or not REMOTION_OK, reason="needs Blender and remotion/")


def _film_with_label(tmp_path, at):
    film = make_film(tmp_path, dict(GOOD, anchors=["top"], objects=["cube"]))
    shutil.copyfile(os.path.join(ROOT, "tests/fixtures/blender/cube_scene.py"), film + "/blender/s.py")
    shutil.copyfile(os.path.join(ROOT, "tests/fixtures/blender_film/PlateProbe.tsx"), film + "/workshop/shots/PlateProbe.tsx")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "0.6",
                    film + "/audio/01.mp3"], check=True)
    b = json.load(open(film + "/storyboard.json"))
    b["slides"][0].update(duration=0.6, shot_props={"label": "LABEL TEXT", "at": at})
    json.dump(b, open(film + "/storyboard.json", "w"), ensure_ascii=False)
    assert bp.main([film, "--yes"]) == 0
    return film


@needs_both
def test_overlap_caught_then_cleared(tmp_path):
    on = _film_with_label(tmp_path / "on", [880, 500])            # the cube fills the middle of the frame
    r = plate_qa.scan_film(on, every=3)
    assert r["errors"] and "LABEL TEXT" in r["errors"][0] and plate_qa.verdict(r)[1] == 1, r
    off = _film_with_label(tmp_path / "off", [40, 40])
    r = plate_qa.scan_film(off, every=3)
    assert plate_qa.verdict(r) == ("ok", 0), r
