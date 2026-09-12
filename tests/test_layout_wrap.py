"""How many lines a string takes — the number every type fit in this library divides by.

`fitBlockPx` counted lines as `ceil(totalWidth / measure)`. That ratio is only right when a glyph is small
relative to the measure, and for CJK it never is: a Han glyph is a full em, so a 766px measure at 198px
holds THREE of them, not 3.87. Eleven glyphs were counted as three lines, the browser drew four, and the
fourth line went into the caption band — measured on KineticManifesto at 1:1, 117px in. These pin the
counter against the cases that separate breaking from dividing.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
REMOTION = os.path.join(os.path.dirname(_HERE), "remotion")
RUNTIME = os.path.join(REMOTION, "src", "runtime")


def run_probe(body):
    if not shutil.which("npx") or not shutil.which("node"):
        pytest.skip("npx/node unavailable")
    if not os.path.isdir(os.path.join(REMOTION, "node_modules")):
        pytest.skip("remotion/node_modules not installed")
    tmp = tempfile.mkdtemp(prefix="layout_probe_")
    try:
        entry = os.path.join(tmp, "probe.tsx")
        open(entry, "w", encoding="utf-8").write(
            "import * as L from %s;\nconst out: any = {};\n" % json.dumps(os.path.join(RUNTIME, "layout"))
            + body + "\nconsole.log(JSON.stringify(out));\n")
        out = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--external:react",
                            "--external:remotion", "--outfile=" + out, "--log-level=error"],
                           cwd=REMOTION, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", out], cwd=REMOTION, capture_output=True, text=True,
                           env=dict(os.environ, NODE_PATH=os.path.join(REMOTION, "node_modules")))
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_a_full_em_glyph_is_counted_by_breaking_not_by_dividing():
    """THE CASE THAT MOTIVATED IT. Eleven Han glyphs at 198px in a 766px measure: three fit on a line
    (3 x 198 = 594; a fourth would need 792), so it is FOUR lines. The ratio says 11 x 1.05 x 198 / 766 =
    2.99 -> 3, and a fit that believes three draws the fourth over the subtitle."""
    r = run_probe("""
      const text = '在授权目录里真正动文件';
      out.lines = L.wrapLines(text, 198, 766);
      out.ratio = Math.ceil(L.textWidthPx(text, 198) / 766);
      out.perLine = Math.floor(766 / (198 * 1.05));
    """)
    assert r["lines"] == 4, "counted %r lines for eleven glyphs that fit three to a line" % r["lines"]
    assert r["ratio"] == 3, (
        "the ratio no longer under-counts this case, so it is not the control it was written to be")


def test_latin_breaks_at_a_space_and_a_short_line_is_one():
    r = run_probe("""
      out.short = L.wrapLines('Ship it', 44, 900);
      out.two   = L.wrapLines('Draft the brief and pull the numbers before Friday', 44, 620);
      out.empty = L.wrapLines('', 44, 900);
      out.blank = L.wrapLines('   ', 44, 900);
    """)
    assert r["short"] == 1
    assert r["two"] >= 2, "a sentence twice its measure came back as %r line(s)" % r["two"]
    assert r["empty"] == 1 and r["blank"] == 1, "an empty string must still occupy one line, not zero"


def test_a_word_longer_than_its_measure_still_terminates_and_breaks():
    """A Latin run with no space in it cannot break at a space, and the first version of this loop had
    nowhere to go. It must break mid-word rather than return 1 and let the caller reserve a single line for
    something five lines tall."""
    r = run_probe("""
      out.long = L.wrapLines('Supercalifragilisticexpialidocious', 60, 200);
      out.url  = L.wrapLines('https://example.com/a/very/long/path/that/never/breaks', 40, 300);
    """)
    assert r["long"] >= 2, "an unbreakable word wider than its measure came back as %r line(s)" % r["long"]
    assert r["url"] >= 2


def test_more_room_never_means_more_lines():
    """Monotonicity is what makes a bisection on the measure safe, and `fitBlockPx` is exactly that."""
    r = run_probe("""
      const t = '它自主拆解任务、在你授权的目录里真正动文件，并把重复动作沉淀成可复用的技能';
      out.series = [240, 360, 480, 640, 820, 1080, 1400].map((w) => L.wrapLines(t, 40, w));
    """)
    s = r["series"]
    assert s == sorted(s, reverse=True), "line count is not monotone in the measure: %r" % s
    assert s[0] > s[-1], "widening the measure sevenfold changed nothing: %r" % s


def test_the_fit_uses_the_same_counter_it_reasons_about():
    """`fitBlockPx` and a caller that needs the block's HEIGHT must agree on the line count, or the caller
    reserves for a different block than the one the fit chose. KineticManifesto asks `wrapLines` with the
    size `fitBlockPx` returned, in the same measure — this pins that the fit is built on it."""
    src = open(os.path.join(RUNTIME, "layout.ts"), encoding="utf-8").read()
    body = src[src.index("export const fitBlockPx"):]
    body = body[:body.index("\n};")]
    assert "wrapLines(" in body, "fitBlockPx no longer counts lines with wrapLines — the two can now disagree"
    assert "Math.ceil((units * px) / width)" not in body, "the ratio is back inside the fit"
