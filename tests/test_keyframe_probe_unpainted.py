"""keyframe_qa's content box counts only what paints.

The box probe (`_OVERFLOW_JS`) took every `.stage *` element with a non-zero rect and its own opacity above 0. Three
kinds of element have a rect and paint nothing: the geometry inside an SVG `<clipPath>`/`<mask>`/`<defs>` (a clip
region, not ink), an element under `visibility:hidden`, and an element whose ANCESTOR is at opacity 0 (its own opacity
is 1). A QR-code film's component (2026-11-04) kept a clipPath sized past its card and a collapsed tear piece, and
the caption-zone gate reported content reaching the subtitle band where nothing was drawn."""
import os
import sys
import tempfile
from urllib.parse import quote

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import keyframe_qa as kq  # noqa: E402
import scenes  # noqa: E402

needs_chrome = pytest.mark.skipif(scenes._chrome_bin({}) is None, reason="no Chrome for the html-tier probe")

_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>html,body{{margin:0;width:1920px;height:1080px;background:#111;color:#eee}}
.stage{{position:absolute;inset:0}}.card{{position:absolute;left:200px;top:100px;width:400px;height:400px;background:#eee}}
</style></head><body><div class="stage"><div class="card">a card</div>{extra}</div></body></html>"""

_UNPAINTED = {
    "clipPath": ('<svg style="position:absolute;left:0;top:0" width="1920" height="1080"><defs></defs>'
                 '<clipPath id="c"><rect x="100" y="80" width="600" height="990"/></clipPath>'
                 '<rect x="200" y="100" width="400" height="400" clip-path="url(#c)" fill="#eee"/></svg>'),
    "mask": ('<svg style="position:absolute;left:0;top:0" width="1920" height="1080">'
             '<mask id="m"><rect x="100" y="80" width="600" height="990" fill="#fff"/></mask>'
             '<rect x="200" y="100" width="400" height="400" mask="url(#m)" fill="#eee"/></svg>'),
    "clipped ink": ('<svg style="position:absolute;left:0;top:0" width="1920" height="1080" viewBox="0 0 960 540">'
                    '<clipPath id="k"><rect x="100" y="50" width="200" height="200"/></clipPath>'
                    '<g clip-path="url(#k)"><rect x="100" y="50" width="200" height="480" fill="#eee"/></g></svg>'),
    "visibility": '<div style="position:absolute;left:200px;top:900px;width:300px;height:150px;visibility:hidden">x</div>',
    "faded parent": ('<div style="opacity:0"><div style="position:absolute;left:200px;top:900px;width:300px;'
                     'height:150px;background:#eee">gone</div></div>'),
}


def _cbot(extra):
    with tempfile.TemporaryDirectory() as d:
        page = os.path.join(d, "p.html")
        open(page, "w", encoding="utf-8").write(_PAGE.format(extra=extra))
        chrome = kq._open_cdp({}, 1920, 1080)
        assert chrome, "no CDP Chrome"
        try:
            chrome.shot("file://" + quote(page), os.path.join(d, "s.png"))
            return kq._dom_probe(chrome)["cbot"]
        finally:
            chrome.close()


@needs_chrome
@pytest.mark.parametrize("kind", sorted(_UNPAINTED))
def test_an_unpainted_box_is_not_content(kind):
    assert _cbot(_UNPAINTED[kind]) == 500, kind


@needs_chrome
def test_a_painted_box_low_on_the_page_still_counts():
    low = '<div style="position:absolute;left:200px;top:900px;width:300px;height:150px;background:#eee">low</div>'
    assert _cbot(low) == 1050
