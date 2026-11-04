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
    board["meta"]["renderer"] = "local"
    board["slides"][0]["image"] = "frames/01.png"
    r = validate.evaluate(board, film)
    assert any("remotion-tier plate" in e for e in r["errors"])


# ── the build: key, budget, run, encode, boxes, plates.ts ─────────────────────────────────────────────────────
import shutil  # noqa: E402
import subprocess  # noqa: E402

from PIL import Image  # noqa: E402


def _spec(film):
    return bp.spec_of(json.load(open(film + "/storyboard.json"))["slides"][0], film)


def test_key_moves_with_each_input(tmp_path, monkeypatch):
    film = make_film(tmp_path, dict(GOOD, cues=["广播"]))
    kit = tmp_path / "skill"
    (kit / "blender").mkdir(parents=True)
    (kit / "blender" / "runner.py").write_text("a")
    monkeypatch.setattr(bp, "SKILL_ROOT", str(kit))
    monkeypatch.setattr(bp, "KIT_DIR", str(kit / "blender"))
    spec = _spec(film)
    base = dict(spec=spec, out_dir=film, frames=169, fps=30, w=1920, h=1080, cue_t={"广播": 2.32}, blender_version="5.2.4")
    keys = {bp.plate_key(**base)}
    keys.add(bp.plate_key(**dict(base, frames=170)))
    keys.add(bp.plate_key(**dict(base, cue_t={"广播": 2.4})))
    keys.add(bp.plate_key(**dict(base, spec=dict(spec, engine="cycles"))))
    keys.add(bp.plate_key(**dict(base, blender_version="5.3.0")))
    keys.add(bp.plate_key(**dict(base, w=1080, h=1920)))
    (kit / "blender" / "runner.py").write_text("b")
    keys.add(bp.plate_key(**base))
    open(film + "/blender/s.py", "a").write("# edited\n")
    keys.add(bp.plate_key(**base))
    assert len(keys) == 8


def _ids_png(path, size, block=None, colour=(255, 0, 0), stray=None):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    if block:
        x0, y0, x1, y1 = block
        for x in range(x0, x1):
            for y in range(y0, y1):
                im.putpixel((x, y), (*colour, 255))
    if stray:
        im.putpixel(stray[0], stray[1])
    im.save(path)


def test_boxes_from_ids(tmp_path):
    d = tmp_path / "ids"
    d.mkdir()
    _ids_png(d / "0001.png", (8, 8), block=(1, 1, 3, 3), stray=((3, 3), (254, 1, 0, 255)))   # a near-red edge pixel
    _ids_png(d / "0002.png", (8, 8))
    b = bp.boxes_from_ids(str(d), {"sat": "#ff0000"}, 2, scale=2)
    assert b["sat"][0] == [2, 2, 8, 8] and b["sat"][1] is None


def test_boxes_null_when_absent(tmp_path):
    d = tmp_path / "ids"
    d.mkdir()
    _ids_png(d / "0001.png", (8, 8), block=(0, 0, 2, 2), colour=(0, 0, 0))                  # an unnamed (black) object
    assert bp.boxes_from_ids(str(d), {"sat": "#ff0000"}, 1)["sat"] == [None]


def test_boxes_refuse_a_missing_frame(tmp_path):
    d = tmp_path / "ids"
    d.mkdir()
    with pytest.raises(bp.PlateError, match="0001"):
        bp.boxes_from_ids(str(d), {"sat": "#ff0000"}, 1)


def _facts(monkeypatch, frames=4, w=32, h=18):
    monkeypatch.setattr(bp, "_frame_facts", lambda out_dir, board, i: (frames, 30, w, h))
    monkeypatch.setattr(bp, "_blender_version_str", lambda meta: "5.2.4")
    monkeypatch.setattr(bp, "require_blender", lambda meta=None: "/fake/Blender")


def _fake_runner(objects=("sat",)):
    """Stands in for Blender: writes what runner.py writes, for the arguments it was given."""
    def run(cmd, log):
        a = cmd[cmd.index("--") + 1:]
        opt = {a[i]: a[i + 1] for i in range(0, len(a) - 1, 2) if a[i].startswith("--")}
        out, n, w, h = opt["--out"], int(opt["--frames"]), int(opt["--w"]), int(opt["--h"])
        os.makedirs(out + "/rgba", exist_ok=True)
        os.makedirs(out + "/ids", exist_ok=True)
        for f in range(1, n + 1):
            im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            im.paste((200, 160, 60, 255), (4, 4, 12, 12))
            im.save(out + "/rgba/%04d.png" % f)
            _ids_png(out + "/ids/%04d.png" % f, (w // 2, h // 2), block=(2, 2, 6, 6))
        json.dump({"w": w, "h": h, "fps": 30, "frames": n, "anchors": {}}, open(out + "/anchors.json", "w"))
        json.dump({"frames": [{}] * n}, open(out + "/camera.json", "w"))
        json.dump({"blender": "5.2.4", "ids": {o: "#ff0000" for o in objects}, "rendered": n, "seconds": 1.0},
                  open(out + "/run.json", "w"))
        return 0
    return run


def test_build_writes_the_contract(tmp_path, monkeypatch):
    film = make_film(tmp_path, dict(GOOD, objects=["sat"]))
    _facts(monkeypatch)
    monkeypatch.setattr(bp, "_run_blender", _fake_runner())
    rep = bp.build(film)
    assert rep[0]["id"] == "sat" and rep[0]["state"] == "built"
    pd = bp.plate_dir(film, "sat")
    assert sorted(f for f in os.listdir(pd) if not f.startswith(".")) == \
        ["anchors.json", "boxes.json", "camera.json", "plate.json", "plate.webm"]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", pd + "/plate.webm"], capture_output=True, text=True).stdout
    assert "alpha_mode=1" in probe.lower().replace("tag:", "")
    assert json.load(open(pd + "/boxes.json"))["sat"][0] == [4, 4, 12, 12]
    board = json.load(open(film + "/storyboard.json"))
    assert bp.plate_state(film, board, 0) == "fresh"
    assert bp.build(film)[0]["state"] == "fresh"                 # nothing changed: nothing rebuilt


def test_partial_of_old_key_discarded(tmp_path, monkeypatch):
    film = make_film(tmp_path, GOOD)
    _facts(monkeypatch)
    monkeypatch.setattr(bp, "_run_blender", _fake_runner(objects=()))
    old = os.path.join(bp.plate_dir(film, "sat"), ".work-deadbeef0000", "rgba")
    os.makedirs(old)
    open(old + "/0001.png", "wb").write(b"x")
    bp.build(film)
    assert not os.path.exists(os.path.dirname(old))


def test_runner_failure_is_a_build_failure(tmp_path, monkeypatch, capsys):
    film = make_film(tmp_path, GOOD)
    _facts(monkeypatch)
    monkeypatch.setattr(bp, "_run_blender", lambda cmd, log: (open(log, "w").write("Traceback: boom\n"), 1)[1])
    assert bp.main([film]) == 1
    assert "boom" in capsys.readouterr().out


def test_over_budget_exits_3(tmp_path, monkeypatch, capsys):
    film = make_film(tmp_path, GOOD)
    board = json.load(open(film + "/storyboard.json"))
    board["meta"]["blender_budget_min"] = 0.01
    json.dump(board, open(film + "/storyboard.json", "w"), ensure_ascii=False)
    _facts(monkeypatch, frames=169)
    monkeypatch.setattr(bp, "_run_blender", _fake_runner(objects=()))
    assert bp.main([film]) == 3
    out = capsys.readouterr().out
    assert "--yes" in out and "min" in out
    assert not os.path.exists(os.path.join(bp.plate_dir(film, "sat"), "plate.json"))


def test_no_blender_exits_2(tmp_path, monkeypatch):
    film = make_film(tmp_path, GOOD)
    monkeypatch.setattr(bp, "blender_bin", lambda meta=None: None)
    assert bp.main([film]) == 2


def test_estimate_uses_the_measured_rates():
    spec = {"engine": "eevee", "objects": ["a"]}
    assert bp.estimate_seconds(spec, 100) == pytest.approx(10 + 100 * (4.6 + 0.72))
    assert bp.estimate_seconds(dict(spec, engine="cycles", objects=[]), 100) == pytest.approx(10 + 100 * 16.0)


def test_plates_ts_names_its_files(tmp_path, monkeypatch):
    film = make_film(tmp_path, dict(GOOD, objects=["sat"]))
    _facts(monkeypatch)
    monkeypatch.setattr(bp, "_run_blender", _fake_runner())
    bp.build(film)
    import remotion_segments as rs
    ts = open(os.path.join(film, "workshop/assets/plates.ts"), encoding="utf-8").read()
    assert "import type {Plate} from '@runtime/blenderPlate';" in ts
    assert "media/blender/sat/plate.webm" in rs.code_named_files(os.path.realpath(film), ts)
