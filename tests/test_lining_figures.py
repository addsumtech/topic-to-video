"""Digits sit on one baseline at one height, in every register — `runtime/fonts.ts` and the fallback stacks.

THE RULE. The person this pipeline works for has ruled out old-style (text) figures twice — digits that
drop below the baseline and rise above the x-height, so "3,457,689" bobs ("忽上忽下不是很美观") — and asked
for it to be enforced in the build, because it recurred while nothing detected it. It recurred here too:
Playfair Display, the editorial DNA's display face, ships old-style figures by default, and a register audit
found EdStat's hero number and TallyLedger's total bobbing.

WHAT HOLDS IT. Two things, each checked here:
  * `runtime/fonts.ts` switches the `lnum` feature on for every element, so a face that HAS lining figures
    (Playfair, Bodoni Moda, Source Serif 4) uses them whatever a register sets inline.
  * No stack may fall back to a face with old-style digits and no `lnum` (Georgia, Palatino, Iowan Old Style,
    Hoefler Text, Constantia) BEFORE a bundled face — so a standalone preview with no DNA cannot render one.
Every bundled face must either draw lining digits by default or carry `lnum`; that is read from the font
files themselves, so a face added later is held to it on the day it is added.
"""
import glob
import os
import re

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_FONTS = os.path.join(_ROOT, "assets", "fonts")
_SRC = os.path.join(_ROOT, "remotion", "src")

OLDSTYLE_SYSTEM = ("Georgia", "Palatino", "Palatino Linotype", "Iowan Old Style", "Hoefler Text", "Constantia")


def _digit_profile(path):
    from fontTools.ttLib import TTFont
    from fontTools.pens.boundsPen import BoundsPen
    t = TTFont(path, lazy=True)
    feats = {fr.FeatureTag for fr in t["GSUB"].table.FeatureList.FeatureRecord} if "GSUB" in t else set()
    cmap, gs = t.getBestCmap(), t.getGlyphSet()
    bounds = {}
    for ch in "0123456789":
        g = cmap.get(ord(ch))
        if not g:
            continue
        p = BoundsPen(gs)
        gs[g].draw(p)
        if p.bounds:
            bounds[ch] = p.bounds
    return feats, bounds


def test_every_bundled_face_can_set_lining_digits():
    pytest.importorskip("fontTools")
    bad = []
    for f in sorted(glob.glob(os.path.join(_FONTS, "*.ttf"))):
        feats, b = _digit_profile(f)
        if not b:
            continue
        upm_span = max(v[3] for v in b.values()) - min(v[1] for v in b.values())
        lows = [v[1] for v in b.values()]
        highs = [v[3] for v in b.values()]
        # lining: every digit spans (about) the same band; old-style: the 3/4/5/7/9 descend, the 6/8 ascend
        oldstyle = (max(lows) - min(lows)) > 0.12 * upm_span or (max(highs) - min(highs)) > 0.12 * upm_span
        if oldstyle and "lnum" not in feats:
            bad.append(os.path.basename(f))
    assert not bad, "bundled faces with old-style digits and no `lnum` to switch them: %r" % bad


def test_the_runtime_switches_lining_figures_on_for_every_element():
    src = open(os.path.join(_SRC, "runtime", "fonts.ts"), encoding="utf-8").read()
    code = re.sub(r"//[^\n]*", "", src)
    assert re.search(r"\*\s*,\s*\*::before\s*,\s*\*::after\s*\{\s*font-feature-settings:\s*\"lnum\"\s*1\s*!important", code), (
        "runtime/fonts.ts no longer turns `lnum` on for every element — an inherited body rule is not enough, "
        "because the inline `font` shorthand most registers use resets it")


def test_no_register_overrides_the_feature_setting():
    """`!important` beats an inline shorthand, but a register writing its own feature settings would be the
    one place the rule silently stops holding — so there must be none."""
    hits = []
    for f in glob.glob(os.path.join(_SRC, "**", "*.tsx"), recursive=True):
        if "fontFeatureSettings" in open(f, encoding="utf-8").read():
            hits.append(os.path.relpath(f, _SRC))
    assert not hits, "these set fontFeatureSettings and may switch lining figures off: %r" % hits


def test_no_stack_falls_back_to_an_oldstyle_face_before_a_bundled_one():
    """In a font stack, the first face that EXISTS renders. Georgia before any bundled face means a preview
    with no DNA sets its digits in Georgia, which has no `lnum` table for the runtime rule to switch on."""
    bundled = {"Playfair Display", "Source Serif 4", "Bodoni Moda", "Inter", "Space Grotesk", "JetBrains Mono",
               "IBM Plex Sans", "IBM Plex Mono", "Baloo 2", "Bangers", "Noto Sans SC", "Noto Serif SC"}
    bad = []
    for f in sorted(glob.glob(os.path.join(_SRC, "**", "*.tsx"), recursive=True)):
        if "__probe" in f:
            continue
        for n, line in enumerate(open(f, encoding="utf-8"), 1):
            for m in re.finditer(r"""(?:var\(--f-[a-z]+,\s*)?((?:["']?[A-Z][\w ]+["']?\s*,\s*)+(?:serif|sans-serif|monospace))""", line):
                faces = [x.strip().strip("'\"") for x in m.group(1).split(",")]
                for face in faces:
                    if face in bundled:
                        break
                    if face in OLDSTYLE_SYSTEM:
                        bad.append("%s:%d %s" % (os.path.relpath(f, _SRC), n, m.group(1)[:80]))
                        break
    assert not bad, "stacks that reach an old-style face before any bundled one:\n" + "\n".join(bad)
