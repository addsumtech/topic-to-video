"""A cued element's PARTS animate on its cue, not on page load (assets/html/seek.js), and the render captures them
to the end (_common.cued_anim_need).

THE DEFECT. seek.js anchored an element to a spoken cue only when the element itself carried `data-cue-index`.
Everything animated inside it kept its own `animation-delay` counted from the SCENE's start. A validation film's
`<tiling-patch>` (cells built by its script, each delayed .05-.95 s outward from the centre) rippled its cells in
during the scene's first second while the patch sat at opacity 0 until its word — measured on the delivered film,
the triangle patch faded in already complete at frames 310-320; the ripple was never on screen. A `.bar` fill
inside a cued `.card` had the same fault, with no component involved.

THE RULE NOW. A part with no `data-cue-index` of its own is timed from its nearest cued ancestor's start: the cue
(+ data-cue-offset) on a page with word timings, the ancestor's own authored delay on a paced one. Its own delay
is an offset from there. And the capture plan's per-cue window counts a part's delay + duration and a component's
declared `static span`, so the burst does not freeze the ripple mid-way.

Measured here through a real headless Chrome reading computed opacity at seek.js's frozen time — not a re-derivation
of the schedule.
"""
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import _common  # noqa: E402
import scenes  # noqa: E402

ASSETS = os.path.join(_ROOT, "assets", "html")
needs_chrome = pytest.mark.skipif(scenes._chrome_bin({}) is None, reason="no Chrome")

# a cued card (fades on its cue) holding a part that rises .3 s after the card starts, and an uncued header line
_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="file://{base}">
<style>.card{{width:400px;height:200px}} .card .part{{width:100px;height:40px;background:#fff}}</style>
</head><body><div class="stage">
<div id="head" class="reveal">Header</div>
<div id="card" class="card reveal" data-cue-index="0" data-cue="word"{hostdelay}>
  <div id="part" class="part reveal-up" style="animation-delay:.3s"></div>
</div>
<div id="later" class="reveal" data-cue-index="1" data-cue="later"></div>
</div><script src="file://{seek}"></script></body></html>"""


def _opacity(chrome, tmp_path, query, el="part", hostdelay=""):
    page = tmp_path / "p.html"
    page.write_text(_PAGE.format(base=os.path.join(ASSETS, "base.css"), seek=os.path.join(ASSETS, "seek.js"),
                                 hostdelay=hostdelay), encoding="utf-8")
    chrome.shot("file://%s?%s" % (page, query), str(tmp_path / "shot.jpg"))
    r = chrome._cmd("Runtime.evaluate", {"expression": "getComputedStyle(document.getElementById(%s)).opacity"
                                         % json.dumps(el), "returnByValue": True}, chrome.sid)
    return float(r["result"]["result"]["value"])


@pytest.fixture(scope="module")
def chrome():
    import _cdp
    c = _cdp.Chrome(scenes._chrome_bin({}), 800, 600)
    yield c
    c.close()


@needs_chrome
def test_a_part_inside_a_cued_element_waits_for_the_cue(chrome, tmp_path):
    """Cue at 2.0 s of a 4 s scene: at 2.2 s the part (its .3 s offset not yet reached) is still hidden — before the
    fix it had risen at 0.3 s and stood at full opacity here; at 3.3 s it has risen."""
    cues = "cues=2.0,3.5&dur=4"
    assert _opacity(chrome, tmp_path, "p=0.55&" + cues) == 0.0          # T = 2.2 s
    assert _opacity(chrome, tmp_path, "p=0.825&" + cues) > 0.95         # T = 3.3 s
    # the host itself is unchanged: on its cue
    assert _opacity(chrome, tmp_path, "p=0.45&" + cues, el="card") == 0.0
    # an element outside every cued ancestor keeps the scene clock
    assert _opacity(chrome, tmp_path, "p=0.4&" + cues, el="head") == 1.0


@needs_chrome
def test_a_negative_cue_offset_on_the_host_leads_its_parts_too(chrome, tmp_path):
    page_q = "p=0.5&cues=2.6,3.5&dur=4"                                   # T = 2.0 s
    plain = _opacity(chrome, tmp_path, page_q)
    led = _opacity(chrome, tmp_path, page_q, hostdelay=' data-cue-offset="-0.6"')   # host starts 2.0, part 2.3
    assert plain == 0.0 and led == 0.0
    assert _opacity(chrome, tmp_path, "p=0.65&cues=2.6,3.5&dur=4", hostdelay=' data-cue-offset="-0.6"') > 0.5


@needs_chrome
def test_on_a_paced_page_a_part_counts_from_its_hosts_own_delay(chrome, tmp_path):
    """No word timings: the host reveals on its authored delay (1.0 s) and its part .3 s after that. The paced
    envelope is max(start + duration) = 1.3 + .7 = 2.0 s, so p=0.6 is T=1.2 s: the part has not begun."""
    hd = ' style="animation-delay:1s"'
    assert _opacity(chrome, tmp_path, "p=0.6", hostdelay=hd) == 0.0
    assert _opacity(chrome, tmp_path, "p=1", hostdelay=hd) == 1.0


def test_the_capture_plan_counts_a_parts_delay_under_its_host():
    html = _PAGE.format(base="/x/base.css", seek="/x/seek.js", hostdelay="")
    need = _common.cued_anim_need(html)
    assert need[0] == pytest.approx(0.3 + 0.7)            # the part's offset + its .reveal-up
    assert need[1] == pytest.approx(0.7)


def test_the_capture_plan_reads_a_components_declared_span(tmp_path):
    js = tmp_path / "TilingPatch.js"
    js.write_text("customElements.define('tiling-patch', class extends HTMLElement {\n"
                  "  static demo = {shape: 'hex'};\n  static span = 1.45;\n});\n", encoding="utf-8")
    html = ('<div class="tiles"><tiling-patch class="reveal" shape="tri" data-cue-index="3" data-cue="三角形">'
            '</tiling-patch><div data-cue-index="4" data-cue="x"><tiling-patch shape="hex" '
            'style="animation-delay:.2s"></tiling-patch></div></div>'
            '<script src="file://%s"></script>' % js)
    need = _common.cued_anim_need(html)
    assert need[3] == pytest.approx(1.45)                  # the host IS the component
    assert need[4] == pytest.approx(0.2 + 1.45)            # the component is a part of a cued wrapper
    assert _common.component_spans(html) == {"tiling-patch": 1.45}
    # an unreadable script is not a span (and not an exception)
    assert _common.component_spans('<script src="file:///nope/Missing.js"></script>') == {}
