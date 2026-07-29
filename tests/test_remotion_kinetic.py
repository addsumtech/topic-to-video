"""P4 backstop — varied motivated motion + kinetic typography.

Locks: per-shot ENERGY (amplitude) validates + threads; kinetic-text reveal frames auto-derive from the
shot that first frames an element; the move-DIVERSITY lint fires on N identical shots; and the TS wiring
(KineticText exists, elements use it, motions.ts takes an amplitude) can't silently regress."""
import os
import pytest
import render_remotion as rr
import storyboard as sb

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _board(shots, elements=None, dur=12.0):
    d = sb.new_storyboard({"aspect": "16:9", "fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "audio/01.mp3"; s["duration"] = dur
    s["stage"] = {"elements": elements or [
        {"id": "grid", "kind": "grid", "position": [0, 0, -1200]},
        {"id": "gateway", "kind": "panel", "position": [0, -40, 120], "title": "API Gateway"},
        {"id": "db", "kind": "hero", "position": [1200, 0, -400], "heroText": "PRIMARY"}]}
    s["shots"] = shots
    d["slides"] = [s]
    return d


# ── energy (motion amplitude) ─────────────────────────────────────────────────────────────────────
def test_energy_threads_and_defaults(tmp_path):
    sc = rr.build_props(_board([{"type": "HERO", "target": "gateway", "energy": "bold"},
                                {"type": "MEDIUM", "target": "db"}]), str(tmp_path))["scenes"][0]
    assert sc["shots"][0]["energy"] == "bold"
    assert sc["shots"][1]["energy"] == "balanced"  # default


def test_bad_energy_fails_loud(tmp_path):
    with pytest.raises(RuntimeError, match="energy must be"):
        rr.build_props(_board([{"type": "HERO", "target": "gateway", "energy": "huge"}]), str(tmp_path))


# ── kinetic type: reveal-on-arrival ─────────────────────────────────────────────────────────────────
def test_enter_frame_derives_from_first_targeting_shot(tmp_path):
    d = _board([{"type": "ESTABLISH", "duration": 4.0, "target": "grid"},
                {"type": "MEDIUM", "duration": 4.0, "target": "gateway", "carry": True},
                {"type": "HERO", "duration": 4.0, "target": "db"}])
    els = {e["id"]: e for e in rr.build_props(d, str(tmp_path))["scenes"][0]["stage"]["elements"]}
    assert els["grid"]["enterAtFrame"] == 0      # first shot
    assert els["gateway"]["enterAtFrame"] == 120  # shot 2 start (4s @30)
    assert els["db"]["enterAtFrame"] == 240       # shot 3 start


def test_explicit_enter_frame_is_kept(tmp_path):
    els = [{"id": "gateway", "kind": "panel", "position": [0, 0, 120], "title": "X", "enterAtFrame": 45}]
    d = _board([{"type": "HERO", "target": "gateway"}], elements=els)
    e = rr.build_props(d, str(tmp_path))["scenes"][0]["stage"]["elements"][0]
    assert e["enterAtFrame"] == 45  # author's value not overwritten


# ── move-diversity lint ─────────────────────────────────────────────────────────────────────────────
def _diversity_warn(shots):
    import validate as v
    errs, warns = [], []
    stage = {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0], "title": "X"}]}
    v._shot_stage_fields(stage, shots, "scene 1", errs, warns)
    return any("same framing+motion" in w for w in warns)


def test_diversity_lint_flags_identical_shots():
    assert _diversity_warn([{"type": "MEDIUM", "target": "a", "motion": "PUSH_IN"}] * 3)


def test_diversity_lint_passes_varied_shots():
    assert not _diversity_warn([{"type": "ESTABLISH", "target": "a"},
                                {"type": "MEDIUM", "target": "a", "motion": "PUSH_IN"},
                                {"type": "HERO", "target": "a", "motion": "PULL_OUT"}])


def test_diversity_lint_ignores_two_shots():
    assert not _diversity_warn([{"type": "MEDIUM", "target": "a"}, {"type": "MEDIUM", "target": "a"}])


# ── TS wiring source-guards (bundle-level regressions the Python tests can't see) ───────────────────
def test_kinetic_text_component_exists_and_is_restrained():
    src = open(os.path.join(_SKILL, "remotion", "src", "theme", "KineticText.tsx"), encoding="utf-8").read()
    assert "spring(" in src, "kinetic type must use a spring settle"
    assert "overshootClamping" in src or "damping: 200" in src, "restrained spring (no bouncy pop)"
    assert "reduced" in src, "must freeze under reduced motion"


def test_elements_use_kinetic_text():
    src = open(os.path.join(_SKILL, "remotion", "src", "stage", "elements.tsx"), encoding="utf-8").read()
    assert "KineticText" in src and src.count("KineticText") >= 4  # kicker+title+sub+textblock


def test_motions_takes_energy_amplitude():
    src = open(os.path.join(_SKILL, "remotion", "src", "stage", "motions.ts"), encoding="utf-8").read()
    assert "amp" in src and "* A" in src, "motion deltas must scale by an energy amplitude"


def test_elements_fade_in_on_arrival():
    """A content element must materialise at its enterAtFrame (camera arrival), not from frame 0 — else an
    empty glass card floats in space before its text reveals (mystery furniture)."""
    src = open(os.path.join(_SKILL, "remotion", "src", "stage", "elements.tsx"), encoding="utf-8").read()
    assert "enterAtFrame" in src and "isBackground" in src, "content elements fade in on arrival; backgrounds don't"
    assert "opacity: op" in src
