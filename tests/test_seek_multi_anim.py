"""An element with TWO animations keeps both delays (assets/html/seek.js).

seek.js read `animation-delay` with parseFloat — the FIRST value of the list — and wrote one value back, so every
animation on the element ran on the first one's delay. On a QR-code film (2026-11-04) a module that faded in and then
flipped 1.45 s later had flipped already at 0.47 s, before its mask's veil swept over it; a highlighted module and a
healed outline changed state on their entrance. Measured here in a real headless Chrome at seek.js's frozen time."""
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import scenes  # noqa: E402

ASSETS = os.path.join(_ROOT, "assets", "html")
needs_chrome = pytest.mark.skipif(scenes._chrome_bin({}) is None, reason="no Chrome")

_PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
@keyframes in {{ to {{ opacity: 1 }} }}
@keyframes shift {{ to {{ transform: translateX(100px) }} }}
#el {{ width: 50px; height: 50px; background: #fff; opacity: 0;
       animation: in .2s linear 0s forwards, shift .1s linear 1s forwards; animation-play-state: paused }}
</style></head><body>
<div id="host" data-cue-index="0" data-cue="word"><div id="el"></div></div>
<script src="file://{seek}"></script></body></html>"""


@pytest.fixture(scope="module")
def chrome():
    import _cdp
    c = _cdp.Chrome(scenes._chrome_bin({}), 800, 600)
    yield c
    c.close()


def _state(chrome, tmp_path, query):
    page = tmp_path / "p.html"
    page.write_text(_PAGE.format(seek=os.path.join(ASSETS, "seek.js")), encoding="utf-8")
    chrome.shot("file://%s?%s" % (page, query), str(tmp_path / "shot.jpg"))
    r = chrome._cmd("Runtime.evaluate", {"expression": "JSON.stringify([getComputedStyle(document.getElementById('el')).opacity,"
                                         "getComputedStyle(document.getElementById('el')).transform])", "returnByValue": True},
                    chrome.sid)
    return json.loads(r["result"]["result"]["value"])


@needs_chrome
def test_the_second_animation_keeps_its_own_delay(chrome, tmp_path):
    # cue 0 at 1.0 s in a 4 s scene; p = 0.375 → T = 1.5 s, half a second after the cue: faded in, not shifted yet
    op, tf = _state(chrome, tmp_path, "p=0.375&dur=4&cues=1.0")
    assert float(op) == pytest.approx(1.0), op
    assert tf in ("none", "matrix(1, 0, 0, 1, 0, 0)"), "the 1 s animation fired on the first one's delay: %s" % tf
    # p = 0.75 → T = 3.0 s, 2 s after the cue: both have run
    op, tf = _state(chrome, tmp_path, "p=0.75&dur=4&cues=1.0")
    assert tf == "matrix(1, 0, 0, 1, 100, 0)", tf
