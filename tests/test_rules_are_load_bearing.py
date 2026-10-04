"""Every rule must be LOAD-BEARING: delete it and a probe must fail.

WHY THIS FILE EXISTS. An independent audit applied 29 mutations at once — each one reverting a behaviour
a repair commit claimed to have fixed — and the entire suite stayed green. The repairs were real; the
tests were not. Each pinned the specific case that had been reported, several by grepping source text,
so the RULE behind the case was free to be deleted.

The fix is not more tests, it is a different shape of test:

  PROBES[module][rule]   a callable given the module, which must raise if that rule is not working
  MUTANTS[module][name]  a (old, new) source edit that disables exactly one rule

Then two claims are checked mechanically, and the second is the one that matters:
  1. every probe passes on the real module
  2. every mutant is CAUGHT — at least one probe fails when it is applied

A mutant whose `old` text is not found raises immediately. That trap is not hypothetical: an earlier
hand-run of this exercise recorded a mutation as "survived" when the replacement had silently not applied
(`EN_TELLS = {} or {…}` evaluates to the original dict), which reads as a passing rule and is the same
class of lie this file exists to prevent.

Probes are written against SYNTHETIC inputs wherever possible, so one rule can be removed at a time. That
is why register_shot's sync-point check was refactored into `missing_rules(shot, sources, filenames)`:
reading the real repo can only ever tell you "something is wrong", never which rule noticed.
"""
import os
import re
import sys
import tempfile
import types

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(_HERE, "..", "scripts")
sys.path.insert(0, _SCRIPTS)

MODULE_PATH = {
    "register_shot": os.path.join(_SCRIPTS, "register_shot.py"),
    "shot_still_qa": os.path.join(_SCRIPTS, "shot_still_qa.py"),
    "frame_safe_qa": os.path.join(_SCRIPTS, "frame_safe_qa.py"),
    "shot_proof": os.path.join(_SCRIPTS, "shot_proof.py"),
    "voice_qa": os.path.join(_SCRIPTS, "voice_qa.py"),
    "shot_director": os.path.join(_SCRIPTS, "shot_director.py"),
    "film_energy_qa": os.path.join(_SCRIPTS, "film_energy_qa.py"),
    "text_safe_qa": os.path.join(_SCRIPTS, "text_safe_qa.py"),
    "register_energy": os.path.join(_SCRIPTS, "register_energy.py"),
    "band_debt": os.path.join(_SCRIPTS, "band_debt.py"),
    "prop_reach": os.path.join(_SCRIPTS, "prop_reach.py"),
    "cjk_type_qa": os.path.join(_SCRIPTS, "cjk_type_qa.py"),
    "measure_ground_luma": os.path.join(_SCRIPTS, "measure_ground_luma.py"),
    "measure_ground_reach": os.path.join(_SCRIPTS, "measure_ground_reach.py"),
    "demo_copy_qa": os.path.join(_SCRIPTS, "demo_copy_qa.py"),
    "energy_skeleton": os.path.join(_SCRIPTS, "energy_skeleton.py"),
    "ink_contrast_qa": os.path.join(_SCRIPTS, "ink_contrast_qa.py"),
}


def load(name, mutation=None):
    """The module, optionally with ONE source edit applied, exec'd into a fresh namespace.

    Never writes to the repo. A mutation whose `old` text is absent is an error, not a silent no-op.
    """
    path = MODULE_PATH[name]
    src = open(path, encoding="utf-8").read()
    if mutation is not None:
        old, new = mutation
        if old not in src:
            raise AssertionError("mutation text not found in %s: %r" % (name, old[:90]))
        src = src.replace(old, new, 1)
    mod = types.ModuleType(name)
    mod.__file__ = path
    exec(compile(src, path, "exec"), mod.__dict__)   # noqa: S102 — this is the point of the file
    return mod


# ── register_shot: the nine sync-point rules ─────────────────────────────────────────────────────────
# A COMPLETE synthetic registration for a shot called Zed. Each probe removes exactly one thing and
# asserts that exactly that rule is reported — which is impossible to test against the real repo.
def _zed_sources():
    return {
        "registry.ts": "import {Zed} from './shots/Zed';\nexport const REGISTRY = {\n  Alpha, Zed,\n};\n",
        "Root.tsx": "import {Zed, DURATION as D_ZED} from './shots/Zed';\n    {F('Zed', Zed, D_ZED)}\n",
        "shotLuma.ts": ("export type Lum = 'dark' | 'mid' | 'light';\n"
                        "export type GroundToken = 'bg' | 'bgGrad' | 'accent' | 'accent2' | 'surface';\n"
                        "  Zed: 'dark',\n  Zed: 'bgGrad',\n"),
        # shot_director carries BOTH the family letter and the idiom world; a registration missing
        # either one is incomplete, and the provenance half is the one that decays silently (an untagged
        # register is skipped by the idiom-world gate rather than refused).
        "shot_director.py": '    "Zed": "D",\n    "Zed": \'survey-archive\',\n',
        "LIBRARY.md": "12. **Zed** — a probe. *Use: probing.*\n",
    }


_ZED_BREAK = {
    "tsx_file": ("FILES", None),
    "registry_import": ("registry.ts", "import {Zed} from './shots/Zed';\n"),
    "registry_map": ("registry.ts", "  Alpha, Zed,\n"),
    "root_import": ("Root.tsx", "import {Zed, DURATION as D_ZED} from './shots/Zed';\n"),
    "root_preview": ("Root.tsx", "    {F('Zed', Zed, D_ZED)}\n"),
    "luma_coarse": ("shotLuma.ts", "  Zed: 'dark',\n"),
    "luma_ground": ("shotLuma.ts", "  Zed: 'bgGrad',\n"),
    "family": ("shot_director.py", '    "Zed": "D",\n'),
    "provenance": ("shot_director.py", '    "Zed": \'survey-archive\',\n'),
    "library_entry": ("LIBRARY.md", "12. **Zed** — a probe. *Use: probing.*\n"),
}


def _probe_sync_rule(rule):
    def probe(mod):
        src, files = _zed_sources(), ["Zed.tsx"]
        assert mod.missing_rules("Zed", src, files) == [], "a complete registration reports gaps"
        label, text = _ZED_BREAK[rule]
        if label == "FILES":
            files = ["Other.tsx"]
        else:
            src[label] = src[label].replace(text, "")
        missing = mod.missing_rules("Zed", src, files)
        assert rule in missing, "removing %s is not noticed (reported: %r)" % (rule, missing)
    return probe


def _probe_the_next_step_hint_names_both_emits(mod):
    """The scaffold writes a placeholder into SHOT_LUMA *and* DNA_GROUND_TOKEN, and each is written by a
    different mode of measure_ground_luma. The old hint named one command that measures and writes nothing,
    so following the tool's own instructions left the register flagged 'never measured' for ever — and
    test_shot_luma_is_measured_not_guessed then failed with no way to satisfy it."""
    hint = mod.next_steps("Zed")
    assert "--luma --emit" in hint, "the hint must name the SHOT_LUMA emit"
    assert "--only Zed --emit" in hint, "the hint must name the DNA_GROUND_TOKEN emit too"


def _probe_comments_are_not_code(mod):
    src, files = _zed_sources(), ["Zed.tsx"]
    src["registry.ts"] = src["registry.ts"].replace("  Alpha, Zed,\n", "  Alpha,\n  // Zed,\n")
    assert "registry_map" in mod.missing_rules("Zed", src, files), \
        "a COMMENTED-OUT registry entry still counts as registered"


def _probe_substring_is_not_registration(mod):
    src, files = _zed_sources(), ["Zed.tsx"]
    assert set(mod.missing_rules("Ze", src, files)) == set(mod.sync_patterns("Ze")), \
        "an id that is only a SUBSTRING of a registered one reads as registered"


def _probe_library_entry_not_a_cross_reference(mod):
    src, files = _zed_sources(), ["Zed.tsx"]
    src["LIBRARY.md"] = "12. **Other** — see also **Zed** for the sibling. *Use: x.*\n"
    assert "library_entry" in mod.missing_rules("Zed", src, files), \
        "a bold CROSS-REFERENCE inside another entry counts as this shot's catalogue entry"


def _probe_token_vocabulary_follows_the_type(mod):
    src, files = _zed_sources(), ["Zed.tsx"]
    # 'line' is NOT a GroundToken; the hardcoded alternation once accepted it and rejected 'bgGrad'.
    src["shotLuma.ts"] = src["shotLuma.ts"].replace("  Zed: 'bgGrad',", "  Zed: 'line',")
    assert "luma_ground" in mod.missing_rules("Zed", src, files), \
        "a value outside the GroundToken union is accepted as a ground token"
    src2 = _zed_sources()
    assert "luma_ground" not in mod.missing_rules("Zed", src2, files), "'bgGrad' is rejected"


def _probe_union_beats_the_fallback(mod):
    """The token vocabulary must come from the SOURCE, not from a hardcoded list.

    This needs a case where the two DISAGREE. With a synthetic file that declares the real union, the
    fallback is dead code and both "ignore the union" and "corrupt the fallback" survive every other
    probe — which is exactly what happened on this harness's first run.
    """
    src, files = _zed_sources(), ["Zed.tsx"]
    # (a) a union the fallback does not know about must still be honoured
    src["shotLuma.ts"] = ("export type Lum = 'dark' | 'mid' | 'light';\n"
                          "export type GroundToken = 'bg' | 'plate';\n"
                          "  Zed: 'dark',\n  Zed: 'plate',\n")
    assert "luma_ground" not in mod.missing_rules("Zed", src, files), \
        "a token declared by the union is rejected — the union is being ignored"
    # (b) with NO union in the file, the fallback is what decides, and it must be the REAL vocabulary
    src2 = dict(_zed_sources())
    src2["shotLuma.ts"] = "  Zed: 'dark',\n  Zed: 'line',\n"
    assert "luma_ground" in mod.missing_rules("Zed", src2, files), \
        "'line' is not a GroundToken, but the fallback vocabulary accepts it"
    src3 = dict(_zed_sources())
    src3["shotLuma.ts"] = "  Zed: 'dark',\n  Zed: 'bgGrad',\n"
    assert "luma_ground" not in mod.missing_rules("Zed", src3, files), \
        "'bgGrad' IS a GroundToken, but the fallback vocabulary rejects it"


def _probe_registry_insert_survives_its_own_output(mod):
    one = "export const REGISTRY = {\n  Alpha, Beta,\n};\n"
    once = mod.insert_registry_entry(one, "Zed")
    assert once and "\n  Zed,\n" in once
    twice = mod.insert_registry_entry(once, "Yed")      # the shape THIS function leaves behind
    assert twice and "\n  Yed,\n" in twice, "insertion works only once"
    assert mod.insert_registry_entry("export const OTHER = {\n};\n", "Zed") is None


PROBES = {
    "register_shot": dict(
        [("sync:" + r, _probe_sync_rule(r)) for r in _ZED_BREAK],
        comments_are_not_code=_probe_comments_are_not_code,
        substring_is_not_registration=_probe_substring_is_not_registration,
        library_entry_shape=_probe_library_entry_not_a_cross_reference,
        token_vocabulary=_probe_token_vocabulary_follows_the_type,
        union_beats_the_fallback=_probe_union_beats_the_fallback,
        registry_insert_idempotent=_probe_registry_insert_survives_its_own_output,
        next_step_names_both_emits=_probe_the_next_step_hint_names_both_emits,
    ),
}

# Each mutant disables exactly ONE rule. The pattern mutants are DERIVED FROM THE SOURCE rather than
# hand-written: seven hand-written ones did not match the file at all on the first run (raw-string
# escaping), which would have made them silent no-ops that "pass". test_every_mutant_text_still_exists
# is the backstop for that, and it fired immediately.
def _rule_line(src, rule):
    """The exact source line that defines `rule`'s pattern inside sync_patterns()."""
    for line in src.split("\n"):
        if line.strip().startswith('"%s":' % rule) and ("% (b" in line or "% b" in line):
            return line
    raise AssertionError("no pattern line for rule %r" % rule)


def _pattern_mutants():
    src = open(MODULE_PATH["register_shot"], encoding="utf-8").read()
    out = {}
    for rule in ("registry_import", "registry_map", "root_import", "root_preview",
                 "luma_coarse", "luma_ground", "family"):
        line = _rule_line(src, rule)
        out["%s pattern always matches" % rule] = (line, '        "%s": r"",' % rule)
    lib = _rule_line(src, "library_entry")
    out["library_entry accepts the id in bold anywhere"] = (lib, '        "library_entry": r"\\*\\*%s\\*\\*" % b,')
    return out


MUTANTS = {
    "register_shot": dict(
        _pattern_mutants(),
        **{
            "tsx_file check dropped":
                ('        if rule == "tsx_file":\n            if ("%s.tsx" % shot) not in list(filenames):',
                 '        if rule == "tsx_file":\n            if False:'),
            "comments are treated as code":
                ("        if not re.search(pat, _uncommented(src), re.M):",
                 "        if not re.search(pat, src, re.M):"),
            "ground-token vocabulary hardcoded wrongly again":
                ('_GROUND_FALLBACK = ("bg", "bgGrad", "accent", "accent2", "surface")',
                 '_GROUND_FALLBACK = ("bg", "surface", "accent", "accent2", "line", "fg")'),
            "union values ignored, fallback always used":
                ('    vals = re.findall(r"\'([^\']+)\'", m.group(1)) if m else []',
                 "    vals = []"),
            "registry insertion anchors on the last line's shape":
                ('    m = re.search(r"export const REGISTRY[^=]*=\\s*\\{", src)',
                 '    m = re.search(r"export const REGISTRY[^=]*=\\s*\\{\\n  \\w+, \\w+,\\n\\};", src)'),
        }
    ),
}


# ── frame-craft: shot_still_qa + frame_safe_qa ───────────────────────────────────────────────────────
DARK, LIGHT = (10, 12, 20), (236, 233, 226)


def _frame(mod, ground, ink, *, w=1920, h=1080, bleed=False, band=None, gradient=False, text=False):
    """A synthetic frame. `band`: None clean · 'covered' · 'half' · 'tone' (a flat plate) ."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), ground)
    d = ImageDraw.Draw(im)
    d.rectangle([int(w * .21), int(h * .19), int(w * .79), int(h * .57)], fill=ink)
    if gradient:
        for y in range(h // 2, h):
            v = int(ground[0] + (y - h // 2) / (h / 2) * 70)
            d.line([(0, y), (w, y)], fill=(v, v + 2, v + 10))
    bp = mod._caption_band_px(w, h)
    if band == "covered":
        d.rectangle([0, h - bp, w, h], fill=ink)
    if band == "half":
        d.rectangle([0, h - bp // 2, w, h], fill=ink)
    if band == "tone":
        # AWAY from the ground, in whichever direction has room. It only ever brightened, so on a LIGHT
        # ground `c + 60` clamped at 255 and the "distinct plate" was the ground itself — the caption-bar
        # rule had never actually been exercised on a light film, and a new probe found it by failing.
        lift = 60 if sum(ground) / 3 < 128 else -60
        d.rectangle([0, h - bp, w, h], fill=tuple(max(0, min(255, c + lift)) for c in ground))
    if band == "filled-zone":
        # A register that COMPOSES TO FILL: content across the whole content zone, stopping exactly at the
        # band, which leaves the band as the film's OWN ground. The frame's overall median is then the
        # content, not the ground — the shape that made the previous rule return 1.0 on a correct frame.
        d.rectangle([0, int(h * .16), w, h - bp], fill=ink)
    if text:
        # Deliberately at the band's LEFT EDGE, inside the action-safe strip's x-range: ink drawn further
        # in proves nothing, because the strip only samples the outer ~3.5% of the width. A probe that
        # cannot see the rule it is testing is not a probe.
        d.rectangle([0, h - bp + 40, 900, h - 30], fill=ink)
    if bleed:
        d.rectangle([0, 0, int(w * .03), h], fill=ink)
        d.rectangle([0, 0, w, int(h * .03)], fill=ink)
    f = os.path.join(tempfile.mkdtemp(), "f.png")
    im.save(f)
    return f


def _probe_edge_on_both_grounds(mod):
    """Content is a DEPARTURE from the frame's own ground, not an absolute brightness.

    An absolute >=120 rule is only true on a dark film: every pixel of a light-ground shot clears it, so
    frame_safe_qa — a DELIVERY gate — reported 100% off-frame on every scene and a light film could never
    ship."""
    for ground, ink, label in [(DARK, (240, 240, 240), "dark"), (LIGHT, (20, 20, 20), "light")]:
        clean = mod.measure(_frame(mod, ground, ink))["edge"]
        over = mod.measure(_frame(mod, ground, ink, bleed=True))["edge"]
        assert clean <= mod.EDGE_FRAC_ERR, "%s ground: a clean frame reads as overflow (%.2f)" % (label, clean)
        assert over > mod.EDGE_FRAC_ERR, "%s ground: a real overflow is missed (%.2f)" % (label, over)


def _probe_caption_band_verdicts(mod):
    """Clean and a GRADIENT ground pass; half-covered, fully covered and a distinct plate are flagged.

    The two failures this replaced were opposite: treating any tone difference as coverage made a legit
    gradient a blocking error, and treating flatness as ground let a flat panel covering the whole band
    read as clean — the original inversion, restored."""
    f = mod.CAPTION_FRAC_ERR
    assert mod.measure(_frame(mod, DARK, (60, 200, 150)))["caption"] <= f, "a clean band is flagged"
    assert mod.measure(_frame(mod, DARK, (60, 200, 150), gradient=True))["caption"] <= f, \
        "a gradient ground is read as a covered band"
    assert mod.measure(_frame(mod, DARK, (60, 200, 150), band="half"))["caption"] > f, "half-covered passes"
    assert mod.measure(_frame(mod, DARK, (60, 200, 150), band="covered"))["caption"] > f, \
        "a band covered end to end reads CLEANER than one covered halfway"
    assert mod.measure(_frame(mod, DARK, (60, 200, 150), band="tone"))["caption"] > f, \
        "a distinct plate laid over the band — the separate caption strip the rule forbids — passes"


def _probe_caption_band_follows_the_frame(mod):
    """The reserved band is the renderer's, and it differs by aspect.

    This used to pin the two literals (200 / 150). That made the probe a copy of the constant rather than a
    test of the rule, so it broke the moment the renderer changed the band — reporting a failure in the QA
    when the QA was correctly following the renderer. It asserts the RELATIONSHIP now: a narrow frame wraps
    the caption to more lines and therefore reserves MORE than a wide one, and both must be tall enough to
    hold the caption type the renderer will actually draw.
    """
    narrow, wide = mod._caption_band_px(1080, 1920), mod._caption_band_px(1920, 1080)
    assert narrow > wide, "a narrow frame wraps to more lines and must reserve more, not less"
    assert wide > 2 * mod.caption_size_px(1920, 1080), "the band cannot hold two lines of its own caption"


def _probe_edge_excludes_the_caption_band(mod):
    """Ink in the caption band must not move the action-safe reading AT ALL.

    Asserting only that it stays under the threshold is too blunt to see the rule: band ink is diluted by
    the whole border sample and lands around 2%, under the 4.5% limit either way. The rule is EXCLUSION,
    so the test is equality — the same frame with and without ink in the band must read identically."""
    without = mod.measure(_frame(mod, DARK, (240, 240, 240)))["edge"]
    with_ink = mod.measure(_frame(mod, DARK, (240, 240, 240), text=True))["edge"]
    assert abs(with_ink - without) < 1e-9, \
        "ink in the caption band changes the action-safe reading (%.4f -> %.4f): the band is being swept" \
        % (without, with_ink)


def _fsq_dir(mod, **kw):
    d = tempfile.mkdtemp()
    kf = os.path.join(d, "_keyframes")
    os.makedirs(kf)
    import shot_still_qa as sq
    for i in range(2):
        src = _frame(sq, **kw)
        os.rename(src, os.path.join(kf, "scene_%02d.png" % (i + 1)))
    return d


def _probe_delivery_gate_on_both_grounds(mod):
    for ground, ink, label in [(DARK, (240, 240, 240), "dark"), (LIGHT, (20, 20, 20), "light")]:
        ok = mod.evaluate(_fsq_dir(mod, ground=ground, ink=ink))
        bad = mod.evaluate(_fsq_dir(mod, ground=ground, ink=ink, bleed=True))
        assert not ok["errors"] and not ok["warnings"], \
            "%s ground: a clean film draws a complaint (%r)" % (label, (ok["errors"] + ok["warnings"])[:1])
        # The border measure is ADVISORY now — it cannot tell a cut word from a full-bleed flood (see
        # frame_safe_qa's own comment), so it must still SEE a flooded border and must no longer block on it.
        assert bad["warnings"], "%s ground: a flooded border is not even reported" % label
        assert not bad["errors"], "%s ground: the border measure is blocking delivery again" % label


def _probe_a_filled_zone_is_not_a_caption_bar(mod):
    """A register that fills the content zone and stops at the band leaves the band as the FILM'S OWN
    ground — and the previous rule read exactly that as a laid-over panel, because both produce a hard step
    at the band's top edge. Measured on a real one: InOrder's band is uniformly 0.027, min == max ==
    median, nothing drawn on it, and the rule returned 1.0. As registers get denser it would have returned
    1.0 for all of them, filling band_debt.json with debt that is not there."""
    f = mod.CAPTION_FRAC_ERR
    for ground, ink in ((DARK, (90, 130, 235)), (LIGHT, (30, 40, 70))):
        assert mod.measure(_frame(mod, ground, ink, band="filled-zone"))["caption"] <= f, \
            "a content zone filled to the band edge is read as a caption bar"
    # and the thing the rule is actually for must still be caught, on both grounds
    assert mod.measure(_frame(mod, DARK, (60, 200, 150), band="tone"))["caption"] > f
    assert mod.measure(_frame(mod, LIGHT, (20, 24, 30), band="tone"))["caption"] > f


PROBES["shot_still_qa"] = {
    "a_filled_zone_is_not_a_caption_bar": _probe_a_filled_zone_is_not_a_caption_bar,
    "edge_on_both_grounds": _probe_edge_on_both_grounds,
    "caption_band_verdicts": _probe_caption_band_verdicts,
    "caption_band_follows_the_frame": _probe_caption_band_follows_the_frame,
    "edge_excludes_the_caption_band": _probe_edge_excludes_the_caption_band,
}
PROBES["frame_safe_qa"] = {"delivery_gate_on_both_grounds": _probe_delivery_gate_on_both_grounds}

MUTANTS["shot_still_qa"] = {
    "edge back to an absolute brightness":
        ("            bright += abs(px[x, y] - ground_all) > _EDGE_DELTA",
         "            bright += px[x, y] >= 120"),
    "edge threshold never fires": ("EDGE_FRAC_ERR = 0.045", "EDGE_FRAC_ERR = 9.9"),
    "caption threshold never fires": ("CAPTION_FRAC_ERR = 0.05", "CAPTION_FRAC_ERR = 9.9"),
    "any tone difference counts as coverage":
        ("    if abs(band_ground - ground_all) > _INK_DELTA and edge_step > _BAND_EDGE_STEP and not is_own_ground:",
         "    if abs(band_ground - ground_all) > _INK_DELTA:"),
    # The fourth version's own rule. Without it, every register that fills the content zone and leaves the
    # band as the film's ground reads as a caption BAR — measured 1.0 on InOrder, whose band is uniformly
    # 0.027, min == max == median, with nothing drawn on it at all.
    "a register's own ground counts as a caption bar":
        ("and edge_step > _BAND_EDGE_STEP and not is_own_ground:", "and edge_step > _BAND_EDGE_STEP:"),
    "coverage never detected":
        ("    if abs(band_ground - ground_all) > _INK_DELTA and edge_step > _BAND_EDGE_STEP and not is_own_ground:",
         "    if False:"),
    "band width no longer follows the frame":
        ("    return caption_band_px(w, h)", "    return 150"),
    "the caption band is swept as part of the border":
        ("    for y in range(m, cap_top, 2):                            # left + right strips, above the caption band",
         "    for y in range(m, h, 2):"),
}
MUTANTS["frame_safe_qa"] = {
    "delivery gate back to an absolute brightness":
        ("if abs(px[x, y] - ground) > INK_DELTA:", "if px[x, y] >= 120:"),
    "delivery gate threshold never fires": ("EDGE_FRAC_ERR = 0.045", "EDGE_FRAC_ERR = 9.9"),
}


# ── voice_qa: the rules an audit found unpinned ──────────────────────────────────────────────────────
def _probe_cv_is_a_ratio(mod):
    """CV is spread/mean, so scaling every sentence must not change it. Deleting `/ mean` turns the
    headline metric into a raw spread and no sample-based test notices."""
    # Capitalised on purpose: the Latin splitter needs whitespace-then-capital after a stop, so a
    # lowercase sample never splits and the probe would measure one sentence per beat.
    short = [(i, "One two. One two three.") for i in range(4)]
    longm = [(i, ("One " + "word " * 7).strip() + ". " + ("One " + "word " * 11).strip() + ".")
             for i in range(4)]
    a = mod.evaluate(short)["metrics"]["sentence_len_cv"]
    b = mod.evaluate(longm)["metrics"]["sentence_len_cv"]
    assert a > 0 and abs(a - b) < 0.06, "CV is not scale-invariant (%.3f vs %.3f): it is not a ratio" % (a, b)


def _probe_aphorism_looks_at_the_end(mod):
    """The rule is about how a beat LANDS. Reading any sentence makes it a duplicate of antithesis."""
    first = [(i, "差别不在它更聪明，而在真的跑了一遍。后来我们又补了一个用例。") for i in range(6)]
    last = [(i, "后来我们又补了一个用例。差别不在它更聪明，而在真的跑了一遍。") for i in range(6)]
    assert mod.evaluate(first)["metrics"]["aphorism_ending_share"] == 0.0, \
        "a figure in the FIRST sentence counts as an aphorism ENDING"
    assert mod.evaluate(last)["metrics"]["aphorism_ending_share"] > 0.5


def _probe_unit_follows_the_script(mod):
    assert mod._units("the code runs and it is wrong", mod.profile_for("latin")) == 7
    assert mod._units("这段代码能跑但是错的", mod.profile_for("han")) == 10


def _probe_unsupported_scripts_are_excluded_not_guessed(mod):
    """A script with no segmenter must leave the metrics alone — including the DENOMINATOR. Dividing by
    every beat while skipping some diluted the result by exactly the beats just declared excluded."""
    zh = [(i, "测试全是绿的。代码其实是错的。") for i in range(4)]
    mixed = zh + [(i + 4, "โค้ดทำงานได้ การทดสอบผ่าน") for i in range(4)]
    assert mod.evaluate(zh)["metrics"]["balanced_pair_share"] == 1.0
    assert mod.evaluate(mixed)["metrics"]["balanced_pair_share"] == 1.0, \
        "excluded beats are still in the denominator"
    for text in ("הקוד עובד. הבדיקות ירוקות.", "19.3 28.9 80", "🙂🙂🙂"):
        assert mod.profile_for(mod._script_of(text)).get("unsupported"), \
            "%r is being measured with the English rules" % text[:14]


def _probe_vocabulary_follows_each_beats_script(mod):
    """Running only the film's dominant list left an English beat inside a Chinese film unchecked."""
    mixed = [(i, "随着技术的不断发展，我们赋能业务。") for i in range(3)] + \
            [(3, "We must delve into the tapestry of this realm.")]
    v = mod.evaluate(mixed)["vocab"]
    assert any("delve" in k for k in v), "the English beat's slop is never checked (%r)" % sorted(v)
    assert any(k in ("商务黑话", "时代背景开场") for k in v), "the Chinese beats' slop is never checked"


def _probe_antithesis_needs_a_parallel_counterpart(mod):
    lat, han = mod.profile_for("latin"), mod.profile_for("han")
    assert mod._antithesis_pairs("The difference is not that it got smarter, but that something ran.", lat)
    assert mod._antithesis_pairs("差别不在它更聪明，而在真的跑了一遍。", han)
    assert not mod._antithesis_pairs("A crash reports itself, so you never miss it.", lat)
    assert not mod._antithesis_pairs("训练时默认没人真的跑一遍。", han)
    # matches the surface pattern, rejected ONLY by the parallelism ratio
    assert not mod._antithesis_pairs(
        "It measures how strong the tests are and how carefully they were reviewed, not correctness.", lat), \
        "a lopsided negation counts as the figure — the parallelism requirement is gone"


def _probe_latin_segmentation(mod):
    lat = mod.profile_for("latin")
    for text, n, why in [("It dropped to 19.3. That is real.", 2, "a sentence ending in a number"),
                         ("Use e.g. a checklist. Then run it.", 2, "e.g. before lowercase"),
                         ("We shipped it e.g. Redis. Then it broke.", 2, "abbreviation before a capital"),
                         ("Dr. Smith ran it twice. Nothing failed.", 2, "Dr."),
                         ("The U.S. Army shipped it. It broke.", 2, "a dotted initialism"),
                         ("pass@k fell 19.3 to 28.9 percent.", 1, "a decimal is not a stop")]:
        assert len(mod._sentences(text, lat)) == n, "%s: %r" % (why, mod._sentences(text, lat))


def _probe_thresholds_fire_on_the_right_side(mod):
    """Every threshold, both sides. Walks THRESHOLDS, so a rule added later is covered the same way."""
    fire = {
        "uniform_cv": ["测试是绿的。代码是错的。"] * 8,
        "connective": ["测试是绿的。代码是错的。"] * 8,
        "balanced": ["测试全是绿的。代码其实是错的。"] * 8,
        "antithesis": ["绿灯量的是测试有多强，而不是代码有多对。"] * 8,
        "aphorism": (["绿灯量的是测试有多强，而不是代码有多对。"] * 4 +
                     ["我们又跑了一遍，边界上差了一个等号，于是补了个用例。"] * 4),
        # The same short denial answering the previous beat, over and over. Varied ON PURPOSE — the defect
        # is the repeated SHAPE, not one phrase, so a probe of eight identical strings would pass a
        # detector that only matched a literal.
        # Eight beats, each ONE sentence, all about the same length: the uniformity is the beat plan's and
        # no rewrite of the prose can change it, which is what this threshold exists to say.
        "one_sentence_beats": ["它读的是你授权的目录。", "报告落在同一个文件夹。", "简历和清单分开放。",
                               "面试的问题从档案里出。", "追不到出处就标出来。", "改写之前先过一道闸。",
                               "每改一条就记一行。", "最后一步还是你自己选。"],
        "same_opener": ["不会。它在这里就停了。", "不能。那一块不许填。", "删不掉。只能标成撤回。",
                        "不是这样。它清点的是证据。", "没人再核对。后面全部继承它。",
                        "别急。先把地区问清楚。", "未必。要看它读到了什么。", "非也。收据拿不出来就不算。"],
    }
    quiet = ["这段代码是 AI 写的，能跑，测试全绿，但它其实是错的，而且没有任何提示。", "写崩的会当场报错。",
             "所以我们又跑了一遍，结果发现边界上差了一个等号，于是补了个用例。", "覆盖率只证明这行被执行过。",
             "因为出题的和判卷的是同一个来源，错误模式也一样，所以互相看不见对方的盲区。", "还没人做过受控比较。",
             "有个数字到处在传，但我们查了那份报告，里面根本没有它，所以别当结论。", "先弄坏它一次。"]
    quiet_fired = set(mod.evaluate([(i, t) for i, t in enumerate(quiet)])["fired"])

    # ...and the repeated-opener check must not count a LEGITIMATE short opener. A mutant that returns
    # True for any short leading unit survived every other probe here: these eight all open short and
    # none of them is the answering device, which is the distinction the whole signal rests on.
    short_but_fine = ["装一次，以后一句人话就进去了。", "第一站找岗，你给方向它给清单。",
                      "你挑中一条，就进第二站了。", "每改一条，它就往账本里追一行。",
                      "三审都过了，还得练。", "算了一下，一共五行。",
                      "开头那句，现在能回答了。", "四句人话，一轮就跑完了。"]
    assert "same_opener" not in set(mod.evaluate(
        [(i, t) for i, t in enumerate(short_but_fine)])["fired"]), (
        "the repeated-opener check counts any short opener, so it reports every brisk script and "
        "distinguishes nothing — the signal is the answering SHAPE, not brevity")
    # ...AND THE OTHER SIDE OF THE ONE THAT ROUTES ADVICE. `one_sentence_beats` does not decide WHETHER to
    # speak — `uniform_cv` does that — it decides WHICH advice is actionable. So the case that must not
    # fire is a script that is just as uniform and whose beats hold SEVERAL sentences: there the author
    # really can vary their prose, and being told the beat plan is at fault would send them to the wrong
    # layer. Both scripts below trip `uniform_cv`; only one of them is the beat plan's doing.
    multi = ["它读目录。它归档。它交一份成果。"] * 8
    multi_fired = set(mod.evaluate([(i, t) for i, t in enumerate(multi)])["fired"])
    assert "uniform_cv" in multi_fired, "the control script is not uniform, so it proves nothing"
    assert "one_sentence_beats" not in multi_fired, (
        "a uniform script whose beats hold three sentences each is blamed on the beat plan — the author "
        "is sent to change durations when the prose is what they can actually vary")

    assert set(fire) == set(mod.THRESHOLDS), \
        "a threshold has no boundary probe: %r" % (set(mod.THRESHOLDS) - set(fire))
    for key, beats in fire.items():
        got = set(mod.evaluate([(i, t) for i, t in enumerate(beats)])["fired"])
        assert key in got, "threshold %r never fires" % key
        assert key not in quiet_fired, "threshold %r fires on varied prose too" % key


PROBES["voice_qa"] = {
    "cv_is_a_ratio": _probe_cv_is_a_ratio,
    "aphorism_looks_at_the_end": _probe_aphorism_looks_at_the_end,
    "unit_follows_the_script": _probe_unit_follows_the_script,
    "unsupported_excluded": _probe_unsupported_scripts_are_excluded_not_guessed,
    "vocabulary_per_beat_script": _probe_vocabulary_follows_each_beats_script,
    "antithesis_parallelism": _probe_antithesis_needs_a_parallel_counterpart,
    "latin_segmentation": _probe_latin_segmentation,
    "thresholds_both_sides": _probe_thresholds_fire_on_the_right_side,
}

def _guard_mutants():
    """The two splitter guards, located in the SOURCE by a stable marker.

    Hand-writing these as Python literals failed twice on raw-string escaping, and a mutant whose text
    does not match is a silent no-op that reads as a passing rule.
    """
    src = open(MODULE_PATH["voice_qa"], encoding="utf-8").read()
    out = {}
    for marker, name in (("_ABBR, before, re.I):", "abbreviation guard removed"),
                         ("[A-Z]$\", before):", "initialism guard removed")):
        line = next(l for l in src.split("\n") if marker in l)
        out[name] = (line, "        if False:")
    return out


MUTANTS["voice_qa"] = {
    # The repeated-opener detector, both halves: the shape test and the SHORTNESS test. Widening it to
    # any short opener is the failure mode that matters — measured, that turned a real 19%->8% separation
    # into a muddy 41%->30%, because 「装一次，」 and 「第一站找岗，」 are perfectly good openers.
    "the repeated-opener check is blind to the denial":
        ('    pat = _DENY_OPEN["han"] if prof == "han" else _DENY_OPEN["latin"]\n    return bool(pat.match(m.group(1).strip()))',
         '    pat = _DENY_OPEN["han"] if prof == "han" else _DENY_OPEN["latin"]\n    return False'),
    "any short opener counts, not just an answering one":
        ('    pat = _DENY_OPEN["han"] if prof == "han" else _DENY_OPEN["latin"]\n    return bool(pat.match(m.group(1).strip()))',
         '    pat = _DENY_OPEN["han"] if prof == "han" else _DENY_OPEN["latin"]\n    return True'),
    "CV loses its denominator":
        ("    cv = (statistics.pstdev(sent) / statistics.mean(sent)) if len(sent) > 1 and statistics.mean(sent) else 0.0",
         "    cv = statistics.pstdev(sent) if len(sent) > 1 else 0.0"),
    "aphorism reads the FIRST sentence":
        ("        if ss and _antithesis_pairs(ss[-1], prof):", "        if ss and _antithesis_pairs(ss[0], prof):"),
    "units reversed": ('    if prof["unit"] == "char":', '    if prof["unit"] != "char":'),
    "excluded beats back in the denominator":
        ("    measured = len(beats) - len(unsupported_beats)", "    measured = len(beats)"),
    "unsupported scripts measured anyway":
        ("        if prof.get(\"unsupported\"):", "        if False:"),
    "unlisted scripts read as latin": ('        return "unknown"', '        return "latin"'),
    # The defect was that only ONE list ran — the film's dominant one — so an English beat inside a
    # Chinese film was never scanned. Dropping the `sc == script` filter instead runs BOTH lists over
    # every beat, which detects MORE, not less: a mutant has to reproduce the defect, not merely change
    # the line.
    "vocabulary back to the dominant list only":
        ('VOCAB_LISTS = {"han": ZH_TELLS, "latin": EN_TELLS}', 'VOCAB_LISTS = {"han": ZH_TELLS}'),
    "parallelism requirement removed": ("PARALLEL_RATIO = 3.0", "PARALLEL_RATIO = 999.0"),
    **_guard_mutants(),
    "uniform threshold never fires": ('"uniform_cv": 0.45', '"uniform_cv": 0.0'),
    "antithesis threshold never fires": ('"antithesis": 0.35', '"antithesis": 9.9'),
    "balanced threshold never fires": ('"balanced": 0.35', '"balanced": 9.9'),
    "connective threshold flipped":
        ('m["connective_share"] < THRESHOLDS["connective"]', 'm["connective_share"] > THRESHOLDS["connective"]'),
    "aphorism threshold never fires": ('"aphorism": 0.30', '"aphorism": 0.99'),
    "balanced tolerance collapsed": ("BALANCED_TOL = 0.30", "BALANCED_TOL = 0.00"),
}


# ── shot_proof: the pre-render judgements ────────────────────────────────────────────────────────────
_REN = "export const Zed: React.FC<{t?: string}> = ({ title: TITLE = 'Demo words' } = {}) => {"
_PLN = "export const Zed: React.FC<{t?: string}> = ({ title = 'Demo words' } = {}) => {"


def _probe_defaults_read_both_destructuring_forms(mod):
    """Only the RENAMED form was parsed, so this returned NOTHING for 72 of 136 registers and the
    demo-default rule — the module's headline reason for existing — was silent on half the library."""
    for src, label in ((_REN, "renamed"), (_PLN, "plain")):
        got = mod.defaults_from_source(src, "Zed")
        assert got.get("title") == "Demo words", "%s destructuring form is not parsed: %r" % (label, got)
    assert "TITLE" not in mod.defaults_from_source(_REN, "Zed"), "the alias comes back as a phantom prop"
    blind = [i for i in os.listdir(os.path.join(_SCRIPTS, "..", "remotion", "src", "shots"))
             if i.endswith(".tsx") and not mod.shot_defaults(i[:-4])]
    assert len(blind) < 25, "blind on %d registers" % len(blind)


def _board(slides, meta=None):
    return {"meta": dict({"renderer": "remotion"}, **(meta or {})), "slides": slides}


def _probe_demo_default_leak(mod):
    defs = mod.shot_defaults("CardFlip3D")
    assert defs.get("backLabel"), "cannot read a real register's defaults"
    leaked = _board([{"index": 0, "shot": "CardFlip3D", "narration": "x",
                      "shot_props": {"title": "t", "backLabel": defs["backLabel"],
                                     "items": [{"front": "a", "back": "b"}]}}])
    _e, w = mod.static_checks(leaked)
    assert any("DEMO DEFAULT" in x for x in w), "a register's demo default left in props is not reported"
    ok = _board([{"index": 0, "shot": "CardFlip3D", "narration": "x",
                  "shot_props": {"title": "t", "backLabel": "我们查到的",
                                 "items": [{"front": "a", "back": "b"}]}}])
    assert not any("DEMO DEFAULT" in x for x in mod.static_checks(ok)[1]), "real copy is reported as a default"


def _probe_duplicate_composition(mod):
    same = _board([{"index": i, "shot": "CardFlip3D", "narration": "x",
                    "shot_props": {"title": "t%d" % i, "backLabel": "b%d" % i,
                                   "items": [{"front": "f%d" % i, "back": "k%d" % i}]}} for i in range(3)])
    rep = [x for x in mod.static_checks(same)[1] if "same prop shape" in x]
    assert rep and "1, 2, 3" in rep[0], "three beats on one composition are not grouped: %r" % rep
    varied = _board([
        {"index": 0, "shot": "CardFlip3D", "narration": "x", "shot_props": {"title": "a"}},
        {"index": 1, "shot": "CardFlip3D", "narration": "x",
         "shot_props": {"title": "b", "backLabel": "c", "items": [{"front": "d", "back": "e"},
                                                                  {"front": "f", "back": "g"},
                                                                  {"front": "h", "back": "i"}]}}])
    assert not [x for x in mod.static_checks(varied)[1] if "same prop shape" in x], \
        "structurally different uses are reported as the same picture"


def _probe_topic_weld(mod):
    """A register must carry the ARGUMENT SHAPE with the topic in props. The check compares the film's
    PROSE against the register's STRING LITERALS: comparing whole sources caught JS keywords, and
    comparing every prop value caught hex colours and enum names."""
    real = _board([{"index": 0, "shot": "OverlapSeparation", "narration": "两条分布几乎完全重合在一起",
                    "shot_props": {}}])
    assert not [x for x in mod.static_checks(real)[0] if "hardcodes" in x], "a clean register is flagged"
    src = open(os.path.join(_SCRIPTS, "..", "remotion", "src", "shots", "OverlapSeparation.tsx"),
               encoding="utf-8").read()
    assert "两条分布几乎完全重合在一起" not in src                      # the control the probe relies on
    # The difference between "whole source" and "string literals" only shows on prose that collides with
    # CODE: an English script saying "we return the reverse order" hits `return`/`reverse` in every .tsx.
    code = _board([{"index": 0, "shot": "QuadSplit",
                    "narration": "The function should return the reverse order of the const values.",
                    "shot_props": {"heading": "return the reverse order of the const values"}}])
    assert not [x for x in mod.static_checks(code)[0] if "hardcodes" in x], \
        "prose that collides with JS keywords is reported as a welded topic"


def _probe_palette_is_an_arc(mod):
    data = [154.0, 39.0]
    assert mod._in_palette(120.0, data), "a blend of the two accents reads as off-system"
    assert mod._in_palette(154.0, data) and mod._in_palette(39.0, data)
    assert not mod._in_palette(207.0, data), "cyan-blue passes in a green/amber film"
    assert not mod._in_palette(280.0, data)


def _probe_dna_hues_survive_any_css_colour(mod):
    assert mod._dna_hues({"meta": {"design_dna": {"accent": "#c33", "accent2": "rebeccapurple"}}}) == [0.0]
    assert mod._dna_hues({"meta": {}}) is not None


def _probe_dead_frame_needs_off_centre(mod):
    """Narrow ALONE is not the defect: seven beats of a real film were narrow and dead-centre — a title,
    a cube, a counter — and flagging on width reported 11 of 37."""
    import shot_still_qa as sq
    from PIL import Image, ImageDraw

    def box(x0, x1):
        im = Image.new("RGB", (1920, 1080), (10, 12, 20))
        ImageDraw.Draw(im).rectangle([x0, 300, x1, 700], fill=(200, 200, 200))
        f = os.path.join(tempfile.mkdtemp(), "f.png")
        im.save(f)
        return mod._content_box(f)
    _, _, wide = box(200, 1720)
    cx0, cx1, narrow = box(790, 1190)          # centre 990: inside tolerance, but NOT exactly 960, so
                                              # setting OFFSET_FRAC to 0 changes the verdict
    ox0, ox1, off = box(120, 520)
    assert wide > mod.NARROW_FRAC
    assert narrow < mod.NARROW_FRAC and abs((cx0 + cx1) / 2 - 960) / 1920 <= mod.OFFSET_FRAC
    assert off < mod.NARROW_FRAC and abs((ox0 + ox1) / 2 - 960) / 1920 > mod.OFFSET_FRAC


def _probe_empty_frame_is_an_error(mod):
    from PIL import Image
    f = os.path.join(tempfile.mkdtemp(), "f.png")
    Image.new("RGB", (1920, 1080), (10, 12, 20)).save(f)
    assert mod._content_box(f)[2] == 0.0, "a frame with nothing on it reports content"


PROBES["shot_proof"] = {
    "defaults_both_forms": _probe_defaults_read_both_destructuring_forms,
    "demo_default_leak": _probe_demo_default_leak,
    "duplicate_composition": _probe_duplicate_composition,
    "topic_weld": _probe_topic_weld,
    "palette_is_an_arc": _probe_palette_is_an_arc,
    "dna_hues_robust": _probe_dna_hues_survive_any_css_colour,
    "dead_frame_needs_off_centre": _probe_dead_frame_needs_off_centre,
    "empty_frame": _probe_empty_frame_is_an_error,
}

def _plain_form_mutant():
    """Delete the PLAIN destructuring pattern, located in the source.

    Written by hand this literal broke the test file twice on backslash escaping — and a mutant that does
    not parse is not a mutant."""
    s = open(MODULE_PATH["shot_proof"], encoding="utf-8").read()
    line = next(l for l in s.split("\n") if "[a-z]\\w*" in l and "(?<![:" in l)
    return {"only the renamed destructuring form is parsed": (line, "            ]")}


MUTANTS["shot_proof"] = {
    **_plain_form_mutant(),
    "demo-default comparison dropped":
        ("                if isinstance(val, str) and val.strip() == dv.strip():",
         "                if False:"),
    "duplicate grouping never reports":
        ("            if common and len(base & set(shape)) / len(common) >= PROPS_SAME:",
         "            if False:"),
    "duplicate grouping reports everything":
        ("PROPS_SAME = 0.80", "PROPS_SAME = 0.0"),
    # NOT MUTATED, and the reason is recorded rather than hidden: comparing the film's prose against the
    # register's STRING LITERALS instead of its whole source has no observable difference today. The
    # false positive it was added for ('return', 'reverse' reaching the topic set from a beat carrying a
    # code sample) is now impossible for a second reason — the topic set takes CJK runs and multi-word
    # PHRASES, and a lone code token can no longer enter it at all. The narrower comparison is kept as
    # defence for the day the topic set widens again, but it cannot be probed, so no mutant claims it is.
    "palette compares to the endpoints only":
        ("    if len(accents) >= 2:", "    if False:"),
    "dead frame flags on width alone": ("OFFSET_FRAC = 0.06", "OFFSET_FRAC = 0.0"),
}


# ── shot_director: the plan actually reaching the beat it belongs to ─────────────────────────────────
def _plan_board(n=6):
    return ({"meta": {"renderer": "remotion"},
             "slides": [{"index": i, "narration": "x", "duration": 5.0, "audio": "a.mp3"} for i in range(n)]},
            {"beats": [{"id": i + 1, "visual_intent": ["statement", "metric", "contrast", "list",
                                                       "structure", "sequence"][i]} for i in range(n)]})


def _probe_plan_offset_is_decided_once(mod):
    """content_plan beat ids are 1-BASED and scene indices 0-BASED.

    Looking a scene up by its own index missed beat 1 and handed every other scene the PREVIOUS beat's
    plan — its intent, its climax flag — silently. And deciding the offset PER SCENE does not fix it,
    because scene indices 1..N are themselves valid beat ids, so the wrong branch keeps winning."""
    board, plan = _plan_board()
    mod.assign_shots(board, plan)
    want = {b["id"]: b["visual_intent"] for b in plan["beats"]}
    for s in board["slides"]:
        fit = s.get("shot_fit") or {}
        got = fit.get("assigned_by", "")
        if got.startswith("intent "):
            assert got == "intent '%s'" % want[s["index"] + 1], \
                "scene %d got %r, the plan says %r" % (s["index"], got, want[s["index"] + 1])
    assert {(s.get("shot_fit") or {}).get("plan_matched_by") for s in board["slides"]} == {"id = index + 1"}


def _probe_zero_based_plan_still_matches(mod):
    """A 0-based plan must still line up — the fix is an offset, not a hardcoded +1."""
    board, plan = _plan_board()
    for b in plan["beats"]:
        b["id"] -= 1
    mod.assign_shots(board, plan)
    assert {(s.get("shot_fit") or {}).get("plan_matched_by") for s in board["slides"]} == {"id"}
    want = {b["id"]: b["visual_intent"] for b in plan["beats"]}
    for s in board["slides"]:
        got = (s.get("shot_fit") or {}).get("assigned_by", "")
        if got.startswith("intent "):
            assert got == "intent '%s'" % want[s["index"]]


def _probe_every_beat_records_that_nobody_judged(mod):
    """The deterministic path cannot judge whether a register carries an argument. Leaving the field
    ABSENT made 'assigned mechanically' indistinguishable from 'considered and found to fit'."""
    board, plan = _plan_board()
    mod.assign_shots(board, plan)
    for s in board["slides"]:
        fit = s.get("shot_fit")
        assert isinstance(fit, dict) and fit.get("verdict") == "unjudged", \
            "scene %d records no unjudged verdict: %r" % (s["index"], fit)
        assert fit.get("why") and fit.get("assigned_by")


PROBES["shot_director"] = {
    "plan_offset_decided_once": _probe_plan_offset_is_decided_once,
    "zero_based_plan_matches": _probe_zero_based_plan_still_matches,
    "records_unjudged": _probe_every_beat_records_that_nobody_judged,
}

MUTANTS["shot_director"] = {
    "offset decided per scene again":
        ("        if _offset is not None and (scene_index + _offset) in _by_id:",
         "        if scene_index in _by_id:"),
    # "Hardcoded +1" means the 0-BASED case stops being detected, leaving the offset always 1. Mutating
    # the second branch instead changes nothing, because a 0-based plan takes the first one and works.
    "offset hardcoded to +1":
        ("    if _by_id and _scene_ix and set(_by_id) == _scene_ix:", "    if False:"),
    "the unjudged record is dropped":
        ('        s["shot_fit"] = {"verdict": "unjudged",', '        s["_dropped"] = {"verdict": "unjudged",'),
}


# ── film_energy_qa: the three floors that make "this could have been HTML" a red number ─────────────
# The measurement needs ffmpeg and a real film; the RULES do not. These probes hand `check()` a
# synthesised measurement, so a floor can be disabled one at a time and the failure names which one.
# The end-to-end claim — that the instrument separates a real slideshow from a real film — is proved
# against rendered fixtures in tests/test_film_energy_qa.py, not here.
_SLIDESHOW = {"seconds": 163.0, "motion_p50": 0.0004, "motion_p75": 0.0023, "motion_p90": 0.0085,
              "ink_median": 0.043, "luma_range": 0.079, "luma_steps": 0.000, "luma_windows": 163,
              "declared_seconds": 163.0, "frames": 1956, "fps": 12, "decode_rc": 0, "decode_stderr": ""}
_ALIVE = {"seconds": 81.0, "motion_p50": 0.0181, "motion_p75": 0.0481, "motion_p90": 0.1169,
          "ink_median": 0.361, "luma_range": 0.903, "luma_steps": 0.425, "luma_windows": 81,
          "declared_seconds": 81.0, "frames": 972, "fps": 12, "decode_rc": 0, "decode_stderr": ""}
# The gaming case, MEASURED: the delivered film with four seconds of a blank white rectangle appended. Every
# other frame identical; the luminance RANGE goes from 0.097 to 0.910 and clears its floor by 6.7x.
_GAMED = {"seconds": 60.0, "motion_p50": 0.0005, "motion_p75": 0.0025, "motion_p90": 0.0089,
          "ink_median": 0.047, "luma_range": 0.910, "luma_steps": 0.017, "luma_windows": 60,
          "declared_seconds": 60.0, "frames": 720, "fps": 12, "decode_rc": 0, "decode_stderr": ""}


def _energy(mod, measurement, board=None):
    """Run check() over a temp out_dir with `measurement` substituted for the real ffmpeg pass."""
    import json as _json
    d = tempfile.mkdtemp()
    open(os.path.join(d, "out.mp4"), "wb").write(b"\0")           # existence is all check() asks of it
    if board is not None:
        _json.dump(board, open(os.path.join(d, "storyboard.json"), "w", encoding="utf-8"))
    mod.measure = lambda path: measurement
    return mod.check(d)


def _probe_slideshow_fails_all_three(mod):
    errs, _warns, _m = _energy(mod, _SLIDESHOW)
    blob = " ".join(errs)
    # DENSITY left this list when its floor retired — it reports instead of gating. The axes that still
    # hold a defensible floor still gate, and a slideshow must still trip every one of them.
    for word in ("MOTION", "LIGHT"):
        assert word in blob, "a film measured at slideshow level was not flagged for %s: %r" % (word, errs)


def _probe_a_bright_passage_is_not_a_luminance_arc(mod):
    """One flat white block moves the RANGE to Figma's own number while nothing in the film changes."""
    errs, _warns, _m = _energy(mod, _GAMED)
    assert any("LIGHT ARC" in e for e in errs), (
        "a film whose light moves once in sixty seconds passed the light gate: %r" % errs)


def _probe_a_real_film_passes(mod):
    # The POSITIVE control. Without it, floors raised until nothing can pass would read as a working
    # gate — the same failure as a gate that never fires, wearing the opposite costume.
    errs, _warns, _m = _energy(mod, _ALIVE)
    assert not errs, "a measured launch film fails the floors derived from it: %r" % errs


def _probe_floors_stay_under_every_reference(mod):
    for name, (motion, ink, luma, steps) in mod.REFERENCE.items():
        assert mod.MOTION_P75_FLOOR <= motion, "%s sits under the motion floor" % name
        assert mod.INK_FLOOR <= ink, "%s sits under the ink floor" % name
        assert mod.LUMA_RANGE_FLOOR <= luma, "%s sits under the light floor" % name
        assert mod.LUMA_STEP_FLOOR <= steps, "%s sits under the light-arc floor" % name


def _probe_a_blank_waiver_is_not_a_waiver(mod):
    errs, _warns, _m = _energy(mod, _SLIDESHOW, board={"meta": {"energy_waiver": "   "}})
    assert errs, "an empty `energy_waiver` waived the gate — a waiver must carry a reason"


def _probe_a_written_waiver_downgrades_to_warning(mod):
    errs, warns, _m = _energy(mod, _SLIDESHOW, board={"meta": {"energy_waiver": "a held single frame, by design"}})
    assert not errs and warns, "a reasoned waiver must accept the film and keep the numbers visible"


def _probe_a_waiver_does_not_absolve_axes_it_never_named(mod):
    """The hole this closes shipped: a reasoned DENSITY waiver silently excused a MOTION failure that
    appeared later from an unrelated change."""
    errs, warns, _m = _energy(mod, _SLIDESHOW, board={"meta": {"energy_waiver": {"density": "sparse by design"}}})
    assert any(e.startswith("MOTION") for e in errs), "an axis nobody reasoned about must stay gated"
    assert any("DENSITY" in w for w in warns), "the named axis IS waived, and says so"


def _probe_a_missing_film_is_not_a_pass(mod):
    errs, _warns, _m = mod.check(tempfile.mkdtemp())
    assert errs, "no out.mp4 reported as clean — an unmeasured film is not a passing film"


def _probe_an_undecodable_film_is_not_a_pass(mod):
    d = tempfile.mkdtemp()
    open(os.path.join(d, "out.mp4"), "wb").write(b"\0")
    mod.measure = lambda path: None
    errs, _warns, _m = mod.check(d)
    assert errs, "a film that could not be decoded reported as clean"


def _probe_a_film_too_short_to_measure_is_not_a_pass(mod):
    d = tempfile.mkdtemp()
    open(os.path.join(d, "out.mp4"), "wb").write(b"\0")
    mod.measure = lambda path: 5                       # an INT = decoded, but only 5 sampled frames
    errs, _warns, _m = mod.check(d)
    assert errs, "a half-second clip reported as a clean film"
    assert any("frame" in e for e in errs), "the error does not say the film was too SHORT: %r" % errs


def _probe_the_sampling_frame_follows_the_films_shape(mod):
    """A portrait film must be sampled portrait. Squashing it to 192x108 undercounts its ink."""
    seen = {}

    class R:
        returncode, stdout, stderr = 0, "1080,1920,\n", ""

    def run(cmd, **kw):
        if "ffprobe" in cmd[0]:
            return R()
        seen["vf"] = cmd[cmd.index("-vf") + 1]
        out = R()
        out.stdout = b""
        return out
    mod.subprocess = types.SimpleNamespace(run=run)
    mod.measure(os.path.join(tempfile.mkdtemp(), "x.mp4"))
    assert "scale=" in seen.get("vf", ""), seen
    w, h = [int(v) for v in seen["vf"].split("scale=")[1].split(":")[:2]]
    assert h > w, "a 1080x1920 film was sampled %dx%d — landscape, so its ink is undercounted" % (w, h)


def _probe_the_density_report_names_the_next_command(mod):
    """A gate that stops at a number teaches an author to waive it — and the density axis no longer even
    has a number to fail. Its floor retired with the metric that could not tell a drawn frame from a
    blurred blank one (a film's emptiest beat scored its second densest), and what replaced it REPORTS:
    the film's own distribution, the beats at the bottom of it, and the command that names denser
    registers in each beat's own design family. The rule this pins is unchanged — say what to do next —
    it has simply moved from an error to a measurement that cannot be waived because it never blocked."""
    errs, warns, _m = _energy(mod, _SLIDESHOW)
    assert not [e for e in errs if e.startswith("DENSITY")], (
        "density is measured, not gated; it must not be back to erroring: %r" % errs)
    hit = [w for w in warns if "DENSITY" in w]
    assert hit, warns
    assert "density_advice" in hit[0], "the density report names no next command: %r" % hit[0]


PROBES["film_energy_qa"] = {
    "density_report_names_the_next_command": _probe_the_density_report_names_the_next_command,
    "a_bright_passage_is_not_an_arc": _probe_a_bright_passage_is_not_a_luminance_arc,
    "short_film_is_not_a_pass": _probe_a_film_too_short_to_measure_is_not_a_pass,
    "sampling_follows_the_shape": _probe_the_sampling_frame_follows_the_films_shape,
    "slideshow_fails_all_three": _probe_slideshow_fails_all_three,
    "a_real_film_passes": _probe_a_real_film_passes,
    "floors_stay_under_every_reference": _probe_floors_stay_under_every_reference,
    "blank_waiver_is_not_a_waiver": _probe_a_blank_waiver_is_not_a_waiver,
    "waiver_is_per_axis": _probe_a_waiver_does_not_absolve_axes_it_never_named,
    "written_waiver_downgrades": _probe_a_written_waiver_downgrades_to_warning,
    "missing_film_is_not_a_pass": _probe_a_missing_film_is_not_a_pass,
    "undecodable_film_is_not_a_pass": _probe_an_undecodable_film_is_not_a_pass,
}

MUTANTS["register_shot"] = dict(MUTANTS.get("register_shot", {}), **{
    # Following the tool's own next-step hint must FINISH the job. The old hint named one command that
    # measures and writes nothing, so a new register stayed flagged 'never measured' for ever.
    "the next-step hint forgets the second emit":
        ("    python3 scripts/measure_ground_luma.py --only %(s)s --emit          # DNA_GROUND_TOKEN\\n",
         ""),
})

MUTANTS["film_energy_qa"] = {
    # The same shape as register_shot's "next-step hint forgets the second emit" below: a gate that reports
    # a number and stops leaves the author one move, and it is the waiver.
    "the density report stops at the number":
        ('"the same family." % (m["ink_median"] * 100, _where))', '"." % (m["ink_median"] * 100,))'),
    "density goes back to a coloured-area count":
        ("    return float((np.maximum(gx, gy) > _EDGE).mean())",
         "    return float((np.abs(f - np.median(f)) > 0.10).mean())"),
    "the motion floor is disabled":
        ("MOTION_P75_FLOOR = 0.0037", "MOTION_P75_FLOOR = 0.0"),

    "the light floor is disabled":
        ("LUMA_RANGE_FLOOR = 0.135", "LUMA_RANGE_FLOOR = 0.0"),
    "the light-arc floor is disabled":
        ("LUMA_STEP_FLOOR = 0.019", "LUMA_STEP_FLOOR = 0.0"),
    "any flicker counts as a change of light":
        ("LUMA_STEP_DELTA = 0.12", "LUMA_STEP_DELTA = 0.0001"),
    "a film too short for an arc scores zero instead of unknown":
        ("             if len(win) >= MIN_WINDOWS else None)", "             if True else None)"),
    # The opposite failure, and the one a threshold gate slides into on its own: floors raised until
    # the gate is decoration nobody can satisfy. Only the positive control catches this.
    "the floors are raised past the reference films":
        ("MOTION_P75_FLOOR = 0.0037", "MOTION_P75_FLOOR = 0.9"),
    # The waiver became PER-AXIS, so the reason requirement moved into parse_waiver. Same rule, same
    # mutant: make the presence of the key enough and the written reason optional.
    "a waiver needs no reason":
        ('        return {str(k).strip().upper(): str(v).strip() for k, v in raw.items() if str(v).strip()}, ""\n'
         '    if isinstance(raw, str):\n        return {}, raw.strip()',
         '        return {str(k).strip().upper(): "waived" for k in raw}, ""\n'
         '    if isinstance(raw, str):\n        return {}, (raw.strip() or "waived")'),
    # ...and the new rule the per-axis shape introduced: a waiver must not absolve axes it never named.
    "one axis waives every axis":
        ('        reason = per_axis.get(axis) or (blanket if blanket else "")',
         '        reason = (per_axis and "waived") or (blanket if blanket else "")'),
    "a missing film passes":
        ('return ["no out.mp4 — this gate reads the delivered film, so it runs after the render"], [], None',
         "return [], [], None"),
    "an undecodable film passes":
        ('return ["could not decode %s — check ffmpeg/ffprobe are installed and the file is a video" % mp4], [], None',
         "return [], [], None"),
    "a film too short to measure passes":
        ('    if isinstance(m, int):', "    if False:"),
    # The sampling frame must follow the film's shape. Forcing 192x108 squashes a portrait film, and squashing
    # blends pixels, which UNDERCOUNTS ink — measured 2.2 points low at 9:16 — biasing the gate against
    # vertical films for no reason anyone chose.
    "the sampling frame stops following the aspect":
        ("        h, w = long_side, max(2, int(round(long_side * W0 / H0)) // 2 * 2)",
         "        h, w = 108, 192"),
}


# ── text_safe_qa: the rules around the DOM audit's ONE channel back from a render ────────────────────
# The audit itself lives in TypeScript and is proved by tests/test_text_safe_qa.py against real renders.
# What lives here is the python half: the payload must survive the trace it travels in, a render that never
# ran must not read as clean, and the props must reach the renderer as a FILE with the audit armed.
def _fake_run(mod, returncode=0, stderr="", stdout=""):
    seen = {}

    class R:
        pass
    r = R()
    r.returncode, r.stdout, r.stderr = returncode, stdout, stderr

    def run(cmd, **kw):
        seen["cmd"] = cmd
        return r
    mod.subprocess = types.SimpleNamespace(run=run)
    return seen


def _probe_a_failed_render_is_a_finding(mod):
    _fake_run(mod, returncode=1, stderr="Error: bundle failed")
    out = mod.audit_shot("Z", {}, 10, os.path.join(tempfile.mkdtemp(), "x.png"))
    assert out, "a render that never produced a frame reported as clean"


def _probe_a_clean_render_is_clean(mod):
    _fake_run(mod, returncode=0)
    assert mod.audit_shot("Z", {}, 10, os.path.join(tempfile.mkdtemp(), "x.png")) == []


def _probe_the_payload_survives_its_stack_trace(mod):
    import json as _json
    payload = [{"out": {"right": 848}, "text": "A]B", "tag": "div", "cls": "", "font": "104px Inter"}]
    _fake_run(mod, returncode=1,
              stderr="at cancelRender\nError: " + mod.TAG + _json.dumps(payload) + "\n  at f (b.js:1:1) [x]\n")
    got = mod.audit_shot("Z", {}, 10, os.path.join(tempfile.mkdtemp(), "x.png"))
    assert got == payload, "payload lost in the trace around it: %r" % (got,)


def _probe_props_reach_the_render_as_a_file_with_the_audit_armed(mod):
    import json as _json
    seen = _fake_run(mod, returncode=0)
    mod.audit_shot("Z", {"title": "\u6700\u540e\u4e00\u516c\u91cc"}, 10,
                   os.path.join(tempfile.mkdtemp(), "x.png"))
    pf = [c for c in seen["cmd"] if str(c).startswith("--props=")]
    assert pf, "no --props reached the renderer: %r" % (seen["cmd"],)
    path = str(pf[0]).split("=", 1)[1]
    assert os.path.exists(path), "props were passed inline, not as a file — CJK copy breaks the argument"
    data = _json.load(open(path, encoding="utf-8"))
    assert data.get("textSafe") is True, "the render was made without arming the audit"
    assert data.get("title") == "\u6700\u540e\u4e00\u516c\u91cc"


PROBES["text_safe_qa"] = {
    "failed_render_is_a_finding": _probe_a_failed_render_is_a_finding,
    "clean_render_is_clean": _probe_a_clean_render_is_clean,
    "payload_survives_its_trace": _probe_the_payload_survives_its_stack_trace,
    "props_by_file_audit_armed": _probe_props_reach_the_render_as_a_file_with_the_audit_armed,
}

MUTANTS["text_safe_qa"] = {
    # The anchor moved when the failure branch learned to RETRY and to report a FAILURE distinct from a
    # type finding. The rule it pins is unchanged and is the one that matters: a render that never ran must
    # never read as clean.
    # The anchor moved when the failure branch learned to RETRY and to report a FAILURE distinct from a type
    # finding. The rule it pins is unchanged and is the one that matters: a render that never ran must never
    # read as clean. It spans BOTH lines of the statement on purpose — replacing only the first leaves the
    # second dangling, and a mutant that does not compile proves nothing about the rule.
    "a render that never ran passes":
        ('        return [{"text": "(render FAILED twice — nothing was measured on this frame: %s)"\n'
         '                         % _stderr_reason(blob, limit=160), "out": {}}]',
         "        return []"),
    "the audit is never armed":
        ('    payload["textSafe"] = True', '    payload["textSafe"] = False'),
    "the payload is ignored":
        ("    if TAG in blob:", "    if False:"),
    # The bug a test drove out: a hand-rolled bracket scan closes on the first ']' in the copy.
    "the payload end is guessed instead of parsed":
        ("            found, _end = json.JSONDecoder().raw_decode(raw)\n            return found",
         "            return json.loads(raw[:raw.index(']') + 1])"),
    "props go inline on the command line":
        ('               "--props=" + os.path.abspath(pf)]',
         '               "--props=" + json.dumps(payload)]'),
}


# ── register_energy: the library-wide diagnostic's two load-bearing rules ────────────────────────────
def _probe_floors_are_derived_not_restated(mod):
    """Move film_energy_qa's floor and the ranking must move with it.

    Checking equality would pass a hardcoded copy of today's numbers, which is exactly the failure: a
    diagnostic that keeps ranking against a private copy after the real gate moved. So the probe CHANGES the
    source of truth and requires the derived value to follow."""
    # `mod.fe` is the SHARED film_energy_qa module — `load()` re-execs register_energy but its import
    # returns the one cached instance — so an unrestored edit here silently moves the delivery gate's floor
    # for every test that runs afterwards.
    was = mod.fe.MOTION_P75_FLOOR
    try:
        mod.fe.MOTION_P75_FLOOR = 0.4242
        got = mod.floors()
    finally:
        mod.fe.MOTION_P75_FLOOR = was
    assert got["motion_p75"] == 0.4242, (
        "floors() returned %r — it is not reading film_energy_qa, it is carrying its own copy" % (got,))


def _probe_an_unmeasured_register_is_not_a_passing_one(mod):
    """A register that failed to render is ABSENT from the ranking, and absence reads as 'fine'."""
    import json as _json
    d = tempfile.mkdtemp()
    path = os.path.join(d, "m.json")
    _json.dump({"_regenerate": "x", "_basis": "x",
                "_floors": {"motion_p75": 0.0037, "ink_median": 0.12, "luma_range": 0.135},
                "_failed": ["Zed (render blew up)"],
                "registers": {"Alpha": {"motion_p75": 0.9, "ink_median": 0.9, "luma_range": 0.9,
                                        "seconds": 5.0}}},
               open(path, "w", encoding="utf-8"))
    mod.MANIFEST = path
    rc = mod.main(["--report"])
    assert rc == 1, "a manifest with an UNMEASURED register reported success (exit %r)" % rc


def _probe_the_fixture_list_is_derived_from_the_call_sites(mod):
    """Four registers refuse to draw without a real image. If the sweep stops supplying one, they are not
    measured as weak — they are recorded as FAILURES, and their real densities (37.2 / 28.9 / 16.5 / 25.7%)
    vanish from the record that tells authors which registers to reach for."""
    ev = mod.evidence_props()
    assert ev, "the sweep supplies no fixture — every guarded register will be recorded as unmeasurable"
    assert all(v for v in ev.values()), "a guarded register got an empty prop set: %r" % (ev,)


def _probe_the_render_cache_distinguishes_two_design_systems(mod):
    """Keyed by NAME alone, the cache re-measured pre-fixture footage for four registers and would serve
    product-DNA video to an editorial sweep while the manifest announced editorial."""
    import json as _json
    seen = []

    def fake_render(name, mp4, dna=None, extra=None):
        seen.append(mp4)
        open(mp4, "wb").close()
        return True, [""]

    d = tempfile.mkdtemp()
    mod.MANIFEST = os.path.join(d, "m.json")
    mod.durations = lambda: {"Alpha": 150}
    mod.render_one = fake_render
    mod.stills_from = lambda *a, **k: None
    mod.footprint = lambda *a, **k: 0.4
    # A FRESH cache per invocation: this probe runs once for the real module and once per mutant, and the
    # sweep's cache lives under $TMPDIR — so without this the second run finds the first run's files, calls
    # render_one zero times, and the probe reports a cache failure that is its own leftovers. Restoring
    # fe.measure matters for the same reason the floors probe restores its floor.
    was_tmp, was_measure = os.environ.get("TMPDIR"), mod.fe.measure
    os.environ["TMPDIR"] = d
    try:
        mod.fe.measure = lambda *a, **k: {"motion_p75": 0.5, "ink_median": 0.5, "luma_range": 0.5,
                                          "seconds": 5.0}
        mod.main(["--dna=product"])
        mod.main(["--dna=editorial"])
    finally:
        mod.fe.measure = was_measure
        if was_tmp is None:
            os.environ.pop("TMPDIR", None)
        else:
            os.environ["TMPDIR"] = was_tmp
    assert len(seen) == 2 and seen[0] != seen[1], (
        "the same cached video was reused across two design systems: %r" % (seen,))


def _probe_a_partial_sweep_reaches_the_record(mod):
    """--only once OVERWROTE all 149 rows; the fix for that stopped it writing at all, so a register that
    was repaired and re-measured could never correct its own row."""
    import json as _json
    d = tempfile.mkdtemp()
    path = os.path.join(d, "m.json")
    _json.dump({"_dna": "product", "_floors": mod.floors(), "_failed": [], "_source": {},
                "registers": {"Old": {"motion_p75": 1, "ink_median": 1, "luma_range": 1, "seconds": 5},
                              "Alpha": {"motion_p75": 0, "ink_median": 0.006, "luma_range": 0,
                                        "seconds": 5}}},
               open(path, "w", encoding="utf-8"))
    mod.MANIFEST = path
    mod.durations = lambda: {"Alpha": 150, "Old": 150}
    mod.render_one = lambda *a, **k: (True, [""])
    mod.stills_from = lambda *a, **k: None
    mod.footprint = lambda *a, **k: 0.4
    was_measure, was_density = mod.fe.measure, mod.fe.density
    try:
        # BOTH decodes are faked, because ink moved to its own. `measure` no longer answers the density
        # question — it returns None for it — so a probe that stubs only `measure` measures nothing and
        # the row it checks is the stub's silence rather than the sweep's record.
        mod.fe.measure = lambda *a, **k: {"motion_p75": 0.5, "ink_median": None, "luma_range": 0.5,
                                          "seconds": 5.0}
        mod.fe.density = lambda *a, **k: {"median": 0.372, "beats": []}
        mod.main(["--only=Alpha"])
    finally:
        mod.fe.measure, mod.fe.density = was_measure, was_density
    out = _json.load(open(path, encoding="utf-8"))
    assert out["registers"]["Alpha"]["ink_median"] == 0.372, "the re-measure never reached the record"
    assert out["registers"]["Old"]["ink_median"] == 1, "the partial sweep clobbered a row it never rendered"


def _probe_the_ink_cut_is_the_librarys_own_distribution(mod):
    """The ink cut is RELATIVE, and it has to stay that way.

    `film_energy_qa` retired its absolute ink floor with the metric that could not tell a drawn frame from
    a blurred blank one, and refused to re-guess a replacement: its reference films were measured under the
    old definition and are not in this repo. A diagnostic must not invent the constant the gate declined to
    invent — so the cut is the bottom fifth of the library's OWN measured rows, and it must MOVE when that
    distribution moves. A fixed number would read as measured and rank registers against a bar nobody
    derived."""
    rows = {"A%d" % i: {"ink_median": i / 100.0} for i in range(1, 21)}
    cut = mod._ink_cut(rows)
    assert cut is not None and 0.03 <= cut <= 0.05, (
        "the bottom fifth of 0.01..0.20 should land near 0.04, got %r" % cut)
    # ...and it moves with the library, which a constant does not
    denser = {k: {"ink_median": v["ink_median"] * 10} for k, v in rows.items()}
    assert mod._ink_cut(denser) > cut * 5, (
        "a ten-times denser library must move the cut: %r then %r" % (cut, mod._ink_cut(denser)))
    # a set too small to have a distribution says so instead of inventing one
    assert mod._ink_cut({"A": {"ink_median": 0.1}}) is None


def _probe_the_light_cut_is_the_librarys_own_not_a_films(mod):
    """A per-register light reading must not be judged against a whole FILM's threshold.

    `film_energy_qa.LUMA_RANGE_FLOOR` is 0.135 — half the lowest reference launch film — and a film's
    luminance range is mostly the CUT: it comes from moving between a dark beat and a light one. A single
    register paints on ONE ground by construction, so it cannot produce a film's range and was never the
    thing that number described. Measured before this changed: of 180 registers, 12 cleared light and those
    twelve were EXACTLY the twelve clearing all three floors — the light axis was deciding the whole test
    on its own, and the twelve were the registers whose own composition spans dark to light rather than the
    ones with an arc. Same category error the ink floor was retired for, one axis over.

    The gate keeps its constant, because there it judges FILMS. Here the reference is the library's own
    distribution."""
    assert mod.floors()["luma_range"] is None, (
        "floors() is taking a light constant from the gate again; a whole-film threshold cannot judge one shot")
    rows = {"A%d" % i: {"luma_range": i / 100.0} for i in range(1, 21)}
    cut = mod._light_cut(rows)
    assert cut is not None and 0.03 <= cut <= 0.05, (
        "the bottom fifth of 0.01..0.20 should land near 0.04, got %r" % cut)
    brighter = {k: {"luma_range": v["luma_range"] * 10} for k, v in rows.items()}
    assert mod._light_cut(brighter) > cut * 5, (
        "a ten-times brighter library must move the cut: %r then %r" % (cut, mod._light_cut(brighter)))
    assert mod._light_cut({"A": {"luma_range": 0.1}}) is None


PROBES["register_energy"] = {
    "floors_are_derived": _probe_floors_are_derived_not_restated,
    "unmeasured_is_not_passing": _probe_an_unmeasured_register_is_not_a_passing_one,
    "fixture_is_derived": _probe_the_fixture_list_is_derived_from_the_call_sites,
    "cache_separates_design_systems": _probe_the_render_cache_distinguishes_two_design_systems,
    "partial_sweep_reaches_the_record": _probe_a_partial_sweep_reaches_the_record,
    "ink_cut_is_relative": _probe_the_ink_cut_is_the_librarys_own_distribution,
    "light_cut_is_relative": _probe_the_light_cut_is_the_librarys_own_not_a_films,
}

MUTANTS["register_energy"] = {
    "the floors become a private copy":
        ('    return {"motion_p75": fe.MOTION_P75_FLOOR, "ink_median": None, "luma_range": None}',
         '    return {"motion_p75": 0.0037, "ink_median": None, "luma_range": None}'),
    # ...and the LIGHT cut must not go back to the gate's number. That constant describes a whole film —
    # it is half the lowest reference launch film — and a film's range comes from cutting between a dark
    # beat and a light one, which one register on one ground cannot do. Reverting it made 12 of 180
    # registers "clear light", and those twelve were exactly the twelve clearing all three floors.
    "the light cut goes back to the film's threshold":
        ("    return vals[max(0, int(len(vals) * LIGHT_QUINTILE) - 1)]", "    return fe.LUMA_RANGE_FLOOR"),
    # ...and the ink cut, which is NOT taken from the gate because the gate has none to give, must stay the
    # library's own distribution rather than becoming a second invented constant.
    "the relative ink cut becomes an invented constant":
        ("    return vals[max(0, int(len(vals) * INK_QUINTILE) - 1)]", "    return 0.12"),
    "an unmeasured register reads as fine":
        ("    return 1 if unknown or gaps else 0", "    return 0"),
    # ...AND THE OTHER HALF OF THE SAME SENTENCE: `_failed` only ever held what a sweep TRIED and lost. A
    # register it never reached had no row, no failure line, and nothing that counted its absence.
    "a register the sweep never reached reads as fine":
        ("    return 1 if unknown or gaps else 0", "    return 1 if unknown else 0"),
    "the coverage line counts its own rows instead of the library":
        ('    _c.coverage("register_energy", len([n for n in regs if n in set(univ)]), len(univ), gaps)',
         '    _c.coverage("register_energy", len(regs), len(regs), {})'),
    "the guarded registers are swept with no image":
        ("    return out\n\n\ndef ensure_fixture():", "    return {}\n\n\ndef ensure_fixture():"),
    "the render cache forgets what it rendered":
        ('            mp4 = os.path.join(tmp, "%s.%s.mp4" % (n, key))',
         '            mp4 = os.path.join(tmp, n + ".mp4")'),
    "a partial sweep is discarded instead of merged":
        ('        if only:\n            # MERGE a targeted re-measure',
         '        if only:\n            return 0\n            # MERGE a targeted re-measure'),
}



# ── demo_copy_qa: a register must not print its own demo copy as content ─────────────────────────────
_DEMO_SRC = """
export const Demo: React.FC<{title?: string; page?: UiPage; marks?: {n: number; label: string}[]}> = ({
  title = 'WorkBuddy', marks = [{n: 1, label: 'what to notice here'}], accent = '#22d3ee',
  align = 'center', page = 'cards',
} = {}) => {
  return <svg fill="none" strokeLinecap="round" transform="rotate(-90 55 55)"><text>hi</text></svg>;
};
"""


def _probe_demo_copy_is_read_from_the_signature(mod):
    """A gate that invents findings gets switched off. Regexed to the first `} = {})`, the parser ran past a
    props type containing an object literal and reported SVG attributes from the JSX as demo copy."""
    got = mod.demo_defaults(_DEMO_SRC, "Demo")
    assert got.get("title") == "WorkBuddy" and "what to notice here" in got.get("marks", ""), got
    for attr in ("fill", "strokeLinecap", "transform"):
        assert attr not in got, "%r came from the component body, not the signature: %r" % (attr, got)


def _probe_configuration_is_not_mistaken_for_copy(mod):
    """No viewer reads '#22d3ee' off the frame, and the DNA overrides it anyway — flagging it would make
    every themed beat a finding."""
    got = mod.demo_defaults(_DEMO_SRC, "Demo")
    assert "accent" not in got, "a colour was reported as demo copy"
    assert "align" not in got, "a CSS keyword ('center') was reported as demo copy"
    # A SELECTOR is configuration too, and it does not look like one: `page = 'cards'` is an ordinary word
    # whose type says it chooses a layout. Counted as copy it errors every beat using the register, and the
    # only escape the message offers is setting the prop to "" — which draws no page at all.
    assert "page" not in got, "a typed selector ('page: UiPage') was reported as demo copy"


def _probe_a_partially_supplied_beat_is_caught(mod):
    """Empty props were already caught by validate; the beat that ships English demo labels onto a Chinese
    frame is the one that LOOKS authored."""
    lib = {"Reg": {"title": "WorkBuddy", "items": "['Throughput']"}}
    board = {"slides": [{"index": 4, "shot": "Reg", "shot_props": {"title": "the film's own words"}}]}
    found = mod.audit_board(board, lib)
    assert [(f[1], f[2]) for f in found] == [("Reg", "items")], found
    assert mod.audit_board({"slides": [{"index": 4, "shot": "Reg",
                                        "shot_props": {"title": "x", "items": []}}]}, lib) == [], (
        "an explicitly emptied prop was reported — the opt-out is gone")


# A SLOT COUNT is part of a register's form, and both ways of getting it wrong have shipped here: a fourth
# item dropped in silence (IsometricAssembly) and a third condition thrown mid-render, after a full bundle
# (AcceptanceStamp). Three registers in the library declare a fixed count; this is the parser that sees it.
_ARITY_SRC = """
type Props = {
  /** two things that must BOTH hold; a third would make it a list, not a conjunction. */
  pair?: [string, string];
  loose?: [string, string] | string[];
  nested?: {from?: [number, number]; to?: [number, number]};
  rows?: {label: string; v: number}[];
  note?: string;
};

export const Aliased: React.FC<Props> = ({pair = ['a', 'b'], note = 'n'} = {}) => null;

export const Inline: React.FC<{items?: [string, string, string]; last?: boolean}> = ({
  items = ['Raw work', 'WorkBuddy', 'Delivered'],
} = {}) => null;
"""


def _probe_a_fixed_slot_count_is_read(mod):
    """`items?: [string, string, string]` says the register draws three slots. Nothing read that until a
    board had already handed one of them four items and another three conditions."""
    assert mod.tuple_arity(_ARITY_SRC, "Inline") == {"items": 3}, mod.tuple_arity(_ARITY_SRC, "Inline")
    assert mod.tuple_arity(_ARITY_SRC, "Aliased").get("pair") == 2, "a NAMED props type was not resolved"


def _probe_a_union_with_a_loose_array_fixes_nothing(mod):
    """`[string, string] | string[]` says any length is legal. Enforcing the strict-looking half would make
    a correct board an error AND hide the real finding: a declaration its own runtime contradicts."""
    assert "loose" not in mod.tuple_arity(_ARITY_SRC, "Aliased"), "a union was read as a fixed count"


def _probe_a_nested_shape_is_not_a_prop(mod):
    """`channel?: {from?: [number, number]}` is one prop, not two. Read as top-level, MapPlate gained two
    props that do not exist and every board using it became an error about `from`."""
    got = mod.tuple_arity(_ARITY_SRC, "Aliased")
    assert "from" not in got and "to" not in got, got
    assert "v" not in mod._declared_types(_ARITY_SRC, "Aliased"), "a nested object's `;` invented a prop"


def _probe_the_last_prop_is_read(mod):
    """A props list's final entry carries no `;`. Requiring one dropped the last prop of every inline
    register — silently, into the loosest possible reading of the thing this parser is strict about."""
    assert "last" in mod._declared_types(_ARITY_SRC, "Inline"), "the last prop was dropped"


_INTERSECTED_SRC = """
type Props = ObjectProps & {
  years?: number[];
  laid?: number;
};
export const Aliased: React.FC<Props> = ({w, years = []}) => null;
export const Inline: React.FC<ObjectProps & {packed?: number}> = ({w, packed = 0}) => null;
"""


def _probe_an_intersected_props_type_is_read(mod):
    """`React.FC<ObjectProps & {packed?: number}>` declares `packed`; the slot's own props come from the named
    base. Read only up to that name, every object declared nothing — inline and through an alias alike."""
    assert set(mod._declared_types(_INTERSECTED_SRC, "Inline")) == {"packed"}, \
        mod._declared_types(_INTERSECTED_SRC, "Inline")
    assert set(mod._declared_types(_INTERSECTED_SRC, "Aliased")) == {"years", "laid"}, \
        mod._declared_types(_INTERSECTED_SRC, "Aliased")


def _probe_supersession_is_narrow(mod):
    """A superseded prop's default cannot draw, so it is not a finding — but ONLY when the beat actually
    supplies the prop that supersedes it.

    `PortRail` declares `// @supersedes groups: items`. The delivered AgentHalo film's beat 3 supplies three
    named groups and the standalone CLI still reported `PortRail.items -> ['Docs','Chat',…]`: a wolf on a
    shipped film, while `validate.py`, reading the same declaration, stayed quiet. The repair has to narrow
    exactly one prop and only on the beats that earned it, or it becomes a way for demo copy to ship unseen.
    """
    sup = mod.supersedes()
    assert sup.get("PortRail", {}).get("groups") == ["items"], \
        "PortRail no longer declares the supersession this probe rests on: %r" % (sup.get("PortRail"),)
    bare = _board([{"index": 0, "shot": "PortRail", "narration": "x", "shot_props": {"title": "t"}}])
    grouped = _board([{"index": 0, "shot": "PortRail", "narration": "x", "shot_props": {
        "title": "t", "groups": [{"label": "a", "items": ["p"]}]}}])
    props = lambda b: {p for _, _, p, _ in mod.audit_board(b)}
    assert "items" in props(bare), "a default the film did NOT supersede stopped being a finding"
    assert "items" not in props(grouped), "a superseded default is still reported, on a prop that cannot draw"
    assert props(bare) - {"items"} == props(grouped), \
        "supersession silenced more than the prop it kills: %r vs %r" % (props(bare), props(grouped))


PROBES["demo_copy_qa"] = {
    "read_from_the_signature": _probe_demo_copy_is_read_from_the_signature,
    "configuration_is_not_copy": _probe_configuration_is_not_mistaken_for_copy,
    "partial_props_are_caught": _probe_a_partially_supplied_beat_is_caught,
    "fixed_slot_count_is_read": _probe_a_fixed_slot_count_is_read,
    "a_union_fixes_nothing": _probe_a_union_with_a_loose_array_fixes_nothing,
    "nested_shapes_are_not_props": _probe_a_nested_shape_is_not_a_prop,
    "the_last_prop_is_read": _probe_the_last_prop_is_read,
    "intersected_props_are_read": _probe_an_intersected_props_type_is_read,
    "supersession_is_narrow": _probe_supersession_is_narrow,
}

MUTANTS["demo_copy_qa"] = {
    # The real bug this rule fixes is OVER-running the destructure into the component body, where every
    # JSX attribute looks like `name = "value"`. Under-running is caught by the same probe's marks assertion.
    "the destructure has no end, so the component body counts as props":
        ("    depth, j = 0, start", "    return src[start + 1:]\n    depth, j = 0, start"),
    "colours and css keywords count as copy":
        ('            if re.search(r"[A-Za-z]{3}", v) and not _NOT_COPY.match(v) and _is_copy(m.group(1)):',
         '            if re.search(r"[A-Za-z]{3}", v) and _is_copy(m.group(1)):'),
    # The other half of the same line: a prop TYPED as a selector (`page?: UiPage`) defaults to a word that
    # is never drawn, and counting it as copy errors every beat that uses the register while offering the
    # author no way out but to switch the page off.
    "a selector's default counts as copy":
        ('            if re.search(r"[A-Za-z]{3}", v) and not _NOT_COPY.match(v) and _is_copy(m.group(1)):',
         '            if re.search(r"[A-Za-z]{3}", v) and not _NOT_COPY.match(v):'),
    "an absent prop stops being a finding":
        ("            if prop not in props and prop not in dead:", "            if False:"),
    # ...and the SUPERSESSION that narrows it must stay narrow: a mutant that treats every superseded prop
    # as dead on every beat silences findings the film never superseded.
    "a supersession silences a prop the beat did not supersede":
        ("            if given in props:", "            if True:"),
    # ── the slot count ───────────────────────────────────────────────────────────────────────────────
    "a named props type is not resolved, so an aliased register declares nothing":
        ("    body = _brace_body(src, _past_intersected(src, m.end()))\n    if body is None:",
         "    body = _brace_body(src, _past_intersected(src, m.end()))\n    if body is None:\n        return {}\n"
         "    if body is None:"),
    # An object is declared `React.FC<ObjectProps & {...}>` or through an alias of that intersection; stopping
    # at the base type's name read every object as declaring nothing, so promote.py catalogued none of them.
    "an intersection's own props are not read":
        ("    m = _INTERSECTED.match(src, i)\n    while m:", "    m = None\n    while m:"),
    # NOT the `startswith("[")` guard: `string[]`'s middle is not a primitive either, so the next line
    # catches it anyway and the mutant survives while looking like it disabled the rule. The rule that
    # actually carries the union is reading EVERY member of it.
    "only the first member of a union type is read":
        ('    return _split_top(t, "|")', '    return _split_top(t, "|")[:1]'),
    "the last prop of an inline register is dropped again":
        ('    for chunk in _split_top(body, ";"):', '    for chunk in body.split(";")[:-1]:'),
    "a nested object's own `;` splits into invented props":
        ('    for chunk in _split_top(body, ";"):', '    for chunk in body.split(";"):'),
}

def _all(kind):
    return [(m, k) for m, d in kind.items() for k in d]

# ── energy_skeleton: the five skeleton rules, and the picker that reads them ─────────────────────
# A synthetic six-register library, so one rule can be removed at a time. Cuts and floor are handed in
# directly: quiet < 0.0025 <= steady < 0.005 <= kinetic; the delivery floor sits inside "steady".
_ES_MOTION = {"Still": 0.0002, "Calm": 0.0010, "Mid": 0.0025, "Live": 0.0050, "Wild": 0.0150, "Blaze": 0.0300}
_ES_ARGS = dict(motion=_ES_MOTION, floor=0.0037, quiet_cut=0.0025, kinetic_cut=0.0050)


def _es_kinds(mod, slides):
    return [f["kind"] for f in mod.findings(slides, **_ES_ARGS)]


def _probe_high_on_quiet(mod):
    assert "high-on-quiet" in _es_kinds(mod, [{"shot": "Still", "energy": "high"}])
    assert "high-on-quiet" not in _es_kinds(mod, [{"shot": "Live", "energy": "high"}])


def _probe_peak_under_floor(mod):
    assert "peak-under-floor" in _es_kinds(mod, [{"shot": "Mid", "energy": "peak"}]), "0.0025 is under the 0.0037 floor"
    assert "peak-under-floor" not in _es_kinds(mod, [{"shot": "Live", "energy": "peak"}])


def _probe_low_on_kinetic(mod):
    assert "low-on-kinetic" in _es_kinds(mod, [{"shot": "Wild", "energy": "low"}])
    assert "low-on-kinetic" not in _es_kinds(mod, [{"shot": "Calm", "energy": "low"}])


def _probe_run_of_kinetic(mod):
    run = [{"shot": n, "energy": "medium"} for n in ("Live", "Wild", "Blaze")]
    assert "run-of-kinetic" in _es_kinds(mod, run), "three kinetic registers in a row read as noise"
    assert "run-of-kinetic" not in _es_kinds(mod, run[:2] + [{"shot": "Calm", "energy": "medium"}] + run[2:])


def _probe_summit_off_peak(mod):
    assert "summit-off-peak" in _es_kinds(mod, [{"shot": "Blaze", "energy": "medium"}, {"shot": "Live", "energy": "peak"}])
    assert "summit-off-peak" not in _es_kinds(mod, [{"shot": "Live", "energy": "medium"}, {"shot": "Blaze", "energy": "peak"}])


def _probe_medium_never_mismatches(mod):
    assert not [k for k in _es_kinds(mod, [{"shot": "Still", "energy": "medium"}, {"shot": "Blaze", "energy": "medium"}])
                if k in mod.HARD]


def _probe_bands(mod):
    assert mod.band_for("medium", 0.0025, 0.005, 0.0037) == (0.0, float("inf"))
    assert mod.band_for("high", 0.0025, 0.005, 0.0037)[0] == 0.0025
    assert mod.band_for("low", 0.0025, 0.005, 0.0037)[1] == 0.005
    assert mod.band_for("peak", 0.0025, 0.005, 0.0037)[0] == 0.0037, "the peak band starts at the delivery floor"


PROBES["energy_skeleton"] = {
    "high_on_quiet": _probe_high_on_quiet,
    "peak_under_floor": _probe_peak_under_floor,
    "low_on_kinetic": _probe_low_on_kinetic,
    "run_of_kinetic": _probe_run_of_kinetic,
    "summit_off_peak": _probe_summit_off_peak,
    "medium_never_mismatches": _probe_medium_never_mismatches,
    "bands": _probe_bands,
}

MUTANTS["energy_skeleton"] = {
    "high-on-quiet rule removed": ('        if e in ("high", "peak") and m < quiet_cut:', "        if False:"),
    "peak-under-floor rule removed": ('        if e == "peak" and m < floor:', "        if False:"),
    "low-on-kinetic rule removed": ('        if e == "low" and m >= kinetic_cut:', "        if False:"),
    "a run is never long enough": ("RUN = 3 ", "RUN = 999 "),
    "the summit is never elsewhere": ("SUMMIT_RATIO = 1.5 ", "SUMMIT_RATIO = 1e9 "),
    "the peak band forgets the floor": ('        return (max(quiet_cut, floor), float("inf"))',
                                        '        return (quiet_cut, float("inf"))'),
}


def _probe_picker_prefers_the_band(mod):
    """shot_director._pick: with a band and the sweep, an in-band candidate beats an earlier out-of-band one."""
    assert mod._pick(["Still", "Live"], None, set(), band=(0.0025, float("inf")), motion=_ES_MOTION) == "Live"
    assert mod._pick(["Live", "Still"], None, set(), band=(0.0, 0.0025), motion=_ES_MOTION) == "Still"
    assert mod._pick(["Still", "Live"], None, set()) == "Still", "no band: the pool's own order stands"


def _probe_peak_takes_the_liveliest(mod):
    assert mod._pick(["Live", "Blaze", "Wild"], None, set(), band=(0.0037, float("inf")), motion=_ES_MOTION,
                     summit=True) == "Blaze"
    assert mod._pick(["Live", "Blaze", "Wild"], None, set(), band=(0.0037, float("inf")), motion=_ES_MOTION) == "Live"


PROBES["shot_director"]["picker_prefers_the_band"] = _probe_picker_prefers_the_band
PROBES["shot_director"]["peak_takes_the_liveliest"] = _probe_peak_takes_the_liveliest
MUTANTS["shot_director"]["the band is ignored in the pick"] = (
    "    pool = sorted(pool, key=lambda c: (not in_band(c), lively(c), flips(c)))",
    "    pool = sorted(pool, key=lambda c: (False, lively(c), flips(c)))")
MUTANTS["shot_director"]["the peak is not the liveliest"] = (
    '    lively = (lambda c: -motion.get(c, 0.0)) if (summit and motion) else (lambda c: 0.0)',
    '    lively = (lambda c: 0.0)')





# ── the five library-wide SWEEPS: every one must be able to say what it did NOT measure ──────────────
# `ink_contrast_qa` swept 170 registers and reported 19 "skipped". A skip reads like a clean result, and
# behind those 19 were four different bugs: a fixed frame past the end of seven short registers, six
# registers handed no picture to draw, a skip reason that printed `at process.processTicksAndRejections
# (node:internal/…)`, and a probe DNA value no preset ships that made a register throw and be recorded as
# refusing. None of it was visible in the headline, because the headline counted what the gate MEASURED.
#
# These sweeps are the expensive ones — a full run of any of them is tens of minutes to hours — so a hole
# here is the one that costs the most to notice. Two rules per sweep: the headline states COVERAGE against
# a universe it DERIVED, and an item it could not measure never reads as a passing one.
def _capture(fn, *a, **k):
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*a, **k)
    return rc, buf.getvalue()


def _tiny_png(path, v=200):
    from PIL import Image
    Image.new("RGB", (8, 8), (v, v, v)).save(path)
    return path


# ── register_energy ──────────────────────────────────────────────────────────────────────────────────
def _probe_energy_coverage_is_derived_from_the_library(mod):
    """The headline's M must follow the shots directory. Pinned by MOVING the universe and requiring the
    number to move with it — equality against 170 would pass a hardcoded constant, which is the bug."""
    import json as _json
    d = tempfile.mkdtemp()
    path = os.path.join(d, "m.json")
    _json.dump({"_dna": "product", "_floors": mod.floors(), "_failed": [], "_source": {},
                "registers": {"Alpha": {"motion_p75": 1, "ink_median": 1, "luma_range": 1, "seconds": 5},
                              "Beta": {"motion_p75": 1, "ink_median": 1, "luma_range": 1, "seconds": 5}}},
               open(path, "w", encoding="utf-8"))
    mod.MANIFEST = path
    for lib, expect in ((["Alpha", "Beta", "Gamma", "Zed"], "measured 2 of 4"),
                        (["Alpha", "Beta", "Gamma", "Zed", "Omega"], "measured 2 of 5")):
        mod.universe = lambda lib=lib: list(lib)
        mod.durations = lambda lib=lib: {n: 150 for n in lib}
        _rc, out = _capture(mod.main, ["--report"])
        assert expect in out, "the coverage line does not follow the library (%r): %r" % (expect, out)
    assert "Gamma" in out and "Zed" in out, "the registers with no row are counted and not NAMED: %r" % out


def _probe_a_register_the_sweep_never_reached_is_not_a_passing_one(mod):
    """`_failed` held what a sweep TRIED and lost. A register it never reached — an older manifest, an
    `--only` run, a register exporting no DURATION — had no row and nothing counted its absence."""
    import json as _json
    d = tempfile.mkdtemp()
    path = os.path.join(d, "m.json")
    _json.dump({"_dna": "product", "_floors": mod.floors(), "_failed": [], "_source": {},
                "registers": {"Alpha": {"motion_p75": 1, "ink_median": 1, "luma_range": 1, "seconds": 5}}},
               open(path, "w", encoding="utf-8"))
    mod.MANIFEST = path
    mod.universe = lambda: ["Alpha", "Zed"]
    mod.durations = lambda: {"Alpha": 150, "Zed": 150}
    rc, out = _capture(mod.main, ["--report"])
    assert rc == 1, "a manifest missing a register reported success (exit %r): %r" % (rc, out)
    assert "Zed" in out, "and it did not say which register is missing: %r" % out


PROBES["register_energy"]["coverage_is_derived"] = _probe_energy_coverage_is_derived_from_the_library
PROBES["register_energy"]["never_reached_is_not_passing"] = (
    _probe_a_register_the_sweep_never_reached_is_not_a_passing_one)


# ── prop_reach ───────────────────────────────────────────────────────────────────────────────────────
def _prop_reach_stub(mod, lib, fail=None):
    """The sweep with no renders.

    The RENDER is stubbed, never `_still` itself: a probe that replaces `_still` cannot see what `_still`
    does with a failure, and the probe below is about exactly that. (It also leaked — running first, it
    left its own stub in place for the later probe, which then passed on the stub's answer.)
    """
    import json as _json
    mod.universe = lambda: list(lib)
    mod.re_mod = types.SimpleNamespace(durations=lambda: {n: 150 for n in lib},
                                       source_hash=lambda n: "h-" + n)
    mod.cq = types.SimpleNamespace(cjk_props=lambda n, offset=0: ({"title": "%s-%d" % (n, offset)}, []),
                                   evidence_props=lambda: {})
    mod.props_hash = lambda n: "p-" + n

    class R:
        returncode, stdout, stderr = 0, "", ""

    def run(cmd, **kw):
        r = R()
        name, out_png = cmd[4], cmd[5]
        if fail and name in fail:
            r.returncode = 1
            r.stderr = ("Bundling...\n%s\n    at process.processTicksAndRejections (node:internal/x)"
                        % fail[name])
            return r
        props = _json.load(open(out_png + ".props.json", encoding="utf-8"))
        _tiny_png(out_png, 200 if str(props.get("title", "")).endswith("-0") else 40)
        return r
    mod.subprocess = types.SimpleNamespace(run=run)


def _probe_prop_reach_names_what_it_could_not_measure(mod):
    """"5 could not be measured (empty frame or render failure)" is a GUESS between two opposite facts,
    printed because the sweep threw the renderer's own message away."""
    import json as _json
    d = tempfile.mkdtemp()
    mod.MANIFEST = os.path.join(d, "m.json")
    _prop_reach_stub(mod, ["Alpha", "Zed"], fail={"Zed": "Error: needs at least one `cells` entry"})
    rc, out = _capture(mod.main, [])
    assert rc == 1, "a sweep that lost half its universe exited 0: %r" % out
    assert "cells" in out, "the reason the register refused is not in the output: %r" % out
    rec = _json.load(open(mod.MANIFEST, encoding="utf-8"))["_failed"]
    assert isinstance(rec, dict) and "cells" in str(rec.get("Zed")), (
        "the manifest records names without reasons: %r" % (rec,))


def _probe_prop_reach_coverage_is_derived(mod):
    """M follows the shots directory, so a register added today is a hole in the manifest from today."""
    import json as _json
    d = tempfile.mkdtemp()
    mod.MANIFEST = os.path.join(d, "m.json")
    _json.dump({"_low_reach": 0.15, "_failed": {}, "_untrusted": [],
                "registers": {"Alpha": {"reach": 0.4, "prop_diff": 1.0}}},
               open(mod.MANIFEST, "w", encoding="utf-8"))
    for lib, expect in ((["Alpha", "Zed"], "measured 1 of 2"), (["Alpha", "Zed", "Omega"], "measured 1 of 3")):
        mod.universe = lambda lib=lib: list(lib)
        rc, out = _capture(mod.main, ["--report"])
        assert expect in out, "the coverage line does not follow the library (%r): %r" % (expect, out)
        assert rc == 1, "a report over a manifest with holes in it exited 0"


def _probe_prop_reach_keeps_the_renderers_own_message(mod):
    """The REASON, from the renderer, not "failed". Exercised through the real `_still` with the render
    stubbed, because a probe that replaces `_still` cannot see what `_still` does with a failure."""
    _fake_run(mod, returncode=1,
              stderr="Bundling...\nError: StateSheet needs at least one `cells` entry\n"
                     "    at process.processTicksAndRejections (node:internal/x)")
    ok, why = mod._still("Zed", {}, os.path.join(tempfile.mkdtemp(), "x.png"), 10, "product")
    assert ok is False
    assert "cells" in (why or ""), "the renderer's own message was thrown away: %r" % (why,)
    assert "processTicksAndRejections" not in (why or ""), "the stack was kept instead of the reason"


PROBES["prop_reach"] = {
    "names_what_it_could_not_measure": _probe_prop_reach_names_what_it_could_not_measure,
    "coverage_is_derived": _probe_prop_reach_coverage_is_derived,
    "keeps_the_renderers_message": _probe_prop_reach_keeps_the_renderers_own_message,
}

MUTANTS["prop_reach"] = {
    "a hole in the coverage reads as a clean sweep":
        ("    return 1 if k else 0", "    return 0"),
    "the coverage line counts its own rows instead of the library":
        ('    k = _c.coverage("prop_reach", len([n for n in regs if n in set(univ)]), len(univ), gaps)',
         '    k = _c.coverage("prop_reach", len(regs), len(regs), {})'),
    "the render failure loses its reason":
        ("    return False, _c.render_error(r.stdout, r.stderr)", "    return False, None"),
    "an unmeasurable register is recorded as a bare name":
        ('                "_failed": dict(sorted(failed.items())),',
         '                "_failed": sorted(failed),'),
}


# ── band_debt ────────────────────────────────────────────────────────────────────────────────────────
def _probe_a_type_measurement_that_never_ran_is_not_zero_debt(mod):
    """`text_safe_qa` reports a failed render and an unparseable payload as ENTRIES with no `band` key, and
    `max([v.get("band") or 0 ...], default=0)` reads both as zero px of type in the band — the same answer a
    clean register gives. The register then went into the manifest as measured and clean."""
    assert mod._audit_failure([{"text": "(render FAILED twice — nothing was measured on this frame: x)",
                                "out": {}}]), "a render that never ran reads as no text debt"
    assert mod._audit_failure([{"text": "(unparseable payload)", "out": {}}]), (
        "a payload that could not be read reads as no text debt")
    assert mod._audit_failure([{"text": "REAL COPY", "band": 12}]) is None, (
        "a real finding was mistaken for a failed measurement")
    assert mod._audit_failure([]) is None


def _probe_band_debt_coverage_is_derived_and_a_hole_is_not_clean(mod):
    import json as _json
    d = tempfile.mkdtemp()
    mod._MANIFEST = os.path.join(d, "m.json")
    _json.dump({"registers": {}}, open(mod._MANIFEST, "w", encoding="utf-8"))
    mod.measure_all = lambda png_dir, quiet=False, only=None: (
        {}, {"Zed": "refused to render at frame 129: Error: no `src`"}, ["Alpha"])
    for lib, expect in ((["Alpha", "Zed"], "measured 1 of 2"),
                        (["Alpha", "Zed", "Omega"], "measured 1 of 3")):
        mod.universe = lambda lib=lib: list(lib)
        rc, out = _capture(mod.main, ["--check"])
        assert expect in out, "the coverage line does not follow the library (%r): %r" % (expect, out)
        assert "no `src`" in out, "the register's own reason is not in the output: %r" % out
        assert rc == 1, "a sweep that could not measure a register reported a clean check (exit %r)" % rc


def _probe_band_debt_refuses_to_write_a_manifest_with_a_hole(mod):
    """The manifest lists the registers IN DEBT, so a register that could not be measured is simply absent
    from it — the same shape as "repaired". The ratchet in test_remotion.py then reads a hole as progress."""
    import json as _json
    d = tempfile.mkdtemp()
    mod._MANIFEST = os.path.join(d, "m.json")
    _json.dump({"registers": {"Zed": {"band": 9.0, "edge": 0.0}}},
               open(mod._MANIFEST, "w", encoding="utf-8"))
    mod.universe = lambda: ["Alpha", "Zed"]
    mod.measure_all = lambda png_dir, quiet=False, only=None: (
        {}, {"Zed": "refused to render"}, ["Alpha"])
    rc, out = _capture(mod.main, ["--write"])
    assert rc != 0, "it wrote a manifest over a register whose debt is unknown: %r" % out
    assert _json.load(open(mod._MANIFEST, encoding="utf-8"))["registers"] == {"Zed": {"band": 9.0,
                                                                                     "edge": 0.0}}, (
        "the unmeasured register was dropped from the manifest, which reads as FIXED")


PROBES["band_debt"] = {
    "a_failed_type_measurement_is_not_zero_debt": _probe_a_type_measurement_that_never_ran_is_not_zero_debt,
    "coverage_is_derived": _probe_band_debt_coverage_is_derived_and_a_hole_is_not_clean,
    "refuses_to_write_over_a_hole": _probe_band_debt_refuses_to_write_a_manifest_with_a_hole,
}

MUTANTS["band_debt"] = {
    "a type measurement that never ran counts as no debt":
        ('        if not (v.get("out") or v.get("band")):', "        if False:"),
    "the coverage line counts the sweep against itself":
        ('    _c.coverage("band_debt", len(swept), len(only or universe()), not_measured)',
         '    _c.coverage("band_debt", len(swept), len(swept), {})'),
    "a hole in the sweep reads as a clean check":
        ("    return 1 if (fresh or worse or not_measured) else 0",
         "    return 1 if (fresh or worse) else 0"),
    "the manifest is written with a hole in it":
        ('        if not_measured:\n            print("[band_debt] REFUSING to write:',
         '        if False:\n            print("[band_debt] REFUSING to write:'),
}


# ── measure_ground_luma ──────────────────────────────────────────────────────────────────────────────
def _probe_the_settled_frame_follows_the_registers_own_duration(mod):
    """A fixed frame 110 is past the END of every register shorter than 111 — `remotion still` refuses it
    outright ("Cannot use frame 110: Duration of composition is 96") — and the retry at frame 30 then wrote
    a third-of-the-way-in reading into SHOT_LUMA as if it were the settled state."""
    short, long_ = mod.settled_frame("S", {"S": 96}), mod.settled_frame("L", {"L": 210})
    assert short is not None and 0 < short < 96, (
        "the settled frame is not inside a 96-frame register: %r" % (short,))
    assert long_ > short, "the frame does not follow DURATION — it is a constant: %r vs %r" % (short, long_)
    assert mod.settled_frame("X", {}) is None, "a register with no DURATION got a guessed frame"


def _probe_shot_luma_does_not_confirm_a_shot_it_could_not_render(mod):
    mod._fixture_props = lambda: {}
    mod._durations = lambda: {"Alpha": 150, "Zed": 150}
    mod.dna_audit = types.SimpleNamespace(registered_shots=lambda: ["Alpha", "Zed"])
    mod.read_shot_luma = lambda: {"Alpha": "dark", "Zed": "dark"}
    mod.provisional_shots = lambda: []
    mod.measure_own = lambda sh, td, fx=None, durs=None: (
        (0.001, None) if sh == "Alpha" else (None, "Error: needs a real photograph"))
    rc, out = _capture(mod.main, ["--luma", "--check"])
    assert "measured 1 of 2" in out, "the coverage line does not state the universe: %r" % out
    assert "photograph" in out, "the shot's own reason is not in the output: %r" % out
    assert rc == 1, "SHOT_LUMA reported its declaration confirmed over a shot it never measured"


def _probe_ground_token_does_not_confirm_a_shot_it_could_not_render(mod):
    """The other half of the same file, and the one the seam guard reads on a themed film."""
    mod._fixture_props = lambda: {}
    mod.dna_audit = types.SimpleNamespace(registered_shots=lambda: ["GlowPick"])
    mod.measure = lambda s, td, fx=None: (None, "Error: needs a real photograph")
    rc, out = _capture(mod.main, ["--only=GlowPick", "--check"])
    assert "measured 0 of 1" in out, "the coverage line does not state the universe: %r" % out
    assert rc == 1, "DNA_GROUND_TOKEN reported a match over a shot it never measured: %r" % out


PROBES["measure_ground_luma"] = {
    "settled_frame_follows_duration": _probe_the_settled_frame_follows_the_registers_own_duration,
    "shot_luma_does_not_confirm_a_hole": _probe_shot_luma_does_not_confirm_a_shot_it_could_not_render,
    "ground_token_does_not_confirm_a_hole": _probe_ground_token_does_not_confirm_a_shot_it_could_not_render,
}

MUTANTS["measure_ground_luma"] = {
    "the settled frame goes back to a constant":
        ("    return int(round(rr.frame_at_t(durs[shot], rr.SETTLED_T)))", "    return 110"),
    "SHOT_LUMA confirms a shot it could not measure":
        ("        if drift or prov or failed:", "        if drift or prov:"),
    "DNA_GROUND_TOKEN confirms a shot it could not measure":
        ('        if failed:\n            # A SHOT THAT WOULD NOT RENDER WAS NEVER COMPARED',
         '        if False:\n            # A SHOT THAT WOULD NOT RENDER WAS NEVER COMPARED'),
    "the coverage line counts what it managed to measure":
        ('    _c.coverage("ground_luma", len(meas), len(shots), failed)',
         '    _c.coverage("ground_luma", len(meas), len(meas), {})'),
}


# ── measure_ground_reach ─────────────────────────────────────────────────────────────────────────────
def _probe_ground_reach_does_not_confirm_a_safety_guard_it_could_not_measure(mod):
    """`GROUND_FOLLOWS_MEASURED` is the allow list `runtime/light.tsx` consults before it lets a beat
    re-ground a register. A shot that would not render keeps its entry — the safe choice, and an invisible
    one: the check then compared the committed set against a sweep with holes in it and printed "matches
    the measured pixels"."""
    d = tempfile.mkdtemp()
    # THE SWEEP WRITES ITS RECORD, and a non-`--only` run writes it BEFORE the --check verdict — so a probe
    # that calls main() against the real tree replaces `remotion/_ground_reach.json` with its two fake rows.
    # This probe did exactly that once. The module's own paths are redirected into a temp tree so the
    # measurement it takes lands there.
    mod._REMOTION = d
    mod.INK_REFUSED = {}
    mod.dna_audit = types.SimpleNamespace(registered_shots=lambda: ["Alpha", "Zed"])
    mod.probe_dnas = lambda: {"dna": {"light": {}, "dark": {}}, "groundY": {"light": 1.0, "dark": 0.0},
                              "groundInk": {"light": "#000", "dark": "#fff"}, "band": 200,
                              "groundLum": {"light": "light", "dark": "dark"}}
    mod.runtime_verdicts = lambda rows: {"ink": ["#000", "#fff"] * (2 * len(rows)),
                                         "lum": ["light", "dark"] * (2 * len(rows))}
    mod.read_set = lambda: {"Alpha", "Zed"}

    class R:
        returncode, stdout, stderr = 0, "", ""

    def run(cmd, **kw):
        # THE RENDER, not `render` itself — a probe that replaces `render` cannot see what `render` does
        # with a failure, and it leaves its own stub behind for the probe that is about exactly that.
        r = R()
        out_png = cmd[5]
        shot, _, key = os.path.basename(out_png)[:-4].partition("__")
        if shot == "Zed":
            r.returncode = 1
            r.stderr = ("An error occurred:\nError: needs a real photograph\n"
                        "    at process.processTicksAndRejections (node:internal/x)")
            return r
        _tiny_png(out_png, 240 if key == "light" else 5)
        return r
    mod.subprocess = types.SimpleNamespace(run=run)
    mod.stats = lambda shot, pngs, band_px: {"shot": shot, "bandY": {"light": 1.0, "dark": 0.0},
                                             "fieldY": {"light": 1.0, "dark": 0.0}, "moved": 1.0}
    rc, out = _capture(mod.main, ["--check", "--keep=" + d])
    assert "measured 1 of 2" in out, "the coverage line does not state the universe: %r" % out
    assert "photograph" in out, "the shot's own reason is not in the output: %r" % out
    assert rc == 1, "the allow list was reported as matching the pixels over a shot nobody measured: %r" % out
    assert "Zed" in out.split("cannot be confirmed")[-1], (
        "the unmeasured shot is LISTED in the guard and the check did not say so: %r" % out)


def _probe_ground_reach_keeps_the_renderers_own_message(mod):
    """Through the real `render`, for the reason the prop_reach twin gives."""
    _fake_run(mod, returncode=1,
              stderr="An error occurred:\nError: PhotoPlate needs a real photograph\n"
                     "    at process.processTicksAndRejections (node:internal/x)")
    png, why = mod.render("Zed", "light", {}, tempfile.mkdtemp())
    assert png is None
    assert "photograph" in (why or ""), "the renderer's own message was thrown away: %r" % (why,)
    assert "processTicksAndRejections" not in (why or ""), "the stack was kept instead of the reason"


PROBES["measure_ground_reach"] = {
    "does_not_confirm_a_hole": _probe_ground_reach_does_not_confirm_a_safety_guard_it_could_not_measure,
    "keeps_the_renderers_message": _probe_ground_reach_keeps_the_renderers_own_message,
}

MUTANTS["measure_ground_reach"] = {
    "the allow list is confirmed over a shot nobody measured":
        ('        if failed:\n            # THE SET IS A SAFETY GUARD',
         '        if False:\n            # THE SET IS A SAFETY GUARD'),
    "the coverage line counts the rows it managed to measure":
        ('    _c.coverage("ground_reach", len(rows), len(shots), failed)',
         '    _c.coverage("ground_reach", len(rows), len(rows), {})'),
    "a render failure loses its reason":
        ('        return None, "; ".join([_c.render_error(r.stdout, r.stderr)] + _FIXTURE_ERR)',
         '        return None, "failed"'),
}


# ── ink_contrast_qa: the gate that has been wrong in five different ways ─────────────────────────────
# This one was absent from this file entirely, which is the loudest kind of hole: it is the gate that has
# needed the most repair (a white card's FILL counted as ink, bold display type dropped as a fill, a
# wordmark read against paper two hundred pixels away, a panel's shadow reported, a fixed frame past the
# end of seven short registers), and every one of those repairs was pinned only by the case that prompted
# it. Its arithmetic is exercised on synthetic frames — no renders, no toolchain.
def _ink_map(shape=(540, 960)):
    import numpy as np
    return np.zeros(shape, dtype=bool)


def _probe_a_hole_is_a_place_not_an_amount(mod):
    """The rule that separates `AnswerStream` from `StateSheet`, which the share cannot: the same count of
    failing marks, scattered as rims or gathered into one lost paragraph, must NOT measure the same."""
    block, rims = _ink_map(), _ink_map()
    block[100:140, 300:600] = True                           # one lost line of type: 300x40
    for r in range(26):                                      # the SAME pixel count, spread as 1px rims
        for c in range(23):
            rims[80 + r * 12, 40 + c * 40: 40 + c * 40 + 20] = True
    assert abs(int(block.sum()) - int(rims.sum())) < 0.02 * int(block.sum()), \
        "the two maps must hold the same amount of failing ink, or the probe proves nothing"
    big, small = mod._largest_hole(block), mod._largest_hole(rims)
    assert big > 8 * small, ("a lost block and scattered rims measure alike: %d vs %d" % (big, small))


def _probe_a_lost_word_is_one_hole(mod):
    """Letters are separate shapes. Without closing the gaps between them the largest region a lost
    sentence can ever show is one letter — and the measure says what the share already said."""
    word, solid = _ink_map(), _ink_map()
    for k in range(6):
        word[300:340, 200 + k * 24: 200 + k * 24 + 20] = True
    solid[300:340, 200:344] = True
    assert mod._largest_hole(word) > 0.7 * mod._largest_hole(solid), \
        "the glyphs of one word are being counted as six separate holes"
    assert mod._largest_hole(_ink_map()) == 0, "a clean register must measure no hole at all"


def _probe_the_ground_behind_a_mark_is_the_one_behind_it(mod):
    """Polarity, and locality. White type on an accent TILE is read against the tile — measured against
    the frame's median `BentoReveal`'s wordmark scored 1.0:1, white on blue, which is what `onAccent` is
    for — and dark type on paper is read against the paper."""
    import numpy as np
    y = np.full((200, 300), 0.9, dtype=np.float32)           # paper
    y[40:160, 40:260] = 0.05                                 # a dark tile on it
    y[60:64, 60:240] = 0.95                                  # a stroke of white type ON the tile
    y[170:174, 40:260] = 0.02                                # a stroke of dark type on the paper
    # read at the middle of each stroke: a mark thicker than the probe radius has no ground within it, by
    # design — that is what keeps a bold glyph's INTERIOR out of the mask instead of reported as a fill
    g = mod._ground_behind(y, radius=3)
    assert g[62, 150] < 0.2, "white type on a dark tile is being read against the paper across the frame"
    assert g[172, 150] > 0.7, "dark type on paper is being read against something darker than the paper"


def _probe_the_settled_frame_is_the_one_useT_calls_settled(mod):
    """`useT` holds each shot still for SEAM_FRAMES at both edges and runs its span between them, so the
    settled point is the INVERSE of that mapping — not a fraction of the whole clip. Written as
    `DURATION * REDUCED_MOTION_T` the two disagreed on all 170 registers, by up to 12 frames."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("render_remotion",
                                                  os.path.join(_SCRIPTS, "render_remotion.py"))
    rr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rr)
    seen = 0
    for shot in ("FractureIn", "AnswerStream", "PixelBuild", "TerrainFly"):
        dur = mod._DUR.search(open(os.path.join(mod._SHOTS, shot + ".tsx"), encoding="utf-8").read())
        if not dur:
            continue
        seen += 1
        want = int(round(rr.frame_at_t(int(dur.group(1)), rr.SETTLED_T)))
        assert mod.settled_frame(shot) == want, \
            "%s: the gate measures frame %d, `useT` settles at %d" % (shot, mod.settled_frame(shot), want)
    assert seen >= 3, "the probe read no register's DURATION — it is proving nothing"


def _probe_a_hole_alone_is_a_finding(mod):
    """A register whose MEDIAN mark reads and whose share is small can still have lost a whole region —
    that is every one of the five that shipped. The verdict must fire on the hole by itself, and it must be
    asked of a row read back from `--store` as well as one just measured (a resumed sweep printed "every
    register's ink still reads" over findings it had written to disk itself)."""
    # MEASURED values, not `HOLE_FLOOR * 1.2` — a probe scaled by the constant it is testing moves with the
    # mutation and proves nothing. 0.0126 is `GFactorNoise`, whose title and every axis label went while its
    # median stayed 5.61 on a speckle field; 0.00082 is `StateSheet`'s soft caption rims, which cost nothing.
    lost = {"ink": 20000, "under": 6000, "share": 0.30, "median": 5.6, "worst": 1.1, "hole": 0.0126}
    fine = dict(lost, hole=0.00082)
    assert mod.is_finding(lost), "a lost region is not reported when the median and the share are fine"
    assert not mod.is_finding(fine), "a register with no hole worth the name is being reported"
    assert mod.is_finding({"lie": "declares @dark-world but took the film's LIGHT ground"})
    assert mod.is_finding({"blind": "keeps its own dark ground without declaring @dark-world"}), \
        "a register that never took the film's ground is not reported at all"
    assert not mod.is_finding({"skipped": "nothing to judge"}), "a skip is not a finding"


def _probe_a_register_never_seen_does_not_read_as_a_pass(mod):
    """The headline states COVERAGE against a universe it DERIVED, and a register that REFUSED TO RENDER
    moves the exit code — it was never seen, and this sweep's own history is four bugs hiding behind the
    word "skipped". A register that WAS rendered twice and simply has no ink to judge (its frame is the
    evidence picture; it is soft-edged throughout) is a complete answer and must not be counted as a hole.

    Run with the renders replaced, so this measures the bookkeeping and nothing else.
    """
    import shutil
    d = tempfile.mkdtemp()
    for n in ("Alpha", "Beta", "Gamma"):
        open(os.path.join(d, n + ".tsx"), "w", encoding="utf-8").write("export const DURATION = 150;\n")
    rows = {"Alpha": {"ink": 9000, "under": 10, "share": 0.001, "median": 9.0, "worst": 4.0, "hole": 0.0},
            "Beta": {"skipped": "the frame is the evidence picture (4 sharp mark(s) outside it)"},
            "Gamma": {"skipped": "refused to render: TypeError: props.rows is not iterable"}}
    try:
        mod._SHOTS = d
        mod.bundle = lambda out: None
        mod.ensure_alt_fixture = lambda: None
        mod._register_props = lambda: {}
        mod.measure = lambda shot, *a, **k: rows[shot]
        rc, out = _capture(mod.main, [])
        assert "measured 2 of 3 · 1 NOT measured" in out, out
        assert "Gamma" in out.split("NOT measured")[1][:300], "the register never seen is not named: %s" % out
        assert rc == 2, "a register that was never rendered exits %r, not 2" % rc
        # ...and the one that WAS read and has nothing to judge is not counted against coverage
        del rows["Gamma"]
        os.remove(os.path.join(d, "Gamma.tsx"))
        rc2, out2 = _capture(mod.main, [])
        assert "measured 2 of 2 · 0 NOT measured" in out2, out2
        assert rc2 == 0, "a clean sweep exits %r, not 0" % rc2
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _probe_a_waiver_forgives_only_what_it_names(mod):
    """A gate carrying a permanent finding stops being read to the end, so two registers whose flagged marks
    were looked at at 7x and judged furniture are waived — and a waiver that is not checked is a mute button.
    It forgives the HOLE rule only, and only up to the number measured on the day it was written."""
    ok = {"ink": 20000, "under": 5200, "share": 0.26, "median": 4.15, "worst": 1.2, "hole": 0.0103}
    assert not mod.is_finding(ok, "RansomZine"), "the waiver does not apply to the register it names"
    assert mod.is_finding(ok, "SomeOtherRegister"), "the waiver is forgiving registers it never named"
    assert len(mod.RIM_WAIVED) <= 4, \
        "the waiver list is growing into a habit — %d entries. Each one must name a form that CANNOT draw "\
        "the edge, with the number measured the day it was written." % len(mod.RIM_WAIVED)
    ceiling = mod.RIM_WAIVED["RansomZine"][0]
    assert mod.is_finding(dict(ok, hole=ceiling * 1.3), "RansomZine"), \
        "a waived register that got worse than its own ceiling is still silent"
    assert mod.is_finding(dict(ok, median=2.0), "RansomZine"), \
        "the waiver is silencing ink that stopped reading, which it does not cover"
    assert mod.is_finding(dict(ok, share=0.8), "RansomZine"), \
        "the waiver is silencing a register that lost most of its marks"


def _probe_a_ground_the_film_chose_is_not_a_blind_one(mod):
    """A dark frame on a light film is only a finding when the register was supposed to be painting the
    film's SHEET. `KineticManifesto` floods `accent`->`accent2` edge to edge, and on a light film those
    accents are dark by construction — the frame comes back at Y=0.13 with nothing wrong. The library
    already records which token each ground comes from; the gate reads that table rather than guessing."""
    assert len(mod._GROUND_TOKENS) > 100, \
        "the ground-token table was not read at all (%d entries) — every register would be held to the "\
        "film's key" % len(mod._GROUND_TOKENS)
    assert not mod.ground_is_the_films_sheet("KineticManifesto"), \
        "a register whose ground IS the film's accent flood is being held to the film's sheet"
    assert not mod.ground_is_the_films_sheet("PointerTour"), "a `surface` ground is not the film's sheet"
    assert mod.ground_is_the_films_sheet("ChartLive"), "a register declaring `bg` must be held to it"
    assert mod.ground_is_the_films_sheet("NoSuchRegisterExists"), \
        "a register missing from the table must still be held to the film's key, not exempted by absence"


PROBES["ink_contrast_qa"] = {
    "a_waiver_forgives_only_what_it_names": _probe_a_waiver_forgives_only_what_it_names,
    "a_ground_the_film_chose_is_not_a_blind_one": _probe_a_ground_the_film_chose_is_not_a_blind_one,
    "a_register_never_seen_does_not_read_as_a_pass": _probe_a_register_never_seen_does_not_read_as_a_pass,
    "a_hole_alone_is_a_finding": _probe_a_hole_alone_is_a_finding,
    "a_hole_is_a_place_not_an_amount": _probe_a_hole_is_a_place_not_an_amount,
    "a_lost_word_is_one_hole": _probe_a_lost_word_is_one_hole,
    "the_ground_behind_a_mark_is_the_one_behind_it": _probe_the_ground_behind_a_mark_is_the_one_behind_it,
    "the_settled_frame_is_the_one_useT_calls_settled": _probe_the_settled_frame_is_the_one_useT_calls_settled,
}
MUTANTS["ink_contrast_qa"] = {
    "a waived register is silent whatever it measures":
        ('    if ceiling is not None:\n        return row.get("hole", 0.0) > ceiling', '    if ceiling is not None:\n        return False'),
    "every register is held to the film's sheet, whatever its ground is":
        ('    names = re.findall(r"[A-Za-z]\\w*", tok)\n    return bool(names) and all(n in ("bg", "bgGrad") for n in names)',
         '    return True'),
    "the ground-token table is never read":
        ('        i = src.index("export const DNA_GROUND_TOKEN")', '        i = len(src)'),
    "the coverage line counts every register as measured":
        ('    _c.coverage("ink_contrast", len(out) - len(unseen), len(names), unseen)',
         '    _c.coverage("ink_contrast", len(names), len(names), {})'),
    "a register that never rendered leaves the exit code clean":
        ('    return 1 if findings else (2 if unseen else 0)', '    return 1 if findings else 0'),
    "a lost region is not a finding on its own": ("HOLE_FLOOR = 0.0027", "HOLE_FLOOR = 9.9"),
    "a ground the register never took reads as a pass":
        ('    if row.get("lie") or row.get("blind"):\n        return True',
         '    if False:\n        return True'),
    "the hole is the total failing ink, not one region":
        ("    counts = np.bincount(lab.ravel())\n    counts[0] = 0\n    return int(counts.max())",
         "    return int(solid.sum())"),
    "the failing marks are labelled before the gaps between glyphs are closed":
        ("    solid = _band(_band(bad, close, np.maximum), close, np.minimum)", "    solid = bad"),
    "the ground behind a mark loses its polarity":
        ("    return np.where(y < mid, hi, lo)", "    return hi"),
    "the settled frame goes back to a fraction of the clip":
        ("    return max(0, min(dur - 1, int(round(rr.frame_at_t(dur, rr.SETTLED_T)))))",
         "    return max(0, min(dur - 1, int(dur * rr.REDUCED_MOTION_T)))"),
}


# ── the fixture synthesiser: cjk_type_qa ─────────────────────────────────────────────────────────────
#
# This module decides what EVERY register in the library is fed, and it carried no mutant of any kind. A
# rule here can be deleted while the suite stays green and 181 registers are swept with the wrong props —
# which is the exact failure this file exists to catch, and the exact shape three of this session's
# findings took (a boolean selector true on every row; a numeric index nobody supplied; a demo object's
# numbers lost). Probes are synthetic so one rule can be removed at a time.

_REFUSAL_IN_CODE = "throw new Error('WhateverShot: pass `hero` \u2014 the row the tint follows.');"
_REFUSAL_IN_PROSE = "// you may pass `hero` to tint one cell; most films leave it unset\nhero?: boolean;"
_NESTED_DEMO = ("const DEMO_TYPICAL = {typical: 12, tail: 30, cap: {hi: 9}};\n"
                "export const S: React.FC<{typical?: {typical: number}}> = ({typical = DEMO_TYPICAL}) => null;")


def _probe_a_refusal_is_code_not_prose(mod):
    assert mod._refused_without("hero", _REFUSAL_IN_CODE), "a register's own throw no longer reads as a refusal"
    assert not mod._refused_without("hero", _REFUSAL_IN_PROSE), (
        "a doc comment that merely MENTIONS a prop reads as a refusal, so an OPTIONAL selector gets set on "
        "a row and the unset branch — what a film that omits it actually renders — never renders again")


def _probe_an_index_refusal_is_code_not_prose(mod):
    assert mod._is_an_index("target", "throw new Error(`pass \\`target\\` \u2014 the item to punch into.`)"), (
        "a refusal inside a template literal no longer reads as one; that regression took a full sweep to find")
    assert not mod._is_an_index("target", "// pass `target` to aim it somewhere else\ntarget?: number;"), (
        "a doc comment reads as a refusal, so an optional number is fed a list position")


def _probe_a_nested_demo_object_keeps_its_own_numbers(mod):
    got = mod._declared_numbers("typical", _NESTED_DEMO)
    assert got.get("typical") == 12 and got.get("tail") == 30, (
        "one nested value loses EVERY number the author declared, and the relation-based refusal these "
        "numbers exist to satisfy throws again, reporting a coverage hole instead of a finding: %r" % got)
    assert "hi" not in got, (
        "a nested object's field is being read as this object's field, which is a different wrong "
        "answer, not a fix: %r" % got)

    # ...and a QUOTED value is copy, not a field
    quoted = mod._declared_numbers("typical", "const D = {typical: 12, label: 'ratio: 9,'};\n"
                                              "const S = ({typical = D}) => null;")
    assert quoted == {"typical": 12}, (
        "a string whose CONTENT looks like a field contributes a number the register never declared: %r"
        % quoted)


def _probe_a_selector_is_not_set_on_every_row(mod):
    for flag in ("hero", "find", "done", "ok"):
        vals = [mod._synth_field(flag, "boolean", "const x = 1;", i, i) for i in range(4)]
        assert sum(bool(v) for v in vals) == 1, (
            "`%s` is set on %d of 4 rows; a sweep where every row is marked never renders the unmarked "
            "branch, which on these registers is half the picture" % (flag, sum(bool(v) for v in vals)))


def _probe_a_refused_flag_is_set_on_exactly_one_row(mod):
    src = "throw new Error('NearTheLine: needs at least one case marked `near` \u2014 else it argues the opposite.');"
    vals = [mod._synth_field("near", "boolean", src, i, i) for i in range(4)]
    assert sum(bool(v) for v in vals) == 1, (
        "a flag the register REFUSES without must be set on exactly one row — %r renders either a refusal "
        "or a frame with no unflagged branch" % (vals,))


# A TEMPLATE LITERAL INSIDE A TEMPLATE LITERAL. The blanker's first version scanned a template by running
# to the next unescaped backtick, which is the wrong backtick as soon as the template interpolates one:
# `FallbackPath` writes ``${missing.map((k) => `\`${k}\``).join(' or ')}`` inside its refusal. From there
# the scanner was off by one string and NOTHING downstream was blanked — 8 live comments in FallbackPath,
# 6 in TechnicalPlate, and the audit that added the blanker reported it as working, because the other 179
# files were fine. Caught by asking the blanked library how many comments SURVIVED, not by asking whether
# the thing it was built for still passed.
_NESTED_TEMPLATE = ("const msg = `got ${ks.map((k) => `\\`${k}\\``).join(' or ')}, so it stopped.`;\n"
                    "// you may pass `hero` to tint one cell\n"
                    "hero?: boolean;\n")


def _probe_a_template_inside_a_template_keeps_the_scanner_in_sync(mod):
    blanked = mod._code_only(_NESTED_TEMPLATE)
    assert len(blanked) == len(_NESTED_TEMPLATE), "the blanker changed the source LENGTH, so every offset moved"
    assert "//" not in blanked, (
        "a nested template literal puts the comment scanner out of sync, and every comment after it stays "
        "live — so the rules below read prose as code again, silently: %r" % blanked)
    assert not mod._refused_without("hero", _NESTED_TEMPLATE), (
        "the doc comment after a nested template still reads as a refusal")
    assert "got ${ks" in blanked and "stopped" in blanked, "the blanker ate the code it was meant to keep"

# A UNION FED ITS FIRST MEMBER ON EVERY ROW. The boolean-selector defect in a third shape, and the worst of
# the three: a register can REFUSE over it. `HardBarrier` refuses a board where every condition is a `gap`
# on purpose — that frame draws a run with an open road at the end and argues the opposite of its own claim,
# convincingly, past every gate. Fed `'gap'` on all four rows it could not render at all, and its
# `prop_reach` row read "could not be measured" while 182 of 183 rows were sound. A register no fixture can
# feed is a register nobody checks.
_UNION_REFUSAL = (
    "/** 'gap' = effort closes it · 'barrier' = nothing does */\n"
    "  kind?: 'gap' | 'barrier';\n"
    "const DEMO = [{label: 'a', kind: 'gap'}, {label: 'b', kind: 'barrier'}];\n"
    "  if (!rows.some((c) => c.kind === 'barrier')) throw new Error(\n"
    "    'Shot was given no condition with `kind: \"barrier\"`. Every condition being a gap argues the "
    "opposite.');\n")


def _probe_a_refused_union_member_reaches_exactly_one_row(mod):
    got = mod._refused_member("kind", ["gap", "barrier"], _UNION_REFUSAL)
    assert got == "barrier", (
        "the member the register's own refusal NAMES is not found, so the union is fed its first member on "
        "every row and a register that refuses without the other one cannot be fed at all: %r" % got)

    vals = [mod._synth_field("kind", "'gap' | 'barrier'", _UNION_REFUSAL, i, i) for i in range(4)]
    assert vals.count("barrier") == 1 and vals.count("gap") == 3, (
        "the refused member must land on exactly one row — every row carrying it renders only that branch, "
        "and no row carrying it renders nothing at all: %r" % vals)

    # ...and a union the register does NOT refuse over keeps its first member everywhere
    plain = "  side?: 'a' | 'b';\n"
    assert {mod._synth_field("side", "'a' | 'b'", plain, i, i) for i in range(3)} == {"a"}, (
        "an ordinary union changed shape — this rule must only fire on a refusal")
_NESTED_LIST_TYPE = (
    "type Stage = {\n"
    "  /** what this stage is, in the film's words */\n"
    "  label?: string;\n"
    "  cells?: {name?: string; share?: number}[];\n"
    "  lost?: number;\n"
    "};\n"
    "const DEMO: Stage[] = [{label: 'a', cells: [{name: 'x', share: 0.6}], lost: 0.55}];\n"
    "export const S: React.FC<{stages?: Stage[]}> = ({stages = DEMO}) => null;\n"
)


def _probe_a_nested_list_field_is_a_list_not_a_sentence(mod):
    rows = mod._shape_from_type("stages", "Stage[]", _NESTED_LIST_TYPE)
    assert isinstance(rows, list) and rows, "a register's own row type no longer shapes at all"
    r = rows[0]
    assert isinstance(r.get("cells"), list) and r["cells"], (
        "a row's OWN list came back as %r. The register is then handed a string where it declares a list, "
        "calls .some/.filter on it, and the sweep records 'refused to render \u2014 TypeError' under the "
        "REGISTER's name for a defect that is entirely the fixture's" % (r.get("cells"),))
    assert isinstance(r["cells"][0], dict) and r["cells"][0].get("name"), (
        "the nested rows carry no copy, so the one audit that reads Chinese type never sees any of it")
    assert "share" not in r, (
        "a field from INSIDE the nested object was hoisted into the parent row \u2014 the flat `;` split "
        "cutting the inline object in half, which is what turned the list into a sentence to begin with")


def _probe_a_fraction_is_read_from_the_registers_own_demo(mod):
    # THROUGH THE SYNTHESISER, not the helper. The first version of this probe asked `_demo_fraction`
    # directly and passed with the CALL SITE deleted — it proved the helper worked and said nothing about
    # whether anything used it, which is the exact shape of a rule that is not load-bearing.
    frac = mod._synth_field("lost", "number", "const DEMO = [{lost: 0.55}, {lost: 0.7}];", 0, 0)
    assert 0 < frac <= 1, (
        "a field this register's own demo writes as 0.55 is fed %r \u2014 whole shares where a fraction "
        "was declared, clamped to the cap, leaving a sliver where the subject should be" % (frac,))
    cnt = mod._synth_field("tally", "number", "const DEMO = [{tally: 6}, {tally: 12}];", 0, 0)
    assert cnt > 1, (
        "a COUNT reads as a fraction (%r), so a register that draws six strokes is asked for a third of "
        "one" % (cnt,))
    assert mod._demo_fraction("lost", "const DEMO = [{lost: 0.55}, {lost: 0.7}];"), (
        "a field this register's own demo writes as 0.55 no longer reads as a fraction, so it is fed 62 "
        "\u2014 sixty-two whole shares, clamped to the cap, leaving a sliver where the subject should be")
    assert not mod._demo_fraction("count", "const DEMO = [{count: 6}, {count: 12}];"), (
        "a COUNT reads as a fraction, so a register that draws six strokes is asked for 0.3 of one")
    assert not mod._demo_fraction("share", ""), (
        "a field with no evidence in the register at all is guessed rather than declined")


PROBES["cjk_type_qa"] = {
    "a_refusal_is_code_not_prose": _probe_a_refusal_is_code_not_prose,
    "a_refused_union_member_reaches_exactly_one_row":
        _probe_a_refused_union_member_reaches_exactly_one_row,
    "a_template_inside_a_template_keeps_the_scanner_in_sync":
        _probe_a_template_inside_a_template_keeps_the_scanner_in_sync,
    "an_index_refusal_is_code_not_prose": _probe_an_index_refusal_is_code_not_prose,
    "a_nested_demo_object_keeps_its_own_numbers": _probe_a_nested_demo_object_keeps_its_own_numbers,
    "a_selector_is_not_set_on_every_row": _probe_a_selector_is_not_set_on_every_row,
    "a_refused_flag_is_set_on_exactly_one_row": _probe_a_refused_flag_is_set_on_exactly_one_row,
    "a_nested_list_field_is_a_list_not_a_sentence": _probe_a_nested_list_field_is_a_list_not_a_sentence,
    "a_fraction_is_read_from_the_registers_own_demo":
        _probe_a_fraction_is_read_from_the_registers_own_demo,
}
MUTANTS["cjk_type_qa"] = {
    # the flat split this replaced: one inline object inside a type body cuts a field in half and invents
    # a sibling out of the other half
    "a type body is split on every `;`, so a nested object halves a field":
        ('    for chunk in _top_split(body, ";"):', '    for chunk in body.split(";"):'),
    "a row's own list falls through to a sentence":
        ("    if depth < _MAX_NEST:\n        mm = re.match(r\"^\\{(.+)\\}(\\[\\])?$\", t)",
         "    if False:\n        mm = re.match(r\"^\\{(.+)\\}(\\[\\])?$\", t)"),
    "the register's own demo stops deciding whether a number is a fraction":
        ("        if _demo_fraction(name, src):", "        if False:"),
    # the flat scan this replaced: a backtick runs to the next backtick, which inside a nested template
    # is the one that OPENS the inner one
    "a template literal is scanned flat, so a nested one desyncs it":
        ('        if c == "`":\n            stack.append("tpl")\n            i += 1\n            continue',
         '        if c == "`":\n            q, i = c, i + 1\n'
         '            while i < n and src[i] != q:\n                i += 2 if src[i] == "\\\\" else 1\n'
         '            i += 1\n            continue'),
    "a union is always fed its first member":
        ('        want = _refused_member(name, members, src)', '        want = None'),
    "the refusal matcher ignores the backtick, so it finds the demo default":
        ('        if re.search(r"\\\\?`%s\\s*:\\s*\\\\?[\\"\']%s\\\\?[\\"\']"',
         '        if re.search(r"%s\\s*:\\s*\\\\?[\\"\']%s\\\\?[\\"\']"'),
    "a comment reads as a refusal":
        ("% re.escape(prop), _code_only(src)))", '% re.escape(prop), src or ""))'),
    "a comment reads as an index refusal":
        ("% re.escape(prop), _code_only(src)):", '% re.escape(prop), src or ""):'),
    "a demo object with any nested value yields nothing":
        ("            if depth == 0:\n                return src[brace + 1:i]",
         "            if depth == 0:\n                return None"),
    "a quoted value's contents count as fields":
        ('        if c in "\'\\"`":                     # a QUOTED value is copy, not a field',
         '        if False:                     # a QUOTED value is copy, not a field'),
    "a nested object's fields count as this object's":
        ("        elif depth == 0:\n            m = _NUM_PAIR.match(body, i)",
         "        else:\n            m = _NUM_PAIR.match(body, i)"),
    "a selector goes back to being set on every row":
        ('        if name in ("find", "hero", "done", "ok"):\n            return rowIdx == 0',
         '        if name in ("find", "hero", "done", "ok"):\n            return True'),
    "a refused flag goes back to being set on every row":
        ("        if _refused_without(name, src):\n            return rowIdx == 0",
         "        if _refused_without(name, src):\n            return True"),
}


@pytest.mark.parametrize("module,rule", _all(PROBES))
def test_probe_holds_on_the_real_module(module, rule):
    """Every probe must pass against the shipped code. A probe that cannot pass is not a probe."""
    PROBES[module][rule](load(module))


@pytest.mark.parametrize("module,mutant", _all(MUTANTS))
def test_mutant_is_caught_by_some_probe(module, mutant):
    """Disabling one rule must make at least one probe fail. This is the claim the audit disproved."""
    mod = load(module, MUTANTS[module][mutant])
    for rule, probe in PROBES[module].items():
        try:
            probe(mod)
        except AssertionError:
            return                                   # caught
        except Exception as exc:                     # a mutant that crashes a probe is also caught
            assert exc is not None
            return
    raise AssertionError("mutant %r survives every probe — the rule it disables is not load-bearing"
                         % mutant)


def test_every_mutant_text_still_exists():
    """A mutation whose `old` text has drifted silently becomes a no-op, and a no-op always 'passes'."""
    for module, muts in MUTANTS.items():
        src = open(MODULE_PATH[module], encoding="utf-8").read()
        for name, (old, _new) in muts.items():
            assert old in src, "%s: mutant %r no longer matches the source" % (module, name)


@pytest.mark.parametrize("module", sorted(MUTANTS))
def test_all_mutants_at_once_are_caught(module):
    """The audit's exact framing: 29 mutations, each reverting a claimed repair, applied SIMULTANEOUSLY,
    and the whole suite stayed green. Applying them one at a time is the sharper test — this one only
    confirms the headline case, and that a module carrying every regression at once cannot pass."""
    src = open(MODULE_PATH[module], encoding="utf-8").read()
    applied = 0
    for old, new in MUTANTS[module].values():
        if old in src:
            src = src.replace(old, new, 1)
            applied += 1
    assert applied >= 2, "%s: fewer than two mutants applied" % module
    mod = types.ModuleType(module)
    mod.__file__ = MODULE_PATH[module]
    try:
        exec(compile(src, MODULE_PATH[module], "exec"), mod.__dict__)
    except Exception:
        return                                    # a module carrying every regression no longer loads
    for probe in PROBES[module].values():
        try:
            probe(mod)
        except Exception:
            return
    raise AssertionError("%s survives ALL %d of its mutants at once" % (module, applied))


def test_the_idiom_world_gate_actually_refuses_the_wrong_world():
    """The gate that converts "this design feels inappropriate" into a refusal.

    Its whole value is the ERROR path, and that path was never exercised when it was written: the film it
    was built for declared eight of the thirteen worlds, which happened to cover every register it used, so
    every run looked green whether or not the check worked. Each branch is exercised here, including the one
    that made the check decay silently — a register with no PROVENANCE entry, which validate looks up, gets
    nothing for, and skips. Every register built after the table was written would have arrived untagged.
    """
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import shot_director as sd
    import validate as v

    def board(**over):
        m = {"renderer": "remotion", "fps": 30, "shot_template": "data",
             "form_vocabulary": [{"form": "a", "carries": "x"}, {"form": "b", "carries": "x"},
                                 {"form": "c", "carries": "x"}, {"form": "d", "carries": "x"}],
             "idiom_world": ["survey-archive"]}
        m.update(over)
        return {"meta": m, "slides": [
            {"index": i, "shot": "MapPlate", "shot_props": {"place": "X", "marks": []},
             "shot_adaptation": {"kept": "k", "redesigned": "r", "topic_idea": "t"},
             "shot_fit": {"verdict": "adapt", "why": "w", "form": "a"},
             "audio": "audio/%02d.mp3" % i, "duration": 5.0, "narration": "A line."} for i in range(4)]}

    def errs(b):
        return v.evaluate(b, "/tmp")["errors"]

    assert not errs(board()), errs(board())

    # a beat speaking a world the film did not declare
    b = board()
    b["slides"][1]["shot"] = "TermDiff"
    assert any("comes from" in e and "developer-tooling" in e for e in errs(b)), \
        "a terminal idiom in a survey film must be refused"

    # a declared world that does not exist
    assert any("unknown world" in e for e in errs(board(idiom_world=["not-a-world"])))

    # THE DECAY PATH: an untagged register must be a finding, not a silent pass
    saved = sd.PROVENANCE.pop("MapPlate")
    try:
        b = board(idiom_world=["print-editorial"])          # MapPlate's real world is NOT declared
        assert any("no PROVENANCE" in e for e in errs(b)), \
            "an untagged register is exempt from the gate by accident, so it must be reported"
    finally:
        sd.PROVENANCE["MapPlate"] = saved

    # and every register in the library carries one, or the gate is already partly decorative
    untagged = sorted(k for k in sd.FAMILY if k not in sd.PROVENANCE)
    assert not untagged, "registers with no idiom world: %s" % ", ".join(untagged[:8])


def test_every_beat_must_name_a_form_the_film_derived():
    """The step that stops the catalogue supplying the vocabulary. Both failure directions are exercised:
    a beat that names no form at all, and one that names a form the film never derived."""
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import validate as v

    def board(mutate=None):
        b = {"meta": {"renderer": "remotion", "fps": 30, "shot_template": "data",
                      "form_vocabulary": [{"form": "map plate", "carries": "where"},
                                          {"form": "ledger", "carries": "a count"},
                                          {"form": "section", "carries": "levels"},
                                          {"form": "label", "carries": "evidence"}],
                      "idiom_world": ["survey-archive"]},
             "slides": [{"index": i, "shot": "MapPlate", "shot_props": {"place": "X", "marks": []},
                         "shot_adaptation": {"kept": "k", "redesigned": "r", "topic_idea": "t"},
                         "shot_fit": {"verdict": "adapt", "why": "w", "form": "map plate"},
                         "audio": "audio/%02d.mp3" % i, "duration": 5.0, "narration": "A line."}
                        for i in range(4)]}
        if mutate:
            mutate(b)
        return b

    assert not v.evaluate(board(), "/tmp")["errors"]

    def drop(b):
        del b["slides"][2]["shot_fit"]["form"]
    assert any("name no `shot_fit.form`" in e for e in v.evaluate(board(drop), "/tmp")["errors"])

    def invent(b):
        b["slides"][1]["shot_fit"]["form"] = "a form nobody derived"
    assert any("not in meta.form_vocabulary" in e for e in v.evaluate(board(invent), "/tmp")["errors"])

    # and a film that never derived anything is told so
    def strip(b):
        del b["meta"]["form_vocabulary"]
    assert any("no meta.form_vocabulary" in w for w in v.evaluate(board(strip), "/tmp")["warnings"])
