"""AcceptanceStamp — the register written FOR an argument the library could not draw.

A film about an office AI agent reached twice for the isometric conveyor, and the viewer's note was that a
factory line is the wrong world for this product. That is right in a way worth pinning: a belt says the
output is MANUFACTURED, stage after stage, each improving what the last one made. The argument it was
carrying is not sequential — two things must BOTH hold, in no order, and with one missing you do not get a
rougher deliverable, you get none.
"""
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
_SRC = os.path.join(_REM, "src", "shots", "AcceptanceStamp.tsx")

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _render(props, out, frame=145):
    pf = out + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(dict(props, dna="product"), fh, ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "AcceptanceStamp", out,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    return r.returncode, (r.stderr or "") + (r.stdout or "")


# ── the contract: a conjunction is exactly two ─────────────────────────────────────────────────────
@needs_toolchain
@pytest.mark.parametrize("conditions,why", [
    (["只有一个"], "one condition is not a conjunction — it drew an empty second card"),
    (["一", "二", "三"], "three is a list — the third was dropped without a word"),
    (["规划闭环", ""], "a blank condition is the same empty card by another route"),
])
def test_it_refuses_anything_that_is_not_two_conditions(tmp_path, conditions, why):
    rc, err = _render({"conditions": conditions, "result": "成果"}, str(tmp_path / "x.png"))
    assert rc != 0, why
    assert "exactly TWO" in err and "conjunction" in err, err[-400:]


@needs_toolchain
def test_two_conditions_and_the_bare_defaults_both_draw(tmp_path):
    rc, err = _render({"conditions": ["规划闭环", "动真实文件"], "result": "可验收的成果",
                       "stamp": "验收通过"}, str(tmp_path / "a.png"))
    assert rc == 0, err[-400:]
    rc, err = _render({}, str(tmp_path / "b.png"))
    assert rc == 0, "the register must still preview on its own defaults"


@needs_toolchain
def test_it_reflows_to_portrait(tmp_path):
    """Sizes come off Math.min(W, H), so the composition holds at 9:16 instead of assuming landscape."""
    rc, err = _render({"conditions": ["规划闭环", "动真实文件"], "result": "可验收的成果",
                       "stamp": "验收通过", "aspect": "9:16"}, str(tmp_path / "p.png"))
    assert rc == 0, err[-400:]
    sys.path.insert(0, os.path.join(_ROOT, "scripts"))
    import cjk_type_qa as c
    assert c._ink_fraction(str(tmp_path / "p.png")) > 0.01, "it drew almost nothing at portrait"


# ── the design rules this register is held to, like every other ────────────────────────────────────
def test_every_word_comes_from_a_prop_or_is_declared_intrinsic():
    src = open(_SRC, encoding="utf-8").read()
    assert "export const INTRINSIC_TEXT" in src, "the × operator belongs to the FORM and must be declared"
    assert "'×'" in src


def test_the_result_stays_empty_until_both_conditions_land():
    """The argument, drawn: with one condition missing the outline never fills. If this coupling is lost the
    register still looks fine and stops making its claim."""
    src = open(_SRC, encoding="utf-8").read()
    assert "Math.min(tickA, tickB)" in src, "the result must not lead the SECOND tick"


def test_it_sizes_off_the_short_side_not_a_px_literal():
    src = open(_SRC, encoding="utf-8").read()
    assert "const U = Math.min(W, H)" in src
    assert "leading(" in src, "author copy must go through the CJK leading floor"
