"""P1 backstop — the cinematic tier must LOAD the deck's bundled faces, portably.

The Remotion renderer only shows fonts that are system-installed OR loaded via @remotion/fonts. A CSS
font-family stack alone renders the real face ONLY on a machine that happens to have it installed and
silently falls back everywhere else — a portability bug that looks fine locally. So three things must
hold and are locked here (source-regex, like test_remotion_3d.py): the bundled files exist, fonts.ts
references them by their REAL basenames (the VF trap: SpaceGrotesk-VF.ttf, not SpaceGrotesk-Bold.ttf),
and Root.tsx actually calls loadDeckFonts() so the render blocks on the load. Proven at runtime by a
negative-control render (no .fonts/ -> 4 'could not load' warnings)."""
import os
import re

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONTS_DIR = os.path.join(_SKILL, "assets", "fonts")
_FONTS_TS = os.path.join(_SKILL, "remotion", "src", "theme", "fonts.ts")
_ROOT_TSX = os.path.join(_SKILL, "remotion", "src", "Root.tsx")

# family -> the EXACT bundled file (three variable fonts + one single-weight)
_EXPECTED = {
    "Space Grotesk": "SpaceGrotesk-VF.ttf",
    "Playfair Display": "PlayfairDisplay-VF.ttf",
    "JetBrains Mono": "JetBrainsMono-VF.ttf",
    "Bangers": "Bangers-Regular.ttf",
}


def test_bundled_font_files_exist():
    for f in _EXPECTED.values():
        assert os.path.isfile(os.path.join(_FONTS_DIR, f)), "missing bundled face %s" % f


def test_fonts_ts_references_real_basenames_and_families():
    src = open(_FONTS_TS, encoding="utf-8").read()
    for family, fname in _EXPECTED.items():
        assert family in src, "fonts.ts must register the '%s' family (matches theme.py's stack)" % family
        assert fname in src, "fonts.ts must load the real bundled file %s (the -VF trap)" % fname
    # the three variable fonts must register a weight RANGE so fontWeight 700/800 hit the real axis
    assert "100 900" in src, "variable faces need a '100 900' weight range, not a single weight"


def test_root_invokes_loadDeckFonts():
    """Wiring proof: loadDeckFonts must be imported AND called at Root module scope, or the render
    never blocks on the fonts and the tier silently falls back to machine fonts."""
    src = open(_ROOT_TSX, encoding="utf-8").read()
    assert "loadDeckFonts" in src and "from './theme/fonts'" in src, "Root.tsx must import loadDeckFonts"
    assert re.search(r"^loadDeckFonts\(\);", src, re.M), "Root.tsx must CALL loadDeckFonts() at module scope"


def test_copy_fonts_stages_bundled_faces(tmp_path):
    """_copy_fonts must stage the skill's assets/fonts/*.ttf into <out_dir>/.fonts/ (NOT read out_dir/assets)."""
    import sys
    sys.path.insert(0, os.path.join(_SKILL, "scripts"))
    import render_remotion as rr
    copied = rr._copy_fonts(str(tmp_path))
    for f in _EXPECTED.values():
        assert f in copied, "_copy_fonts must stage %s" % f
        assert os.path.isfile(tmp_path / ".fonts" / f)
