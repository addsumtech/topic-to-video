"""scripts/blender_plate.py — a beat's Blender plate: where Blender is, the board contract, the keyed build.

A Blender plate is a 3D render a workshop shot draws under its own overlay (docs/superpowers/specs/
2026-11-04-blender-plates-design.md). These tests pin the host side; tests/test_blender_runner.py runs Blender."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import blender_plate as bp  # noqa: E402


def test_blender_bin_order(tmp_path, monkeypatch):
    fake = tmp_path / "Blender"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setenv("TTV_BLENDER", str(fake))
    assert bp.blender_bin({"blender": str(fake)}) == str(fake)
    assert bp.blender_bin({}) == str(fake)
    monkeypatch.setenv("TTV_BLENDER", str(tmp_path / "missing"))
    monkeypatch.setattr(bp, "_APP_PATHS", ())
    monkeypatch.setattr(bp.shutil, "which", lambda n: None)
    assert bp.blender_bin({}) is None


@pytest.mark.parametrize("line,want", [("Blender 5.2.4 LTS Release Candidate", (5, 2, 4, True)),
                                       ("Blender 5.0.1", (5, 0, 1, False))])
def test_version_parse(line, want, monkeypatch):
    monkeypatch.setattr(bp, "_version_line", lambda b: line)
    assert bp.blender_version("x") == want


def test_version_without_a_version_line_is_refused(monkeypatch):
    monkeypatch.setattr(bp, "_version_line", lambda b: "")
    with pytest.raises(bp.PlateError, match="version"):
        bp.blender_version("x")


def test_version_floor_refused(monkeypatch, tmp_path):
    fake = tmp_path / "Blender"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setattr(bp, "_version_line", lambda b: "Blender 4.2.0")
    with pytest.raises(bp.PlateError, match="5.0"):
        bp.require_blender({"blender": str(fake)})


def test_missing_blender_refused(monkeypatch):
    monkeypatch.setattr(bp, "blender_bin", lambda meta=None: None)
    with pytest.raises(bp.PlateError, match="not found"):
        bp.require_blender({})


def test_doctor_lists_blender():
    import doctor
    assert any(row[0] == "blender" and row[1] is False for row in doctor.CHECKS)


# ── the board contract ──────────────────────────────────────────────────────────────────────────────────────
import json  # noqa: E402

WORDS = [{"w": "卫星", "t": 0.1}, {"w": "也有", "t": 0.53}, {"w": "它", "t": 1.88}, {"w": "不停", "t": 2.02},
         {"w": "广播", "t": 2.32}, {"w": "我", "t": 3.04}, {"w": "在", "t": 3.16}, {"w": "哪", "t": 3.35}]


def make_film(root, blender=None, shot="PlateProbe"):
    """A one-beat film: a workshop shot, the beat's word times, a scene script under blender/."""
    out = root / "film"
    (out / "audio").mkdir(parents=True)
    (out / "blender").mkdir()
    (out / "workshop" / "shots").mkdir(parents=True)
    (out / "workshop" / "shots" / "PlateProbe.tsx").write_text("export const PlateProbe = () => null;\n")
    (out / "blender" / "s.py").write_text("def build(k):\n    return {}\n\ndef pose(k, t):\n    pass\n")
    (out / "audio" / "01.words.json").write_text(json.dumps(WORDS, ensure_ascii=False))
    slide = {"index": 1, "narration": "卫星也有它不停广播我在哪", "duration": 5.6, "audio": "audio/01.mp3", "shot": shot}
    if blender is not None:
        slide["blender"] = blender
    board = {"meta": {"renderer": "remotion"}, "slides": [slide]}
    (out / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False))
    return str(out)


GOOD = {"id": "sat", "scene": "blender/s.py", "why": "real-world"}


def test_spec_normalises_defaults(tmp_path):
    film = make_film(tmp_path, GOOD)
    s = bp.spec_of(json.load(open(film + "/storyboard.json"))["slides"][0], film)
    assert s == {"id": "sat", "scene": "blender/s.py", "why": "real-world", "mode": "rgba", "engine": "eevee",
                 "cues": [], "anchors": [], "objects": [], "assets": []}


def test_spec_absent_is_none(tmp_path):
    film = make_film(tmp_path)
    assert bp.spec_of(json.load(open(film + "/storyboard.json"))["slides"][0], film) is None


def test_spec_rejects_each_bad_field(tmp_path):
    film = make_film(tmp_path)
    s = {"blender": {"id": "Bad Id", "scene": "blender/none.py", "why": "pretty", "mode": "x", "engine": "octane",
                     "cues": [""]}, "shot": "PlateProbe"}
    with pytest.raises(bp.PlateError) as e:
        bp.spec_of(s, film)
    for word in ("id", "scene", "why", "mode", "engine", "cues"):
        assert word in str(e.value), word


def test_spec_needs_a_workshop_shot(tmp_path):
    film = make_film(tmp_path, GOOD, shot="KineticManifesto")
    with pytest.raises(bp.PlateError, match="workshop shot"):
        bp.spec_of(json.load(open(film + "/storyboard.json"))["slides"][0], film)


def test_scene_outside_blender_dir_is_refused(tmp_path):
    film = make_film(tmp_path, dict(GOOD, scene="../evil.py"))
    (tmp_path / "evil.py").write_text("")
    with pytest.raises(bp.PlateError, match="scene"):
        bp.spec_of(json.load(open(film + "/storyboard.json"))["slides"][0], film)


def test_asset_without_sidecar_is_refused(tmp_path):
    film = make_film(tmp_path, dict(GOOD, assets=["assets/earth.jpg"]))
    os.makedirs(film + "/assets")
    open(film + "/assets/earth.jpg", "wb").write(b"x")
    with pytest.raises(bp.PlateError, match="sidecar"):
        bp.spec_of(json.load(open(film + "/storyboard.json"))["slides"][0], film)
    json.dump({"license": "Public domain", "source": "https://example.org/e"}, open(film + "/assets/earth.jpg.json", "w"))
    assert bp.spec_of(json.load(open(film + "/storyboard.json"))["slides"][0], film)["assets"] == ["assets/earth.jpg"]


def test_cue_times_strict(tmp_path):
    film = make_film(tmp_path, GOOD)
    assert bp.cue_times(film, 1, ["广播", "我在哪"]) == {"广播": 2.32, "我在哪": 3.04}
    with pytest.raises(bp.PlateError, match="不存在的词"):
        bp.cue_times(film, 1, ["不存在的词"])


def test_duplicate_ids_are_refused(tmp_path):
    film = make_film(tmp_path, GOOD)
    board = json.load(open(film + "/storyboard.json"))
    board["slides"].append(dict(board["slides"][0], index=2))
    errs, _ = bp.validate_blender(board, film)
    assert any("twice" in e for e in errs)


def test_missing_plate_is_an_error(tmp_path):
    film = make_film(tmp_path, GOOD)
    errs, _ = bp.validate_blender(json.load(open(film + "/storyboard.json")), film)
    assert any("not built" in e for e in errs)


def test_stale_plate_after_retime_is_an_error(tmp_path, monkeypatch):
    film = make_film(tmp_path, GOOD)
    board = json.load(open(film + "/storyboard.json"))
    monkeypatch.setattr(bp, "_frame_facts", lambda out_dir, board, i: (round(board["slides"][i]["duration"] * 30), 30, 1920, 1080))
    monkeypatch.setattr(bp, "_blender_version_str", lambda meta: "5.2.4")
    os.makedirs(bp.plate_dir(film, "sat"))
    key = bp.current_key(film, board, 0)
    json.dump({"key": key}, open(os.path.join(bp.plate_dir(film, "sat"), "plate.json"), "w"))
    assert bp.plate_state(film, board, 0) == "fresh"
    board["slides"][0]["duration"] = 6.1
    assert bp.plate_state(film, board, 0) == "stale"
    errs, _ = bp.validate_blender(board, film)
    assert any("stale" in e for e in errs)


def test_validate_evaluate_carries_blender_errors(tmp_path):
    import validate
    film = make_film(tmp_path, dict(GOOD, why="pretty"))
    r = validate.evaluate(json.load(open(film + "/storyboard.json")), film)
    assert any("blender" in e for e in r["errors"])


def test_blender_on_a_non_remotion_film_is_refused(tmp_path):
    import validate
    film = make_film(tmp_path, GOOD)
    board = json.load(open(film + "/storyboard.json"))
    board["meta"]["renderer"] = "html"
    r = validate.evaluate(board, film)
    assert any("remotion-tier plate" in e for e in r["errors"])
