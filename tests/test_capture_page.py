"""Baking a real page into a texture the film can use — and refusing to bake a picture of nothing.

The register this feeds (`PageWrite`) exists because a drawn window cannot make the one claim a document
shot is for: that this is the actual artefact. That premise dies the moment the capture quietly writes
something else, and the two ways it does are both silent — Chrome renders its OWN error page for a bad
target (which screenshots perfectly well and probes clean), and a page with no measurable blocks gives a
texture that can be panned across but never animated.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import capture_page                            # noqa: E402

_PAGE = os.path.join(_ROOT, "remotion", "fixtures", "demo-report.html")
_LAYOUT = os.path.join(_ROOT, "remotion", "fixtures", "demo-report.layout.json")


def _chrome():
    try:
        import scenes
        b = scenes._chrome_bin({})
        return b if b and os.path.exists(b) else None
    except Exception:
        return None


def test_a_target_that_is_not_a_page_is_refused_before_chrome_ever_sees_it():
    """The failure that matters most, because its output looks like a success: Chrome renders its own
    ERR_FILE_NOT_FOUND page, the screenshot is a perfectly good PNG, and the film is built on it."""
    with pytest.raises(FileNotFoundError):
        capture_page._url_for("/no/such/page.html")
    assert capture_page._url_for("https://example.com/x").startswith("https://")
    assert capture_page._url_for(_PAGE).startswith("file://")


def test_the_shipped_demo_capture_still_describes_its_own_page():
    """The committed texture is a fixture the energy sweep and the register's own preview both film. A layout
    whose boxes no longer sit inside the page it claims is a texture and a description of a different page."""
    lay = json.load(open(_LAYOUT, encoding="utf-8"))
    assert lay["blocks"], "a capture with no boxes can be panned across and never animated"
    assert lay.get("bg"), "the reveal mask is painted in the page's own ground; without it the wipe is a grey bar"
    for b in lay["blocks"]:
        assert 0 <= b["x"] and b["x"] + b["w"] <= lay["pageW"] + 2, b
        assert 0 <= b["y"] and b["y"] + b["h"] <= lay["pageH"] + 2, b
    png = os.path.join(os.path.dirname(_LAYOUT), "demo-report.png")
    assert os.path.getsize(png) > 5000, "the texture is missing or empty"


def test_the_demo_capture_is_tracked_not_left_in_the_disposable_staging_dir():
    """`remotion/public/` is git-ignored — it is the per-film staging directory, wiped and refilled by every
    render. A fixture committed there is one a fresh clone does not have, and it fails as a permanent
    "PageWrite RENDER FAILED" that reads as a broken register rather than as a missing file."""
    import subprocess
    r = subprocess.run(["git", "check-ignore", "-q", _LAYOUT], cwd=_ROOT)
    assert r.returncode != 0, "the demo capture is sitting in an ignored directory"


@pytest.mark.skipif(not _chrome(), reason="needs a Chrome binary")
def test_capturing_the_demo_page_reproduces_the_committed_layout():
    """The pixels and the boxes come from ONE page load, which is the whole reason this is a capture and not
    a hand-marked overlay. Re-running it on the same page must land on the same geometry, or the fixture in
    the repo describes a render nobody can reproduce."""
    with tempfile.TemporaryDirectory() as td:
        got = capture_page.capture(_PAGE, "probe", out_dir=td)
        want = json.load(open(_LAYOUT, encoding="utf-8"))
        assert got["pageW"] == want["pageW"] and got["pageH"] == want["pageH"]
        assert len(got["blocks"]) == len(want["blocks"])
        for a, b in zip(got["blocks"], want["blocks"]):
            assert abs(a["x"] - b["x"]) <= 2 and abs(a["y"] - b["y"]) <= 2, (a, b)
        assert os.path.exists(os.path.join(td, "probe.png"))
