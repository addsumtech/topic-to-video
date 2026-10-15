"""validate.py knows what a film built: the build list and the workshop agree both ways, every reference names
something that exists, and the stage registers' own previews never reach a film."""
import os
import subprocess
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


def test_a_board_that_builds_nothing_is_judged_exactly_as_before(tmp_path, monkeypatch):
    """No workshop, no build list: a library beat with a legacy `build` verdict gets no new finding — and the
    EXISTING library-registration check (register_shot.check) still fires on its own terms, forced here since
    the real TermTable is properly registered and would otherwise stay silent either way."""
    import register_shot as rs
    monkeypatch.setattr(rs, "check", lambda shot: ["registry.ts"] if shot == "TermTable" else [])
    board = _board(tmp_path, [{"shot": "TermTable", "shot_props": {"cmd": "ls"},
                               "shot_fit": {"verdict": "build", "why": "x"}}], shots=(), objects=())
    errs = _errs(board, tmp_path)
    assert not os.path.exists(tmp_path / "workshop")
    assert any("not registered in registry.ts" in e for e in errs), errs
    # the design-first floor (validate._design_share) is a separate, deliberate finding on a film that built
    # nothing; this test is about the build-list checks staying silent
    assert not [e for e in errs if not e.startswith("design-first") and (
                "shot_fit.ref" in e or "names no `ref`" in e or "build_list" in e
                or "workshop" in e or "Design DNA" in e or "the film built" in e)], errs


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
    """Only true of a STAGE — a register whose REQUIRED_IN_FILM names its own object slot, so it cannot appear
    without one; see test_a_non_stage_host_is_judged_on_its_own_world_and_each_held_object_s for the other kind
    of host."""
    industrial = OBJECT.replace("'motion-graphics'", "'industrial'")
    ok = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                meta={"idiom_world": ["industrial"]}, obj_src=industrial, shot_src=REQUIRING)
    assert not [e for e in _errs(ok, tmp_path) if "world" in e], _errs(ok, tmp_path)
    (tmp_path / "workshop" / "objects" / "WsDisc.tsx").write_text(OBJECT % {"name": "WsDisc"}, encoding="utf-8")
    errs = _errs(ok, tmp_path)
    assert any("holding WsDisc" in e and "motion-graphics" in e for e in errs), errs


def test_the_workshop_code_check_reaches_validate(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "check", lambda out_dir: ["workshop/objects/WsDisc.tsx:3 words written into the code"])
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    assert any(e.startswith("workshop: workshop/objects/WsDisc.tsx:3") for e in _errs(board, tmp_path))


def test_a_malformed_shot_fit_ref_is_reported_not_raised(tmp_path):
    """A `ref` is a SINGLE build-list id; a list, a dict or an int can never be one — reported, never crashed."""
    for bad in (["WsShotA", "WsDisc"], {"id": "WsDisc"}, 3):
        board = _board(tmp_path, [_holding(ref=bad)], [_entry("WsDisc"), _entry("WsShotA", "shot")])
        errs = _errs(board, tmp_path)
        assert any("shot_fit.ref must name ONE build-list id" in e for e in errs), (bad, errs)


def test_malformed_beats_are_reported_not_raised(tmp_path):
    """`beats` mixing incomparable types crashed `sorted()`; a non-list `beats` was never checked at all."""
    for bad in (5, "7", [1, "2"], [None, 1], ["1"]):
        board = _board(tmp_path, [_holding(ref="WsDisc")],
                       [_entry("WsDisc", beats=bad), _entry("WsShotA", "shot")])
        errs = _errs(board, tmp_path)
        assert any("`beats` must be a list of whole numbers" in e for e in errs), (bad, errs)


def test_beats_that_are_whole_numbers_are_compared_as_a_set(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")],
                   [_entry("WsDisc", beats=[1, 99]), _entry("WsShotA", "shot")])
    warns = v.evaluate(board, str(tmp_path))["warnings"]
    assert any("says beats [1, 99]" in w and "uses it on beats [1]" in w for w in warns), warns


def test_a_topic_named_shot_template_with_no_preset_still_needs_a_design_dna(tmp_path):
    """`meta.shot_template` naming a bespoke, unrecognised direction renders with `dna = null` — it must not
    count as a Design DNA here any more than it does for `_check_remotion`'s own "NO Design DNA" warning."""
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                   meta={"design_dna": None, "shot_template": "no-such-template"})
    assert any("builds things but has no Design DNA" in e for e in _errs(board, tmp_path))


def test_a_workshop_shot_with_no_provenance_is_told_to_declare_it_there(tmp_path):
    """A fresh scaffold's `PROVENANCE = ''` must not send its author to register_shot.py, which writes the
    film's OWN item into the library (and workshop.check then refuses the shadowed name)."""
    noprov = SHOT.replace("export const PROVENANCE = 'motion-graphics';\n", "")
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {},
                               "shot_fit": {"verdict": "build", "ref": "WsShotA", "why": "x"}}],
                   [_entry("WsShotA", "shot")], objects=(), shot_src=noprov, meta={"idiom_world": ["industrial"]})
    errs = _errs(board, tmp_path)
    assert any("export const PROVENANCE" in e and "workshop/shots/WsShotA.tsx" in e for e in errs), errs
    assert not any("register_shot.py WsShotA" in e for e in errs), errs


def test_a_workshop_shot_that_reads_useDNA_is_not_flagged_unaware(tmp_path):
    """dna_audit only scans the LIBRARY; a workshop shot must be judged from its own source instead."""
    dna_shot = SHOT.replace("import {AbsoluteFill} from 'remotion';",
                            "import {AbsoluteFill} from 'remotion';\nimport {useDNA} from '@runtime/dna';").replace(
        "=> (\n  <AbsoluteFill style={{background: fill}}>",
        "=> {\n  const dna = useDNA();\n  return (\n  <AbsoluteFill style={{background: dna.bg}}>").replace(
        "  </AbsoluteFill>\n);", "  </AbsoluteFill>\n  );\n};")
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                   meta={"idiom_world": ["motion-graphics"]}, shot_src=dna_shot)
    warns = v.evaluate(board, str(tmp_path))["warnings"]
    assert not [w for w in warns if "NOT Design-DNA-aware" in w], warns


def test_a_workshop_shot_that_never_reads_useDNA_is_still_flagged(tmp_path):
    """The positive control for the probe above: the gate still bites a workshop shot that really doesn't."""
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                   meta={"idiom_world": ["motion-graphics"]})
    warns = v.evaluate(board, str(tmp_path))["warnings"]
    assert any("NOT Design-DNA-aware" in w and "WsShotA" in w for w in warns), warns


def test_a_workshop_shot_s_energy_is_worded_as_unmeasured_by_design(tmp_path):
    """register_energy.py is a LIBRARY sweep and never sees a workshop; telling the author to run it for a
    workshop shot's missing energy row is advice that cannot help."""
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                   meta={"idiom_world": ["motion-graphics"]})
    warns = v.evaluate(board, str(tmp_path))["warnings"]
    energy = [w for w in warns if w.startswith("remotion: energy skeleton — ")]
    assert energy, warns
    assert not any("register_energy.py" in w for w in energy), energy
    assert any("unmeasured" in w and "WsShotA" in w for w in energy), energy


def test_a_workshop_shot_is_never_told_to_keep_a_register_s_style(tmp_path):
    """§B2 adapt-don't-text-swap is about ADAPTING an existing library register; a shot the film itself
    authored has no prior style to keep."""
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {"object": {"id": "WsDisc"}},
                               "shot_fit": {"verdict": "build", "ref": "WsShotA", "why": "x"}}],
                   [_entry("WsDisc"), _entry("WsShotA", "shot")], meta={"idiom_world": ["motion-graphics"]})
    warns = v.evaluate(board, str(tmp_path))["warnings"]
    assert not [w for w in warns if "shot_adaptation" in w or "EMPTY shot_props" in w], warns


def test_a_stray_file_in_an_otherwise_empty_workshop_folder_is_not_checked(tmp_path, monkeypatch):
    """workshop.prepare() (the render path) treats a workshop/ folder with no objects/ or shots/ as no
    workshop at all; the validate-time check must agree — a library-only board is not failed by a folder the
    render itself never reads as a workshop."""
    monkeypatch.undo()   # this one test needs the REAL workshop.check, not the autouse stub
    board = _board(tmp_path, [{"shot": "TermTable", "shot_props": {"cmd": "ls"}}], shots=(), objects=())
    os.makedirs(tmp_path / "workshop", exist_ok=True)
    (tmp_path / "workshop" / "bench-photo.jpg").write_bytes(b"\xff\xd8\xff")
    errs = _errs(board, tmp_path)
    assert not [e for e in errs if e.startswith("workshop:")], errs


def test_a_non_stage_host_is_judged_on_its_own_world_and_each_held_object_s(tmp_path):
    """A HUD reticle, a technical plate, a device frame — a host with a strong visual language of its own —
    does not hand the whole beat's idiom to what it holds; only a STAGE does that."""
    industrial = OBJECT.replace("'motion-graphics'", "'industrial'")
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                   meta={"idiom_world": ["industrial"]}, obj_src=industrial)   # default shot_src: no REQUIRED_IN_FILM
    errs = _errs(board, tmp_path)
    assert any(e.startswith("remotion: beat 1 uses WsShotA, whose visual language comes from 'motion-graphics'")
              for e in errs), errs


def test_one_held_object_without_a_provenance_does_not_excuse_another_that_has_one(tmp_path):
    """A beat can hold several objects; one with no declared provenance must not wave through a SIBLING that
    has one and disagrees with the film. Each held object with a provenance is judged on its own."""
    scientific = OBJECT.replace("'motion-graphics'", "'scientific'")
    bare = OBJECT.replace(", provenance: 'motion-graphics'", "")
    two = SHOT.replace("{fill?: string; object?: ObjectRef}", "{fill?: string; first?: ObjectRef; second?: ObjectRef}") \
              .replace("({fill = '#00ff00', object})", "({fill = '#00ff00', first, second})") \
              .replace('{object ? <ObjectSlot object={object} box={{x: 660, y: 240, w: 600, h: 600}} /> : null}',
                       "{first ? <ObjectSlot object={first} box={{x: 60, y: 240, w: 600, h: 600}} /> : null}\n"
                       "    {second ? <ObjectSlot object={second} box={{x: 960, y: 240, w: 600, h: 600}} /> : null}")
    beat = {"shot": "WsTwo", "shot_props": {"first": {"id": "WsSci"}, "second": {"id": "WsBare"}},
            "shot_fit": {"verdict": "build", "ref": "WsTwo", "why": "x"}}
    board = _board(tmp_path, [beat], [_entry("WsSci"), _entry("WsBare"), _entry("WsTwo", "shot")],
                   shots=("WsTwo",), objects=("WsSci", "WsBare"), shot_src=two,
                   meta={"idiom_world": ["motion-graphics"]})   # WsTwo's own world; declares nothing else
    (tmp_path / "workshop" / "objects" / "WsSci.tsx").write_text(scientific % {"name": "WsSci"}, encoding="utf-8")
    (tmp_path / "workshop" / "objects" / "WsBare.tsx").write_text(bare % {"name": "WsBare"}, encoding="utf-8")
    errs = _errs(board, tmp_path)
    assert any("holding WsSci" in e and "scientific" in e for e in errs), errs
    assert not [e for e in errs if "WsBare" in e and "world" in e], errs


def test_no_idiom_world_warning_lists_the_workshop_s_own_worlds_too(tmp_path):
    industrial = OBJECT.replace("'motion-graphics'", "'industrial'")
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")],
                   obj_src=industrial)   # no meta.idiom_world at all
    warns = v.evaluate(board, str(tmp_path))["warnings"]
    msg = next(w for w in warns if "no meta.idiom_world" in w)
    assert "industrial" in msg and "motion-graphics" in msg, msg


def test_a_required_prop_set_to_null_still_counts_as_missing(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {"object": None},
                               "shot_fit": {"verdict": "build", "ref": "WsShotA", "why": "x"}}],
                   [_entry("WsShotA", "shot")], objects=(), shot_src=REQUIRING)
    assert any("WsShotA needs `object` in a film" in e for e in _errs(board, tmp_path))


def test_a_commented_out_required_in_film_does_not_count(tmp_path):
    commented = SHOT.replace("export const DURATION = 30;",
                             "export const DURATION = 30;\n// export const REQUIRED_IN_FILM = ['fill'];")
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {},
                               "shot_fit": {"verdict": "build", "ref": "WsShotA", "why": "x"}}],
                   [_entry("WsShotA", "shot")], objects=(), shot_src=commented)
    assert not any("needs `fill` in a film" in e for e in _errs(board, tmp_path))


def test_a_ref_with_a_stray_key_outside_id_and_props_is_refused(tmp_path):
    s = _holding(ref="WsDisc")
    s["shot_props"]["object"]["prop"] = {"color": "#fff"}   # typo of `props`: a stray top-level key
    board = _board(tmp_path, [s], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert any('"WsDisc" has prop outside "props"' in e for e in errs), errs


def test_the_unknown_object_list_never_offers_a_demo_object(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "demo_objects", lambda: {"WsDisc"})
    board = _board(tmp_path, [_holding("Nope", ref="WsShotA")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    msg = next(e for e in _errs(board, tmp_path) if "names object 'Nope'" in e)
    assert "WsDisc" not in msg, msg


def test_a_kind_mismatch_message_uses_the_right_article(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc", kind="shot"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert any("is listed as a shot and the workshop holds it as an object" in e for e in errs), errs


def test_a_non_pascalcase_build_list_id_is_named_a_bad_name(tmp_path):
    """The workshop's own scaffold refuses this name; validate must say so up front rather than offer a
    `new-object ws_ghost` command that would fail."""
    board = _board(tmp_path, [_holding(ref="WsDisc")],
                   [_entry("WsDisc"), _entry("WsShotA", "shot"), _entry("ws_ghost")])
    errs = _errs(board, tmp_path)
    assert any("not a name the workshop accepts" in e and "ws_ghost" in e for e in errs), errs


def test_promoted_must_be_a_real_boolean(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")],
                   [_entry("WsDisc", promoted="false"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert any("`promoted` must be a boolean" in e for e in errs), errs
    assert not any("is marked promoted but the library has no" in e for e in errs), errs


def test_duplicate_and_unused_entries_both_name_a_fix(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {}}],
                   [_entry("WsDisc"), _entry("WsDisc", means=""), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    twice = next(e for e in errs if "is listed twice" in e)
    unused = next(e for e in errs if "is used by no beat" in e)
    assert "remove the duplicate" in twice, twice
    assert "remove the entry" in unused, unused


def test_an_orphan_workshop_item_names_the_entry_to_add(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {}}], [])
    errs = _errs(board, tmp_path)
    orphan = next(e for e in errs if "workshop/shots/WsShotA.tsx is not on meta.build_list" in e)
    assert "add an entry" in orphan and "WsShotA" in orphan, orphan


def test_unknown_shot_error_also_points_at_the_film_s_own_workshop(tmp_path):
    board = _board(tmp_path, [{"shot": "NotARealShot", "shot_props": {}}], shots=(), objects=())
    errs = _errs(board, tmp_path)
    msg = next(e for e in errs if "unknown shot" in e)
    assert "workshop" in msg, msg


def test_a_workshop_check_exception_is_reported_not_raised(tmp_path, monkeypatch):
    monkeypatch.undo()   # this one test needs to install its OWN workshop.check, not the autouse stub

    def _boom(out_dir):
        raise RuntimeError("disk fell over")
    monkeypatch.setattr(ws, "check", _boom)
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert any(e.startswith("workshop:") and "RuntimeError" in e and "disk fell over" in e for e in errs), errs


def test_an_unmeasurable_workshop_check_is_a_skip_not_an_error(tmp_path, monkeypatch):
    monkeypatch.undo()
    monkeypatch.setattr(ws, "check",
                        lambda out_dir: ["the type-check could not run: tsc is missing — " + ws.NOTHING_CHECKED])
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    res = v.evaluate(board, str(tmp_path))
    assert not [e for e in res["errors"] if "type-check could not run" in e], res["errors"]
    assert any("type-check could not run" in s for s in res["skipped"]), res["skipped"]


def test_a_crashing_baked_words_scan_is_a_skip_not_an_error(tmp_path, monkeypatch):
    """The workshop's own code check, for real — only jsx_words.cjs's own subprocess call is faked, so
    `ws.baked_words` reaches its actual crash handling rather than a stand-in for it, and the type-check (its
    own tests live in tests/test_workshop.py) is stubbed out to keep this one about the baked-words scan
    alone."""
    monkeypatch.undo()
    monkeypatch.setattr(ws, "typecheck", lambda out_dir: [])
    real_run = ws.subprocess.run

    def _crash(cmd, **kw):
        if any("jsx_words.cjs" in str(a) for a in cmd):
            return subprocess.CompletedProcess(cmd, 1, stdout="",
                                                stderr="TypeError: Cannot read properties of undefined")
        return real_run(cmd, **kw)
    monkeypatch.setattr(ws.subprocess, "run", _crash)
    board = _board(tmp_path, [_holding(ref="WsDisc")], [_entry("WsDisc"), _entry("WsShotA", "shot")])
    res = v.evaluate(board, str(tmp_path))
    assert not [e for e in res["errors"] if "baked-words scan failed" in e], res["errors"]
    assert any("baked-words scan failed" in s and s.endswith(ws.NOTHING_CHECKED) for s in res["skipped"]), \
        res["skipped"]


def test_a_workshop_shot_beat_with_the_wrong_verdict_is_refused(tmp_path):
    """Spec §1: a beat that uses a built item says so (`verdict: "build"`) — recording `fit`/`adapt` for a
    beat whose shot the film itself built is a lie the fit judgement should catch."""
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {"object": {"id": "WsDisc"}},
                               "shot_fit": {"verdict": "fit", "why": "x"}}],
                   [_entry("WsDisc"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert any("the film built" in e and "WsShotA" in e and "got verdict 'fit'" in e for e in errs), errs


def test_a_workshop_shot_beat_with_no_shot_fit_at_all_is_refused(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {"object": {"id": "WsDisc"}}}],
                   [_entry("WsDisc"), _entry("WsShotA", "shot")])
    errs = _errs(board, tmp_path)
    assert any("the film built" in e and "WsShotA" in e for e in errs), errs


def test_a_beat_holding_a_workshop_object_through_a_slotted_library_shot_is_also_refused(tmp_path, monkeypatch):
    """The other half of the rule: a beat need not be ON a workshop shot to owe `verdict: "build"` — holding a
    workshop OBJECT is enough. No current library register has a slot yet, so this is exercised through a
    fabricated one (workshop.LIB_SHOTS monkeypatched), the same technique used elsewhere for a fabricated
    library object."""
    lib = tmp_path / "fake_lib_shots"
    lib.mkdir()
    (lib / "LibStage.tsx").write_text(SHOT % {"name": "LibStage"}, encoding="utf-8")
    monkeypatch.setattr(ws, "LIB_SHOTS", str(lib))
    board = _board(tmp_path, [{"shot": "LibStage", "shot_props": {"object": {"id": "WsDisc"}},
                               "shot_fit": {"verdict": "fit", "why": "x"}}],
                   [_entry("WsDisc")], shots=(), objects=("WsDisc",))
    errs = _errs(board, tmp_path)
    assert any("the film built" in e and "WsDisc" in e for e in errs), errs


def test_a_shot_entry_s_slot_should_be_own(tmp_path):
    board = _board(tmp_path, [{"shot": "WsShotA", "shot_props": {"object": {"id": "WsDisc"}},
                               "shot_fit": {"verdict": "build", "ref": "WsShotA", "why": "x"}}],
                   [_entry("WsDisc"), _entry("WsShotA", "shot", slot="ObjectStage")])
    warns = v.evaluate(board, str(tmp_path))["warnings"]
    assert any("`WsShotA` is a shot; its `slot` should be \"own\"" in w for w in warns), warns


def test_an_object_entry_s_declared_slot_must_match_where_it_is_held(tmp_path):
    board = _board(tmp_path, [_holding(ref="WsDisc")],
                   [_entry("WsDisc", slot="SomeOtherShot"), _entry("WsShotA", "shot")])
    warns = v.evaluate(board, str(tmp_path))["warnings"]
    assert any("`WsDisc` names slot 'SomeOtherShot'" in w and "'WsShotA'" in w for w in warns), warns


def test_an_object_held_by_several_templates_lists_them_all(tmp_path):
    """One object serving several beats in different templates is the reuse the build flow is for, so `slot`
    may list every template that holds it; only a holder it does not list is named."""
    held_in_both = [_holding(ref="WsDisc"),
                    {"shot": "WsShotB", "shot_props": {"object": {"id": "WsDisc"}},
                     "shot_fit": {"verdict": "build", "ref": "WsDisc", "why": "x"}}]
    entries = lambda slot: [_entry("WsDisc", slot=slot), _entry("WsShotA", "shot"), _entry("WsShotB", "shot")]
    ok = v.evaluate(_board(tmp_path, held_in_both, entries(["WsShotA", "WsShotB"]),
                           shots=("WsShotA", "WsShotB")), str(tmp_path))
    assert not any("names slot" in w for w in ok["warnings"]), ok["warnings"]
    assert not any("`slot`" in e for e in ok["errors"]), ok["errors"]
    short = v.evaluate(_board(tmp_path, held_in_both, entries(["WsShotA"]), shots=("WsShotA", "WsShotB")),
                       str(tmp_path))["warnings"]
    assert any("names slot ['WsShotA']" in w and "'WsShotB'" in w and "'WsShotA', " not in w for w in short), short
    for bad in ([], ["WsShotA", ""], ["WsShotA", 3]):
        errs = v.evaluate(_board(tmp_path, held_in_both, entries(bad), shots=("WsShotA", "WsShotB")),
                          str(tmp_path))["errors"]
        assert any("a non-empty list of register names" in e for e in errs), (bad, errs)
