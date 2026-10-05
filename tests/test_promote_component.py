"""promote.py for an HTML component: refused unless delivered and checked; otherwise into
assets/html/components/, catalogued in references/html-components.md, and the film's pages follow it."""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_html_workshop import (JS, _film, _sub, needs_chrome, ws)  # noqa: E402,F401

from test_html_build_validate import _validate, no_runtime  # noqa: E402,F401


# ── promote.py: a component into assets/html/components/ ────────────────────────────────────────────────

@pytest.fixture
def lib(tmp_path, monkeypatch):
    import promote as pr
    d = tmp_path / "lib"
    monkeypatch.setattr(ws, "LIB_COMPONENTS", str(d / "components"))
    monkeypatch.setattr(pr, "HTML_COMPONENTS_DOC", str(d / "html-components.md"))
    return pr, d


def _deliver(out):
    time.sleep(0.02)
    open(os.path.join(out, "out.mp4"), "wb").write(b"\0")


def test_promoting_an_undelivered_film_is_refused(tmp_path, lib, no_runtime):
    pr, _d = lib
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(_film(tmp_path), "LabelGauge")
    assert any("no out.mp4" in p for p in e.value.problems)


def test_promoting_a_component_that_fails_its_check_is_refused(tmp_path, lib):
    pr, d = lib
    out = _film(tmp_path, js=_sub(JS, "    const attr =", "    const j = Math.random();\n    const attr ="))
    _deliver(out)
    with pytest.raises(pr.PromoteError) as e:
        pr.promote(out, "LabelGauge")
    assert any("Math.random" in p for p in e.value.problems)
    assert not os.path.exists(str(d / "components" / "LabelGauge.js"))


@needs_chrome
def test_a_component_moves_into_the_library_and_the_film_follows_it(tmp_path, lib):
    pr, d = lib
    out = _film(tmp_path)
    _deliver(out)
    plan = pr.promote(out, "LabelGauge", log=lambda *_: None)
    lib_js = os.path.join(str(d / "components"), "LabelGauge.js")
    assert os.path.isfile(lib_js) and os.path.isfile(lib_js[:-3] + ".css") and os.path.isfile(lib_js[:-3] + ".png")
    doc = open(str(d / "html-components.md")).read()
    assert "## LabelGauge — `<label-gauge>`" in doc and "`label`, `value`, `min`, `max`, `unit`" in doc
    page = open(os.path.join(out, "pages", "scene_01.html")).read()
    assert ws._url(lib_js) in page and "workshop/html" not in page
    assert plan["pages"] == ["pages/scene_01.html"]
    assert not os.path.exists(ws.component_paths(out, "LabelGauge")[0])
    board = json.load(open(os.path.join(out, "storyboard.json")))
    assert board["meta"]["build_list"][0]["promoted"] is True
    # the film still validates against the library copy, and the page still links it right
    assert ws.page_component_problems(out, "pages/scene_01.html") == []
    assert _validate(out) == []
