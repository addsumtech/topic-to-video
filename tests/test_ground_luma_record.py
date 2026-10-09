"""`record_spot` is the one write path a SPOT CHECK has into the committed `_ground_luma.json`.

`measure_ground_luma.py --only A,B --emit` classifies A and B and prints them, but never writes this file —
by design, a bare `--only` write once silently replaced a 134-shot table with a 1-shot measurement. So a
register re-measured alone, without a full library sweep, could confirm its own classification and
`stale()` would go on calling it unmeasured forever: the committed table never moved. `record_spot` is the
narrower door — it merges only the rows it was asked about, so a spot check leaves the table exactly as
confirmable as a full sweep does.

No renders here: `measure` is replaced with a stub that returns a controlled luminance, so `classify`,
`token_lums` and the real `_source_hashes` (over two harmless, cheap library registers) run unstubbed."""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import measure_ground_luma as gl  # noqa: E402

# Two real, cheap library registers (source_hash reads their .tsx from disk; no render). TermTree stands in
# for a name the table already knows about (classified); TermTable for one it has never seen at all.
KNOWN, NEW = "TermTree", "TermTable"


@pytest.fixture
def spot(tmp_path, monkeypatch):
    """A committed-shaped `_ground_luma.json` in a temp `remotion/` — record_spot's only write target — and
    `_fixture_props` short-circuited so no evidence fixture is built for a test that never really renders."""
    data = {
        "table": {KNOWN: "dark", "Unrelated1": "light"},
        "unclassified": ["Unrelated2"],
        "failed": {"Unrelated3": "boom"},
        "universe": 4,                                    # TermTree + Unrelated1 + Unrelated2 + Unrelated3
        "_source": {KNOWN: "deadbeef00000000", "Unrelated1": "abc0000000000000"},
    }
    path = tmp_path / "_ground_luma.json"
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    monkeypatch.setattr(gl, "_REMOTION", str(tmp_path))
    monkeypatch.setattr(gl, "_fixture_props", lambda: {})
    # the light probe a `bg` row is asked under: these stand-ins FOLLOW the film's ground, so `bg` stays `bg`
    monkeypatch.setattr(gl, "measure_light", lambda shot, td, fixtures=None: (0.9, "#f2f2f2", None))
    monkeypatch.setattr(gl, "light_key_y", lambda: 0.35)
    return path, data


def _stub(table):
    """A `measure(shot, td, fixtures)` stand-in: `table` maps a shot name to (lum, err)."""
    def measure(shot, td, fixtures=None):
        return table[shot]
    return measure


def test_record_spot_updates_only_the_named_entries(spot, monkeypatch):
    path, before = spot
    lums = gl.token_lums()
    # KNOWN measures as a DIFFERENT token than its stale "dark" row, proving the merge writes the fresh
    # classification and not just a refreshed hash; NEW measures as unclassified.
    monkeypatch.setattr(gl, "measure", _stub({KNOWN: (lums["bg"], None), NEW: (0.5, None)}))
    assert gl.classify(0.5, lums)[0] is None, "0.5 must classify as nothing for this test to prove anything"

    out = gl.record_spot([KNOWN, NEW])

    assert out == {KNOWN: "bg", NEW: None}
    after = json.loads(path.read_text(encoding="utf-8"))
    # the two named entries moved as their measurement says
    assert after["table"][KNOWN] == "bg"
    assert NEW not in after["table"]
    assert sorted(after["unclassified"]) == sorted(["Unrelated2", NEW])
    real_hash = gl._source_hashes([KNOWN])[KNOWN]
    assert after["_source"][KNOWN] == real_hash and real_hash != before["_source"][KNOWN]
    assert NEW not in after["_source"], "an unclassified name is not in `table`, so it gets no source hash"
    # every OTHER entry is untouched, byte for byte
    assert after["table"]["Unrelated1"] == "light"
    assert after["_source"]["Unrelated1"] == "abc0000000000000"
    assert after["failed"] == {"Unrelated3": "boom"}
    # universe: KNOWN was already counted (it was in `table`); NEW was in none of table/unclassified/failed
    assert after["universe"] == before["universe"] + 1


def test_record_spot_prunes_the_source_hash_when_a_name_turns_unclassified(spot, monkeypatch):
    """KNOWN starts classified, with a `_source` entry left over from that earlier measurement. Measured
    unclassified this time, its row leaves `table` — and the hash that described its old classification must
    leave `_source` with it, not linger describing a row that no longer exists (`stale()` only ever reads
    `_source[shot]` for `shot in table`, so a leftover entry backs nothing and is real debt, not a value)."""
    path, before = spot
    assert before["_source"].get(KNOWN), "the fixture must start KNOWN with a _source entry for this to prove anything"
    lums = gl.token_lums()
    monkeypatch.setattr(gl, "measure", _stub({KNOWN: (0.5, None)}))
    assert gl.classify(0.5, lums)[0] is None, "0.5 must classify as nothing for this test to prove anything"

    out = gl.record_spot([KNOWN])

    assert out == {KNOWN: None}
    after = json.loads(path.read_text(encoding="utf-8"))
    assert KNOWN not in after["table"] and KNOWN in after["unclassified"]
    assert KNOWN not in after["_source"], "a name that just left `table` must not keep a source hash for it"


def test_record_spot_leaves_stale_empty_for_the_named_shot(spot, monkeypatch):
    path, _before = spot
    lums = gl.token_lums()
    monkeypatch.setattr(gl, "measure", _stub({KNOWN: (lums["bg"], None), NEW: (0.5, None)}))
    gl.record_spot([KNOWN, NEW])
    after = json.loads(path.read_text(encoding="utf-8"))
    bad = [shot for shot, _why in gl.stale(after) if shot in (KNOWN, NEW)]
    assert not bad, "record_spot must leave the shots it just measured confirmable: %r" % bad


def test_record_spot_refuses_a_failed_measurement_and_writes_nothing(spot, monkeypatch):
    path, _before = spot
    raw_before = path.read_text(encoding="utf-8")
    # KNOWN measures fine; a later name in the same call fails — nothing may be written for either.
    monkeypatch.setattr(gl, "measure", _stub({KNOWN: (0.1, None), "BadOne": (None, "could not render")}))

    with pytest.raises(SystemExit) as exc:
        gl.record_spot([KNOWN, "BadOne"])

    assert "BadOne" in str(exc.value) and "could not render" in str(exc.value), str(exc.value)
    assert path.read_text(encoding="utf-8") == raw_before, "a refused spot check must not write a partial table"


def test_record_spot_records_the_night_a_dark_world_register_keeps(spot, monkeypatch):
    """A register that is `bg` under the dark probe but stays dark under the LIGHT one is recorded as the colour
    it keeps — the row a light film's caption ink and seam guard then read — not as the film's paper."""
    path, _before = spot
    lums = gl.token_lums()
    monkeypatch.setattr(gl, "measure", _stub({KNOWN: (lums["bg"], None)}))
    monkeypatch.setattr(gl, "measure_light", lambda shot, td, fixtures=None: (0.005, "#0a101c", None))
    assert gl.record_spot([KNOWN]) == {KNOWN: "#0a101c"}
    assert json.loads(path.read_text(encoding="utf-8"))["table"][KNOWN] == "#0a101c"


def test_a_failed_light_probe_refuses_the_spot_check(spot, monkeypatch):
    path, _before = spot
    raw_before = path.read_text(encoding="utf-8")
    lums = gl.token_lums()
    monkeypatch.setattr(gl, "measure", _stub({KNOWN: (lums["bg"], None)}))
    monkeypatch.setattr(gl, "measure_light", lambda shot, td, fixtures=None: (None, None, "could not render"))
    with pytest.raises(SystemExit) as exc:
        gl.record_spot([KNOWN])
    assert "light probe" in str(exc.value)
    assert path.read_text(encoding="utf-8") == raw_before
