"""Design-first on the HTML tier: at least half of an HTML film's non-exempt pages are BUILT (a workshop component)
or BESPOKE (a composition of the page's own), measured from the page source; a stock page used AS-IS earns it
(`shot_fit.ideal` + `shot_fit.shares`). Definitions live in scripts/validate.py above `_HTML_STOCK_SHEETS`."""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import validate as v  # noqa: E402

SHARES = {"ideal": "five ordered steps where the third one visibly narrows and holds everything back",
          "shares": "its left-to-right row already encodes order by position, and its single lit step carries "
                    "the bottleneck by colour"}

STOCK = """<div class="stage"><div class="kicker">k</div><div class="flow">
<div class="step"><div class="t">a</div></div><div class="arrow">→</div><div class="step on"><div class="t">b</div></div>
</div></div>"""

BESPOKE_STYLE = """<style>
.lanes{display:grid;grid-template-columns:repeat(4,1fr);gap:24px}
.pkt{position:absolute;left:40px;top:12px;width:30px;height:30px;background:var(--accent)}
</style>
<div class="stage"><div class="title">t</div><div class="lanes"><div class="lane"><div class="pkt"></div></div></div></div>"""

COLOUR_ONLY = """<style>
.card{background:color-mix(in srgb,var(--accent) 20%,var(--bg));border-color:var(--accent)}
.flow .step{color:var(--accent2)}
.flow{flex-direction:column}
.mine{color:var(--accent);font-size:40px;letter-spacing:.04em}
</style>
<div class="stage"><div class="mine">m</div><div class="flow"><div class="step"><div class="t">a</div></div></div>
<div class="card">c</div></div>"""

SVG8 = ('<svg viewBox="0 0 900 500">' + "".join('<line x1="%d" y1="0" x2="%d" y2="400"/>' % (i * 90, i * 90)
                                               for i in range(6)) + '<circle cx="1" cy="1" r="3"/><text>x</text></svg>')


def _film(tmp_path, pages, fits=None, meta=None, types=None):
    """pages: page bodies in beat order. fits: {beat: shot_fit}. types: {beat: scene type} for non-html beats."""
    out = tmp_path / "film"
    (out / "pages").mkdir(parents=True, exist_ok=True)
    slides = []
    for i, body in enumerate(pages, 1):
        t = (types or {}).get(i, "html")
        s = {"index": i, "type": t, "narration": "A sentence.", "duration": 5.0}
        if t == "html":
            rel = "pages/scene_%02d.html" % i
            (out / rel).write_text("<!doctype html><html><head></head><body>%s</body></html>" % body,
                                   encoding="utf-8")
            s["props"] = {"html": rel}
        if (fits or {}).get(i):
            s["shot_fit"] = dict(fits[i])
        slides.append(s)
    return dict(meta or {}), slides, str(out)


def _routes(meta, slides, out):
    return {n: r for n, r, _w, _rel in v.html_design_routes(meta, slides, out)}


def _share(meta, slides, out):
    errs, warns = [], []
    v._html_design_share(meta, slides, errs, warns, out)
    return errs, warns


def test_stock_only_pages_under_half_is_an_error_naming_the_pages_and_the_routes(tmp_path):
    meta, slides, out = _film(tmp_path, [BESPOKE_STYLE, STOCK, STOCK, STOCK], fits={2: SHARES, 3: SHARES, 4: SHARES})
    errs, _ = _share(meta, slides, out)
    msg = [e for e in errs if "only 1 of 4" in e]
    assert msg, errs
    assert "pages/scene_02.html" in msg[0] and "BUILD" in msg[0] and "BESPOKE" in msg[0]
    # every page stock: the zero case names itself
    meta, slides, out = _film(tmp_path / "z", [STOCK, STOCK], fits={1: SHARES, 2: SHARES})
    errs, _ = _share(meta, slides, out)
    assert any("no page is BUILT or BESPOKE" in e for e in errs), errs


BUILT = "<div class='stage'><espresso-puck packed='1'></espresso-puck></div>"
BUILT_META = {"build_list": [{"id": "EspressoPuck", "kind": "component", "beats": [1]}]}


def test_exactly_half_passes(tmp_path):
    meta, slides, out = _film(tmp_path, [BUILT, STOCK], fits={2: SHARES}, meta=BUILT_META)
    errs, _ = _share(meta, slides, out)
    assert not errs, errs


def test_no_built_page_is_an_error(tmp_path):
    # the signature beat is BUILT on this tier too — a film of bespoke pages alone is refused
    meta, slides, out = _film(tmp_path, [BESPOKE_STYLE, BESPOKE_STYLE, STOCK], fits={3: SHARES})
    errs, _ = _share(meta, slides, out)
    assert any("no page is BUILT" in e for e in errs), errs
    # …also when every other beat is exempt
    title = "<div class='stage'><div class='title'>T</div></div>"
    meta, slides, out = _film(tmp_path / "x", [title, title])
    assert any("no page is BUILT" in e for e in _share(meta, slides, out)[0])


def test_a_page_style_block_that_lays_out_its_own_classes_counts(tmp_path):
    cjk = ("<style>.主图{display:grid;grid-template-columns:2fr 1fr}.标记{position:absolute;left:4px}</style>"
           "<div class='主图'><b class='标记'>中</b></div>")
    at_rules = ("<style>@media (min-width:1px){.lane{display:grid;grid-template-columns:repeat(3,1fr)}} "
                "@keyframes k{from{transform:scale(1)}}"
                ".pk{transform:rotate(3deg)}</style><div class='lane'><b class='pk'></b></div>")
    meta, slides, out = _film(tmp_path, [STOCK, BESPOKE_STYLE, cjk, at_rules, STOCK])
    routes = _routes(meta, slides, out)
    assert [routes[i] for i in (2, 3, 4)] == ["bespoke"] * 3, routes


def test_a_colour_only_override_or_a_restyled_archetype_does_not_count(tmp_path):
    one_own_grid = "<style>.cmp{display:grid;grid-template-columns:1fr 1fr}</style>" \
                   "<div class='stage'><div class='cmp'><div class='card'>a</div><div class='card'>b</div></div></div>"
    dead_css = "<style>.lanes{display:grid}.pkt{position:absolute;left:4px}</style>" + STOCK
    inline_wrapper = ("<div class='stage'><div style='display:grid;grid-template-columns:1fr 1fr;gap:40px'>"
                      "<div class='card'>a</div><div style='display:flex;flex-direction:column'>b</div></div></div>")
    meta, slides, out = _film(tmp_path, [STOCK, COLOUR_ONLY, one_own_grid, dead_css, inline_wrapper, STOCK])
    routes = _routes(meta, slides, out)
    assert [routes[i] for i in (2, 3, 4, 5)] == ["as-is"] * 4, routes


def test_a_stock_part_reused_outside_its_archetype_is_the_pages_own(tmp_path):
    # base.css styles `.band` only inside `.bullet`; a page building its own `.band` outside one is composing
    page = ("<style>.band{display:grid;grid-template-columns:2fr 1fr;height:140px}.nm{position:absolute;left:0}"
            "</style><div class='stage'><div class='band'><i></i><i></i></div><div class='nm'><span>a</span></div></div>")
    inside = ("<style>.bullet .band{position:absolute;left:0}.nm{display:flex}</style><div class='stage'>"
              "<div class='bullet'><div class='band'></div></div><div class='nm'>a</div></div>")
    meta, slides, out = _film(tmp_path, [STOCK, page, inside, STOCK])
    routes = _routes(meta, slides, out)
    assert routes[2] == "bespoke" and routes[3] == "as-is", routes


def test_a_drawn_svg_counts_but_an_icon_or_a_ghosted_backdrop_does_not(tmp_path):
    drawn = "<div class='stage'><div class='title'>t</div>%s</div>" % SVG8
    ghost = "<div class='bg-motif'>%s</div>%s" % (SVG8, STOCK)
    full = "<div class='bg-motif' style='opacity:1'>%s</div>%s" % (SVG8, STOCK)
    icon = "<div class='icon'>%s</div>%s" % (SVG8, STOCK)
    meta, slides, out = _film(tmp_path, [STOCK, drawn, ghost, full, icon, STOCK])
    routes = _routes(meta, slides, out)
    assert [routes[i] for i in (2, 3, 4, 5)] == ["bespoke", "as-is", "bespoke", "as-is"], routes


def test_a_hand_placed_composition_counts(tmp_path):
    nodes = "".join("<div class='label' style='position:absolute;left:%dpx;top:%dpx'>n</div>" % (i * 200, i * 90)
                    for i in range(3))
    meta, slides, out = _film(tmp_path, [STOCK, "<div class='stage'>%s</div>" % nodes, STOCK])
    assert _routes(meta, slides, out)[2] == "bespoke"


def test_a_component_page_is_built(tmp_path):
    meta, slides, out = _film(tmp_path, [STOCK, "<div class='stage'><espresso-puck packed='1'></espresso-puck></div>"])
    assert _routes(meta, slides, out)[2] == "as-is", "an undeclared tag is not a build"
    os.makedirs(os.path.join(out, "workshop", "html"))
    open(os.path.join(out, "workshop", "html", "EspressoPuck.js"), "w").write("// component")
    assert _routes(meta, slides, out)[2] == "built"
    meta2 = {"build_list": [{"id": "EspressoPuck", "kind": "component", "beats": [2]}]}
    os.remove(os.path.join(out, "workshop", "html", "EspressoPuck.js"))
    assert _routes(meta2, slides, out)[2] == "built", "a build-list component (e.g. promoted) is a build too"


def test_an_as_is_page_without_ideal_and_shares_is_an_error(tmp_path):
    meta, slides, out = _film(tmp_path, [BUILT, STOCK], fits={2: {"ideal": SHARES["ideal"], "shares": "fits"}},
                              meta=BUILT_META)
    errs, _ = _share(meta, slides, out)
    assert any("AS-IS without earning it" in e and "scene #2" in e and "shot_fit.shares" in e for e in errs), errs
    slides[1]["shot_fit"] = dict(SHARES)
    assert not _share(meta, slides, out)[0]
    # the design plan is an accepted home for the same two fields
    del slides[1]["shot_fit"]
    json.dump({"beats": [{"index": 2, "ideal": SHARES["ideal"], "shares": SHARES["shares"]}]},
              open(os.path.join(out, "design_plan.json"), "w"))
    assert not _share(meta, slides, out)[0]


def test_exempt_set_is_narrow(tmp_path):
    title = "<div class='stage'><div class='kicker'>k</div><div class='rule'></div><div class='title reveal-up'>T</div></div>"
    meta, slides, out = _film(tmp_path, [title, title, STOCK, title])
    routes = _routes(meta, slides, out)
    assert routes[1] == "exempt" and routes[4] == "exempt" and routes[2] == "as-is", routes
    # a real photo is a plate only when the picture IS the page and carries imagefetch's provenance
    img = os.path.join(out, "mars.jpg")
    open(img, "wb").write(b"\xff\xd8")
    plate = "<img class='bg-photo' src='../mars.jpg'><div class='stage'><div class='title'>t</div></div>"
    hub = ("<div class='stage'><div class='hubspoke'><div class='hs-spoke'><div class='media'>"
           "<img src='../mars.jpg'></div></div><div class='hs-hub'>h</div></div></div>")
    meta, slides, out2 = _film(tmp_path, [STOCK, plate, hub, STOCK])
    os.rename(img, os.path.join(out2, "mars.jpg"))
    assert _routes(meta, slides, out2)[2] == "as-is", "no provenance sidecar: not a known real photo"
    json.dump({"artist": "NASA/JPL-Caltech", "license": "Public domain"}, open(os.path.join(out2, "mars.jpg.json"), "w"))
    routes = _routes(meta, slides, out2)
    assert routes[2] == "exempt" and routes[3] == "as-is", routes


def test_the_slides_tier_and_a_remotion_film_are_exempt(tmp_path):
    meta, slides, out = _film(tmp_path, ["", "", ""], types={1: "slide", 2: "slide", 3: "slide"})
    assert _share(meta, slides, out) == ([], [])
    meta, slides, out = _film(tmp_path / "r", [STOCK, STOCK], meta={"renderer": "remotion"})
    assert _share(meta, slides, out) == ([], [])


def test_the_floor_is_wired_into_evaluate(tmp_path):
    meta, slides, out = _film(tmp_path, [STOCK, STOCK, STOCK])
    for s in slides:
        s["audio"] = "audio/%02d.mp3" % s["index"]
    errs = v.evaluate({"meta": meta, "slides": slides}, out, pre_tts=True)["errors"]
    assert any(e.startswith("design-first:") for e in errs), errs
    slides_tier = [{"index": i, "type": "slide", "image": None, "narration": "A sentence.", "duration": 5.0,
                    "audio": "audio/%02d.mp3" % i} for i in (1, 2, 3)]
    errs = v.evaluate({"meta": {}, "slides": slides_tier}, out, pre_tts=True)["errors"]
    assert not any(e.startswith("design-first:") for e in errs), errs


def test_display_flex_alone_is_not_a_layout_of_the_pages_own(tmp_path):
    # the finding: <style>.r{display:flex}.c{display:flex}</style> around stock cards read as BESPOKE, while the
    # same layout written inline was as-is
    flex = ("<style>.r{display:flex}.c{display:flex;flex-direction:column}</style><div class='stage'>"
            "<div class='r'><div class='c'><div class='card'>a</div></div><div class='card'>b</div></div></div>")
    one_track = ("<style>.r{display:grid;grid-template-columns:1fr}.c{top:10px}</style><div class='stage'>"
                 "<div class='r'><div class='c'><div class='card'>a</div></div></div></div>")
    real = ("<style>.r{display:grid;grid-template-columns:1fr 2fr}.c{grid-column:2}</style><div class='stage'>"
            "<div class='r'><div class='c'><div class='card'>a</div></div></div></div>")
    meta, slides, out = _film(tmp_path, [STOCK, flex, one_track, real, STOCK])
    routes = _routes(meta, slides, out)
    assert [routes[i] for i in (2, 3, 4)] == ["as-is", "as-is", "bespoke"], routes
    why = [w for n, r, w, _rel in v.html_design_routes(meta, slides, out) if n == 2][0]
    assert "display" in why, why


def test_a_template_svg_or_labels_are_not_the_pages_own_drawing(tmp_path):
    # the stock slopegraph (references/html-templates.md): an unclassed <svg> of `.sl` lines and `.axl` labels
    slope = ("<div class='stage'><svg viewBox='0 0 900 560' style='width:900px'>"
             + "".join("<line class='sl reveal-wipe' x1='90' y1='%d' x2='810' y2='%d' stroke='var(--accent)'/>"
                       "<text class='axl'>a</text><text>b</text>" % (100 + i * 40, 300 - i * 30) for i in range(6))
             + "</svg></div>")
    labels = ("<div class='stage'><svg viewBox='0 0 900 500'>" + "<line x1='0' y1='0' x2='9' y2='9'/>" * 3
              + "<text>x</text>" * 5 + "</svg></div>")
    meta, slides, out = _film(tmp_path, [STOCK, slope, labels, STOCK])
    routes = _routes(meta, slides, out)
    assert routes[2] == "as-is" and routes[3] == "as-is", routes
    assert {"sl", "axl"} <= v.template_svg_classes() and "draw" not in v.template_svg_classes()
