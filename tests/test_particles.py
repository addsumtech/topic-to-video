"""Particles taken FROM a word (or any drawn mark), that dissolve and re-form as another (runtime/particles).

WHY. The peer library boils a line of text into grain and condenses the cloud into a larger word (grain-dissolve),
bursts a formation into a smoke ring (card-flock-tumble) and scatters gold dust over a finale. This library's one
particle register flies ~140 dots into a fixed checkmark. The core here samples points from a mask, makes two sets
the same size, pairs them so the flow reads left to right, and places every particle on its way from one to the
other — starting exactly on the first mark and landing exactly on the second.
"""
import pytest

import _tsprobe as tp

pytestmark = pytest.mark.skipif(not tp.available(), reason="needs node + remotion/node_modules")


def _run(body):
    return tp.run_ts("import * as pt from %s;" % tp.mod("particles.ts"), body)


SQUARE = ("const W = 40, H = 20; const a = new Array(W * H).fill(0);"
          "for (let y = 5; y < 15; y++) for (let x = 5; x < 15; x++) a[y * W + x] = 255;")


def test_points_come_only_from_inked_pixels():
    out = _run(SQUARE + "out.p = pt.sampleMask(a, W, H, 2);")
    pts = out["p"]
    assert pts and all(5 <= p["x"] < 15 and 5 <= p["y"] < 15 for p in pts)
    assert len(pts) == 25, "a 10x10 inked square sampled every 2 px gives 5x5 points"


def test_two_sets_are_made_the_same_size_deterministically():
    out = _run("const a = Array.from({length: 7}, (_, i) => ({x: i, y: 0}));"
               "out.up = pt.fitCount(a, 12, 3); out.up2 = pt.fitCount(a, 12, 3); out.down = pt.fitCount(a, 4, 3);")
    assert len(out["up"]) == 12 and out["up"] == out["up2"]
    assert len(out["down"]) == 4
    assert all(p in [{"x": i, "y": 0} for i in range(7)] for p in out["down"]), "subsampling keeps real points"


def test_a_particle_starts_on_the_first_mark_and_lands_on_the_second():
    out = _run("const a = [{x: 0, y: 0}, {x: 10, y: 0}], b = [{x: 100, y: 50}, {x: 120, y: 50}];"
               "const pr = pt.pair(a, b);"
               "out.s = pr.map((q: any, i: number) => pt.particleAt(q, i, 0, {scatter: 80}));"
               "out.e = pr.map((q: any, i: number) => pt.particleAt(q, i, 1, {scatter: 80}));"
               "out.m = pr.map((q: any, i: number) => pt.particleAt(q, i, 0.5, {scatter: 80}));")
    assert sorted((p["x"], p["y"]) for p in out["s"]) == [(0, 0), (10, 0)]
    assert sorted((p["x"], p["y"]) for p in out["e"]) == [(100, 50), (120, 50)]
    mid_straight = [(50, 25), (65, 25)]
    assert any(abs(p["x"] - m[0]) + abs(p["y"] - m[1]) > 5 for p, m in zip(sorted(out["m"], key=lambda p: p["x"]), mid_straight)), \
        "on the way the particles scatter off the straight line"


def test_pairing_keeps_the_left_of_one_word_flowing_to_the_left_of_the_next():
    out = _run("const a = [{x: 300, y: 0}, {x: 0, y: 0}, {x: 150, y: 0}], b = [{x: 900, y: 0}, {x: 500, y: 0}, {x: 700, y: 0}];"
               "out.p = pt.pair(a, b).map((q: any) => [q.a.x, q.b.x]);")
    assert sorted(out["p"]) == [[0, 500], [150, 700], [300, 900]]


def test_a_burst_leaves_from_the_mark_and_fades():
    out = _run("const a = [{x: 100, y: 100}, {x: 110, y: 100}];"
               "out.s = a.map((q: any, i: number) => pt.burstAt(q, i, 0, {cx: 105, cy: 100, reach: 300}));"
               "out.e = a.map((q: any, i: number) => pt.burstAt(q, i, 1, {cx: 105, cy: 100, reach: 300}));")
    assert [(p["x"], p["y"], p["alpha"]) for p in out["s"]] == [(100, 100, 1), (110, 100, 1)]
    assert all(p["alpha"] == 0 for p in out["e"])
    assert all(abs(e["x"] - 105) > abs(s["x"] - 105) for s, e in zip(out["s"], out["e"])), "they fly outward"
