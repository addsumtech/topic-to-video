"""A beat built of the film's OTHER beats — the cold open's flash of what is coming, the finale's gathering of what
was seen (runtime/teaser, ColdOpen, Callback).

WHY. The peer library opens a trailer on three 9-frame cuts and a beat of black (trailer-grammar-moves) and ends on
the film's elements assembling around the wordmark (outro-group-photo-launch). This tier's opening and closing beats
could only be registers drawing their own content. Film.tsx now hands such a beat the film's other beats, each on
its own ground and frozen once it has landed; validate refuses references that cannot mean anything.
"""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import validate as v  # noqa: E402
import _tsprobe as tp  # noqa: E402


def _board(*shots_and_beats):
    return [{"shot": sh, "shot_props": ({"beats": b} if b is not None else {})} for sh, b in shots_and_beats]


def test_a_cold_open_names_beats_still_to_come_and_a_callback_beats_already_seen():
    ok = _board(("ColdOpen", [2, 3]), ("EdStat", None), ("WordDust", None), ("Callback", [2, 3, 1]))
    assert v.teaser_problems(ok[0], ok) == []
    probs = v.teaser_problems(ok[3], ok)
    assert any("ColdOpen" in p for p in probs), "a callback of the cold open shows a beat built of beats"
    bad = _board(("EdStat", None), ("ColdOpen", [1, 2]), ("WordDust", None))
    assert any("comes before it" in p for p in v.teaser_problems(bad[1], bad))
    assert any("cannot show itself" in p for p in v.teaser_problems(bad[1], bad))
    late = _board(("Callback", [2, 3, 4]), ("EdStat", None), ("EdStat", None), ("EdStat", None))
    assert any("comes after it" in p for p in v.teaser_problems(late[0], late))
    assert v.teaser_problems({"shot": "ColdOpen", "shot_props": {}}, [{"shot": "ColdOpen"}])


@pytest.mark.skipif(not tp.available(), reason="needs node + remotion/node_modules")
def test_a_teaser_is_frozen_at_the_frame_where_its_beat_has_landed():
    out = tp.run_ts("import {frameAtT, SETTLED_T} from %s; import {ENTRY_T, SEAM_FRAMES} from %s;"
                    % (tp.mod("teaser.tsx"), tp.mod("motion.ts")),
                    "const d = 150; const f = frameAtT(SETTLED_T, d); const pad = Math.min(SEAM_FRAMES, Math.floor((d - 1) / 3));"
                    "const span = d - 1 - 2 * pad; out.t = ENTRY_T + (1 - ENTRY_T) * Math.min(1, Math.max(0, (f - pad) / span));"
                    "out.want = SETTLED_T; out.inTail = f > d - 1 - pad;")
    assert abs(out["t"] - out["want"]) < 0.01, "frameAtT is the inverse of useT's own map"
    assert not out["inTail"], "frozen before the held tail, where the outgoing seam runs"


def test_a_promo_opens_cold_on_its_liveliest_beats_and_a_long_film_ends_on_a_callback():
    import shot_director as sd
    sl = [{"index": i, "shot": "EdStat" if i % 2 else "WordDust", "shot_fit": {"verdict": "unjudged"}} for i in range(8)]
    sl[-1]["shot"] = "EdStat"
    plan = {"beats": [{"energy": e, "relation": r} for e, r in zip(
        ["medium", "low", "peak", "high", "low", "high", "medium", "low"],
        ["new-topic", "continuation", "payoff", "continuation", "continuation", "new-topic", "continuation", "close"])]}
    data = {"meta": {"purpose": "launch", "title": "Ship it"}, "slides": sl}
    notes = sd.bookends(data, plan)
    assert sl[0]["shot"] == "ColdOpen" and sl[0]["shot_props"] == {"beats": [3, 4, 6], "title": "Ship it"}
    assert sl[-1]["shot"] == "Callback" and 3 <= len(sl[-1]["shot_props"]["beats"]) <= 4
    assert all(b < 8 for b in sl[-1]["shot_props"]["beats"]) and 1 not in sl[-1]["shot_props"]["beats"]
    assert len(notes) == 2 and all("bookend" in s["shot_fit"] for s in (sl[0], sl[-1]))
    import validate as v
    for s in (sl[0], sl[-1]):
        assert v.teaser_problems(s, sl) == [], v.teaser_problems(s, sl)


def test_an_explainer_does_not_open_cold_and_a_routed_or_short_film_is_left_alone():
    import shot_director as sd
    sl = [{"index": i, "shot": "EdStat", "shot_fit": {"verdict": "unjudged"}} for i in range(8)]
    sd.bookends({"meta": {"purpose": "teach"}, "slides": sl}, None)
    assert sl[0]["shot"] == "EdStat", "an explainer opens on its first idea, not a trailer"
    routed = [{"index": i, "shot": "EdStat", "shot_fit": {"verdict": "fit"}} for i in range(8)]
    sd.bookends({"meta": {"purpose": "launch"}, "slides": routed}, None)
    assert {s["shot"] for s in routed} == {"EdStat"}, "a routed beat is the director's"
    short = [{"index": i, "shot": "EdStat", "shot_fit": {"verdict": "unjudged"}} for i in range(4)]
    assert sd.bookends({"meta": {"purpose": "launch"}, "slides": short}, None) == []


def test_a_bookend_is_exempt_from_the_design_floor_only_at_its_end_of_the_film():
    """ColdOpen and Callback draw only the film's own beats — nothing to adapt — so as the first or last beat they are
    the open/close card (exempt, like CinematicTitle); anywhere else they are judged like any register."""
    import validate as v
    sl = [{"shot": "ColdOpen", "shot_props": {"beats": [2]}}, {"shot": "EdStat"},
          {"shot": "Callback", "shot_props": {"beats": [2]}}, {"shot": "Callback", "shot_props": {"beats": [2]}}]
    routes = {n: r for n, r, _ in v.design_routes({}, sl, None)}
    assert routes[1] == "exempt" and routes[4] == "exempt"
    assert routes[3] != "exempt", "a Callback in the middle of a film is not its closing card"
