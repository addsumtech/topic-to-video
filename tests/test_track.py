"""runtime/track.ts — where the film's through-object is at a moment of its beat (spec 2026-11-06 C1)."""
import pytest

import _tsprobe as tp

pytestmark = pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")


def test_track_at_starts_on_in_ends_on_out_and_eases_between():
    out = tp.run_ts("import {trackAt} from %s;" % tp.mod("track.ts"), """
const tr = {object: 'cap', in: {x: 0.2, y: 0.5, scale: 1, rot: 0}, out: {x: 0.6, y: 0.3, scale: 2, rot: 90}};
out.a = trackAt(tr, 0); out.b = trackAt(tr, 1); out.m = trackAt(tr, 0.5); out.q = trackAt(tr, 0.1);
out.lo = trackAt(tr, -1); out.hi = trackAt(tr, 3);
""")
    assert out["a"] == {"x": 0.2, "y": 0.5, "scale": 1, "rot": 0}
    assert out["b"] == {"x": 0.6, "y": 0.3, "scale": 2, "rot": 90}
    assert abs(out["m"]["x"] - 0.4) < 1e-9                       # an ease symmetric about the middle
    assert out["q"]["x"] - 0.2 < 0.1 * 0.4                       # eased: slower than linear at the start
    assert out["lo"] == out["a"] and out["hi"] == out["b"]       # clamped outside the beat


def test_a_malformed_track_is_refused_loudly():
    with pytest.raises(AssertionError, match="track"):
        tp.run_ts("import {trackAt} from %s;" % tp.mod("track.ts"),
                  "out.a = trackAt({object: 'cap', in: {x: 0.2}, out: {x: 0.4, y: 0.1, scale: 1, rot: 0}} as any, 0.5);")
