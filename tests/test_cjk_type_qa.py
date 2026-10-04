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
    assert set(props) >= {"sectionLabel", "title", "headline", "deck", "contents"}, props
    assert not untestable, untestable
    # A value is COPY: a string, or a list of them (`contents` is the register's index list). The first
    # version of this asserted `isinstance(v, str)` and broke the day a register grew a list prop, which
    # is a test pinning the fixture's incidental shape rather than the rule it exists for.
    def copyish(v):
        return isinstance(v, str) or (isinstance(v, list) and v and all(isinstance(x, str) for x in v))
    assert all(copyish(v) for v in props.values()), props
    assert all(c._HAS_CJK.search(v if isinstance(v, str) else v[0]) for v in props.values()), props


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
    """Deleting the hand table no longer makes a prop unfeedable — shapes come from the register's own type
    now, which is the point. So the contract under test is the REMAINING one: a prop whose shape cannot be
    resolved by EITHER route is reported, never silently skipped, because a register nobody can feed is
    exactly where this defect hides."""
    # TermTree declares `items?: Item[]` — a NAMED alias, so blinding the type resolver leaves no route.
    # (TimelineTravel's nodes are an INLINE object type and are resolved by the other branch, which is why
    # this test names a register whose shape actually depends on the alias.)
    #
    # IT PATCHES `_type_fields`, which is the resolver — `_alias_fields` used to be a second name for the
    # same lookup and this test went green through it while the real route stayed open. The two were merged
    # when the reader learned to read UNION aliases; a test that blinds a wrapper nothing calls asserts
    # nothing, which is the failure mode this whole file is about.
    monkeypatch.setattr(c, "_type_fields", lambda ty, src, _depth=0: None)
    monkeypatch.setattr(c, "_ARRAY_SHAPES", {})
    _, untestable = c.cjk_props("TermTree")
    assert "items" in untestable


def test_the_type_derived_shape_survives_losing_the_hand_table(monkeypatch):
    """The hand table is an OVERRIDE for what the parser cannot reach, not the source of truth. Keyed by
    prop NAME it was actively wrong: `items` is declared by many registers with different element shapes."""
    monkeypatch.setattr(c, "_ARRAY_SHAPES", {})
    props, untestable = c.cjk_props("TimelineTravel")
    assert not untestable and isinstance(props["nodes"][0], dict) and "label" in props["nodes"][0]
    tree, _ = c.cjk_props("TermTree")
    assert set(tree["items"][0]) == {"name", "note", "tag"}, "shaped from TermTree's OWN type alias"


def test_colours_and_images_are_not_fed_chinese():
    props, _ = c.cjk_props("MetaballMerge")
    assert "accent" not in props and "accent2" not in props


# ── the CJK leading floor, RUN — not grepped ───────────────────────────────────────────────────────
def _run_probe(body):
    """Bundle `body` against the REAL cjkType.ts and run it, so this tests BEHAVIOUR, not the presence of
    source text. Same shape as tests/test_camera_pan.py's probe."""
    import shutil as _sh, subprocess as _sp, tempfile as _tf
    if not _sh.which("npx") or not _sh.which("node"):
        pytest.skip("npx/node unavailable")
    rem = os.path.join(_ROOT, "remotion")
    if not os.path.isdir(os.path.join(rem, "node_modules")):
        pytest.skip("remotion/node_modules not installed")
    tmp = _tf.mkdtemp(prefix="cjk_probe_")
    try:
        entry = os.path.join(tmp, "probe.ts")
        header = ("import * as C from %s;\nconst out: any = {};\n"
                  % json.dumps(os.path.join(rem, "src", "runtime", "cjkType")))
        open(entry, "w", encoding="utf-8").write(header + body + "\nconsole.log(JSON.stringify(out));\n")
        outf = os.path.join(tmp, "probe.cjs")
        b = _sp.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--outfile=" + outf,
                     "--log-level=error"], cwd=rem, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = _sp.run(["node", outf], cwd=rem, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        _sh.rmtree(tmp, ignore_errors=True)


def test_has_cjk_covers_every_script_a_film_might_use():
    """zh-Hans, zh-Hant, kana, kanji, Hangul and CJK punctuation are all CJK; Latin, digits and emoji are
    not. A detector that misses Japanese would leave a Japanese film with the defect this floor exists for."""
    out = _run_probe("""
      const cases: [string, string][] = [
        ['zh_hans', '交付可验收的成果'], ['zh_hant', '交付可驗收的成果'], ['kana', 'おつかれさまです'],
        ['kanji', '納品物'], ['hangul', '전달물'], ['cjk_punct', '交付，然后。'], ['fullwidth', '（授权）'],
        ['latin', 'An accepted result'], ['digits', '100+ experts'], ['emoji', 'done'], ['empty', ''],
      ];
      cases.forEach(([k, v]) => { out[k] = C.hasCJK(v); });
      out.notAString = C.hasCJK(42 as never);
    """)
    for k in ("zh_hans", "zh_hant", "kana", "kanji", "hangul", "cjk_punct", "fullwidth"):
        assert out[k] is True, k
    for k in ("latin", "digits", "emoji", "empty", "notAString"):
        assert out[k] is False, k


def test_leading_raises_for_cjk_and_never_touches_latin():
    out = _run_probe("""
      out.latinTight   = C.leading('WORK BUDDY', 0.82);
      out.cjkTight     = C.leading('自主循环', 0.82);
      out.cjkAlready   = C.leading('自主循环', 1.4);
      out.arrayAnyCJK  = C.leading(['WORK', '自主循环'], 0.82);
      out.arrayNoCJK   = C.leading(['WORK', 'BUDDY'], 0.82);
      out.emptyArray   = C.leading([], 0.82);
      out.undef        = C.leading(undefined, 0.82);
      out.floor        = C.CJK_MIN_LEADING;
    """)
    assert out["latinTight"] == 0.82, "a Latin stack must render byte-for-byte as before"
    assert out["cjkTight"] == out["floor"] > 1.0
    assert out["cjkAlready"] == 1.4, "the floor RAISES; it never lowers an author's larger value"
    assert out["arrayAnyCJK"] == out["floor"], "one CJK string in the block raises the whole block"
    assert out["arrayNoCJK"] == 0.82 and out["emptyArray"] == 0.82 and out["undef"] == 0.82


def test_fit_if_cjk_leaves_latin_at_its_designed_size():
    out = _run_probe("""
      const half = (t: string, base: number) => base / 2;
      out.latin = C.fitIfCJK('An accepted result', 116, half);
      out.cjk   = C.fitIfCJK('交付可验收的成果', 116, half);
      out.mixed = C.fitIfCJK('WorkBuddy 是全场景 AI 工作台', 116, half);
      out.undef = C.fitIfCJK(undefined, 116, half);
    """)
    assert out["latin"] == 116 and out["undef"] == 116, "Latin keeps the register's own size"
    assert out["cjk"] == 58 and out["mixed"] == 58, "mixed copy counts as CJK — the CJK half is what wraps"


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


def test_every_register_with_tight_leading_uses_the_floor_or_says_why_it_cannot_wrap():
    """THE CLASS, closed at the source rather than watched by a sweep.

    A face set below ~1.05 is confident Latin display typography and a collision in Chinese. Three registers
    shipped that way; fixing those three fixes three instances. So the rule is stated here instead: a
    register that sets tight leading must EITHER pass its copy through `leading()` — which raises only for
    CJK, so its Latin typography is untouched — OR declare, in one line, why its type cannot wrap at all
    (nowrap, fitted to a single line, or a numeric readout). Silence is not an option, which is the same
    discipline INTRINSIC_TEXT and requireEvidence run elsewhere in this library.

    Checked statically so it costs nothing and cannot be skipped; `cjk_type_qa --library` remains the
    MEASUREMENT, and this is the thing that stops register 154 from reintroducing it.

    WHERE THIS RULE STOPS, deliberately. The pattern below requires a DECIMAL point, so `px/1` — exactly
    1.0, and used by 97 of the 153 registers — is outside it. That is not an oversight to fix by widening
    the regex: most of those 97 set a single word, a numeral or a chip that cannot wrap, and a static test
    cannot tell those from a card label. `CardStack3D` was in that blind spot and shipped a three-line
    Chinese label at 1.0 on a delivered film. The MEASUREMENT covers it instead: the sweep reports `tight`
    for copy that actually wrapped below `CJK_MIN_LEADING`, which needs no guess about what can wrap.
    """
    import glob
    offenders = []
    for f in sorted(glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx"))):
        src = open(f, encoding="utf-8").read()
        if not re.search(r"px/(0\.\d+|1\.0[0-4])[\s`']", src):
            continue
        if "runtime/cjkType" in src or "CJK-EXEMPT" in src:
            continue
        offenders.append(os.path.basename(f)[:-4])
    assert not offenders, (
        "these set a leading under 1.05 on type that can wrap, without the CJK floor and without saying why "
        "it cannot wrap: %s. Either pass the copy through `leading(text, latin)` from runtime/cjkType, or "
        "add a `// CJK-EXEMPT (tight leading, no floor): <reason>` line above the component." % offenders)


def test_the_declared_exemptions_are_the_ones_that_really_cannot_wrap():
    """An exemption must be TRUE, not merely written. Each declared one is checked against the property it
    claims, so a comment cannot become a way to opt out of the rule."""
    import glob
    for f in sorted(glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx"))):
        src = open(f, encoding="utf-8").read()
        if "CJK-EXEMPT" not in src:
            continue
        name = os.path.basename(f)[:-4]
        assert re.search(r"nowrap|fitTextPx|NUMERAL|numeral", src), \
            "%s claims a CJK exemption but shows no nowrap, no one-line fit and no numeric readout" % name


# ── the CONTROL contract — the part that already failed twice ───────────────────────────────────────
def test_the_positive_control_is_synthetic_not_a_real_register():
    """The first controls were the two registers that had broken a film. They worked exactly once: repairing
    both made the controls report 'not caught', and the instrument could no longer show it detects anything."""
    assert c.CONTROLS_BAD and all(n.endswith("Probe") for n in c.CONTROLS_BAD), c.CONTROLS_BAD
    assert "TypeCollisionProbe" in c.CONTROLS_BAD
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


def test_a_cjk_face_is_bundled_so_the_dna_typography_reaches_chinese():
    """The finding this closes: ten Latin faces were bundled and none carried a Han glyph, so every Chinese
    character was drawn by whatever the render machine had. Measured on one register across the two DNAs
    whose display faces differ most — English 1480 vs 1573px, Chinese 1383 vs 1383px. Width is the WRONG
    metric for CJK (every Han glyph is one em wide, so two faces give identical widths); the proof is the
    SHAPE, and the same DNA's Chinese title changed at IoU 0.689 once the faces were bundled."""
    cov = c.bundled_cjk_coverage()
    if cov is None:
        pytest.skip("fontTools not installed")
    drawing = [f for f, has in cov if has]
    assert len(drawing) >= 2, "a CJK sans AND a CJK serif must be bundled, or a serif DNA is sans in Chinese"
    ts = open(os.path.join(_ROOT, "remotion", "src", "runtime", "fonts.ts"), encoding="utf-8").read()
    for fam in ("Noto Sans SC", "Noto Serif SC"):
        assert "family: '%s'" % fam in ts, "%s is on disk but fonts.ts does not load it" % fam
    dna = open(os.path.join(_ROOT, "remotion", "src", "runtime", "dna.tsx"), encoding="utf-8").read()
    import re as _re
    naked = _re.findall(r'(?<!SC", )"PingFang SC"', dna)
    assert not naked, ("%d DNA font stack(s) still reach a system CJK font before a bundled one — those "
                       "render differently on another machine" % len(naked))


def test_a_character_the_subset_cannot_draw_is_refused_by_name():
    """The subset is GB2312 + kana, which is normal prose and not every character that exists. A glyph the
    face cannot draw is an empty box beside correct type and reads as a rendering bug, so it is refused with
    the character named rather than shipped."""
    if c.subset_coverage("交付") is None:
        pytest.skip("fontTools not installed")
    assert c.subset_coverage("交付可验收的成果，办公的产物本身就是文件。") == []
    assert c.subset_coverage("おつかれさまです") == [], "kana is in the subset — ja is an offered language"
    rare = c.subset_coverage("龘")
    assert rare and rare[0][0] == "龘"
    import sys as _s
    _s.path.insert(0, os.path.join(_ROOT, "scripts"))
    import validate as v
    board = {"meta": {"renderer": "remotion", "title": "t", "language": "zh"},
             "slides": [{"index": 0, "shot": "ChatThread", "shot_props": {}, "narration": "龘字交付"}]}
    hits = [e for e in v.evaluate(board, "/tmp", pre_tts=True)["errors"] if "bundled CJK subset" in e]
    assert hits and "龘" in hits[0], hits


def test_the_gate_says_so_when_no_bundled_face_can_draw_chinese():
    """The finding this records: fonts.ts bundles ten Latin faces and no CJK one, so every Chinese glyph is
    drawn by whatever the render machine has. Measured on one register across two DNAs whose display faces
    are as different as the library holds — English 1480 vs 1573px, Chinese 1383 vs 1383px."""
    src = open(os.path.join(_ROOT, "scripts", "cjk_type_qa.py"), encoding="utf-8").read()
    assert "1383" in src and "1573" in src, "the measurement that proves it must travel with the claim"
    assert "NONE of the %d bundled faces" in src, "the warning must survive for a repo that drops the faces"


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


# ── tilted type: the instrument was wrong in BOTH directions, so both are pinned ────────────────────
_TEXTSAFE = os.path.join(_ROOT, "remotion", "src", "runtime", "textSafe.tsx")
_NEEDS_REMOTION = pytest.mark.skipif(not os.path.isdir(os.path.join(_ROOT, "remotion", "node_modules")),
                                     reason="needs the remotion toolchain")


def _probe_leading(name, props=None):
    """The leading findings a probe reports, through the real render path."""
    tmp = os.path.join(_ROOT, "remotion", ".cjk_type_test.png")
    try:
        hits = c.audit(name, props or {}, 145, tmp, "product")
        assert hits is not None, "%s failed to render" % name
        return [h for h in hits if h["kind"] in ("leading", "unmeasured")]
    finally:
        for f in (tmp, tmp + ".props.json"):
            if os.path.exists(f):
                os.remove(f)


@_NEEDS_REMOTION
def test_the_rotation_guard_is_load_bearing_in_both_directions():
    """Remove it and the instrument does not merely get noisier — it inverts.

    A client rect is axis-aligned, so a tilted line's rect is its BOUNDING BOX: consecutive rects of
    well-set copy overlap by `width·|sin θ|` (a false finding), and they overlap each other enough to be
    grouped into one line, which leaves a genuinely mis-set block with nothing to compare (a missed one).
    Measured at 13 degrees: the clean probe read as a 148px collision and the broken one read as clean.
    """
    assert not _probe_leading("TiltedTypeCleanProbe"), "well-set tilted copy must be clean"
    assert _probe_leading("TiltedTypeCollisionProbe"), "mis-set tilted copy must be caught"
    src = open(_TEXTSAFE, encoding="utf-8").read()
    # The mutant disables the guard at its root — `selfRotated`, which every path consults. Anchored there
    # rather than on `rotatedUnder`'s signature, which changed once already when the walk was memoised; the
    # anchor going stale is what this harness is built to REFUSE rather than silently pass.
    old = "const selfRotated = (cs: CSSStyleDeclaration): boolean => {\n  const tr = cs.transform;"
    assert old in src, "the rotation guard moved — update this mutant"
    # Announce the mutation: any OTHER run of this gate refuses while the sentinel is there rather than
    # quietly reporting numbers taken from the broken instrument. `_probe_leading` is called through the
    # same `audit()`, so the sentinel is dropped for the two renders that are meant to see the mutant.
    with open(c._MUTATING, "w", encoding="utf-8") as fh:
        fh.write(str(os.getpid()))
    try:
        open(_TEXTSAFE, "w", encoding="utf-8").write(
            src.replace(old, old.replace("{\n  const tr", "{\n  if (1) return false;\n  const tr"), 1))
        blind_clean = _probe_leading("TiltedTypeCleanProbe")
        blind_bad = _probe_leading("TiltedTypeCollisionProbe")
    finally:
        open(_TEXTSAFE, "w", encoding="utf-8").write(src)
        if os.path.exists(c._MUTATING):
            os.remove(c._MUTATING)
    assert blind_clean, "without the guard the clean tilted probe must report a (false) collision"
    assert not blind_bad, "without the guard the mis-set tilted probe must be MISSED"


def test_the_tilted_probes_are_synthetic_and_permanent():
    """A control that needs a production register to stay broken works exactly once. Both tilted probes
    live in Root.tsx beside the original, take no props, and are registered as compositions."""
    root = open(os.path.join(_ROOT, "remotion", "src", "Root.tsx"), encoding="utf-8").read()
    for n in ("TiltedTypeCollisionProbe", "TiltedTypeCleanProbe"):
        assert "export const %s: React.FC = () =>" % n in root, n
        assert "{F('%s', %s, " % (n, n) in root, n
    assert c.CONTROLS_BAD["TiltedTypeCollisionProbe"] == "leading"
    assert c.CONTROLS_CLEAN["TiltedTypeCleanProbe"] == "leading"


# ── "drew nothing": the verdict comes from the DOM, not from an ink ratio ───────────────────────────
def test_only_cjk_copy_is_looked_for_on_screen():
    """Icon names, colour tokens and asset paths are strings a register never prints. Looking for them
    would report every register that takes one as having dropped copy."""
    assert c._string_leaves({"a": "x", "b": ["y", {"c": "z"}], "n": 4}) == ["x", "y", "z"]
    assert bool(c._HAS_CJK.search("文档")) and not c._HAS_CJK.search("doc") and not c._HAS_CJK.search("5.5.0")


@_NEEDS_REMOTION
def test_a_sparse_frame_whose_copy_is_on_screen_is_not_reported_as_unfed():
    """The false positive that put this on a delivered film's report: four `QuadSplit` panels on a
    warm-white palette draw ~3% ink, under the suspicion floor, with every string plainly visible."""
    film = {"heading": "办公的产物，本身就是文件", "hero": None,
            "panels": [{"label": "文档"}, {"label": "表格"}, {"label": "演示 PPT"}, {"label": "数据分析"}]}
    tmp = os.path.join(_ROOT, "remotion", ".cjk_type_test_qs.png")
    try:
        hits = c.audit("QuadSplit", film, 145, tmp, "product")
        assert hits == [], hits
    finally:
        for f in (tmp, tmp + ".props.json"):
            if os.path.exists(f):
                os.remove(f)


@_NEEDS_REMOTION
def test_a_wrong_shaped_fixture_is_still_caught_and_now_names_what_vanished():
    """The case the guard exists for: TermTree declares {name, note, tag} and drawing it from a list of
    bare strings yields empty rows. The verdict must name the strings that never reached the screen."""
    tmp = os.path.join(_ROOT, "remotion", ".cjk_type_test_tt.png")
    try:
        hits = c.audit("TermTree", {"cmd": c._SHORT, "root": c._SHORT, "items": list(c._ITEMS[:3])}, 145, tmp)
        unfed = [h for h in (hits or []) if h["kind"] == "unfed"]
        assert unfed, hits
        assert "never reached the screen" in unfed[0]["text"], unfed[0]["text"]
        assert c._ITEMS[0] in unfed[0]["text"], unfed[0]["text"]
    finally:
        for f in (tmp, tmp + ".props.json"):
            if os.path.exists(f):
                os.remove(f)


# ── the fixture must not invent values for fields that are not copy ─────────────────────────────────
def test_a_named_type_alias_is_resolved_not_filled_with_a_sentence():
    """`QuadSplit` declares `icon?: IconName`. The shaper used to hand that field a Chinese sentence, the
    icon registry threw (as it is written to), and the register reported as a RENDER FAILURE — which the
    controls then counted as a clean known-GOOD. A named type is resolved to a real member of its union."""
    props, _ = c.cjk_props("QuadSplit")
    icons = [p.get("icon") for p in props["panels"]]
    assert icons and all(i and not c._HAS_CJK.search(i) for i in icons), icons
    assert c._named_union_member("IconName", "") == "file"


def test_an_unresolvable_field_is_left_out_rather_than_guessed():
    assert c._synth_field("whatever", "SomeTypeNobodyDeclared") is c._OMIT
    # The CONTRACT is that `b` is left out. Which Chinese string `a` receives is incidental, and pinning it
    # broke the day row fields were made to vary by name (two fields of one row carrying one string cannot
    # be told apart from a collision by the overlap detector) — a test that fails on a correct change is one
    # people learn to edit rather than read.
    row = c._shaped_row({"a": "string", "b": "SomeTypeNobodyDeclared"}, "")
    assert set(row) == {"a"}, "an unresolvable field was guessed instead of omitted: %r" % (row,)
    assert c._HAS_CJK.search(row["a"]), row


def test_a_control_that_did_not_render_is_not_counted_as_clean():
    """A failed render carries no hits, so the known-GOOD side passed on a register that never drew. The
    controls now require every control to have rendered."""
    src = open(os.path.join(_ROOT, "scripts", "cjk_type_qa.py"), encoding="utf-8").read()
    assert "DID NOT RENDER" in src and "and not dead and fed" in src


def test_list_fixture_copy_is_long_enough_to_wrap():
    """The precondition for the whole defect. At six characters a card label never wrapped, so the sweep
    reported CardStack3D clean while the same register broke on a delivered film."""
    assert max(len(x) for x in c._ITEMS) >= 10, c._ITEMS
    assert min(len(x) for x in c._ITEMS) <= 7, "a real list has short entries too"


def test_the_measured_sweep_covers_what_the_static_rule_cannot():
    """The two halves of the same rule: the static test refuses a NEW register written below 1.05, and the
    sweep reports any register whose Chinese actually wrapped below the floor — including at exactly 1.0,
    which the static pattern cannot judge."""
    dom = open(os.path.join(_ROOT, "remotion", "src", "runtime", "textSafe.tsx"), encoding="utf-8").read()
    assert "CJK_MIN_LEADING" in dom and "kind: 'tight'" in dom, \
        "the sweep must measure the floor it shares with the registers, not a second copy of the number"
    assert "hasCJK(text)" in dom, "the report is for CJK copy only — Latin display type keeps its leading"


# ── the orphaned last line ──────────────────────────────────────────────────────────────────────────
@_NEEDS_REMOTION
def test_a_single_character_last_line_is_caught_and_balance_fixes_it():
    """The pair is the whole point: two probes differing in ONE property. Chinese breaks between any two
    glyphs, so a label a unit too wide for its box drops one character onto a line of its own — a delivered
    film's card read 「Craft · 直接开」 over a line holding just 「干」. `text-wrap: balance` is the fix, and
    the twin proves the detector is reading the break rather than the copy."""
    bad = _probe_kind("OrphanLineProbe", "orphan")
    assert bad and bad[0]["other"] == "录", bad
    assert not _probe_kind("BalancedLineProbe", "orphan"), "balanced copy must come back clean"


@_NEEDS_REMOTION
def test_the_orphan_detector_reads_lines_correctly_under_rotation():
    """It has to: the register that exposed the defect fans its cards on a tilt, so an axis-aligned line
    grouping would not have found it at all. The line direction is measured from the copy itself."""
    hits = _probe_kind("CardStack3D", "orphan",
                       {"title": "三种工作模式",
                        "items": ["Craft · 直接开干", "Plan · 确认后再动", "Ask · 不碰文件"]})
    assert not hits, "CardStack3D balances its card labels now: %s" % hits


def _probe_kind(name, kind, props=None):
    tmp = os.path.join(_ROOT, "remotion", ".cjk_type_kind.png")
    try:
        hits = c.audit(name, props or {}, 145, tmp, "product")
        assert hits is not None, "%s failed to render" % name
        return [h for h in hits if h["kind"] == kind]
    finally:
        for f in (tmp, tmp + ".props.json"):
            if os.path.exists(f):
                os.remove(f)


def test_every_synthetic_control_has_a_one_property_twin():
    """A catch is only evidence when its twin, differing in one property, comes back clean."""
    assert set(c.CONTROLS_BAD.values()) == {"leading", "orphan", "tight"}
    assert set(c.CONTROLS_CLEAN.values()) <= set(c.CONTROLS_BAD.values())
    root = open(os.path.join(_ROOT, "remotion", "src", "Root.tsx"), encoding="utf-8").read()
    for n in list(c.CONTROLS_BAD) + list(c.CONTROLS_CLEAN):
        assert "{F('%s', %s, " % (n, n) in root, n
    assert "ORPHAN_COPY" in root, "both orphan probes must set the SAME copy, or they are not a pair"


# ── the leading floor's BOUNDARY, and the two claims about a sparse frame ───────────────────────────
@_NEEDS_REMOTION
def test_copy_set_exactly_at_the_floor_is_not_reported_as_under_it():
    """The failure this pins shipped in the gate itself. `tight` compared the RATIO, and `line-height: 1.06`
    is a used value the browser rounds to whole pixels, so the ratio reads 1.0599… — two registers that pass
    their copy through `leading()` were reported, at a shortfall of 0px and 1px. A finding about missing air
    that names none of it is the kind of false positive that teaches a reader to ignore a gate."""
    assert _probe_kind("TightLeadingProbe", "tight"), "copy at 0.95 must be caught"
    assert not _probe_kind("FlooredLeadingProbe", "tight"), "copy at exactly the floor must be clean"


def test_the_tight_finding_has_a_pixel_floor_not_just_a_ratio():
    dom = open(_TEXTSAFE, encoding="utf-8").read()
    assert "TIGHT_MIN_PX" in dom and "shortPx > TIGHT_MIN_PX" in dom, \
        "the shortfall must be measured in pixels of missing air, with a floor"


def test_a_register_that_dropped_a_little_copy_is_not_called_unreached():
    """Two different claims, and the first version made one for both. A register that drew 9 of the 11
    strings it was given HAS been reached; saying the fixture never reached it is false, and it failed the
    gate for it. Saying nothing is worse — silently dropped copy is worth knowing about."""
    assert 0 < c.UNFED_MISSING_FRAC <= 0.5
    src = open(os.path.join(_ROOT, "scripts", "cjk_type_qa.py"), encoding="utf-8").read()
    assert '"kind": "dropped"' in src and "DREW A SPARSE FRAME" in src
    assert "A report, not a failure" in src


# ── the fixture must not feed prose to a dial, or copy to a colour ──────────────────────────────────
def test_a_numeric_readout_is_fed_a_numeral_not_a_sentence():
    """`VelocitySnap` hands its metric to the shared `Figure` atom, which sets numerals at 0.86 leading —
    correct for digits, and reported as tight Chinese the moment the fixture fed it a sentence. `TermCounter`
    simply drew nothing for a value it could not read as a number. Detected from the register's OWN default,
    because `value` is real copy on some registers and a dial on others."""
    for name, prop in (("VelocitySnap", "metric"), ("TermCounter", "value"), ("EdStat", "value"),
                       ("OdometerRoll", "value")):
        props, _ = c.cjk_props(name)
        assert props.get(prop) == c._READOUT, "%s.%s = %r" % (name, prop, props.get(prop))
    # ...and a field that is real copy keeps its Chinese
    assert c._HAS_CJK.search(c.cjk_props("MagazineSpread")[0]["headline"])


def test_a_colour_field_is_never_fed_copy_at_any_depth():
    """The top-level skip covered `accent`; a ROW's own `tone` sat below it, so `TermBars` was handed a
    Chinese sentence as the colour of every bar."""
    row = c.cjk_props("TermBars")[0]["rows"][0]
    assert "tone" not in row, row
    assert row.get("value") == c._READOUT, "a measured row's value is its readout"
    assert c._HAS_CJK.search(row["label"]), "the row's LABEL is still copy"


def test_the_sweep_records_that_it_must_run_serially():
    """Four concurrent shards reported five registers as render failures that render fine alone, called
    twelve 'drew almost nothing' that draw fine alone, and MISSED findings the serial run then reported."""
    src = open(os.path.join(_ROOT, "scripts", "cjk_type_qa.py"), encoding="utf-8").read()
    assert "RUN IT SERIALLY" in src and "TermBars" in src


def test_a_role_is_matched_on_the_name_not_on_the_whole_name():
    """`_ROLE` matched exactly, so `label` was a label and `underLabel` was not.

    Twenty-seven props across the library carry an obvious role word and fell through to the MED fallback,
    which handed a legend swatch a 26-glyph CAPTION. That is not a harder test, it is the wrong one, and
    `PlanPalimpsest` answered it by growing its legend past the whole content zone and lifting the block
    229px off the top of the frame. A prop whose name ends in `Label` — or begins with it — is a label.
    """
    import cjk_type_qa as q
    label = set(q._LABEL_V)
    long_ = set(q._LONG_V)
    for prop in ("underLabel", "overLabel", "leftLabel", "rightLabel", "metricLabel", "backLabel",
                 "scanLabel", "lockLabel", "scaleLabel", "labelLeft", "labelRight", "headword"):
        got = q._string_for(prop, prop, "", 0)
        assert got in label, "%s was handed %r, which is not label-length copy" % (prop, got)
    for prop in ("underNote", "overNote", "doneNote", "noteLeft"):
        assert q._string_for(prop, prop, "", 0) in long_, "%s should take the note role" % prop
    # ORDER STILL DECIDES. `doneLabel` and `sectionLabel` are listed with the SHORT role and must keep it —
    # a tail match that re-read them as labels would silently lengthen two props this file already placed.
    short = set(q._SHORT_V)
    for prop in ("doneLabel", "sectionLabel"):
        assert q._string_for(prop, prop, "", 0) in short, "%s lost its SHORT role to the tail match" % prop
    # ...and a name with no role word still falls through, rather than everything becoming a label
    assert q._string_for("somethingElse", "somethingElse", "", 0) in set(q._MED_V)


def test_a_fixed_length_tuple_is_not_over_fed():
    """`items?: [string, string, string]` declares THREE slots.

    The fixture fed four, and the fourth was reported as a dropped string on `IsometricAssembly` at every
    aspect the library was swept at — a finding about a register that had done nothing wrong."""
    import cjk_type_qa as q
    assert q._tuple_len("[string, string, string]") == 3
    assert q._tuple_len("[string, string]") == 2
    assert q._tuple_len("string[]") is None, "a plain array is not a fixed-length tuple"
    assert q._tuple_len("[string, number]") is None, "a mixed tuple is not this function's business"
    r = q.cjk_props("IsometricAssembly")
    props = r[0] if isinstance(r, tuple) else r
    assert len(props["items"]) == 3, "fed %d items into a three-slot tuple" % len(props["items"])


def test_an_object_prop_gets_only_the_keys_its_own_type_declares():
    """`_ARRAY_SHAPES` is keyed by PROP NAME, and one name serves registers with different shapes.

    `left` is a `Col {head, body, hero}` on EdCompare and `{label, points}` on VersusSplit, so the shared
    entry carries both. Handing EdCompare the `points` it cannot read produced 2 of 11 dropped strings at
    four aspects."""
    import cjk_type_qa as q
    ed = q.cjk_props("EdCompare")
    ed = (ed[0] if isinstance(ed, tuple) else ed)["left"]
    vs = q.cjk_props("VersusSplit")
    vs = (vs[0] if isinstance(vs, tuple) else vs)["left"]
    assert set(ed) <= {"head", "body", "hero"}, "EdCompare's Col got keys it does not declare: %r" % set(ed)
    assert "points" not in ed and "label" not in ed
    # ...and the OTHER register keeps what IT declares — the filter is per-register, not a table edit
    assert "points" in vs and "label" in vs, "VersusSplit lost the keys its own type declares: %r" % set(vs)


def test_it_resolves_a_named_object_alias_not_just_an_inline_one():
    """`Col` is declared beside the register, so the keys have to be looked up, not guessed."""
    import cjk_type_qa as q
    src = open(os.path.join(_ROOT, "remotion", "src", "shots", "EdCompare.tsx"),
               encoding="utf-8").read()
    assert q._declared_keys("Col", src) == {"head", "body", "hero"}
    assert q._declared_keys("{a?: string; b?: string}", src) == {"a", "b"}
    assert q._declared_keys("string", src) is None


# ── THREE MORE WAYS TO BE INVISIBLE, all found by asking which registers this gate feeds NOTHING ────
#
# The JSDoc blindness (pinned above) was not the only one. Reading the whole library's signatures turned up
# two further shapes the declaration reader refused, and one shape the FIXTURE generator refused:
#
#   React.FC<Props>       AcceptanceStamp declares its four props in a named alias above the component.
#   React.FC<{...} >      MRIPipeline has one space before the closing angle.
#   type X = A | B        TechnicalPlate's `Stroke`, SplitFlap's `FlapRow`, CardStack3D's `StackItem`.
#
# Each produced the same silence: the sweep rendered the register's own ENGLISH demo defaults and reported
# zero findings, which reads identically to "this register is fine in Chinese".
# (the library-wide version of this check — all four declaration readers, compared against each other —
# lives in tests/test_declaration_readers.py, which is where the CLASS is owned. What follows is specific to
# this gate's own fixture generator.)


@pytest.mark.parametrize("register,prop", [
    ("AcceptanceStamp", "conditions"),   # React.FC<Props> — a named alias
    ("MRIPipeline", "label"),            # React.FC<{...} > — a space before the angle
])
def test_a_props_declaration_is_read_however_it_is_spelled(register, prop):
    sig = c.prop_signature(register)[0]
    assert prop in sig, "%s declares %s and the reader cannot see it: %r" % (register, prop, sig)
    assert prop in c.cjk_props(register)[0]


def test_a_union_alias_is_shaped_from_its_own_type_not_from_the_prop_name_table():
    """`FlapRow = string | {text: string; tone?: ...}`. Unreadable, the prop fell through to `_ARRAY_SHAPES`,
    where `rows` means a two-column TABLE — and SplitFlap's `String(r?.text ?? '')` turns an array row into
    the empty string. Measured on the real frame: 0.05% ink against 8.30% when fed rows it can read. The gate
    reported it clean at every aspect for as long as that fixture existed, which is the same lie as measuring
    an empty plate."""
    rows = c.cjk_props("SplitFlap")[0]["rows"]
    assert isinstance(rows, list) and rows, rows
    for r in rows:
        assert isinstance(r, (str, dict)), "a FlapRow is a string or an object, never %r" % (type(r),)
        if isinstance(r, dict):
            assert c._HAS_CJK.search(str(r.get("text", ""))), "a flap row carries no Chinese: %r" % (r,)


def test_geometry_is_kept_out_of_the_copy_gate_without_being_called_untestable():
    """`TechnicalPlate.strokes` is a discriminated union of coordinates — there is no Chinese to put in a
    radius. Fed a fixture it renders nonsense; filed UNTESTABLE it claims the register has copy nobody can
    reach, while every string it draws is fed and measured. It keeps its own default and says nothing.

    The distinction must be EARNED, not assumed: a type the reader cannot parse is still untestable.

    ...AND GEOMETRY THAT TRAVELS WITH COPY IS FED, NOT KEPT. TechnicalPlate now refuses `parts` without
    `strokes` (a film's part names used to land on the demo bicycle), so the sweep feeds the fixed object in
    `_COUPLED_GEOMETRY` — coordinates, still no Chinese in a radius, and still never reported untestable."""
    props, untestable = c.cjk_props("TechnicalPlate")
    assert "strokes" not in untestable, untestable
    assert props.get("strokes") == c._COUPLED_GEOMETRY["strokes"], props.get("strokes")
    assert {"kicker", "object", "parts"} <= set(props), props
    src = open(os.path.join(_ROOT, "remotion", "src", "shots", "TechnicalPlate.tsx"), encoding="utf-8").read()
    assert c._type_fields("Stroke", src) is not None, "the union alias no longer resolves"
    assert not c._carries_copy(*c._type_fields("Stroke", src)), "Stroke gained a string field"
    assert c._type_fields("NoSuchAliasAnywhere", src) is None, (
        "an unreadable type resolved to something — geometry would then swallow every shape this "
        "reader fails on, which is exactly where the defect hides")


def test_a_lone_object_prop_is_shaped_the_way_an_object_ARRAY_already_was():
    """`MapPlate.channel` is one object carrying a label and two coordinate pairs. Only the array side had a
    reader, so it was filed untestable although its label is exactly the copy this gate sets in Chinese."""
    ch = c.cjk_props("MapPlate")[0]["channel"]
    assert c._HAS_CJK.search(ch["label"]), ch
    assert ch["from"] != ch["to"], (
        "both ends of the channel are the same point — one `i` reaches every field of a row, so two "
        "coordinate pairs came back identical and the register drew a line of zero length: %r" % (ch,))
    assert 0 < ch["width"] < 0.2, (
        "`width` is a plate FRACTION (the register's own default is 0.02) and was handed a magnitude: %r"
        % (ch["width"],))


def test_a_string_literal_union_is_fed_one_of_its_own_literals_and_never_varies_by_offset():
    """A union of quoted literals is a SWITCH, not copy. It gets a declared value — and the same one at every
    `offset`, because `prop_reach` renders two sets to ask how much of the picture the film's WORDS author,
    and a switch that flipped between them would answer with a colour change."""
    a = c.cjk_props("NeuralField", offset=0)[0]
    b = c.cjk_props("NeuralField", offset=3)[0]
    assert a["tone"] in ("accent", "accent2"), a["tone"]
    assert a["tone"] == b["tone"], "the switch moved between two prop sets that differ only in their words"
    assert a["input"] != b["input"], "the two sets are not actually different copy"


def test_the_curated_table_wins_when_it_FITS_the_register_and_loses_when_it_does_not():
    """"Read the type, never the prop name" was the right fix for the wrong scope.

    The type route exists because the name table describes a DIFFERENT register that shares a prop name:
    `rows` there means a two-column table, and `SplitFlap`'s rows are strings, so it was swept on a blank
    board. But a curated entry knows things a type cannot — `sources?: {t: string; d: string}[]` says nothing
    about `t` being a four-glyph chip — and making the type win ALWAYS filled both fields with 26-glyph
    sentences, which orphaned a glyph off an `AnswerStream` source chip.

    So the arbiter is compatibility with the register's OWN declared keys, not precedence."""
    src = open(os.path.join(_ROOT, "remotion", "src", "shots", "AnswerStream.tsx"), encoding="utf-8").read()
    keys = c._declared_keys("{t: string; d: string}", src)
    assert keys == {"t", "d"}
    got = c.cjk_props("AnswerStream")[0]["sources"]
    assert got == c._ARRAY_SHAPES["sources"], (
        "the curated chips lost to the type route, which cannot know a source chip is short: %r" % (got,))

    rows = c.cjk_props("SplitFlap")[0]["rows"]
    assert rows != c._ARRAY_SHAPES["rows"], (
        "the table won on a register whose type it does not fit — this is the blank board again: %r" % (rows,))
    assert all(isinstance(r, (str, dict)) for r in rows), rows


def test_two_fields_of_one_row_never_carry_the_same_string():
    """One `i` reached every field of a row, so `{t, d}` came back with one sentence twice. The overlap
    detector matches elements by their text: a row whose two labels are one string is indistinguishable
    from a real collision, and the gate cannot tell a dropped string from a duplicated one."""
    bad = {}
    import glob
    for f in glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx")):
        name = os.path.basename(f)[:-4]
        for prop, val in c.cjk_props(name)[0].items():
            for row in (val if isinstance(val, list) else [val]):
                if not isinstance(row, dict):
                    continue
                words = [v for v in row.values() if isinstance(v, str) and c._HAS_CJK.search(v)]
                if len(words) != len(set(words)):
                    bad["%s.%s" % (name, prop)] = row
    assert not bad, "rows carrying one string in two fields: %r" % (bad,)


def test_the_probe_fraction_is_named_once_so_the_alternate_probes_cannot_drift():
    src = open(c.__file__, encoding="utf-8").read()
    assert "PROBE_FRAC = 0.88" in src
    assert "* 0.88)" not in src, "the probe fraction is written twice — two copies of a number always drift"
    fn = src.split("def audit(", 1)[1].split("\ndef ", 1)[0]
    assert "PROBE_FRAC" in fn, (
        "the alternate probes no longer derive from the same fraction the close is taken at")


def test_a_sequential_register_is_probed_more_than_once_before_it_is_called_unfed():
    """`VoiceSignal` is a timeline: it shows ONE phase at a time, because that is what a timeline IS. Judged
    on the close alone it 'dropped 2 of 3' and was reported as a register the fixture never reached — a
    claim that is false about a frame carrying a settled waveform and its final label at 1.90% ink, MORE
    than the register draws on its own defaults.

    The previous repair varied the phases' timestamps, which changed WHICH label shows and not that only one
    can, so the finding survived its own fix wearing a different name. No register is exempted here: the
    union across probes is measured, and a string that appears at NO probe is still reported — which is the
    WordTunnel case this branch was built for."""
    src = open(c.__file__, encoding="utf-8").read()
    fn = src.split("def audit(", 1)[1].split("\ndef ", 1)[0]
    assert "for frac_t in (0.45, 0.65)" in fn, "the alternate probes are gone"
    assert "missing = [x for x in missing if x in seen_there]" in fn, (
        "the probes no longer INTERSECT — a string found at any frame was drawn, and keeping the close's "
        "answer instead would make the extra renders decorative")
    after = fn.split("_fed_missing(shot, props, frame", 1)[1]
    assert after.index("if missing:") < after.index("for frac_t in"), (
        "the extra renders are no longer gated on the close having found something missing, so every "
        "low-ink register now pays for three renders instead of one")


def test_a_films_own_pictures_are_not_replaced_by_the_library_fixture(monkeypatch):
    """StateSheet on a real film carried seventeen real sprites; the sweep overwrote them with the library's
    stand-in picture, which does not exist under the film's asset root, and reported FAILED TO RENDER on a
    film that rendered fine. A film's props win; the fixture only fills a plate the film left empty."""
    seen = {}
    monkeypatch.setattr(c, "evidence_props", lambda: {"StateSheet": {"cells": [{"src": "_energy_fixture.png"}]}})
    monkeypatch.setattr(c, "audit", lambda n, props, *a, **k: seen.setdefault(n, props) and [])
    film = {"cells": [{"src": "assets/pikachu/idle-wave.svg", "label": "待机"}]}
    c.sweep(["StateSheet"], film_props={"StateSheet": film})
    assert seen["StateSheet"]["cells"] == film["cells"], seen
    seen.clear()
    c.sweep(["StateSheet"])                        # the library sweep still gets its fixture
    assert seen["StateSheet"]["cells"][0]["src"] == "_energy_fixture.png"


def test_film_mode_serves_the_films_own_asset_folder(monkeypatch, tmp_path):
    """render_remotion serves `--public-dir=<out_dir>`; this gate rendered film beats against the library's
    folder, so every register drawing a film's own image failed here and nowhere else."""
    board = {"meta": {"aspect": "16:9"}, "slides": [{"index": 1, "shot": "CinematicTitle", "shot_props": {}}]}
    import json as _json
    _json.dump(board, open(tmp_path / "storyboard.json", "w"))
    monkeypatch.setattr(c, "sweep", lambda *a, **k: {})
    old = c.PUBLIC_DIR
    try:
        c.main([str(tmp_path)])
        assert c.PUBLIC_DIR == os.path.abspath(str(tmp_path)), c.PUBLIC_DIR
    finally:
        c.PUBLIC_DIR = old


# ── COVERAGE: what this gate did NOT measure ───────────────────────────────────────────────────────
# The headline was `N register(s) rendered with Chinese copy` — a count of what rendered, with no
# denominator and no check that any Chinese went in. Three items used to leave the measurement while the
# run still read as a pass, and a real 170-register sweep produced two of them:
#   PortRail    refused the gate's OWN fixture (fed `items` AND `groups`, two spellings of one rail)
#   StateSheet  a browser that died under a loaded sweep; it rendered clean on its own seconds later
# Neither name was a register defect, both printed as a bare name under "FAILED TO RENDER", and the run
# exited 0 on them.

def test_the_headline_states_coverage_with_a_derived_denominator(monkeypatch, capsys):
    """`measured N of M`, M read from the shots directory. A constant cannot satisfy this."""
    import glob as _g
    on_disk = len(_g.glob(os.path.join(c._SHOTS, "*.tsx")))
    monkeypatch.setattr(c, "sweep", lambda names, *a, **k: {
        n: {"hits": [], "untestable": [], "failed": False, "why": None, "cjk_fed": 3} for n in names})
    rc = c.main(["--library"])
    head = [l for l in capsys.readouterr().out.splitlines() if l.startswith("[cjk_type] measured")][0]
    assert "measured %d of %d registers in shots/" % (on_disk, on_disk) in head, head
    assert "0 not measured" in head, head
    assert rc == 0


def test_a_register_that_refused_to_render_is_named_with_its_own_message(monkeypatch, capsys):
    """"FAILED TO RENDER: PortRail" is not a reason. The register's own words are."""
    real = "PortRail seats 1-6 modules on its rail (got 9 across the groups)."
    monkeypatch.setattr(c, "sweep", lambda names, *a, **k: {
        names[0]: {"hits": [], "untestable": [], "failed": True, "why": real, "cjk_fed": 4},
        names[1]: {"hits": [], "untestable": [], "failed": False, "why": None, "cjk_fed": 4}})
    rc = c.main(["--only=PortRail,CinematicTitle"])
    out = capsys.readouterr().out
    assert "measured 1 of 2" in out and "1 not measured" in out, out
    assert "NOT MEASURED" in out and "refused to render" in out and real in out, out
    assert rc == 2, "a register nothing was measured on exited %r" % rc


def test_a_register_fed_no_chinese_is_not_counted_as_rendered_with_chinese(monkeypatch, capsys):
    """A register renders perfectly on its own ENGLISH demo defaults. `audit()` only asks which fed
    strings reached the screen when the frame already looks empty, so a busy English frame short-circuits
    to clean — and the headline called it 'rendered with Chinese copy'."""
    monkeypatch.setattr(c, "sweep", lambda names, *a, **k: {
        names[0]: {"hits": [], "untestable": [], "failed": False, "why": None, "cjk_fed": 0},
        names[1]: {"hits": [], "untestable": [], "failed": False, "why": None, "cjk_fed": 7}})
    rc = c.main(["--only=SplitFlap,CinematicTitle"])
    out = capsys.readouterr().out
    assert "measured 1 of 2" in out, out
    assert "no Chinese copy could be shaped" in out and "SplitFlap" in out, out
    assert rc == 2


def test_only_refuses_a_name_that_is_not_a_register(capsys):
    """An unknown name was swept anyway: prop_signature returns ({}, '') for a file it cannot open, the
    render then died on an unknown composition, and it was reported as a register that FAILED TO RENDER."""
    rc = c.main(["--only=NoSuchRegister,CinematicTitle"])
    out = capsys.readouterr().out
    assert "not registers in shots/" in out and "NoSuchRegister" in out, out
    assert "CinematicTitle" not in out, "a real name must not be blamed alongside the bad one"
    assert rc == 2


def test_the_film_universe_is_beats_and_says_so(monkeypatch, capsys, tmp_path):
    """A film sweeps DISTINCT REGISTERS, not beats — two beats on one register are one render. Saying
    'measured 1' of a three-beat film reads as one beat of three."""
    import json as _json
    _json.dump({"meta": {"aspect": "16:9"}, "slides": [
        {"index": 1, "shot": "CinematicTitle", "shot_props": {}},
        {"index": 2, "shot": "CinematicTitle", "shot_props": {}},
        {"index": 3, "shot_props": {}},
    ]}, open(tmp_path / "storyboard.json", "w"))
    monkeypatch.setattr(c, "sweep", lambda names, *a, **k: {
        n: {"hits": [], "untestable": [], "failed": False, "why": None, "cjk_fed": 2} for n in names})
    old = c.PUBLIC_DIR
    try:
        rc = c.main([str(tmp_path)])
    finally:
        c.PUBLIC_DIR = old
    out = capsys.readouterr().out
    assert "measured 1 of 1 distinct registers across 3 beat(s)" in out, out
    assert "selects no register" in out, "the still beat was dropped in silence"
    assert rc == 2


def test_the_fixture_never_feeds_two_spellings_of_one_slot():
    """`// @supersedes groups: items` says `groups` REPLACES `items`. The shaper walks the signature prop
    by prop and filled both, so PortRail got 4 modules AND 3 groups of 3, refused the 9 against its own
    1-6 guard, and was recorded as FAILED TO RENDER on every sweep. The relation is parsed from the
    registers' own declarations, never listed here."""
    import demo_copy_qa as _dc
    rel = _dc.supersedes()
    assert rel, "no register declares @supersedes any more — this test is measuring nothing"
    for name, providers in rel.items():
        props, _ = c.cjk_props(name)
        for provider, supplied in providers.items():
            assert provider not in props, (
                "%s was fed both %r and what it supersedes (%s)" % (name, provider, ", ".join(supplied)))
            assert any(p in props for p in supplied), (
                "%s was fed neither spelling of the slot — it would draw nothing" % name)


def test_a_failure_reason_is_the_registers_words_not_the_node_stack():
    """The ink gate printed the last line of the failure, which is always
    `at process.processTicksAndRejections (node:internal/…)` — eight registers carried that non-reason."""
    blob = ("\n Error  PortRail seats 1-6 modules on its rail (got 9 across the groups).\n"
            "    at PortRail (file:///x/PortRail.tsx:250:11)\n"
            "    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)\n")
    got = c._why_it_refused(blob)
    assert got.startswith("PortRail seats 1-6"), got
    assert "processTicksAndRejections" not in got
    assert "no output at all" in c._why_it_refused("")
    # and a blob that is ALL stack must say so, not print a stack line as though it were the reason
    only_stack = c._why_it_refused("    at process.processTicksAndRejections (node:internal/x:9:5)\n")
    assert "no message" in only_stack, only_stack


def test_a_flaky_render_is_retried_before_it_is_called_unmeasured():
    """StateSheet came back FAILED TO RENDER in a loaded 170-register sweep and rendered clean alone
    seconds later. text_safe_qa.audit_shot already retries for exactly this."""
    import inspect
    src = inspect.getsource(c.audit)
    assert "for _attempt in (1, 2):" in src, "a single failed render still ends the measurement"


def test_sweep_carries_the_refusal_reason_out_of_the_render(monkeypatch, tmp_path):
    """The wiring, not just the parser: `audit` must APPEND the reason and `sweep` must record it. The
    reason used to be computed nowhere at all — `audit` returned None and `sweep` stored `failed: True`."""
    class _R:
        returncode = 1
        stdout = ""
        stderr = (" Error  Widget seats 1-6 modules on its rail (got 9 across the groups).\n"
                  "    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)\n")
    calls = []

    def _fake_run(cmd, **kw):
        calls.append(cmd)
        return _R()
    monkeypatch.setattr(c.subprocess, "run", _fake_run)
    monkeypatch.setattr(c, "durations", lambda: {"Widget": 150})
    monkeypatch.setattr(c, "evidence_props", lambda: {})
    monkeypatch.setattr(c, "cjk_props", lambda n, offset=0: ({"title": "交付可验收的成果"}, []))
    monkeypatch.setattr(c, "_ink_fraction", lambda p: 1.0)
    res = c.sweep(["Widget"])
    assert res["Widget"]["failed"] is True
    assert res["Widget"]["why"].startswith("Widget seats 1-6"), res["Widget"]["why"]
    assert "processTicks" not in (res["Widget"]["why"] or "")
    assert res["Widget"]["cjk_fed"] == 1, "the CJK leaves fed in are not counted"
    assert len(calls) == 2, "a failed render was not retried (%d attempt(s))" % len(calls)


# ── the second prop set ───────────────────────────────────────────────────────────────────────────────
def test_a_second_prop_set_is_different_words_and_never_a_different_shape():
    """`cjk_props(offset=)` exists so one register can be rendered twice with the same SHAPE and different
    WORDS — that is the whole basis of `prop_reach`'s measurement. Rotating a list of rows rotated the
    numbers in them too, and in a list whose order IS its meaning that is not a new topic, it is an invalid
    board: `VoiceSignal` refuses phases out of time order (its own header says so), threw, and was the one
    register of 170 that `prop_reach` could not measure — a fixture bug wearing a register's name.
    """
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import cjk_type_qa as c
    import prop_reach as pr

    a, _ = c.cjk_props("VoiceSignal")
    b, _ = c.cjk_props("VoiceSignal", offset=pr.OFFSET)
    at_a = [r["at"] for r in a["phases"]]
    at_b = [r["at"] for r in b["phases"]]
    assert at_b == sorted(at_b), "the second prop set put the phases out of time order: %r" % (at_b,)
    assert at_a == at_b, "the ordered column moved, which changes the shape rather than the words"
    assert [r["label"] for r in a["phases"]] != [r["label"] for r in b["phases"]], \
        "the words did not change, so the two sets are the same board"


def test_every_register_really_gets_two_different_prop_sets():
    """A no-op is not a rotation. `off % n` is zero whenever the length divides the offset, and the offset
    this library uses is 2 — so every TWO-element list came back unrotated. `ChatThread`'s two messages are
    the whole content of that register, so its second prop set was its first one and `prop_reach` rendered
    the identical frame twice and measured its reach as 0.000."""
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import cjk_type_qa as c
    import prop_reach as pr

    shots = os.path.join(os.path.dirname(__file__), "..", "remotion", "src", "shots")
    same, seen = [], 0
    for name in sorted(f[:-4] for f in os.listdir(shots) if f.endswith(".tsx")):
        try:
            a, _ = c.cjk_props(name)
            b, _ = c.cjk_props(name, offset=pr.OFFSET)
        except Exception:                      # a register this fixture cannot shape is a different finding
            continue
        if not a:
            continue
        seen += 1
        if pr.prop_diff(a, b) == 0.0:
            same.append(name)
    assert seen > 100, "only %d registers were shaped, so this proves nothing" % seen
    assert not same, "these registers are measured against an identical second prop set: %r" % same


def test_a_required_index_is_fed_because_the_register_says_it_is_one():
    """A register that REFUSES without an index was fed one from a hardcoded list of two prop names.

    Under the content contract a register no longer picks which of the film's items to point at — it
    refuses to render without the film's choice. `focal` and `target` were named in `cjk_type_qa` the day
    they were written, and the next such prop was not: `HeldInstant.held` made the register refuse at all
    five aspects, and the sweep reported a COVERAGE HOLE rather than a finding. A register no gate can feed
    is a register nobody checks, and it fails in the direction that looks like nothing happened — the same
    shape `evidence_props` fixed by parsing `requireEvidence` call sites instead of listing registers.

    The two signals are the ones a register already carries: its refusal names the prop it wants, and its
    documentation says the prop is an index. Optional SELECTORS stay unset, because their neutral state is
    what a film that omits them gets.
    """
    import glob
    fed = {}
    for f in sorted(glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx"))):
        n = os.path.basename(f)[:-4]
        # NOT a bare `except Exception`: the first draft of this test called the module by the wrong
        # alias, the NameError was swallowed here, and the assertion below reported "the legacy pair is
        # not fed" about a loop that had never run. A guard that hides the reason a check did nothing
        # reports the wrong defect with total confidence.
        try:
            props, _ = c.cjk_props(n, 0)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        got = {k: v for k, v in props.items()
               if isinstance(v, (int, float)) and not isinstance(v, bool)}
        if got:
            fed[n] = got

    # THE PROPERTY, over the whole library — not three names. The first draft of this test asserted
    # FocalIsolation, GlowPick and HeldInstant by name, and a refusal written inside a TEMPLATE LITERAL
    # (where a backtick must be escaped) went unmatched: `CrashZoom` stopped being fed, its row went from
    # measured to "refused to render", and the unit test stayed green because CrashZoom was not one of the
    # three. A test that names the cases it knows about cannot catch the case it does not.
    refusing = {}
    for f in sorted(glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx"))):
        n = os.path.basename(f)[:-4]
        src = open(f, encoding="utf-8").read()
        sig, _ = c.prop_signature(n)
        for m in re.finditer(r"pass\s+\\?`([A-Za-z][A-Za-z0-9_]*)\\?`", src):
            prop = m.group(1)
            if (sig.get(prop) or "").split("|")[0].strip().startswith("number"):
                refusing.setdefault(n, set()).add(prop)
    assert refusing, "no register refuses without a numeric index — this test is measuring nothing"
    missing = {n: sorted(ps) for n, ps in refusing.items()
               if not ps <= set(fed.get(n, {}))}
    assert not missing, (
        "these registers REFUSE to render without a numeric index and the gate does not feed them one, so "
        "it cannot measure them at all: %r (fed: %r)" % (missing, fed))

    # ...AND NOT EVERY NUMBER. An optional selector left unset is the state a film that omits it gets.
    for n, got in fed.items():
        for prop in got:
            src = open(os.path.join(_ROOT, "remotion", "src", "shots", n + ".tsx"), encoding="utf-8").read()
            assert re.search(r"pass `%s`" % re.escape(prop), src) or re.search(
                r"\bindex(es)?\b|\bwhich (one|of)\b", src, re.I), (
                "%s.%s was fed a number without the register asking for one" % (n, prop))


def test_a_flag_the_register_refuses_without_is_set_on_something():
    """A register that throws unless one item is flagged is UNMEASURABLE if the fixture flags none.

    `NearTheLine` refuses unless a case is marked `near`, and `PulledThread` unless a thread `moves`.
    Both refusals are deliberate and both are the register's best property: with nothing marked, the
    frame argues the OPPOSITE of its beat — a clean separation, a change that came away clean — and it
    does so convincingly, past every gate in this repo. But a boolean fixture that answers `false`
    everywhere turns that good refusal into a COVERAGE HOLE: the sweep reports "refused to render" at
    five aspects and says nothing about the register at all.

    The signal is the one the numeric-index rule already reads — the refusal names the prop it wants —
    so this is the same structural fix, not a second list of names. Exactly ONE item is marked, because
    a fixture that flags every row never renders the unflagged branch, which on these registers is half
    the picture.
    """
    import glob
    for f in sorted(glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx"))):
        n = os.path.basename(f)[:-4]
        src = open(f, encoding="utf-8").read()
        # the registers this is about: ones whose refusal names a boolean prop
        sig, _ = c.prop_signature(n)
        wanted = set()
        for m in re.finditer(r"(?:pass|marked|needs at least one[^.]{0,40}?)\s*\\?`([A-Za-z][A-Za-z0-9_]*)\\?`",
                             src):
            wanted.add(m.group(1))
        if not wanted:
            continue
        try:
            props, _ = c.cjk_props(n, 0)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        for prop in wanted:
            rows = [v for v in props.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
            flagged = [r for r in rows if any(isinstance(it.get(prop), bool) for it in r)]
            for r in flagged:
                vals = [it.get(prop) for it in r if isinstance(it.get(prop), bool)]
                assert any(vals), (
                    "%s refuses without `%s` and the fixture set it nowhere, so the gate cannot render it "
                    "at all: %r" % (n, prop, vals))
                assert not all(vals), (
                    "%s.%s is set on EVERY row, so the unflagged branch — half of what the register draws "
                    "— is never rendered: %r" % (n, prop, vals))


def test_a_relation_between_two_of_the_films_numbers_is_taken_from_the_register_s_own_demo():
    """A generic fixture can supply a TYPE. It cannot supply a RELATION between two of the film's numbers.

    `AverageHides` refuses a tail under 1.5x its typical value — deliberately: that close, the quoted
    number IS a fair summary, and the frame would manufacture an alarm the beat never made. Two
    independently synthesised numbers came out EQUAL, the register threw, and the sweep reported a
    coverage hole at all five aspects — the third time in this session that a good refusal turned into a
    register no gate could measure.

    Weakening the refusal to please the instrument is the wrong direction, and so is a solver that
    invents numbers satisfying it: that is the instrument making the film's claim. The register already
    ships a valid instance — its demo — so the numbers come from there, parsed from the declaration the
    way `evidence_props` parses `requireEvidence` call sites. The Chinese still goes on every string,
    which is the only thing this gate actually asks about; numbers are not copy.
    """
    src = open(os.path.join(_ROOT, "remotion", "src", "shots", "AverageHides.tsx"), encoding="utf-8").read()
    assert c._declared_numbers("typical", src) == {"value": 1}, c._declared_numbers("typical", src)
    assert c._declared_numbers("tail", src) == {"value": 9}, c._declared_numbers("tail", src)

    props, _ = c.cjk_props("AverageHides", 0)
    tv, xv = props["typical"]["value"], props["tail"]["value"]
    assert xv / tv >= 1.5, (
        "the fixture no longer satisfies the register's own refusal, so it cannot be rendered at all: "
        "typical=%r tail=%r" % (tv, xv))
    # ...and the STRINGS are still Chinese, which is what the gate is for
    assert any("一" <= ch <= "鿿" for ch in str(props["typical"]["label"])), props["typical"]

    # the binding form matters: this register defaults to an IDENTIFIER (`typical = DEMO_TYPICAL`), not a
    # rename (`typical: TYPICAL`), and reading only the rename form is what made the first fix a no-op
    assert re.search(r"typical\s*=\s*DEMO_TYPICAL", src), (
        "this test pins the identifier-default binding form; the register no longer uses it")


def test_a_curated_row_that_omits_a_field_is_saying_not_this_one():
    """A selector set on every row renders a frame no film produces.

    `_ARRAY_SHAPES['layers']` marks exactly ONE layer `find: true` — a singleton, which is what
    `StrataColumn` draws and what its own demo supplies. Two things were overriding that. The boolean
    synthesiser returned a flat `True` for `find`/`hero`/`done`/`ok`, so every layer was the one you came
    for and every item was a hero; and the curated table was merged as a UNION, so even after that was
    fixed the synthesiser refilled `find` on the rows the table had deliberately left it off.

    Absence in a curated row is a statement, not a hole: the table says "not this one". A field the table
    mentions anywhere therefore belongs to the table, including on the rows it omits — and the unmarked
    branch, which is half of what these registers draw, finally renders.
    """
    import glob
    props, _ = c.cjk_props("StrataColumn", 0)
    marked = [bool(x.get("find")) for x in props["layers"]]
    assert sum(marked) == 1, (
        "`find` marks the layer, singular — the fixture set it on %d of %d: %r"
        % (sum(marked), len(marked), marked))

    props, _ = c.cjk_props("PositioningMatrix", 0)
    heroes = [bool(x.get("hero")) for x in props["items"]]
    assert sum(heroes) == 1, "`hero` is the one the tint follows, set on %d: %r" % (sum(heroes), heroes)

    # ...and a curated RUN is still a run — GrantedTree brackets a contiguous branch on purpose
    props, _ = c.cjk_props("GrantedTree", 0)
    granted = [bool(x.get("granted")) for x in props["nodes"]]
    assert 0 < sum(granted) < len(granted), (
        "GrantedTree's authorised branch must be some-but-not-all: %r" % granted)

    # the property, library-wide: no boolean selector is true on EVERY row of any register
    for f in sorted(glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx"))):
        n = os.path.basename(f)[:-4]
        try:
            props, _ = c.cjk_props(n, 0)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        for k, v in props.items():
            if not (isinstance(v, list) and len(v) > 1 and all(isinstance(x, dict) for x in v)):
                continue
            for field in ("find", "hero", "done", "ok"):
                vals = [x.get(field) for x in v if field in x]
                assert not (vals and all(bool(x) for x in vals) and len(vals) == len(v)), (
                    "%s.%s[].%s is set on every row, so the unmarked branch never renders" % (n, k, field))


def test_the_rotation_flag_on_an_overlap_is_read_by_something():
    """`textSafe` tags an overlap pair involving 2D-rotated type, and nothing read the tag.

    The cross-element overlap pass intersects axis-aligned BOXES. A tilted element's box is larger than
    its glyphs and grows on the side it slopes toward, so a pair involving one overlaps more on paper
    than the ink does — which is why the renderer sets `rot: true` and its own comment says the flag
    "says which numbers to discount". Grepped across `scripts/` and `tests/`, nothing discounted
    anything: the advice was written and never delivered, and a flag with no reader is not a mitigation.
    It cost a real detour — a 4:3 pair was rendered and inspected by hand that the tag would have
    qualified on sight.

    This pins the READER, not the wording. The separating-axis test that would remove the false pair
    instead of labelling it is still open (open-work B11).
    """
    src = open(os.path.join(_ROOT, "scripts", "cjk_type_qa.py"), encoding="utf-8").read()
    assert re.search(r'\.get\(\s*["\']rot["\']\s*\)|\["rot"\]', src), (
        "nothing in cjk_type_qa reads the `rot` flag; the renderer sets it to say which overlap numbers "
        "to discount, and that advice is going nowhere")

    # ...and the renderer still SETS it, or the reader above is reading a field that no longer exists
    ts = open(os.path.join(_ROOT, "remotion", "src", "runtime", "textSafe.tsx"), encoding="utf-8").read()
    assert re.search(r"rot\s*\?\s*\{\s*rot:\s*true\s*\}|rot:\s*true", ts), (
        "textSafe no longer tags rotated overlaps, so the reader in cjk_type_qa is dead code")


def test_a_top_level_switch_is_fed_its_value_not_a_sentence():
    """DeviceDemo types `device?: DeviceKind` (a runtime alias of string literals) and `camera?: 'still'` (one
    literal). The top level knew only unions of two or more literals, so both were filed untestable and the
    library gate reported the device registers as unfeedable in Chinese."""
    props, holes = c.cjk_props("DeviceDemo")
    assert not holes, holes
    assert (props["device"], props["look"], props["placement"], props["camera"]) == ("phone", "flat", "center", "still")
    assert c._literal_alias_member("DeviceKind", "") == "phone"
    assert c._literal_alias_member("Step", "") is None          # an object alias is not a switch



def test_an_open_map_prop_is_not_fed_another_registers_copy(tmp_path, monkeypatch):
    """`shared?: Record<string, unknown>` declares no field: it is props a register hands on to the objects it holds.
    The fixture's name-keyed table has a `shared` entry ({label, a, b, note}) that belongs to another register; fed
    into an open map, nothing draws those strings, they count as copy that never reached the screen, and a sparse
    aspect is reported as a frame the fixture never reached. An open map is left to the register's own default."""
    (tmp_path / "Mirror.tsx").write_text("""import React from 'react';
export const DURATION = 150;
export const Mirror: React.FC<{
  shared?: Record<string, unknown>;   // merged into both objects' props
  title?: string;                     // the claim
}> = ({shared = {}, title = ''}) => null;
""", encoding="utf-8")
    monkeypatch.setattr(c, "_SHOTS", str(tmp_path))
    assert "shared" in c._ARRAY_SHAPES, "the premise: the shared table has an entry under this prop's name"
    props, untestable = c.cjk_props("Mirror")
    assert "shared" not in props and "shared" not in untestable, (props, untestable)
    assert "title" in props, props
