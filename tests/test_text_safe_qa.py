"""The text-safe audit, proved to FIRE and proved to stay quiet — on real renders.

A gate that reports nothing is indistinguishable from a gate that cannot report. This one currently finds
zero violations across all 148 registers and all 30 beats of the reference film, which is either a clean
library or a broken instrument, and only a positive control tells them apart. So the first test below drives
a real register into a real overflow and requires the finding.

The other half matters just as much: the whole point of the redesign is that a DELIBERATE frame-break is not
a finding. A travelling world and a full-bleed field must come back clean, or the gate is the old inverted
one with a new name.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

import text_safe_qa as g

_REMOTION = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion")
_NEEDS_RENDER = pytest.mark.skipif(
    shutil.which("npx") is None or not os.path.isdir(os.path.join(_REMOTION, "node_modules")),
    reason="needs the remotion toolchain (cd remotion && npm install)")

LONG = "SUPERCALIFRAGILISTICEXPIALIDOCIOUSNESSABSOLUTELYUNBREAKABLE"


def _audit(shot, props, tmp_path):
    return g.audit_shot(shot, props, g.durations()[shot] // 2, str(tmp_path / "probe.png"))


def _audit_settled(shot, props, tmp_path):
    """At the frame `useT()` calls SETTLED — the frame every visual gate and the shot-critic read, and the
    only one where a title that animates in has finished arriving. Mid-clip, CardStack3D's title has not
    reached its resting place yet and the band finding is genuinely absent."""
    import render_remotion as rr
    frame = int(round(rr.frame_at_t(g.durations()[shot], rr.SETTLED_T)))
    return g.audit_shot(shot, props, frame, str(tmp_path / "probe.png"))


@_NEEDS_RENDER
def test_type_the_layout_cannot_hold_is_caught(tmp_path):
    """THE positive control for the CUT-OFF half: copy wider than the canvas, with nothing clipping it.

    IT USED TO BE A PRODUCTION REGISTER, AND THAT IS THE MISTAKE THIS FILE'S SIBLING ALREADY MADE ONCE.
    The control fed `AnalogTape` a 59-character word and depended on the register to keep overflowing. It
    stopped: AnalogTape now sizes its title with `fitTextPx(TITLE, W * 0.92 - SPLIT_MAX * 2, 168, …)`,
    which shrinks any word to the frame — looked at rather than inferred, the rendered still shows the word
    spanning roughly 380→1540px of 1920. The audit was correct to report nothing, and the only proof that
    this gate can SEE a cut went dark with `assert []`. (Exactly what happened to the BAND control when
    AsciiField was fixed; see `CaptionBandProbe`'s comment in Root.tsx.)

    `CutOffProbe` is synthetic and permanent, and `CutOffCleanProbe` carries the SAME copy at a size that
    fits — a detector that fires on everything proves as little as one that fires on nothing."""
    # the probes live in Root.tsx, not in src/shots, so `durations()` does not know them — and they are
    # static, so any frame is the settled one (same reason the band control passes 82 by hand)
    found = g.audit_shot("CutOffProbe", {"dna": "product"}, 82, str(tmp_path / "cut.png"))
    assert found, "a line far wider than the canvas was not reported"
    assert any("WIDER THAN THE CANVAS" in (v.get("text") or "") for v in found), found
    px = max(max((v.get("out") or {}).values(), default=0) for v in found)
    assert px > 100, "reported a cut of only %dpx for a line overflowing both edges" % px
    assert g.audit_shot("CutOffCleanProbe", {"dna": "product"}, 82, str(tmp_path / "fit.png")) == [], (
        "the same copy at a size that FITS was reported — the detector fires on everything")


@_NEEDS_RENDER
def test_a_register_that_autofits_its_copy_is_not_a_finding(tmp_path):
    """The other side of the control above, kept because it is what took the old one away: a register that
    shrinks overlong copy to the frame is CORRECT, and must stay clean however long the word is."""
    assert _audit("AnalogTape", {"title": LONG}, tmp_path) == [], (
        "AnalogTape fits its title with fitTextPx; a fitted word is not a cut")


@_NEEDS_RENDER
def test_a_travelling_world_is_not_a_finding(tmp_path):
    """TimelineTravel moves its world past the frame on purpose and says so with `data-bleed`. Reporting it
    would be the old gate's mistake: refusing the technique instead of catching the accident."""
    assert _audit("TimelineTravel", {}, tmp_path) == []


@_NEEDS_RENDER
def test_a_full_bleed_field_is_not_a_finding(tmp_path):
    """A flow field running to all four edges loses nothing a viewer needed. The pixel gate blocked exactly
    this (9.6% border ink, over its 4.5% error floor)."""
    assert _audit("FlowField", {}, tmp_path) == []


def test_a_render_that_failed_is_reported_not_passed_and_is_retried_first(monkeypatch, tmp_path):
    """A crashed render measured nothing. Counting it as clean is how a gate quietly stops gating.

    But it is not a TYPE finding either, and filing it as one sent the reader after a defect that did not
    exist: under a loaded sweep roughly one register in twenty came back "render failed", and none of them
    reproduced when run alone. So it is retried once, and what survives the retry is reported as a FAILURE —
    a frame nobody measured — distinct from a finding about the copy on it."""
    calls = []

    class R:
        returncode, stdout, stderr = 1, "", "Error: bundle failed\n"

    def _run(*a, **k):
        calls.append(1)
        return R()

    monkeypatch.setattr(g.subprocess, "run", _run)
    found = g.audit_shot("Whatever", {}, 10, str(tmp_path / "x.png"))
    assert found, "a failed render must not read as clean"
    assert "FAILED twice" in found[0]["text"] and "nothing was measured" in found[0]["text"]
    assert len(calls) == 2, "a flaky render must be retried once before it is believed (%d attempt(s))" % len(calls)


def test_a_render_that_succeeds_on_the_retry_is_not_reported(monkeypatch, tmp_path):
    """The point of the retry. The first attempt dies the way a lost browser connection does; the second
    carries the payload, and the sweep reports what the SECOND one measured."""
    payload = [{"out": {"right": 12}, "text": "x", "tag": "div", "cls": "", "font": "40px Inter"}]
    state = {"n": 0}

    class Dead:
        returncode, stdout, stderr = 1, "", "Error: at TCP.<anonymous> (node:net:347:12)\n"

    class Good:
        returncode = 1
        stdout = ""
        stderr = "at Object.cancelRender\nError: " + g.TAG + json.dumps(payload) + "\n"

    def _run(*a, **k):
        state["n"] += 1
        return Dead() if state["n"] == 1 else Good()

    monkeypatch.setattr(g.subprocess, "run", _run)
    assert g.audit_shot("Whatever", {}, 10, str(tmp_path / "x.png")) == payload
    assert state["n"] == 2


def test_the_payload_survives_the_stack_trace_around_it(monkeypatch, tmp_path):
    """The violations travel inside a render-cancelling error, so they arrive wrapped in a trace. Parsing has
    to find the JSON array and stop at its end, not at the first ']' in the noise that follows."""
    payload = [{"out": {"right": 848}, "text": "A]B", "tag": "div", "cls": "", "font": "104px Inter"}]
    class R:
        returncode = 1
        stdout = ""
        stderr = ("at Object.cancelRender\nError: " + g.TAG + json.dumps(payload)
                  + "\n    at foo (bar.js:1:1) [inner]\n")
    monkeypatch.setattr(g.subprocess, "run", lambda *a, **k: R())
    assert g.audit_shot("Whatever", {}, 10, str(tmp_path / "x.png")) == payload


def test_props_travel_by_file_so_cjk_copy_survives(monkeypatch, tmp_path):
    """A beat's real copy is routinely CJK, and a multibyte character in a --props argument breaks the arg
    before remotion sees it. The props must reach the render as a file, with the audit armed."""
    seen = {}
    class R:
        returncode, stdout, stderr = 0, "", ""
    def fake(cmd, **k):
        seen["cmd"] = cmd
        return R()
    monkeypatch.setattr(g.subprocess, "run", fake)
    g.audit_shot("Whatever", {"title": "最后一公里"}, 10, str(tmp_path / "x.png"))
    pf = [c for c in seen["cmd"] if c.startswith("--props=")]
    assert pf, seen["cmd"]
    payload = json.load(open(pf[0].split("=", 1)[1], encoding="utf-8"))
    assert payload["title"] == "最后一公里" and payload["textSafe"] is True


def test_every_register_the_audit_exempts_says_why():
    """`data-bleed` is the one way to silence this gate, so each use must carry a written reason beside it —
    the same discipline the energy waiver runs on. An unexplained exemption is a hole with a name."""
    import glob
    import re
    shots = os.path.join(_REMOTION, "src", "shots")
    bare = []
    for f in sorted(glob.glob(os.path.join(shots, "*.tsx"))):
        src = open(f, encoding="utf-8").read()
        for m in re.finditer(r"data-bleed(?!:)", src):    # the ATTRIBUTE, not the `data-bleed:` note itself
            before = src[max(0, m.start() - 400):m.start()]
            if "data-bleed:" not in before:          # the reason is written as a `data-bleed: ...` note
                bare.append(os.path.basename(f))
    assert not bare, "data-bleed with no written reason in: %s" % sorted(set(bare))


def test_an_echo_hides_a_duplicate_and_never_the_original():
    """`data-echo` is the second way to silence these gates, and the more dangerous one: `data-bleed` says
    "this type leaves the frame on purpose", while `data-echo` says "do not measure this type at all".

    It exists because `PointerTour` draws its page TWICE — sharp, and softened with a hole where the lens is
    looking — so every label really does sit on top of an identical copy of itself, and the collision audit
    reported exactly that: two boxes, same rect, on every string. A true finding and a useless one, and a
    register that always cries wolf is a register whose gate output nobody reads.

    The guarantee that keeps it from being a hole: the SHARP copy carries no marker, so every string is still
    audited exactly once. A register that marked its only copy would be hiding type from the gates, which is
    the failure this asserts against.
    """
    import glob
    import re
    shots = os.path.join(_REMOTION, "src", "shots")
    for f in sorted(glob.glob(os.path.join(shots, "*.tsx"))):
        src = open(f, encoding="utf-8").read()
        # the ATTRIBUTE, not the word in the comment beside it — counting prose as a use is how a check
        # like this passes on a register that marks everything and explains it twice
        marks = list(re.finditer(r"(?<![`\w-])data-echo(?![`\w:-])", src))
        if not marks:
            continue
        name = os.path.basename(f)
        # a duplicate is only a duplicate if the thing it duplicates is also drawn, unmarked
        copies = src.count("<PageCam2D")
        assert copies == 0 or len(marks) < copies, (
            "%s marks %d of its %d page copies as echoes — nothing is left to measure"
            % (name, len(marks), copies))
        for m in marks:
            before = src[max(0, m.start() - 500):m.start()]
            assert "data-echo" in before or "echo" in before.lower(), (
                "%s uses data-echo with no written reason beside it" % name)
        # and it must be hidden from assistive tech too: a duplicate nobody reads twice on screen is one no
        # screen reader should announce twice either
        assert "aria-hidden data-echo" in src or "data-echo aria-hidden" in src, (
            "%s hides a duplicate from the gates but not from a screen reader" % name)


def test_the_audit_actually_honours_the_echo_marker():
    """The rule has to live in the walker, not only in the register. Checked at source because the audit runs
    in the render browser: every walker that collects text must skip an echo, or one of the three gates goes
    on double-counting while the other two do not — the worst of both."""
    src = open(os.path.join(_REMOTION, "src", "runtime", "textSafe.tsx"), encoding="utf-8").read()
    assert "const isEcho" in src and "[data-echo]" in src, "textSafe no longer knows what an echo is"
    walkers = [b for b in src.split("root.querySelectorAll('*')")[1:]]
    assert len(walkers) >= 3, "the walker count changed — re-check which audits collect text"
    for i, w in enumerate(walkers):
        assert "isEcho(el)" in w[:400], (
            "walker #%d collects text without skipping echoes, so it measures the page twice" % (i + 1))


@_NEEDS_RENDER
def test_type_sitting_in_the_caption_band_is_caught(tmp_path):
    """The second question, and the one pixels could not answer.

    CardStack3D set its title 'All of it, in hand' wholly inside the strip the renderer reserves for the
    burned caption, so the caption drew straight through it. `band_debt.py` measured that band as an ink
    FRACTION and read 2.1% — under its threshold — while AuroraFlow, a generative field whose ground
    legitimately covers the frame, read 53%. The instrument ranked the harmless case 25x above the fatal one
    and the collision sat outside the manifest entirely. Type has a box; this asks the box.

    THE CONTROL IS SYNTHETIC, and it took two goes to get there. Written against CardStack3D, this test
    passed for exactly as long as that defect survived and then failed when it was fixed. It was moved to
    AsciiField, a full-frame character field — whose own docstring warned "a positive control must not be a
    bug report" and then became one: AsciiField was putting 224 glyphs under the burned subtitle at 9:16,
    that was fixed, and this test went quiet. A gate reporting nothing is indistinguishable from a gate that
    cannot report.

    `CaptionBandProbe` puts a line in the reserved strip on purpose, in a composition nobody will ever fix.
    Its twin sets the same line in the content zone and must come back clean — the pairing is the point: a
    detector that fires on everything proves as little as one that fires on nothing."""
    # the probes live in Root.tsx, not in src/shots, so `durations()` does not know them — and they are
    # static, so any frame is the settled one
    found = g.audit_shot("CaptionBandProbe", {"dna": "product"}, 82, str(tmp_path / "band.png"))
    hit = [v for v in found if v.get("band")]
    assert hit, "type placed inside the caption band was not reported: %r" % (found,)
    assert max(v["band"] for v in hit) > 20, "reported only %spx into a 227px band" % hit[0]["band"]
    clean = [v for v in g.audit_shot("CaptionBandCleanProbe", {"dna": "product"}, 82,
                                     str(tmp_path / "clean.png")) if v.get("band")]
    assert not clean, "the same line ABOVE the band was reported too — the audit fires on anything: %r" % clean


@_NEEDS_RENDER
def test_a_register_that_respects_the_band_stays_quiet(tmp_path):
    """The other half. If every register reported band debt, the finding would carry no information — and
    the reserved strip is 21% of the frame's height, so a rule that fires on any low content would."""
    assert not [v for v in _audit_settled("CinematicTitle", {"dna": "product"}, tmp_path) if v.get("band")]


def test_the_finding_says_which_defect_it_is():
    """The two defects want opposite fixes — text off the canvas is a layout that did not fit, text in the
    band is a layout that fit into space it does not own — and the message used to name neither."""
    assert "CUT OFF" in g._describe({"text": "x", "out": {"right": 40}})
    band = g._describe({"text": "All of it, in hand", "band": 79})
    assert "CAPTION BAND" in band and "79" in band and "burned caption" in band


def test_the_library_sweep_measures_the_mode_films_actually_ship():
    """Bare props render the un-themed fallback, and the Design DNA sets the type family and therefore every
    metric this audit measures. register_energy.py made exactly this mistake and reported one register at
    0.6% the same day it measured 32.2% themed."""
    import inspect
    src = inspect.getsource(g.scan_library)
    assert 'base["dna"] = dna' in src and g.DEFAULT_DNA, src


def test_a_face_that_comes_from_the_dna_is_never_measured_as_a_constant():
    """A register whose type size is fitted to a MEASURED width must measure the face that actually renders.

    `CompressedSensingEq` sets its equation in `var(--f-display)` — the FILM's face, not the register's. Its
    width was first guessed (1600px), then "measured" off a still (1352px), and the second number was worse
    than the first: a plain `remotion still` renders the fallback serif while every real film renders the
    DNA's own face, and the product DNA's Space Grotesk is wider. The gate went from 1 finding to 5.

    There is no correct constant here — the width is a property of a typeface the register does not choose.
    `fitText` measures the real one, and the family must be read from the DNA in JS: it measures in a
    detached node outside `.dna-film`, where `var(--f-display)` is undefined, so passing the CSS var
    measures the fallback again and reproduces the same bug one layer down (the trap `NeonGrid` documents).
    """
    import glob
    import re
    shots = os.path.join(_REMOTION, "src", "shots")
    bad = []
    for f in sorted(glob.glob(os.path.join(shots, "*.tsx"))):
        src = open(f, encoding="utf-8").read()
        # a CSS var can reach the call through a constant, which is how the first version of this check
        # passed on `fontFamily: SERIF` — the name carries the var, the call site does not show it
        varconst = {m.group(1) for m in re.finditer(r"const\s+([A-Za-z_$][\w$]*)\s*=\s*[^;]*var\(--f-", src)}
        for m in re.finditer(r"fitText\(\{", src):
            call = src[m.start():m.start() + 400]
            fam = re.search(r"fontFamily:\s*([^,\n]+)", call)
            if not fam:
                continue
            expr = fam.group(1).strip()
            if "var(--f-" in expr or any(re.search(r"\b%s\b" % re.escape(v), expr) for v in varconst):
                bad.append("%s: fitText measures %s" % (os.path.basename(f), expr))
    assert not bad, (
        "fitText was given a CSS variable, which is undefined in the node it measures in:\n  " +
        "\n  ".join(bad))


def test_the_equation_is_fitted_and_not_scaled():
    """`transform: scale()` does not change layout. Scaled down, the line still LAYS OUT at full width, so it
    overflows its box, `text-align: center` centres a box the glyphs have spilled out of, and the audit reads
    rects nowhere near the ink — measured, 198px of margin on one side against 24px on the other. Fitting the
    font size makes the line genuinely narrower, so picture and rects agree."""
    src = open(os.path.join(_REMOTION, "src", "shots", "CompressedSensingEq.tsx"), encoding="utf-8").read()
    eq = src[src.index("const eqY"):src.index("return (")]
    # CODE, not the prose beside it. The comment here explains why the transform was wrong, so matching the
    # bare word would fail on the very explanation of the fix — the same way `data-echo` in a comment made
    # its own check pass vacuously two commits ago.
    code = "\n".join(l.split("//")[0] for l in eq.splitlines())
    assert "fitText(" in code, "the equation no longer measures its own line"
    assert "transform" not in code, "the equation is back to being scaled by a transform"
    assert "dna?.fontDisplay" in code, "the measured face is not the film's"


def test_the_corridors_bleed_exemption_never_covers_its_subject():
    """`SurfaceCarousel` shows its neighbours partly on purpose — that IS the queue — so at 9:16 the panel
    above centre stage runs off the top with its nav labels, and the audit reported 8 strings cut off. The
    composition is right and so was the gate, which is what the bleed exemption is for.

    But the exemption is placed per panel, and the one it must never cover is the panel the shot is ABOUT.
    Marked wholesale the register would stop being audited at all, and the screen on centre stage — the one
    the viewer is asked to read — is exactly the one that must never bleed. The proof at render time is the
    9:16 library sweep; this is the cheap guard that the marking stayed CONDITIONAL."""
    src = open(os.path.join(_REMOTION, "src", "shots", "SurfaceCarousel.tsx"), encoding="utf-8").read()
    code = "\n".join(l.split("//")[0] for l in src.splitlines())
    assert "data-bleed" in code, "the corridor no longer declares its partly-shown neighbours"
    mark = code[code.index("data-bleed") - 200:code.index("data-bleed") + 80]
    assert "subject" in mark, (
        "the bleed exemption is unconditional — the centre panel is exempt too, so the subject of the shot "
        "is no longer audited:\n%s" % mark)
    assert "const subject" in code, "nothing computes which panel is on centre stage"


def test_the_character_field_stops_at_the_caption_band():
    """AsciiField drew its field to the bottom of the frame, so 224 glyphs sat under the burned subtitle at
    9:16 — the viewer reading a sentence through a moving field of characters. The glyphs are noise rather
    than copy, but every other register in this library reserves that strip and the caption is drawn on the
    shot's own ground. Whole rows only: `ceil` left the last row straddling the boundary and the svg clipped
    it through the middle of the glyphs, which reads as a broken render rather than as an edge."""
    src = open(os.path.join(_REMOTION, "src", "shots", "AsciiField.tsx"), encoding="utf-8").read()
    code = "\n".join(l.split("//")[0] for l in src.splitlines())
    assert "contentBottom(" in code, "the field no longer asks where the caption band starts"
    rows = [l for l in code.splitlines() if "rows =" in l]
    assert rows, "no row count found"
    assert all("bottom" in l for l in rows), (
        "the field's row count is not bounded by the content zone: %r" % rows)
    assert all("Math.floor" in l for l in rows), (
        "rows are rounded UP, so the last one is drawn half-clipped: %r" % rows)


# ── the sweep must be able to enumerate the FACES it claims to cover ─────────────────────────────────────
def test_the_dna_list_is_read_from_the_renderer_not_restated_here():
    """A register that passes in one face has been tested in one face.

    `scan_library`'s own docstring says the Design DNA "sets the type family and therefore every metric this
    audit measures" — and the sweep then only ever ran `product`, a narrow grotesque. Under `editorial`'s
    serif, VariableTypeMorph's one enormous word was sliced at BOTH edges of a 1:1 frame while the product
    sweep called it clean at all five aspects. `--all-dna` closes that, and it reads the list from the
    renderer so a new preset is covered the day it is added, not the day someone remembers this file.
    """
    import re as _re
    names = g.dna_presets()
    assert len(names) >= 5, "only %d preset(s): %r" % (len(names), names)
    src = open(os.path.join(g._REMOTION, "src", "runtime", "dna.tsx"), encoding="utf-8").read()
    for n in names:
        assert _re.search(r"\b%s\s*:" % _re.escape(n), src), "%r is not a key of DNA_PRESETS" % n
    # every name the sweep offers must actually resolve in the renderer, or the sweep reports a face it
    # never rendered
    for n in names:
        assert _re.search(r"%s\s*:\s*[A-Z_]+_DNA" % _re.escape(n), src), (
            "%r does not map to a DNA constant" % n)


def test_it_refuses_to_guess_the_dna_list(tmp_path, monkeypatch):
    """If the presets cannot be READ, the sweep must say so rather than fall back to a built-in list —
    falling back is how it came to sweep exactly one face for this long."""
    fake = tmp_path / "src" / "runtime"
    fake.mkdir(parents=True)
    (fake / "dna.tsx").write_text("export const DNA_PRESETS: Record<string, DesignDNA> = {\n};\n",
                                  encoding="utf-8")
    monkeypatch.setattr(g, "_REMOTION", str(tmp_path))
    with pytest.raises(RuntimeError, match="EMPTY"):
        g.dna_presets()


# ── COVERAGE: which universe a run covered, and what left it ───────────────────────────────────────
# This script covers TWO universes — a film's beats and the library — and the scope line must never let
# one be read as the other. `scan_film` counted only the beats that SURVIVED its skip branch, so a
# twelve-beat film where eight select a register printed "8 beats": a line indistinguishable from full
# coverage. And `--cjk` swallowed a shaping failure into `{}`, sweeping the register in its own LATIN
# demo defaults while the headline still said "CJK fixtures".

def _film(tmp_path, slides):
    d = tmp_path / "film"
    d.mkdir()
    (d / "storyboard.json").write_text(json.dumps({"meta": {"aspect": "16:9"}, "slides": slides}),
                                       encoding="utf-8")
    return str(d)


def test_a_film_run_says_how_many_of_its_beats_it_measured(monkeypatch, capsys, tmp_path):
    seen = []
    # this counts RENDERS; two identical beats would otherwise share one (see the reuse test below)
    monkeypatch.setattr(g, "NO_CACHE", True)
    monkeypatch.setattr(g, "audit_shot", lambda *a, **k: seen.append(a[0]) or [])
    out_dir = _film(tmp_path, [
        {"index": 1, "shot": "CinematicTitle", "shot_props": {}},
        {"index": 2, "shot": "GoneRegister", "shot_props": {}},
        {"index": 3, "shot_props": {}},
        {"index": 4, "shot": "CinematicTitle", "shot_props": {}},
    ])
    rc = g.main([out_dir])
    text = capsys.readouterr().out
    assert "across 2 of 4 beats" in text, text
    assert "2 beat(s) NOT measured" in text, text
    assert "'GoneRegister' is not a register" in text and "selects no register" in text, text
    assert rc == 2, "two beats nothing was measured on exited %r" % rc
    assert seen == ["CinematicTitle", "CinematicTitle"]


def test_a_fully_covered_film_says_so_and_exits_clean(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(g, "audit_shot", lambda *a, **k: [])
    rc = g.main([_film(tmp_path, [{"index": 1, "shot": "CinematicTitle", "shot_props": {}}])])
    assert "across 1 of 1 beats" in capsys.readouterr().out
    assert rc == 0


def test_the_library_scope_line_names_the_library_not_the_film(monkeypatch, capsys):
    """The two universes share one report. A `--library` line must read as registers, a film's as beats."""
    monkeypatch.setattr(g, "audit_shot", lambda *a, **k: [])
    g.main(["--library", "--limit=3"])
    text = capsys.readouterr().out
    # …and a NARROWED run must carry the catalogue's own size, or "3 of 3 registers" reads as the library.
    assert "3 of 3 registers (--limit=3 — of %d registers in shots/)" % len(g.durations()) in text, text
    assert "at default props" in text and "beats" not in text, text


def test_a_cjk_sweep_never_sweeps_a_register_in_english_under_a_cjk_headline(monkeypatch, capsys):
    """`except Exception: cjk_fixture[n] = {}` left the register with base props only, so it rendered its
    LATIN demo defaults — and the scope line still said 'CJK fixtures'. Chinese is where this audit's
    findings live, so a register swept in English is one the run says nothing about."""
    import cjk_type_qa as _cjk
    swept = []
    monkeypatch.setattr(g, "audit_shot", lambda n, *a, **k: swept.append(n) or [])
    real = _cjk.cjk_props

    def _broken(name, offset=0):
        if name == "Aliasing":
            raise ValueError("no shape for its props")
        if name == "AnalogTape":
            return {}, []                     # shaped, but nothing Chinese in it
        return real(name, offset)
    monkeypatch.setattr(_cjk, "cjk_props", _broken)
    rc = g.main(["--library", "--cjk", "--limit=4"])
    text = capsys.readouterr().out
    assert "Aliasing" not in swept and "AnalogTape" not in swept, swept
    assert "2 register(s) NOT swept" in text, text
    assert "could not be shaped" in text and "English demo defaults" in text, text
    assert "2 of 4 registers (--limit=4 — of %d registers in shots/) at CJK fixtures" % len(
        g.durations()) in text, text
    assert rc == 2


def test_type_under_the_size_floor_is_reported_as_the_viewer_sees_it(tmp_path):
    # nothing measured type SIZE: a frame of 19-26 px labels passed every gate, and the first sweep found 53 of 194
    # registers under ~24 px. The size is the RENDERED one — font-size times every transform and viewBox above it.
    found = g.audit_shot("SmallTypeProbe", {"dna": "product"}, 82, str(tmp_path / "small.png"), type_size=True)
    small = {v["text"]: v for v in found if v.get("small")}
    assert "TINY LABEL UNDER THE FLOOR" in small and g.type_size_level(small["TINY LABEL UNDER THE FLOOR"]) == "error"
    assert "SVG TOO SMALL" in small and small["SVG TOO SMALL"]["small"] < 24, small
    assert not any(t.startswith("TICK") for t in small), "declared texture (data-small) is not copy"
    assert "SCALED UP TO READ" not in small and "SVG LARGE ENOUGH" not in small, small
    # without the flag nothing about size is said (the library sweep's baseline is unchanged unless asked)
    assert not any(v.get("small") for v in g.audit_shot("SmallTypeProbe", {"dna": "product"}, 82,
                                                         str(tmp_path / "s2.png")))


def test_the_library_type_debt_is_a_warning_in_a_film_and_a_films_own_shot_is_held_to_the_floor():
    debt = g.type_debt()
    assert len(debt) >= 50 and all(set(r) == {"min_px", "under_error", "under_warn"} for r in debt.values())
    lib = g.durations()
    assert set(debt) <= set(lib), "the debt names registers the library no longer has: %s" % (set(debt) - set(lib))


# ── TITLE PLACEMENT ─────────────────────────────────────────────────────────────────────────────────────────────
def _t(ax, cy, text="一个标题"):
    return {"text": text, "ax": ax, "cy": cy, "px": 64, "align": "left"}


def test_title_placement_reads_the_edge_a_line_is_set_from():
    """A long LEFT-aligned title reaching past a third of the frame was read by its centre, as centred. Its zone is
    the edge it is set from (`ax`)."""
    titles = [(i, "S", _t(0.06, 0.12), "") for i in range(1, 6)]
    note = g.title_repetition(titles)
    assert note and "5 of 5" in note and "top-left" in note, note
    assert g.title_repetition([(1, "S", _t(0.06, 0.12), ""), (2, "S", _t(0.5, 0.5), ""),
                               (3, "S", _t(0.9, 0.85), ""), (4, "S", _t(0.06, 0.5), ""),
                               (5, "S", _t(0.5, 0.15), "")]) is None


def test_a_repeated_title_position_is_an_error_unless_the_film_declares_it():
    """It was a warning, and the unattended compound-interest run triaged it as accepted: 9 of 11 beats top-left."""
    titles = [(i, "S", _t(0.06, 0.12), "") for i in range(1, 10)]
    lvl, note = g.title_placement(titles, {})
    assert lvl == "error" and "fixed_title_position" in note, note
    lvl, note = g.title_placement(titles, {"fixed_title_position": "a running head every page of a ledger keeps"})
    assert lvl == "warn" and "kept by meta.fixed_title_position" in note, note
    assert g.title_placement(titles, {"fixed_title_position": "ok"})[0] == "error", "a reason, not a token"
    assert g.title_placement(titles[:3], {}) is None


@_NEEDS_RENDER
def test_the_title_is_the_largest_type_that_is_not_a_figure(tmp_path):
    """On the compound film the largest type was the printed figures (1,000 · 2,593.74 · 18%), so the old reading
    never saw the titles. The fixture puts a 220 px figure under a 64 px left-aligned title that reaches past the
    middle of the frame."""
    t = g.title_of("TitleProbeFixture", {}, 120, str(tmp_path / "t.png"))
    assert t and t["text"].startswith("THE SECOND YEAR") and t["align"] == "left", t
    assert t["ax"] < 1 / 3 and t["cy"] < 1 / 3, t


def test_title_placement_is_a_neighbourhood_not_a_ninth_and_sees_centred_titles():
    """Fixed thirds split six titles at x 0.31-0.36 between two zones and reported nothing; a title centred by its
    container (text-align "left") moved its left edge with its length. Same place = close height and ANY of left
    edge / centre / right edge lined up."""
    mk = lambda lx, cx, rx, cy: {"lx": lx, "cx": cx, "rx": rx, "ax": lx, "cy": cy, "text": "t"}
    straddle = [(i, "S", mk(0.31 + 0.01 * i, 0.45, 0.6, 0.12), "") for i in range(1, 7)]
    assert g.title_repetition(straddle)
    centred = [(i, "S", mk(0.5 - w, 0.5, 0.5 + w, 0.5), "") for i, w in enumerate([0.1, 0.2, 0.3, 0.15, 0.25], 1)]
    assert g.title_repetition(centred)
    varied = [(1, "S", mk(.05, .2, .35, .1), ""), (2, "S", mk(.6, .75, .9, .85), ""), (3, "S", mk(.3, .5, .7, .5), ""),
              (4, "S", mk(.05, .2, .35, .6), ""), (5, "S", mk(.6, .75, .9, .1), "")]
    assert g.title_repetition(varied) is None


def test_an_unchanged_beat_is_measured_once_and_its_answer_reused(monkeypatch, capsys, tmp_path):
    """Two beats with the same shot, props and frame are the same picture: the second reuses the first's answer, and a
    second RUN renders nothing at all. A failed render is never kept."""
    out = tmp_path / "film"
    out.mkdir()
    board = {"meta": {"renderer": "remotion"}, "slides": [
        {"shot": "CinematicTitle", "shot_props": {"title": "A"}},
        {"shot": "CinematicTitle", "shot_props": {"title": "A"}},
        {"shot": "CinematicTitle", "shot_props": {"title": "B"}}]}
    (out / "storyboard.json").write_text(json.dumps(board), encoding="utf-8")
    seen = []
    monkeypatch.setattr(g, "NO_CACHE", False)
    monkeypatch.setattr(g, "title_of", lambda *a, **k: None)
    monkeypatch.setattr(g, "audit_shot", lambda *a, **k: seen.append(a[1].get("title")) or [])
    g.scan_film(str(out))
    assert seen == ["A", "B"], seen
    g.scan_film(str(out))
    assert seen == ["A", "B"], "a second run re-rendered beats nothing had touched: %r" % seen
    (out / g.BEAT_CACHE).unlink()
    monkeypatch.setattr(g, "audit_shot", lambda *a, **k: seen.append("x") or
                        [{"text": "(render FAILED twice — nothing was measured on this frame: boom)", "out": {}}])
    g.scan_film(str(out))
    g.scan_film(str(out))
    # three beats, two runs, every one rendered: a failure is kept neither across runs nor within one
    assert seen.count("x") == 6, "a failed render was kept and replayed"
