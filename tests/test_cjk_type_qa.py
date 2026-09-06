"""cjk_type_qa — does a register's TYPE still hold together when the copy is Chinese?

The defect this gate exists for shipped in a real film and every other gate was green: `text_safe_qa` asks
whether type falls OFF the canvas, and these registers set Chinese copy INTO itself while staying entirely
inside the frame. The tests below pin the parts that can rot silently — the fixture generator, the CJK
leading floor, and above all the CONTROL contract, because this instrument produced a false positive and a
false negative before it produced a finding worth acting on.
"""
import json
import os
import re
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import cjk_type_qa as c          # noqa: E402


# ── the fixture generator: it must actually feed each register its own props ────────────────────────
def test_props_are_shaped_from_the_register_s_own_signature():
    props, untestable = c.cjk_props("MagazineSpread")
    assert set(props) >= {"sectionLabel", "title", "headline", "deck"}, props
    assert not untestable, untestable
    assert all(c._ROLE and isinstance(v, str) for v in props.values())


def test_a_role_gets_copy_of_the_length_that_actually_wraps():
    """A tagline that fits on one line tests nothing — the collision only appears once a line wraps."""
    assert len(c._string_for("tagline")) > 20
    assert len(c._string_for("kicker")) <= 6
    assert c._string_for("headline") == c._TITLE


def test_object_shaped_array_props_are_written_out_not_guessed():
    props, untestable = c.cjk_props("TimelineTravel")
    assert "nodes" in props and isinstance(props["nodes"][0], dict) and "label" in props["nodes"][0]
    assert not untestable, "a shape this gate cannot feed must be REPORTED, not silently skipped"


def test_every_register_in_the_library_can_be_fed_chinese():
    """The first sweep left 14 registers UNTESTED because their object-shaped props had no fixture — and the
    gate's own doctrine says a register nobody can feed is exactly where this defect hides. Each shape is
    written from the register's own type declaration, because a WRONG shape renders nothing and would read
    as 'this register is fine in Chinese'."""
    import glob
    names = sorted(os.path.basename(f)[:-4]
                   for f in glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx")))
    assert len(names) > 140
    holes = {n: c.cjk_props(n)[1] for n in names}
    holes = {n: v for n, v in holes.items() if v}
    assert not holes, "no CJK copy can be shaped for: %r" % holes


def test_a_table_prop_is_routed_before_the_plain_list_rule():
    """`string[][]` also startsWith `string[]`. Routed by the flat rule, TermTable took a list of strings,
    threw `(r ?? []).map is not a function`, and reported as a RENDER FAILURE — a fixture bug wearing a
    register's name. Five more 'failures' were the same class."""
    props, _ = c.cjk_props("TermTable")
    assert isinstance(props["rows"][0], list), props["rows"][:1]


def test_image_props_are_never_fed_chinese_text():
    """KSpaceAnatomy declares srcK / srcLow / srcHigh. An exact-match skip on 'src' fed all three a Chinese
    sentence as a URL and the register 'failed to render'."""
    props, _ = c.cjk_props("KSpaceAnatomy")
    assert not [k for k in props if k.startswith("src")], props


def test_an_unfeedable_prop_is_reported_rather_than_passing_silently(monkeypatch):
    monkeypatch.setitem(c._ARRAY_SHAPES, "nodes", None)
    monkeypatch.delitem(c._ARRAY_SHAPES, "nodes")
    _, untestable = c.cjk_props("TimelineTravel")
    assert "nodes" in untestable, "a register nobody can feed is exactly where this defect hides"


def test_colours_and_images_are_not_fed_chinese():
    props, _ = c.cjk_props("MetaballMerge")
    assert "accent" not in props and "accent2" not in props


# ── the CJK leading floor, in the runtime the registers actually import ─────────────────────────────
def _cjk_type_src():
    return open(os.path.join(_ROOT, "remotion", "src", "runtime", "cjkType.ts"), encoding="utf-8").read()


def test_the_floor_only_ever_raises_and_only_for_cjk():
    src = _cjk_type_src()
    assert "Math.max(latin, CJK_MIN_LEADING)" in src, "the floor must RAISE, never impose a value"
    assert "hasCJK" in src, "it must be decided by the COPY, not by a flag"
    m = re.search(r"CJK_MIN_LEADING = ([\d.]+)", src)
    assert m and 1.0 < float(m.group(1)) < 1.2, "a CJK em box abuts at 1.0; the floor sits just above it"


def test_latin_copy_keeps_the_register_s_own_typography():
    """A 0.82 stack is the POINT of a brutalist title. Raising every register would redesign every English
    film to repair a Chinese one."""
    src = _cjk_type_src()
    assert "fitIfCJK" in src
    assert "hasCJK(text) ? fit(" in src.replace("\n", " ").replace("  ", " "), \
        "fitIfCJK must return the base size untouched for Latin"


@pytest.mark.parametrize("register,call", [("BrutalistType", "leading([titleTop, titleBottom], 0.82)"),
                                           ("MagazineSpread", "leading(HEADLINE, 0.98)")])
def test_the_two_repaired_registers_still_go_through_the_floor(register, call):
    src = open(os.path.join(_ROOT, "remotion", "src", "shots", register + ".tsx"), encoding="utf-8").read()
    assert call in src, "%s stopped using the CJK leading floor" % register


# ── the CONTROL contract — the part that already failed twice ───────────────────────────────────────
def test_the_positive_control_is_synthetic_not_a_real_register():
    """The first controls were the two registers that had broken a film. They worked exactly once: repairing
    both made the controls report 'not caught', and the instrument could no longer show it detects anything."""
    assert c.CONTROLS_BAD == ["TypeCollisionProbe"], c.CONTROLS_BAD
    root = open(os.path.join(_ROOT, "remotion", "src", "Root.tsx"), encoding="utf-8").read()
    assert "TypeCollisionProbe" in root and "0.55" in root, \
        "the probe must exist and stay deliberately mis-set"
    assert "{F('TypeCollisionProbe'" in root, "the probe needs a composition or the control cannot render"


def test_the_repaired_registers_are_negative_controls_so_a_regression_shows_up():
    assert {"MagazineSpread", "BrutalistType"} <= set(c.CONTROLS_GOOD)


def test_kinetic_manifesto_is_a_negative_control_and_the_misdiagnosis_is_recorded():
    """It was condemned off ONE still — a mid-flythrough frame where the register deliberately blurs and
    scales past 1.9x — and swapped out of a film for a defect it does not have."""
    assert "KineticManifesto" in c.CONTROLS_GOOD
    assert "KineticManifesto" in c.__doc__ and "innocent" in c.__doc__


def test_the_overlap_is_measured_against_the_line_box_so_scale_cancels():
    """A register drawn inside a scaled or 3D-transformed container reports rects in SCALED pixels while
    getComputedStyle().fontSize stays unscaled. Measured against fontSize, the zoom itself read as a
    collision: InfiniteCanvas (a camera-zoomed canvas) was reported at 14px on '40px Inter' with visibly
    clean type, and three more findings had the same shape — 5 of the sweep's 6 were this artifact."""
    src = open(os.path.join(_ROOT, "remotion", "src", "runtime", "textSafe.tsx"), encoding="utf-8").read()
    assert "box * LEADING_OVERLAP_FRAC" in src, "the threshold must be relative to the LINE BOX"
    assert "size * LEADING_OVERLAP_FRAC" not in src, "a fontSize-relative threshold reads zoom as collision"
    assert "InfiniteCanvas" in src, "the case that proved it must travel with the fix"


def test_cartoon_pop_goes_through_the_floor_too():
    src = open(os.path.join(_ROOT, "remotion", "src", "shots", "CartoonPop.tsx"), encoding="utf-8").read()
    assert "leading(label, 0.9)" in src


def test_font_runs_are_grouped_into_lines_before_they_are_compared():
    """getClientRects() returns one rect per FONT RUN. A mixed CJK+Latin string is two runs on one baseline,
    and compared raw a folio reading `交付可验收的成果.CO — 01` was reported as a 31px collision."""
    src = open(os.path.join(_ROOT, "remotion", "src", "runtime", "textSafe.tsx"), encoding="utf-8").read()
    assert "SAME_LINE_FRAC" in src and "per FONT RUN" in src


# ── the static half: can any bundled face draw Chinese at all? ─────────────────────────────────────
def test_the_bundled_faces_are_measured_for_cjk_coverage():
    cov = c.bundled_cjk_coverage()
    if cov is None:
        pytest.skip("fontTools not installed")
    assert len(cov) >= 10, cov
    assert all(isinstance(h, bool) for _, h in cov)


def test_the_gate_says_so_when_no_bundled_face_can_draw_chinese():
    """The finding this records: fonts.ts bundles ten Latin faces and no CJK one, so every Chinese glyph is
    drawn by whatever the render machine has. Measured on one register across two DNAs whose display faces
    are as different as the library holds — English 1480 vs 1573px, Chinese 1383 vs 1383px."""
    src = open(os.path.join(_ROOT, "scripts", "cjk_type_qa.py"), encoding="utf-8").read()
    assert "1383" in src and "1573" in src, "the measurement that proves it must travel with the claim"
    assert "NONE of the %d bundled faces" in src


def test_the_withdrawn_dom_detector_is_recorded_not_silently_dropped():
    """`document.fonts.check()` counts fallbacks and returned true for Chinese in Space Grotesk; measuring
    against a sentinel stack false-positived on every monospace face. Both are recorded so the next person
    does not rebuild them."""
    src = open(os.path.join(_ROOT, "scripts", "cjk_type_qa.py"), encoding="utf-8").read()
    assert "WITHDRAWN" in src and "fonts.check()" in src
    dom = open(os.path.join(_ROOT, "remotion", "src", "runtime", "textSafe.tsx"), encoding="utf-8").read()
    assert "SENTINEL_FALLBACK" not in dom and "measureIn" not in dom, "the noisy detector must be gone"


# ── end to end: the instrument must separate its classes ───────────────────────────────────────────
@pytest.mark.skipif(not os.path.isdir(os.path.join(_ROOT, "remotion", "node_modules")),
                    reason="needs the remotion toolchain")
def test_controls_separate_the_classes():
    r = subprocess.run([sys.executable, os.path.join(_ROOT, "scripts", "cjk_type_qa.py"), "--controls"],
                       capture_output=True, text=True, cwd=_ROOT, timeout=900)
    assert "controls PASS" in r.stdout, r.stdout[-2000:]
