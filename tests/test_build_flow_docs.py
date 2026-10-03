"""The flow reaches the agents that run it. A capability the authoring path cannot name is indistinguishable from
one that was never built — this repo has shipped that shape before (a seam vocabulary complete, tested and unused)."""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))


def _read(*p):
    return open(os.path.join(_ROOT, *p), encoding="utf-8").read()


def test_the_shot_director_is_told_to_build_and_how():
    d = _read("agents", "shot-director.md")
    for needle in ("## Step 0.55 — NEED FIRST", "meta.build_list", '"ref"', "workshop.py <out_dir> new-object",
                   "workshop.py <out_dir> new-shot", "workshop.py <out_dir> still", "ObjectStage", "ObjectCompare",
                   "ObjectPath", "ObjectTurntable", "references/object-authoring.md", "references/building-blocks.md",
                   "scripts/promote.py"):
        assert needle in d, needle


def test_s15_is_a_dimension_the_ledger_requires():
    import critic_ledger
    dims = dict(critic_ledger.dimensions())
    assert "S15" in dims and "BUILT THINGS" in dims["S15"]
    assert critic_ledger.precedents()["S15"] is None          # doctrine: no film has failed it yet


def test_the_critic_brief_lists_what_the_film_built(tmp_path, monkeypatch):
    import critic_brief
    monkeypatch.setattr(critic_brief, "_run", lambda *a, **k: "(stubbed)")
    board = {"meta": {"renderer": "remotion", "language": "zh",
                      "build_list": [{"id": "EspressoPuck", "kind": "object", "beats": [3], "slot": "ObjectStage",
                                      "means": "water forced through a packed bed",
                                      "accept": "caption hidden, the bed resists"}]},
             "slides": [{"index": 3, "shot": "ObjectStage", "shot_fit": {"verdict": "build", "ref": "EspressoPuck"}}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    text = critic_brief.build(str(tmp_path))
    assert "**Built things**" in text and "`EspressoPuck`" in text
    assert "water forced through a packed bed" in text and "caption hidden, the bed resists" in text


def test_skill_md_names_the_workshop_the_build_list_and_promotion():
    s = _read("SKILL.md")
    for needle in ("scripts/workshop.py", "meta.build_list", "scripts/promote.py", "references/object-authoring.md",
                   "PROMOTION IS THE USER'S CHOICE"):
        assert needle in s, needle


def test_the_authoring_reference_points_at_the_builder_s_two_references():
    a = _read("references", "remotion-shot-authoring.md")
    assert "references/building-blocks.md" in a and "references/object-authoring.md" in a
