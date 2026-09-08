"""A chart of nothing is a claim about a trend, drawn.

`UiSurface` is right to refuse: it plots `series` exactly as given and draws no line when given none, because
a curve with no data behind it asserts something the film has not earned. What that correct rule left behind
was a caller problem. `SurfaceCarousel` rotated its four page shapes by index, so index 1 always asked for a
chart — and no caller could pass a series at all, because neither `Surface` nor `GlowPick` had the prop. The
result was visible and was missed by every gate this project owns: for a third of the carousel's run the
window on CENTRE STAGE was an empty plate with four grey rules in it, measured as ink and counted as content.

So the fix is two-sided, and neither half works alone. The pass-through means an author with real numbers
gets a real chart; the fallback means a surface with no numbers is never offered the chart shape. Take the
pass-through away and the chart is unreachable; take the fallback away and the default is an empty box again.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(os.path.dirname(_HERE), "remotion")

_NEEDS_NODE = pytest.mark.skipif(
    not (shutil.which("npx") and shutil.which("node") and os.path.isdir(os.path.join(_REM, "node_modules"))),
    reason="needs the remotion toolchain")


def _markup(content_js, page="chart"):
    """Render UiSurface to static markup under node. It takes no remotion hooks, so the real component can be
    asked what it actually draws rather than the test asking its source what it says it draws."""
    tmp = tempfile.mkdtemp(prefix="uis_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.tsx")
        open(entry, "w", encoding="utf-8").write(
            "import React from 'react';\n"
            "import {renderToStaticMarkup} from 'react-dom/server';\n"
            "import {UiSurface} from %s;\n"
            "const html = renderToStaticMarkup(React.createElement(UiSurface, "
            "{page: %s, W: 900, H: 560, content: %s} as any));\n"
            "console.log(JSON.stringify({html}));\n"
            % (json.dumps(os.path.join(_REM, "src", "runtime", "uiSurface")), json.dumps(page), content_js))
        outf = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--outfile=" + outf,
                            "--log-level=error"], cwd=_REM, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", outf], cwd=_REM, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])["html"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@_NEEDS_NODE
def test_the_chart_plots_real_numbers_and_invents_none():
    """Both halves of the primitive's own rule, checked on what it draws rather than on what it says."""
    given = _markup("{title: 'Reports', items: ['a','b'], series: [3, 9, 4, 12, 7]}")
    assert "<polyline" in given, "a chart given five real numbers drew no line"
    withheld = _markup("{title: 'Reports', items: ['a','b']}")
    assert "<polyline" not in withheld, "a chart with no data drew a trend line anyway"
    # a single point is not a trend either — two points make a line, one makes a claim
    one = _markup("{title: 'Reports', items: ['a'], series: [7]}")
    assert "<polyline" not in one, "one number was drawn as a curve"
    # and rubbish in the series is dropped rather than plotted as zero
    junk = _markup("{title: 'R', items: ['a'], series: [1, null, 'x', NaN, Infinity, 4, 6]}")
    assert "NaN" not in junk and "Infinity" not in junk, "a non-finite value reached the plotted path"
    assert "<polyline" in junk, "the three real numbers in the series were thrown away with the rubbish"


def test_the_carousel_does_not_put_an_empty_chart_on_centre_stage():
    src = open(os.path.join(_REM, "src", "shots", "SurfaceCarousel.tsx"), encoding="utf-8").read()
    assert "series?: number[]" in src, "a Surface still cannot be given chart data"
    assert "series: s.series" in src, "the carousel accepts `series` and never passes it to the surface"
    body = src[src.index("const wanted ="):src.index("const content:")]
    assert "'chart'" in body and "hasData" in body, (
        "the page rotation no longer skips the chart for a surface with no data:\n%s" % body)
    assert "isFinite" in body, (
        "`hasData` accepts a series of nulls — the chart would draw the empty plate for it")


def test_glowpick_can_be_given_the_chart_it_is_allowed_to_ask_for():
    """It exposes `page`, so an author may choose `'chart'`. Without a way to supply numbers that choice
    could only ever produce the empty plate — a prop that guarantees a defect when used."""
    src = open(os.path.join(_REM, "src", "shots", "GlowPick.tsx"), encoding="utf-8").read()
    assert "series?: number[]" in src, "GlowPick offers the chart page and no prop to fill it"
    # the prop must reach the SURFACE, not merely be destructured — `series: SERIES` also appears in the
    # parameter list, so matching that string alone passes on a register that accepts the numbers and drops
    # them, which is the same empty plate with an extra prop in the manifest.
    content = src[src.index("const content: UiContent ="):]
    content = content[:content.index("\n")]
    assert "series" in content, "GlowPick accepts `series` and never passes it on: %s" % content
