"""The html diversity lints abstain on pages they cannot read: BUILT pages (a workshop component draws the picture)
and BESPOKE pages (hand-placed or self-styled compositions).

The layout-family, composition and background-flatness lints read base.css classes and the .stage's flex signature.
A page laid out by its own absolutely-placed classes around a built component has neither, so every lint fell to its
default: a QR-code film (2026-11-04) whose 31 pages each drew a different state of its own <qr-matrix> was warned
"31/31 use the same form family ('title')", "100% CENTER-anchored", "only 0% break the centered column" and "26/30
have NO backdrop" — four confident readings of things the gate never saw. The pages it CAN read still vote."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import validate  # noqa: E402

_BUILT = ('<!doctype html><html><head><style>.stage{position:absolute;inset:0}.abs{position:absolute}'
          '.lab{position:absolute;left:1500px;top:400px}</style></head><body><div class="stage">'
          '<div class="abs" style="left:900px;top:120px;width:720px;height:720px"><demo-code n="%d"></demo-code></div>'
          '<div class="lab reveal-up" data-cue-index="0" data-cue="one">label %d</div></div></body></html>')
_STOCK = ('<!doctype html><html><head></head><body><div class="stage"><div class="kicker">k</div>'
          '<h1 class="title">a title %d</h1></div></body></html>')


def _film(tmp_path, pages):
    out = tmp_path / "film"
    (out / "workshop" / "html").mkdir(parents=True)
    (out / "workshop" / "html" / "DemoCode.js").write_text("customElements.define('demo-code', class extends HTMLElement{});")
    (out / "workshop" / "html" / "DemoCode.css").write_text("demo-code{display:block}")
    (out / "pages").mkdir()
    slides = []
    for i, html in enumerate(pages, 1):
        (out / "pages" / ("p%02d.html" % i)).write_text(html)
        slides.append({"index": i, "type": "html", "props": {"html": "pages/p%02d.html" % i},
                       "narration": "one two three four five six", "duration": 4.0})
    return str(out), {"meta": {"title": "t", "voice": "say", "transition": "none"}, "slides": slides}


def _diversity(warnings):
    return [w for w in warnings if w.startswith(("layout diversity", "composition diversity", "background flatness"))]


def test_built_pages_cast_no_family_composition_or_flatness_vote(tmp_path):
    out, board = _film(tmp_path, [_BUILT % (i, i) for i in range(8)])
    warnings = validate.evaluate(board, out, pre_tts=True)["warnings"]
    assert _diversity(warnings) == []


def test_readable_stock_pages_still_vote(tmp_path):
    out, board = _film(tmp_path, [_STOCK % i for i in range(6)] + [_BUILT % (i, i) for i in range(2)])
    warnings = validate.evaluate(board, out, pre_tts=True)["warnings"]
    found = _diversity(warnings)
    assert any(w.startswith("layout diversity: 6/6 ") for w in found), found
    assert any(w.startswith("background flatness: 6/6 ") for w in found), found
