"""The Blender plate tier is findable: SKILL.md points at its scripts and reference, the reference carries the whole
routing vocabulary, and pipeline-scripts.md has an entry for each script."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import blender_plate as bp  # noqa: E402


def _read(rel):
    return open(os.path.join(ROOT, rel), encoding="utf-8").read()


def test_skill_md_points_at_the_plate_tier():
    s = _read("SKILL.md")
    for name in ("scripts/blender_plate.py", "scripts/plate_qa.py", "references/blender-plates.md"):
        assert name in s, name


def test_reference_lists_every_reason_and_the_contract():
    s = _read("references/blender-plates.md")
    for word in bp.BLENDER_WHY:
        assert "`%s`" % word in s, word
    for field in ("id", "scene", "why", "mode", "engine", "cues", "anchors", "objects", "assets", "build(k)", "pose(k, t)",
                  "blender_budget_min"):
        assert field in s, field


def test_pipeline_scripts_has_both_entries():
    s = _read("references/pipeline-scripts.md")
    assert "`scripts/blender_plate.py <out_dir>" in s and "`scripts/plate_qa.py <out_dir>" in s
