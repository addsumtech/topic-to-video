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


def test_a_render_that_failed_is_a_finding_not_a_pass(monkeypatch, tmp_path):
    """A crashed render measured nothing. Counting it as clean is how a gate quietly stops gating."""
    class R:
        returncode, stdout, stderr = 1, "", "Error: bundle failed\n"
    monkeypatch.setattr(g.subprocess, "run", lambda *a, **k: R())
    found = g.audit_shot("Whatever", {}, 10, str(tmp_path / "x.png"))
    assert found and "render failed" in found[0]["text"]


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


@_NEEDS_RENDER
def test_type_sitting_in_the_caption_band_is_caught(tmp_path):
    """The second question, and the one pixels could not answer.

    CardStack3D set its title 'All of it, in hand' wholly inside the strip the renderer reserves for the
    burned caption, so the caption drew straight through it. `band_debt.py` measured that band as an ink
    FRACTION and read 2.1% — under its threshold — while AuroraFlow, a generative field whose ground
    legitimately covers the frame, read 53%. The instrument ranked the harmless case 25x above the fatal one
    and the collision sat outside the manifest entirely. Type has a box; this asks the box.

    THE CONTROL IS AsciiField, NOT the register that prompted this. Written against CardStack3D, this test
    passed for exactly as long as that defect survived and then failed as a consequence of fixing it — a
    positive control must not be a bug report. AsciiField draws a full-frame field of characters: its ground
    IS the frame, so type in the band is what it is FOR and the finding is permanent. (If AsciiField ever
    stops being full-bleed, move the control to another full-bleed character register rather than deleting
    it — an audit that reports nothing is indistinguishable from one that cannot report.)"""
    found = _audit_settled("AsciiField", {"dna": "product"}, tmp_path)
    hit = [v for v in found if v.get("band")]
    assert hit, "a full-frame character field reported no type in the caption band: %r" % (found,)
    assert max(v["band"] for v in hit) > 20, "reported only %spx into a 227px band" % hit[0]["band"]


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
