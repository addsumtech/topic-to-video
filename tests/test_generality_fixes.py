"""Fixes from the 2026-10-30 generality validation (two films off the Agent HUD path: a 9:16 remotion teach film and
a 1:1 HTML film). Each test is the defect as the run met it."""
import os

import jitter_qa as jq
import keyframe_qa as kq
import imagefetch as F
import storyboard as sb
import validate


def test_keyframe_qa_judges_a_square_film_on_its_own_canvas():
    # a 1:1 film's pages were captured and judged on 1920x1080 while render.py drew them at 1080x1080
    assert kq.canvas({"aspect": "1:1", "width": 1080, "height": 1080}) == (1080, 1080)
    assert kq.canvas({"aspect": "4:5", "width": 1080, "height": 1350}) == (1080, 1350)
    assert kq.canvas({"aspect": "9:16"}) == (1080, 1920)
    assert kq.canvas({}) == (1920, 1080)


def _board(tmp_path, stage):
    aud = os.path.join("audio", "00.mp3")
    os.makedirs(os.path.join(str(tmp_path), "audio"), exist_ok=True)
    open(os.path.join(str(tmp_path), aud), "wb").write(b"\x00")
    s = sb.new_scene(0, "title", {"title": "Hello"}, narration="A short line.")
    s.update(audio=aud, duration=4.0, stage=stage)
    data = sb.new_storyboard({"renderer": "local"})
    data["slides"] = [s]
    sb.save(data, os.path.join(str(tmp_path), "storyboard.json"))
    return data


def test_the_plan_learning_stage_is_not_the_removed_stage_tier(tmp_path):
    # storyboard.py --from-plan writes the content plan's learning stage ("hook") on every slide of every tier;
    # validate ERRORed on it as the removed generic-scene `stage`, on every beat of an HTML film
    r = validate.evaluate(_board(tmp_path, "hook"), str(tmp_path))
    assert not any("carries ['stage']" in e for e in r["errors"]), r["errors"]


def test_the_removed_stage_object_is_still_refused(tmp_path):
    r = validate.evaluate(_board(tmp_path, {"elements": [{"kind": "text"}]}), str(tmp_path))
    assert any("carries ['stage']" in e for e in r["errors"]), r["errors"]


def test_the_author_is_the_name_not_the_template_box_after_it():
    raw = ('<a href="//commons.wikimedia.org/wiki/User:Fred_the_Oyster">Fred the Oyster</a><br>'
           '<div lang="en" class="plainlinks"><table><tr><td><a href="https://validator.w3.org/"><img alt="W3C"></a>'
           '</td><td>The source code of this SVG is valid.</td></tr></table></div>')
    assert F._artist(raw) == "Fred the Oyster"
    assert F._strip_html("Richard Bartz &amp; Hubert Seibring") == "Richard Bartz & Hubert Seibring"


def _search(monkeypatch, ii):
    fake = {"query": {"pages": {"1": {"title": "File:x", "imageinfo": [dict(ii, extmetadata={
        "LicenseShortName": {"value": "CC0"}, "Artist": {"value": "<a>N</a>"}})]}}}}
    monkeypatch.setattr(F, "_http_json", lambda params, timeout=30: fake)
    return F.search("x", width=2400)[0]


def test_a_small_original_is_not_reported_at_the_requested_width(monkeypatch):
    # Commons answered thumbwidth 2400 for a 417x277 original, and it passed min_width=800 into a film
    got = _search(monkeypatch, {"thumburl": "u", "url": "u", "mime": "image/jpeg", "width": 417, "height": 277,
                                "thumbwidth": 2400, "thumbheight": 1594})
    assert (got["width"], got["height"]) == (417, 277)


def test_a_vector_keeps_its_rendered_width(monkeypatch):
    got = _search(monkeypatch, {"thumburl": "u.png", "url": "u.svg", "mime": "image/svg+xml", "width": 512,
                                "height": 512, "thumbwidth": 2400, "thumbheight": 2400})
    assert got["width"] == 2400
