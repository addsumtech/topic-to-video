"""SHARED-ELEMENT / MATCH-CUT transition (audit top-3 #3).

A cross-scene seam can carry a `match_cut` anchor held/morphed across the cut so a reel of shots reads as one
continuous space. It was long declared impossible ("-c copy can't see the neighbour") — but that limit came
from the ffmpeg image tier; the Remotion TransitionSeries renders both scenes co-existing during the overlap.
These guard the coercion (_clean_match), the wiring (_transitions attaches match, forces a seam on a hard
cut), validate's early checks, and the TS presentation (source-guard)."""
import os

import pytest
import validate
import storyboard as sb
import render_remotion as rr

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "src")


# ── _clean_match coercion ─────────────────────────────────────────────────────────────────────────────
def test_clean_match_coerces_a_valid_spec():
    m = rr._clean_match({"shape": "bar", "from": [0.5, 0.5, 0.3, 0.1], "to": [0.2, 0.3, 0.2, 0.1], "color": "#fff"}, "s1")
    assert m["shape"] == "bar" and m["from"] == [0.5, 0.5, 0.3, 0.1] and m["color"] == "#fff"


def test_clean_match_rejects_bad_shape_and_arity():
    with pytest.raises(RuntimeError):
        rr._clean_match({"shape": "blob", "from": [0, 0, 0, 0], "to": [0, 0, 0, 0]}, "s1")
    with pytest.raises(RuntimeError):
        rr._clean_match({"from": [0, 0, 0], "to": [0, 0, 0, 0]}, "s1")     # `from` wrong length


# ── _transitions wiring ───────────────────────────────────────────────────────────────────────────────
def test_transitions_attaches_match_on_a_seam():
    scenes = [{"index": 1, "fadeOutFrames": 12,
               "match_cut": {"shape": "box", "from": [0.5, 0.5, 0.2, 0.2], "to": [0.3, 0.4, 0.15, 0.15]}},
              {"index": 2, "fadeInFrames": 0}]
    rr._transitions(scenes, {"audio_master": False}, 30)
    t = scenes[0]["transitionToNext"]
    assert t and t.get("match") and t["match"]["shape"] == "box"


def test_match_cut_forces_a_seam_on_a_hard_cut():
    # no fade edges at all, but a match-cut needs an overlap to carry the anchor — _transitions creates one.
    scenes = [{"index": 1, "match_cut": {"shape": "dot", "from": [0.5, 0.5, 0.1, 0.1], "to": [0.5, 0.5, 0.1, 0.1]}},
              {"index": 2}]
    rr._transitions(scenes, {"audio_master": False}, 30)
    assert scenes[0]["transitionToNext"] is not None and scenes[0]["transitionToNext"].get("match")


# ── validate early checks ─────────────────────────────────────────────────────────────────────────────
def _board(tmp, slides):
    data = sb.new_storyboard(None)
    data["slides"] = slides
    sb.save(data, os.path.join(str(tmp), "storyboard.json"))
    return data


def _cine(idx, tmp, **over):
    aud = os.path.join("audio", f"{idx:02d}.mp3")
    os.makedirs(os.path.join(str(tmp), "audio"), exist_ok=True)
    open(os.path.join(str(tmp), aud), "wb").write(b"\x00")
    s = sb.new_scene(idx, "title", {"title": "Hi"}, narration="A short line.")
    s["audio"] = aud
    s["duration"] = 4.0
    s.update(over)
    return s


def test_match_cut_on_last_scene_warns(tmp_path):
    s0 = _cine(0, tmp_path)
    s1 = _cine(1, tmp_path, match_cut={"shape": "box", "from": [0.5, 0.5, 0.2, 0.2], "to": [0.5, 0.5, 0.2, 0.2]})
    r = validate.evaluate(_board(tmp_path, [s0, s1]), str(tmp_path))
    assert any("LAST scene" in w for w in r["warnings"]), r["warnings"]


def test_match_cut_bad_shape_errors(tmp_path):
    s0 = _cine(0, tmp_path, match_cut={"shape": "blob", "from": [0.5, 0.5, 0.2, 0.2], "to": [0.5, 0.5, 0.2, 0.2]})
    s1 = _cine(1, tmp_path)
    r = validate.evaluate(_board(tmp_path, [s0, s1]), str(tmp_path))
    assert any("must be box|bar|line|dot" in e for e in r["errors"]), r["errors"]


def test_match_cut_pixel_coords_warn(tmp_path):
    s0 = _cine(0, tmp_path, match_cut={"shape": "box", "from": [960, 540, 400, 200], "to": [0.5, 0.5, 0.2, 0.2]})
    s1 = _cine(1, tmp_path)
    r = validate.evaluate(_board(tmp_path, [s0, s1]), str(tmp_path))
    assert any("looks like PIXELS" in w for w in r["warnings"]), r["warnings"]


def test_valid_match_cut_is_clean(tmp_path):
    s0 = _cine(0, tmp_path, match_cut={"shape": "bar", "from": [0.5, 0.6, 0.3, 0.08], "to": [0.4, 0.4, 0.2, 0.08]})
    s1 = _cine(1, tmp_path)
    r = validate.evaluate(_board(tmp_path, [s0, s1]), str(tmp_path))
    assert not any("match_cut" in e for e in r["errors"]), r["errors"]


# ── TS presentation source-guard ──────────────────────────────────────────────────────────────────────
def test_shared_element_presentation_is_wired():
    pres = open(os.path.join(_SRC, "transitions", "sharedElement.tsx"), encoding="utf-8").read()
    assert "TransitionPresentation" in pres and "presentationProgress" in pres, "presentation API not used"
    assert "MatchSpec" in pres and "presentationDirection === 'entering'" in pres, "anchor not drawn on the entering side"
    video = open(os.path.join(_SRC, "Video.tsx"), encoding="utf-8").read()
    assert "sharedElement" in video and "t.match" in video, "Video.tsx does not route a match seam to the shared-element presentation"
