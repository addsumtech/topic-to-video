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


def _film_with_label(tmp_path, at, scene="cube_scene.py", seconds=0.6, aspect=None):
    film = make_film(tmp_path, dict(GOOD, anchors=["top"], objects=["cube"]))
    shutil.copyfile(os.path.join(ROOT, "tests/fixtures/blender", scene), film + "/blender/s.py")
    shutil.copyfile(os.path.join(ROOT, "tests/fixtures/blender_film/PlateProbe.tsx"), film + "/workshop/shots/PlateProbe.tsx")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", str(seconds),
                    film + "/audio/01.mp3"], check=True)
    b = json.load(open(film + "/storyboard.json"))
    b["slides"][0].update(duration=seconds, shot_props={"label": "LABEL TEXT", "at": at})
    if aspect:
        b["meta"]["aspect"] = aspect
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


def test_coverage_uses_no_deprecated_pillow_call(tmp_path):
    # Image.getdata is gone in Pillow 14 (2027-10-15); the gate must keep working past it
    import warnings
    from PIL import Image
    d = tmp_path / "ids"
    d.mkdir()
    Image.new("RGBA", (8, 8), (0, 0, 255, 255)).save(d / "0001.png")
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert plate_qa.mask_share(str(d), {"earth": "#0000ff"}, 0, (0, 0, 8, 8), scale=1) == {"earth": 1.0}


def test_the_census_is_of_the_film_as_it_will_play_warps_included(tmp_path, monkeypatch):
    # the layout gate runs BEFORE the render, when a beat's warp is not derived yet: judged on the registers' own
    # clocks, the type sits where it never will in the film (render_remotion derives the warps first; so must this)
    import render_remotion as rr
    import remotion_segments as rs
    import sync_qa as sq
    import text_safe_qa as ts
    import workshop as ws
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {}, "slides": []}))
    monkeypatch.setattr(rr, "film_props", lambda out, board: ({"scenes": [{"shot": "S", "durF": 30}]}, []))

    def derive(out, board, props, slides, log=print):
        props["scenes"] = [dict(props["scenes"][0], warp=[[0, 0], [10, 6], [30, 30]])]
    monkeypatch.setattr(sq, "derive_warps", derive)
    monkeypatch.setattr(ws, "prepare", lambda out: {})
    monkeypatch.setattr(rs, "minimal_public", lambda props, out, dest: dest)
    monkeypatch.setattr(ts, "glide_bundle", lambda *a, **k: "bundle")
    seen = []
    monkeypatch.setattr(ts, "glide_run", lambda jobs, *a, **k: (seen.append(jobs[0]["props"]), {"film": {}})[1])
    monkeypatch.delenv("REMOTION_SYNC", raising=False)
    plate_qa.census_film(str(tmp_path))
    assert seen[0]["scenes"][0].get("warp") == [[0, 0], [10, 6], [30, 30]], seen


def test_a_caption_on_an_object_is_one_finding_that_moves_the_object():
    # the caption is the film's and its place is fixed: its karaoke text changes every frame, so it is judged as ONE
    # line per beat and object, and the fix it names is the object's
    frames = {f: {"hits": [["慢 7.2；净快约"[: 2 + f], "sat", f, [0, 0, 10, 10], 1]]} for f in range(0, 9, 3)}
    out = plate_qa.judge(frames, lambda f: 0, [2], lambda pid, pf, rect: {"earth": 0.4})
    assert len(out["errors"]) == 1 and "caption" in out["errors"][0] and "move the object" in out["errors"][0], out


@needs_both
def test_a_plate_object_under_the_caption_is_caught(tmp_path):
    # GPS beat 2 (2026-11-04): the Earth's limb ran under the caption with every gate green — the census had the
    # captions off, and the caption is not any beat's own type
    # 1.5 s: the Film shows a caption from frame 14 to 16 frames before the end, so a shorter beat has none
    film = _film_with_label(tmp_path / "low", [40, 40], scene="low_cube_scene.py", seconds=1.5)
    r = plate_qa.scan_film(film, every=3)
    assert plate_qa.verdict(r)[1] == 1 and any("caption" in e for e in r["errors"]), r


def test_an_object_over_one_glyph_of_a_long_line_is_on_it(tmp_path):
    # a share of the WHOLE line's box dilutes with its length: GPS beat 2's satellite wing over 走快, the last two glyphs
    # of a 13-glyph title, measured under 5% and passed. Judged over the worst glyph-sized window, it is on the type.
    from PIL import Image, ImageDraw
    d = tmp_path / "ids"
    d.mkdir()
    im = Image.new("RGBA", (400, 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle((380, 10, 399, 29), fill=(0, 0, 255, 255))      # one glyph's square at the end
    im.save(d / "0001.png")
    share = plate_qa.mask_share(str(d), {"sat": "#0000ff"}, 0, (0, 10, 400, 30), scale=1)["sat"]
    assert share >= plate_qa.ERROR_SHARE, share


@needs_both
def test_on_a_9_16_film_the_caption_is_judged_against_the_plate_as_drawn(tmp_path):
    # a 9:16 film mounts each register twice: full-frame in the margin echo (only its ground shows) and scaled in its
    # frame. The caption was judged against the ECHO's plate, so the glass film's caption 'sat 100% over' a glass drawn
    # well above it (2026-11-05). Here the echo's cube is under the caption and the drawn one is clear of it.
    film = _film_with_label(tmp_path / "tall", [40, 40], scene="echo_cube_scene.py", seconds=1.5, aspect="9:16")
    r = plate_qa.scan_film(film, every=3)
    assert plate_qa.verdict(r) == ("ok", 0), r
