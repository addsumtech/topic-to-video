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
        "shot_director.py": '    "Zed": "D",\n',
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
        d.rectangle([0, h - bp, w, h], fill=tuple(min(255, c + 60) for c in ground))
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
    """The reserved band is the renderer's, and it differs by aspect."""
    assert mod._caption_band_px(1080, 1920) == 200
    assert mod._caption_band_px(1920, 1080) == 150


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
        assert not ok["errors"], "%s ground: a clean film cannot be delivered (%r)" % (label, ok["errors"][:1])
        assert bad["errors"], "%s ground: a real overflow is not blocked" % label


PROBES["shot_still_qa"] = {
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
        ("    if abs(band_ground - ground_all) > _INK_DELTA and edge_step > _BAND_EDGE_STEP:",
         "    if abs(band_ground - ground_all) > _INK_DELTA:"),
    "coverage never detected":
        ("    if abs(band_ground - ground_all) > _INK_DELTA and edge_step > _BAND_EDGE_STEP:",
         "    if False:"),
    "band width no longer follows the frame":
        ("    return 200 if w < 1400 else 150", "    return 150"),
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


def _all(kind):
    return [(m, k) for m, d in kind.items() for k in d]


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
