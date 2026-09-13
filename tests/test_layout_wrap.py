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


# ── the advance is a property of the FACE ───────────────────────────────────────────────────────────────
# Every fitter here carried ONE Han advance, 1.05, which is the proportional answer. In a monospace face a
# Han glyph occupies TWO CELLS, so it advances twice the Latin cell — 14% more. Under-measured that way,
# TermGitLog ran a commit message 345px off the frame, TensionScale centred a note 68px too wide on BOTH
# sides, and BlueprintGrid clipped a spec by 288px, all with `white-space: pre`/`nowrap` so none of them
# could wrap out of it.

def test_a_han_glyph_is_two_cells_in_a_monospace_face():
    r = run_probe("""
      out.proportional = L.textWidthPx('中', 100);
      out.mono = L.textWidthPx('中', 100, L.monoFit());
      out.latinMono = L.textWidthPx('a', 100, L.monoFit());
      out.cells = L.monoCells('中');
    """)
    assert r["cells"] == 2
    # the mono answer IS two cells of the mono advance — not a second, unrelated constant
    assert abs(r["mono"] - 2 * r["latinMono"]) < 1e-6, (
        "the mono Han advance (%r) is not twice the mono Latin cell (%r)" % (r["mono"], r["latinMono"]))
    assert r["mono"] > r["proportional"], (
        "a monospace Han glyph measured %r, no wider than the proportional %r — the face is being ignored"
        % (r["mono"], r["proportional"]))


def test_the_default_is_unchanged_so_no_existing_fit_moves():
    """The option exists to let a MONO caller say so. Every proportional caller must measure exactly what
    it measured before, or this change silently re-sizes 104 registers that never asked for it."""
    r = run_probe("""
      out.a = L.textWidthPx('在授权目录里真正动文件', 100);
      out.b = L.textWidthPx('在授权目录里真正动文件', 100, {cjk: L.CJK_FIT_ADVANCE});
      out.lines = L.wrapLines('在授权目录里真正动文件', 198, 766);
      out.linesExplicit = L.wrapLines('在授权目录里真正动文件', 198, 766, {cjk: L.CJK_FIT_ADVANCE});
    """)
    assert r["a"] == r["b"] and r["lines"] == r["linesExplicit"]


def test_a_mono_measure_wraps_sooner_than_a_proportional_one():
    """The whole point: the same string in the same box takes MORE lines in a monospace face.

    The box is chosen where the two answers straddle a line boundary, because most boxes do not: at 38px a
    900px measure holds 22 proportional Han glyphs and only 19 monospace ones, so 20 glyphs is one line by
    the proportional model and two by the real one. Picked deliberately — a width where both happen to
    round the same way would pass whatever the advance was, which is how this went unnoticed."""
    r = run_probe("""
      const s = [...'办公的产物本身就是文件，不是一段还要你二次加工的文字'].slice(0, 20).join('');
      out.n = [...s].length;
      out.prop = L.wrapLines(s, 38, 900);
      out.mono = L.wrapLines(s, 38, 900, L.monoFit());
    """)
    assert r["n"] == 20
    assert r["prop"] == 1, "the proportional model no longer fits 20 glyphs on a line; the case has moved"
    assert r["mono"] == 2, (
        "monospace wrapped %r glyphs to %r line(s) where two cells each needs 2 — the face is not reaching "
        "the wrap" % (r["n"], r["mono"]))


def test_the_prediction_side_asks_the_face_too():
    """`cjkAdvance` mirrors `latinAdvance`: same argument, same question, for the other script. Film.tsx
    predicts the CAPTION's wrap with it, and a terminal DNA sets the caption in the mono stack."""
    r = run_probe("""
      out.prop = L.cjkAdvance('Inter, system-ui, sans-serif');
      out.mono = L.cjkAdvance('"JetBrains Mono", ui-monospace, monospace');
      out.monoLatin = L.latinAdvance('"JetBrains Mono", ui-monospace, monospace');
      out.none = L.cjkAdvance();
    """)
    assert r["prop"] == r["none"], "a face-less call must fall back to the proportional answer"
    assert abs(r["mono"] - 2 * r["monoLatin"]) < 1e-6
    assert r["mono"] > r["prop"]


def test_a_line_may_not_open_with_a_closing_mark():
    """CJK kinsoku: `wrapLines` broke "between any two glyphs", which is what the SCRIPT allows and not what
    a browser does.

    A line may not begin with a closing mark, so the browser carries the preceding glyph down with it and
    the block takes one line MORE than a naive per-glyph fill predicts. Found on `RealVersus` at 4:5, whose
    label carries four such marks: the reserve settled on four lines and ended 22px clear of the caption
    band, and the rendered label took five and closed 13px inside it — one line, to the half-pixel. Every
    Chinese reserve in this library divides by this function.
    """
    r = run_probe("""
      const punctuated = '它自己拆解任务、调用工具、改动文件，最后交出可验收的结果';
      const plain      = '自动拆解任务规划执行步骤并调用工具在授权目录真正动文';
      out.nPunct = [...punctuated].length;
      out.nPlain = [...plain].length;
      out.punct = L.wrapLines(punctuated, 30, 237.5);
      out.plain = L.wrapLines(plain, 30, 237.5);
      // the mark must travel WITH the glyph before it, never alone at the head of a line
      out.pair = L.wrapLines('工具、改', 30, 30 * 3.2);
    """)
    assert r["punct"] == 5, (
        "a 28-glyph label with four closing marks counted %r lines; the browser drew 5" % r["punct"])
    assert r["plain"] == 4, (
        "the same length WITHOUT punctuation counted %r — the rule must not inflate every string, only the "
        "ones a browser actually breaks differently" % r["plain"])
    assert r["punct"] > r["plain"], "punctuation made no difference, so the rule is not reaching the wrap"
    # three glyphs plus a mark in a box that holds 3.2 glyphs: the mark cannot open line 2, so its glyph
    # goes down with it and the answer is 2 rather than the 2 a naive fill would also give — pinned so a
    # future edit cannot quietly make the glue a no-op for short runs.
    assert r["pair"] == 2
