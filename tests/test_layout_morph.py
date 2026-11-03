"""The same items, re-arranged — and the arrangement is the argument (runtime/layoutMorph).

WHY. The peer library re-frames one set of tiles between a grid, a mosaic with one hero slot and a diagonal cascade
(mosaic-reframe), demotes a headline into a section label as content grows under it (title-demote-to-label), and
turns table rows into cards mid-flight (canvas-materialize). This library could carry ONE element across a cut and
had nothing that moved a set of things from one arrangement to another inside a beat. The layouts here are
deterministic boxes inside the content zone; the morph between two of them is per item, staggered, on a slight
arc, and lands exactly on the target.
"""
import pytest

import _tsprobe as tp

pytestmark = pytest.mark.skipif(not tp.available(), reason="needs node + remotion/node_modules")

BOX = "{x: 100, y: 100, w: 1600, h: 700}"


def _run(body):
    return tp.run_ts("import * as lm from %s;" % tp.mod("layoutMorph.ts"), body)


def _inside(r, box=(100, 100, 1600, 700)):
    x, y, w, h = box
    return r["x"] >= x - 1e-6 and r["y"] >= y - 1e-6 and r["x"] + r["w"] <= x + w + 1e-6 and r["y"] + r["h"] <= y + h + 1e-6


def _overlap(a, b):
    return not (a["x"] + a["w"] <= b["x"] + 1e-6 or b["x"] + b["w"] <= a["x"] + 1e-6 or
                a["y"] + a["h"] <= b["y"] + 1e-6 or b["y"] + b["h"] <= a["y"] + 1e-6)


@pytest.mark.parametrize("n", [1, 2, 5, 7, 12])
def test_every_arrangement_fits_the_box_and_no_two_items_overlap(n):
    out = _run("const B = %s; out.g = lm.grid(%d, B); out.h = lm.featured(%d, B, 0); out.r = lm.rank([%s], B);"
               "out.p = lm.groups([%s], B);" % (BOX, n, n, ",".join(str(i * 7 % 5) for i in range(n)),
                                                   ",".join("'%s'" % "abc"[i % 3] for i in range(n))))
    for k in ("g", "h", "r", "p"):
        rs = out[k]
        assert len(rs) == n
        assert all(_inside(r) for r in rs), (k, rs)
        assert not any(_overlap(a, b) for i, a in enumerate(rs) for b in rs[i + 1:]), k


def test_the_hero_is_the_largest_and_a_ranking_orders_by_value():
    out = _run("const B = %s; out.h = lm.featured(6, B, 3); out.r = lm.rank([2, 9, 5], B); out.s = lm.shares([2, 9, 5]);" % BOX)
    areas = [r["w"] * r["h"] for r in out["h"]]
    assert areas.index(max(areas)) == 3
    r = out["r"]
    assert r[1]["y"] < r[2]["y"] < r[0]["y"], "the largest value sits first (top)"
    assert r[0]["w"] == r[1]["w"] == r[2]["w"], "every row is full width: its label needs the room whatever its value"
    assert out["s"] == pytest.approx([2 / 9, 1, 5 / 9]), "the bar inside a row is its value's share of the largest"


def test_a_morph_starts_and_lands_exactly_and_staggers_on_the_way():
    out = _run("const B = %s; const a = lm.grid(4, B), b = lm.featured(4, B, 2);"
               "out.a = a; out.b = b; out.m0 = lm.morph(a, b, 0); out.m1 = lm.morph(a, b, 1);"
               "out.mid = lm.morph(a, b, 0.3, {stagger: 0.5});" % BOX)
    for m, ref in ((out["m0"], out["a"]), (out["m1"], out["b"])):
        for got, want in zip(m, ref):
            for k in ("x", "y", "w", "h"):
                assert got[k] == pytest.approx(want[k], abs=1e-6)
    prog = [abs(m["x"] - a["x"]) + abs(m["y"] - a["y"]) for m, a in zip(out["mid"], out["a"])]
    assert len(set(round(p, 3) for p in prog)) > 1, "a staggered morph moves its items at different times"


def test_a_layout_asked_to_hold_more_than_it_can_draw_refuses():
    out = _run("try { lm.grid(40, {x: 0, y: 0, w: 400, h: 200}); out.e = null; }"
               " catch (e: any) { out.e = String(e.message); }")
    assert out["e"] and "too small" in out["e"]


def test_a_portrait_hero_takes_the_top_not_a_strip():
    out = _run("out.h = lm.featured(5, {x: 0, y: 0, w: 900, h: 1400}, 2);")
    h = out["h"][2]
    assert h["w"] == pytest.approx(900) and h["y"] == 0, "the hero spans the width at the top of a tall box"
    assert all(r["y"] >= h["h"] for i, r in enumerate(out["h"]) if i != 2)
