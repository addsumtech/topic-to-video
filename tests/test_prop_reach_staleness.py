"""A measurement is stale when ANY of its inputs moved — and `prop_reach` was only watching one of them.

Each row of `remotion/prop_reach.json` is the result of rendering a register twice with two prop sets. That
is TWO inputs: the register's own source, and the props it was fed. Only the source was hashed.

The props are not a constant. They come from `cjk_type_qa.cjk_props`, a fixture GENERATOR whose reader of a
register's declaration was blind in five separate ways, all found on 2026-09-15. When those were fixed, 24 of
166 registers began receiving props they had never been given — `AcceptanceStamp` had been handed none of its
four, `MadeOf` one of five. Every one of those reach numbers became meaningless, and `--check` reported the
manifest CLEAN, because not a single `.tsx` had changed.

The bias runs one way, which is what made it dangerous rather than merely wrong: a register given fewer words
to change can only appear to change LESS. So the corruption landed entirely on the FLOOR of the table — the
half people read — and a sentence derived from it was published in `LIBRARY.md` as a fact about the library.

The guard hashes the FED PROPS, not the generator's source. That is exact and free: computing the props takes
no render. Hashing the module would mark all 161 rows stale on any edit anywhere in `cjk_type_qa`, which is
the over-broad dep-hash `open-work.md` D1 accepts for `register_energy` only because there it cannot be made
exact.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import prop_reach as pr          # noqa: E402


def test_a_row_records_the_props_it_was_measured_with():
    src = open(pr.__file__, encoding="utf-8").read()
    assert '"_props": {n: props_hash(n) for n in rows}' in src, (
        "the sweep no longer records which props each row was measured with")
    assert '"_props"' in src.split("def stale(", 1)[1].split("\ndef ", 1)[0], (
        "the staleness check no longer READS the fixture hash — recording it and not comparing it is the "
        "same silence with an extra field")


def test_the_hash_is_of_the_props_themselves_not_of_the_generator():
    """Two registers with different props must hash differently, and the SAME register must hash the same
    twice — a hash that moved on its own would mark the whole manifest stale on every run and teach people
    to pass --no-strict."""
    a1, a2 = pr.props_hash("MagazineSpread"), pr.props_hash("MagazineSpread")
    b = pr.props_hash("TermTree")
    assert a1 == a2, "the fixture hash is not deterministic"
    assert a1 != b, "two registers with different props hash the same"


def test_a_changed_fixture_marks_the_row_stale_even_though_the_register_did_not_move(monkeypatch):
    """The exact case that went unseen: the `.tsx` is untouched and the props are different."""
    name = "TermTree"
    data = {"registers": {name: {"reach": 0.4}},
            "_source": {name: pr.re_mod.source_hash(name)},
            "_props": {name: pr.props_hash(name)}}
    assert not [r for r in pr.stale(data) if r[0] == name], (
        "a row whose inputs are both unchanged is reported stale: %r" % (pr.stale(data),))

    real = pr.cq.cjk_props
    monkeypatch.setattr(pr.cq, "cjk_props",
                        lambda n, off=0: ({"items": ["完全不同的一组词"]}, []) if n == name else real(n, off))
    why = dict(pr.stale(data)).get(name)
    assert why and "fixture" in why, (
        "the register's source is untouched and it is being fed different props — the row is a measurement "
        "of inputs that no longer exist, and the check said: %r" % (why,))


def test_a_manifest_written_before_the_fixture_was_hashed_is_not_trusted():
    """Silence must not read as agreement. A row with no `_props` entry was measured with props nobody
    recorded, so it cannot be confirmed — and the committed manifest is exactly that."""
    data = {"registers": {"TermTree": {"reach": 0.4}},
            "_source": {"TermTree": pr.re_mod.source_hash("TermTree")}}
    why = dict(pr.stale(data)).get("TermTree")
    assert why and "before the FIXTURE was hashed" in why, why


def test_the_committed_manifest_is_currently_stale_and_says_so():
    """Not a regression test — a RECORD. Every row in the repo right now was measured through the blind
    reader, and `LIBRARY.md` carries a warning saying so. When `prop_reach.py` is re-run this test changes
    from documenting a known-bad state to asserting the guard still bites; it must not be deleted quietly,
    because a green `--check` over numbers nobody re-measured is the whole failure."""
    path = os.path.join(_ROOT, "remotion", "prop_reach.json")
    if not os.path.exists(path):
        pytest.skip("no manifest committed")
    data = json.load(open(path, encoding="utf-8"))
    bad = pr.stale(data)
    lib = open(os.path.join(_ROOT, "remotion", "LIBRARY.md"), encoding="utf-8").read()
    if bad:
        assert "MEASURED WITH A BROKEN INSTRUMENT" in lib, (
            "%d row(s) are stale and LIBRARY.md quotes their numbers with no warning" % len(bad))
    else:
        assert "MEASURED WITH A BROKEN INSTRUMENT" not in lib, (
            "the sweep has been re-run and the numbers are sound — remove the warning from LIBRARY.md")
