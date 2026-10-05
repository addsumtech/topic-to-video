"""keyframe_qa and its type-glide census on a page that holds a component — no rule changes: its parts are light
DOM inside .stage, so the caption-band geometry and the glide census see them like any page element."""
import json
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_html_workshop import (CSS, _film, _page, needs_chrome, ws)  # noqa: E402,F401


# ── keyframe_qa and the glide census see a component's parts (no rule changes there) ─────────────────────

def _positioned_film(tmp_path, css=CSS, top=200, duration=None):
    style = "position:absolute;left:560px;top:%dpx;width:800px;height:440px" % top
    out = _film(tmp_path, css=css)
    jsp, cssp = ws.component_paths(out, "LabelGauge")
    body = ('<label-gauge label="Brew pressure" value="9" min="0" max="12" unit="bar" style="%s"></label-gauge>'
            % style)
    open(os.path.join(out, "pages", "scene_01.html"), "w").write(_page(ws._url(jsp), ws._url(cssp), body=body))
    if duration:
        board = json.load(open(os.path.join(out, "storyboard.json")))
        board["slides"][0]["duration"] = duration
        json.dump(board, open(os.path.join(out, "storyboard.json"), "w"))
    return out


def _keyframe_report(out, capsys):
    import keyframe_qa as kq
    rc = kq.run(out, ps=[0.5, 1.0], as_json=True)
    text = capsys.readouterr().out
    rep = json.loads(text[text.index("{"):])
    return rc, [i for r in rep["report"] for i in r.get("issues") or []]


@needs_chrome
def test_keyframe_qa_catches_a_component_part_reaching_into_the_caption_band(tmp_path, capsys):
    # the host box ends at y=840, above the 16:9 band (880); one of its PARTS hangs below it, into the band
    css = CSS + "\nlabel-gauge .label-gauge__label{position:absolute;left:0;top:105%}\n"
    rc, issues = _keyframe_report(_positioned_film(tmp_path, css=css, top=400), capsys)
    assert rc != 0 and any("caption zone" in i for i in issues), issues


@needs_chrome
def test_keyframe_qa_passes_the_same_component_kept_in_its_box(tmp_path, capsys):
    rc, issues = _keyframe_report(_positioned_film(tmp_path, top=400), capsys)
    assert rc == 0 and issues == [], issues


def _glide(tmp_path, css):
    import keyframe_qa as kq
    out = _positioned_film(tmp_path, css=css)
    chrome = kq._open_cdp({}, 1920, 1080)
    assert chrome
    try:
        chrome.shot(ws._url(os.path.join(out, "pages", "scene_01.html")), str(tmp_path / "g.jpg"))
        return kq._glide_issue(chrome, 10.0, 30)
    finally:
        chrome.close()


@needs_chrome
def test_the_glide_census_flags_a_component_s_moving_text_without_the_unlock(tmp_path):
    locked = CSS.replace(" matrix(1,.0009765625,0,1,0,0)", "")
    assert locked != CSS
    issue, warn = _glide(tmp_path, locked)
    assert issue and "crawl" in issue, (issue, warn)


@needs_chrome
def test_the_glide_census_passes_the_same_component_with_the_unlock(tmp_path):
    issue, warn = _glide(tmp_path, CSS)
    assert issue is None and warn is None, (issue, warn)
