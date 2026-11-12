"""motion_events_qa — sharp changes OFF the planned cuts, listed for the reviewer's eye (WorkBuddy, 2026-11-11)."""
import os
import sys

import pytest

np = pytest.importorskip("numpy")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import critic_ledger as cl            # noqa: E402
import motion_events_qa as me         # noqa: E402

H, W = 72, 160


def _film(n=120):
    """A slow, smooth pan of a textured card: the motion a film is made of, which must list nothing."""
    x = np.arange(W * 3, dtype=np.float32)
    y = np.arange(H, dtype=np.float32)[:, None]
    tex = 128 + 60 * np.sin(x / 23.0) * np.cos(y / 17.0) + 40 * np.sin(x / 7.0 + y / 11.0)
    return np.stack([tex[:, i: i + W] for i in range(n)]).astype(np.float32)


def test_smooth_motion_and_a_planned_cut_list_nothing():
    F = _film()
    F[60:] = 255 - F[60:]                                   # a hard cut at frame 60, on the plan
    plan = {f: "seam" for f in range(58, 63)}
    assert me.scan(F, plan) == []


def test_a_framing_that_jumps_between_tabs_is_listed_as_wander():
    # beat 11's tail: six frames alternating between framings, ending near where they began
    F = _film()
    for k, f in enumerate(range(80, 86)):
        F[f] = np.roll(F[f], (k % 2) * 9 + (k % 3) * 5, axis=1)
    kinds = {e["kind"] for e in me.scan(F, {})}
    assert "WANDER" in kinds


def test_a_change_that_stays_off_the_plan_is_listed_and_on_the_plan_is_not():
    # beat 10's light switching off: one sharp change that stays
    F = _film()
    F[70:] = np.clip(F[70:] * 0.5 + 120, 0, 255)
    assert [e["kind"] for e in me.scan(F, {})] == ["JUMP"]
    assert me.scan(F, {f: "coverage" for f in range(67, 72)}) == []


def test_it_is_an_advisory_delivery_gate():
    rows = [g for g in cl.DELIVERY_GATES["remotion"] if g[1] == "motion_events_qa.py"]
    assert len(rows) == 1 and rows[0][4] is False


def _screen_film(n=120, die_at=None, fade=False):
    """A textured screen (a third of the picture) on a dark room, the next beat's seam at frame 100."""
    F = np.full((n, H, W), 20.0, np.float32)
    scr = _film(n)[:, 10:40, 40:120]
    F[:, 10:40, 40:120] = scr
    if die_at is not None:
        if fade:
            for f in range(die_at - 12, n):
                F[f, 10:40, 40:120] = 12 + (scr[f] - 12) * max(0.0, 1 - (f - die_at + 12) / 12.0)
        else:
            F[die_at:, 10:40, 40:120] = 12.0
    return F


def test_a_screen_that_goes_black_before_its_cut_is_listed_as_blank():
    """The promo's six screens: the clip's span ended under the beat (2026-11-12) — inside the seam pad, so only
    BLANK sees it. A screen still playing at the seam lists nothing; a designed gradual fade lists nothing."""
    segs = [(0, 99), (100, 119)]
    ev = me.blanks(_screen_film(die_at=98), segs)
    assert [(e["kind"], e["frame"]) for e in ev] == [("BLANK", 98)] and ev[0]["cells"] >= me.BLANK_CELLS
    assert me.blanks(_screen_film(), segs) == []
    assert me.blanks(_screen_film(die_at=98, fade=True), segs) == []


def test_a_blank_that_starts_inside_the_seam_is_the_transition_not_the_beat():
    assert me.blanks(_screen_film(die_at=102), [(0, 99), (100, 119)]) == []
