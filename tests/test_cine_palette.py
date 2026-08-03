"""Backstops for the cinematic GENERALISATION engine (scripts/cine_palette.py): one deck accent + a template
key deterministically derives the per-beat colour worlds, so any topic re-skins any template with no
hand-authored colour. Guards: determinism, valid hex, accent actually re-colours, aurora page well-formed."""
import os
import re
import sys

import pytest

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_SKILL, "scripts"))
import cine_palette as cp  # noqa: E402

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_TPLS = ["command-surface", "ignition-monument", "aurora-bloom", "liquid-model", "molten-ledger", "defrag",
         "doorway-gallery", "rakelight", "exploded-schematic"]  # all 9 — none may fall to the generic default


@pytest.mark.parametrize("tpl", _TPLS)
def test_derive_returns_valid_palettes(tpl):
    pals = cp.derive("#7c5cff", tpl, 6)
    assert len(pals) == 6
    for p in pals:
        assert _HEX.match(p["bg"]) and _HEX.match(p["accent"]) and _HEX.match(p["ink"])
        assert isinstance(p["blobs"], list) and all(_HEX.match(b) for b in p["blobs"])
        assert p["light"] in ("dark", "light")


def test_deterministic():
    assert cp.derive("#20c997", "molten-ledger", 5) == cp.derive("#20c997", "molten-ledger", 5)


def test_accent_actually_recolours():
    """The whole point: a different accent yields different colour worlds (generalisation, not a fixed look)."""
    a = cp.derive("#7c5cff", "ignition-monument", 5)
    b = cp.derive("#e0a020", "ignition-monument", 5)
    assert [p["accent"] for p in a] != [p["accent"] for p in b]
    assert a[0]["bg"] != b[0]["bg"]  # bg keeps the accent's temperature


def test_aurora_bloom_is_a_light_film():
    pals = cp.derive("#2dd4bf", "aurora-bloom", 4)
    assert all(p["light"] == "light" for p in pals)
    # a light ground (high luminance bg)
    r, g, b = cp._hex(pals[0]["bg"])
    assert (r + g + b) / 3 > 0.85


def test_all_templates_have_bespoke_palettes_no_fallback():
    # every catalogue template must map to its OWN palette function — none may silently route to _default
    # (which would render a wrong-colour generic aurora and collapse the catalogue's variety).
    assert cp.TEMPLATE_KEYS == set(cp._TEMPLATES), "a template key has no bespoke palette (falls to _default)"


def test_unknown_template_falls_back_not_crashes():
    pals = cp.derive("#ff6b4a", "no-such-template", 3)
    assert len(pals) == 3 and _HEX.match(pals[0]["accent"])


def test_bad_accent_fails_loud():
    with pytest.raises(ValueError):
        cp.derive("not-a-hex", "defrag", 3)


def test_aurora_page_is_wellformed_and_carries_content():
    pal = cp.derive("#e0a020", "molten-ledger", 7)[2]
    html = cp.aurora_page(pal, "/skill", "/out", title="收入", kicker="Q3", grad_words="翻倍", sub="核实每个数字")
    assert "<!doctype html>" in html and "aurora" in html and "seek.js" in html
    assert "收入" in html and "翻倍" in html and "Q3" in html
    assert "background-clip:text" in html  # the gradient-word clip (the bug we fixed)


def test_color_helpers_roundtrip():
    assert _HEX.match(cp.rot("#7c5cff", 120))
    assert _HEX.match(cp.complement("#20c997"))
    assert cp.setl("#7c5cff", 0.5) != "#7c5cff"


# ── the INSTANTIATOR: a template contributes STRUCTURE (arc/signature/transition), not just colour ──────
def test_storyboard_skeleton_gives_structure():
    sk = cp.storyboard_skeleton("command-surface", "#7c5cff", 5)
    assert len(sk) == 5
    assert sk[0]["is_signature"] and sk[-1]["is_signature"], "signature beat on first AND last frame"
    assert all(b.get("archetype") and b.get("palette") and "transition" in b for b in sk)
    assert sk[0]["transition"] == "none", "the first beat has no transition-IN"


def test_skeleton_archetypes_are_all_valid():
    import validate as _v
    for t in cp._TEMPLATES:
        for b in cp.storyboard_skeleton(t, "#20c997", 6):
            assert b["archetype"] in _v._ARCHETYPES, "%s: unknown archetype %r" % (t, b["archetype"])


def test_skeleton_preserves_arc_opening_and_close():
    # proportional sampling keeps the arc's first + last archetype at the film's first + last beat
    for t, spec in cp._ARCS.items():
        sk = cp.storyboard_skeleton(t, "#7c5cff", 4)
        assert sk[0]["archetype"] == spec["arc"][0] and sk[-1]["archetype"] == spec["arc"][-1]


def test_every_template_has_an_arc():
    assert set(cp._ARCS) == set(cp._TEMPLATES), "every template needs a beat-arc for the instantiator"


def test_derive_never_returns_empty():
    for t in cp._TEMPLATES:
        assert len(cp.derive("#7c5cff", t, 3)) == 3


def test_substrate_templates_may_be_mono_by_design():
    # defrag/rakelight/exploded are DELIBERATELY a fixed substrate (variety = archetype/light, not hue). This
    # is not a bug — guard that they still return valid palettes so nobody "fixes" the single-substrate away.
    import json as _j
    for t in ("defrag", "rakelight", "exploded-schematic"):
        pals = cp.derive("#7c5cff", t, 5)
        assert len({_j.dumps(p, sort_keys=True) for p in pals}) >= 1 and _HEX.match(pals[0]["bg"])
