"""A register whose premise is a real photograph must REFUSE to draw without one — and must be MEASURED
with one.

Four registers exist to put a real artefact on the frame and reason about it: PhotoPlate frames a photo and
points at two places in it, RealVersus puts two real states side by side, ScanReconstruct rebuilds one, and
MuseumLabel captions one. Given no image they each drew the furniture around an absent picture — an outlined
empty box, callout chips reading "what to notice here" pointing at nothing — and the render succeeded, so
nothing anywhere said the frame was empty.

The energy sweep then measured those empty boxes and wrote them down as the register: PhotoPlate 0.6% ink,
RealVersus and ScanReconstruct 0.0%, MuseumLabel 0.9% — the four emptiest rows in a 152-register library.
Given the image they are built for, the same four measure 37.2%, 28.9%, 16.5% and 25.7%, well over the 12%
delivery floor. The manifest was not describing a weakness in these registers; it was describing a hole in
how they were called, and `density_advice.py` reads that manifest to tell authors which registers to avoid.

So there are two rules here and they hold each other up: the shot refuses, and the sweep supplies. Either one
alone breaks: refusing without supplying makes the four permanently unmeasurable, and supplying without
refusing leaves a real film free to ship the empty box.
"""
import json
import os
import re
import subprocess

import pytest

import register_energy as reg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(reg.__file__)))
SHOTS = os.path.join(ROOT, "remotion", "src", "shots")


def _shot(name):
    return open(os.path.join(SHOTS, name + ".tsx"), encoding="utf-8").read()


def test_the_four_hole_drawers_refuse_rather_than_draw_an_empty_plate():
    """Pinned by NAME because each was confirmed by rendering it: all four drew a hole."""
    for name, prop in [("PhotoPlate", "src"), ("RealVersus", "srcLeft"),
                       ("ScanReconstruct", "src"), ("MuseumLabel", "src")]:
        src = _shot(name)
        assert re.search(r"requireEvidence\(\s*'%s'\s*,\s*'%s'" % (name, prop), src), (
            "%s no longer requires `%s` — it will render an empty plate again" % (name, prop))


def test_the_refusal_says_what_to_do_not_just_that_something_is_missing():
    """An author who hits this is one `imagefetch` call from a working frame. A bare 'src is required'
    leaves them to guess where the file goes and what the path is relative to."""
    ev = open(os.path.join(ROOT, "remotion", "src", "runtime", "evidence.ts"), encoding="utf-8").read()
    for needed in ("imagefetch.py", "relative to", "different register"):
        assert needed in ev, "the refusal does not tell the author %r" % needed


def test_the_sweep_derives_its_fixture_list_from_the_call_sites():
    """A restated list drifts: a fifth register adopting the guard would be swept without a fixture and
    recorded as a permanent failure, and one dropping it would keep a fixture nothing asked for."""
    ev = reg.evidence_props()
    # FIVE now: `PageWrite` adopted the guard, and its evidence is a captured PAGE — a texture AND the boxes
    # measured from the same load, because a screenshot with no layout can be panned across and never
    # animated. Which registers need that is read from their own signatures too, not listed in the code.
    # SIX now, and the sixth arrives by a SECOND derivation. `requireEvidence` names one `src` prop, so a
    # register that draws a LIST of pictures — StateSheet's `cells: {src, label}[]` — matched no call site,
    # was rendered on its defaults (an empty sheet, which throws), and all three measurement scripts recorded
    # RENDER FAILED. Its fixture is derived from the TYPE: an array whose element declares `src: string`.
    assert set(ev) == {"PhotoPlate", "RealVersus", "ScanReconstruct", "MuseumLabel", "PageWrite",
                       "StateSheet"}, ev
    cells = ev["StateSheet"].get("cells")
    assert isinstance(cells, list) and len(cells) >= 2 and all(c.get("src") for c in cells), (
        "a list-of-pictures register must get a LIST of pictures, not one path: %r" % (cells,))
    assert set(ev["PageWrite"]) >= {"src", "blocks", "pageW", "pageH", "bg"}, ev["PageWrite"]
    # a paired register guards ONE prop; both halves must be filled or half the frame is still the hole
    assert set(ev["RealVersus"]) == {"srcLeft", "srcRight"}, ev["RealVersus"]
    # the names may appear in prose (this history is worth keeping); what must not exist is a name in the
    # CODE that builds the list
    import inspect
    body = inspect.getsource(reg.evidence_props)
    parts = body.split('"""')
    code = "\n".join(l.split("#")[0] for l in (parts[0] + parts[2]).splitlines())
    for n in ("PhotoPlate", "RealVersus", "ScanReconstruct", "MuseumLabel", "PageWrite", "StateSheet"):
        assert n not in code, "evidence_props hardcodes %s instead of parsing the call sites or the type" % n


def test_the_fixture_is_drawn_not_committed_and_is_deterministic(tmp_path, monkeypatch):
    """Two machines must measure the same pixels, and the repo must not carry a stand-in photograph that
    someone later mistakes for content."""
    pytest.importorskip("PIL")
    import hashlib
    monkeypatch.setattr(reg, "_REMOTION", str(tmp_path))
    rel = reg.ensure_fixture()
    p = tmp_path / "public" / rel
    first = hashlib.sha256(p.read_bytes()).hexdigest()
    p.unlink()
    reg.ensure_fixture()
    assert hashlib.sha256(p.read_bytes()).hexdigest() == first, "the fixture is not deterministic"


def test_the_measured_rows_describe_the_register_not_an_empty_box():
    """The regression this whole file exists for: if the sweep stops supplying the fixture, these rows go
    back to describing an empty box and the manifest lies about the library again.

    The EVIDENCE differs by register and so does the symptom. A photograph register handed nothing draws a
    frame that is nearly all ground — measured at 0.0-0.6% ink — so the ink floor catches it. A register whose
    evidence is a captured PAGE does not get that far: it throws, so it has no row at all and appears in
    `_failed`. Asserting the ink floor on it would be asserting the wrong thing about the right worry, and it
    would fail honestly — a real page is mostly its own flat ground, which is what `ink_median` measures the
    absence of."""
    data = json.load(open(reg.MANIFEST, encoding="utf-8"))
    listed = sorted(data["_fixture"]["registers"])
    assert listed == ["MuseumLabel", "PageWrite", "PhotoPlate", "RealVersus", "ScanReconstruct",
                      "StateSheet"], listed
    # THE QUESTION IS "EMPTY PLATE OR NOT", AND THE FILM'S INK FLOOR WAS ONLY EVER STANDING IN FOR IT. The
    # docstring above records the two populations: a register handed nothing measures 0.0-0.6%; reached with
    # its artefact, the photo registers measured 16.5-37.2%. A 12% film floor happened to fall in that gap.
    # The sixth register does not sit on the same side of it: StateSheet, correctly fed six stand-in cells,
    # measures 11.6% — twenty times an empty plate and still under a number chosen for a different question.
    # Asserting the film floor there fails a register that is demonstrably reached, which is the test crying
    # wolf; the bound below is the empty-plate ceiling the docstring itself measured, with a 5x margin.
    EMPTY_PLATE_CEILING = 0.03
    for n in listed:
        assert n not in data.get("_failed", []), (
            "%s failed to render, so the sweep is not reaching it with its fixture" % n)
        assert n in data["registers"], "%s has no measured row at all" % n
        if "blocks" in reg.evidence_props().get(n, {}):
            continue                    # a captured page: reaching it at all is the thing being checked
        assert data["registers"][n]["ink_median"] >= EMPTY_PLATE_CEILING, (
            "%s measures %.1f%% ink — an empty plate is 0.0-0.6%%, so the sweep is no longer reaching it "
            "with its fixture" % (n, data["registers"][n]["ink_median"] * 100))


def test_the_render_cache_is_keyed_on_everything_the_pixels_depend_on():
    """Keyed by name alone, the cache re-measured pre-fixture footage for exactly these four, and would
    serve product-DNA video to an editorial sweep while `_basis` announced editorial."""
    src = open(reg.__file__, encoding="utf-8").read()
    body = src.split("for i, n in enumerate(names, 1):")[1][:900]
    assert "hashlib.sha256" in body and "hashes.get(n" in body and "dna" in body and "ev.get(n)" in body, (
        "the mp4 cache key no longer covers source, dna and props")


def test_a_partial_sweep_merges_instead_of_dropping_or_overwriting(tmp_path, monkeypatch):
    """Both failure modes have happened here: --only once overwrote all 149 rows, and the fix for that
    stopped it writing at all, so a corrected register could never reach the record."""
    man = tmp_path / "m.json"
    man.write_text(json.dumps({
        "_dna": "product", "_floors": reg.floors(), "_failed": ["PhotoPlate (drew a hole)"],
        "_source": {"Old": "aaa", "PhotoPlate": "bbb"},
        "registers": {"Old": {"motion_p75": 1, "ink_median": 1, "luma_range": 1, "seconds": 5},
                      "PhotoPlate": {"motion_p75": 0, "ink_median": 0.006, "luma_range": 0, "seconds": 5}},
    }), encoding="utf-8")
    monkeypatch.setattr(reg, "MANIFEST", str(man))
    monkeypatch.setattr(reg, "durations", lambda: {"Old": 150, "PhotoPlate": 150})
    monkeypatch.setattr(reg, "render_one", lambda *a, **k: (True, [""]))
    monkeypatch.setattr(reg, "stills_from", lambda *a, **k: None)
    monkeypatch.setattr(reg, "footprint", lambda *a, **k: 0.45)
    monkeypatch.setattr(reg.fe, "measure", lambda *a, **k: {
        "motion_p75": 0.0009, "ink_median": 0.372, "luma_range": 0.131, "seconds": 5.8})
    reg.main(["--only=PhotoPlate"])
    out = json.loads(man.read_text(encoding="utf-8"))
    assert set(out["registers"]) == {"Old", "PhotoPlate"}, "the merge dropped rows it did not measure"
    assert out["registers"]["PhotoPlate"]["ink_median"] == 0.372, "the merge did not update what it measured"
    assert out["registers"]["Old"]["ink_median"] == 1, "the merge overwrote a row it never rendered"
    assert out["_failed"] == [], "a register that now renders is still recorded as a hole"


def test_a_partial_sweep_refuses_to_blend_two_design_systems(tmp_path, monkeypatch, capsys):
    """Rows are only comparable against rows rendered the same way; a blended table is worse than none."""
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"_dna": "editorial", "_floors": reg.floors(), "registers": {}}),
                   encoding="utf-8")
    monkeypatch.setattr(reg, "MANIFEST", str(man))
    monkeypatch.setattr(reg, "durations", lambda: {"PhotoPlate": 150})
    monkeypatch.setattr(reg, "render_one", lambda *a, **k: (True, [""]))
    monkeypatch.setattr(reg, "stills_from", lambda *a, **k: None)
    monkeypatch.setattr(reg, "footprint", lambda *a, **k: 0.45)
    monkeypatch.setattr(reg.fe, "measure", lambda *a, **k: {
        "motion_p75": 0.0009, "ink_median": 0.372, "luma_range": 0.131, "seconds": 5.8})
    assert reg.main(["--only=PhotoPlate", "--dna=product"]) == 1
    assert "REFUSING to merge" in capsys.readouterr().out
    assert json.loads(man.read_text(encoding="utf-8"))["registers"] == {}, "it merged anyway"
