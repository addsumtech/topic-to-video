"""The style engine is DOCUMENTED where an agent will look, and gated where a film is delivered.

A capability that is not in the index, the agent's procedure and the delivery gates is a capability no run uses
(memory: an opt-in gate that is not scaffolded never ran). These pin each place it must appear.
"""
import json
import os
import re

import style_spec as ss

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*p):
    return open(os.path.join(ROOT, *p), encoding="utf-8").read()


def test_style_scripts_are_indexed_and_documented():
    skill, ps = _read("SKILL.md"), _read("references", "pipeline-scripts.md")
    for s in ("style_spec.py", "style_sample.py", "style_qa.py", "style_coverage.py"):
        assert s in skill, "SKILL.md does not index %s" % s
        assert re.search(r"scripts/%s" % re.escape(s), ps), "pipeline-scripts.md has no entry for %s" % s
    assert "--signoff" in skill and "only after" in skill.lower(), "SKILL.md does not say the sign-off follows the user's yes"


def test_the_reference_explains_every_axis():
    ref = _read("references", "style-engine.md")
    for group, params in ss.AXES.items():
        for name in params:
            assert "%s.%s" % (group, name) in ref, "references/style-engine.md does not explain %s.%s" % (group, name)
    for rule in ("recolour", "refs_missing", "shortfall", "style_sample.py"):
        assert rule in ref, rule


def test_the_remotion_design_step_decomposes_a_named_style():
    sd = _read("agents", "shot-director.md")
    assert "references/style-engine.md" in sd and "meta.style" in sd
    lib = _read("remotion", "LIBRARY.md")
    assert "## Style follows the film's spec" in lib


def test_style_qa_is_a_delivery_gate_for_a_styled_film_only(tmp_path):
    import critic_ledger as cl
    base = {"renderer": "remotion"}
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": base, "slides": []}))
    assert "style_qa.py" not in [g[1] for g in cl.delivery_gates(str(tmp_path))]
    styled = dict(base, style={"name": "x", "refs": [], "refs_missing": "t", "line": {"outline": "all"}})
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": styled, "slides": []}))
    gates = {g[1]: g for g in cl.delivery_gates(str(tmp_path))}
    assert "style_qa.py" in gates and gates["style_qa.py"][4] is True        # blocking


def test_the_axis_gallery_shows_every_value():
    import style_axis_gallery as g
    cases = g.cases()
    for group, params in ss.AXES.items():
        for name, p in params.items():
            if p["kind"] != "enum":
                continue
            for v in p["values"]:
                if v == p["default"] or name in ("stepping", "easing", "source"):    # motion and provenance: not a still
                    continue
                assert any(c["axis"] == "%s.%s" % (group, name) and c["value"] == v for c in cases), (group, name, v)
