"""The environment answers the object, and an object moves like a character (spec 2026-11-06 C2, C3). The user's
example: a 3D character hops across a Mac and the Dock icon under it rises to meet it. runtime/reacts.ts gives an
element its answer from the object's distance; runtime/character.ts gives a hop its anticipation, arc and landing."""
import pytest

import _tsprobe as tp

pytestmark = pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")
IMP = "import {react, contactTimes} from %s; import {hop, stagger} from %s;" % (tp.mod("reacts.ts"),
                                                                                 tp.mod("character.ts"))


def test_press_peaks_on_the_element_and_is_zero_beyond_one_width():
    o = tp.run_ts(IMP, "out.d = [0, 0.25, 0.5, 0.99, 1, 2].map((d) => react('press', d));")["d"]
    assert o[0]["dy"] > o[1]["dy"] > o[2]["dy"] > o[3]["dy"] >= 0
    assert o[4]["dy"] == 0 and o[5] == {"dy": 0, "scale": 1, "glow": 0}


def test_rise_lifts_and_grows_neighbours_less_than_the_element_under_it():
    o = tp.run_ts(IMP, "out.d = [0, 1, 3].map((d) => react('rise', d));")["d"]
    assert o[0]["dy"] < o[1]["dy"] <= 0 and o[0]["scale"] > o[1]["scale"] > 1 and o[2]["scale"] == 1


def test_light_glows_and_ripple_decays_with_time_since_contact():
    o = tp.run_ts(IMP, """out.l = react('light', 0); out.r0 = react('ripple', 0, {since: 0.05});
out.r1 = react('ripple', 0, {since: 0.6}); out.rn = react('ripple', 0, {since: -0.1});""")
    assert o["l"]["glow"] == 1
    assert abs(o["r0"]["scale"] - 1) > abs(o["r1"]["scale"] - 1) and o["rn"]["scale"] == 1


def test_reactions_are_pure_and_refuse_an_unknown_kind():
    o = tp.run_ts(IMP, "out.a = react('press', 0.3); out.b = react('press', 0.3);")
    assert o["a"] == o["b"]
    with pytest.raises(AssertionError, match="react"):
        tp.run_ts(IMP, "out.a = react('wobble' as any, 0);")


def test_contact_times_name_when_the_object_reaches_each_item():
    o = tp.run_ts(IMP, """const s = Array.from({length: 101}, (_, i) => ({t: i / 100, x: i / 100}));
out.c = contactTimes(s, [{x: 0.1, w: 0.1}, {x: 0.5, w: 0.1}, {x: 2, w: 0.1}]);""")["c"]
    assert abs(o[0] - 0.1) < 0.011 and abs(o[1] - 0.5) < 0.011 and o[2] is None


def test_hop_squashes_before_take_off_and_after_landing_and_keeps_its_volume():
    o = tp.run_ts(IMP, """out.pre = hop(0.12); out.mid = hop(0.5); out.land = hop(0.9); out.end = hop(1);
out.v = Array.from({length: 200}, (_, i) => { const h = hop(i / 199); return Math.abs(h.sx * h.sy - 1); });""")
    assert o["pre"]["sy"] < 1 and o["land"]["sy"] < 1
    assert o["mid"]["y"] < 0 and o["pre"]["y"] == 0 and o["end"] == {"y": 0, "sx": 1, "sy": 1}
    assert max(o["v"]) < 1e-6


def test_stagger_starts_later_parts_later_and_all_finish():
    o = tp.run_ts(IMP, "out.s = [0, 1, 2].map((i) => [stagger(i, 3, 0.15, 0.2), stagger(i, 3, 1, 0.2)]);")["s"]
    assert o[0][0] > o[1][0] > o[2][0] == 0 and all(e == 1 for _s, e in o)
