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
    assert c._shaped_row({"a": "string", "b": "SomeTypeNobodyDeclared"}, "") == {"a": c._string_for("a")}


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

    The distinction must be EARNED, not assumed: a type the reader cannot parse is still untestable."""
    props, untestable = c.cjk_props("TechnicalPlate")
    assert "strokes" not in props and "strokes" not in untestable, (props.get("strokes"), untestable)
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
