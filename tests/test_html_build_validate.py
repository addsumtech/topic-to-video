"""validate.py's HTML build rules: components and the build list agree, every custom tag a page uses is
defined, and a board with none of it takes the old path. Shares tests/test_html_workshop.py's fixture film."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_html_workshop import (_film, ws)  # noqa: E402,F401


# ── validate.py: build-list rules and unknown tags ───────────────────────────────────────────────────────

def _validate(out):
    import validate
    board = json.load(open(os.path.join(out, "storyboard.json")))
    errors, warnings, skips = [], [], []
    validate._check_html_build(board["meta"], board["slides"], errors, warnings, out, skips=skips)
    return errors


@pytest.fixture
def no_runtime(monkeypatch):
    """validate's own rules, without re-running the Chrome checks tested above."""
    monkeypatch.setattr(ws, "component_runtime", lambda *a, **k: {"problems": [], "demo": {}})


def test_a_board_without_components_takes_the_old_path(tmp_path, monkeypatch):
    out = tmp_path / "film"
    (out / "pages").mkdir(parents=True)
    (out / "pages" / "scene_01.html").write_text("<div class='stage'><div class='title'>x</div></div>")
    board = {"meta": {}, "slides": [{"index": 1, "type": "html", "props": {"html": "pages/scene_01.html"}}]}
    (out / "storyboard.json").write_text(json.dumps(board))

    def boom(*a, **k):
        raise AssertionError("a board without components must not reach the component checks")
    monkeypatch.setattr(ws, "html_problems", boom)
    assert _validate(str(out)) == []


def test_a_correct_component_film_validates_clean(tmp_path, no_runtime):
    assert _validate(_film(tmp_path)) == []


def test_a_component_not_on_the_build_list_is_an_error(tmp_path, no_runtime):
    assert any("not on meta.build_list" in e for e in _validate(_film(tmp_path, entry=False)))


def test_an_entry_whose_beats_disagree_with_the_pages_is_an_error(tmp_path, no_runtime):
    out = _film(tmp_path)
    board = json.load(open(os.path.join(out, "storyboard.json")))
    board["meta"]["build_list"][0]["beats"] = [2]
    json.dump(board, open(os.path.join(out, "storyboard.json"), "w"))
    assert any("says beats [2]" in e for e in _validate(out))


def test_an_entry_no_page_draws_is_an_error(tmp_path, no_runtime):
    out = _film(tmp_path)
    open(os.path.join(out, "pages", "scene_01.html"), "w").write("<div class='stage'></div>")
    assert any("drawn by no page" in e for e in _validate(out))


def test_an_entry_with_the_wrong_slot_or_no_means_is_an_error(tmp_path, no_runtime):
    out = _film(tmp_path)
    board = json.load(open(os.path.join(out, "storyboard.json")))
    board["meta"]["build_list"][0].update({"slot": "ObjectStage", "means": ""})
    json.dump(board, open(os.path.join(out, "storyboard.json"), "w"))
    errs = _validate(out)
    assert any('`slot` is "page"' in e for e in errs) and any("`means` is empty" in e for e in errs)


def test_an_unknown_custom_tag_is_an_error_even_without_a_workshop(tmp_path):
    out = tmp_path / "film"
    (out / "pages").mkdir(parents=True)
    (out / "pages" / "scene_01.html").write_text("<div class='stage'><espresso-puck packed='1'></espresso-puck></div>")
    board = {"meta": {}, "slides": [{"index": 1, "type": "html", "props": {"html": "pages/scene_01.html"}}]}
    (out / "storyboard.json").write_text(json.dumps(board))
    assert any("<espresso-puck>, which neither" in e for e in _validate(str(out)))
