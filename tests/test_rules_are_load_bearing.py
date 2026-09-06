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
    "demo_copy_qa": os.path.join(_SCRIPTS, "demo_copy_qa.py"),
    "energy_skeleton": os.path.join(_SCRIPTS, "energy_skeleton.py"),
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
    }
    quiet = ["这段代码是 AI 写的，能跑，测试全绿，但它其实是错的，而且没有任何提示。", "写崩的会当场报错。",
             "所以我们又跑了一遍，结果发现边界上差了一个等号，于是补了个用例。", "覆盖率只证明这行被执行过。",
             "因为出题的和判卷的是同一个来源，错误模式也一样，所以互相看不见对方的盲区。", "还没人做过受控比较。",
             "有个数字到处在传，但我们查了那份报告，里面根本没有它，所以别当结论。", "先弄坏它一次。"]
    quiet_fired = set(mod.evaluate([(i, t) for i, t in enumerate(quiet)])["fired"])
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
        ('[(k, v, "latin") for k, v in EN_TELLS.items()]):', '[]):'),
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
              "ink_median": 0.043, "luma_range": 0.079, "luma_steps": 0.000, "luma_windows": 163}
_ALIVE = {"seconds": 81.0, "motion_p50": 0.0181, "motion_p75": 0.0481, "motion_p90": 0.1169,
          "ink_median": 0.361, "luma_range": 0.903, "luma_steps": 0.425, "luma_windows": 81}
# The gaming case, MEASURED: the delivered film with four seconds of a blank white rectangle appended. Every
# other frame identical; the luminance RANGE goes from 0.097 to 0.910 and clears its floor by 6.7x.
_GAMED = {"seconds": 60.0, "motion_p50": 0.0005, "motion_p75": 0.0025, "motion_p90": 0.0089,
          "ink_median": 0.047, "luma_range": 0.910, "luma_steps": 0.017, "luma_windows": 60}


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
    for word in ("MOTION", "DENSITY", "LIGHT"):
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


PROBES["film_energy_qa"] = {
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

MUTANTS["film_energy_qa"] = {
    "the motion floor is disabled":
        ("MOTION_P75_FLOOR = 0.0037", "MOTION_P75_FLOOR = 0.0"),
    "the density floor is disabled":
        ("INK_FLOOR = 0.12", "INK_FLOOR = 0.0"),
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
    "a render that never ran passes":
        ('        return [{"text": "(render failed: %s)" % (blob.strip().splitlines() or ["?"])[-1][:160], "out": {}}]',
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
        ('                        "--props=" + os.path.abspath(pf)],',
         '                        "--props=" + json.dumps(payload)],'),
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
    was_measure = mod.fe.measure
    try:
        mod.fe.measure = lambda *a, **k: {"motion_p75": 0.5, "ink_median": 0.372, "luma_range": 0.5,
                                          "seconds": 5.0}
        mod.main(["--only=Alpha"])
    finally:
        mod.fe.measure = was_measure
    out = _json.load(open(path, encoding="utf-8"))
    assert out["registers"]["Alpha"]["ink_median"] == 0.372, "the re-measure never reached the record"
    assert out["registers"]["Old"]["ink_median"] == 1, "the partial sweep clobbered a row it never rendered"


PROBES["register_energy"] = {
    "floors_are_derived": _probe_floors_are_derived_not_restated,
    "unmeasured_is_not_passing": _probe_an_unmeasured_register_is_not_a_passing_one,
    "fixture_is_derived": _probe_the_fixture_list_is_derived_from_the_call_sites,
    "cache_separates_design_systems": _probe_the_render_cache_distinguishes_two_design_systems,
    "partial_sweep_reaches_the_record": _probe_a_partial_sweep_reaches_the_record,
}

MUTANTS["register_energy"] = {
    "the floors become a private copy":
        ('    return {"motion_p75": fe.MOTION_P75_FLOOR, "ink_median": fe.INK_FLOOR, "luma_range": fe.LUMA_RANGE_FLOOR}',
         '    return {"motion_p75": 0.0037, "ink_median": 0.12, "luma_range": 0.135}'),
    "an unmeasured register reads as fine":
        ("    return 1 if unknown else 0", "    return 0"),
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
export const Demo: React.FC<{title?: string; marks?: {n: number; label: string}[]}> = ({
  title = 'WorkBuddy', marks = [{n: 1, label: 'what to notice here'}], accent = '#22d3ee',
  align = 'center',
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


PROBES["demo_copy_qa"] = {
    "read_from_the_signature": _probe_demo_copy_is_read_from_the_signature,
    "configuration_is_not_copy": _probe_configuration_is_not_mistaken_for_copy,
    "partial_props_are_caught": _probe_a_partially_supplied_beat_is_caught,
}

MUTANTS["demo_copy_qa"] = {
    # The real bug this rule fixes is OVER-running the destructure into the component body, where every
    # JSX attribute looks like `name = "value"`. Under-running is caught by the same probe's marks assertion.
    "the destructure has no end, so the component body counts as props":
        ("    depth, j = 0, start", "    return src[start + 1:]\n    depth, j = 0, start"),
    "colours and css keywords count as copy":
        ('            if re.search(r"[A-Za-z]{3}", v) and not _NOT_COPY.match(v):',
         '            if re.search(r"[A-Za-z]{3}", v):'),
    "an absent prop stops being a finding":
        ("            if prop not in props:", "            if False:"),
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
