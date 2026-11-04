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


def _hit(text, plate="sat", f=0, rect=(0, 0, 10, 10)):
    return [text, plate, f, list(rect)]


def test_judge_needs_two_frames():
    cov = lambda plate, f, rect: {"sat": 0.5}  # noqa: E731
    fr = {3: {"hits": [_hit("我在哪")], "texts": 1, "objects": 1}}
    assert plate_qa.judge(fr, lambda f: 0, [1], cov)["errors"] == []
    fr[6] = {"hits": [_hit("我在哪", f=3)], "texts": 1, "objects": 1}
    errs = plate_qa.judge(fr, lambda f: 0, [1], cov)["errors"]
    assert len(errs) == 1 and "我在哪" in errs[0] and "sat" in errs[0] and "50%" in errs[0]


def test_judge_warn_band():
    fr = {f: {"hits": [_hit("note", plate="e")], "texts": 1, "objects": 1} for f in (0, 3)}
    r = plate_qa.judge(fr, lambda f: 0, [1], lambda plate, f, rect: {"earth": 0.08})
    assert r["errors"] == [] and len(r["warns"]) == 1


def test_judge_ignores_a_graze():
    fr = {f: {"hits": [_hit("note")], "texts": 1, "objects": 1} for f in (0, 3)}
    assert plate_qa.judge(fr, lambda f: 0, [1], lambda plate, f, rect: {"earth": 0.02}) == {"errors": [], "warns": []}


def test_coverage_is_the_silhouette_not_the_box(tmp_path):
    """A round object's box has empty corners: type there is beside the object, not on it."""
    from PIL import Image, ImageDraw
    d = tmp_path / "ids"
    d.mkdir()
    im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((0, 0, 99, 99), fill=(0, 0, 255, 255))
    im.save(d / "0001.png")
    colors = {"earth": "#0000ff"}
    corner = plate_qa.mask_share(str(d), colors, 0, (0, 0, 12, 12), scale=1)      # inside the box, outside the disc
    middle = plate_qa.mask_share(str(d), colors, 0, (40, 40, 60, 60), scale=1)
    assert corner["earth"] < 0.05 and middle["earth"] > 0.95


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
    assert bp.main([film, "--yes", "--skip-layout"]) == 0     # a picture plate whatever its layout: plate_qa is what is tested
    return film


@needs_both
def test_overlap_caught_then_cleared(tmp_path):
    on = _film_with_label(tmp_path / "on", [880, 500])            # the cube fills the middle of the frame
    r = plate_qa.scan_film(on, every=3)
    assert r["errors"] and "LABEL TEXT" in r["errors"][0] and plate_qa.verdict(r)[1] == 1, r
    off = _film_with_label(tmp_path / "off", [40, 40])
    r = plate_qa.scan_film(off, every=3)
    assert plate_qa.verdict(r) == ("ok", 0), r


@needs_both
def test_type_of_another_beat_is_not_judged_against_a_plate(tmp_path):
    film = _film_with_label(tmp_path / "seam", [40, 40])
    b = json.load(open(film + "/storyboard.json"))
    two = dict(b["slides"][0], index=2, shot="Other", shot_props={"label": "NEXT BEAT", "at": [880, 500]})
    two.pop("blender")
    b["slides"].append(two)
    json.dump(b, open(film + "/storyboard.json", "w"), ensure_ascii=False)
    shutil.copyfile(film + "/audio/01.mp3", film + "/audio/02.mp3")
    shutil.copyfile(film + "/audio/01.words.json", film + "/audio/02.words.json")
    open(film + "/workshop/shots/Other.tsx", "w").write(
        "import React from 'react';\nimport {AbsoluteFill} from 'remotion';\nexport const DURATION = 18;\n"
        "export const GROUND = '#204060';\nexport const PROVENANCE = 'scientific';\n"
        "export const Other: React.FC<{label?: string; at?: number[]}> = ({label = '', at = [0, 0]}) => (\n"
        "  <AbsoluteFill style={{background: '#204060'}}><div style={{position: 'absolute', left: at[0], top: at[1], "
        "font: '700 40px sans-serif', color: '#fff'}}>{label}</div></AbsoluteFill>);\n")
    r = plate_qa.scan_film(film, every=1)
    assert plate_qa.verdict(r) == ("ok", 0), r


@needs_both
def test_layout_gate_renders_no_picture_until_the_layout_passes(tmp_path):
    # the expensive pass runs once: type over an object is found on the ID pass alone (exit 4, a LAYOUT plate, no
    # picture rendered), and a clean layout is recorded so the picture build that follows does not judge it again
    on = _film_with_label(tmp_path / "on", [880, 500])
    import shutil as _sh
    _sh.rmtree(bp.plate_dir(on, "sat"))
    assert bp.main([on, "--yes"]) == 4
    pj = json.load(open(os.path.join(bp.plate_dir(on, "sat"), "plate.json")))
    assert pj["layout"] is True and not os.path.exists(os.path.join(bp.plate_dir(on, "sat"), bp.LAYOUT_RECORD))
    off = _film_with_label(tmp_path / "off", [40, 40])
    _sh.rmtree(bp.plate_dir(off, "sat"))
    assert bp.main([off, "--yes"]) == 0
    pd = bp.plate_dir(off, "sat")
    assert json.load(open(os.path.join(pd, "plate.json")))["layout"] is False
    assert os.path.exists(os.path.join(pd, bp.LAYOUT_RECORD))
    board = json.load(open(off + "/storyboard.json"))
    assert bp.layout_passed(off, board, 0) and bp.plate_state(off, board, 0) == "fresh"
