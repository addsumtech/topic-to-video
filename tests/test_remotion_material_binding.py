"""theme.style -> MATERIAL binding, both tiers (the half-closed 'design gap' fix).

The deck's chosen visual style used to reach only the GRADE (Finish.tsx) + the R3F light MOOD (ThreeScene)
— never the element SURFACE, so a brutalism deck and a glassmorphism deck rendered the identical glass card
(and the identical matte-plastic mesh). This binds style -> panel material (CSS-3D, both the shot tier
elements.tsx AND the legacy Camera.tsx) and style -> mesh material (R3F). These source-guards lock the
binding in place (no other test greps for it, so a revert to the hardcoded recipe would pass the suite) and
lock the DEFAULT byte-identical to the prior look so an unstyled deck (e.g. the golden-film fixture) never
regresses."""
import os
import re

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_SKILL, "remotion", "src")


def _read(*p):
    return open(os.path.join(_SRC, *p), encoding="utf-8").read()


# ── CSS-3D panel (shot tier) ──────────────────────────────────────────────────────────────────────────
def test_panel_material_is_style_bound_in_elements():
    src = _read("stage", "elements.tsx")
    assert "panelMaterial" in src, "panelMaterial helper is gone — panel reverted to a hardcoded recipe"
    assert "theme.style" in src, "elements.tsx no longer branches on theme.style for the panel surface"
    # a real vocabulary, not one recipe: the key style families must each have a distinct recipe
    for k in ("brutalism", "noir", "blueprint", "glassmorphism", "claymorphism", "swiss", "terminal"):
        assert re.search(r"\b%s:" % k, src), "panel material map is missing the '%s' style recipe" % k
    # the panel div must actually CONSUME the recipe (not compute it and drop it)
    assert "mat.background" in src and "mat.boxShadow" in src and "mat.border" in src, \
        "the panel div no longer applies the resolved material (background/border/boxShadow)"


def test_panel_default_is_byte_identical_glass():
    # unstyled / unknown style must fall back to the EXACT prior glass recipe (no fixture regression).
    src = _read("stage", "elements.tsx")
    assert "linear-gradient(158deg, ${bg}f2 0%, ${bg}cc 100%)" in src, "the default glass background changed"
    assert "0 54px 150px rgba(0,0,0,0.62)" in src, "the default glass boxShadow changed"
    assert "return R[theme.style] || GLASS" in src, "unknown style no longer falls back to GLASS"


def test_legacy_camera_tier_shares_the_same_recipe():
    # the legacy `layers` tier (Camera.tsx PlaneContent) must not be left on the hardcoded glass while the
    # shot tier gets style — both tiers reuse the one exported helper so two decks look like two films EVERYWHERE.
    src = _read("Camera.tsx")
    assert "panelMaterial" in src, "Camera.tsx PlaneContent still hardcodes the glass panel (style ignored)"
    assert "linear-gradient(158deg" not in src, "Camera.tsx still inlines the old glass gradient"


# ── R3F mesh material (true-3D tier) ──────────────────────────────────────────────────────────────────
def test_r3f_material_is_style_bound():
    src = _read("three", "ThreeScene.tsx")
    assert "STYLE_TO_MATERIAL3D" in src, "R3F meshes no longer bind theme.style to material"
    for k in ("brutalism", "noir", "blueprint"):
        assert re.search(r"\b%s:\s*\{" % k, src), "STYLE_TO_MATERIAL3D missing the '%s' surface" % k
    # brutalism = flat-shaded matte; noir = metal; blueprint = wireframe — the three must be distinct kinds
    assert "flatShading: true" in src, "no flat-shaded (matte-graphic) material — brutalism/swiss regressed"
    assert "wireframe: true" in src, "no wireframe material — blueprint line-render regressed"
    assert re.search(r"metalness:\s*0\.[89]", src), "no metallic material — noir/artdeco metal regressed"
    # the meshes must CONSUME the resolved material, not keep the old hardcoded literals
    assert "metalness={m.metalness}" in src and "wireframe={m.wireframe}" in src, \
        "bars/stack meshes no longer apply the resolved material"
    assert "mat={mat3d}" in src, "the resolved style material is not threaded into the meshes"


def test_r3f_default_material_is_the_prior_look():
    # DEFAULT_MAT3D must equal the old hardcoded {metalness:0.1, roughness:0.55} so an unstyled 3D scene
    # (golden-film / any unknown style) renders byte-identical.
    src = _read("three", "ThreeScene.tsx")
    m = re.search(r"DEFAULT_MAT3D:\s*Mat3D\s*=\s*\{metalness:\s*0\.1,\s*roughness:\s*0\.55\}", src)
    assert m, "DEFAULT_MAT3D is no longer the prior {0.1, 0.55} — unstyled 3D scenes would change"
