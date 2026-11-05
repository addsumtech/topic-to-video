"""runtime/blenderPlate under a workshop shot, rendered by Remotion: the plate's alpha shows the shot's own ground,
and its anchors land where Blender projected them, at the film's own frame size."""
import json
import os
import shutil
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import blender_plate as bp  # noqa: E402
from test_blender_plate import GOOD, make_film  # noqa: E402

REMOTION_OK = os.path.isdir(os.path.join(ROOT, "remotion", "node_modules"))
needs_both = pytest.mark.skipif(bp.blender_bin() is None or not REMOTION_OK, reason="needs Blender and remotion/")
GROUND = (0x20, 0x40, 0x60)


def make_plate_film(tmp_path, monkeypatch, w, h, aspect=None):
    film = make_film(tmp_path, dict(GOOD, anchors=["top"], objects=["cube"]))
    shutil.copyfile(os.path.join(ROOT, "tests/fixtures/blender/cube_scene.py"), film + "/blender/s.py")
    shutil.copyfile(os.path.join(ROOT, "tests/fixtures/blender_film/PlateProbe.tsx"), film + "/workshop/shots/PlateProbe.tsx")
    if aspect:
        b = json.load(open(film + "/storyboard.json"))
        b["meta"]["aspect"] = aspect
        json.dump(b, open(film + "/storyboard.json", "w"), ensure_ascii=False)
    monkeypatch.setattr(bp, "_frame_facts", lambda out_dir, board, i: (4, 30, w, h))
    assert bp.build(film)[0]["state"] == "built"
    return film


def near(a, b, tol=24):
    return all(abs(x - y) <= tol for x, y in zip(a[:3], b[:3]))


def still(film, frame, props=None, aspect=None):
    import workshop
    return Image.open(workshop.still(film, "PlateProbe", props or {}, frame=frame, aspect=aspect)).convert("RGB")


def anchor(film, f):
    return json.load(open(os.path.join(bp.plate_dir(film, "sat"), "anchors.json")))["anchors"]["top"][f]


@needs_both
def test_plate_composites_over_the_ground(tmp_path, monkeypatch):
    film = make_plate_film(tmp_path, monkeypatch, 480, 270)
    im = still(film, 2)
    W, H = im.size
    assert near(im.getpixel((8, 8)), GROUND)                          # the plate's transparent corner shows the ground
    assert not near(im.getpixel((W // 2, H // 2)), GROUND)            # the cube is drawn over it
    x, y = anchor(film, 2)[:2]
    k = W / 480
    assert near(im.getpixel((round(x * k), round(y * k))), (255, 0, 255), tol=40)


@needs_both
def test_plate_scales_to_frame(tmp_path, monkeypatch):
    film = make_plate_film(tmp_path, monkeypatch, 270, 480, aspect="9:16")
    im = still(film, 1, aspect="9:16")
    W, H = im.size
    assert H > W
    x, y = anchor(film, 1)[:2]
    k = W / 270
    assert near(im.getpixel((round(x * k), round(y * k))), (255, 0, 255), tol=40)


import _tsprobe  # noqa: E402


@pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")
def test_plate_frame_is_whole_and_clamped():
    # a warped or timed beat clock hands its register FRACTIONS of a frame (Film BeatClock -> Freeze): indexing the
    # plate's per-frame anchors with 3.4 read `undefined` and crashed the glass film's full render, 2026-11-04
    out = _tsprobe.run_ts("import {plateFrame} from %s;" % _tsprobe.mod("blenderPlate"),
                          "out.v = [plateFrame(3.4, 10), plateFrame(3.6, 10), plateFrame(-2, 10), plateFrame(99, 10)];\n"
                          "try { plateFrame(NaN, 10); out.nan = 'no error'; } catch (e) { out.nan = String(e); }")
    assert out["v"] == [3, 4, 0, 9]
    assert "frame" in out["nan"] and out["nan"] != "no error"


@needs_both
def test_plate_keeps_the_voice_clock_under_a_warp(tmp_path, monkeypatch):
    # the warp re-times a REGISTER's entrances onto its voice; a plate's motion is on the voice already (its cues are
    # baked from the word times), so the plate shows beat frame f on film frame f, and nothing crashes on a fraction
    import plate_qa
    import render_remotion as rr
    from test_plate_qa import _film_with_label
    film = _film_with_label(tmp_path, [880, 500])
    real = rr.film_props

    def warped(out_dir, board):
        props, slides = real(out_dir, board)
        props["scenes"][0]["warp"] = [[0, 0], [9, 5.5], [17, 17]]
        return props, slides
    monkeypatch.setattr(rr, "film_props", warped)
    res, segs, slides, total = plate_qa.census_film(film, every=1)
    n = json.load(open(os.path.join(bp.plate_dir(film, "sat"), "plate.json")))["frames"]
    seen = {int(f): {h[2] for h in r.get("hits") or []} for f, r in (res.get("frames") or {}).items()}
    assert len(seen) == total, res
    hit = {f: s for f, s in seen.items() if s}
    assert hit and all(s == {min(f, n - 1)} for f, s in hit.items()), hit


@pytest.mark.skipif(not REMOTION_OK, reason="needs remotion/ (tsc)")
def test_the_generated_plates_index_type_checks(tmp_path):
    # the anc film, 2026-11-05: write_plates_ts writes each anchor as [x, y, depth, visible] with visible a JSON
    # boolean, while Plate typed anchors number[][] — 2220 tsc errors on a three-plate film, every one a
    # validate ERROR, the shots themselves fine
    import workshop
    film = make_film(tmp_path, dict(GOOD, anchors=["top"], objects=["cube"]))
    shutil.copyfile(os.path.join(ROOT, "tests/fixtures/blender_film/PlateProbe.tsx"), film + "/workshop/shots/PlateProbe.tsx")
    pd = bp.plate_dir(film, "sat")
    os.makedirs(pd, exist_ok=True)
    json.dump({"w": 64, "h": 36, "fps": 30, "frames": 2, "mode": "rgba"}, open(os.path.join(pd, "plate.json"), "w"))
    json.dump({"anchors": {"top": [[1.5, 2.5, 3.0, True], [1.5, 2.5, 3.0, False]]}}, open(os.path.join(pd, "anchors.json"), "w"))
    json.dump({"cube": [[0, 0, 4, 4], None]}, open(os.path.join(pd, "boxes.json"), "w"))
    bp.write_plates_ts(film)
    assert "true" in open(film + "/workshop/assets/plates.ts").read()
    workshop.write_index(film)
    probs = workshop.typecheck(film)
    assert not [p for p in probs if "plates.ts" in p], probs
