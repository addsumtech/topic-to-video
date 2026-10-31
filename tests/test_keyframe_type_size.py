"""keyframe_qa's rendered type-size floor — the html tier's half of runtime/textSafe.tsx's TYPE_*_FRAC.

Film B v1 of the 2026-10-30 generality validation shipped its body copy at 16 px on a 1080x1080 frame: a `font:`
shorthand naming an undefined `var(--font-display)` was invalid as a whole, so the browser default applied, and all
eight gates passed it. The CSS said 30px; only the computed, rendered size could say otherwise."""
import os
import sys
import tempfile
from urllib.parse import quote

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import keyframe_qa as kq
import scenes
import text_safe_qa as tsq

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _row(t, px, cls=""):
    return {"t": t, "px": px, "cls": cls, "tag": "div", "font": "%spx X" % px}


@pytest.mark.parametrize("W,H", [(1080, 1080), (1920, 1080), (1080, 1920), (1080, 1350)])
def test_the_floor_is_the_remotion_tiers_fraction_of_the_short_side(W, H):
    short = min(W, H)
    probe = {"W": W, "H": H, "measured": 3, "exempt": 0,
             "rows": [_row("body", 16.0), _row("label", TYPE := round(tsq.TYPE_ERROR_FRAC * short + 1, 1)),
                      _row("title", 62.0)]}
    issues, adv = kq.type_size_verdict(probe, W, H)
    assert len(issues) == 1 and "'body' 16.0px" in issues[0] and "browser default" in issues[0], issues
    assert len(adv) == 1 and "'label'" in adv[0], adv                     # between the two floors: a warning
    assert TYPE < tsq.TYPE_WARN_FRAC * short


def test_a_smaller_canvas_scales_the_floor_down():
    probe = {"W": 720, "H": 1280, "measured": 1, "exempt": 0, "rows": [_row("label", 17.0)]}
    issues, adv = kq.type_size_verdict(probe, 720, 1280)
    assert issues == [] and len(adv) == 1      # 17 px clears 0.022 x 720 = 15.8, not 0.0275 x 720 = 19.8


def test_a_probe_run_at_another_viewport_is_refused():
    with pytest.raises(ValueError, match="renders at 1080x1080"):
        kq.type_size_verdict({"W": 1920, "H": 1080, "rows": []}, 1080, 1080)


def test_the_floor_constants_are_the_runtimes():
    tsx = open(os.path.join(ROOT, "remotion", "src", "runtime", "textSafe.tsx"), encoding="utf-8").read()
    assert "export const TYPE_WARN_FRAC = %s;" % tsq.TYPE_WARN_FRAC in tsx
    assert "export const TYPE_ERROR_FRAC = %s;" % tsq.TYPE_ERROR_FRAC in tsx


needs_chrome = pytest.mark.skipif(scenes._chrome_bin({}) is None, reason="no Chrome for the html-tier probe")

_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>html,body{{margin:0;width:{w}px;height:{h}px;background:#111;color:#eee}}
.bad{{font:700 30px/1.2 var(--font-display)}}
.good{{font:700 30px/1.2 var(--font-display, "PingFang SC", sans-serif)}}
.half{{transform:scale(.5);transform-origin:0 0;font-size:40px}}
.hidden{{opacity:0;font-size:12px}}
.credit{{font-size:15px}}</style></head><body>
<div class="bad">留下空隙 invalid shorthand</div>
<div class="good">只有这三种 valid shorthand</div>
<div class="half"><span>scaled to twenty</span></div>
<div class="hidden">not yet revealed</div>
<div data-small="tick marks"><span>0 1 2 3</span></div>
<div class="credit">A. Person · CC BY 4.0 · Wikimedia Commons</div>
<svg width="200" height="40" viewBox="0 0 100 20"><text x="0" y="15" font-size="10">svg at twenty</text></svg>
<svg width="1000" height="200" viewBox="0 0 100 20"><text x="0" y="15" font-size="10">svg at a hundred</text></svg>
<x-label></x-label>
<script>customElements.define('x-label', class extends HTMLElement {{ connectedCallback() {{
  const r = this.attachShadow({{mode: 'open'}}); r.innerHTML = '<span style="font-size:14px">shadow label</span>'; }} }});</script>
</body></html>"""


def _probe(W, H):
    with tempfile.TemporaryDirectory() as d:
        page = os.path.join(d, "p.html")
        open(page, "w", encoding="utf-8").write(_PAGE.format(w=W, h=H))
        chrome = kq._open_cdp({}, W, H)
        assert chrome, "no CDP Chrome"
        try:
            chrome.shot("file://" + quote(page), os.path.join(d, "s.png"))
            return kq._type_size_probe(chrome)
        finally:
            chrome.close()


@needs_chrome
@pytest.mark.parametrize("W,H", [(1080, 1080), (1920, 1080), (1080, 1920)])
def test_the_probe_reads_the_rendered_size_not_the_declared_one(W, H):
    p = _probe(W, H)
    assert (p["W"], p["H"]) == (W, H), "the probe ran at the wrong viewport"
    px = {r["t"].split()[0] if r["t"][0].isascii() else r["t"][:4]: r["px"] for r in p["rows"]}
    assert px["留下空隙"] == 16.0, px          # the invalid shorthand: the CSS says 30, the browser draws 16
    assert px["只有这三"] == 30.0, px
    assert px["scaled"] == 20.0, px            # a transform above the text scales what the viewer sees
    assert px["svg"] in (20.0, 100.0) and sorted(r["px"] for r in p["rows"] if r["t"].startswith("svg")) == [20.0, 100.0]
    assert px["shadow"] == 14.0, px            # a component's shadow-root label is the page's text too
    assert "not" not in px, "an unrevealed (opacity 0) line was judged"
    assert p["exempt"] == 2, p                 # data-small + .credit: counted, not judged
    issues, _adv = kq.type_size_verdict(p, W, H)
    assert issues and all(t in issues[0] for t in ("留下空隙", "shadow label", "svg at twenty", "scaled to twenty"))
    assert "valid shorthand" not in issues[0].replace("invalid shorthand", "")
