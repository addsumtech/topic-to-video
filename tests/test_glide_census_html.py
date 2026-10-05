"""The HTML tier's type-glide census (keyframe_qa._glide_issue / _glide_census).

The shared base.css reveals already carry the baseline unlock (proven in test_html_baseline_unlock.py,
through the real render path). What that file does NOT cover is a page's OWN custom animation — a
`[data-ambient]` drift, or a per-page `<style>` @keyframes an author writes without knowing the unlock
exists — which can move text under an axis-aligned matrix with nobody checking it. This tests the
census that closes that gap, through the REAL CDP measurement path (keyframe_qa._glide_census), not a
re-derivation of the judgment (that part — judge_glide/glide_level — is reused unchanged from
text_safe_qa.py and already tested there).

Fixture: a `[data-ambient]` element whose own `<style>` @keyframes drifts it 40px over the whole scene
(well under 1px/frame — a crawl, not a jump) via a plain `transform:translateY`, with/without the
baseline unlock riding the same keyframe. 40px of crawl crosses far more than the 3-step error floor,
so the LOCKED version must be flagged and the UNLOCKED one must be clean — mirroring exactly what
test_html_baseline_unlock.py proved pixel-for-pixel for the shared reveal classes.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import keyframe_qa as kq
import scenes

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE_CSS = os.path.join(ROOT, "assets", "html", "base.css")
SEEK_JS = os.path.join(ROOT, "assets", "html", "seek.js")
UNLOCK = "matrix(1,.0009765625,0,1,0,0)"           # the literal every axis-aligned reveal carries

W, H, FPS, DUR = 1920, 1080, 30, 10.0               # 300 real frames; 40px over 300 -> ~0.13px/frame


def _chrome_present():
    return scenes._chrome_bin({}) is not None


needs_chrome = pytest.mark.skipif(not _chrome_present(), reason="no Chrome for HTML-tier integration test")

# the SAME 40px drift, with the per-keyframe transform either plain (snaps) or carrying the unlock on
# BOTH stops (an ambient loop, per base.css's own doctrine, never settles — it keeps the skew throughout)
_PAGE_TMPL = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="file://{base}">
<style>
  html,body{{width:{w}px;height:{h}px;margin:0;background:#111;overflow:hidden}}
  .stage{{width:{w}px;height:{h}px;position:relative}}
  #drift{{position:absolute;left:200px;top:400px;font:700 64px/1 Arial,Helvetica,sans-serif;color:#fff;
          animation:drift 1s linear forwards;animation-play-state:paused}}
  @keyframes drift{{from{{transform:translateY(0){unlock}}}to{{transform:translateY(40px){unlock}}}}}
</style></head>
<body>
<div class="stage"><div id="drift" data-ambient>Slow drifting caption text</div></div>
<script src="file://{seek}"></script>
</body></html>"""


def _build(path, unlocked):
    open(path, "w", encoding="utf-8").write(
        _PAGE_TMPL.format(base=BASE_CSS, seek=SEEK_JS, w=W, h=H,
                          unlock=(" " + UNLOCK) if unlocked else ""))


def _census(tmp_path, unlocked):
    page = os.path.join(str(tmp_path), "probe.html")
    _build(page, unlocked)
    chrome = kq._open_cdp({}, W, H)
    assert chrome, "no CDP Chrome available (needs_chrome should have skipped this test)"
    try:
        from urllib.parse import quote
        chrome.shot("file://" + quote(os.path.abspath(page)), os.path.join(str(tmp_path), "shot.png"))
        return kq._glide_issue(chrome, DUR, FPS)
    finally:
        chrome.close()


@needs_chrome
def test_locked_custom_drift_is_flagged():
    """A page's own @keyframes, with no unlock, crawling text 40px over 300 frames: a sub-pixel-per-
    frame drift that steps far past the 3-crossing error floor — must FAIL."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        issue, warn = _census(d, unlocked=False)
    assert issue, "a locked custom drift must be flagged as an error, not pass clean"
    assert "crawl" in issue and "animation" in issue


@needs_chrome
def test_same_drift_with_the_unlock_appended_is_clean():
    """The identical 40px drift, with the baseline-unlock skew riding both keyframe stops (the
    convention authors are told to use in base.css's own doctrine) — must be CLEAN: no issue, no
    warning. This is the regression a fix must not cry wolf on."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        issue, warn = _census(d, unlocked=True)
    assert issue is None and warn is None, (issue, warn)


@needs_chrome
def test_jev_html_pages_stay_clean():
    """The real jev-html film (no custom ambient/@keyframes authoring) must not false-positive."""
    film = os.path.join(ROOT, ".superpowers", "films", "jev-html")
    if not os.path.isdir(film):
        pytest.skip("jev-html fixture film not present in this checkout")
    rc = kq.run(film, ps=kq.DEFAULT_PS, as_json=False)
    assert rc == 0, "jev-html should stay clean through the glide census (rc=%d)" % rc
