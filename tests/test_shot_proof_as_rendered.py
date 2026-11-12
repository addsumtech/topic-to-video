"""shot_proof judges what the register is HANDED and what can reach the frame (topic-to-video promo, 2026-11-12):
a LivingMap beat's `{map, add, focus}` is expanded by render_remotion before React sees it, and a developer's error
message is not copy on the frame."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import shot_proof as sp  # noqa: E402


def test_a_living_map_beat_is_checked_with_the_props_it_renders_with():
    board = {"meta": {"maps": {"studio": {"nodes": [{"id": "research", "label": "research"},
                                                    {"id": "script", "label": "script"}],
                                          "edges": [["research", "script"]]}}},
             "slides": [{"shot": "LivingMap", "narration": "It researches, then writes.",
                         "shot_props": {"map": "studio", "add": ["research", "script"]}}]}
    errors, _w = sp.static_checks(board)
    assert not [e for e in errors if "is not a prop of this register" in e], errors


def test_error_messages_are_not_copy_but_on_frame_literals_still_are():
    src = ("const p = requireEvidence('X', 'src', s, 'the real photograph the beat turns into a diagram');\n"
           "if (!ok) throw new Error(`a real photograph says ${here}`);\n"
           "return <div>{'the real photograph'}</div>;\n")
    out = sp._strip_diagnostics(src)
    assert "turns into a diagram" not in out and "says" not in out
    assert "'the real photograph'" in out, "a literal drawn on the frame is still read"
