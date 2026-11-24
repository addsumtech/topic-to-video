"""assets/html/math.js: the Remotion tier's typeset, moving maths on a director-path film page. The bundle is the
committed one; mathtex.py <film_dir> typesets a film's math.json into _math/equations.js; a derivation's settled
frames are the plain typeset forms, every frame is a pure function of t, a TeX nobody typeset is refused by name, and
the page checks see an equation as a line of text."""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common  # noqa: E402
import mathtex  # noqa: E402
import page_overlap_qa as po  # noqa: E402

CHROME = _common.find_chrome()
needs_chrome = pytest.mark.skipif(not CHROME, reason="Chrome not installed")
FORMS = ["x^2 + 6x + 5 = 0", "\\class{sq}{(x+3)^2} - 4 = 0", "\\class{sq}{(x+3)^2} = 4", "x = -3 \\class{root}{\\pm 2}"]


def test_the_committed_bundle_matches_its_source(tmp_path):
    out = tmp_path / "math.js"
    subprocess.run([os.path.join(ROOT, "remotion", "node_modules", ".bin", "esbuild"),
                    os.path.join(ROOT, "assets", "html", "math", "src.js"), "--bundle", "--minify", "--format=iife",
                    "--global-name=MathFilm", "--log-level=warning", "--outfile=%s" % out], check=True)
    assert out.read_bytes() == open(os.path.join(ROOT, "assets", "html", "math.js"), "rb").read(), \
        "assets/html/math.js is stale: run scripts/build_math_page.sh"


def _eqs(d):
    js = (d / "_math" / "equations.js").read_text()
    head = "window.MATH_EQ = Object.assign(window.MATH_EQ || {}, "
    return json.loads(js[js.index(head) + len(head):js.rindex(");")]).values()


def _typeset(d, forms=FORMS):
    (d / "math.json").write_text(json.dumps({"equations": forms}))
    return mathtex.ensure_film(str(d))


def test_a_films_math_json_is_typeset_into_equations_js(tmp_path):
    _typeset(tmp_path)
    assert sorted(e["tex"] for e in _eqs(tmp_path)) == sorted(FORMS)
    (tmp_path / "math.json").write_text(json.dumps({"equations": ["\\frac{a"]}))
    with pytest.raises(RuntimeError, match="close brace"):           # MathJax's own message, never a red glyph
        mathtex.ensure_film(str(tmp_path))
    (tmp_path / "math.json").write_text(json.dumps({"equations": [{"display": True}]}))
    with pytest.raises(ValueError, match="TeX string"):
        mathtex.ensure_film(str(tmp_path))


def _page(d, script, body=""):
    shutil.copy(os.path.join(ROOT, "assets", "html", "math.js"), d)
    (d / "film.html").write_text("""<!doctype html><html><head><meta charset='utf-8'></head>
<body style='margin:0;width:1920px;height:1080px'>%s
<svg id="m" width="1920" height="1080" style="position:absolute;left:0;top:0"></svg>
<script src="_math/equations.js"></script><script src="math.js"></script><script>
try { %s } catch (e) { document.title = 'ERR ' + e.message; }
</script></body></html>""" % (body, script))
    (d / "_plan.json").write_text(json.dumps({"video": "final.mp4", "fps": 30, "frames": 300}))


def _title(dom):
    t = dom[dom.index("<title>") + 7:dom.index("</title>")].replace("&quot;", '"').replace("&amp;", "&")
    assert not t.startswith("ERR"), t
    return json.loads(t)


def _dom(d):
    r = subprocess.run([CHROME, "--headless=new", "--allow-file-access-from-files", "--window-size=1920,1080",
                        "--virtual-time-budget=4000", "--dump-dom", "file://%s" % (d / "film.html")],
                       capture_output=True, text=True, timeout=120)
    return r.stdout


DERIVE = """const D = MathFilm.derivation({forms: %s, box: {x: 160, y: 300, w: 1600, h: 420}, em: 130,
  write: [0, 1.5], steps: [[2, 3.2], [4, 5.2], [6, 7.2]], highlight: {term: 'root', at: [8, 9]}});
const svg = document.getElementById('m');
window.seek = (t) => MathFilm.render(svg, D.at(t), {ink: '#1d1f24', accent: '#d9480f'});
""" % json.dumps(FORMS)


@needs_chrome
def test_settled_frames_are_the_typeset_forms_and_every_frame_is_a_function_of_t(tmp_path):
    _typeset(tmp_path)
    _page(tmp_path, DERIVE + """
const glyphs = () => svg.querySelectorAll('g[data-math] path').length;
const html = (t) => { seek(t); return svg.innerHTML; };
const n = FORMS_N.map((t) => { seek(t); return glyphs(); });
const a = html(4.6), b = (html(8.5), html(0.7), html(4.6));
seek(1.8); const label = svg.querySelector('g[data-math]').getAttribute('data-math');
seek(9.5); const accented = Array.from(svg.querySelectorAll('g[data-math] path')).filter((p) => p.getAttribute('fill') === '#d9480f').length;
document.title = JSON.stringify({n, same: a === b, label, accented, frame: !!svg.querySelector('g[data-math] path[fill=none]')});
""".replace("FORMS_N", "[1.8, 3.6, 5.6, 7.6]"))
    dom = _dom(tmp_path)
    got = _title(dom)
    eqs = {e["tex"]: e for e in _eqs(tmp_path)}
    assert got["n"] == [len(eqs[f]["glyphs"]) for f in FORMS], got     # held between steps: exactly one form, whole
    assert got["same"], "seek(t) after other frames drew a different frame"
    assert got["label"] == FORMS[0]
    assert got["accented"] >= 2 and got["frame"], got                  # the picked-out term takes the accent + frame


@needs_chrome
def test_a_tex_nobody_typeset_is_refused_by_name(tmp_path):
    _typeset(tmp_path)
    _page(tmp_path, "MathFilm.eq('E = mc^2'); document.title = 'drawn';")
    dom = _dom(tmp_path)
    assert "ERR MathFilm: TeX not typeset" in dom and "mc^2" in dom, dom[:400]


@needs_chrome
def test_a_label_laid_over_an_equation_collides(tmp_path):
    _typeset(tmp_path)
    label = "<div style='position:absolute;left:820px;top:470px;font:48px sans-serif'>complete the square</div>"
    _page(tmp_path, DERIVE + "seek(0);", body=label)
    assert po.main([str(tmp_path)]) == 1
    _page(tmp_path, DERIVE + "seek(0);", body=label.replace("top:470px", "top:900px"))
    assert po.main([str(tmp_path)]) == 0


CROSS = ["x^2 + \\class{ca}{\\frac{c}{a}} = 0", "x^2 = \\class{ca}{-\\frac{c}{a}}"]


@needs_chrome
def test_a_named_term_crossing_the_equals_sign_travels_as_one_piece(tmp_path):
    # proof film 2026-11-24: per-glyph arcs lifted the c but slid the fraction bar and the a straight through "="
    _typeset(tmp_path, CROSS)
    _page(tmp_path, """const D = MathFilm.derivation({forms: %s, box: {x: 100, y: 300, w: 1700, h: 400}, em: 120,
  steps: [[0, 1]]});
const ca = MathFilm.core.glyphsOf(D.eqs[0], 'ca');
const st = D.at(0.5).draws.filter((d) => /^p/.test(d.id) && ca.includes(+d.id.slice(1).split('_')[0]));
const rest = D.at(-1).draws.filter((d) => ca.includes(+d.id.slice(1)));
// both forms share one baseline, so a glyph's lift at mid-step is its y there minus its y at rest
document.title = JSON.stringify({n: st.length, dys: st.map((d) => Math.round(d.m[5] -
  rest.find((r) => +r.id.slice(1) === +d.id.slice(1).split('_')[0]).m[5]))});
""" % json.dumps(CROSS))
    dom = _dom(tmp_path)
    got = _title(dom)
    assert got["n"] >= 3, got                                          # c, the bar and a all travel
    assert max(got["dys"]) - min(got["dys"]) <= 2 and min(got["dys"]) < -20, got   # lifted, and lifted together


@needs_chrome
def test_by_default_only_named_terms_and_short_orderly_moves_travel(tmp_path):
    forms = ["ax^2 + bx + c = 0", "x^2 + \\frac{b}{a}x + \\frac{c}{a} = 0"]
    _typeset(tmp_path, forms)
    _page(tmp_path, """const F = %s, box = {x: 100, y: 300, w: 1700, h: 400};
const n = (match) => MathFilm.derivation({forms: F, box, em: 120, steps: [{at: [0, 1], match}]}).at(0.5).draws
  .filter((d) => /^p/.test(d.id)).length;
let bad = 'none'; try { n('soup'); } catch (e) { bad = e.message; }
document.title = JSON.stringify({all: n('all'), named: n('named'), fade: n('fade'), bad});""" % json.dumps(forms))
    dom = _dom(tmp_path)
    got = _title(dom)
    assert got["fade"] == 0 and 0 < got["named"] < got["all"], got   # the a sliding through x² no longer travels
    assert "'named', 'all' or 'fade'" in got["bad"], got


@needs_chrome
def test_the_highlight_frame_clears_the_swollen_term_and_tex_colours_are_kept(tmp_path):
    forms = ["x = \\class{root}{\\pm 2}", "\\color{#2b8a3e}{y} = 1"]
    _typeset(tmp_path, forms)
    _page(tmp_path, """const D = MathFilm.derivation({forms: [%s], box: {x: 100, y: 300, w: 1700, h: 400}, em: 120, steps: [],
  highlight: {term: 'root', at: [0, 1]}});
const s = D.at(0.5), idx = MathFilm.core.glyphsOf(D.eqs[0], 'root');
const rest = MathFilm.core.unionBox(D.eqs[0], idx, D.pl[0]);
const L = MathFilm.label(%s, {x: 300, y: 800, em: 80, anchor: 'center', display: true});
const svg = document.getElementById('m'); MathFilm.render(svg, L.at(0), {accent: '#d9480f'});
const fills = Array.from(svg.querySelectorAll('path')).map((p) => p.getAttribute('fill'));
const ink = L.eq.ink, cx = L.pl.x + (ink[0] + ink[2]) / 2 * L.pl.s, by = L.pl.y + L.eq.base * L.pl.s;
document.title = JSON.stringify({grow: [rest[0] - s.frame.box[0], s.frame.box[2] - rest[2]], fills, cx, by});
""" % (json.dumps(forms[0]), json.dumps(forms[1])))
    dom = _dom(tmp_path)
    got = _title(dom)
    assert min(got["grow"]) > 1, got                                  # the frame box is the term at its largest
    assert "#2b8a3e" in got["fills"] and "#d9480f" not in got["fills"], got   # \\color kept, not the accent
    assert abs(got["cx"] - 300) < 0.5 and abs(got["by"] - 800) < 0.5, got     # a label sits where it was put


def test_math_json_edits_leave_no_stale_typeset_files(tmp_path):
    _typeset(tmp_path)
    rep = _typeset(tmp_path, FORMS[:2])
    assert rep["pruned"] == 2 and len([f for f in os.listdir(tmp_path / "_math") if f.endswith(".json")]) == 2
