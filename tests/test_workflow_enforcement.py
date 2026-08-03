"""Backstops for the STRICTER agent-workflow enforcement on the cinematic tier (hardening requested after an
enforcement audit showed the workflow was the intended-but-bypassable path and novelty was critic-judgment,
not a hard gate). Three deterministic gates now BLOCK where they used to warn:

  (1) meta.template_contest is required (ERROR) at the DEFAULT balanced audacity, not only bold/experimental
      (only `conservative` — which may skip the contest — stays a warning).
  (2) render_remotion.render() REQUIRES content_plan.json for a cinematic deck (the "agents ran" trace),
      unless --no-plan / meta.no_plan opts out of the workflow deliberately.
  (3) the archetype-diversity checks (>45% / >=3 distinct / >=1 signature / no back-to-back) ERROR-block on a
      >=4-archetype film instead of merely warning.

Honest scope kept in the docstrings: (3) reads the archetype STRING, not pixels, so 'different label, same
panel' still needs design-critic D12h — this gate catches only the DECLARED-sameness case."""
import json
import os
import sys

import pytest

_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_SKILL, "scripts"))
import render_remotion as rr  # noqa: E402
import validate as v  # noqa: E402


def _cine(extra=None, arches=None):
    """A cinematic deck. `arches` = per-beat archetype list (default a single hero-on-void beat)."""
    m = {"renderer": "remotion", "fps": 30, "cinematic_template": "defrag", "accent": "#37e0ff"}
    m.update(extra or {})
    arches = arches or ["hero-on-void"]
    slides = [{"index": i + 1, "type": "cinematic", "archetype": a, "duration": 5, "narration": "x",
               "stage": {"elements": [{"id": "a%d" % i, "kind": "display", "text": "x", "position": [0, 0, 0]}]},
               "shots": [{"type": "HERO", "target": "a%d" % i}]} for i, a in enumerate(arches)]
    return {"meta": m, "slides": slides}


# ── (1) template contest is required at the DEFAULT (balanced) audacity ─────────────────────────────────
def test_template_contest_errors_at_default_balanced_audacity():
    r = v.evaluate(_cine(), "/tmp", pre_tts=True)  # audacity unset -> balanced
    assert any("template_contest" in e for e in r["errors"]), \
        "a cinematic film at the DEFAULT audacity must now ERROR without a recorded contest"


def test_template_contest_only_warns_at_conservative():
    r = v.evaluate(_cine({"audacity": "conservative"}), "/tmp", pre_tts=True)
    assert not any("template_contest" in e for e in r["errors"]), "conservative may skip the contest — warn only"
    assert any("template_contest" in w for w in r["warnings"])


def test_template_contest_present_passes_at_balanced():
    r = v.evaluate(_cine({"template_contest": {"candidates": ["defrag", "command-surface"], "winner": "defrag"}}),
                   "/tmp", pre_tts=True)
    assert not any("template_contest" in e for e in r["errors"])


# ── (2) render() requires the content_plan.json trace for a cinematic deck ───────────────────────────────
def _write_cine_board(d):
    board = {"meta": {"renderer": "remotion", "fps": 30, "cinematic_template": "defrag", "accent": "#37e0ff"},
             "slides": [{"index": 1, "type": "cinematic", "archetype": "hero-on-void", "duration": 5.0,
                         "audio": "audio/01.mp3", "narration": "x",
                         "stage": {"elements": [{"id": "a", "kind": "display", "text": "x", "position": [0, 0, 0]}]},
                         "shots": [{"type": "HERO", "target": "a", "duration": 5.0}]}]}
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "storyboard.json"), "w", encoding="utf-8") as f:
        json.dump(board, f)


def test_render_blocks_cinematic_without_content_plan(tmp_path):
    # the plan-trace gate runs BEFORE the Node toolchain probe, so this holds with or without npx installed.
    _write_cine_board(str(tmp_path))
    with pytest.raises(RuntimeError, match="content_plan.json"):
        rr.render(str(tmp_path))


def test_render_no_plan_flag_skips_the_gate(tmp_path):
    # --no-plan opts out: whatever render raises next, it is NOT the plan-trace error (a deliberate hand-author).
    _write_cine_board(str(tmp_path))
    try:
        rr.render(str(tmp_path), no_plan=True, sample=999)  # sample 999 -> a later, deterministic raise
    except RuntimeError as e:
        assert "content_plan.json" not in str(e), "no_plan must SKIP the plan-trace gate"


def test_render_meta_no_plan_also_skips(tmp_path):
    _write_cine_board(str(tmp_path))
    p = os.path.join(str(tmp_path), "storyboard.json")
    d = json.load(open(p)); d["meta"]["no_plan"] = True; json.dump(d, open(p, "w"))
    try:
        rr.render(str(tmp_path), sample=999)
    except RuntimeError as e:
        assert "content_plan.json" not in str(e), "meta.no_plan must SKIP the plan-trace gate"


def test_render_plan_present_passes_the_gate(tmp_path):
    _write_cine_board(str(tmp_path))
    open(os.path.join(str(tmp_path), "content_plan.json"), "w").write("{}")
    try:
        rr.render(str(tmp_path), sample=999)
    except RuntimeError as e:
        assert "content_plan.json" not in str(e), "a present content_plan.json must satisfy the gate"


# ── (3) archetype diversity now BLOCKS (errors) on a >=4-archetype same-look film ────────────────────────
def test_archetype_sameness_now_errors():
    # 4 beats all hero-on-void: >45%, <3 distinct, no signature, back-to-back — all now ERROR (was warn).
    board = _cine({"audacity": "conservative",
                   "template_contest": {"candidates": ["defrag", "command-surface"], "winner": "defrag"}},
                  arches=["hero-on-void"] * 4)
    r = v.evaluate(board, "/tmp", pre_tts=True)
    assert any("design-variety" in e for e in r["errors"]), "a same-look >=4-beat cinematic film must now BLOCK"


def test_archetype_variety_passes():
    board = _cine({"audacity": "conservative",
                   "template_contest": {"candidates": ["defrag", "command-surface"], "winner": "defrag"}},
                  arches=["hero-on-void", "process-flow", "metric-wall", "metaphor-mechanic"])
    r = v.evaluate(board, "/tmp", pre_tts=True)
    assert not any("design-variety" in e for e in r["errors"]), \
        "a varied film (4 distinct, a metaphor signature, no back-to-back) must pass the diversity gate"
