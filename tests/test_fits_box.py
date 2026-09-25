"""`fitsBox` — is this text readable in a box this size?

The rule it replaces is a fixed width floor, and a fixed floor is a floor for ONE string at ONE size. In a
register whose boxes change width for the whole shot that is not a rule at all: `SameStuffChanged` gated its
cell names on `w > U * 0.05`, and a 70px sliver kept its seven-glyph name, which the browser then set one
glyph per line. Both settled frames were correct; only the frames between them were wrong.

These probe BOTH directions. A predicate that only ever says "no" passes every "did it stack?" test ever
written and ships a register with no labels at all, so the cases that must fit are as load-bearing as the
cases that must not.
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


def _run(body):
    tmp = tempfile.mkdtemp(prefix="fits_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        open(entry, "w", encoding="utf-8").write(
            "import {fitsBox} from %s;\nconst out: any = {};\n"
            % json.dumps(os.path.join(_REM, "src", "runtime", "layout"))
            + body + "\nconsole.log(JSON.stringify(out));\n")
        outf = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--outfile=" + outf,
                            "--log-level=error"], cwd=_REM, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", outf], cwd=_REM, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# The two advances `wrapLines` measures with, so every number below is computed rather than guessed.
# A first draft of this file asserted both of these from intuition and both expectations were wrong while
# the helper was right — which is its own lesson about probes written without doing the arithmetic.
_CJK, _LATIN = 1.05, 0.72                       # ems per glyph: layout.CJK_FIT_ADVANCE, wrapLines' `adv`


@_NEEDS_NODE
def test_the_floor_is_two_glyphs_and_it_is_probed_on_both_sides():
    """At 24px two CJK glyphs need 2 x 1.05 x 24 = 50.4px. 50px must refuse and 51px must accept: a floor
    only means something if the frame on each side of it behaves differently."""
    assert abs(2 * _CJK * 24 - 50.4) < 1e-9
    out = _run(
        "out.just_under = fitsBox('四个汉字', 24, 50, 400);\n"
        "out.just_over  = fitsBox('四个汉字', 24, 51, 400);\n")
    assert out["just_under"] is False, "a column too narrow for two glyphs is accepted; the text will stack"
    assert out["just_over"] is True, (
        "one pixel of extra room is still refused — the predicate is saying no to everything, which ships a "
        "register with no labels at all and passes every stacking test ever written")


@_NEEDS_NODE
def test_the_case_that_shipped_with_the_registers_own_padding():
    """Seven CJK glyphs at 23px in a 70px cell, padded the way SameStuffChanged pads: inner 39.8px against
    a two-glyph need of 48.3px. This is the frame that rendered as a vertical column of characters."""
    out = _run(
        "out.sliver = fitsBox('追不回,进诚实缺口', 23, 70, 500, 30.24, 38.9);\n"
        "out.roomy  = fitsBox('追不回,进诚实缺口', 23, 400, 500, 30.24, 38.9);\n"
        "out.one_glyph_in_a_narrow_box = fitsBox('留', 23, 30, 500);\n")
    assert out["sliver"] is False, "the seven-glyph name still fits the 70px cell, so it will stack again"
    assert out["roomy"] is True, "the same name is refused a cell with ten times the room it needs"
    assert out["one_glyph_in_a_narrow_box"] is True, (
        "a ONE-glyph name is refused in a box that holds it — the two-glyph floor must be asked of the "
        "string's own length, not applied to strings that have no second glyph")


@_NEEDS_NODE
def test_latin_and_cjk_get_their_own_answer_at_the_same_box():
    """A CJK glyph is 1.05em and a Latin one 0.72em, so at 24px two of them need 50.4px and 34.6px. One
    advance for both is the guess the library's own wrap model exists to replace, and it is wrong by ~46%
    in whichever direction it is tuned. A 40px box sits between the two answers."""
    assert 2 * _LATIN * 24 < 40 < 2 * _CJK * 24
    out = _run(
        "out.cjk   = fitsBox('四个汉字', 24, 40, 400);\n"
        "out.latin = fitsBox('four words here', 24, 40, 400);\n")
    assert out["cjk"] is False, "full-width glyphs are being measured at the Latin advance"
    assert out["latin"] is True, (
        "Latin is being measured at the CJK advance, so half the library's English labels would vanish")


@_NEEDS_NODE
def test_a_box_that_is_wide_enough_and_too_short_is_still_refused():
    """Width was the defect that shipped, so height is the one that would be left out of the fix."""
    out = _run(
        "out.tall_enough = fitsBox('一段需要换行才放得下的说明文字', 24, 200, 400);\n"
        "out.too_short   = fitsBox('一段需要换行才放得下的说明文字', 24, 200, 40);\n")
    assert out["tall_enough"] is True, "wrapped text no longer fits a box with room for it"
    assert out["too_short"] is False, "a wrapped block taller than its box is accepted and overflows it"


@_NEEDS_NODE
def test_it_refuses_rather_than_throwing_on_the_empty_and_absent_cases():
    out = _run(
        "out.empty = fitsBox('', 24, 400, 400);\n"
        "out.no_text = fitsBox(undefined as any, 24, 400, 400);\n"
        "out.zero_width = fitsBox('文字', 24, 0, 400);\n"
        "out.zero_font = fitsBox('文字', 0, 400, 400);\n"
        "out.negative = fitsBox('文字', 24, -50, 400);\n")
    for k, v in out.items():
        assert v is False, "%s should be a quiet false, not %r — a label needs a box to be drawn in" % (k, v)


@_NEEDS_NODE
def test_a_blank_label_is_not_a_label():
    """`'   '` is a truthy string that wraps to one line and fits any box, so the first version said TRUE and
    the caller drew a padded ground with nothing on it. Found by probing this helper adversarially after it
    had shipped, not by any gate."""
    out = _run(
        "out.spaces = fitsBox('   ', 24, 400, 400);\n"
        "out.tab = fitsBox('\\t\\n', 24, 400, 400);\n"
        "out.padded_real = fitsBox('  \u6587\u5b57  ', 24, 400, 400);\n")
    assert out["spaces"] is False, "a run of spaces is accepted as a label"
    assert out["tab"] is False, "whitespace characters are accepted as a label"
    assert out["padded_real"] is True, (
        "a real label with incidental whitespace is refused — the trim must clean the ends, not reject them")
