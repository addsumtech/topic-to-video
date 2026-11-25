"""screenrec_cues: a recorded tutorial's clicks and keystrokes, on the film seconds the edit plays them."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import screenrec_cues as sc  # noqa: E402

REC = {"actions": [
    {"i": 0, "kind": "click", "label": "prep", "t": 0.5, "t_end": 0.5},
    {"i": 1, "kind": "click", "label": "Title", "t": 2.0, "t_end": 2.0, "clicks": 2},
    {"i": 2, "kind": "type", "label": "type", "text": "ab c", "t": 2.0, "t_end": 2.4},
    {"i": 3, "kind": "scroll", "label": "up", "t": 3.0, "t_end": 3.2},
    {"i": 4, "kind": "key", "label": "return", "t": 4.0, "t_end": 4.0},
    {"i": 5, "kind": "drag", "label": "move", "t": 5.0, "t_end": 6.5},
    {"i": 6, "kind": "click", "label": "late", "t": 9.0, "t_end": 9.0}]}


def test_each_visible_action_has_its_sound_and_nothing_else_does():
    ev = sc.events(REC, until=8.0, skip={0})
    what = [(round(r, 2), cue) for r, cue, _, _ in ev]
    assert what == [(1.76, "click"), (1.92, "click"),                         # a double-click: two clicks
                    (2.0, "key"), (2.1, "key"), (2.2, "key"), (2.3, "key"),   # four characters, the space quieter
                    (3.95, "key"),                                            # Return (no sound for the scroll)
                    (5.5, "click"), (6.45, "click")], what                    # a drag's press and release
    gains = {round(r, 2): g for r, _, g, _ in ev}
    assert gains[2.2] < gains[2.1] < gains[3.95]


def test_a_cue_lands_where_the_edit_plays_it_and_a_held_stretch_is_silent():
    # film 0-2 s plays recording 0-2 s, then holds at 2.0 until film 5 s, then plays on
    ts = [i / 10 for i in range(0, 90)]
    rs = [t if t <= 2 else (2.0 if t <= 5 else 2.0 + (t - 5)) for t in ts]
    cues = sc.place([(1.5, "click", 0.5, "a"), (2.5, "key", 0.3, "b"), (30.0, "key", 0.3, "never shown")], ts, rs)
    assert [(c["t"], c["what"]) for c in cues] == [(1.5, "a"), (5.5, "b")]
