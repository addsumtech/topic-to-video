"""A gate that is tier-agnostic in code must not be introduced by a tier-conditional sentence.

The narration is the one thing the two tiers share outright: both read the same `narration` from the same
`storyboard.json`, and `tts.py` speaks it for both. `voice_qa.py` is therefore a BOTH-TIERS gate — and its
instruction sat between "On a `meta.renderer:"remotion"` deck, run shot_proof…" and "For an HTML-tier deck,
also run keyframe_qa…". An author working on an html deck reads down the page, hits the remotion sentence,
sees it is not their tier, and skips everything under it — including the voice gate.

Nothing was wrong with the code. The rule existed, was correct, applied to them, and was not on the path
they take. This repo has paid for that shape before in another skill: a rule written only where its reader
does not look is not a rule.

So: for every gate that reads the shared narration, find the bold lead-in that introduces it and require
that the lead-in does not scope it to ONE tier. This is a text check on SKILL.md, which is exactly the
level the failure lives at.
"""
import os
import re

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Gates whose input is the narration in storyboard.json — shared by both renderers by construction.
SHARED_NARRATION_GATES = ["voice_qa.py", "script_audition.py", "pedagogy_qa.py", "rhythm_qa.py"]

_SINGLE_TIER = re.compile(r"`meta\.renderer:\"remotion\"`|remotion.{0,12}deck|HTML-tier deck|html-tier deck",
                          re.I)
_BOTH = re.compile(r"both tiers|either tier|both renderers", re.I)


_STEP = re.compile(r"^\d+\. \*\*", re.M)      # a numbered workflow step

# THE CONVENTION IS DECLARED, NOT INFERRED, and three failed attempts are why.
#
# Trying to work out from the prose WHICH tier condition governs a sentence does not survive contact with
# this file: one version read the bold run the gate is written in and passed the very tree the defect was
# on; one read back through the whole document and reported thirteen offences on a clean tree; one bounded
# the scan to the numbered step and still reported seven, because a tool list and a workflow step look the
# same to a regex. A check that cries wolf is a check that gets switched off — this repo has written that
# down more than once, and shipping a fourth guess would be ignoring it.
#
# So the invariant is carried by a MARKER the author writes. Every shared-narration gate's workflow lead-in
# says "BOTH TIERS", which is exact to test, and — more to the point — is the thing an html author reading
# down the page actually needs to see. The text that fixes the bug and the text the test checks are the
# same text.
_MARKER = re.compile(r"BOTH TIERS", re.I)


def _workflow_lead_ins(text, gate):
    """Every bold lead-in that introduces this gate as a step to RUN (not a tool-list entry)."""
    out = []
    for m in re.finditer(r"\*\*([^*]{0,300}?)\*\*", text, re.S):
        lead = m.group(1)
        if re.search(r"scripts/%s" % re.escape(gate), lead) and re.search(r"\brun\b|AUDIBLE", lead, re.I):
            out.append(lead)
    return out


@pytest.mark.parametrize("gate", SHARED_NARRATION_GATES)
def test_a_shared_gate_is_not_introduced_by_a_single_tier_sentence(gate):
    skill = open(os.path.join(_ROOT, "SKILL.md"), encoding="utf-8").read()
    # the WORKFLOW mention, not the tool-list one: the workflow is the path an author walks
    hits = [m.start() for m in re.finditer(re.escape(gate), skill)]
    assert hits, "%s is not mentioned in SKILL.md at all" % gate
    leads = _workflow_lead_ins(skill, gate)
    assert leads, (
        "%s has no workflow lead-in telling an author to RUN it — it exists in the tool list and is not on "
        "anyone's path" % gate)
    offenders = [l.strip().replace("\n", " ")[:160] for l in leads if not _MARKER.search(l)]
    assert not offenders, (
        "%s reads the shared narration, so it applies to BOTH tiers — say so in the lead-in that tells an "
        "author to run it. Without it the step sits under whatever tier sentence came before, and the "
        "author on the other tier skips the clause and the gate with it. Offending lead-in(s): %r"
        % (gate, offenders))
