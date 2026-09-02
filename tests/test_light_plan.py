"""The light arc must follow the ARGUMENT, and must never overrule a director.

`light_plan.py` exists because a capability nothing reaches is indistinguishable from one that was never
built: the runtime could re-ground every beat and the whole library still measured a median luminance range
of 0.013 against Apple's 0.270. But a pass that simply rotates colours every beat would move the same number
while meaning nothing — so what is pinned here is that the exposure changes where the CLAIM changes.
"""
import json
import os

import pytest

import light_plan as lp

FOLLOWERS = {"Alpha", "Beta", "Gamma"}


def _b(i, rel, energy="medium", shot="Alpha", **extra):
    d = {"index": i, "relation": rel, "energy": energy, "shot": shot}
    d.update(extra)
    return d


def _grounds(rows):
    return [r.get("ground") for r in rows]


def test_light_moves_where_the_claim_moves_and_holds_where_it_does_not():
    rows = lp.plan([_b(0, "new-topic"), _b(1, "continuation"), _b(2, "continuation"),
                    _b(3, "new-topic"), _b(4, "continuation"),
                    _b(5, "new-topic")], FOLLOWERS)
    g = _grounds(rows)
    assert g[0] == g[1] == g[2], "the exposure moved inside one section: %r" % g
    assert g[3] != g[2], "a new claim did not get a new exposure: %r" % g
    assert g[4] == g[3], "the exposure moved on a continuation: %r" % g
    assert g[5] != g[3], "two consecutive sections share a ground: %r" % g


def test_a_payoff_lifts_and_a_close_comes_home():
    rows = lp.plan([_b(0, "new-topic"), _b(1, "new-topic"), _b(2, "payoff"), _b(3, "close")], FOLLOWERS)
    g = _grounds(rows)
    assert g[2] != g[1], "a payoff did not lift out of its section: %r" % g
    assert g[3] == lp.NATIVE, "the film did not come home on its close: %r" % g


def test_energy_peak_counts_as_a_payoff():
    rows = lp.plan([_b(0, "new-topic"), _b(1, "new-topic"), _b(2, "continuation", energy="peak")], FOLLOWERS)
    assert _grounds(rows)[2] == lp.CHROMA_A


def test_a_beat_the_director_authored_is_left_alone():
    """It fills silence; it never overrules. Both fields count as authored."""
    rows = lp.plan([_b(0, "new-topic", ground="gallery"), _b(1, "new-topic", key="light")], FOLLOWERS)
    assert all("ground" not in r for r in rows), rows
    assert all("already authored" in r["skip"] for r in rows), rows


def test_a_register_that_cannot_follow_a_ground_is_skipped_and_counted():
    """Stamping one puts a dark subtitle over black pixels: the register paints its own ground and the
    caption pick believes the declaration."""
    rows = lp.plan([_b(0, "new-topic", shot="Alpha"), _b(1, "new-topic", shot="NotAFollower")], FOLLOWERS)
    assert "ground" in rows[0]
    assert "does not follow" in rows[1]["skip"]


def test_the_follower_set_is_read_from_the_runtime():
    names = lp.ground_followers()
    assert len(names) > 50, "only %d registers parsed — the set looks truncated" % len(names)
    src = open(lp._SHOTLUMA, encoding="utf-8").read()
    for n in list(names)[:5]:
        assert "'%s'" % n in src


def test_an_absent_follower_set_fails_loud_instead_of_skipping_every_beat(tmp_path, monkeypatch):
    """An empty set would silently skip every beat and report a lightless film as 'nothing to do'."""
    empty = tmp_path / "shotLuma.ts"
    empty.write_text("export const SOMETHING_ELSE = 1;\n", encoding="utf-8")
    monkeypatch.setattr(lp, "_SHOTLUMA", str(empty))
    with pytest.raises(RuntimeError, match="GROUND_FOLLOWS_MEASURED"):
        lp.ground_followers()


def test_apply_writes_only_the_planned_beats(tmp_path):
    board = {"slides": [_b(0, "new-topic"), _b(1, "new-topic", shot="NotAFollower"), _b(2, "continuation")]}
    rows = lp.plan(board["slides"], FOLLOWERS)
    n = lp.apply(board, rows)
    assert n == 2
    assert "ground" in board["slides"][0] and "ground" not in board["slides"][1]


def test_a_film_of_one_section_is_reported_as_not_an_arc(capsys, tmp_path):
    d = tmp_path / "film"
    d.mkdir()
    (d / "storyboard.json").write_text(json.dumps(
        {"slides": [_b(i, "continuation") for i in range(6)]}), encoding="utf-8")
    lp.main([str(d)])
    out = capsys.readouterr().out
    assert "not an arc" in out, out
