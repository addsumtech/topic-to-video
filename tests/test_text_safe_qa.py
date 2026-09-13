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
    """THE positive control: copy longer than the layout assumed is the accident this exists for, and it is
    what real topic copy does to a register tuned on a short demo string."""
    found = _audit("AtomOrbital", {"title": LONG}, tmp_path)
    assert found, "a word far wider than the frame was not reported"
    assert any("SUPERCALIFRAGIL" in (v.get("text") or "") for v in found), found
    px = max(max((v.get("out") or {}).values(), default=0) for v in found)
    assert px > 100, "reported a cut of only %dpx for a word overflowing both edges" % px


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
