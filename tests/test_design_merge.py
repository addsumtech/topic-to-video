"""design_merge: parallel builders never write the board; their parts are merged here, and a conflict writes nothing."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import design_merge as dm  # noqa: E402

import pytest  # noqa: E402


def _film(tmp_path, n=4):
    out = tmp_path / "film"
    (out / "workshop" / "shots").mkdir(parents=True)
    (out / dm.PARTS).mkdir()
    slides = [{"narration": "n%d" % i, "shot_fit": {"ideal": "ideal %d" % i, "form": "f", "composition": "wide"}}
              for i in range(1, n + 1)]
    board = {"meta": {"build_list": [{"id": "Kit0", "kind": "object"}]}, "slides": slides}
    (out / "storyboard.json").write_text(json.dumps(board), encoding="utf-8")
    return out


def _part(out, name, shots, beats, build=None):
    for s in shots:
        (out / "workshop" / "shots" / (s + ".tsx")).write_text("export const %s = () => null;\n" % s)
    (out / dm.PARTS / (name + ".json")).write_text(json.dumps(
        {"builder": name, "shots": shots, "beats": beats,
         "build_list": build if build is not None else [{"id": s, "kind": "shot", "means": "m", "accept": "a"}
                                                        for s in shots]}), encoding="utf-8")


def test_two_clean_parts_merge_and_the_leads_fit_is_kept(tmp_path):
    out = _film(tmp_path)
    _part(out, "b1", ["Alpha"], {"1": {"shot": "Alpha", "shot_props": {"t": 1},
                                       "shot_fit": {"verdict": "build", "ideal": "builder rewrote it"}}})
    _part(out, "b2", ["Beta"], {"3": {"shot": "Beta", "shot_props": {"t": 3}}, "4": {"shot": "Beta", "shot_props": {}}})
    dm.merge(str(out), log=lambda *a: None)
    b = json.load(open(out / "storyboard.json"))
    assert b["slides"][0]["shot"] == "Alpha" and b["slides"][0]["shot_props"] == {"t": 1}
    assert b["slides"][0]["shot_fit"]["ideal"] == "ideal 1", "the lead's ideal is not the builder's to rewrite"
    assert b["slides"][0]["shot_fit"]["verdict"] == "build"
    assert [s.get("shot") for s in b["slides"]] == ["Alpha", None, "Beta", "Beta"]
    assert b["slides"][1]["narration"] == "n2"
    assert [e["id"] for e in b["meta"]["build_list"]] == ["Kit0", "Alpha", "Beta"]
    assert (out / "storyboard.premerge.json").exists()


@pytest.mark.parametrize("case", ["same_beat", "same_shot", "foreign_shot", "missing_file", "off_board", "foreign_build"])
def test_a_conflict_writes_nothing(tmp_path, case):
    out = _film(tmp_path)
    before = (out / "storyboard.json").read_text(encoding="utf-8")
    _part(out, "b1", ["Alpha"], {"1": {"shot": "Alpha"}})
    if case == "same_beat":
        _part(out, "b2", ["Beta"], {"1": {"shot": "Beta"}})
    elif case == "same_shot":
        _part(out, "b2", ["Alpha"], {"2": {"shot": "Alpha"}})
    elif case == "foreign_shot":
        _part(out, "b2", ["Beta"], {"2": {"shot": "Alpha"}})
    elif case == "missing_file":
        _part(out, "b2", ["Beta"], {"2": {"shot": "Beta"}})
        os.remove(out / "workshop" / "shots" / "Beta.tsx")
    elif case == "off_board":
        _part(out, "b2", ["Beta"], {"9": {"shot": "Beta"}})
    elif case == "foreign_build":
        _part(out, "b2", ["Beta"], {"2": {"shot": "Beta"}}, build=[{"id": "Alpha", "kind": "shot"}])
    with pytest.raises(dm.MergeError):
        dm.merge(str(out), log=lambda *a: None)
    assert (out / "storyboard.json").read_text(encoding="utf-8") == before
    assert not (out / "storyboard.premerge.json").exists()


def test_a_library_register_on_a_builders_beat_is_allowed(tmp_path):
    out = _film(tmp_path)
    _part(out, "b1", ["Alpha"], {"1": {"shot": "Alpha"}, "2": {"shot": "CardFlip3D", "shot_props": {}}})
    dm.merge(str(out), log=lambda *a: None)
    assert json.load(open(out / "storyboard.json"))["slides"][1]["shot"] == "CardFlip3D"
