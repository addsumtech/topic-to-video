"""#12 type_attitude backstops: the native giant kinetic DISPLAY-type element (the manifesto-monolith
vehicle) — full-strength statement type staged as an object, with an entrance `attitude`
(rise / tracking-in / blur-in). Verified from a render; here we lock the threading + the wiring."""
import os

import render_remotion as rr
import storyboard as sb
import validate as v

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


def _db(el):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "a"
    s["duration"] = 5.0
    s["stage"] = {"elements": [{"id": "g", "kind": "grid", "position": [0, 0, -1]},
                               {**el, "id": "d", "position": [0, 0, 0]}]}
    s["shots"] = [{"type": "HERO", "target": "d"}]
    d["slides"] = [s]
    return d


def test_display_threads_text_and_attitude(tmp_path):
    d = [e for e in rr.build_props(_db({"kind": "display", "text": "Ship faster.", "attitude": "tracking-in"}),
                                   str(tmp_path))["scenes"][0]["stage"]["elements"] if e["id"] == "d"][0]
    assert d["kind"] == "display" and d["text"] == "Ship faster." and d["attitude"] == "tracking-in"


def test_display_branch_and_all_attitudes_present():
    src = _src("remotion", "src", "stage", "elements.tsx")
    assert "kind === 'display'" in src
    for a in ("'rise'", "'tracking-in'", "'blur-in'"):
        assert a in src, "attitude %s must be implemented" % a
    assert "fontSize: 200" in src, "giant full-strength display type (not the 9% hero watermark)"


def test_display_is_a_known_element_kind():
    assert "display" in v._ELEM_KINDS


def test_catalog_wires_manifesto_to_native_display():
    assert "native `display`" in _src("references", "shot-archetypes.md")
