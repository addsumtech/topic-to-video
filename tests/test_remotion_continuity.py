"""#11 continuity-spine backstops: a persistent hero mark (meta.hero_mark) rendered OUTSIDE the
TransitionSeries so it's CONSTANT across every scene — the through-line that keeps aggressive per-beat
design variety reading as ONE film. Verified from a render; here we lock the threading + the persistence."""
import os

import render_remotion as rr
import storyboard as sb

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*p):
    return open(os.path.join(_SKILL, *p), encoding="utf-8").read()


def _board(meta=None):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False, **(meta or {})})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "a"
    s["duration"] = 3.0
    s["stage"] = {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0], "title": "X"}]}
    s["shots"] = [{"type": "HERO", "target": "a"}]
    d["slides"] = [s]
    return d


def test_hero_mark_threads_from_meta(tmp_path):
    assert rr.build_props(_board({"hero_mark": "ACME"}), str(tmp_path))["heroMark"] == "ACME"


def test_hero_mark_is_none_when_unset(tmp_path):
    assert rr.build_props(_board(), str(tmp_path))["heroMark"] is None


def test_hero_mark_renders_persistently_outside_the_transitions():
    src = _src("remotion", "src", "Video.tsx")
    assert "HeroMark" in src and "heroMark" in src
    idx_ts = src.rindex("</TransitionSeries>")
    idx_hm = src.find("<HeroMark", idx_ts)
    assert idx_hm > idx_ts, "HeroMark must render as a SIBLING after the TransitionSeries (constant, not per-scene)"


def test_continuity_spine_is_documented():
    assert "continuity spine" in _src("references", "shot-archetypes.md").lower()
