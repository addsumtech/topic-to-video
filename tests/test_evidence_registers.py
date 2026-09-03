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
    assert set(ev) == {"PhotoPlate", "RealVersus", "ScanReconstruct", "MuseumLabel"}, ev
    # a paired register guards ONE prop; both halves must be filled or half the frame is still the hole
    assert set(ev["RealVersus"]) == {"srcLeft", "srcRight"}, ev["RealVersus"]
    # the names may appear in prose (this history is worth keeping); what must not exist is a name in the
    # CODE that builds the list
    import inspect
    body = inspect.getsource(reg.evidence_props)
    parts = body.split('"""')
    code = "\n".join(l.split("#")[0] for l in (parts[0] + parts[2]).splitlines())
    for n in ("PhotoPlate", "RealVersus", "ScanReconstruct", "MuseumLabel"):
        assert n not in code, "evidence_props hardcodes %s instead of parsing the call sites" % n


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
    """The regression this whole file exists for. If these fall back under the delivery floor, the sweep has
    stopped supplying the fixture and the manifest is lying about the library again."""
    data = json.load(open(reg.MANIFEST, encoding="utf-8"))
    assert sorted(data["_fixture"]["registers"]) == ["MuseumLabel", "PhotoPlate", "RealVersus",
                                                     "ScanReconstruct"]
    floor = data["_floors"]["ink_median"]
    for n in data["_fixture"]["registers"]:
        assert data["registers"][n]["ink_median"] >= floor, (
            "%s is back under the ink floor — it was measured as an empty plate" % n)


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
