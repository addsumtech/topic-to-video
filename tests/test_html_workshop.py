"""The HTML tier's workshop: components a film builds for itself (scripts/workshop.py, validate.py, promote.py).

ONE example component, tests/fixtures/html_component/LabelGauge.{js,css}, is the CORRECT case for every check here.
Each broken case is that same component with one thing broken (a string replacement), so a check that fails the
broken one and passes the fixture is judging exactly the thing it names. The runtime checks drive a real headless
Chrome through the same harness `workshop.py check` uses; they skip when this machine has no Chrome.
"""
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import workshop as ws  # noqa: E402
import scenes  # noqa: E402

FIX = os.path.join(_ROOT, "tests", "fixtures", "html_component")
JS = open(os.path.join(FIX, "LabelGauge.js"), encoding="utf-8").read()
CSS = open(os.path.join(FIX, "LabelGauge.css"), encoding="utf-8").read()
ASSETS = os.path.join(_ROOT, "assets", "html")

needs_chrome = pytest.mark.skipif(scenes._chrome_bin({}) is None, reason="no Chrome for the component runtime checks")


def _component(tmp_path, js=JS, css=CSS, name="LabelGauge"):
    d = tmp_path / "c"
    d.mkdir(exist_ok=True)
    (d / (name + ".js")).write_text(js, encoding="utf-8")
    if css is not None:
        (d / (name + ".css")).write_text(css, encoding="utf-8")
    return str(d / (name + ".js")), str(d / (name + ".css"))


def _sub(text, old, new):
    assert old in text, "the fixture no longer contains %r — update this test's mutation" % old
    return text.replace(old, new, 1)


def _page(js_ref, css_ref, body='<label-gauge label="Brew pressure" value="9" min="0" max="12" unit="bar" '
                                 'style="width:800px;height:420px"></label-gauge>', after_seek=False, extra=""):
    seek = '<script src="file://%s"></script>' % os.path.join(ASSETS, "seek.js")
    comp = '<script src="%s"%s></script>' % (js_ref, extra)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">\n'
            '<link rel="stylesheet" href="file://%s">\n<link rel="stylesheet" href="%s">\n</head><body>\n'
            '<div class="stage">%s</div>\n%s\n%s\n</body></html>'
            % (os.path.join(ASSETS, "base.css"), css_ref, body,
               seek if after_seek else comp, comp if after_seek else seek))


def _film(tmp_path, page=None, entry=True, js=JS, css=CSS, slides=None):
    """A minimal HTML film whose workshop holds LabelGauge and whose beat 1 page draws it."""
    out = tmp_path / "film"
    (out / "workshop" / "html").mkdir(parents=True)
    (out / "pages").mkdir()
    (out / "workshop" / "html" / "LabelGauge.js").write_text(js, encoding="utf-8")
    (out / "workshop" / "html" / "LabelGauge.css").write_text(css, encoding="utf-8")
    jsp, cssp = ws.component_paths(str(out), "LabelGauge")
    (out / "pages" / "scene_01.html").write_text(page or _page(ws._url(jsp), ws._url(cssp)), encoding="utf-8")
    bl = [{"id": "LabelGauge", "kind": "component", "beats": [1], "slot": "page",
           "means": "how hard the pump pushes, against its range", "accept": "the needle sits past the middle"}]
    board = {"meta": {"language": "en", "aspect": "16:9", "build_list": bl if entry else []},
             "slides": slides or [{"index": 1, "type": "html", "props": {"html": "pages/scene_01.html"},
                                   "narration": "x"}]}
    (out / "storyboard.json").write_text(json.dumps(board), encoding="utf-8")
    return str(out)


# ── names and the pure helpers ────────────────────────────────────────────────────────────────────────────

def test_the_tag_is_the_kebab_form_of_the_name():
    assert ws.component_tag("EspressoPuck") == "espresso-puck"
    assert ws.component_tag("LabelGauge") == "label-gauge"


@pytest.mark.parametrize("name, why", [("Gauge", "no hyphen"), ("FontFace", "reserves"), ("espresso", "PascalCase")])
def test_a_name_whose_tag_cannot_be_a_custom_element_is_refused(name, why):
    assert why in (ws._component_name_problem(name) or "")


def test_words_must_come_from_attributes_numbers_only_when_they_are_attribute_values():
    attrs = ["Brew pressure", "9", "bar", "压力很高"]
    assert ws.unsourced_words(["Brew", "pressure 9 bar", "压力"], attrs) == []
    assert ws.unsourced_words(["Pressure"], attrs) == []                         # case-folded
    assert ws.unsourced_words(["Pump"], attrs) == ["pump"]
    assert ws.unsourced_words(["4.5"], attrs) == ["4.5"]                         # a computed number
    assert ws.unsourced_words(["温度"], attrs) == ["温度"]
    assert ws.unsourced_words(["→ % °"], attrs) == []                            # marks are not words


def test_page_custom_tags_skips_comments_scripts_and_svg_reserved_names():
    html = ('<!-- <old-gauge> --><label-gauge a="1"></label-gauge><svg><font-face></font-face></svg>'
            '<script>var s="<fake-tag>";</script><Espresso-Puck/>')
    assert ws.page_custom_tags(html) == ["label-gauge", "espresso-puck"]


def test_the_js_comment_stripper_keeps_strings_so_a_url_cannot_hide_code():
    src = "const u = 'a // b'; Math.random(); /* x */ // tail"
    assert "Math.random" in ws._strip_js_comments(src)
    assert "tail" not in ws._strip_js_comments(src)


def test_a_remotion_workshop_check_accepts_an_html_folder(tmp_path):
    out = tmp_path / "film"
    (out / "workshop" / "html").mkdir(parents=True)
    assert not any("html" in p for p in ws.names_problems(str(out)))


# ── the lint: what reading the files can judge ────────────────────────────────────────────────────────────

def test_the_fixture_passes_the_lint(tmp_path):
    js, css = _component(tmp_path)
    assert ws.component_lint("LabelGauge", js, css, "c/LabelGauge") == []


@pytest.mark.parametrize("old, new, expect", [
    ("    if (this._built) return;", "    this.attachShadow({mode: 'open'});\n    if (this._built) return;",
     "attachShadow"),
    ("    const attr =", "    const jitter = Math.random();\n    const attr =", "Math.random"),
    ("    const attr =", "    setTimeout(() => this.remove(), 0);\n    const attr =", "setTimeout"),
    ("    const attr =", "    const now = Date.now();\n    const attr =", "Date"),
    ("    const attr =", "    requestAnimationFrame(() => {});\n    const attr =", "requestAnimationFrame"),
    ("    const attr =", "    fetch('data.json');\n    const attr =", "fetch"),
    ("    const attr =", "    this.animate([{opacity: 0}, {opacity: 1}], 500);\n    const attr =", "el.animate"),
    ("customElements.define('label-gauge'", "customElements.define('label-dial'", "defines <label-dial>"),
    ("  static demo = {", "  static sample = {", "static demo"),
    ("});\n", "});\ncustomElements.define('label-gauge-two', class extends HTMLElement {});\n", "2 times"),
])
def test_each_js_rule_fails_its_broken_component(tmp_path, old, new, expect):
    js, css = _component(tmp_path, js=_sub(JS, old, new))
    probs = ws.component_lint("LabelGauge", js, css, "c/LabelGauge")
    assert any(expect in p for p in probs), probs


@pytest.mark.parametrize("old, new, expect", [
    ("@keyframes label-gauge-fade{", "@keyframes fade{", "@keyframes fade"),
    ("label-gauge .label-gauge__unit{", ".label-gauge__unit{", "not scoped"),
    ("label-gauge .label-gauge__unit{", "label-gauge .label-gauge__unit, .title{", "'.title'"),
    ("@keyframes label-gauge-fade{", "@import url(other.css);\n@keyframes label-gauge-fade{", "@import"),
])
def test_each_css_rule_fails_its_broken_component(tmp_path, old, new, expect):
    js, css = _component(tmp_path, css=_sub(CSS, old, new))
    probs = ws.component_lint("LabelGauge", js, css, "c/LabelGauge")
    assert any(expect in p for p in probs), probs


def test_a_component_without_its_css_is_refused(tmp_path):
    js, css = _component(tmp_path, css=None)
    assert any(".css is missing" in p for p in ws.component_lint("LabelGauge", js, css, "c/LabelGauge"))


# ── pages: the tag defined, both files linked, the script before seek.js ─────────────────────────────────

def test_a_correct_page_has_no_component_problems(tmp_path):
    out = _film(tmp_path)
    assert ws.page_component_problems(out, "pages/scene_01.html") == []


def test_a_script_linked_after_seek_js_is_refused(tmp_path):
    out = _film(tmp_path)
    jsp, cssp = ws.component_paths(out, "LabelGauge")
    open(os.path.join(out, "pages", "scene_01.html"), "w").write(_page(ws._url(jsp), ws._url(cssp), after_seek=True))
    probs = ws.page_component_problems(out, "pages/scene_01.html")
    assert any("AFTER seek.js" in p for p in probs), probs


@pytest.mark.parametrize("mutate, expect", [
    (lambda js, css: _page("", css).replace('<script src=""></script>', ""), "does not link its script"),
    (lambda js, css: _page(js, ws._url("/nowhere/x.css")), "does not link its stylesheet"),
    (lambda js, css: _page(js, css, extra=" defer"), "deferred"),
    (lambda js, css: _page(js, css, body="<label-dial></label-dial>"), "<label-dial>, which neither"),
])
def test_each_page_rule_fails_its_broken_page(tmp_path, mutate, expect):
    out = _film(tmp_path)
    jsp, cssp = ws.component_paths(out, "LabelGauge")
    open(os.path.join(out, "pages", "scene_01.html"), "w").write(mutate(ws._url(jsp), ws._url(cssp)))
    probs = ws.page_component_problems(out, "pages/scene_01.html")
    assert any(expect in p for p in probs), probs


def test_a_relative_link_to_the_workshop_counts(tmp_path):
    out = _film(tmp_path)
    open(os.path.join(out, "pages", "scene_01.html"), "w").write(
        _page("../workshop/html/LabelGauge.js", "../workshop/html/LabelGauge.css"))
    assert ws.page_component_problems(out, "pages/scene_01.html") == []


# ── runtime: the component rendered on its own ───────────────────────────────────────────────────────────

def _runtime(tmp_path, js=JS, css=CSS):
    j, c = _component(tmp_path, js=js, css=css)
    return ws.component_runtime("LabelGauge", j, c, "c/LabelGauge", str(tmp_path / "scratch"))


@needs_chrome
def test_the_fixture_passes_every_runtime_check(tmp_path):
    r = _runtime(tmp_path)
    assert r["problems"] == []
    assert r["demo"] == {"label": "Demo reading", "value": "6", "min": "0", "max": "10", "unit": "units"}


@needs_chrome
def test_a_word_written_into_the_code_is_caught(tmp_path):
    js = _sub(JS, "part(this, 'label', attr('label'));", "part(this, 'label', 'Pump pressure');")
    probs = _runtime(tmp_path, js=js)["problems"]
    assert any("'pump'" in p and "none of its attributes" in p for p in probs), probs


@needs_chrome
def test_a_computed_number_is_caught(tmp_path):
    js = _sub(JS, "part(reading, 'value', attr('value'));", "part(reading, 'value', String(val * 2));")
    probs = _runtime(tmp_path, js=js)["problems"]
    assert any("'12'" in p for p in probs), probs


@needs_chrome
def test_a_word_in_a_css_pseudo_element_is_caught(tmp_path):
    css = CSS + "\nlabel-gauge .label-gauge__unit::after{content:\" max\"}\n"
    probs = _runtime(tmp_path, css=css)["problems"]
    assert any("'max'" in p for p in probs), probs


@needs_chrome
def test_overflow_at_9_16_is_caught_and_only_there(tmp_path):
    css = CSS + "\nlabel-gauge .label-gauge__label{min-width:1200px}\n"
    probs = _runtime(tmp_path, css=css)["problems"]
    assert any("overflows at 9:16" in p for p in probs), probs
    assert not any("overflows at 16:9" in p for p in probs), probs


@needs_chrome
def test_movement_under_reduced_motion_is_caught(tmp_path):
    css = _sub(CSS, "transform:translateY(calc(6cqmin * var(--motion, 1)))", "transform:translateY(6cqmin)")
    probs = _runtime(tmp_path, css=css)["problems"]
    assert any("moves under reduced motion" in p and "label-gauge__reading" in p for p in probs), probs


@needs_chrome
def test_an_inline_component_that_ignores_its_box_is_caught(tmp_path):
    css = _sub(CSS, "label-gauge{display:flex;", "label-gauge{display:inline;")
    probs = _runtime(tmp_path, css=css)["problems"]
    assert any("display:inline" in p for p in probs), probs


@needs_chrome
def test_a_component_that_throws_is_reported_not_raised(tmp_path):
    js = _sub(JS, "    const attr =", "    this.nope.nope = 1;\n    const attr =")
    probs = _runtime(tmp_path, js=js)["problems"]
    assert any("threw" in p for p in probs), probs


@needs_chrome
def test_check_on_a_correct_film_is_clean_and_on_a_scaffold_names_only_the_scaffold(tmp_path):
    out = _film(tmp_path)
    assert ws.check(out) == []
    ws.scaffold_component(out, "BrewClock", "the shot's time against its target")
    probs = [p for p in ws.check(out) if "BrewClock" in p]
    assert len(probs) == 1 and "still the scaffold" in probs[0], probs


@needs_chrome
def test_check_finds_a_script_after_seek_js_in_a_film_page(tmp_path):
    out = _film(tmp_path)
    jsp, cssp = ws.component_paths(out, "LabelGauge")
    open(os.path.join(out, "pages", "scene_01.html"), "w").write(_page(ws._url(jsp), ws._url(cssp), after_seek=True))
    assert any("AFTER seek.js" in p for p in ws.check(out))


@needs_chrome
def test_the_still_command_writes_a_png(tmp_path):
    out = _film(tmp_path)
    attrs = tmp_path / "a.json"
    attrs.write_text(json.dumps({"label": "Brew pressure", "value": "9", "min": "0", "max": "12", "unit": "bar"}))
    assert ws.main([out, "still", "LabelGauge", "--attrs", str(attrs), "--p", "1", "--aspect", "9:16"]) == 0
    png = os.path.join(out, "workshop", "_stills", "LabelGauge.9x16.png")
    with open(png, "rb") as fh:
        assert fh.read(8) == b"\x89PNG\r\n\x1a\n"


def test_new_component_scaffolds_both_files_and_refuses_a_hyphenless_name(tmp_path):
    out = str(tmp_path / "film")
    assert ws.main([out, "new-component", "BrewClock", "--means", "the shot's time"]) == 0
    js, css = ws.component_paths(out, "BrewClock")
    assert "customElements.define('brew-clock'" in open(js).read() and os.path.isfile(css)
    assert ws.main([out, "new-component", "Clock", "--means", "x"]) == 1


@needs_chrome
def test_a_wide_unlocked_text_under_reduced_motion_is_not_called_moving(tmp_path):
    """The unlock's 1/1024 skew rides moving text and is dropped at rest: on a wide line it changes the box's
    height by width/1024, which is not movement."""
    css = _sub(CSS, "label-gauge .label-gauge__label{font:600 5.5cqmin/1.2",
               "label-gauge .label-gauge__label{min-width:1500px;text-align:center;font:600 5.5cqmin/1.2")
    css = _sub(css, "animation:label-gauge-fade .6s ease-out .4s forwards;",
               "transform:translateY(calc(5cqmin * var(--motion, 1))) matrix(1,.0009765625,0,1,0,0);"
               "animation:label-gauge-rise .6s ease-out .4s forwards;")
    probs = _runtime(tmp_path, css=css)["problems"]
    assert not any("reduced motion" in p for p in probs), probs
