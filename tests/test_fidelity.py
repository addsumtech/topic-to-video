"""OBJECT FIDELITY (references/object-authoring.md rule 7): a built thing that depicts a real thing declares its
references, proportions, parts and materials, and the fidelity sheet finds its declared parts in the DOM.

Each rule has a record that passes and one that fails; the DOM findings are judged on part reports shaped exactly
as runtime/fidelity.tsx logs them; one test renders the deliberately unfaithful BadWatch fixture end to end."""
import json
import os
import re
import shutil
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import fidelity as fid  # noqa: E402
import workshop as ws  # noqa: E402

BADWATCH = os.path.join(_ROOT, "tests", "fixtures", "fidelity", "badwatch")


def _good(tmp_path):
    (tmp_path / "refs").mkdir(exist_ok=True)
    (tmp_path / "refs" / "thing.jpg").write_bytes(b"\xff\xd8" + b"\0" * 2000)
    (tmp_path / "refs" / "thing.jpg.json").write_text(json.dumps({"license": "CC0", "source": "https://x"}))
    return {"subject": "a thing", "depicts": "real",
            "references": [{"kind": "photo", "source": "refs/thing.jpg"},
                           {"kind": "spec", "source": "https://example.org/spec"}],
            "proportions": {"w_to_h": {"value": 1.5, "source": "https://example.org/spec"}},
            "parts": ["body", "lid"], "materials": ["steel"]}


def _errs(rec, base, parts=None):
    return fid.errors_of(fid.problems(rec, str(base), "X", parts))


# ── the record ──────────────────────────────────────────────────────────────────────────────────────────────

def test_a_complete_real_record_passes(tmp_path):
    assert _errs(_good(tmp_path), tmp_path) == []


def _holds(rec, base):
    return [m for lv, m in fid.problems(rec, str(base), "X") if lv == "WARN" and "says what holds" in m]


def test_every_part_of_a_real_assembly_says_what_holds_it(tmp_path):
    """A part no mount names is checked against nothing — the floating jewel passed every distance test — so a real
    thing of two or more parts accounts for each: mounted on a part, null (held by what is not drawn), or a mount."""
    rec = dict(_good(tmp_path), parts=["plate", "wheel", "jewel"])
    w = _holds(rec, tmp_path)
    assert len(w) == 1 and "plate, wheel, jewel" in w[0] and "only 0" in w[0], w
    rec["mounted_on"] = {"jewel": "wheel"}                     # the wheel holds the jewel; the plate is unaccounted
    w = _holds(rec, tmp_path)
    assert len(w) == 1 and w[0].split(" — ")[1].startswith("plate:"), w
    rec["mounted_on"] = {"jewel": "wheel", "plate": None}      # null: held by something the drawing does not show
    assert _holds(rec, tmp_path) == [] and _errs(rec, tmp_path) == []
    rec["mounted_on"] = {"jewel": ["wheel", "plate"]}          # a list of mounts accounts for each of them
    assert _holds(rec, tmp_path) == []


def test_a_one_part_abstract_or_exploded_thing_owes_no_mounts(tmp_path):
    assert _holds(dict(_good(tmp_path), parts=["body"]), tmp_path) == []
    assert _holds({"subject": "a chart", "depicts": "abstract", "parts": ["a", "b"]}, tmp_path) == []
    assert _holds(dict(_good(tmp_path), parts=["a", "b", "c"], exploded=True), tmp_path) == []


def test_a_null_mount_is_not_a_part_name(tmp_path):
    rec = dict(_good(tmp_path), mounted_on={"body": None, "lid": "body"})
    assert _errs(rec, tmp_path) == [] and _holds(rec, tmp_path) == []
    bad = dict(_good(tmp_path), mounted_on={"lid": "hinge"})
    assert any("names 'hinge'" in e for e in _errs(bad, tmp_path))


def test_an_abstract_record_needs_no_reference(tmp_path):
    assert _errs({"subject": "a chart of years", "depicts": "abstract"}, tmp_path) == []


@pytest.mark.parametrize("mutate, needle", [
    (lambda r: r.update(references=[]), "names no reference"),
    (lambda r: r.update(references=[{"kind": "spec", "source": "https://example.org/spec"}]), "no reference IMAGE"),
    (lambda r: r["proportions"]["w_to_h"].pop("source"), "has no source"),
    (lambda r: r["proportions"]["w_to_h"].update(source="https://elsewhere"), "not among fidelity.references"),
    (lambda r: r.update(proportions={}), "records no proportion"),
    (lambda r: r.update(parts=[]), "names no defining parts"),
    (lambda r: r.update(parts=["Crown Wheel"]), "is not a part name"),
    (lambda r: r["references"].append({"kind": "drawing", "source": "refs/nope.png"}), "does not exist"),
    (lambda r: r["references"].append({"kind": "photo", "source": "https://example.org/a.jpg"}), "photo by URL"),
    (lambda r: r["references"].append({"kind": "sketch", "source": "https://example.org/a"}), "kind is one of"),
    (lambda r: r.update(depicts="realistic"), "fidelity.depicts"),
    (lambda r: r.update(subject=""), "subject is empty"),
    (lambda r: r.update(colour="gold"), "unknown key"),
])
def test_each_rule_fails_loudly(tmp_path, mutate, needle):
    rec = _good(tmp_path)
    mutate(rec)
    errs = _errs(rec, tmp_path)
    assert any(needle in e for e in errs), errs


def test_a_local_photo_needs_its_imagefetch_sidecar_and_an_asset_does_not(tmp_path):
    rec = _good(tmp_path)
    os.remove(tmp_path / "refs" / "thing.jpg.json")
    assert any("sidecar" in e for e in _errs(rec, tmp_path))
    rec["references"][0]["kind"] = "asset"                     # the product's own picture
    assert _errs(rec, tmp_path) == []


def test_a_declared_part_the_source_never_marks_is_reported(tmp_path):
    rec = _good(tmp_path)
    errs = _errs(rec, tmp_path, (set(), False))
    assert any("marks none of them" in e for e in errs), errs
    warns = [m for lv, m in fid.problems(rec, str(tmp_path), "X", ({"body"}, False)) if lv == "WARN"]
    assert any("lid" in w for w in warns), warns


# ── reading it out of a .tsx ────────────────────────────────────────────────────────────────────────────────

SRC = """import React from 'react';
// export const META = {aspect: 9};   a commented-out META never counts
export const META: FidelityMeta = {aspect: 16 / 9, provenance: 'scientific', fidelity: {
  subject: "a satellite's bus", // the thing
  depicts: 'real',
  references: [{kind: 'spec', source: 'https://example.org/a//b', note: 'a // inside a string'},],
  proportions: {aspect: {value: 3, source: 'https://example.org/a//b'}},  /* a proportion named aspect */
  parts: ['bus', 'wing'],
}, turns: true};
export const Thing = () => <g data-part="bus"><g data-part={side ? 'wing' : 'boom'} /></g>;
"""


def test_the_record_is_read_with_urls_comments_and_trailing_commas_intact():
    rec, why = fid.object_fidelity(SRC)
    assert why is None
    assert rec["references"][0]["source"] == "https://example.org/a//b"
    assert rec["references"][0]["note"] == "a // inside a string"
    assert rec["subject"] == "a satellite's bus"
    assert rec["parts"] == ["bus", "wing"]


def test_meta_keys_after_a_nested_record_are_still_read_and_a_proportion_is_not_meta():
    meta = ws.object_meta(SRC)
    assert meta["aspect"] == pytest.approx(16 / 9)            # not 3, the proportion named `aspect`
    assert meta["turns"] is True and meta["provenance"] == "scientific"


def test_a_computed_record_is_refused_by_name():
    rec, why = fid.object_fidelity(SRC.replace("depicts: 'real'", "depicts: KIND"))
    assert rec is None and "cannot be read as data" in why


def test_part_marks_are_read_from_the_source():
    names, dynamic = fid.source_part_names(SRC)
    assert {"bus", "wing", "boom"} <= names and dynamic is False
    assert fid.source_part_names("<g data-part={`w${i}`} />")[1] is True


def test_the_log_tag_is_the_runtimes():
    tsx = open(os.path.join(_ROOT, "remotion", "src", "runtime", "fidelity.tsx"), encoding="utf-8").read()
    assert "FIDELITY_TAG = '%s'" % fid.FIDELITY_TAG in tsx
    cjs = open(os.path.join(_ROOT, "scripts", "fidelity_stills.cjs"), encoding="utf-8").read()
    assert "TAG = '%s'" % fid.FIDELITY_TAG in cjs


# ── the library and the workshop ────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", sorted(ws.library_object_names()))
def test_every_library_object_declares_a_valid_record(name):
    src = open(os.path.join(ws.LIB_OBJECTS, name + ".tsx"), encoding="utf-8").read()
    rec, why = fid.object_fidelity(src)
    assert why is None and isinstance(rec, dict), "%s: META.fidelity is missing or unreadable (%s)" % (name, why)
    probs = fid.problems(rec, fid.SKILL, name, fid.source_part_names(src))
    assert fid.errors_of(probs) == [], probs
    assert not [m for lv, m in probs if lv == "WARN" and "says what holds" in m], probs
    if rec["depicts"] == "real":
        names, _dyn = fid.source_part_names(src)
        assert set(rec["parts"]) <= names, "every declared part is marked data-part in the source"


def _registers_with_a_record():
    out = []
    for n in sorted(ws.library_shot_names()):
        src = open(os.path.join(ws.LIB_SHOTS, n + ".tsx"), encoding="utf-8").read()
        if re.search(r"export\s+const\s+FIDELITY\b", src):
            out.append(n)
    return out


def test_a_library_register_declares_its_record_as_an_exported_fidelity():
    """A library register that draws a real thing inline has no build-list entry and no META: it exports FIDELITY,
    read with the same comment- and URL-aware scanner, and the sheet finds it by name."""
    src = ("export const DURATION = 90;\nexport const FIDELITY = {subject: 'x', depicts: 'abstract', // a note\n"
           "  references: [{kind: 'spec', source: 'https://example.org/a//b'}],};\nexport const X = () => null;\n")
    rec, why = fid.register_fidelity(src)
    assert why is None and rec["references"][0]["source"] == "https://example.org/a//b"
    assert fid.register_fidelity("export const DURATION = 90;\n") == (None, None)
    assert fid.register_fidelity("export const FIDELITY = {subject: f()};")[1]
    regs = _registers_with_a_record()
    assert regs, "at least one library register declares FIDELITY (references/object-audit.md)"
    rec, base, _src, where, kind = fid.record_for("/nonexistent-film", regs[0])
    assert kind == "shot" and base == fid.SKILL and where == "remotion/src/shots/%s.tsx" % regs[0]


@pytest.mark.parametrize("name", _registers_with_a_record())
def test_every_library_register_that_declares_a_record_declares_a_valid_one(name):
    src = open(os.path.join(ws.LIB_SHOTS, name + ".tsx"), encoding="utf-8").read()
    rec, why = fid.register_fidelity(src)
    assert why is None and isinstance(rec, dict), "%s: FIDELITY is unreadable (%s)" % (name, why)
    probs = fid.problems(rec, fid.SKILL, name, fid.source_part_names(src))
    assert fid.errors_of(probs) == [], probs
    assert not [m for lv, m in probs if lv == "WARN" and "says what holds" in m], probs
    if rec["depicts"] == "real":
        names, _dyn = fid.source_part_names(src)
        assert set(rec["parts"]) <= names, "every declared part is marked data-part in the source"


def test_a_workshop_object_without_a_record_is_a_check_problem(tmp_path):
    d = tmp_path / "workshop" / "objects"
    d.mkdir(parents=True)
    (d / "Plain.tsx").write_text("import React from 'react';\nexport const META = {aspect: 1, provenance: "
                                 "'scientific'};\nexport const Plain = () => null;\n", encoding="utf-8")
    assert any("META.fidelity is missing" in p for p in ws.names_problems(str(tmp_path)))


def test_the_scaffold_asks_for_the_record(tmp_path):
    ws.scaffold(str(tmp_path), "object", "NewThing", "a thing")
    probs = ws.names_problems(str(tmp_path))
    assert any("subject is empty" in p for p in probs)
    assert any("names no reference" in p for p in probs)


def test_the_bad_watch_fixture_has_a_valid_record_and_lies_in_its_drawing():
    src = open(os.path.join(BADWATCH, "workshop", "objects", "BadWatch.tsx"), encoding="utf-8").read()
    rec, _ = fid.object_fidelity(src)
    assert fid.errors_of(fid.problems(rec, BADWATCH, "BadWatch", fid.source_part_names(src))) == []
    assert not [p for p in ws.names_problems(BADWATCH) if "fidelity" in p.lower() and "warning" not in p]


# ── what the DOM drew ───────────────────────────────────────────────────────────────────────────────────────

def _rep(**parts):
    return {"f": 0, "canvas": {"w": 1000, "h": 1000},
            "parts": {k: {"boxes": [dict(zip("xywh", b)) for b in v], "hidden": 0} for k, v in parts.items()}}


def test_an_assembled_drawing_has_no_dom_problem():
    rep = _rep(case=[(100, 100, 400, 400)], band=[(200, 0, 200, 110), (200, 490, 200, 300)], crown=[(495, 280, 30, 40)])
    assert fid.dom_problems(rep, ["case", "band", "crown"], "W") == []


def test_a_declared_part_not_drawn_is_an_error():
    probs = fid.dom_problems(_rep(case=[(100, 100, 400, 400)]), ["case", "crown"], "W")
    assert any("'crown' is declared and not drawn" in m for _lv, m in probs)
    hidden = _rep(case=[(100, 100, 400, 400)])
    hidden["parts"]["crown"] = {"boxes": [], "hidden": 1}
    assert any("none visible" in m for _lv, m in fid.dom_problems(hidden, ["case", "crown"], "W"))


def test_a_floating_part_is_detached_unless_the_view_is_exploded():
    rep = _rep(case=[(300, 300, 400, 400)], band=[(350, 0, 300, 150), (350, 850, 300, 150)])
    probs = fid.dom_problems(rep, ["case", "band"], "W")
    assert any("'band' is detached" in m for _lv, m in probs), probs
    assert fid.dom_problems(rep, ["case", "band"], "W", exploded=True) == []


def test_no_part_report_is_never_read_as_clean():
    assert fid.errors_of(fid.dom_problems(None, ["case"], "W"))


def test_the_part_report_is_read_from_a_log():
    rec = _rep(case=[(1, 2, 3, 4)])
    log = "noise\n[Tab 1] %s%s\nmore" % (fid.FIDELITY_TAG, json.dumps(rec))
    assert fid.parts_from_log(log) == rec


def test_the_sheet_composes_from_its_renders(tmp_path):
    from PIL import Image
    rec = _good(tmp_path)
    Image.new("RGB", (800, 600), (40, 60, 90)).save(tmp_path / "refs" / "thing.jpg")
    hero, film = tmp_path / "hero.png", tmp_path / "film.png"
    Image.new("RGB", (1920, 1080), (10, 10, 10)).save(hero)
    Image.new("RGB", (1920, 1080), (20, 20, 20)).save(film)
    rep = _rep(body=[(600, 300, 700, 500)])
    out = fid.compose(str(tmp_path / "s.png"), "Thing", rec, str(tmp_path), str(hero), rep, str(film), rep,
                      fid.dom_problems(rep, rec["parts"], "Thing"), "on ObjectStage")
    im = Image.open(out)
    assert im.width == 2400 and im.height > 1200


# ── end to end: the bad watch, rendered ─────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not os.environ.get("FIDELITY_RENDER"), reason="renders: set FIDELITY_RENDER=1")
def test_the_sheet_catches_the_bad_watchs_missing_crown_and_detached_band(tmp_path):
    out = tmp_path / "film"
    shutil.copytree(BADWATCH, out)
    res = fid.sheet(str(out), "BadWatch")
    errs = fid.errors_of(res["problems"])
    assert any("'crown' is declared and not drawn" in e for e in errs), errs
    assert any("'band' is detached" in e for e in errs), errs
    assert os.path.isfile(res["png"])


# ── the gates that carry it: validate.py, shot_proof.py, the critic's ledger ─────────────────────────────────

def _shot_entry(**kw):
    e = {"id": "OrbitDial", "kind": "shot", "means": "m", "accept": "a", "slot": "own"}
    e.update(kw)
    return e


def test_validate_refuses_a_built_shot_with_no_record_and_reads_a_real_ones():
    import validate as v
    errs, warns = [], []
    v._check_build_fidelity({"OrbitDial": _shot_entry()}, {}, errs, warns, None)
    assert any("`fidelity` is missing" in e for e in errs), errs
    errs = []
    v._check_build_fidelity({"OrbitDial": _shot_entry(fidelity={"subject": "a dial", "depicts": "abstract"})}, {},
                            errs, warns, None)
    assert errs == []
    v._check_build_fidelity({"OrbitDial": _shot_entry(fidelity={"subject": "a watch", "depicts": "real"})}, {},
                            errs, warns, None)
    assert any("names no reference" in e for e in errs), errs


def _film_with_real_shot(tmp_path, rec):
    (tmp_path / "workshop" / "shots").mkdir(parents=True)
    (tmp_path / "workshop" / "shots" / "OrbitDial.tsx").write_text("export const OrbitDial = () => null;\n")
    board = {"meta": {"renderer": "remotion", "build_list": [_shot_entry(fidelity=rec)]}, "slides": []}
    (tmp_path / "storyboard.json").write_text(json.dumps(board), encoding="utf-8")
    return str(tmp_path)


def test_a_real_built_thing_owes_a_current_clean_sheet(tmp_path):
    import shot_proof as sp
    out = _film_with_real_shot(tmp_path, _good(tmp_path))
    assert fid.real_built_things(out) == [("OrbitDial", "shot")]
    assert fid.sheet_status(out, "OrbitDial") == "missing"
    assert any("sheet is missing" in e for e in sp.fidelity_sheet_findings(out))
    os.makedirs(os.path.join(out, fid.SHEET_DIR))
    with open(os.path.join(out, fid.SHEET_DIR, "OrbitDial.json"), "w") as fh:
        json.dump({"problems": [{"level": "ERROR", "message": "x"}]}, fh)
    assert fid.sheet_status(out, "OrbitDial") == "errors"
    with open(os.path.join(out, fid.SHEET_DIR, "OrbitDial.json"), "w") as fh:
        json.dump({"problems": []}, fh)
    assert fid.sheet_status(out, "OrbitDial") == "ok" and sp.fidelity_sheet_findings(out) == []
    later = os.path.getmtime(os.path.join(out, fid.SHEET_DIR, "OrbitDial.json")) + 10
    os.utime(os.path.join(out, "workshop", "shots", "OrbitDial.tsx"), (later, later))
    assert fid.sheet_status(out, "OrbitDial") == "stale"


def test_the_critics_fidelity_row_cites_each_sheet_and_cannot_pass_over_a_bad_one(tmp_path):
    import critic_ledger as cl
    out = _film_with_real_shot(tmp_path, _good(tmp_path))
    declared = cl.dimensions()
    sid = next(i for i, t in declared if t.startswith("FIDELITY"))
    row = {"id": sid, "verdict": "na", "note": "nothing real"}
    assert any("is N/A" in e for e in cl._fidelity_rows(out, declared, {sid: row}))
    row = {"id": sid, "verdict": "pass", "evidence": "looked at it"}
    errs = cl._fidelity_rows(out, declared, {sid: row})
    assert any("does not cite _fidelity/OrbitDial.png" in e for e in errs)
    assert any("sheet is missing" in e for e in errs)
    os.makedirs(os.path.join(out, fid.SHEET_DIR))
    with open(os.path.join(out, fid.SHEET_DIR, "OrbitDial.json"), "w") as fh:
        json.dump({"problems": []}, fh)
    row["evidence"] = "_fidelity/OrbitDial.png: proportions hold against the reference"
    assert cl._fidelity_rows(out, declared, {sid: row}) == []


def test_a_group_whose_box_spans_the_body_is_still_detached_by_its_leaves():
    """Two straps in ONE <g>: the group's box runs across the case between them, so a box test reads it as
    attached. The leaves — the straps themselves — float, and that is what is judged."""
    rep = _rep(case=[(300, 300, 400, 400)], band=[(350, 0, 300, 1000)])
    assert fid.dom_problems(rep, ["case", "band"], "W") == []          # what a group box alone would say
    rep["parts"]["band"]["leaves"] = [dict(zip("xywh", b)) for b in ((350, 0, 300, 150), (350, 850, 300, 150))]
    assert any("'band' is detached" in m for _lv, m in fid.dom_problems(rep, ["case", "band"], "W"))


def test_an_undeclared_marked_part_bridges_declared_ones_and_pieces_are_reported_once():
    rep = _rep(bus=[(300, 300, 200, 200)], wing=[(0, 350, 150, 100)], face=[(150, 300, 150, 200)])
    assert fid.dom_problems(rep, ["bus", "wing"], "S") == []            # the face (marked, undeclared) joins them
    rep = _rep(case=[(300, 300, 400, 400)], band=[(350, 0, 300, 1000)])
    rep["parts"]["band"]["leaves"] = [dict(zip("xywh", b)) for b in ((350, 0, 300, 150), (350, 850, 300, 150))]
    msgs = [m for _lv, m in fid.dom_problems(rep, ["case", "band"], "W")]
    assert len(msgs) == 1 and "2 pieces" in msgs[0], msgs


@pytest.mark.skipif(not os.environ.get("FIDELITY_RENDER"), reason="renders: set FIDELITY_RENDER=1")
@pytest.mark.parametrize("aspect", ["9:16", "1:1"])
def test_the_sheet_of_a_library_object_at_portrait_and_square(tmp_path, aspect):
    """E6/E8: the sheet was made and tested at 16:9 only. At 9:16 and 1:1 the film-size frame is the film's own
    shape, every declared part is found and attached, and the scope names the aspect it measured."""
    from PIL import Image
    (tmp_path / "storyboard.json").write_text(json.dumps(
        {"meta": {"renderer": "remotion", "aspect": aspect, "design_dna": "product"}, "slides": []}))
    res = fid.sheet(str(tmp_path), "GpsSatellite")
    assert fid.errors_of(res["problems"]) == [], res["problems"]
    want = {"9:16": (1080, 1920), "1:1": (1080, 1080)}[aspect]
    assert Image.open(os.path.join(str(tmp_path), "_fidelity", "GpsSatellite.film.png")).size == want
    assert any(aspect in ln for ln in res["scope"]) and res["scope"][0].startswith("MEASURED")


# ── attachment by the OUTLINES the probe reports, at the part's own scale, and on the part it is mounted on ──────
import math  # noqa: E402


def _square(x, y, w, h, fill=1, sw=0.5):
    """A filled rectangle's leaf as the probe reports it: its box and its outline sampled every ~3 px."""
    pts = []
    for (ax, ay), (bx, by) in zip([(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                                  [(x + w, y), (x + w, y + h), (x, y + h), (x, y)]):
        n = max(2, int(math.hypot(bx - ax, by - ay) / 3))
        pts += [v for k in range(n) for v in (ax + (bx - ax) * k / n, ay + (by - ay) * k / n)]
    return {"x": x, "y": y, "w": w, "h": h}, {"p": pts, "sw": sw, "f": fill, "s": 1}


def _ring(cx, cy, r, sw):
    n = int(2 * math.pi * r / 3)
    pts = [v for k in range(n) for v in (cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n))]
    return {"x": cx - r - sw, "y": cy - r - sw, "w": 2 * (r + sw), "h": 2 * (r + sw)}, {"p": pts, "sw": sw, "f": 0, "s": 1}


def _geo_rep(**parts):
    return {"f": 0, "canvas": {"w": 1000, "h": 1000},
            "parts": {k: {"boxes": [b for b, _g in v], "leaves": [b for b, _g in v], "geo": [g for _b, g in v],
                          "hidden": 0} for k, v in parts.items()}}


def test_a_piece_inside_a_rings_box_but_far_from_its_rim_is_detached_by_its_outline():
    """A rim's BOX holds everything inside the ring (the escapement's balance: a 926 px box around every part), so a
    box test called any piece in there attached. The outline says how far the ink really is."""
    rep = _geo_rep(rim=[_ring(500, 500, 300, 6)], hub=[_square(480, 480, 40, 40)])
    assert any("'hub' is detached" in m for _lv, m in fid.dom_problems(rep, ["rim", "hub"], "R"))
    rep["parts"]["hub"]["geo"] = [None]                             # no outline: the box, as before (a lower bound)
    assert fid.dom_problems(rep, ["rim", "hub"], "R") == []
    rep = _geo_rep(rim=[_ring(500, 500, 300, 6)], spoke=[_square(200, 490, 600, 20)])
    assert fid.dom_problems(rep, ["rim", "spoke"], "R") == [], "a spoke that meets the rim is attached"


def test_the_tolerance_is_the_small_parts_own_not_the_drawings():
    """2% of the diagonal is 12 px here; a 20 px part 10 px off the body floats in a gap half its own size."""
    rep = _geo_rep(body=[_square(100, 100, 400, 400)], pin=[_square(510, 290, 20, 20)])
    msgs = [m for _lv, m in fid.dom_problems(rep, ["body", "pin"], "P")]
    assert len(msgs) == 1 and "'pin' is detached" in msgs[0], msgs
    rep = _geo_rep(body=[_square(100, 100, 400, 400)], pin=[_square(501, 290, 20, 20)])
    assert fid.dom_problems(rep, ["body", "pin"], "P") == [], "a seam of a pixel is attached"


def test_a_part_touching_something_else_is_still_reported_off_its_mount():
    """The escapement's jewel rests on a wheel tooth and crosses the balance rim in the picture: it belongs to the
    drawing's one piece whether or not it sits on its fork. Only the declared mount says what it must touch."""
    rep = _geo_rep(fork=[_square(100, 340, 200, 60)], wheel=[_square(100, 400, 300, 300)],
                   jewel=[_square(330, 380, 30, 60)])                       # on the wheel, 30 px off the fork's end
    assert fid.dom_problems(rep, ["fork", "wheel", "jewel"], "E") == []    # touching the wheel: one piece
    msgs = [m for _lv, m in fid.dom_problems(rep, ["fork", "wheel", "jewel"], "E", mounted_on={"jewel": "fork"})]
    assert len(msgs) == 1 and "'jewel' is mounted on 'fork'" in msgs[0] and "does not touch it" in msgs[0], msgs
    rep["parts"]["jewel"] = _geo_rep(j=[_square(280, 345, 30, 60)])["parts"]["j"]   # set into the fork
    assert fid.dom_problems(rep, ["fork", "wheel", "jewel"], "E", mounted_on={"jewel": ["fork"]}) == []


def test_mounted_on_names_declared_parts(tmp_path):
    rec = _good(tmp_path)
    rec["mounted_on"] = {"lid": "body"}
    assert _errs(rec, tmp_path) == []
    rec["mounted_on"] = {"lid": "hinge"}
    assert any("'hinge', which is not one of fidelity.parts" in e for e in _errs(rec, tmp_path))
    rec["mounted_on"] = {"lid": "lid"}
    assert any("mounted on itself" in e for e in _errs(rec, tmp_path))


# ── a film with a drawing style: the sheet is measured on the STYLED drawing (style engine spec, Constraints) ──────

_STYLED = {"name": "fidelity under a style", "refs": [], "refs_missing": "test",
           "line": {"outline": "all", "weight": 4, "color": "ink"}, "fill": {"mode": "cel", "steps": 3},
           "shadow": {"mode": "hard-offset", "offset": 6}, "form": {"simplify": 0.5}}


@pytest.mark.skipif(not os.environ.get("FIDELITY_RENDER"), reason="renders: set FIDELITY_RENDER=1")
@pytest.mark.parametrize("name", ["GpsSatellite", "DNAHelix", "GearTrain", "MoleculeBallStick"])
def test_the_sheet_of_a_library_thing_under_a_drawing_style(tmp_path, name):
    """A style may simplify detail and round forms; it may not lose a part or detach one. The sheet renders the
    film's style, says so, and finds every declared part attached."""
    (tmp_path / "storyboard.json").write_text(json.dumps(
        {"meta": {"renderer": "remotion", "design_dna": "product", "style": _STYLED}, "slides": []}))
    res = fid.sheet(str(tmp_path), name)
    assert fid.errors_of(res["problems"]) == [], res["problems"]
    rep = json.load(open(res["json"], encoding="utf-8"))
    assert rep.get("style") == _STYLED["name"], "the sheet does not say it measured the styled drawing"


# ── marks a shot makes through a helper it imports ──────────────────────────────────────────────────────────────

def test_create_element_part_marks_are_read():
    # a .ts kit has no JSX: it marks parts as createElement props — the same mark, in the other spelling
    src = "h('path', {key: 'tip', 'data-part': 'ear-tip'}); h('g', {\"data-part\": \"shell\"});"
    names, dynamic = fid.source_part_names(src)
    assert {"ear-tip", "shell"} <= names and dynamic is False


def test_a_shot_drawing_its_thing_through_a_local_kit_has_its_marks_read(tmp_path):
    # the anc film: every earbud part is drawn (and marked) in workshop/shots/ancKit.ts, which the shots import;
    # validate read only the shot's own file and said the shot "marks none of them"
    import validate as v
    shots = tmp_path / "workshop" / "shots"
    shots.mkdir(parents=True)
    (shots / "kit.ts").write_text("export const body = () => h('g', {'data-part': 'body'}, h('g', {'data-part': 'lid'}));\n")
    (shots / "OrbitDial.tsx").write_text("import {body} from './kit';\nexport const OrbitDial = () => body();\n")
    rec = _good(tmp_path)
    errs, warns = [], []
    v._check_build_fidelity({"OrbitDial": _shot_entry(fidelity=rec)}, {"OrbitDial": "shot"}, errs, warns, str(tmp_path))
    assert not any("marks none" in m for m in errs + warns), errs + warns
    assert not any("never marks" in m for m in warns), warns
