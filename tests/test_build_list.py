"""validate.py knows what a film built: the build list and the workshop agree both ways, every reference names
something that exists, and the stage registers' own previews never reach a film."""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate as v  # noqa: E402
import workshop as ws  # noqa: E402
from test_workshop_bundle import SHOT, OBJECT  # noqa: E402

REQUIRING = SHOT.replace("export const DURATION = 30;", "export const DURATION = 30;\n"
                                                        "export const REQUIRED_IN_FILM = ['object'] as const;")


@pytest.fixture(autouse=True)
def _workshop_code_check_is_stubbed(monkeypatch):
    """The workshop's own code check has its tests in tests/test_workshop.py; stubbed here so these judge the
    board. `test_the_workshop_code_check_reaches_validate` runs the wiring for real."""
    monkeypatch.setattr(ws, "check", lambda out_dir: [])


def _entry(eid, kind="object", **kw):
    e = {"id": eid, "kind": kind, "means": "what a viewer must see", "slot": "WsShotA" if kind == "object" else "own",
         "accept": "caption hidden, the viewer still sees it"}
    e.update(kw)
    return e


def _board(tmp_path, slides, build_list=None, shots=("WsShotA",), objects=("WsDisc",), meta=None,
           shot_src=SHOT, obj_src=OBJECT):
    for kind, names, src in (("shots", shots, shot_src), ("objects", objects, obj_src)):
        d = tmp_path / "workshop" / kind
        for n in names:
            d.mkdir(parents=True, exist_ok=True)
            (d / (n + ".tsx")).write_text(src % {"name": n}, encoding="utf-8")
    (tmp_path / "audio").mkdir(exist_ok=True)
    for i, s in enumerate(slides, 1):
        (tmp_path / "audio" / ("%02d.mp3" % i)).write_bytes(b"\0")
        s.setdefault("index", i)
        s.setdefault("narration", "这一拍说的事。")
        s.setdefault("audio", "audio/%02d.mp3" % i)
        s.setdefault("duration", 3.0)
    m = {"renderer": "remotion", "design_dna": "product", "language": "zh", "captions": False}
    m.update(meta or {})
    if build_list is not None:
        m["build_list"] = build_list
    return {"meta": m, "slides": slides}


def _errs(board, tmp_path):
    return v.evaluate(board, str(tmp_path))["errors"]


def _holding(obj="WsDisc", **fit):
    s = {"shot": "WsShotA", "shot_props": {"object": {"id": obj}}}
    if fit:
        s["shot_fit"] = dict({"verdict": "build", "why": "no register draws it"}, **fit)
    return s


def test_a_workshop_shot_is_a_valid_shot_id(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert not [e for e in errs if "unknown shot" in e or "WsShotA is" in e], errs


def test_the_build_list_and_the_workshop_agree_both_ways(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("Ghost")])
    errs = _errs(board, tmp_path)
    assert any("`Ghost` has no workshop/objects/Ghost.tsx" in e for e in errs), errs
    assert any("workshop/shots/WsShotA.tsx is not on meta.build_list" in e for e in errs), errs


def test_an_entry_says_what_it_is_for_and_how_it_is_judged(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")],
                   [_entry("WsDisc", kind="widget", means="", accept=" ", slot=""), _entry("WsShotA", "shot")])
    errs = " | ".join(_errs(board, tmp_path))
    for needle in ("`kind` is object or shot", "`means` is empty", "`accept` is empty", "`slot` names the template"):
        assert needle in errs, (needle, errs)


def test_an_entry_no_beat_uses_is_refused_and_a_wrong_beats_list_is_named(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {}}],
                   [_entry("WsDisc"), _entry("WsShotA", "shot", beats=[2])])
    res = v.evaluate(board, str(tmp_path))
    assert any("`WsDisc` is used by no beat" in e for e in res["errors"]), res["errors"]
    assert any("`WsShotA` says beats [2]" in w for w in res["warnings"]), res["warnings"]


def test_shot_fit_ref_must_name_an_entry_this_beat_uses(tmp_path):
    board = _board(tmp_path, [_holding(ref="Nope"), {"shot": "WsShotA", "shot_props": {},
                                                      "shot_fit": {"verdict": "build", "ref": "WsDisc", "why": "x"}}],
                   [_entry("WsDisc"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert any("scene #1: shot_fit.ref 'Nope' is not on meta.build_list" in e for e in errs), errs
    assert any("scene #2: shot_fit.ref 'WsDisc', but this beat" in e for e in errs), errs


def test_a_build_verdict_names_its_entry(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {"object": {"id": "WsDisc"}},
                               "shot_fit": {"verdict": "build", "why": "x"}}],
                   [_entry("WsDisc"), _entry("WsShotA", "shot")])
    assert any("shot_fit says build but names no `ref`" in e for e in _errs(board, tmp_path))


def test_a_board_that_builds_nothing_is_judged_exactly_as_before(tmp_path):
    """No workshop, no build list: a library beat with a legacy `build` verdict gets no new finding."""
    board = _board(tmp_path, [{"shot": "TermTable", "shot_props": {"cmd": "ls"},
                               "shot_fit": {"verdict": "build", "why": "x"}}], shots=(), objects=())
    errs = _errs(board, tmp_path)
    assert not os.path.exists(tmp_path / "workshop")
    assert not [e for e in errs if "shot_fit.ref" in e or "names no `ref`" in e or "build_list" in e
                or "workshop" in e or "Design DNA" in e], errs


def test_an_unknown_object_is_named_with_what_exists(tmp_path):
    board = _board(tmp_path, [_holding("Nope", ref="WsShotA")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert any("names object 'Nope'" in e and "WsDisc" in e for e in errs), errs


def test_object_props_are_the_film_s_and_never_the_slot_s(tmp_path):
    s = _holding(ref="WsDisc")
    s["shot_props"]["object"]["props"] = {"t": 0.5, "color": "#fff"}
    board = _board(tmp_path, [s], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    assert any("props sets t" in e for e in _errs(board, tmp_path))


def test_a_prop_the_register_requires_in_a_film_must_be_set(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {}}], [_entry("WsShotA", "shot")],
                   objects=(), shot_src=REQUIRING)
    assert any("WsShotA needs `object` in a film" in e for e in _errs(board, tmp_path))


def test_a_film_that_builds_needs_a_design_dna(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                   meta={"design_dna": None})
    assert any("builds things but has no Design DNA" in e for e in _errs(board, tmp_path))


def test_a_held_object_supplies_the_beat_s_idiom_world(tmp_path):
    industrial = OBJECT.replace("'motion-graphics'", "'industrial'")
    ok = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                meta={"idiom_world": ["industrial"]}, obj_src=industrial)
    assert not [e for e in _errs(ok, tmp_path) if "world" in e], _errs(ok, tmp_path)
    (tmp_path / "workshop" / "objects" / "WsDisc.tsx").write_text(OBJECT % {"name": "WsDisc"}, encoding="utf-8")
    errs = _errs(ok, tmp_path)
    assert any("holding WsDisc" in e and "motion-graphics" in e for e in errs), errs


def test_the_workshop_code_check_reaches_validate(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "check", lambda out_dir: ["workshop/objects/WsDisc.tsx:3 words written into the code"])
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    assert any(e.startswith("workshop: workshop/objects/WsDisc.tsx:3") for e in _errs(board, tmp_path))
